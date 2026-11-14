# Hồ sơ nhân vật (chỉ xem)

- **Trạng thái:** Đã xong · **Phase:** Phase 2b (§16)
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

- [x] Từ Khám phá, chạm thẻ nhân vật mở `#/character/<id>` hoặc `#/character/template/<slug>`, không mở story.
- [x] Không có ô nhập hay khung trông như sửa được; 'Sửa nhân vật' chỉ có với card của mình.
- [x] Tab 'Giới thiệu' hiện Đôi nét, Tính cách, Ngoại hình...; `{{user}}` thành 'bạn'; không có trường bí mật.
- [x] Tab 'Thiết lập' hiện xưng hô, giọng kể, 6 thanh cảm xúc ban đầu.
- [x] Có 2-3 thẻ 'Lời nói đặc trưng' (tự chọn từ ví dụ thoại khi card không có).
- [x] Điện thoại có thanh dính đáy với 'Bước vào câu chuyện' và 'Tiếp tục story'.
- [x] `#/character/999` hiện 'Không tìm thấy nhân vật này…' + 'Về Khám phá'.

## Liên quan

- **Code:** [`frontend/src/pages/character/CharacterPage.tsx`](../../frontend/src/pages/character/CharacterPage.tsx), [`frontend/src/pages/character/logic.ts`](../../frontend/src/pages/character/logic.ts), [`frontend/src/components/CharacterPicture.tsx`](../../frontend/src/components/CharacterPicture.tsx), [`frontend/src/lib/signatureLines.ts`](../../frontend/src/lib/signatureLines.ts)
- **Tài liệu:** [design-impl.md §16](../../docs/design-impl.md)
- **Quyết định:** [ho-so-nhan-vat-chi-doc](../decisions/ho-so-nhan-vat-chi-doc.md)
