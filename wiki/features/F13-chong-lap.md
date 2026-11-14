# F13 — Chống lặp câu

- **Trạng thái:** xem `memory/features.json` · **Phase:** Phase 3
- **Giai đoạn:** Đã có
- **Màn hình:** Không có màn hình riêng (chạy nền hoặc ngoài app).

## Là gì

Lấy câu kết của 3 tin DM gần đây và câu mở đầu của 3 lượt Story gần đây, đưa vào ghi chú cuối (khối F) dặn model tránh. Sửa lỗi DM tin nào cũng kết bằng 'đi ngủ sớm đi'.

Còn thiếu: code và test đã xong, nhưng docs chưa ghi lần chat thử nào trên model thật để xác nhận hết lặp.

## Hoạt động thế nào

- Người chơi không thấy gì khác, chỉ thấy nhân vật bớt nói lặp.
- Trước đây ở DM, tin nào của nhân vật cũng kết bằng 'đi ngủ sớm đi'. Phần này sửa lỗi đó.

Kỹ thuật:

- `prompt/repetition.py` lấy câu kết của 3 tin DM gần đây và câu mở đầu của 3 lượt Story gần đây.
- Builder đưa các câu đó vào khối F, dặn model đừng lặp lại.

## Done when

- [ ] Unit: ghi chú F liệt kê tối đa 3 câu cần tránh của các lượt gần đây, câu trùng thì gộp; system message không đổi.
- [ ] Unit: ở DM lấy câu cuối của tin trước (tối đa 90 ký tự); ở Story lấy 9 chữ đầu của lượt trước; bỏ lời mở đầu và lượt của mode kia.
- [ ] Model thật: chat thử 10 lượt DM trên gemma4:12b: không còn lượt nào cũng kết bằng cùng một lời dặn: không câu kết nào lặp ở quá 2/10 lượt, 3 chữ cuối không trùng nhau ở quá 3/10 lượt (kịch bản `f13-dm-10-luot`).

## Tests

- backend/tests/test_repetition.py
- backend/tests/test_prompt_state.py::test_repetition_avoid_lines_kept_with_state
- model: f13-dm-10-luot

## Liên quan

- **Code:** [`backend/lyris/prompt/repetition.py`](../../backend/lyris/prompt/repetition.py), [`backend/lyris/prompt/builder.py`](../../backend/lyris/prompt/builder.py)
- **Tài liệu:** [phase3.md §10.1](../../docs/phase3.md)
