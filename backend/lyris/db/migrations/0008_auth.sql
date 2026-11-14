-- Phase 4b (docs/auth.md): đăng nhập, mã mời, vai trò, nhân vật công khai cho tài khoản khác.
-- Account id nhỏ nhất (chủ mọi dữ liệu hiện có) thành chủ máy. Không xoá dữ liệu nào.

-- 1. Tài khoản: vai trò, trạng thái, mật khẩu (scrypt), cài đặt riêng.
ALTER TABLE accounts ADD COLUMN role TEXT NOT NULL DEFAULT 'member'
    CHECK (role IN ('owner', 'member'));
ALTER TABLE accounts ADD COLUMN status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'disabled'));
ALTER TABLE accounts ADD COLUMN must_change_password INTEGER NOT NULL DEFAULT 0
    CHECK (must_change_password IN (0, 1));
-- NULL cả nhóm = chưa có mật khẩu. Có mật khẩu thì đủ cả 5 trường (kiểm ở code, SQLite không thêm
-- được CHECK nhiều cột bằng ALTER). Tham số scrypt lưu theo từng dòng để nâng dần khi đăng nhập.
ALTER TABLE accounts ADD COLUMN password_salt BLOB;          -- 16 byte ngẫu nhiên
ALTER TABLE accounts ADD COLUMN password_hash BLOB;          -- scrypt, 32 byte
ALTER TABLE accounts ADD COLUMN scrypt_n INTEGER;            -- 131072 (2^17)
ALTER TABLE accounts ADD COLUMN scrypt_r INTEGER;            -- 8
ALTER TABLE accounts ADD COLUMN scrypt_p INTEGER;            -- 1
ALTER TABLE accounts ADD COLUMN password_changed_at TEXT;
ALTER TABLE accounts ADD COLUMN password_expires_at TEXT;    -- chỉ mật khẩu tạm (72 giờ); NULL = không hết hạn
ALTER TABLE accounts ADD COLUMN last_login_at TEXT;
ALTER TABLE accounts ADD COLUMN disabled_at TEXT;
ALTER TABLE accounts ADD COLUMN invited_by INTEGER REFERENCES accounts(id) ON DELETE SET NULL;
-- Persona mặc định cho story mới: trước nằm trong app_settings (chung cả máy), giờ theo tài khoản.
ALTER TABLE accounts ADD COLUMN default_persona_id INTEGER REFERENCES personas(id) ON DELETE SET NULL;
-- Phase 5 chỉ lấy dữ liệu train từ tài khoản có cờ này. Thành viên mặc định 0.
ALTER TABLE accounts ADD COLUMN training_opt_in INTEGER NOT NULL DEFAULT 0
    CHECK (training_opt_in IN (0, 1));

UPDATE accounts SET role = 'owner', training_opt_in = 1 WHERE id = (SELECT MIN(id) FROM accounts);
CREATE UNIQUE INDEX idx_accounts_one_owner ON accounts (role) WHERE role = 'owner';

-- Lưới an toàn: cột account_id thêm ở 0005 cho phép NULL. Dòng NULL (không nên có) thì giao cho chủ máy,
-- để sau phase này không còn dòng "không của ai" mà `(? IS NULL OR account_id = ?)` cũ lỡ trả ra.
UPDATE personas        SET account_id = (SELECT id FROM accounts WHERE role = 'owner') WHERE account_id IS NULL;
UPDATE character_cards SET account_id = (SELECT id FROM accounts WHERE role = 'owner') WHERE account_id IS NULL;
UPDATE stories         SET account_id = (SELECT id FROM accounts WHERE role = 'owner') WHERE account_id IS NULL;

-- Chuyển persona mặc định của máy sang chủ máy (chỉ khi persona đó thuộc chủ máy), rồi bỏ khoá cũ.
UPDATE accounts
   SET default_persona_id = (
         SELECT p.id
           FROM app_settings s
           JOIN personas p ON json_valid(s.value_json)
                          AND json_type(s.value_json) = 'integer'
                          AND p.id = json_extract(s.value_json, '$')
          WHERE s.key = 'default_persona_id' AND p.account_id = accounts.id)
 WHERE role = 'owner';
DELETE FROM app_settings WHERE key = 'default_persona_id';

-- 2. Phiên đăng nhập. Token thật chỉ nằm trong cookie của trình duyệt.
CREATE TABLE sessions (
    id           INTEGER PRIMARY KEY,
    account_id   INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    token_hash   BLOB NOT NULL UNIQUE,         -- sha256(token), 32 byte
    created_at   TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    expires_at   TEXT NOT NULL,                -- trượt: last_seen_at + 30 ngày, không quá created_at + 180 ngày
    device_label TEXT NOT NULL DEFAULT '',     -- "Safari · iPhone", rút gọn từ User-Agent, <= 60 ký tự
    ip           TEXT NOT NULL DEFAULT ''      -- IP lúc đăng nhập (sau proxy tin cậy, §3.7)
);
CREATE INDEX idx_sessions_account ON sessions (account_id);
CREATE INDEX idx_sessions_expires ON sessions (expires_at);

-- 3. Mã mời. Chỉ lưu hash; mã đầy đủ hiện một lần lúc tạo.
CREATE TABLE invites (
    id          INTEGER PRIMARY KEY,
    code_hash   BLOB NOT NULL UNIQUE,          -- sha256 của mã đã chuẩn hoá (12 ký tự base32)
    code_hint   TEXT NOT NULL,                 -- 4 ký tự cuối, ví dụ "4TPA"
    note        TEXT NOT NULL DEFAULT '',      -- chủ máy ghi "cho Mai", <= 60 ký tự
    created_by  INTEGER NOT NULL REFERENCES accounts(id),
    created_at  TEXT NOT NULL,
    expires_at  TEXT NOT NULL,
    max_uses    INTEGER NOT NULL DEFAULT 1 CHECK (max_uses = 1),
    used_by     INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
    used_at     TEXT,                          -- khác NULL = đã dùng
    revoked_at  TEXT                           -- khác NULL = đã huỷ
);
CREATE INDEX idx_invites_created ON invites (created_at);

-- 4. Lần thử đăng nhập / thiết lập / tạo tài khoản / đổi mật khẩu, để giới hạn thử sai (§3.4).
-- Giữ 30 ngày. `handle` là chữ người dùng gõ (đã chuẩn hoá), có thể không phải tài khoản thật.
CREATE TABLE auth_attempts (
    id         INTEGER PRIMARY KEY,
    kind       TEXT NOT NULL CHECK (kind IN ('login', 'setup', 'signup', 'change_password')),
    handle     TEXT COLLATE NOCASE,
    ip         TEXT NOT NULL,
    ok         INTEGER NOT NULL CHECK (ok IN (0, 1)),
    device_hash BLOB,                          -- sha256 của cookie thiết bị (§3.4), chỉ ghi ở lần đúng
    created_at TEXT NOT NULL
);
CREATE INDEX idx_auth_attempts_handle ON auth_attempts (kind, handle, created_at);
CREATE INDEX idx_auth_attempts_ip ON auth_attempts (kind, ip, created_at);
CREATE INDEX idx_auth_attempts_device ON auth_attempts (device_hash) WHERE device_hash IS NOT NULL;

-- 5. Nhân vật công khai dùng ở tài khoản khác: bản sao chụp lúc bắt đầu story (§4.3).
ALTER TABLE character_cards ADD COLUMN story_copy INTEGER NOT NULL DEFAULT 0
    CHECK (story_copy IN (0, 1));
ALTER TABLE character_cards ADD COLUMN origin_card_id INTEGER
    REFERENCES character_cards(id) ON DELETE SET NULL;       -- card gốc; NULL khi gốc đã bị xoá
ALTER TABLE character_cards ADD COLUMN origin_account_id INTEGER
    REFERENCES accounts(id) ON DELETE SET NULL;              -- người tạo gốc, để ghi "bởi @handle"
ALTER TABLE character_cards ADD COLUMN origin_updated_at TEXT; -- phiên bản của gốc lúc chụp
CREATE INDEX idx_cards_origin ON character_cards (origin_card_id);
CREATE INDEX idx_cards_visibility ON character_cards (visibility, story_copy);

-- Giao diện chỉ có Riêng tư / Công khai. 'unlisted' chưa từng được đặt từ giao diện; đưa về private để
-- không card nào lộ ra ngoài ý muốn khi có tài khoản thứ hai.
UPDATE character_cards SET visibility = 'private' WHERE visibility = 'unlisted';
