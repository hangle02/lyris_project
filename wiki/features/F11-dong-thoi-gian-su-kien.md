# F11 — Sự kiện: dòng thời gian

- **Trạng thái:** xem `memory/features.json` · **Phase:** Phase 3b
- **Giai đoạn:** Đã có
- **Màn hình:** [events-sheet](../screens/events-sheet.md)

## Là gì

Sheet 'Sự kiện' (mở từ menu '+') liệt kê các lượt có ký ức, điều đã biết, thay đổi cảm xúc hay đổi cảnh, mới ở trên. Chạm một mục thì nhảy tới lượt đó. Tab 'Khoảnh khắc' để trống chờ Phase 8.

## Hoạt động thế nào

- Mở menu '+' và chọn 'Xem sự kiện'.
- Sheet liệt kê những lượt đáng nhớ: ký ức, điều đã biết, cảm xúc thay đổi, đổi cảnh. Mới nhất ở trên.
- Chạm một mục thì nhảy về đúng lượt đó trong chat, kể cả lượt ở mode kia.

Kỹ thuật:

- `GET /api/stories/{id}/timeline` trả `TimelineEntry[]` (dựng ở `state/service.py`).
- `eventsLogic.ts` định dạng giờ và chip; `EventsSheet.tsx` vẽ hai tab.
- Tab 'Khoảnh khắc' để trống, chờ Phase 8.

## Done when

- [ ] Unit: `GET /api/stories/{id}/timeline` trả `TimelineEntry[]` theo thứ tự story, mỗi lượt một mục, có mode.
- [ ] Unit: `eventsLogic.ts`: mới nhất ở trên, lượt không có gì bị bỏ; chip '+2 Thương mến' / '−3 Tin cậy' (dấu trừ thật, thứ tự DESIGN.md, bỏ số 0); giờ hôm nay / hôm qua / ngày.
- [ ] Unit: `jumpPlan`: lượt cùng mode thì cuộn tới; lượt mode kia thì đổi mode trước; không đổi mode được thì báo một dòng.
- [ ] Bot: mở menu 'Thêm' rồi chọn 'Xem sự kiện' thì hiện sheet có nhóm tab 'Loại sự kiện' với 'Dòng thời gian' và 'Khoảnh khắc'.
- [ ] Bot: sau một lượt có ký ức, tab 'Dòng thời gian' có mục của lượt đó (nhãn Story/DM, giờ); chạm mục thì sheet đóng và lượt đó được cuộn vào màn hình.

## Tests

- backend/tests/test_phase3b.py::test_timeline
- backend/tests/test_phase3b_e2e.py::test_timeline_after_several_turns
- frontend/src/pages/chat/eventsLogic.test.ts
- bot: menu cộng mở sheet Sự kiện
- bot: chạm mục dòng thời gian thì nhảy tới lượt

## Liên quan

- **Code:** [`frontend/src/pages/chat/EventsSheet.tsx`](../../frontend/src/pages/chat/EventsSheet.tsx), [`frontend/src/pages/chat/eventsLogic.ts`](../../frontend/src/pages/chat/eventsLogic.ts), [`backend/lyris/state/service.py`](../../backend/lyris/state/service.py), [`backend/lyris/api/routes_state.py`](../../backend/lyris/api/routes_state.py)
- **Tài liệu:** [phase3.md §10.1-10.3](../../docs/phase3.md)
- **Quyết định:** [su-kien-ca-hai-che-do](../decisions/su-kien-ca-hai-che-do.md)
