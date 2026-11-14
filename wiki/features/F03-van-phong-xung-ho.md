# F03 — Văn phong, xưng hô và thiết lập story

- **Trạng thái:** xem `memory/features.json` · **Phase:** Phase 0-2
- **Giai đoạn:** Đã có
- **Màn hình:** [story-settings](../screens/story-settings.md), [start-story-sheet](../screens/start-story-sheet.md), [card-editor](../screens/card-editor.md)

## Là gì

Xưng hô và giọng văn đi theo bối cảnh (viet_hien_dai, trung_hien_dai, trung_co_dai, trung_dan_quoc), không theo ngôn ngữ hiển thị. Mỗi story ghi giới tính hai bên, kiểu quan hệ, ngôi kể, đại từ dẫn truyện, ngôn ngữ (Việt/Anh). Xưng hô chỉ dùng trong thoại và Thought, không dùng để dẫn truyện.

## Hoạt động thế nào

- Mỗi nhân vật chọn một bối cảnh văn phong, ví dụ Việt hiện đại hay Trung cổ đại.
- Xưng hô và giọng văn đi theo bối cảnh đó, không theo ngôn ngữ hiển thị.
- Mỗi story có thiết lập riêng: giới tính hai bên, kiểu quan hệ, ngôi kể, đại từ dẫn truyện, ngôn ngữ.
- Xưng hô chỉ dùng trong lời thoại và suy nghĩ. Dẫn truyện dùng đại từ dẫn truyện.

Kỹ thuật:

- Style profile là file markdown trong `prompt/styles/` (chung, viet_hien_dai, trung_hien_dai, trung_co_dai, trung_dan_quoc).
- Template prompt theo ngôn ngữ: `prompt/templates/vi.py` và `en.py`.
- Thiết lập story lưu và sửa qua `studio/stories.py`, giao diện ở `StorySettingsPanel.tsx`.

## Done when

- [ ] Unit: có đủ 5 style profile trong `backend/lyris/prompt/styles/`, mỗi file có phần vi và en; frontmatter không lọt vào prompt.
- [ ] Unit: `PATCH /api/stories/{id}` sửa được tiêu đề, bối cảnh, ngôn ngữ, kiểu quan hệ, ngôi kể, kiểu suy nghĩ, `show_thoughts`; giao diện chỉ gửi trường đã đổi.
- [ ] Unit: tạo story lấy đại từ dẫn truyện từ card, rồi từ style profile; xưng hô trùng đại từ dẫn truyện bị bắt.
- [ ] Unit: story tiếng Anh dùng prompt tiếng Anh đã kiểm; story tiếng Việt dùng prompt tiếng Việt đã kiểm.
- [ ] Unit: thành viên không đổi được model của story và không thấy danh sách model; chỉ chủ máy đổi được.
- [ ] Bot: ở `#/chat/<id>`, bấm 'Thiết lập story' mở panel có ô tiêu đề, bối cảnh, ngôn ngữ, kiểu quan hệ, ngôi kể, kiểu suy nghĩ và công tắc 'Đọc suy nghĩ của nhân vật'; bấm 'Xoá story…' thì hiện hộp 'Xác nhận xoá story' có nút 'Xoá vĩnh viễn' trước khi xoá (bấm 'Huỷ' thì story vẫn còn).
- [ ] Bot: chọn model của story chỉ có trong 'Nâng cao' và chỉ chủ máy thấy: sheet bắt đầu (cả khi mở 'Tuỳ chỉnh story') không có chữ hay ô model; 'Thiết lập story' của chủ máy có 'Nâng cao' đang gập, chỉ khi mở ra mới có ô 'Model trả lời' (có danh sách model); sheet bắt đầu và 'Thiết lập story' của thành viên không có 'Nâng cao' hay model.
- [ ] Model thật: card `trung_co_dai` không dùng 'anh/em' hay 'tớ/cậu' (harness `run_eval.py`, kịch bản `07-co-trang`).
- [ ] Model thật: dẫn truyện ngôi thứ ba không có 'tôi' và không dùng đại từ xưng hô của lời thoại (harness `run_eval.py`, kịch bản `01-mo-dau`, `06-viet-hien-dai`, `07-co-trang`: `narration_forbidden`).
- [ ] Model thật: story tiếng Anh trả lời bằng tiếng Anh (harness kịch bản `08-tieng-anh`).

## Tests

- backend/tests/test_styles.py
- backend/tests/test_studio_stories.py
- backend/tests/test_api_studio.py::test_patch_story_phase2_fields
- backend/tests/test_prompt.py::test_en_story_rules_match_verified_prompt
- backend/tests/test_prompt.py::test_vi_story_rules_match_verified_prompt
- backend/tests/test_prompt.py::test_address_terms_overlapping_narration_pronoun
- backend/tests/test_auth_routes.py::test_member_cannot_change_story_model_and_health_hides_models
- frontend/src/lib/storyOptions.test.ts
- bot: Thiết lập story có đủ ô, Xoá story hỏi lại
- bot: chọn model của story chỉ có trong Nâng cao của Thiết lập story, chỉ chủ máy thấy
- model: 01-mo-dau
- model: 06-viet-hien-dai
- model: 07-co-trang
- model: 08-tieng-anh

## Liên quan

- **Code:** [`backend/lyris/prompt/styles/`](../../backend/lyris/prompt/styles/), [`backend/lyris/prompt/templates/vi.py`](../../backend/lyris/prompt/templates/vi.py), [`backend/lyris/prompt/templates/en.py`](../../backend/lyris/prompt/templates/en.py), [`backend/lyris/studio/stories.py`](../../backend/lyris/studio/stories.py), [`frontend/src/components/StorySettingsPanel.tsx`](../../frontend/src/components/StorySettingsPanel.tsx), [`frontend/src/components/PronounFields.tsx`](../../frontend/src/components/PronounFields.tsx)
- **Tài liệu:** [plan.md §7](../../docs/plan.md), [phase2.md](../../docs/phase2.md)
- **Quyết định:** [van-phong-theo-boi-canh](../decisions/van-phong-theo-boi-canh.md), [xung-ho-tach-dan-truyen](../decisions/xung-ho-tach-dan-truyen.md), [tieng-viet-truoc](../decisions/tieng-viet-truoc.md)
