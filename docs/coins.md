# Coin: ví, tiêu coin khi chat, nạp coin (chế độ thử), thưởng sáng tác, nhiệm vụ ngày

> F42, F43, F44 và F45 đã có code (2026-11-14; điểm tạm chọn khi build: [coin-f42-khi-build](../wiki/decisions/coin-f42-khi-build.md),
> [coin-f43-khi-build](../wiki/decisions/coin-f43-khi-build.md), [coin-f45-khi-build](../wiki/decisions/coin-f45-khi-build.md),
> [coin-f44-khi-build](../wiki/decisions/coin-f44-khi-build.md)). Tính năng: [F42](../wiki/features/F42-vi-coin.md) (ví và tiêu coin), [F43](../wiki/features/F43-nap-coin.md)
> (nạp coin, chế độ thử), [F44](../wiki/features/F44-thuong-sang-tac.md) (thưởng sáng tác theo bảng xếp hạng: **làm lại**
> 2026-11-14 22:15, đã có code), [F45](../wiki/features/F45-nhiem-vu-ngay.md) (nhiệm vụ ngày), bảng xếp hạng
> [F46](../wiki/features/F46-bang-xep-hang-nhan-vat-hot.md) và tìm nhân vật [F47](../wiki/features/F47-tim-nhan-vat.md) (đã có code). Lời chủ dự án:
> [raw/2026-11-14-coin.md](../wiki/raw/2026-11-14-coin.md), [raw/2026-11-14-coin-tra-loi.md](../wiki/raw/2026-11-14-coin-tra-loi.md),
> [raw/2026-11-14-f44-bang-xep-hang.md](../wiki/raw/2026-11-14-f44-bang-xep-hang.md),
> [raw/2026-11-14-f44-bang-xep-hang-tra-loi.md](../wiki/raw/2026-11-14-f44-bang-xep-hang-tra-loi.md).
> Phần AI tự chọn ghi **(tạm chọn)**; câu hỏi mở nằm ở `memory/po-questions.md`.

## 0. Quyết định của chủ dự án (đã chốt 2026-11-14)

| Câu hỏi | Trả lời |
|---|---|
| Giá và số dư | **Mỗi lượt tốn 6 coin** (nguyên văn). Tài khoản mới được **300 coin**. Mỗi ngày đăng nhập được **+60 coin**. Kế hoạch hiểu "một lượt" là một câu trả lời của nhân vật được sinh ra, nên "Trả lời" sau lỗi, "Tạo lại câu trả lời" và chat thử ở Studio cũng tốn 6 **(tạm chọn, §3.1, đã hỏi PO)**. |
| Nạp tiền | Màn **"Nạp coin"** có các gói giá, nhưng ở **chế độ thử**: người quản lý (chủ máy) tạo **mã nạp** hoặc cộng coin tay cho thành viên. Cổng thanh toán thật chỉ nối khi ra mắt. |
| Thưởng sáng tác | **Đổi 2026-11-14 22:15** (thay hẳn thưởng mốc 10/50/100 người chơi): nhân vật công khai vào **top 100 / top 50 / top 10** của bảng **"Nhân vật hot"** thì người tạo được **+100 / +200 / +300 coin**, mỗi bậc một lần cho mỗi nhân vật, cộng dồn (lên thẳng top 10 nhận đủ 600). "Hot" = **tổng người chơi từ trước tới nay**. Bảng ở Khám phá `#/explore/hot`, top 100, cập nhật mỗi giờ. Công khai nhân vật lần đầu: **+50 coin** một lần mỗi tài khoản, khi nhân vật đã công khai đủ 24 giờ và có ít nhất 1 người chơi khác. (§5) |
| Nhiệm vụ | Nhiệm vụ ngày, tối đa **30 coin/ngày**: xem quảng cáo **+5** (tối đa 3 lần/ngày, quảng cáo giả 15 giây), trò chuyện với **3 nhân vật khác nhau +10**, gửi **20 lượt +5**. |
| Hết coin | Ô nhập bị khoá, câu **"Bạn đã hết coin"** với nút **"Nạp coin"** và **"Nhiệm vụ"**. **Chủ máy không tốn coin.** Số coin hiện ở **Tài khoản** và một **chip nhỏ trên thanh đầu**. |

Mọi con số dưới đây không ghi "(tạm chọn)" là của chủ dự án.

## 1. Khái niệm

- **Coin**: đơn vị ảo chỉ dùng trong Lyris. Không phải tiền, không đổi ra tiền, không chuyển cho người khác (§12).
- **Ví**: mỗi tài khoản một số dư (số nguyên ≥ 0).
- **Sổ coin** (`coin_ledger`): mỗi lần số dư đổi là một dòng, **chỉ thêm, không sửa**. Số dư trong ví luôn bằng tổng các dòng.
- **Giữ chỗ** (`coin_holds`): 6 coin được "giữ" trước khi nhân vật bắt đầu viết. Có chữ thì giữ chỗ thành một dòng trừ 6 trong
  sổ; không có chữ thì nhả, sổ không có dòng nào (lịch sử của người dùng không bị rối bởi lượt lỗi).
- **Số coin dùng được** = số dư − coin đang giữ chỗ. Giao diện hiện số dư; nút gửi dựa vào số coin dùng được.
- **Ngày coin**: ngày lịch theo giờ Việt Nam (UTC+7, không có giờ mùa hè). Mọi thứ "mỗi ngày" (đăng nhập, nhiệm vụ, giới hạn
  quảng cáo, trần 30 coin) đổi ngày lúc **00:00 giờ Việt Nam** (= 17:00 UTC hôm trước). Hằng số `COIN_TZ = UTC+7`, hàm
  `coin_day(moment) -> "YYYY-MM-DD"` trong `lyris/coins/clock.py`, dùng `lyris.auth.clock.now()` để test giả giờ được.
  **(tạm chọn: múi giờ cố định UTC+7 thay vì `zoneinfo`, để không phụ thuộc gói tzdata.)**
- **Chủ máy** (`accounts.role = 'owner'`): không bao giờ bị trừ coin, không có giữ chỗ, không nhận quà, nhiệm vụ hay thưởng
  (không cần). Ví trả `unlimited: true` ([quyết định](../wiki/decisions/chu-may-khong-ton-coin.md)).
- **Tắt hẳn coin**: `LYRIS_COINS=0` (mặc định `1`). Tắt thì không ai bị trừ, giao diện không có chip, ví, nhiệm vụ; dành cho
  người tự chạy Lyris cho bạn bè mà không muốn coin **(tạm chọn)**. Biến này đọc qua `_env` của `lyris/config.py`, nên tên cũ
  `NORA_COINS` cũng có tác dụng khi `LYRIS_COINS` chưa đặt (như mọi biến `LYRIS_*`).
- **Ví luôn có**: mọi thành viên có đúng một dòng `coin_wallets`, kể cả khi coin đang tắt. Ví được mở ngay lúc tạo thành viên
  (§3.4), và mọi hàm đọc/ghi ví gặp thành viên chưa có ví thì tự tạo ví 0 trong cùng transaction, không bao giờ lỗi.

## 2. Dữ liệu: migration `0012_coins.sql`

Chỉ thêm bảng, không đổi bảng cũ, không xoá dữ liệu.

```sql
-- 1. Ví: số dư cache, đổi cùng transaction với dòng sổ.
CREATE TABLE coin_wallets (
    account_id  INTEGER PRIMARY KEY REFERENCES accounts(id) ON DELETE CASCADE,
    balance     INTEGER NOT NULL DEFAULT 0 CHECK (balance >= 0),
    updated_at  TEXT NOT NULL
);

-- 2. Sổ coin: chỉ thêm. Mỗi sự kiện có một khoá chống trùng (idem_key), ghi lại cùng khoá thì bỏ qua.
CREATE TABLE coin_ledger (
    id             INTEGER PRIMARY KEY,
    account_id     INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    delta          INTEGER NOT NULL CHECK (delta <> 0),
    balance_after  INTEGER NOT NULL CHECK (balance_after >= 0),
    kind           TEXT NOT NULL CHECK (kind IN ('signup_grant', 'backfill_grant', 'daily_login', 'chat',
                                                 'mission', 'creator_milestone', 'topup_code', 'admin_adjust')),
    idem_key       TEXT NOT NULL UNIQUE,
    coin_day       TEXT NOT NULL,                 -- 'YYYY-MM-DD' giờ Việt Nam
    story_id       INTEGER,                       -- chat: id nội bộ, không khoá ngoại (xoá story không xoá sổ)
    card_id        INTEGER,                       -- chat: nhân vật; creator_milestone: nhân vật gốc
    hold_id        INTEGER,                       -- chat: giữ chỗ đã thành dòng này
    code_id        INTEGER,                       -- topup_code
    mission        TEXT CHECK (mission IS NULL OR mission IN ('ad', 'characters', 'turns')),
    milestone      INTEGER CHECK (milestone IS NULL OR milestone IN (10, 50, 100)),
    actor_id       INTEGER REFERENCES accounts(id) ON DELETE SET NULL,   -- chủ máy (admin_adjust, mã nạp)
    reason         TEXT CHECK (reason IS NULL OR length(reason) <= 120), -- chỉ admin_adjust, bắt buộc ở đó
    created_at     TEXT NOT NULL
);
CREATE INDEX idx_coin_ledger_account ON coin_ledger (account_id, id DESC);
CREATE INDEX idx_coin_ledger_day ON coin_ledger (account_id, coin_day, kind);
-- Chỉ thêm. Lưu ý: `ON DELETE SET NULL` của `actor_id` là một lệnh UPDATE và CÓ chạy trigger (đã thử bằng sqlite3:
-- một trigger "BEFORE UPDATE ON coin_ledger" chặn luôn việc xoá tài khoản chủ máy). Vì vậy:
-- (1) chặn UPDATE mọi cột trừ actor_id; (2) actor_id chỉ được đổi thành NULL (đúng việc SET NULL làm).
CREATE TRIGGER coin_ledger_append_only
BEFORE UPDATE OF id, account_id, delta, balance_after, kind, idem_key, coin_day, story_id, card_id, hold_id, code_id,
                 mission, milestone, reason, created_at ON coin_ledger
BEGIN SELECT RAISE(ABORT, 'coin_ledger chỉ thêm, không sửa'); END;
CREATE TRIGGER coin_ledger_actor_only_null
BEFORE UPDATE OF actor_id ON coin_ledger WHEN NEW.actor_id IS NOT NULL
BEGIN SELECT RAISE(ABORT, 'coin_ledger chỉ thêm, không sửa'); END;
-- Không có code nào xoá dòng sổ. Dòng chỉ mất khi xoá tài khoản (ON DELETE CASCADE, docs/compliance.md §4).

-- 3. Giữ chỗ cho một lượt sinh. Mỗi tài khoản tối đa một giữ chỗ đang mở (khớp cổng sinh: mỗi tài khoản 1 lượt).
CREATE TABLE coin_holds (
    id             INTEGER PRIMARY KEY,
    account_id     INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    story_id       INTEGER,                       -- NULL khi mode = 'test' (chat thử ở Studio, không có story)
    char_key       INTEGER,                       -- nhân vật để đếm "3 nhân vật khác nhau": origin_card_id nếu là bản sao, không thì card_id; NULL khi 'test'
    origin_card_id INTEGER,                       -- nhân vật công khai gốc (bản sao), để đếm người chơi (F44); NULL khi 'test'
    mode           TEXT NOT NULL CHECK (mode IN ('story', 'dm', 'test')),
    kind           TEXT NOT NULL CHECK (kind IN ('send', 'retry', 'regenerate')),
    amount         INTEGER NOT NULL CHECK (amount > 0),
    status         TEXT NOT NULL DEFAULT 'held' CHECK (status IN ('held', 'charged', 'released')),
    release_reason TEXT CHECK (release_reason IS NULL OR release_reason IN
                       ('error', 'empty', 'cancelled', 'queue_timeout', 'save_failed', 'invalid', 'restart')),
    message_id     INTEGER,                       -- câu trả lời đã lưu (charged)
    coin_day       TEXT NOT NULL,                 -- ngày coin lúc giữ chỗ
    created_at     TEXT NOT NULL,
    settled_at     TEXT
);
CREATE UNIQUE INDEX idx_coin_holds_one_open ON coin_holds (account_id) WHERE status = 'held';
CREATE INDEX idx_coin_holds_day ON coin_holds (account_id, coin_day, status);
CREATE INDEX idx_coin_holds_origin ON coin_holds (origin_card_id, account_id) WHERE status = 'charged';

-- 4. Mã nạp (F43). Như mã mời: chỉ lưu hash, mã đầy đủ hiện một lần.
CREATE TABLE coin_topup_codes (
    id          INTEGER PRIMARY KEY,
    code_hash   BLOB NOT NULL UNIQUE,             -- sha256 mã đã chuẩn hoá (12 ký tự base32, dùng lại auth/codes.py)
    code_hint   TEXT NOT NULL,                    -- 4 ký tự cuối
    amount      INTEGER NOT NULL CHECK (amount BETWEEN 1 AND 10000),
    pack_id     TEXT CHECK (pack_id IS NULL OR pack_id IN ('p100', 'p550', 'p1200', 'p2500')),
    note        TEXT NOT NULL DEFAULT '' CHECK (length(note) <= 60),
    created_by  INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
    created_at  TEXT NOT NULL,
    expires_at  TEXT NOT NULL,
    used_by     INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
    used_at     TEXT,
    revoked_at  TEXT
);
CREATE TABLE coin_code_attempts (                 -- giới hạn thử mã sai (§4.3); dọn lúc ghi: mỗi lần ghi một lần thử thì
                                                  -- xoá dòng > 30 ngày của tài khoản đó, cùng transaction (không cần việc nền)
    id          INTEGER PRIMARY KEY,
    account_id  INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    ok          INTEGER NOT NULL CHECK (ok IN (0, 1)),
    created_at  TEXT NOT NULL
);
CREATE INDEX idx_coin_code_attempts ON coin_code_attempts (account_id, created_at);

-- 5. Quảng cáo mẫu (F45): server ghi giờ bắt đầu, nhận thưởng chỉ khi đã đủ 15 giây.
CREATE TABLE coin_ad_views (
    id          INTEGER PRIMARY KEY,
    account_id  INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    coin_day    TEXT NOT NULL,
    started_at  TEXT NOT NULL,
    claimed_at  TEXT,
    cancelled_at TEXT                             -- "Đóng" sớm, hoặc bị thay bởi lượt xem mới
);
CREATE UNIQUE INDEX idx_coin_ad_open ON coin_ad_views (account_id) WHERE claimed_at IS NULL AND cancelled_at IS NULL;

-- 6. Người chơi của nhân vật công khai và mốc đã thưởng (F44 bản cũ; từ khi làm lại, creator_milestones không ghi thêm, §2.2).
CREATE TABLE creator_players (
    card_id       INTEGER NOT NULL REFERENCES character_cards(id) ON DELETE CASCADE,  -- nhân vật gốc
    player_id     INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    creator_id    INTEGER REFERENCES accounts(id) ON DELETE SET NULL,  -- người tạo X lúc đủ điều kiện
    qualified_at  TEXT NOT NULL,
    PRIMARY KEY (card_id, player_id)
);
CREATE TABLE creator_milestones (
    card_id     INTEGER NOT NULL REFERENCES character_cards(id) ON DELETE CASCADE,
    milestone   INTEGER NOT NULL CHECK (milestone IN (10, 50, 100)),
    creator_id  INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
    outcome     TEXT NOT NULL CHECK (outcome IN ('paid', 'owner')),  -- 'owner': người tạo là chủ máy, không trả coin
    ledger_id   INTEGER,
    reached_at  TEXT NOT NULL,
    PRIMARY KEY (card_id, milestone)
);

-- 7. Mở ví cho thành viên có từ trước: +300 một lần (tạm chọn). Chủ máy không có dòng nào.
INSERT INTO coin_wallets (account_id, balance, updated_at)
    SELECT id, 300, strftime('%Y-%m-%dT%H:%M:%fZ', 'now') FROM accounts WHERE role = 'member';
INSERT INTO coin_ledger (account_id, delta, balance_after, kind, idem_key, coin_day, created_at)
    SELECT id, 300, 300, 'backfill_grant', 'backfill:' || id,
           strftime('%Y-%m-%d', 'now', '+7 hours'), strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
      FROM accounts WHERE role = 'member';
```

### 2.1 Khoá chống trùng (`idem_key`)

| Sự kiện | `idem_key` | Ghi chú |
|---|---|---|
| Tạo thành viên | `signup:<account_id>` | trong `auth/store.insert_member`, cùng transaction tạo tài khoản (§3.4) |
| Mở ví (migration) | `backfill:<account_id>` | |
| Đăng nhập trong ngày | `daily:<account_id>:<coin_day>` | |
| Một câu trả lời | `chat:<hold_id>` | |
| Nhiệm vụ | `mission:<account_id>:<coin_day>:<mission>[:<n>]` | quảng cáo có `:<1..3>` |
| Mốc sáng tác (cũ, không ghi thêm từ khi F44 làm lại) | `milestone:<card_id>:<10/50/100>` | dòng cũ giữ nguyên trong sổ và lịch sử |
| Thưởng xếp hạng (F44 làm lại) | `rank:<card_id>:<100/50/10>` | thêm khoá chính `creator_rank_tiers (card_id, tier)`; id nhân vật bị dùng lại thì thêm `:<uid>` (§5.6) |
| Thưởng công khai lần đầu | `first_public:<account_id>` | thêm khoá chính `creator_first_public (account_id)` |
| Mã nạp | `topup:<code_id>` | |
| Chủ máy điều chỉnh | `adjust:<uuid4 do giao diện gửi>` | bấm hai lần, mạng chập chờn: chỉ ghi một lần |

Ghi một dòng sổ = một hàm duy nhất `post(conn, account_id, delta, kind, idem_key, **refs)` trong `lyris/coins/ledger.py`, chạy
trong `BEGIN IMMEDIATE` (SQLite cho một người ghi một lúc; gọi bên trong `repo.transaction()` có sẵn thì thành SAVEPOINT,
`db/repo.py`): kiểm `idem_key` → nếu đã có **và cùng nội dung** (`account_id`, `delta`, `kind`) thì trả dòng cũ (không lỗi);
đã có mà **khác nội dung** thì `IdemConflict` (API trả 409 `idem_conflict`, ví dụ cùng `request_id` của "Cộng/trừ coin" mà khác
số coin); chưa có thì tạo ví 0 nếu thiếu, rồi
`UPDATE coin_wallets SET balance = balance + :delta WHERE account_id = ? AND balance + :delta >= 0`; không đổi dòng nào thì
`InsufficientCoins`; rồi `INSERT` dòng sổ với `balance_after`. Không chỗ nào khác được đổi `coin_wallets.balance`.

Mọi việc "đọc rồi quyết rồi ghi" (giữ chỗ, trần nhiệm vụ, đếm quảng cáo, trần thưởng xếp hạng, trừ tay theo số dùng được) nằm **trong
cùng một transaction** với `post()`/`INSERT` của nó, không đọc trước rồi ghi ở transaction khác.

**Bất biến:** `balance − (tổng amount của giữ chỗ 'held') >= 0` mọi lúc. Chỉ có hai thứ làm số dư giảm: trừ khi chat (từ một giữ
chỗ đã có) và chủ máy trừ tay (kiểm theo số dùng được, §4.4). Nhờ vậy `charge` của một giữ chỗ `held` luôn đủ coin.

### 2.2 Migration `0014_hot_board.sql` (F44 làm lại, F46)

**Chỉ thêm** bảng (và một lệnh `INSERT` vào bảng mới), không `ALTER`/`DROP`/`UPDATE` bảng cũ. App của chủ dự án chạy `--reload`
nên tự áp migration lên `data/lyris.db` ngay khi file `.py` đổi ([learned.md](../wiki/learned.md), 2026-11-14): chép file `.sql`
**trước** khi nối code `.py`, và báo chủ dự án trong báo cáo build.

```sql
-- 1. Lúc nhân vật bật Công khai gần nhất (thưởng công khai lần đầu cần ≥ 24 giờ liên tục). Về Riêng tư thì xoá dòng.
CREATE TABLE card_public_since (
    card_id  INTEGER PRIMARY KEY REFERENCES character_cards(id) ON DELETE CASCADE,
    since    TEXT NOT NULL
);
-- Nhân vật đang công khai lúc áp migration: tính từ lúc áp (phải đợi đủ 24 giờ như mọi người).
INSERT INTO card_public_since (card_id, since)
    SELECT id, strftime('%Y-%m-%dT%H:%M:%fZ', 'now') FROM character_cards
     WHERE visibility = 'public' AND story_copy = 0;

-- 2. Bảng "Nhân vật hot": chỉ giữ lần tính mới nhất (lần tính mới xoá lần cũ, CASCADE).
CREATE TABLE hot_board_runs (
    id           INTEGER PRIMARY KEY,
    computed_at  TEXT NOT NULL,
    ranked       INTEGER NOT NULL CHECK (ranked >= 0)   -- tổng số nhân vật đủ điều kiện xếp hạng (có thể > 100)
);
CREATE TABLE hot_board (
    run_id   INTEGER NOT NULL REFERENCES hot_board_runs(id) ON DELETE CASCADE,
    rank     INTEGER NOT NULL CHECK (rank BETWEEN 1 AND 100),
    card_id  INTEGER NOT NULL REFERENCES character_cards(id) ON DELETE CASCADE,
    players  INTEGER NOT NULL CHECK (players >= 1),
    PRIMARY KEY (run_id, rank)
);

-- 3. Bậc xếp hạng nhân vật đã đạt (top 100 / 50 / 10), mỗi bậc một lần mỗi nhân vật.
CREATE TABLE creator_rank_tiers (
    card_id     INTEGER NOT NULL REFERENCES character_cards(id) ON DELETE CASCADE,
    tier        INTEGER NOT NULL CHECK (tier IN (100, 50, 10)),
    creator_id  INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
    rank        INTEGER NOT NULL,                      -- hạng lúc đạt bậc
    outcome     TEXT NOT NULL CHECK (outcome IN ('waiting', 'paid', 'owner')),
    ledger_id   INTEGER,
    reached_at  TEXT NOT NULL,
    paid_at     TEXT,
    PRIMARY KEY (card_id, tier)
);

-- 4. Thưởng công khai lần đầu: mỗi tài khoản một dòng.
CREATE TABLE creator_first_public (
    account_id  INTEGER PRIMARY KEY REFERENCES accounts(id) ON DELETE CASCADE,
    card_id     INTEGER,                               -- nhân vật làm đủ điều kiện (không khoá ngoại: xoá nhân vật không xoá dòng)
    ledger_id   INTEGER NOT NULL,
    paid_at     TEXT NOT NULL
);
```

- **Không thêm `kind` mới cho sổ** **(tạm chọn)**: `coin_ledger.kind` có `CHECK` liệt kê sẵn, SQLite không sửa được `CHECK` nếu
  không dựng lại bảng; dựng lại sổ chỉ thêm (có trigger chặn sửa/xoá) trên DB thật là việc rủi ro. Vì vậy thưởng xếp hạng và
  thưởng công khai lần đầu ghi bằng `kind = 'creator_milestone'` (nghĩa mới: "thưởng sáng tác"): thưởng xếp hạng có
  `milestone = <bậc 100/50/10>` (khớp `CHECK (milestone IN (10, 50, 100))` có sẵn) và `card_id`; thưởng công khai lần đầu có
  `milestone = NULL`. Loại thưởng phân biệt bằng tiền tố `idem_key` (`milestone:`, `rank:`, `first_public:`). Mọi chỗ đọc sổ
  (lịch sử ví §10.5, "Nhật ký" §4.5, tổng "coin đã phát") dùng tiền tố này.
- Bảng cũ `creator_players` (người chơi) vẫn dùng; `creator_milestones` không ghi thêm, không xoá (chỉ thêm).
- Xoá tài khoản (F35): `creator_rank_tiers.creator_id` SET NULL, `creator_first_public` CASCADE; test xoá tài khoản của F35
  quét thêm hai bảng này.

## 3. Tiêu coin khi chat (F42)

### 3.1 Lượt nào tốn coin

| Thao tác | Tốn 6 coin? |
|---|---|
| Gửi lượt mới (Story hoặc DM) → nhân vật trả lời | Có (lời chủ dự án: "mỗi lượt tốn 6 coin") |
| "Trả lời" (thử lại khi lượt trước lỗi, `POST /stories/{id}/reply`) | Có **(PO chốt 2026-11-14)**. Lượt lỗi trước đã được nhả nên không tính hai lần. |
| "Tạo lại câu trả lời" (`POST /messages/{id}/regenerate`) | Có **(PO chốt 2026-11-14)**. Không tính thì bấm "Tạo lại" liên tục là chat miễn phí không giới hạn. |
| Chat thử ở Studio (`POST /api/cards/test-chat`) | Có, 6 mỗi câu trả lời **(PO chốt 2026-11-14)**. Route này nhận cả card lẫn tối đa 400 lượt `messages` từ trình duyệt (`MAX_TEST_TURNS`), nên nếu miễn phí thì dán bất kỳ thẻ nào (kể cả chữ chép từ nhân vật công khai) là chat được mãi không tốn coin, coin mất tác dụng. Giữ chỗ không có story: `story_id`, `char_key`, `origin_card_id` để NULL, `mode = 'test'`, `kind = 'send'`. Không tính cho nhiệm vụ hay người chơi (F44/F45). |
| Lời mở đầu của story (lấy từ card, không sinh) | Không |
| DM | Có, như Story **(PO chốt 2026-11-14)** |
| "Nhận gợi ý", "AI viết nháp" | Không **(PO chốt 2026-11-14)**. Gợi ý gắn với một story của chính người chơi, chỉ ra 3 câu ngắn cho người chơi chọn, không phải lời nhân vật; viết nháp ra một thẻ nhân vật, không phải hội thoại. Cả hai vẫn đi qua cổng sinh (1 lượt/tài khoản). |
| Việc nền (trích xuất cảm xúc, ký ức, tóm tắt, prefill) | Không (người dùng không bấm gì) |
| Lật phiên bản, sửa, xoá, thích/chê | Không |

### 3.2 Thứ tự trong `ChatService._run` ([quyết định](../wiki/decisions/giu-cho-coin-truoc-khi-sinh.md))

```
khoá story (409 nếu story đang bận)
→ vé cổng sinh `gate.reserve` (409 nếu tài khoản đang sinh ở story khác)
→ giữ chỗ coin `coins.hold(account, story, kind)`      ← mới; 402 `coins_required` nếu dùng được < 6
→ prepare (lưu lượt người chơi, dựng prompt)            ← lỗi ở đây (InvalidOperation) → nhả 'invalid'
→ chờ chỗ (waiting) …                                   ← quá 120 giây → nhả 'queue_timeout'
→ stream
→ _persist lưu câu trả lời (kể cả bản bị ngắt có chữ)  → `coins.charge(hold, message_id)` cùng transaction ghi sổ
```

- Giữ chỗ chạy **trước** khi lưu lượt người chơi: hết coin thì trả 402 ngay, lượt người chơi **không** được lưu, chữ còn trong
  ô nhập (bản nháp của ô nhập đã có).
- `hold` là một `INSERT INTO coin_holds` trong `BEGIN IMMEDIATE` sau khi kiểm `balance - (giữ chỗ đang mở) >= 6`; chỉ mục
  `idx_coin_holds_one_open` bảo đảm mỗi tài khoản một giữ chỗ (hai tab cùng gửi: một cái thắng, cái kia 409 vì cổng sinh, hoặc
  402 nếu đã hết coin; số dư không bao giờ âm vì `CHECK balance >= 0`).
- **Có chữ = có câu trả lời được lưu.** `_persist` lưu khi `raw.strip()` không rỗng: câu trả lời trọn vẹn, hoặc phần dở khi
  người chơi bấm "Dừng" / đóng tab sau khi đã có chữ. Câu trả lời chỉ có suy nghĩ cũng là có chữ.
- **Nhả giữ chỗ** (không ghi sổ, số dư không đổi) khi: lỗi model (`error`), câu trả lời rỗng (`empty`), lưu lỗi
  (`save_failed`), chờ quá 120 giây (`queue_timeout`), người chơi dừng hoặc đóng tab **trước chữ đầu tiên** (`cancelled`),
  lỗi khi chuẩn bị (`invalid`). Nhả nằm trong `finally` của `_run` (khiên `anyio.CancelScope(shield=True)` như phần lưu dở).
- Máy tắt giữa chừng: lúc khởi động, mọi giữ chỗ còn `held` được nhả với lý do `restart` (không ai bị trừ cho lượt không có chữ).
  Việc nhả này **chỉ** chạy trong `lifespan` của app FastAPI (`lyris/main.py`), trước khi nhận request. `python -m lyris.auth.cli`,
  `migrate`, script hay test mở DB **không** được nhả giữ chỗ: lúc đó app có thể đang chạy và đang sinh. Sự kiện
  `coins_released reason=restart` phát bằng `Tracker.emit_detached` (`analytics/tracker.py`), vì lúc khởi động không có request.
- **Dừng sau khi đã có chữ vẫn trừ 6** **(tạm chọn)**: model đã chạy, chữ đã lưu và người chơi đọc được. "Đã có chữ" nghĩa là
  người chơi đã nhận ít nhất một `delta` có chữ khác khoảng trắng (giống chat thử). Mẩu "[Thought…" còn nằm trong parser thì
  chưa tính: phần dở vẫn được lưu nhưng giữ chỗ nhả với lý do `cancelled` (rà soát 2026-11-14).
- **Giữ chỗ kẹt không chặn lượt sau** (rà soát 2026-11-14): `CoinService` nhớ những giữ chỗ còn một lượt sinh của tiến trình
  đang dùng. Giữ chỗ `held` của tài khoản mà không ai dùng (nhả lỗi "database is locked", transaction lưu bị cuộn lại) được
  nhả với lý do `error` ở lần giữ chỗ kế tiếp của tài khoản đó, trong cùng transaction. Cổng sinh bảo đảm mỗi tài khoản chỉ một
  lượt sinh trong tiến trình, nên không nhả nhầm giữ chỗ đang dùng. Lưu lỗi (`save_failed`) thì nhả theo DB (`WHERE
  status='held'`), không tin cờ `settled` trong bộ nhớ.
- **Sổ chặn cả DELETE**: migration `0013_coin_ledger_no_delete.sql` thêm trigger `coin_ledger_no_delete`; dòng sổ chỉ mất khi
  xoá tài khoản (cascade: lúc đó dòng `accounts` đã mất nên điều kiện `WHEN EXISTS` không còn đúng).
- **`charge` không bao giờ làm mất câu trả lời.** `charge(hold, message_id)` chạy trong cùng `repo.transaction()` bọc `_persist`
  (cả nhánh `_save_aborted` khi bị ngắt có chữ): `UPDATE coin_holds SET status='charged' … WHERE id=? AND status='held'` rồi
  `post(… 'chat', 'chat:<hold_id>')`. Theo bất biến ở §2.1, giữ chỗ `held` luôn đủ coin nên `post` không thể báo
  `InsufficientCoins`. Giữ chỗ không còn `held` lúc `charge` (không thể xảy ra trong luồng thường: nhả chỉ chạy trong `finally` của
  chính `_run` sau khi biết không có chữ, hoặc lúc khởi động khi không còn luồng sinh nào) thì vẫn lưu câu trả lời, ghi log lỗi và
  không trừ. Không bao giờ rollback câu trả lời vì coin.

### 3.2a Móc vào code có sẵn

- `ChatService.__init__(…, coins: CoinService | None = None)`. `None` = không tính coin (như `lore`, `gate`), nên các test cũ
  dựng `ChatService` bằng tay vẫn chạy mà không phải sửa fixture. App (`main.py`) luôn truyền `CoinService`; `LYRIS_COINS=0` hay
  chủ máy thì `CoinService.hold` trả `None` (không giữ chỗ).
- Exception mới `CoinsRequired(balance, price)` trong `lyris/coins/errors.py`, ném từ `hold`. `api/sse.py` "mồi" sự kiện đầu bằng
  `anext` trước khi mở stream; với `send`, sự kiện đầu (`user_message`) đến sau `prepare`, mà `hold` chạy trước `prepare`, nên lỗi
  luôn ra trước byte SSE đầu tiên. Bốn route ánh xạ `CoinsRequired` → 402: `POST /api/stories/{id}/messages`,
  `POST /api/stories/{id}/reply`, `POST /api/messages/{id}/regenerate`, `POST /api/cards/test-chat` (route này giữ chỗ trong
  `_locked_stream` sau `reserve_generation`, trừ khi luồng chat thử có chữ).

### 3.3 Lỗi khi hết coin

HTTP **402**, cùng định dạng lỗi `{detail, code}` của [auth.md §6.1](auth.md):

```json
{"detail": "Bạn đã hết coin. Mỗi câu trả lời cần 6 coin.", "code": "coins_required", "balance": 4, "price": 6}
```

Áp dụng cho `POST /api/stories/{id}/messages`, `POST /api/stories/{id}/reply`, `POST /api/messages/{id}/regenerate`,
`POST /api/cards/test-chat`. Lỗi được
"mồi" trước khi stream (như 404/409 hiện nay, `api/sse.py`), nên là HTTP status thường, không phải sự kiện SSE. Giao diện
nhận `code = coins_required` thì làm mới ví và chuyển ô nhập sang trạng thái khoá (§10.3). Không chữ "token", "model", "credits".

### 3.4 Quà tạo tài khoản và đăng nhập trong ngày

- **Tạo thành viên**: +300 (`signup_grant`). `coins.open_wallet(conn, account_id)` (tạo ví rồi `post(+300, 'signup:<id>')`) được gọi
  **bên trong `auth/store.insert_member`**, cùng transaction. Như vậy **mọi đường tạo thành viên** đều có ví và quà: tạo tài
  khoản bằng mã mời (`auth/service.signup`), server giả của bot (`environment/fake-server.py` gọi thẳng `insert_member`), fixture
  của test. Thiết lập chủ máy (`setup_owner`) không qua `insert_member`: chủ máy không có ví, không có quà.
- Ví mở và quà 300 được ghi **kể cả khi `LYRIS_COINS=0`** **(tạm chọn)**: tắt coin chỉ là không trừ, không hiện; bật lại thì thành
  viên tạo lúc tắt đã có 300 như mọi người, không cần backfill lần hai.
- **Ngày đầu tiên**: tạo tài khoản +300, rồi mở app (checkin) +60 ngay trong ngày coin đó, tổng **360** **(PO chốt 2026-11-14)**.
  Hai thứ là hai quà khác nhau (quà tạo tài khoản, quà đăng nhập trong ngày) nên không trừ nhau.
- **Đăng nhập trong ngày**: phiên đăng nhập kéo dài 30 ngày nên người dùng ít khi "đăng nhập" lại. Vì vậy "đăng nhập" = **mở app
  lần đầu trong ngày coin** **(tạm chọn)**: sau khi qua cổng đăng nhập, app gọi `POST /api/coins/checkin`; lần đầu trong ngày
  cộng +60 (`daily_login`) và trả `granted: true`, giao diện hiện thông báo nhỏ "+60 coin cho hôm nay". Gọi lại cùng ngày:
  `granted: false`. Đăng nhập bằng mật khẩu (`POST /api/auth/login`) cũng gọi cùng hàm, nên không bao giờ được hai lần.
- Tài khoản tạm khoá không gọi được API nên không nhận gì.

## 4. Nạp coin, chế độ thử (F43)

### 4.1 Gói giá **(PO chốt 2026-11-14)**

PO chốt bảng dưới (1A, [raw](../wiki/raw/2026-11-14-coin-tra-loi-2.md)). Trên giao diện mọi giá ghi là **"Giá dự kiến"** (giá khi ra mắt), vì ở chế độ thử
không ai bán coin.

| `pack_id` | Coin | Tặng thêm | Giá dự kiến | Tương đương |
|---|---|---|---|---|
| `p100` | 100 | 0 | 10.000đ | ~16 câu trả lời |
| `p550` | 550 | 50 | 50.000đ | ~91 câu trả lời |
| `p1200` | 1.200 | 200 | 100.000đ | 200 câu trả lời |
| `p2500` | 2.500 | 500 | 200.000đ | ~416 câu trả lời |

"Coin" là tổng đã cộng tặng thêm. Bảng gói nằm trong code (`lyris/coins/packs.py`), không trong DB; giá chỉ để hiện.
Không có giảm giá kiểu bốc thăm, không phần thưởng ngẫu nhiên.

### 4.2 Chế độ thử

- `GET /api/coins/packs` trả `test_mode: true` (mặc định; thanh toán thật là cờ khác lúc ra mắt, ngoài phạm vi này).
- Màn "Nạp coin" nói rõ: **"Chế độ thử: Lyris chưa bán coin. Nhập mã nạp người quản lý tặng bạn."** Chạm một gói chỉ mở hộp
  giải thích: "Giá dự kiến khi Lyris ra mắt. Ở chế độ thử chưa bán coin; người quản lý có thể tặng bạn mã nạp để thử." với một nút
  **"Đóng"**. **Không** có nút thanh toán, **không** có nút "Liên hệ" trên gói (để gói không thành kênh bán coin lấy tiền mặt hay
  chuyển khoản ngoài app), không hỏi thẻ hay số điện thoại.
- **Mã nạp được tặng, không bán.** Ở chế độ thử, người quản lý chỉ tặng mã (thử nghiệm, bù lỗi, cảm ơn người thử). Bán mã lấy tiền
  là bán coin không có điều khoản bán, hoá đơn hay hoàn tiền: Điều khoản và [quyết định](../wiki/decisions/nap-coin-che-do-thu.md)
  ghi rõ điều này (§12).
- Không thu tiền nên không có hoàn tiền trong chế độ thử (§12).

### 4.3 Mã nạp (chủ máy tạo)

- Chủ máy tạo ở `#/admin` → mục "Coin" → "Tạo mã nạp": chọn một gói (số coin của gói) hoặc nhập số coin 1–10.000, ghi chú
  ≤ 60 ký tự, hết hạn sau 1 / 7 / 30 ngày (mặc định 7). Mã 12 ký tự base32 (dùng lại `auth/codes.py`), chỉ lưu hash, mã đầy đủ
  **hiện một lần** (như mã mời: nền mờ và Esc không đóng được hộp, "Sao chép mã").
- Dùng **một lần**, cho bất kỳ thành viên nào nhập (không gắn trước với người nhận) **(tạm chọn)**. Chủ máy nhập mã: 422
  `topup_code_owner` "Tài khoản quản lý không cần nạp coin." (mã không bị dùng).
- Tối đa 50 mã còn hiệu lực cùng lúc **(tạm chọn)**: mã thứ 51 trả 422 `topup_code_limit` "Đã có 50 mã nạp còn hiệu lực. Huỷ bớt mã
  cũ rồi tạo mã mới." Huỷ được mã chưa dùng.
- Danh sách mã: ghi chú, 4 ký tự cuối, số coin, nhãn "Còn hiệu lực" / "Đã dùng bởi @handle" / "Hết hạn" / "Đã huỷ".
- Nhập mã (`POST /api/coins/redeem`): chuẩn hoá như mã mời (viết thường, gạch ngang của iPhone, khoảng trắng). Sai, hết hạn,
  đã dùng, đã huỷ: **cùng một câu** "Mã nạp không đúng hoặc đã hết hạn." (422 `topup_code_invalid`). Đúng: một transaction đánh
  dấu `used_by/used_at` (`UPDATE … WHERE used_at IS NULL AND revoked_at IS NULL AND expires_at > now`) rồi ghi sổ
  `topup:<code_id>`; hai người nhập cùng mã cùng lúc: chỉ một người được.

### 4.4 Chủ máy cộng/trừ coin tay

- `#/admin` → "Thành viên" → "…" → **"Cộng/trừ coin"**: số nguyên −10.000…10.000, khác 0; **lý do bắt buộc**, 3–120 ký tự.
- Trừ được tối đa **số coin dùng được** (số dư − giữ chỗ đang mở), không phải số dư: nếu thành viên đang chờ một câu trả lời
  (6 coin đang giữ), chủ máy không trừ được 6 coin đó, để lượt đang chạy vẫn trừ được khi có chữ (bất biến §2.1). Trừ quá:
  422 `adjust_too_large` "Không trừ được quá số coin dùng được ({n} coin)." với `{n}` = số dùng được (không bao giờ âm).
  Kiểm và ghi trong cùng một transaction.
- Ghi sổ `admin_adjust` với `actor_id` = chủ máy, `reason`, `idem_key = adjust:<uuid>` do giao diện tạo mỗi lần mở hộp. Gửi lại
  cùng `request_id` với cùng `delta` và tài khoản: trả kết quả cũ, không ghi thêm; khác `delta` hay khác tài khoản: 409
  `idem_conflict`.
- Thành viên thấy dòng "Người quản lý điều chỉnh" kèm lý do trong lịch sử **(tạm chọn: minh bạch)**.

### 4.5 Nhật ký cho chủ máy

`#/admin` → "Coin" có phần "Nhật ký" (50 dòng mới nhất của `topup_code`, `admin_adjust` và `creator_milestone`: thời gian,
@handle, số coin, lý do, ghi chú mã, hoặc thưởng sáng tác kèm @handle người tạo, để chủ máy thấy thưởng bất thường; chữ theo
tiền tố `idem_key` (§2.2): "Thưởng xếp hạng top {100/50/10}", "Thưởng công khai lần đầu", dòng cũ "Thưởng mốc {10} người chơi")
và ba con số của 30 ngày: coin đã phát (quà, nhiệm vụ, thưởng), coin đã nạp bằng mã, coin đã tiêu. Không có
story, tin nhắn hay nhân vật riêng tư của ai.

## 5. Thưởng sáng tác theo bảng xếp hạng "Nhân vật hot" (F44 làm lại, F46)

> **Đổi 2026-11-14 22:15** ([raw](../wiki/raw/2026-11-14-f44-bang-xep-hang-tra-loi.md), PO chọn 1A 2C 3A 4A 5A): thưởng mốc
> 10/50/100 người chơi (+100/+300/+600) **bị thay hẳn** bằng thưởng xếp hạng và thưởng công khai lần đầu. Quyết định:
> [xep-hang-nhan-vat-hot](../wiki/decisions/xep-hang-nhan-vat-hot.md) (thay [moc-nguoi-choi-sang-tac](../wiki/decisions/moc-nguoi-choi-sang-tac.md)).
> Phần AI tự chọn ghi **(tạm chọn)**.

### 5.1 "Người chơi" là ai (giữ nguyên từ bản trước)

Một **người chơi** của nhân vật công khai X là một tài khoản P sao cho:

1. P **không phải** người tạo X và **không phải** chủ máy **(tạm chọn)**;
2. P có story chơi bằng **bản sao** của X (`character_cards.story_copy = 1`, `origin_card_id = X`, F31);
3. P đã có **ít nhất 3 câu trả lời đã trả coin** (giữ chỗ `charged`), cộng dồn trong **mọi** story P chơi bằng bản sao của X,
   và các câu đó nằm ở **ít nhất 2 ngày coin khác nhau** **(tạm chọn)**.

Đủ thì ghi `creator_players (X, P, người tạo X)` một lần (khoá chính), ngay sau mỗi `charge` có `origin_card_id`, trong cùng
transaction (`creator.note_charged`, đã có). Cách đếm qua story và bản sao (id nhân vật bị dùng lại) giữ như
[coin-f44-khi-build](../wiki/decisions/coin-f44-khi-build.md). **Khác bản trước:** `note_charged` chỉ ghi người chơi, **không trả
coin** nữa; `settle_milestones`/`settle_creator` theo mốc bị bỏ.

Giá coin không chặn được tài khoản ảo (18 coin lấy từ quà miễn phí). Thứ giới hạn lạm dụng: mỗi tài khoản cần mã mời của chủ máy
(F30); "2 ngày coin" làm việc dựng người chơi chậm lại; **bậc top N chỉ trả khi bảng có nhân vật của ít nhất N người tạo khác nhau** (§5.3); trần thưởng
xếp hạng theo người tạo (§5.4); "Nhật ký" của chủ máy hiện mọi thưởng (§4.5).

### 5.2 Bảng "Nhân vật hot" (F46)

**"Hot" = tổng người chơi từ trước tới nay** (PO chọn 2C) = số dòng `creator_players` của nhân vật mà tài khoản người chơi đang
`active` (người chơi bị tạm khoá không được đếm tới khi mở khoá, tạm chọn: chủ máy khoá tài khoản phụ là chặn được việc leo bảng).

Nhân vật **được xếp hạng** khi đủ cả bốn **(tạm chọn)**:

- là nhân vật gốc (`story_copy = 0`), đang `visibility = 'public'` (nhân vật bị chủ máy "Ẩn nhân vật" là riêng tư nên không có);
- người tạo đang `active` (bị tạm khoá thì không lên bảng);
- có **ít nhất 1 người chơi**;
- nhân vật mẫu của Lyris không bao giờ có trên bảng (không công khai, không có người chơi).

Nhân vật của chủ máy **được** xếp hạng như mọi người nhưng không bao giờ nhận coin (§5.4).

**Thứ tự** (`hot.rank_cards`): nhiều người chơi trước; bằng nhau thì nhân vật **đạt số người chơi hiện tại sớm hơn** trước
(`MAX(creator_players.qualified_at)` nhỏ hơn); vẫn bằng thì `card_id` nhỏ hơn trước. Hạng là 1, 2, 3… liên tiếp, không có hạng
đồng. Bảng lưu **100 hạng đầu** (`hot_board`), cùng `hot_board_runs.ranked` = tổng số nhân vật đủ điều kiện (có thể > 100).

**Cập nhật mỗi giờ, tính khi cần** **(tạm chọn: app không có việc nền theo giờ)**: `hot.refresh_if_stale(conn, now)` tính lại khi
lần tính mới nhất cũ hơn **60 phút** (hay chưa có). Gọi từ `GET /api/explore/hot` và `POST /api/coins/checkin` (mỗi lần mở app),
nên bảng không bao giờ cũ hơn 60 phút lúc có người xem, và thưởng được trả dù không ai mở bảng. Tính và trả thưởng trong **một**
transaction `BEGIN IMMEDIATE`; trong transaction kiểm lại "đã cũ chưa" để hai request cùng lúc chỉ tính một lần. Bảng còn mới thì
`CoinService.refresh_hot` chỉ đọc (không mở transaction ghi), nên mỗi lần mở Khám phá hay checkin không giữ khoá ghi. Lần tính mới xoá
lần cũ. Lỗi khi tính (lỗi DB, `IdemConflict`) không làm hỏng request gọi nó: `GET /api/explore/hot` trả bảng cũ (hay rỗng),
checkin vẫn trả 200; lần sau tính lại.

**Đọc bảng**: `GET /api/explore/hot?limit=<1..100>` (mặc định 100) trả
`{updated_at, ranked, items: [{rank, card_id, name, avatar_url, creator_handle, players}]}`. Lúc đọc, bỏ nhân vật đã về Riêng tư,
đã xoá hay có người tạo bị khoá kể từ lần tính (hạng của nhân vật khác **giữ nguyên số**, tới lần tính sau). Chỉ có trường công
khai (như `GET /api/public-cards`), không có `account_id`, mô tả hay trường bí mật. Cần đăng nhập; `test_isolation_sweep.py`
phân loại route mới.

### 5.3 Bậc xếp hạng và phần thưởng **(PO chốt 2026-11-14 22:15)**

| Bậc | Thưởng | Điều kiện thêm **(tạm chọn)** | `idem_key` |
|---|---|---|---|
| top 100 | +100 coin | các nhân vật được xếp hạng thuộc ≥ 100 người tạo khác nhau (`creators ≥ 100`) | `rank:<X>:100` |
| top 50 | +200 coin | `creators ≥ 50` | `rank:<X>:50` |
| top 10 | +300 coin | `creators ≥ 10` | `rank:<X>:10` |

- `creators` (`hot.ranked_creators`) = số người tạo khác nhau có ít nhất một nhân vật được xếp hạng (cùng điều kiện với
  §5.2), đếm lúc tính bảng. Luôn ≤ `ranked`.
- Ở mỗi lần tính bảng, nhân vật X có hạng `r` **đạt** bậc N khi `r ≤ N` và `creators ≥ N`. Bậc đạt lần đầu thì ghi
  `creator_rank_tiers (X, N, người tạo, r, …)`; đã có dòng thì bỏ qua (khoá chính): **mỗi bậc một lần cho mỗi nhân vật**, rớt hạng
  rồi lên lại không trả lại.
- **Cộng dồn** (PO 3A): lên thẳng top 10 trong một lần tính (và `creators ≥ 100`) thì đạt cả ba bậc: 100 + 200 + 300 = **600**.
  Bảng có nhân vật của 60 người tạo thì bậc top 100 chưa đạt được (ai cũng "trong top 100"); bậc đó đạt ở lần tính đầu tiên có
  `creators ≥ 100` mà X vẫn ở hạng ≤ 100.
- Vì sao "≥ N người tạo" **(tạm chọn)**: máy ít người dùng (vài chục thành viên) thì một nhân vật có 1 người chơi đã ở top 10;
  không có điều kiện này thì công khai là gần như chắc chắn được 600 coin. Bản đầu đếm **nhân vật** (`ranked ≥ N`); rà soát
  2026-11-14 thấy một người tạo tự lấp bảng được: 10 nhân vật công khai, mỗi nhân vật 1 người chơi (cùng một bạn) → cả 10 ở top 10,
  mỗi nhân vật +300 (3.000 coin sau 5 tuần, trần chỉ làm chậm). Đếm người tạo khác nhau thì tự lấp bảng không đủ: cần N tài
  khoản có nhân vật được người khác chơi.
- Lúc đạt bậc: người tạo là chủ máy → `outcome = 'owner'`, không có coin, không có dòng sổ; người tạo là thành viên → trả ngay nếu
  được (§5.4), không thì `outcome = 'waiting'`.

### 5.4 Khi nào trả, trần theo người tạo

`hot.settle_rewards(conn, now)` chạy cuối mỗi lần tính bảng, cùng transaction. Ghi bậc, mỗi dòng trả bậc và mỗi dòng +50 có
SAVEPOINT riêng **(tạm chọn)**: một dòng lỗi (lỗi DB, `IdemConflict`) chỉ để chính dòng đó chờ lần tính sau; bậc đã đạt vẫn
được ghi, người tạo khác vẫn được trả. Trả mọi bậc `waiting` (cũ trước: `reached_at`, rồi
`card_id`, rồi bậc 100 → 50 → 10) **chỉ khi** lúc đó:

- coin đang bật (`LYRIS_COINS=1`); tắt thì chờ tới khi bật lại;
- nhân vật còn và đang công khai; người tạo đang `active` và là thành viên;
- **trần theo người tạo** **(tạm chọn)**: tổng thưởng xếp hạng đã trả cho người đó trong **7 ngày coin gần nhất** (hôm nay và 6 ngày
  trước, đếm trong sổ: `idem_key LIKE 'rank:%'`, kể cả nhân vật đã xoá) cộng bậc này **không quá 600 coin**. Vượt thì bậc đó
  **chờ, không mất**, trả ở lần tính sau khi cửa sổ có chỗ. 600 = đúng một nhân vật lên thẳng top 10, nên người tạo thật không bị
  chặn ở nhân vật đầu tiên; xoá rồi đăng lại, hay "Nhân bản" rồi công khai để lấy lại thưởng thì tối đa 600 coin mỗi 7 ngày.

Trả = `post(conn, người tạo, +thưởng, 'creator_milestone', rank_key, card_id=X, milestone=N)` rồi đổi dòng `creator_rank_tiers`
sang `paid` với `ledger_id`, `paid_at`. Gọi lại bao nhiêu lần, hay hai request cùng tính, vẫn chỉ một dòng sổ cho mỗi
`(X, N)` (khoá chính + `idem_key`).

Các trường hợp:

- **Nhân vật về Riêng tư** (người tạo tắt hay chủ máy ẩn): rời bảng ở lần tính sau; bậc `waiting` chờ tới khi công khai lại.
- **Nhân vật bị xoá**: `creator_rank_tiers`, `hot_board`, `card_public_since` của nó bị xoá (CASCADE); coin đã trả **giữ nguyên**
  trong sổ; bậc đang chờ (`waiting`, chưa trả vì trần hay coin tắt) **mất cùng nhân vật** (tạm chọn: chỉ nhân vật còn công khai
  mới được trả). Đăng lại nhân vật mới thì đếm người chơi lại từ 0 (§5.1) và bị trần 600 coin/7 ngày.
- **Người chơi xoá tài khoản**: dòng `creator_players` của họ mất, nhân vật có thể tụt hạng; thưởng đã trả không bị thu lại.
- **Người chơi bị tạm khoá** **(tạm chọn)**: không được đếm (bảng, số người chơi trong trình sửa, điều kiện +50) tới khi mở khoá.
  Chủ máy khoá tài khoản phụ thì nhân vật tụt hạng ở lần tính sau; thưởng đã trả không bị thu lại.
- **Thưởng mốc cũ**: dòng `milestone:` đã trả trước khi đổi luật giữ nguyên, không trừ vào thưởng xếp hạng, không tính vào trần
  **(tạm chọn)**. Không trả thêm mốc nào nữa.

### 5.5 Thưởng công khai lần đầu **(PO chốt 2026-11-14 22:15, 5A)**

- **+50 coin, một lần mỗi tài khoản** (`first_public:<account_id>`), khi **một** nhân vật của tài khoản đó đủ cả hai:
  đã công khai **liên tục ít nhất 24 giờ** (`card_public_since.since ≤ now − 24h`) **và** có **ít nhất 1 người chơi** (§5.1).
- `card_public_since`: ghi `since = now` khi nhân vật chuyển từ Riêng tư sang Công khai (`PUT /api/cards/{id}`, cả khi tạo mới ở
  trạng thái công khai); xoá dòng khi về Riêng tư (người tạo tắt, hay chủ máy ẩn). Bật lại thì đếm 24 giờ lại từ đầu: bật rồi tắt
  ngay không được gì.
- Kiểm ở `hot.settle_rewards` (mỗi lần tính bảng, cho mọi tài khoản) và trong checkin của chính tài khoản đó. Chủ máy không bao giờ
  nhận (không ghi gì). Người tạo bị khoá hay coin tắt: chờ. Không tính vào trần 600.
- Không cần nhân vật đó có hạng nào (chỉ cần 1 người chơi).

### 5.6 Khoá sổ khi id nhân vật bị dùng lại

SQLite dùng lại id lớn nhất vừa bị xoá. Như `milestone_key` cũ: nếu `rank:<X>:<N>` đã có trong sổ mà nhân vật hiện tại chưa có
dòng `creator_rank_tiers (X, N)`, khoá thành `rank:<X>:<N>:<uid của nhân vật mới>`.

### 5.7 Người tạo thấy gì

- **Trình sửa nhân vật** (phần "Cơ bản", dưới công tắc "Công khai"), nhân vật đã lưu công khai. `GET /api/cards/{id}` của chủ
  nhân vật có `creator: {players, rank, next_tier, next_reward, waiting_coins, board_creators}` (`players`: người chơi đang hoạt
  động; `rank` null khi chưa có trên bảng; `next_tier` theo hạng hiện tại (`hot.next_tier_for`): trong các bậc chưa đạt, nếu hạng
  đã đủ cho bậc nào (chỉ còn chờ bảng đủ người tạo) thì bậc nhỏ nhất trong số đó, không thì bậc lớn nhất còn lại; null khi đạt
  đủ; `next_reward` null với chủ máy, coin tắt, hay đạt đủ; `waiting_coins` = tổng thưởng `waiting`; `board_creators` = `creators`
  của §5.3, đếm lúc đọc). Chữ (`creatorLogic.ts`):
  - dòng đậm: **"{n} người chơi · Hạng {r} Nhân vật hot"**, chưa có hạng: **"{n} người chơi · Chưa có trên bảng Nhân vật hot"**;
  - dòng thưởng: **"Bậc thưởng tiếp theo: top {N} (+{c} coin)"**; chủ máy / coin tắt: "Bậc tiếp theo: top {N}"; đạt đủ:
    **"Đã nhận đủ thưởng xếp hạng"**;
  - khi `board_creators < N` (có coin): **"Thưởng top {N} chỉ có khi bảng có nhân vật của ít nhất {N} người tạo khác nhau (hiện
    có {k})."** để người tạo hạng 1 trên bảng nhỏ biết vì sao chưa có coin;
  - có thưởng chờ: **"Thưởng đang chờ: +{w} coin (tối đa 600 coin mỗi 7 ngày)"**;
  - câu nhỏ: "Người chơi là tài khoản khác đã trò chuyện với nhân vật này ít nhất 3 câu trả lời, ở 2 ngày khác nhau. Bảng xếp
    hạng cập nhật mỗi giờ."
- **Lịch sử ví** (`label` server dựng theo tiền tố `idem_key`): `rank:` → **"{tên} vào top {N} Nhân vật hot"**; `first_public:` →
  **"Thưởng công khai nhân vật lần đầu"**; dòng cũ `milestone:` → "{tên} đạt {m} người chơi" (giữ). `{tên}` chỉ lấy từ card của
  chính tài khoản (luật §10.5); không thấy thì "nhân vật".
- **Bảng xếp hạng** `#/explore/hot`: thành viên (coin bật) thấy câu "Nhân vật của bạn vào top 100, top 50, top 10 thì bạn được
  thưởng 100, 200, 300 coin."; chủ máy và coin tắt không có câu này.

## 6. Nhiệm vụ ngày (F45)

### 6.1 Ba nhiệm vụ

| `mission` | Tên trên giao diện | Điều kiện trong ngày coin | Thưởng | Nhận |
|---|---|---|---|---|
| `ad` | "Xem quảng cáo" | xem xong một quảng cáo mẫu 15 giây | +5 mỗi lần, tối đa 3 lần | nút "Nhận 5 coin" trong hộp quảng cáo |
| `characters` | "Trò chuyện với 3 nhân vật khác nhau" | có câu trả lời đã trả coin với 3 `char_key` khác nhau | +10 | nút "Nhận" |
| `turns` | "Gửi 20 lượt" | 20 câu trả lời đã trả coin loại `send` hoặc `retry` (không tính "Tạo lại") **(tạm chọn)** | +5 | nút "Nhận" |

- `char_key` = nhân vật gốc nếu story chơi bằng bản sao, không thì nhân vật của story. Hai story với cùng một nhân vật là một.
- Chat thử ở Studio (`mode = 'test'`) không tính cho `characters` hay `turns` **(tạm chọn)**: nhiệm vụ là để chơi story.
- Tổng tối đa = 3×5 + 10 + 5 = **30 coin/ngày**. Trần 30 vẫn được kiểm ở server mỗi lần nhận, để sau này thêm nhiệm vụ không vượt
  trần. Hàm `post_mission(conn, account, mission)` làm **trong một `BEGIN IMMEDIATE`**: đọc tổng `delta` các dòng
  `kind = 'mission'` của ngày coin, (quảng cáo) đếm số lần đã nhận `n` để dựng `idem_key …:ad:<n+1>`, kiểm điều kiện, kiểm
  tổng + phần sắp nhận ≤ 30, rồi `post()`. Không đọc ở một transaction rồi ghi ở transaction khác.
- Nhận là bấm nút (không tự cộng) **(tạm chọn)**: nhận hai lần cùng ngày cùng nhiệm vụ trả dòng cũ (idem_key), không cộng thêm.
- Qua 00:00 giờ Việt Nam: tiến độ về 0, nhiệm vụ chưa nhận của hôm qua mất.
- Chủ máy: không có nhiệm vụ (`GET /api/coins/missions` trả `missions: []`, `unlimited: true`).

### 6.2 Quảng cáo mẫu, trung thực và không lách được ([quyết định](../wiki/decisions/nhiem-vu-va-quang-cao-mau.md))

- Hộp có tiêu đề **"Quảng cáo mẫu"** và câu **"Đây là quảng cáo mẫu của Lyris, chưa phải quảng cáo thật."** Nội dung là một thẻ
  giới thiệu tính năng của chính Lyris (ảnh và chữ có sẵn trong repo), không gọi mạng ngoài, không cookie, không đo gì thêm.
- `POST /api/coins/ads/start`: còn lượt (< 3 lần đã nhận hôm nay) thì đánh dấu `cancelled_at` cho lượt xem dở trước đó của tài
  khoản và tạo `coin_ad_views` mới (`started_at` = giờ server); trả `{ad_id, seconds: 15}`. Hết lượt: 409 `ad_limit` "Hôm nay bạn
  đã xem đủ 3 quảng cáo."
- Giao diện đếm ngược "Còn 15 giây"; nút "Nhận 5 coin" khoá tới khi hết giờ. Bấm "Đóng" trước khi nhận: giao diện gọi
  `POST /api/coins/ads/{ad_id}/cancel` (đặt `cancelled_at`; gọi lại không lỗi), lượt xem đó không bao giờ nhận được nữa.
- `POST /api/coins/ads/{ad_id}/claim`: server kiểm, theo đồng hồ server (không tin giờ của trình duyệt), trong cùng transaction
  với `post()`:
  - `ad_id` không có hoặc của tài khoản khác: 404;
  - đã nhận rồi: trả kết quả cũ, không cộng thêm;
  - `now - started_at < 15 giây`: 409 `ad_not_finished` "Quảng cáo chưa xem xong.";
  - đã huỷ ("Đóng" hoặc bị lượt xem mới thay), quá 10 phút, hoặc khác ngày coin với lúc bắt đầu: 409 `ad_expired`
    "Lượt xem này đã hết hạn. Hãy xem lại.";
  - đã đủ 3 lần hôm nay: 409 `ad_limit`; vượt trần 30: 409 `mission_cap`.
  Ghi sổ `mission:<acc>:<day>:ad:<n>`.
- **Giới hạn biết trước** (ghi trong [quyết định](../wiki/decisions/nhiem-vu-va-quang-cao-mau.md)): "Đóng" chỉ chặn được giao diện
  thật. Một script gọi thẳng `start`, đợi 15 giây, rồi `claim` (không gọi `cancel`) vẫn nhận được, giống hệt người xem hết quảng
  cáo. Quảng cáo mẫu không có cách nào biết người dùng có nhìn màn hình. Thiệt hại tối đa là 15 coin/ngày/tài khoản (3 × 5), dưới
  trần 30. Khi có mạng quảng cáo thật thì dùng xác nhận phía server của mạng đó.
- Thời lượng mặc định 15 giây, nằm trong `Settings.ad_seconds`. Không có biến môi trường nào đổi được nó: chỉ server giả của bot
  (`environment/fake-server.py`) dựng app với `ad_seconds=2` để bot không phải chờ **(tạm chọn)**.
- Sau này thay bằng mạng quảng cáo thật: cần đồng ý quảng cáo cá nhân hoá, kê khai trong Chính sách, xác nhận phía server
  (server-side verification callback) của mạng quảng cáo, và xem lại luật cửa hàng (§12). Ngoài phạm vi kế hoạch này.

## 7. API

Mọi route dưới đây cần đăng nhập (`CurrentAccount`), trừ khi ghi "chủ máy" (`owner_auth`, 403 `owner_only`). Ghi (POST) cần
`X-Lyris: 1` như mọi route ghi khác. `test_isolation_sweep.py` phải phân loại mọi route mới.

| Route | Trả | Ghi chú |
|---|---|---|
| `GET /api/coins/wallet` | `{balance, available, unlimited, price_per_reply: 6, enabled}` | `available` = số dư − giữ chỗ |
| `POST /api/coins/checkin` | `{granted, amount, wallet}` | §3.4 |
| `GET /api/coins/history?before=<id>&limit=30` | `{items: [{id, delta, kind, label, created_at, balance_after, story_id?}], next}` | chỉ của mình; `label` server dựng (§10.5) |
| `GET /api/coins/packs` | `{test_mode, packs: [{id, coins, bonus, price_vnd}], contact}` | §4.1 |
| `POST /api/coins/redeem` `{code}` | `{amount, wallet}` | 422 `topup_code_invalid`, 422 `topup_code_owner` (chủ máy), 429 `rate_limited` (10 lần sai/giờ/tài khoản) |
| `GET /api/coins/missions` | `{coin_day, earned_today, cap: 30, missions: [{id, progress, target, reward, claimed, claimable, remaining}], unlimited, enabled}` | §6; chủ máy / coin tắt: `missions: []`, ghi thì 409 `no_missions` (tạm chọn) |
| `POST /api/coins/missions/{characters\|turns}/claim` | `{amount, wallet}` | 409 `mission_not_done`, 409 `mission_cap` |
| `POST /api/coins/ads/start` | `{ad_id, seconds}` | 409 `ad_limit` |
| `POST /api/coins/ads/{ad_id}/claim` | `{amount, wallet}` | 409 `ad_not_finished`, `ad_expired`, `ad_limit`, `mission_cap`; 404 lượt xem không của mình |
| `POST /api/coins/ads/{ad_id}/cancel` | `{ok: true}` | gọi khi bấm "Đóng"; gọi lại không lỗi; 404 lượt xem không của mình |
| `GET /api/admin/coins/codes` | danh sách mã | chủ máy |
| `POST /api/admin/coins/codes` `{pack_id \| amount, note, expires_days}` | `{code, …}` (một lần) | chủ máy; 422 `topup_code_limit` khi đã có 50 mã còn hiệu lực |
| `POST /api/admin/coins/codes/{id}/revoke` | mã | chủ máy |
| `POST /api/admin/accounts/{id}/coins` `{delta, reason, request_id}` | `{balance, available}` | chủ máy; 422 `adjust_too_large`; 409 `idem_conflict`; không áp dụng cho chủ máy (422) |
| `GET /api/admin/coins/log` | nhật ký + tổng 30 ngày | chủ máy |

Tập route có tiền tố `/api/coins/` và `/api/admin/coins/` (cộng `POST /api/admin/accounts/{id}/coins`) **đúng bằng** bảng trên,
không hơn: không có route nào nhận thông tin thẻ, ví điện tử hay thanh toán (test so `app.routes` với danh sách này).

Đổi ở API có sẵn:

- `GET /api/admin/accounts`: mỗi thành viên thêm `coin_balance` (chủ máy: `null`).
- `GET /api/cards/{id}` (chủ nhân vật, nhân vật công khai): thêm `creator: {players, rank, next_tier, next_reward, waiting_coins, board_creators}`
  (F44 làm lại, §5.7; bản cũ `{players, next_milestone, next_reward}` bị thay).
- Mới (F46, ngoài tiền tố `/api/coins/`): `GET /api/explore/hot?limit=<1..100>` → `{updated_at, ranked, items: [{rank, card_id,
  name, avatar_url, creator_handle, players}]}` (§5.2). `POST /api/coins/checkin` gọi thêm `hot.refresh_if_stale` và kiểm thưởng
  công khai lần đầu của chính tài khoản (§5.5); hình dạng trả về không đổi.
- `PUT /api/cards/{id}` (và tạo mới): ghi/xoá `card_public_since` khi đổi Riêng tư ⇄ Công khai (§5.5); không còn gọi trả mốc.
- `POST /api/auth/signup`: cộng quà 300 qua `insert_member` (§3.4). `POST /api/auth/login`: gọi checkin.
- `POST /api/cards/test-chat`: giữ chỗ và trừ 6 mỗi câu trả lời có chữ, 402 `coins_required` khi không đủ (§3.1).
- "Tải dữ liệu của tôi" (F35): thêm `coins: {balance, ledger: […]}`; không có mã nạp đầy đủ (chỉ có hash, không xuất).
- Xoá tài khoản (F35): mọi bảng coin có khoá ngoại CASCADE hoặc SET NULL; test của F35 quét mọi bảng.

## 8. Hai tab, nhiều thiết bị, đua nhau

- Một tài khoản chỉ sinh một lượt một lúc (cổng sinh, F32) và chỉ có một giữ chỗ (`idx_coin_holds_one_open`). Tab thứ hai gửi
  khi tab đầu đang chờ câu trả lời: 409 như hiện nay.
- Mọi ghi sổ đi qua `post()` trong `BEGIN IMMEDIATE`; `CHECK (balance >= 0)` là lưới an toàn cuối.
- Hai tab cùng bấm "Nhận" một nhiệm vụ, hai thiết bị cùng mở app lúc 00:00: `idem_key` UNIQUE, chỉ một dòng.
- Hai người cùng nhập một mã nạp: `UPDATE … WHERE used_at IS NULL` chỉ đổi một dòng.
- Hai request cùng tính bảng "Nhân vật hot": `BEGIN IMMEDIATE` + kiểm lại "đã cũ chưa" trong transaction; thưởng xếp hạng có khoá
  chính `creator_rank_tiers (card_id, tier)` + `idem_key`, thưởng công khai lần đầu có khoá chính `creator_first_public` +
  `idem_key`: chỉ trả một lần.
- Ví trên giao diện làm mới khi: mở app, quay lại tab (`visibilitychange`), sau mỗi câu trả lời (`done`/`error`), sau nhận
  thưởng, sau 402.

## 9. Lạm dụng và cách chặn

| Cách lách | Chặn |
|---|---|
| Tạo nhiều tài khoản để lấy quà 300 coin | Tạo tài khoản cần mã mời của chủ máy, mã dùng một lần, tối đa số mã còn hiệu lực (F30). Chủ máy là người phát mã. |
| Tài khoản ảo "chơi" nhân vật của mình để leo bảng "Nhân vật hot" | Giá coin **không** chặn được (18 coin lấy từ quà miễn phí). Chặn bằng: mã mời của chủ máy cho mỗi tài khoản; người chơi cần ≥ 3 câu trả lời đã trả coin ở ≥ 2 ngày coin; bậc top N chỉ trả khi bảng có nhân vật của ≥ N người tạo khác nhau; người chơi bị tạm khoá không được đếm; trần 600 coin thưởng xếp hạng mỗi 7 ngày cho mỗi người tạo; "Nhật ký" của chủ máy hiện mọi thưởng sáng tác (§5.1, §5.3, §5.4). |
| Xoá rồi đăng lại, hoặc "Nhân bản" rồi công khai, để lấy lại thưởng xếp hạng với cùng nhóm bạn | Trần 600 coin/7 ngày theo người tạo, thưởng vượt trần chờ (§5.4); chủ máy thấy trong "Nhật ký" và thu lại bằng "Cộng/trừ coin". |
| Bật Công khai rồi tắt ngay để lấy +50 | +50 chỉ trả khi nhân vật công khai liên tục ≥ 24 giờ và có ≥ 1 người chơi; mỗi tài khoản một lần (§5.5). |
| Dán thẻ bất kỳ vào chat thử ở Studio để chat miễn phí | Chat thử cũng tốn 6 mỗi câu trả lời (§3.1). |
| Tự chơi nhân vật của mình | Người tạo không bao giờ được tính (§5.1). |
| Bấm "Tạo lại câu trả lời" liên tục | Mỗi lần tốn 6 coin; "Gửi 20 lượt" không tính "Tạo lại". |
| Gọi API nhận thưởng quảng cáo mà không xem | Server ghi giờ bắt đầu, kiểm đủ 15 giây theo đồng hồ server, tối đa 3 lần/ngày, trần 30. "Đóng" gọi `cancel`. Script đợi đủ 15 giây vẫn nhận được: giới hạn biết trước, tối đa 15 coin/ngày (§6.2). |
| Chủ máy trừ tay đúng lúc thành viên đang chờ câu trả lời | Trừ tay kiểm theo số dùng được (số dư − giữ chỗ), nên lượt đang chạy luôn trừ được, câu trả lời không bao giờ mất (§4.4, §3.2). |
| Đổi giờ máy để nhận đăng nhập hai lần | Ngày coin tính bằng giờ server, không phải trình duyệt. |
| Đoán mã nạp | 12 ký tự base32 (~60 bit), 10 lần sai/giờ/tài khoản rồi 429, cùng một câu lỗi cho mọi trường hợp. |
| Dừng ngay khi có chữ đầu tiên để "đọc chùa" | Có chữ là trừ 6 (§3.2). |
| Gửi rồi đóng tab trước chữ đầu tiên để thử nhiều lần | Không tốn coin nhưng cũng không có gì; cổng sinh vẫn giới hạn 1 lượt/tài khoản. |
| Thành viên bị khoá vì lạm dụng | Chủ máy tạm khoá (F30) và trừ coin bằng "Cộng/trừ coin" có lý do. |

## 10. Giao diện

Theo [wiki/design/style.md](../wiki/design/style.md): màu chỉ qua token, không emoji, chữ kỹ thuật không lên giao diện, nút qua
`Button`/`IconButton` (chạm 44px ở điện thoại). Biểu tượng coin: icon mới `IconCoin` (đồng xu nét 1.8px, màu `accent-2`) trong
`components/icons.tsx`. Số viết theo kiểu Việt Nam: "1.200 coin".

### 10.1 Chip trên thanh đầu

`HubHeader` (ba tab chính), trước nút đổi theme: chip `surface-2`, icon coin `accent-2`, số dư. aria-label
**"Coin: {n}. Mở ví coin"**. Chạm mở `#/coins`. Chủ máy và `LYRIS_COINS=0`: không có chip **(tạm chọn)**. Header màn chat không có
chip **(tạm chọn: header chat đã chật, 44px; hết coin thì khối ở ô nhập đã báo)**.

### 10.2 Màn "Ví coin" (`#/coins`)

Xem [wiki/screens/coin-wallet.md](../wiki/screens/coin-wallet.md). Tiêu đề "Ví coin"; số dư lớn; dòng "Mỗi câu trả lời của nhân vật
tốn 6 coin."; nút "Nạp coin" (chính) và "Nhiệm vụ"; "Lịch sử".

### 10.3 Ô nhập khi hết coin

Khi số coin dùng được < 6 (thành viên): ô nhập `disabled`, nút gửi và "+" khoá; thay chỗ banner trên ô nhập là khối
**"Bạn đã hết coin"** + "Mỗi câu trả lời cần 6 coin." + nút **"Nạp coin"** (→ `#/coins/top-up`) và **"Nhiệm vụ"** (→ `#/missions`).
"Tạo lại câu trả lời" khoá với lý do (`lib/actionLock.ts`) "Cần 6 coin để tạo lại." Bản nháp trong ô nhập giữ nguyên. Story và DM
như nhau; ô nhập của chat thử ở Studio cũng vậy. Có coin trở lại (quay lại từ Nạp coin / Nhiệm vụ) thì ô nhập mở lại không cần tải
lại trang: trạng thái khoá tính từ kho ví dùng chung (`lib/coins.ts`, `composerCoinLock(wallet)`), và kho ví làm mới theo §8.

### 10.4 Tài khoản

Sheet "Tài khoản": dưới khối tài khoản, hàng **"Coin"** với số dư ("300 coin") và nút **"Mở ví coin"**. Chủ máy: "Tài khoản quản lý
không tốn coin." (không có nút).

### 10.5 Chữ (bảng chữ)

| Chỗ | Chữ |
|---|---|
| Chip | "{n}" · aria-label "Coin: {n}. Mở ví coin" |
| Ví | "Ví coin", "Mỗi câu trả lời của nhân vật tốn 6 coin.", "Nạp coin", "Nhiệm vụ", "Lịch sử", "Chưa có gì trong lịch sử.", "Xem thêm" |
| Lịch sử (`label`) | "Quà tạo tài khoản", "Quà mở ví", "Đăng nhập hôm nay", "Câu trả lời của {tên}" (gộp: "{k} câu trả lời của {tên}"), "Chat thử ở Studio", "Nhiệm vụ: Xem quảng cáo", "Nhiệm vụ: Trò chuyện với 3 nhân vật khác nhau", "Nhiệm vụ: Gửi 20 lượt", "{tên} vào top {N} Nhân vật hot", "Thưởng công khai nhân vật lần đầu", dòng cũ "{tên} đạt {10} người chơi", "Nạp bằng mã", "Người quản lý điều chỉnh: {lý do}". `{tên}` chỉ lấy từ story/card của chính tài khoản đó (id đã xoá có thể được dùng lại cho nhân vật của người khác); không thấy thì "nhân vật" |
| Đăng nhập | "+60 coin cho hôm nay" |
| Hết coin | "Bạn đã hết coin", "Mỗi câu trả lời cần 6 coin.", "Nạp coin", "Nhiệm vụ", lý do khoá "Cần 6 coin để tạo lại." |
| Nạp coin | "Nạp coin", "Chế độ thử: Lyris chưa bán coin. Nhập mã nạp người quản lý tặng bạn.", "Giá dự kiến", "{n} coin", "Tặng thêm {k}", "{giá}đ", ô "Mã nạp", "Dùng mã", "Đã nạp {n} coin.", "Mã nạp không đúng hoặc đã hết hạn.", hộp gói: "Gói {n} coin · Giá dự kiến {giá}đ", "Giá dự kiến khi Lyris ra mắt. Ở chế độ thử chưa bán coin; người quản lý có thể tặng bạn mã nạp để thử.", "Đóng" |
| Nhiệm vụ | "Nhiệm vụ hôm nay", "Đã nhận {x}/30 coin hôm nay", "Làm mới lúc 0:00", "Xem quảng cáo", "Trò chuyện với 3 nhân vật khác nhau", "Gửi 20 lượt", "Xem", "Nhận", "Đã nhận", "Hôm nay bạn đã xem đủ 3 quảng cáo." |
| Quảng cáo | "Quảng cáo mẫu", "Đây là quảng cáo mẫu của Lyris, chưa phải quảng cáo thật.", "Còn {s} giây", "Nhận 5 coin", "Đóng", "Quảng cáo chưa xem xong.", "Lượt xem này đã hết hạn. Hãy xem lại." |
| Sáng tác (F44 làm lại, §5.7) | "{n} người chơi · Hạng {r} Nhân vật hot", "{n} người chơi · Chưa có trên bảng Nhân vật hot", "Bậc thưởng tiếp theo: top {N} (+{c} coin)", "Bậc tiếp theo: top {N}" (chủ máy, coin tắt), "Thưởng top {N} chỉ có khi bảng có nhân vật của ít nhất {N} người tạo khác nhau (hiện có {k}).", "Đã nhận đủ thưởng xếp hạng", "Thưởng đang chờ: +{w} coin (tối đa 600 coin mỗi 7 ngày)" |
| Nhân vật hot (F46) | "Nhân vật hot", "Xếp theo tổng số người chơi. Cập nhật mỗi giờ.", "Cập nhật lúc {HH:mm}", "{n} người chơi", "bởi @handle", "Xem bảng xếp hạng", "Về Khám phá", "Nhân vật của bạn vào top 100, top 50, top 10 thì bạn được thưởng 100, 200, 300 coin.", "Chưa có nhân vật nào trên bảng xếp hạng.", "Công khai nhân vật của bạn trong Studio để người khác cùng chơi.", "Mở Studio", "Không tải được bảng xếp hạng.", "Thử lại" |
| Quản trị | tab "Coin", "Mã nạp", "Tạo mã nạp", "Số coin", "Gói", "Ghi chú", "Hết hạn sau", "Tạo mã", "Mã nạp mới", "Sao chép mã", "Nhật ký", "Thưởng xếp hạng top {N}", "Thưởng công khai lần đầu", dòng cũ "Thưởng mốc {m} người chơi", "Cộng/trừ coin", "Lý do", "Lưu", "Không trừ được quá số coin dùng được ({n} coin).", "Đã có 50 mã nạp còn hiệu lực. Huỷ bớt mã cũ rồi tạo mã mới." |
| Tài khoản | "Coin", "{n} coin", "Mở ví coin", "Tài khoản quản lý không tốn coin." |

Màn của thành viên không có chữ "chủ máy" (luật chữ cho người ngoài; hiện `pages/auth/logic.test.ts` chỉ kiểm màn đăng nhập):
dùng "người quản lý". Chữ của màn coin cho thành viên (chip, ví, ô nhập hết coin, nạp coin, nhiệm vụ, quảng cáo) nằm trong một
module `frontend/src/lib/coinCopy.ts`; `coins.test.ts` kiểm mọi chuỗi trong đó không có "chủ máy", "token", "credits", "model",
"Ollama" (không phân biệt hoa thường). Chữ của `#/admin` (chỉ chủ máy thấy) để riêng, không nằm trong module này.

## 11. Số liệu: sự kiện mới cho `analytics/events.py`

Thuộc tính chỉ là enum, true/false, số trong khoảng; không chữ tự do (không tên nhân vật, không lý do điều chỉnh, không mã nạp).
Khi build: thêm vào `events.py`, `frontend/src/lib/track.ts` và **cùng lúc** vào [tracking-plan.md §4](tracking-plan.md#4-event-catalog)
(test của F34 đối chiếu hai bên). Chưa thêm vào tracking-plan.md lúc lập kế hoạch để không làm đỏ F34.

| Sự kiện | Nguồn | Thuộc tính | Ghi ở đâu |
|---|---|---|---|
| `coins_spent` | S | `mode: story/dm/test`, `kind: send/retry/regenerate` | `charge` |
| `coins_released` | S | `kind`, `reason: error/empty/cancelled/queue_timeout/save_failed/invalid/restart` | nhả giữ chỗ; `restart` phát bằng `Tracker.emit_detached` (lúc khởi động, không có request) |
| `coins_insufficient` | S | `mode: story/dm/test`, `kind` | trả 402 |
| `coins_granted` | S | `source: signup/daily/mission_ad/mission_characters/mission_turns/creator_rank/creator_first_public/topup_code` (F44 làm lại: `creator_milestone` thay bằng hai giá trị mới), `amount: Count(1, 10000)` | `post()` với delta > 0. Quà mở ví (`backfill_grant`) do migration SQL ghi nên **không phát** sự kiện. |
| `coins_adjusted` | S | `direction: up/down`, `amount_bucket: 1_50/51_300/301_plus` | chủ máy điều chỉnh |
| `wallet_viewed` | C | `from: header/account/composer/link` | mở `#/coins` |
| `topup_viewed` | C | `from: wallet/composer/link` | mở `#/coins/top-up` |
| `topup_pack_selected` | C | `pack: p100/p550/p1200/p2500` | chạm gói |
| `topup_code_redeemed` | S | `pack: p100/p550/p1200/p2500/custom` | nhập mã đúng |
| `topup_code_failed` | S | `reason: invalid/expired/used/revoked/rate_limited` | nhập mã sai |
| `topup_code_created` | S | `pack`, `expires_days: 1/7/30` | chủ máy tạo mã |
| `missions_viewed` | C | `from: wallet/composer/link` | mở `#/missions` |
| `ad_started` | S | | bắt đầu quảng cáo mẫu |
| `mission_claimed` | S | `mission: ad/characters/turns` | nhận thưởng |
| `creator_rank_reached` (thay `creator_milestone_reached`, F44 làm lại) | S | `tier: 100/50/10`, `paid: bool` | `hot.settle_rewards`, lúc một bậc được ghi (`paid` = trả ngay); phát tách như sự kiện cũ (không gắn tài khoản, thiết bị, story) |
| `hot_board_viewed` (F46) | C | `from: explore/link` | mở `#/explore/hot` (`explore` = bấm "Xem bảng xếp hạng") |
| `explore_searched` (F47) | C | `has_results: bool` | ô "Tìm nhân vật" ổn định sau debounce, tối đa một lần cho mỗi chuỗi tìm khác nhau; không gửi chữ người dùng gõ |

Chỉ số mới cho trang "Số liệu" (sau F45): coin phát ra / coin tiêu mỗi ngày; % thành viên chạm 0 coin trong 7 ngày; phễu
`coins_insufficient` → `topup_viewed` → `topup_code_redeemed`; tỉ lệ hoàn thành từng nhiệm vụ; số nhân vật đạt từng bậc xếp hạng; % lượt mở Khám phá có dùng ô tìm.

Khi build F44/F46/F47: thêm/bỏ ba dòng trên **cùng lúc** trong `events.py`, `track.ts` và `tracking-plan.md` (bỏ
`creator_milestone_reached`, thêm `creator_rank_reached`, `hot_board_viewed`, `explore_searched`: 55 → 57, dưới trần 60 của F34).

## 12. Tuân thủ và Điều khoản

Thêm vào [docs/legal/terms.md](legal/terms.md) (vi + en) một mục **"Coin"**, đổi `LEGAL_VERSION` (tài khoản cũ được hỏi đồng ý lại,
F35). **Kể cả chủ máy**: lần mở app đầu tiên sau khi build xong, chủ dự án (đang dùng app hằng ngày) cũng thấy màn đồng ý một lần.

- Coin là đơn vị ảo để dùng tính năng trong Lyris; **không phải tiền**, không có giá trị tiền tệ, **không đổi ra tiền**, không
  rút, không chuyển hay bán cho người khác, không có lãi.
- Giá (6 coin mỗi câu trả lời), quà và nhiệm vụ có thể thay đổi; thay đổi được báo trước trong app.
- **Chế độ thử:** Lyris chưa bán coin và chưa thu tiền. Coin có được từ mã nạp, quà, nhiệm vụ, thưởng; không có hoàn tiền vì không
  có khoản thanh toán nào. **Mã nạp ở chế độ thử được tặng, không bán**; không ai được bán mã nạp hay coin của Lyris.
- **Coin của chế độ thử khi Lyris ra mắt:** mọi số dư được **đặt lại về 0** **(PO chốt 2026-11-14)**. Lyris báo trong app ít nhất 30 ngày trước
  ngày đặt lại. Điều khoản ghi điều này ngay từ bây giờ để không có tranh chấp về sau.
- Xoá tài khoản thì coin còn lại mất. Coin có được do lạm dụng (tài khoản ảo, lách nhiệm vụ) có thể bị người quản lý thu hồi.
- Thưởng sáng tác không phải tiền công hay hợp đồng; không có chia sẻ doanh thu.
- Quảng cáo mẫu không gửi dữ liệu cho bên quảng cáo nào (Lyris vẫn ghi số liệu sử dụng như mọi màn khác, theo Chính sách).
- Người dưới 16 tuổi cần phép của cha mẹ/người giám hộ (đã có, §1). Khi có thanh toán thật: người dưới 18 tuổi cần cha mẹ/người
  giám hộ đồng ý trước khi mua coin.

Chính sách quyền riêng tư ([docs/legal/privacy.md](legal/privacy.md), vi + en): kê thêm **sổ coin** (số coin, thời điểm, loại;
không nội dung) trong dữ liệu được lưu, giữ tới khi xoá tài khoản, có trong "Tải dữ liệu của tôi"; và ghi quảng cáo mẫu không
gửi dữ liệu cho bên thứ ba. Có test (`test_terms_have_coin_section_and_version_bumped`) kiểm cả terms lẫn privacy, cả hai ngôn ngữ.

Không có phần thưởng ngẫu nhiên (không hộp quà, không quay số): tránh bị coi là cờ bạc và luật loot box của cửa hàng.

**Khi ra mắt có tiền thật (ngoài kế hoạch này):** cổng thanh toán được cấp phép ở Việt Nam trên web (hoá đơn điện tử, điều khoản
bán hàng, chính sách hoàn tiền); trong app cửa hàng phải dùng Google Play Billing / Apple In-App Purchase cho coin (hàng số);
quảng cáo thật cần đồng ý quảng cáo cá nhân hoá, ATT trên iOS, kê khai Data safety; **người dưới 16 tuổi không được nhận quảng
cáo cá nhân hoá** (chỉ quảng cáo không cá nhân hoá, đánh dấu tuổi với mạng quảng cáo); xem lại thuế và nghĩa vụ của đơn vị phát hành;
và thực hiện điều Điều khoản đã hứa về coin của chế độ thử.
Cập nhật [compliance.md §5.4](compliance.md) lúc đó.

## 13. Kiểm tra

- Backend (`backend/.venv/bin/pytest`, DB tạm, `FakeLLM`, `clock.now` giả): tên test ở mục "Tests" của F42–F45.
- Test cũ chat bằng tài khoản thành viên nhiều hơn 50 câu trả lời sẽ hết coin: fixture tạo thành viên được nạp thêm qua
  `post(... kind='admin_adjust')`, hoặc đặt `LYRIS_COINS=0` cho test không nói về coin. Không sửa assert của test cũ.
- Test chat thử ở Studio bằng tài khoản thành viên giờ tốn coin: 300 coin quà đủ cho 50 câu trả lời; test nào cần nhiều hơn thì
  nạp thêm như trên, không sửa assert.
- Server giả của bot (`environment/fake-server.py`): thành viên tạo bằng `insert_member` nên tự có ví 300 (§3.4). Thêm:
  - `@hetcoin`: tạo bằng `insert_member` rồi `post(-300, 'admin_adjust', reason='bot')` về 0 coin; có một story chế độ Story và
    một story DM;
  - `@coinmoi`: thành viên mới, chưa checkin; chỉ check bot "+60 coin cho hôm nay" đăng nhập bằng tài khoản này;
  - `ad_seconds=2`; một nhân vật công khai đã có vài người chơi (đã làm, F44 bản cũ: không sửa server giả mà dựng 12 người chơi trong DB tạm bằng `environment/seed-creator-players.py`, do bot gọi). F44 làm lại và F46 dùng lại script này: script tính lại bảng ngay sau khi dựng người chơi (`hot.compute`, như lần tính mỗi giờ; app đã tính bảng lúc bot mở app nên `GET /api/explore/hot` chỉ tính lại sau 60 phút), nhân vật đó ở hạng 1, có ảnh (bot tải ảnh lên như ở Studio), rồi kiểm dòng "Hạng 1 Nhân vật hot" trong trình sửa và hàng của nhân vật đó ở `#/explore/hot`. Thưởng theo bậc cần ≥ 10 nhân vật được xếp hạng nên chỉ kiểm bằng unit (DB tạm, đồng hồ giả).
- Bot đo ở 390px, hai theme: chip không làm header tràn ngang; khối "Bạn đã hết coin" không che ô nhập.

## 14. Thứ tự làm

1. **F42 backend**: `0012_coins.sql`, `lyris/coins/` (`clock.py`, `ledger.py`, `holds.py`, `wallet.py`, `errors.py`), móc vào
   `ChatService._run`, `_persist`, `_save_aborted` và `POST /api/cards/test-chat`, `open_wallet` trong `auth/store.insert_member`,
   nhả lúc khởi động (chỉ trong `lifespan`), checkin, 402, `/api/coins/wallet|checkin|history`, sự kiện, xuất/xoá dữ
   liệu, Điều khoản + `LEGAL_VERSION`. Test trước.
2. **F42 frontend**: `IconCoin`, chip, `#/coins`, hàng "Coin" trong Tài khoản, khoá ô nhập, thông báo "+60 coin"; check bot; nhìn
   (`bot.mjs --look`, 390px, hai theme).
3. **F43**: gói, mã nạp, `#/coins/top-up`, tab "Coin" ở `#/admin`, "Cộng/trừ coin", nhật ký.
4. **F45**: tiến độ nhiệm vụ từ `coin_holds`, quảng cáo mẫu, `#/missions`, trần 30.
5. **F44** (bản cũ, đã làm): `creator_players`, `settle_milestones`, dòng người chơi trong trình sửa nhân vật.
6. **F44 làm lại + F46 + F47** (đã làm 2026-11-14): chép `0014_hot_board.sql` **trước** mọi `.py` (§2.2) → `lyris/coins/hot.py`
   (`rank_cards`, `refresh_if_stale`, `settle_rewards`, `first_public_check`) + bỏ trả mốc trong `creator.py` → `GET /api/explore/hot`,
   `card_public_since` trong `PUT /api/cards/{id}`, `creator` mới trong `GET /api/cards/{id}`, nhãn lịch sử/nhật ký → frontend:
   bỏ khung nổi bật, ô "Tìm nhân vật", dải "Nhân vật hot", màn `#/explore/hot`, dòng xếp hạng trong trình sửa → check bot → nhìn
   (`bot.mjs --look`, 390px, hai theme). Test trước.

## 15. Không làm ở kế hoạch này

Cổng thanh toán thật; mạng quảng cáo thật; giá theo độ dài câu trả lời; coin cho gợi ý, AI viết nháp (chờ PO); chuyển
coin giữa thành viên; bảng xếp hạng **tác giả** (chỉ có bảng xếp hạng **nhân vật**, F46); bảng theo tuần/tháng (PO chọn tổng
từ trước tới nay); thưởng theo tổng số lượt; nhiệm vụ một lần khác (ngoài thưởng công khai lần đầu).
