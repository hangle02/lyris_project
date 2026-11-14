# Studio: tạo và sửa nhân vật

- **Trạng thái:** Đã xong · **Phase:** Phase 2, 2b
- **Màn hình:** [studio-list](../screens/studio-list.md), [card-editor](../screens/card-editor.md)

## Là gì

Form sửa card theo phần: Cơ bản (tên, vai trò, avatar, Công khai), Xưng hô, Tính cách và bí mật, Mở đầu, Cảm xúc ban đầu, Thế giới, Ghi chú của người tạo. Có Chat thử trước khi lưu, nhân bản, xoá. 'Xem trước prompt' và số token chỉ hiện khi bật công cụ nâng cao.

## Hoạt động thế nào

- Vào tab Studio, bấm tạo nhân vật mới hoặc mở nhân vật có sẵn.
- Form chia thành từng phần: Cơ bản, Xưng hô, Tính cách và bí mật, Mở đầu, Cảm xúc ban đầu, Thế giới, Ghi chú của người tạo.
- Bấm 'Chat thử' để thử nhân vật trước khi lưu.
- Có nhân bản và xoá nhân vật.

Kỹ thuật:

- Card lưu theo chuẩn Character Card V2, phần riêng của Lyris nằm ở `extensions.lyris`.
- API ở `api/routes_studio.py`; xem trước prompt ở `studio/preview.py` (chỉ hiện khi bật công cụ nâng cao).
- `lib/signatureLines.ts` kiểm 'Lời nói đặc trưng' (tối đa 3 dòng, mỗi dòng 140 ký tự).

## Done when

- [x] Tạo nhân vật bằng tay, lưu, mở lại thấy đủ trường.
- [x] Tải avatar lên; ảnh hiện ở Studio, Khám phá, hồ sơ và chat.
- [x] 'Lời nói đặc trưng (tuỳ chọn)': hơn 3 dòng hoặc một dòng dài quá 140 ký tự thì chặn lưu.
- [x] Chat thử chạy với persona mặc định, có ba chấm khi chờ.
- [x] Nhân bản tạo card mới; xoá báo số story bị xoá theo.
- [x] Rời trang khi còn thay đổi chưa lưu thì hỏi lại.
- [x] Tắt công cụ nâng cao thì không còn tab 'Xem trước' và tốc độ token.

## Liên quan

- **Code:** [`frontend/src/pages/studio/CardEditorPage.tsx`](../../frontend/src/pages/studio/CardEditorPage.tsx), [`frontend/src/pages/studio/CardForm.tsx`](../../frontend/src/pages/studio/CardForm.tsx), [`frontend/src/pages/studio/AvatarField.tsx`](../../frontend/src/pages/studio/AvatarField.tsx), [`frontend/src/pages/studio/EmotionSection.tsx`](../../frontend/src/pages/studio/EmotionSection.tsx), [`frontend/src/pages/studio/TestChatPanel.tsx`](../../frontend/src/pages/studio/TestChatPanel.tsx), [`frontend/src/pages/studio/PromptPreviewPanel.tsx`](../../frontend/src/pages/studio/PromptPreviewPanel.tsx), [`frontend/src/lib/cardForm.ts`](../../frontend/src/lib/cardForm.ts), [`frontend/src/lib/signatureLines.ts`](../../frontend/src/lib/signatureLines.ts), [`backend/lyris/api/routes_studio.py`](../../backend/lyris/api/routes_studio.py), [`backend/lyris/studio/preview.py`](../../backend/lyris/studio/preview.py)
- **Tài liệu:** [phase2.md](../../docs/phase2.md), [design-impl.md §6.5, §16](../../docs/design-impl.md)
- **Quyết định:** [card-doi-story-doi-theo](../decisions/card-doi-story-doi-theo.md), [an-chu-ky-thuat](../decisions/an-chu-ky-thuat.md)
