# F43 — Nạp coin (chế độ thử, mã nạp)

- **Trạng thái:** xem `memory/features.json` · **Phase:** Ra mắt (coin)
- **Giai đoạn:** Đã có
- **Màn hình:** [top-up](../screens/top-up.md), [admin](../screens/admin.md) (tab "Coin", "Cộng/trừ coin")

## Là gì

Màn "Nạp coin" có các gói giá, nhưng đang ở chế độ thử: Lyris chưa bán coin, giá chỉ là "Giá dự kiến" khi ra mắt. Người quản lý (chủ máy) tặng mã nạp dùng một lần hoặc cộng/trừ coin tay cho thành viên, kèm lý do. Mã nạp được tặng, không bán. Cổng thanh toán thật chỉ nối khi ra mắt.

## Hoạt động thế nào

- Thành viên mở "Nạp coin" (`#/coins/top-up`) từ Ví coin hay từ khối "Bạn đã hết coin". Màn ghi rõ "Chế độ thử: Lyris chưa bán coin. Nhập mã nạp người quản lý tặng bạn."
- Bốn gói, ghi "Giá dự kiến" (giá PO chốt 2026-11-14): 100 coin 10.000đ · 550 coin 50.000đ · 1.200 coin 100.000đ · 2.500 coin 200.000đ. Chạm gói chỉ mở hộp giải thích "Giá dự kiến khi Lyris ra mắt…" với nút "Đóng": không có thanh toán, không có nút liên hệ trên gói (để gói không thành kênh bán coin ngoài app).
- Thành viên nhập mã vào ô "Mã nạp", bấm "Dùng mã": đúng thì "Đã nạp {n} coin.", sai/hết hạn/đã dùng thì cùng một câu "Mã nạp không đúng hoặc đã hết hạn."
- Chủ máy vào `#/admin` → "Coin" → "Tạo mã nạp": chọn gói hoặc số coin, ghi chú, hạn 1/7/30 ngày. Mã hiện một lần, dùng một lần.
- Chủ máy cộng/trừ coin cho một thành viên ở "Thành viên" → "…" → "Cộng/trừ coin", bắt buộc ghi lý do. Không trừ quá số coin dùng được (số dư trừ 6 coin đang giữ cho câu trả lời đang chạy), để câu trả lời đang chạy không bao giờ hỏng.
- Mọi lần nạp, điều chỉnh và thưởng mốc sáng tác có trong "Nhật ký" của chủ máy; nạp và điều chỉnh có trong lịch sử ví của thành viên.

Kỹ thuật:

- Bảng `coin_topup_codes`, `coin_code_attempts` (migration `0012_coins.sql`); gói trong `lyris/coins/packs.py`.
- Mã như mã mời: 12 ký tự base32, chỉ lưu hash (`auth/codes.py`). 10 lần nhập sai mỗi giờ thì 429. Dòng `coin_code_attempts` quá 30 ngày được xoá ngay lúc ghi lần thử mới (không cần việc nền).
- Trừ tay kiểm và ghi trong một transaction; cùng `request_id` mà khác số coin thì 409 `idem_conflict`.
- Thiết kế đầy đủ: [docs/coins.md §4](../../docs/coins.md). Điểm tạm chọn khi build: [coin-f43-khi-build](../decisions/coin-f43-khi-build.md).
- Code: `lyris/coins/packs.py`, `lyris/coins/topup.py`, `CoinService` (`lyris/coins/wallet.py`), `api/routes_coins.py`; giao diện `pages/coins/TopUpPage.tsx` + `topupLogic.ts`, `pages/admin/CoinView.tsx` + `adminCoinLogic.ts`.

## Done when

- [ ] Unit: `GET /api/coins/packs` trả `test_mode: true` và đúng 4 gói `p100`, `p550`, `p1200`, `p2500` với `coins` 100/550/1200/2500 và `price_vnd` 10000/50000/100000/200000; tập route của app có đường dẫn bắt đầu bằng `/api/coins/` hay `/api/admin/coins/` (cộng `POST /api/admin/accounts/{id}/coins`) đúng bằng danh sách ở [docs/coins.md §7](../../docs/coins.md), không thừa route nào.
- [ ] Unit: `POST /api/admin/coins/codes` (chủ máy) tạo mã 12 ký tự, DB chỉ có `code_hash` và `code_hint`; `GET /api/admin/coins/codes` không bao giờ trả mã đầy đủ; thành viên gọi route `/api/admin/coins/*` nhận 403 `owner_only`; khi đã có 50 mã còn hiệu lực, tạo mã thứ 51 trả 422 `topup_code_limit`, huỷ một mã thì tạo lại được.
- [ ] Unit: `POST /api/coins/redeem` với mã đúng cộng đúng `amount` một lần (`topup:<code_id>`); dùng lại, hết hạn, đã huỷ, không có thật → cùng 422 `topup_code_invalid` "Mã nạp không đúng hoặc đã hết hạn."; mã được chuẩn hoá (viết thường, gạch ngang của iPhone, khoảng trắng); hai tài khoản nhập cùng mã cùng lúc chỉ một tài khoản được cộng.
- [ ] Unit: 10 lần nhập sai trong 60 phút thì lần thứ 11 trả 429 `rate_limited`, kể cả khi mã đúng; dòng `coin_code_attempts` cũ hơn 30 ngày bị xoá khi ghi lần thử mới; chủ máy nhập một mã còn hiệu lực trả 422 `topup_code_owner` và mã vẫn còn hiệu lực.
- [ ] Unit: `POST /api/admin/accounts/{id}/coins` cần `reason` 3–120 ký tự (thiếu thì 422); trừ quá số coin dùng được trả 422 `adjust_too_large` "Không trừ được quá số coin dùng được ({n} coin)."; cùng `request_id` gửi hai lần cùng `delta` chỉ ghi một dòng, khác `delta` trả 409 `idem_conflict`; dòng sổ có `actor_id` của chủ máy; áp dụng cho chủ máy trả 422.
- [ ] Unit: thành viên có 10 coin đang chờ một câu trả lời (6 coin giữ chỗ, dùng được 4): chủ máy trừ 5 trả 422 `adjust_too_large` với `n = 4`, trừ 4 thì được; câu trả lời sau đó vẫn được lưu và trừ 6, số dư cuối là 0.
- [ ] Unit: `GET /api/admin/coins/log` có 50 dòng mới nhất của `topup_code`, `admin_adjust` và `creator_milestone` (test ghi một dòng `creator_milestone` bằng `post()`) và ba tổng 30 ngày; không có `story_id`, tên nhân vật hay nội dung tin nhắn; sự kiện `topup_code_redeemed`, `topup_code_failed`, `topup_code_created`, `coins_adjusted` đúng luật `events.py`.
- [ ] Unit: `topupLogic.ts`: `formatVnd(50000)` = "50.000đ"; chuẩn hoá mã giống `inviteCode.ts`; `adminCoinLogic.ts` kiểm số coin 1–10.000 và lý do 3–120 ký tự trước khi gửi.
- [ ] Bot: thành viên mở `#/coins/top-up` thấy tiêu đề 'Nạp coin', câu có 'Chế độ thử' và 'chưa bán coin', 4 thẻ gói có 'coin', 'đ' và 'Giá dự kiến', ô có aria-label 'Mã nạp' và nút 'Dùng mã'; chạm thẻ '100 coin' mở hộp có 'Giá dự kiến khi Lyris ra mắt' và chỉ có nút 'Đóng' (không có nút thanh toán hay 'Liên hệ'); 390px không cuộn ngang.
- [ ] Bot: chủ máy mở `#/admin`, chọn 'Coin', bấm 'Tạo mã nạp', chọn gói 100 coin, bấm 'Tạo mã' thì hộp 'Mã nạp mới' hiện mã kèm 'Sao chép mã'; thành viên nhập mã đó ở `#/coins/top-up`, bấm 'Dùng mã' thì thấy 'Đã nạp 100 coin.' và số dư ở `#/coins` tăng đúng 100.
- [ ] Bot: chủ máy ở `#/admin` mở '…' của một thành viên, chọn 'Cộng/trừ coin', nhập 20 và lý do 'thử bot', bấm 'Lưu' thì hàng thành viên đó có số coin tăng 20 và 'Nhật ký' có dòng 'thử bot'.

## Tests

- backend/tests/test_coins_topup.py::test_packs_are_test_mode_with_vnd_prices
- backend/tests/test_coins_topup.py::test_coin_routes_are_exactly_the_documented_list
- backend/tests/test_coins_topup.py::test_owner_creates_code_shown_once_hash_stored
- backend/tests/test_coins_topup.py::test_at_most_50_active_codes
- backend/tests/test_coins_topup.py::test_member_gets_403_on_admin_coin_routes
- backend/tests/test_coins_topup.py::test_redeem_once_same_error_for_used_expired_revoked_unknown
- backend/tests/test_coins_topup.py::test_concurrent_redeem_credits_one_account
- backend/tests/test_coins_topup.py::test_redeem_rate_limited_after_10_failures
- backend/tests/test_coins_topup.py::test_owner_cannot_redeem_code
- backend/tests/test_coins_topup.py::test_owner_adjust_requires_reason_and_never_negative
- backend/tests/test_coins_topup.py::test_adjust_during_open_hold_keeps_reply_and_charge
- backend/tests/test_coins_topup.py::test_admin_coin_log_has_no_story_content
- frontend/src/pages/coins/topupLogic.test.ts
- frontend/src/pages/admin/adminCoinLogic.test.ts
- bot: Nạp coin có gói giá chế độ thử và ô mã nạp
- bot: chủ máy tạo mã nạp, thành viên dùng mã thì ví tăng
- bot: chủ máy cộng coin cho thành viên có lý do

## Ngoài Done when

Không chặn ✅ (còn là kế hoạch).

- Cổng thanh toán thật (cổng được cấp phép ở Việt Nam trên web; Google Play Billing / Apple In-App Purchase nếu bọc app), hoá đơn, chính sách hoàn tiền: chỉ làm khi ra mắt, cần quyết định của PO ([docs/coins.md §12](../../docs/coins.md)).

## Liên quan

- **Tài liệu:** [docs/coins.md §4](../../docs/coins.md), [auth.md §1.3](../../docs/auth.md) (mã mời, cùng cách làm)
- **Quyết định:** [nap-coin-che-do-thu](../decisions/nap-coin-che-do-thu.md)
- **Tính năng liên quan:** [F30](F30-quan-ly-tai-khoan.md) (trang quản trị), [F42](F42-vi-coin.md)
