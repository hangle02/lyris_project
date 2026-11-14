# Quản lý tài khoản (chủ máy)

- **Trạng thái:** Đã xong · **Phase:** Phase 4b
- **Màn hình:** [admin](../screens/admin.md)

## Là gì

Trang `#/admin` chỉ chủ máy vào được: tạo và huỷ mã mời, xem thành viên, đặt lại mật khẩu, tạm khoá và mở khoá.

## Hoạt động thế nào

- Chủ máy mở trang `#/admin` (thành viên khác không vào được).
- Tạo mã mời với hạn 1, 7 hoặc 30 ngày, rồi gửi mã hoặc liên kết cho người cần.
- Xem thành viên, đặt lại mật khẩu, tạm khoá hoặc mở khoá.

Kỹ thuật:

- API ở `api/routes_admin.py`, chỉ chủ máy gọi được.
- Mã mời chỉ hiện một lần; đặt lại mật khẩu thì đăng xuất mọi phiên cũ của người đó.

## Done when

- [x] Thành viên mở `#/admin` thì về hub mà không gọi /api/admin.
- [x] 'Tạo mã mời' chọn hết hạn 1/7/30 ngày; mã chỉ hiện một lần, có 'Sao chép mã' và 'Sao chép liên kết'.
- [x] Danh sách mã có badge Còn hiệu lực / Đã dùng bởi @x / Hết hạn / Đã huỷ.
- [x] Đặt lại mật khẩu hiện mật khẩu tạm; phiên cũ của người đó bị đăng xuất.
- [x] Tạm khoá thì người đó không đăng nhập được; Mở khoá thì được lại.

## Liên quan

- **Code:** [`frontend/src/pages/admin/AdminPage.tsx`](../../frontend/src/pages/admin/AdminPage.tsx), [`frontend/src/pages/admin/logic.ts`](../../frontend/src/pages/admin/logic.ts), [`backend/lyris/api/routes_admin.py`](../../backend/lyris/api/routes_admin.py)
- **Tài liệu:** [auth.md §6.3, §7.3](../../docs/auth.md)
- **Quyết định:** [dang-ky-bang-ma-moi](../decisions/dang-ky-bang-ma-moi.md), [quen-mat-khau](../decisions/quen-mat-khau.md)
