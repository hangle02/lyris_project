"""Chống lặp giữa các lượt: lấy những câu model đã dùng gần đây để ghi chú cuối lượt (khối F) dặn tránh.

Model nhỏ hay rơi vào khuôn: trong DM, tin nào cũng kết bằng cùng một lời dặn ("ngủ sớm đi", "nghỉ ngơi
đi"); trong Story, lượt nào cũng mở đầu bằng "<Tên> khẽ ...". Lượt trước nằm trong lịch sử nên khuôn tự
củng cố. Ghi chú cuối lượt nêu đích danh các câu đó để model đổi cách viết.
"""
from __future__ import annotations

import re
from collections.abc import Sequence

from lyris.models import Message, Mode

RECENT_REPLIES = 3
MAX_DM_CHARS = 90
STORY_OPENING_WORDS = 9

_SENTENCE_END = re.compile(r"(?<=[.!?…])\s+")


def _clip_words(text: str, words: int) -> str:
    parts = text.split()
    if len(parts) <= words:
        return text.strip()
    return " ".join(parts[:words]) + "…"


def _dm_phrase(content: str) -> str | None:
    lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
    if not lines:
        return None
    last = lines[-1]
    if len(last) > MAX_DM_CHARS:
        last = last[:MAX_DM_CHARS].rsplit(" ", 1)[0] + "…"
    return last


def _story_opening(content: str) -> str | None:
    text = content.strip()  # visible_content: đã bỏ Thought
    if not text:
        return None
    first = _SENTENCE_END.split(text, maxsplit=1)[0]
    return _clip_words(first, STORY_OPENING_WORDS)


def recent_phrases(history: Sequence[Message], mode: Mode) -> list[str]:
    """Các câu cần tránh lặp cho lượt sắp viết ở `mode`.

    DM: dòng cuối của tối đa 3 tin DM gần nhất của nhân vật. Story: câu mở đầu (cắt ngắn) của tối đa
    3 lượt Story gần nhất. Bỏ greeting (lượt 0) vì đó là văn của tác giả card, không phải khuôn của model.
    """
    picked: list[str] = []
    for msg in reversed(history):
        if len(picked) >= RECENT_REPLIES:
            break
        if msg.role != "assistant" or msg.mode != mode or msg.turn_index == 0:
            continue
        phrase = _dm_phrase(msg.visible_content) if mode == "dm" else _story_opening(msg.visible_content)
        if phrase and phrase not in picked:
            picked.append(phrase)
    picked.reverse()
    return picked
