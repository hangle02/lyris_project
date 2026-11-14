"""Luồng đăng nhập (docs/auth.md §1.4, §2.4, §2.5, §3, §6): đọc phiên từ cookie, đăng nhập, thiết lập chủ máy,
tạo tài khoản bằng mã mời, đổi mật khẩu, đăng xuất, và việc của chủ máy (mã mời, đặt lại mật khẩu, tạm khoá).

Thứ tự cố định khi có mật khẩu: kiểm giới hạn thử sai và giữ chỗ lần thử (một dòng `ok = 0`, cùng một
transaction ngắn) -> nhả khoá -> băm/so sánh trong thread -> mới mở transaction để ghi, và trong đó kiểm lại
hash của tài khoản vẫn là hash đã so (mật khẩu có thể vừa đổi trong lúc băm). Không bao giờ ghi mật khẩu, token, mã mời
hay mã thiết lập vào log.
"""
from __future__ import annotations

import logging
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime

from starlette.requests import Request

from lyris.accounts import AccountInputError, validate_display_name, validate_handle
from lyris.auth import clock, codes, errors, passwords, ratelimit, setup, store
from lyris.auth.errors import AuthError
from lyris.auth.middleware import COOKIE_STATE_KEY
from lyris.auth.net import (
    DEVICE_COOKIE,
    DEVICE_MAX_AGE,
    SESSION_COOKIE,
    clear_cookie_header,
    client_ip,
    cookie_name,
    cookie_names_present,
    device_label,
    read_cookie,
    request_is_secure,
    set_cookie_header,
    token_hash,
)
from lyris.compliance import legal
from lyris.db.repo import HandleTaken, NotFound, Repo, new_uid

logger = logging.getLogger("lyris.auth")

_RESOLVED_KEY = "lyris_auth_resolved"


def _repo(request: Request) -> Repo:
    repo: Repo = request.app.state.repo
    return repo


def log_handle(raw: str | None) -> str | None:
    """Handle đã chuẩn hoá nếu đúng luật handle, không thì None (§3.4: không để mật khẩu gõ nhầm vào ô tên
    đăng nhập nằm trong DB hay log)."""
    if not raw:
        return None
    try:
        return validate_handle(raw)
    except AccountInputError:
        return None


# ---------------------------------------------------------------------------- cookie


def queue_cookie(request: Request, header: str) -> None:
    """Hẹn một `Set-Cookie`; AuthMiddleware gắn vào response (kể cả response lỗi hay stream)."""
    pending: list[str] = list(getattr(request.state, COOKIE_STATE_KEY, []))
    pending.append(header)
    setattr(request.state, COOKIE_STATE_KEY, pending)


def _clear_session_cookies(request: Request) -> None:
    for name in cookie_names_present(request, SESSION_COOKIE):
        queue_cookie(request, clear_cookie_header(name))


def _set_session_cookie(request: Request, token: str, expires: datetime, now: datetime) -> None:
    secure = request_is_secure(request)
    max_age = int((expires - now).total_seconds())
    queue_cookie(request, set_cookie_header(cookie_name(SESSION_COOKIE, secure), token, max_age=max_age, secure=secure))


def _device(request: Request) -> tuple[bytes, bool]:
    """(sha256 cookie thiết bị, có sẵn từ trước không). Chưa có thì sinh mới và hẹn gửi (giữ khi đăng xuất)."""
    found = read_cookie(request, DEVICE_COOKIE)
    if found is not None:
        return token_hash(found[1]), True
    token = secrets.token_urlsafe(32)
    secure = request_is_secure(request)
    queue_cookie(request, set_cookie_header(cookie_name(DEVICE_COOKIE, secure), token, max_age=DEVICE_MAX_AGE, secure=secure))
    return token_hash(token), False


def _existing_device(request: Request) -> bytes | None:
    found = read_cookie(request, DEVICE_COOKIE)
    return None if found is None else token_hash(found[1])


def _old_session_hash(request: Request) -> bytes | None:
    found = read_cookie(request, SESSION_COOKIE)
    return None if found is None else token_hash(found[1])


# ---------------------------------------------------------------------------- phiên của request


@dataclass(frozen=True)
class Resolved:
    """Kết quả đọc cookie phiên: `account` None khi chưa đăng nhập; `logged_out` khi có cookie mà không dùng
    được nữa (hết hạn, bị xoá, tài khoản bị khoá)."""

    account: store.AuthRow | None
    session: store.SessionRow | None
    logged_out: bool


def resolve_session(request: Request) -> Resolved:
    """Đọc phiên từ cookie (một lần mỗi request). Hết hạn/không có -> xoá cookie; tài khoản bị khoá -> xoá
    mọi phiên của nó; `last_seen_at` cũ hơn 1 giờ -> gia hạn trượt và gửi lại cookie."""
    cached: Resolved | None = getattr(request.state, _RESOLVED_KEY, None)
    if cached is not None:
        return cached
    result = _resolve_session(request)
    setattr(request.state, _RESOLVED_KEY, result)
    return result


def _resolve_session(request: Request) -> Resolved:
    found = read_cookie(request, SESSION_COOKIE)
    if found is None:
        had_cookie = bool(cookie_names_present(request, SESSION_COOKIE))
        if had_cookie:
            _clear_session_cookies(request)
        return Resolved(None, None, logged_out=had_cookie)
    name, token = found
    repo = _repo(request)
    now = clock.now()
    with repo.locked() as conn:
        hit = store.find_session(conn, token_hash(token))
    if hit is None:
        _clear_session_cookies(request)
        return Resolved(None, None, logged_out=True)
    session, account = hit
    if account.status != "active":
        with repo.transaction():
            store.delete_sessions(repo.conn, account.id)
        _clear_session_cookies(request)
        return Resolved(None, None, logged_out=True)
    if store.session_expired(session, now):
        with repo.transaction():
            store.delete_session_by_id(repo.conn, session.id)
        _clear_session_cookies(request)
        return Resolved(None, None, logged_out=True)
    if store.session_needs_touch(session, now):
        with repo.transaction():
            expires = store.touch_session(repo.conn, session, now)
        secure = name.startswith("__Host-")
        queue_cookie(
            request, set_cookie_header(name, token, max_age=int((expires - now).total_seconds()), secure=secure)
        )
    return Resolved(account, session, logged_out=False)


def setup_needed(repo: Repo) -> bool:
    with repo.locked() as conn:
        return store.owner_needs_setup(conn)


def require_account(request: Request, *, allow_pending: bool) -> store.AuthRow:
    """Tài khoản đang đăng nhập, hoặc AuthError theo §2.5 (409 setup_required, 401, 403)."""
    if setup_needed(_repo(request)):
        raise errors.setup_required()
    resolved = resolve_session(request)
    if resolved.account is None:
        raise errors.auth_required(logged_out=resolved.logged_out)
    if resolved.account.must_change_password and not allow_pending:
        raise AuthError(403, errors.PASSWORD_CHANGE_REQUIRED, "password_change_required")
    return resolved.account


# ---------------------------------------------------------------------------- đăng nhập


def _new_session(conn: sqlite3.Connection, request: Request, account_id: int, now: datetime) -> tuple[str, datetime]:
    return store.insert_session(
        conn,
        account_id,
        now=now,
        label=device_label(request.headers.get("user-agent")),
        ip=client_ip(request),
        replace=_old_session_hash(request),
    )


async def _hash_new(password: str) -> passwords.PasswordHash:
    """Băm mật khẩu mới (thiết lập, tạo tài khoản, mật khẩu tạm). Hàng chờ băm đầy: 503, chưa ghi gì."""
    try:
        return await passwords.hash_password(password)
    except passwords.HashingBusy:
        raise errors.busy() from None


async def _verify_reserved(repo: Repo, attempt: int, password: str, stored: passwords.PasswordHash | None) -> bool:
    """So mật khẩu cho một lần thử đã giữ chỗ. Hàng chờ băm đầy: bỏ chỗ (mật khẩu chưa được so) và trả 503."""
    try:
        return await passwords.verify_password(password, stored)
    except passwords.HashingBusy:
        with repo.transaction():
            store.drop_attempt(repo.conn, attempt)
        raise errors.busy() from None


async def login(request: Request, raw_handle: str, password: str) -> store.AuthRow:
    repo = _repo(request)
    if setup_needed(repo):
        raise errors.setup_required()
    handle = log_handle(raw_handle)
    ip = client_ip(request)
    label = device_label(request.headers.get("user-agent"))
    device = _existing_device(request)
    now = clock.now()
    # Kiểm giới hạn và giữ chỗ (một dòng `ok = 0`) trong CÙNG một transaction, trước khi băm: request song
    # song thấy ngay các lần thử đang chạy, không cùng lọt qua một bộ đếm còn trống.
    with repo.transaction():
        conn = repo.conn
        known = handle is not None and device is not None and store.known_device(conn, handle, device, now)
        blocked = ratelimit.login_block(conn, now, handle=handle, ip=ip, device=device, known=known)
        account = store.account_by_handle(conn, handle) if handle is not None else None
        attempt = (
            None
            if blocked is not None
            else store.record_attempt(
                conn, "login", handle=handle, ip=ip, ok=False, now=now, device=device if known else None
            )
        )
    if blocked is not None or attempt is None:
        logger.info("Đăng nhập bị chặn vì thử sai nhiều: @%s, IP %s", handle or "?", ip)
        raise errors.rate_limited(blocked or 1)

    stored = account.password if account is not None else None
    correct = await _verify_reserved(repo, attempt, password, stored)
    now = clock.now()
    if not correct or account is None or stored is None:
        logger.info("Đăng nhập sai: @%s, IP %s, %s", handle or "?", ip, label or "?")
        raise AuthError(401, errors.BAD_LOGIN)

    # Mật khẩu đúng: giờ mới được báo trạng thái tài khoản (§3.5). Lần thử vẫn là `ok = 0`, không kèm thiết bị.
    if account.status != "active":
        with repo.transaction():
            store.settle_attempt(repo.conn, attempt, ok=False, now=now, device=None)
        logger.info("Đăng nhập vào tài khoản đang tạm khoá: @%s, IP %s", handle, ip)
        raise AuthError(403, errors.ACCOUNT_DISABLED, "account_disabled")
    if (
        account.must_change_password
        and account.password_expires_at is not None
        and clock.parse(account.password_expires_at) <= now
    ):
        with repo.transaction():
            store.settle_attempt(repo.conn, attempt, ok=False, now=now, device=None)
        logger.info("Đăng nhập bằng mật khẩu tạm đã hết hạn: @%s, IP %s", handle, ip)
        detail = errors.TEMP_EXPIRED_OWNER if account.role == "owner" else errors.TEMP_EXPIRED
        raise AuthError(401, detail, "temporary_password_expired")

    upgraded = None
    if not stored.current_params():
        upgraded = await passwords.hash_password(password, admit=False)
    device_hash, _ = _device(request)
    now = clock.now()
    with repo.transaction():
        conn = repo.conn
        # Trong lúc băm, mật khẩu có thể đã bị đổi/đặt lại (mọi phiên đã bị xoá) hoặc tài khoản bị khoá:
        # khi đó lần đăng nhập này là lần sai, không được cấp phiên sống sót qua lần đổi đó.
        if not store.password_current(conn, account.id, stored.digest):
            stale = True
        else:
            stale = False
            if upgraded is not None:
                store.rehash_password(conn, account.id, stored, upgraded)
            token, expires = _new_session(conn, request, account.id, now)
            store.mark_login(conn, account.id, now)
            store.settle_attempt(conn, attempt, ok=True, now=now, device=device_hash)
    if stale:
        logger.info("Đăng nhập sai (mật khẩu vừa đổi): @%s, IP %s, %s", handle, ip, label or "?")
        raise AuthError(401, errors.BAD_LOGIN)
    _set_session_cookie(request, token, expires, now)
    logger.info("Đăng nhập: @%s, IP %s, %s", account.handle, ip, label or "?")
    with repo.locked() as conn:
        fresh = store.account_by_id(conn, account.id)
    assert fresh is not None
    return fresh


async def setup_owner(
    request: Request,
    setup_code: str,
    password: str,
    display_name: str | None,
    handle: str | None,
    *,
    terms_version: str | None = None,
) -> store.AuthRow:
    """`terms_version`: phiên bản Điều khoản người dùng vừa đồng ý (docs/compliance.md §3), ghi cùng transaction."""
    repo = _repo(request)
    ip = client_ip(request)
    now = clock.now()
    with repo.locked() as conn:
        owner = store.owner(conn)
        if owner is None or owner.password is not None:
            raise AuthError(409, errors.ALREADY_SET_UP, "already_set_up")
        blocked = ratelimit.setup_block(conn, now, ip=ip)
        code_ok = blocked is None and setup.check_code(conn, setup_code, now)
    if blocked is not None:
        logger.info("Thiết lập chủ máy bị chặn vì thử sai nhiều: IP %s", ip)
        raise errors.rate_limited(blocked)
    if not code_ok:
        with repo.transaction():
            store.record_attempt(repo.conn, "setup", handle=None, ip=ip, ok=False, now=now)
        logger.info("Mã thiết lập sai: IP %s", ip)
        raise AuthError(400, errors.BAD_SETUP_CODE, "bad_setup_code")

    # DB mới tinh (profile_completed = 0): nhận tên và handle; DB đã đặt tên thì bỏ qua hai trường này.
    new_name = new_handle = None
    if not owner.profile_completed:
        if display_name is not None and display_name.strip():
            new_name = validate_display_name(display_name)
        if handle is not None and handle.strip():
            new_handle = validate_handle(handle)
    final_handle = new_handle or owner.handle
    value = passwords.check_rules(password, handle=final_handle)
    if new_handle is not None and repo.handle_taken(new_handle, exclude_account_id=owner.id):
        raise HandleTaken(new_handle)

    hashed = await _hash_new(value)
    device_hash, _ = _device(request)
    now = clock.now()
    with repo.transaction():
        conn = repo.conn
        # Hai request đúng mã cùng lúc: chỉ một UPDATE thắng (rowcount = 1), cái sau nhận 409.
        owner_id = store.set_owner_password(conn, hashed, now)
        if owner_id is None:
            raise AuthError(409, errors.ALREADY_SET_UP, "already_set_up")
        # Mã có thể vừa được thay (lệnh setup-code chạy xen giữa): kiểm lại; sai thì rollback cả mật khẩu.
        if not setup.check_code(conn, setup_code, now):
            raise AuthError(400, errors.BAD_SETUP_CODE, "bad_setup_code")
        store.delete_setup(conn)
        if new_name is not None or new_handle is not None:
            try:
                conn.execute(
                    "UPDATE accounts SET display_name = COALESCE(?, display_name), handle = COALESCE(?, handle),"
                    " profile_completed = 1 WHERE id = ?",
                    (new_name, new_handle, owner_id),
                )
            except sqlite3.IntegrityError as exc:
                raise HandleTaken(final_handle) from exc
        if terms_version is not None:
            legal.accept(conn, owner_id, now, terms_version)
        token, expires = _new_session(conn, request, owner_id, now)
        store.mark_login(conn, owner_id, now)
        store.record_attempt(conn, "setup", handle=final_handle, ip=ip, ok=True, now=now, device=device_hash)
    _set_session_cookie(request, token, expires, now)
    logger.info("Chủ máy đã đặt mật khẩu lần đầu: @%s, IP %s", final_handle, ip)
    with repo.locked() as conn:
        fresh = store.account_by_id(conn, owner_id)
    assert fresh is not None
    return fresh


async def signup(
    request: Request,
    invite_code: str,
    raw_handle: str,
    display_name: str,
    password: str,
    *,
    terms_version: str | None = None,
) -> store.AuthRow:
    """`terms_version`: phiên bản Điều khoản người dùng vừa đồng ý (docs/compliance.md §3), ghi cùng transaction."""
    repo = _repo(request)
    if setup_needed(repo):
        raise errors.setup_required()
    ip = client_ip(request)
    now = clock.now()
    normalized = codes.normalize_code(invite_code)
    with repo.locked() as conn:
        blocked = ratelimit.signup_block(conn, now, ip=ip)
        invite = store.find_invite(conn, codes.code_hash(normalized)) if normalized and blocked is None else None
    if blocked is not None:
        logger.info("Tạo tài khoản bị chặn vì thử sai nhiều: IP %s", ip)
        raise errors.rate_limited(blocked)
    # Kiểm mã mời TRƯỚC (§3.5): mã sai, hết hạn, đã dùng, đã huỷ đều cùng một câu.
    if invite is None or invite.status(now) != "active":
        with repo.transaction():
            store.record_attempt(repo.conn, "signup", handle=None, ip=ip, ok=False, now=now)
        logger.info("Mã mời sai: IP %s", ip)
        raise AuthError(400, errors.BAD_INVITE, "bad_invite")

    handle = validate_handle(raw_handle)
    name = validate_display_name(display_name)
    value = passwords.check_rules(password, handle=handle)
    if repo.handle_taken(handle):
        raise HandleTaken(handle)

    hashed = await _hash_new(value)
    device_hash, _ = _device(request)
    now = clock.now()
    with repo.transaction():
        conn = repo.conn
        if not store.claim_invite(conn, invite.id, now):
            raise AuthError(400, errors.BAD_INVITE, "bad_invite")
        try:
            account_id = store.insert_member(
                conn, uid=new_uid(), handle=handle, display_name=name, invited_by=invite.created_by
            )
        except sqlite3.IntegrityError as exc:
            raise HandleTaken(handle) from exc  # rollback: mã chưa bị dùng
        store.set_invite_user(conn, invite.id, account_id)
        store.write_password(conn, account_id, hashed, now, temporary=False)
        if terms_version is not None:
            legal.accept(conn, account_id, now, terms_version)
        token, expires = _new_session(conn, request, account_id, now)
        store.mark_login(conn, account_id, now)
        store.record_attempt(conn, "signup", handle=handle, ip=ip, ok=True, now=now, device=device_hash)
    _set_session_cookie(request, token, expires, now)
    logger.info("Tạo tài khoản: @%s bằng mã mời số %d, IP %s", handle, invite.id, ip)
    with repo.locked() as conn:
        fresh = store.account_by_id(conn, account_id)
    assert fresh is not None
    return fresh


async def change_password(
    request: Request, account: store.AuthRow, current_password: str, new_password: str
) -> store.AuthRow:
    repo = _repo(request)
    ip = client_ip(request)
    key = store.account_key(account.id)  # luật theo tài khoản, không theo @handle (đổi handle không làm mới)
    now = clock.now()
    # Như đăng nhập: kiểm giới hạn và giữ chỗ lần thử trong cùng transaction, trước khi so mật khẩu hiện tại.
    with repo.transaction():
        conn = repo.conn
        blocked = ratelimit.change_password_block(conn, now, account_id=account.id)
        row = store.account_by_id(conn, account.id)
        assert row is not None
        attempt = None
        value = ""
        if blocked is None:
            # Sai luật (422) thì không tính là một lần đoán: transaction rollback, không ghi gì.
            value = passwords.check_rules(new_password, handle=row.handle, current=current_password)
            attempt = store.record_attempt(conn, "change_password", handle=key, ip=ip, ok=False, now=now)
    if blocked is not None or attempt is None:
        raise errors.rate_limited(blocked or 1)
    # Không xét `password_expires_at` ở đây (§1.2): người đã đăng nhập bằng mật khẩu tạm vẫn đổi được.
    stored = row.password
    if not await _verify_reserved(repo, attempt, current_password, stored) or stored is None:
        logger.info("Đổi mật khẩu: mật khẩu hiện tại sai, @%s, IP %s", row.handle, ip)
        raise AuthError(400, errors.BAD_CURRENT_PASSWORD, "bad_current_password")
    hashed = await passwords.hash_password(value, admit=False)
    now = clock.now()
    with repo.transaction():
        conn = repo.conn
        # Mật khẩu vừa bị đặt lại (hoặc tài khoản bị khoá) trong lúc băm: không ghi đè.
        current = store.password_current(conn, row.id, stored.digest)
        if current:
            store.write_password(conn, row.id, hashed, now, temporary=False)
            store.delete_sessions(conn, row.id)  # mọi phiên khác; phiên hiện tại được cấp token mới
            token, expires = _new_session(conn, request, row.id, now)
            store.settle_attempt(conn, attempt, ok=True, now=now, device=None)
    if not current:
        logger.info("Đổi mật khẩu: mật khẩu vừa được đặt lại, @%s, IP %s", row.handle, ip)
        raise AuthError(400, errors.BAD_CURRENT_PASSWORD, "bad_current_password")
    _set_session_cookie(request, token, expires, now)
    logger.info("Đổi mật khẩu: @%s, IP %s", row.handle, ip)
    with repo.locked() as conn:
        fresh = store.account_by_id(conn, row.id)
    assert fresh is not None
    return fresh


def logout(request: Request) -> None:
    repo = _repo(request)
    old = _old_session_hash(request)
    if old is not None:
        with repo.transaction():
            store.delete_session_by_hash(repo.conn, old)
    _clear_session_cookies(request)


def logout_all(request: Request, account: store.AuthRow) -> None:
    repo = _repo(request)
    with repo.transaction():
        count = store.delete_sessions(repo.conn, account.id)
    _clear_session_cookies(request)
    logger.info("Đăng xuất mọi thiết bị: @%s (%d thiết bị)", account.handle, count)


# ---------------------------------------------------------------------------- chủ máy


class AdminConflict(AuthError):
    def __init__(self, detail: str) -> None:
        super().__init__(409, detail)


async def reset_password(request: Request, actor: store.AuthRow, account_id: int) -> tuple[store.AdminRow, str]:
    """Mật khẩu tạm (hiện một lần): buộc đổi, hết hạn sau 72 giờ, xoá mọi phiên và các lần sai."""
    repo = _repo(request)
    with repo.locked() as conn:
        target = store.account_by_id(conn, account_id)
    if target is None:
        raise NotFound("Không tìm thấy tài khoản.")
    if target.id == actor.id:
        raise AdminConflict("Bạn hãy đổi mật khẩu của mình trong Tài khoản.")
    temporary = codes.temporary_password()
    hashed = await _hash_new(temporary)
    now = clock.now()
    with repo.transaction():
        conn = repo.conn
        store.write_password(conn, target.id, hashed, now, temporary=True)
        store.delete_sessions(conn, target.id)
        store.clear_failures(conn, target.handle, target.id)
    logger.info("Chủ máy @%s đặt lại mật khẩu cho @%s", actor.handle, target.handle)
    return admin_row(repo, target.id), temporary


def set_disabled(request: Request, actor: store.AuthRow, account_id: int, disabled: bool) -> store.AdminRow:
    repo = _repo(request)
    now = clock.now()
    with repo.transaction():
        conn = repo.conn
        target = store.account_by_id(conn, account_id)
        if target is None:
            raise NotFound("Không tìm thấy tài khoản.")
        if disabled:
            if target.role == "owner":
                raise AdminConflict("Không tạm khoá được tài khoản chủ máy.")
            store.set_status(conn, target.id, "disabled", now)
            store.delete_sessions(conn, target.id)
        else:
            store.set_status(conn, target.id, "active", now)
    logger.info("Chủ máy @%s %s @%s", actor.handle, "tạm khoá" if disabled else "mở khoá", target.handle)
    return admin_row(repo, target.id)


def admin_row(repo: Repo, account_id: int) -> store.AdminRow:
    with repo.locked() as conn:
        rows = store.admin_accounts(conn, clock.now(), account_id)
    if not rows:
        raise NotFound("Không tìm thấy tài khoản.")
    return rows[0]


def create_invite(request: Request, actor: store.AuthRow, note: str, days: int) -> tuple[store.InviteRow, str]:
    """Mã mời mới; mã đầy đủ chỉ trả về một lần (DB chỉ có hash và 4 ký tự cuối)."""
    repo = _repo(request)
    now = clock.now()
    code = codes.random_code()
    with repo.transaction():
        conn = repo.conn
        if store.active_invite_count(conn, now) >= store.MAX_ACTIVE_INVITES:
            raise AdminConflict(
                f"Đang có {store.MAX_ACTIVE_INVITES} mã mời còn hiệu lực. Hãy huỷ bớt mã chưa dùng rồi tạo lại."
            )
        invite_id = store.insert_invite(
            conn, hashed=codes.code_hash(code), hint=codes.code_hint(code), note=note, created_by=actor.id,
            now=now, days=days,
        )
        invite = store.get_invite(conn, invite_id)
    assert invite is not None
    logger.info("Chủ máy @%s tạo mã mời số %d (…%s)", actor.handle, invite.id, invite.hint)
    return invite, codes.format_invite(code)


def revoke_invite(request: Request, actor: store.AuthRow, invite_id: int) -> None:
    repo = _repo(request)
    now = clock.now()
    with repo.transaction():
        conn = repo.conn
        invite = store.get_invite(conn, invite_id)
        if invite is None:
            raise NotFound("Không tìm thấy mã mời.")
        if invite.used_at is not None:
            raise AdminConflict("Mã này đã được dùng.")
        store.revoke_invite(conn, invite_id, now)
    logger.info("Chủ máy @%s huỷ mã mời số %d (…%s)", actor.handle, invite.id, invite.hint)


__all__ = [
    "Resolved",
    "change_password",
    "create_invite",
    "log_handle",
    "login",
    "logout",
    "logout_all",
    "queue_cookie",
    "require_account",
    "reset_password",
    "resolve_session",
    "revoke_invite",
    "set_disabled",
    "setup_needed",
    "setup_owner",
    "signup",
]
