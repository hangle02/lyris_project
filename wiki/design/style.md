# Phong cách của Lyris

Giá trị thật đang chạy trong code (`frontend/src/index.css`, `components/ui`, `components/brand`). Đặc tả gốc: [DESIGN.md](../raw/DESIGN.md). Chi tiết đầy đủ và API của từng thành phần: [docs/design-impl.md](../../docs/design-impl.md) §11. Nguyên tắc: [README.md](README.md).

## 1. Hai theme

- **Velvet Nocturne** (tối, mặc định): đêm nhung và ánh nến, cho đọc đêm khuya.
- **Rosewater Parchment** (sáng): giấy lụa và nắng sớm, cho đọc ban ngày.
- Thứ tự chọn: `?theme=` trên URL (chỉ để chụp kiểm tra), rồi lựa chọn đã lưu (`localStorage["lyris.theme"]`), rồi theo hệ thống. Nút Mặt trời / Mặt trăng ở header hub.
- Đổi theme: mọi màu chuyển trong 500ms, như vặn đèn.

## 2. Màu (token cuối cùng)

Dùng qua Tailwind (`bg-surface`, `text-muted`...) hoặc `var(--color-*)`. Không viết mã màu thẳng trong component.

| Token | Tối | Sáng | Dùng cho |
|---|---|---|---|
| `bg` | #130D14 | #FAF5EE | nền app |
| `surface` | #1F1521 | #FFFDF9 | card, thẻ thoại, modal, ngăn kéo |
| `surface-2` | #2A1D2C | #F4ECE4 | ô nhập, chip, nút secondary |
| `surface-3` | #352536 | #EDE2D8 | hover, đang chọn, khung xương |
| `glass` | rgb(31 21 33 / .78) | rgb(255 252 249 / .85) | chỉ header hub, header chat, thanh tab |
| `line` | #382635 | #E8D7CE | viền mảnh |
| `fg` | #FAF2EB | #2D1E24 | chữ chính |
| `prose` | #E9DDE0 | #3A2A31 | văn bản dài |
| `muted` | #C2AAB8 | #6B535D | dẫn truyện nghiêng, phụ đề, giờ |
| `faint` | #9C8797 | #7B626B | placeholder (không đặt trên `surface-3`) |
| `dialogue` | #FAF2EB | #2D1E24 | chữ trong thẻ thoại |
| `thought` | #EBC9CF | #8E4A5A | chữ trong thẻ suy nghĩ |
| `accent` | #E5989B | #A14A5B | nút chính, viền suy nghĩ, focus, active |
| `accent-strong` | #F0B3B5 | #8A3A4D | hover của accent |
| `accent-2` | #F3C68F | #875A2B | vai trò nhân vật, điểm nhấn hổ phách |
| `on-accent` | #1A1018 | #FFFDF9 | chữ trên nền accent |
| `user-from → user-to` | #3D2638 → #291928 | #B45A6C → #9E4A5C | bong bóng người chơi |
| `user-fg` | #FAF2EB | #FFFFFF | chữ bong bóng người chơi |
| `danger / ok / warn` | #F08A8A / #7FD1A2 / #F3C68F | #AB3E49 / #306F4B / #845B22 | |

**6 màu cảm xúc** (giống nhau ở hai theme, chỉ cho thanh và chấm, không làm màu chữ):

| Cảm xúc | Màu |
|---|---|
| Thương mến | #D86C86 |
| Tin cậy | #C58B52 |
| Rung động | #A864A8 |
| Nhung nhớ / Chiếm hữu | #D15B5B |
| Lo sợ mất mát | #6E7BB8 |
| Khoảng cách | #9E8881 |

**Gradient** (chỉ 4 chỗ):
- Quả cầu tab giữa và nút gửi: `#C86D7E → #D98A6C → #F3C68F`, icon màu mực tối `on-orb`.
- Bong bóng người chơi: `user-from → user-to`.
- Chữ L của wordmark: tối `#F3C68F → #E5989B → #FAF2EB`, sáng `#9E475B → #C86D7E → #B87D4B`.

## 3. Chữ

Ba font, tự host qua `@fontsource` (chạy offline, có dấu tiếng Việt):

| Lớp | Font | Weight đã nạp | Dùng cho |
|---|---|---|---|
| `font-brand` | Cormorant Garamond, nghiêng | 600, 700 | wordmark Lyris, tên nhân vật trên hồ sơ |
| `font-sans` | Plus Jakarta Sans | 400, 500, 600, 700 | giao diện, DM |
| `font-story` | Be Vietnam Pro, line-height 1.65 | 300, 400, 400 nghiêng, 500 | văn Story, thẻ thoại, suy nghĩ |

- Không có weight 800 và không có Be Vietnam 500 nghiêng: không dùng `font-extrabold`; thẻ thoại đậm vừa, không nghiêng.
- Thang: 12 / 13 / 14 / 15 / 16 / 20 / 24px. Ô nhập 16px (để iPhone không tự phóng to). Số liệu `tabular-nums`.

## 4. Bo góc, khoảng cách, bóng

- `rounded-card` 20px, `rounded-control` 14px, còn lại `rounded-full`. Lồng nhau thì bo nhỏ dần.
- Control cao 44px (`md`, mặc định) hoặc 36px (`sm`).
- `shadow-float` cho modal, ngăn kéo, menu, thanh tab. `shadow-orb` (hồng mềm) cho quả cầu và nút gửi.

## 5. Thương hiệu

- **LogoMark**: hai trang sách cong thành trái tim, ngôi sao 4 cánh vàng ở giữa, nét 1.8px, gradient hồng → vàng.
- **Wordmark**: "Lyris" bằng Cormorant nghiêng; L gradient; chữ "ı" không chấm, thay bằng ngôi sao nhấp nháy nhẹ; dải lụa cong bên dưới.
- Favicon `public/favicon.svg` (ô vuông nền #130D14), `apple-touch-icon.png` 180px, `manifest.webmanifest` (standalone, nền #130D14).

## 6. Khung app

- **Header hub** (kính mờ): wordmark trái; nút đổi theme và avatar tài khoản phải.
- **Thanh tab nổi**: cách đáy 16px cộng vùng an toàn, rộng 90% (tối đa 420px), cao 64px, tròn hẳn. Trái "Khám phá" (la bàn), giữa "Tương tác" là quả cầu gradient nhô lên 12px với tim đặc, phải "Studio" (lấp lánh). Ẩn ở trang con và trong chat.
- Trang có thanh tab chừa đáy bằng `pb-tabbar`.

## 7. Thành phần dùng lại

Lấy từ `components/ui`, không tự viết lại: `Button`, `IconButton`, `Chip`, `Badge`, `Card`, `TextField`, `TextArea`, `Select`, `Toggle`, `ChoiceGroup`, `SegmentedControl`, `Modal`, `Drawer`, `Disclosure`, `InlineAlert`, `ErrorDetails`, `EmptyState`, `Skeleton`, `Meter`, `Spinner`. Thêm `Avatar`, `CharacterPicture`, `TypingDots`, `LiveStatus`.

- Trên điện thoại, `Modal` là sheet trượt từ dưới.
- Icon: bộ SVG nội bộ `components/icons.tsx`, kiểu Lucide, nét 1.75px, cỡ `1em`, màu `currentColor`. Không thêm thư viện icon.

## 8. Khối trong chat

**Story** (mỗi lượt của nhân vật tách thành khối, `lib/storyBlocks.ts`):
- *Dẫn truyện và hành động*: đoạn nghiêng màu `muted`, không khung.
- *Lời thoại*: thẻ `bg-surface rounded-card`, chữ `dialogue` đậm vừa, không có ngoặc ngoài cùng. Đoạn trong ngoặc từ 3 từ trở lên mới thành thẻ.
- *Suy nghĩ "Tiếng Lòng Giấu Kín"*: viền trái 3px `accent`, nền tint phẳng (accent khoảng 8%). Mặc định làm mờ 3px kèm "Chạm để lắng nghe"; chạm thì hiện rõ. Công tắc "Luôn hiện suy nghĩ" bỏ mờ. Tắt "Đọc suy nghĩ của nhân vật" thì thẻ không có trong trang.
- *Lượt người chơi*: cột phải, rộng tối đa 85%, avatar persona 28px. Lời thoại trong bong bóng gradient; hành động nghiêng `muted` như dẫn truyện. Chỉ đạo `((...))` là chip nhỏ.

**DM**: bong bóng tối đa 80% chiều rộng, avatar thật cạnh tin nhân vật, chân tin "00:40 • Đã gửi" / "Đã xem", gom nhóm theo giờ.

**Khác**:
- Đang chờ: ba chấm nhảy (1.2 giây), đứng yên khi reduced-motion.
- Ô nhập: "+" (xoay 45° khi mở), ô nhập nền `surface-2` bo 20px, nút gửi gradient (máy bay giấy).
- Cột đọc 720px; header chat rộng 960px từ 1024px.

## 9. Ảnh

- Thẻ Khám phá: ảnh 4:3. Thẻ nổi bật: 3:1 trên điện thoại. Hồ sơ nhân vật: 4:5 (dính bên trái từ 768px).
- Thứ tự ảnh: avatar của nhân vật → ảnh bối cảnh của nhân vật mẫu → chữ cái đầu trên nền phẳng.

## 10. Chỗ lệch DESIGN.md (có chủ đích)

| DESIGN.md | Lyris hiện tại | Vì sao |
|---|---|---|
| Thẻ thoại bọc trong `“...”` | Không ngoặc | Chủ dự án chọn 2026-11-13 |
| Pill `● M2 Local` ở header | Không có; thông tin máy trong "Nâng cao" | Chủ dự án muốn giấu |
| Emoji ở banner chào và chip (☀️, ✨) | Bỏ emoji, giữ lời | Luật taste |
| "TƯƠNG TÁC", "STORY" viết hoa | "Tương tác", "Story" | Luật taste |
| Thẻ suy nghĩ nền gradient | Nền tint phẳng | Luật taste |
| Gợi ý trả lời tự hiện | Chỉ khi bấm "Nhận gợi ý" | Chủ dự án chọn 2026-11-13 |
| Lưới Khám phá thẻ dọc 3:4, nút "Trò chuyện" | Ảnh 4:3, cả thẻ mở hồ sơ | Chủ dự án muốn thẻ nhỏ hơn và mở hồ sơ |
| Light `accent` #C86D7E, `accent-2` #C58B52, `muted` #7D636D | #A14A5B, #875A2B, #6B535D | Màu gốc không đạt tương phản 4.5:1 |
| Chữ đang chờ "{Tên} đang ngập ngừng…" | Ba chấm nhảy | Chủ dự án chọn 2026-11-13 |

Màu gốc DESIGN.md vẫn dùng cho logo, favicon và quả cầu.
