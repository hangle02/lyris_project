# F29 — Đăng nhập, mã mời và nhiều tài khoản

- **Trạng thái:** xem `memory/features.json` · **Phase:** Phase 4b
- **Giai đoạn:** Đã có
- **Màn hình:** [login](../screens/login.md), [signup](../screens/signup.md), [setup-owner](../screens/setup-owner.md), [force-password](../screens/force-password.md), [auth-splash](../screens/auth-splash.md), [account-sheet](../screens/account-sheet.md)

## Là gì

Mở Lyris phải đăng nhập. Tài khoản đầu tiên là chủ máy, người duy nhất tạo mã mời. Người khác tạo tài khoản bằng mã mời; mỗi người chỉ thấy story của mình. Quên mật khẩu thì chủ máy đặt lại; chủ máy quên thì chạy lệnh trên Mac.

## Hoạt động thế nào

- Mở Lyris thì phải đăng nhập.
- Lần đầu, chủ máy tạo tài khoản bằng mã thiết lập in ra Terminal.
- Người khác tạo tài khoản bằng mã mời của chủ máy. Mỗi người chỉ thấy story của mình.
- Quên mật khẩu thì chủ máy đặt lại. Chủ máy quên thì chạy `scripts/lyris-admin.sh` trên Mac.

Kỹ thuật:

- Mật khẩu băm bằng scrypt; phiên lưu bằng cookie (`backend/lyris/auth/`).
- Bảng và cột mới nằm trong migration `0008_auth.sql`.
- `test_isolation_sweep.py` gọi mọi route bằng hai tài khoản để chắc không ai thấy dữ liệu của người kia.

## Done when

- [ ] Unit: lần đầu, backend in mã thiết lập ra stderr (hết hạn sau 24 giờ); trang thiết lập chủ máy dùng mã đó; hai người cùng thiết lập thì chỉ một người thắng.
- [ ] Unit: tạo tài khoản bằng mã mời; mã được chuẩn hoá (viết thường, gạch ngang của iPhone); mã sai hay hết hạn cho cùng một câu lỗi.
- [ ] Unit: mật khẩu tạm bắt phải đổi trước khi vào app (403 `password_change_required`).
- [ ] Unit: đăng xuất, đăng xuất mọi thiết bị; đổi mật khẩu xoay phiên; cookie HttpOnly; giới hạn đăng nhập theo IP và theo cặp.
- [ ] Unit: mọi route được phân loại; quét mọi route với hai tài khoản không đọc chéo dữ liệu, 404 giống nhau cho thiếu và của người khác.
- [ ] Unit: đổi tài khoản trên cùng trình duyệt xoá bản nháp của người trước, giữ theme; trang cần đăng nhập được nhớ để quay lại sau khi đăng nhập.
- [ ] Unit: `scripts/lyris-admin.sh` đặt lại mật khẩu và mở khoá được cả khi app đang chạy.
- [ ] Bot: `#/login` có tiêu đề 'Đăng nhập', ô tên đăng nhập và mật khẩu; đăng nhập đúng thì vào app (header có nút '… Mở tài khoản').
- [ ] Bot: chưa đăng nhập mà mở `#/studio` thì sang `#/login`; đăng nhập xong quay lại `#/studio`.
- [ ] Bot: mở `#/signup?code=<mã>` thì ô 'Mã mời' được điền và thanh địa chỉ không còn mã.
- [ ] Bot: sheet Tài khoản có 'Đổi mật khẩu', 'Đăng xuất', 'Đăng xuất mọi thiết bị'; bấm 'Đăng xuất mọi thiết bị' thì hỏi lại trước khi làm.

## Tests

- backend/tests/test_auth_api.py
- backend/tests/test_auth_routes.py
- backend/tests/test_auth_units.py
- backend/tests/test_auth_hardening.py
- backend/tests/test_auth_cli.py
- backend/tests/test_auth_migration.py
- backend/tests/test_isolation_sweep.py
- frontend/src/lib/auth.test.ts
- frontend/src/lib/inviteCode.test.ts
- frontend/src/lib/passwordRules.test.ts
- frontend/src/lib/leaveGuard.test.ts
- frontend/src/pages/auth/logic.test.ts
- frontend/src/pages/auth/tapTargets.test.ts
- frontend/src/hooks/accountLogic.test.ts
- bot: trang đăng nhập hiện và đăng nhập được
- bot: chưa đăng nhập thì sang login rồi quay lại
- bot: link mời điền mã và bỏ mã khỏi URL
- bot: sheet Tài khoản có đổi mật khẩu và đăng xuất

## Liên quan

- **Code:** [`backend/lyris/auth/`](../../backend/lyris/auth/), [`backend/lyris/api/routes_auth.py`](../../backend/lyris/api/routes_auth.py), [`backend/lyris/db/migrations/0008_auth.sql`](../../backend/lyris/db/migrations/0008_auth.sql), [`frontend/src/lib/auth.ts`](../../frontend/src/lib/auth.ts), [`frontend/src/hooks/useAuth.ts`](../../frontend/src/hooks/useAuth.ts), [`frontend/src/pages/auth/`](../../frontend/src/pages/auth/), [`scripts/lyris-admin.sh`](../../scripts/lyris-admin.sh)
- **Tài liệu:** [auth.md](../../docs/auth.md)
- **Quyết định:** [dang-ky-bang-ma-moi](../decisions/dang-ky-bang-ma-moi.md), [quen-mat-khau](../decisions/quen-mat-khau.md), [scrypt-va-phien](../decisions/scrypt-va-phien.md)
