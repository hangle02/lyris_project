# F40 — Đạo diễn truyện và Khoảnh khắc

- **Trạng thái:** xem `memory/features.json` · **Phase:** Phase 8 (tuỳ chọn)
- **Giai đoạn:** Kế hoạch
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

- [ ] Unit: backend sinh `extras.moment` khi có khoảnh khắc đáng nhớ.
- [ ] Bot: banner 'Khoảnh khắc' hiện dưới header chat khi `extras.moment` có dữ liệu.
- [ ] Bot: tab 'Khoảnh khắc' trong sheet Sự kiện có nội dung.

## Tests

Chưa có test: tính năng còn là kế hoạch. Viết test cùng lúc với code.

Tên check bot dự kiến (chưa có trong `environment/e2e.mjs`, thêm khi làm): `bot: banner Khoảnh khắc`; `bot: tab Khoảnh khắc có nội dung`.

## Ngoài Done when

Không chặn ✅ (cần thử tay, dịch vụ thật, hoặc còn là kế hoạch).

- Trước khi code: có plan riêng cho Phase 8.

## Liên quan

- **Code:** [`frontend/src/pages/chat/MomentBanner.tsx`](../../frontend/src/pages/chat/MomentBanner.tsx), [`frontend/src/pages/chat/EventsSheet.tsx`](../../frontend/src/pages/chat/EventsSheet.tsx), [`backend/lyris/models.py`](../../backend/lyris/models.py)
- **Tài liệu:** [plan.md Phase 8](../../docs/plan.md), [phase3.md §10.3](../../docs/phase3.md)
