# Đăng nhập, mã mời và nhiều tài khoản

- **Trạng thái:** Đã xong · **Phase:** Phase 4b
- **Màn hình:** [login](../screens/login.md), [signup](../screens/signup.md), [setup-owner](../screens/setup-owner.md), [force-password](../screens/force-password.md), [auth-splash](../screens/auth-splash.md), [account-sheet](../screens/account-sheet.md)

## Là gì

Mở Lyris phải đăng nhập. Tài khoản đầu tiên là chủ máy, người duy nhất tạo mã mời. Người khác tạo tài khoản bằng mã mời; mỗi người chỉ thấy story của mình. Quên mật khẩu thì chủ máy đặt lại; chủ máy quên thì chạy lệnh trên Mac.

## Hoạt động thế nào

- Mở Lyris thì phải đăng nhập.
- Lần đầu, chủ máy tạo tài khoản bằng mã thiết lập in ra Terminal.
- Người khác tạo tài khoản bằng mã mời của chủ máy. Mỗi người chỉ thấy story của mình.
- Quên mật khẩu thì chủ máy đặt lại. Chủ máy quên thì chạy `scripts/lyris-admin.sh` trên Mac.

Kỹ thuật:

- Mật khẩu băm bằng scrypt; phiên lưu bằng cookie (`backend/lyris/auth/`).
- Bảng và cột mới nằm trong migration `0008_auth.sql`.
- `test_isolation_sweep.py` gọi mọi route bằng hai tài khoản để chắc không ai thấy dữ liệu của người kia.

## Done when

- [x] Chưa đăng nhập mà mở `#/studio` thì sang `#/login`, đăng nhập xong quay lại `#/studio`.
- [x] Lần đầu, backend in mã thiết lập ra Terminal; trang thiết lập chủ máy dùng mã đó.
- [x] Tạo tài khoản bằng mã mời (viết thường cũng được); mã bị bỏ khỏi thanh địa chỉ.
- [x] Mật khẩu tạm bắt phải đổi trước khi vào app.
- [x] Sheet Tài khoản có 'Đổi mật khẩu', 'Đăng xuất', 'Đăng xuất mọi thiết bị' (hỏi lại).
- [x] Đổi tài khoản trên cùng trình duyệt thì bản nháp của người trước bị xoá, theme giữ nguyên.
- [x] `test_isolation_sweep.py` (quét mọi route với hai tài khoản) và các test auth qua; `scripts/lyris-admin.sh` đặt lại mật khẩu được.

## Liên quan

- **Code:** [`backend/lyris/auth/`](../../backend/lyris/auth/), [`backend/lyris/api/routes_auth.py`](../../backend/lyris/api/routes_auth.py), [`backend/lyris/db/migrations/0008_auth.sql`](../../backend/lyris/db/migrations/0008_auth.sql), [`frontend/src/lib/auth.ts`](../../frontend/src/lib/auth.ts), [`frontend/src/hooks/useAuth.ts`](../../frontend/src/hooks/useAuth.ts), [`frontend/src/pages/auth/`](../../frontend/src/pages/auth/), [`scripts/lyris-admin.sh`](../../scripts/lyris-admin.sh)
- **Tài liệu:** [auth.md](../../docs/auth.md)
- **Quyết định:** [dang-ky-bang-ma-moi](../decisions/dang-ky-bang-ma-moi.md), [quen-mat-khau](../decisions/quen-mat-khau.md), [scrypt-va-phien](../decisions/scrypt-va-phien.md)
