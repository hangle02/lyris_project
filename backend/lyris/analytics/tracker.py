"""Ghi sự kiện (docs/tracking-plan.md).

- `context(request)`: ai/thiết bị nào đang dùng (tài khoản nếu đã đăng nhập, `anon_id` từ cookie `lyris_anon`;
  chưa có cookie thì sinh và hẹn gửi). Gọi trong route, trước khi response bắt đầu (cookie đi kèm response).
  Trình duyệt gửi `Sec-GPC: 1`, hoặc thiết bị đã tắt chia sẻ (cookie `lyris_noshare`, đặt khi một tài khoản tắt
  chia sẻ trên thiết bị này), không bao giờ nhận cookie `lyris_anon`.
- `Tracker.emit(ctx, name, props)`: kiểm sự kiện theo bảng, bỏ qua nếu tài khoản đã tắt chia sẻ hoặc trình duyệt
  gửi Global Privacy Control (`Sec-GPC: 1`), chia lượt dùng (30 phút không hoạt động là lượt mới, ghi thêm
  `session_started`), ghi vào DB, báo bộ chuyển tiếp PostHog. Không bao giờ raise và không bao giờ chặn request:
  lỗi chỉ ghi log (tên sự kiện và loại lỗi, không có giá trị nào).
- `track(request, name, props)`: gộp hai bước trên cho route.
- `track_detached(request, name, props)`: sự kiện không gắn tài khoản, thiết bị, lượt hay story, chỉ lưu ở máy
  (không gửi PostHog): báo cáo nội dung (không ai biết ai báo cáo), xoá tài khoản.
- Tài khoản chưa đồng ý bản Điều khoản / Chính sách quyền riêng tư hiện tại: sự kiện chỉ lưu ở máy, không gửi
  PostHog (chính sách là nơi nói về việc gửi).
"""
from __future__ import annotations

import logging
import os
import secrets
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any

from starlette.requests import Request

from lyris.analytics import events, store
from lyris.auth import clock
from lyris.auth.net import (
    clear_cookie_header,
    cookie_name,
    cookie_names_present,
    read_cookie,
    request_is_secure,
    set_cookie_header,
)
from lyris.compliance import legal
from lyris.db.repo import Repo

logger = logging.getLogger("lyris.analytics")

ANON_COOKIE = "lyris_anon"
ANON_MAX_AGE = 365 * 24 * 3600
# Thiết bị đã tắt chia sẻ (một tài khoản tắt trên thiết bị này): không ghi gì khi chưa đăng nhập, không sinh anon_id.
NOSHARE_COOKIE = "lyris_noshare"
_CTX_KEY = "lyris_analytics_ctx"


def app_version() -> str:
    """Phiên bản app gắn vào mọi sự kiện: LYRIS_APP_VERSION, không thì phiên bản của gói `lyris`."""
    raw = (os.environ.get("LYRIS_APP_VERSION") or "").strip()
    if raw:
        return raw[:32]
    try:
        from importlib.metadata import version

        return version("lyris")[:32]
    except Exception:
        return "0.1.0"


@dataclass(frozen=True)
class TrackContext:
    """Người gửi sự kiện, chốt lúc route chạy (dùng tiếp được sau khi stream đã bắt đầu)."""

    account_id: int | None
    anon_id: str
    do_not_track: bool = False  # Sec-GPC: 1 (Global Privacy Control)
    device_opt_out: bool = False  # cookie `lyris_noshare`: chưa đăng nhập thì không ghi gì

    def for_account(self, account_id: int | None) -> TrackContext:
        return replace(self, account_id=account_id)


def _queue_cookie(request: Request, header: str) -> None:
    from lyris.auth.service import queue_cookie

    queue_cookie(request, header)


def anon_id(request: Request) -> str:
    """`anon_id` của thiết bị (cookie `lyris_anon`, HttpOnly, 1 năm). Chưa có thì sinh và hẹn gửi cookie."""
    found = read_cookie(request, ANON_COOKIE)
    if found is not None:
        return found[1]
    cached = getattr(request.state, "lyris_new_anon", None)
    if isinstance(cached, str):
        return cached
    value = secrets.token_urlsafe(16)
    secure = request_is_secure(request)
    _queue_cookie(request, set_cookie_header(cookie_name(ANON_COOKIE, secure), value, max_age=ANON_MAX_AGE, secure=secure))
    request.state.lyris_new_anon = value
    return value


def _gpc(request: Request) -> bool:
    return request.headers.get("sec-gpc", "").strip() == "1"


def device_opted_out(request: Request) -> bool:
    """Thiết bị đã tắt chia sẻ (cookie `lyris_noshare` hoặc `__Host-lyris_noshare` = "1")."""
    return any(request.cookies.get(name) == "1" for name in cookie_names_present(request, NOSHARE_COOKIE))


def forget_device(request: Request, *, opt_out: bool | None) -> None:
    """Thiết bị này không còn gắn với người dùng trước đó: xoá cookie `lyris_anon` (lần sau là một thiết bị mới).
    `opt_out=True` (tắt chia sẻ): đặt thêm `lyris_noshare` để không ghi gì khi chưa đăng nhập; False (bật lại):
    gỡ `lyris_noshare`; None (xoá tài khoản): giữ nguyên."""
    from lyris.auth.service import queue_cookie

    for name in cookie_names_present(request, ANON_COOKIE):
        queue_cookie(request, clear_cookie_header(name))
    request.state.lyris_new_anon = None
    if opt_out is True:
        secure = request_is_secure(request)
        queue_cookie(request, set_cookie_header(cookie_name(NOSHARE_COOKIE, secure), "1", max_age=ANON_MAX_AGE, secure=secure))
    elif opt_out is False:
        for name in cookie_names_present(request, NOSHARE_COOKIE):
            queue_cookie(request, clear_cookie_header(name))
    # Phần còn lại của request không dùng lại anon_id cũ (cookie của request vẫn còn tới hết request này).
    base: TrackContext | None = getattr(request.state, _CTX_KEY, None)
    if base is None:
        base = TrackContext(account_id=None, anon_id="", do_not_track=_gpc(request), device_opt_out=device_opted_out(request))
    noshare = base.device_opt_out if opt_out is None else opt_out
    setattr(request.state, _CTX_KEY, replace(base, anon_id="", device_opt_out=noshare))


def allow_device(request: Request) -> None:
    """Bật lại chia sẻ: gỡ `lyris_noshare` của thiết bị này (nếu có)."""
    from lyris.auth.service import queue_cookie

    for name in cookie_names_present(request, NOSHARE_COOKIE):
        queue_cookie(request, clear_cookie_header(name))


def honour_opt_out_on_login(request: Request, account_id: int, repo: Repo) -> None:
    """Tài khoản đã tắt chia sẻ vừa đăng nhập trên thiết bị này: xoá sự kiện lúc chưa đăng nhập của thiết bị (chưa
    gắn tài khoản nào) và đánh dấu thiết bị không chia sẻ (`forget_device`). Không bao giờ raise."""
    try:
        with repo.transaction():
            if not store.opted_out(repo.conn, account_id):
                return
            anon = device_anon(request)
            if anon:
                store.forget_anon(repo.conn, anon)
        forget_device(request, opt_out=True)
    except Exception as exc:
        logger.warning("Không đánh dấu được thiết bị không chia sẻ (%s)", type(exc).__name__)


def device_anon(request: Request) -> str:
    """`anon_id` hiện có của thiết bị (không sinh mới), hoặc ""."""
    found = read_cookie(request, ANON_COOKIE)
    return "" if found is None else found[1]


def session_account(request: Request) -> int | None:
    """Tài khoản đang đăng nhập (active, không chờ đổi mật khẩu), hoặc None. Không raise."""
    try:
        from lyris.auth.service import resolve_session

        resolved = resolve_session(request)
    except Exception:
        return None
    account = resolved.account
    if account is None or account.must_change_password:
        return None
    return account.id


def context(request: Request, *, account_id: int | None | bool = True) -> TrackContext:
    """Ngữ cảnh của request. `account_id=True`: đọc từ phiên (route đã qua `current_account`, phiên đã đọc);
    số hoặc None: dùng giá trị đó, không đọc phiên (route đăng nhập: cookie cũ của request không còn đúng)."""
    base: TrackContext | None = getattr(request.state, _CTX_KEY, None)
    if base is None:
        gpc = _gpc(request)
        noshare = device_opted_out(request)
        # GPC hoặc thiết bị đã tắt chia sẻ: không sinh định danh thiết bị (không cookie 1 năm nào được gửi).
        anon = "" if gpc or noshare else anon_id(request)
        base = TrackContext(account_id=None, anon_id=anon, do_not_track=gpc, device_opt_out=noshare)
        setattr(request.state, _CTX_KEY, base)
    if account_id is True:
        return base.for_account(session_account(request))
    if account_id is False:
        return base.for_account(None)
    return base.for_account(account_id)


class Tracker:
    """Ghi sự kiện vào DB của app; `on_pending` báo bộ chuyển tiếp PostHog có việc (None = không chuyển tiếp)."""

    def __init__(
        self,
        repo: Repo,
        *,
        forward: bool = False,
        version: str | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.repo = repo
        self.forward = forward
        self.version = version if version is not None else app_version()
        self._clock = now  # None = lyris.auth.clock.now (test giả được giờ)
        self.on_pending: Callable[[], None] | None = None

    def _now_(self) -> datetime:
        return self._clock() if self._clock is not None else clock.now()

    def emit(
        self,
        ctx: TrackContext,
        name: str,
        props: Mapping[str, Any] | None = None,
        *,
        story_id: int | None = None,
        source: events.Source = "server",
    ) -> bool:
        """Ghi một sự kiện. Trả True nếu đã ghi. Sự kiện sai bảng từ server: log lỗi (lỗi lập trình), bỏ."""
        try:
            clean = events.validate(name, props, source=source)
        except events.EventRejected as exc:
            if source == "server":
                logger.error("Sự kiện %s sai bảng: %s", name, exc)
            return False
        try:
            return self._write(ctx, name, clean, story_id, source)
        except Exception as exc:  # số liệu không bao giờ được làm hỏng request
            logger.warning("Không ghi được sự kiện %s (%s)", name, type(exc).__name__)
            return False

    def _write(
        self, ctx: TrackContext, name: str, props: dict[str, Any], story_id: int | None, source: str
    ) -> bool:
        if ctx.do_not_track or (ctx.account_id is None and ctx.device_opt_out):
            return False
        now = self._now_()
        ts = clock.iso(now)
        with self.repo.transaction():
            conn = self.repo.conn
            forward = self.forward
            if ctx.account_id is not None:
                if store.opted_out(conn, ctx.account_id):
                    return False
                # Chưa đồng ý chính sách hiện tại (nơi nói về việc gửi PostHog): chỉ lưu ở máy.
                if forward and legal.terms_required(conn, ctx.account_id):
                    forward = False
            last = store.last_session(conn, ctx.anon_id, ctx.account_id)
            if last is not None and now - clock.parse(last[1]) < store.SESSION_IDLE:
                session = last[0]
            else:
                session = secrets.token_urlsafe(12)
                store.insert(
                    conn, ts=ts, name="session_started", account_id=ctx.account_id, anon_id=ctx.anon_id,
                    session_id=session, story_id=None, props_json="{}", source="server",
                    app_version=self.version, pending=forward,
                )
            store.insert(
                conn, ts=ts, name=name, account_id=ctx.account_id, anon_id=ctx.anon_id, session_id=session,
                story_id=story_id, props_json=events.dumps(props), source=source, app_version=self.version,
                pending=forward,
            )
        if forward and self.on_pending is not None:
            try:
                self.on_pending()
            except Exception:
                pass
        return True

    def emit_detached(self, ctx: TrackContext, name: str, props: Mapping[str, Any] | None = None) -> bool:
        """Một sự kiện của server không gắn tài khoản, thiết bị, lượt hay story, chỉ lưu ở máy (không bao giờ gửi
        PostHog). Vẫn tôn trọng GPC, thiết bị đã tắt chia sẻ và tài khoản `ctx.account_id` đã tắt chia sẻ.
        Không bao giờ raise."""
        try:
            clean = events.validate(name, props, source="server")
        except events.EventRejected as exc:
            logger.error("Sự kiện %s sai bảng: %s", name, exc)
            return False
        if ctx.do_not_track or (ctx.account_id is None and ctx.device_opt_out):
            return False
        try:
            ts = clock.iso(self._now_())
            with self.repo.transaction():
                conn = self.repo.conn
                if ctx.account_id is not None and store.opted_out(conn, ctx.account_id):
                    return False
                store.insert(
                    conn, ts=ts, name=name, account_id=None, anon_id="", session_id="", story_id=None,
                    props_json=events.dumps(clean), source="server", app_version=self.version, pending=False,
                )
            return True
        except Exception as exc:
            logger.warning("Không ghi được sự kiện %s (%s)", name, type(exc).__name__)
            return False

    def record_opt_out(self) -> None:
        """Một dòng `analytics_opt_out` không gắn tài khoản hay thiết bị (chỉ để đếm tỉ lệ tắt), chỉ lưu ở máy."""
        try:
            ts = clock.iso(self._now_())
            with self.repo.transaction():
                store.insert(
                    self.repo.conn, ts=ts, name="analytics_opt_out", account_id=None, anon_id="", session_id="",
                    story_id=None, props_json="{}", source="server", app_version=self.version, pending=False,
                )
        except Exception as exc:
            logger.warning("Không ghi được sự kiện analytics_opt_out (%s)", type(exc).__name__)


def tracker_of(request: Request) -> Tracker | None:
    tracker: Tracker | None = getattr(request.app.state, "analytics", None)
    return tracker


def track(
    request: Request,
    name: str,
    props: Mapping[str, Any] | None = None,
    *,
    story_id: int | None = None,
    account_id: int | None | bool = True,
) -> bool:
    """Ghi sự kiện của server cho request này. Không bao giờ raise."""
    tracker = tracker_of(request)
    if tracker is None:
        return False
    try:
        ctx = context(request, account_id=account_id)
    except Exception as exc:
        logger.warning("Không đọc được ngữ cảnh cho sự kiện %s (%s)", name, type(exc).__name__)
        return False
    return tracker.emit(ctx, name, props, story_id=story_id)


def track_detached(
    request: Request, name: str, props: Mapping[str, Any] | None = None, *, account_id: int | None
) -> bool:
    """Sự kiện không gắn ai (xem `Tracker.emit_detached`). Không đọc hay sinh cookie `lyris_anon`. `account_id`:
    người làm (chỉ để kiểm họ đã tắt chia sẻ chưa; không ghi vào sự kiện). Không bao giờ raise."""
    tracker = tracker_of(request)
    if tracker is None:
        return False
    try:
        ctx = TrackContext(account_id=account_id, anon_id="", do_not_track=_gpc(request), device_opt_out=device_opted_out(request))
    except Exception:
        return False
    return tracker.emit_detached(ctx, name, props)


__all__ = [
    "ANON_COOKIE",
    "NOSHARE_COOKIE",
    "TrackContext",
    "Tracker",
    "allow_device",
    "anon_id",
    "app_version",
    "context",
    "device_anon",
    "device_opted_out",
    "forget_device",
    "honour_opt_out_on_login",
    "session_account",
    "track",
    "track_detached",
    "tracker_of",
]
