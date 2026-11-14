# Hộp "Người khác thấy gì"

- **Đường dẫn:** hộp thoại trong [trình sửa nhân vật](card-editor.md) (`#/studio/<id>`), nút "Người khác thấy gì" cạnh công tắc "Công khai" · **File:** `frontend/src/pages/character/PublicPreview.tsx`

## Dùng để làm gì

Cho chủ nhân vật xem đúng bản công khai mà tài khoản khác nhìn thấy, để yên tâm là bí mật không lộ ra. Nút chỉ hiện khi nhân vật đã được lưu ở chế độ công khai.

## Có gì trên màn hình

Ở điện thoại 390px là sheet trượt từ đáy. Từ trên xuống:

1. **Tiêu đề "Người khác thấy gì"** và dòng "Hồ sơ này là tất cả những gì tài khoản khác xem được. Họ không sửa được nhân vật."
2. **Đầu hồ sơ**: ảnh 4:5 nhỏ bên trái; tên (serif nghiêng), vai trò, "bởi @handle", tag bên phải.
3. **Lời nói đặc trưng**: các thẻ trích dẫn.
4. **Phần giới thiệu** công khai, cùng kiểu với tab "Giới thiệu" của [hồ sơ nhân vật](character-profile.md) nhưng chỉ còn những phần được chia sẻ (như Đôi nét, Ngoại hình, Bối cảnh).

Không có tính cách, hoàn cảnh, mục tiêu, bí mật hay sổ thế giới: server không bao giờ gửi những phần này cho tài khoản khác.

Từ 640px: hộp thoại giữa màn hình, ảnh to hơn.

## Trạng thái

- **Đang tải:** khung xương ảnh và chữ.
- **Chưa có giới thiệu:** "Chưa có giới thiệu nào để người khác đọc."
- **Lỗi:** câu lỗi + "Chi tiết" + "Thử lại".

## Tính năng

- [Nhân vật công khai](../features/F31-nhan-vat-cong-khai.md)

Chi tiết: [auth.md §7.3](../../docs/auth.md).
