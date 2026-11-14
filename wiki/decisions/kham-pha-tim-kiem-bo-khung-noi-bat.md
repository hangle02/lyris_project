# Khám phá: bỏ khung nổi bật, thêm ô tìm và dải "Nhân vật hot"

- **Ngày:** 2026-11-14 · **Ai quyết:** người dùng ("thiết kế thêm thanh tìm kiếm nữa, bạn có thể bỏ cái hạ vy to to đi, thay bằng
  bảng xếp hạng hay gì đó", [raw](../raw/2026-11-14-f44-bang-xep-hang-tra-loi.md)) + thiết kế (các điểm ghi "(tạm chọn)")

## Bối cảnh

Đầu trang Khám phá có khung nhân vật nổi bật lớn (luôn là Hạ Vy, ảnh cảnh 3:1, nút "Bước vào câu chuyện"). Chủ dự án muốn bỏ nó,
thay bằng bảng xếp hạng ([xep-hang-nhan-vat-hot](xep-hang-nhan-vat-hot.md)), và thêm thanh tìm kiếm.

## Lựa chọn

- **Bỏ khung nổi bật.** Hạ Vy và mọi nhân vật mẫu nằm trong lưới "Nhân vật" như các nhân vật khác. Backend giữ cờ `featured` của
  nhân vật mẫu (không đổi API, tạm chọn); frontend không dùng nữa.
- **Ô "Tìm nhân vật"** ở trên cùng, dưới tiêu đề: placeholder ngắn "Tìm nhân vật", nhãn đầy đủ ở aria-label "Tìm nhân vật theo
  tên, tag hoặc giới thiệu" (luật [placeholder-ngan](placeholder-ngan.md)).
- Tìm **không dấu, không phân biệt hoa thường**, mọi từ phải khớp **phần đầu một từ** ("ha" ra "Hạ", không ra "thành"; sau rà soát 2026-11-14), trong tên, vai trò, tag, giới thiệu (tạm chọn). Lọc ở trình
  duyệt trên danh sách đã tải (nhân vật của mình, mẫu, chia sẻ), không có API mới (tạm chọn: số nhân vật trên một máy nhỏ). Debounce
  250 ms (tạm chọn).
- Tìm và chip cảm xúc dùng cùng lúc ("và"). Chữ đã gõ không lưu khi rời trang và không vào sự kiện (tạm chọn).
- **Dải "Nhân vật hot"**: 3 hạng đầu + "Xem bảng xếp hạng" → `#/explore/hot` (tạm chọn: 3 hàng ~170px ở 390px, không đẩy lưới
  xuống quá xa). Chỉ ẩn khi đang tìm; bảng rỗng thì một dòng báo rỗng, chưa tải được thì tiêu đề và nút (sau rà soát 2026-11-14: dải là lối vào duy nhất của bảng).
- Dải là danh sách xếp hạng, không phải lưới: nhân vật trên dải **vẫn có ô** trong lưới (tạm chọn). Luật "một nhân vật chỉ hiện
  một lần trên một trang" của [design/README.md](../design/README.md) đổi thành "một lần trong mỗi lưới".

## Vì sao

- Khung nổi bật luôn là một nhân vật mẫu, chiếm gần nửa màn 390px; người quay lại app lần thứ hai không cần thấy lại.
- Bảng xếp hạng ở đầu trang cho thấy nhân vật người khác thật sự chơi, và là chỗ người sáng tác thấy nhân vật của mình.
- Gõ không dấu là thói quen trên điện thoại; tìm có dấu thì "ha vy" không ra "Hạ Vy".
- Bỏ nhân vật trên dải khỏi lưới sẽ làm lưới và kết quả tìm thiếu nhân vật, khó hiểu hơn việc thấy một nhân vật hai lần.

## Đã cân nhắc

- Dải top 10 cuộn ngang: dễ làm trang cuộn ngang ở 390px (luật "không tràn ngang"), và ẩn 7 hàng sau mép màn.
- Tìm ở server (`GET /api/search`): cần khi có hàng nghìn nhân vật công khai; chưa cần trên một máy.
- Giữ khung nổi bật nhưng nhỏ lại: PO muốn bỏ.

## Nguồn

- [F22](../features/F22-kham-pha.md), [F46](../features/F46-bang-xep-hang-nhan-vat-hot.md), [F47](../features/F47-tim-nhan-vat.md)
- [screens/explore.md](../screens/explore.md), [screens/hot-ranking.md](../screens/hot-ranking.md)
