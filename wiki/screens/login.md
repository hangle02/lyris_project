# Đăng nhập

- **Đường dẫn:** `#/login`. Chưa đăng nhập mà mở đường dẫn khác thì app nhớ đường dẫn đó, chuyển về đây, đăng nhập xong quay lại. · **File:** `frontend/src/pages/auth/LoginPage.tsx` (khung chung: `AuthLayout.tsx`)

## Dùng để làm gì

Đăng nhập bằng @handle và mật khẩu. Đã đăng nhập mà mở `#/login` thì app chuyển về Tương tác.

## Có gì trên màn hình

Ở điện thoại 390px, một cột ở giữa, lề hai bên 20px. Nút đổi theme ở góc trên phải. Từ trên xuống:

1. **Wordmark Lyris** và câu "Nơi những tâm hồn trang sách bước ra sưởi ấm thực tại".
2. **Tiêu đề "Đăng nhập"**.
3. **Ô "Tên đăng nhập"** (placeholder "@handle").
4. **Ô "Mật khẩu"** với nút "Hiện" / "Ẩn" ở cuối ô.
5. **Nút "Đăng nhập"** rộng hết cột.
6. **"Có mã mời? Tạo tài khoản"** (link tới [Tạo tài khoản](signup.md)).
7. **"Quên mật khẩu? Hãy nhờ chủ máy đặt lại."**

Từ 640px: cột vẫn rộng tối đa 400px, nằm giữa màn hình.

## Trạng thái

- **Bỏ trống ô:** "Hãy nhập tên đăng nhập." / "Hãy nhập mật khẩu." dưới ô.
- **Sai tên hoặc mật khẩu:** câu lỗi của server dưới nút đăng nhập, kèm "Chi tiết" khi có.
- **Thử sai nhiều lần (429):** "Bạn đã thử sai nhiều lần. Hãy đợi 15 phút rồi thử lại."
- **Bị đăng xuất giữa chừng:** khung thông tin "Bạn đã bị đăng xuất. Hãy đăng nhập lại." trên form.
- **Máy bận hoặc không trả lời (502/503/504):** một câu dễ hiểu về kết nối, không có mã lỗi.
- **Đang gửi:** nút quay, các ô khoá.

## Tính năng

- [Đăng nhập](../features/F29-dang-nhap.md)

Chi tiết: [auth.md §7.3 và §7.4](../../docs/auth.md).
