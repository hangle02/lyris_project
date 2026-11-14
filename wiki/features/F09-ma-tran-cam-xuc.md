# F09 — Ma trận cảm xúc 6 chỉ số

- **Trạng thái:** xem `memory/features.json` · **Phase:** Phase 3, 3b
- **Giai đoạn:** Đã có
- **Màn hình:** [heart-drawer](../screens/heart-drawer.md), [hub](../screens/hub.md), [card-editor](../screens/card-editor.md), [character-profile](../screens/character-profile.md)

## Là gì

Sáu chỉ số 0-100: Thương mến, Tin cậy, Rung động, Nhung nhớ / Chiếm hữu, Lo sợ mất mát, Khoảng cách. Sau mỗi lượt, việc nền chấm `tone` (everyday/warm/hurt/mixed) rồi tăng hoặc giảm vài chỉ số; directive mapper đổi số thành 1-2 câu chỉ dẫn diễn xuất cho prompt, không bao giờ đưa số thô.

## Hoạt động thế nào

- Nhân vật có sáu cảm xúc với người chơi, mỗi cái 0-100.
- Sau mỗi lượt, cảm xúc tăng hoặc giảm một chút tuỳ chuyện vừa xảy ra. Chuyện thường ngày thì không đổi.
- Người chơi xem sáu thanh đo trong ngăn cảm xúc (nút tim trên header chat).
- Nhân vật diễn theo cảm xúc, nhưng model không bao giờ thấy con số.

Kỹ thuật:

- `state/extract.py` cho model chấm `tone` (everyday/warm/hurt/mixed) rồi mới chấm số.
- Mỗi chỉ số đổi tối đa ±5 một lượt (`MAX_DELTA`); lượt ấm lòng giữ tối đa 2 chỉ số, lượt tổn thương hoặc lẫn lộn tối đa 3.
- `state/directive.py` đổi số thành 1-2 câu chỉ dẫn diễn xuất trong khối F.
- Cảm xúc ban đầu đặt ở Studio (`EmotionSection.tsx`).

## Done when

- [ ] Unit: mỗi chỉ số luôn trong 0-100 và đổi tối đa ±5 một lượt (`MAX_DELTA`); dữ liệu rác từ model không làm lỗi.
- [ ] Unit: theo `tone`: lượt thường ngày không đổi chỉ số nào; lượt ấm lòng giữ tối đa 2 thay đổi; lượt tổn thương hoặc lẫn lộn tối đa 3.
- [ ] Unit: `state/directive.py` đổi số thành 1-2 câu chỉ dẫn diễn xuất, không bao giờ có con số.
- [ ] Unit: cảm xúc ban đầu lấy từ `extensions.lyris.initial_relationship` của card và được chụp vào story khi tạo.
- [ ] Unit: thẻ story ở hub có chip cảm xúc nổi bật như 'Thương mến 91%' (`dominantEmotion`, `storyChips`); sáu chỉ số theo thứ tự DESIGN.md.
- [ ] Bot: bấm 'Cảm xúc & ký ức' mở ngăn cùng tên có đúng 6 thanh `role="meter"`.
- [ ] Bot: ngăn 'Cảm xúc & ký ức' có thẻ 'Chỉ dẫn diễn xuất' và mỗi thanh cảm xúc có phần trăm.
- [ ] Model thật: ghen, nói dối, quên hẹn thì Tin cậy giảm; xin lỗi thật lòng thì Khoảng cách giảm, Tin cậy tăng; 'chào buổi sáng' hay nhờ giảng bài không đổi chỉ số; xét chỉ số sau khi app lọc, đúng số được lưu (harness kịch bản `f09-cam-xuc`, [phase3.md §10.5](../../docs/phase3.md)).

## Tests

- backend/tests/test_extract.py
- backend/tests/test_directive.py
- backend/tests/test_state_fold.py
- backend/tests/test_api_state.py::test_create_story_snapshots_card_relationship
- backend/tests/test_jobs.py::test_initial_relationship_used_for_old_story_without_snapshot
- frontend/src/pages/hub/logic.test.ts
- frontend/src/pages/chat/chatLogic.test.ts
- frontend/src/components/ui/logic.test.ts
- frontend/src/lib/cardForm.test.ts
- bot: ngăn trái tim mở với 6 cảm xúc
- bot: ngăn trái tim có Chỉ dẫn diễn xuất và phần trăm
- model: f09-cam-xuc

## Liên quan

- **Code:** [`backend/lyris/state/extract.py`](../../backend/lyris/state/extract.py), [`backend/lyris/state/directive.py`](../../backend/lyris/state/directive.py), [`backend/lyris/state/fold.py`](../../backend/lyris/state/fold.py), [`backend/lyris/jobs/worker.py`](../../backend/lyris/jobs/worker.py), [`frontend/src/pages/chat/HeartDrawer.tsx`](../../frontend/src/pages/chat/HeartDrawer.tsx), [`frontend/src/pages/studio/EmotionSection.tsx`](../../frontend/src/pages/studio/EmotionSection.tsx)
- **Tài liệu:** [phase3.md §2-§5, §10.5, §10.7](../../docs/phase3.md), [DESIGN.md §3.3](../../DESIGN.md)
- **Quyết định:** [cam-xuc-tang-giam](../decisions/cam-xuc-tang-giam.md), [viec-nen-dung-model-chat](../decisions/viec-nen-dung-model-chat.md)
