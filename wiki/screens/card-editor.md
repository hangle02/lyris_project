# Trình sửa nhân vật

- **Đường dẫn:** `#/studio/new` (nhân vật mới), `#/studio/<id>` (sửa). Thêm `?section=world` thì cuộn tới phần Thế giới. · **File:** `frontend/src/pages/studio/CardEditorPage.tsx` (form: `CardForm.tsx`, `EmotionSection.tsx`; chat thử: `TestChatPanel.tsx`; xem trước prompt: `PromptPreviewPanel.tsx`)

## Dùng để làm gì

Tạo và sửa toàn bộ card nhân vật, rồi chat thử ngay (kể cả khi chưa lưu). Cũng là nơi bật "Công khai", nhân bản, xuất file và xoá nhân vật.

## Có gì trên màn hình

Ở điện thoại 390px, từ trên xuống. Không có thanh tab nổi.

1. **Header phụ**: "Về Studio", tên nhân vật (hoặc "Nhân vật mới"), dòng trạng thái ("Chưa lưu", "Có thay đổi chưa lưu", "Đã lưu <ngày> · N story", "Bản nháp AI · chưa lưu", "Card import · chưa lưu") và nút **"Lưu nhân vật" / "Lưu" / "Đã lưu"** (Ctrl/⌘ + S).
2. **Tab**: "Hồ sơ", "Chat thử", và "Xem trước" (chỉ khi bật Công cụ nâng cao).
3. **Tab Hồ sơ**, từng phần:
   - **Cơ bản**: avatar (chọn, đổi, xoá ảnh), Tên nhân vật, Vai trò, công tắc **"Công khai"**, Giới tính, Ngôn ngữ của card, Bộ văn phong, Đại từ dẫn truyện cho nhân vật (tuỳ chọn), Tag.
   - **Tính cách và bí mật**: Mô tả, Tính cách, Ngoại hình, Hoàn cảnh, Mục tiêu, Bí mật, Cách nói, Lời nói đặc trưng (tuỳ chọn).
   - **Cảm xúc ban đầu**: 6 thanh trượt từ 0 đến 100, điểm xuất phát cho mỗi story mới.
   - **Xưng hô**: Nhân vật tự xưng, Gọi người chơi, Tên gọi thân mật cho người chơi, Xưng hô với người khác, có các cặp mẫu để chọn nhanh.
   - **Mở đầu**: Bối cảnh mặc định, Lời mở đầu (và các lời mở đầu khác), Ví dụ thoại.
   - **[Thế giới](lorebook-section.md)**.
   - **Ghi chú của người tạo**: "Chỉ bạn thấy, nhân vật không bao giờ đọc."
   - **Dùng nhân vật**: "Mở story mới", "Nhân bản", "Xuất JSON", "Xuất PNG" (Character Card V2).
   - **Xoá nhân vật**: viền đỏ, nói rõ số story đang dùng nhân vật. Hỏi lại trước khi xoá.
4. **Tab Chat thử**: một cuộc trò chuyện nháp với card đang sửa, dòng "Không lưu gì". Chọn persona để chat.
5. **Tab Xem trước** (nâng cao): prompt gửi cho model và ước lượng token.

Từ 1024px: không còn tab trên cùng. Form bên trái, bảng phụ rộng 440px bên phải (500px từ 1280px) luôn hiện "Chat thử". Bật Công cụ nâng cao thì bảng phụ có hai tab "Xem trước prompt" và "Chat thử".

Công tắc "Công khai": bật rồi phải bấm Lưu mới chia sẻ ("Bấm Lưu để chia sẻ."). Khi đã lưu công khai, có nút **"Người khác thấy gì"** mở [hộp xem trước](public-preview.md).

## Trạng thái

- **Đang tải:** khung xương form.
- **Không tìm thấy:** "Không tìm thấy nhân vật này (có thể đã bị xoá)."
- **Chưa lưu (dirty):** dòng trạng thái đổi. Rời trang thì hỏi "Bạn có thay đổi chưa lưu. Rời trang và bỏ các thay đổi này?"
- **Lỗi kiểm tra:** khung "Chưa lưu được:" liệt kê từng lỗi (tên trống, vai trò quá dài, lời nói đặc trưng quá dài, quá nhiều tag...). Chat thử cũng báo "Sửa form trước khi chat thử:".
- **Bản nháp AI / card nhập:** khung nhắc kiểm tra rồi bấm Lưu. Bản nháp AI có thêm "Lưu ý từ bản nháp:".
- **Chưa lưu lần nào:** phần "Dùng nhân vật" chỉ có câu "Lưu nhân vật trước để mở story, nhân bản hoặc xuất file."
- **Có thay đổi chưa lưu:** "Nhân bản" bị khoá. Xuất file dùng bản đã lưu.
- **Nhân vật mẫu:** không có công tắc "Công khai".
- **Công cụ nâng cao tắt:** không có tab Xem trước, không có ước lượng token.

## Tính năng

- [Xưởng nhân vật](../features/xuong-nhan-vat.md)
- [Nhập và xuất card](../features/nhap-xuat-card.md)
- [Ma trận cảm xúc](../features/ma-tran-cam-xuc.md) (cảm xúc ban đầu)
- [Sổ thế giới](../features/so-the-gioi.md)
- [Nhân vật công khai](../features/nhan-vat-cong-khai.md)
- [Văn phong và xưng hô](../features/van-phong-xung-ho.md)
- [Ẩn chữ kỹ thuật](../features/an-chu-ky-thuat.md) (xem trước prompt chỉ trong Công cụ nâng cao)

Chi tiết: [phase2.md](../../docs/phase2.md), [design-impl.md §6.5](../../docs/design-impl.md), [auth.md §7.3](../../docs/auth.md).
