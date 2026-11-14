# Trang profile

- **Đường dẫn:** `#/me` (của bạn), `#/u/<handle>` (của người khác). `?tab=characters` hoặc `?tab=personas` mở sẵn tab. · **File:** `frontend/src/pages/profile/ProfilePage.tsx` (ảnh bìa: `ProfileBanner.tsx`)

## Dùng để làm gì

Trang của một tài khoản: ảnh bìa, avatar, tên, @handle, lời giới thiệu. Với trang của bạn có thêm số liệu, nhân vật và persona. Với trang người khác chỉ có nhân vật họ chia sẻ.

## Có gì trên màn hình

Ở điện thoại 390px, từ trên xuống. Không có thanh tab nổi.

1. **Header phụ**: "Về Tương tác", tiêu đề "Profile" (trang của bạn có dòng phụ "Tài khoản của bạn").
2. **Ảnh bìa** tỉ lệ 3:1, avatar lớn đè lên mép dưới.
3. **Tên hiển thị**, **@handle**, **lời giới thiệu**. Trang của bạn chưa có giới thiệu thì ghi "Chưa có lời giới thiệu."
4. **Nút "Sửa profile"** (chỉ trang của bạn): mở [sheet Sửa profile](edit-profile-sheet.md).
5. **Số liệu** (chỉ trang của bạn): số nhân vật, số story, số persona.
6. **Trang của bạn có hai tab**, mỗi tab kèm số đếm:
   - **"Nhân vật"**: dòng "Nhân vật bạn tạo, chỉ nằm trên máy này." rồi lưới ô nhân vật (ảnh 3:4, tên, vai trò, nhãn Riêng tư / Công khai). Chạm ô mở [hồ sơ nhân vật](character-profile.md).
   - **"Persona"**: dòng "Chỉ bạn thấy. Story mới dùng persona mặc định." + nút "Quản lý persona". Danh sách persona, persona mặc định có nhãn "Mặc định". Chạm mở [trang persona](personas.md).
7. **Trang người khác**: không có tab, chỉ một mục **"Nhân vật"** gồm các nhân vật công khai của họ. Chạm mở hồ sơ chỉ đọc.

Lưới nhân vật: 2 cột ở điện thoại, 3 cột từ 640px. Từ 640px ảnh bìa bo góc.

## Trạng thái

- **Đang tải:** khung xương ảnh bìa, đầu trang và số liệu.
- **Handle không có:** "Không có tài khoản @handle trên máy này." + nút "Về Tương tác".
- **Lỗi tải:** "Không tải được …" + "Thử lại".
- **Chưa có nhân vật** (của bạn): "Bạn chưa tạo nhân vật nào. Nhân vật bạn tạo sẽ hiện ở đây."
- **Chưa có persona:** "Chưa có persona nào. Persona là vai bạn đóng khi trò chuyện trong story."
- **Người khác chưa chia sẻ gì:** "<tên> chưa chia sẻ nhân vật nào."
- **Profile người khác:** không có nút sửa, không có số liệu, không có persona.

## Tính năng

- [Tài khoản và profile](../features/tai-khoan-profile.md)
- [Nhân vật công khai](../features/nhan-vat-cong-khai.md) (trang người khác)

Chi tiết: [accounts.md §5](../../docs/accounts.md).
