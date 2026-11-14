# Persona của người chơi

- **Trạng thái:** Đã xong · **Phase:** Phase 2, 2c
- **Màn hình:** [personas](../screens/personas.md), [account-sheet](../screens/account-sheet.md), [start-story-sheet](../screens/start-story-sheet.md)

## Là gì

Một tài khoản có nhiều persona (tên, giới tính, mô tả, xưng hô, avatar). Persona dùng khi trò chuyện; một persona là mặc định cho story mới.

## Hoạt động thế nào

- Persona là vai người chơi nhập khi trò chuyện: tên, giới tính, mô tả, xưng hô, avatar.
- Một tài khoản có nhiều persona. Một persona là mặc định cho story mới.
- Quản lý persona ở trang `#/personas`; đổi persona mặc định ở sheet Tài khoản.

Kỹ thuật:

- API persona ở `api/routes_studio.py`.
- `pages/personaLogic.ts` lo form; `usePersonaSettings.ts` lo persona mặc định.

## Done when

- [x] Trang `#/personas` thêm, sửa, xoá persona; xoá báo số story bị xoá theo.
- [x] Tải avatar persona; avatar hiện cạnh lượt người chơi ở Story và DM.
- [x] Đổi persona mặc định ở sheet Tài khoản; story mới dùng persona đó.
- [x] Persona không có ảnh dùng chữ cái đầu.

## Liên quan

- **Code:** [`frontend/src/pages/PersonasPage.tsx`](../../frontend/src/pages/PersonasPage.tsx), [`frontend/src/pages/personaLogic.ts`](../../frontend/src/pages/personaLogic.ts), [`backend/lyris/api/routes_studio.py`](../../backend/lyris/api/routes_studio.py), [`frontend/src/components/shell/usePersonaSettings.ts`](../../frontend/src/components/shell/usePersonaSettings.ts)
- **Tài liệu:** [accounts.md](../../docs/accounts.md)
- **Quyết định:** [tach-tai-khoan-persona](../decisions/tach-tai-khoan-persona.md)
