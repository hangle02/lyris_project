# Tạo tài khoản cần mã mời; tài khoản đầu là chủ máy

- **Ngày:** 2026-11-14 · **Ai quyết:** người dùng

## Bối cảnh

Người dùng muốn đăng nhập, tạo tài khoản và quản lý nhiều tài khoản.

## Lựa chọn

Tài khoản id nhỏ nhất (chủ mọi dữ liệu cũ) là chủ máy, người duy nhất tạo mã mời. Mã dùng một lần, hết hạn 1/7/30 ngày, DB chỉ lưu sha256. Chủ máy đặt mật khẩu lần đầu bằng mã thiết lập in ra Terminal.

## Vì sao

Người lạ cùng Wi-Fi hay Tailscale không tự tạo được tài khoản. Không phải "ai mở trang trước thì thắng".

## Đã cân nhắc

Đăng ký tự do; chủ máy đặt mật khẩu chỉ bằng trang web.

## Nguồn

- Lời người dùng, 2026-11-13 17:18 (xem [raw/](../raw/))
- [docs/auth.md](../../docs/auth.md) (Quyết định của người dùng), §1.3, §2.4
