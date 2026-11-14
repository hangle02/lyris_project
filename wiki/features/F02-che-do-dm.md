# F02 — Chế độ DM (nhắn tin)

- **Trạng thái:** xem `memory/features.json` · **Phase:** Phase 2, 2b
- **Giai đoạn:** Đã có
- **Màn hình:** [chat-dm](../screens/chat-dm.md), [chat-story](../screens/chat-story.md)

## Là gì

Khung nhắn tin riêng: bong bóng, avatar thật, mốc giờ, nhiều tin ngắn liền nhau. Đổi Story ⇄ DM bằng pill trên header chat. Mỗi khung chỉ hiện tin của mode đó; lượt của mode kia gộp thành một dòng nhãn.

## Hoạt động thế nào

- Bấm pill Story/DM trên header chat để đổi khung. Cùng một story, chỉ đổi cách hiện.
- Ở DM, nhân vật nhắn nhiều tin ngắn liền nhau, như nhắn tin điện thoại.
- Lượt đã chơi ở mode kia không hiện nội dung, chỉ có một dòng nhãn gộp.

Kỹ thuật:

- Mỗi lượt lưu `mode` (story hoặc dm); template prompt DM nằm trong `prompt/templates/vi.py`.
- `lib/threadRows.ts` gộp lượt mode kia và tính chân 'Đã gửi' / 'Đã xem'.
- `DmThread.tsx` vẽ bong bóng, avatar và mốc giờ.

## Done when

- [ ] Unit: lượt gửi ở DM lưu `mode = dm` và dùng template prompt DM (vi và en).
- [ ] Unit: `lib/threadRows.ts`: mỗi khung gộp các lượt của mode kia thành một dòng nhãn và đếm số lượt bị ẩn; tin người chơi mới nhất có '• Đã gửi', thành '• Đã xem' khi đã có trả lời.
- [ ] Unit: `*hành động*` trong tin nhắn được nhận là hành động (hiện nghiêng, bỏ dấu sao).
- [ ] Bot: bấm 'DM' trong nhóm 'Chế độ hiển thị' thì ô nhập thành 'Tin nhắn cho {tên}'; gửi một tin thì có tin của bạn (`aria-label="Tin nhắn của bạn"`) và tin trả lời của nhân vật; bấm 'Story' thì về ô nhập Story và các lượt Story vẫn còn.
- [ ] Bot: ở DM, tin người chơi có chân giờ kèm 'Đã gửi' hoặc 'Đã xem'; tin nhân vật có avatar; lúc chờ trả lời có bong bóng ba chấm cạnh avatar nhân vật.
- [ ] Bot: lượt đã chơi ở Story hiện trong DM thành một dòng nhãn gộp, không hiện chữ của lượt đó.

## Tests

- backend/tests/test_api.py::test_dm_mode_reply
- backend/tests/test_prompt.py::test_vi_dm_rules
- backend/tests/test_prompt.py::test_en_dm
- frontend/src/lib/threadRows.test.ts
- frontend/src/lib/text.test.ts
- bot: chuyển sang DM rồi quay lại Story
- bot: DM có avatar, chân Đã gửi/Đã xem, bong bóng ba chấm
- bot: lượt mode kia thành một dòng nhãn

## Liên quan

- **Code:** [`frontend/src/components/DmThread.tsx`](../../frontend/src/components/DmThread.tsx), [`frontend/src/lib/threadRows.ts`](../../frontend/src/lib/threadRows.ts), [`frontend/src/pages/chat/ChatHeader.tsx`](../../frontend/src/pages/chat/ChatHeader.tsx), [`backend/lyris/prompt/templates/vi.py`](../../backend/lyris/prompt/templates/vi.py)
- **Tài liệu:** [phase2.md](../../docs/phase2.md), [design-impl.md §6.2](../../docs/design-impl.md)
- **Quyết định:** [dm-giao-dien-nhan-tin](../decisions/dm-giao-dien-nhan-tin.md), [story-dm-chung-dong-thoi-gian](../decisions/story-dm-chung-dong-thoi-gian.md)
