# F44 — Thưởng sáng tác theo bảng xếp hạng Nhân vật hot

- **Trạng thái:** xem `memory/features.json` · **Phase:** Ra mắt (coin)
- **Giai đoạn:** Đã có
- **Màn hình:** [card-editor](../screens/card-editor.md) (dòng người chơi và hạng dưới "Công khai"), [coin-wallet](../screens/coin-wallet.md) (dòng thưởng trong lịch sử), [admin](../screens/admin.md) ("Nhật ký"), [hot-ranking](../screens/hot-ranking.md) (câu giới thiệu thưởng)

> **Làm lại 2026-11-14 22:15** (PO chọn 1A 2C 3A 5A, [raw](../raw/2026-11-14-f44-bang-xep-hang-tra-loi.md)): thưởng mốc
> 10/50/100 người chơi (+100/+300/+600) **bị thay hẳn**. Code mới có từ 2026-11-14 (build F44/F46/F47): `creator.py` chỉ
> còn ghi người chơi, thưởng nằm ở `backend/lyris/coins/hot.py`. Bảng xếp hạng là [F46](F46-bang-xep-hang-nhan-vat-hot.md).

## Là gì

Người tạo nhân vật công khai được thưởng coin khi nhân vật vào **top 100 / top 50 / top 10** của bảng **"Nhân vật hot"**:
**+100 / +200 / +300 coin**, mỗi bậc một lần cho mỗi nhân vật, cộng dồn (lên thẳng top 10 nhận đủ 600). Lần đầu có nhân vật
công khai được người khác chơi, tài khoản được **+50 coin** một lần.

## Hoạt động thế nào

- **Người chơi** (giữ như bản cũ): tài khoản khác, không phải người tạo, không phải chủ máy, có story chơi bằng bản sao của nhân vật, có ≥ 3 câu trả lời đã trả coin cộng dồn ở ≥ 2 ngày coin (tạm chọn).
- **Hot** = tổng người chơi từ trước tới nay (PO 2C); người chơi đang bị tạm khoá không được đếm tới khi mở khoá (tạm chọn, sau rà soát). Bảng tính lại mỗi giờ ([F46](F46-bang-xep-hang-nhan-vat-hot.md)); thưởng được trả ngay trong lần tính đó.
- **Bậc** (PO 3A): ở một lần tính, nhân vật hạng `r` đạt bậc N (100, 50, 10) khi `r ≤ N` **và** các nhân vật được xếp hạng thuộc ít nhất N người tạo khác nhau (tạm chọn, chống máy ít người và tự lấp bảng: 1 người chơi không được lên thẳng top 10, một người tạo có 10 nhân vật công khai chỉ tính là 1; bản đầu đếm nhân vật, đổi sau rà soát 2026-11-14). Mỗi bậc một lần cho mỗi nhân vật; rớt rồi lên lại không trả lại.
- **Trần theo người tạo** (tạm chọn): tối đa 600 coin thưởng xếp hạng trong 7 ngày coin gần nhất; vượt thì bậc đó chờ, không mất, trả ở lần tính sau khi có chỗ.
- **Công khai lần đầu** (PO 5A): +50 coin một lần mỗi tài khoản, khi một nhân vật của tài khoản đã công khai liên tục ≥ 24 giờ và có ≥ 1 người chơi. Về Riêng tư thì đếm 24 giờ lại từ đầu.
- Chủ máy không bao giờ nhận coin (nhân vật của chủ máy vẫn được xếp hạng). Coin tắt, người tạo bị khoá, nhân vật đang riêng tư: thưởng chờ.
- Thưởng mốc cũ đã trả giữ nguyên trong sổ và lịch sử ("Hạ Vy đạt 10 người chơi"); không trả mốc nào nữa.
- Người tạo thấy trong trình sửa: "12 người chơi · Hạng 7 Nhân vật hot" và "Bậc thưởng tiếp theo: top 50 (+200 coin)" (bậc tiếp theo theo hạng hiện tại); bảng chưa có nhân vật của đủ N người tạo thì thêm "Thưởng top 10 chỉ có khi bảng có nhân vật của ít nhất 10 người tạo khác nhau (hiện có 1)." Lịch sử ví: "Hạ Vy vào top 10 Nhân vật hot" +300, "Thưởng công khai nhân vật lần đầu" +50.

Kỹ thuật:

- Migration **chỉ thêm** `0014_hot_board.sql` (`card_public_since`, `hot_board_runs`, `hot_board`, `creator_rank_tiers`, `creator_first_public`), chép **trước** mọi `.py` (app của chủ dự án chạy `--reload`, [learned.md](../learned.md)).
- Sổ coin không thêm `kind` (CHECK không sửa được): ghi `kind = 'creator_milestone'` với `idem_key` `rank:<X>:<N>` (`milestone = N`) và `first_public:<account>` (`milestone = NULL`); nhãn theo tiền tố `idem_key`.
- Code: `backend/lyris/coins/hot.py` (`rank_cards`, `compute`, `refresh_if_stale`, `reach_tiers`, `settle_rewards`, `first_public_check`, `sync_public_since`, `progress`); `creator.note_charged` chỉ ghi người chơi; `card_public_since` được ghi/xoá trong `Repo.create_card`, `Repo.update_card` và `reports.unpublish_card` (mọi chỗ đổi Công khai); `CoinService.refresh_hot` (không bao giờ raise) và `first_public`; nhãn ở `hot.reward_label` / `hot.admin_label` (`label` mới trong `GET /api/admin/coins/log`); chữ ở `frontend/src/pages/studio/creatorLogic.ts` (`creatorBlock`). Lỗi khi trả thưởng chỉ cuộn lại dòng lỗi (ghi bậc, mỗi dòng trả bậc, mỗi dòng +50 có SAVEPOINT riêng): bảng vẫn cập nhật, bậc vẫn được ghi, người tạo khác vẫn được trả, dòng lỗi chờ lần tính sau (tạm chọn, [xep-hang-nhan-vat-hot](../decisions/xep-hang-nhan-vat-hot.md)).
- Thiết kế đầy đủ: [docs/coins.md §2.2, §5](../../docs/coins.md). Quyết định: [xep-hang-nhan-vat-hot](../decisions/xep-hang-nhan-vat-hot.md).

## Done when

- [ ] Unit: một thành viên khác có 2 câu trả lời đã trả coin với bản sao của X thì chưa được tính; câu thứ 3 cùng ngày coin vẫn chưa; một câu ở ngày coin sau (đồng hồ giả +1 ngày) thì có đúng một dòng `creator_players (X, người đó)`; 3 câu chia ở hai story bản sao khác nhau của X cũng được cộng dồn.
- [ ] Unit: người tạo X chơi bản sao của chính X và chủ máy chơi X không bao giờ có dòng trong `creator_players`; câu trả lời bị nhả (lỗi, rỗng) không được đếm.
- [ ] Unit: `note_charged` không còn ghi dòng sổ nào: người chơi thứ 10, 50, 100 của X đủ điều kiện thì `coin_ledger` không có dòng `idem_key LIKE 'milestone:%'` mới; dòng `milestone:<X>:10` cũ (ghi bằng `post()`) vẫn hiện trong `GET /api/coins/history` với nhãn "{tên} đạt 10 người chơi".
- [ ] Unit: bảng có 100 nhân vật được xếp hạng của 100 người tạo khác nhau, X lên hạng 7 trong một lần tính → người tạo nhận đúng ba dòng sổ `rank:<X>:100` +100, `rank:<X>:50` +200, `rank:<X>:10` +300 (tổng 600); gọi `settle_rewards` thêm 3 lần, hay tính bảng lại sau 61 phút với X vẫn hạng 7, vẫn chỉ ba dòng; X rớt hạng 120 rồi lên lại hạng 5 không có dòng mới.
- [ ] Unit: bậc top N đếm **người tạo khác nhau**: một người tạo có 12 nhân vật công khai, mỗi nhân vật 1 người chơi (cùng một người chơi) → 12 nhân vật hạng 1–12, `creators = 1`, không có dòng `rank:` và không có `creator_rank_tiers` nào; 21 nhân vật của 9 người tạo, X hạng 1 → không có dòng `rank:` nào; nhân vật của 60 người tạo, X hạng 7 → chỉ có `rank:<X>:50` và `rank:<X>:10` (+500), không có `rank:<X>:100`; khi bảng lên 100 người tạo mà X vẫn hạng ≤ 100 thì `rank:<X>:100` +100 được trả ở lần tính đó, còn 12 nhân vật tự lấp bảng (hạng > 100) vẫn không có bậc nào.
- [ ] Unit: trần 600 coin/7 ngày coin theo người tạo: nhân vật thứ hai của cùng người tạo lên top 10 trong cùng tuần (bảng 100 người tạo) → `creator_rank_tiers` của nó có 3 dòng `outcome = 'waiting'`, không có dòng sổ; đồng hồ giả +7 ngày coin rồi tính bảng → trả đủ 600; thưởng mốc cũ `milestone:` không tính vào trần.
- [ ] Unit: người tạo là chủ máy → nhân vật vẫn có hạng, `creator_rank_tiers.outcome = 'owner'`, không có dòng sổ và không có `first_public`; coin tắt (`LYRIS_COINS=0`) lúc đạt bậc → bậc của thành viên `waiting`, không có dòng sổ; sau đó bật coin lại mà người tạo đang bị tạm khoá, hay X đã về Riêng tư → bậc vẫn `waiting` (người tạo khác thì được trả); mở khoá / công khai lại → trả đủ ở lần tính đầu tiên sau đó (nhân vật riêng tư hay người tạo bị khoá không có trên bảng nên không đạt bậc mới).
- [ ] Unit: thưởng công khai lần đầu: X công khai 23 giờ 59 phút có 1 người chơi → không có `first_public:<người tạo>`; đủ 24 giờ → đúng một dòng +50; nhân vật công khai thứ hai của cùng người tạo không có thêm dòng nào; X về Riêng tư rồi công khai lại thì `card_public_since.since` đổi sang lúc bật lại (24 giờ đếm lại); nhân vật công khai đủ 24 giờ mà 0 người chơi → không trả.
- [ ] Unit: xoá X thì `creator_rank_tiers`, `hot_board`, `card_public_since` của X bị xoá, dòng sổ đã ghi vẫn còn; id X bị dùng lại cho nhân vật mới thì khoá là `rank:<X>:<N>:<uid>` (không `IdemConflict`); trả thưởng lỗi (lỗi DB, `IdemConflict`) lúc tính bảng thì `GET /api/explore/hot` và `POST /api/coins/checkin` vẫn trả 200, không bao giờ 500, và bậc vẫn được ghi `waiting` (trả ở lần tính sau).
- [ ] Unit: một dòng thưởng lỗi không chặn dòng khác: ghi sổ lỗi cho mọi dòng thưởng của người tạo A (bậc và +50) thì trong cùng lần tính người tạo B vẫn được trả đủ 600 và +50, bậc của A được ghi `waiting`, A không có dòng sổ; hết lỗi thì lần tính sau trả đủ 600 và +50 cho A.
- [ ] Unit: `GET /api/cards/{id}` của chủ nhân vật công khai có `creator: {players, rank, next_tier, next_reward, waiting_coins, board_creators}` (X hạng 1 trên bảng chỉ có nhân vật của 1 người tạo → `next_tier: 10`, `next_reward: 300`, `board_creators: 1`, chưa có bậc nào; X hạng 60 trên bảng 100 người tạo, đã nhận top 100 → `next_tier: 50`, `next_reward: 200`, `board_creators: 100`; đạt đủ → `next_tier: null`; chủ máy → `next_reward: null`); người khác gọi không có khoá `creator`; `GET /api/coins/history` có nhãn "{tên} vào top 10 Nhân vật hot" và "Thưởng công khai nhân vật lần đầu"; `GET /api/admin/coins/log` có "Thưởng xếp hạng top 10" và "Thưởng công khai lần đầu"; sự kiện `creator_rank_reached` có `tier` 100/50/10 và `paid`.
- [ ] Unit: `creatorLogic.ts` dựng đúng chữ "{n} người chơi · Hạng {r} Nhân vật hot", "{n} người chơi · Chưa có trên bảng Nhân vật hot", "Bậc thưởng tiếp theo: top {N} (+{c} coin)", "Bậc tiếp theo: top {N}" (không có coin), "Đã nhận đủ thưởng xếp hạng", "Thưởng đang chờ: +{w} coin (tối đa 600 coin mỗi 7 ngày)", và "Thưởng top {N} chỉ có khi bảng có nhân vật của ít nhất {N} người tạo khác nhau (hiện có {k})." chỉ khi có coin, còn bậc chưa đạt và `board_creators < N`; không còn chữ "Mốc tiếp theo".
- [ ] Bot: người tạo mở trình sửa `#/studio/<id>` của nhân vật công khai có sẵn 12 người chơi (server giả, `environment/seed-creator-players.py`; script tính lại bảng ngay sau khi dựng người chơi, như lần tính mỗi giờ, vì app đã tính bảng lúc bot mở app) thấy trong phần 'Cơ bản' dòng có '12 người chơi' và 'Hạng 1 Nhân vật hot', dòng 'Bậc thưởng tiếp theo: top 10 (+300 coin)' và 'Thưởng top 10 chỉ có khi bảng có nhân vật của ít nhất 10 người tạo khác nhau (hiện có 1).' (bảng của bot chỉ có nhân vật của 1 người tạo); không có chữ 'Mốc tiếp theo'; nhân vật riêng tư không có dòng này.

## Tests

- backend/tests/test_coins_creator.py::test_player_counts_after_3_charged_replies
- backend/tests/test_coins_creator.py::test_creator_owner_and_released_replies_never_count
- backend/tests/test_creator_rank.py::test_milestones_no_longer_paid_old_rows_keep_label
- backend/tests/test_creator_rank.py::test_rank_tiers_pay_100_200_300_once_cumulative
- backend/tests/test_creator_rank.py::test_tier_needs_board_of_at_least_n_creators
- backend/tests/test_creator_rank.py::test_rank_rewards_capped_600_per_7_days_wait_not_lost
- backend/tests/test_creator_rank.py::test_owner_coins_off_disabled_private_tiers_wait
- backend/tests/test_creator_rank.py::test_first_public_bonus_50_after_24h_with_player_once
- backend/tests/test_creator_rank.py::test_deleted_or_reused_card_and_settle_failure_never_500
- backend/tests/test_creator_rank.py::test_one_failed_reward_never_blocks_other_rewards
- backend/tests/test_creator_rank.py::test_card_api_history_admin_log_and_event_labels
- frontend/src/pages/studio/creatorLogic.test.ts
- bot: trình sửa nhân vật công khai có số người chơi, hạng Nhân vật hot và điều kiện bậc thưởng

## Ngoài Done when

Không chặn ✅.

- Thử tay với ≥ 10 nhân vật công khai thật có người chơi: cần nhiều mã mời và nhiều người; unit đã kiểm bằng DB tạm.

## Liên quan

- **Tài liệu:** [docs/coins.md §2.2, §5](../../docs/coins.md), [auth.md §4.3](../../docs/auth.md) (bản sao nhân vật công khai)
- **Quyết định:** [xep-hang-nhan-vat-hot](../decisions/xep-hang-nhan-vat-hot.md) (thay [moc-nguoi-choi-sang-tac](../decisions/moc-nguoi-choi-sang-tac.md)), [coin-f44-khi-build](../decisions/coin-f44-khi-build.md) (phần đếm người chơi còn đúng), [ban-sao-nhan-vat-cong-khai](../decisions/ban-sao-nhan-vat-cong-khai.md)
- **Tính năng liên quan:** [F46](F46-bang-xep-hang-nhan-vat-hot.md) (bảng xếp hạng), [F31](F31-nhan-vat-cong-khai.md), [F35](F35-quyen-rieng-tu-va-bao-cao.md) (ẩn nhân vật bị báo cáo), [F42](F42-vi-coin.md), [F43](F43-nap-coin.md) ("Nhật ký")
