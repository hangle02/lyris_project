# F53 — Cổng suy luận vLLM trên GPU riêng

- **Trạng thái:** xem `memory/features.json` · **Phase:** Máy chủ (sau khi nộp bài)
- **Giai đoạn:** Kế hoạch
- **Màn hình:** Chat (`#/chat/{id}`): không đổi; bận vẫn là ba chấm và "Lyris đang bận…", không chữ kỹ thuật.

## Là gì

Model mở (`gemma4:12b`, sau này LoRA tự train) chạy trên máy chủ GPU riêng bằng vLLM để phục vụ nhiều người cùng lúc
(PO 2A). `VllmClient` thoả `LLMClient` có sẵn; gateway định tuyến mỗi story về cùng một replica để trúng prefix cache.
Thiết kế: [docs/server.md §8, §15](../../docs/server.md).

## Hoạt động thế nào

- `vllm serve … --max-model-len 8192 --enable-prefix-caching --kv-cache-dtype fp8 --scheduling-policy priority`.
  Context 8192 cho mọi lời gọi, như [cung-num-ctx](../decisions/cung-num-ctx.md).
- Lyris tự dựng prompt (`llm/render.py`) và gọi `/v1/completions`, để phần đầu gửi trước (prefill) và prompt thật trùng
  từng byte. `VllmClient` tự tokenize và gửi **danh sách token id** (không BOS đôi: `render.py` đã có `<bos>`).
- Giữ giọng văn: bảng tham số lấy mẫu cố định giống hồ sơ Ollama đang dùng, `--generation-config vllm` (không lấy mặc
  định của `generation_config.json`); `repetition_penalty` 1,0 trừ khi eval cần. Tắt suy nghĩ nằm trong `render.py`.
- `max_tokens = min(reply_tokens, 8192 − số token prompt thật)`; không bao giờ để vLLM trả 400 vì vượt 8192.
- Structured output dùng đúng tên tham số của bản vLLM đã ghim.
- Định tuyến dính theo story bằng rendezvous hashing; replica quá tải thì tràn sang replica ít tải nhất.
- Ưu tiên: chat 0, gợi ý 1, viết nháp/chat thử 2, trích xuất/tóm tắt 5, prefill 9.
- Ước lượng chờ > 120 s → báo bận ngay, nhả giữ chỗ coin.
- Sức chứa mỗi replica (`chat_capacity`) lấy từ bài tải 300 người chơi ảo, không đoán.
- `harness/run_eval.py` thêm `--backend vllm --base-url …` để chạy cùng kịch bản trên vLLM ở GPU staging.
- Trích xuất dùng chung phần đầu prompt của story (tạm chọn), chỉ bật khi kịch bản `f10-ky-uc` không kém bản cũ.

## Done when

- [ ] Unit: `VllmClient.chat_stream` trên server vLLM giả (giao thức `/v1/completions` stream) trả các `TextDelta` rồi `Done` có `GenStats` (ttft, số token) (`test_vllm_client_stream_and_stats`).
- [ ] Unit: prompt gửi vLLM bằng đúng `render_prefix(…)` của lượt trước cộng lượt người chơi mới, khớp từng byte (`test_vllm_prompt_equals_render_prefix_plus_turn`).
- [ ] Unit: request gửi vLLM có `prompt` là danh sách token id, chỉ có đúng 1 token BOS ở đầu; đường dự phòng gửi chuỗi có `add_special_tokens: false`; token id của prefill là tiền tố của token id lượt thật (`test_vllm_no_double_bos`).
- [ ] Unit: request chat gửi vLLM có đủ `temperature`, `top_p`, `top_k`, `min_p`, `max_tokens`, `stop` đúng bằng bảng hồ sơ Ollama trong code, `repetition_penalty` = 1,0; request trích xuất/gợi ý dùng hồ sơ của chúng (`test_vllm_sampling_params_match_ollama_profile`).
- [ ] Unit: mọi lời gọi (chat, `chat_json`, prefill) có `số token prompt + max_tokens` ≤ 8192 tính bằng token thật (prompt 8.000 token → `max_tokens` ≤ 192; còn < 64 token chỗ → builder cắt thêm lịch sử) và không gửi tham số context nào khác (`test_vllm_single_context_8192`).
- [ ] Unit: `chat_json` gửi tham số structured output theo đúng tên của bản vLLM đã ghim trong cấu hình; server giả trả JSON hỏng lần đầu → thử lại đúng 1 lần (`test_vllm_structured_output_param`).
- [ ] Unit: 10.000 story trên 3 replica, thêm replica thứ 4 → ≤ 30 % story đổi replica; replica có `num_requests_waiting` > 4 → story tràn sang replica ít tải nhất (`test_gateway_sticky_hrw_and_spill`).
- [ ] Unit: request gửi vLLM có `priority` 0/1/2/5/9 theo loại (chat, gợi ý, nháp, trích xuất, prefill) (`test_vllm_priorities`).
- [ ] Unit: ước lượng chờ > 120 s → stream trả `error` với câu "Lyris đang bận…" trước `start`, giữ chỗ coin nhả, số dư không đổi (`test_backpressure_rejects_when_wait_over_120s`).
- [ ] Unit: `harness/run_eval.py --backend vllm --base-url http://127.0.0.1:<cổng> --no-judge` chạy được kịch bản `07-co-trang` trên server vLLM giả và ghi kết quả cùng định dạng như khi chạy Ollama (`test_run_eval_backend_vllm_flag`).
- [ ] Bot: backend của bot dùng `VllmClient` trỏ server vLLM giả; gửi lượt ở `#/chat/{id}` thấy câu trả lời; màn chat không có chữ `vLLM`, `GPU`, `token`.

## Tests

- `backend/tests/test_vllm_client.py::test_vllm_client_stream_and_stats`
- `backend/tests/test_vllm_client.py::test_vllm_prompt_equals_render_prefix_plus_turn`
- `backend/tests/test_vllm_client.py::test_vllm_no_double_bos`
- `backend/tests/test_vllm_client.py::test_vllm_sampling_params_match_ollama_profile`
- `backend/tests/test_vllm_client.py::test_vllm_single_context_8192`
- `backend/tests/test_vllm_client.py::test_vllm_structured_output_param`
- `backend/tests/test_gateway.py::test_gateway_sticky_hrw_and_spill`
- `backend/tests/test_gateway.py::test_vllm_priorities`
- `backend/tests/test_gateway.py::test_backpressure_rejects_when_wait_over_120s`
- `backend/tests/test_run_eval_backend.py::test_run_eval_backend_vllm_flag`
- bot: chat qua cổng vLLM giả

## Ngoài Done when

Không chặn ✅ (cổng G4 ở GPU staging, [docs/server.md §18](../../docs/server.md); không chạy được bằng `verify.sh` vì
`verify.sh --real-model` chạy trên máy Mac với Ollama, không có vLLM hay GPU staging):

- `harness/run_eval.py --backend vllm --base-url …` trên GPU staging cho điểm ≥ Ollama (GGUF đang chạy) ở mọi kịch bản,
  nhất là `07-co-trang`, `f10-ky-uc`, `f14-ttft`; báo cáo ghi rõ "FP8 trên vLLM so với GGUF trên Ollama".
- Bài tải `harness/load/chatters.py` 300 người chơi ảo: TTFT p95 ≤ 4 s, TTFT lượt thường p50 ≤ 1,5 s, tốc độ p05 ≥ 12
  token/s, trúng prefix cache ≥ 70 % (lượt chat) và ≥ 60 % (prompt trích xuất nếu bật dùng chung phần đầu), phương trình
  ngân sách KV ở [docs/server.md §8.3](../../docs/server.md) thoả. Kịch bản `f14-ttft` hiện có không đo được tải hay tỉ lệ
  trúng cache, nên không dùng làm bằng chứng cho dòng này.
- Chọn GPU và ký hợp đồng chỉ sau bài tải; kiểm chất lượng FP8 so bf16 bằng đọc 50 câu trả lời mẫu; kiểm giấy phép
  trọng số gemma4 cho dịch vụ thương mại và fine-tune.

## Liên quan

- **Tài liệu:** [docs/server.md §8, §15](../../docs/server.md), [docs/phase3.md §10.6](../../docs/phase3.md)
- **Code hiện tại:** [`llm/base.py`](../../backend/lyris/llm/base.py), [`llm/ollama.py`](../../backend/lyris/llm/ollama.py), [`llm/render.py`](../../backend/lyris/llm/render.py), [`jobs/worker.py`](../../backend/lyris/jobs/worker.py)
- **Quyết định:** [suy-luan-vllm](../decisions/suy-luan-vllm.md), [prefill-raw](../decisions/prefill-raw.md), [chon-gemma4-12b](../decisions/chon-gemma4-12b.md)
