# Tạo tài khoản

- **Đường dẫn:** `#/signup`, hoặc `#/signup?code=LYR-…` (mã mời điền sẵn) · **File:** `frontend/src/pages/auth/SignupPage.tsx`

## Dùng để làm gì

Người được mời tạo tài khoản mới bằng mã mời do chủ máy tạo ở [Quản lý tài khoản](admin.md). Không có mã thì không tạo được tài khoản.

## Có gì trên màn hình

Ở điện thoại 390px, cùng khung với [Đăng nhập](login.md): một cột ở giữa, nút theme ở góc. Từ trên xuống:

1. **Wordmark** và câu khẩu hiệu.
2. **Tiêu đề "Tạo tài khoản"** và câu về quyền riêng tư: "Lyris chạy trên máy của chủ máy. Story của bạn là riêng tư: tài khoản khác, kể cả chủ máy, không xem được trong app. Nhưng dữ liệu nằm trên máy đó."
3. **"Mã mời"** (placeholder "LYR-XXXX-XXXX-XXXX").
4. **"Tên hiển thị"** (ví dụ "Mai").
5. **"Tên đăng nhập"** (placeholder "@handle"), gợi ý quy tắc độ dài và ký tự: chữ a-z, số, _ và dấu chấm.
6. **"Mật khẩu"** ("Ít nhất 8 ký tự.") và **"Nhập lại mật khẩu"**, có nút Hiện/Ẩn.
7. **Nút "Tạo tài khoản"** rộng hết cột.
   - *Ngay trên nút:* ô đánh dấu đồng ý Điều khoản và Chính sách (bắt buộc, [F35](../features/F35-quyen-rieng-tu-va-bao-cao.md)).
     *Kế hoạch ([F48](../features/F48-noi-dung-an-toan.md)):* câu đồng ý thêm "và xác nhận tôi đã đủ 16 tuổi" (Lyris dành cho
     người 16+). **Không có ô năm sinh / ngày sinh** (PO chốt 2026-11-15).
8. **"Đã có tài khoản? Đăng nhập"**.

Từ 640px: cột rộng tối đa 400px, nằm giữa màn hình.

## Trạng thái

- **Mã sai dạng:** "Mã mời gồm 12 ký tự, ví dụ LYR-7KQ2-M9XD-4TPA." dưới ô.
- **Mã sai hoặc hết hạn** (server báo): câu lỗi dưới ô "Mã mời".
- **Handle trùng hoặc sai quy tắc:** câu lỗi dưới ô "Tên đăng nhập".
- **Mật khẩu yếu:** "Mật khẩu cần ít nhất 8 ký tự.", "Mật khẩu không được giống tên đăng nhập.", "Hai mật khẩu chưa giống nhau."
- **Lỗi chung:** khung lỗi dưới nút.
- **Xong:** đăng nhập luôn và vào [Tương tác](hub.md) còn trống.

## Tính năng

- [Đăng nhập](../features/F29-dang-nhap.md)
- [Nút Nội dung an toàn và xác nhận 18+](../features/F48-noi-dung-an-toan.md) (kế hoạch: câu đồng ý 16+)

Chi tiết: [auth.md §7.3 và §7.4](../../docs/auth.md).
