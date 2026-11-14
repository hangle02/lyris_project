# F21 — Persona của người chơi

- **Trạng thái:** xem `memory/features.json` · **Phase:** Phase 2, 2c
- **Giai đoạn:** Đã có
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

- [ ] Unit: tạo, sửa, xoá persona qua API; xoá persona đang có story thì 409, xác nhận thì xoá kèm story và trả các story bị xoá.
- [ ] Unit: avatar persona tải lên được; story mới dùng persona mặc định của tài khoản.
- [ ] Unit: persona không có ảnh dùng chữ cái đầu (giữ dấu tiếng Việt).
- [ ] Bot: bấm 'Bước vào câu chuyện' ở hồ sơ mở sheet 'Chọn persona' có nhóm radio 'Persona' với ít nhất một persona chọn được.
- [ ] Bot: ở `#/personas`, bấm 'Thêm persona', điền tên, lưu thì persona mới có trong danh sách với avatar chữ cái đầu.
- [ ] Bot: sheet Tài khoản có nhóm radio 'Persona đang dùng'; chọn persona khác rồi tải lại thì lựa chọn vẫn giữ.

## Tests

- backend/tests/test_api_studio.py::test_persona_crud
- backend/tests/test_integration_phase2.py::test_delete_card_and_persona_409_then_with_stories
- backend/tests/test_integration_phase2.py::test_persona_edit_accepts_persona_out_as_sent_by_ui
- backend/tests/test_phase3_fixes.py::test_delete_card_and_persona_return_deleted_story_ids
- backend/tests/test_accounts.py::test_persona_avatar
- backend/tests/test_lyris_design.py::test_default_persona_and_model_for_new_story
- frontend/src/pages/personaLogic.test.ts
- frontend/src/components/ui/logic.test.ts
- bot: bắt đầu story qua sheet và persona, story mở với lời chào
- bot: thêm persona
- bot: đổi persona mặc định ở sheet Tài khoản

## Liên quan

- **Code:** [`frontend/src/pages/PersonasPage.tsx`](../../frontend/src/pages/PersonasPage.tsx), [`frontend/src/pages/personaLogic.ts`](../../frontend/src/pages/personaLogic.ts), [`backend/lyris/api/routes_studio.py`](../../backend/lyris/api/routes_studio.py), [`frontend/src/components/shell/usePersonaSettings.ts`](../../frontend/src/components/shell/usePersonaSettings.ts)
- **Tài liệu:** [accounts.md](../../docs/accounts.md)
- **Quyết định:** [tach-tai-khoan-persona](../decisions/tach-tai-khoan-persona.md)
