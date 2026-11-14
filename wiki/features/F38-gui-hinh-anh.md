# F38 — Gửi hình ảnh trong chat

- **Trạng thái:** xem `memory/features.json` · **Phase:** Chưa xếp phase
- **Giai đoạn:** Kế hoạch
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

- [ ] Unit: ảnh gửi đi được lưu theo trang thiết kế; ảnh quá giới hạn dung lượng hoặc không phải ảnh bị từ chối.
- [ ] Bot: chọn 'Gửi hình ảnh' trong menu 'Thêm' mở trình chọn ảnh (`input[type=file]` nhận ảnh).
- [ ] Bot: ảnh gửi đi hiện trong lượt của người chơi ở cả Story và DM.
- [ ] Model thật: nhân vật phản ứng với nội dung ảnh, hoặc giao diện nói rõ nhân vật không xem được ảnh.

## Tests

Chưa có test: tính năng còn là kế hoạch. Viết test cùng lúc với code.

Tên check bot dự kiến (chưa có trong `environment/e2e.mjs`, thêm khi làm): `bot: Gửi hình ảnh mở trình chọn ảnh`; `bot: ảnh hiện trong lượt người chơi`.

## Ngoài Done when

Không chặn ✅ (cần thử tay, dịch vụ thật, hoặc còn là kế hoạch).

- Trước khi code: có trang thiết kế (ảnh lưu ở đâu, model đọc ảnh thế nào, giới hạn dung lượng).
- Thử tay trên Mac và iPhone.

## Liên quan

- **Code:** [`frontend/src/pages/chat/suggestLogic.ts`](../../frontend/src/pages/chat/suggestLogic.ts)
- **Tài liệu:** [phase3.md §10.3](../../docs/phase3.md)
- **Quyết định:** [gui-hinh-anh-chi-la-khung](../decisions/gui-hinh-anh-chi-la-khung.md), [menu-cong-o-nhap](../decisions/menu-cong-o-nhap.md)
