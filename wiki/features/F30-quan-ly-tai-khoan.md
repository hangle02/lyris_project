# F30 — Quản lý tài khoản (chủ máy)

- **Trạng thái:** xem `memory/features.json` · **Phase:** Phase 4b
- **Giai đoạn:** Đã có
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

- [ ] Unit: route của chủ máy trả 403 cho thành viên.
- [ ] Unit: mã mời hết hạn sau 1/7/30 ngày, có giới hạn số mã còn hiệu lực; badge Còn hiệu lực / Đã dùng bởi @x / Hết hạn / Đã huỷ.
- [ ] Unit: mã mới và mật khẩu tạm chỉ hiện một lần: nền mờ và Esc không đóng được hộp đó; sao chép lỗi thì liên kết hiện ra để chọn tay.
- [ ] Unit: đặt lại mật khẩu cho mật khẩu tạm và đăng xuất mọi phiên cũ của người đó; tạm khoá thì không đăng nhập được, mở khoá thì được lại.
- [ ] Bot: chủ máy mở `#/admin` thấy nhóm 'Mục quản lý' có 'Tài khoản' và 'Số liệu', mục Mã mời và mục Thành viên có @handle của chủ máy.
- [ ] Bot: tạo mã mời 7 ngày thì mã hiện kèm 'Sao chép mã' và 'Sao chép liên kết'.
- [ ] Bot: tài khoản thành viên mở `#/admin` thì về `#/` và không có request nào tới `/api/admin`.

## Tests

- backend/tests/test_auth_api.py::test_admin_accounts_disable_enable
- backend/tests/test_auth_api.py::test_admin_reset_then_forced_change
- backend/tests/test_auth_api.py::test_active_invite_cap
- backend/tests/test_auth_api.py::test_invites_and_signup
- backend/tests/test_auth_routes.py::test_member_gets_403_on_owner_routes
- backend/tests/test_auth_hardening.py::test_admin_reset_clears_change_password_failures
- frontend/src/pages/admin/logic.test.ts
- frontend/src/pages/admin/secrets.test.ts
- bot: trang quản trị của chủ máy có tài khoản, mã mời, Số liệu
- bot: chủ máy tạo mã mời
- bot: thành viên mở #/admin thì về hub

## Liên quan

- **Code:** [`frontend/src/pages/admin/AdminPage.tsx`](../../frontend/src/pages/admin/AdminPage.tsx), [`frontend/src/pages/admin/logic.ts`](../../frontend/src/pages/admin/logic.ts), [`backend/lyris/api/routes_admin.py`](../../backend/lyris/api/routes_admin.py)
- **Tài liệu:** [auth.md §6.3, §7.3](../../docs/auth.md)
- **Quyết định:** [dang-ky-bang-ma-moi](../decisions/dang-ky-bang-ma-moi.md), [quen-mat-khau](../decisions/quen-mat-khau.md)
