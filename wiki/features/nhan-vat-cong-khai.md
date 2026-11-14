# Nhân vật công khai

- **Trạng thái:** Đã xong · **Phase:** Phase 4b
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

- [x] Studio có công tắc 'Công khai' trong phần Cơ bản; nhân vật mẫu không có công tắc này.
- [x] Bản đã lưu công khai có nút 'Người khác thấy gì'.
- [x] Tài khoản khác thấy nhân vật ở 'Nhân vật được chia sẻ' của Khám phá.
- [x] Người khác bắt đầu story thì được bản sao; chủ sửa, ẩn hay xoá nhân vật cũng không làm hỏng story của họ.
- [x] Hồ sơ công khai không có 'Sửa nhân vật'; 'bởi @handle' là link tới profile.
- [x] `test_public_cards.py` qua.

## Liên quan

- **Code:** [`backend/lyris/api/routes_studio.py`](../../backend/lyris/api/routes_studio.py), [`frontend/src/pages/studio/shareLogic.ts`](../../frontend/src/pages/studio/shareLogic.ts), [`frontend/src/pages/character/PublicPreview.tsx`](../../frontend/src/pages/character/PublicPreview.tsx), [`frontend/src/pages/explore/logic.ts`](../../frontend/src/pages/explore/logic.ts)
- **Tài liệu:** [auth.md §4.3-§4.5](../../docs/auth.md)
- **Quyết định:** [nhan-vat-cong-khai](../decisions/nhan-vat-cong-khai.md), [ban-sao-nhan-vat-cong-khai](../decisions/ban-sao-nhan-vat-cong-khai.md)
