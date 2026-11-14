# Gửi hình ảnh trong chat

- **Trạng thái:** Chưa làm · **Phase:** Chưa xếp phase
- **Màn hình:** [composer-menu](../screens/composer-menu.md)

## Là gì

Người dùng muốn gửi ảnh từ menu '+'. Hiện mục này chỉ là vỏ, bị khoá với nhãn 'Sắp có'. Chưa có thiết kế backend.

## Hoạt động thế nào

- Mong muốn: người chơi chọn ảnh từ menu '+' và gửi vào chat.
- Hiện tại mục 'Gửi hình ảnh' bị khoá, có badge 'Sắp có' và một câu giải thích.

Kỹ thuật:

- Chỉ có mục khoá trong `composerActions` (`suggestLogic.ts`).
- Chưa có API, chưa có chỗ lưu ảnh, chưa chọn model đọc ảnh.

## Done when

- [ ] Có trang thiết kế (ảnh lưu ở đâu, model đọc ảnh thế nào, giới hạn dung lượng) trước khi code.
- [ ] Chọn 'Gửi hình ảnh' mở được trình chọn ảnh trên Mac và iPhone.
- [ ] Ảnh gửi đi hiện trong lượt của người chơi ở cả Story và DM.
- [ ] Nhân vật phản ứng với nội dung ảnh, hoặc giao diện nói rõ nhân vật không xem được ảnh.

## Liên quan

- **Code:** [`frontend/src/pages/chat/suggestLogic.ts`](../../frontend/src/pages/chat/suggestLogic.ts)
- **Tài liệu:** [phase3.md §10.3](../../docs/phase3.md)
- **Quyết định:** [gui-hinh-anh-chi-la-khung](../decisions/gui-hinh-anh-chi-la-khung.md), [menu-cong-o-nhap](../decisions/menu-cong-o-nhap.md)
