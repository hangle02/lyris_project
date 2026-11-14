# F61 — Đăng ký công khai, khôi phục bằng email, đăng nhập Apple/Google

- **Trạng thái:** xem `memory/features.json` · **Phase:** Máy chủ (sau khi nộp bài)
- **Giai đoạn:** Kế hoạch
- **Màn hình:** Đăng ký (`#/signup`, [signup](../screens/signup.md)), Đăng nhập (`#/login`, [login](../screens/login.md)),
  Tài khoản (`#/me`): thêm email khôi phục.

## Là gì

Bản host mở đăng ký cho mọi người (không cần mã mời), cho người dùng tự khôi phục mật khẩu bằng email đã xác minh (tuỳ
chọn), và thêm "Tiếp tục với Apple" / "Tiếp tục với Google". App Store 4.8 (bản từ 2024): có đăng nhập bên thứ ba thì
phải có thêm một cách đăng nhập tương đương bảo vệ riêng tư; Sign in with Apple thoả luật đó và là cách Lyris chọn.
Thiết kế: [docs/server.md §10](../../docs/server.md).

## Hoạt động thế nào

- `LYRIS_SIGNUP=open` (bản host) hoặc `invite` (mặc định, bản tự chạy, như bây giờ).
- Email không bắt buộc; mã xác minh 6 số; liên kết đặt lại mật khẩu dùng 1 lần, hết hạn 30 phút.
- Sign in with Apple: server đổi `authorization code` lấy `refresh_token` và lưu mã hoá (cần để thu hồi). Tài khoản tạo
  bằng Apple trên iOS đăng nhập được ở web (Sign in with Apple JS qua Services ID) và đặt được mật khẩu cho @handle.
- Xoá tài khoản đã liên kết Apple: gọi API thu hồi token của Apple bằng `refresh_token` đã lưu.
- Quà tạo tài khoản 300 coin, định danh thiết bị phải sống qua cài lại app: iOS dùng **DeviceCheck** (2 bit do Apple giữ;
  App Attest chỉ để chứng minh app thật, khoá của nó đổi khi cài lại), Android dùng Play Integrity (device recall),
  mỗi thiết bị 1 lần quà mỗi 30 ngày. Web: Turnstile chỉ chặn bot, nên quà trên web chỉ trao sau khi xác minh email hoặc
  số điện thoại (tạm chọn).
- Móc OTP số điện thoại theo cờ `LYRIS_PHONE_VERIFY=publish`: bật thì phải xác thực số điện thoại Việt Nam trước khi bật
  "Công khai" nhân vật (Nghị định 147/2024, chờ luật sư; tạm chọn).
- Bản host hỏi năm sinh khi đăng ký (chỉ lưu năm) để có cơ chế "tuổi đã khai" của App Store 1.2.1(a) (tạm chọn).
- Vai trò `owner` thành `staff` (nhiều người, MFA TOTP, nhật ký `admin_audit`).

## Done when

- [ ] Unit: `LYRIS_SIGNUP=open` → `POST /api/auth/signup` không cần mã mời; `LYRIS_SIGNUP=invite` (mặc định) vẫn bắt mã như bây giờ (`test_signup_open_vs_invite`).
- [ ] Unit: thêm email → mã 6 số gửi qua bộ gửi email giả; sai 5 lần trong 15 phút → 429; đã xác minh thì `POST /api/auth/recover` gửi liên kết dùng 1 lần, hết hạn 30 phút (`test_email_verify_and_recover`).
- [ ] Unit: identity token Apple ký bằng khoá test, `aud` = bundle id, `nonce` khớp → tạo hoặc đăng nhập tài khoản và server đổi `authorization code` lấy `refresh_token` (endpoint giả) rồi lưu ở dạng mã hoá; sai `aud` → 401 (`test_sign_in_with_apple`).
- [ ] Unit: tài khoản tạo bằng Apple trên iOS → đăng nhập được trên web bằng identity token có `aud` = Services ID của web; đặt mật khẩu ở `#/me` rồi đăng nhập @handle + mật khẩu được (`test_apple_account_signs_in_on_web`).
- [ ] Unit: xoá tài khoản đã liên kết Apple → gọi API thu hồi token giả đúng 1 lần, bằng `refresh_token` đã lưu (`test_delete_account_revokes_apple`).
- [ ] Unit: thiết bị iOS có bit DeviceCheck "đã nhận quà" (API giả) → tài khoản mới vẫn tạo được nhưng ví 0 coin, kể cả sau khi "cài lại app" (khoá App Attest mới); thiết bị chưa có bit → +300 và server đặt bit; tài khoản tạo trên web chỉ nhận +300 sau khi xác minh email hoặc số điện thoại (`test_signup_grant_device_limit`).
- [ ] Unit: `LYRIS_PHONE_VERIFY=publish` → bật "Công khai" nhân vật khi chưa xác thực số điện thoại trả 403 `phone_required`; sau khi nhập đúng OTP (bộ gửi SMS giả) thì bật được; cờ tắt → như bây giờ (`test_phone_verify_before_publish`).
- [ ] Unit: staff vào `/api/admin/*` cần TOTP; mỗi thao tác staff có một dòng `admin_audit` (`test_staff_mfa_and_audit`).
- [ ] Bot: với `LYRIS_SIGNUP=open`, `#/signup` không có ô "Mã mời"; có nút "Tiếp tục với Google" và "Tiếp tục với Apple" (trên web và trên vỏ iOS giả), và ô "Năm sinh".

## Tests

- `backend/tests/test_public_signup.py::test_signup_open_vs_invite`
- `backend/tests/test_public_signup.py::test_email_verify_and_recover`
- `backend/tests/test_public_signup.py::test_sign_in_with_apple`
- `backend/tests/test_public_signup.py::test_apple_account_signs_in_on_web`
- `backend/tests/test_public_signup.py::test_delete_account_revokes_apple`
- `backend/tests/test_public_signup.py::test_signup_grant_device_limit`
- `backend/tests/test_public_signup.py::test_phone_verify_before_publish`
- `backend/tests/test_public_signup.py::test_staff_mfa_and_audit`
- bot: đăng ký mở không cần mã mời

## Ngoài Done when

Không chặn ✅: Điều khoản và Chính sách mới cho bản host (email, Apple/Google, số điện thoại, năm sinh, nơi lưu dữ liệu,
hạn sao lưu 35 ngày), đổi `LEGAL_VERSION`; luật sư duyệt; luật sư trả lời Lyris có thuộc diện mạng xã hội theo Nghị định
147/2024 không (quyết định bật cờ `LYRIS_PHONE_VERIFY`); nhà cung cấp SMS OTP.

## Liên quan

- **Tài liệu:** [docs/server.md §10, §13](../../docs/server.md), [docs/auth.md](../../docs/auth.md), [docs/compliance.md §3, §4](../../docs/compliance.md)
- **Tính năng:** [F29](F29-dang-nhap.md), [F30](F30-quan-ly-tai-khoan.md), [F42](F42-vi-coin.md), [F55](F55-app-ios-android.md)
- **Quyết định:** [dang-ky-bang-ma-moi](../decisions/dang-ky-bang-ma-moi.md), [quen-mat-khau](../decisions/quen-mat-khau.md), [phien-token-cho-app](../decisions/phien-token-cho-app.md)
