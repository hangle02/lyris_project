# F20 — Nhập và xuất card (Character Card V2)

- **Trạng thái:** xem `memory/features.json` · **Phase:** Phase 2
- **Giai đoạn:** Đã có
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

- [ ] Unit: nhập card V1, V2, V3 ở dạng .json và .png (chunk `chara` / `ccv3`); file hỏng hoặc quá lớn bị từ chối với câu lỗi rõ.
- [ ] Unit: xuất .json và .png; file xuất nhập lại được, ghi đúng tác giả và giữ `extensions.lyris` (vai trò, lời nói đặc trưng…).
- [ ] Unit: book của Card V2 được đổi thành mục thế giới khi lưu.
- [ ] Bot: ở `#/studio` có nút 'Nhập card'; chọn một file `.json` Character Card V2 thì trình sửa mở với tên của card đó, chưa lưu.

## Tests

- backend/tests/test_card_v2.py
- backend/tests/test_api_studio.py::test_export_json_and_png
- backend/tests/test_api_studio.py::test_import_json_roundtrip
- backend/tests/test_api_studio.py::test_import_v1_card
- backend/tests/test_api_studio.py::test_import_rejects_garbage
- backend/tests/test_api_studio.py::test_import_png_holds_avatar_until_saved
- backend/tests/test_integration_phase2.py::test_png_export_import_roundtrip_with_avatar
- backend/tests/test_integration_phase2.py::test_import_json_save_story_and_reexport_keeps_v2_data
- backend/tests/test_accounts.py::test_export_writes_creator
- backend/tests/test_lore_api.py::test_card_book_import_save_reput_export_roundtrip
- backend/tests/test_signature_lines.py::test_signature_lines_survive_export_and_import
- frontend/src/pages/studio/loreLogic.test.ts
- bot: nhập card .json mở trình sửa

## Liên quan

- **Code:** [`backend/lyris/studio/card_v2.py`](../../backend/lyris/studio/card_v2.py), [`backend/lyris/lore/book.py`](../../backend/lyris/lore/book.py), [`backend/lyris/api/routes_studio.py`](../../backend/lyris/api/routes_studio.py), [`frontend/src/pages/studio/CardListPage.tsx`](../../frontend/src/pages/studio/CardListPage.tsx)
- **Tài liệu:** [phase2.md](../../docs/phase2.md), [phase4.md §4.6](../../docs/phase4.md)
- **Quyết định:** [lore-trong-db-theo-card](../decisions/lore-trong-db-theo-card.md)
