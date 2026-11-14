# Quản lý tài khoản

- **Đường dẫn:** `#/admin`, chỉ chủ máy. Thành viên mở đường dẫn này thì bị chuyển về [Tương tác](hub.md). · **File:** `frontend/src/pages/admin/AdminPage.tsx`

## Dùng để làm gì

Chủ máy mời người khác vào Lyris bằng mã mời, và quản lý thành viên: đặt lại mật khẩu, tạm khoá, mở khoá. Chủ máy không đọc được story của thành viên ở đây.

## Có gì trên màn hình

Ở điện thoại 390px, từ trên xuống. Không có thanh tab nổi.

1. **Header phụ**: "Về Tương tác", tiêu đề "Quản lý tài khoản".
2. **Mục "Mã mời"**, nút **"Tạo mã mời"**, rồi danh sách mã. Mỗi mã có ghi chú, nhãn trạng thái ("Còn hiệu lực", "Đã dùng bởi @handle", "Hết hạn", "Đã huỷ") và nút **"Huỷ"** (hỏi lại trước khi huỷ).
3. **Mục "Thành viên"** kèm số đếm. Mỗi hàng: avatar, tên, @handle, nhãn **"Chủ máy"** / **"Tạm khoá"** / **"Chờ đổi mật khẩu"**, dòng "Vào lần cuối …" (hoặc "Chưa đăng nhập lần nào") và số thiết bị đang đăng nhập.
4. **Nút "…"** trên mỗi hàng thành viên: mở một sheet có **"Đặt lại mật khẩu"** và **"Tạm khoá"** (hoặc **"Mở khoá"** nếu đang khoá).

**Hộp "Tạo mã mời"**: "Người nhận nhập mã này ở trang tạo tài khoản." Ô "Ghi chú" (ví dụ "cho Mai", chỉ bạn thấy), "Hết hạn sau" 1 / 7 / 30 ngày (mặc định 7 ngày), nút "Huỷ" / "Tạo mã".

**Coin** ([F43](../features/F43-nap-coin.md), `pages/admin/CoinView.tsx`):

- Nhóm "Mục quản lý" có thêm mục **"Coin"** (cạnh "Tài khoản", "Số liệu", "Báo cáo"). Trong đó:
  - **"Mã nạp"**: nút **"Tạo mã nạp"**, danh sách mã (ghi chú, 4 ký tự cuối, số coin, nhãn "Còn hiệu lực" / "Đã dùng bởi @handle" / "Hết hạn" / "Đã huỷ", nút "Huỷ").
  - **"Nhật ký"**: 50 lần nạp bằng mã, điều chỉnh và thưởng sáng tác mới nhất (giờ, @handle, ±coin, lý do, ghi chú, hoặc "Thưởng xếp hạng top {N}", "Thưởng công khai lần đầu", dòng cũ "Thưởng mốc {m} người chơi"; server gửi chữ trong `label`), ba tổng 30 ngày: coin đã phát, coin đã nạp, coin đã tiêu. Không có story hay tin nhắn của ai.
- **Hộp "Tạo mã nạp"**: "Gói" (100 / 550 / 1.200 / 2.500 coin) hoặc "Số coin" tự nhập (1–10.000), "Ghi chú", "Hết hạn sau" 1 / 7 / 30 ngày, nút "Huỷ" / "Tạo mã". Xong thì hộp **"Mã nạp mới"** hiện mã một lần, nút "Sao chép mã" (nền mờ và Esc không đóng được, như mã mời).
- Hàng thành viên ở mục "Thành viên" có thêm số coin ("1.200 coin"); hàng chủ máy không có.
- Sheet "…" của thành viên có thêm **"Cộng/trừ coin"**: hộp với ô số (âm là trừ), ô **"Lý do"** bắt buộc (3–120 ký tự, thành viên thấy lý do trong lịch sử ví), nút "Huỷ" / "Lưu". Trừ quá số coin dùng được (số dư trừ coin đang giữ cho câu trả lời đang chạy): "Không trừ được quá số coin dùng được ({n} coin)."
- Đã có 50 mã còn hiệu lực mà bấm "Tạo mã": "Đã có 50 mã nạp còn hiệu lực. Huỷ bớt mã cũ rồi tạo mã mới."

Từ 640px: các hộp thành hộp thoại giữa màn hình.

## Trạng thái

- **Đang tải:** khung xương.
- **Chưa có mã:** "Chưa có mã mời nào. Tạo một mã để mời người khác vào Lyris này."
- **Chỉ có chủ máy:** "Chưa có ai khác. Tạo mã mời ở trên để mời người khác."
- **Mã vừa tạo** ("Mã mời mới"): mã chỉ hiện một lần và dùng được một lần. Nút "Sao chép mã", "Sao chép liên kết" (đổi thành "Đã sao chép" trong hai giây). Sao chép lỗi thì hiện liên kết để chọn tay. Mở bằng địa chỉ máy (localhost) thì nhắc mở Lyris bằng địa chỉ Wi-Fi của Mac trước khi gửi liên kết.
- **Mật khẩu tạm vừa tạo** (sau "Đặt lại"): hộp "Mật khẩu tạm" có nút "Sao chép". Thành viên sẽ phải [đổi mật khẩu](force-password.md) lần đăng nhập sau.
- **Xác nhận tạm khoá:** hộp "Tạm khoá @handle" hỏi lại.
- **Lỗi:** câu lỗi + "Chi tiết" + "Thử lại".
- **Thành viên mở trang:** chuyển về Tương tác, trang không bao giờ tải.

## Tính năng

- [Quản lý tài khoản](../features/F30-quan-ly-tai-khoan.md)
- [Nạp coin (chế độ thử, mã nạp)](../features/F43-nap-coin.md) (mục "Coin", "Cộng/trừ coin")

Chi tiết: [auth.md](../../docs/auth.md) (mã mời, đặt lại mật khẩu, khoá tài khoản).
