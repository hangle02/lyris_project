# F57 — Nạp coin trên web bằng VNPay và MoMo

- **Trạng thái:** xem `memory/features.json` · **Phase:** Máy chủ (sau khi nộp bài)
- **Giai đoạn:** Kế hoạch
- **Màn hình:** Nạp coin (`#/coins/top-up`) trên web: chọn gói → chọn VNPay hoặc MoMo → trang cổng → quay về thấy kết quả.

## Là gì

Trên web, coin bán qua cổng thanh toán Việt Nam (PO 5A). Coin chỉ được cộng khi IPN (server-to-server) của cổng có chữ
ký đúng và số tiền khớp đơn; vào cùng sổ coin với IAP. Thiết kế: [docs/server.md §11.5, §11.6](../../docs/server.md).

## Hoạt động thế nào

- `POST /api/payments/web/orders` tạo đơn `pending` (hết hạn 15 phút) và trả URL thanh toán đã ký
  (VNPay HMAC-SHA512, MoMo HMAC-SHA256).
- IPN: kiểm chữ ký → đơn có thật → số tiền khớp → một transaction: đơn `paid`, biên nhận, dòng sổ
  `idem_key = vnpay:{vnp_TxnRef}` / `momo:{orderId}`. Trả mã đúng đặc tả để cổng ngừng gửi lại.
- `vnp_Amount` = số tiền VND × 100; lưu `vnp_CreateDate` của đơn (`querydr` cần nó).
- IPN báo giao dịch **thất bại** (huỷ, thẻ bị từ chối) → đơn `failed`, không ghi sổ, vẫn trả `00` (đã nhận xong).
- Trang quay về là đường thật `/pay/return` (không phải `#/…`, vì cổng nối query vào sau URL), chuyển hướng sang
  `#/coins/top-up?order=…`; chỉ hỏi trạng thái đơn, không bao giờ cộng coin.
- Đơn treo > 15 phút: job tra cứu (`querydr` của VNPay với ngày tạo đã lưu, query của MoMo).
- Giới hạn 5 đơn `paid` và 2.000.000đ mỗi ngày mỗi tài khoản (tạm chọn); hoàn tiền qua staff thành dòng sổ âm.

## Done when

- [ ] Unit: `POST /api/payments/web/orders {"pack_id": "p100", "provider": "vnpay"}` → đơn `pending` 10.000đ, URL có `vnp_Amount=1000000` (số tiền × 100), `vnp_ReturnUrl` là `https://…/pay/return` (không có `#`), `vnp_SecureHash` HMAC-SHA512 đúng với khoá test, và đơn lưu `vnp_CreateDate` (`test_vnpay_order_url_signed`).
- [ ] Unit: IPN đúng chữ ký và số tiền → `RspCode = 00` và 1 dòng sổ `vnpay:{vnp_TxnRef}`; IPN lặp lại → `RspCode = 02`, vẫn 1 dòng sổ (`test_vnpay_ipn_idempotent`).
- [ ] Unit: IPN sai chữ ký → `97`, sai số tiền → `04`, không có đơn → `01`; cả ba không ghi sổ (`test_vnpay_ipn_rejects`).
- [ ] Unit: IPN đúng chữ ký báo giao dịch thất bại (`vnp_ResponseCode = 24`, người dùng huỷ) → `RspCode = 00`, đơn `failed`, 0 dòng sổ; IPN thành công tới sau cho cùng đơn → `02`, không cộng (`test_vnpay_ipn_failed_payment_acknowledged`).
- [ ] Unit: gọi `/pay/return` với tham số "thành công" khi chưa có IPN → 302 tới `#/coins/top-up?order=…`, 0 dòng sổ, đơn vẫn `pending` (`test_return_url_never_credits`).
- [ ] Unit: IPN MoMo `resultCode = 0` chữ ký HMAC-SHA256 đúng → cộng 1 lần, trả HTTP 204; gửi lại → không cộng (`test_momo_ipn_idempotent`).
- [ ] Unit: đơn `pending` quá 15 phút → `querydr` giả (nhận đúng `vnp_TransactionDate` = `vnp_CreateDate` đã lưu) trả thành công → `paid` và cộng; trả thất bại → `expired`, không cộng (`test_pending_order_reconcile`).
- [ ] Unit: đơn thứ 6 trong một ngày của cùng tài khoản → 429 (`test_web_purchase_daily_limit`).
- [ ] Bot: ở `#/coins/top-up` trên web bấm gói 100 coin → trang cổng VNPay giả → quay về thấy "+100 coin" và chip coin tăng 100.

## Tests

- `backend/tests/test_pay_vnpay.py::test_vnpay_order_url_signed`
- `backend/tests/test_pay_vnpay.py::test_vnpay_ipn_idempotent`
- `backend/tests/test_pay_vnpay.py::test_vnpay_ipn_rejects`
- `backend/tests/test_pay_vnpay.py::test_vnpay_ipn_failed_payment_acknowledged`
- `backend/tests/test_pay_vnpay.py::test_return_url_never_credits`
- `backend/tests/test_pay_momo.py::test_momo_ipn_idempotent`
- `backend/tests/test_pay_reconcile.py::test_pending_order_reconcile`
- `backend/tests/test_pay_reconcile.py::test_web_purchase_daily_limit`
- bot: nạp coin qua cổng VNPay giả

## Ngoài Done when

Không chặn ✅: 7 ngày sandbox VNPay/MoMo đối soát khớp 100 %; hợp đồng merchant, hoá đơn điện tử, chính sách hoàn tiền
(việc của pháp nhân phát hành, [docs/server.md §20](../../docs/server.md)).

## Liên quan

- **Tài liệu:** [docs/server.md §11](../../docs/server.md), [docs/coins.md §4, §12](../../docs/coins.md), [docs/compliance.md §5.4](../../docs/compliance.md)
- **Tính năng:** [F43](F43-nap-coin.md), [F56](F56-iap-google-play.md)
- **Quyết định:** [thanh-toan-iap-va-cong-vn](../decisions/thanh-toan-iap-va-cong-vn.md)
