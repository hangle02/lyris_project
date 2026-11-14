# Sự kiện: dòng thời gian

- **Trạng thái:** Đã xong · **Phase:** Phase 3b
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

- [x] Tab 'Dòng thời gian' có nhãn Story/DM, giờ, câu ký ức, 'Điều đã biết', chip như '+2 Thương mến' / '−3 Tin cậy' và chip cảnh.
- [x] Lượt không có gì thì không hiện.
- [x] Chạm một mục: sheet đóng, cuộn tới lượt, viền sáng lượt đó khoảng 2.4 giây; lượt ở mode kia thì đổi mode trước.
- [x] Đang bận thì chỉ báo một dòng; lượt không hiện ra sau 4 giây thì bỏ lượt nhảy.
- [x] GET /api/stories/{id}/timeline trả đúng `TimelineEntry[]`.

## Liên quan

- **Code:** [`frontend/src/pages/chat/EventsSheet.tsx`](../../frontend/src/pages/chat/EventsSheet.tsx), [`frontend/src/pages/chat/eventsLogic.ts`](../../frontend/src/pages/chat/eventsLogic.ts), [`backend/lyris/state/service.py`](../../backend/lyris/state/service.py), [`backend/lyris/api/routes_state.py`](../../backend/lyris/api/routes_state.py)
- **Tài liệu:** [phase3.md §10.1-10.3](../../docs/phase3.md)
- **Quyết định:** [su-kien-ca-hai-che-do](../decisions/su-kien-ca-hai-che-do.md)
