-- Phase 2c (docs/accounts.md): account tách khỏi persona; mọi persona/card/story thuộc một account
-- và có uid toàn cầu (chuẩn bị cho cộng đồng, Phase 7). Account chủ máy được tạo sẵn; người dùng
-- tự đặt tên/handle ở lần mở đầu tiên (profile_completed = 0 cho tới lúc đó).
CREATE TABLE accounts (
    id                INTEGER PRIMARY KEY,
    uid               TEXT NOT NULL UNIQUE,
    handle            TEXT NOT NULL UNIQUE COLLATE NOCASE,
    display_name      TEXT NOT NULL,
    bio               TEXT NOT NULL DEFAULT '',
    avatar            TEXT,
    banner            TEXT,
    profile_completed INTEGER NOT NULL DEFAULT 0 CHECK (profile_completed IN (0, 1)),
    created_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

INSERT INTO accounts (uid, handle, display_name) VALUES (lower(hex(randomblob(16))), 'ban', 'Bạn');

ALTER TABLE personas ADD COLUMN account_id INTEGER REFERENCES accounts(id);
ALTER TABLE personas ADD COLUMN uid TEXT;
ALTER TABLE personas ADD COLUMN avatar TEXT;
ALTER TABLE character_cards ADD COLUMN account_id INTEGER REFERENCES accounts(id);
ALTER TABLE character_cards ADD COLUMN uid TEXT;
ALTER TABLE character_cards ADD COLUMN visibility TEXT NOT NULL DEFAULT 'private'
    CHECK (visibility IN ('private', 'unlisted', 'public'));
ALTER TABLE stories ADD COLUMN account_id INTEGER REFERENCES accounts(id);
ALTER TABLE stories ADD COLUMN uid TEXT;

UPDATE personas SET account_id = (SELECT MIN(id) FROM accounts) WHERE account_id IS NULL;
UPDATE character_cards SET account_id = (SELECT MIN(id) FROM accounts) WHERE account_id IS NULL;
UPDATE stories SET account_id = (SELECT MIN(id) FROM accounts) WHERE account_id IS NULL;
UPDATE personas SET uid = lower(hex(randomblob(16))) WHERE uid IS NULL;
UPDATE character_cards SET uid = lower(hex(randomblob(16))) WHERE uid IS NULL;
UPDATE stories SET uid = lower(hex(randomblob(16))) WHERE uid IS NULL;

CREATE UNIQUE INDEX idx_personas_uid ON personas (uid);
CREATE UNIQUE INDEX idx_cards_uid ON character_cards (uid);
CREATE UNIQUE INDEX idx_stories_uid ON stories (uid);
CREATE INDEX idx_personas_account ON personas (account_id);
CREATE INDEX idx_cards_account ON character_cards (account_id);
CREATE INDEX idx_stories_account ON stories (account_id);
