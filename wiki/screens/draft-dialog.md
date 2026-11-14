# Hộp "AI viết nháp"

- **Đường dẫn:** hộp thoại trên [Studio](studio-list.md) (`#/studio`), nút "AI viết nháp" · **File:** `frontend/src/pages/studio/DraftDialog.tsx`

## Dùng để làm gì

Gõ một hai câu ý tưởng, AI viết thành một card nhân vật đầy đủ. Bản nháp chưa lưu: nó mở trong [trình sửa](card-editor.md) để bạn duyệt và sửa rồi mới bấm Lưu.

## Có gì trên màn hình

Ở điện thoại 390px là sheet trượt từ đáy. Từ trên xuống:

1. **Tiêu đề "AI viết nháp nhân vật"** và dòng "Một hai câu ý tưởng thành một card đầy đủ. Bản nháp chưa lưu cho tới khi bạn duyệt."
2. **Ô "Ý tưởng"**, gợi ý: "Thân phận, tính cách, quan hệ với {{user}} (nhân vật của bạn), bối cảnh."
3. **"Hoặc bắt đầu từ một ví dụ:"** và vài nút ví dụ (như "Sư tỷ Thanh Vân Tông", "Kiến trúc sư ở Sài Gòn", "Night-shift librarian"). Chạm để điền vào ô ý tưởng.
4. **"Ngôn ngữ của card"** (Tiếng Việt / English) và **"Giới tính"** (có lựa chọn "AI chọn").
5. **"Bộ văn phong"**: "Để AI chọn" hoặc một bộ văn phong cụ thể.
6. Dòng nhỏ "Ctrl/⌘ + Enter để bắt đầu."
7. **Chân hộp**: "Đóng" và "Viết nháp". "Viết nháp" chỉ bật khi đã có ý tưởng và ý tưởng không quá dài.

Từ 640px: hộp thoại giữa màn hình, cỡ vừa.

## Trạng thái

- **Đang viết:** thân hộp đổi thành "Đang viết nháp · <thời gian đã chờ>" kèm vòng quay, dòng "Thường mất 1-2 phút. Bạn sẽ duyệt và sửa trong form trước khi lưu." và ý tưởng bạn vừa gõ. Chân hộp chỉ còn nút "Huỷ viết nháp".
- **Lỗi:** khung lỗi trên form, câu dễ hiểu + "Chi tiết". Ý tưởng vẫn còn để thử lại.
- **Xong:** hộp đóng, trình sửa mở với bản nháp. Header ghi "Bản nháp AI · chưa lưu". Một khung nhắc duyệt giới tính, xưng hô và bộ văn phong rồi bấm Lưu, kèm "Lưu ý từ bản nháp:" nếu AI có lưu ý.

## Tính năng

- [AI viết nháp](../features/ai-viet-nhap.md)

Chi tiết: [phase2.md](../../docs/phase2.md).
