# Tự train nghĩa là LoRA trên model mở, không train từ đầu

- **Ngày:** 2026-11-12 · **Ai quyết:** thiết kế

## Bối cảnh

Yêu cầu đầu tiên: "i want to train the model by my self and deploy on this macbook". Máy chỉ có 24GB.

## Lựa chọn

Dùng một base model mở, fine-tune bằng LoRA (mlx-lm), fuse rồi chuyển GGUF để Ollama chạy. Dữ liệu: synthetic tiếng Việt + tiếng Anh + dataset public, rồi chat thật đã đánh giá của người dùng.

## Vì sao

LoRA với vài nghìn ví dụ dạy được format và gu (tag Thought, không godmodding, xưng hô). Nó không làm model thông minh hơn base, và đó là mục tiêu đúng cho dự án này.

## Đã cân nhắc

Train model từ đầu (không khả thi trên một máy 24GB).

## Nguồn

- Lời người dùng, 2026-11-12 04:04 (xem [raw/](../raw/))
- [docs/plan.md](../../docs/plan.md) §1, §8
