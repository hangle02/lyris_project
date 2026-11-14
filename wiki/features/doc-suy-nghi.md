# Công tắc 'Đọc suy nghĩ của nhân vật'

- **Trạng thái:** Đã xong · **Phase:** Phase 4 (B)
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

- [x] Công tắc có ở 3 chỗ: sheet Bước vào câu chuyện (trong 'Tuỳ chỉnh story'), Thiết lập story, và menu Suy nghĩ trên header chat.
- [x] Tắt thì thẻ suy nghĩ không có trong DOM ở Story, DM và cả lúc stream.
- [x] Lượt chỉ có suy nghĩ hiện dòng 'Lượt này chỉ có suy nghĩ của {tên}.' và vẫn còn hàng thao tác.
- [x] Tắt thì nút header đổi sang icon mắt gạch, aria-label 'Suy nghĩ (đang ẩn)'.
- [x] Tắt thì nhóm 'Điều {tên} giữ trong lòng' trong ngăn cảm xúc biến mất.
- [x] Chat thử ở Studio không bị ảnh hưởng.

## Liên quan

- **Code:** [`frontend/src/components/showThoughts.ts`](../../frontend/src/components/showThoughts.ts), [`frontend/src/lib/storyBlocks.ts`](../../frontend/src/lib/storyBlocks.ts), [`frontend/src/lib/storyOptions.ts`](../../frontend/src/lib/storyOptions.ts), [`frontend/src/pages/chat/ThoughtMenu.tsx`](../../frontend/src/pages/chat/ThoughtMenu.tsx), [`frontend/src/components/StorySettingsPanel.tsx`](../../frontend/src/components/StorySettingsPanel.tsx), [`backend/lyris/api/routes.py`](../../backend/lyris/api/routes.py)
- **Tài liệu:** [phase4.md §12](../../docs/phase4.md), [design-impl.md §17](../../docs/design-impl.md)
- **Quyết định:** [tuy-chon-doc-suy-nghi](../decisions/tuy-chon-doc-suy-nghi.md)
