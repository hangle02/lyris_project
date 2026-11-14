"""Giờ của phần đăng nhập, gom một chỗ để test giả thời gian (`monkeypatch.setattr(clock, "now", ...)`).

Mọi mốc thời gian lưu dạng `YYYY-MM-DDTHH:MM:SS.fffZ` (UTC), cùng dạng với `strftime('%Y-%m-%dT%H:%M:%fZ')`
của SQLite trong các migration, nên so sánh chuỗi là so sánh thời gian.
"""
from __future__ import annotations

from datetime import datetime, timezone


def now() -> datetime:
    return datetime.now(timezone.utc)


def iso(moment: datetime) -> str:
    moment = moment.astimezone(timezone.utc)
    return moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"


def parse(text: str) -> datetime:
    """Đọc mốc đã lưu (chấp nhận cả dạng không có phần nghìn giây hay không có `Z`)."""
    value = text.strip().replace("Z", "+00:00")
    moment = datetime.fromisoformat(value)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


__all__ = ["iso", "now", "parse"]
