# Nhiều người dùng chung một máy

- **Trạng thái:** Đã xong · **Phase:** Phase 4b
- **Màn hình:** [chat-story](../screens/chat-story.md), [chat-dm](../screens/chat-dm.md)

## Là gì

Một Ollama phục vụ nhiều tài khoản: tối đa 2 lượt sinh cùng lúc trên cả máy, mỗi tài khoản 1, xếp hàng vào trước ra trước. Việc nền xen kẽ theo tài khoản. Khi phải chờ, giao diện nói bằng lời thường.

## Hoạt động thế nào

- Nhiều người dùng chung một máy Mac, một model.
- Khi người khác đang trò chuyện, lượt của mình phải chờ một chút. Giao diện nói rõ bằng lời thường.
- Mỗi người chỉ sinh một lượt một lúc.

Kỹ thuật:

- `chat/gate.py`: tối đa 2 lượt sinh cùng lúc trên cả máy, mỗi tài khoản 1, vào trước ra trước.
- Chờ quá 120 giây thì báo bận; lượt thứ hai của cùng tài khoản bị từ chối (409).
- Việc nền trong `jobs/queue.py` xen kẽ theo tài khoản.

## Done when

- [x] Hai lượt cùng một tài khoản cùng lúc thì lượt thứ hai bị từ chối (409).
- [x] Hết chỗ thì lượt mới chờ; chờ quá 120 giây thì báo bận.
- [x] Khi chờ, dưới ba chấm có dòng 'Có người khác đang trò chuyện. {Tên} sẽ trả lời ngay sau.'
- [x] Không có chữ 'model', 'slot', 'Ollama' trong câu báo bận.
- [x] `test_generation_gate.py` qua.

## Liên quan

- **Code:** [`backend/lyris/chat/gate.py`](../../backend/lyris/chat/gate.py), [`backend/lyris/jobs/queue.py`](../../backend/lyris/jobs/queue.py), [`frontend/src/pages/chat/chatLogic.ts`](../../frontend/src/pages/chat/chatLogic.ts)
- **Tài liệu:** [auth.md §5](../../docs/auth.md)
- **Quyết định:** [cong-sinh-chung](../decisions/cong-sinh-chung.md)
