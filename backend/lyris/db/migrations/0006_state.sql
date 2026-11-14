-- Phase 3: state và trí nhớ (docs/phase3.md §1).

-- Điểm xuất phát của 6 chỉ số cảm xúc, chụp lại lúc tạo story; NULL (story cũ) = đọc từ card hiện tại.
ALTER TABLE stories ADD COLUMN initial_relationship_json TEXT;

-- Hiệu ứng của từng message lên state. Chỉ đọc qua message active (regenerate/lật variant tự rollback).
CREATE TABLE state_events (
  id INTEGER PRIMARY KEY,
  story_id INTEGER NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
  message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
  kind TEXT NOT NULL CHECK (kind IN ('relationship_delta','scene','summary','suggestions')),
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX idx_state_events_story ON state_events(story_id, message_id);
CREATE INDEX idx_state_events_message ON state_events(message_id);

-- Ký ức (sự việc của một lượt) và fact (sự thật bền vững), chung một bảng và một chỉ mục FTS.
CREATE TABLE memories (
  id INTEGER PRIMARY KEY,
  story_id INTEGER NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
  message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
  turn_index INTEGER NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('memory','fact')),
  subject TEXT,
  text TEXT NOT NULL,
  importance INTEGER NOT NULL DEFAULT 3 CHECK (importance BETWEEN 1 AND 5),
  embedding BLOB,            -- float32 little-endian, NULL nếu chưa embed
  embed_model TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX idx_memories_story ON memories(story_id, turn_index);
CREATE INDEX idx_memories_message ON memories(message_id);

-- FTS5 giữ dấu tiếng Việt (ma/má/mà khác nhau): remove_diacritics 0. Đồng bộ bằng trigger insert/delete/update.
CREATE VIRTUAL TABLE memories_fts USING fts5(
  text, content='memories', content_rowid='id', tokenize='unicode61 remove_diacritics 0'
);

CREATE TRIGGER memories_fts_ai AFTER INSERT ON memories BEGIN
  INSERT INTO memories_fts(rowid, text) VALUES (new.id, new.text);
END;

CREATE TRIGGER memories_fts_ad AFTER DELETE ON memories BEGIN
  INSERT INTO memories_fts(memories_fts, rowid, text) VALUES ('delete', old.id, old.text);
END;

CREATE TRIGGER memories_fts_au AFTER UPDATE OF text ON memories BEGIN
  INSERT INTO memories_fts(memories_fts, rowid, text) VALUES ('delete', old.id, old.text);
  INSERT INTO memories_fts(rowid, text) VALUES (new.id, new.text);
END;

-- Hàng đợi việc nền (trích xuất, tóm tắt, embed), chạy lần lượt trong tiến trình app.
CREATE TABLE jobs (
  id INTEGER PRIMARY KEY,
  story_id INTEGER NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
  message_id INTEGER REFERENCES messages(id) ON DELETE CASCADE,
  kind TEXT NOT NULL CHECK (kind IN ('extract','summarize','embed')),
  status TEXT NOT NULL CHECK (status IN ('queued','running','done','failed','cancelled')),
  attempts INTEGER NOT NULL DEFAULT 0,
  error TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX idx_jobs_status ON jobs(status, id);
CREATE INDEX idx_jobs_story ON jobs(story_id, status);
CREATE INDEX idx_jobs_message ON jobs(message_id);
