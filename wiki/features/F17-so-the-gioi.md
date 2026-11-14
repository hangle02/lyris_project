# F17 — Sổ thế giới (lorebook)

- **Trạng thái:** xem `memory/features.json` · **Phase:** Phase 4
- **Giai đoạn:** Đã có
- **Màn hình:** [lorebook-section](../screens/lorebook-section.md), [heart-drawer](../screens/heart-drawer.md), [character-profile](../screens/character-profile.md)

## Là gì

Mỗi nhân vật có các mục thế giới (chuyện và bí mật, người xung quanh, nơi chốn) kích hoạt khi story nhắc tới từ khoá gợi nhớ. Mỗi mục có 'Ai biết điều này', nên nhân vật không biết điều nó không được biết. Nhập được từ `world.md` (thư mục worlds/) hoặc book của Card V2.

## Hoạt động thế nào

- Người tạo nhân vật viết các mục thế giới: chuyện và bí mật, người xung quanh, nơi chốn.
- Mỗi mục có từ khoá gợi nhớ. Story nhắc tới từ khoá thì nhân vật nhớ ra mục đó.
- Mỗi mục ghi 'Ai biết điều này'. Mục 'Chỉ bạn biết' không bao giờ tới tay nhân vật.
- Người chơi thấy các mục đã mở khoá trong ngăn cảm xúc.

Kỹ thuật:

- Mục lưu trong DB theo card; nhập được từ `worlds/<tên>/world.md` (`lore/parse.py`) hoặc book của Card V2 (`lore/book.py`).
- `lore/match.py` so khớp từ khoá tiếng Việt giữ dấu; `lore/select.py` chọn mục đưa vào khối D.
- API ở `api/routes_lore.py`.

## Done when

- [ ] Unit: API mục thế giới: thêm, sửa, bật/tắt, xoá, kiểm dữ liệu với câu lỗi tiếng Việt; mục của tài khoản khác hay card khác trả 404.
- [ ] Unit: nhập `worlds/luc-bac-uyen/world.md` có bước xem trước (dry run); nhập lại lần hai không tạo gì mới; dòng bí mật không bao giờ được nhập.
- [ ] Unit: so khớp từ khoá tiếng Việt giữ dấu, không phân biệt hoa thường, NFC và NFD như nhau.
- [ ] Unit: nhắc từ khoá thì mục vào khối D trong ngân sách; mục 'Chỉ bạn biết' không bao giờ vào prompt của nhân vật; không có mục nào thì prompt giữ nguyên từng byte.
- [ ] Unit: hồ sơ nhân vật chỉ liệt kê tên người và nơi chốn công khai, không lộ nội dung (`summary_only_lists_public_people_and_places`, `worldTeaser`).
- [ ] Bot: mở `#/studio/<id>?section=world` thì thấy phần 'Thế giới'; thêm một mục rồi tải lại trang thì mục vẫn còn, không cần bấm lưu nhân vật.
- [ ] Bot: khi 'Công cụ nâng cao' tắt, chữ hiển thị ở `#/studio/<id>?section=world` và `#/character/<id>` không có 'lore', 'keys', 'token'.
- [ ] Bot: gửi một lượt có từ khoá của một mục thì ngăn 'Cảm xúc & ký ức' có 'Thế giới đã mở khoá' với mục đó và nút 'Xem lúc được nhắc tới lần đầu'.
- [ ] Bot: `#/character/<id>` của nhân vật có mục thế giới hiện phần 'Thế giới' chỉ có tên người / nơi chốn, không có nội dung mục.
- [ ] Model thật: trên gemma4:12b, nhắc từ khoá trong chat thì nhân vật dùng đúng chi tiết của mục; mục 'Chỉ bạn biết' (cùng từ khoá) không bao giờ được nhân vật nói ra và không có trong prompt (kịch bản `f17-the-gioi`).

## Tests

- backend/tests/test_lore_api.py
- backend/tests/test_lore_parse.py
- backend/tests/test_lore_match.py
- backend/tests/test_lore_select.py
- backend/tests/test_lore_prompt.py
- backend/tests/test_lore_e2e.py
- backend/tests/test_lore_migration.py
- frontend/src/pages/studio/loreLogic.test.ts
- frontend/src/pages/chat/loreLogic.test.ts
- frontend/src/pages/character/logic.test.ts
- bot: thêm mục thế giới lưu ngay
- bot: sổ thế giới không có chữ lore, keys, token
- bot: nhắc từ khoá thì mục thế giới mở khoá
- bot: hồ sơ có phần Thế giới chỉ có tên
- model: f17-the-gioi

## Liên quan

- **Code:** [`backend/lyris/lore/parse.py`](../../backend/lyris/lore/parse.py), [`backend/lyris/lore/match.py`](../../backend/lyris/lore/match.py), [`backend/lyris/lore/select.py`](../../backend/lyris/lore/select.py), [`backend/lyris/lore/service.py`](../../backend/lyris/lore/service.py), [`backend/lyris/lore/book.py`](../../backend/lyris/lore/book.py), [`backend/lyris/api/routes_lore.py`](../../backend/lyris/api/routes_lore.py), [`frontend/src/pages/studio/LorebookSection.tsx`](../../frontend/src/pages/studio/LorebookSection.tsx), [`frontend/src/pages/studio/LoreEntryDialog.tsx`](../../frontend/src/pages/studio/LoreEntryDialog.tsx), [`frontend/src/pages/studio/LoreImportDialog.tsx`](../../frontend/src/pages/studio/LoreImportDialog.tsx), [`frontend/src/pages/chat/useStoryLore.ts`](../../frontend/src/pages/chat/useStoryLore.ts), [`worlds/`](../../worlds/)
- **Tài liệu:** [phase4.md](../../docs/phase4.md), [design-impl.md §17](../../docs/design-impl.md)
- **Quyết định:** [the-gioi-cho-nhan-vat](../decisions/the-gioi-cho-nhan-vat.md), [lore-khong-trong-system](../decisions/lore-khong-trong-system.md), [lore-trong-db-theo-card](../decisions/lore-trong-db-theo-card.md)
