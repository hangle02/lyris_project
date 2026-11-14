# Đạo diễn truyện và Khoảnh khắc

- **Trạng thái:** Chưa làm · **Phase:** Phase 8 (tuỳ chọn)
- **Màn hình:** [chat-story](../screens/chat-story.md), [events-sheet](../screens/events-sheet.md)

## Là gì

Director điều tiết nhịp truyện và mission, cảnh nhiều nhân vật, NPC tự hành, địa điểm và quest. Banner 'Khoảnh khắc' và tab 'Khoảnh khắc' trong sheet Sự kiện đã có chỗ, nhưng backend chưa sinh dữ liệu (`moment` luôn null).

## Hoạt động thế nào

- Mong muốn: một 'đạo diễn' điều tiết nhịp truyện, có mission, cảnh nhiều nhân vật, NPC tự hành, địa điểm, quest.
- Khoảnh khắc đáng nhớ sẽ hiện thành banner dưới header chat và trong tab 'Khoảnh khắc' của sheet Sự kiện.
- Hiện chỉ có chỗ trên giao diện; chưa có dữ liệu.

Kỹ thuật:

- `models.py` có kiểu `Moment`, nhưng `extras.moment` luôn là null.
- `MomentBanner.tsx` và tab 'Khoảnh khắc' trong `EventsSheet.tsx` đã có sẵn.

## Done when

- [ ] Có plan riêng cho Phase 8.
- [ ] Backend sinh `extras.moment` khi có khoảnh khắc đáng nhớ.
- [ ] Banner 'Khoảnh khắc' hiện dưới header chat khi có dữ liệu.
- [ ] Tab 'Khoảnh khắc' trong sheet Sự kiện có nội dung.

## Liên quan

- **Code:** [`frontend/src/pages/chat/MomentBanner.tsx`](../../frontend/src/pages/chat/MomentBanner.tsx), [`frontend/src/pages/chat/EventsSheet.tsx`](../../frontend/src/pages/chat/EventsSheet.tsx), [`backend/lyris/models.py`](../../backend/lyris/models.py)
- **Tài liệu:** [plan.md Phase 8](../../docs/plan.md), [phase3.md §10.3](../../docs/phase3.md)
