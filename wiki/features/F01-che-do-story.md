# F01 — Chế độ Story (văn tiểu thuyết)

- **Trạng thái:** xem `memory/features.json` · **Phase:** Phase 1, 2, 2b
- **Giai đoạn:** Đã có
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

- [ ] Unit: `POST /api/stories/{id}/messages` stream câu trả lời qua SSE rồi lưu lượt khi xong; ngắt giữa chừng thì lưu phần đã có, ngắt trước chữ đầu tiên thì không lưu gì.
- [ ] Unit: `llm/thought.py` tách `[Thought: ...]` khỏi chữ ở mọi cách chia chunk, kể cả khối chưa đóng lúc đang stream; thẻ suy nghĩ nằm đúng chỗ của nó trong lượt.
- [ ] Unit: `lib/storyBlocks.ts`: lời trong ngoặc kép từ 3 chữ trở lên thành thẻ thoại, bỏ cặp ngoặc ngoài cùng; câu ngắn hơn ở lại trong dòng; `*hành động*` thành dẫn truyện không còn dấu sao.
- [ ] Bot: gửi một lượt ở Story thì ba chấm đang gõ hiện trước chữ đầu tiên, chữ hiện dần trong vùng đang stream, rồi lượt mới của nhân vật xuất hiện.
- [ ] Bot: trong lúc sinh có nút aria-label 'Dừng' (thay nút 'Gửi (Enter)'); sinh xong thì 'Dừng' biến mất.
- [ ] Bot: lượt nhân vật vừa sinh (`aria-label="Lượt của {tên}"`) có thẻ thoại không bắt đầu bằng dấu ngoặc kép, có thẻ suy nghĩ, không chứa chữ `[Thought`; phần dẫn truyện có `font-style: italic` và không có viền.
- [ ] Bot: trong lúc chờ chữ đầu tiên không có chữ 'đang suy nghĩ' hay số giây đếm.

## Tests

- backend/tests/test_thought.py
- backend/tests/test_api.py::test_full_send_flow
- backend/tests/test_api.py::test_abort_before_any_text_saves_nothing
- backend/tests/test_api.py::test_aclose_mid_stream_persists_partial
- backend/tests/test_api.py::test_client_disconnect_over_asgi_persists_partial
- frontend/src/lib/storyBlocks.test.ts
- frontend/src/lib/sse.test.ts
- frontend/src/lib/text.test.ts
- bot: lời trả lời stream, chấm đang gõ rồi tới chữ
- bot: đang sinh có nút Dừng
- bot: lượt nhân vật có thẻ thoại, thẻ suy nghĩ, dẫn truyện nghiêng
- bot: lúc chờ chỉ có ba chấm, không có chữ

## Liên quan

- **Code:** [`backend/lyris/chat/service.py`](../../backend/lyris/chat/service.py), [`backend/lyris/llm/thought.py`](../../backend/lyris/llm/thought.py), [`backend/lyris/prompt/builder.py`](../../backend/lyris/prompt/builder.py), [`backend/lyris/api/routes.py`](../../backend/lyris/api/routes.py), [`frontend/src/lib/storyBlocks.ts`](../../frontend/src/lib/storyBlocks.ts), [`frontend/src/components/Prose.tsx`](../../frontend/src/components/Prose.tsx), [`frontend/src/components/MessageList.tsx`](../../frontend/src/components/MessageList.tsx), [`frontend/src/hooks/useChat.ts`](../../frontend/src/hooks/useChat.ts)
- **Tài liệu:** [phase1.md](../../docs/phase1.md), [design-impl.md §6.2](../../docs/design-impl.md), [DESIGN.md §6](../../DESIGN.md)
- **Quyết định:** [thuat-ngu-story](../decisions/thuat-ngu-story.md), [the-thoai-khong-ngoac](../decisions/the-thoai-khong-ngoac.md), [thought-rai-giua-truyen](../decisions/thought-rai-giua-truyen.md), [an-chu-ky-thuat](../decisions/an-chu-ky-thuat.md)
