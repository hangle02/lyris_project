# Thẻ thoại không hiện dấu ngoặc ngoài cùng

- **Ngày:** 2026-11-13 · **Ai quyết:** người dùng

## Bối cảnh

DESIGN.md nói lời thoại nằm trong ngoặc kép. Người dùng thấy thẻ thoại vẫn còn dấu "".

## Lựa chọn

Thẻ thoại ở Story (của nhân vật và người chơi) bỏ cặp ngoặc ngoài cùng khi hiển thị (speechText trong lib/storyBlocks.ts). Chữ đã lưu giữ nguyên ngoặc.

## Vì sao

Khung thẻ đã đánh dấu đó là lời nói. Khác DESIGN.md có chủ đích.

## Đã cân nhắc

Giữ ngoặc như DESIGN.md.

## Nguồn

- Lời người dùng, 2026-11-13 10:35 (xem [raw/](../raw/))
- [docs/design-impl.md](../../docs/design-impl.md) §6.2
