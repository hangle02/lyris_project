# Harness: bake-off và chấm hành vi model

- **Trạng thái:** Một phần · **Phase:** Phase 0, 1, 2
- **Màn hình:** Không có màn hình riêng (chạy nền hoặc ngoài app).

## Là gì

`harness/bakeoff.py` so sánh model ứng viên; `harness/run_eval.py` chạy 8 kịch bản YAML và kiểm tra godmodding (có LLM judge), format Thought, rò chỉ đạo, ngôn ngữ, xưng hô, tốc độ. Chưa có kịch bản sổ thế giới và chưa so sánh base với bản fine-tune.

Còn thiếu: kịch bản sổ thế giới và chế độ so sánh base với bản fine-tune (`run_eval.py` hiện chỉ nhận một `--model`).

## Hoạt động thế nào

- Đây là công cụ cho người làm app, không có trong giao diện.
- Bake-off so sánh các model ứng viên trên cùng câu hỏi.
- Eval chạy 8 kịch bản (mở đầu, bẫy im lặng, hành động cho AI, chỉ đạo, DM, Việt hiện đại, cổ trang, tiếng Anh) và chấm từng câu trả lời.

Kỹ thuật:

- `harness/checks.py` kiểm tra format Thought, rò chỉ đạo, ngôn ngữ, xưng hô, độ dài.
- Godmodding được chấm thêm bằng LLM judge.
- Kịch bản là YAML trong `harness/scenarios/`; card thử ở `harness/cards/`.

## Done when

- [x] `backend/.venv/bin/python harness/bakeoff.py` in bảng so sánh model.
- [x] `backend/.venv/bin/python harness/run_eval.py --model gemma4:12b` chạy hết kịch bản và lưu báo cáo vào harness/results/.
- [x] `test_harness_checks.py` qua.
- [ ] Có kịch bản có/không có từ khoá thế giới và kịch bản mục bị cấm (Phase 4 §14.4).
- [ ] Chạy được `--models base,lyris-vN` đặt hai model cạnh nhau.

## Liên quan

- **Code:** [`harness/bakeoff.py`](../../harness/bakeoff.py), [`harness/run_eval.py`](../../harness/run_eval.py), [`harness/checks.py`](../../harness/checks.py), [`harness/scenarios/`](../../harness/scenarios/), [`harness/cards/`](../../harness/cards/)
- **Tài liệu:** [plan.md §9](../../docs/plan.md), [phase4.md §14.4](../../docs/phase4.md)
- **Quyết định:** [chon-gemma4-12b](../decisions/chon-gemma4-12b.md)
