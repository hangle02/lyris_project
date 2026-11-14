# F07 — Thẻ suy nghĩ (Tiếng lòng giấu kín)

- **Trạng thái:** xem `memory/features.json` · **Phase:** Phase 1, 2b
- **Giai đoạn:** Đã có
- **Màn hình:** [chat-story](../screens/chat-story.md), [chat-dm](../screens/chat-dm.md), [thought-menu](../screens/thought-menu.md)

## Là gì

Suy nghĩ thầm của nhân vật hiện thành thẻ viền trái, mặc định làm mờ với lời mời 'Chạm để lắng nghe'. Có hai kiểu: 'Lồng trong truyện' (inline, 2-3 thẻ rải giữa truyện) và 'Một đoạn ở cuối' (end). Công tắc 'Luôn hiện suy nghĩ' bỏ làm mờ.

## Hoạt động thế nào

- Thẻ suy nghĩ mặc định bị làm mờ, có lời mời 'Chạm để lắng nghe'. Chạm thì đọc được.
- Người chơi chọn kiểu suy nghĩ: 'Lồng trong truyện' (rải 2-3 thẻ giữa truyện) hoặc 'Một đoạn ở cuối'.
- Ai thích đọc hết thì bật 'Luôn hiện suy nghĩ'.

Kỹ thuật:

- Model viết `[Thought: ...]`; `llm/thought.py` tách khối.
- Kiểu suy nghĩ lưu theo story (`thought_style`), chọn ở `ThoughtMenu.tsx` hoặc Thiết lập story.
- 'Luôn hiện suy nghĩ' lưu ở trình duyệt (`revealThoughts.ts`).

## Done when

- [ ] Unit: kiểu suy nghĩ lưu theo story (`thought_style`); mặc định 'Lồng trong truyện' (inline) và ghi chú cuối dặn đúng kiểu; 'Một đoạn ở cuối' (end) dặn một Thought dài hơn ở cuối lượt.
- [ ] Unit: checker harness đếm đúng số Thought, Thought liền nhau, Thought ở cuối và Thought chưa đóng.
- [ ] Bot: thẻ suy nghĩ trong lượt nhân vật (nút có `aria-pressed`) bị làm mờ (`filter: blur`) kèm chữ 'Chạm để lắng nghe'; chạm thì hết mờ và `aria-pressed="true"`.
- [ ] Bot: bật 'Luôn hiện suy nghĩ' trong menu 'Suy nghĩ' thì mọi thẻ hiện rõ và localStorage có khoá `lyris.revealThoughts`.
- [ ] Bot: menu 'Suy nghĩ' có nhóm radio 'Lồng trong truyện' / 'Một đoạn ở cuối'; chọn kiểu kia thì `GET /api/stories/{id}` trả `thought_style` mới.
- [ ] Bot: ở DM, lượt nhân vật có Thought hiện thẻ suy nghĩ thu gọn.
- [ ] Model thật: kiểu 'Lồng trong truyện' cho 2-4 Thought, không có hai Thought liền nhau; kiểu 'Một đoạn ở cuối' cho đúng một Thought cuối lượt; không có Thought chưa đóng (harness `run_eval.py`, kịch bản `f07-thought-long`, `f07-thought-cuoi`).

## Tests

- backend/tests/test_prompt.py::test_thought_style_inline_is_default_and_in_note
- backend/tests/test_prompt.py::test_thought_style_end_asks_for_one_longer_thought
- backend/tests/test_prompt.py::test_thought_style_en
- backend/tests/test_repo.py::test_v1_database_upgrades_with_default_thought_style
- backend/tests/test_harness_checks.py::test_thought_range_checks
- backend/tests/test_harness_checks.py::test_thought_at_end_check
- backend/tests/test_harness_checks.py::test_adjacent_thoughts_check
- backend/tests/test_harness_checks.py::test_unclosed_inline_thought_is_caught
- frontend/src/lib/storyOptions.test.ts
- frontend/src/lib/storyBlocks.test.ts
- bot: thẻ suy nghĩ bị làm mờ, chạm thì hiện
- bot: Luôn hiện suy nghĩ bỏ làm mờ
- bot: đổi kiểu suy nghĩ ở menu Suy nghĩ
- bot: DM có thẻ suy nghĩ thu gọn
- model: f07-thought-long
- model: f07-thought-cuoi

## Liên quan

- **Code:** [`frontend/src/pages/chat/ThoughtCard.tsx`](../../frontend/src/pages/chat/ThoughtCard.tsx), [`frontend/src/pages/chat/ThoughtMenu.tsx`](../../frontend/src/pages/chat/ThoughtMenu.tsx), [`frontend/src/pages/chat/revealThoughts.ts`](../../frontend/src/pages/chat/revealThoughts.ts), [`frontend/src/lib/storyOptions.ts`](../../frontend/src/lib/storyOptions.ts), [`backend/lyris/llm/thought.py`](../../backend/lyris/llm/thought.py)
- **Tài liệu:** [plan.md §1](../../docs/plan.md), [design-impl.md §6.2](../../docs/design-impl.md)
- **Quyết định:** [thought-rai-giua-truyen](../decisions/thought-rai-giua-truyen.md), [tuy-chon-doc-suy-nghi](../decisions/tuy-chon-doc-suy-nghi.md)
