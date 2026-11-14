-- Báo cáo nhân vật công khai (nội dung người dùng tạo: tên, mô tả, lời chào, ảnh, thẻ) ngay từ hồ sơ nhân vật
-- (docs/compliance.md §2). Dùng lại bảng `content_reports` (migration 0010): báo cáo nhân vật có
-- `target = 'character'`, `public_card_id` là nhân vật bị báo cáo, không có tin nhắn, story hay bản chụp nào.
-- Chỉ thêm cột và chỉ mục, không xoá dữ liệu nào. Báo cáo cũ đều là báo cáo câu trả lời (`'message'`).
ALTER TABLE content_reports ADD COLUMN target TEXT NOT NULL DEFAULT 'message'
    CHECK (target IN ('message', 'character'));

-- Một người báo cáo một nhân vật một lần (báo cáo lại thì cập nhật lý do).
CREATE UNIQUE INDEX idx_reports_card_once ON content_reports (reporter_id, public_card_id)
    WHERE target = 'character' AND reporter_id IS NOT NULL AND public_card_id IS NOT NULL;
