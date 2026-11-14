# F42 — Ví coin và tiêu coin khi chat

- **Trạng thái:** xem `memory/features.json` · **Phase:** Ra mắt (coin)
- **Giai đoạn:** Đã có
- **Màn hình:** [coin-wallet](../screens/coin-wallet.md), [hub](../screens/hub.md) (chip coin), [account-sheet](../screens/account-sheet.md), [chat-story](../screens/chat-story.md) và [chat-dm](../screens/chat-dm.md) (ô nhập khi hết coin), [card-editor](../screens/card-editor.md) (chat thử)

## Là gì

Mỗi thành viên có một ví coin. Chủ dự án chốt: mỗi lượt tốn 6 coin, tài khoản mới được 300 coin, mỗi ngày đăng nhập được thêm 60 coin. Kế hoạch hiểu "một lượt" là một câu trả lời của nhân vật được sinh ra, nên "Trả lời" sau lỗi, "Tạo lại câu trả lời" và chat thử ở Studio cũng tốn 6 (tạm chọn, đã hỏi PO). Hết coin thì ô nhập bị khoá, có nút "Nạp coin" và "Nhiệm vụ". Chủ máy không bao giờ tốn coin.

## Hoạt động thế nào

- Thành viên thấy số coin trên một chip nhỏ ở thanh đầu (Tương tác, Khám phá, Studio) và trong sheet Tài khoản. Chạm chip mở "Ví coin" (`#/coins`): số dư, lịch sử, nút "Nạp coin" và "Nhiệm vụ". Header màn chat không có chip (tạm chọn).
- Gửi một lượt (Story hay DM): 6 coin được giữ chỗ trước khi nhân vật viết. Có chữ thì trừ 6. Lỗi, máy bận quá lâu, hay dừng trước chữ đầu tiên thì không mất coin.
- "Trả lời" sau lỗi, "Tạo lại câu trả lời", chat thử ở Studio: cũng 6 mỗi câu trả lời (PO chốt 2026-11-14). Chat thử mà miễn phí thì dán thẻ bất kỳ vào Studio là chat được mãi không tốn coin.
- Bấm "Dừng" khi nhân vật đã viết được một phần: vẫn trừ 6 (tạm chọn).
- Không đủ 6 coin: ô nhập khoá, khối "Bạn đã hết coin" với "Nạp coin" và "Nhiệm vụ". Chữ đang gõ được giữ. Có coin lại thì ô nhập tự mở, không cần tải lại.
- Mọi thành viên (tạo bằng mã mời hay cách khác) có ví và +300. Mở app lần đầu mỗi ngày (giờ Việt Nam): +60, hiện "+60 coin cho hôm nay". Ngày đầu tiên: 300 + 60 = 360 (PO chốt 2026-11-14).
- Chủ máy: không có chip, không bị trừ; sheet Tài khoản ghi "Tài khoản quản lý không tốn coin."
- "Nhận gợi ý" và "AI viết nháp" không tốn coin (PO chốt 2026-11-14).

Kỹ thuật:

- Migration `0012_coins.sql`: `coin_wallets` (số dư), `coin_ledger` (sổ chỉ thêm, khoá chống trùng `idem_key`), `coin_holds` (giữ chỗ, mỗi tài khoản tối đa một). Trigger chỉ thêm chừa `actor_id` (để `ON DELETE SET NULL` chạy được) và chỉ cho `actor_id` thành NULL.
- Module mới `backend/lyris/coins/`. `ChatService.__init__(…, coins: CoinService | None = None)`: `None` = không tính coin, test cũ không phải sửa. Giữ chỗ sau vé cổng sinh, trước khi lưu lượt người chơi; `charge` trong cùng `repo.transaction()` với `_persist`/`_save_aborted`, không bao giờ làm mất câu trả lời.
- `auth/store.insert_member` gọi `coins.open_wallet` (ví + 300) cùng transaction, nên server giả của bot và fixture cũng có ví. Ví thiếu thì tự tạo ví 0.
- Hết coin: exception `CoinsRequired` → HTTP 402 `coins_required` ở 4 route (gửi, trả lời, tạo lại, chat thử). `LYRIS_COINS=0` (hoặc tên cũ `NORA_COINS`) tắt hẳn coin.
- Nhả giữ chỗ lúc khởi động chỉ chạy trong `lifespan` của app, không trong CLI hay script. Trong lúc chạy, `CoinService` nhớ giữ chỗ nào còn một lượt sinh đang dùng; giữ chỗ `held` không còn ai dùng (nhả lỗi, lưu lỗi) được nhả (`error`) ở lần giữ chỗ kế tiếp của tài khoản đó. Lưu lỗi thì nhả theo DB, không tin cờ trong bộ nhớ.
- Dừng chỉ trừ coin khi người chơi đã nhận ít nhất một `delta` có chữ (giống chat thử).
- Migration `0013_coin_ledger_no_delete.sql`: sổ coin chặn cả `DELETE` (trừ cascade khi xoá tài khoản). Tên nhân vật trong lịch sử ví chỉ lấy từ story/card của chính tài khoản.
- Thiết kế đầy đủ: [docs/coins.md](../../docs/coins.md) §1–§3, §7–§12.
- Code: `backend/lyris/coins/` (`clock`, `errors`, `ledger`, `holds`, `wallet`), `backend/lyris/api/routes_coins.py`
  (`/api/coins/wallet|checkin|history` và `POST /api/admin/accounts/{id}/coins` mà bot dùng để đưa `@hetcoin` về 0),
  `backend/lyris/db/migrations/0012_coins.sql`; giao diện `frontend/src/lib/coins.ts`, `lib/coinCopy.ts`,
  `hooks/useWallet.ts`, `pages/coins/WalletPage.tsx`, `components/CoinsOutBlock.tsx`. Cách làm chi tiết và các điểm tạm
  chọn khi build: [coin-f42-khi-build](../decisions/coin-f42-khi-build.md).

## Done when

- [ ] Unit: migration `0012_coins.sql` tạo `coin_wallets`, `coin_ledger`, `coin_holds`; `UPDATE` cột `delta` hay `actor_id = 5` trên `coin_ledger` bị trigger chặn; sau 200 thao tác ngẫu nhiên `coin_wallets.balance` bằng tổng `delta` trong sổ và không bao giờ < 0; ghi lại cùng `idem_key` cùng nội dung không cộng lần hai, khác `delta` thì `IdemConflict`.
- [ ] Unit: tạo tài khoản bằng mã mời (`POST /api/auth/signup`) và gọi thẳng `auth/store.insert_member` đều cho đúng một dòng `coin_wallets` và một dòng `signup:<id>` +300, kể cả khi `LYRIS_COINS=0`; `post()` cho tài khoản chưa có ví tự tạo ví 0 thay vì lỗi; migration cho mỗi thành viên có từ trước +300 (`backfill_grant`); chủ máy không có dòng nào trong `coin_ledger`.
- [ ] Unit: `POST /api/coins/checkin` cộng 60 coin một lần mỗi ngày giờ Việt Nam (UTC+7): gọi lúc 16:59Z rồi 17:00Z cùng ngày UTC là hai ngày coin (2 lần +60); gọi lại cùng ngày coin trả `granted: false`; `POST /api/auth/login` cùng ngày không cộng thêm; thành viên vừa tạo gọi checkin cùng ngày có số dư 360.
- [ ] Unit: gửi lượt, `POST /api/stories/{id}/reply` và `POST /api/messages/{id}/regenerate` ở cả `mode` story và dm, và `POST /api/cards/test-chat`, mỗi câu trả lời có chữ trừ đúng 6 coin (một dòng `kind = 'chat'`, `idem_key = chat:<hold_id>`; chat thử có giữ chỗ `mode = 'test'`, `story_id` NULL).
- [ ] Unit: lỗi model, câu trả lời rỗng, lưu lỗi, chờ quá 120 giây, đóng kết nối trước sự kiện `delta` đầu tiên, `InvalidOperation` khi chuẩn bị → giữ chỗ `released` đúng lý do, số dư không đổi, không có dòng sổ; đóng kết nối sau khi đã có `delta` → trừ 6.
- [ ] Unit: dừng khi người chơi chưa nhận `delta` có chữ nào (mẩu "[Thought…" còn nằm trong parser) → giữ chỗ `released` lý do `cancelled`, số dư không đổi, không có dòng sổ.
- [ ] Unit: giữ chỗ bị kẹt `held` (nhả lỗi "database is locked"; hay transaction lưu câu trả lời bị cuộn lại sau khi `charge` đã đánh dấu trong bộ nhớ) không chặn lượt sau: "Trả lời" và gửi tiếp chạy được ngay, không cần khởi động lại app; giữ chỗ kẹt thành `released` (`error` / `save_failed`), không có dòng sổ thừa, số dư đúng.
- [ ] Unit: `DELETE` trực tiếp trên `coin_ledger` bị trigger chặn (migration `0013_coin_ledger_no_delete.sql`), số dư vẫn bằng tổng sổ; xoá tài khoản vẫn xoá mọi dòng sổ của tài khoản đó (cascade).
- [ ] Unit: lịch sử ví và "Tải dữ liệu của tôi" chỉ lấy tên nhân vật từ story/card của CHÍNH tài khoản đó: id story hay card đã xoá được dùng lại cho nhân vật riêng tư của thành viên khác thì nhãn ghi "nhân vật", không bao giờ hiện tên của người khác.
- [ ] Unit: giữ chỗ còn `held` được nhả với lý do `restart` khi `lifespan` của app khởi động (sự kiện `coins_released` phát qua `emit_detached`); mở DB bằng `migrate()` hay `lyris.auth.cli` không nhả giữ chỗ nào.
- [ ] Unit: `charge` của một giữ chỗ `held` luôn ghi được dòng sổ và câu trả lời luôn được lưu, kể cả khi trong lúc sinh số dư bị trừ tay xuống mức thấp nhất cho phép; `ChatService` dựng không có `coins` (`None`) thì không tạo giữ chỗ nào.
- [ ] Unit: thành viên còn dưới 6 coin dùng được: bốn route gửi/trả lời/tạo lại/chat thử trả HTTP 402 `{code: "coins_required", detail: "Bạn đã hết coin. Mỗi câu trả lời cần 6 coin."}` trước byte SSE đầu tiên, lượt người chơi không được lưu (`active_messages` không đổi).
- [ ] Unit: thành viên còn đúng 6 coin, hai request gửi cùng lúc ở hai story: một request chạy, request kia 409 hoặc 402; số dư cuối là 0, không âm.
- [ ] Unit: chủ máy gửi 10 lượt và 10 câu chat thử thì không có `coin_holds` nào, số dư không đổi, `GET /api/coins/wallet` trả `unlimited: true`; với `LYRIS_COINS=0` thành viên gửi lượt cũng không bị trừ và wallet trả `enabled: false`; `NORA_COINS=0` khi chưa đặt `LYRIS_COINS` cũng tắt coin.
- [ ] Unit: `POST /api/stories/{id}/suggestions` và `POST /api/cards/draft` không tạo giữ chỗ hay dòng sổ.
- [ ] Unit: `GET /api/coins/history` chỉ trả dòng của tài khoản đang đăng nhập, 30 dòng mỗi trang, có `label` tiếng Việt theo bảng chữ của [docs/coins.md §10.5](../../docs/coins.md) (chat thử: "Chat thử ở Studio"); `groupHistory()` ở frontend gộp các dòng `chat` liền nhau cùng story cùng ngày thành "{k} câu trả lời của {tên}"; `formatCoins(1200)` = "1.200 coin".
- [ ] Unit: `coins.test.ts`: `composerCoinLock({available: 4})` khoá ô nhập và `actionLock` của "Tạo lại câu trả lời" trả lý do "Cần 6 coin để tạo lại."; kho ví làm mới thành `available: 6` thì `composerCoinLock` mở, không cần tải lại trang; chủ máy (`unlimited: true`) không bao giờ bị khoá; mọi chuỗi trong `lib/coinCopy.ts` không có "chủ máy", "token", "credits", "model", "Ollama".
- [ ] Unit: sự kiện `coins_spent`, `coins_released`, `coins_insufficient`, `coins_granted`, `wallet_viewed` có trong `events.py`, `track.ts` và `tracking-plan.md` §4, chỉ có thuộc tính enum/bool/số, `coins_granted.source` không có `backfill`; "Tải dữ liệu của tôi" có `coins.balance` và `coins.ledger`; xoá tài khoản không còn dòng nào của tài khoản đó trong mọi bảng coin; xoá một tài khoản đang là `actor_id` của dòng sổ người khác thì xoá được và dòng đó còn, `actor_id` thành NULL.
- [ ] Unit: `docs/legal/terms.md` có mục "Coin" ở cả phần tiếng Việt và "## English" (không đổi ra tiền, không chuyển nhượng, mất khi xoá tài khoản, chế độ thử không bán coin, mã nạp được tặng không bán, coin chế độ thử khi ra mắt); `docs/legal/privacy.md` nhắc sổ coin ở cả hai ngôn ngữ; `LEGAL_VERSION` đổi nên tài khoản cũ (kể cả chủ máy) thấy màn đồng ý một lần.
- [ ] Bot: thành viên ở `#/` thấy nút có aria-label dạng 'Coin: <số>. Mở ví coin' trên header; bấm thì sang `#/coins` có tiêu đề 'Ví coin', cùng số dư, nút 'Nạp coin', 'Nhiệm vụ' và mục 'Lịch sử' có dòng 'Quà tạo tài khoản'; 390px không cuộn ngang.
- [ ] Bot: thành viên `@coinmoi` (server giả, chưa checkin) đăng nhập và mở `#/` lần đầu thấy thông báo '+60 coin cho hôm nay'; số dư ở `#/coins` là 360.
- [ ] Bot: thành viên gửi một lượt ở `#/chat/<id>` (LLM giả) thì số dư ở `#/coins` giảm đúng 6.
- [ ] Bot: tài khoản `@hetcoin` (0 coin, server giả) mở story chế độ Story ở `#/chat/<id>`: ô nhập có `disabled`, có chữ 'Bạn đã hết coin', nút 'Nạp coin' mở `#/coins/top-up`, nút 'Nhiệm vụ' mở `#/missions`; 390px không cuộn ngang.
- [ ] Bot: `@hetcoin` mở story DM ở `#/chat/<id>`: ô có aria-label của DM có `disabled`, có chữ 'Bạn đã hết coin' và hai nút 'Nạp coin', 'Nhiệm vụ'; 390px không cuộn ngang.
- [ ] Bot: sheet Tài khoản của thành viên có hàng 'Coin' với số dư và nút 'Mở ví coin'; của chủ máy có 'Tài khoản quản lý không tốn coin.' và header của chủ máy không có nút 'Coin: …'.

## Tests

- backend/tests/test_coins_wallet.py::test_migration_0012_ledger_append_only_and_balance_matches_sum
- backend/tests/test_coins_wallet.py::test_idem_key_never_posts_twice_conflict_on_other_payload
- backend/tests/test_coins_wallet.py::test_every_member_creation_path_opens_wallet_with_300
- backend/tests/test_coins_wallet.py::test_missing_wallet_is_created_not_error
- backend/tests/test_coins_wallet.py::test_signup_grants_300_once_owner_gets_nothing
- backend/tests/test_coins_wallet.py::test_existing_members_get_backfill_grant
- backend/tests/test_coins_wallet.py::test_daily_checkin_once_per_vietnam_day
- backend/tests/test_coins_wallet.py::test_first_day_is_300_plus_60
- backend/tests/test_coins_wallet.py::test_owner_unlimited_and_coins_off_flag
- backend/tests/test_coins_chat.py::test_each_saved_reply_costs_6_story_dm_retry_regenerate_test_chat
- backend/tests/test_coins_chat.py::test_no_text_releases_hold
- backend/tests/test_coins_chat.py::test_stop_after_first_delta_charges
- backend/tests/test_coins_chat.py::test_stop_before_visible_text_releases_hold
- backend/tests/test_coins_chat.py::test_stuck_hold_never_blocks_next_turn
- backend/tests/test_coins_wallet.py::test_ledger_rows_cannot_be_deleted_only_cascade_with_account
- backend/tests/test_coins_api.py::test_history_label_never_shows_other_accounts_card_name
- backend/tests/test_coins_chat.py::test_open_holds_released_only_in_app_lifespan
- backend/tests/test_coins_chat.py::test_charge_of_held_hold_never_loses_reply
- backend/tests/test_coins_chat.py::test_chat_service_without_coins_never_holds
- backend/tests/test_coins_chat.py::test_out_of_coins_402_before_user_turn_saved
- backend/tests/test_coins_chat.py::test_two_tabs_cannot_overspend
- backend/tests/test_coins_chat.py::test_suggestions_and_draft_are_free
- backend/tests/test_coins_api.py::test_history_is_own_paged_and_labelled
- backend/tests/test_coins_api.py::test_coin_events_follow_the_strict_schema
- backend/tests/test_coins_api.py::test_export_has_coins_and_delete_removes_coin_rows
- backend/tests/test_coins_api.py::test_terms_have_coin_section_and_version_bumped
- frontend/src/lib/coins.test.ts
- bot: chip coin trên header mở Ví coin
- bot: mở app lần đầu trong ngày được +60 coin
- bot: gửi một lượt thì ví giảm đúng 6 coin
- bot: hết coin thì ô nhập khoá, có Nạp coin và Nhiệm vụ
- bot: hết coin thì ô nhập DM cũng khoá
- bot: sheet Tài khoản có số coin, chủ máy không tốn coin

## Ngoài Done when

Không chặn ✅ (thử tay hoặc còn là kế hoạch).

- Thử tay trên iPhone 390px, hai theme: chip không chen mất nút đổi theme; khối "Bạn đã hết coin" không che bàn phím.

## Liên quan

- **Tài liệu:** [docs/coins.md](../../docs/coins.md)
- **Quyết định:** [giu-cho-coin-truoc-khi-sinh](../decisions/giu-cho-coin-truoc-khi-sinh.md), [chu-may-khong-ton-coin](../decisions/chu-may-khong-ton-coin.md)
- **Lời gốc:** [raw/2026-11-14-coin.md](../raw/2026-11-14-coin.md), [raw/2026-11-14-coin-tra-loi.md](../raw/2026-11-14-coin-tra-loi.md)
- **Tính năng liên quan:** [F29](F29-dang-nhap.md) (tạo tài khoản), [F32](F32-dung-chung-may.md) (cổng sinh), [F34](F34-theo-doi-su-kien.md) (sự kiện), [F35](F35-quyen-rieng-tu-va-bao-cao.md) (Điều khoản, xuất và xoá dữ liệu), [F43](F43-nap-coin.md), [F45](F45-nhiem-vu-ngay.md)
