# Dùng trên iPhone qua Tailscale

- **Trạng thái:** Một phần · **Phase:** Phase 6
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

- [x] `manifest.webmanifest` và apple-touch-icon có sẵn (đã có).
- [ ] Tailscale Serve phục vụ Lyris qua HTTPS.
- [x] Cookie phiên có `Secure` khi qua HTTPS (code đã có ở `auth/net.py`; chưa thử qua Tailscale).
- [ ] `allowedHosts` của Vite chỉ thêm đúng tên *.ts.net của Mac.
- [ ] Chat được từ iPhone bằng 4G; chưa đăng nhập thì bị từ chối (401).

## Liên quan

- **Code:** [`frontend/public/manifest.webmanifest`](../../frontend/public/manifest.webmanifest), [`frontend/vite.config.ts`](../../frontend/vite.config.ts)
- **Tài liệu:** [plan.md Phase 6](../../docs/plan.md), [auth.md §3.7, §3.8](../../docs/auth.md)
- **Quyết định:** [mo-cong-5173](../decisions/mo-cong-5173.md)
