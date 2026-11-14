"""Tách chỉ đạo ẩn `((...))` khỏi lượt của người chơi.

Quét tuyến tính (không dùng regex lười quét lại phần đuôi), nên chuỗi dài nhiều "((" không đóng
vẫn xử lý trong thời gian O(n).

Không coi là mở chỉ đạo: "((" đứng ngay sau ký tự mặt cười (":((", ";((", "=((", "x((", "8((")
hoặc nằm trong một dãy "(" đứng sau ký tự đó (":(((").
"""
from __future__ import annotations

import re

_OPEN = "(("
_CLOSE = "))"
# Ký tự đứng ngay trước "((" khiến nó là mặt cười, không phải chỉ đạo.
_EMOTICON_BEFORE = frozenset(":;=xX8")

_INLINE_SPACES = re.compile(r"[ \t]{2,}")
_SPACE_AROUND_NEWLINE = re.compile(r"[ \t]*\n[ \t]*")
_MANY_BLANK_LINES = re.compile(r"\n{3,}")
# Không gồm ":" và ";" để không dính mặt cười (":))", ";)") vào chữ trước nó.
_SPACE_BEFORE_PUNCT = re.compile(r"[ \t]+([,.!?…])")
_WHITESPACE = re.compile(r"\s+")


def _clean_text(text: str) -> str:
    text = _INLINE_SPACES.sub(" ", text)
    text = _SPACE_AROUND_NEWLINE.sub("\n", text)
    text = _MANY_BLANK_LINES.sub("\n\n", text)
    text = _SPACE_BEFORE_PUNCT.sub(r"\1", text)
    return text.strip()


def _next_opener(text: str, pos: int) -> int:
    """Vị trí "((" mở chỉ đạo kế tiếp từ `pos`, hoặc -1. Bỏ qua "((" của mặt cười."""
    n = len(text)
    while True:
        i = text.find(_OPEN, pos)
        if i == -1:
            return -1
        run_start = i
        while run_start > pos and text[run_start - 1] == "(":
            run_start -= 1
        before = text[run_start - 1] if run_start > 0 else ""
        if before and before in _EMOTICON_BEFORE:
            # Bỏ qua cả dãy "(" của mặt cười.
            j = i
            while j < n and text[j] == "(":
                j += 1
            pos = j
            continue
        return i


def _scan(text: str, *, allow_unclosed: bool) -> tuple[list[str], list[str]]:
    """Trả (các mảnh văn bản còn lại, các chỉ đạo đã gộp khoảng trắng)."""
    kept: list[str] = []
    found: list[str] = []
    pos = 0
    while True:
        i = _next_opener(text, pos)
        if i == -1:
            kept.append(text[pos:])
            break
        j = text.find(_CLOSE, i + len(_OPEN))
        if j == -1:
            # "((" không được đóng: người chơi quên gõ "))", chỉ khi "((" đứng đầu dòng hoặc sau
            # khoảng trắng và theo sau là chữ; còn lại giữ nguyên như văn bản thường.
            rest = text[i + len(_OPEN) :]
            before = text[i - 1] if i > 0 else ""
            if allow_unclosed and (not before or before.isspace()) and rest.strip(" \t\n()"):
                kept.append(text[pos:i])
                inner = _WHITESPACE.sub(" ", rest).strip()
                if inner:
                    found.append(inner)
            else:
                kept.append(text[pos:])
            break
        kept.append(text[pos:i])
        kept.append(" ")
        inner = _WHITESPACE.sub(" ", text[i + len(_OPEN) : j]).strip()
        if inner:
            found.append(inner)
        pos = j + len(_CLOSE)
    return kept, found


def extract_directives(text: str) -> tuple[str, str | None]:
    """Trả `(văn bản đã bỏ chỉ đạo và dọn khoảng trắng, các chỉ đạo nối bằng "; " hoặc None)`.

    Chỉ đạo rỗng (`(( ))`) bị bỏ. Khoảng trắng trong mỗi chỉ đạo được gộp thành một dấu cách.
    """
    kept, found = _scan(text, allow_unclosed=True)
    return _clean_text("".join(kept)), ("; ".join(found) if found else None)


def remove_directives(text: str) -> str:
    """Bỏ các cặp `((...))` đã đóng (dùng cho câu trả lời của model). Không có cặp nào thì trả nguyên văn."""
    kept, _ = _scan(text, allow_unclosed=False)
    if len(kept) == 1:
        return text
    return _clean_text("".join(kept))
