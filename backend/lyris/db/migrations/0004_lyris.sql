-- Lyris design (Phase 2b): vai trò ngắn của nhân vật hiện trên thẻ, và cài đặt chung của app.
ALTER TABLE character_cards ADD COLUMN role TEXT NOT NULL DEFAULT '';

CREATE TABLE app_settings (
    key        TEXT PRIMARY KEY,
    value_json TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
