# F08 — Công tắc 'Đọc suy nghĩ của nhân vật'

- **Trạng thái:** xem `memory/features.json` · **Phase:** Phase 4 (B)
- **Giai đoạn:** Đã có
- **Màn hình:** [chat-story](../screens/chat-story.md), [chat-dm](../screens/chat-dm.md), [thought-menu](../screens/thought-menu.md), [story-settings](../screens/story-settings.md), [start-story-sheet](../screens/start-story-sheet.md), [heart-drawer](../screens/heart-drawer.md)

## Là gì

Người chơi chọn không đọc suy nghĩ. Tắt thì thẻ suy nghĩ không có trong DOM, nhưng nhân vật vẫn nghĩ như thường. Lưu theo từng story (`show_thoughts`).

## Hoạt động thế nào

- Người chơi không muốn biết nhân vật nghĩ gì thì tắt 'Đọc suy nghĩ của nhân vật'.
- Nhân vật vẫn nghĩ như thường, chỉ là người chơi không thấy.
- Bật lại lúc nào cũng được, các thẻ cũ hiện lại.

Kỹ thuật:

- Lưu theo từng story ở cột `show_thoughts`.
- Tắt thì frontend bỏ khối thought trước khi vẽ (`showThoughts.ts`), nên thẻ không có trong DOM.
- Prompt không đổi; chat thử ở Studio luôn hiện suy nghĩ.

## Done when

- [ ] Unit: `show_thoughts` lưu theo story (tạo, sửa, đọc qua API); story cũ thiếu trường thì coi là bật; đổi công tắc không đổi prompt.
- [ ] Unit: `visibleBlocks` bỏ khối thought khi tắt, cả lúc đang stream; lượt chỉ có suy nghĩ cho dòng 'Lượt này chỉ có suy nghĩ của {tên}.' thay vì bong bóng rỗng.
- [ ] Unit: sheet Bước vào câu chuyện chỉ gửi `show_thoughts` khi tắt; khi tắt, ngăn cảm xúc không có nhóm 'Điều {tên} giữ trong lòng'.
- [ ] Bot: trong menu 'Suy nghĩ' tắt công tắc 'Đọc suy nghĩ của nhân vật' thì số thẻ suy nghĩ trong chat về 0 (không còn trong DOM); bật lại thì thẻ hiện lại.
- [ ] Bot: khi tắt, nút trên header có aria-label 'Suy nghĩ (đang ẩn)' và ở DM cũng không có thẻ suy nghĩ; công tắc cũng có ở sheet Bước vào câu chuyện (trong 'Tuỳ chỉnh story') và ở Thiết lập story.
- [ ] Bot: chat thử ở Studio vẫn hiện thẻ suy nghĩ.

## Tests

- backend/tests/test_lore_api.py::test_show_thoughts_create_patch_and_list
- backend/tests/test_lore_api.py::test_show_thoughts_does_not_change_prompt
- backend/tests/test_lore_api.py::test_story_model_default_show_thoughts
- frontend/src/lib/storyBlocks.test.ts
- frontend/src/lib/storyOptions.test.ts
- frontend/src/pages/character/startLogic.test.ts
- frontend/src/pages/chat/loreLogic.test.ts
- frontend/src/pages/chat/chatLogic.test.ts
- bot: tắt Đọc suy nghĩ thì ẩn suy nghĩ
- bot: Đọc suy nghĩ có ở header, sheet bắt đầu, Thiết lập story
- bot: chat thử ở Studio vẫn có suy nghĩ

## Liên quan

- **Code:** [`frontend/src/components/showThoughts.ts`](../../frontend/src/components/showThoughts.ts), [`frontend/src/lib/storyBlocks.ts`](../../frontend/src/lib/storyBlocks.ts), [`frontend/src/lib/storyOptions.ts`](../../frontend/src/lib/storyOptions.ts), [`frontend/src/pages/chat/ThoughtMenu.tsx`](../../frontend/src/pages/chat/ThoughtMenu.tsx), [`frontend/src/components/StorySettingsPanel.tsx`](../../frontend/src/components/StorySettingsPanel.tsx), [`backend/lyris/api/routes.py`](../../backend/lyris/api/routes.py)
- **Tài liệu:** [phase4.md §12](../../docs/phase4.md), [design-impl.md §17](../../docs/design-impl.md)
- **Quyết định:** [tuy-chon-doc-suy-nghi](../decisions/tuy-chon-doc-suy-nghi.md)
