# F28 — Tài khoản và trang profile

- **Trạng thái:** xem `memory/features.json` · **Phase:** Phase 2c
- **Giai đoạn:** Đã có
- **Màn hình:** [profile](../screens/profile.md), [edit-profile-sheet](../screens/edit-profile-sheet.md), [account-sheet](../screens/account-sheet.md)

## Là gì

Tài khoản (tên hiển thị, @handle, avatar, ảnh bìa, giới thiệu) tách khỏi persona. Tài khoản dùng cho việc bên ngoài (tạo nhân vật, sau này bình luận); persona dùng khi chat. Có trang profile của mình và của người khác.

## Hoạt động thế nào

- Tài khoản là 'mình' ở bên ngoài story: tên hiển thị, @handle, avatar, ảnh bìa, giới thiệu.
- Persona là vai trong story. Hai thứ tách riêng.
- Trang `#/me` là profile của mình; `#/u/<handle>` là profile của người khác.

Kỹ thuật:

- API ở `api/routes_accounts.py`, logic ở `accounts.py`.
- Mọi card, persona, story có `uid` của tài khoản sở hữu.
- `hooks/useAccount.ts` cập nhật header ngay khi lưu.

## Done when

- [ ] Unit: handle theo luật (chữ thường, không trùng, so trùng không phân biệt hoa thường); trùng thì 422; sai thì báo ngay dưới ô, mỗi luật một câu.
- [ ] Unit: profile công khai đọc theo handle; handle không có thì 404.
- [ ] Unit: mọi card, persona, story thuộc một tài khoản và có `uid`; hai tài khoản không thấy dữ liệu của nhau.
- [ ] Unit: đổi tên profile thì trạng thái đăng nhập nhận tên mới ngay, không cần tải lại.
- [ ] Bot: `#/me` có số liệu và hai tab 'Nhân vật', 'Persona'.
- [ ] Bot: bấm 'Sửa profile', đổi tên hiển thị, lưu thì nút tài khoản trên header có tên mới (aria-label 'Tài khoản: {tên}. …') mà không tải lại trang; gõ handle có khoảng trắng hoặc ký tự lạ (vd `chu may!`) thì ô có `aria-invalid="true"` và câu lỗi ngay dưới ô.
- [ ] Bot: `#/u/<handle của mình>` hiện profile; `#/u/khong_ton_tai_xyz` hiện 'Không có tài khoản @khong_ton_tai_xyz trên Lyris.'
- [ ] Bot: 'Sửa profile' đổi cả giới thiệu, ảnh đại diện, ảnh bìa: chọn ảnh (như hộp chọn file) thì ảnh được lưu và nút thành 'Đổi ảnh đại diện' / 'Đổi ảnh bìa'; sửa 'Giới thiệu', bấm Lưu, tải lại `#/me` thì trang hiện giới thiệu mới, ảnh đại diện và ảnh bìa (ảnh tải được).

## Tests

- backend/tests/test_accounts.py
- backend/tests/test_auth_api.py::test_completed_profile_ignores_setup_profile_fields
- frontend/src/pages/profile/logic.test.ts
- frontend/src/lib/auth.test.ts
- bot: #/me có số liệu và hai tab
- bot: Sửa profile đổi tên ngay, handle sai báo dưới ô
- bot: profile công khai theo handle
- bot: Sửa profile đổi giới thiệu, ảnh đại diện, ảnh bìa và #/me hiện đủ

## Liên quan

- **Code:** [`frontend/src/pages/profile/ProfilePage.tsx`](../../frontend/src/pages/profile/ProfilePage.tsx), [`frontend/src/pages/profile/EditProfileSheet.tsx`](../../frontend/src/pages/profile/EditProfileSheet.tsx), [`frontend/src/pages/profile/ProfileBanner.tsx`](../../frontend/src/pages/profile/ProfileBanner.tsx), [`frontend/src/hooks/useAccount.ts`](../../frontend/src/hooks/useAccount.ts), [`backend/lyris/api/routes_accounts.py`](../../backend/lyris/api/routes_accounts.py), [`backend/lyris/accounts.py`](../../backend/lyris/accounts.py)
- **Tài liệu:** [accounts.md](../../docs/accounts.md), [design-impl.md §13](../../docs/design-impl.md)
- **Quyết định:** [tach-tai-khoan-persona](../decisions/tach-tai-khoan-persona.md)
