# Làm app trước với gemma4:12b gốc, fine-tune sau

- **Ngày:** 2026-11-12 · **Ai quyết:** người dùng + đo đạc

## Bối cảnh

Người dùng muốn tự train model. Lần train thử LoRA trên 12B dùng hết 24GB RAM, swap 5GB, chỉ 2-3 tok/s (khoảng 1 phút mỗi vòng).

## Lựa chọn

Hoãn fine-tune sang Phase 5. Làm app với gemma4:12b gốc. App lưu mọi prompt, câu trả lời, đánh giá và bản sửa để train sau. Trạng thái: fine-tune Chưa làm.

## Vì sao

Train không vừa RAM. Người dùng nói: "tạm thời cứ dùng model cũ đi đã, tạo app trước, mình sẽ trainning và fine-tune sau".

## Đã cân nhắc

Khi quay lại: đóng hết app + 8 lớp LoRA + --max-seq-length 1024; nâng giới hạn RAM GPU (sysctl iogpu.wired_limit_mb); hoặc train trên gemma4:e4b.

## Nguồn

- Lời người dùng, 2026-11-12 04:45, 08:25 (xem [raw/](../raw/))
- [docs/plan.md](../../docs/plan.md) Phase 0 (Kết quả thực tế)
