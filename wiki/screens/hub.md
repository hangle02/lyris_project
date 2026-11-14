# Tương tác (danh sách story)

- **Đường dẫn:** `#/` (cả `#/chat` không có số) · **File:** `frontend/src/pages/hub/HubPage.tsx`

## Dùng để làm gì

Màn hình mở app. Hiện mọi story của tài khoản, story có hoạt động mới nhất ở trên cùng. Chạm một story để vào chat và trò chuyện tiếp.

## Có gì trên màn hình

Ở điện thoại 390px, từ trên xuống:

1. **Header kính, dính trên cùng** (`components/shell/HubHeader.tsx`): wordmark Lyris bên trái. Bên phải là nút đổi theme và avatar tài khoản. Chạm avatar mở [sheet Tài khoản](account-sheet.md). Khi máy không trả lời được, avatar có một chấm đỏ nhỏ.
2. **Câu chào theo giờ**, chữ serif nghiêng, là tiêu đề của màn hình. Ví dụ "Tối rồi, kể nhau nghe chuyện hôm nay?". Câu đổi theo đồng hồ, mỗi phút cập nhật một lần.
3. **Khối mời đặt profile** (chỉ khi tài khoản chưa đặt profile): "Đặt tên cho tài khoản của bạn" + nút "Đặt tên". Nút mở [sheet Sửa profile](edit-profile-sheet.md). Khối tự biến mất khi đã lưu.
4. **Ô "Tìm story"** (placeholder "Tìm trong N story") và nút **"Mới"** cạnh nó. Nút mở [Khám phá](explore.md). Hai thứ này chỉ hiện khi đã có ít nhất một story.
5. **Danh sách story**, mỗi hàng gồm:
   - Avatar nhân vật dạng chân dung, có huy hiệu **Story** (hồng) hoặc **DM** (vàng).
   - Tên nhân vật và giờ (dạng "23:15" hay "Hôm qua").
   - Vai trò của nhân vật (chữ vàng), thêm tiêu đề story nếu khác tên và vai trò.
   - Dòng xem trước lời cuối, chữ nghiêng. Story chưa có lời nào: "Chưa có lời nào, story đang chờ bạn mở đầu."
   - Chip cảm xúc nổi bật (ví dụ "Thương mến 91%") và chip nơi chốn, khi story đã có dữ liệu.
6. **Thanh tab nổi** ở đáy (`components/shell/TabBar.tsx`): Khám phá, nút tròn Tương tác ở giữa, Studio.

Từ 640px: nút "Mới" đổi chữ thành "Story mới", lề rộng hơn, câu chào to hơn (32px). Thanh tab vẫn nổi ở giữa, rộng tối đa 420px.

Danh sách tự tải lại khi quay về app từ tab hay app khác.

## Trạng thái

- **Đang tải:** khung xương 3 hàng story.
- **Rỗng:** "Chưa có story nào. Chọn một nhân vật ở Khám phá để bắt đầu." + nút "Mở Khám phá".
- **Tìm không thấy:** "Không có story nào khớp “…”." + nút "Xoá tìm kiếm".
- **Lỗi tải lần đầu:** "Không tải được danh sách story." kèm lý do và nút "Thử lại".
- **Lỗi khi làm mới** (đã có danh sách cũ): danh sách cũ vẫn hiện, thêm một dòng nhỏ "Chưa làm mới được danh sách: …".

## Tính năng

- [Danh sách story](../features/F25-danh-sach-story.md)
- [Ma trận cảm xúc](../features/F09-ma-tran-cam-xuc.md) (chip cảm xúc trên mỗi hàng)
- [Giao diện và theme](../features/F26-giao-dien-theme.md)
- [Tài khoản và profile](../features/F28-tai-khoan-profile.md)

Chi tiết thiết kế: [DESIGN.md](../../DESIGN.md) trang 1, [design-impl.md §6.1](../../docs/design-impl.md).
