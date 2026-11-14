# Thẻ suy nghĩ (Tiếng lòng giấu kín)

- **Trạng thái:** Đã xong · **Phase:** Phase 1, 2b
- **Màn hình:** [chat-story](../screens/chat-story.md), [chat-dm](../screens/chat-dm.md), [thought-menu](../screens/thought-menu.md)

## Là gì

Suy nghĩ thầm của nhân vật hiện thành thẻ viền trái, mặc định làm mờ với lời mời 'Chạm để lắng nghe'. Có hai kiểu: 'Lồng trong truyện' (inline, 2-3 thẻ rải giữa truyện) và 'Một đoạn ở cuối' (end). Công tắc 'Luôn hiện suy nghĩ' bỏ làm mờ.

## Hoạt động thế nào

- Thẻ suy nghĩ mặc định bị làm mờ, có lời mời 'Chạm để lắng nghe'. Chạm thì đọc được.
- Người chơi chọn kiểu suy nghĩ: 'Lồng trong truyện' (rải 2-3 thẻ giữa truyện) hoặc 'Một đoạn ở cuối'.
- Ai thích đọc hết thì bật 'Luôn hiện suy nghĩ'.

Kỹ thuật:

- Model viết `[Thought: ...]`; `llm/thought.py` tách khối.
- Kiểu suy nghĩ lưu theo story (`thought_style`), chọn ở `ThoughtMenu.tsx` hoặc Thiết lập story.
- 'Luôn hiện suy nghĩ' lưu ở trình duyệt (`revealThoughts.ts`).

## Done when

- [x] Thẻ suy nghĩ mặc định bị mờ; chạm thì rõ, chạm lần nữa mờ lại.
- [x] Bật 'Luôn hiện suy nghĩ' (lưu ở localStorage `lyris.revealThoughts`) thì mọi thẻ hiện rõ.
- [x] Kiểu 'Lồng trong truyện' cho 2-4 Thought, không có hai Thought liền nhau; kiểu 'Một đoạn ở cuối' cho đúng một Thought cuối lượt (harness kiểm tra).
- [x] Đổi kiểu suy nghĩ ở menu 'Suy nghĩ' (icon mắt) trên header hoặc ở Thiết lập story.
- [x] DM cũng hiện thẻ suy nghĩ thu gọn (`ThoughtCard compact`).

## Liên quan

- **Code:** [`frontend/src/pages/chat/ThoughtCard.tsx`](../../frontend/src/pages/chat/ThoughtCard.tsx), [`frontend/src/pages/chat/ThoughtMenu.tsx`](../../frontend/src/pages/chat/ThoughtMenu.tsx), [`frontend/src/pages/chat/revealThoughts.ts`](../../frontend/src/pages/chat/revealThoughts.ts), [`frontend/src/lib/storyOptions.ts`](../../frontend/src/lib/storyOptions.ts), [`backend/lyris/llm/thought.py`](../../backend/lyris/llm/thought.py)
- **Tài liệu:** [plan.md §1](../../docs/plan.md), [design-impl.md §6.2](../../docs/design-impl.md)
- **Quyết định:** [thought-rai-giua-truyen](../decisions/thought-rai-giua-truyen.md), [tuy-chon-doc-suy-nghi](../decisions/tuy-chon-doc-suy-nghi.md)
