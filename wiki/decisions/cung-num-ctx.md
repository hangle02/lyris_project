# Mọi lời gọi model chat dùng cùng num_ctx 8192

- **Ngày:** 2026-11-13 · **Ai quyết:** đo đạc

## Bối cảnh

Model hỗ trợ tới 256K token, nhưng máy chỉ 24GB. Ollama nạp lại model khi num_ctx khác.

## Lựa chọn

App chạy ở 8192 token. Mọi lời gọi tới model chat (chat, trích xuất, tóm tắt, gợi ý, prefill) dùng đúng num_ctx của PromptBudget.

## Vì sao

Đổi num_ctx làm Ollama nạp lại model, mất 10-20 giây. 8192 giữ RAM và tốc độ.

## Đã cân nhắc

Context lớn hơn; num_ctx riêng cho việc nền.

## Nguồn

- [docs/phase3.md](../../docs/phase3.md) §0
- [docs/plan.md](../../docs/plan.md) §3, §4
