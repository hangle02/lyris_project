# Đổi mật khẩu bắt buộc

- **Đường dẫn:** hiện ở mọi đường dẫn khi tài khoản đang ở trạng thái `must_change_password` · **File:** `frontend/src/pages/auth/ForcePasswordPage.tsx` (form: `ChangePasswordForm.tsx`)

## Dùng để làm gì

Sau khi chủ máy đặt lại mật khẩu cho một thành viên, thành viên đăng nhập bằng mật khẩu tạm và phải chọn mật khẩu mới ngay. Chưa đổi thì server từ chối mọi việc khác (403).

## Có gì trên màn hình

Ở điện thoại 390px, cùng khung với [Đăng nhập](login.md). Từ trên xuống:

1. **Wordmark** và câu khẩu hiệu.
2. **Tiêu đề "Đặt mật khẩu mới"** và câu: "Mật khẩu của bạn vừa được đặt lại. Hãy chọn mật khẩu mới để tiếp tục."
3. **"Mật khẩu tạm"**, **"Mật khẩu mới"**, **"Nhập lại mật khẩu"**, có nút Hiện/Ẩn.
4. **Nút "Lưu mật khẩu"**.
5. **Nút "Đăng xuất"**: rời đi mà không đổi.

Từ 640px: cột rộng tối đa 400px, nằm giữa màn hình.

## Trạng thái

- **Sai mật khẩu tạm:** câu lỗi của server.
- **Mật khẩu mới không hợp lệ:** "Mật khẩu cần ít nhất 8 ký tự.", "Mật khẩu mới phải khác mật khẩu cũ.", "Hai mật khẩu chưa giống nhau."...
- **Lỗi đăng xuất:** câu lỗi dưới nút.
- **Xong:** vào app như bình thường.

## Tính năng

- [Đăng nhập](../features/F29-dang-nhap.md)
- [Quản lý tài khoản](../features/F30-quan-ly-tai-khoan.md) (chủ máy đặt lại mật khẩu)

Chi tiết: [auth.md](../../docs/auth.md).
