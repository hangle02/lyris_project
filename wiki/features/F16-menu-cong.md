# F16 — Menu '+' ở ô nhập

- **Trạng thái:** xem `memory/features.json` · **Phase:** Phase 3b
- **Giai đoạn:** Đã có
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

- [ ] Unit: danh sách mục của menu '+' lấy từ dữ liệu; 'Gửi hình ảnh' là mục bị khoá có badge 'Sắp có'; mở menu thì focus vào mục đầu tiên chạy được.
- [ ] Bot: nút aria-label 'Thêm' rộng và cao ≥ 44px, có `aria-expanded` đổi từ false sang true khi bấm; ở 390px menu là sheet từ dưới có nền mờ, ở 1280px là popover phía trên nút.
- [ ] Bot: ArrowDown, ArrowUp, Home, End di chuyển focus qua mọi mục, kể cả mục bị khoá; Esc đóng menu và focus về nút 'Thêm'.
- [ ] Bot: mục 'Gửi hình ảnh' bị khoá (disabled hoặc aria-disabled), có badge 'Sắp có' và một câu giải thích.

## Tests

- frontend/src/pages/chat/suggestLogic.test.ts
- frontend/src/components/ui/logic.test.ts
- bot: nút Thêm 44px, sheet ở điện thoại, popover ở máy tính
- bot: menu cộng đi bằng phím, Esc trả focus
- bot: Gửi hình ảnh bị khoá, Sắp có

## Liên quan

- **Code:** [`frontend/src/pages/chat/ComposerMenu.tsx`](../../frontend/src/pages/chat/ComposerMenu.tsx), [`frontend/src/pages/chat/suggestLogic.ts`](../../frontend/src/pages/chat/suggestLogic.ts), [`frontend/src/components/Composer.tsx`](../../frontend/src/components/Composer.tsx)
- **Tài liệu:** [phase3.md §10.3](../../docs/phase3.md), [design-impl.md §15](../../docs/design-impl.md)
- **Quyết định:** [menu-cong-o-nhap](../decisions/menu-cong-o-nhap.md), [gui-hinh-anh-chi-la-khung](../decisions/gui-hinh-anh-chi-la-khung.md)
