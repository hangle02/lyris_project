# Ghi công

Mọi ảnh, font, icon đi kèm Lyris và nguồn của chúng. Lấy từ code: `backend/lyris/seed/templates/*.json` (khối `image`), `frontend/node_modules/@fontsource/*/LICENSE`, `frontend/src/components/icons.tsx`. Cách tìm thêm tài nguyên: [assets.md](assets.md).

Trong app, ghi công ảnh hiện ở sheet Tài khoản → "Giới thiệu & bản quyền ảnh". Khi cài một nhân vật mẫu có ảnh, một dòng ghi công được thêm vào "ghi chú của người tạo" của card.

## 1. Ảnh bối cảnh của nhân vật mẫu

Tất cả lấy từ Wikimedia Commons, đã cắt thành khung dọc 3:4.

| Nhân vật | File | Ảnh gốc | Tác giả | Giấy phép | Đã sửa |
|---|---|---|---|---|---|
| Hạ Vy | `ha-vy.jpg` | [Da Lat - Viet Nam](https://commons.wikimedia.org/wiki/File:Da_Lat_-_Viet_Nam.jpg) | Tuong Lam Photos | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0) | Cắt khung dọc 3:4 và thu nhỏ; bản đã sửa dùng cùng giấy phép CC BY-SA 4.0. |
| Trần Minh Khang | `tran-minh-khang.jpg` | [2024-11-16 Ho Chi Minh City at night 3](https://commons.wikimedia.org/wiki/File:2024-11-16_Ho_Chi_Minh_City_at_night_3.jpg) | Alexey Komarov (Alexkom000) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0) | Cắt khung dọc 3:4 và thu nhỏ. |
| Tạ Vân Lan | `ta-van-lan.jpg` | [Landscape in the Style of Juran and Yan Wengui (倣巨然燕文貴山水圖), 1713](https://commons.wikimedia.org/wiki/File:%E6%B8%85_%E7%8E%8B%E7%BF%AC_%E5%80%A3%E5%B7%A8%E7%84%B6%E7%87%95%E6%96%87%E8%B2%B4%E5%B1%B1%E6%B0%B4%E5%9C%96_%E5%8D%B7-Landscape_in_the_Style_of_Juran_and_Yan_Wengui_MET_DP204418.jpg) | Wang Hui (王翬) | [CC0](https://creativecommons.org/publicdomain/zero/1.0/) | Cắt một đoạn của cuộn tranh (The Metropolitan Museum of Art) thành khung dọc 3:4. |
| Morwenna Penrose | `morwenna-penrose.jpg` | [Pendeen Watch lighthouse Cornwall](https://commons.wikimedia.org/wiki/File:Pendeen_Watch_lighthouse_Cornwall.jpg) | Tom Corser (www.tomcorser.com) | [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0) | Cắt khung dọc 3:4 và thu nhỏ; bản đã sửa dùng cùng giấy phép CC BY-SA 3.0. |

Lạc Dương (nhân vật mẫu) không có ảnh đi kèm.

## 2. Font

Tự host qua gói `@fontsource` 5.3.0, giấy phép SIL Open Font License 1.1.

| Font | Bản quyền |
|---|---|
| Cormorant Garamond | Copyright 2015 The Cormorant Project Authors (github.com/CatharsisFonts/Cormorant) |
| Plus Jakarta Sans | Copyright 2020 The Plus Jakarta Sans Project Authors (https://github.com/tokotype/PlusJakartaSans) |
| Be Vietnam Pro | Copyright 2021 The Be Vietnam Pro Project Authors (https://github.com/bettergui/BeVietnamPro) |

## 3. Icon

- Bộ icon trong `frontend/src/components/icons.tsx` vẽ theo đường nét của [Lucide](https://lucide.dev) (giấy phép ISC), ví dụ `eye`, `eye-off`, `send`. Không cài gói Lucide.
- Ngôi sao 4 cánh, logo (LogoMark), wordmark, favicon và icon màn hình chính (`frontend/public/`) là hình riêng của Lyris, vẽ theo mô tả trong [DESIGN.md](../raw/DESIGN.md) §2.

## 4. Ảnh trong dữ liệu của máy

- Ảnh nhân vật, persona và tài khoản trong `data/avatars/` không thuộc mã nguồn. Chúng là ảnh của nhân vật mẫu đã cài (ghi công ở §1) hoặc ảnh chủ dự án tự tải lên qua app.
- Các nhân vật chủ dự án gửi (Lục Bắc Uyên, Yến Hoành Sinh, Cố Hoài Dã, Tần Dương) và Lạc Dương không có ảnh trong repo. Ảnh của họ trong app nằm trong dữ liệu của máy; chủ dự án gửi ảnh nhân vật ngày 2026-11-13 và thêm ảnh Tần Dương qua web ngày 2026-11-14 ([raw](../raw/2026-11-14-kham-pha-trung-nhan-vat-va-luoi.md)). **Chưa ghi nguồn.** Cần bổ sung trước khi chia sẻ những nhân vật này ra ngoài máy (Phase 7).
