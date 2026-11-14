# Thanh toán: IAP trên app, VNPay/MoMo trên web, chung một sổ coin

- **Ngày:** 2026-11-14 · **Ai quyết:** PO chốt hướng (5A); AI chọn chi tiết (tạm chọn)

## Bối cảnh

Coin đang ở chế độ thử (mã nạp, [nap-coin-che-do-thu](nap-coin-che-do-thu.md)); sổ coin chỉ thêm, có `idem_key` duy nhất
([docs/coins.md §2](../../docs/coins.md)). App Store 3.1.1 bắt bán hàng số trong app qua IAP.

## Lựa chọn

- iOS: Apple IAP, gói consumable; Android: Google Play Billing; web: VNPay, MoMo ([F56](../features/F56-iap-google-play.md),
  [F57](../features/F57-vnpay-momo.md)).
- **Server tự xác minh** (thư viện App Store Server chính thức, Google Play Developer API, chữ ký IPN của cổng); không dùng
  dịch vụ trung gian (RevenueCat…) để không thêm bên giữ dữ liệu mua hàng và phí.
- Mỗi giao dịch = một dòng sổ `purchase`, `idem_key = {provider}:{mã giao dịch}` (Google: `google:{sha256(purchaseToken)}`,
  vì mã khuyến mãi không có `orderId`); hoàn tiền/chargeback/thu hồi = dòng âm `purchase_refund`.
- **Cộng cho chủ giao dịch** (chủ của `appAccountToken` / `obfuscatedExternalAccountId`), không cho người đang gọi; không
  có mã thì cho tài khoản của phiên. Chỉ từ chối khi chữ ký/gói/sản phẩm sai. Apple `ONE_TIME_CHARGE` và Google RTDN cộng
  coin khi app không kịp gửi.
- **Hoàn tiền lớn hơn số dư (tạm chọn):** chỉ trừ tới `số dư − giữ chỗ đang mở`, phần thiếu ghi `coin_wallets.debt` và
  `payment_receipts.shortfall`, lần cộng sau trả nợ trước (`debt_repay`), `ledger_audit` kiểm cả nợ. **Có nợ vẫn mua
  được** (mua là cách trả nợ); gian lận hoàn tiền chặn bằng luật "≥ 2 lần hoàn trong 30 ngày → khoá mua".
- App không nhắc, không link tới thanh toán web; coin mua trên web dùng được trong app (3.1.3(b)).
- Giao dịch sandbox ở bản production được cộng cho **mọi** tài khoản (người duyệt có thể tạo tài khoản mới lúc duyệt),
  gắn cờ `sandbox`, không tính doanh thu, trần 3 giao dịch/ngày/tài khoản.
- VNPay: return URL là `/pay/return` rồi chuyển sang `#/coins/top-up`; IPN báo thất bại vẫn trả `00` và đánh dấu `failed`.

Sửa sau phản biện ([docs/server.md §21](../../docs/server.md), điểm 2, 11, 15, 16, P3).
- Coin của chế độ thử đặt về 0 khi bắt đầu bán, báo trước ≥ 30 ngày (PO đã chốt).

## Vì sao

Một sổ chỉ thêm và `idem_key` đã có giải quyết sẵn chuyện gửi lại, webhook lặp, hai thiết bị. Tự xác minh giữ dữ liệu
trong hệ thống của Lyris.

## Đã cân nhắc

RevenueCat (nhanh hơn, nhưng phí theo doanh thu và dữ liệu mua ra nước ngoài); cho số dư âm (phá `CHECK balance >= 0`
đang có); chỉ IAP (PO chọn 5A).

## Nguồn

- [raw/2026-11-14-server-lon-appstore-tra-loi.md](../raw/2026-11-14-server-lon-appstore-tra-loi.md)
- [raw/2026-11-14-coin-tra-loi-2.md](../raw/2026-11-14-coin-tra-loi-2.md)
- [docs/server.md §11](../../docs/server.md)
