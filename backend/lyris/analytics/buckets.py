"""Chia khoảng các số có thể nói lên nội dung (độ dài tin nhắn, số ngày vắng...) trước khi ghi số liệu.

Mọi hàm trả một giá trị nằm trong enum tương ứng của `lyris.analytics.events`.
"""
from __future__ import annotations

import re

_ACTION = re.compile(r"\*[^*\n]+\*")


def length_bucket(chars: int) -> str:
    if chars <= 20:
        return "1_20"
    if chars <= 80:
        return "21_80"
    if chars <= 200:
        return "81_200"
    if chars <= 500:
        return "201_500"
    return "501_plus"


def turn_bucket(turn: int) -> str:
    if turn <= 1:
        return "1"
    if turn <= 4:
        return "2_4"
    if turn <= 9:
        return "5_9"
    if turn <= 19:
        return "10_19"
    return "20_plus"


def ttft_bucket(ms: float | None) -> str:
    if ms is None:
        return "none"
    if ms < 1000:
        return "lt_1s"
    if ms < 3000:
        return "1_3s"
    if ms < 10_000:
        return "3_10s"
    if ms < 30_000:
        return "10_30s"
    return "30s_plus"


def days_bucket(days: float) -> str:
    if days < 2:
        return "1"
    if days < 4:
        return "2_3"
    if days < 8:
        return "4_7"
    if days < 31:
        return "8_30"
    return "31_plus"


def small_count_bucket(count: int) -> str:
    if count <= 1:
        return "1"
    if count <= 5:
        return "2_5"
    return "6_plus"


def age_bucket(seconds: float) -> str:
    if seconds < 3600:
        return "lt_1h"
    if seconds < 86_400:
        return "lt_1d"
    if seconds < 7 * 86_400:
        return "lt_7d"
    return "7d_plus"


def has_action(text: str) -> bool:
    """Lượt của người chơi có *hành động* (giữa dấu sao) không."""
    return _ACTION.search(text) is not None


def clamp(value: float | int | None, lo: int, hi: int, *, step: int = 1) -> int:
    """Số nguyên trong [lo, hi], làm tròn theo `step` (thời gian làm tròn 100 ms)."""
    if value is None:
        return lo
    number = int(round(float(value) / step) * step)
    return max(lo, min(hi, number))


__all__ = [
    "age_bucket",
    "clamp",
    "days_bucket",
    "has_action",
    "length_bucket",
    "small_count_bucket",
    "ttft_bucket",
    "turn_bucket",
]
