# Chế độ DM (nhắn tin)

- **Trạng thái:** Đã xong · **Phase:** Phase 2, 2b
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

- [x] Pill Story/DM trên header đổi khung ngay, story vẫn là một.
- [x] Ở DM, tin nhân vật là bong bóng có avatar; tin người chơi có chân '00:40 • Đã gửi', tin cuối đã được trả lời có '• Đã xem'.
- [x] Lượt của mode kia hiện thành một dòng nhãn gộp, không hiện nội dung.
- [x] Đang chờ trả lời: bong bóng ba chấm cạnh avatar nhân vật.
- [x] `*hành động*` trong DM hiện nghiêng, không còn dấu sao.
- [x] `lib/threadRows.test.ts` qua.

## Liên quan

- **Code:** [`frontend/src/components/DmThread.tsx`](../../frontend/src/components/DmThread.tsx), [`frontend/src/lib/threadRows.ts`](../../frontend/src/lib/threadRows.ts), [`frontend/src/pages/chat/ChatHeader.tsx`](../../frontend/src/pages/chat/ChatHeader.tsx), [`backend/lyris/prompt/templates/vi.py`](../../backend/lyris/prompt/templates/vi.py)
- **Tài liệu:** [phase2.md](../../docs/phase2.md), [design-impl.md §6.2](../../docs/design-impl.md)
- **Quyết định:** [dm-giao-dien-nhan-tin](../decisions/dm-giao-dien-nhan-tin.md), [story-dm-chung-dong-thoi-gian](../decisions/story-dm-chung-dong-thoi-gian.md)
