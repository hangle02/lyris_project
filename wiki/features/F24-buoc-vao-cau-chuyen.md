# F24 — Bắt đầu story ('Bước vào câu chuyện')

- **Trạng thái:** xem `memory/features.json` · **Phase:** Phase 2b (§16)
- **Giai đoạn:** Đã có
- **Màn hình:** [start-story-sheet](../screens/start-story-sheet.md), [character-profile](../screens/character-profile.md)

## Là gì

Bấm 'Bước vào câu chuyện' mở sheet chọn persona. 'Tuỳ chỉnh story' (đóng sẵn) cho sửa tiêu đề, bối cảnh, lời mở đầu, ngôn ngữ, Story/DM, kiểu quan hệ, ngôi kể, đại từ, kiểu suy nghĩ. Mẫu chưa cài chỉ được cài khi thật cần.

## Hoạt động thế nào

- Trong hồ sơ nhân vật, bấm 'Bước vào câu chuyện'.
- Sheet hiện ra để chọn persona. Persona mặc định đã được chọn sẵn.
- Muốn đổi gì thì mở 'Tuỳ chỉnh story': tiêu đề, bối cảnh, lời mở đầu, ngôn ngữ, Story/DM, kiểu quan hệ, ngôi kể, đại từ, kiểu suy nghĩ.
- Bấm tạo thì vào thẳng chat.

Kỹ thuật:

- Không mở tuỳ chỉnh thì frontend chỉ gửi `card_id` và `persona_id`; server tự điền mặc định.
- Nhân vật mẫu chưa cài chỉ được cài khi người dùng thật sự tạo story.
- Nhân vật công khai của người khác: story dùng bản sao chụp lúc bắt đầu.

## Done when

- [ ] Unit: không mở 'Tuỳ chỉnh story' thì chỉ gửi `card_id` và `persona_id`; server tự điền mặc định (tiêu đề, ngôn ngữ, đại từ, lời mở đầu).
- [ ] Unit: link cũ `#/new-story?card=12` chuyển sang `#/character/12?start=1`.
- [ ] Unit: persona mặc định được chọn sẵn; bắt đầu story với nhân vật công khai của người khác thì chụp một bản sao đầy đủ.
- [ ] Bot: bấm 'Bước vào câu chuyện' ở hồ sơ mở sheet 'Chọn persona'; chọn persona rồi bấm 'Bước vào câu chuyện' trong sheet thì sang `#/chat/<id>` và có lời chào của nhân vật.
- [ ] Bot: sheet mở với persona đang dùng (đã đổi ở sheet Tài khoản, không phải persona mới thêm gần nhất) được chọn sẵn và 'Tuỳ chỉnh story' đang gập.
- [ ] Bot: mở `#/new-story?card=<id>` (link cũ) thì về hồ sơ `#/character/<id>` với sheet 'Chọn persona' đang mở.
- [ ] Bot: tài khoản thứ hai bắt đầu story với nhân vật công khai của người khác thì sheet có dòng '@{handle} sửa nhân vật sau này thì story của bạn không đổi.'

## Tests

- frontend/src/pages/character/startLogic.test.ts
- frontend/src/lib/router.test.ts
- backend/tests/test_studio_stories.py
- backend/tests/test_api_studio.py::test_story_defaults
- backend/tests/test_lyris_design.py::test_default_persona_and_model_for_new_story
- backend/tests/test_lyris_design.py::test_story_defaults_without_any_persona
- backend/tests/test_public_cards.py::test_start_story_makes_a_full_copy
- bot: bắt đầu story qua sheet và persona, story mở với lời chào
- bot: sheet bắt đầu chọn sẵn persona mặc định, Tuỳ chỉnh gập
- bot: link new-story cũ chuyển sang hồ sơ
- bot: nhân vật công khai có dòng bản sao

## Liên quan

- **Code:** [`frontend/src/pages/character/StartStorySheet.tsx`](../../frontend/src/pages/character/StartStorySheet.tsx), [`frontend/src/pages/character/startLogic.ts`](../../frontend/src/pages/character/startLogic.ts), [`frontend/src/lib/router.ts`](../../frontend/src/lib/router.ts), [`backend/lyris/api/routes.py`](../../backend/lyris/api/routes.py)
- **Tài liệu:** [design-impl.md §16](../../docs/design-impl.md)
- **Quyết định:** [card-doi-story-doi-theo](../decisions/card-doi-story-doi-theo.md), [ban-sao-nhan-vat-cong-khai](../decisions/ban-sao-nhan-vat-cong-khai.md)
