# Tăng tốc: cửa sổ theo khúc và prefill

- **Trạng thái:** Đã xong · **Phase:** Phase 3b (§10.1, §10.6)
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

- [x] Prefill chỉ chạy khi hàng đợi rỗng, chỉ cho story đang chơi, và bị huỷ ngay khi người chơi gửi tin.
- [x] Phần đầu prefill trùng từng message với prompt thật của lượt sau (`test_prefill_prefix_is_exactly_the_next_prompt_head`).
- [x] Renderer gemma4 khớp token-từng-token với /api/chat (`test_render_prefix_gemma4_matches_ollama_chat_template`).
- [x] Prefill lỗi chỉ ghi log, không làm hỏng lượt chat.
- [x] Đo trên gemma4:12b: TTFT các lượt sau lượt đầu khoảng 4-5 giây, kể cả lượt cửa sổ dịch.

## Liên quan

- **Code:** [`backend/lyris/llm/render.py`](../../backend/lyris/llm/render.py), [`backend/lyris/llm/ollama.py`](../../backend/lyris/llm/ollama.py), [`backend/lyris/jobs/worker.py`](../../backend/lyris/jobs/worker.py), [`backend/lyris/state/service.py`](../../backend/lyris/state/service.py), [`backend/lyris/prompt/builder.py`](../../backend/lyris/prompt/builder.py)
- **Tài liệu:** [phase3.md §10.1, §10.6](../../docs/phase3.md)
- **Quyết định:** [cua-so-lich-su-theo-khuc](../decisions/cua-so-lich-su-theo-khuc.md), [prefill-raw](../decisions/prefill-raw.md), [cung-num-ctx](../decisions/cung-num-ctx.md)
