-- Phase 1 schema. Áp dụng theo PRAGMA user_version (file 0001 -> version 1).
-- Các cột *_json lưu JSON dạng text.

CREATE TABLE character_cards (
    id                 INTEGER PRIMARY KEY,
    name               TEXT NOT NULL,
    gender             TEXT NOT NULL CHECK (gender IN ('male', 'female', 'other')),
    language           TEXT NOT NULL DEFAULT 'vi' CHECK (language IN ('vi', 'en')),
    description        TEXT NOT NULL DEFAULT '',
    personality        TEXT NOT NULL DEFAULT '',
    appearance         TEXT NOT NULL DEFAULT '',
    background         TEXT NOT NULL DEFAULT '',
    goals              TEXT NOT NULL DEFAULT '',
    secrets            TEXT NOT NULL DEFAULT '',
    speech_style       TEXT NOT NULL DEFAULT '',
    style_profile      TEXT NOT NULL,
    address_terms_json TEXT NOT NULL,
    greeting           TEXT NOT NULL DEFAULT '',
    example_dialogues  TEXT NOT NULL DEFAULT '',
    tags_json          TEXT NOT NULL DEFAULT '[]',
    created_at         TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at         TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE personas (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    gender      TEXT NOT NULL CHECK (gender IN ('male', 'female', 'other')),
    description TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE stories (
    id                      INTEGER PRIMARY KEY,
    card_id                 INTEGER NOT NULL REFERENCES character_cards(id),
    persona_id              INTEGER NOT NULL REFERENCES personas(id),
    title                   TEXT NOT NULL,
    scenario                TEXT NOT NULL DEFAULT '',
    language                TEXT NOT NULL DEFAULT 'vi' CHECK (language IN ('vi', 'en')),
    mode                    TEXT NOT NULL DEFAULT 'story' CHECK (mode IN ('story', 'dm')),
    relationship_type       TEXT NOT NULL DEFAULT 'het' CHECK (relationship_type IN ('het', 'bl', 'gl', 'none')),
    pov                     TEXT NOT NULL DEFAULT 'third' CHECK (pov IN ('third', 'first')),
    narration_pronouns_json TEXT NOT NULL,
    model_name              TEXT NOT NULL DEFAULT 'gemma4:12b',
    scene_summary           TEXT NOT NULL DEFAULT '',
    created_at              TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at              TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- Mỗi lượt (turn_index) có thể có nhiều variant (regenerate); đúng một variant active mỗi lượt.
-- user message luôn chỉ có variant 0.
CREATE TABLE messages (
    id                   INTEGER PRIMARY KEY,
    story_id             INTEGER NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    turn_index           INTEGER NOT NULL,
    variant_index        INTEGER NOT NULL DEFAULT 0,
    is_active            INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    role                 TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    mode                 TEXT NOT NULL CHECK (mode IN ('story', 'dm')),
    raw_content          TEXT NOT NULL,
    visible_content      TEXT NOT NULL,
    thought              TEXT,
    directive            TEXT,
    model_output         TEXT,
    prompt_snapshot_json TEXT,
    model_name           TEXT,
    gen_stats_json       TEXT,
    created_at           TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    edited_at            TEXT,
    UNIQUE (story_id, turn_index, variant_index)
);
CREATE INDEX idx_messages_story_turn ON messages (story_id, turn_index);
CREATE UNIQUE INDEX idx_messages_one_active ON messages (story_id, turn_index) WHERE is_active = 1;

-- Đánh giá hiện tại của một message (một dòng mỗi message).
CREATE TABLE feedback (
    message_id INTEGER PRIMARY KEY REFERENCES messages(id) ON DELETE CASCADE,
    rating     TEXT CHECK (rating IN ('up', 'down')),
    note       TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- Lịch sử sửa nội dung message (dữ liệu train: model_output -> bản đã sửa).
CREATE TABLE message_edits (
    id          INTEGER PRIMARY KEY,
    message_id  INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    before_raw  TEXT NOT NULL,
    after_raw   TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
