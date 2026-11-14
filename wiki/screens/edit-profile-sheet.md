# Sheet "Sửa profile"

- **Đường dẫn:** trên [trang profile](profile.md) của bạn, nút "Sửa profile" (hoặc `#/me?open=profile`). Cũng mở từ khối "Đặt tên cho tài khoản của bạn" trên [Tương tác](hub.md). · **File:** `frontend/src/pages/profile/EditProfileSheet.tsx`

## Dùng để làm gì

Đổi tên hiển thị, @handle, lời giới thiệu, ảnh đại diện và ảnh bìa của tài khoản. Đây là bạn bên ngoài story; persona mới là vai bạn đóng trong story.

## Có gì trên màn hình

Ở điện thoại 390px là sheet trượt từ đáy. Từ trên xuống:

1. **Tiêu đề "Sửa profile"**. Lần đầu (tài khoản chưa đặt profile) thì là "Đặt tên cho tài khoản", kèm dòng "Tên và @handle là của bạn bên ngoài story. Persona vẫn là vai bạn đóng trong story."
2. **Ảnh bìa** xem trước, avatar đè lên. Hai nhóm nút **"Ảnh đại diện"** và **"Ảnh bìa"**: "Chọn ảnh" / "Đổi ảnh" và "Xoá". Dòng nhỏ: "Ảnh lưu ngay khi chọn. Ảnh bìa nên là ảnh ngang, tỉ lệ 3:1."
3. **"Tên hiển thị"**: "Hiện trên profile và trên nhân vật bạn tạo."
4. **"Handle"**: kiểm tra ngay khi gõ. Gợi ý quy tắc: độ dài cho phép, chữ a-z, số, dấu gạch dưới và dấu chấm (không ở đầu hay cuối). Gõ đúng thì: "Lyris sẽ kiểm tra @… còn trống khi bạn lưu."
5. **"Giới thiệu"**: "Vài dòng về bạn, hiện trên profile."
6. **Chân sheet**: "Huỷ" và "Lưu".

Từ 640px: hộp thoại giữa màn hình, cỡ vừa.

## Trạng thái

- **Handle sai quy tắc:** báo ngay dưới ô.
- **Handle đã có người dùng:** server trả 422, câu lỗi hiện dưới ô Handle (không hiện trên đầu form).
- **Đang tải ảnh:** vòng quay trên ảnh bìa hoặc avatar. Nút "Lưu" khoá cho tới khi xong.
- **Đang lưu:** nút "Lưu" quay, sheet không đóng được.
- **Lỗi tải tài khoản:** câu lỗi + "Thử lại".
- **Lỗi chung:** khung lỗi trên form, đóng được.

## Tính năng

- [Tài khoản và profile](../features/tai-khoan-profile.md)

Chi tiết: [accounts.md §5](../../docs/accounts.md).
