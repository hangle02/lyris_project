"""Ngày coin (docs/coins.md §1): ngày lịch theo giờ Việt Nam (UTC+7, không có giờ mùa hè).

Mọi thứ "mỗi ngày" (quà đăng nhập, nhiệm vụ, giới hạn quảng cáo, trần 30 coin) đổi ngày lúc 00:00 giờ Việt Nam
(= 17:00 UTC hôm trước). Giờ lấy từ `lyris.auth.clock.now()` để test giả được giờ. Múi giờ cố định thay vì
`zoneinfo` (tạm chọn): không phụ thuộc gói tzdata.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from lyris.auth import clock as auth_clock

COIN_TZ = timezone(timedelta(hours=7), "UTC+7")


def now() -> datetime:
    return auth_clock.now()


def coin_day(moment: datetime | None = None) -> str:
    """'YYYY-MM-DD' của `moment` (mặc định: bây giờ) theo giờ Việt Nam."""
    value = moment if moment is not None else auth_clock.now()
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(COIN_TZ).strftime("%Y-%m-%d")


__all__ = ["COIN_TZ", "coin_day", "now"]
