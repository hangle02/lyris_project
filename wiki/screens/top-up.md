# Nạp coin

- **Đường dẫn:** `#/coins/top-up` ([F43](../features/F43-nap-coin.md)). Mở từ nút "Nạp coin" ở [Ví coin](coin-wallet.md) và ở khối "Bạn đã hết coin" trong [chat](chat-story.md). · **File:** `frontend/src/pages/coins/TopUpPage.tsx`

## Dùng để làm gì

Thành viên xem bảng giá dự kiến và nhập mã nạp người quản lý tặng. Đang là chế độ thử: Lyris chưa bán coin, mã nạp được tặng chứ không bán, không có thanh toán, không hỏi thẻ hay số điện thoại.

## Có gì trên màn hình

Ở điện thoại 390px, từ trên xuống. Không có thanh tab nổi.

1. **Header phụ**: "Về Ví coin", tiêu đề **"Nạp coin"**. Bên phải: số dư hiện tại ("1.200 coin", chữ nhỏ).
2. **Dòng chế độ thử** (`InlineAlert` loại thông tin): "Chế độ thử: Lyris chưa bán coin. Nhập mã nạp người quản lý tặng bạn."
3. **Ô mã nạp**: ô có nhãn và aria-label **"Mã nạp"** (placeholder ngắn "Nhập mã"), nút **"Dùng mã"**.
4. **Lưới gói** (2 cột ở điện thoại, các ô cao bằng nhau), tiêu đề nhỏ **"Giá dự kiến"**: mỗi thẻ có số coin ("550 coin"), dòng "Tặng thêm 50" (khi có, chữ `accent-2`), giá ("50.000đ") với nhãn nhỏ "Giá dự kiến". Bốn gói (giá PO chốt 2026-11-14): 100 coin 10.000đ · 550 coin 50.000đ · 1.200 coin 100.000đ · 2.500 coin 200.000đ.
5. **Hộp gói** (chạm một thẻ; sheet từ đáy): tiêu đề "Gói 550 coin · Giá dự kiến 50.000đ", câu "Giá dự kiến khi Lyris ra mắt. Ở chế độ thử chưa bán coin; người quản lý có thể tặng bạn mã nạp để thử.", chỉ một nút **"Đóng"**. Không có nút thanh toán, không có nút liên hệ (để gói có giá không thành lời mời mua coin ngoài app).

Từ 640px: lưới 3 cột, hộp gói thành hộp thoại giữa màn hình.

## Trạng thái

- **Đang dùng mã:** nút "Dùng mã" có vòng quay nhỏ, ô bị khoá.
- **Mã đúng:** thông báo "Đã nạp 100 coin.", số dư trên header cập nhật, ô được xoá trống.
- **Mã sai, hết hạn, đã dùng:** dưới ô: "Mã nạp không đúng hoặc đã hết hạn." (ô có `aria-invalid="true"`).
- **Thử sai nhiều lần:** "Bạn đã thử sai nhiều lần. Hãy đợi một lúc rồi thử lại."
- **Chủ máy mở trang:** chỉ "Tài khoản quản lý không tốn coin." và link về Quản lý tài khoản để tạo mã.
- **Lỗi tải gói:** câu lỗi + "Thử lại"; ô mã nạp vẫn dùng được.

## Tính năng

- [Nạp coin (chế độ thử, mã nạp)](../features/F43-nap-coin.md)

Chi tiết: [docs/coins.md §4, §10](../../docs/coins.md).
