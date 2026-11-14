# F06 — Tạo lại, phiên bản, sửa, xoá, thích/chê

- **Trạng thái:** xem `memory/features.json` · **Phase:** Phase 1
- **Giai đoạn:** Đã có
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

- [ ] Unit: 'Tạo lại câu trả lời' sinh variant mới ở cùng `turn_index`; chọn variant nào thì variant đó active; tạo lại sai chỗ bị từ chối.
- [ ] Unit: lật variant, sửa hay xoá lượt thì ký ức và chỉ số cảm xúc tính lại theo variant đang chọn (rollback qua `state_events`).
- [ ] Unit: 'Sửa' lưu nguyên văn và xoá gợi ý của lượt đó.
- [ ] Unit: 'Xoá từ đây' xoá lượt đó và mọi lượt sau, kể cả lượt mode kia nằm sau.
- [ ] Unit: thích/chê lưu vào bảng feedback qua `PUT /messages/{id}/feedback`.
- [ ] Unit: thao tác bị khoá thì có lý do (`actionLockReason`, `messageLockReason`): nhân vật đang trả lời (đợi xong hoặc bấm 'Dừng'), đang nghĩ gợi ý, đang lưu, lượt chưa lưu xong; nút 'Sửa' và 'Xoá từ đây' đặt lý do đó vào `title`.
- [ ] Bot: bấm 'Tạo lại câu trả lời' trên lượt nhân vật cuối thì có câu trả lời mới và bộ đếm '2/2' trong nhóm 'Các phiên bản trả lời'.
- [ ] Bot: dưới lượt nhân vật có 'Thích', 'Chê', 'Sửa', 'Xoá từ đây'; bấm 'Xoá từ đây' thì hiện hộp 'Xác nhận xoá' có câu 'Xoá lượt này và mọi lượt sau?' và nút 'Xoá'.
- [ ] Bot: trong lúc nhân vật đang trả lời (nút 'Dừng' đang hiện), mọi nút 'Sửa' và 'Xoá từ đây' đều bị khoá (disabled) và có lý do (`title` là một câu lý do, không chỉ lặp tên nút).

## Tests

- backend/tests/test_api.py::test_regenerate_and_switch_variants
- backend/tests/test_api.py::test_regenerate_invalid_targets
- backend/tests/test_api.py::test_edit_assistant_and_user
- backend/tests/test_api.py::test_delete_from_here
- backend/tests/test_api.py::test_feedback
- backend/tests/test_jobs.py::test_regenerate_and_select_variant_roll_state_back
- backend/tests/test_phase3_e2e.py::test_variants_edit_and_delete_roll_state
- backend/tests/test_api_state.py::test_regenerate_and_delete_through_api_roll_back
- backend/tests/test_phase3b.py::test_edit_clears_suggestions
- backend/tests/test_repo.py::test_add_variant_and_select_variant
- backend/tests/test_repo.py::test_truncate_from
- frontend/src/lib/threadRows.test.ts
- frontend/src/lib/actionLock.test.ts
- bot: tạo lại ra phiên bản mới
- bot: hàng thao tác có Thích, Chê, Sửa, Xoá từ đây hỏi lại
- bot: đang trả lời thì Sửa và Xoá từ đây bị khoá, có lý do (title)

## Liên quan

- **Code:** [`frontend/src/components/MessageItem.tsx`](../../frontend/src/components/MessageItem.tsx), [`backend/lyris/api/routes.py`](../../backend/lyris/api/routes.py), [`backend/lyris/state/fold.py`](../../backend/lyris/state/fold.py), [`backend/lyris/db/repo.py`](../../backend/lyris/db/repo.py)
- **Tài liệu:** [phase1.md](../../docs/phase1.md), [phase3.md §2](../../docs/phase3.md)
