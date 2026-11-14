# Khám phá và nhân vật mẫu

- **Trạng thái:** Đã xong · **Phase:** Phase 2b, 4b
- **Màn hình:** [explore](../screens/explore.md)

## Là gì

Trang Khám phá có khung nhân vật nổi bật, chip lọc theo cảm xúc (vibe), lưới nhân vật (card của mình + nhân vật mẫu chưa cài) và phần 'Nhân vật được chia sẻ'. Mọi ô cùng một kích thước.

## Hoạt động thế nào

- Tab Khám phá có khung nhân vật nổi bật ở trên cùng.
- Chip cảm xúc (vibe) lọc lưới nhân vật theo tag.
- Lưới gồm nhân vật của mình và nhân vật mẫu của Lyris. Dưới cùng là 'Nhân vật được chia sẻ' từ tài khoản khác.
- Mọi ô cùng một kích thước.

Kỹ thuật:

- Nhân vật mẫu nằm ở `seed/templates/`, phục vụ qua `api/routes_lyris.py`.
- `pages/explore/logic.ts` chọn nhân vật nổi bật, lọc vibe và bỏ trùng.
- Lưới dùng số cột cố định theo bề rộng màn hình.

## Done when

- [x] Khung nổi bật có ảnh và nút 'Bước vào câu chuyện' (mở hồ sơ kèm sheet).
- [x] Chip vibe lọc lưới theo tag, không phân biệt hoa thường.
- [x] Lưới cố định 2 cột (điện thoại) / 3 cột (máy tính bảng) / 5 cột (máy tính); hàng cuối thiếu ô thì để trống, không kéo giãn.
- [x] Các ô trong cùng một hàng cao bằng nhau.
- [x] Nhân vật ở khung nổi bật không lặp lại trong lưới (trừ khi đang lọc).
- [x] Nhân vật mẫu ghi 'Mẫu của Lyris', card của người dùng ghi 'bởi @handle'; không có dòng nguồn ảnh.

## Liên quan

- **Code:** [`frontend/src/pages/explore/ExplorePage.tsx`](../../frontend/src/pages/explore/ExplorePage.tsx), [`frontend/src/pages/explore/logic.ts`](../../frontend/src/pages/explore/logic.ts), [`backend/lyris/seed/templates/`](../../backend/lyris/seed/templates/), [`backend/lyris/api/routes_lyris.py`](../../backend/lyris/api/routes_lyris.py)
- **Tài liệu:** [design-impl.md §6.4, §16, §18](../../docs/design-impl.md), [DESIGN.md §6](../../DESIGN.md)
- **Quyết định:** [the-kham-pha-nho-lai](../decisions/the-kham-pha-nho-lai.md), [luoi-o-bang-nhau](../decisions/luoi-o-bang-nhau.md)
