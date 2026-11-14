# Chủ máy không tốn coin

- **Ngày:** 2026-11-14 · **Ai quyết:** người dùng (chủ máy không tốn coin) + thiết kế (phần ghi "(tạm chọn)")

## Bối cảnh

Lyris chạy trên máy của chủ máy, chủ máy trả tiền điện và máy. Chủ dự án chọn 5A: chủ máy không tốn coin ([raw](../raw/2026-11-14-coin-tra-loi.md)). README hứa "tự chạy trên máy mình vẫn miễn phí".

## Lựa chọn

- Tài khoản `role = 'owner'` không có giữ chỗ, không có dòng sổ khi chat (kể cả chat thử ở Studio), không có ví (thiết lập chủ máy không qua `insert_member`); `GET /api/coins/wallet` trả `unlimited: true`.
- Chủ máy cũng không nhận quà tạo tài khoản, quà đăng nhập, nhiệm vụ hay thưởng sáng tác (không cần coin). Nhân vật của chủ máy vẫn được đếm người chơi và ghi mốc, nhưng không có coin (tạm chọn). Từ khi F44 làm lại (2026-11-14 22:15, [xep-hang-nhan-vat-hot](xep-hang-nhan-vat-hot.md)): nhân vật của chủ máy có hạng trên bảng "Nhân vật hot", bậc được ghi `outcome = 'owner'`, không có coin, không có thưởng công khai lần đầu.
- Chủ máy chơi nhân vật công khai của người khác: **không** tính là người chơi của họ, để chủ máy (chat miễn phí) không tự tạo thưởng cho ai (tạm chọn).
- Giao diện: header của chủ máy không có chip coin; sheet Tài khoản ghi "Tài khoản quản lý không tốn coin." (tạm chọn).
- `LYRIS_COINS=0` tắt hẳn coin cho mọi người, dành cho người tự chạy Lyris cho bạn bè (tạm chọn, mặc định bật).

## Vì sao

Chủ máy là người vận hành, không phải khách. Chủ máy chat miễn phí nên mọi thứ chủ máy làm không được biến thành coin cho ai (kể cả chính mình), không thì đó là cửa in coin.

## Đã cân nhắc

- Chủ máy cũng tốn coin (5B): chủ dự án không chọn.
- Chip "Không giới hạn" cho chủ máy: thêm chữ vô ích trên header vốn đã chật.

## Nguồn

- [docs/coins.md §1, §5.1, §10.1](../../docs/coins.md)
- [F42](../features/F42-vi-coin.md), [F44](../features/F44-thuong-sang-tac.md)
