# Ma trận cảm xúc 6 chỉ số

- **Trạng thái:** Đã xong · **Phase:** Phase 3, 3b
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

- [x] Ngăn cảm xúc có thẻ 'Chỉ dẫn diễn xuất' và 6 thanh đo màu theo DESIGN.md §3.3, kèm phần trăm.
- [x] Mỗi chỉ số đổi tối đa ±5 một lượt; lượt ấm lòng đổi tối đa 2 chỉ số, lượt tổn thương hoặc lẫn lộn tối đa 3.
- [x] Lượt thường ngày ('chào buổi sáng', nhờ giảng bài) không đổi chỉ số.
- [x] Ghen, nói dối, quên hẹn thì Tin cậy giảm; xin lỗi thật lòng thì Khoảng cách giảm, Tin cậy tăng (đo bằng harness fixemo).
- [x] Cảm xúc ban đầu lấy từ `extensions.lyris.initial_relationship` của card.
- [x] Thẻ story ở hub có chip cảm xúc nổi bật như 'Thương mến 91%'.
- [x] `test_directive.py`, `test_extract.py`, `test_state_fold.py` qua.

## Liên quan

- **Code:** [`backend/lyris/state/extract.py`](../../backend/lyris/state/extract.py), [`backend/lyris/state/directive.py`](../../backend/lyris/state/directive.py), [`backend/lyris/state/fold.py`](../../backend/lyris/state/fold.py), [`backend/lyris/jobs/worker.py`](../../backend/lyris/jobs/worker.py), [`frontend/src/pages/chat/HeartDrawer.tsx`](../../frontend/src/pages/chat/HeartDrawer.tsx), [`frontend/src/pages/studio/EmotionSection.tsx`](../../frontend/src/pages/studio/EmotionSection.tsx)
- **Tài liệu:** [phase3.md §2-§5, §10.5, §10.7](../../docs/phase3.md), [DESIGN.md §3.3](../../DESIGN.md)
- **Quyết định:** [cam-xuc-tang-giam](../decisions/cam-xuc-tang-giam.md), [viec-nen-dung-model-chat](../decisions/viec-nen-dung-model-chat.md)
