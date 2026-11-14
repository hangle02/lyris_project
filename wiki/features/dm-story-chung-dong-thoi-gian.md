# Story và DM chung một dòng thời gian

- **Trạng thái:** Một phần · **Phase:** Phase 3b (§10.8)
- **Màn hình:** [chat-story](../screens/chat-story.md), [chat-dm](../screens/chat-dm.md)

## Là gì

Nhân vật nhớ cả điều đã nói qua tin nhắn khi quay lại Story. Ở Story, mỗi lượt DM trong lịch sử được gắn nhãn '[Tin nhắn điện thoại]' và khối F có một dòng nhắc. Code và test đã xong; doc ghi chưa thử trên model thật.

Còn thiếu: chưa thử trên model thật (docs/phase3.md §10.8 ghi sẽ thử cùng đợt kiểm tra Phase 4).

## Hoạt động thế nào

- Người chơi nhắn với nhân vật ở DM, rồi chuyển sang Story.
- Nhân vật ở Story vẫn biết những gì vừa nói qua tin nhắn, và hiểu đó là tin nhắn điện thoại, không phải gặp mặt.

Kỹ thuật:

- Ở Story, builder gắn nhãn '[Tin nhắn điện thoại]' trước mỗi lượt DM trong lịch sử, và thêm một dòng nhắc ở khối F.
- Story không có lượt DM thì prompt không đổi (golden test).
- Tóm tắt (`memory/summarize.py`) cũng ghi nhãn này cho lượt DM.

## Done when

- [x] Ở Story Mode, prompt gắn '[Tin nhắn điện thoại]' trước mỗi lượt DM; ở DM Mode không gắn.
- [x] Story không có lượt DM nào thì prompt giữ nguyên từng byte như trước (golden test).
- [x] Tóm tắt ghi 'Tên [Tin nhắn điện thoại]: ...' cho lượt DM.
- [x] `backend/tests/test_dm_continuity.py` qua.
- [ ] Thử tay trên gemma4:12b: nhân vật xưng tên qua DM, sang Story thì Thought không còn nói 'chưa nói tên với ai'.

## Liên quan

- **Code:** [`backend/lyris/prompt/builder.py`](../../backend/lyris/prompt/builder.py), [`backend/lyris/prompt/templates/vi.py`](../../backend/lyris/prompt/templates/vi.py), [`backend/lyris/prompt/templates/en.py`](../../backend/lyris/prompt/templates/en.py), [`backend/lyris/memory/summarize.py`](../../backend/lyris/memory/summarize.py)
- **Tài liệu:** [phase3.md §10.8](../../docs/phase3.md)
- **Quyết định:** [story-dm-chung-dong-thoi-gian](../decisions/story-dm-chung-dong-thoi-gian.md)
