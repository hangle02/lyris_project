# Hồ sơ nhân vật

- **Đường dẫn:** `#/character/<id>`, `#/character/template/<slug>` (nhân vật mẫu chưa cài). Thêm `?start=1` thì mở sẵn sheet [Bước vào câu chuyện](start-story-sheet.md). · **File:** `frontend/src/pages/character/CharacterPage.tsx`

## Dùng để làm gì

Xem nhân vật trước khi bắt đầu story. Trang chỉ đọc, ai cũng xem được nếu được phép. Muốn sửa thì vào Studio.

## Có gì trên màn hình

Ở điện thoại 390px, từ trên xuống:

1. **Header phụ**: nút "Về Khám phá" và tiêu đề "Nhân vật". Không có thanh tab nổi.
2. **Ảnh lớn** tỉ lệ 4:5. Nhân vật chưa có ảnh: một dải chữ cái thấp (2:1) để tên không bị đẩy xuống quá sâu.
3. **Tên** (serif nghiêng, to), **vai trò** (chữ vàng), **tác giả**: "Mẫu của Lyris" hoặc "bởi @handle". Nhân vật của người khác thì "bởi @handle" là link tới [profile](profile.md) của họ.
4. **Tag** dạng chip (gồm cả vibe của nhân vật mẫu).
5. **"Sửa nhân vật"**: chỉ hiện với nhân vật của chính bạn (không phải mẫu, không phải của người khác). Mở [trình sửa](card-editor.md).
6. **"Lời nói đặc trưng"**: mỗi câu là một thẻ trích dẫn rộng hết cột.
7. **Hai tab**:
   - **"Giới thiệu"**: Đôi nét, Tính cách, Ngoại hình, Hoàn cảnh, Điều mong muốn, Bối cảnh (bỏ phần trống, không bao giờ hiện bí mật). Cuối tab là phần **"Thế giới"**: có bao nhiêu mục, tên những người và nơi chốn ai cũng biết. Không hiện nội dung mục.
   - **"Thiết lập"**: Xưng hô (Tự xưng, Gọi bạn là, Tên gọi thân mật, Với người khác), Giọng kể (Văn phong, Ngôn ngữ, Giới tính, Dẫn truyện gọi nhân vật là, Cách nói), và 6 thanh "Cảm xúc ban đầu".
8. **"Story của bạn với <tên>"**: các story bạn đã có với nhân vật này, chạm để mở chat.
9. **Thanh dính đáy**: "Tiếp tục story" (khi đã có story) và "Bước vào câu chuyện".

Từ 768px: hai cột. Ảnh 340px dính bên trái khi cuộn. Nút "Bước vào câu chuyện" và "Tiếp tục story" nằm ngay dưới tag, thanh dính đáy biến mất.

## Trạng thái

- **Đang tải:** khung xương ảnh, tên, tag.
- **Không tìm thấy:** "Không tìm thấy nhân vật này. Có thể nhân vật đã bị xoá." + nút "Về Khám phá".
- **Lỗi khác:** InlineAlert có câu dễ hiểu, "Chi tiết" và "Thử lại".
- **Nhân vật công khai của người khác:** không có "Sửa nhân vật". Sheet bắt đầu story có thêm dòng nhắc về bản sao.
- **Bản sao** (mở từ chat của một story dùng nhân vật người khác): không bắt đầu story mới được, chỉ còn "Tiếp tục story".
- **Nhân vật mẫu đã cài:** tự chuyển sang `#/character/<id>` của card đã cài.

## Tính năng

- [Hồ sơ nhân vật](../features/F23-ho-so-nhan-vat.md)
- [Bước vào câu chuyện](../features/F24-buoc-vao-cau-chuyen.md)
- [Sổ thế giới](../features/F17-so-the-gioi.md) (phần "Thế giới")
- [Ma trận cảm xúc](../features/F09-ma-tran-cam-xuc.md) (cảm xúc ban đầu)
- [Nhân vật công khai](../features/F31-nhan-vat-cong-khai.md)

Chi tiết: [design-impl.md §16](../../docs/design-impl.md), [phase4.md §10](../../docs/phase4.md) (phần Thế giới), [auth.md §7.3](../../docs/auth.md).
