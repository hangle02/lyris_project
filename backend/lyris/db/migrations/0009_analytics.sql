-- Event tracking (docs/tracking-plan.md): sự kiện sử dụng lưu trong DB của app, chuyển tiếp sang PostHog khi có
-- khoá (LYRIS_POSTHOG_KEY). Không bao giờ lưu chữ của người dùng: `props_json` chỉ chứa giá trị đã kiểm theo
-- bảng sự kiện (enum, bool, số đã chia khoảng) và nhỏ (<= 1024 byte). Chỉ thêm bảng và cột, không xoá dữ liệu.

CREATE TABLE analytics_events (
    id               INTEGER PRIMARY KEY,
    ts               TEXT NOT NULL,                               -- UTC, YYYY-MM-DDTHH:MM:SS.fffZ
    name             TEXT NOT NULL CHECK (length(name) BETWEEN 1 AND 64),
    -- Xoá tài khoản thì sự kiện còn lại thành ẩn danh (không xoá dây chuyền số liệu tổng).
    account_id       INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
    anon_id          TEXT NOT NULL DEFAULT '',                    -- ngẫu nhiên theo thiết bị (cookie lyris_anon)
    session_id       TEXT NOT NULL DEFAULT '',                    -- một lượt dùng: hết 30 phút không hoạt động là lượt mới
    story_id         INTEGER,                                     -- id nội bộ, không khoá ngoại (xoá story không xoá số liệu)
    props_json       TEXT NOT NULL DEFAULT '{}'
                     CHECK (json_valid(props_json) AND length(props_json) <= 1024),
    source           TEXT NOT NULL DEFAULT 'server' CHECK (source IN ('server', 'client')),
    app_version      TEXT NOT NULL DEFAULT '',
    -- local: chỉ lưu ở máy (chưa cấu hình PostHog); pending: chờ gửi; sent: đã gửi; failed: bỏ sau nhiều lần lỗi.
    posthog_state    TEXT NOT NULL DEFAULT 'local' CHECK (posthog_state IN ('local', 'pending', 'sent', 'failed')),
    posthog_attempts INTEGER NOT NULL DEFAULT 0,
    posthog_next_at  TEXT                                          -- lần gửi lại sớm nhất (backoff)
);
CREATE INDEX idx_analytics_ts ON analytics_events (ts);
CREATE INDEX idx_analytics_name_ts ON analytics_events (name, ts);
CREATE INDEX idx_analytics_anon ON analytics_events (anon_id, id);
CREATE INDEX idx_analytics_account ON analytics_events (account_id);
CREATE INDEX idx_analytics_outbox ON analytics_events (posthog_next_at, id) WHERE posthog_state = 'pending';

-- Mặc định 0 = đang chia sẻ dữ liệu sử dụng ẩn danh (quyết định của chủ sản phẩm; chính sách quyền riêng tư giải
-- thích, người dùng tắt được trong Tài khoản). 1 = không ghi, không gửi sự kiện nào của tài khoản này.
ALTER TABLE accounts ADD COLUMN analytics_opt_out INTEGER NOT NULL DEFAULT 0 CHECK (analytics_opt_out IN (0, 1));
