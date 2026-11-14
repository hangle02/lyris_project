# Nhiệm vụ

- **Đường dẫn:** `#/missions` (Đã có, [F45](../features/F45-nhiem-vu-ngay.md)). Mở từ nút "Nhiệm vụ" ở [Ví coin](coin-wallet.md) và ở khối "Bạn đã hết coin" trong [chat](chat-story.md). · **File:** `frontend/src/pages/coins/MissionsPage.tsx`, hộp quảng cáo `AdDialog.tsx`, logic `missionsLogic.ts` · Điểm tạm chọn khi build: [coin-f45-khi-build](../decisions/coin-f45-khi-build.md)

## Dùng để làm gì

Thành viên kiếm thêm tối đa 30 coin mỗi ngày bằng ba nhiệm vụ. Làm lại từ đầu lúc 0:00 giờ Việt Nam.

## Có gì trên màn hình

Ở điện thoại 390px, từ trên xuống. Không có thanh tab nổi.

1. **Header phụ**: "Về Ví coin", tiêu đề **"Nhiệm vụ hôm nay"**.
2. **Dòng tổng**: "Đã nhận {x}/30 coin hôm nay" với thanh `Meter` mảnh, dòng phụ `muted` "Làm mới lúc 0:00".
3. **Ba dòng nhiệm vụ** (`Card`, cao bằng nhau). Mỗi dòng: tên, thưởng ("+5 coin"), tiến độ ("1/3") và một nút bên phải:
   - **"Xem quảng cáo"** · +5 coin mỗi lần · "x/3" · nút **"Xem"** (hết lượt: "Đã xem đủ").
   - **"Trò chuyện với 3 nhân vật khác nhau"** · +10 coin · "x/3" · nút **"Nhận"** khi đủ, **"Đã nhận"** sau khi nhận; chưa đủ thì không có nút, chỉ tiến độ.
   - **"Gửi 20 lượt"** · +5 coin · "x/20" · như trên. Dòng phụ nhỏ: "Không tính 'Tạo lại câu trả lời'."

**Hộp "Quảng cáo mẫu"** (`Modal`, toàn màn hình ở điện thoại):

- Nhãn trên cùng **"Quảng cáo mẫu"** và câu **"Đây là quảng cáo mẫu của Lyris, chưa phải quảng cáo thật."**
- Nội dung: một thẻ giới thiệu tính năng của chính Lyris (ảnh có sẵn trong repo, ví dụ "Đọc suy nghĩ của nhân vật"). Không tải gì từ mạng ngoài.
- Đếm ngược "Còn 15 giây" (`aria-live="polite"`, đọc mỗi 5 giây).
- Nút **"Nhận 5 coin"** khoá cho tới khi hết giờ; nút **"Đóng"** luôn bấm được (đóng khi chưa nhận thì giao diện gọi `POST /api/coins/ads/{id}/cancel`: lượt xem đó bị huỷ ở server, không có thưởng).

Từ 640px: cột giữa rộng tối đa 560px; hộp quảng cáo là hộp thoại giữa màn hình, rộng 420px.

## Trạng thái

- **Đang tải:** khung xương 3 dòng.
- **Đủ 30 coin hôm nay:** dòng tổng thành "Đã nhận đủ 30 coin hôm nay. Quay lại sau 0:00 nhé."; mọi nút "Xem" khoá.
- **Hết lượt quảng cáo:** "Hôm nay bạn đã xem đủ 3 quảng cáo."
- **Bấm "Nhận 5 coin" mà server chưa thấy đủ 15 giây** (đồng hồ máy lệch): "Quảng cáo chưa xem xong." và đếm thêm vài giây.
- **Lượt xem hết hạn** (quá 10 phút, qua 0:00, hoặc đã mở lượt xem khác ở tab khác): "Lượt xem này đã hết hạn. Hãy xem lại." và nút "Xem" mở lượt mới.
- **Vừa nhận:** dòng nhiệm vụ đổi sang "Đã nhận", dòng tổng cộng thêm, thông báo "+5 coin".
- **Qua 0:00 khi đang mở trang:** lần làm mới kế tiếp (quay lại tab) hiện tiến độ mới.
- **Chủ máy:** "Tài khoản quản lý không tốn coin nên không có nhiệm vụ."
- **Lỗi:** câu lỗi + "Chi tiết" + "Thử lại".

## Tính năng

- [Nhiệm vụ ngày và quảng cáo mẫu](../features/F45-nhiem-vu-ngay.md)

Chi tiết: [docs/coins.md §6, §10](../../docs/coins.md).
