# Không dùng sqlite-vec; tìm ký ức lai, embedding không bắt buộc

- **Ngày:** 2026-11-13 · **Ai quyết:** thiết kế

## Bối cảnh

plan.md định dùng sqlite-vec cho ký ức dài hạn.

## Lựa chọn

Lưu vector float32 dạng BLOB, tính cosine bằng Python. Tìm theo từ khoá bằng FTS5 giữ dấu (remove_diacritics 0). bge-m3 không bắt buộc: có thì tìm lai (vector + từ khoá), không thì chỉ từ khoá. App không tự pull model; embed dùng keep_alive 1m.

## Vì sao

Mỗi story chỉ vài trăm ký ức nên Python đủ nhanh, và tránh cài extension native. Không giữ thêm model trong RAM.

## Đã cân nhắc

sqlite-vec; luôn bắt buộc bge-m3.

## Nguồn

- [docs/phase3.md](../../docs/phase3.md) §0, §1, §9
