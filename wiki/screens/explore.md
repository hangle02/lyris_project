# Khám phá

- **Đường dẫn:** `#/explore` · **File:** `frontend/src/pages/explore/ExplorePage.tsx`

## Dùng để làm gì

Tìm nhân vật để bắt đầu story. Có nhân vật nổi bật, chip lọc theo cảm xúc, lưới nhân vật của bạn (cả nhân vật mẫu chưa cài) và lưới nhân vật người khác chia sẻ. Chạm một ô để mở [Hồ sơ nhân vật](character-profile.md).

## Có gì trên màn hình

Ở điện thoại 390px, từ trên xuống (dưới header chung có wordmark, nút theme, avatar):

1. **Tiêu đề "Khám phá"** và dòng phụ "Chạm một nhân vật để xem hồ sơ của họ."
2. **Khung nhân vật nổi bật** (một nhân vật mẫu): ảnh cảnh tỉ lệ 3:1 ở trên, rồi tên, vai trò (chữ vàng), hai dòng bối cảnh, nút **"Bước vào câu chuyện"** và các vibe của nhân vật. Chạm cả khung thì mở hồ sơ. Chạm nút thì mở hồ sơ với sheet [Bước vào câu chuyện](start-story-sheet.md) mở sẵn.
3. **Mục "Nhân vật"** kèm số đếm (khi lọc: "3 / 8").
4. **Chip lọc vibe**: "Tất cả" và các vibe lấy từ nhân vật mẫu. Chạm lại chip đang chọn thì bỏ lọc.
5. **Lưới "Nhân vật"**: 2 cột cố định. Mỗi ô có ảnh 4:3, tên, vai trò (hoặc "Chưa có vai trò"), tối đa hai dòng giới thiệu, và dòng tác giả: "Mẫu của Lyris" cho nhân vật mẫu, "bởi @handle" cho nhân vật của tài khoản. Nhân vật nổi bật không lặp lại trong lưới, trừ khi đang lọc.
6. **Mục "Nhân vật được chia sẻ"**: nhân vật công khai của tài khoản khác, kèm dòng "Người khác trên Lyris này chia sẻ. Story bạn bắt đầu là của riêng bạn." Lưới giống hệt lưới trên, mỗi ô ghi "bởi @handle".
7. **Thanh tab nổi** ở đáy.

Từ 640px: khung nổi bật thành hai cột (ảnh 240px bên trái, chữ bên phải, ba dòng bối cảnh). Lưới 3 cột. Từ 1024px: lưới 5 cột.

Quy tắc lưới (người dùng chọn 2026-11-14): số cột cố định, mọi ô ở cả hai mục bằng nhau. Hàng cuối thiếu ô thì để trống, không kéo giãn ô. Các ô trong một hàng cao bằng nhau.

## Trạng thái

- **Đang tải:** khung xương của khung nổi bật và 4 ô lưới.
- **Chưa có nhân vật nào:** "Chưa có nhân vật nào. Tạo nhân vật đầu tiên trong Studio." + nút "Tạo nhân vật" (mở trình sửa trống).
- **Lọc không có kết quả:** "Chưa có nhân vật nào mang nét “…”." + nút "Xem tất cả".
- **Không có nhân vật chia sẻ** (hoặc không đọc được): cả mục đó không hiện.
- **Lỗi tải:** "Không tải được danh sách nhân vật." kèm lý do và nút "Thử lại". Không tải được nhân vật mẫu thì lưới vẫn hiện nhân vật của bạn.

## Tính năng

- [Khám phá](../features/kham-pha.md)
- [Nhân vật công khai](../features/nhan-vat-cong-khai.md)
- [Bước vào câu chuyện](../features/buoc-vao-cau-chuyen.md) (nút trên khung nổi bật)
- [Giao diện và theme](../features/giao-dien-theme.md)

Chi tiết: [DESIGN.md](../../DESIGN.md) trang 2, [design-impl.md §6.4 và "Lưới Khám phá"](../../docs/design-impl.md), [accounts.md §5](../../docs/accounts.md) (dòng tác giả).
