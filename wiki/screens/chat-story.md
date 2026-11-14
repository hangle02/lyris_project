# Chat: chế độ Story

- **Đường dẫn:** `#/chat/<id>` khi story đang ở chế độ Story · **File:** `frontend/src/pages/chat/ChatPage.tsx` (header: `ChatHeader.tsx`; lượt: `components/MessageItem.tsx`, `components/Prose.tsx`; ô nhập: `components/Composer.tsx`)

## Dùng để làm gì

Không gian nhập vai toàn màn hình. Nhân vật trả lời bằng văn tiểu thuyết: dẫn truyện, lời thoại và suy nghĩ. Không có thanh tab nổi.

## Có gì trên màn hình

Ở điện thoại 390px, từ trên xuống:

1. **Header kính, dính trên cùng**, hai hàng:
   - Hàng 1: nút quay lại (về danh sách story), avatar và tên nhân vật, dòng phụ. Chạm tên mở [Hồ sơ nhân vật](character-profile.md). Bên phải là nút trái tim (mở [Cảm xúc & ký ức](heart-drawer.md)) và nút bánh răng (mở [Thiết lập story](story-settings.md)).
   - Hàng 2: công tắc **Story / DM** và nút **"Suy nghĩ"** (icon mắt, mở [menu Suy nghĩ](thought-menu.md)).
   - Dòng phụ: vai trò (chữ vàng) · nơi chốn · thời gian. Trên điện thoại và máy tính bảng, nếu đã có cảnh thì chỉ hiện nơi chốn và thời gian, vai trò nằm trong tooltip.
2. **Banner "Khoảnh khắc"** (khi story có): một dòng dưới header, ví dụ "Khoảnh khắc: …" kèm nhãn hiệu ứng như "+Thương mến".
3. **Các lượt**, cột đọc rộng tối đa 720px:
   - **Lượt nhân vật**: dẫn truyện chữ nghiêng màu nhạt, không có khung. Lời thoại trong thẻ. Suy nghĩ là thẻ có viền hồng bên trái, bị làm mờ với nhãn "Chạm để lắng nghe". Chạm để đọc, chạm lần nữa để giấu.
   - **Lượt của bạn**, căn phải, có avatar persona: lời thoại trong ô hồng, hành động và dẫn truyện là dòng nghiêng, phần `((…))` hiện thành chip nhỏ "Chỉ đạo" dưới lượt.
   - **Hàng thao tác** dưới lượt: Phiên bản trước / sau (khi có nhiều phiên bản), Tạo lại câu trả lời, Thích, Chê, Sửa, Xoá từ đây. Hàng này luôn hiện ở lượt trả lời mới nhất. Ở lượt khác: điện thoại thì chạm vào lượt để hiện, máy tính thì rê chuột.
   - **Nhãn gộp lượt DM**: chip "N tin nhắn riêng" thay cho các lượt đã nhắn bên DM.
4. **Banner trên ô nhập** (khi cần): lỗi, "Lượt của bạn chưa có câu trả lời." + "Trả lời", "Lượt của bạn bên DM chưa có câu trả lời." + "Mở DM", hoặc một câu thường khi máy không trả lời được.
5. **Ô nhập**: nút "+" (mở [menu +](composer-menu.md)), ô 'Nhập lời thoại vào "…"', nút gửi. Khi nhân vật đang viết, nút gửi đổi thành "Dừng". Enter để gửi, Shift+Enter xuống dòng.

Từ 640px: header gộp thành một hàng. Từ 1024px: hàng header rộng 960px, dòng phụ hiện đủ vai trò và cảnh.

## Trạng thái

- **Đang tải story:** khung xương ở header và trong cột.
- **Story trống:** "Chưa có lượt nào. Hãy viết lượt đầu tiên cho story với <tên>."
- **Chờ chữ đầu tiên:** ba chấm nhảy trong một viên tròn (không đếm giờ).
- **Đang stream:** chữ hiện dần, có con trỏ ở khối cuối.
- **Đang chờ người khác:** dưới ba chấm có dòng "Có người khác đang trò chuyện. <tên> sẽ trả lời ngay sau."
- **Lỗi:** banner có câu dễ hiểu, "Chi tiết" và "Thử lại".
- **Suy nghĩ đang ẩn** ("Đọc suy nghĩ" tắt): không có thẻ suy nghĩ. Lượt chỉ có suy nghĩ thì hiện "Lượt này chỉ có suy nghĩ của <tên>."
- **Không tìm thấy story:** trang riêng "Không tìm thấy story", có nút về danh sách. **Không mở được:** "Chưa mở được story" + "Thử lại".
- **Hết coin** (Kế hoạch, [F42](../features/F42-vi-coin.md); thành viên còn dưới 6 coin): ô nhập `disabled`, nút gửi và "+" khoá. Thay chỗ banner trên ô nhập là khối **"Bạn đã hết coin"**, dòng "Mỗi câu trả lời cần 6 coin." và hai nút **"Nạp coin"** (mở [Nạp coin](top-up.md)) và **"Nhiệm vụ"** (mở [Nhiệm vụ](missions.md)). "Tạo lại câu trả lời" khoá với lý do "Cần 6 coin để tạo lại." Chữ đang gõ được giữ. Server trả 402 `coins_required` (vd tab khác vừa tiêu hết) thì cũng chuyển sang trạng thái này. Có coin lại thì ô nhập mở, không cần tải lại. Chủ máy không bao giờ thấy trạng thái này.

## Tính năng

- [Chế độ Story](../features/F01-che-do-story.md)
- [Thẻ suy nghĩ](../features/F07-the-suy-nghi.md), [Đọc suy nghĩ](../features/F08-doc-suy-nghi.md)
- [Thao tác tin nhắn](../features/F06-thao-tac-tin-nhan.md)
- [Định dạng lượt người chơi](../features/F04-dinh-dang-luot-nguoi-choi.md), [Chỉ đạo ẩn](../features/F05-chi-dao-an.md)
- [DM và Story chung dòng thời gian](../features/F12-dm-story-chung-dong-thoi-gian.md)
- [Dùng chung máy](../features/F32-dung-chung-may.md)
- [Ẩn chữ kỹ thuật](../features/F27-an-chu-ky-thuat.md)
- [Ví coin và tiêu coin khi chat](../features/F42-vi-coin.md) (Kế hoạch)

Chi tiết: [DESIGN.md](../../DESIGN.md) mục 6, [design-impl.md §6.2 và §15](../../docs/design-impl.md), [phase3.md](../../docs/phase3.md), [auth.md §5.5](../../docs/auth.md) (hàng đợi).
