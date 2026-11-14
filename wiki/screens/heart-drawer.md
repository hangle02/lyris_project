# Ngăn "Cảm xúc & ký ức"

- **Đường dẫn:** trong `#/chat/<id>`, mở bằng nút trái tim trên header (hoặc `?open=heart` để chụp ảnh kiểm tra) · **File:** `frontend/src/pages/chat/HeartDrawer.tsx`

## Dùng để làm gì

Xem nhân vật đang cảm thấy gì và còn nhớ gì trong story này: chỉ số cảm xúc, cảnh hiện tại, ký ức, và những điều trong sổ thế giới mà story đã mở khoá. Không có chữ kỹ thuật (trạng thái job, kiểu tìm kiếm...).

## Có gì trên màn hình

Ở điện thoại 390px là ngăn trượt từ phải, phủ hết màn hình. Từ trên xuống:

1. **Tiêu đề "Cảm xúc & ký ức"** và dòng "Điều <tên> đang cảm thấy và còn nhớ trong story này."
2. **"Chỉ dẫn diễn xuất"**: một đoạn văn nói nhân vật nên diễn thế nào lúc này.
3. **"Ma trận cảm xúc"**: 6 thanh đo (Thương mến, Tin cậy, Rung động, Nhung nhớ / Chiếm hữu, Lo sợ mất mát, Khoảng cách), mỗi thanh một màu.
4. **"Cảnh"**: nơi chốn và thời gian hiện tại.
5. **"Ký ức"**: mỗi ký ức một hàng, có nhãn **"Sự kiện"** hoặc **"Điều đã biết"**, và nút **"Quên"**. Bấm "Quên" thì hỏi lại, có nút "Giữ lại".
6. **"Tóm tắt những lượt cũ"**: một mục gập, mở ra là bản tóm tắt.
7. **"Thế giới đã mở khoá"**:
   - Các mục bạn được đọc: hàng gập có tên mục, nhãn "Chỉ bạn biết" nếu chỉ bạn biết. Mở ra có nội dung và nút "Xem lúc được nhắc tới lần đầu" (đóng ngăn, nhảy tới lượt đó).
   - Nhóm **"Điều <tên> giữ trong lòng"**: các bí mật của nhân vật, bị làm mờ, chạm để đọc. Nếu "Đọc suy nghĩ" tắt thì nhóm này không hiện.

Từ 640px: ngăn có độ rộng cố định ở mép phải, bo góc trái. Phía sau có lớp mờ, bấm ra ngoài hoặc Esc để đóng.

## Trạng thái

- **Đang tải:** khung xương từng phần.
- **Chưa có dữ liệu cảm xúc:** "Story này chưa có dữ liệu cảm xúc." Các thanh ở 0 và mờ.
- **Chưa có ký ức:** "Chưa có ký ức nào. Nhân vật ghi nhớ sau mỗi lượt trả lời."
- **Còn lượt chưa đọc:** "Lyris chưa đọc hết story này." + nút "Đọc lại story".
- **Đang đọc lại:** ba chấm nhảy thay cho nút.
- **Chưa có sổ thế giới:** "<tên> chưa có sổ thế giới." Chủ nhân vật thấy thêm link "Thêm trong Studio" (mở [phần Thế giới](lorebook-section.md)).
- **Chưa mở khoá gì:** "Chưa mở khoá điều gì. Khi story nhắc tới người, nơi chốn hay chuyện cũ trong thế giới của <tên>, chúng sẽ hiện ở đây."
- **Lỗi tải thế giới:** "Chưa tải được thế giới." + "Thử lại" + "Chi tiết".
- **Lỗi tải cảm xúc:** chỉ hiện câu lỗi và "Thử lại".
- **Quên lỗi:** "Chưa quên được. …" ngay dưới hàng.

## Tính năng

- [Ma trận cảm xúc](../features/ma-tran-cam-xuc.md)
- [Trí nhớ](../features/tri-nho.md)
- [Sổ thế giới](../features/so-the-gioi.md)
- [Đọc suy nghĩ](../features/doc-suy-nghi.md)

Chi tiết: [design-impl.md §6.3 và §14](../../docs/design-impl.md), [phase3.md §8](../../docs/phase3.md), [phase4.md](../../docs/phase4.md).
