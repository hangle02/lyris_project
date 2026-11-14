# Màn chờ mở app

- **Đường dẫn:** hiện trước mọi đường dẫn, trong lúc app hỏi `/api/auth/me` xem bạn đã đăng nhập chưa · **File:** `frontend/src/pages/auth/AuthSplash.tsx`

## Dùng để làm gì

Che khoảng chờ ngắn lúc mở app, trước khi biết nên hiện [Đăng nhập](login.md), [Thiết lập chủ máy](setup-owner.md), [Đổi mật khẩu bắt buộc](force-password.md) hay vào thẳng app.

## Có gì trên màn hình

Ở mọi cỡ màn hình: nền của theme và wordmark Lyris ở giữa (không chạy hiệu ứng). Không có vòng quay nhấp nháy. Trình đọc màn hình nghe "Đang mở Lyris…".

## Trạng thái

- **Đang chờ:** chỉ có wordmark.
- **Backend không trả lời:** dưới wordmark có một câu thường (không có mã lỗi) và nút "Thử lại".

## Tính năng

- [Đăng nhập](../features/F29-dang-nhap.md)

Chi tiết: [auth.md §7.3](../../docs/auth.md).
