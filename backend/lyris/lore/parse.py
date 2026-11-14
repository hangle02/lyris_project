"""Đọc `world.md` thành các mục thế giới (docs/phase4.md §4). Hàm thuần, không đụng DB.

Ba phần cấp `##` được đọc (so tiêu đề bằng `match_form` theo tiền tố):
- "Mục lore": mỗi `### Tiêu đề` kèm các dòng `keys`, `known_by`, `content` (cả `- **keys:**` lẫn `- keys:`).
- "Nhân vật xung quanh": mỗi `### Tên (中文)` hoặc đoạn mở đầu bằng `**Tên (中文)**`.
- "Địa điểm": mỗi `### Tên` hoặc đoạn mở đầu bằng `**Tên.**`.

Người và nơi chốn được nhập với "mọi người biết", nên:
- bỏ các dòng "Bí mật..." và "Chức năng..." (nhân vật chính không biết bí mật của họ; chức năng là ghi chú tác giả);
- người/nơi có khoá trùng khoá của một mục chỉ người chơi biết thì nhập là "Chỉ bạn" (`player_only`);
- bỏ từng câu chứa một từ trong META_SPOILER_TERMS hoặc một khoá của mục chỉ người chơi biết.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

from lyris.lore.match import LoreMatcher, ignore_forms, usable_key
from lyris.lore.normalize import (
    ascii_fold,
    has_cjk,
    is_name_like,
    match_form,
    nfc,
    same_name,
    syllables,
)
from lyris.models import LoreCategory

META_SPOILER_TERMS: tuple[str, ...] = (
    "nguyên tác",
    "nguyên chủ",
    "cốt truyện gốc",
    "xuyên sách",
    "xuyên không",
    "kiếp trước",
    "trùng sinh",
    "nữ chính",
    "nam chính",
    "nữ phụ",
    "nam phụ",
)
MAX_DROPPED_LISTED = 50

# Ví dụ từ ghép cho câu cảnh báo khoá một chữ (không cần đủ).
COMPOUND_EXAMPLES: dict[str, str] = {
    "nhẫn": "kiên nhẫn",
    "lục": "lục tung",
    "mắt": "mắt xích",
    "hoa": "hoa mắt",
    "tâm": "quan tâm",
    "trì": "trì hoãn",
    "tình": "tình cờ",
    "đông": "đám đông",
    "kim": "kim chỉ",
    "đường": "con đường",
    "giang": "giang hồ",
    "thiên": "thiên nhiên",
    "dương": "đại dương",
}

_SECTIONS: tuple[tuple[str, LoreCategory], ...] = (
    ("Mục lore", "lore"),
    ("Nhân vật xung quanh", "character"),
    ("Địa điểm", "place"),
)
_SECTION_LABEL: dict[LoreCategory, str] = {"lore": "Mục lore", "character": "Nhân vật xung quanh", "place": "Địa điểm"}
_ATX = re.compile(r"^(#{1,6})[ \t]+(.*?)[ \t]*#*[ \t]*$")
_BOLD_HEAD = re.compile(r"^\*\*(.+?)\*\*(.*)$")
_FIELD = re.compile(r"^\s*[-*]\s+(?:\*\*)?(keys|known_by|content)\s*:?\s*(?:\*\*)?\s*:?\s*(.*)$", re.IGNORECASE)
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_PAREN = re.compile(r"\(([^)]*)\)")
_SPLIT_LIST = re.compile(r"[,，]")
_SPLIT_HEAD = re.compile(r",|，| và | ở | trên ")
_SENTENCE = re.compile(r"(?<=[.!?…])\s+")
_SECRET_PREFIXES = ("bí mật", "chức năng")
_USER_RE = re.compile(r"^\{\{\s*user\s*\}\}$", re.IGNORECASE)
_CHAR_RE = re.compile(r"^\{\{\s*char\s*\}\}$", re.IGNORECASE)


@dataclass
class ParsedEntry:
    slug: str
    title: str
    category: LoreCategory
    keys: list[str]
    known_by: list[str]
    content: str


@dataclass
class ParsedWorld:
    entries: list[ParsedEntry] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    player_only: list[str] = field(default_factory=list)
    dropped_sentences: list[str] = field(default_factory=list)
    skipped_duplicates: list[str] = field(default_factory=list)


@dataclass
class _Raw:
    category: LoreCategory
    head: str
    keys_raw: str | None = None
    known_by_raw: str | None = None
    content: list[str] = field(default_factory=list)
    body: list[str] = field(default_factory=list)
    dropped_secret: int = 0
    in_content: bool = False
    label_head: bool = False  # mở bằng dòng đậm dạng nhãn ("**Tên:** ..."): các nhãn đậm sau cũng là người/nơi mới
    # Đang bỏ phần sau một dòng "Bí mật"/"Chức năng": None | "item" (dòng nối + mục con thụt sâu hơn drop_indent)
    # | "block" (nhãn đứng riêng: bỏ cả danh sách theo sau) | "heading" (bỏ tới tiêu đề cấp <= drop_level).
    drop_mode: str | None = None
    drop_indent: int = 0
    drop_level: int = 0
    after_blank: bool = False


# ---------------------------------------------------------------------------- tiện ích


def slugify(title: str) -> str:
    """`match_form`, bỏ dấu (`đ`->`d`), giữ [a-z0-9] nối bằng `-`. Chữ Hán bị bỏ; rỗng thì `h` + 10 hex đầu
    của sha1(match_form(title)) để hai tiêu đề toàn chữ Hán không trùng slug rỗng."""
    form = match_form(title).strip()
    words = [re.sub(r"[^a-z0-9]", "", ascii_fold(w)) for w in form.split()]
    slug = "-".join(w for w in words if w)
    if slug:
        return slug[:80].rstrip("-")
    return "h" + hashlib.sha1(form.encode("utf-8")).hexdigest()[:10]


def section_kind(title: str) -> LoreCategory | None:
    form = match_form(title)
    for label, kind in _SECTIONS:
        if form.startswith(match_form(label)):
            return kind
    return None


def _unbold(line: str) -> str:
    return _BOLD.sub(r"\1", line)


def _dedupe_keys(keys: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for key in keys:
        k = " ".join(nfc(key).split())
        form = match_form(k)
        if not k or not form.strip() or form in seen:
            continue
        seen.add(form)
        out.append(k)
    return out


def _cap_runs(text: str) -> list[str]:
    """Các cụm >= 2 âm tiết viết hoa liền nhau (chỉ chữ cái, không số, không chữ Hán)."""
    runs: list[str] = []
    cur: list[str] = []

    def flush() -> None:
        if len(cur) >= 2:
            runs.append(" ".join(cur))
        cur.clear()

    for word in text.split():
        bare = word.strip(".,;:!?\"'“”()")
        if bare and bare[0].isupper() and bare.isalpha() and not has_cjk(bare):
            cur.append(bare)
            if bare != word:  # dấu câu dính liền: cụm kết thúc ở đây
                flush()
        else:
            flush()
    flush()
    return runs


def _keep_part(part: str) -> bool:
    """Phần của tiêu đề đáng làm khoá: có chữ hoa ngoài chữ đầu, hoặc >= 2 âm tiết và mở đầu bằng chữ hoa."""
    if not part:
        return False
    if any(c.isupper() for c in part[1:]):
        return True
    return syllables(part) >= 2 and part[0].isupper()


def heading_keys(head: str, category: LoreCategory) -> tuple[str, list[str]]:
    """(tiêu đề, khoá tự sinh) của một người / nơi chốn (§4.3). Không bao giờ sinh khoá một âm tiết."""
    head = " ".join(_unbold(nfc(head)).split()).strip().rstrip(".").strip()
    paren_parts: list[str] = []
    for inner in _PAREN.findall(head):
        paren_parts += [p.strip() for p in _SPLIT_LIST.split(inner) if p.strip()]
    base = " ".join(_PAREN.sub(" ", head).split())
    base = re.sub(r"\s+([,，])", r"\1", base).strip(" ,，")
    keys = [base, *paren_parts]
    parts = [p.strip() for p in _SPLIT_HEAD.split(base)]
    keys += [p for p in parts if _keep_part(p)]
    for part in parts:
        keys += _cap_runs(part)
    words = base.split()
    if category == "character" and len(words) == 3 and all(w[:1].isupper() for w in words):
        keys.append(" ".join(words[1:]))
    keys = [k for k in keys if has_cjk(k) and len(k) >= 2 or not has_cjk(k) and syllables(k) >= 2]
    return base, _dedupe_keys(keys)


def key_warnings(keys: list[str], char_name: str | None = None) -> list[str]:
    """Câu cảnh báo từng khoá (Studio + kết quả nhập): khoá một chữ, khoá là tên nhân vật."""
    out: list[str] = []
    for key in keys:
        k = key.strip()
        if not k:
            continue
        if char_name and same_name(k, char_name):
            out.append(f"Từ khoá “{k}” là tên nhân vật nên không dùng để gợi nhớ.")
            continue
        if has_cjk(k) or syllables(k) != 1:
            continue
        if is_name_like(k):
            continue  # tên riêng một chữ (London, GHOST, A3): người dùng tự chọn, không nhắc
        example = COMPOUND_EXAMPLES.get(match_form(k).strip())
        if example:
            out.append(f"Từ khoá “{k}” chỉ có một chữ, cũng khớp trong những từ như “{example}”.")
        else:
            out.append(f"Từ khoá “{k}” chỉ có một chữ nên sẽ gợi rất thường xuyên.")
    return out


def normalize_known_by(values: list[str], char_name: str | None) -> list[str]:
    """Giữ `*`, `{{user}}`; tên trùng tên nhân vật -> `{{char}}`; tên khác giữ nguyên chữ. Bỏ rỗng/trùng."""
    out: list[str] = []
    for raw in values:
        v = " ".join(nfc(raw).split())
        if not v:
            continue
        if v == "*":
            norm = "*"
        elif _USER_RE.match(v):
            norm = "{{user}}"
        elif _CHAR_RE.match(v) or (char_name and same_name(v, char_name)):
            norm = "{{char}}"
        else:
            norm = v
        if norm not in out:
            out.append(norm)
    return out


def _audience(known_by: list[str]) -> str:
    """Như select.audience_of nhưng trên known_by đã chuẩn hoá ({{char}} thay tên nhân vật)."""
    if "*" in known_by:
        return "everyone"
    if "{{char}}" in known_by:
        return "character"
    if "{{user}}" in known_by:
        return "player"
    return "others"


def _clean_block(lines: list[str]) -> str:
    out: list[str] = []
    for line in lines:
        line = line.rstrip()
        if not line.strip():
            if out and out[-1] != "":
                out.append("")
            continue
        out.append(line.strip())
    while out and out[-1] == "":
        out.pop()
    return "\n".join(out)


def _secret_bare(stripped: str) -> str:
    return nfc(_unbold(stripped).lstrip("#-*• \t").lstrip("*").strip()).casefold()


def _is_secret_line(stripped: str) -> bool:
    folded = _secret_bare(stripped)
    return any(folded.startswith(p) for p in _SECRET_PREFIXES)


def _secret_standalone(stripped: str) -> bool:
    """Dòng "Bí mật" chỉ là nhãn (nội dung nằm ở các dòng/mục con theo sau): "**Bí mật:**", "- Bí mật/động cơ:"."""
    bare = _secret_bare(stripped)
    if ":" in bare:
        return not bare.split(":", 1)[1].strip()
    return len(bare.split()) <= 4


def _is_label(bold: re.Match[str]) -> bool:
    """Dòng đậm dạng nhãn: "**Tính cách:** ..." hoặc "**Tính cách**: ..."."""
    return bold.group(1).rstrip().endswith(":") or bold.group(2).lstrip().startswith(":")


# ---------------------------------------------------------------------------- đọc file


def _scan(text: str) -> list[_Raw]:
    text = nfc(text.lstrip("﻿")).replace("\r\n", "\n").replace("\r", "\n")
    section: LoreCategory | None = None
    raws: list[_Raw] = []
    cur: _Raw | None = None
    for line in text.split("\n"):
        stripped = line.strip()
        atx = _ATX.match(line)
        if atx:
            level = len(atx.group(1))
            if level <= 2:
                section = section_kind(atx.group(2)) if level == 2 else None
                cur = None
                continue
            if section is None:
                continue
            if level == 3:
                cur = _Raw(category=section, head=atx.group(2))
                raws.append(cur)
                continue
            if section != "lore" and cur is not None:
                # Tiêu đề cấp 4+ trong một người / nơi chốn: "#### Bí mật" bỏ mọi thứ tới tiêu đề cùng cấp.
                if cur.drop_mode == "heading" and level > cur.drop_level:
                    continue
                cur.drop_mode = None
                cur.after_blank = False
                if _is_secret_line(atx.group(2)):
                    cur.dropped_secret += 1
                    cur.drop_mode, cur.drop_level = "heading", level
                    continue
                cur.body.append(_unbold(line))
                continue
        if section is None:
            continue
        if section != "lore":
            if not stripped:
                if cur is not None:
                    cur.after_blank = True
                    cur.body.append("")
                continue
            if cur is not None and cur.drop_mode == "heading":
                continue
            indent = len(line) - len(line.lstrip())
            is_bullet = stripped[:1] in "-*•" and not stripped.startswith("**")
            bold = _BOLD_HEAD.match(line)
            # "Bí mật"/"Chức năng" xét TRƯỚC dòng đậm, để "**Bí mật:** ..." không thành một mục mọi người biết.
            if _is_secret_line(stripped):
                if cur is not None:
                    cur.dropped_secret += 1
                    standalone = _secret_standalone(stripped)
                    if standalone and not is_bullet and indent == 0:
                        cur.drop_mode = "block"
                    else:
                        cur.drop_mode, cur.drop_indent = "item", indent
                    cur.after_blank = False
                continue
            if cur is not None and cur.drop_mode == "item":
                if indent > cur.drop_indent or (not is_bullet and not bold and not cur.after_blank):
                    continue  # dòng nối tiếp / mục con của dòng "Bí mật"
                cur.drop_mode = None
            elif cur is not None and cur.drop_mode == "block":
                if not bold and (is_bullet or indent > 0 or not cur.after_blank):
                    continue  # danh sách dưới nhãn "Bí mật:" đứng riêng
                cur.drop_mode = None
            if bold:
                label = _is_label(bold)
                # Trong một mục đã mở, nhãn đậm ("**Tính cách:** ...") là nội dung, không phải người/nơi mới,
                # trừ khi chính các mục được viết theo kiểu "**Tên:** mô tả".
                if cur is None or not label or cur.label_head:
                    head = bold.group(1).rstrip().rstrip(":") if label else bold.group(1)
                    cur = _Raw(category=section, head=head, label_head=label)
                    rest = bold.group(2).strip().lstrip(".,;:").strip()
                    if rest:
                        cur.body.append(rest)
                    raws.append(cur)
                    continue
            if cur is None:
                continue
            cur.after_blank = False
            cur.body.append(_unbold(line))
            continue
        if cur is None:
            continue
        if section == "lore":
            fld = _FIELD.match(line)
            if fld:
                name, value = fld.group(1).lower(), fld.group(2).strip()
                if name == "keys":
                    cur.keys_raw = value
                    cur.in_content = False
                elif name == "known_by":
                    cur.known_by_raw = value
                    cur.in_content = False
                else:
                    cur.content = [value] if value else []
                    cur.in_content = True
                continue
            if cur.in_content:
                cur.content.append(_unbold(line))
            continue
    return raws


def _drop_sentences(content: str, matcher: LoreMatcher, title: str, dropped: list[str]) -> str:
    out: list[str] = []
    for line in content.split("\n"):
        if not line.strip():
            out.append(line)
            continue
        bullet = line.startswith("- ")
        sentences = [s for s in _SENTENCE.split(line) if s.strip()]
        kept: list[str] = []
        for s in sentences:
            if matcher.scan(s):
                dropped.append(f"{title}: {s.strip().lstrip('- ').strip()}")
            else:
                kept.append(s.strip())
        if not kept:
            continue
        joined = " ".join(kept)
        if bullet and not joined.startswith("- "):
            joined = "- " + joined
        out.append(joined)
    return _clean_block(out)


def parse_world_md(text: str, char_name: str | None = None) -> ParsedWorld:
    """Các mục thế giới của một file `world.md`. `char_name`: tên nhân vật của card (để lưu `{{char}}` và
    viết câu thông báo); None = không đổi tên nào."""
    char = (char_name or "").strip() or None
    who = char or "Nhân vật"
    result = ParsedWorld()
    raws = _scan(text)

    lore_titles = {match_form(_strip_parens_title(r.head)) for r in raws if r.category == "lore"}
    entries: list[tuple[_Raw, ParsedEntry]] = []
    seen_warn: set[str] = set()

    def warn(msg: str) -> None:
        if msg not in seen_warn:
            seen_warn.add(msg)
            result.warnings.append(msg)

    for raw in raws:
        if raw.category == "lore":
            title = " ".join(_unbold(nfc(raw.head)).split())
            keys = _dedupe_keys([k for k in _SPLIT_LIST.split(raw.keys_raw or "")])
            if raw.known_by_raw is None:
                known_by = ["*"]
                warn(f"Mục “{title}” chưa ghi ai biết, nên được coi là mọi người đều biết.")
            else:
                known_by = normalize_known_by(_SPLIT_LIST.split(raw.known_by_raw), char) or ["*"]
            others = [v for v in known_by if v not in ("*", "{{user}}", "{{char}}")]
            if others and _audience(known_by) in ("others", "player") and char:
                warn(f"Mục “{title}” chỉ {', '.join(others)} biết, nên {char} sẽ không dùng mục này.")
            content = _clean_block(raw.content)
        else:
            title, keys = heading_keys(raw.head, raw.category)
            if match_form(title) in lore_titles:
                result.skipped_duplicates.append(title)
                result.notes.append(
                    f"Bỏ qua “{title}” trong phần {_SECTION_LABEL[raw.category]} vì đã có mục cùng tên."
                )
                continue
            known_by = ["*"]
            content = _clean_block(raw.body)
        if not title:
            continue
        entries.append((raw, ParsedEntry(slug="", title=title, category=raw.category, keys=keys, known_by=known_by, content=content)))

    # ---- Lọc lộ điều chỉ người chơi biết (§4.3)
    skip = ignore_forms([char] if char else [])
    user_keys = [
        k
        for _, e in entries
        if e.category == "lore" and _audience(e.known_by) == "player"
        for k in e.keys
        if usable_key(k, skip)
    ]
    user_forms = {match_form(k) for k in user_keys}
    matcher = LoreMatcher([(0, [*META_SPOILER_TERMS, *user_keys])], ignore=[char] if char else [])
    dropped: list[str] = []
    secret_people = 0
    for raw, entry in entries:
        if entry.category == "lore":
            continue
        if raw.dropped_secret and entry.category == "character":
            secret_people += 1
        if user_forms and any(match_form(k) in user_forms for k in entry.keys):
            entry.known_by = ["{{user}}"]
            result.player_only.append(entry.title)
            continue
        entry.content = _drop_sentences(entry.content, matcher, entry.title, dropped)

    if secret_people:
        result.notes.insert(
            0,
            f"Không nhập phần Bí mật và Chức năng của {secret_people} nhân vật xung quanh, "
            f"vì {who} không biết những điều đó.",
        )
    if dropped:
        result.notes.append(f"Bỏ {len(dropped)} câu nhắc tới điều chỉ bạn biết.")
    if result.player_only:
        result.notes.append(
            f"{', '.join(result.player_only)}: chỉ bạn biết, vì thế giới có điều chỉ bạn biết về họ. "
            f"Nếu {who} cũng biết họ, đổi trong Studio."
        )
    result.dropped_sentences = dropped[:MAX_DROPPED_LISTED]

    # ---- Slug ổn định, cảnh báo
    counts: dict[str, int] = {}
    for _, entry in entries:
        base = f"md:{entry.category}/{slugify(entry.title)}"
        counts[base] = counts.get(base, 0) + 1
        entry.slug = base if counts[base] == 1 else f"{base}-{counts[base]}"
        if not entry.keys:
            warn(f"Mục “{entry.title}” chưa có từ khoá gợi nhớ nên sẽ không bao giờ được nhắc tới.")
        for msg in key_warnings(entry.keys, char):
            warn(msg)
        result.entries.append(entry)
    return result


def _strip_parens_title(head: str) -> str:
    return " ".join(_PAREN.sub(" ", _unbold(nfc(head))).split()).strip().rstrip(".").strip()


__all__ = [
    "META_SPOILER_TERMS",
    "ParsedEntry",
    "ParsedWorld",
    "heading_keys",
    "key_warnings",
    "normalize_known_by",
    "parse_world_md",
    "section_kind",
    "slugify",
]
