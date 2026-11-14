# Khám phá

- **Đường dẫn:** `#/explore` · **File:** `frontend/src/pages/explore/ExplorePage.tsx`

## Dùng để làm gì

Tìm nhân vật để bắt đầu story. Có ô tìm nhân vật, dải "Nhân vật hot", chip lọc theo cảm xúc, lưới nhân vật của bạn (cả nhân vật mẫu chưa cài) và lưới nhân vật người khác chia sẻ. Chạm một ô để mở [Hồ sơ nhân vật](character-profile.md).

> **Đổi 2026-11-14 22:15** (PO, [raw](../raw/2026-11-14-f44-bang-xep-hang-tra-loi.md)): bỏ khung nhân vật nổi bật (Hạ Vy) ở đầu trang; thay bằng ô "Tìm nhân vật" ([F47](../features/F47-tim-nhan-vat.md)) và dải "Nhân vật hot" ([F46](../features/F46-bang-xep-hang-nhan-vat-hot.md)). Đã build cùng ngày.

## Có gì trên màn hình

Ở điện thoại 390px, từ trên xuống (dưới header chung có wordmark, chip coin, nút theme, avatar):

1. **Tiêu đề "Khám phá"** và dòng phụ "Chạm một nhân vật để xem hồ sơ của họ."
2. **Ô tìm** (F47): `input type="search"` nền `surface-2`, bo `rounded-full`, cao 44px, icon `IconSearch` có sẵn (`muted`) bên trái, placeholder **"Tìm nhân vật"**, aria-label **"Tìm nhân vật theo tên, tag hoặc giới thiệu"**. Có chữ thì bên phải có nút `IconX` (aria-label **"Xoá tìm kiếm"**, vùng chạm 44 × 44px). Lọc sau 250 ms kể từ lần gõ cuối, không dấu, không phân biệt hoa thường.
3. **Dải "Nhân vật hot"** (F46), `section aria-labelledby="explore-hot"`: tiêu đề "Nhân vật hot" và bên phải nút chữ **"Xem bảng xếp hạng"** (→ `#/explore/hot`, vùng chạm 44px). Dưới là **3 hàng đầu** của bảng xếp hạng, mỗi hàng giống hàng ở [Nhân vật hot](hot-ranking.md): hạng, ảnh tròn 44px, tên, "bởi @handle", "{n} người chơi". Chạm hàng mở hồ sơ. Khung `bg-surface rounded-card`, mỗi hàng cao 56px. Bảng rỗng: một dòng **"Chưa có nhân vật nào trên bảng xếp hạng."** thay 3 hàng; chưa tải được: chỉ tiêu đề và nút (dải là lối vào duy nhất của `#/explore/hot`). **Không có dải** chỉ khi ô tìm đang có chữ.
4. **Mục "Nhân vật"** kèm số đếm (khi lọc hay tìm: "3 / 8").
5. **Chip lọc vibe**: "Tất cả" và các vibe lấy từ nhân vật mẫu. Chạm lại chip đang chọn thì bỏ lọc. Tìm và chip cùng lúc: nhân vật phải khớp cả hai.
6. **Lưới "Nhân vật"**: 2 cột cố định. Mỗi ô có ảnh 4:3, tên, vai trò (hoặc "Chưa có vai trò"), tối đa hai dòng giới thiệu, và dòng tác giả: "Mẫu của Lyris" cho nhân vật mẫu, "bởi @handle" cho nhân vật của tài khoản. Hạ Vy nằm trong lưới như mọi nhân vật mẫu.
7. **Mục "Nhân vật được chia sẻ"**: nhân vật công khai của tài khoản khác, kèm dòng "Người khác trên Lyris này chia sẻ. Story bạn bắt đầu là của riêng bạn." Lưới giống hệt lưới trên, mỗi ô ghi "bởi @handle". Khi tìm: chỉ còn ô khớp; không còn ô nào thì cả mục ẩn.
8. **Thanh tab nổi** ở đáy.

Từ 640px: lưới 3 cột, ô tìm rộng tối đa 560px. Từ 1024px: lưới 5 cột; dải "Nhân vật hot" vẫn là 3 hàng (một cột, rộng tối đa 720px).

Quy tắc lưới (người dùng chọn 2026-11-14): số cột cố định, mọi ô ở cả hai mục bằng nhau. Hàng cuối thiếu ô thì để trống, không kéo giãn ô. Các ô trong một hàng cao bằng nhau. Dải "Nhân vật hot" là danh sách xếp hạng, không phải lưới, nên nhân vật trên dải vẫn có ô của nó trong lưới (tạm chọn, [kham-pha-tim-kiem-bo-khung-noi-bat](../decisions/kham-pha-tim-kiem-bo-khung-noi-bat.md)).

## Trạng thái

- **Đang tải:** khung xương của ô tìm, 3 hàng dải "Nhân vật hot" và 4 ô lưới.
- **Chưa có nhân vật nào:** "Chưa có nhân vật nào. Tạo nhân vật đầu tiên trong Studio." + nút "Tạo nhân vật" (mở trình sửa trống).
- **Lọc không có kết quả:** "Chưa có nhân vật nào mang nét “…”." + nút "Xem tất cả".
- **Tìm không có kết quả** (cả hai mục rỗng): "Không tìm thấy nhân vật nào cho “{chữ đã gõ}”." + nút "Xoá tìm kiếm".
- **Không có nhân vật chia sẻ** (hoặc không đọc được): cả mục đó không hiện.
- **Bảng xếp hạng rỗng:** dải "Nhân vật hot" vẫn có tiêu đề và nút "Xem bảng xếp hạng", thay 3 hàng bằng một dòng `muted` **"Chưa có nhân vật nào trên bảng xếp hạng."** (dải là lối vào duy nhất của `#/explore/hot`).
- **Bảng xếp hạng chưa tải được hay lỗi:** dải chỉ có tiêu đề và nút (không báo lỗi ở Khám phá; lỗi chỉ báo ở `#/explore/hot`). Đang tìm thì dải ẩn.
- **Lỗi tải:** "Không tải được danh sách nhân vật." kèm lý do và nút "Thử lại". Không tải được nhân vật mẫu thì lưới vẫn hiện nhân vật của bạn.

## Tính năng

- [Khám phá](../features/F22-kham-pha.md)
- [Bảng xếp hạng Nhân vật hot](../features/F46-bang-xep-hang-nhan-vat-hot.md) (dải ở đầu trang)
- [Tìm nhân vật](../features/F47-tim-nhan-vat.md) (ô tìm)
- [Nhân vật công khai](../features/F31-nhan-vat-cong-khai.md)
- [Giao diện và theme](../features/F26-giao-dien-theme.md)

Chi tiết: [DESIGN.md](../../DESIGN.md) trang 2, [design-impl.md §6.4 và "Lưới Khám phá"](../../docs/design-impl.md), [accounts.md §5](../../docs/accounts.md) (dòng tác giả).
