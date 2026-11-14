# F14 — Tăng tốc: cửa sổ theo khúc và prefill

- **Trạng thái:** xem `memory/features.json` · **Phase:** Phase 3b (§10.1, §10.6)
- **Giai đoạn:** Đã có
- **Màn hình:** Không có màn hình riêng (chạy nền hoặc ngoài app).

## Là gì

Cửa sổ lịch sử chỉ dịch theo khúc để phần đầu prompt đứng yên. Khi rảnh, worker gửi trước phần đầu prompt của lượt kế (prefill raw qua /api/generate) để Ollama giữ cache. Lượt thường còn khoảng 4-5 giây tới chữ đầu.

## Hoạt động thế nào

- Người chơi không thấy gì khác, chỉ thấy nhân vật trả lời nhanh hơn.
- Lượt thường còn khoảng 4-5 giây tới chữ đầu tiên trên MacBook M2.

Kỹ thuật:

- Cửa sổ lịch sử chỉ dịch theo khúc, nên phần đầu prompt đứng yên giữa các lượt và Ollama dùng lại cache.
- Khi rảnh, worker gửi trước phần đầu prompt của lượt kế qua `/api/generate` (raw, `llm/render.py` dựng đúng template gemma4).
- Người chơi gửi tin thì prefill bị huỷ ngay; prefill lỗi chỉ ghi log.

## Done when

- [ ] Unit: prefill chỉ chạy khi hàng đợi rỗng, chỉ cho story đang chơi, và bị huỷ ngay khi người chơi gửi tin.
- [ ] Unit: phần đầu prefill trùng từng message với prompt thật của lượt sau.
- [ ] Unit: renderer gemma4 khớp token-từng-token với template /api/chat của Ollama.
- [ ] Unit: prefill lỗi chỉ ghi log, không làm hỏng lượt chat.
- [ ] Unit: cửa sổ lịch sử cắt theo khúc: điểm bắt đầu chỉ dịch ở ranh giới khúc và không lùi lại.
- [ ] Model thật: đo qua app thật trên gemma4:12b (chờ việc nền và prefill xong rồi mới gửi lượt sau): TTFT các lượt sau lượt đầu khoảng 4-5 giây (trung vị ≤ 5 giây), không lượt nào quá 6 giây, kể cả lượt cửa sổ dịch; TTFT đo phía người chơi, từ lúc gửi lượt tới chữ đầu tiên qua HTTP (kịch bản `f14-ttft`; ngưỡng 6 giây tạm chọn, xem [nguong-ttft-f14](../decisions/nguong-ttft-f14.md)).

## Tests

- backend/tests/test_jobs.py::test_worker_prefills_next_prompt_head_when_idle
- backend/tests/test_jobs.py::test_prefill_only_the_story_being_played
- backend/tests/test_jobs.py::test_chat_cancels_running_prefill
- backend/tests/test_jobs.py::test_prefill_error_is_swallowed
- backend/tests/test_phase3b_e2e.py::test_prefill_prefix_is_exactly_the_next_prompt_head
- backend/tests/test_ollama_client.py::test_render_prefix_gemma4_matches_ollama_chat_template
- backend/tests/test_window_hysteresis.py
- model: f14-ttft

## Liên quan

- **Code:** [`backend/lyris/llm/render.py`](../../backend/lyris/llm/render.py), [`backend/lyris/llm/ollama.py`](../../backend/lyris/llm/ollama.py), [`backend/lyris/jobs/worker.py`](../../backend/lyris/jobs/worker.py), [`backend/lyris/state/service.py`](../../backend/lyris/state/service.py), [`backend/lyris/prompt/builder.py`](../../backend/lyris/prompt/builder.py)
- **Tài liệu:** [phase3.md §10.1, §10.6](../../docs/phase3.md)
- **Quyết định:** [cua-so-lich-su-theo-khuc](../decisions/cua-so-lich-su-theo-khuc.md), [prefill-raw](../decisions/prefill-raw.md), [cung-num-ctx](../decisions/cung-num-ctx.md)
