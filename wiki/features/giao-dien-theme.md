# Thiết kế Lyris: theme sáng/tối, điều hướng

- **Trạng thái:** Đã xong · **Phase:** Phase 2b
- **Màn hình:** [hub](../screens/hub.md), [explore](../screens/explore.md), [studio-list](../screens/studio-list.md)

## Là gì

Giao diện theo DESIGN.md: hai theme (Velvet Nocturne tối, Rosewater Parchment sáng), ba font tự host, logo và wordmark, thanh tab nổi 3 tab (Khám phá, Tương tác, Studio). Đổi tên Nora thành Lyris.

## Hoạt động thế nào

- Lyris có hai theme: Velvet Nocturne (tối) và Rosewater Parchment (sáng). Nút Sun/Moon ở header đổi theme.
- Thanh tab nổi ở dưới có 3 tab: Khám phá, Tương tác, Studio.
- Thanh tab ẩn khi vào chat, trình sửa, persona và hồ sơ nhân vật.

Kỹ thuật:

- Màu và font là token trong `frontend/src/theme/`, theo DESIGN.md.
- Ba font tự host nên chạy offline và hiện đúng dấu tiếng Việt.
- `lint.mjs` là script của skill thiết kế, không nằm trong repo (xem design-impl.md).

## Done when

- [x] Nút Sun/Moon ở header đổi theme; lựa chọn được nhớ (`lyris.theme`).
- [x] Thanh tab nổi có 3 tab; ẩn ở chat, trình sửa, persona, hồ sơ nhân vật.
- [x] Dấu tiếng Việt hiển thị đúng ở cả ba font, chạy offline.
- [x] Ở 390px không có cuộn ngang; chạm tối thiểu 44px.
- [x] `lint.mjs --app frontend/src` (script của skill thiết kế) 0 FAIL.

## Liên quan

- **Code:** [`frontend/src/theme/`](../../frontend/src/theme/), [`frontend/src/components/shell/TabBar.tsx`](../../frontend/src/components/shell/TabBar.tsx), [`frontend/src/components/shell/HubHeader.tsx`](../../frontend/src/components/shell/HubHeader.tsx), [`frontend/src/components/brand/`](../../frontend/src/components/brand/), [`frontend/src/index.css`](../../frontend/src/index.css)
- **Tài liệu:** [DESIGN.md](../../DESIGN.md), [design-impl.md](../../docs/design-impl.md)
- **Quyết định:** [ten-app-lyris](../decisions/ten-app-lyris.md), [dung-khung-giao-dien-som](../decisions/dung-khung-giao-dien-som.md), [tiet-che-thiet-ke](../decisions/tiet-che-thiet-ke.md)
