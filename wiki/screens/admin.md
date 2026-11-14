# Quản lý tài khoản

- **Đường dẫn:** `#/admin`, chỉ chủ máy. Thành viên mở đường dẫn này thì bị chuyển về [Tương tác](hub.md). · **File:** `frontend/src/pages/admin/AdminPage.tsx`

## Dùng để làm gì

Chủ máy mời người khác vào Lyris bằng mã mời, và quản lý thành viên: đặt lại mật khẩu, tạm khoá, mở khoá. Chủ máy không đọc được story của thành viên ở đây.

## Có gì trên màn hình

Ở điện thoại 390px, từ trên xuống. Không có thanh tab nổi.

1. **Header phụ**: "Về Tương tác", tiêu đề "Quản lý tài khoản".
2. **Mục "Mã mời"**, nút **"Tạo mã mời"**, rồi danh sách mã. Mỗi mã có ghi chú, nhãn trạng thái ("Còn hiệu lực", "Đã dùng bởi @handle", "Hết hạn", "Đã huỷ") và nút **"Huỷ"** (hỏi lại trước khi huỷ).
3. **Mục "Thành viên"** kèm số đếm. Mỗi hàng: avatar, tên, @handle, nhãn **"Chủ máy"** / **"Tạm khoá"** / **"Chờ đổi mật khẩu"**, dòng "Vào lần cuối …" (hoặc "Chưa đăng nhập lần nào") và số thiết bị đang đăng nhập.
4. **Nút "…"** trên mỗi hàng thành viên: mở một sheet có **"Đặt lại mật khẩu"** và **"Tạm khoá"** (hoặc **"Mở khoá"** nếu đang khoá).

**Hộp "Tạo mã mời"**: "Người nhận nhập mã này ở trang tạo tài khoản." Ô "Ghi chú" (ví dụ "cho Mai", chỉ bạn thấy), "Hết hạn sau" 1 / 7 / 30 ngày (mặc định 7 ngày), nút "Huỷ" / "Tạo mã".

Từ 640px: các hộp thành hộp thoại giữa màn hình.

## Trạng thái

- **Đang tải:** khung xương.
- **Chưa có mã:** "Chưa có mã mời nào. Tạo một mã để mời người khác vào Lyris này."
- **Chỉ có chủ máy:** "Chưa có ai khác. Tạo mã mời ở trên để mời người khác."
- **Mã vừa tạo** ("Mã mời mới"): mã chỉ hiện một lần và dùng được một lần. Nút "Sao chép mã", "Sao chép liên kết" (đổi thành "Đã sao chép" trong hai giây). Sao chép lỗi thì hiện liên kết để chọn tay. Mở bằng địa chỉ máy (localhost) thì nhắc mở Lyris bằng địa chỉ Wi-Fi của Mac trước khi gửi liên kết.
- **Mật khẩu tạm vừa tạo** (sau "Đặt lại"): hộp "Mật khẩu tạm" có nút "Sao chép". Thành viên sẽ phải [đổi mật khẩu](force-password.md) lần đăng nhập sau.
- **Xác nhận tạm khoá:** hộp "Tạm khoá @handle" hỏi lại.
- **Lỗi:** câu lỗi + "Chi tiết" + "Thử lại".
- **Thành viên mở trang:** chuyển về Tương tác, trang không bao giờ tải.

## Tính năng

- [Quản lý tài khoản](../features/F30-quan-ly-tai-khoan.md)

Chi tiết: [auth.md](../../docs/auth.md) (mã mời, đặt lại mật khẩu, khoá tài khoản).
