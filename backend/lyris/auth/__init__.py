"""Phase 4b (docs/auth.md): đăng nhập, phiên, mã mời, giới hạn thử sai, chặn CSRF, lệnh trên Mac.

- `passwords`: luật và băm mật khẩu (scrypt, NFC, so sánh an toàn thời gian, băm ngoài khoá Repo).
- `codes`: mã mời, mã thiết lập chủ máy, mật khẩu tạm (Crockford base32, sha256).
- `net`: IP thật sau proxy (`client_ip`), HTTPS, nhãn thiết bị, cookie.
- `store`: các câu SQL của phase này (phiên, mã mời, lần thử, tài khoản).
- `ratelimit`: luật giới hạn thử sai (§3.4).
- `middleware`: chặn CSRF, `Cache-Control: no-store`, gửi cookie do dependency hẹn.
- `setup`: mã thiết lập chủ máy in ra Terminal lúc khởi động.
- `cli`: lệnh trên Mac (`scripts/lyris-admin.sh`).
"""
