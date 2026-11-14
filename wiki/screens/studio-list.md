# Studio: danh sách nhân vật

- **Đường dẫn:** `#/studio` · **File:** `frontend/src/pages/studio/CardListPage.tsx`

## Dùng để làm gì

Chỗ làm việc của người tạo nhân vật: xem mọi nhân vật của bạn, tạo mới, để AI viết nháp, nhập card từ file, và xem nhanh persona.

## Có gì trên màn hình

Ở điện thoại 390px, từ trên xuống (dưới header chung có wordmark, nút theme, avatar):

1. **Tiêu đề "Xưởng dệt tâm hồn"** và dòng "Tạo nhân vật, đặt cảm xúc ban đầu và giữ thế giới của họ ở một chỗ."
2. **Ba nút**: "Tạo nhân vật" (rộng hết hàng, mở [trình sửa](card-editor.md) trống), rồi "AI viết nháp" (mở [hộp AI viết nháp](draft-dialog.md)) và "Nhập card" cạnh nhau. "Nhập card" nhận Character Card V1/V2 dạng .json hoặc .png, tối đa 8MB.
3. **Thông báo** sau khi lưu, xoá hay nhập (một khung xanh, đóng được).
4. **"Nhân vật của bạn · N"**. Từ 5 nhân vật trở lên có thêm ô "Tìm nhân vật" (tên, vai trò, tag).
5. **Thẻ nhân vật**, mỗi thẻ có:
   - Avatar chân dung, tên, vai trò (chữ vàng).
   - Dòng tác giả: "bởi @handle" kèm nhãn **"Riêng tư"** hoặc **"Công khai"**. Nhân vật mẫu chỉ ghi "Mẫu của Lyris".
   - Giới tính · ngôn ngữ · số story ("chưa có story" nếu chưa có).
   - Hai dòng mô tả.
   - "Sửa <ngày>" và nút **"Bước vào câu chuyện"** (mở hồ sơ nhân vật với sheet bắt đầu story mở sẵn).
   - Chạm chỗ khác trên thẻ thì mở trình sửa.
6. **Khối "Persona của bạn"**: "Người bạn nhập vai; thay cho {{user}} trong mọi card." Nút "Quản lý persona" (hoặc "Thêm persona" khi chưa có). Bên dưới là tối đa 3 persona (avatar, tên, giới tính, số story) và "và N persona khác".
7. **Thanh tab nổi** ở đáy.

Từ 640px: thẻ nhân vật thành 2 cột. Nếu số thẻ lẻ thì thẻ cuối rộng hết hai cột. Từ 768px: ba nút nằm cùng hàng với tiêu đề, bên phải. Khối persona chia hai cột (chữ bên trái, danh sách bên phải).

## Trạng thái

- **Đang tải:** khung xương 4 thẻ.
- **Rỗng:** "Chưa có nhân vật nào. Tạo bằng form, để AI viết nháp từ một dòng ý tưởng, hoặc import card .json/.png." + nút "Tạo nhân vật đầu tiên".
- **Tìm không thấy:** "Không có nhân vật nào khớp “…”."
- **Đang đọc file nhập:** nút đổi thành "Đang đọc…".
- **Lỗi nhập:** "File quá lớn (tối đa 8MB).", "Chỉ import được card dạng .json hoặc .png (Character Card V1/V2).", hoặc "Không import được “<tên file>”: …". Nhập thành công thì mở trình sửa với bản nhập chưa lưu.
- **Lỗi tải:** khung lỗi, có "Thử lại" khi danh sách đang trống. Không tải được persona: "Không tải được danh sách persona."

## Tính năng

- [Xưởng nhân vật](../features/F18-xuong-nhan-vat.md)
- [AI viết nháp](../features/F19-ai-viet-nhap.md)
- [Nhập và xuất card](../features/F20-nhap-xuat-card.md)
- [Nhân vật công khai](../features/F31-nhan-vat-cong-khai.md) (nhãn Riêng tư / Công khai)
- [Persona](../features/F21-persona.md)

Chi tiết: [DESIGN.md](../../DESIGN.md) trang 3, [design-impl.md §6.5](../../docs/design-impl.md), [phase2.md](../../docs/phase2.md).
