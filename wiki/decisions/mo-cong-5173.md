# Mở Vite ra mạng LAN để thử bằng điện thoại

- **Ngày:** 2026-11-13 · **Ai quyết:** người dùng

## Bối cảnh

Người dùng muốn thử app trên điện thoại.

## Lựa chọn

Vite nghe 0.0.0.0:5173 (LAN); backend vẫn chỉ nghe 127.0.0.1:8000. Từ Phase 4b mọi /api cần đăng nhập. Truy cập từ xa qua Tailscale Serve để Phase 6.

## Vì sao

Người dùng: "Bạn mở port 5173 ra để mình có thể thử xem bằng điện thoại".

## Đã cân nhắc

Mở thẳng backend ra LAN.

## Nguồn

- Lời người dùng, 2026-11-13 01:59 (xem [raw/](../raw/))
- [docs/auth.md](../../docs/auth.md) §3.8
- [docs/plan.md](../../docs/plan.md) Phase 6
