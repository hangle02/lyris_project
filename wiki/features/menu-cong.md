# Menu '+' ở ô nhập

- **Trạng thái:** Đã xong · **Phase:** Phase 3b
- **Màn hình:** [composer-menu](../screens/composer-menu.md)

## Là gì

Nút '+' bên trái ô nhập mở danh sách việc phụ: 'Nhận gợi ý', 'Xem sự kiện', 'Gửi hình ảnh' (nhãn 'Sắp có'). Thêm mục mới chỉ cần thêm dữ liệu vào `composerActions`.

## Hoạt động thế nào

- Nút '+' nằm bên trái ô nhập. Chạm thì mở danh sách việc phụ.
- Hiện có: 'Nhận gợi ý', 'Xem sự kiện', 'Gửi hình ảnh' (chưa dùng được, ghi 'Sắp có').
- Trên máy tính là popover; trên điện thoại là sheet trượt từ dưới lên.

Kỹ thuật:

- Danh sách mục là dữ liệu `composerActions` trong `suggestLogic.ts`; thêm mục mới chỉ cần thêm dữ liệu.
- `ComposerMenu.tsx` lo bàn phím, focus và đóng menu.

## Done when

- [x] Nút '+' 44px, có aria-expanded, xoay 45° khi mở.
- [x] Từ 640px là popover phía trên nút; trên điện thoại là sheet từ dưới có nền mờ.
- [x] Phím mũi tên, Home, End đi qua mọi mục, kể cả mục bị khoá; Esc hay bấm ra ngoài thì đóng và focus về nút '+'.
- [x] Mục 'Gửi hình ảnh' bị khoá, có badge 'Sắp có' và một câu giải thích.

## Liên quan

- **Code:** [`frontend/src/pages/chat/ComposerMenu.tsx`](../../frontend/src/pages/chat/ComposerMenu.tsx), [`frontend/src/pages/chat/suggestLogic.ts`](../../frontend/src/pages/chat/suggestLogic.ts), [`frontend/src/components/Composer.tsx`](../../frontend/src/components/Composer.tsx)
- **Tài liệu:** [phase3.md §10.3](../../docs/phase3.md), [design-impl.md §15](../../docs/design-impl.md)
- **Quyết định:** [menu-cong-o-nhap](../decisions/menu-cong-o-nhap.md), [gui-hinh-anh-chi-la-khung](../decisions/gui-hinh-anh-chi-la-khung.md)
