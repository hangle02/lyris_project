# Sổ thế giới (lorebook)

- **Trạng thái:** Đã xong · **Phase:** Phase 4
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

- [x] Phần 'Thế giới' trong trình sửa nhân vật thêm, sửa, bật/tắt, xoá mục; lưu ngay không cần bấm Lưu nhân vật.
- [x] Nhập `worlds/luc-bac-uyen/world.md` có bước xem trước; nhập lại lần hai báo 'không có gì mới'.
- [x] Nhắc từ khoá thì mục được đưa vào khối D; mục 'Chỉ bạn biết' không bao giờ vào prompt của nhân vật.
- [x] So khớp tiếng Việt giữ dấu, không phân biệt hoa thường (`test_lore_match.py`).
- [x] Ngăn cảm xúc có 'Thế giới đã mở khoá', mục có nút 'Xem lúc được nhắc tới lần đầu'.
- [x] Hồ sơ nhân vật có phần 'Thế giới' với 'Người quanh {tên}' và 'Nơi chốn', không lộ nội dung.
- [x] Trên màn hình không có chữ 'lore', 'keys', 'token' (trừ khi bật công cụ nâng cao).

## Liên quan

- **Code:** [`backend/lyris/lore/parse.py`](../../backend/lyris/lore/parse.py), [`backend/lyris/lore/match.py`](../../backend/lyris/lore/match.py), [`backend/lyris/lore/select.py`](../../backend/lyris/lore/select.py), [`backend/lyris/lore/service.py`](../../backend/lyris/lore/service.py), [`backend/lyris/lore/book.py`](../../backend/lyris/lore/book.py), [`backend/lyris/api/routes_lore.py`](../../backend/lyris/api/routes_lore.py), [`frontend/src/pages/studio/LorebookSection.tsx`](../../frontend/src/pages/studio/LorebookSection.tsx), [`frontend/src/pages/studio/LoreEntryDialog.tsx`](../../frontend/src/pages/studio/LoreEntryDialog.tsx), [`frontend/src/pages/studio/LoreImportDialog.tsx`](../../frontend/src/pages/studio/LoreImportDialog.tsx), [`frontend/src/pages/chat/useStoryLore.ts`](../../frontend/src/pages/chat/useStoryLore.ts), [`worlds/`](../../worlds/)
- **Tài liệu:** [phase4.md](../../docs/phase4.md), [design-impl.md §17](../../docs/design-impl.md)
- **Quyết định:** [the-gioi-cho-nhan-vat](../decisions/the-gioi-cho-nhan-vat.md), [lore-khong-trong-system](../decisions/lore-khong-trong-system.md), [lore-trong-db-theo-card](../decisions/lore-trong-db-theo-card.md)
