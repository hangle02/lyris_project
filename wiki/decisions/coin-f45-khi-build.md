# Coin F45: các điểm tạm chọn khi build

- **Ngày:** 2026-11-14 · **Ai quyết:** AI khi build F45 (mọi điểm dưới đây là **tạm chọn**, PO đổi được)

## Bối cảnh

Khi build [F45](../features/F45-nhiem-vu-ngay.md) theo [docs/coins.md §6, §7](../../docs/coins.md) và quyết định
[nhiem-vu-va-quang-cao-mau](nhiem-vu-va-quang-cao-mau.md), vài chỗ thiết kế chưa nói rõ. Ghi lại để PO thấy.

## Lựa chọn

- **Chủ máy và `LYRIS_COINS=0`:** `GET /api/coins/missions` trả `missions: []` (chủ máy kèm `unlimited: true`); gọi
  `ads/start`, `ads/{id}/claim` hay `missions/{…}/claim` thì 409 `no_missions` "Tài khoản này không có nhiệm vụ.". Phản hồi
  của `GET /api/coins/missions` có thêm `unlimited` và `enabled` (như ví) để giao diện biết khi nào hiện câu của chủ máy.
- **`POST /api/coins/missions/ad/claim` không có:** đường dẫn chỉ nhận `characters` hoặc `turns` (khác: 422). Quảng cáo chỉ
  nhận trong hộp, qua `ads/{id}/claim`.
- **Thứ tự kiểm khi nhận quảng cáo:** không có / của người khác (404) → đã nhận (trả kết quả cũ) → đã huỷ, quá 10 phút, khác
  ngày coin (`ad_expired`) → chưa đủ 15 giây (`ad_not_finished`) → đã 3 lần (`ad_limit`) → trần 30 (`mission_cap`). Lượt
  đã huỷ thì báo "hết hạn" ngay, không bảo "chưa xem xong" (vì không bao giờ nhận được nữa).
- **Tiến độ tính theo ngày coin của giữ chỗ** (`coin_holds.coin_day`, lúc bắt đầu sinh). Câu trả lời bắt đầu lúc 23:59:59
  và xong sau 0:00 được tính cho hôm trước.
- **Số quảng cáo đã nhận đếm trong sổ** (`coin_ledger`, khoá `mission:<tài khoản>:<ngày>:ad:<n>`), không đếm `coin_ad_views`:
  sổ là nguồn sự thật. Hai lượt xem cùng nhận song song (chỉ xảy ra nếu chỉ mục "một lượt xem mở" bị gỡ) vẫn chỉ một lần
  thành công, vì đếm và ghi nằm trong cùng `BEGIN IMMEDIATE` (test gỡ chỉ mục để chứng minh).
- **"Xem" bị khoá khi phần thưởng sẽ vượt 30** (đã nhận 26 coin trở lên trong ngày), không chỉ khi đủ đúng 30; server vẫn là
  nơi kiểm cuối (`mission_cap`).
- **Hộp "Quảng cáo mẫu":** đóng ngay sau khi nhận, trang báo "+5 coin" và tải lại tiến độ. Lượt xem hết hạn: hộp báo "Lượt
  xem này đã hết hạn. Hãy xem lại." với nút "Xem" mở lượt mới. Server báo "chưa xem xong" (đồng hồ máy nhanh hơn server):
  hộp đếm thêm 3 giây rồi mở khoá lại. "Đóng", nút X, Esc hay chạm ra ngoài khi chưa nhận đều gọi `cancel`.
- **Nội dung quảng cáo mẫu:** một khung story mẫu của Hạ Vy (dẫn truyện, một câu thoại, một suy nghĩ) và giới thiệu "Đọc suy
  nghĩ của nhân vật". Ảnh là ảnh nhân vật mẫu có sẵn trong repo, tải từ chính app (`/api/templates/ha-vy/image`).
- **Bot chờ 15 giây thật.** Thiết kế muốn server giả của bot dựng app với `ad_seconds=2`, nhưng `environment/fake-server.py`
  không được sửa trong lượt build này. Check bot đợi nút "Nhận 5 coin" mở khoá (tối đa 30 giây), nên chạy đúng với cả 15 lẫn
  2 giây. Bản vá đề xuất (một dòng `ad_seconds=2`) để chủ dự án quyết.

## Nguồn

- [docs/coins.md §6, §7](../../docs/coins.md)
- `backend/lyris/coins/missions.py`, `backend/tests/test_coins_missions.py`, `frontend/src/pages/coins/missionsLogic.ts`
