# Tạo lại, phiên bản, sửa, xoá, thích/chê

- **Trạng thái:** Đã xong · **Phase:** Phase 1
- **Màn hình:** [chat-story](../screens/chat-story.md), [chat-dm](../screens/chat-dm.md)

## Là gì

Mỗi lượt có hàng thao tác: lật phiên bản, tạo lại câu trả lời, thích/chê, sửa, 'Xoá từ đây'. Tạo lại sinh một variant mới ở cùng lượt; state của variant cũ được rollback.

## Hoạt động thế nào

- Dưới mỗi lượt có hàng thao tác: phiên bản trước/sau, tạo lại, thích/chê, sửa, xoá từ đây.
- Không ưng câu trả lời thì bấm 'Tạo lại câu trả lời'. Bản cũ vẫn còn, lật lại được.
- Lật sang bản nào thì cảm xúc và ký ức của nhân vật đi theo bản đó.

Kỹ thuật:

- Variant lưu cùng `turn_index`; mỗi thay đổi state ghi vào `state_events` gắn với message.
- `state/fold.py` tính lại state từ các event của variant đang chọn.
- Thích/chê lưu ở bảng feedback qua `PUT /messages/{id}/feedback`.

## Done when

- [x] 'Tạo lại câu trả lời' sinh variant mới; nút 'Phiên bản trước/sau' lật qua lại.
- [x] Lật variant thì ký ức và chỉ số cảm xúc đổi theo variant đang chọn (rollback qua state_events).
- [x] 'Sửa' mở ô sửa nguyên văn; lưu xong thì gợi ý của lượt đó bị xoá.
- [x] 'Xoá từ đây' hỏi lại 'Xoá lượt này và mọi lượt sau?' và xoá cả lượt mode kia nằm sau.
- [x] Thích/Chê được lưu vào bảng feedback (PUT /messages/{id}/feedback).
- [x] Trong lúc nhân vật đang trả lời, sửa và xoá bị khoá kèm lý do.

## Liên quan

- **Code:** [`frontend/src/components/MessageItem.tsx`](../../frontend/src/components/MessageItem.tsx), [`backend/lyris/api/routes.py`](../../backend/lyris/api/routes.py), [`backend/lyris/state/fold.py`](../../backend/lyris/state/fold.py), [`backend/lyris/db/repo.py`](../../backend/lyris/db/repo.py)
- **Tài liệu:** [phase1.md](../../docs/phase1.md), [phase3.md §2](../../docs/phase3.md)
