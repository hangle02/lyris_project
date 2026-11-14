# F12 — Story và DM chung một dòng thời gian

- **Trạng thái:** xem `memory/features.json` · **Phase:** Phase 3b (§10.8)
- **Giai đoạn:** Đã có
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

- [ ] Unit: ở Story Mode, prompt gắn '[Tin nhắn điện thoại]' trước mỗi lượt DM và giải thích trong khối F; ở DM Mode không gắn.
- [ ] Unit: story không có lượt DM nào thì system message giữ nguyên từng byte như trước.
- [ ] Unit: tóm tắt ghi 'Tên [Tin nhắn điện thoại]: ...' cho lượt DM; cửa sổ đánh dấu giống nhau ở cả hai mode.
- [ ] Model thật: trên gemma4:12b, nhân vật xưng tên qua DM, sang Story thì Thought (và cả câu trả lời) không còn nói 'chưa nói tên với ai' hay 'sao cô ấy biết tên mình' (kịch bản `f12-dm-xung-ten`).

## Tests

- backend/tests/test_dm_continuity.py
- model: f12-dm-xung-ten

## Liên quan

- **Code:** [`backend/lyris/prompt/builder.py`](../../backend/lyris/prompt/builder.py), [`backend/lyris/prompt/templates/vi.py`](../../backend/lyris/prompt/templates/vi.py), [`backend/lyris/prompt/templates/en.py`](../../backend/lyris/prompt/templates/en.py), [`backend/lyris/memory/summarize.py`](../../backend/lyris/memory/summarize.py)
- **Tài liệu:** [phase3.md §10.8](../../docs/phase3.md)
- **Quyết định:** [story-dm-chung-dong-thoi-gian](../decisions/story-dm-chung-dong-thoi-gian.md)
