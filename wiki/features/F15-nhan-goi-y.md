# F15 — Nhận gợi ý (chỉ khi bấm)

- **Trạng thái:** xem `memory/features.json` · **Phase:** Phase 3b
- **Giai đoạn:** Đã có
- **Màn hình:** [composer-menu](../screens/composer-menu.md), [chat-story](../screens/chat-story.md), [chat-dm](../screens/chat-dm.md)

## Là gì

Gợi ý trả lời chỉ được sinh khi người chơi chọn 'Nhận gợi ý' trong menu '+', không tự chạy sau mỗi lượt. Ra 3 thẻ; chạm là gửi ngay. Có 'Gợi ý khác', 'Huỷ gợi ý' và nút đóng.

## Hoạt động thế nào

- Bí ý thì mở menu '+' và chọn 'Nhận gợi ý'.
- Trong lúc chờ có ba chấm và nút 'Huỷ gợi ý'. Xong thì ra tối đa 3 thẻ.
- Chạm một thẻ là gửi luôn câu đó. Muốn hướng khác thì bấm 'Gợi ý khác'.

Kỹ thuật:

- `state/suggest.py` sinh gợi ý khi được gọi; worker không tự sinh sau mỗi lượt.
- API ở `api/routes_state.py`; frontend ở `useSuggestions.ts` và `SuggestionArea.tsx`.
- Lý do khoá nút nằm trong `suggestLogic.ts`.

## Done when

- [ ] Unit: gợi ý chỉ sinh khi người chơi yêu cầu; worker không tự sinh; kết quả thay gợi ý cũ và chỉ gắn với lượt cuối của nhân vật.
- [ ] Unit: `suggestAvailability` khoá kèm lý do khi: story đang tải, máy không trả lời, nhân vật đang trả lời, đang nghĩ gợi ý, lượt cuối là của người chơi, chưa có lượt nào, hoặc lượt cuối thuộc mode kia; server cũng từ chối khi bận.
- [ ] Unit: gửi lượt mới, sửa hay xoá lượt được gợi ý thì gợi ý biến mất; lỗi là một câu không có chữ 'model' hay 'Ollama', chi tiết kỹ thuật để riêng (`suggestions_error_is_plain_with_technical_detail`).
- [ ] Unit: prompt gợi ý có luật an toàn.
- [ ] Bot: mở menu 'Thêm' và chọn 'Nhận gợi ý' thì nhóm 'Gợi ý cho bạn' hiện đúng 3 nút 'Gửi: …'; nút 'Ẩn gợi ý' ẩn chúng.
- [ ] Bot: trong lúc chờ gợi ý có ba chấm và nút 'Huỷ gợi ý'; bấm một thẻ gợi ý thì lượt người chơi mới có đúng chữ của thẻ và nhóm gợi ý biến mất.
- [ ] Model thật: trên gemma4:12b, 'Nhận gợi ý' cho đúng 3 gợi ý tiếng Việt, mỗi gợi ý gửi đi làm lượt người chơi vẫn giữ nguyên văn (không bị tách thành chỉ đạo, nằm nguyên văn trong lượt gửi model); 'Gợi ý khác' cho 3 gợi ý không trùng và không trùng quá 60% từ với lần trước, tính trên gợi ý ngắn hơn (kịch bản `f15-goi-y`).

## Tests

- backend/tests/test_phase3b.py::test_suggestions_on_demand_and_replace
- backend/tests/test_phase3b.py::test_suggestions_need_character_last
- backend/tests/test_phase3b.py::test_suggestions_busy_both_ways
- backend/tests/test_phase3b.py::test_suggestions_error_is_plain_with_technical_detail
- backend/tests/test_phase3b.py::test_suggest_validate_and_prompt
- backend/tests/test_phase3b.py::test_repo_replace_suggestions_only_on_last_character_message
- backend/tests/test_phase3b_e2e.py::test_suggestions_requested_shown_then_gone_after_send
- backend/tests/test_phase3b_e2e.py::test_suggestions_survive_reextract_but_not_edit
- backend/tests/test_compliance.py::test_safety_line_in_reply_suggestions
- frontend/src/pages/chat/suggestLogic.test.ts
- bot: menu cộng, Nhận gợi ý hiện gợi ý
- bot: chờ gợi ý có Huỷ gợi ý, chạm thẻ là gửi
- model: f15-goi-y

## Ngoài Done when

Không chặn ✅ — kiểm bằng tay (chủ dự án đồng ý 2026-11-14, [raw](../raw/2026-11-14-po-quyet-harness.md)).

- "'Gợi ý khác' cho **hướng khác về ý** với lần trước": chỉ người đọc chấm được. Phần máy chấm được nằm ở dòng Model thật (`f15-goi-y`: lần hai trùng < 60% từ), "bấm thẻ thì gửi nguyên văn" có dòng Bot thứ hai và dòng Model thật. Xem [kich-ban-model-that](../decisions/kich-ban-model-that.md).

## Liên quan

- **Code:** [`backend/lyris/state/suggest.py`](../../backend/lyris/state/suggest.py), [`backend/lyris/api/routes_state.py`](../../backend/lyris/api/routes_state.py), [`frontend/src/pages/chat/useSuggestions.ts`](../../frontend/src/pages/chat/useSuggestions.ts), [`frontend/src/pages/chat/SuggestionArea.tsx`](../../frontend/src/pages/chat/SuggestionArea.tsx), [`frontend/src/pages/chat/QuickReplies.tsx`](../../frontend/src/pages/chat/QuickReplies.tsx), [`frontend/src/pages/chat/suggestLogic.ts`](../../frontend/src/pages/chat/suggestLogic.ts)
- **Tài liệu:** [phase3.md §10.1-10.3](../../docs/phase3.md), [design-impl.md §15](../../docs/design-impl.md)
- **Quyết định:** [goi-y-chi-khi-bam](../decisions/goi-y-chi-khi-bam.md), [menu-cong-o-nhap](../decisions/menu-cong-o-nhap.md)
