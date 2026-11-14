# F04 — Trình bày lượt của người chơi

- **Trạng thái:** xem `memory/features.json` · **Phase:** Phase 3b, 4
- **Giai đoạn:** Đã có
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

- [ ] Unit: `lib/playerBlocks.ts`: mỗi câu trong "…" thành một ô thoại, bỏ dấu ngoặc; hai câu thoại trong một lượt thành hai ô.
- [ ] Unit: `*"…"*` ở lại trong dòng, chữ đứng, giữ ngoặc; `*hành động*` thành dòng nghiêng không dấu sao; lượt chỉ có '...' hay emoji vẫn hiện chữ.
- [ ] Unit: ngoặc mở kiểu ” của bàn phím điện thoại được nhận như ngoặc mở.
- [ ] Unit: chữ đã lưu không đổi: lượt người chơi (kể cả emoticon) được lưu nguyên văn.
- [ ] Bot: gửi lượt `"Chào cậu, hôm nay trời đẹp quá nhỉ" *mỉm cười kéo ghế ngồi xuống*` ở Story thì lượt người chơi (`aria-label="Lượt của bạn"`) có đúng 1 ô lời nói, không còn ngoặc kép ngoài, và một dòng hành động in nghiêng không còn dấu *.
- [ ] Bot: ô nhập ở Story có placeholder 'Nhập lời thoại vào "…"'; ở DM là 'Nhắn tin…'; lượt người chơi căn phải và có avatar persona.

## Tests

- frontend/src/lib/playerBlocks.test.ts
- frontend/src/lib/text.test.ts
- backend/tests/test_api.py::test_emoticons_stay_in_player_text
- bot: lượt người chơi có lời nói và hành động không bị bọc ngoặc kép ngoài
- bot: placeholder ô nhập và lượt người chơi căn phải

## Liên quan

- **Code:** [`frontend/src/lib/playerBlocks.ts`](../../frontend/src/lib/playerBlocks.ts), [`frontend/src/lib/storyBlocks.ts`](../../frontend/src/lib/storyBlocks.ts), [`frontend/src/lib/text.ts`](../../frontend/src/lib/text.ts), [`frontend/src/components/Prose.tsx`](../../frontend/src/components/Prose.tsx), [`frontend/src/components/Composer.tsx`](../../frontend/src/components/Composer.tsx)
- **Tài liệu:** [phase3.md §10.3](../../docs/phase3.md), [design-impl.md §6.2, §15](../../docs/design-impl.md)
- **Quyết định:** [the-thoai-khong-ngoac](../decisions/the-thoai-khong-ngoac.md), [trich-dan-trong-dau-sao](../decisions/trich-dan-trong-dau-sao.md), [placeholder-ngan](../decisions/placeholder-ngan.md)
