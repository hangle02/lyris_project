"""Các câu SQL của Phase 4b (docs/auth.md §2.1). Hàm thuần nhận `sqlite3.Connection`.

Ai gọi tự giữ khoá: `repo.locked()` để đọc, `repo.transaction()` để ghi (lệnh trên Mac mở transaction
`BEGIN IMMEDIATE` trên kết nối riêng). Không hàm nào ở đây băm mật khẩu.
"""
from __future__ import annotations

import json
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Literal

from lyris.auth import clock
from lyris.auth.net import token_hash
from lyris.auth.passwords import PasswordHash

SESSION_SLIDE = timedelta(days=30)
SESSION_ABSOLUTE = timedelta(days=180)
SESSION_TOUCH = timedelta(hours=1)
MAX_SESSIONS = 20
ATTEMPT_RETENTION = timedelta(days=30)
KNOWN_DEVICE_WINDOW = timedelta(days=30)
TEMP_PASSWORD_TTL = timedelta(hours=72)
SETUP_CODE_TTL = timedelta(hours=24)
INVITE_DAYS = (1, 7, 30)
DEFAULT_INVITE_DAYS = 7
MAX_ACTIVE_INVITES = 20
SETUP_KEY = "owner_setup"

AttemptKind = Literal["login", "setup", "signup", "change_password"]
InviteStatus = Literal["active", "used", "expired", "revoked"]


@dataclass(frozen=True)
class AuthRow:
    """Một dòng `accounts` với các cột của phần đăng nhập."""

    id: int
    handle: str
    display_name: str
    avatar: str | None
    role: str
    status: str
    must_change_password: bool
    profile_completed: bool
    password: PasswordHash | None
    password_expires_at: str | None


@dataclass(frozen=True)
class SessionRow:
    id: int
    account_id: int
    created_at: str
    last_seen_at: str
    expires_at: str


_ACCOUNT_COLUMNS = (
    "a.id, a.handle, a.display_name, a.avatar, a.role, a.status, a.must_change_password, a.profile_completed,"
    " a.password_salt, a.password_hash, a.scrypt_n, a.scrypt_r, a.scrypt_p, a.password_expires_at"
)


def _auth_row(row: sqlite3.Row) -> AuthRow:
    password = None
    if row["password_hash"] is not None and row["password_salt"] is not None and row["scrypt_n"]:
        password = PasswordHash(
            salt=bytes(row["password_salt"]),
            digest=bytes(row["password_hash"]),
            n=int(row["scrypt_n"]),
            r=int(row["scrypt_r"]),
            p=int(row["scrypt_p"]),
        )
    return AuthRow(
        id=int(row["id"]),
        handle=str(row["handle"]),
        display_name=str(row["display_name"]),
        avatar=row["avatar"],
        role=str(row["role"]),
        status=str(row["status"]),
        must_change_password=bool(row["must_change_password"]),
        profile_completed=bool(row["profile_completed"]),
        password=password,
        password_expires_at=row["password_expires_at"],
    )


def schema_version(conn: sqlite3.Connection) -> int:
    return int(conn.execute("PRAGMA user_version").fetchone()[0])


# ---------------------------------------------------------------------------- tài khoản


def account_by_handle(conn: sqlite3.Connection, handle: str) -> AuthRow | None:
    row = conn.execute(f"SELECT {_ACCOUNT_COLUMNS} FROM accounts a WHERE a.handle = ?", (handle,)).fetchone()
    return None if row is None else _auth_row(row)


def account_by_id(conn: sqlite3.Connection, account_id: int) -> AuthRow | None:
    row = conn.execute(f"SELECT {_ACCOUNT_COLUMNS} FROM accounts a WHERE a.id = ?", (account_id,)).fetchone()
    return None if row is None else _auth_row(row)


def owner(conn: sqlite3.Connection) -> AuthRow | None:
    row = conn.execute(f"SELECT {_ACCOUNT_COLUMNS} FROM accounts a WHERE a.role = 'owner'").fetchone()
    return None if row is None else _auth_row(row)


def owner_needs_setup(conn: sqlite3.Connection) -> bool:
    """Chủ máy chưa có mật khẩu. Đọc DB mỗi lần (không cache) để lệnh trên Mac có hiệu lực ngay (§2.4)."""
    row = conn.execute("SELECT password_hash IS NULL FROM accounts WHERE role = 'owner'").fetchone()
    return row is None or bool(row[0])


def write_password(
    conn: sqlite3.Connection, account_id: int, hashed: PasswordHash, now: datetime, *, temporary: bool
) -> None:
    """Đặt mật khẩu. `temporary`: mật khẩu tạm (buộc đổi, hết hạn sau 72 giờ, chỉ xét lúc đăng nhập)."""
    conn.execute(
        "UPDATE accounts SET password_salt = ?, password_hash = ?, scrypt_n = ?, scrypt_r = ?, scrypt_p = ?,"
        " password_changed_at = ?, password_expires_at = ?, must_change_password = ?, updated_at = ?"
        " WHERE id = ?",
        (
            hashed.salt,
            hashed.digest,
            hashed.n,
            hashed.r,
            hashed.p,
            clock.iso(now),
            clock.iso(now + TEMP_PASSWORD_TTL) if temporary else None,
            1 if temporary else 0,
            clock.iso(now),
            account_id,
        ),
    )


def rehash_password(conn: sqlite3.Connection, account_id: int, old: PasswordHash, new: PasswordHash) -> None:
    """Thay hash bằng tham số mới, chỉ khi hash cũ vẫn còn đó (không đè lên lần đổi mật khẩu xen giữa)."""
    conn.execute(
        "UPDATE accounts SET password_salt = ?, password_hash = ?, scrypt_n = ?, scrypt_r = ?, scrypt_p = ?"
        " WHERE id = ? AND password_hash = ?",
        (new.salt, new.digest, new.n, new.r, new.p, account_id, old.digest),
    )


def set_owner_password(conn: sqlite3.Connection, hashed: PasswordHash, now: datetime) -> int | None:
    """Thiết lập lần đầu: chỉ thắng khi chủ máy vẫn chưa có mật khẩu. Trả id chủ máy, hoặc None nếu thua."""
    cur = conn.execute(
        "UPDATE accounts SET password_salt = ?, password_hash = ?, scrypt_n = ?, scrypt_r = ?, scrypt_p = ?,"
        " password_changed_at = ?, password_expires_at = NULL, must_change_password = 0, updated_at = ?"
        " WHERE role = 'owner' AND password_hash IS NULL",
        (hashed.salt, hashed.digest, hashed.n, hashed.r, hashed.p, clock.iso(now), clock.iso(now)),
    )
    if cur.rowcount != 1:
        return None
    row = conn.execute("SELECT id FROM accounts WHERE role = 'owner'").fetchone()
    return int(row[0])


def mark_login(conn: sqlite3.Connection, account_id: int, now: datetime) -> None:
    conn.execute("UPDATE accounts SET last_login_at = ? WHERE id = ?", (clock.iso(now), account_id))


def set_status(conn: sqlite3.Connection, account_id: int, status: Literal["active", "disabled"], now: datetime) -> None:
    conn.execute(
        "UPDATE accounts SET status = ?, disabled_at = ?, updated_at = ? WHERE id = ?",
        (status, clock.iso(now) if status == "disabled" else None, clock.iso(now), account_id),
    )


def insert_member(
    conn: sqlite3.Connection, *, uid: str, handle: str, display_name: str, invited_by: int | None
) -> int:
    """Thêm thành viên (vai trò `member`, đã đặt profile). Handle trùng -> sqlite3.IntegrityError.

    F42 (docs/coins.md §3.4): mọi đường tạo thành viên (mã mời, server giả của bot, fixture) đi qua đây, nên ví và
    quà tạo tài khoản +300 (`signup:<id>`) được ghi ngay tại đây, cùng transaction với việc tạo tài khoản."""
    from lyris.coins import ledger as coin_ledger

    cur = conn.execute(
        "INSERT INTO accounts (uid, handle, display_name, profile_completed, role, invited_by)"
        " VALUES (?, ?, ?, 1, 'member', ?)",
        (uid, handle, display_name, invited_by),
    )
    assert cur.lastrowid is not None
    account_id = int(cur.lastrowid)
    # DB chưa có migration 0012 (dựng DB cũ trong test, hay code mới tải trước migration): bỏ qua, migration
    # 0012 sẽ mở ví +300 cho mọi thành viên đã có (`backfill_grant`).
    if conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'coin_wallets'").fetchone():
        coin_ledger.open_wallet(conn, account_id)
    return account_id


# ---------------------------------------------------------------------------- phiên


def insert_session(
    conn: sqlite3.Connection,
    account_id: int,
    *,
    now: datetime,
    label: str = "",
    ip: str = "",
    replace: bytes | None = None,
) -> tuple[str, datetime]:
    """Cấp phiên mới: (token thô cho cookie, hạn). DB chỉ có sha256 của token.

    `replace`: hash của cookie phiên request đang mang; dòng đó bị xoá (không để phiên cũ hay phiên bị cài
    sẵn còn sống song song). Quá 20 phiên thì xoá phiên có `last_seen_at` cũ nhất.
    """
    if replace is not None:
        conn.execute("DELETE FROM sessions WHERE token_hash = ?", (replace,))
    token = secrets.token_urlsafe(32)
    expires = now + SESSION_SLIDE
    conn.execute(
        "INSERT INTO sessions (account_id, token_hash, created_at, last_seen_at, expires_at, device_label, ip)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (account_id, token_hash(token), clock.iso(now), clock.iso(now), clock.iso(expires), label[:60], ip[:64]),
    )
    conn.execute(
        "DELETE FROM sessions WHERE account_id = ? AND id NOT IN ("
        " SELECT id FROM sessions WHERE account_id = ? ORDER BY last_seen_at DESC, id DESC LIMIT ?)",
        (account_id, account_id, MAX_SESSIONS),
    )
    return token, expires


def find_session(conn: sqlite3.Connection, hashed: bytes) -> tuple[SessionRow, AuthRow] | None:
    row = conn.execute(
        "SELECT s.id AS session_id, s.account_id, s.created_at AS s_created, s.last_seen_at, s.expires_at,"
        f" {_ACCOUNT_COLUMNS}"
        " FROM sessions s JOIN accounts a ON a.id = s.account_id WHERE s.token_hash = ?",
        (hashed,),
    ).fetchone()
    if row is None:
        return None
    session = SessionRow(
        id=int(row["session_id"]),
        account_id=int(row["account_id"]),
        created_at=str(row["s_created"]),
        last_seen_at=str(row["last_seen_at"]),
        expires_at=str(row["expires_at"]),
    )
    return session, _auth_row(row)


def session_expired(session: SessionRow, now: datetime) -> bool:
    if clock.parse(session.expires_at) <= now:
        return True
    return clock.parse(session.created_at) + SESSION_ABSOLUTE <= now


def session_needs_touch(session: SessionRow, now: datetime) -> bool:
    return clock.parse(session.last_seen_at) + SESSION_TOUCH <= now


def touch_session(conn: sqlite3.Connection, session: SessionRow, now: datetime) -> datetime:
    """Gia hạn trượt: `expires_at = now + 30 ngày`, không quá `created_at + 180 ngày`. Trả hạn mới."""
    expires = min(now + SESSION_SLIDE, clock.parse(session.created_at) + SESSION_ABSOLUTE)
    conn.execute(
        "UPDATE sessions SET last_seen_at = ?, expires_at = ? WHERE id = ?",
        (clock.iso(now), clock.iso(expires), session.id),
    )
    return expires


def delete_session_by_id(conn: sqlite3.Connection, session_id: int) -> None:
    conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))


def delete_session_by_hash(conn: sqlite3.Connection, hashed: bytes) -> None:
    conn.execute("DELETE FROM sessions WHERE token_hash = ?", (hashed,))


def delete_sessions(conn: sqlite3.Connection, account_id: int) -> int:
    return conn.execute("DELETE FROM sessions WHERE account_id = ?", (account_id,)).rowcount


def purge(conn: sqlite3.Connection, now: datetime) -> tuple[int, int]:
    """Xoá phiên hết hạn (trượt hoặc tuyệt đối) và lần thử cũ hơn 30 ngày. Trả (số phiên, số lần thử)."""
    sessions = conn.execute(
        "DELETE FROM sessions WHERE expires_at <= ? OR created_at <= ?",
        (clock.iso(now), clock.iso(now - SESSION_ABSOLUTE)),
    ).rowcount
    attempts = conn.execute(
        "DELETE FROM auth_attempts WHERE created_at < ?", (clock.iso(now - ATTEMPT_RETENTION),)
    ).rowcount
    return sessions, attempts


# ---------------------------------------------------------------------------- lần thử


def record_attempt(
    conn: sqlite3.Connection,
    kind: AttemptKind,
    *,
    handle: str | None,
    ip: str,
    ok: bool,
    now: datetime,
    device: bytes | None = None,
) -> int:
    """Ghi một lần thử; trả id của dòng (để `settle_attempt`/`drop_attempt` khi lần thử được giữ chỗ trước)."""
    cur = conn.execute(
        "INSERT INTO auth_attempts (kind, handle, ip, ok, device_hash, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (kind, handle, ip, 1 if ok else 0, device, clock.iso(now)),
    )
    assert cur.lastrowid is not None
    return int(cur.lastrowid)


def settle_attempt(
    conn: sqlite3.Connection, attempt_id: int, *, ok: bool, now: datetime, device: bytes | None
) -> None:
    """Chốt kết quả của lần thử đã giữ chỗ (ghi `ok = 0` cùng lúc kiểm giới hạn, trước khi băm)."""
    conn.execute(
        "UPDATE auth_attempts SET ok = ?, device_hash = ?, created_at = ? WHERE id = ?",
        (1 if ok else 0, device, clock.iso(now), attempt_id),
    )


def drop_attempt(conn: sqlite3.Connection, attempt_id: int) -> None:
    """Bỏ lần thử đã giữ chỗ mà mật khẩu chưa hề được so (hàng chờ băm đầy)."""
    conn.execute("DELETE FROM auth_attempts WHERE id = ?", (attempt_id,))


def account_key(account_id: int) -> str:
    """Khoá của luật đổi mật khẩu trong cột `auth_attempts.handle`: `#<id tài khoản>`. Không trùng được handle
    thật (handle không có `#`) và không đổi khi người dùng đổi @handle (§3.4: luật theo tài khoản)."""
    return f"#{account_id}"


def password_current(conn: sqlite3.Connection, account_id: int, digest: bytes) -> bool:
    """Tài khoản còn đang dùng đúng hash này và đang hoạt động (kiểm lại trong transaction ghi: mật khẩu có
    thể đã bị đổi/đặt lại, hoặc tài khoản bị khoá, trong lúc băm)."""
    row = conn.execute(
        "SELECT 1 FROM accounts WHERE id = ? AND password_hash = ? AND status = 'active'", (account_id, digest)
    ).fetchone()
    return row is not None



def failures(
    conn: sqlite3.Connection,
    kind: AttemptKind,
    *,
    since: datetime,
    reset_on_ok: bool,
    handle: str | None = None,
    ip: str | None = None,
    device: bytes | None = None,
) -> list[datetime]:
    """Mốc các lần sai (mới nhất trước) của khoá (handle/ip/thiết bị đã cho) từ `since`; `reset_on_ok`:
    chỉ tính sau lần đúng gần nhất của cùng khoá."""
    where = ["kind = ?"]
    params: list[Any] = [kind]
    for column, value in (("handle", handle), ("ip", ip), ("device_hash", device)):
        if value is not None:
            where.append(f"{column} = ?")
            params.append(value)
    cond = " AND ".join(where)
    after_id = 0
    if reset_on_ok:
        # "Sau lần đúng gần nhất" theo thứ tự ghi (id), không theo giờ: hai lần thử cùng một mili giây vẫn đúng thứ tự.
        row = conn.execute(f"SELECT MAX(id) FROM auth_attempts WHERE {cond} AND ok = 1", params).fetchone()
        after_id = int(row[0] or 0)
    rows = conn.execute(
        f"SELECT created_at FROM auth_attempts WHERE {cond} AND ok = 0 AND created_at > ? AND id > ?"
        " ORDER BY created_at DESC, id DESC",
        [*params, clock.iso(since), after_id],
    ).fetchall()
    return [clock.parse(str(r[0])) for r in rows]


def known_device(conn: sqlite3.Connection, handle: str, device: bytes, now: datetime) -> bool:
    """Trình duyệt này (cookie thiết bị) đã đăng nhập đúng `handle` trong 30 ngày (§3.4)."""
    row = conn.execute(
        "SELECT 1 FROM auth_attempts WHERE device_hash = ? AND handle = ? AND ok = 1"
        " AND kind IN ('login', 'setup', 'signup') AND created_at > ? LIMIT 1",
        (device, handle, clock.iso(now - KNOWN_DEVICE_WINDOW)),
    ).fetchone()
    return row is not None


def clear_failures(conn: sqlite3.Connection, handle: str, account_id: int) -> int:
    """Xoá các lần sai của tài khoản: đăng nhập theo handle, đổi mật khẩu theo `account_key` (đặt lại mật khẩu
    bằng lệnh trên Mac hoặc từ trang Quản lý tài khoản)."""
    return conn.execute(
        "DELETE FROM auth_attempts WHERE handle IN (?, ?) AND ok = 0", (handle, account_key(account_id))
    ).rowcount


# ---------------------------------------------------------------------------- mã thiết lập chủ máy


def read_setup(conn: sqlite3.Connection) -> tuple[str, str] | None:
    """(sha256 hex, hạn) của mã thiết lập đang dùng; None nếu không có hoặc hỏng."""
    row = conn.execute("SELECT value_json FROM app_settings WHERE key = ?", (SETUP_KEY,)).fetchone()
    if row is None:
        return None
    try:
        data = json.loads(row[0])
        return str(data["hash"]), str(data["expires_at"])
    except (ValueError, KeyError, TypeError):
        return None


def write_setup(conn: sqlite3.Connection, hash_hex: str, expires: datetime) -> None:
    value = json.dumps({"hash": hash_hex, "expires_at": clock.iso(expires)})
    conn.execute(
        "INSERT INTO app_settings (key, value_json) VALUES (?, ?)"
        " ON CONFLICT(key) DO UPDATE SET value_json = excluded.value_json,"
        " updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')",
        (SETUP_KEY, value),
    )


def delete_setup(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM app_settings WHERE key = ?", (SETUP_KEY,))


# ---------------------------------------------------------------------------- mã mời


@dataclass(frozen=True)
class InviteRow:
    id: int
    hint: str
    note: str
    created_at: str
    expires_at: str
    used_at: str | None
    revoked_at: str | None
    used_by_handle: str | None
    created_by: int

    def status(self, now: datetime) -> InviteStatus:
        if self.used_at is not None:
            return "used"
        if self.revoked_at is not None:
            return "revoked"
        if clock.parse(self.expires_at) <= now:
            return "expired"
        return "active"


_INVITE_SELECT = (
    "SELECT i.id, i.code_hint, i.note, i.created_at, i.expires_at, i.used_at, i.revoked_at, i.created_by,"
    " u.handle AS used_by_handle FROM invites i LEFT JOIN accounts u ON u.id = i.used_by"
)


def _invite(row: sqlite3.Row) -> InviteRow:
    return InviteRow(
        id=int(row["id"]),
        hint=str(row["code_hint"]),
        note=str(row["note"]),
        created_at=str(row["created_at"]),
        expires_at=str(row["expires_at"]),
        used_at=row["used_at"],
        revoked_at=row["revoked_at"],
        used_by_handle=row["used_by_handle"],
        created_by=int(row["created_by"]),
    )


def list_invites(conn: sqlite3.Connection) -> list[InviteRow]:
    return [_invite(r) for r in conn.execute(f"{_INVITE_SELECT} ORDER BY i.created_at DESC, i.id DESC")]


def get_invite(conn: sqlite3.Connection, invite_id: int) -> InviteRow | None:
    row = conn.execute(f"{_INVITE_SELECT} WHERE i.id = ?", (invite_id,)).fetchone()
    return None if row is None else _invite(row)


def find_invite(conn: sqlite3.Connection, hashed: bytes) -> InviteRow | None:
    row = conn.execute(f"{_INVITE_SELECT} WHERE i.code_hash = ?", (hashed,)).fetchone()
    return None if row is None else _invite(row)


def active_invite_count(conn: sqlite3.Connection, now: datetime) -> int:
    row = conn.execute(
        "SELECT COUNT(*) FROM invites WHERE used_at IS NULL AND revoked_at IS NULL AND expires_at > ?",
        (clock.iso(now),),
    ).fetchone()
    return int(row[0])


def insert_invite(
    conn: sqlite3.Connection, *, hashed: bytes, hint: str, note: str, created_by: int, now: datetime, days: int
) -> int:
    cur = conn.execute(
        "INSERT INTO invites (code_hash, code_hint, note, created_by, created_at, expires_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (hashed, hint, note, created_by, clock.iso(now), clock.iso(now + timedelta(days=days))),
    )
    assert cur.lastrowid is not None
    return int(cur.lastrowid)


def claim_invite(conn: sqlite3.Connection, invite_id: int, now: datetime) -> bool:
    """Khoá mã mời cho một lần dùng; hai người dùng cùng mã cùng lúc chỉ một người được (rowcount = 1)."""
    cur = conn.execute(
        "UPDATE invites SET used_at = ? WHERE id = ? AND used_at IS NULL AND revoked_at IS NULL AND expires_at > ?",
        (clock.iso(now), invite_id, clock.iso(now)),
    )
    return cur.rowcount == 1


def set_invite_user(conn: sqlite3.Connection, invite_id: int, account_id: int) -> None:
    conn.execute("UPDATE invites SET used_by = ? WHERE id = ?", (account_id, invite_id))


def revoke_invite(conn: sqlite3.Connection, invite_id: int, now: datetime) -> None:
    conn.execute(
        "UPDATE invites SET revoked_at = ? WHERE id = ? AND used_at IS NULL AND revoked_at IS NULL",
        (clock.iso(now), invite_id),
    )


# ---------------------------------------------------------------------------- quản trị


@dataclass(frozen=True)
class AdminRow:
    id: int
    handle: str
    display_name: str
    avatar: str | None
    role: str
    status: str
    must_change_password: bool
    has_password: bool
    created_at: str
    last_login_at: str | None
    invited_by_handle: str | None
    session_count: int
    # F43 (docs/coins.md §7): số dư ví của thành viên (chưa có ví: 0); chủ máy: None (không tốn coin).
    coin_balance: int | None = None


def admin_accounts(conn: sqlite3.Connection, now: datetime, account_id: int | None = None) -> list[AdminRow]:
    """Tài khoản cho trang Quản lý: chủ máy trước, rồi theo `created_at`. Không có gì bên trong tài khoản."""
    where = "" if account_id is None else " WHERE a.id = ?"
    params: list[Any] = [clock.iso(now), clock.iso(now - SESSION_ABSOLUTE)]
    if account_id is not None:
        params.append(account_id)
    rows = conn.execute(
        "SELECT a.id, a.handle, a.display_name, a.avatar, a.role, a.status, a.must_change_password,"
        " a.password_hash IS NOT NULL AS has_password, a.created_at, a.last_login_at, i.handle AS invited_by_handle,"
        " (SELECT COUNT(*) FROM sessions s WHERE s.account_id = a.id AND s.expires_at > ? AND s.created_at > ?)"
        "   AS session_count,"
        " (SELECT w.balance FROM coin_wallets w WHERE w.account_id = a.id) AS coin_balance"
        f" FROM accounts a LEFT JOIN accounts i ON i.id = a.invited_by{where}"
        " ORDER BY a.role = 'owner' DESC, a.created_at, a.id",
        params,
    ).fetchall()
    return [
        AdminRow(
            id=int(r["id"]),
            handle=str(r["handle"]),
            display_name=str(r["display_name"]),
            avatar=r["avatar"],
            role=str(r["role"]),
            status=str(r["status"]),
            must_change_password=bool(r["must_change_password"]),
            has_password=bool(r["has_password"]),
            created_at=str(r["created_at"]),
            last_login_at=r["last_login_at"],
            invited_by_handle=r["invited_by_handle"],
            session_count=int(r["session_count"]),
            coin_balance=None if str(r["role"]) == "owner" else int(r["coin_balance"] or 0),
        )
        for r in rows
    ]
