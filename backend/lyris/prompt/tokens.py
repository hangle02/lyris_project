"""Ước lượng số token, không cần tokenizer thật.

Đo thực tế với Gemma 4 trên tiếng Việt: khoảng 3.4 ký tự/token. Chia cho 3.0 để ước lượng
dư một chút (an toàn khi cắt lịch sử), cộng 4 token cho phần đầu/cuối của mỗi message.
"""
from __future__ import annotations

import math

CHARS_PER_TOKEN = 3.0
MESSAGE_OVERHEAD = 4


def estimate_tokens(text: str) -> int:
    """`ceil(len(text) / 3.0) + 4`."""
    return math.ceil(len(text) / CHARS_PER_TOKEN) + MESSAGE_OVERHEAD
