-- Phase 2: Character Studio.
-- Card có bối cảnh mặc định, lời mở đầu thay thế, ghi chú người tạo, ảnh đại diện,
-- và phần dữ liệu Character Card V2 không dùng tới (để export lại không mất).
ALTER TABLE character_cards ADD COLUMN scenario TEXT NOT NULL DEFAULT '';
ALTER TABLE character_cards ADD COLUMN alternate_greetings_json TEXT NOT NULL DEFAULT '[]';
ALTER TABLE character_cards ADD COLUMN creator_notes TEXT NOT NULL DEFAULT '';
ALTER TABLE character_cards ADD COLUMN avatar TEXT;
ALTER TABLE character_cards ADD COLUMN extensions_json TEXT NOT NULL DEFAULT '{}';

CREATE INDEX idx_stories_card ON stories (card_id);
CREATE INDEX idx_stories_persona ON stories (persona_id);
