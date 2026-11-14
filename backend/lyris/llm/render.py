"""Dựng lại đúng văn bản prompt mà Ollama render từ `/api/chat`, để gửi qua `/api/generate` `raw` (prefill §10.6).

Chỉ dùng cho prefill: phần đầu prompt lượt sau phải kết thúc ĐÚNG chỗ prompt thật rẽ ra (ngay trước lượt
người chơi mới), mà `/api/chat` luôn nối thêm phần mở lượt model (generation prompt) vào cuối. Mỗi renderer
ở đây đã được đối chiếu token-từng-token với `/api/chat` trên Ollama thật (khớp `matched == total` trong
`prefix_cache` của server.log). Renderer chưa đối chiếu: trả None, worker prefill bằng `/api/chat` như cũ.
"""
from __future__ import annotations

import re
from collections.abc import Sequence

from lyris.models import ChatTurn

# gemma4 (renderer "gemma4-large", ví dụ gemma4:12b; Ollama 0.40.16): BOS, rồi mỗi message là
# `<|turn>{role}\n{content đã trim}<turn|>\n` (assistant -> "model", bỏ khối suy nghĩ <|channel>...<channel|>).
# Generation prompt (không gửi trong prefix) là `<|turn>model\n<|channel>thought\n<channel|>` khi think tắt.
_GEMMA4_THOUGHT = re.compile(r"<\|channel>.*?<channel\|>", re.S)
_GEMMA4_ROLES = {"system": "system", "user": "user", "assistant": "model"}


def _render_gemma4(messages: Sequence[ChatTurn], open_last: bool = False) -> str | None:
    parts = ["<bos>"]
    last = len(messages) - 1
    for i, m in enumerate(messages):
        role = _GEMMA4_ROLES.get(m.role)
        if role is None:
            return None
        content = _GEMMA4_THOUGHT.sub("", m.content) if role == "model" else m.content
        if open_last and i == last:
            # Lượt còn mở (Phase 4, §6.5): phần đầu của message thật, chưa có phần sau nên không trim cuối,
            # không đóng lượt.
            parts.append(f"<|turn>{role}\n{content.lstrip()}")
        else:
            parts.append(f"<|turn>{role}\n{content.strip()}<turn|>\n")
    return "".join(parts)


_RENDERERS = {"gemma4-large": _render_gemma4}


def render_prefix(renderer: str | None, messages: Sequence[ChatTurn], *, open_last: bool = False) -> str | None:
    """Văn bản raw của `messages` đúng như `/api/chat` render, KHÔNG kèm generation prompt: prompt chat thật
    `messages + [lượt người chơi]` có văn bản này làm phần đầu. None khi renderer chưa hỗ trợ (hoặc gặp role lạ).

    `open_last` (Phase 4, docs/phase4.md §6.5): message cuối là lượt user còn mở (`lore_head`), render thành
    `<|turn>user\n{content.lstrip()}` không có `<turn|>\n`, để văn bản là chuỗi đầu của prompt thật.
    """
    fn = _RENDERERS.get(renderer or "")
    if fn is None or not messages:
        return None
    return fn(messages, open_last)
