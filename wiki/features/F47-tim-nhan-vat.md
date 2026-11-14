# F47 — Tìm nhân vật ở Khám phá

- **Trạng thái:** xem `memory/features.json` · **Phase:** Ra mắt (coin)
- **Giai đoạn:** Đã có
- **Màn hình:** [explore](../screens/explore.md) (ô "Tìm nhân vật" ở đầu trang)

## Là gì

Ô **"Tìm nhân vật"** ở đầu Khám phá (PO: "thiết kế thêm thanh tìm kiếm nữa"). Gõ tên, vai trò, tag hay một chữ trong giới thiệu
là lưới chỉ còn nhân vật khớp. Gõ không dấu vẫn ra ("ha vy" ra "Hạ Vy").

## Hoạt động thế nào

- Tìm trong **mọi nhân vật trên Khám phá**: nhân vật của bạn, nhân vật mẫu của Lyris và nhân vật công khai của người khác ("Nhân vật được chia sẻ") (tạm chọn: cả nhân vật của bạn, vì chúng nằm chung lưới).
- So sánh **không dấu, không phân biệt hoa thường** (bỏ dấu tiếng Việt, "đ" thành "d"), gộp khoảng trắng. Nhiều từ thì nhân vật phải khớp **mọi** từ, ở bất kỳ trường nào (tên, vai trò, tag, giới thiệu). Mỗi từ gõ phải khớp **phần đầu một từ** ("ha" ra "Hạ", "Hải", không ra "thành", "nhà"; tạm chọn sau rà soát 2026-11-14); dấu câu tách từ.
- Lọc sau **250 ms** kể từ lần gõ cuối (debounce). Ô rỗng (hay chỉ có khoảng trắng) là không lọc.
- Tìm cùng lúc với chip cảm xúc: nhân vật phải khớp cả hai. Bộ đếm của mục "Nhân vật" thành "x / tổng".
- Đang tìm thì dải "Nhân vật hot" ([F46](F46-bang-xep-hang-nhan-vat-hot.md)) ẩn; mục "Nhân vật được chia sẻ" chỉ còn ô khớp, không còn ô nào thì mục ẩn.
- Không có kết quả ở cả hai mục: "Không tìm thấy nhân vật nào cho “{chữ đã gõ}”." và nút "Xoá tìm kiếm". Nút "×" trong ô (aria-label "Xoá tìm kiếm") xoá chữ, lưới về như cũ.
- Chữ đã gõ không gửi lên server, không vào sự kiện (chỉ `explore_searched {has_results}`). Không lưu sau khi rời trang (tạm chọn).

Kỹ thuật:

- `frontend/src/pages/explore/search.ts`: `foldVietnamese(text)`, `searchText(item)` (tên, vai trò, tag, giới thiệu đầy đủ; gấp một lần rồi nhớ theo item), `matchesQuery(item, query)`, `filterItems(items, {query, vibe})`; hook `useDebounced(value, 250)` dựng trên lõi thuần `createDebounced` (test bằng `mock.timers`); `createSearchTracker` phát `explore_searched` một lần cho mỗi chuỗi tìm khác nhau.
- `ExploreItem` thêm `about` (giới thiệu đầy đủ cho người đọc, dựng trong `buildItems`, `sharedItems`); `searchText` tính trong `search.ts` để `logic.ts` không phải import ngược `search.ts`. Không thêm API. Lưới vẫn theo [luoi-o-bang-nhau](../decisions/luoi-o-bang-nhau.md).
- Quyết định: [kham-pha-tim-kiem-bo-khung-noi-bat](../decisions/kham-pha-tim-kiem-bo-khung-noi-bat.md).

## Done when

- [ ] Unit: `foldVietnamese("Hạ Vy ĐÀ LẠT  ở  Huế")` là `"ha vy da lat o hue"`; `matchesQuery` của mẫu Hạ Vy đúng với "ha vy", "HẠ VY", "vy", "tiem sach", "da lat" (giới thiệu có "tiệm sách", "Đà Lạt") và sai với "vy khang"; nhiều từ phải khớp mọi từ ("vy da lat" ra Hạ Vy, "vy morwenna" không ra nhân vật nào); mỗi từ khớp phần đầu một từ: "ha" khớp "Hải Đăng" nhưng không khớp nhân vật chỉ có "thành", "nhà" ("thanh", "nha", "lao th" thì khớp), "a" không khớp Hạ Vy; dấu câu tách từ ("da-lat", "vy," vẫn ra Hạ Vy).
- [ ] Unit: `filterItems` tìm trong tên, vai trò, tag và giới thiệu của cả ba loại thẻ (`card`, `template`, `shared`); kết hợp với vibe là phép "và"; chuỗi rỗng hay chỉ khoảng trắng trả đúng danh sách cũ (cùng thứ tự); thứ tự kết quả giữ nguyên thứ tự lưới.
- [ ] Unit: `useDebounced` (đồng hồ giả của `node:test` `mock.timers`) chỉ đổi giá trị sau 250 ms kể từ lần đổi cuối: gõ 5 ký tự cách nhau 100 ms thì chỉ lọc một lần.
- [ ] Unit: sự kiện `explore_searched` chỉ có `has_results: bool` (không có chữ đã gõ), nằm trong `track.ts` và `tracking-plan.md`; phát tối đa một lần cho mỗi chuỗi tìm khác nhau sau debounce.
- [ ] Bot: ở 390px `#/explore` có ô `input[type=search]` placeholder 'Tìm nhân vật', aria-label 'Tìm nhân vật theo tên, tag hoặc giới thiệu', đứng trên dải 'Nhân vật hot' và mục 'Nhân vật'; gõ 'ha vy' (không dấu) thì sau ≤ 1 giây lưới 'Nhân vật' chỉ còn thẻ có tên chứa 'Hạ Vy', bộ đếm là '1 / tổng', dải 'Nhân vật hot' ẩn; bấm nút 'Xoá tìm kiếm' thì ô rỗng, bộ đếm về tổng và lưới về như cũ (cùng các thẻ, cùng thứ tự).
- [ ] Bot: gõ 'zzqxy' thì hiện 'Không tìm thấy nhân vật nào cho “zzqxy”.' và nút 'Xoá tìm kiếm', không còn thẻ nào trong hai lưới; bấm nút thì lưới về như cũ; tìm 'ha vy' khi đang bật một chip cảm xúc mà Hạ Vy không có thì cũng ra trạng thái không có kết quả.
- [ ] Bot: ở 390px, cả hai theme, ô tìm vừa một dòng (placeholder không bị cắt: `scrollWidth ≤ clientWidth` của input), cao ít nhất 44px, nút 'Xoá tìm kiếm' trong ô chạm được 44 × 44px; trang không cuộn ngang.

## Tests

- frontend/src/pages/explore/search.test.ts
- frontend/src/lib/track.test.ts
- backend/tests/test_analytics.py::test_catalog_is_focused_snake_case_and_documented
- bot: tìm 'ha vy' không dấu ra thẻ Hạ Vy, xoá tìm thì lưới như cũ
- bot: tìm không có kết quả thì báo và có nút Xoá tìm kiếm
- bot: ô Tìm nhân vật vừa một dòng 390px, cao 44px, không tràn ngang

## Liên quan

- **Tài liệu:** [DESIGN.md](../../DESIGN.md) trang 2, [design/style.md](../design/style.md), luật chữ trong `environment/rules.md` (placeholder ngắn, nhãn đầy đủ ở `aria-label`)
- **Quyết định:** [kham-pha-tim-kiem-bo-khung-noi-bat](../decisions/kham-pha-tim-kiem-bo-khung-noi-bat.md), [placeholder-ngan](../decisions/placeholder-ngan.md), [luoi-o-bang-nhau](../decisions/luoi-o-bang-nhau.md)
- **Tính năng liên quan:** [F22](F22-kham-pha.md), [F46](F46-bang-xep-hang-nhan-vat-hot.md), [F34](F34-theo-doi-su-kien.md) (sự kiện)
