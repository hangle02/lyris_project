# Tên app là Lyris, thư mục vẫn là nora

- **Ngày:** 2026-11-12 · **Ai quyết:** người dùng

## Bối cảnh

Người dùng tải lên DESIGN.md (thiết kế của chính họ) và muốn đổi tên app từ Nora sang Lyris.

## Lựa chọn

Đổi tên ở mọi chỗ: package Python backend/lyris, biến môi trường `LYRIS_*` (vẫn đọc `NORA_*` cũ), file DB data/lyris.db (tự đổi tên từ nora.db), localStorage `lyris.*`, phần riêng trong card export (extensions.lyris). Thư mục repo giữ nguyên tên `nora`.

## Vì sao

Lyris là thương hiệu người dùng chọn trong DESIGN.md. Người dùng chọn không đổi tên thư mục.

## Đã cân nhắc

Đổi cả tên thư mục repo (người dùng không chọn).

## Nguồn

- Lời người dùng, 2026-11-12 15:50 (xem [raw/](../raw/))
- [docs/design-impl.md](../../docs/design-impl.md) §1
