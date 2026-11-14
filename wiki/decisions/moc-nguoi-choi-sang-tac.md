# Thưởng sáng tác: "người chơi" là ai và trả mốc thế nào

> **Đã thay (2026-11-14 22:15)** bởi [xep-hang-nhan-vat-hot](xep-hang-nhan-vat-hot.md): PO chọn thay hẳn thưởng mốc 10/50/100
> người chơi bằng thưởng bảng xếp hạng "Nhân vật hot" (top 100/50/10 → +100/+200/+300) và +50 khi công khai lần đầu
> ([raw](../raw/2026-11-14-f44-bang-xep-hang-tra-loi.md)). **Còn đúng:** định nghĩa "người chơi" (mục đầu của "Lựa chọn") và lý do
> của nó. **Hết hiệu lực:** số coin theo mốc, trần mốc 10 theo người tạo, dòng "Mốc tiếp theo" trong trình sửa. Trang giữ lại để
> biết vì sao các dòng sổ `milestone:` cũ tồn tại.

- **Ngày:** 2026-11-14 · **Ai quyết:** người dùng (3C: thưởng một lần ở mốc 10, 50, 100 người chơi) + thiết kế (định nghĩa người chơi, số coin: "(tạm chọn)")

## Bối cảnh

Chủ dự án muốn thưởng người sáng tác khi nhân vật công khai được nhiều người khác trò chuyện, và chọn thưởng một lần theo mốc 10, 50, 100 người chơi ([raw](../raw/2026-11-14-coin-tra-loi.md)). Người khác chơi nhân vật công khai bằng một bản sao chụp lúc bắt đầu story (F31). Cần một định nghĩa khó lách.

## Lựa chọn

- **Người chơi** của nhân vật X = tài khoản không phải người tạo X, không phải chủ máy, có story chơi bằng bản sao của X, và đã có **ít nhất 3 câu trả lời đã trả coin** cộng dồn trong các story đó, ở **ít nhất 2 ngày coin khác nhau** (tạm chọn). Mỗi tài khoản tính một lần cho mỗi nhân vật.
- Thưởng (PO chốt 2026-11-14): 10 người chơi +100 coin, 50 người +300, 100 người +600. Mỗi mốc trả một lần cho mỗi nhân vật. Chưa có mốc sau 100.
- **Trần mốc 10 theo người tạo** (tạm chọn): tối đa 3 lần thưởng mốc 10 (300 coin) trong 7 ngày coin gần nhất, trên mọi nhân vật của người đó; lần vượt trần chờ, không mất. Mốc 50/100 không có trần.
- "Nhật ký" của chủ máy hiện mọi lần thưởng mốc.
- Chỉ trả khi nhân vật đang Công khai, chưa bị ẩn, người tạo không bị khoá và không phải chủ máy. Mốc đạt lúc nhân vật Riêng tư hay người tạo bị khoá được trả sau, khi điều kiện đủ lại.
- Nhân vật bị xoá: ngừng đếm, coin đã trả giữ nguyên. Người chơi xoá tài khoản: mốc đã trả không bị thu lại.
- Người tạo thấy số người chơi và mốc tiếp theo trong trình sửa nhân vật.

## Vì sao

Ba câu trả lời đã trả coin ở hai ngày khác nhau nghĩa là người đó thật sự quay lại chơi, không chỉ bấm thử. Bản trước của trang này viết "tài khoản ảo phải tiêu 18 coin nên không lời": **sai**, vì 18 coin đó lấy từ quà 300 và +60 mỗi ngày, người lách không mất gì. Thứ thật sự giới hạn tài khoản ảo là: mỗi tài khoản cần một mã mời của chủ máy; "2 ngày" làm việc dựng mốc chậm lại; và trần mốc 10 theo người tạo. Không có trần thì xoá rồi đăng lại, hay "Nhân bản" rồi công khai, là đếm lại từ 0 với chính nhóm bạn cũ, mỗi nhân vật +100, nhiều lần mỗi ngày. Với trần, phần lặp này tối đa 300 coin mỗi 7 ngày, ít hơn quà đăng nhập (420 coin mỗi 7 ngày), và chủ máy thấy từng lần trong "Nhật ký" để thu lại bằng "Cộng/trừ coin". Mốc 50/100 cần 50/100 mã mời nên không cần trần. Không tính chủ máy vì chủ máy chat miễn phí. Mốc đạt lúc riêng tư vẫn trả sau, để người tạo không bị phạt vì tạm ẩn nhân vật để sửa.

## Đã cân nhắc

- Tính mọi người bắt đầu story (0 lượt): bấm "Bước vào câu chuyện" là được tính, quá dễ lách.
- Mỗi người chơi chỉ tính một lần cho mỗi người tạo trong 30 ngày: chặn đăng lại tốt hơn, nhưng phạt người tạo thật có nhiều nhân vật được cùng một nhóm fan chơi.
- Thưởng theo mỗi người chơi (3A, +5 coin mỗi người) hay theo tổng lượt (3B): chủ dự án chọn mốc.
- Thu hồi thưởng khi nhân vật bị ẩn vì báo cáo: phức tạp, và chủ máy đã có "Cộng/trừ coin" có lý do cho trường hợp lạm dụng.

## Nguồn

- [docs/coins.md §5, §9](../../docs/coins.md)
- [F44](../features/F44-thuong-sang-tac.md), [ban-sao-nhan-vat-cong-khai](ban-sao-nhan-vat-cong-khai.md)
