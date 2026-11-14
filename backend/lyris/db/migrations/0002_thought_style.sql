-- Cách đặt suy nghĩ thầm [Thought: ...] trong Story Mode:
--   inline = vài dòng Thought lồng vào giữa truyện (mặc định)
--   end    = đúng một dòng Thought ở cuối lượt
ALTER TABLE stories ADD COLUMN thought_style TEXT NOT NULL DEFAULT 'inline'
    CHECK (thought_style IN ('inline', 'end'));
