-- Coin (docs/coins.md §2): ví, sổ coin chỉ thêm, giữ chỗ khi sinh câu trả lời (F42); mã nạp và lần thử mã (F43);
-- quảng cáo mẫu của nhiệm vụ ngày (F45); người chơi và mốc thưởng sáng tác (F44).
-- Chỉ thêm bảng, không đổi bảng cũ, không xoá dữ liệu.

-- 1. Ví: số dư cache, đổi cùng transaction với dòng sổ (lyris/coins/ledger.py `post`).
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
-- Chỉ thêm. `ON DELETE SET NULL` của `actor_id` là một lệnh UPDATE và CÓ chạy trigger, nên:
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
    char_key       INTEGER,                       -- origin_card_id nếu là bản sao, không thì card_id; NULL khi 'test'
    origin_card_id INTEGER,                       -- nhân vật công khai gốc (bản sao), để đếm người chơi (F44)
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
    code_hash   BLOB NOT NULL UNIQUE,
    code_hint   TEXT NOT NULL,
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
CREATE TABLE coin_code_attempts (
    id          INTEGER PRIMARY KEY,
    account_id  INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    ok          INTEGER NOT NULL CHECK (ok IN (0, 1)),
    created_at  TEXT NOT NULL
);
CREATE INDEX idx_coin_code_attempts ON coin_code_attempts (account_id, created_at);

-- 5. Quảng cáo mẫu (F45): server ghi giờ bắt đầu, nhận thưởng chỉ khi đã đủ thời lượng.
CREATE TABLE coin_ad_views (
    id           INTEGER PRIMARY KEY,
    account_id   INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    coin_day     TEXT NOT NULL,
    started_at   TEXT NOT NULL,
    claimed_at   TEXT,
    cancelled_at TEXT
);
CREATE UNIQUE INDEX idx_coin_ad_open ON coin_ad_views (account_id) WHERE claimed_at IS NULL AND cancelled_at IS NULL;

-- 6. Người chơi của nhân vật công khai và mốc đã thưởng (F44).
CREATE TABLE creator_players (
    card_id       INTEGER NOT NULL REFERENCES character_cards(id) ON DELETE CASCADE,
    player_id     INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    creator_id    INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
    qualified_at  TEXT NOT NULL,
    PRIMARY KEY (card_id, player_id)
);
CREATE TABLE creator_milestones (
    card_id     INTEGER NOT NULL REFERENCES character_cards(id) ON DELETE CASCADE,
    milestone   INTEGER NOT NULL CHECK (milestone IN (10, 50, 100)),
    creator_id  INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
    outcome     TEXT NOT NULL CHECK (outcome IN ('paid', 'owner')),
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
