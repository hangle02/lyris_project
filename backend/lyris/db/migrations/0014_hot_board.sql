-- F44 làm lại + F46 (docs/coins.md §2.2, §5): bảng "Nhân vật hot" và thưởng sáng tác theo bậc xếp hạng.
-- CHỈ THÊM: bảng mới, chỉ mục mới và một lệnh INSERT vào bảng mới. Không đổi bảng cũ, không đổi số dư hay sổ coin.
-- App của chủ dự án chạy `--reload` nên migration này được áp lên DB thật ngay khi code .py đổi (wiki/learned.md).

-- 1. Lúc nhân vật bật Công khai gần nhất (thưởng công khai lần đầu cần ≥ 24 giờ liên tục). Về Riêng tư thì xoá dòng
--    (code Python, không phải trigger).
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
CREATE INDEX idx_hot_board_card ON hot_board (card_id);

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
CREATE INDEX idx_creator_rank_tiers_wait ON creator_rank_tiers (outcome, reached_at);

-- 4. Thưởng công khai lần đầu: mỗi tài khoản một dòng.
CREATE TABLE creator_first_public (
    account_id  INTEGER PRIMARY KEY REFERENCES accounts(id) ON DELETE CASCADE,
    card_id     INTEGER,                               -- nhân vật làm đủ điều kiện (không khoá ngoại: xoá nhân vật không xoá dòng)
    ledger_id   INTEGER NOT NULL,
    paid_at     TEXT NOT NULL
);
