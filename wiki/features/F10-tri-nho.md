# F10 — Trí nhớ: ký ức, điều đã biết, tóm tắt, cảnh

- **Trạng thái:** xem `memory/features.json` · **Phase:** Phase 3
- **Giai đoạn:** Đã có
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

- [ ] Unit: sau mỗi lượt, việc nền trích ký ức, điều đã biết và cảnh rồi ghi vào state; lượt bị huỷ giữa chừng không được trích.
- [ ] Unit: tìm ký ức lai: từ khoá (FTS giữ dấu tiếng Việt) cộng tìm theo nghĩa khi có model embedding; embedding lỗi thì quay về từ khoá.
- [ ] Unit: ký ức nằm ngoài cửa sổ lịch sử được đưa lại vào prompt (tối đa 3); ký ức còn trong cửa sổ thì bỏ qua.
- [ ] Unit: tóm tắt theo khúc luôn sẵn khi cửa sổ lịch sử dịch; đổi mode vẫn dùng tóm tắt ngay trước cửa sổ.
- [ ] Unit: 'Quên' xoá một ký ức và ngăn cảm xúc bỏ đúng dòng đó; 'Đọc lại story' xếp việc trích các lượt chưa đọc.
- [ ] Unit: header chat hiện 'nơi chốn · thời gian' khi có (`headerSubtitle`, `sceneLine`).
- [ ] Bot: sau một lượt (LLM giả trả ký ức và cảnh), ngăn 'Cảm xúc & ký ức' liệt kê ký ức có nhãn 'Sự kiện' hoặc 'Điều đã biết', mỗi ký ức có nút 'Quên: …'; header chat hiện 'nơi chốn · thời gian'.
- [ ] Bot: story dài có `<details>` 'Tóm tắt những lượt cũ': story dựng qua HTTP API của app trên LLM giả (6 lượt người chơi dài, lịch sử dài hơn cả `num_ctx` 8192 nên cửa sổ lịch sử chắc chắn đã dịch); việc nền viết tóm tắt; mở `#/chat/<id>`, ngăn 'Cảm xúc & ký ức' có `<details>` 'Tóm tắt những lượt cũ' gập sẵn, mở ra thì hiện đúng tóm tắt server đã lưu.
- [ ] Model thật: sau vài lượt trên gemma4:12b, ký ức và điều đã biết được trích đúng ý lượt chơi (kịch bản `f10-ky-uc`); tóm tắt những lượt cũ của story dài đúng nội dung (kịch bản `f10-tom-tat`).
- [ ] Model thật: trên gemma4:12b, việc trích xuất thật ghi ký ức và điều đã biết có đúng chi tiết người chơi hoặc nhân vật vừa kể, điều đã biết nói về đúng người (kịch bản `f10-ky-uc`); tóm tắt thật của một đoạn story dài giữ đủ lời hứa, nơi chốn, tên người và bí mật đã có (kịch bản `f10-tom-tat`).

## Tests

- backend/tests/test_jobs.py::test_turn_enqueues_extract_and_worker_writes_state
- backend/tests/test_jobs.py::test_aborted_turn_is_not_extracted
- backend/tests/test_retrieval.py
- backend/tests/test_prompt_state.py::test_memories_before_window_after_truncation
- backend/tests/test_prompt_state.py::test_memories_inside_window_are_skipped_facts_kept
- backend/tests/test_phase3b_e2e.py::test_mode_switch_keeps_summary_right_before_window
- backend/tests/test_window_hysteresis.py
- backend/tests/test_summarize.py
- backend/tests/test_api_state.py::test_forget_memory
- backend/tests/test_api_state.py::test_rebuild_route
- backend/tests/test_phase3_e2e.py::test_turn_flows_into_extras_and_next_prompt
- frontend/src/pages/chat/memoryLogic.test.ts
- frontend/src/pages/chat/chatLogic.test.ts
- frontend/src/pages/chat/extrasPoller.test.ts
- bot: ngăn trái tim có ký ức và nút Quên, header có cảnh
- bot: story dài (cửa sổ đã dịch) có Tóm tắt những lượt cũ trong ngăn trái tim
- model: f10-ky-uc
- model: f10-tom-tat

## Ghi chú

- Dòng gốc "story dài có '<details> Tóm tắt những lượt cũ' với tóm tắt đúng nội dung" được chứng minh bằng hai dòng (PO đồng ý 2026-11-14, [raw](../raw/2026-11-14-po-quyet-harness.md)): phần giao diện (story đủ dài để cửa sổ dịch thì hiện `<details>` với đúng tóm tắt đã lưu) là dòng Bot; phần nội dung (tóm tắt đúng ý) là dòng Model thật với kịch bản `f10-tom-tat`. Bot không cần sửa `environment/fake-server.py`: LLM giả đã trả tóm tắt cho lời gọi tóm tắt. Xem [kich-ban-model-that](../decisions/kich-ban-model-that.md).

## Liên quan

- **Code:** [`backend/lyris/state/extract.py`](../../backend/lyris/state/extract.py), [`backend/lyris/state/service.py`](../../backend/lyris/state/service.py), [`backend/lyris/memory/retrieval.py`](../../backend/lyris/memory/retrieval.py), [`backend/lyris/memory/summarize.py`](../../backend/lyris/memory/summarize.py), [`backend/lyris/jobs/queue.py`](../../backend/lyris/jobs/queue.py), [`backend/lyris/jobs/worker.py`](../../backend/lyris/jobs/worker.py), [`frontend/src/pages/chat/useStoryExtras.ts`](../../frontend/src/pages/chat/useStoryExtras.ts), [`frontend/src/pages/chat/memoryLogic.ts`](../../frontend/src/pages/chat/memoryLogic.ts)
- **Tài liệu:** [phase3.md](../../docs/phase3.md)
- **Quyết định:** [viec-nen-dung-model-chat](../decisions/viec-nen-dung-model-chat.md), [khong-sqlite-vec](../decisions/khong-sqlite-vec.md), [cua-so-lich-su-theo-khuc](../decisions/cua-so-lich-su-theo-khuc.md)
