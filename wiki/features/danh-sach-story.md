# Tương tác: danh sách story

- **Trạng thái:** Đã xong · **Phase:** Phase 2b
- **Màn hình:** [hub](../screens/hub.md)

## Là gì

Tab giữa 'Tương tác' liệt kê mọi story, mới nhất trên cùng: avatar, huy hiệu Story/DM, giờ gần nhất, vai trò, một dòng xem trước, chip cảm xúc và nơi chốn. Có câu chào theo giờ và ô tìm kiếm.

## Hoạt động thế nào

- Mở app thì vào tab giữa 'Tương tác', không tự nhảy vào story gần nhất.
- Danh sách story mới nhất ở trên: avatar, Story/DM, giờ, vai trò, một dòng xem trước, cảm xúc nổi bật, nơi chốn.
- Ô 'Tìm story' lọc theo tên nhân vật, tiêu đề và nơi chốn.
- Chưa có story nào thì có nút 'Mở Khám phá'.

Kỹ thuật:

- `pages/hub/logic.ts` định dạng giờ, chọn cảm xúc nổi bật và làm sạch dòng xem trước.
- Danh sách story lấy từ `api/routes.py`.

## Done when

- [x] Mở app vào hub, không tự nhảy vào story gần nhất.
- [x] Ô 'Tìm story' lọc theo tên nhân vật, tiêu đề và nơi chốn.
- [x] Giờ hiện '23:15' (hôm nay), 'Hôm qua', hoặc '12/11'.
- [x] Dòng xem trước không chứa Thought hay ((...)).
- [x] Chưa có story thì có trạng thái rỗng + 'Mở Khám phá'.
- [x] Tài khoản chưa đặt profile thì thấy khối mời đặt profile.

## Liên quan

- **Code:** [`frontend/src/pages/hub/HubPage.tsx`](../../frontend/src/pages/hub/HubPage.tsx), [`frontend/src/pages/hub/logic.ts`](../../frontend/src/pages/hub/logic.ts), [`frontend/src/pages/profile/AccountInvite.tsx`](../../frontend/src/pages/profile/AccountInvite.tsx), [`backend/lyris/api/routes.py`](../../backend/lyris/api/routes.py)
- **Tài liệu:** [design-impl.md §6.1, §14](../../docs/design-impl.md)
- **Quyết định:** [thuat-ngu-story](../decisions/thuat-ngu-story.md)
