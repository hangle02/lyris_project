# Sheet "Tài khoản"

- **Đường dẫn:** mở từ avatar trên header của ba tab chính (`#/`, `#/explore`, `#/studio`). `?open=system` mở sẵn sheet, `?open=about` mở sẵn trang "Giới thiệu". · **File:** `frontend/src/components/shell/AccountSheet.tsx`

## Dùng để làm gì

Mọi thứ về tài khoản ở một chỗ: profile, mật khẩu, persona cho story mới, đăng xuất. Mọi thứ kỹ thuật (máy, model, bộ nhớ, công cụ nâng cao) gập trong "Nâng cao", màn chính không có chữ kỹ thuật.

## Có gì trên màn hình

Ở điện thoại 390px là sheet trượt từ đáy, tiêu đề "Tài khoản". Từ trên xuống:

1. **Khối tài khoản**: avatar lớn, tên hiển thị, @handle, nút **"Xem profile"** (mở [trang profile](profile.md)).
2. Nút **"Đổi mật khẩu"**. Chủ máy có thêm **"Quản lý tài khoản"** (mở [trang quản lý](admin.md)).
3. **"Persona cho story mới"**: dòng "Persona là vai bạn đóng trong story. Story mới sẽ dùng persona này; đổi được ở từng story khi tạo." rồi danh sách persona dạng radio (avatar, tên, giới tính, mô tả). Chạm để đổi, lưu ngay. Nút **"Quản lý persona"** mở [trang persona](personas.md).
4. **Một câu về máy** (chỉ khi có trục trặc), ví dụ "Lyris chưa kết nối được phần trả lời trên máy này, nên nhân vật tạm thời chưa trả lời được."
5. **"Nâng cao"** (gập sẵn):
   - Chủ máy: phần **"Máy MacBook M2"** với nhãn trạng thái, Bộ nhớ hợp nhất, Model đang nạp, Model chat mặc định (đổi được), KV cache, Flash Attention, Lượt sinh song song, Model nạp cùng lúc, Phiên bản Ollama, Ký ức. Dòng "Cập nhật lúc …, tự làm mới mỗi 10 giây."
   - Mọi người: phần **"Công cụ"** với công tắc **"Công cụ nâng cao"** ("Hiện xem trước prompt, ước lượng token và thời gian sinh trong Studio.").
6. **"Đăng xuất"** và **"Đăng xuất mọi thiết bị"**.
7. Link nhỏ **"Giới thiệu & bản quyền ảnh"**.

**Trang con trong sheet** (có nút "‹ Tài khoản" để quay lại):

- **"Đổi mật khẩu"**: "Đổi xong, mọi thiết bị khác đang đăng nhập sẽ phải đăng nhập lại." Ô Mật khẩu hiện tại, mật khẩu mới, nhập lại, nút "Lưu mật khẩu". Xong thì quay về màn chính với dòng "Đã đổi mật khẩu. Các thiết bị khác đã được đăng xuất."
- **"Giới thiệu & bản quyền ảnh"**: wordmark, câu "Lyris chạy hoàn toàn trên chiếc Mac này: nhân vật, story và ký ức của bạn không rời khỏi máy." và danh sách ghi nguồn ảnh của nhân vật mẫu.

Từ 640px: hộp thoại giữa màn hình, cỡ vừa.

## Trạng thái

- **Đang tải:** khung xương avatar và persona.
- **Máy không trả lời:** một câu dễ hiểu ở màn chính. Avatar trên header có chấm đỏ.
- **Lỗi tải tài khoản / persona:** câu lỗi + "Thử lại".
- **Chưa có persona:** "Chưa có persona nào. Tạo một persona để bước vào story." + "Tạo persona".
- **Đang đổi persona:** vòng quay nhỏ trên hàng vừa chọn.
- **Xác nhận đăng xuất mọi thiết bị:** "Mọi điện thoại và máy tính đang đăng nhập @handle sẽ phải đăng nhập lại, kể cả máy này." + "Giữ nguyên" / "Đăng xuất mọi thiết bị".
- **Thành viên (không phải chủ máy):** không có "Quản lý tài khoản". "Nâng cao" chỉ có phần "Công cụ".

## Tính năng

- [Tài khoản và profile](../features/F28-tai-khoan-profile.md)
- [Persona](../features/F21-persona.md)
- [Đăng nhập](../features/F29-dang-nhap.md)
- [Ẩn chữ kỹ thuật](../features/F27-an-chu-ky-thuat.md)

Chi tiết: [accounts.md §5](../../docs/accounts.md), [auth.md](../../docs/auth.md), [design-impl.md §6.6 và §13](../../docs/design-impl.md).
