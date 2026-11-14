# Nhiệm vụ ngày có trần 30 coin, quảng cáo mẫu kiểm giờ ở server

- **Ngày:** 2026-11-14 · **Ai quyết:** người dùng (4A: ba nhiệm vụ, trần 30, quảng cáo giả 15 giây) + thiết kế (cách đếm, cách nhận: "(tạm chọn)")

## Bối cảnh

Chủ dự án chọn 4A: nhiệm vụ ngày, tổng tối đa 30 coin/ngày: xem quảng cáo +5 (tối đa 3 lần), trò chuyện với 3 nhân vật khác nhau +10, gửi 20 lượt +5; quảng cáo là quảng cáo giả 15 giây, sau này thay bằng mạng quảng cáo thật ([raw](../raw/2026-11-14-coin-tra-loi.md)).

## Lựa chọn

- Ngày tính theo giờ Việt Nam (0:00 làm lại), đồng hồ server.
- "3 nhân vật khác nhau": nhân vật đã trả lời mình (câu trả lời đã trả coin) trong ngày; bản sao nhân vật công khai tính theo nhân vật gốc; hai story cùng nhân vật là một.
- "Gửi 20 lượt": 20 câu trả lời đã trả coin của lượt gửi mới và "Trả lời"; không tính "Tạo lại câu trả lời" (tạm chọn).
- Nhận thưởng bằng nút "Nhận", không tự cộng (tạm chọn); thưởng chưa nhận mất lúc 0:00.
- Trần 30 kiểm ở server mỗi lần nhận, kể cả khi sau này thêm nhiệm vụ: đọc tổng, đếm số quảng cáo, kiểm và ghi sổ trong cùng một transaction.
- Chat thử ở Studio không tính cho nhiệm vụ (tạm chọn).
- **Quảng cáo mẫu trung thực:** hộp ghi "Quảng cáo mẫu" và "Đây là quảng cáo mẫu của Lyris, chưa phải quảng cáo thật."; nội dung là thẻ giới thiệu tính năng của Lyris, không gọi mạng ngoài, không đo thêm gì.
- **Khó lách:** server ghi giờ bắt đầu; chỉ nhận khi đã đủ 15 giây theo đồng hồ server, trong vòng 10 phút, cùng ngày coin, đúng tài khoản, chưa bị huỷ, tối đa 3 lần/ngày. Bấm "Đóng" thì giao diện gọi `POST /api/coins/ads/{id}/cancel`, lượt đó không nhận được nữa (`ad_expired`). Chỉ server giả của bot dựng app với `ad_seconds=2`; app thật không có biến môi trường nào đổi được 15 giây (tạm chọn).
- **Giới hạn biết trước:** "Đóng" chỉ chặn được giao diện thật. Script gọi thẳng `start`, đợi 15 giây rồi `claim` (không gọi `cancel`) vẫn nhận được, giống người xem hết. Quảng cáo mẫu không có cách biết ai nhìn màn hình. Thiệt hại tối đa 15 coin/ngày/tài khoản; khi có mạng quảng cáo thật thì dùng xác nhận phía server của mạng đó.
- Chủ máy không có nhiệm vụ.

## Vì sao

Chỉ đếm câu trả lời đã trả coin nên không ai làm nhiệm vụ bằng lượt lỗi; mỗi lượt tốn 6 coin nên "Gửi 20 lượt" (+5) không thể lời bằng cách spam. Nếu giao diện tự đếm 15 giây thì gọi thẳng API là có coin; giờ phải nằm ở server. Ghi rõ "quảng cáo mẫu" để không ai tưởng đó là quảng cáo thật. Quảng cáo mẫu không gửi dữ liệu cho bên quảng cáo nào; Lyris vẫn ghi sự kiện `ad_started`/`mission_claimed` như mọi màn khác (Chính sách đã kê).

## Đã cân nhắc

- Bỏ quảng cáo (4B): chủ dự án muốn giữ chỗ cho quảng cáo thật.
- Nhiệm vụ một lần (4C: tạo nhân vật đầu tiên…): chưa làm.
- Tự cộng khi đủ điều kiện: ít bấm hơn nhưng người chơi không thấy mình vừa được thưởng.

## Nguồn

- [docs/coins.md §6, §9](../../docs/coins.md)
- [F45](../features/F45-nhiem-vu-ngay.md)
