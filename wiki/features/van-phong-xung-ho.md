# Văn phong, xưng hô và thiết lập story

- **Trạng thái:** Đã xong · **Phase:** Phase 0-2
- **Màn hình:** [story-settings](../screens/story-settings.md), [start-story-sheet](../screens/start-story-sheet.md), [card-editor](../screens/card-editor.md)

## Là gì

Xưng hô và giọng văn đi theo bối cảnh (viet_hien_dai, trung_hien_dai, trung_co_dai, trung_dan_quoc), không theo ngôn ngữ hiển thị. Mỗi story ghi giới tính hai bên, kiểu quan hệ, ngôi kể, đại từ dẫn truyện, ngôn ngữ (Việt/Anh). Xưng hô chỉ dùng trong thoại và Thought, không dùng để dẫn truyện.

## Hoạt động thế nào

- Mỗi nhân vật chọn một bối cảnh văn phong, ví dụ Việt hiện đại hay Trung cổ đại.
- Xưng hô và giọng văn đi theo bối cảnh đó, không theo ngôn ngữ hiển thị.
- Mỗi story có thiết lập riêng: giới tính hai bên, kiểu quan hệ, ngôi kể, đại từ dẫn truyện, ngôn ngữ.
- Xưng hô chỉ dùng trong lời thoại và suy nghĩ. Dẫn truyện dùng đại từ dẫn truyện.

Kỹ thuật:

- Style profile là file markdown trong `prompt/styles/` (chung, viet_hien_dai, trung_hien_dai, trung_co_dai, trung_dan_quoc).
- Template prompt theo ngôn ngữ: `prompt/templates/vi.py` và `en.py`.
- Thiết lập story lưu và sửa qua `studio/stories.py`, giao diện ở `StorySettingsPanel.tsx`.

## Done when

- [x] Có 5 file style profile trong backend/lyris/prompt/styles/.
- [x] Thiết lập story sửa được tiêu đề, bối cảnh, ngôn ngữ, kiểu quan hệ, ngôi kể, kiểu suy nghĩ, 'Đọc suy nghĩ'; nút Xoá story hỏi lại.
- [x] Card trung_co_dai không dùng 'anh/em' hay 'tớ/cậu' (harness kiểm tra).
- [x] Phần dẫn truyện ngôi thứ ba không có 'tôi' và dùng đúng đại từ dẫn truyện.
- [x] Story tiếng Anh trả lời bằng tiếng Anh.
- [x] Chọn model của story chỉ có trong 'Nâng cao' và chỉ chủ máy thấy.

## Liên quan

- **Code:** [`backend/lyris/prompt/styles/`](../../backend/lyris/prompt/styles/), [`backend/lyris/prompt/templates/vi.py`](../../backend/lyris/prompt/templates/vi.py), [`backend/lyris/prompt/templates/en.py`](../../backend/lyris/prompt/templates/en.py), [`backend/lyris/studio/stories.py`](../../backend/lyris/studio/stories.py), [`frontend/src/components/StorySettingsPanel.tsx`](../../frontend/src/components/StorySettingsPanel.tsx), [`frontend/src/components/PronounFields.tsx`](../../frontend/src/components/PronounFields.tsx)
- **Tài liệu:** [plan.md §7](../../docs/plan.md), [phase2.md](../../docs/phase2.md)
- **Quyết định:** [van-phong-theo-boi-canh](../decisions/van-phong-theo-boi-canh.md), [xung-ho-tach-dan-truyen](../decisions/xung-ho-tach-dan-truyen.md), [tieng-viet-truoc](../decisions/tieng-viet-truoc.md)
