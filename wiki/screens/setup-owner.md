# Thiết lập chủ máy

- **Đường dẫn:** hiện ở mọi đường dẫn khi máy chưa có mật khẩu chủ máy (server trả `setup_required`) · **File:** `frontend/src/pages/auth/SetupPage.tsx`

## Dùng để làm gì

Lần đầu bật đăng nhập, chủ máy đặt mật khẩu cho tài khoản của mình. Để chứng minh mình là chủ máy, họ nhập mã thiết lập mà Lyris in ra cửa sổ Terminal trên Mac.

## Có gì trên màn hình

Ở điện thoại 390px, cùng khung với [Đăng nhập](login.md). Từ trên xuống:

1. **Wordmark** và câu khẩu hiệu.
2. **Tiêu đề "Đặt mật khẩu cho chủ máy"** và câu: "Lyris giờ có đăng nhập. Nhập mã thiết lập in trong cửa sổ Terminal đang chạy Lyris trên Mac, rồi chọn mật khẩu cho tài khoản của bạn."
3. **"Mã thiết lập"** (placeholder "XXXX-XXXX-XXXX").
4. **"Tên hiển thị"** và **"Tên đăng nhập"**: chỉ hiện khi cơ sở dữ liệu mới tinh, chưa có tài khoản nào.
5. **"Mật khẩu mới"** và **"Nhập lại mật khẩu"**.
6. **Nút "Lưu và vào Lyris"**.

Từ 640px: cột rộng tối đa 400px, nằm giữa màn hình.

## Trạng thái

- **Mã trống:** "Hãy nhập mã thiết lập."
- **Mã sai dạng:** "Mã thiết lập gồm 12 ký tự, ví dụ 7KQ2-M9XD-4TPA."
- **Mã sai** (server báo): câu lỗi dưới ô mã.
- **Thử sai nhiều lần (429):** "Bạn đã thử sai nhiều lần. Hãy đợi 15 phút rồi thử lại."
- **Mật khẩu không hợp lệ:** câu lỗi dưới ô mật khẩu.
- **Xong:** vào app như chủ máy.

## Tính năng

- [Đăng nhập](../features/F29-dang-nhap.md)

Chi tiết: [auth.md](../../docs/auth.md) (thiết lập lần đầu và mã in ra Terminal).
