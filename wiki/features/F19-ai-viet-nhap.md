# F19 — AI viết nháp nhân vật

- **Trạng thái:** xem `memory/features.json` · **Phase:** Phase 2
- **Giai đoạn:** Đã có
- **Màn hình:** [studio-list](../screens/studio-list.md), [card-editor](../screens/card-editor.md)

## Là gì

Gõ một dòng ý tưởng, AI viết ra một card đầy đủ (chưa lưu) để người dùng sửa rồi lưu. AI đề xuất style profile nhưng người dùng xác nhận.

## Hoạt động thế nào

- Ở Studio, bấm 'AI viết nháp' và gõ một dòng ý tưởng.
- AI viết ra một nhân vật đầy đủ và mở trình sửa. Nhân vật chưa được lưu.
- Người dùng đọc, sửa, chọn lại văn phong nếu cần, rồi mới lưu.

Kỹ thuật:

- `studio/draft.py` gọi model chat và đọc kết quả thành card.
- API ở `api/routes_studio.py`; hộp nhập ở `DraftDialog.tsx`.

## Done when

- [ ] Unit: viết nháp gọi model với schema JSON; kết quả được hậu xử lý (tên, vai trò, tính cách, lời mở đầu, Thought…) kèm cảnh báo khi thiếu; không lưu card.
- [ ] Unit: ý tưởng tối đa 2000 ký tự; hai yêu cầu cùng lúc thì một cái báo bận; người dùng ngắt kết nối thì huỷ và nhả khoá.
- [ ] Unit: câu lỗi không nhắc 'model' hay 'Ollama'; chữ gốc nằm dưới 'Chi tiết' (`friendlyError`).
- [ ] Unit: prompt viết nháp có luật an toàn.
- [ ] Bot: ở `#/studio`, bấm 'AI viết nháp' mở hộp thoại có một ô nhập ý tưởng; gửi ý tưởng khi LLM giả báo lỗi thì hộp hiện câu lỗi kèm 'Chi tiết', không có chữ 'model' hay 'Ollama'.
- [ ] Bot: ở `#/studio`, bấm 'AI viết nháp', gửi một ý tưởng mà LLM giả viết được card thì app mở `#/studio/new` với ô 'Tên nhân vật' là tên card nháp, header có 'chưa lưu', và `/api/cards` chưa có card đó (rời trang không lưu thì vẫn chưa có).
- [ ] Model thật: một dòng ý tưởng cho card đủ tên, vai trò, tính cách, lời mở đầu; trình sửa mở với card đó, chưa lưu (kịch bản `f19-viet-nhap` cho card trên model thật; phần trình sửa: dòng Bot ở trên và `test_integration_phase2.py::test_draft_save_and_open_story`).
- [ ] Model thật: trên gemma4:12b, một dòng ý tưởng cho card nháp chưa lưu, đủ tên, vai trò, tính cách, lời mở đầu; tính cách và lời mở đầu bằng tiếng Việt; không có cảnh báo thiếu tên, thiếu lời mở đầu hay thiếu xưng hô (kịch bản `f19-viet-nhap`).

## Tests

- backend/tests/test_draft.py
- backend/tests/test_api_studio.py::test_draft_card
- backend/tests/test_api_studio.py::test_draft_errors
- backend/tests/test_api_studio.py::test_draft_concurrent_requests_one_is_busy
- backend/tests/test_api_studio.py::test_draft_client_disconnect_cancels_and_frees_lock
- backend/tests/test_integration_phase2.py::test_draft_save_and_open_story
- backend/tests/test_compliance.py::test_safety_rule_in_draft_prompt
- frontend/src/lib/friendlyError.test.ts
- bot: AI viết nháp mở hộp ý tưởng, lỗi không có chữ kỹ thuật
- bot: AI viết nháp xong thì mở trình sửa với card nháp, chưa lưu
- model: f19-viet-nhap

## Liên quan

- **Code:** [`backend/lyris/studio/draft.py`](../../backend/lyris/studio/draft.py), [`frontend/src/pages/studio/DraftDialog.tsx`](../../frontend/src/pages/studio/DraftDialog.tsx), [`backend/lyris/api/routes_studio.py`](../../backend/lyris/api/routes_studio.py)
- **Tài liệu:** [phase2.md](../../docs/phase2.md)
- **Quyết định:** [van-phong-theo-boi-canh](../decisions/van-phong-theo-boi-canh.md)
