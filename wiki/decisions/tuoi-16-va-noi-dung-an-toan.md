# Lyris cho người 16+, "Nội dung an toàn" bật sẵn, 18+ bằng ô tự xác nhận

- **Ngày:** 2026-11-15 · **Ai quyết:** người dùng (PO chốt) · **Thay cho:** [noi-dung-an-toan-chua-cong-tuoi](noi-dung-an-toan-chua-cong-tuoi.md) (phần "không đặt tuổi tối thiểu")

## Bối cảnh

Quyết định 2026-11-14 không đặt tuổi tối thiểu và chỉ nhắc người dưới 16 tuổi xin phép cha mẹ. Rà soát tuân thủ hỏi lại tuổi
tối thiểu và cách mở nội dung 18+ sau này. PO trả lời ba lần trong một buổi:

1. 00:38: để 12 tuổi; nếu sau này có nội dung 18+ thì thêm nút "Nội dung an toàn", muốn không an toàn thì tắt nút và kiểm 18+.
2. 00:43: dưới 16 là trẻ em (Nghị định 13/2023/NĐ-CP), nên ghi **16+** trong điều khoản, thay cho 12; giữ ý nút "Nội dung an
   toàn" bật sẵn, tắt để xem nội dung 18+ thì phải xác nhận 18+.
3. 00:45: không cần khai năm sinh khi đăng ký; tắt nút thì hiện **ô tích "đã đủ 18+"** là đủ.

## Lựa chọn (bản cuối)

- **Lyris dành cho người từ đủ 16 tuổi.** Ghi trong [Điều khoản §1](../../docs/legal/terms.md) và [Chính sách §8](../../docs/legal/privacy.md).
  Đồng ý Điều khoản lúc tạo tài khoản là xác nhận đã đủ 16 tuổi. Người dưới 16 không được dùng; người vận hành biết tài khoản
  của người dưới 16 thì xoá.
- **Không có ô năm sinh / ngày sinh** khi đăng ký (kể cả bản host, [F61](../features/F61-dang-ky-cong-khai.md)).
- **Nút "Nội dung an toàn" bật sẵn cho mọi người.** Hiện chưa có nội dung 18+ nên chưa có nút. Khi có nội dung 18+: thêm nút
  ở sheet Tài khoản, theo từng tài khoản, không theo từng story (tạm chọn: PO không nói chỗ đặt nút); tắt nút thì hiện ô tích **"Tôi đã đủ 18 tuổi"**, phải tích mới tắt được (tự xác nhận). Chỉ lưu thời điểm xác
  nhận. Người vận hành gỡ được quyền này nếu bị lạm dụng. Cách làm: [F48](../features/F48-noi-dung-an-toan.md).
- Phần còn lại của quyết định 2026-11-14 vẫn giữ: luật an toàn trong mọi prompt, mọi nội dung tình dục liên quan tới người
  dưới 18 tuổi bị từ chối tuyệt đối (kể cả khi đã tắt nút).

## Vì sao

- Nghị định 13/2023/NĐ-CP coi người dưới 16 tuổi là trẻ em: xử lý dữ liệu của họ cần cha mẹ/người giám hộ đồng ý, mà Lyris
  không có cách lấy đồng ý đó. Đặt 16+ thì Lyris không phục vụ trẻ em theo nghĩa của nghị định.
- Không hỏi năm sinh: thu thập tối thiểu (năm sinh tự khai cũng dễ khai sai như ô tích, mà thêm dữ liệu cá nhân).
- Ô tích 18+ chỉ cần khi có nội dung 18+; nội dung an toàn bật sẵn nên người không tắt nút không bị hỏi gì.

## Đã cân nhắc

- 12+ (lời PO lúc 00:38): bị thay bằng 16+ vì người 12–15 tuổi là trẻ em theo Nghị định 13.
- Khai năm sinh khi đăng ký (tạm chọn cũ trong docs/server.md §13 và F61): PO bỏ.
- Xác minh tuổi bằng giấy tờ hay bên thứ ba cho 18+: không làm; tự xác nhận theo lời PO. Kênh phát hành nào đòi hơn thế thì
  xem lại khi bọc app (docs/compliance.md §6).

## Ảnh hưởng

- Văn bản: [docs/legal/terms.md](../../docs/legal/terms.md) §1, §3 và [docs/legal/privacy.md](../../docs/legal/privacy.md) §2, §8 (vi + en).
  `LEGAL_VERSION` chưa đổi (đổi khi thật sự mở nội dung 18+, F48).
- [docs/compliance.md](../../docs/compliance.md) §0, §5.2 (dòng trẻ em, nội dung 18+, xếp hạng tuổi), §5.3, §6; [docs/server.md](../../docs/server.md) §13, §16;
  [docs/coins.md](../../docs/coins.md) §12; README (EN + VI).
- Xếp hạng tuổi cửa hàng (khi bọc app): an toàn bật sẵn, chưa có nội dung 18+ → cân nhắc 12+ hoặc 17+ của App Store; có chế
  độ 18+ thì phải trả lời lại bảng hỏi tuổi (17+ / 18+).

## Nguồn

- Lời gốc: [raw/2026-11-15-tuoi-toi-thieu.md](../raw/2026-11-15-tuoi-toi-thieu.md) (00:38),
  [raw/2026-11-15-tuoi-toi-thieu-2.md](../raw/2026-11-15-tuoi-toi-thieu-2.md) (00:43),
  [raw/2026-11-15-tuoi-toi-thieu-3.md](../raw/2026-11-15-tuoi-toi-thieu-3.md) (00:45).
