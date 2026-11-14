# Quản lý persona

- **Đường dẫn:** `#/personas` · **File:** `frontend/src/pages/PersonasPage.tsx`

## Dùng để làm gì

Thêm, sửa, xoá persona. Persona là vai bạn đóng trong story, khác với tài khoản của bạn. Card nhân vật gọi bạn là `{{user}}`; khi tạo story, chỗ đó được thay bằng tên persona bạn chọn.

Persona mặc định (persona story mới sẽ dùng) được chọn trong [sheet Tài khoản](account-sheet.md), mục "Persona cho story mới". Trang này chỉ đánh dấu nó bằng nhãn "Mặc định".

## Có gì trên màn hình

Ở điện thoại 390px, từ trên xuống. Không có thanh tab nổi.

1. **Header phụ**: "Về trang chính", tiêu đề "Persona", dòng phụ "Nhân vật của bạn trong truyện", nút "Studio".
2. **Đoạn giới thiệu** persona là gì, và nút **"Thêm persona"**.
3. **Form persona** (khi thêm mới hoặc sửa, mở ngay trong trang): avatar (chọn, đổi, xoá ảnh), Tên, Giới tính, Mô tả ("Ngắn gọn: tuổi, thân phận, vài nét tính cách. Nhân vật đọc phần này để hiểu bạn là ai."). Nút "Huỷ" và "Thêm persona" / "Lưu".
4. **Thông báo** sau khi lưu hay xoá (khung xanh, đóng được).
5. **Thẻ persona**, mỗi thẻ: avatar, tên, giới tính và số story, nhãn **"Mặc định"** nếu có, ba dòng mô tả (hoặc "Chưa có mô tả."), nút sửa và nút xoá.

Từ 640px: phần mô tả của thẻ thẳng hàng với tên, lệch sang phải avatar.

## Trạng thái

- **Đang tải:** khung xương.
- **Rỗng:** "Chưa có persona nào. Thêm một persona để bắt đầu story với bất kỳ nhân vật nào."
- **Đang lưu:** nút đổi thành "Đang lưu…".
- **Lỗi nhập:** "Tên persona không được để trống.", "Tên persona dài quá … ký tự.", "Mô tả dài quá 20.000 ký tự."
- **Lỗi tải:** "Không tải được danh sách persona: …".
- **Lưu được nhưng ảnh lỗi:** "Đã thêm “…”, nhưng chưa tải được ảnh: …".
- **Xoá:** hộp "Xoá persona" hỏi lại. Nếu đang có story dùng persona: "Đang có N story dùng mục này. Bạn sẽ được hỏi lại trước khi xoá các story đó." và lựa chọn "Xoá luôn các story". Xoá xong báo "Đã xoá “…” và N story."

## Tính năng

- [Persona](../features/F21-persona.md)

Chi tiết: [design-impl.md §13](../../docs/design-impl.md), [accounts.md](../../docs/accounts.md).
