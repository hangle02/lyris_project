# Chỉ số cảm xúc phải giảm được

- **Ngày:** 2026-11-13 · **Ai quyết:** người dùng + đo đạc

## Bối cảnh

Người dùng hỏi: làm điều nhân vật thấy không đúng thì chỉ số có giảm không. Đo thật: 11/12 lượt thường đổi đúng 2 chỉ số, hầu như luôn +1/+2.

## Lựa chọn

Prompt trích xuất có trường reason (một câu) và tone (everyday / warm / hurt / mixed) trước các con số. Mỗi chỉ số có dòng "tăng khi, giảm khi". pick_changes chọn theo ấm lòng / tổn thương (WARM_SIGN): everyday không đổi gì, warm tối đa 2, hurt tối đa 3. Mỗi giá trị trong ±5.

## Vì sao

Sau khi sửa: ghen ra tin cậy -1, nhung nhớ +2, lo sợ +2; quên sinh nhật ra thương mến -1, tin cậy -1; hỏi han thường ngày nhiều nhất một ±1. Bỏ reason thì kết quả kém đi.

## Đã cân nhắc

Giữ 2 thay đổi lớn nhất theo trị tuyệt đối (top_delta cũ); xét theo dấu số học.

## Nguồn

- Lời người dùng, 2026-11-13 03:47 (xem [raw/](../raw/))
- [docs/phase3.md](../../docs/phase3.md) §10.5, §10.7
