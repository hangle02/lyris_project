# Sheet "Bước vào câu chuyện"

- **Đường dẫn:** mở trên [Hồ sơ nhân vật](character-profile.md), hoặc thẳng bằng `#/character/<id>?start=1`. Link cũ `#/new-story?card=<id>` được chuyển sang `#/character/<id>?start=1`; không có card thì về [Khám phá](explore.md) · **File:** `frontend/src/pages/character/StartStorySheet.tsx`

## Dùng để làm gì

Chọn persona (bạn sẽ là ai trong story) rồi tạo story. Có thể mở "Tuỳ chỉnh story" để chỉnh trước khi tạo. Không mở thì story dùng thiết lập mặc định.

## Có gì trên màn hình

Ở điện thoại 390px là sheet trượt từ đáy. Từ trên xuống:

1. **Tiêu đề "Chọn persona"** và câu hỏi "Bạn sẽ là ai khi gặp <tên>?".
2. **Dòng nhắc bản sao** (chỉ với nhân vật người khác chia sẻ): "Bạn chơi với <tên> như bây giờ. @handle sửa nhân vật sau này thì story của bạn không đổi."
3. **Danh sách persona** dạng radio: avatar, tên, giới tính và một dòng mô tả. Persona mặc định được chọn sẵn.
4. **"Tạo persona mới"**: form nhỏ ngay trong sheet (Tên persona, Giới tính, Mô tả tuỳ chọn, nút "Tạo persona"). Cạnh đó là link **"Quản lý persona"** tới [trang persona](personas.md).
5. **Disclosure "Tuỳ chỉnh story"** (gợi ý: "Bối cảnh, chế độ Story hay DM, ngôi kể, cách hiện suy nghĩ."). Mở ra có:
   - Tiêu đề
   - Bối cảnh (lấy từ bối cảnh mặc định của nhân vật)
   - Lời mở đầu: chọn một trong các lời mở đầu hoặc "Không có", kèm khung xem trước đúng như sẽ hiện trong story
   - Ngôn ngữ (Tiếng Việt / Tiếng Anh)
   - Chế độ mở đầu: Story / DM
   - Kiểu quan hệ: Nam - nữ, Nam - nam (đam mỹ), Nữ - nữ (bách hợp), Không lãng mạn
   - Ngôi kể: Ngôi thứ ba / Ngôi thứ nhất
   - Đại từ dẫn truyện (cho nhân vật và cho bạn)
   - Suy nghĩ của nhân vật (Story): Lồng trong truyện / Một đoạn ở cuối
   - Công tắc "Đọc suy nghĩ của nhân vật"
6. **Chân sheet**: nút "Bước vào câu chuyện" rộng hết sheet. Nếu thiết lập có vấn đề thì một dòng cảnh báo hiện trên nút.

Từ 640px: thành hộp thoại giữa màn hình, nút ở chân không còn rộng hết.

Với nhân vật mẫu chưa cài, bấm nút sẽ cài nhân vật vào tài khoản trước rồi mới tạo story. Tạo xong thì vào thẳng [chat](chat-story.md).

## Trạng thái

- **Đang tải persona:** khung xương.
- **Chưa có persona:** "Bạn chưa có persona nào. Tạo một persona để bước vào story." Form tạo persona tự mở.
- **Đang chuẩn bị thiết lập** (vừa mở "Tuỳ chỉnh story"): khung xương. Chưa chọn persona: "Chọn một persona trước."
- **Đang tạo story:** nút quay, sheet không đóng được.
- **Lỗi** (tải persona, tải thiết lập, tạo story): câu dễ hiểu kèm "Chi tiết", có "Thử lại" khi thử lại được.
- Đổi persona khi đã sửa thiết lập: các thay đổi của bạn được giữ.

## Tính năng

- [Bước vào câu chuyện](../features/buoc-vao-cau-chuyen.md)
- [Persona](../features/persona.md)
- [Văn phong và xưng hô](../features/van-phong-xung-ho.md)
- [Đọc suy nghĩ](../features/doc-suy-nghi.md)
