# F25 — Tương tác: danh sách story

- **Trạng thái:** xem `memory/features.json` · **Phase:** Phase 2b
- **Giai đoạn:** Đã có
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

- [ ] Unit: giờ hiện '23:15' (hôm nay), 'Hôm qua', hoặc '12/11', kể cả qua ranh giới tháng.
- [ ] Unit: tìm story khớp mọi từ ở tên nhân vật, tiêu đề, nơi chốn; không cần gõ dấu.
- [ ] Unit: dòng xem trước bỏ Thought và ((...)); story mới hoạt động nhất ở trên.
- [ ] Bot: tài khoản đã có story đăng nhập thẳng ở `#/login` thì vào màn Tương tác `#/` (header hub có nút '… Mở tài khoản', danh sách có link `#/chat/<id>`), không tự nhảy vào story gần nhất.
- [ ] Bot: gõ tên nhân vật vào ô 'Tìm story' thì danh sách chỉ còn story của nhân vật đó; gõ chữ không khớp thì danh sách rỗng; dòng xem trước không chứa '[Thought' hay '(('.
- [ ] Bot: tài khoản không có story nào thấy 'Chưa có story nào…' và nút 'Mở Khám phá'; tài khoản chưa đặt profile thấy khối 'Đặt tên cho tài khoản của bạn'.

## Tests

- frontend/src/pages/hub/logic.test.ts
- backend/tests/test_lyris_design.py::test_story_list_fields
- backend/tests/test_repo.py::test_list_stories_newest_first
- backend/tests/test_repo.py::test_story_activity_and_list_order
- bot: đăng nhập ở #/login thì vào Tương tác, không tự mở story
- bot: Tìm story lọc danh sách, xem trước sạch
- bot: hub rỗng có Mở Khám phá, khối mời đặt profile

## Liên quan

- **Code:** [`frontend/src/pages/hub/HubPage.tsx`](../../frontend/src/pages/hub/HubPage.tsx), [`frontend/src/pages/hub/logic.ts`](../../frontend/src/pages/hub/logic.ts), [`frontend/src/pages/profile/AccountInvite.tsx`](../../frontend/src/pages/profile/AccountInvite.tsx), [`backend/lyris/api/routes.py`](../../backend/lyris/api/routes.py)
- **Tài liệu:** [design-impl.md §6.1, §14](../../docs/design-impl.md)
- **Quyết định:** [thuat-ngu-story](../decisions/thuat-ngu-story.md)
