# Nguồn miễn phí dùng được

Các nguồn dưới đây là nguồn Lyris đang dùng hoặc đã dùng để tìm tài nguyên. Ghi công cho từng thứ đang có trong app: [credits.md](credits.md).

App chạy offline trên máy Mac, nên **mọi tài nguyên phải tải về và đi kèm repo**. Không nạp font, icon hay ảnh từ CDN lúc chạy.

## 1. Font

| Nguồn | Cách dùng trong Lyris | Giấy phép |
|---|---|---|
| Google Fonts, qua gói npm `@fontsource/*` | `npm install @fontsource/<tên>`, rồi import đúng weight cần trong `frontend/src/main.tsx` | SIL Open Font License 1.1 (OFL) |

- Đang dùng: Cormorant Garamond, Plus Jakarta Sans, Be Vietnam Pro (xem [style.md](style.md) §3).
- Font mới phải có subset `vietnamese` và hiển thị đúng dấu chồng (ư ơ ằ ễ ỡ ặ ữ ỷ).
- Chỉ import weight thật dùng. Không thêm font thứ tư ([README.md](README.md) §7).

## 2. Icon

| Nguồn | Cách dùng | Giấy phép |
|---|---|---|
| [Lucide](https://lucide.dev) | Chép đường vẽ SVG của icon cần, thêm thành một hàm `Icon<Tên>` trong `frontend/src/components/icons.tsx` | ISC |

- Không cài gói icon. Mọi icon đi qua hàm `Svg` chung (lưới 24px, nét 1.75px, `currentColor`, `aria-hidden`).
- Ngôi sao 4 cánh (`IconStar4`) và logo là hình riêng của Lyris, không lấy từ Lucide.

## 3. Ảnh bối cảnh cho nhân vật mẫu

Tìm bằng script của skill `design-taste-frontend`:

```sh
node ~/.claude/skills/design-taste-frontend/scripts/assets.mjs "<từ khoá>" --orientation portrait
node ~/.claude/skills/design-taste-frontend/scripts/assets.mjs --get <ref> --to <thư mục>
node ~/.claude/skills/design-taste-frontend/scripts/assets.mjs --credits --to <thư mục>
```

Script tìm trong các nguồn này (không cần API key), mặc định chỉ lấy giấy phép an toàn (CC0, public domain, CC BY, CC BY-SA):

| Nguồn | Có gì | Lyris đã dùng |
|---|---|---|
| Wikimedia Commons | ảnh địa danh, phố, phong cảnh, bản scan tranh cổ | Có (Hạ Vy, Trần Minh Khang, Morwenna Penrose, Tạ Vân Lan) |
| The Metropolitan Museum of Art (Open Access) | tranh, bản khắc cổ, CC0 | Có (tranh của Tạ Vân Lan, lấy qua Commons) |
| Art Institute of Chicago | tranh, ảnh, vải cổ, public domain | Chưa |
| Openverse | một chỉ mục gồm Flickr, Commons, bảo tàng, thư viện | Chưa |

**Luật khi chọn ảnh** (design-impl §10):
- Chỉ dùng ảnh **bối cảnh** (tiệm sách, phố mưa, núi mây...) hoặc tranh cổ cho nhân vật cổ trang.
- **Không** dùng ảnh người thật làm chân dung nhân vật.
- Ưu tiên CC0 và public domain, rồi CC BY, CC BY-SA. Không dùng ảnh "ND" (không cho sửa), vì ảnh nhân vật mẫu đều phải cắt thành khung dọc 3:4.
- CC BY-SA: bản đã cắt cũng phải mang cùng giấy phép.

**Thêm ảnh cho một nhân vật mẫu:**
1. Đặt file `.jpg` cạnh file JSON trong `backend/lyris/seed/templates/`.
2. Thêm khối `image` vào JSON: `file`, `title`, `creator`, `licence`, `licence_url`, `source_url`, `changes` (đã cắt, thu nhỏ thế nào).
3. App tự làm phần còn lại: ảnh thành avatar khi cài nhân vật mẫu; một dòng ghi công được thêm vào "ghi chú của người tạo" (để đi theo file export); ghi công hiện ở sheet Tài khoản → "Giới thiệu & bản quyền ảnh".

Không có mạng thì dùng avatar chữ cái trên nền phẳng. Không vẽ hình trang trí thay ảnh.

## 4. Ảnh người dùng tải lên

- Avatar nhân vật, avatar persona, ảnh đại diện và ảnh bìa tài khoản do người dùng tải lên, lưu trong thư mục ảnh của app (mặc định `data/avatars/`, đổi bằng `LYRIS_AVATARS_DIR`).
- Lyris không kiểm tra nguồn những ảnh này. Người tải lên chịu trách nhiệm.
- Khi có Phase 7 (chia sẻ ra ngoài máy), cần thêm chỗ ghi nguồn cho ảnh nhân vật công khai.
