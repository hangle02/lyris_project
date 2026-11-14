# Tuỳ chọn không đọc suy nghĩ của nhân vật

- **Ngày:** 2026-11-13 · **Ai quyết:** người dùng

## Bối cảnh

Người dùng muốn thêm lựa chọn không đọc suy nghĩ.

## Lựa chọn

Công tắc "Đọc suy nghĩ của nhân vật" (stories.show_thoughts, lưu trên server theo story) ở sheet "Bước vào câu chuyện", Thiết lập story và menu "Suy nghĩ" trên header. Tắt thì thẻ suy nghĩ không có trong DOM. Model vẫn viết Thought, worker vẫn đọc để chấm cảm xúc. Prompt không đổi.

## Vì sao

Theo yêu cầu người dùng. Lưu theo story trên server để iPhone và Mac giống nhau.

## Đã cân nhắc

Chỉ làm mờ ("Luôn hiện suy nghĩ" lưu theo thiết bị); tắt hẳn Thought trong prompt.

## Nguồn

- Lời người dùng, 2026-11-13 15:32 (xem [raw/](../raw/))
- [docs/phase4.md](../../docs/phase4.md) §12
