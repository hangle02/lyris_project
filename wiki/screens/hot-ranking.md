# Nhân vật hot (bảng xếp hạng)

- **Đường dẫn:** `#/explore/hot` · **File:** `frontend/src/pages/explore/HotPage.tsx`, `frontend/src/pages/explore/hotLogic.ts`, `frontend/src/pages/explore/HotRows.tsx`
- **Giai đoạn:** Đã có ([F46](../features/F46-bang-xep-hang-nhan-vat-hot.md))

## Dùng để làm gì

Xem 100 nhân vật công khai có nhiều người chơi nhất từ trước tới nay, và biết nhân vật của mình đứng thứ mấy. Chạm một hàng mở
[Hồ sơ nhân vật](character-profile.md). Mở từ nút "Xem bảng xếp hạng" ở [Khám phá](explore.md). Tab Khám phá ở thanh tab nổi vẫn
sáng khi đang ở đây.

## Có gì trên màn hình

Ở điện thoại 390px, từ trên xuống (dưới header chung):

1. Nút quay lại `IconButton` (`IconChevronLeft`, aria-label **"Về Khám phá"**, 44 × 44px) → `#/explore`.
2. **Tiêu đề "Nhân vật hot"** (font tiêu đề như "Khám phá") và dòng phụ **"Xếp theo tổng số người chơi. Cập nhật mỗi giờ."** (`muted`).
3. Dòng nhỏ **"Cập nhật lúc {HH:mm}"** (giờ của máy người xem, `faint`).
4. Chỉ với thành viên khi coin bật ([F44](../features/F44-thuong-sang-tac.md)): khối nhỏ `bg-surface-2 rounded-control`, `IconCoin`
   `accent-2`, chữ **"Nhân vật của bạn vào top 100, top 50, top 10 thì bạn được thưởng 100, 200, 300 coin. Thưởng top N chỉ có khi bảng có nhân vật của ít nhất N người tạo khác nhau."** Chủ máy và
   `LYRIS_COINS=0` không có khối này.
5. **Danh sách** `ol aria-label="Bảng xếp hạng Nhân vật hot"`, tối đa 100 hàng, khung `bg-surface rounded-card`, vạch mảnh giữa
   các hàng. Mỗi hàng là một link cao **64px** (tối thiểu 44px), aria-label **"Hạng {r}: {tên}, {n} người chơi"**:
   - số hạng, cột rộng cố định 32px, chữ số đều (`tabular-nums`); hạng 1–3 màu `accent-2` đậm, còn lại `muted`;
   - ảnh tròn 44px (`CharacterPicture`; không có ảnh thì chữ cái đầu trên `surface-3`);
   - tên (đậm, một dòng, quá dài thì "…") và dưới là "bởi @handle" (`muted`, một dòng);
   - bên phải: **"{n} người chơi"** (số kiểu Việt Nam: "1.200 người chơi").
   Hàng của nhân vật của chính người xem có viền trái 3px `accent` (tạm chọn) để dễ thấy.
6. **Thanh tab nổi** ở đáy; danh sách có khoảng đệm dưới để hàng cuối không bị che.

Từ 640px: danh sách rộng tối đa 720px, giữa màn. Không có lưới ở màn này nên luật lưới ô bằng nhau không áp dụng; mọi hàng cao
bằng nhau.

## Trạng thái

- **Đang tải:** ba chấm nhảy dưới tiêu đề, rồi 8 hàng khung xương.
- **Bảng rỗng:** **"Chưa có nhân vật nào trên bảng xếp hạng."** + **"Công khai nhân vật của bạn trong Studio để người khác cùng chơi."** + nút **"Mở Studio"** (→ `#/studio`).
- **Lỗi tải:** **"Không tải được bảng xếp hạng."**, chữ gốc dưới "Chi tiết", nút **"Thử lại"**.
- Không có chữ kỹ thuật (không "snapshot", "rank", "API"); không có số liệu máy.

## Tính năng

- [Bảng xếp hạng Nhân vật hot](../features/F46-bang-xep-hang-nhan-vat-hot.md)
- [Thưởng sáng tác theo bảng xếp hạng](../features/F44-thuong-sang-tac.md)
- [Hồ sơ nhân vật](../features/F23-ho-so-nhan-vat.md)

Chi tiết: [docs/coins.md §5.2, §10.5](../../docs/coins.md), [design/style.md](../design/style.md), quyết định
[xep-hang-nhan-vat-hot](../decisions/xep-hang-nhan-vat-hot.md).
