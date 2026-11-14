"""Lỗi và hằng số của coin (docs/coins.md §2.1, §3.3)."""
from __future__ import annotations

PRICE_PER_REPLY = 6
SIGNUP_GRANT = 300
DAILY_GRANT = 60

# §3.3, §10.5: không chữ "token", "model", "credits".
COINS_REQUIRED_DETAIL = "Bạn đã hết coin. Mỗi câu trả lời cần 6 coin."
IDEM_CONFLICT_DETAIL = "Yêu cầu này đã được ghi với nội dung khác. Hãy tải lại trang rồi thử lại."


class CoinError(Exception):
    """Gốc của mọi lỗi coin."""


class CoinsRequired(CoinError):
    """Số coin dùng được (số dư − giữ chỗ) không đủ cho một câu trả lời (API: 402 `coins_required`)."""

    def __init__(self, balance: int, available: int, price: int = PRICE_PER_REPLY) -> None:
        super().__init__(COINS_REQUIRED_DETAIL)
        self.balance = balance
        self.available = available
        self.price = price

    def payload(self) -> dict[str, object]:
        return {
            "detail": COINS_REQUIRED_DETAIL,
            "code": "coins_required",
            "balance": self.balance,
            "available": self.available,
            "price": self.price,
        }


class InsufficientCoins(CoinError):
    """`post()` với delta âm làm số dư < 0 (không bao giờ xảy ra khi trừ từ một giữ chỗ `held`)."""


class IdemConflict(CoinError):
    """Cùng `idem_key` đã ghi với nội dung khác (API: 409 `idem_conflict`)."""


class HoldBusy(CoinError):
    """Tài khoản đã có một giữ chỗ đang mở (một lượt sinh khác chưa xong; API: 409)."""


__all__ = [
    "COINS_REQUIRED_DETAIL",
    "DAILY_GRANT",
    "IDEM_CONFLICT_DETAIL",
    "PRICE_PER_REPLY",
    "SIGNUP_GRANT",
    "CoinError",
    "CoinsRequired",
    "HoldBusy",
    "IdemConflict",
    "InsufficientCoins",
]


class AdjustRejected(CoinError):
    """Chủ máy cộng/trừ coin không hợp lệ (API: 422 với `code`)."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


def adjust_too_large_detail(available: int) -> str:
    return f"Không trừ được quá số coin dùng được ({max(0, available)} coin)."


ADJUST_OWNER_DETAIL = "Tài khoản quản lý không tốn coin."
