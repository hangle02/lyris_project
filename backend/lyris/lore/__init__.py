"""Sổ thế giới (lorebook) theo nhân vật, Phase 4 (docs/phase4.md).

- `normalize`: dạng so khớp (giữ dấu, chuẩn hoá vị trí dấu thanh), hàm thuần.
- `parse`: đọc `world.md` thành các mục, hàm thuần.
- `match`: so khớp từ khoá trên văn bản, hàm thuần.
- `select`: chọn mục cho prompt của một lượt (ngân sách, ai biết), hàm thuần.
- `book`: Character Card V2 `character_book` <-> mục thế giới, hàm thuần.
- `service`: `LoreService` (DB, nhập file, prompt, danh sách đã mở khoá).
"""
