# Chế độ Story (văn tiểu thuyết)

- **Trạng thái:** Đã xong · **Phase:** Phase 1, 2, 2b
- **Màn hình:** [chat-story](../screens/chat-story.md)

## Là gì

Nhân vật trả lời như một đoạn tiểu thuyết. Mỗi lượt được tách thành 3 loại khối: dẫn truyện (nghiêng, không khung), lời thoại (thẻ, bỏ cặp ngoặc ngoài) và thẻ suy nghĩ. Trả lời được stream từng chữ qua SSE, có nút Dừng.

## Hoạt động thế nào

- Người chơi gõ một lượt ở ô nhập rồi gửi.
- Câu trả lời hiện dần từng chữ. Muốn dừng giữa chừng thì bấm Dừng.
- Mỗi lượt của nhân vật có ba loại khối: dẫn truyện nghiêng, thẻ thoại, thẻ suy nghĩ.

Kỹ thuật:

- Backend stream qua SSE (`POST /api/stories/{id}/messages` gửi lượt mới; `POST /api/stories/{id}/reply` để nhân vật nói tiếp), `chat/service.py` lưu lượt khi xong.
- `llm/thought.py` tách `[Thought: ...]` ra khỏi chữ, kể cả khối chưa đóng lúc đang stream.
- Frontend: `lib/storyBlocks.ts` chia khối, `Prose.tsx` vẽ khối.

## Done when

- [x] Gửi một lượt ở Story thì câu trả lời hiện dần từng chữ, có nút Dừng trong lúc sinh.
- [x] Lời trong ngoặc kép từ 3 chữ trở lên hiện thành thẻ thoại, không còn dấu ngoặc ngoài cùng.
- [x] Phần dẫn truyện hiện nghiêng màu muted, không có khung.
- [x] `[Thought: ...]` không bao giờ lọt vào chữ dẫn truyện; nó thành thẻ suy nghĩ đúng chỗ nó nằm.
- [x] Trong lúc chờ chữ đầu tiên chỉ có ba chấm nhảy ở cột nhân vật, không có chữ 'đang suy nghĩ' hay đồng hồ.
- [x] `lib/storyBlocks.test.ts` và `backend/tests/test_thought.py` qua.

## Liên quan

- **Code:** [`backend/lyris/chat/service.py`](../../backend/lyris/chat/service.py), [`backend/lyris/llm/thought.py`](../../backend/lyris/llm/thought.py), [`backend/lyris/prompt/builder.py`](../../backend/lyris/prompt/builder.py), [`backend/lyris/api/routes.py`](../../backend/lyris/api/routes.py), [`frontend/src/lib/storyBlocks.ts`](../../frontend/src/lib/storyBlocks.ts), [`frontend/src/components/Prose.tsx`](../../frontend/src/components/Prose.tsx), [`frontend/src/components/MessageList.tsx`](../../frontend/src/components/MessageList.tsx), [`frontend/src/hooks/useChat.ts`](../../frontend/src/hooks/useChat.ts)
- **Tài liệu:** [phase1.md](../../docs/phase1.md), [design-impl.md §6.2](../../docs/design-impl.md), [DESIGN.md §6](../../DESIGN.md)
- **Quyết định:** [thuat-ngu-story](../decisions/thuat-ngu-story.md), [the-thoai-khong-ngoac](../decisions/the-thoai-khong-ngoac.md), [thought-rai-giua-truyen](../decisions/thought-rai-giua-truyen.md), [an-chu-ky-thuat](../decisions/an-chu-ky-thuat.md)
