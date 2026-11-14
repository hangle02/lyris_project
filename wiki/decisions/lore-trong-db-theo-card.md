# Sổ thế giới thuộc từng nhân vật, nằm trong DB

- **Ngày:** 2026-11-13 · **Ai quyết:** thiết kế

## Bối cảnh

plan.md định đồng bộ thư mục world_wiki/ (Markdown có YAML frontmatter).

## Lựa chọn

Mỗi card có sổ thế giới riêng trong DB, sửa ở Studio, nhập từ file .md hoặc character_book của Card V2. So khớp chỉ là chuỗi, không gọi model, giữ dấu, chuẩn hoá vị trí dấu thanh. Lượt nhân vật chỉ được quét bằng khoá dạng tên riêng. Giao diện không dùng chữ lore/keys/known_by.

## Vì sao

Một card thường đi kèm đúng một thế giới. Không gọi model nên lượt chat không chậm thêm.

## Đã cân nhắc

Thư mục world_wiki/ đồng bộ tự động; phạm vi global (để sau).

## Nguồn

- [docs/phase4.md](../../docs/phase4.md) §0, §5, §16
