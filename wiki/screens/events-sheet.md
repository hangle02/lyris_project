# Sheet "Sự kiện"

- **Đường dẫn:** trong `#/chat/<id>`, mở từ [menu "+"](composer-menu.md) > "Xem sự kiện" (hoặc `?open=events` để chụp ảnh kiểm tra) · **File:** `frontend/src/pages/chat/EventsSheet.tsx`

## Dùng để làm gì

Dòng thời gian những gì nhân vật đã ghi nhớ sau mỗi lượt. Chạm một mục thì sheet đóng và chat cuộn tới đúng lượt đó, lượt được tô sáng một lúc.

## Có gì trên màn hình

Ở điện thoại 390px là sheet trượt từ đáy. Từ trên xuống:

1. **Tiêu đề "Sự kiện"** và dòng "Những gì đã xảy ra giữa bạn và <tên>."
2. **Hai tab**: "Dòng thời gian" và "Khoảnh khắc" (đổi bằng phím mũi tên trái/phải).
3. **Tab "Dòng thời gian"**: dòng "Mới nhất ở trên. Chạm một sự kiện để xem lại lượt đó." rồi danh sách. Mỗi mục có:
   - Nhãn **Story** (hồng) hoặc **DM** (vàng) và giờ.
   - Ký ức của lượt đó (chữ kiểu truyện).
   - Các dòng "Điều đã biết: …".
   - Chip thay đổi cảm xúc (chấm màu theo cảm xúc) và chip cảnh (nơi chốn).
4. **Tab "Khoảnh khắc"**: hai phần có tiêu đề, "Khoảnh khắc" (khoảnh khắc hiện tại kèm nhãn hiệu ứng, nếu có) và "Nhiệm vụ".

Từ 640px: thành hộp thoại giữa màn hình.

## Trạng thái

- **Đang tải:** khung xương.
- **Rỗng:** "Chưa có sự kiện nào. Sau mỗi lượt <tên> trả lời, Lyris ghi lại điều đáng nhớ ở đây."
- **Tab Khoảnh khắc trống:** "Chưa có khoảnh khắc nào. Khi story với <tên> rẽ sang một hướng đáng nhớ, khoảnh khắc đó hiện ở đây." và "Chưa có nhiệm vụ nào. …". Đây là phần vỏ, chờ đạo diễn khoảnh khắc ở Phase 8 lấp vào. Nhiệm vụ chưa làm.
- **Lỗi:** câu lỗi + "Chi tiết" + "Thử lại".

## Tính năng

- [Dòng thời gian sự kiện](../features/F11-dong-thoi-gian-su-kien.md)
- [Đạo diễn khoảnh khắc](../features/F40-dao-dien-khoanh-khac.md) (tab Khoảnh khắc, chưa làm)

Chi tiết: [design-impl.md §15](../../docs/design-impl.md), [plan.md](../../docs/plan.md) (Phase 8).
