-- Phase 4 (docs/phase4.md §1): sổ thế giới theo nhân vật, lượt nào đã mở mục nào, và tuỳ chọn không đọc suy nghĩ.
-- Chỉ thêm cột/bảng mới (story và card cũ giữ nguyên).

-- B. Hiện thẻ suy nghĩ của nhân vật trong story (1) hay không (0). Chỉ là cách hiển thị: model vẫn viết
-- [Thought: ...], chữ đã lưu không đổi.
ALTER TABLE stories ADD COLUMN show_thoughts INTEGER NOT NULL DEFAULT 1 CHECK (show_thoughts IN (0, 1));

CREATE TABLE lore_entries (
  id            INTEGER PRIMARY KEY,
  card_id       INTEGER NOT NULL REFERENCES character_cards(id) ON DELETE CASCADE,
  -- Khoá ổn định trong một card. "md:<loại>/<slug tiêu đề>" (nhập từ world.md), "book:..." (character_book
  -- của Card V2), "manual:<12 hex>" (tự thêm). Nhập lại cập nhật theo slug, không nhân đôi.
  slug          TEXT NOT NULL,
  title         TEXT NOT NULL,
  category      TEXT NOT NULL DEFAULT 'lore' CHECK (category IN ('lore', 'character', 'place')),
  keys_json     TEXT NOT NULL DEFAULT '[]',     -- ["Hôn ước", "đính hôn", ...]
  known_by_json TEXT NOT NULL DEFAULT '["*"]',  -- "*" mọi người, "{{user}}" người chơi, "{{char}}" hoặc tên nhân vật
  content       TEXT NOT NULL DEFAULT '',       -- được có {{user}} / {{char}}
  source        TEXT NOT NULL DEFAULT 'manual' CHECK (source IN ('manual', 'world_md', 'card_book')),
  edited        INTEGER NOT NULL DEFAULT 0 CHECK (edited IN (0, 1)),  -- mục nhập từ file đã được sửa tay
  -- Mục nhập từ file/card mà người dùng đã xoá: giữ hàng làm "bia mộ" để nhập lại không thêm lại nó.
  -- Hàng removed = 1 không bao giờ được so khớp, liệt kê, export hay đếm.
  removed       INTEGER NOT NULL DEFAULT 0 CHECK (removed IN (0, 1)),
  enabled       INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
  priority      INTEGER NOT NULL DEFAULT 0,     -- lớn hơn thì được chọn trước khi hết chỗ
  position      INTEGER NOT NULL DEFAULT 0,     -- thứ tự hiển thị; Card V2 insertion_order
  extra_json    TEXT,                           -- trường Card V2 chưa dùng (secondary_keys, constant, ...) để export lại
  created_at    TEXT NOT NULL,
  updated_at    TEXT NOT NULL,
  UNIQUE (card_id, slug)
);
CREATE INDEX idx_lore_entries_card ON lore_entries(card_id, position, id);

-- Mục nào đã được so khớp ở lượt nào. Gắn với message assistant mà prompt của nó đã dùng mục đó.
-- Chỉ đọc qua message active (giống state_events), nên regenerate / lật variant / xoá tự rollback.
CREATE TABLE lore_hits (
  id          INTEGER PRIMARY KEY,
  story_id    INTEGER NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
  message_id  INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
  entry_id    INTEGER NOT NULL REFERENCES lore_entries(id) ON DELETE CASCADE,
  -- carried: trong khối lore, có từ các lượt trước; fresh: trong khối lore, vừa được lượt người chơi gợi ra;
  -- unsent: khớp nhưng không gửi (chỉ người chơi biết, người khác biết, hoặc hết chỗ).
  slot        TEXT NOT NULL CHECK (slot IN ('carried', 'fresh', 'unsent')),
  created_at  TEXT NOT NULL,
  UNIQUE (message_id, entry_id)   -- ghi lại (lượt bị ngắt rồi lưu) không nhân đôi
);
CREATE INDEX idx_lore_hits_story ON lore_hits(story_id, message_id);
CREATE INDEX idx_lore_hits_message ON lore_hits(message_id);  -- CASCADE khi xoá message (truncate_from)
CREATE INDEX idx_lore_hits_entry ON lore_hits(entry_id);
