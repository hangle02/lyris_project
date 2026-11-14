# Quên mật khẩu thì chủ máy đặt lại

- **Ngày:** 2026-11-14 · **Ai quyết:** người dùng

## Bối cảnh

Không có email hay khôi phục tự phục vụ.

## Lựa chọn

Chủ máy đặt lại ở trang "Quản lý tài khoản": mật khẩu tạm hiện một lần, hết hạn 72 giờ, phải đổi ở lần đăng nhập sau. Chủ máy quên thì chạy bash scripts/lyris-admin.sh reset-password trên Mac.

## Vì sao

Quyết định của người dùng. Ai chạy được lệnh trên Mac đã giữ máy và file DB.

## Đã cân nhắc

Email, khôi phục tự phục vụ, passkey (không làm ở phase này).

## Nguồn

- [docs/auth.md](../../docs/auth.md) (Quyết định của người dùng), §1.2, §2.4, §10
