# F36 — Harness: bake-off và chấm hành vi model

- **Trạng thái:** xem `memory/features.json` · **Phase:** Phase 0, 1, 2
- **Giai đoạn:** Đã có
- **Màn hình:** Không có màn hình riêng (chạy nền hoặc ngoài app).

## Là gì

`harness/bakeoff.py` so sánh model ứng viên; `harness/run_eval.py` chạy các kịch bản YAML trong `harness/scenarios/` và kiểm tra godmodding (có LLM judge), format Thought, rò chỉ đạo, ngôn ngữ, xưng hô, tốc độ. Từ 2026-11-14, mỗi dòng "Model thật" của wiki có kịch bản riêng (`f05-…` tới `f36-…`), gồm cả các loại không phải một lượt trả lời: trích xuất cảm xúc/ký ức, tóm tắt, gợi ý, viết nháp, nhiều lượt DM, đo TTFT qua app thật, bake-off, chạy lồng run_eval (`harness/kinds.py`).

Còn thiếu: chế độ so sánh base với bản fine-tune (`run_eval.py` hiện chỉ nhận một `--model`).

## Hoạt động thế nào

- Đây là công cụ cho người làm app, không có trong giao diện.
- Bake-off so sánh các model ứng viên trên cùng câu hỏi.
- Eval chạy 8 kịch bản gốc (mở đầu, bẫy im lặng, hành động cho AI, chỉ đạo, DM, Việt hiện đại, cổ trang, tiếng Anh) và các kịch bản chứng minh dòng "Model thật" của từng tính năng, rồi chấm bằng luật máy (và judge nếu bật).

Kỹ thuật:

- `harness/checks.py` kiểm tra format Thought, rò chỉ đạo, ngôn ngữ, xưng hô, độ dài.
- Godmodding được chấm thêm bằng LLM judge.
- Kịch bản là YAML trong `harness/scenarios/` (khoá `kind`: reply, extract, summarize, suggest, draft, dm_session, app_ttft, bakeoff, nested_eval); card thử ở `harness/cards/`. Cách viết: [harness/README.md](../../harness/README.md).

## Done when

- [ ] Unit: `harness/checks.py` (chỉ thư viện chuẩn) bắt được: lộ '((', số Thought sai, Thought liền nhau hay chưa đóng, xưng hô cấm, sai ngôn ngữ, viết thay người chơi.
- [ ] Unit: `run_eval.py` chạy hết kịch bản với Ollama giả và lưu báo cáo; kịch bản hỏng bị từ chối; bake-off dùng chung bộ check.
- [ ] Unit: mỗi luật máy của các loại kịch bản model thật (trích xuất, tóm tắt, gợi ý, viết nháp, nhiều lượt DM, TTFT qua app thật, bake-off, chạy lồng) báo lỗi với kết quả sai và không báo với kết quả đúng (Ollama giả); lượt chạy lồng và bake-off không in dòng "Đã ghi kết quả vào" mà `verify.sh` đọc.
- [ ] Model thật: `backend/.venv/bin/python harness/bakeoff.py` chạy trên Ollama thật và in bảng so sánh model có TTFT, tok/s của từng model, không câu nào lỗi (kịch bản `f36-bakeoff`: chạy đúng `main()` của lệnh đó với `--models gemma4:12b --limit 2`, 2 câu đầu của prompts.json).
- [ ] Model thật: `backend/.venv/bin/python harness/run_eval.py --model gemma4:12b` chạy trọn trên Ollama thật và lưu `report.md` + `raw.json` vào `harness/results/` (kịch bản `f36-chay-long`: chạy lồng run_eval trên ba kịch bản khác loại, đủ kết quả, không lỗi sinh).

## Tests

- backend/tests/test_harness_checks.py
- backend/tests/test_run_eval_kinds.py
- model: f36-bakeoff
- model: f36-chay-long

## Ngoài Done when

Không chặn ✅ (cần thử tay, dịch vụ thật, hoặc còn là kế hoạch).

- Đã có kịch bản mục thế giới có từ khoá và mục 'Chỉ bạn biết' (`f17-the-gioi`). Kế hoạch còn lại: kịch bản *không* có từ khoá thế giới ([phase4.md §14.4](../../docs/phase4.md)).
- Kế hoạch (Phase 5): chạy `--models base,lyris-vN` đặt hai model cạnh nhau. Khi làm thì thêm dòng Done when mới.
- Chạy tay cả bộ `backend/.venv/bin/python harness/run_eval.py --model gemma4:12b --no-judge` (kiểm bằng tay, chủ dự án đồng ý
  2026-11-14, [raw](../raw/2026-11-14-po-quyet-harness.md)): cả bộ mất khoảng 25–40 phút, quá giới hạn của một lượt verify khi chạy
  cùng tính năng khác; trong verify chỉ chạy lồng ba kịch bản (`f36-chay-long`). Lần chạy tay 2026-11-14: 22/22 kịch bản chạy hết,
  báo cáo ở `harness/results/eval-20261114-154122/`; 20/22 không lỗi máy lần đầu, `04-chi-dao` (Thought liền nhau) và `f10-ky-uc`
  (thiếu fact của nhân vật) đỏ một lần, chạy lại 3/3 xanh.

## Liên quan

- **Code:** [`harness/bakeoff.py`](../../harness/bakeoff.py), [`harness/run_eval.py`](../../harness/run_eval.py), [`harness/kinds.py`](../../harness/kinds.py), [`harness/checks.py`](../../harness/checks.py), [`harness/scenarios/`](../../harness/scenarios/), [`harness/cards/`](../../harness/cards/)
- **Tài liệu:** [plan.md §9](../../docs/plan.md), [phase4.md §14.4](../../docs/phase4.md)
- **Quyết định:** [chon-gemma4-12b](../decisions/chon-gemma4-12b.md), [kich-ban-model-that](../decisions/kich-ban-model-that.md), [nguong-ttft-f14](../decisions/nguong-ttft-f14.md)
