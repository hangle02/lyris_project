# Một loại phiên cho web và app: token opaque, app gửi Bearer

- **Ngày:** 2026-11-14 · **Ai quyết:** AI chọn (tạm chọn, PO đổi được)

## Bối cảnh

Web dùng cookie `HttpOnly` + chặn CSRF bằng `X-Lyris` và `Origin` = `Host` ([scrypt-va-phien](scrypt-va-phien.md)). App
Capacitor có origin `capacitor://localhost` / `https://localhost`, khác tên miền API, nên WKWebView không gửi cookie ổn định.

## Lựa chọn

- Cùng bảng `sessions` (token ngẫu nhiên, DB chỉ giữ sha256) cho cả hai; app gửi `Authorization: Bearer <token>`, lưu token
  ở Keychain/Keystore.
- Request có `Authorization: Bearer` thì bỏ qua cookie hoàn toàn và miễn kiểm cả `Origin` lẫn `Sec-Fetch-Site`
  (request từ `capacitor://localhost` tới `api.lyris.example` luôn là cross-site); vẫn bắt `X-Lyris`. Cookie giữ luật cũ
  (sửa sau phản biện, [docs/server.md §21](../../docs/server.md)).
- Token chỉ trả trong body khi client native đăng nhập; web không bao giờ thấy token.
- Redis cache phiên 60 giây; đăng xuất/đổi mật khẩu/khoá tài khoản xoá cache ngay qua `sess_by_acct:{id}`.
- Không JWT.

## Vì sao

Thu hồi được ngay ("đăng xuất mọi thiết bị", khoá tài khoản), không thêm khoá ký phải xoay vòng, cùng code với web.

## Đã cân nhắc

JWT ngắn hạn + refresh token (khó thu hồi, phức tạp hơn); cookie với App-Bound Domains trên iOS (cấu hình mong manh).

## Nguồn

- [docs/server.md §6.1, §10](../../docs/server.md)
