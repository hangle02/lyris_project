# Chỉ đạo ẩn ((...))

- **Trạng thái:** Đã xong · **Phase:** Phase 1
- **Màn hình:** [chat-story](../screens/chat-story.md)

## Là gì

Người chơi là tác giả: ghi chỉ đạo trong ((...)), ví dụ ((cho Lạc Dương đang ghen nhưng không nói ra)). AI làm theo nhưng giữ giọng nhân vật và không in lại phần đó. Hiện chỉ có cú pháp trong ô nhập; plan có nhắc ô 'Chỉ đạo' riêng nhưng chưa làm.

Chưa làm: ô 'Chỉ đạo' riêng mà plan nhắc tới. Hiện chỉ có cú pháp ((...)) trong ô nhập.

## Hoạt động thế nào

- Người chơi viết chỉ đạo cho AI trong ((...)), ngay trong lượt của mình.
- Nhân vật làm theo nhưng không nhắc lại chỉ đạo, và vẫn giữ giọng của mình.
- Trong khung chat, phần ((...)) hiện thành chip nhỏ.

Kỹ thuật:

- `prompt/directives.py` tách ((...)) khỏi lời người chơi.
- Builder đưa chỉ đạo vào khối F (ghi chú cuối prompt).
- Harness kiểm tra câu trả lời không chứa '((' (`directive_leak`).

## Done when

- [x] ((...)) trong lượt người chơi được tách ra và đưa vào ghi chú cuối (khối F), không nằm trong lời người chơi gửi model.
- [x] Câu trả lời không chứa '((' (harness `directive_leak`).
- [x] Lượt người chơi hiện ((...)) thành chip nhỏ.
- [x] aria-label ô nhập Story nhắc 'lời nói, *hành động* hoặc ((chỉ đạo cho AI))'.

## Liên quan

- **Code:** [`backend/lyris/prompt/directives.py`](../../backend/lyris/prompt/directives.py), [`backend/lyris/prompt/builder.py`](../../backend/lyris/prompt/builder.py), [`harness/checks.py`](../../harness/checks.py), [`frontend/src/components/Prose.tsx`](../../frontend/src/components/Prose.tsx)
- **Tài liệu:** [plan.md §1, §7, §9](../../docs/plan.md)
- **Quyết định:** [nguoi-choi-la-tac-gia](../decisions/nguoi-choi-la-tac-gia.md)
