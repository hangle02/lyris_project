# Chống lặp câu

- **Trạng thái:** Một phần · **Phase:** Phase 3
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

- [x] Ghi chú F liệt kê tối đa 3 câu cần tránh của lượt gần đây.
- [x] Ở DM, câu cuối của tin trước (tối đa 90 ký tự) có trong danh sách tránh.
- [x] Ở Story, 9 chữ đầu của lượt trước có trong danh sách tránh.
- [x] `backend/tests/test_repetition.py` qua.
- [ ] Chat thử 10 lượt DM: không còn lượt nào cũng kết bằng cùng một lời dặn.

## Liên quan

- **Code:** [`backend/lyris/prompt/repetition.py`](../../backend/lyris/prompt/repetition.py), [`backend/lyris/prompt/builder.py`](../../backend/lyris/prompt/builder.py)
- **Tài liệu:** [phase3.md §10.1](../../docs/phase3.md)
