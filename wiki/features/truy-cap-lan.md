# Dùng trên điện thoại cùng Wi-Fi

- **Trạng thái:** Đã xong · **Phase:** Phase 3, 4b
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

- [x] `bash scripts/dev.sh` chạy backend (8000) và frontend (5173).
- [x] Điện thoại cùng Wi-Fi mở http://<IP Mac>:5173 và chat được.
- [x] `LYRIS_LAN=0` thì chỉ mở trên máy này.
- [x] Vite không đặt `allowedHosts: true`; backend chạy `--no-proxy-headers`.

## Liên quan

- **Code:** [`scripts/dev.sh`](../../scripts/dev.sh), [`frontend/vite.config.ts`](../../frontend/vite.config.ts)
- **Tài liệu:** [auth.md §3.8](../../docs/auth.md)
- **Quyết định:** [mo-cong-5173](../decisions/mo-cong-5173.md), [chua-dung-docker](../decisions/chua-dung-docker.md)
