# F05 — Chỉ đạo ẩn ((...))

- **Trạng thái:** xem `memory/features.json` · **Phase:** Phase 1
- **Giai đoạn:** Đã có
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

- [ ] Unit: `prompt/directives.py` tách mọi `((...))` khỏi lượt người chơi (nhiều chỉ đạo, nhiều dòng, chưa đóng) và bỏ qua emoticon.
- [ ] Unit: chỉ đạo vào ghi chú cuối (khối F), không nằm trong lời người chơi gửi model; không còn '((' ở đâu trong prompt, kể cả từ card.
- [ ] Unit: checker `directive_leak` của harness bắt được câu trả lời có '(('.
- [ ] Bot: ô nhập Story có aria-label 'Lượt của bạn: lời nói, *hành động* hoặc ((chỉ đạo cho AI))'; gửi `Chào. ((cho nhân vật đang ghen nhưng không nói ra))` thì lượt người chơi hiện chỉ đạo thành chip nhỏ (title 'Chỉ đạo cho AI (không hiện trong truyện)') và '((' không hiện trong dòng truyện.
- [ ] Model thật: trên gemma4:12b, câu trả lời không chứa '((', không chép lại 5 chữ liền nhau nào của câu chỉ đạo, không có chữ 'chỉ đạo', và khi chỉ đạo bảo ghen mà không nói ra thì nhân vật không nói thẳng chữ 'ghen' trong lời thoại (harness kịch bản `f05-chi-dao`).

## Tests

- backend/tests/test_prompt.py::test_directives_go_to_f_not_history_and_no_double_parens_anywhere
- backend/tests/test_prompt.py::test_extract_directives_multiple_and_multiline
- backend/tests/test_prompt.py::test_extract_directives_ignores_emoticons
- backend/tests/test_prompt.py::test_extract_directives_unclosed_is_directive
- backend/tests/test_prompt.py::test_no_double_parens_even_from_card_or_unclosed_input
- backend/tests/test_api.py::test_directive_handling
- backend/tests/test_harness_checks.py::test_directive_leak
- frontend/src/lib/text.test.ts
- bot: chỉ đạo ((...)) hiện thành chip
- model: f05-chi-dao

## Ngoài Done when

Không chặn ✅ — kiểm bằng tay (chủ dự án đồng ý 2026-11-14, [raw](../raw/2026-11-14-po-quyet-harness.md)).

- Câu trả lời **làm theo** chỉ đạo và **giữ giọng** nhân vật: chỉ người đọc (hoặc judge, cột 'Bám sát' của `run_eval.py` có judge, kịch bản `04-chi-dao`) chấm được; `verify.sh --real-model` chạy `--no-judge`. Phần máy chấm được là dòng Model thật ở trên (`f05-chi-dao`). Xem [kich-ban-model-that](../decisions/kich-ban-model-that.md).

## Liên quan

- **Code:** [`backend/lyris/prompt/directives.py`](../../backend/lyris/prompt/directives.py), [`backend/lyris/prompt/builder.py`](../../backend/lyris/prompt/builder.py), [`harness/checks.py`](../../harness/checks.py), [`frontend/src/components/Prose.tsx`](../../frontend/src/components/Prose.tsx)
- **Tài liệu:** [plan.md §1, §7, §9](../../docs/plan.md)
- **Quyết định:** [nguoi-choi-la-tac-gia](../decisions/nguoi-choi-la-tac-gia.md)
