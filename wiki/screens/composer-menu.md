# Menu "+" và vùng gợi ý

- **Đường dẫn:** trong `#/chat/<id>`, nút "+" ở đầu ô nhập · **File:** `frontend/src/pages/chat/ComposerMenu.tsx` (vùng gợi ý: `SuggestionArea.tsx`, `QuickReplies.tsx`; danh sách mục: `suggestLogic.ts`)

## Dùng để làm gì

Gom các việc phụ quanh ô nhập vào một chỗ, và hiện gợi ý trả lời khi bạn xin. Gợi ý chỉ hiện khi bạn bấm "Nhận gợi ý", không tự bật.

## Có gì trên màn hình

**Menu "+"**, ở điện thoại 390px là sheet trượt từ đáy, có thanh kéo nhỏ ở trên. Ba mục, theo thứ tự:

1. **"Nhận gợi ý"**: "Ba cách trả lời cho lượt tiếp theo."
2. **"Xem sự kiện"**: "Những gì đã xảy ra trong story." Mở [sheet Sự kiện](events-sheet.md).
3. **"Gửi hình ảnh"** với nhãn "Sắp có": "Sắp tới bạn sẽ gửi được ảnh cho nhân vật xem." Luôn bị khoá.

Mục bị khoá vẫn hiện, dòng phụ nói lý do. Ví dụ với "Nhận gợi ý": "Đợi nhân vật trả lời xong đã.", "Story chưa có lượt nào để gợi ý.", "Lượt của bạn chưa có câu trả lời, nên chưa có gì để gợi ý.", "Nhân vật vừa trả lời bên DM. Mở DM để nhận gợi ý.", "Nhân vật tạm thời chưa trả lời được."

Từ 640px: menu là popover rộng 300px nổi ngay trên nút "+". Dùng phím mũi tên để chọn, Esc để đóng.

**Vùng gợi ý**, nằm ngay trên ô nhập:

1. Dòng đầu: "Gợi ý cho bạn", nút "Gợi ý khác", nút đóng (X).
2. **3 thẻ gợi ý.** Chạm một thẻ là gửi luôn câu đó.
   - Điện thoại: một hàng vuốt ngang, mỗi thẻ gần rộng bằng màn hình, cao tối đa hai dòng.
   - Từ 640px: các thẻ xếp xuống dòng trong cột ô nhập, không phải cuộn ngang.

## Trạng thái

- **Đang nghĩ gợi ý:** ba chấm nhảy + nút "Huỷ gợi ý".
- **Có gợi ý:** 3 thẻ như trên.
- **Lỗi:** câu dễ hiểu + "Chi tiết" + "Thử lại".
- Vùng gợi ý tự đóng khi câu trả lời mới nhất thay đổi (gửi lượt mới, tạo lại, sửa, xoá).

## Tính năng

- [Menu +](../features/menu-cong.md)
- [Nhận gợi ý](../features/nhan-goi-y.md)
- [Gửi hình ảnh](../features/gui-hinh-anh.md) (chưa làm, chỉ có mục "Sắp có")
- [Dòng thời gian sự kiện](../features/dong-thoi-gian-su-kien.md)

Chi tiết: [design-impl.md §15](../../docs/design-impl.md) (Phase 3b).
