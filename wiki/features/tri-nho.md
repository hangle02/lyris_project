# Trí nhớ: ký ức, điều đã biết, tóm tắt, cảnh

- **Trạng thái:** Đã xong · **Phase:** Phase 3
- **Màn hình:** [heart-drawer](../screens/heart-drawer.md), [chat-story](../screens/chat-story.md), [chat-dm](../screens/chat-dm.md)

## Là gì

Việc nền ghi ký ức, fact và cảnh (nơi chốn, thời gian) sau mỗi lượt. Lượt cũ rơi khỏi cửa sổ được tóm tắt theo khúc. Mỗi lượt mới tìm lại ký ức liên quan bằng từ khoá (FTS) và theo nghĩa (bge-m3) nếu có.

## Hoạt động thế nào

- Sau mỗi lượt, Lyris ghi lại điều đáng nhớ: sự kiện, điều đã biết về người chơi, nơi chốn và thời gian.
- Người chơi xem và xoá ký ức trong ngăn cảm xúc ('Quên').
- Story dài thì lượt cũ được tóm tắt; nhân vật vẫn nhớ chuyện cũ khi nó được nhắc lại.
- Story cũ chưa được đọc hết thì có nút 'Đọc lại story'.

Kỹ thuật:

- Việc nền (`jobs/queue.py`, `jobs/worker.py`) chạy trích xuất và tóm tắt bằng chính model chat.
- `memory/retrieval.py` tìm ký ức bằng FTS, cộng thêm tìm theo nghĩa (bge-m3) nếu có.
- `memory/summarize.py` tóm tắt theo khúc, khớp với cửa sổ lịch sử.

## Done when

- [x] Ngăn cảm xúc liệt kê ký ức với nhãn 'Sự kiện' / 'Điều đã biết'; nút 'Quên' hỏi lại rồi xoá.
- [x] Còn lượt chưa ghi nhớ thì có 'Lyris chưa đọc hết story này.' + nút 'Đọc lại story'.
- [x] Header chat hiện 'nơi chốn · thời gian' khi có.
- [x] Ký ức cũ nằm ngoài cửa sổ lịch sử được đưa lại vào prompt ('Chuyện cũ {tên} còn nhớ', tối đa 3 ký ức).
- [x] Tóm tắt luôn sẵn khi cửa sổ lịch sử dịch (`test_phase3b_e2e.py`).
- [x] Tóm tắt tự động xem được trong '<details> Tóm tắt những lượt cũ'.

## Liên quan

- **Code:** [`backend/lyris/state/extract.py`](../../backend/lyris/state/extract.py), [`backend/lyris/state/service.py`](../../backend/lyris/state/service.py), [`backend/lyris/memory/retrieval.py`](../../backend/lyris/memory/retrieval.py), [`backend/lyris/memory/summarize.py`](../../backend/lyris/memory/summarize.py), [`backend/lyris/jobs/queue.py`](../../backend/lyris/jobs/queue.py), [`backend/lyris/jobs/worker.py`](../../backend/lyris/jobs/worker.py), [`frontend/src/pages/chat/useStoryExtras.ts`](../../frontend/src/pages/chat/useStoryExtras.ts), [`frontend/src/pages/chat/memoryLogic.ts`](../../frontend/src/pages/chat/memoryLogic.ts)
- **Tài liệu:** [phase3.md](../../docs/phase3.md)
- **Quyết định:** [viec-nen-dung-model-chat](../decisions/viec-nen-dung-model-chat.md), [khong-sqlite-vec](../decisions/khong-sqlite-vec.md), [cua-so-lich-su-theo-khuc](../decisions/cua-so-lich-su-theo-khuc.md)
