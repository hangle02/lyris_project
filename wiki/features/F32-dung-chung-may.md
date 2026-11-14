# F32 — Nhiều người dùng chung một máy

- **Trạng thái:** xem `memory/features.json` · **Phase:** Phase 4b
- **Giai đoạn:** Đã có
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

- [ ] Unit: cổng sinh chung cho tối đa 2 lượt cùng lúc; lượt thứ ba chờ rồi chạy theo thứ tự đến; việc nền xen kẽ theo tài khoản.
- [ ] Unit: cùng một tài khoản gửi lượt thứ hai khi lượt đầu chưa xong thì 409.
- [ ] Unit: chờ quá thời hạn (mặc định 120 giây) thì báo bận, tin người chơi vẫn được giữ; huỷ khi đang chờ không để lại dấu vết.
- [ ] Unit: dòng chờ là 'Có người khác đang trò chuyện. {Tên} sẽ trả lời ngay sau.'; câu báo bận không có 'model', 'slot', 'Ollama'.

## Tests

- backend/tests/test_generation_gate.py
- backend/tests/test_api.py::test_concurrent_send_is_busy
- backend/tests/test_phase3b.py::test_friendly_errors_never_mention_ollama_or_model
- frontend/src/pages/chat/chatLogic.test.ts

## Liên quan

- **Code:** [`backend/lyris/chat/gate.py`](../../backend/lyris/chat/gate.py), [`backend/lyris/jobs/queue.py`](../../backend/lyris/jobs/queue.py), [`frontend/src/pages/chat/chatLogic.ts`](../../frontend/src/pages/chat/chatLogic.ts)
- **Tài liệu:** [auth.md §5](../../docs/auth.md)
- **Quyết định:** [cong-sinh-chung](../decisions/cong-sinh-chung.md)
