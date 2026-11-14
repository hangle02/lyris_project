"""Dạng so khớp cho sổ thế giới (docs/phase4.md §5.1). Hàm thuần.

`match_form` dùng chung cho từ khoá và văn bản cần quét:
1. NFC, casefold, NFC lại.
2. Chuẩn hoá vị trí dấu thanh (`canon_tone`): "hoà" = "hòa", "thuý" = "thúy"; "quý" giữ nguyên.
3. Tách token bằng `[^\\W_]+`: dấu câu, gạch nối, gạch dưới, ngoặc kép, "·" coi như khoảng trắng.
4. `" " + " ".join(tokens) + " "`, để khớp trọn âm tiết bằng phép `in`.

KHÔNG bỏ dấu ở bước nào: "Lục" khác "lúc", "Đ" khác "D".
"""
from __future__ import annotations

import re
import unicodedata

# Dấu thanh tiếng Việt (dạng tổ hợp sau NFD): huyền, sắc, hỏi, ngã, nặng.
_TONE_MARKS = ("̀", "́", "̉", "̃", "̣")
_WORD = re.compile(r"[^\W_]+")  # chữ/số; "_" (in nghiêng markdown, "Hạ_Trì") là dấu câu
_CJK = re.compile(r"[㐀-䶿一-鿿豈-﫿\U00020000-\U0002ffff]")
_UPPER_OR_DIGIT = re.compile(r"[^\W_]")


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def _split_tone(ch: str) -> tuple[str, str | None]:
    """Một ký tự -> (ký tự không dấu thanh nhưng giữ mũ/móc, dấu thanh hoặc None)."""
    decomposed = unicodedata.normalize("NFD", ch)
    tone = next((m for m in _TONE_MARKS if m in decomposed), None)
    if tone is None:
        return ch, None
    base = nfc("".join(c for c in decomposed if c not in _TONE_MARKS))
    return base, tone


def canon_tone(word: str) -> str:
    """Âm tiết kết thúc bằng `oa`, `oe`, `uy` (không đứng sau `q`, không có phụ âm cuối): dấu thanh về
    nguyên âm đầu theo kiểu cũ. `hoà`->`hòa`, `khoẻ`->`khỏe`, `thuý`->`thúy`, `luỹ`->`lũy`; `quý`, `hoàng`
    giữ nguyên. `word` đã NFC và chữ thường."""
    if len(word) < 2:
        return word
    parts = [_split_tone(c) for c in word]
    tones = [t for _, t in parts]
    if not any(tones):
        return word
    bases = "".join(b for b, _ in parts)
    for pair in ("oa", "oe", "uy"):
        if not bases.endswith(pair):
            continue
        if pair == "uy" and bases[:-2].endswith("q"):
            return word
        i = len(bases) - 2
        tone = tones[i] or tones[i + 1]
        if tone is None or tones[i] is not None:
            return word  # không có dấu trên cặp này, hoặc đã đúng chỗ
        out = [b for b, _ in parts]
        # Giữ dấu của các ký tự khác (vd. không có), chỉ dời dấu của cặp cuối.
        for j, (b, t) in enumerate(parts):
            if t is not None and j < i:
                out[j] = nfc(b + t)
        out[i] = nfc(bases[i] + tone)
        out[i + 1] = bases[i + 1]
        return "".join(out)
    return word


def tokens(text: str) -> list[str]:
    """Các token của `text` sau NFC + casefold + chuẩn hoá dấu thanh."""
    folded = nfc(nfc(text).casefold())
    return [canon_tone(w) for w in _WORD.findall(folded)]


def match_form(text: str) -> str:
    """`" tok1 tok2 ... "` (xem đầu file). Văn bản rỗng -> `" "`."""
    return " " + " ".join(tokens(text)) + " "


def cjk_form(text: str) -> str:
    """Dạng so chuỗi con cho khoá có chữ Hán: các token nối liền, không khoảng trắng hay dấu câu."""
    return "".join(tokens(text))


def has_cjk(text: str) -> bool:
    return _CJK.search(text) is not None


def cjk_count(text: str) -> int:
    return len(_CJK.findall(text))


def syllables(text: str) -> int:
    """Số âm tiết (token chữ/số) của `text`. Chữ Hán liền nhau tính là một token."""
    return len(_WORD.findall(text))


def is_name_like(key: str) -> bool:
    """Khoá dạng tên riêng, như tác giả viết: có ít nhất một chữ hoa, một chữ số hoặc một chữ Hán
    (`Hạ Trì`, `GHOST`, `phòng 402`, `夏驰`). Chỉ khoá loại này được quét trên lượt của nhân vật (§5.3)."""
    if has_cjk(key):
        return True
    return any(c.isupper() or c.isdigit() for c in key if _UPPER_OR_DIGIT.match(c))


def strip_parens(text: str) -> str:
    """Bỏ mọi phần trong ngoặc tròn và khoảng trắng thừa: `Lục Tri Hành (陆知行)` -> `Lục Tri Hành`."""
    return " ".join(re.sub(r"\([^)]*\)", " ", text).split())


def same_name(a: str, b: str) -> bool:
    """Hai tên giống nhau (so bằng `match_form`, bỏ phần trong ngoặc của cả hai bên)."""
    fa, fb = match_form(strip_parens(a)), match_form(strip_parens(b))
    return fa.strip() != "" and fa == fb


def ascii_fold(text: str) -> str:
    """Bỏ mọi dấu (kể cả `đ` -> `d`), chữ thường; chỉ dùng cho slug, KHÔNG dùng để so khớp."""
    t = nfc(text).casefold().replace("đ", "d")
    return "".join(c for c in unicodedata.normalize("NFD", t) if not unicodedata.combining(c))


__all__ = [
    "ascii_fold",
    "canon_tone",
    "cjk_count",
    "cjk_form",
    "has_cjk",
    "is_name_like",
    "match_form",
    "nfc",
    "same_name",
    "strip_parens",
    "syllables",
    "tokens",
]
