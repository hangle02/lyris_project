# F37 — Dùng trên iPhone qua Tailscale

- **Trạng thái:** xem `memory/features.json` · **Phase:** Phase 6
- **Giai đoạn:** Kế hoạch
- **Màn hình:** Không có màn hình riêng (chạy nền hoặc ngoài app).

## Là gì

Cài Lyris lên màn hình chính iPhone và chat từ bất cứ đâu qua Tailscale (HTTPS). Đã có manifest PWA và icon từ Phase 2b, và cookie đã tự bật Secure khi request là HTTPS. Chưa làm: Tailscale Serve và tên *.ts.net trong Vite.

## Hoạt động thế nào

- Mong muốn: cài Lyris lên màn hình chính iPhone và chat ở bất cứ đâu, không cần cùng Wi-Fi.
- Đi qua Tailscale nên không mở cổng ra Internet.
- Đã có: manifest PWA và icon. Chưa có: Tailscale Serve và tên *.ts.net.

Kỹ thuật:

- Cookie đã tự có `Secure` khi request là HTTPS hoặc `LYRIS_COOKIE_SECURE=1` (`backend/lyris/auth/net.py`), nhưng chưa thử qua Tailscale.
- Phase 6 chỉ thêm đúng tên *.ts.net của Mac vào `allowedHosts` của Vite.

## Done when

- [ ] Unit: cookie phiên có `Secure` khi request tới qua HTTPS tin cậy (đã có ở `auth/net.py`).
- [ ] Unit: `allowedHosts` của Vite chỉ thêm đúng tên `*.ts.net` của Mac, không bao giờ `true`.
- [ ] Unit: chưa đăng nhập thì mọi route (trừ route mở) trả 401.
- [ ] Bot: trang chủ có link `manifest.webmanifest` và apple-touch-icon, cả hai tải được (200).

## Tests

- backend/tests/test_auth_api.py::test_secure_cookie_only_from_trusted_https
- backend/tests/test_auth_routes.py::test_no_cookie_is_401_except_open_routes
- frontend/src/viteConfig.test.ts

Tên check bot dự kiến (chưa có trong `environment/e2e.mjs`, thêm khi làm): `bot: có manifest và apple-touch-icon`.

## Ngoài Done when

Không chặn ✅ (cần thử tay, dịch vụ thật, hoặc còn là kế hoạch).

- Thử tay: Tailscale Serve phục vụ Lyris qua HTTPS; chat được từ iPhone bằng 4G.

## Liên quan

- **Code:** [`frontend/public/manifest.webmanifest`](../../frontend/public/manifest.webmanifest), [`frontend/vite.config.ts`](../../frontend/vite.config.ts)
- **Tài liệu:** [plan.md Phase 6](../../docs/plan.md), [auth.md §3.7, §3.8](../../docs/auth.md)
- **Quyết định:** [mo-cong-5173](../decisions/mo-cong-5173.md)
