# Nạp coin ở chế độ thử: mã nạp và cộng tay, chưa có cổng thanh toán

- **Ngày:** 2026-11-14 · **Ai quyết:** người dùng (2A) + thiết kế (giá gói, chi tiết mã: "(tạm chọn)")

## Bối cảnh

Lyris chạy trên máy riêng, chưa có tài khoản doanh nghiệp hay API key của cổng thanh toán. Chủ dự án chọn 2A: có màn "Nạp coin" với các gói giá nhưng ở chế độ thử; chủ máy tạo mã nạp hoặc cộng coin tay; ra mắt mới nối cổng thật ([raw](../raw/2026-11-14-coin-tra-loi.md)).

## Lựa chọn

- Màn "Nạp coin" (`#/coins/top-up`) ghi rõ "Chế độ thử: Lyris chưa bán coin."; chạm gói chỉ mở hộp "Giá dự kiến khi Lyris ra mắt…" với nút "Đóng": không có nút thanh toán, không có nút liên hệ trên gói, không hỏi thẻ hay số điện thoại.
- **Ở chế độ thử, mã nạp được tặng, không bán** (tạm chọn, ghi trong Điều khoản). Nếu gói có giá VND và nút "Liên hệ" đi cùng nhau thì gói thành kênh bán coin lấy tiền mặt hay chuyển khoản, không có điều khoản bán, hoá đơn hay hoàn tiền, trái với câu "chưa thu tiền".
- Giá gói (PO chốt 2026-11-14, 1A, ghi "Giá dự kiến", chỉ để hiện): 100 coin 10.000đ · 550 coin 50.000đ · 1.200 coin 100.000đ · 2.500 coin 200.000đ. Ví dụ PO đã xem lúc chọn là 100 coin = 20.000đ; đã hỏi lại PO.
- Coin của chế độ thử khi ra mắt: mọi số dư **đặt lại về 0** (PO chốt 2026-11-14, 6B, [raw](../raw/2026-11-14-coin-tra-loi-2.md)); Điều khoản ghi ngay từ bây giờ, app báo trước ít nhất 30 ngày.
- Mã nạp do chủ máy tạo ở `#/admin` → "Coin": số coin của một gói hoặc tự nhập 1–10.000, hạn 1/7/30 ngày, dùng một lần, ai nhập trước được (tạm chọn), chỉ lưu hash, mã hiện một lần, tối đa 50 mã còn hiệu lực (tạm chọn). Sai/hết hạn/đã dùng cùng một câu lỗi, 10 lần sai mỗi giờ thì chặn.
- Cộng/trừ tay cần lý do 3–120 ký tự, không trừ quá số coin dùng được (số dư trừ coin đang giữ cho câu trả lời đang chạy); thành viên thấy lý do trong lịch sử (tạm chọn).
- Mọi lần nạp, điều chỉnh và thưởng mốc sáng tác ghi vào sổ coin (ai làm, lúc nào, bao nhiêu) và hiện trong "Nhật ký" của chủ máy.
- Chế độ thử không thu tiền nên không có hoàn tiền; Điều khoản ghi rõ.

## Vì sao

Có màn giá thật từ bây giờ để thử trải nghiệm hết coin → nạp, đo phễu, mà không vướng pháp lý thanh toán. Mã nạp dùng lại đúng cách làm của mã mời (đã có test), nên ít rủi ro.

## Đã cân nhắc

- Nối cổng thật ngay (2B: MoMo, VNPay, Stripe): cần tài khoản doanh nghiệp, hoá đơn, chính sách hoàn tiền; chủ dự án để sau.
- Chỉ cộng tay, không có màn nạp (2C): không thử được trải nghiệm mua.
- Nút "Liên hệ người quản lý" trên từng gói: bỏ, vì biến gói có giá thành lời mời mua coin ngoài app.
- Mã gắn sẵn với một người nhận: an toàn hơn khi mã lộ, nhưng chủ máy phải chọn người mỗi lần; mã dùng một lần và hết hạn đã đủ cho chế độ thử.

## Nguồn

- [docs/coins.md §4, §12](../../docs/coins.md)
- [F43](../features/F43-nap-coin.md)
