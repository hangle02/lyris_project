"""Import/export Character Card (V1, V2, V3) dạng JSON hoặc PNG.

Hàm thuần, không đụng DB. Card import ra là bản nháp chưa lưu (`id=None`, `avatar=None`);
Studio mở form để người dùng duyệt rồi mới lưu.

- Phần riêng của Lyris (giới tính, xưng hô, style profile...) nằm ở `data.extensions.lyris`,
  nên bản export của Lyris import lại không mất gì.
- Những phần của card V2/V3 mà Lyris chưa dùng (system_prompt, creator...) được giữ nguyên trong
  `card.extensions["v2"]` và trả về đúng chỗ cũ khi export.
- Phase 4: `character_book` vẫn đi theo bản nháp trong `extensions.v2`; khi card được lưu (POST/PUT /cards)
  nó thành các mục thế giới của card (lyris/lore) và bị bỏ khỏi extensions. Export dựng lại `character_book`
  từ các mục đó (`export_card_json(..., lore=...)`).
"""
from __future__ import annotations

import base64
import binascii
import colorsys
import hashlib
import io
import json
import re
import struct
import unicodedata
import zlib
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from lyris.lore.book import entries_to_book
from lyris.models import AddressTerms, CharacterCard, Gender, Language, LoreEntry

MAX_CARD_BYTES = 8 * 1024 * 1024
# Giới hạn bung nén cho zTXt/iTXt (chống "zip bomb").
_MAX_INFLATED_BYTES = 16 * 1024 * 1024
# Giới hạn của API khi lưu card (docs/phase2.md); import chỉ cảnh báo, không cắt.
_MAX_TEXT_CHARS = 20_000
_MAX_NAME_CHARS = 80
_MAX_TAGS = 20

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_PNG_CHARA_KEYS = ("chara", "ccv3")

# Khoá trong card.extensions chứa phần V2/V3 giữ lại để export.
PRESERVED_KEY = "v2"
LYRIS_EXT_KEY = "lyris"
# Bản export trước khi đổi tên app (Nora) ghi dữ liệu riêng ở khoá "nora"; vẫn đọc được.
LEGACY_EXT_KEYS = ("nora",)
LYRIS_EXT_VERSION = 1

# Các khoá trong `data` của V2 được ánh xạ thẳng vào trường Lyris (không cần giữ lại).
_MAPPED_KEYS = frozenset(
    {"name", "description", "personality", "scenario", "first_mes", "alternate_greetings",
     "mes_example", "creator_notes", "tags", "extensions"}
)
# Khoá V2/V3 có ảnh hưởng tới cách nhân vật hành xử mà Lyris chưa dùng -> cảnh báo.
_UNUSED_LABELS: dict[str, str] = {
    "system_prompt": "system_prompt (lời nhắc hệ thống riêng)",
    "post_history_instructions": "post_history_instructions (lời nhắc sau lịch sử chat)",
    "group_only_greetings": "group_only_greetings (lời mở đầu cho chat nhóm)",
    "assets": "assets (ảnh/tài nguyên đi kèm card V3)",
}
# V1 kiểu Pygmalion/TavernAI cũ dùng tên khoá khác.
_V1_ALIASES: dict[str, str] = {
    "char_name": "name",
    "char_persona": "description",
    "world_scenario": "scenario",
    "char_greeting": "first_mes",
    "example_dialogue": "mes_example",
    "creatorcomment": "creator_notes",
}
_V1_KEYS = frozenset({"name", "description", "personality", "scenario", "first_mes", "mes_example"})

# Nhãn khi nối các trường riêng của Lyris vào cuối description lúc export.
_EXTRA_FIELDS = ("appearance", "background", "goals", "secrets", "speech_style")
_EXTRA_LABELS: dict[str, dict[str, str]] = {
    "vi": {
        "appearance": "Ngoại hình",
        "background": "Hoàn cảnh",
        "goals": "Mục tiêu",
        "secrets": "Bí mật",
        "speech_style": "Cách nói",
    },
    "en": {
        "appearance": "Appearance",
        "background": "Background",
        "goals": "Goals",
        "secrets": "Secrets",
        "speech_style": "Speech style",
    },
}
_FIELD_LABELS_VI: dict[str, str] = {
    "name": "tên",
    "description": "mô tả",
    "personality": "tính cách",
    "scenario": "bối cảnh",
    "first_mes": "lời mở đầu",
    "mes_example": "ví dụ thoại",
    "creator_notes": "ghi chú người tạo",
}
_GENDER_VI: dict[str, str] = {"male": "nam", "female": "nữ", "other": "khác"}

_VI_CHARS = frozenset(
    "àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ"
)
_WORD_RE = re.compile(r"[^\W\d_]+")
_START_LINE_RE = re.compile(r"^[ \t]*<start>[ \t]*$", re.IGNORECASE | re.MULTILINE)
_LEGACY_USER_RE = re.compile(r"<user>", re.IGNORECASE)
_LEGACY_BOT_RE = re.compile(r"<bot>", re.IGNORECASE)
_MALE_RE = re.compile(r"\b(?:he|him|his|himself|anh ấy|hắn|chàng|ông ấy)\b", re.IGNORECASE)
_FEMALE_RE = re.compile(r"\b(?:she|her|hers|herself|cô ấy|nàng|bà ấy)\b", re.IGNORECASE)
_MALE_TAGS = frozenset({"male", "man", "boy", "nam", "husbando"})
_FEMALE_TAGS = frozenset({"female", "woman", "girl", "nữ", "waifu"})


class CardImportError(ValueError):
    """File card không đọc được (thông điệp tiếng Việt, API trả 422)."""


@dataclass
class ImportResult:
    card: CharacterCard  # id=None, avatar=None
    warnings: list[str] = field(default_factory=list)  # tiếng Việt
    image: bytes | None = None  # ảnh PNG gốc nếu import từ PNG


# --------------------------------------------------------------------------- PNG chunk


def _png_chunks(data: bytes) -> list[tuple[bytes, bytes]]:
    """Tách các chunk (type, data) của một file PNG. Không kiểm CRC (card ngoài hay ghi sai)."""
    if not data.startswith(PNG_SIGNATURE):
        raise CardImportError("File không phải ảnh PNG hợp lệ.")
    chunks: list[tuple[bytes, bytes]] = []
    pos = len(PNG_SIGNATURE)
    end = len(data)
    while pos + 8 <= end:
        (length,) = struct.unpack(">I", data[pos : pos + 4])
        ctype = data[pos + 4 : pos + 8]
        start = pos + 8
        stop = start + length
        if stop + 4 > end:
            # File bị cắt cụt: dùng những chunk đã đọc được.
            break
        chunks.append((ctype, data[start:stop]))
        pos = stop + 4
        if ctype == b"IEND":
            break
    if not chunks or chunks[0][0] != b"IHDR":
        raise CardImportError("File PNG bị hỏng (không đọc được phần đầu ảnh).")
    return chunks


def _inflate(payload: bytes) -> bytes:
    d = zlib.decompressobj()
    out = d.decompress(payload, _MAX_INFLATED_BYTES)
    if d.unconsumed_tail:
        raise CardImportError("Dữ liệu card trong ảnh PNG quá lớn.")
    return out


def _text_chunk(ctype: bytes, payload: bytes) -> tuple[str, str] | None:
    """Đọc chunk văn bản tEXt/zTXt/iTXt -> (keyword, text). Chunk hỏng -> None."""
    try:
        if ctype == b"tEXt":
            key, _, text = payload.partition(b"\x00")
            return key.decode("latin-1"), text.decode("latin-1")
        if ctype == b"zTXt":
            key, _, rest = payload.partition(b"\x00")
            if not rest:
                return None
            return key.decode("latin-1"), _inflate(rest[1:]).decode("latin-1")
        if ctype == b"iTXt":
            key, _, rest = payload.partition(b"\x00")
            if len(rest) < 2:
                return None
            compressed, rest = rest[0], rest[2:]
            _lang, _, rest = rest.partition(b"\x00")
            _translated, _, text = rest.partition(b"\x00")
            raw = _inflate(text) if compressed else text
            return key.decode("latin-1"), raw.decode("utf-8")
    except (zlib.error, UnicodeDecodeError):
        return None
    return None


def _make_chunk(ctype: bytes, payload: bytes) -> bytes:
    crc = zlib.crc32(ctype + payload) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + ctype + payload + struct.pack(">I", crc)


def _is_card_text_chunk(ctype: bytes, payload: bytes) -> bool:
    if ctype not in (b"tEXt", b"zTXt", b"iTXt"):
        return False
    key = payload.split(b"\x00", 1)[0].decode("latin-1", errors="replace").lower()
    return key in _PNG_CHARA_KEYS


def _decode_embedded(text: str) -> Any:
    """Giải mã nội dung chunk 'chara'/'ccv3': base64 của JSON (một số app ghi JSON thô)."""
    stripped = text.strip()
    if stripped.startswith("{"):
        return json.loads(stripped)
    compact = re.sub(r"\s+", "", stripped)
    compact += "=" * (-len(compact) % 4)
    try:
        raw = base64.b64decode(compact, validate=True)
    except (binascii.Error, ValueError):
        raw = base64.urlsafe_b64decode(compact)
    return json.loads(raw.decode("utf-8-sig"))


def _read_png_card(data: bytes) -> Any:
    chunks = _png_chunks(data)
    found: dict[str, str] = {}
    for ctype, payload in chunks:
        if ctype not in (b"tEXt", b"zTXt", b"iTXt"):
            continue
        parsed = _text_chunk(ctype, payload)
        if parsed is None:
            continue
        key = parsed[0].strip().lower()
        if key in _PNG_CHARA_KEYS and key not in found:
            found[key] = parsed[1]
    if not found:
        raise CardImportError(
            "Ảnh PNG này không chứa dữ liệu nhân vật (không có chunk 'chara' hoặc 'ccv3')."
        )
    # V3 khuyến nghị ưu tiên 'ccv3'; hỏng thì lùi về 'chara'.
    for key in ("ccv3", "chara"):
        if key not in found:
            continue
        try:
            obj = _decode_embedded(found[key])
        except (binascii.Error, ValueError, UnicodeDecodeError, RecursionError):
            continue
        if isinstance(obj, dict):
            return obj
    raise CardImportError("Dữ liệu card trong ảnh PNG bị hỏng (base64 hoặc JSON không hợp lệ).")


# --------------------------------------------------------------------------- helpers


class _Warn:
    def __init__(self) -> None:
        self.items: list[str] = []

    def add(self, msg: str) -> None:
        if msg not in self.items:
            self.items.append(msg)


def _norm_text(value: str) -> str:
    text = value.replace("\r\n", "\n").replace("\r", "\n")
    text = _LEGACY_USER_RE.sub("{{user}}", text)
    text = _LEGACY_BOT_RE.sub("{{char}}", text)
    return text.strip()


def _get_str(src: dict[str, Any], key: str, warn: _Warn, label: str | None = None) -> str:
    value = src.get(key)
    if value is None:
        return ""
    if isinstance(value, str):
        return _norm_text(value)
    warn.add(f'Trường "{label or _FIELD_LABELS_VI.get(key, key)}" có kiểu dữ liệu không hợp lệ nên đã bỏ qua.')
    return ""


def _get_str_list(src: dict[str, Any], key: str, warn: _Warn, label: str) -> list[str]:
    value = src.get(key)
    if value is None:
        return []
    if isinstance(value, str):
        # Một số app ghi tags dạng "a, b, c".
        if key == "tags":
            value = value.split(",")
        else:
            value = [value]
    if not isinstance(value, list):
        warn.add(f'Trường "{label}" có kiểu dữ liệu không hợp lệ nên đã bỏ qua.')
        return []
    out: list[str] = []
    skipped = False
    for item in value:
        if not isinstance(item, str):
            skipped = True
            continue
        text = _norm_text(item)
        if text and text not in out:
            out.append(text)
    if skipped:
        warn.add(f'Một số mục trong "{label}" không phải văn bản nên đã bỏ qua.')
    return out


def _is_empty(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _convert_examples(text: str) -> str:
    """mes_example: dòng `<START>` -> dòng trống (giữ `{{char}}:`/`{{user}}:`)."""
    text = _START_LINE_RE.sub("", text)
    text = re.sub(r"\n[ \t]*\n(?:[ \t]*\n)+", "\n\n", text)
    return text.strip()


def _examples_to_v2(text: str) -> str:
    """example_dialogues của Lyris -> mes_example V2: mỗi đoạn (cách bởi dòng trống) mở bằng `<START>`."""
    text = text.strip()
    if not text:
        return ""
    if _START_LINE_RE.search(text):
        return text
    blocks = [b.strip() for b in re.split(r"\n[ \t]*\n", text) if b.strip()]
    return "\n".join(f"<START>\n{b}" for b in blocks)


def _extras_block(values: dict[str, str], language: str) -> str:
    labels = _EXTRA_LABELS.get(language, _EXTRA_LABELS["vi"])
    parts = [f"{labels[k]}: {values[k].strip()}" for k in _EXTRA_FIELDS if values.get(k, "").strip()]
    return "\n\n".join(parts)


def _strip_extras(description: str, values: dict[str, str]) -> tuple[str, bool]:
    """Bỏ phần ngoại hình/hoàn cảnh... mà export đã nối vào cuối description. Trả (mô tả, đã bỏ được)."""
    for lang in ("vi", "en"):
        block = _extras_block(values, lang)
        if not block:
            return description, True
        if description == block:
            return "", True
        if description.endswith("\n\n" + block):
            return description[: -len(block) - 2].rstrip(), True
    return description, False


def _guess_language(texts: list[str]) -> Language:
    words = _WORD_RE.findall("\n".join(texts).lower())
    if not words:
        return "en"
    vi_words = sum(1 for w in words if any(ch in _VI_CHARS for ch in w))
    return "vi" if vi_words >= 3 and vi_words / len(words) >= 0.15 else "en"


def _guess_gender(texts: list[str], tags: list[str]) -> Gender:
    blob = "\n".join(texts)
    male = len(_MALE_RE.findall(blob))
    female = len(_FEMALE_RE.findall(blob))
    lowered = {t.lower() for t in tags}
    if lowered & _MALE_TAGS:
        male += 5
    if lowered & _FEMALE_TAGS:
        female += 5
    if male >= 2 and male >= 2 * female:
        return "male"
    if female >= 2 and female >= 2 * male:
        return "female"
    return "other"


def _default_style(styles: list[str]) -> str:
    if "chung" in styles or not styles:
        return "chung"
    return styles[0]


# --------------------------------------------------------------------------- import


def _detect(obj: Any) -> tuple[dict[str, Any], str]:
    """-> (data, phiên bản 'v1' | 'v2' | 'v3')."""
    if not isinstance(obj, dict):
        raise CardImportError("File không phải card nhân vật (JSON phải là một object).")
    spec = obj.get("spec")
    data = obj.get("data")
    if spec in ("chara_card_v2", "chara_card_v3"):
        if not isinstance(data, dict):
            raise CardImportError("Card thiếu phần 'data' hoặc phần này không hợp lệ.")
        return data, "v3" if spec == "chara_card_v3" else "v2"
    if isinstance(data, dict) and ("name" in data or "first_mes" in data):
        return data, "v2"
    if any(k in obj for k in _V1_KEYS) or any(k in obj for k in _V1_ALIASES):
        v1: dict[str, Any] = {}
        for k in _V1_KEYS | {"creator_notes", "tags", "alternate_greetings"}:
            if k in obj:
                v1[k] = obj[k]
        for alias, key in _V1_ALIASES.items():
            if alias in obj and _is_empty(v1.get(key)):
                v1[key] = obj[alias]
        return v1, "v1"
    raise CardImportError(
        "Không nhận ra định dạng card. Lyris hỗ trợ Character Card V1, V2, V3 dạng JSON hoặc PNG."
    )


def _parse_json_bytes(data: bytes) -> Any:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = data.decode("utf-16") if data[:2] in (b"\xff\xfe", b"\xfe\xff") else ""
        except UnicodeDecodeError:
            text = ""
        if not text:
            raise CardImportError("File không phải JSON hoặc PNG đọc được (lỗi mã hoá ký tự).") from None
    try:
        return json.loads(text)
    except RecursionError:
        raise CardImportError("File JSON lồng nhau quá sâu, không đọc được.") from None
    except json.JSONDecodeError as exc:
        raise CardImportError(
            f"File JSON không hợp lệ (dòng {exc.lineno}, cột {exc.colno})."
        ) from None


def _lyris_address(raw: Any, warn: _Warn) -> AddressTerms | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        warn.add("Phần xưng hô trong card bị sai định dạng nên đã bỏ qua.")
        return None
    self_term = raw.get("self_term")
    player_term = raw.get("player_term")
    if not isinstance(self_term, str) or not isinstance(player_term, str):
        warn.add("Phần xưng hô trong card bị sai định dạng nên đã bỏ qua.")
        return None
    nick_raw = raw.get("nicknames", [])
    nicknames: list[str] = []
    if isinstance(nick_raw, list):
        for n in nick_raw:
            if isinstance(n, str) and n.strip() and n.strip() not in nicknames:
                nicknames.append(n.strip())
            elif not isinstance(n, str):
                warn.add("Một số tên thân mật không phải văn bản nên đã bỏ qua.")
    elif nick_raw is not None:
        warn.add("Danh sách tên thân mật bị sai định dạng nên đã bỏ qua.")
    others = raw.get("others", "")
    if not isinstance(others, str):
        warn.add('Trường "xưng hô với người khác" có kiểu dữ liệu không hợp lệ nên đã bỏ qua.')
        others = ""
    return AddressTerms(
        self_term=self_term.strip(), player_term=player_term.strip(), nicknames=nicknames, others=others.strip()
    )


def _card_from_data(data: dict[str, Any], version: str, styles: list[str], warn: _Warn) -> CharacterCard:
    name = _get_str(data, "name", warn)
    description = _get_str(data, "description", warn)
    personality = _get_str(data, "personality", warn)
    scenario = _get_str(data, "scenario", warn)
    greeting = _get_str(data, "first_mes", warn)
    examples = _convert_examples(_get_str(data, "mes_example", warn))
    creator_notes = _get_str(data, "creator_notes", warn)
    alternate = _get_str_list(data, "alternate_greetings", warn, "các lời mở đầu khác")
    tags = _get_str_list(data, "tags", warn, "tag")

    # ---- extensions: tách phần lyris, giữ phần còn lại
    ext_raw = data.get("extensions")
    other_ext: dict[str, Any] = {}
    lyris: dict[str, Any] | None = None
    if isinstance(ext_raw, dict):
        own_key = LYRIS_EXT_KEY if LYRIS_EXT_KEY in ext_raw else next(
            (k for k in LEGACY_EXT_KEYS if k in ext_raw), LYRIS_EXT_KEY
        )
        for k, v in ext_raw.items():
            if k in LEGACY_EXT_KEYS and k != own_key:
                continue  # có cả khoá mới lẫn khoá cũ: dùng khoá mới
            if k == own_key:
                if isinstance(v, dict):
                    lyris = v
                else:
                    warn.add("Phần dữ liệu riêng của Lyris trong card bị sai định dạng nên đã bỏ qua.")
            else:
                other_ext[k] = v
    elif ext_raw is not None:
        warn.add('Trường "extensions" có kiểu dữ liệu không hợp lệ nên đã bỏ qua.')

    preserved: dict[str, Any] = {}
    if version != "v1":
        for k, v in data.items():
            if k in _MAPPED_KEYS or _is_empty(v):
                continue
            preserved[k] = v
            if k in _UNUSED_LABELS:
                warn.add(f"Phần {_UNUSED_LABELS[k]} chưa được dùng trong prompt; vẫn được giữ lại khi xuất card.")
        book = data.get("character_book")
        entries = book.get("entries") if isinstance(book, dict) else None
        if isinstance(entries, list) and entries:
            n = sum(1 for e in entries if isinstance(e, dict))
            if n:
                # Phase 4: book thành các mục thế giới khi lưu nhân vật (không còn là phần "chưa dùng").
                warn.add(f"Card có {n} mục thế giới; chúng được thêm vào phần “Thế giới” khi bạn lưu nhân vật.")
    if other_ext:
        preserved["extensions"] = other_ext

    extensions: dict[str, Any] = {}
    lyris = lyris or {}
    if "creator_uid" in lyris:
        # File do Lyris xuất: `creator` là @handle của account đã xuất, luôn được ghi lại từ account
        # đang giữ card khi xuất. Card nhập vào thuộc account nhập, nên không giữ tác giả cũ.
        preserved.pop("creator", None)
    lyris_card_ext = lyris.get("extensions")
    if isinstance(lyris_card_ext, dict):
        extensions.update({k: v for k, v in lyris_card_ext.items() if k != PRESERVED_KEY})
    # Card nhập vào là card của người dùng, không phải bản cài từ Khám Phá: bỏ dấu template.
    extensions = strip_template_marker(extensions)
    if preserved:
        extensions[PRESERVED_KEY] = preserved

    # ---- các trường riêng của Lyris
    extras: dict[str, str] = {}
    for k in _EXTRA_FIELDS:
        v = lyris.get(k)
        if v is None:
            extras[k] = ""
        elif isinstance(v, str):
            extras[k] = _norm_text(v)
        else:
            extras[k] = ""
            warn.add(f'Trường "{_EXTRA_LABELS["vi"][k].lower()}" có kiểu dữ liệu không hợp lệ nên đã bỏ qua.')
    if any(extras.values()):
        description, ok = _strip_extras(description, extras)
        if not ok:
            warn.add(
                "Mô tả có thể đã được sửa ở app khác nên còn lặp phần ngoại hình/hoàn cảnh/mục tiêu...; hãy kiểm tra."
            )

    texts = [description, personality, scenario, greeting, examples]

    language: Language
    lang_raw = lyris.get("language")
    if lang_raw in ("vi", "en"):
        language = lang_raw
    else:
        language = _guess_language(texts)
        lang_vi = "tiếng Việt" if language == "vi" else "tiếng Anh"
        warn.add(f"Card không ghi ngôn ngữ; đoán là {lang_vi} từ nội dung, hãy kiểm tra.")

    gender: Gender
    gender_raw = lyris.get("gender")
    if gender_raw in ("male", "female", "other"):
        gender = gender_raw
    else:
        gender = _guess_gender(texts, tags)
        if gender == "other":
            warn.add('Card không ghi giới tính và không đoán được từ mô tả; tạm để "khác", hãy chọn lại.')
        else:
            warn.add(f"Card không ghi giới tính; đoán là {_GENDER_VI[gender]} từ mô tả, hãy kiểm tra.")

    style_raw = lyris.get("style_profile")
    if isinstance(style_raw, str) and style_raw in styles:
        style_profile = style_raw
    else:
        style_profile = _default_style(styles)
        if isinstance(style_raw, str) and style_raw:
            warn.add(
                f'Style profile "{style_raw}" không có trong app; tạm chọn "{style_profile}", hãy chọn lại.'
            )
        else:
            warn.add(
                f'Card chưa có style profile; tạm chọn "{style_profile}", nên chọn lại cho hợp bối cảnh.'
            )

    role_raw = lyris.get("role")
    role = " ".join(role_raw.split()) if isinstance(role_raw, str) else ""
    if role_raw is not None and not isinstance(role_raw, str):
        warn.add('Trường "vai trò" có kiểu dữ liệu không hợp lệ nên đã bỏ qua.')

    address = _lyris_address(lyris.get("address_terms"), warn)
    if address is None:
        if language == "en":
            address = AddressTerms(self_term="I", player_term="you")
        else:
            address = AddressTerms(self_term="", player_term="")
            warn.add("Card chưa có xưng hô; hãy điền cách nhân vật tự xưng và gọi người chơi trước khi lưu.")

    if not name:
        warn.add("Card không có tên nhân vật; hãy đặt tên trước khi lưu.")
    elif len(name) > _MAX_NAME_CHARS:
        warn.add(f"Tên nhân vật dài hơn {_MAX_NAME_CHARS} ký tự; hãy rút gọn trước khi lưu.")
    if len(tags) > _MAX_TAGS:
        warn.add(f"Card có {len(tags)} tag; chỉ giữ {_MAX_TAGS} tag đầu.")
        tags = tags[:_MAX_TAGS]

    try:
        card = CharacterCard(
            id=None,
            name=name,
            role=role,
            gender=gender,
            language=language,
            description=description,
            personality=personality,
            appearance=extras["appearance"],
            background=extras["background"],
            goals=extras["goals"],
            secrets=extras["secrets"],
            speech_style=extras["speech_style"],
            style_profile=style_profile,
            address_terms=address,
            greeting=greeting,
            example_dialogues=examples,
            tags=tags,
            scenario=scenario,
            alternate_greetings=alternate,
            creator_notes=creator_notes,
            avatar=None,
            extensions=extensions,
        )
    except ValidationError:  # không xảy ra với dữ liệu đã kiểm ở trên; phòng hờ
        raise CardImportError("Dữ liệu card không hợp lệ, không tạo được nhân vật.") from None

    long_fields = [
        label
        for label, value in (
            ("mô tả", card.description),
            ("tính cách", card.personality),
            ("bối cảnh", card.scenario),
            ("lời mở đầu", card.greeting),
            ("ví dụ thoại", card.example_dialogues),
            ("ghi chú người tạo", card.creator_notes),
            *((f"ngoại hình/hoàn cảnh ({k})", extras[k]) for k in _EXTRA_FIELDS),
        )
        if len(value) > _MAX_TEXT_CHARS
    ]
    long_fields += ["lời mở đầu khác"] if any(len(g) > _MAX_TEXT_CHARS for g in alternate) else []
    if long_fields:
        warn.add(
            "Các trường dài hơn 20.000 ký tự cần rút gọn trước khi lưu: "
            + ", ".join(long_fields)
            + "."
        )
    return card



def strip_template_marker(extensions: dict[str, Any]) -> dict[str, Any]:
    """Bản sao `extensions` không có `lyris.template` (dấu "đã cài từ Khám Phá").

    Chỉ bản cài từ template mới mang dấu này; bản nhân bản hay card nhập lại thì không, kẻo Khám Phá
    trỏ template sang bản sao khi người dùng xoá bản gốc. Bỏ luôn `lyris` nếu không còn khoá nào.
    """
    out = dict(extensions)
    lyris = out.get("lyris")
    if isinstance(lyris, dict) and "template" in lyris:
        rest = {k: v for k, v in lyris.items() if k != "template"}
        if rest:
            out["lyris"] = rest
        else:
            del out["lyris"]
    return out

def import_card(data: bytes, content_type: str | None, *, styles: list[str]) -> ImportResult:
    """Đọc card V1/V2/V3 từ JSON hoặc PNG -> bản nháp chưa lưu + cảnh báo tiếng Việt."""
    if not isinstance(data, (bytes, bytearray)):
        raise CardImportError("Dữ liệu tải lên không hợp lệ.")
    data = bytes(data)
    if not data.strip():
        raise CardImportError("File rỗng.")
    if len(data) > MAX_CARD_BYTES:
        raise CardImportError("File quá lớn (tối đa 8MB).")

    ctype = (content_type or "").split(";")[0].strip().lower()
    image: bytes | None = None
    if data.startswith(PNG_SIGNATURE):
        obj = _read_png_card(data)
        image = data
    elif (
        data.startswith(b"\xff\xd8\xff")
        or (data[:4] == b"RIFF" and data[8:12] == b"WEBP")
        or data[:6] in (b"GIF87a", b"GIF89a")
        or (ctype.startswith("image/") and ctype != "image/png")
    ):
        raise CardImportError("Chỉ hỗ trợ card dạng PNG hoặc JSON; ảnh JPEG/WebP/GIF không chứa dữ liệu card.")
    elif ctype == "image/png":
        raise CardImportError("File không phải ảnh PNG hợp lệ.")
    else:
        obj = _parse_json_bytes(data)

    card_data, version = _detect(obj)
    warn = _Warn()
    card = _card_from_data(card_data, version, list(styles), warn)
    return ImportResult(card=card, warnings=warn.items, image=image)


# --------------------------------------------------------------------------- export


@dataclass(frozen=True)
class CardCreator:
    """Tác giả ghi vào file export: account tạo card (Phase 2c, docs/accounts.md §2)."""

    handle: str
    uid: str


def _lyris_extension(card: CharacterCard, creator: CardCreator | None = None) -> dict[str, Any]:
    lyris: dict[str, Any] = {
        "version": LYRIS_EXT_VERSION,
        "role": card.role,
        "gender": card.gender,
        "language": card.language,
        "appearance": card.appearance,
        "background": card.background,
        "goals": card.goals,
        "secrets": card.secrets,
        "speech_style": card.speech_style,
        "style_profile": card.style_profile,
        "address_terms": card.address_terms.model_dump(),
    }
    if creator is not None:
        lyris["creator_uid"] = creator.uid
    own_ext = {k: v for k, v in card.extensions.items() if k != PRESERVED_KEY}
    if own_ext:
        lyris["extensions"] = own_ext
    return lyris


def export_card_json(
    card: CharacterCard, creator: CardCreator | None = None, lore: Sequence[LoreEntry] | None = None
) -> dict[str, Any]:
    """CharacterCard -> Character Card V2 (`{"spec": "chara_card_v2", "spec_version": "2.0", "data": {...}}`).

    `creator` (account tạo card): `data.creator = "@handle"` và `data.extensions.lyris.creator_uid`.
    Khi import, hai trường này không quyết định chủ sở hữu: card nhập vào thuộc account nhập.
    `lore` (Phase 4): các mục thế giới của card (chưa xoá); có ít nhất một mục thì `character_book` được dựng
    từ chúng (kèm `extensions.lyris.{known_by, category, slug}`), thay cho book cũ còn giữ lại (nếu có).
    """
    preserved_raw = card.extensions.get(PRESERVED_KEY)
    preserved: dict[str, Any] = preserved_raw if isinstance(preserved_raw, dict) else {}

    description = card.description.strip()
    block = _extras_block(
        {k: getattr(card, k) for k in _EXTRA_FIELDS}, card.language
    )
    if block:
        description = f"{description}\n\n{block}" if description else block

    data: dict[str, Any] = {
        "name": card.name,
        "description": description,
        "personality": card.personality,
        "scenario": card.scenario,
        "first_mes": card.greeting,
        "mes_example": _examples_to_v2(card.example_dialogues),
        "creator_notes": card.creator_notes,
        "system_prompt": "",
        "post_history_instructions": "",
        "alternate_greetings": list(card.alternate_greetings),
        "tags": list(card.tags),
        "creator": "",
        "character_version": "",
    }
    # Phần giữ lại từ lúc import trả về đúng chỗ cũ (kể cả character_book, khoá V3...).
    for k, v in preserved.items():
        if k in _MAPPED_KEYS:
            continue
        data[k] = v
    other_ext = preserved.get("extensions")
    extensions: dict[str, Any] = dict(other_ext) if isinstance(other_ext, dict) else {}
    if creator is not None:
        # Tác giả là account đang giữ card, không phải tác giả cũ còn giữ lại từ lúc import.
        data["creator"] = f"@{creator.handle}"
    extensions[LYRIS_EXT_KEY] = _lyris_extension(card, creator)
    data["extensions"] = extensions
    book = entries_to_book(card.name, lore) if lore else None
    if book is not None:
        data["character_book"] = book
    return {"spec": "chara_card_v2", "spec_version": "2.0", "data": data}


_FONT_CANDIDATES = (
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
)


def _initial(name: str) -> str:
    for ch in name.strip():
        if ch.isalnum():
            return ch.upper()
    return "?"


def _ascii_initial(letter: str) -> str:
    if letter in ("Đ", "đ"):
        return "D"
    base = unicodedata.normalize("NFD", letter)[0]
    return base.upper() if base.isascii() and base.isalnum() else "?"


def _placeholder_png(name: str) -> bytes:
    """Ảnh 512x512 nền tối với chữ cái đầu của tên."""
    from PIL import Image, ImageDraw, ImageFont

    digest = hashlib.sha1(name.encode("utf-8")).digest()
    hue = digest[0] / 255
    r, g, b = colorsys.hsv_to_rgb(hue, 0.45, 0.22)
    bg = (int(r * 255), int(g * 255), int(b * 255))
    img = Image.new("RGB", (512, 512), bg)
    draw = ImageDraw.Draw(img)

    letter = _initial(name)
    font: Any = None
    for path in _FONT_CANDIDATES:
        if Path(path).is_file():
            try:
                font = ImageFont.truetype(path, 280)
                break
            except OSError:
                continue
    if font is None:
        letter = _ascii_initial(letter)
        try:
            font = ImageFont.load_default(size=280)
        except TypeError:  # Pillow cũ không nhận size
            font = ImageFont.load_default()
    left, top, right, bottom = draw.textbbox((0, 0), letter, font=font)
    x = (512 - (right - left)) / 2 - left
    y = (512 - (bottom - top)) / 2 - top
    draw.text((x, y), letter, fill=(236, 233, 228), font=font)
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def _reencode_png(image: bytes) -> bytes | None:
    """Ảnh không phải PNG đọc được -> chuyển sang PNG bằng Pillow; hỏng -> None."""
    from PIL import Image, UnidentifiedImageError

    try:
        with Image.open(io.BytesIO(image)) as img:
            img.load()
            if img.mode not in ("RGB", "RGBA", "L", "LA", "P"):
                img = img.convert("RGBA")
            out = io.BytesIO()
            img.save(out, format="PNG")
            return out.getvalue()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        return None


def export_card_png(
    card: CharacterCard,
    image_png: bytes | None,
    creator: CardCreator | None = None,
    lore: Sequence[LoreEntry] | None = None,
) -> bytes:
    """Ảnh PNG có nhúng chunk tEXt 'chara' (base64 của JSON V2). Không có ảnh -> ảnh chữ cái đầu."""
    base: bytes | None = None
    chunks: list[tuple[bytes, bytes]] | None = None
    if image_png:
        if image_png.startswith(PNG_SIGNATURE):
            try:
                chunks = _png_chunks(image_png)
            except CardImportError:
                chunks = None
            if chunks is not None and not any(c == b"IEND" for c, _ in chunks):
                chunks = None
        if chunks is None:
            base = _reencode_png(image_png)
    if chunks is None:
        if base is None:
            base = _placeholder_png(card.name)
        chunks = _png_chunks(base)

    payload_json = json.dumps(export_card_json(card, creator, lore), ensure_ascii=False, separators=(",", ":"))
    encoded = base64.b64encode(payload_json.encode("utf-8"))
    text_chunk = _make_chunk(b"tEXt", b"chara\x00" + encoded)

    out = bytearray(PNG_SIGNATURE)
    for ctype, payload in chunks:
        if ctype == b"IEND" or _is_card_text_chunk(ctype, payload):
            continue
        out += _make_chunk(ctype, payload)
    out += text_chunk
    out += _make_chunk(b"IEND", b"")
    return bytes(out)
