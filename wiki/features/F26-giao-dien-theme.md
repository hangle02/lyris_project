# F26 — Thiết kế Lyris: theme sáng/tối, điều hướng

- **Trạng thái:** xem `memory/features.json` · **Phase:** Phase 2b
- **Giai đoạn:** Đã có
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

- [ ] Unit: theme chỉ nhận 'light' / 'dark'; thứ tự chọn: tham số URL, lựa chọn đã lưu (`lyris.theme`), hệ thống, rồi tối; màu meta khớp token nền.
- [ ] Unit: thanh tab chỉ có ở hub, Khám phá và danh sách Studio (`tabOf`).
- [ ] Unit: nút nhỏ trên form đăng nhập, ngăn cảm xúc và header chat (nút 'Suy nghĩ', công tắc Story/DM) cao ≥ 44px ở điện thoại.
- [ ] Unit: `Button` và `IconButton` cỡ `sm` cao 44px ở điện thoại (`max-sm:h-11`, icon thêm `max-sm:w-11`), vẫn 36px từ 640px trở lên.
- [ ] Bot: ở 1280px `#/explore` không cuộn ngang.
- [ ] Bot: suốt lượt chạy bot không có lỗi console.
- [ ] Bot: bấm 'Chuyển sang giao diện sáng' / 'Chuyển sang giao diện tối' ở header thì `document.documentElement.dataset.theme` đổi và localStorage `lyris.theme` lưu giá trị mới; tải lại vẫn giữ.
- [ ] Bot: thanh 'Điều hướng chính' có 3 tab (Khám phá, Tương tác, Studio) ở `#/`, `#/explore`, `#/studio`; không có ở `#/chat/<id>`, `#/studio/<id>`, `#/personas`, `#/character/<id>`.
- [ ] Bot: ở 390px, `#/`, `#/studio`, `#/chat/<id>` không cuộn ngang và mọi nút trên header (cả 'Suy nghĩ' và hai nút Story/DM ở `#/chat/<id>`), mọi tab của thanh 'Điều hướng chính' rộng và cao ≥ 44px.
- [ ] Bot: ở 390px, mọi nút dưới lượt cuối của nhân vật trong story (hàng thao tác: Tạo lại, Thích, Chê, Sửa, Xoá từ đây…) và nút 'Huỷ', 'Xoá' của hộp 'Xác nhận xoá' rộng và cao ≥ 44px.
- [ ] Bot: suốt lượt chạy của bot (mọi trang) không có request nào ra ngoài máy (font, icon, ảnh đều tự host).
- [ ] Unit: dấu tiếng Việt có trong cả ba font tự host: mọi file font mà `main.tsx` nhập (Plus Jakarta Sans, Be Vietnam Pro, Cormorant Garamond) có `@font-face` phủ U+1EA0–1EF9, Đ đ, Ơ ơ, Ư ư, lấy từ file `.woff2` tiếng Việt cục bộ; token `--font-sans`, `--font-story`, `--font-brand` đặt đúng font đó đầu tiên.
- [ ] Bot: dấu tiếng Việt hiển thị đúng ở cả ba font: với mọi kiểu chữ app dùng (10 cặp độ đậm/nghiêng), từng chữ 'Ặ ặ Ỡ ỡ Ừ ừ Ữ ữ Ấ ấ Ộ ộ Ệ ệ Ơ ơ Ư ư Ă ă Đ đ' được vẽ bằng chính font đó, không rơi về font dự phòng (đo canvas sau `document.fonts.load`: cùng độ rộng dù font dự phòng là monospace hay serif), và bộ chữ tiếng Việt (U+1EA0–1EF9) của font đã tải.

## Tests

- frontend/src/theme/fonts.test.ts
- frontend/src/theme/theme.test.ts
- frontend/src/lib/router.test.ts
- frontend/src/components/ui/logic.test.ts
- frontend/src/pages/auth/tapTargets.test.ts
- frontend/src/pages/chat/tapTargets.test.ts
- bot: màn desktop 1280px không tràn ngang
- bot: không có lỗi console
- bot: nút đổi theme và nhớ lựa chọn
- bot: thanh tab 3 tab, ẩn ở màn con
- bot: 390px không tràn ngang, nút header và thanh tab ≥ 44px ở #/, #/studio, #/chat
- bot: 390px nút dưới lượt chat và nút hộp Xác nhận xoá ≥ 44px
- bot: không có request ra ngoài
- bot: chữ tiếng Việt có dấu vẽ bằng đúng ba font tự host, không rơi về font dự phòng

## Ngoài Done when

Không chặn ✅ (cần thử tay, dịch vụ thật, hoặc còn là kế hoạch).

- `lint.mjs --app frontend/src` (script của skill thiết kế, nằm ngoài repo) 0 FAIL: chạy tay khi đổi giao diện, xem [design/README.md](../design/README.md) §11.

## Liên quan

- **Code:** [`frontend/src/theme/`](../../frontend/src/theme/), [`frontend/src/components/shell/TabBar.tsx`](../../frontend/src/components/shell/TabBar.tsx), [`frontend/src/components/shell/HubHeader.tsx`](../../frontend/src/components/shell/HubHeader.tsx), [`frontend/src/components/brand/`](../../frontend/src/components/brand/), [`frontend/src/index.css`](../../frontend/src/index.css)
- **Tài liệu:** [DESIGN.md](../../DESIGN.md), [design-impl.md](../../docs/design-impl.md)
- **Quyết định:** [ten-app-lyris](../decisions/ten-app-lyris.md), [dung-khung-giao-dien-som](../decisions/dung-khung-giao-dien-som.md), [tiet-che-thiet-ke](../decisions/tiet-che-thiet-ke.md)
