-- Tuân thủ khi ra mắt trên web mở (docs/compliance.md): đồng ý điều khoản, báo cáo nội dung AI.
-- Chỉ thêm cột và bảng, không xoá dữ liệu nào.

-- 1. Đồng ý Điều khoản + Chính sách quyền riêng tư (docs/legal/). NULL = chưa đồng ý bản nào (tài khoản có từ
--    trước): giao diện hỏi một lần. `privacy_version` là phiên bản bộ văn bản pháp lý đã đồng ý (lyris.compliance.legal).
ALTER TABLE accounts ADD COLUMN terms_accepted_at TEXT;
ALTER TABLE accounts ADD COLUMN privacy_version TEXT;

-- 2. Báo cáo lời trả lời của AI. Chủ máy xem danh sách để rà soát, nhưng KHÔNG đọc được story của người khác:
--    chỉ khi người báo cáo tự bật "Gửi kèm câu trả lời này cho chủ máy xem xét" (`shared_text = 1`) thì mới lưu
--    bản chụp câu trả lời (`message_text`). Không có thì `message_text` luôn NULL (CHECK bên dưới).
CREATE TABLE content_reports (
    id             INTEGER PRIMARY KEY,
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL,
    -- Xoá tài khoản thì báo cáo còn lại thành ẩn danh; ghi chú và bản chụp bị xoá trước đó (lyris.compliance).
    reporter_id    INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
    message_id     INTEGER REFERENCES messages(id) ON DELETE SET NULL,
    story_id       INTEGER,                      -- id nội bộ, không khoá ngoại (xoá story không xoá báo cáo)
    -- Nhân vật công khai đã sinh ra câu trả lời (story chơi bằng bản sao): để chủ máy biết nhân vật nào cần xem lại.
    -- Nhân vật riêng tư của người báo cáo thì NULL (không lộ nhân vật riêng tư).
    public_card_id INTEGER REFERENCES character_cards(id) ON DELETE SET NULL,
    reason         TEXT NOT NULL CHECK (reason IN
                       ('sexual', 'minor_safety', 'violent', 'hateful', 'self_harm', 'harassment', 'other')),
    note           TEXT NOT NULL DEFAULT '' CHECK (length(note) <= 300),
    mode           TEXT CHECK (mode IS NULL OR mode IN ('story', 'dm')),
    language       TEXT CHECK (language IS NULL OR language IN ('vi', 'en')),
    model_name     TEXT,
    shared_text    INTEGER NOT NULL DEFAULT 0 CHECK (shared_text IN (0, 1)),
    message_text   TEXT CHECK (message_text IS NULL OR shared_text = 1),
    status         TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'reviewed', 'dismissed')),
    reviewed_at    TEXT
);
CREATE INDEX idx_reports_status ON content_reports (status, created_at);
CREATE INDEX idx_reports_reporter ON content_reports (reporter_id);
-- Một người báo cáo một tin một lần (báo cáo lại thì cập nhật lý do).
CREATE UNIQUE INDEX idx_reports_once ON content_reports (reporter_id, message_id)
    WHERE reporter_id IS NOT NULL AND message_id IS NOT NULL;
