"""Coin (docs/coins.md): ví, sổ coin chỉ thêm, giữ chỗ khi sinh câu trả lời, quà tạo tài khoản và đăng nhập.

- `clock`: ngày coin theo giờ Việt Nam (UTC+7).
- `errors`: giá, quà, `CoinsRequired` (402), `IdemConflict`, `InsufficientCoins`, `HoldBusy`.
- `ledger`: `post()` (cách DUY NHẤT đổi số dư), `open_wallet`, ví tự tạo khi thiếu.
- `holds`: giữ chỗ / trừ / nhả cho một lượt sinh.
- `wallet`: `CoinService` mà app và `ChatService` dùng (ví, checkin, lịch sử, sự kiện số liệu).

Module này không import gì ở cấp gói để `lyris.auth.store` dùng được `ledger` mà không vòng import.
"""
