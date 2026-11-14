# Ví coin

- **Đường dẫn:** `#/coins` (Kế hoạch, [F42](../features/F42-vi-coin.md)). Mở từ chip coin trên header của ba tab chính, từ hàng "Coin" trong [sheet Tài khoản](account-sheet.md), hoặc link. · **File dự kiến:** `frontend/src/pages/coins/WalletPage.tsx`

## Dùng để làm gì

Thành viên xem mình còn bao nhiêu coin, coin đã đi đâu và lấy thêm coin ở đâu. Chủ máy không tốn coin nên trang chỉ ghi một câu.

## Có gì trên màn hình

Ở điện thoại 390px, từ trên xuống. Không có thanh tab nổi.

1. **Header phụ** (`SubpageHeader`): "Về Tương tác", tiêu đề **"Ví coin"**.
2. **Khối số dư** (`Card`): icon coin màu `accent-2`, số dư lớn (font tiêu đề, ví dụ "1.200"), chữ "coin". Dòng phụ `muted`: "Mỗi câu trả lời của nhân vật tốn 6 coin."
3. **Hai nút**: **"Nạp coin"** (nút chính, mở [Nạp coin](top-up.md)) và **"Nhiệm vụ"** (nút phụ, mở [Nhiệm vụ](missions.md)), cùng hàng, mỗi nút cao 44px.
4. **"Lịch sử"**: danh sách dòng mới nhất trước. Mỗi dòng: chữ (ví dụ "Quà tạo tài khoản", "3 câu trả lời của Hạ Vy", "Nhiệm vụ: Xem quảng cáo", "Hạ Vy vào top 10 Nhân vật hot" và "Thưởng công khai nhân vật lần đầu" (F44 làm lại; dòng cũ "Hạ Vy đạt 10 người chơi" vẫn hiện), "Nạp bằng mã", "Người quản lý điều chỉnh: …"), giờ ("23:15", "Hôm qua"), số coin bên phải: "+300" màu `ok`, "−18" màu `muted`. Các câu trả lời liền nhau cùng story cùng ngày được gộp làm một dòng. Cuối danh sách: nút "Xem thêm" (30 dòng mỗi lần).

Từ 640px: cột giữa rộng tối đa 560px; hai nút giữ cùng hàng.

## Trạng thái

- **Đang tải:** khung xương khối số dư và 4 dòng lịch sử.
- **Lịch sử rỗng:** "Chưa có gì trong lịch sử."
- **Hết coin** (số dư < 6): khối số dư thêm dòng "Bạn đã hết coin. Nạp coin hoặc làm nhiệm vụ để trò chuyện tiếp."
- **Chủ máy:** không có số dư, nút hay lịch sử; chỉ "Tài khoản quản lý không tốn coin."
- **Coin đang tắt** (`LYRIS_COINS=0`): mở đường dẫn này thì về [Tương tác](hub.md).
- **Lỗi:** câu lỗi + "Chi tiết" + "Thử lại".

## Tính năng

- [Ví coin và tiêu coin khi chat](../features/F42-vi-coin.md)
- [Nạp coin](../features/F43-nap-coin.md), [Nhiệm vụ ngày](../features/F45-nhiem-vu-ngay.md), [Thưởng sáng tác](../features/F44-thuong-sang-tac.md) (dòng trong lịch sử)

Chi tiết: [docs/coins.md §10](../../docs/coins.md).
