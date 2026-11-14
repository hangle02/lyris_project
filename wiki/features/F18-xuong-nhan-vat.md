# F18 — Studio: tạo và sửa nhân vật

- **Trạng thái:** xem `memory/features.json` · **Phase:** Phase 2, 2b
- **Giai đoạn:** Đã có
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

- [ ] Unit: tạo, đọc, sửa, xoá card qua API giữ đủ trường; kiểm dữ liệu báo lỗi tiếng Việt.
- [ ] Unit: tải avatar: ảnh được chuẩn hoá (xoay theo EXIF, bỏ metadata, tối đa 768px); file lạ hoặc quá lớn bị từ chối.
- [ ] Unit: 'Lời nói đặc trưng (tuỳ chọn)': hơn 3 dòng hoặc một dòng dài quá 140 ký tự thì chặn lưu; lưu thì làm sạch. Trình sửa kiểm chữ ĐANG GÕ (`saveProblems`), không kiểm bản đã làm sạch (bản đó chỉ giữ 3 dòng nên dòng thứ 4 từng bị bỏ âm thầm).
- [ ] Unit: nhân bản tạo card mới kèm bản sao avatar; xoá card trả về các story bị xoá theo.
- [ ] Unit: chat thử ở Studio stream mà không lưu gì, dùng model chat mặc định.
- [ ] Unit: `isDirty` bỏ qua trường không phải nội dung; reset tài khoản (`allowForcedLeave`) cho tải lại trang mà không hỏi.
- [ ] Unit: router chạy guard rời trang (`addNavigationGuard`) TRƯỚC khi báo đổi màn cho `useRoute`; guard huỷ thì màn không đổi.
- [ ] Bot: ở `#/studio`, mở một nhân vật thì trình sửa `#/studio/<id>` hiện tên đã lưu; sửa tên, bấm Lưu, tải lại thì tên mới còn.
- [ ] Bot: nhập 4 dòng vào 'Lời nói đặc trưng (tuỳ chọn)' rồi bấm Lưu thì không lưu được và hiện 'Chưa lưu được:' (Tối đa 3 lời nói đặc trưng); tải lại thì dòng thứ 4 không có.
- [ ] Bot: trong 'Xem trước và chat thử', gửi một tin thì có ba chấm khi chờ rồi có câu trả lời.
- [ ] Bot: 'Công cụ nâng cao' tắt thì trình sửa không có tab 'Xem trước' và không có chữ 'token'.
- [ ] Bot: ở `#/studio/<id>` sửa 'Tên nhân vật' mà chưa lưu rồi bấm 'Về Studio' thì trình duyệt hỏi lại ('Bạn có thay đổi chưa lưu…'); bấm Huỷ thì ở lại và chữ đang sửa còn nguyên, bấm OK thì về `#/studio` và tên đã lưu không đổi.

## Tests

- backend/tests/test_api_studio.py::test_card_crud
- backend/tests/test_api_studio.py::test_card_validation
- backend/tests/test_api_studio.py::test_card_validation_pydantic_vietnamese
- backend/tests/test_api_studio.py::test_avatar_upload_get_replace_delete
- backend/tests/test_api_studio.py::test_avatar_rejects_bad_and_huge_images
- backend/tests/test_api_studio.py::test_duplicate_copies_avatar_to_new_file
- backend/tests/test_api_studio.py::test_delete_card_with_stories
- backend/tests/test_api_studio.py::test_test_chat_streams_and_saves_nothing
- backend/tests/test_avatars.py
- backend/tests/test_signature_lines.py
- backend/tests/test_review_fixes.py::test_studio_uses_default_chat_model
- frontend/src/lib/cardForm.test.ts
- frontend/src/lib/signatureLines.test.ts
- frontend/src/pages/studio/editorInstance.test.ts
- frontend/src/lib/leaveGuard.test.ts
- frontend/src/lib/router.test.ts
- frontend/src/lib/advancedTools.test.ts
- bot: sửa và lưu nhân vật ở Studio
- bot: lời nói đặc trưng quá 3 dòng bị chặn
- bot: chat thử có ba chấm rồi trả lời
- bot: tắt công cụ nâng cao thì trình sửa không có Xem trước
- bot: rời trình sửa còn thay đổi chưa lưu thì hỏi lại

## Liên quan

- **Code:** [`frontend/src/pages/studio/CardEditorPage.tsx`](../../frontend/src/pages/studio/CardEditorPage.tsx), [`frontend/src/pages/studio/CardForm.tsx`](../../frontend/src/pages/studio/CardForm.tsx), [`frontend/src/pages/studio/AvatarField.tsx`](../../frontend/src/pages/studio/AvatarField.tsx), [`frontend/src/pages/studio/EmotionSection.tsx`](../../frontend/src/pages/studio/EmotionSection.tsx), [`frontend/src/pages/studio/TestChatPanel.tsx`](../../frontend/src/pages/studio/TestChatPanel.tsx), [`frontend/src/pages/studio/PromptPreviewPanel.tsx`](../../frontend/src/pages/studio/PromptPreviewPanel.tsx), [`frontend/src/lib/cardForm.ts`](../../frontend/src/lib/cardForm.ts), [`frontend/src/lib/signatureLines.ts`](../../frontend/src/lib/signatureLines.ts), [`backend/lyris/api/routes_studio.py`](../../backend/lyris/api/routes_studio.py), [`backend/lyris/studio/preview.py`](../../backend/lyris/studio/preview.py)
- **Tài liệu:** [phase2.md](../../docs/phase2.md), [design-impl.md §6.5, §16](../../docs/design-impl.md)
- **Quyết định:** [card-doi-story-doi-theo](../decisions/card-doi-story-doi-theo.md), [an-chu-ky-thuat](../decisions/an-chu-ky-thuat.md)
