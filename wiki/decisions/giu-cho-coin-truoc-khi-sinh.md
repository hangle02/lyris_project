# Giữ chỗ 6 coin trước khi sinh, chỉ trừ khi có chữ

- **Ngày:** 2026-11-14 · **Ai quyết:** người dùng ("mỗi lượt tốn 6 coin", 300 khi tạo tài khoản, +60 mỗi ngày) + thiết kế ("lượt" gồm cả "Trả lời", "Tạo lại", chat thử; cách trừ; phần ghi "(tạm chọn)")

## Bối cảnh

Chủ dự án chốt: mỗi lượt chat tốn 6 coin, tài khoản mới được 300, mỗi ngày đăng nhập được 60 ([raw](../raw/2026-11-14-coin-tra-loi.md)). Một câu trả lời có thể hỏng ở nhiều chỗ: model lỗi, trả rỗng, máy bận quá 120 giây (F32), người chơi bấm "Dừng" hay đóng tab, app tắt giữa chừng. Hai tab của cùng một người có thể gửi cùng lúc.

## Lựa chọn

- "Một lượt" = **một câu trả lời của nhân vật được sinh ra** (PO chốt 2026-11-14, 3A): gửi lượt mới, "Trả lời" sau lỗi, "Tạo lại câu trả lời", chat thử ở Studio; Story và DM như nhau (DM: tạm chọn). Đã hỏi PO về "Trả lời", "Tạo lại" và chat thử.
- Chat thử ở Studio tốn coin (PO chốt 2026-11-14) vì route nhận cả thẻ lẫn tới 400 lượt hội thoại từ trình duyệt: miễn phí thì dán thẻ bất kỳ là chat mãi không tốn coin.
- **Giữ chỗ** 6 coin ngay sau khi lấy vé cổng sinh và **trước** khi lưu lượt người chơi. Không đủ thì HTTP 402 `coins_required`, lượt người chơi không được lưu, chữ còn trong ô nhập.
- **Trừ** khi câu trả lời được lưu (có chữ, kể cả phần dở khi bấm "Dừng" sau chữ đầu tiên — tạm chọn), trong cùng transaction lưu câu trả lời. **Nhả** (không mất coin) khi không có chữ: lỗi model, rỗng, lưu lỗi, chờ quá 120 giây, dừng trước chữ đầu tiên, app khởi động lại. Nhả lúc khởi động chỉ chạy trong `lifespan` của app, không bao giờ trong CLI hay script (app có thể đang sinh).
- **Bất biến:** số dư trừ coin đang giữ chỗ không bao giờ âm; chủ máy trừ tay cũng chỉ trừ được phần dùng được. Nhờ vậy câu trả lời có chữ luôn trừ được, không bao giờ bị huỷ vì coin.
- Mọi thành viên có ví: ví mở trong `auth/store.insert_member` (mọi đường tạo thành viên, kể cả server giả của bot), ví thiếu thì tự tạo ví 0.
- Sổ coin chỉ thêm, mỗi sự kiện có khoá chống trùng; số dư cache trong ví luôn bằng tổng sổ, không bao giờ âm. Mỗi tài khoản tối đa một giữ chỗ. Trigger chỉ thêm chừa cột `actor_id` và chỉ cho nó thành NULL, vì `ON DELETE SET NULL` của SQLite là một lệnh UPDATE có chạy trigger.
- "Mỗi ngày" tính theo giờ Việt Nam (UTC+7, đổi ngày lúc 0:00), bằng đồng hồ server. Múi giờ cố định thay vì `zoneinfo` (tạm chọn).
- "Đăng nhập trong ngày" = mở app lần đầu trong ngày (phiên đăng nhập kéo dài 30 ngày nên ít khi đăng nhập lại) (tạm chọn). Ngày đầu tiên được 300 + 60 = 360 (PO chốt 2026-11-14).
- Gợi ý trả lời và "AI viết nháp" không tốn coin (PO chốt 2026-11-14): không phải lời nhân vật trong hội thoại.

## Vì sao

Người chơi chỉ trả cho thứ đọc được; lỗi của máy không làm mất coin. Giữ chỗ trước khi sinh chặn được hai tab tiêu quá số dư mà không cần khoá dài. Giữ chỗ không ghi vào sổ nên lịch sử ví không đầy những dòng "trừ rồi hoàn". Dừng sau khi có chữ vẫn tính vì model đã chạy và chữ đã được lưu, nếu không người chơi có thể dừng sớm để đọc miễn phí.

## Đã cân nhắc

- Trừ sau khi xong (không giữ chỗ): hai tab có thể cùng chạy khi chỉ còn 6 coin, số dư âm.
- Trừ trước, hoàn bằng một dòng "+6" khi lỗi: đúng nhưng lịch sử rối, và app tắt giữa chừng thì phải có việc dọn riêng.
- Giá theo độ dài câu trả lời (lựa chọn 1B): chủ dự án chọn giá cố định.
- "Tạo lại" và chat thử miễn phí: dễ hiểu hơn nhưng thành cửa chat miễn phí không giới hạn.
- Trừ tay theo số dư (không theo số dùng được): chủ máy trừ đúng lúc thành viên đang chờ câu trả lời thì câu trả lời đó hoặc mất, hoặc được miễn phí.

## Nguồn

- [docs/coins.md §1–§3, §8](../../docs/coins.md)
- [F42](../features/F42-vi-coin.md)
