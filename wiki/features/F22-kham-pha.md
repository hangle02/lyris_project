# F22 — Khám phá và nhân vật mẫu

- **Trạng thái:** xem `memory/features.json` · **Phase:** Phase 2b, 4b
- **Giai đoạn:** Đã có
- **Màn hình:** [explore](../screens/explore.md)

## Là gì

Trang Khám phá có ô tìm nhân vật ([F47](F47-tim-nhan-vat.md)), dải 'Nhân vật hot' ([F46](F46-bang-xep-hang-nhan-vat-hot.md)), chip lọc theo cảm xúc (vibe), lưới nhân vật (card của mình + nhân vật mẫu chưa cài) và phần 'Nhân vật được chia sẻ'. Mọi ô cùng một kích thước.

> **Đổi 2026-11-14 22:15** (PO: "bỏ cái hạ vy to to đi, thay bằng bảng xếp hạng", [raw](../raw/2026-11-14-f44-bang-xep-hang-tra-loi.md)): **bỏ khung nhân vật nổi bật** (Hạ Vy). Hạ Vy nằm trong lưới như mọi nhân vật mẫu. Chỗ đó giờ là dải 'Nhân vật hot' (F46); ô tìm ở F47. Các dòng Done when về khung nổi bật đã bỏ khỏi trang này; điều "không còn khung nổi bật" được chứng minh ở F46.

## Hoạt động thế nào

- Trên cùng: ô "Tìm nhân vật" (F47), rồi dải "Nhân vật hot" (F46). Không còn khung nhân vật nổi bật.
- Chip cảm xúc (vibe) lọc lưới nhân vật theo tag.
- Lưới gồm nhân vật của mình và nhân vật mẫu của Lyris. Dưới cùng là 'Nhân vật được chia sẻ' từ tài khoản khác.
- Mọi ô cùng một kích thước.

Kỹ thuật:

- Nhân vật mẫu nằm ở `seed/templates/`, phục vụ qua `api/routes_lyris.py`.
- `pages/explore/logic.ts` dựng danh sách, lọc vibe và bỏ trùng (không còn chọn nhân vật nổi bật: `featuredTemplate`, `withoutHero`, `heroImageUrl` đã bỏ khi build F46); lọc theo ô tìm ở `pages/explore/search.ts` (F47).
- Lưới dùng số cột cố định theo bề rộng màn hình.

## Done when

- [ ] Unit: danh sách: card của người dùng trước, mẫu đã cài gộp vào (`buildItems`); mỗi nhân vật đúng một ô, kể cả Hạ Vy (không còn nhân vật nổi bật bị tách khỏi lưới).
- [ ] Unit: lọc theo vibe so sánh sau chuẩn hoá: không phân biệt hoa thường, giữ dấu.
- [ ] Unit: dòng tác giả: 'Mẫu của Lyris' cho mẫu, 'bởi @handle' cho card người dùng; không có dòng nguồn ảnh.
- [ ] Unit: Khám phá liệt kê nhân vật công khai của tài khoản khác.
- [ ] Bot: ở 390px `#/explore` có lưới nhân vật `section[aria-labelledby=explore-all]`; các thẻ rộng bằng nhau, thẻ cùng hàng cao bằng nhau; không cuộn ngang.
- [ ] Bot: lưới có 2 cột ở 390px, 3 cột ở 800px, 5 cột ở 1280px; hàng cuối thiếu ô thì không kéo giãn.
- [ ] Bot: bấm một chip trong nhóm 'Lọc theo cảm xúc' thì chip có `aria-pressed="true"`, bộ đếm thành 'x / tổng' (x > 0), lưới còn đúng x thẻ và chỉ còn nhân vật có tag đó (đủ mọi nhân vật có tag, đối chiếu tag từ `/api/cards`, `/api/templates`); bấm lại thì bộ đếm về tổng và lưới về như cũ (cùng các thẻ, cùng thứ tự).

## Tests

- frontend/src/pages/explore/logic.test.ts
- backend/tests/test_public_cards.py::test_explore_lists_other_accounts_public_cards
- backend/tests/test_lyris_design.py::test_templates_list
- backend/tests/test_lyris_design.py::test_template_install_idempotent
- bot: Khám phá tải xong, thẻ đều nhau, không tràn ngang 390px
- bot: lưới Khám phá 2/3/5 cột
- bot: chip cảm xúc chỉ giữ nhân vật có tag đó, bấm lại thì lưới như cũ

## Liên quan

- **Code:** [`frontend/src/pages/explore/ExplorePage.tsx`](../../frontend/src/pages/explore/ExplorePage.tsx), [`frontend/src/pages/explore/logic.ts`](../../frontend/src/pages/explore/logic.ts), [`backend/lyris/seed/templates/`](../../backend/lyris/seed/templates/), [`backend/lyris/api/routes_lyris.py`](../../backend/lyris/api/routes_lyris.py)
- **Tài liệu:** [design-impl.md §6.4, §16, §18](../../docs/design-impl.md), [DESIGN.md §6](../../DESIGN.md)
- **Quyết định:** [the-kham-pha-nho-lai](../decisions/the-kham-pha-nho-lai.md), [luoi-o-bang-nhau](../decisions/luoi-o-bang-nhau.md), [kham-pha-tim-kiem-bo-khung-noi-bat](../decisions/kham-pha-tim-kiem-bo-khung-noi-bat.md)
- **Tính năng liên quan:** [F46](F46-bang-xep-hang-nhan-vat-hot.md) (dải Nhân vật hot thay khung nổi bật), [F47](F47-tim-nhan-vat.md) (ô tìm)
