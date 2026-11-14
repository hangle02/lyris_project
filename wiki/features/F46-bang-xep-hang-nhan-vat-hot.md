# F46 — Bảng xếp hạng Nhân vật hot

- **Trạng thái:** xem `memory/features.json` · **Phase:** Ra mắt (coin)
- **Giai đoạn:** Đã có
- **Màn hình:** [hot-ranking](../screens/hot-ranking.md) (`#/explore/hot`), [explore](../screens/explore.md) (dải "Nhân vật hot" thay khung nổi bật)

## Là gì

Bảng **"Nhân vật hot"**: 100 nhân vật công khai có nhiều người chơi nhất từ trước tới nay, cập nhật mỗi giờ. Ở đầu Khám phá,
dải "Nhân vật hot" (3 hạng đầu) **thay khung nhân vật nổi bật Hạ Vy** (PO: "bỏ cái hạ vy to to đi, thay bằng bảng xếp hạng").
Bảng là nền của thưởng sáng tác [F44](F44-thuong-sang-tac.md).

## Hoạt động thế nào

- Xếp theo **tổng người chơi** (PO 2C; người chơi như [F44](F44-thuong-sang-tac.md); người chơi đang bị tạm khoá không được đếm, tạm chọn sau rà soát). Bằng nhau: nhân vật đạt số đó sớm hơn đứng trước, rồi id nhỏ hơn. Không có hạng đồng.
- Chỉ có nhân vật gốc đang công khai, người tạo đang hoạt động, có ít nhất 1 người chơi (tạm chọn). Nhân vật mẫu không có trên bảng.
- Cập nhật mỗi giờ (PO 4A): app tính lại khi lần tính cuối cũ hơn 60 phút, lúc có người mở bảng hay mở app (tạm chọn: app không có việc nền theo giờ). Thưởng của F44 được trả trong cùng lần tính.
- `#/explore/hot`: tiêu đề "Nhân vật hot", "Xếp theo tổng số người chơi. Cập nhật mỗi giờ.", "Cập nhật lúc 14:00", danh sách tối đa 100 hàng: hạng, ảnh, tên, "bởi @handle", "{n} người chơi". Chạm một hàng mở hồ sơ nhân vật.
- Khám phá: không còn khung nổi bật. Dưới ô tìm ([F47](F47-tim-nhan-vat.md)) là dải "Nhân vật hot" với 3 hạng đầu và nút "Xem bảng xếp hạng". Dải là lối vào duy nhất của bảng nên luôn có (sau rà soát 2026-11-14): bảng rỗng thì một dòng "Chưa có nhân vật nào trên bảng xếp hạng.", chưa tải được thì chỉ tiêu đề và nút; đang tìm thì dải ẩn.
- Hạ Vy và mọi nhân vật mẫu nằm trong lưới "Nhân vật" như các nhân vật khác.

Kỹ thuật:

- Bảng `hot_board_runs`, `hot_board` (migration chỉ thêm `0014_hot_board.sql`, chép trước mọi `.py`); `backend/lyris/coins/hot.py` (`rank_cards`, `refresh_if_stale`; `CoinService.refresh_hot` đọc "đã cũ chưa" trước, bảng còn mới thì không mở transaction ghi); route `GET /api/explore/hot?limit=<1..100>` → `{updated_at, ranked, items: [{rank, card_id, name, avatar_url, creator_handle, players}]}`; `POST /api/coins/checkin` gọi `refresh_if_stale`.
- Frontend: route `{ name: "hot" }` trong `lib/router.ts`; `pages/explore/HotPage.tsx`, `pages/explore/hotLogic.ts`, hàng dùng chung `pages/explore/HotRows.tsx`; `ExplorePage.tsx` bỏ `Hero`, `featuredTemplate`, `withoutHero`, thêm dải `HotStrip` (đọc `GET /api/explore/hot?limit=3`).
- Bot: `environment/seed-creator-players.py` dựng 12 người chơi rồi tính lại bảng ngay (`hot.compute`, như lần tính mỗi giờ), vì app đã tính bảng lúc bot mở app và chỉ tự tính lại sau 60 phút.
- Thiết kế: [docs/coins.md §5.2](../../docs/coins.md), quyết định [xep-hang-nhan-vat-hot](../decisions/xep-hang-nhan-vat-hot.md), [kham-pha-tim-kiem-bo-khung-noi-bat](../decisions/kham-pha-tim-kiem-bo-khung-noi-bat.md).

## Done when

- [ ] Unit: `rank_cards` xếp theo số dòng `creator_players` giảm dần; hai nhân vật cùng 5 người chơi thì nhân vật có `MAX(qualified_at)` nhỏ hơn đứng trước; vẫn bằng thì `card_id` nhỏ hơn đứng trước; hạng là 1, 2, 3… không trùng.
- [ ] Unit: không có trên bảng: nhân vật riêng tư, bản sao (`story_copy = 1`), nhân vật 0 người chơi, nhân vật của người tạo bị tạm khoá, nhân vật mẫu chưa công khai; có 130 nhân vật đủ điều kiện thì `hot_board` có đúng 100 dòng (hạng 1–100) và `hot_board_runs.ranked = 130`.
- [ ] Unit: `refresh_if_stale` tính lần đầu; gọi lại sau 59 phút (đồng hồ giả) không tính lại (`computed_at` giữ nguyên); sau 61 phút thì tính lại và chỉ còn một dòng `hot_board_runs`; hai lời gọi trong cùng lúc chỉ tạo một lần tính.
- [ ] Unit: đọc bảng còn mới không giữ khoá ghi: `CoinService.hot_board` và `refresh_hot` lúc bảng mới 59 phút không chạy câu `BEGIN`, `SAVEPOINT`, `INSERT`, `UPDATE`, `DELETE` nào (bắt bằng `set_trace_callback`); lúc chưa có bảng hay đã cũ 61 phút thì có `BEGIN` và tính lại.
- [ ] Unit: người chơi bị tạm khoá không được đếm: X có 5 người chơi, chủ máy khoá 2 → `hot_board` có X với 3 người chơi, `progress(X).players = 3`; Y chỉ có 1 người chơi (bị khoá) → không có trên bảng, người tạo Y không có `first_public:` dù Y đã công khai đủ 24 giờ (người tạo X thì có); mở khoá → lần tính sau X có 5, Y có 1 và người tạo Y nhận +50.
- [ ] Unit: `GET /api/explore/hot` trả `{updated_at, ranked, items}`, `limit=3` trả 3 hàng đầu, `limit=0` và `limit=101` trả 422; mỗi hàng chỉ có `rank, card_id, name, avatar_url, creator_handle, players` (không có `account_id`, mô tả, trường bí mật); nhân vật về Riêng tư sau lần tính không còn trong `items`, hạng của nhân vật khác giữ nguyên; chưa đăng nhập thì 401; `test_isolation_sweep.py` phân loại route mới.
- [ ] Unit: migration `0014_hot_board.sql` chỉ có `CREATE TABLE`, `CREATE INDEX` và `INSERT INTO card_public_since` (không `ALTER`, `DROP`, `UPDATE`, `DELETE`); áp lên DB tạm có dữ liệu của 0013 thì số dòng và số dư của `coin_wallets`, `coin_ledger`, `character_cards` không đổi.
- [ ] Unit: `parseRoute("#/explore/hot")` là `{ name: "hot" }` và `routeHref` dựng lại `#/explore/hot` (tab Khám phá vẫn sáng: `tabOf` là `explore`); `hotLogic.ts` dựng "Cập nhật lúc 14:05" từ `updated_at` (giờ máy), "1.200 người chơi" (dấu chấm hàng nghìn), aria-label hàng "Hạng {r}: {tên}, {n} người chơi"; `logic.ts` không còn `featuredTemplate`, `withoutHero`, `heroImageUrl`.
- [ ] Unit: sự kiện `hot_board_viewed` có `from: explore/link`, nằm trong `events.py`, `track.ts` và `tracking-plan.md` (test `test_catalog_is_focused_snake_case_and_documented` của F34 xanh với số sự kiện mới).
- [ ] Bot: ở 390px `#/explore` không có phần tử `section[aria-labelledby=explore-featured]` và không có nút 'Bước vào câu chuyện'; có `section[aria-labelledby=explore-hot]` tiêu đề 'Nhân vật hot' với 1–3 hàng (server giả có nhân vật công khai 12 người chơi) đứng trên mục 'Nhân vật'; thẻ 'Hạ Vy' có trong lưới 'Nhân vật'; bấm 'Xem bảng xếp hạng' thì URL thành `#/explore/hot`.
- [ ] Bot: `#/explore/hot` có tiêu đề 'Nhân vật hot', dòng 'Cập nhật lúc', danh sách `ol[aria-label="Bảng xếp hạng Nhân vật hot"]` có hàng hạng 1 với ảnh đã tải (`img.naturalWidth > 0`), tên nhân vật và chữ '12 người chơi'; bấm hàng đó thì URL thành `#/character/<id>` của đúng nhân vật; nút 'Về Khám phá' đưa về `#/explore`.
- [ ] Unit: `hotLogic.ts` `hotView({items: []})` cho trạng thái rỗng với đúng chữ 'Chưa có nhân vật nào trên bảng xếp hạng.', 'Công khai nhân vật của bạn trong Studio để người khác cùng chơi.' và nút 'Mở Studio' (→ `#/studio`); `hotStripItems` trả 3 hàng đầu (`[]` khi bảng rỗng, chưa tải được hay ô tìm có chữ); `hotStripView` chỉ trả `null` (dải ẩn) khi ô tìm có chữ, bảng rỗng thì `{rows: [], empty: 'Chưa có nhân vật nào trên bảng xếp hạng.'}`, chưa tải được thì `{rows: [], empty: null}` (dải vẫn có tiêu đề và nút); câu thưởng 'Nhân vật của bạn vào top 100, top 50, top 10 thì bạn được thưởng 100, 200, 300 coin. Thưởng top N chỉ có khi bảng có nhân vật của ít nhất N người tạo khác nhau.' chỉ có với thành viên khi coin bật (không có với chủ máy, `LYRIS_COINS=0`).
- [ ] Bot: trước khi có người chơi nào (bảng của bot rỗng, `GET /api/explore/hot` không có hàng), `#/explore` vẫn có `section[aria-labelledby=explore-hot]` tiêu đề 'Nhân vật hot' với dòng 'Chưa có nhân vật nào trên bảng xếp hạng.' và không có hàng; bấm 'Xem bảng xếp hạng' thì URL thành `#/explore/hot`, trang có câu bảng rỗng và nút 'Mở Studio'; bấm 'Mở Studio' thì URL thành `#/studio`.
- [ ] Bot: ở 390px, cả hai theme, `#/explore/hot` và `#/explore` không cuộn ngang (`scrollWidth ≤ innerWidth`); mỗi hàng của bảng và của dải 'Nhân vật hot' cao ít nhất 44px; nút 'Xem bảng xếp hạng' và 'Về Khám phá' có vùng chạm ít nhất 44 × 44px.

## Tests

- backend/tests/test_hot_board.py::test_rank_orders_by_players_then_reach_time_then_id
- backend/tests/test_hot_board.py::test_board_only_public_active_with_player_top_100
- backend/tests/test_hot_board.py::test_refresh_if_stale_once_per_hour
- backend/tests/test_hot_board.py::test_fresh_board_read_takes_no_write_lock
- backend/tests/test_hot_board.py::test_disabled_players_never_count_on_board_or_bonus
- backend/tests/test_hot_board.py::test_hot_api_shape_limit_and_hides_private
- backend/tests/test_hot_board.py::test_migration_0014_is_additive
- backend/tests/test_isolation_sweep.py::test_sweep_covers_every_route
- backend/tests/test_analytics.py::test_catalog_is_focused_snake_case_and_documented
- frontend/src/lib/router.test.ts
- frontend/src/pages/explore/hotLogic.test.ts
- frontend/src/pages/explore/logic.test.ts
- bot: bảng Nhân vật hot rỗng thì Khám phá vẫn có dải và nút Xem bảng xếp hạng, bảng mời Mở Studio
- bot: Khám phá không còn khung nổi bật, có dải Nhân vật hot mở bảng xếp hạng
- bot: bảng Nhân vật hot có hạng, ảnh, tên, số người chơi và mở hồ sơ
- bot: bảng Nhân vật hot và dải ở Khám phá không tràn ngang 390px, hàng và nút chạm được 44px

## Liên quan

- **Tài liệu:** [docs/coins.md §2.2, §5.2](../../docs/coins.md), [DESIGN.md](../../DESIGN.md) trang 2, [design/style.md](../design/style.md)
- **Quyết định:** [xep-hang-nhan-vat-hot](../decisions/xep-hang-nhan-vat-hot.md), [kham-pha-tim-kiem-bo-khung-noi-bat](../decisions/kham-pha-tim-kiem-bo-khung-noi-bat.md), [luoi-o-bang-nhau](../decisions/luoi-o-bang-nhau.md)
- **Tính năng liên quan:** [F44](F44-thuong-sang-tac.md) (thưởng theo bậc), [F22](F22-kham-pha.md) (Khám phá), [F47](F47-tim-nhan-vat.md) (tìm nhân vật), [F23](F23-ho-so-nhan-vat.md) (hồ sơ), [F31](F31-nhan-vat-cong-khai.md)
