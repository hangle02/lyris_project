# Mật khẩu scrypt, phiên cookie HttpOnly, không thêm thư viện

- **Ngày:** 2026-11-14 · **Ai quyết:** thiết kế

## Bối cảnh

backend/.venv không có argon2, bcrypt, passlib.

## Lựa chọn

hashlib.scrypt n=2^17 (chuẩn hoá NFC trước khi băm), so sánh hmac.compare_digest. Cookie lyris_session HttpOnly, SameSite=Lax; DB chỉ lưu sha256 của token. Hạn trượt 30 ngày, tuyệt đối 180 ngày, tối đa 20 phiên mỗi tài khoản. Chặn CSRF bằng header X-Lyris.

## Vì sao

Không cài thêm gì. Lộ file DB không lộ phiên đang sống. Bàn phím iPhone và Mac có thể sinh hai dạng Unicode cho cùng chữ có dấu.

## Đã cân nhắc

argon2/bcrypt; lưu token thô; SameSite=Strict (làm liên kết mời mở từ Tin nhắn bị coi như chưa đăng nhập).

## Nguồn

- [docs/auth.md](../../docs/auth.md) §0, §1.4, §3.1, §3.2, §3.3
