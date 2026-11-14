# F31 — Nhân vật công khai

- **Trạng thái:** xem `memory/features.json` · **Phase:** Phase 4b
- **Giai đoạn:** Đã có
- **Màn hình:** [card-editor](../screens/card-editor.md), [public-preview](../screens/public-preview.md), [explore](../screens/explore.md), [character-profile](../screens/character-profile.md)

## Là gì

Nhân vật mặc định riêng tư. Chủ nhân vật bật 'Công khai' để tài khoản khác trên cùng máy thấy ở Khám phá và bắt đầu story riêng. Người khác nhận một bản sao chụp lúc bắt đầu, không sửa được và không thấy bí mật hay sổ thế giới.

## Hoạt động thế nào

- Nhân vật mặc định là riêng tư.
- Bật 'Công khai' ở Studio thì tài khoản khác trên cùng máy thấy nhân vật ở Khám phá.
- Người khác bắt đầu story với một bản sao. Họ không sửa được, không thấy bí mật hay sổ thế giới.
- Nút 'Người khác thấy gì' cho chủ nhân vật xem trước.

Kỹ thuật:

- API ở `api/routes_studio.py`; bản sao chụp lúc bắt đầu story.
- `PublicPreview.tsx` dựng trang 'Người khác thấy gì'.

## Done when

- [ ] Unit: luật bật/tắt 'Công khai' (nhân vật mẫu không có công tắc); Khám phá của tài khoản khác liệt kê nhân vật công khai; người tạo bị khoá thì nhân vật ẩn.
- [ ] Unit: bắt đầu story với nhân vật công khai chụp một bản sao đầy đủ; chủ sửa, ẩn hay xoá nhân vật thì story của người chơi vẫn chạy; sổ thế giới của bản sao không lọt vào xem trước hay chat thử.
- [ ] Unit: hồ sơ công khai chỉ có trường whitelist; mô tả công tắc không hứa giữ bí mật; danh sách Studio ghi 'Công khai' thay 'Riêng tư'.
- [ ] Bot: trình sửa nhân vật của mình (bot nhập từ card .json rồi lưu) có công tắc 'Công khai' trong phần 'Cơ bản', trình sửa nhân vật cài từ mẫu không có; bật 'Công khai' và lưu thì có nút 'Người khác thấy gì'.
- [ ] Bot: tài khoản thứ hai mở `#/explore` thấy nhân vật đó trong 'Nhân vật được chia sẻ'; hồ sơ của nó không có 'Sửa nhân vật' và 'bởi @handle' là link tới `#/u/<handle>`.

## Tests

- backend/tests/test_public_cards.py
- frontend/src/pages/studio/shareLogic.test.ts
- frontend/src/pages/explore/logic.test.ts
- frontend/src/pages/character/logic.test.ts
- bot: công tắc Công khai trong phần Cơ bản, mẫu không có, lưu thì có Người khác thấy gì
- bot: tài khoản khác thấy nhân vật được chia sẻ

## Liên quan

- **Code:** [`backend/lyris/api/routes_studio.py`](../../backend/lyris/api/routes_studio.py), [`frontend/src/pages/studio/shareLogic.ts`](../../frontend/src/pages/studio/shareLogic.ts), [`frontend/src/pages/character/PublicPreview.tsx`](../../frontend/src/pages/character/PublicPreview.tsx), [`frontend/src/pages/explore/logic.ts`](../../frontend/src/pages/explore/logic.ts)
- **Tài liệu:** [auth.md §4.3-§4.5](../../docs/auth.md)
- **Quyết định:** [nhan-vat-cong-khai](../decisions/nhan-vat-cong-khai.md), [ban-sao-nhan-vat-cong-khai](../decisions/ban-sao-nhan-vat-cong-khai.md)
