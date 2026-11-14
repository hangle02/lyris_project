# Bắt đầu story ('Bước vào câu chuyện')

- **Trạng thái:** Đã xong · **Phase:** Phase 2b (§16)
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

- [x] Persona mặc định được chọn sẵn; danh sách là radio thật có avatar.
- [x] Chưa có persona thì form 'Tạo persona mới' tự mở.
- [x] Không mở 'Tuỳ chỉnh story' thì chỉ gửi card_id và persona_id, server tự điền mặc định.
- [x] Tạo story xong thì vào `#/chat/<id>`.
- [x] Link cũ `#/new-story?card=12` chuyển sang `#/character/12?start=1`.
- [x] Nhân vật công khai của người khác có dòng '@{handle} sửa nhân vật sau này thì story của bạn không đổi.'

## Liên quan

- **Code:** [`frontend/src/pages/character/StartStorySheet.tsx`](../../frontend/src/pages/character/StartStorySheet.tsx), [`frontend/src/pages/character/startLogic.ts`](../../frontend/src/pages/character/startLogic.ts), [`frontend/src/lib/router.ts`](../../frontend/src/lib/router.ts), [`backend/lyris/api/routes.py`](../../backend/lyris/api/routes.py)
- **Tài liệu:** [design-impl.md §16](../../docs/design-impl.md)
- **Quyết định:** [card-doi-story-doi-theo](../decisions/card-doi-story-doi-theo.md), [ban-sao-nhan-vat-cong-khai](../decisions/ban-sao-nhan-vat-cong-khai.md)
