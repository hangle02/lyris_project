# Tài khoản và trang profile

- **Trạng thái:** Đã xong · **Phase:** Phase 2c
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

- [x] `#/me` có số liệu, tab 'Nhân vật' và 'Persona'.
- [x] 'Sửa profile' đổi tên, handle (sai thì báo ngay dưới ô; trùng thì 422), giới thiệu, avatar, ảnh bìa.
- [x] Lưu xong thì header đổi tên ngay, không cần tải lại.
- [x] `#/u/<handle>` hiện profile công khai; handle không có thì 404.
- [x] Mọi card, persona, story thuộc một tài khoản và có `uid`.

## Liên quan

- **Code:** [`frontend/src/pages/profile/ProfilePage.tsx`](../../frontend/src/pages/profile/ProfilePage.tsx), [`frontend/src/pages/profile/EditProfileSheet.tsx`](../../frontend/src/pages/profile/EditProfileSheet.tsx), [`frontend/src/pages/profile/ProfileBanner.tsx`](../../frontend/src/pages/profile/ProfileBanner.tsx), [`frontend/src/hooks/useAccount.ts`](../../frontend/src/hooks/useAccount.ts), [`backend/lyris/api/routes_accounts.py`](../../backend/lyris/api/routes_accounts.py), [`backend/lyris/accounts.py`](../../backend/lyris/accounts.py)
- **Tài liệu:** [accounts.md](../../docs/accounts.md), [design-impl.md §13](../../docs/design-impl.md)
- **Quyết định:** [tach-tai-khoan-persona](../decisions/tach-tai-khoan-persona.md)
