# Phần "Thế giới" trong trình sửa

- **Đường dẫn:** một phần của [trình sửa nhân vật](card-editor.md), `#/studio/<id>?section=world` cuộn thẳng tới đây · **File:** `frontend/src/pages/studio/LorebookSection.tsx` (hộp sửa mục: `LoreEntryDialog.tsx`; hộp nhập: `LoreImportDialog.tsx`)

## Dùng để làm gì

Quản lý sổ thế giới của nhân vật: những chuyện cũ, người xung quanh và nơi chốn mà nhân vật sẽ nhớ ra khi story nhắc tới. Mỗi mục lưu thẳng lên server, không cần bấm "Lưu nhân vật".

## Có gì trên màn hình

Ở điện thoại 390px, từ trên xuống:

1. **Tiêu đề "Thế giới"** và một dòng giải thích ngắn.
2. **Khung "Card này có sẵn N mục thế giới từ file gốc."** + nút "Dùng các mục này" (chỉ khi card nhập vào còn sổ thế giới kiểu cũ trong file gốc).
3. **Nút "Thêm mục"** và **"Nhập từ file"** (nhận .md, .markdown, .txt, ví dụ `world.md`).
4. **Ô "Tìm trong thế giới"**: chỉ hiện khi có hơn 12 mục.
5. **Ba nhóm**, mỗi nhóm kèm số mục: "Chuyện và bí mật", "Người xung quanh", "Nơi chốn". Mỗi hàng có:
   - Tên mục.
   - Nhãn ai biết: **"Mọi người"**, **"Chỉ <tên>"**, **"Chỉ bạn"**, hoặc **"Người khác"**.
   - Dòng "Gợi nhớ khi nhắc: …" (tối đa 3 từ khoá). Mục chưa có từ khoá thì ghi "Chưa có từ khoá gợi nhớ" màu cảnh báo.
   - Công tắc dùng / không dùng mục. Mục tắt thì mờ đi.
   - Chạm hàng để mở hộp sửa.

**Hộp sửa mục** ("Mục thế giới" hoặc "Mục mới"): Tên mục, Loại (Chuyện và bí mật / Người / Nơi chốn), Từ khoá gợi nhớ (gõ một từ rồi Enter), Ai biết điều này (Mọi người / Chỉ <tên> / Chỉ bạn, mỗi lựa chọn có câu giải thích), Nội dung. Bật Công cụ nâng cao thì thêm Độ ưu tiên và Người biết (danh sách thô). Có nút xoá mục, hỏi lại trước khi xoá.

**Hộp "Nhập thế giới từ <tên file>"** (hoặc "Dùng các mục từ card gốc"): đọc file, cho xem trước bằng vài dòng như "Thêm 5 mục mới.", "Cập nhật 2 mục.", "Giữ nguyên 1 mục bạn đã sửa."; gập sẵn "Xem các mục" và "Xem các câu đã bỏ". Có công tắc "Xoá N mục không còn trong file" khi nhập lại file cũ. Nút "Huỷ" / "Nhập".

Từ 640px: các hộp thành hộp thoại giữa màn hình. Từ 1024px: phần này nằm trong cột form bên trái của trình sửa.

## Trạng thái

- **Card chưa lưu:** "Lưu nhân vật trước, rồi thêm thế giới cho <tên>."
- **Đang tải:** khung xương.
- **Rỗng:** "Chưa có mục nào. Thêm một mục, hoặc nhập từ file thế giới (như world.md)." + "Thêm mục" / "Nhập từ file".
- **Tìm không thấy:** "Không có mục nào khớp “…”."
- **Đang đọc file:** "Đang đọc file…" kèm vòng quay.
- **File đã nhập, không có gì mới:** "File này đã được nhập, không có gì mới." Chỉ còn nút "Đóng".
- **Nhập xong:** khung xanh "Đã nhập thế giới."
- **Lỗi tải:** "Không tải được thế giới của <tên>." + "Thử lại".
- **Lỗi đọc file:** câu lỗi + "Chi tiết", nút "Chọn file khác".
- **Đổi công tắc lỗi:** "Chưa đổi được. …" ngay dưới hàng.

## Tính năng

- [Sổ thế giới](../features/F17-so-the-gioi.md)
- [Nhập và xuất card](../features/F20-nhap-xuat-card.md) (dùng sổ thế giới từ card gốc)

Chi tiết: [phase4.md §9](../../docs/phase4.md).
