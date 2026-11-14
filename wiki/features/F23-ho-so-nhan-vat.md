# F23 — Hồ sơ nhân vật (chỉ xem)

- **Trạng thái:** xem `memory/features.json` · **Phase:** Phase 2b (§16)
- **Giai đoạn:** Đã có
- **Màn hình:** [character-profile](../screens/character-profile.md)

## Là gì

Bấm vào nhân vật thì mở hồ sơ chỉ xem, không phải form sửa: ảnh lớn, tên, vai trò, tác giả, tag, 'Lời nói đặc trưng', tab 'Giới thiệu' và tab 'Thiết lập'. Không bao giờ hiện bí mật.

## Hoạt động thế nào

- Chạm một nhân vật ở Khám phá thì mở hồ sơ, không vào thẳng story.
- Hồ sơ chỉ để xem: ảnh lớn, tên, vai trò, tác giả, tag, 'Lời nói đặc trưng'.
- Tab 'Giới thiệu' kể về nhân vật; tab 'Thiết lập' cho xem xưng hô, giọng kể và cảm xúc ban đầu.
- Từ đây bấm 'Bước vào câu chuyện' hoặc 'Tiếp tục story'.

Kỹ thuật:

- Route `#/character/<id>` và `#/character/template/<slug>` (`lib/router.ts`).
- `pages/character/logic.ts` chọn trường được hiện và bỏ mọi trường bí mật.
- Thiếu 'Lời nói đặc trưng' thì `lib/signatureLines.ts` chọn từ ví dụ thoại.

## Done when

- [ ] Unit: route `#/character/<id>` và `#/character/template/<slug>` đọc và dựng lại đúng; link hỏng về hub.
- [ ] Unit: tab 'Giới thiệu' chỉ có trường cho người đọc, `{{user}}` thành 'bạn', không bao giờ có trường bí mật; tab 'Thiết lập' có xưng hô, giọng kể, cảm xúc ban đầu.
- [ ] Unit: 'Lời nói đặc trưng' có 2-3 câu, tự chọn từ ví dụ thoại khi card không có.
- [ ] Unit: hồ sơ nhân vật công khai chỉ trả các trường trong whitelist.
- [ ] Bot: bấm thẻ 'Hạ Vy' trong lưới 'Nhân vật' ở `#/explore` (khung nổi bật đã bỏ, [F46](F46-bang-xep-hang-nhan-vat-hot.md)) thì URL thành `#/character/...` (không mở story); hồ sơ có nút 'Bước vào câu chuyện', nhóm tab 'Thông tin nhân vật', và không có ô nhập nào.
- [ ] Bot: hồ sơ nhân vật mẫu không có nút 'Sửa nhân vật'; ở 390px có thanh dính sát đáy màn hình chứa nút 'Bước vào câu chuyện', và khi đã có story với nhân vật đó thì thanh có thêm 'Tiếp tục story' (bấm thì mở lại story `#/chat/<id>`).
- [ ] Bot: `#/character/999999` hiện 'Không tìm thấy nhân vật này' và nút 'Về Khám phá'.

## Tests

- frontend/src/pages/character/logic.test.ts
- frontend/src/lib/router.test.ts
- frontend/src/lib/signatureLines.test.ts
- backend/tests/test_public_cards.py::test_public_card_view_whitelist
- backend/tests/test_public_cards.py::test_story_detail_of_copy_is_public_view
- bot: hồ sơ nhân vật chỉ đọc, có nút Bước vào câu chuyện
- bot: hồ sơ mẫu không có Sửa nhân vật, có thanh dính đáy
- bot: đã có story thì thanh dính đáy của hồ sơ có Tiếp tục story
- bot: nhân vật không có thì báo không tìm thấy

## Liên quan

- **Code:** [`frontend/src/pages/character/CharacterPage.tsx`](../../frontend/src/pages/character/CharacterPage.tsx), [`frontend/src/pages/character/logic.ts`](../../frontend/src/pages/character/logic.ts), [`frontend/src/components/CharacterPicture.tsx`](../../frontend/src/components/CharacterPicture.tsx), [`frontend/src/lib/signatureLines.ts`](../../frontend/src/lib/signatureLines.ts)
- **Tài liệu:** [design-impl.md §16](../../docs/design-impl.md)
- **Quyết định:** [ho-so-nhan-vat-chi-doc](../decisions/ho-so-nhan-vat-chi-doc.md)
