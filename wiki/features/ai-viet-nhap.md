# AI viết nháp nhân vật

- **Trạng thái:** Đã xong · **Phase:** Phase 2
- **Màn hình:** [studio-list](../screens/studio-list.md), [card-editor](../screens/card-editor.md)

## Là gì

Gõ một dòng ý tưởng, AI viết ra một card đầy đủ (chưa lưu) để người dùng sửa rồi lưu. AI đề xuất style profile nhưng người dùng xác nhận.

## Hoạt động thế nào

- Ở Studio, bấm 'AI viết nháp' và gõ một dòng ý tưởng.
- AI viết ra một nhân vật đầy đủ và mở trình sửa. Nhân vật chưa được lưu.
- Người dùng đọc, sửa, chọn lại văn phong nếu cần, rồi mới lưu.

Kỹ thuật:

- `studio/draft.py` gọi model chat và đọc kết quả thành card.
- API ở `api/routes_studio.py`; hộp nhập ở `DraftDialog.tsx`.

## Done when

- [x] Bấm 'AI viết nháp' ở Studio mở hộp nhập một dòng ý tưởng.
- [x] Xong thì mở trình sửa với card đã điền (tên, vai trò, tính cách, lời mở đầu...), chưa lưu.
- [x] Lỗi hiện câu dễ hiểu kèm 'Chi tiết', không nhắc 'model' hay 'Ollama'.
- [x] `backend/tests/test_draft.py` qua.

## Liên quan

- **Code:** [`backend/lyris/studio/draft.py`](../../backend/lyris/studio/draft.py), [`frontend/src/pages/studio/DraftDialog.tsx`](../../frontend/src/pages/studio/DraftDialog.tsx), [`backend/lyris/api/routes_studio.py`](../../backend/lyris/api/routes_studio.py)
- **Tài liệu:** [phase2.md](../../docs/phase2.md)
- **Quyết định:** [van-phong-theo-boi-canh](../decisions/van-phong-theo-boi-canh.md)
