# Trình bày lượt của người chơi

- **Trạng thái:** Đã xong · **Phase:** Phase 3b, 4
- **Màn hình:** [chat-story](../screens/chat-story.md), [chat-dm](../screens/chat-dm.md)

## Là gì

Quy ước người chơi gõ: "…" là lời thoại (thành ô thoại hồng, dài ngắn đều được), *"…"* là trích dẫn hoặc lời của người khác (ở lại trong dòng, giữ ngoặc), *hành động* là dòng nghiêng. Chỉ đổi cách hiển thị, chữ đã lưu không đổi.

## Hoạt động thế nào

- Gõ "…" để nói. Mỗi câu thoại thành một ô thoại hồng.
- Gõ *hành động* để tả việc mình làm. Dòng này hiện nghiêng.
- Gõ *"…"* khi trích lời người khác. Nó ở lại trong dòng, giữ dấu ngoặc.
- Chữ đã lưu không đổi, chỉ cách hiện thay đổi.

Kỹ thuật:

- `lib/playerBlocks.ts` chia lượt người chơi thành khối; nhận cả ngoặc ” của bàn phím điện thoại.
- `Prose.tsx` vẽ lượt người chơi căn phải kèm avatar persona.
- Placeholder nằm trong `Composer.tsx`.

## Done when

- [x] Placeholder ô nhập Story là 'Nhập lời thoại vào "…"' (vừa một dòng trên điện thoại); DM là 'Nhắn tin…'.
- [x] Gõ hai câu thoại trong một lượt thì hiện hai ô thoại, không còn dấu "".
- [x] *"…"* ở lại trong dòng dẫn truyện, chữ đứng, giữ ngoặc.
- [x] *hành động* hiện nghiêng, bỏ dấu sao; đoạn chỉ có '...' hay emoji vẫn hiện.
- [x] Ngoặc mở kiểu ” của bàn phím điện thoại cũng được nhận.
- [x] Cả lượt căn phải kèm avatar persona; `lib/playerBlocks.test.ts` qua.

## Liên quan

- **Code:** [`frontend/src/lib/playerBlocks.ts`](../../frontend/src/lib/playerBlocks.ts), [`frontend/src/lib/storyBlocks.ts`](../../frontend/src/lib/storyBlocks.ts), [`frontend/src/lib/text.ts`](../../frontend/src/lib/text.ts), [`frontend/src/components/Prose.tsx`](../../frontend/src/components/Prose.tsx), [`frontend/src/components/Composer.tsx`](../../frontend/src/components/Composer.tsx)
- **Tài liệu:** [phase3.md §10.3](../../docs/phase3.md), [design-impl.md §6.2, §15](../../docs/design-impl.md)
- **Quyết định:** [the-thoai-khong-ngoac](../decisions/the-thoai-khong-ngoac.md), [trich-dan-trong-dau-sao](../decisions/trich-dan-trong-dau-sao.md), [placeholder-ngan](../decisions/placeholder-ngan.md)
