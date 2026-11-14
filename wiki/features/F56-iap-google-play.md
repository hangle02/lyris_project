# F56 — Mua coin trong app: Apple IAP và Google Play Billing

- **Trạng thái:** xem `memory/features.json` · **Phase:** Máy chủ (sau khi nộp bài)
- **Giai đoạn:** Kế hoạch
- **Màn hình:** Nạp coin (`#/coins/top-up`, [top-up](../screens/top-up.md)): trong app, mỗi gói có nút mua với giá do
  App Store / Google Play trả về.

## Là gì

Trên iOS, coin chỉ bán bằng Apple In-App Purchase (gói consumable); trên Android bằng Google Play Billing (PO 5A). Server tự
xác minh từng giao dịch rồi ghi một dòng `purchase` vào sổ coin chỉ thêm; hoàn tiền thành dòng âm. Thiết kế:
[docs/server.md §11](../../docs/server.md).

## Hoạt động thế nào

- Gói: `<bundle-id>.coins.p100`, `p550`, `p1200`, `p2500` (số coin như [docs/coins.md §4.1](../../docs/coins.md)).
- iOS: StoreKit 2 với `appAccountToken` = token IAP ngẫu nhiên của tài khoản; app gửi JWS cho server; chỉ `finish()` sau
  khi server trả 200. Thông báo App Store Server Notifications V2 cho `ONE_TIME_CHARGE` (cộng coin khi app không kịp gửi),
  `REFUND`, `REFUND_REVERSED`, `CONSUMPTION_REQUEST`.
- **Cộng cho chủ giao dịch:** giao dịch có `appAccountToken` / `obfuscatedExternalAccountId` của tài khoản A mà app đang
  đăng nhập B → vẫn cộng cho A và trả 200 (để app `finish()`/`consume`, giao dịch không kẹt mãi). Không có mã (promoted
  IAP, offer code) → cộng cho tài khoản của phiên. Chỉ trả 400 khi chữ ký, `bundleId`/gói hay `productId` sai.
- Android: server gọi `purchases.products.get`, cộng coin, rồi `consume`; RTDN `oneTimeProductNotification` cho giao dịch
  muộn, `voidedPurchaseNotification` cho hoàn tiền; poll Voided Purchases mỗi giờ chỉ là dự phòng.
- `idem_key` = `apple:{transactionId}` / `google:{sha256(purchaseToken)}` (mã khuyến mãi của Google không có `orderId`):
  gửi lại không cộng lần hai.
- Hoàn tiền: chỉ trừ tới `số dư − giữ chỗ đang mở`, phần thiếu ghi `debt` và `shortfall` của biên nhận, lần cộng sau trả nợ
  trước (tạm chọn). Có nợ vẫn mua được.
- Giao dịch sandbox trên bản production được cộng cho mọi tài khoản (người duyệt của Apple có thể tạo tài khoản mới lúc
  duyệt), biên nhận ghi `sandbox`, không tính doanh thu, trần 3 giao dịch/ngày/tài khoản.
- App không nhắc, không dẫn link tới thanh toán web (App Store 3.1.1).

## Done when

- [ ] Unit: JWS giao dịch Apple hợp lệ (ký bằng chuỗi chứng chỉ test) → 1 biên nhận `credited` và 1 dòng sổ `purchase` với `idem_key = apple:{transactionId}`; gửi lại cùng JWS → 200, số dư không đổi (`test_apple_transaction_credit_idempotent`).
- [ ] Unit: JWS sai chữ ký, sai `bundleId`, hoặc sai `productId` → 400, 0 dòng sổ (`test_apple_transaction_rejects_forged`).
- [ ] Unit: JWS hợp lệ có `appAccountToken` của tài khoản A gửi từ phiên của tài khoản B → 200, đúng 1 dòng sổ `purchase` trong ví của A, ví B không đổi; JWS không có `appAccountToken` → cộng cho B (`test_apple_credit_goes_to_token_owner`).
- [ ] Unit: thông báo `ONE_TIME_CHARGE` (JWS ký bằng chứng chỉ test) cho một giao dịch app chưa gửi → cộng 1 lần; app gửi JWS cùng giao dịch sau đó → 200, vẫn 1 dòng sổ (`test_apple_one_time_charge_notification_credits_once`).
- [ ] Unit: thông báo `REFUND` cho gói 100 coin khi số dư còn 50 → dòng sổ `purchase_refund` −50, `debt` = 50, `shortfall` của biên nhận = 50; lần cộng sau +300 → dòng `debt_repay` −50 và số dư 250 (`test_apple_refund_negative_entry_and_debt`).
- [ ] Unit: số dư 20 và đang có một giữ chỗ 6 coin mở; `REFUND` 100 coin → dòng sổ `purchase_refund` −14 (không phải −20), `debt` = 86; lượt đang sinh vẫn trừ được 6 coin và lưu được câu trả lời (`test_refund_respects_open_hold`).
- [ ] Unit: tài khoản có `debt` > 0 vẫn tạo được đơn mua trên web và mua IAP; khoản mua trả nợ trước (`test_purchase_allowed_while_in_debt`).
- [ ] Unit: giao dịch `environment = Sandbox` ở bản production được cộng cho một tài khoản vừa tạo, biên nhận ghi `sandbox`, không vào tổng doanh thu; giao dịch sandbox thứ 4 trong ngày của cùng tài khoản → 429, 0 dòng sổ (`test_apple_sandbox_flagged_and_capped`).
- [ ] Unit: `purchases.products.get` giả trả `purchaseState = 0` → cộng 1 lần với `idem_key = google:{sha256(purchaseToken)}` rồi gọi `consume`; RTDN cùng giao dịch đến trước app → vẫn chỉ 1 dòng sổ; giao dịch đổi mã khuyến mãi không có `orderId` vẫn cộng đúng 1 lần (`test_google_purchase_credit_consume_once`).
- [ ] Unit: RTDN `voidedPurchaseNotification` cho 1 giao dịch → 1 dòng sổ âm ngay; Voided Purchases poll 3 lần sau đó → vẫn đúng 1 dòng sổ âm (`test_google_voided_refund_once`).
- [ ] Unit: sau 100 lần mua/hoàn ngẫu nhiên (có lúc đang có giữ chỗ mở), `ledger_audit` thấy mọi ví có `balance` = tổng `delta` của sổ và `debt` = `Σ shortfall − Σ |debt_repay|` (`test_ledger_audit_after_purchases`).
- [ ] Bot: với plugin IAP giả trên vỏ native, `#/coins/top-up` có 4 nút mua mang giá do plugin trả; bấm nút của gói 100 coin → chip coin tăng 100; màn không có chữ `VNPay`, `MoMo` hay link mua ngoài app.

## Tests

- `backend/tests/test_iap_apple.py::test_apple_transaction_credit_idempotent`
- `backend/tests/test_iap_apple.py::test_apple_transaction_rejects_forged`
- `backend/tests/test_iap_apple.py::test_apple_credit_goes_to_token_owner`
- `backend/tests/test_iap_apple.py::test_apple_one_time_charge_notification_credits_once`
- `backend/tests/test_iap_apple.py::test_apple_refund_negative_entry_and_debt`
- `backend/tests/test_payments_ledger.py::test_refund_respects_open_hold`
- `backend/tests/test_payments_ledger.py::test_purchase_allowed_while_in_debt`
- `backend/tests/test_iap_apple.py::test_apple_sandbox_flagged_and_capped`
- `backend/tests/test_iap_google.py::test_google_purchase_credit_consume_once`
- `backend/tests/test_iap_google.py::test_google_voided_refund_once`
- `backend/tests/test_payments_ledger.py::test_ledger_audit_after_purchases`
- bot: mua coin trong app bằng IAP giả

## Ngoài Done when

Không chặn ✅: mua và hoàn tiền thật bằng tài khoản sandbox Apple và license tester Google trên thiết bị; khai sản phẩm trong
App Store Connect và Play Console; Điều khoản bán coin mới (đổi `LEGAL_VERSION`).

## Liên quan

- **Tài liệu:** [docs/server.md §11, §16.4](../../docs/server.md), [docs/coins.md §4, §12](../../docs/coins.md)
- **Code hiện tại:** [`coins/ledger.py`](../../backend/lyris/coins/ledger.py), [`coins/topup.py`](../../backend/lyris/coins/topup.py), [`api/routes_coins.py`](../../backend/lyris/api/routes_coins.py)
- **Tính năng:** [F42](F42-vi-coin.md), [F43](F43-nap-coin.md), [F55](F55-app-ios-android.md), [F57](F57-vnpay-momo.md)
- **Quyết định:** [thanh-toan-iap-va-cong-vn](../decisions/thanh-toan-iap-va-cong-vn.md), [nap-coin-che-do-thu](../decisions/nap-coin-che-do-thu.md)
