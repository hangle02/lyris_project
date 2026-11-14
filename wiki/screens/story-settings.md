# Thiết lập story

- **Đường dẫn:** trong `#/chat/<id>`, nút bánh răng trên header (hoặc `?open=settings` để chụp ảnh kiểm tra) · **File:** `frontend/src/components/StorySettingsPanel.tsx`

## Dùng để làm gì

Sửa thiết lập của một story đang chơi, và xoá story. Chế độ Story/DM và cách đọc suy nghĩ cũng đổi nhanh được trên header, không cần vào đây.

## Có gì trên màn hình

Ở điện thoại 390px là sheet trượt từ đáy. Từ trên xuống:

1. **Tiêu đề "Thiết lập story"** và dòng "<tên nhân vật> và <tên persona>".
2. **Tiêu đề** của story.
3. **Bối cảnh**.
4. **Ngôn ngữ**: Tiếng Việt / Tiếng Anh.
5. **Kiểu quan hệ**: Nam - nữ, Nam - nam (đam mỹ), Nữ - nữ (bách hợp), Không lãng mạn.
6. **Ngôi kể**: Ngôi thứ ba / Ngôi thứ nhất.
7. **Đại từ dẫn truyện** cho nhân vật và cho bạn (có gợi ý sẵn).
8. **"Suy nghĩ của nhân vật ở Story"**: Lồng trong truyện / Một đoạn ở cuối.
9. Công tắc **"Đọc suy nghĩ của nhân vật"**.
10. **"Nâng cao"** (gập sẵn, chỉ chủ máy thấy): ô chọn **"Model trả lời"** cho story này. Tự mở nếu story đang dùng model lạ.
11. **Vùng "Xoá story"** viền đỏ: "Xoá story này và mọi tin nhắn của nó. Nhân vật và persona vẫn giữ nguyên." + nút "Xoá story…".
12. **Chân sheet**: "Huỷ" và "Lưu". Nút "Lưu" chỉ bật khi có thay đổi hợp lệ.

Từ 640px: thành hộp thoại giữa màn hình, cỡ vừa.

## Trạng thái

- **Ngôn ngữ khác ngôn ngữ của nhân vật:** dưới lựa chọn có cảnh báo, ví dụ "Nhân vật được viết bằng tiếng anh; nhân vật sẽ phải tự chuyển ngôn ngữ."
- **Đã sửa, chưa lưu:** dòng nhỏ "Áp dụng từ lượt trả lời sau; các lượt đã có giữ nguyên." Có lỗi nhập thì dòng cảnh báo thay vào.
- **Đang lưu:** nút "Lưu" quay, sheet không đóng được.
- **Lỗi:** câu lỗi đỏ ở chân sheet + "Chi tiết".
- **Xác nhận xoá:** "Xoá vĩnh viễn “<tiêu đề>” cùng toàn bộ tin nhắn, đánh giá và lịch sử sửa? Dữ liệu này cũng dùng để train sau này. Không hoàn tác được." + "Huỷ" / "Xoá vĩnh viễn". Nếu nhân vật đang trả lời: "Nhân vật đang trả lời. Hãy đợi xong hoặc bấm Dừng rồi mới xoá."
- **Model:** không kết nối được Ollama hoặc chưa có model thì ô chọn nói lý do bằng một câu.

## Tính năng

- [Văn phong và xưng hô](../features/van-phong-xung-ho.md)
- [Đọc suy nghĩ](../features/doc-suy-nghi.md)
- [Ẩn chữ kỹ thuật](../features/an-chu-ky-thuat.md) (model nằm trong "Nâng cao", chỉ chủ máy)

Chi tiết: [auth.md §1.1](../../docs/auth.md) (ai được đổi model), [design-impl.md §15](../../docs/design-impl.md).
