"""Tách dòng `[Thought: ...]` khỏi câu trả lời của model, cả khi stream lẫn khi đã có đủ văn bản.

Quy ước (xem docs/phase1.md, mục llm/thought.py):
- Thẻ mở `[Thought:` không phân biệt hoa thường, cho phép khoảng trắng/tab (`[ thought :`).
  Thought kết thúc ở `]` đầu tiên; nếu chưa gặp `]` thì kết thúc ở chỗ ngắt đoạn đầu tiên
  (`\n`, có thể xen space/tab, rồi `\n` — một dòng trống) hoặc ở hết văn bản. Một `\n` đơn
  bên trong Thought không kết thúc nó. Phần sau chỗ ngắt đoạn lại là chữ hiển thị.
- Thought kết thúc không có `]` (ngắt đoạn / hết văn bản): bỏ một dấu ngoặc kép lẻ ở cuối
  (`"` lẻ số lần, `”` nhiều hơn `“`, hoặc `“`) cùng khoảng trắng quanh nó.
- Nhiều Thought: mỗi cái bỏ khoảng trắng hai đầu, bỏ cái rỗng, nối bằng `\\n`.
- Phần hiển thị: bỏ khoảng trắng đầu/cuối, gộp từ 3 dấu xuống dòng liền nhau trở lên
  (có thể xen dòng chỉ có khoảng trắng) thành đúng một dòng trống (`\\n\\n`).

`ThoughtStreamParser` cho ra đúng kết quả của `split_thought` dù văn bản bị cắt ở bất kỳ đâu:
ghép mọi delta `text` bằng `visible`, ghép mọi delta `thought` bằng `thought` (hoặc "" nếu None).
"""
from __future__ import annotations

import re

from lyris.llm.base import ParsedDelta

# Thẻ mở đầy đủ.
_OPEN = re.compile(r"\[[ \t]*thought[ \t]*:", re.IGNORECASE)
# Toàn bộ một Thought trong văn bản đầy đủ: đến `]` đầu tiên, chỗ ngắt đoạn đầu tiên (không ăn
# chỗ ngắt đoạn, nó thuộc phần hiển thị) hoặc hết văn bản. Nhóm 2 là `]` nếu Thought đã đóng.
_FULL = re.compile(
    r"\[[ \t]*thought[ \t]*:(.*?)(\]|(?=\n[ \t]*\n)|\Z)", re.IGNORECASE | re.DOTALL
)
# Chỗ ngắt đoạn (dòng trống) và phần đuôi có thể đang là đầu của một chỗ ngắt đoạn.
_PARA_BREAK = re.compile(r"\n[ \t]*\n")
_PARA_BREAK_PREFIX = re.compile(r"\n[ \t]*\Z")
_QUOTES = frozenset('"“”')
# Chuỗi bắt đầu bằng `[` mà vẫn còn có thể trở thành thẻ mở nếu có thêm chữ.
_PREFIX = re.compile(
    r"\[[ \t]*(?:t(?:h(?:o(?:u(?:g(?:h(?:t[ \t]*)?)?)?)?)?)?)?",
    re.IGNORECASE,
)
# Từ 3 dấu xuống dòng trở lên (giữa chúng chỉ có space/tab) -> một dòng trống.
_BLANK_LINES = re.compile(r"\n(?:[ \t]*\n){2,}")
# Tách văn bản thành các đoạn khoảng trắng / không khoảng trắng (cùng định nghĩa với str.strip()).
_WS_SPLIT = re.compile(r"(\s+)")
# Như trên, thêm mỗi dấu ngoặc kép là một mẩu riêng (để giữ lại dấu ngoặc kép lẻ cuối Thought).
_THOUGHT_SPLIT = re.compile(r"(\s+|[\"“”])")


def _collapse_blank_lines(text: str) -> str:
    return _BLANK_LINES.sub("\n\n", text)


def _is_unmatched_quote(content: str) -> bool:
    """Ký tự cuối của `content` (một dấu ngoặc kép) có lẻ không, tính trên cả `content`."""
    last = content[-1]
    if last == '"':
        return content.count('"') % 2 == 1
    if last == "”":
        return content.count("”") > content.count("“")
    return last == "“"


def _strip_unclosed(content: str) -> str:
    """Nội dung Thought không có `]`: bỏ một dấu ngoặc kép lẻ ở cuối và khoảng trắng quanh nó."""
    content = content.strip()
    if content and content[-1] in _QUOTES and _is_unmatched_quote(content):
        content = content[:-1].rstrip()
    return content


def split_thought(raw: str) -> tuple[str, str | None]:
    """Tách văn bản thô thành (phần hiển thị, thought). Thought là None nếu không có nội dung."""
    visible_parts: list[str] = []
    thoughts: list[str] = []
    pos = 0
    for match in _FULL.finditer(raw):
        visible_parts.append(raw[pos : match.start()])
        content = match.group(1).strip() if match.group(2) else _strip_unclosed(match.group(1))
        if content:
            thoughts.append(content)
        pos = match.end()
    visible_parts.append(raw[pos:])
    visible = _collapse_blank_lines("".join(visible_parts).strip())
    return visible, ("\n".join(thoughts) if thoughts else None)


class ThoughtStreamParser:
    """Bộ tách Thought theo kiểu stream (máy trạng thái tăng dần).

    `feed()` nhận từng mẩu văn bản thô, trả các `ParsedDelta` đã chắc chắn; `flush()` gọi một lần
    khi hết stream để nhả phần còn giữ lại. Parser giữ lại:
    - phần đuôi có thể là tiền tố của thẻ mở (ví dụ `[Th`), nhả ra ngay khi chắc chắn không phải thẻ;
    - trong Thought: phần đuôi `\n` + space/tab (có thể là đầu chỗ ngắt đoạn) và dấu ngoặc kép lẻ
      (bị bỏ nếu Thought kết thúc ngay sau nó mà không có `]`);
    - khoảng trắng đang chờ (chưa biết nó nằm giữa hay ở cuối văn bản).
    Sau `flush()` parser trở về trạng thái ban đầu và có thể dùng lại.
    """

    def __init__(self) -> None:
        self._reset()

    def _reset(self) -> None:
        self._buf = ""  # văn bản thô chưa xử lý (chỉ khác rỗng khi đang giữ tiền tố thẻ)
        self._in_thought = False
        # phần hiển thị
        self._text_started = False
        self._text_ws = ""
        # phần thought
        self._thought_started = False  # Thought hiện tại đã có chữ chưa
        self._thought_ws = ""
        self._any_thought = False  # đã phát ra chữ của một Thought nào trước đó chưa
        self._held_quote = ""  # dấu ngoặc kép lẻ đang giữ (có thể là ký tự cuối của Thought)
        self._held_ws = ""  # khoảng trắng sau dấu ngoặc kép đang giữ
        self._quote_counts = {q: 0 for q in _QUOTES}  # số dấu ngoặc kép trong Thought hiện tại
        self._out: list[ParsedDelta] = []

    # ---- phát delta -------------------------------------------------------------------------

    def _push(self, kind: str, text: str) -> None:
        if not text:
            return
        if self._out and self._out[-1].kind == kind:
            self._out[-1] = ParsedDelta(kind=kind, text=self._out[-1].text + text)  # type: ignore[arg-type]
        else:
            self._out.append(ParsedDelta(kind=kind, text=text))  # type: ignore[arg-type]

    def _emit_text(self, text: str) -> None:
        for piece in _WS_SPLIT.split(text):
            if not piece:
                continue
            if piece.isspace():
                if self._text_started:
                    self._text_ws += piece
                continue
            if self._text_ws:
                self._push("text", _collapse_blank_lines(self._text_ws))
                self._text_ws = ""
            self._text_started = True
            self._push("text", piece)

    def _emit_thought_piece(self, piece: str) -> None:
        """Phát một mẩu không phải khoảng trắng của Thought, kèm khoảng trắng đang chờ trước nó."""
        if not self._thought_started:
            if self._any_thought:
                self._push("thought", "\n")
            self._thought_started = True
            self._any_thought = True
        elif self._thought_ws:
            self._push("thought", self._thought_ws)
        self._thought_ws = ""
        self._push("thought", piece)

    def _release_quote(self) -> None:
        """Dấu ngoặc kép đang giữ hoá ra không phải ký tự cuối: phát nó ra."""
        if self._held_quote:
            self._emit_thought_piece(self._held_quote)
            self._thought_ws = self._held_ws
            self._held_quote = ""
            self._held_ws = ""

    def _emit_thought(self, text: str) -> None:
        for piece in _THOUGHT_SPLIT.split(text):
            if not piece:
                continue
            if piece.isspace():
                if self._held_quote:
                    self._held_ws += piece
                elif self._thought_started:
                    self._thought_ws += piece
                continue
            self._release_quote()
            if piece in _QUOTES:
                counts = self._quote_counts
                counts[piece] += 1
                if (
                    (piece == '"' and counts['"'] % 2 == 1)
                    or (piece == "”" and counts["”"] > counts["“"])
                    or piece == "“"
                ):
                    # Nếu Thought hết ở đây mà không có `]` thì dấu này bị bỏ: giữ lại chờ xem.
                    self._held_quote = piece
                    continue
            self._emit_thought_piece(piece)

    def _open_thought(self) -> None:
        self._in_thought = True
        self._thought_started = False
        self._thought_ws = ""
        self._held_quote = ""
        self._held_ws = ""
        self._quote_counts = {q: 0 for q in _QUOTES}

    def _close_thought(self, closed: bool) -> None:
        """Kết thúc Thought; `closed` là có `]` (giữ dấu ngoặc kép cuối) hay không (bỏ nó)."""
        if closed:
            self._release_quote()
        self._in_thought = False
        self._thought_started = False
        self._thought_ws = ""
        self._held_quote = ""
        self._held_ws = ""

    # ---- xử lý buffer -----------------------------------------------------------------------

    def _process(self) -> None:
        buf = self._buf
        while buf:
            if self._in_thought:
                end = buf.find("]")
                brk = _PARA_BREAK.search(buf, 0, end if end >= 0 else len(buf))
                if brk:
                    # Thought chưa đóng hết ở chỗ ngắt đoạn; chỗ ngắt đoạn thuộc phần hiển thị.
                    self._emit_thought(buf[: brk.start()])
                    self._close_thought(closed=False)
                    buf = buf[brk.start() :]
                elif end >= 0:
                    self._emit_thought(buf[:end])
                    self._close_thought(closed=True)
                    buf = buf[end + 1 :]
                else:
                    # Giữ phần đuôi `\n` + space/tab: có thể là đầu một chỗ ngắt đoạn.
                    tail = _PARA_BREAK_PREFIX.search(buf)
                    cut = tail.start() if tail else len(buf)
                    self._emit_thought(buf[:cut])
                    buf = buf[cut:]
                    if buf:
                        break
                continue

            start = buf.find("[")
            if start < 0:
                self._emit_text(buf)
                buf = ""
                continue
            self._emit_text(buf[:start])
            buf = buf[start:]
            tag = _OPEN.match(buf)
            if tag:
                self._open_thought()
                buf = buf[tag.end() :]
            elif _PREFIX.fullmatch(buf):
                break  # có thể là tiền tố của thẻ: chờ thêm chữ
            else:
                self._emit_text("[")  # chắc chắn không phải thẻ: nhả `[` ngay
                buf = buf[1:]
        self._buf = buf

    def _take(self) -> list[ParsedDelta]:
        out, self._out = self._out, []
        return out

    # ---- API --------------------------------------------------------------------------------

    def feed(self, delta: str) -> list[ParsedDelta]:
        """Nhận thêm văn bản thô; trả các delta đã chắc chắn (có thể rỗng)."""
        if delta:
            self._buf += delta
            self._process()
        return self._take()

    def flush(self) -> list[ParsedDelta]:
        """Hết stream: nhả phần đang giữ (tiền tố thẻ chưa hoàn chỉnh là chữ thường), bỏ khoảng trắng cuối."""
        if self._buf:
            # Buffer còn lại: tiền tố thẻ chưa hoàn chỉnh (văn bản) hoặc khoảng trắng cuối (Thought).
            leftover, self._buf = self._buf, ""
            if self._in_thought:
                self._emit_thought(leftover)
            else:
                self._emit_text(leftover)
        if self._in_thought:
            self._close_thought(closed=False)  # hết văn bản mà chưa có `]`: bỏ dấu ngoặc kép lẻ cuối
        out = self._take()
        self._reset()
        return out
