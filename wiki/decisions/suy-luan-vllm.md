# Suy luận bằng vLLM trên GPU riêng, định tuyến dính theo story

- **Ngày:** 2026-11-14 · **Ai quyết:** PO chốt hướng (2A: GPU riêng, model mở, vLLM); AI chọn chi tiết (tạm chọn)

## Bối cảnh

Ollama trên một máy phục vụ ~2 lượt cùng lúc và chỉ giữ cache prompt của một story (docs/deploy.md §9, docs/phase3.md §10.6).
4A cần vài trăm người chat cùng lúc.

## Lựa chọn

- vLLM, đúng trọng số `gemma4:12b` (safetensors), **FP8**, `--max-model-len 8192` (một context như
  [cung-num-ctx](cung-num-ctx.md)), `--enable-prefix-caching`, `--scheduling-policy priority`.
- Lyris tự dựng prompt (`llm/render.py`) và gọi `/v1/completions`, để prefill và prompt thật trùng từng byte.
- Gateway định tuyến **dính theo story** bằng rendezvous hashing; quá tải thì tràn sang replica ít tải nhất.
- Giữ ý tưởng [prefill-raw](prefill-raw.md): sau job trích xuất, gửi trước phần đầu prompt lượt kế tới đúng replica.
- Việc nền vẫn dùng model chat ([viec-nen-dung-model-chat](viec-nen-dung-model-chat.md)) nhưng ưu tiên thấp.
- AWQ 4-bit chỉ khi buộc dùng GPU nhỏ và qua bộ chấm `harness/run_eval.py` (mốc so là GGUF của Ollama đang chạy).
- LoRA tự train (F41) phục vụ bằng `--enable-lora`, A/B gán theo story (khoá cache gồm adapter); kiểm giấy phép trọng số.
- **Giữ giọng văn khi đổi Ollama → vLLM** (sửa sau phản biện, [docs/server.md §8.1–8.2, §21](../../docs/server.md)):
  gửi **token id** (không BOS đôi); bảng tham số lấy mẫu cố định giống hồ sơ Ollama, `--generation-config vllm`;
  `repetition_penalty` khác công thức nên để 1,0 trừ khi eval cần; tắt suy nghĩ nằm trong `render.py`, không qua chat
  template; tên tham số structured output theo bản vLLM đã ghim; `max_tokens = min(reply, 8192 − token prompt thật)`.
- Bật bộ quản lý KV lai (lớp cửa sổ trượt của Gemma); ngân sách KV mỗi replica phải thoả phương trình ở §8.3.
- Trích xuất dùng chung phần đầu prompt của story (tạm chọn), chỉ khi kịch bản `f10-ky-uc` không kém.
- Chấm model thật của bản vLLM (eval, bài tải 300 người) chạy ở GPU staging, là cổng G4, không nằm trong `verify.sh`.

## Vì sao

Prefix caching của vLLM giữ cache của **mọi** story còn chỗ, khối luật đầu system dùng chung cho mọi người; continuous
batching phục vụ hàng chục lượt mỗi GPU. Định tuyến dính giữ cache của một story ở một chỗ.

## Đã cân nhắc

Nhiều máy Ollama sau load balancer (mỗi máy vẫn một cache, ít lượt song song); SGLang (cache radix tốt, nhưng đội đã quen
API kiểu OpenAI của vLLM; có thể thử khi đo); router ngoài (vLLM production-stack, llm-d) — xem lại khi > 8 replica; API
của nhà cung cấp lớn (PO không chọn).

## Nguồn

- [raw/2026-11-14-server-lon-appstore-tra-loi.md](../raw/2026-11-14-server-lon-appstore-tra-loi.md)
- [docs/server.md §8, §15](../../docs/server.md)
