# F22 — Khám phá và nhân vật mẫu

- **Trạng thái:** xem `memory/features.json` · **Phase:** Phase 2b, 4b
- **Giai đoạn:** Đã có
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

- [ ] Unit: danh sách: card của người dùng trước, mẫu đã cài gộp vào; nhân vật nổi bật (mặc định Hạ Vy) không lặp lại trong lưới trừ khi đang lọc.
- [ ] Unit: lọc theo vibe so sánh sau chuẩn hoá: không phân biệt hoa thường, giữ dấu.
- [ ] Unit: dòng tác giả: 'Mẫu của Lyris' cho mẫu, 'bởi @handle' cho card người dùng; không có dòng nguồn ảnh.
- [ ] Unit: Khám phá liệt kê nhân vật công khai của tài khoản khác.
- [ ] Bot: ở 390px `#/explore` có khung nổi bật và lưới nhân vật; các thẻ rộng bằng nhau, thẻ cùng hàng cao bằng nhau; không cuộn ngang.
- [ ] Bot: khi không lọc, nhân vật trong khung nổi bật không xuất hiện lại trong lưới.
- [ ] Bot: lưới có 2 cột ở 390px, 3 cột ở 800px, 5 cột ở 1280px; hàng cuối thiếu ô thì không kéo giãn.
- [ ] Bot: bấm một chip trong nhóm 'Lọc theo cảm xúc' thì chip có `aria-pressed="true"`, bộ đếm thành 'x / tổng' (x > 0), lưới còn đúng x thẻ và chỉ còn nhân vật có tag đó (đủ mọi nhân vật có tag, đối chiếu tag từ `/api/cards`, `/api/templates`); bấm lại thì bộ đếm về tổng và lưới về như cũ (cùng các thẻ, cùng thứ tự).

## Tests

- frontend/src/pages/explore/logic.test.ts
- backend/tests/test_public_cards.py::test_explore_lists_other_accounts_public_cards
- backend/tests/test_lyris_design.py::test_featured_template_is_ha_vy
- backend/tests/test_lyris_design.py::test_templates_list
- backend/tests/test_lyris_design.py::test_template_install_idempotent
- bot: Khám phá tải xong, thẻ đều nhau, không tràn ngang 390px
- bot: nhân vật nổi bật không lặp trong lưới
- bot: lưới Khám phá 2/3/5 cột
- bot: chip cảm xúc chỉ giữ nhân vật có tag đó, bấm lại thì lưới như cũ

## Liên quan

- **Code:** [`frontend/src/pages/explore/ExplorePage.tsx`](../../frontend/src/pages/explore/ExplorePage.tsx), [`frontend/src/pages/explore/logic.ts`](../../frontend/src/pages/explore/logic.ts), [`backend/lyris/seed/templates/`](../../backend/lyris/seed/templates/), [`backend/lyris/api/routes_lyris.py`](../../backend/lyris/api/routes_lyris.py)
- **Tài liệu:** [design-impl.md §6.4, §16, §18](../../docs/design-impl.md), [DESIGN.md §6](../../DESIGN.md)
- **Quyết định:** [the-kham-pha-nho-lai](../decisions/the-kham-pha-nho-lai.md), [luoi-o-bang-nhau](../decisions/luoi-o-bang-nhau.md)
