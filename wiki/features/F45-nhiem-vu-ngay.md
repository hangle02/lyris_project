# F45 — Nhiệm vụ ngày và quảng cáo mẫu

- **Trạng thái:** xem `memory/features.json` · **Phase:** Ra mắt (coin)
- **Giai đoạn:** Đã có
- **Màn hình:** [missions](../screens/missions.md) (kèm hộp "Quảng cáo mẫu")

## Là gì

Ba nhiệm vụ mỗi ngày cho thành viên kiếm thêm coin, tổng tối đa 30 coin/ngày: xem quảng cáo +5 (tối đa 3 lần), trò chuyện với 3 nhân vật khác nhau +10, gửi 20 lượt +5. Quảng cáo hiện là quảng cáo mẫu 15 giây, ghi rõ là mẫu; sau này thay bằng mạng quảng cáo thật.

## Hoạt động thế nào

- Mở "Nhiệm vụ" (`#/missions`) từ Ví coin hoặc từ khối "Bạn đã hết coin". Đầu trang: "Nhiệm vụ hôm nay" và "Đã nhận {x}/30 coin hôm nay".
- "Xem quảng cáo" (+5, "0/3"): bấm "Xem" mở hộp "Quảng cáo mẫu" đếm ngược 15 giây; hết giờ thì bấm "Nhận 5 coin". Bấm "Đóng" thì giao diện báo server huỷ lượt xem đó (`POST /api/coins/ads/{id}/cancel`), không nhận được nữa. Giới hạn biết trước: script gọi thẳng API đợi đủ 15 giây vẫn nhận được, tối đa 15 coin/ngày (quảng cáo mẫu không biết ai nhìn màn hình).
- "Trò chuyện với 3 nhân vật khác nhau" (+10): đếm nhân vật khác nhau đã trả lời mình trong ngày (bản sao nhân vật công khai tính theo nhân vật gốc). Đủ 3 thì bấm "Nhận".
- "Gửi 20 lượt" (+5): đếm câu trả lời đã trả coin của lượt gửi mới và "Trả lời", không tính "Tạo lại câu trả lời" (tạm chọn). Đủ 20 thì bấm "Nhận".
- Chat thử ở Studio không tính cho "3 nhân vật" hay "20 lượt" (tạm chọn).
- 0:00 giờ Việt Nam mọi nhiệm vụ làm lại từ đầu; thưởng chưa nhận của hôm qua mất.
- Chủ máy không có nhiệm vụ.

Kỹ thuật:

- Tiến độ tính từ `coin_holds` đã trừ trong ngày coin; nhận thưởng ghi `coin_ledger` với `idem_key = mission:<tài khoản>:<ngày>:<nhiệm vụ>`; trần 30 kiểm ở server mỗi lần nhận. `post_mission()` đọc tổng nhiệm vụ trong ngày, đếm số quảng cáo đã nhận, kiểm trần và ghi sổ trong **một** `BEGIN IMMEDIATE`.
- Quảng cáo: bảng `coin_ad_views` (có `cancelled_at`), server ghi giờ bắt đầu, chỉ cho nhận khi đã đủ 15 giây theo đồng hồ server. Mã lỗi: `ad_not_finished` (chưa đủ 15 giây), `ad_expired` (đã huỷ, quá 10 phút, khác ngày coin), `ad_limit`, `mission_cap`.
- Thiết kế đầy đủ: [docs/coins.md §6](../../docs/coins.md).

## Done when

- [ ] Unit: `GET /api/coins/missions` của thành viên trả 3 nhiệm vụ `ad` (target 3, reward 5), `characters` (target 3, reward 10), `turns` (target 20, reward 5), `cap: 30`; của chủ máy trả `missions: []`; tiến độ về 0 lúc 17:00Z (0:00 giờ Việt Nam).
- [ ] Unit: `POST /api/coins/ads/{id}/claim` gọi 14 giây sau `ads/start` (đồng hồ server giả) trả 409 `ad_not_finished` và không cộng; gọi lúc ≥ 15 giây cộng 5 một lần; claim lại cùng `ad_id` không cộng thêm; `ad_id` của tài khoản khác trả 404; claim sau `POST /api/coins/ads/{id}/cancel` (dù đã đủ 15 giây), sau 10 phút, hay sau 0:00 giờ Việt Nam so với lúc bắt đầu đều trả 409 `ad_expired` và không cộng; gọi `cancel` hai lần không lỗi; `ads/start` lần hai huỷ lượt xem dở trước đó.
- [ ] Unit: sau 3 lần nhận quảng cáo trong ngày coin, `POST /api/coins/ads/start` trả 409 `ad_limit` "Hôm nay bạn đã xem đủ 3 quảng cáo."; qua ngày coin mới lại xem được.
- [ ] Unit: `characters` đếm `char_key` khác nhau của giữ chỗ `charged` trong ngày coin: hai story cùng một nhân vật là 1, hai bản sao của cùng nhân vật công khai là 1, câu trả lời bị nhả không đếm; `turns` đếm 20 câu trả lời `send`/`retry` đã trừ, không đếm `regenerate`; câu trả lời chat thử (`mode = 'test'`) không đếm cho cả hai; claim khi chưa đủ trả 409 `mission_not_done`.
- [ ] Unit: nhận cùng một nhiệm vụ hai lần (hai tab cùng lúc, hai luồng gọi `post_mission` song song) chỉ có một dòng sổ; hai claim quảng cáo song song của hai lượt xem khác nhau khi đã nhận 2 lần chỉ một claim thành công (không bao giờ có lần thứ 4); tổng `delta` các dòng `kind = 'mission'` trong một ngày coin không bao giờ vượt 30 (kể cả khi thử thêm một nhiệm vụ giả +10 trong test, vượt thì 409 `mission_cap`); sự kiện `ad_started`, `mission_claimed`, `missions_viewed` đúng luật `events.py`.
- [ ] Unit: `missionsLogic.ts`: trạng thái hộp quảng cáo đi đúng thứ tự đang đếm → nhận được → đã nhận, nút 'Nhận 5 coin' khoá khi còn > 0 giây, đóng khi chưa nhận trả hành động `cancel`; dòng nhiệm vụ hiện "x/y", "Nhận" khi `claimable`, "Đã nhận" khi `claimed`.
- [ ] Bot: thành viên mở `#/missions` thấy tiêu đề 'Nhiệm vụ hôm nay', chữ 'Đã nhận' với '/30 coin hôm nay', ba dòng 'Xem quảng cáo', 'Trò chuyện với 3 nhân vật khác nhau', 'Gửi 20 lượt'; 390px không cuộn ngang.
- [ ] Bot: bấm 'Xem' ở 'Xem quảng cáo' mở hộp 'Quảng cáo mẫu' có câu 'chưa phải quảng cáo thật' và nút 'Nhận 5 coin' đang khoá; hết đếm ngược (15 giây theo đồng hồ server như app thật; server giả không rút ngắn) bấm 'Nhận 5 coin' thì dòng nhiệm vụ thành '1/3' và số dư ở `#/coins` tăng đúng 5.

## Tests

- backend/tests/test_coins_missions.py::test_missions_list_and_reset_at_vietnam_midnight
- backend/tests/test_coins_missions.py::test_ad_claim_needs_15_server_seconds
- backend/tests/test_coins_missions.py::test_cancelled_or_expired_ad_cannot_be_claimed
- backend/tests/test_coins_missions.py::test_ad_limit_3_per_day
- backend/tests/test_coins_missions.py::test_characters_and_turns_progress_rules
- backend/tests/test_coins_missions.py::test_claim_once_and_daily_cap_30
- frontend/src/pages/coins/missionsLogic.test.ts
- bot: Nhiệm vụ hôm nay có ba nhiệm vụ và trần 30 coin
- bot: quảng cáo mẫu đếm ngược rồi nhận 5 coin

## Ngoài Done when

Không chặn ✅.

- Thay quảng cáo mẫu bằng mạng quảng cáo thật: cần đồng ý quảng cáo cá nhân hoá, kê khai Chính sách, xác nhận phía server của mạng quảng cáo ([docs/coins.md §6.2, §12](../../docs/coins.md)).

## Liên quan

- **Tài liệu:** [docs/coins.md §6](../../docs/coins.md)
- **Quyết định:** [nhiem-vu-va-quang-cao-mau](../decisions/nhiem-vu-va-quang-cao-mau.md)
- **Tính năng liên quan:** [F42](F42-vi-coin.md)
