# Coin F42: các điểm tạm chọn khi build

- **Ngày:** 2026-11-14 · **Ai quyết:** AI khi build F42 (mọi điểm dưới đây là **tạm chọn**, PO đổi được)

## Bối cảnh

Khi build [F42](../features/F42-vi-coin.md) theo [docs/coins.md](../../docs/coins.md), vài chỗ thiết kế chưa nói rõ hoặc va
với code và test có sẵn. Ghi lại để PO thấy và để F43–F45 làm tiếp cho khớp.

## Lựa chọn

- **Quà đăng nhập khi coin tắt** (`LYRIS_COINS=0`): không cộng +60 (tạm chọn). Quà tạo tài khoản +300 vẫn ghi như
  thiết kế (§3.4) để bật lại coin thì như mọi người. Câu hỏi đã ghi ở `memory/po-questions.md`.
- **Đăng nhập bằng mật khẩu** gọi đúng hàm quà đăng nhập (§3.4), nên khi app mở sau đó thì `checkin` trả `granted: false`.
  Để thông báo "+60 coin cho hôm nay" vẫn hiện đúng một lần mỗi ngày, `checkin` trả thêm `today` (quà của hôm nay, 60
  hoặc 0) và trình duyệt nhớ ngày đã báo (`localStorage`, theo tài khoản). Đổi tài khoản thì báo lại một lần.
- **`POST /api/admin/accounts/{id}/coins` có từ F42** (§4.4: lý do 3–120 ký tự, trừ tối đa số coin dùng được, cùng
  `request_id` không ghi hai lần, chủ máy 422). Bot dùng route này qua HTTP để đưa `@hetcoin` về 0 coin, thay vì sửa
  `environment/fake-server.py`. Giao diện "Cộng/trừ coin", sự kiện `coins_adjusted` và test của route là phần của F43.
- **`#/coins/top-up` và `#/missions`** có trang tạm (tiêu đề, một câu "sắp có") để nút "Nạp coin", "Nhiệm vụ" ở Ví coin
  và ở khối "Bạn đã hết coin" không đưa người dùng về hub. F43 và F45 thay bằng màn thật.
- **Migration `0012_coins.sql` tạo luôn bảng của F43–F45** (mã nạp, lần thử mã, quảng cáo mẫu, người chơi, mốc), đúng
  như §2, để không phải thêm migration thứ hai.
- **Test F34 đếm sự kiện**: `test_catalog_is_focused_snake_case_and_documented` trước đây chặn cứng "≤ 40 sự kiện", nên
  không thêm được 5 sự kiện coin mà §11 yêu cầu. Test giờ so số sự kiện với con số `tracking-plan.md` §4 công bố
  ("**45 events.**") và vẫn có trần (60). `test_auth_events_link_anon_to_account` thêm hai dòng `coins_granted` (quà
  tạo tài khoản, quà đăng nhập) vào đúng thứ tự sự kiện; các dòng cũ giữ nguyên thứ tự.
- **Chip coin** là một link 44px bọc viên thuốc 32px `surface-2` (bot đo nút header ≥ 44px). Khối "Bạn đã hết coin"
  thay chỗ banner trên ô nhập (Story, DM, chat thử ở Studio).

## Nguồn

- [docs/coins.md](../../docs/coins.md) §2, §3.4, §4.4, §10, §11
- [F42](../features/F42-vi-coin.md), [F34](../features/F34-theo-doi-su-kien.md)
