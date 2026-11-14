# Nhập và xuất card (Character Card V2)

- **Trạng thái:** Đã xong · **Phase:** Phase 2
- **Màn hình:** [studio-list](../screens/studio-list.md), [card-editor](../screens/card-editor.md)

## Là gì

Nhập card V1/V2 dạng .json hoặc .png từ app khác; xuất card ra .json hoặc .png, giữ tác giả và sổ thế giới.

## Hoạt động thế nào

- Ở Studio, bấm 'Nhập card' để chọn file .json hoặc .png từ app khác.
- Trong trình sửa, xuất nhân vật ra .json hoặc .png để mang đi nơi khác.
- Book đi kèm card được đổi thành mục thế giới.

Kỹ thuật:

- `studio/card_v2.py` đọc và ghi Card V1/V2, cả dạng nhúng trong ảnh PNG.
- `lore/book.py` đổi book thành mục thế giới.

## Done when

- [x] 'Nhập card' nhận file .json và .png, mở trình sửa với card đã đọc.
- [x] Xuất .json và .png từ trình sửa; file xuất nhập lại được.
- [x] Card xuất ghi đúng tác giả và giữ `extensions.lyris` (vai trò, lời nói đặc trưng...).
- [x] Book của Card V2 được đổi thành mục thế giới khi lưu hoặc khi bấm 'Dùng các mục này'.
- [x] `backend/tests/test_card_v2.py` qua.

## Liên quan

- **Code:** [`backend/lyris/studio/card_v2.py`](../../backend/lyris/studio/card_v2.py), [`backend/lyris/lore/book.py`](../../backend/lyris/lore/book.py), [`backend/lyris/api/routes_studio.py`](../../backend/lyris/api/routes_studio.py), [`frontend/src/pages/studio/CardListPage.tsx`](../../frontend/src/pages/studio/CardListPage.tsx)
- **Tài liệu:** [phase2.md](../../docs/phase2.md), [phase4.md §4.6](../../docs/phase4.md)
- **Quyết định:** [lore-trong-db-theo-card](../decisions/lore-trong-db-theo-card.md)
