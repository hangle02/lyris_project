# Chat: chế độ DM

- **Đường dẫn:** `#/chat/<id>` khi công tắc trên header ở **DM** · **File:** `frontend/src/components/DmThread.tsx` (khung chat chung: `frontend/src/pages/chat/ChatPage.tsx`)

## Dùng để làm gì

Nhắn tin với nhân vật như trên điện thoại: câu ngắn, bong bóng, không có văn dẫn truyện. Đây là cùng một story với chế độ Story, chỉ khác cách hiện.

## Có gì trên màn hình

Ở điện thoại 390px, từ trên xuống:

1. **Header** giống hệt [chế độ Story](chat-story.md): quay lại, avatar, tên, dòng phụ, công tắc Story/DM (đang ở DM), nút "Suy nghĩ", nút trái tim, nút thiết lập.
2. **Đầu cuộc trò chuyện**: avatar lớn của nhân vật, tên, và dòng "Tin nhắn riêng". Chưa có tin nào thì: "Chưa có tin nhắn nào. Nhắn gì đó cho <tên> đi."
3. **Bong bóng tin**:
   - Mỗi dòng trong câu trả lời là một bong bóng riêng, như nhắn liền mấy tin.
   - Tin của nhân vật bên trái, có avatar nhỏ. Tin của bạn bên phải, có avatar persona.
   - Tin gửi cách nhau dưới 5 phút được gộp thành một nhóm (avatar chỉ hiện một lần). Cách nhau từ 15 phút thì có mốc giờ ở giữa.
   - Dưới tin mới nhất của bạn: "00:40 • Đã gửi", "00:40 • Đã xem", hoặc "Đang gửi…".
   - Phần `((…))` hiện thành chip "Chỉ đạo".
4. **Thẻ suy nghĩ thu gọn** dưới tin của nhân vật (chữ nhỏ hơn bên Story), cũng mờ cho tới khi chạm.
5. **Nhãn gộp lượt Story**: chip "N lượt trong truyện" thay cho các lượt đã chơi bên Story.
6. **Hàng thao tác** dưới tin: giống bên Story (phiên bản, tạo lại, thích/chê, sửa, xoá từ đây).
7. **Ô nhập "Nhắn tin…"** với nút "+" và nút gửi / "Dừng".

Từ 640px: header một hàng. Cột tin rộng tối đa 720px.

## Trạng thái

- **Đang tải:** khung xương bong bóng.
- **Đang chờ:** bong bóng ba chấm cạnh avatar nhân vật. Nếu máy đang trả lời người khác thì thêm dòng "Có người khác đang trò chuyện. <tên> sẽ trả lời ngay sau."
- **Lượt chỉ có suy nghĩ khi đang ẩn suy nghĩ:** "Lượt này chỉ có suy nghĩ của <tên>."
- **Lỗi:** banner trên ô nhập, có "Chi tiết" và "Thử lại".
- **Lượt chưa trả lời nằm bên Story:** banner "Lượt của bạn bên Story chưa có câu trả lời." + "Mở Story".

## Tính năng

- [Chế độ DM](../features/F02-che-do-dm.md)
- [DM và Story chung dòng thời gian](../features/F12-dm-story-chung-dong-thoi-gian.md)
- [Thao tác tin nhắn](../features/F06-thao-tac-tin-nhan.md)
- [Thẻ suy nghĩ](../features/F07-the-suy-nghi.md), [Đọc suy nghĩ](../features/F08-doc-suy-nghi.md)

Chi tiết: [phase3.md](../../docs/phase3.md), [design-impl.md §15](../../docs/design-impl.md).
