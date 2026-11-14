# Menu "Suy nghĩ" trên header chat

- **Đường dẫn:** trong `#/chat/<id>`, nút "Suy nghĩ" (icon mắt) cạnh công tắc Story/DM · **File:** `frontend/src/pages/chat/ThoughtMenu.tsx`

## Dùng để làm gì

Chọn cách đọc suy nghĩ của nhân vật ngay trong lúc chat, không phải mở thiết lập: có đọc hay không, có làm mờ hay không, và suy nghĩ nằm ở đâu trong lượt Story.

## Có gì trên màn hình

**Nút trên header**: chữ "Suy nghĩ", icon mắt và mũi tên xuống. Khi đang ẩn suy nghĩ, icon là mắt gạch chéo. Ở điện thoại 390px nút nằm ở hàng thứ hai của header, cạnh công tắc Story/DM. Từ 640px nằm chung hàng với tên.

**Bảng mở ra** (rộng tối đa 20rem, neo dưới nút), từ trên xuống:

1. Công tắc **"Đọc suy nghĩ của nhân vật"**, kèm dòng: "Tắt thì thẻ suy nghĩ không hiện trong story. <tên> vẫn nghĩ như thường, chỉ là bạn không đọc thấy." Lưu ngay vào story.
2. Công tắc **"Luôn hiện suy nghĩ"**: "Không làm mờ thẻ suy nghĩ, khỏi phải chạm để đọc." Chỉ lưu trên thiết bị này.
3. Nhóm **"Ở Story, suy nghĩ nằm"**, chọn một:
   - "Lồng trong truyện": vài dòng suy nghĩ xen giữa diễn biến.
   - "Một đoạn ở cuối": một đoạn suy nghĩ dài hơn ở cuối mỗi lượt.
4. Dòng nhỏ: "Kiểu suy nghĩ áp dụng từ lượt trả lời tiếp theo."

Bấm ra ngoài hoặc Esc để đóng.

## Trạng thái

- **Đang lưu:** công tắc "Đọc suy nghĩ" bị khoá (aria-disabled) cho tới khi server trả lời.
- **Suy nghĩ đang ẩn:** icon mắt gạch. "Luôn hiện suy nghĩ" biến mất (không còn gì để làm mờ). Thêm dòng "Nhân vật vẫn nghĩ trong lòng theo kiểu này, chỉ là bạn không đọc thấy."
- **Đang trả lời / đang lưu thiết lập khác:** các lựa chọn kiểu suy nghĩ bị khoá.
- **Server từ chối:** công tắc trả về giá trị cũ, chat hiện banner lỗi.

## Tính năng

- [Thẻ suy nghĩ](../features/the-suy-nghi.md)
- [Đọc suy nghĩ](../features/doc-suy-nghi.md)

Chi tiết: [phase4.md](../../docs/phase4.md) (phần B), [design-impl.md §17](../../docs/design-impl.md).
