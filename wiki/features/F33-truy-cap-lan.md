# F33 — Dùng trên điện thoại cùng Wi-Fi

- **Trạng thái:** xem `memory/features.json` · **Phase:** Phase 3, 4b
- **Giai đoạn:** Đã có
- **Màn hình:** Không có màn hình riêng (chạy nền hoặc ngoài app).

## Là gì

`scripts/dev.sh` mở frontend cổng 5173 cho mạng LAN; backend chỉ nghe ở máy, điện thoại gọi API qua proxy của Vite. Vẫn phải đăng nhập.

## Hoạt động thế nào

- Chạy `bash scripts/dev.sh` trên Mac.
- Điện thoại cùng Wi-Fi mở `http://<IP Mac>:5173`, đăng nhập rồi chat.
- Muốn chỉ dùng trên Mac thì chạy với `LYRIS_LAN=0`.

Kỹ thuật:

- Backend chỉ nghe ở 127.0.0.1:8000; điện thoại gọi API qua proxy của Vite.
- Vite không mở `allowedHosts: true`; backend chạy `--no-proxy-headers`.

## Done when

- [ ] Unit: Vite không đặt `allowedHosts: true`, chỉ phục vụ `frontend/` và chặn `data/`; proxy `/api` chuyển IP thật (xfwd) và giữ Host gốc.
- [ ] Unit: backend đọc IP thật từ phần tử cuối của `X-Forwarded-For`; header giả từ máy khác trong LAN bị bỏ qua.
- [ ] Unit: chưa đăng nhập thì mọi route (trừ route mở) trả 401.

## Tests

- frontend/src/viteConfig.test.ts
- backend/tests/test_auth_units.py::test_client_ip_uses_last_of_repeated_headers
- backend/tests/test_auth_api.py::test_spoofed_forwarded_for_from_lan_is_ignored
- backend/tests/test_auth_routes.py::test_no_cookie_is_401_except_open_routes

## Ngoài Done when

Không chặn ✅ (cần thử tay, dịch vụ thật, hoặc còn là kế hoạch).

- Thử tay: `bash scripts/dev.sh` chạy backend (8000) và frontend (5173); điện thoại cùng Wi-Fi mở `http://<IP Mac>:5173` và chat được; `LYRIS_LAN=0` thì chỉ mở trên máy này. (Cổng 8000/5173 là app của chủ dự án: bot không dùng.)

## Liên quan

- **Code:** [`scripts/dev.sh`](../../scripts/dev.sh), [`frontend/vite.config.ts`](../../frontend/vite.config.ts)
- **Tài liệu:** [auth.md §3.8](../../docs/auth.md)
- **Quyết định:** [mo-cong-5173](../decisions/mo-cong-5173.md), [chua-dung-docker](../decisions/chua-dung-docker.md)
