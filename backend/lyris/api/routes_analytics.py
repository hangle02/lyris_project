"""Event tracking (docs/tracking-plan.md).

- `POST /api/events`: sự kiện chỉ giao diện biết (mở trang, bấm lọc, mở thẻ suy nghĩ...). Tối đa 20 sự kiện một
  lần, chỉ sự kiện có trong bảng dành cho client, giới hạn tần suất, cần header CSRF như mọi request ghi. Chưa
  đăng nhập vẫn gửi được vài sự kiện trước đăng nhập (`app_opened`, `signup_viewed`), chỉ gắn `anon_id`: mỗi tên
  một lần mỗi request, tối đa 10 request mỗi phút mỗi IP, và tối đa 30 thiết bị mới (request không có cookie
  `lyris_anon`) mỗi giờ mỗi IP; quá thì bỏ sự kiện, không sinh định danh mới (không ai bơm được người dùng giả).
  Luôn 202 `{accepted, dropped}`: sự kiện sai bảng, của tài khoản đã tắt chia sẻ hoặc có `Sec-GPC: 1` bị bỏ.
- `GET /api/admin/analytics/summary`: số liệu tổng (chủ máy): số sự kiện, DAU/WAU/MAU, phễu, giữ chân D1/D7.
- `GET /api/admin/analytics/export.csv` / `.jsonl`: xuất sự kiện cho Apero (chủ máy).

Sự kiện server biết (story mới, gửi tin, trả lời xong...) ghi ngay tại route (`lyris.analytics.track`), không
qua đây.
"""
from __future__ import annotations

import csv
import io
import json
import time
from collections import deque
from collections.abc import Iterator
from datetime import date, datetime, time as dtime, timedelta, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from lyris.analytics import events as catalog
from lyris.analytics import store
from lyris.analytics.tracker import ANON_COOKIE, context, device_opted_out, session_account, tracker_of
from lyris.api.deps import owner_auth
from lyris.auth import clock
from lyris.auth.net import client_ip, read_cookie
from lyris.db.repo import Repo

router = APIRouter(prefix="/api")
admin_router = APIRouter(prefix="/api/admin/analytics", dependencies=[Depends(owner_auth)])

# Route không qua `current_account`: đăng nhập là tuỳ chọn (test xếp loại route đọc danh sách này).
OPTIONAL_AUTH_ROUTES: frozenset[tuple[str, str]] = frozenset({("POST", "/api/events")})

MAX_BATCH = 20
RATE_WINDOW_S = 60.0
RATE_MAX_REQUESTS = 30  # mỗi tài khoản mỗi phút
PRE_AUTH_MAX_REQUESTS = 10  # mỗi IP mỗi phút khi chưa đăng nhập
NEW_DEVICE_WINDOW_S = 3600.0
NEW_DEVICE_MAX = 30  # thiết bị mới (chưa có cookie lyris_anon) mỗi IP mỗi giờ
RATE_DETAIL = "Bạn thao tác hơi nhanh. Đợi một chút rồi thử lại."

PropValue = Annotated[str, Field(max_length=64)] | bool | int


class ClientEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(max_length=64)
    props: dict[Annotated[str, Field(max_length=32)], PropValue] = Field(default_factory=dict)
    story_id: int | None = None


class EventsBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    events: list[ClientEvent] = Field(min_length=1, max_length=MAX_BATCH)


class EventsAccepted(BaseModel):
    accepted: int
    dropped: int


class RateLimiter:
    """Cửa sổ trượt trong bộ nhớ (một tiến trình): tối đa `limit` request mỗi `window` giây cho mỗi khoá."""

    def __init__(self, limit: int = RATE_MAX_REQUESTS, window: float = RATE_WINDOW_S) -> None:
        self.limit = limit
        self.window = window
        self._hits: dict[str, deque[float]] = {}

    def allow(self, key: str, now: float | None = None) -> bool:
        moment = time.monotonic() if now is None else now
        hits = self._hits.setdefault(key, deque())
        while hits and moment - hits[0] >= self.window:
            hits.popleft()
        if len(hits) >= self.limit:
            return False
        hits.append(moment)
        if len(self._hits) > 10_000:  # không để bộ nhớ phình: bỏ các khoá đã nguội
            for stale in [k for k, v in self._hits.items() if not v or moment - v[-1] >= self.window]:
                del self._hits[stale]
        return True


def _limiter(request: Request, attr: str = "events_limiter", limit: int = RATE_MAX_REQUESTS,
             window: float = RATE_WINDOW_S) -> RateLimiter:
    limiter: RateLimiter | None = getattr(request.app.state, attr, None)
    if limiter is None:
        limiter = RateLimiter(limit, window)
        setattr(request.app.state, attr, limiter)
    return limiter


def _rate_limited() -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": RATE_DETAIL, "technical": None, "code": "rate_limited"},
        headers={"Retry-After": str(int(RATE_WINDOW_S))},
    )


def _repo(request: Request) -> Repo:
    repo: Repo = request.app.state.repo
    return repo


@router.post("/events", status_code=202, response_model=EventsAccepted)
def post_events(request: Request, body: EventsBody) -> EventsAccepted | JSONResponse:
    tracker = tracker_of(request)
    if tracker is None:
        return EventsAccepted(accepted=0, dropped=len(body.events))
    account_id = session_account(request)
    if account_id is not None:
        if not _limiter(request).allow(f"u{account_id}"):
            return _rate_limited()
    else:
        ip = client_ip(request)
        if not _limiter(request, "events_anon_limiter", PRE_AUTH_MAX_REQUESTS).allow(f"ip{ip}"):
            return _rate_limited()
        new_device = (
            read_cookie(request, ANON_COOKIE) is None
            and not device_opted_out(request)
            and request.headers.get("sec-gpc", "").strip() != "1"
        )
        devices = _limiter(request, "events_device_limiter", NEW_DEVICE_MAX, NEW_DEVICE_WINDOW_S)
        if new_device and not devices.allow(f"ip{ip}"):
            # Không sinh thêm định danh thiết bị cho IP này: bỏ cả lô (không lỗi, số liệu thôi).
            return EventsAccepted(accepted=0, dropped=len(body.events))
    ctx = context(request)
    accepted = 0
    seen: set[str] = set()
    for item in body.events:
        spec = catalog.EVENTS.get(item.name)
        if spec is None or item.name not in catalog.CLIENT_EVENTS:
            continue
        if ctx.account_id is None:
            if not spec.pre_auth or item.name in seen:
                continue  # chưa đăng nhập: chỉ sự kiện trước đăng nhập, mỗi tên một lần
            seen.add(item.name)
        props: dict[str, Any] = dict(item.props)
        story_id: int | None = None
        if spec.story_scoped and item.story_id is not None and ctx.account_id is not None:
            with _repo(request).locked() as conn:
                mode = store.story_mode(conn, item.story_id, ctx.account_id)
            if mode is not None:
                story_id = item.story_id
                if "mode" in spec.props:
                    props["mode"] = mode  # giá trị thật của story, không tin client
        if tracker.emit(ctx, item.name, props, story_id=story_id, source="client"):
            accepted += 1
    return EventsAccepted(accepted=accepted, dropped=len(body.events) - accepted)


# ---------------------------------------------------------------------------- chủ máy


class EventCount(BaseModel):
    name: str
    count: int


class DailyActive(BaseModel):
    date: str
    active: int


class FunnelStep(BaseModel):
    step: str
    label: str
    users: int  # người làm bước này trong khoảng ngày
    converted: int  # người làm bước này và mọi bước trước


class Retention(BaseModel):
    cohort: int
    retained: int
    rate: float | None


class RetentionOut(BaseModel):
    d1: Retention
    d7: Retention


class AnalyticsSummary(BaseModel):
    since: str
    until: str
    days: int
    total_events: int
    counts: list[EventCount]
    dau: int
    wau: int
    mau: int
    daily: list[DailyActive]
    funnel: list[FunnelStep]
    retention: RetentionOut
    posthog_enabled: bool


@admin_router.get("/summary", response_model=AnalyticsSummary)
def analytics_summary(request: Request, days: int = Query(default=30, ge=1, le=180)) -> AnalyticsSummary:
    with _repo(request).locked() as conn:
        data = store.summary(conn, clock.now(), days)
    return AnalyticsSummary(**data, posthog_enabled=getattr(request.app.state, "posthog", None) is not None)


def _day_bound(value: date | None) -> str | None:
    """Ngày (giờ Việt Nam) -> mốc UTC lưu trong DB."""
    if value is None:
        return None
    local = datetime.combine(value, dtime.min, tzinfo=timezone(timedelta(hours=7)))
    return clock.iso(local)


def _rows(request: Request, since: date | None, until: date | None) -> Iterator[dict[str, Any]]:
    repo = _repo(request)
    end = until + timedelta(days=1) if until is not None else None
    return store.iter_export(repo.locked, since=_day_bound(since), until=_day_bound(end))


def _filename(ext: str) -> str:
    return f'attachment; filename="lyris-events-{(clock.now() + timedelta(hours=7)).strftime("%Y%m%d")}.{ext}"'


@admin_router.get("/export.csv")
def export_csv(request: Request, since: date | None = None, until: date | None = None) -> StreamingResponse:
    """CSV (UTF-8, có dòng tiêu đề). `since`/`until`: ngày theo giờ Việt Nam, gồm cả hai đầu."""

    def lines() -> Iterator[str]:
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=list(store.EXPORT_COLUMNS), lineterminator="\n")
        writer.writeheader()
        for row in _rows(request, since, until):
            writer.writerow(row)
            if buffer.tell() > 64_000:
                yield buffer.getvalue()
                buffer.seek(0)
                buffer.truncate()
        yield buffer.getvalue()

    return StreamingResponse(
        lines(), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": _filename("csv")}
    )


@admin_router.get("/export.jsonl")
def export_jsonl(request: Request, since: date | None = None, until: date | None = None) -> StreamingResponse:
    """Mỗi dòng một sự kiện (JSON); `props` là object."""

    def lines() -> Iterator[str]:
        for row in _rows(request, since, until):
            out = dict(row)
            try:
                out["props"] = json.loads(str(row["props"]))
            except ValueError:
                out["props"] = {}
            yield json.dumps(out, ensure_ascii=False) + "\n"

    return StreamingResponse(
        lines(), media_type="application/x-ndjson; charset=utf-8", headers={"Content-Disposition": _filename("jsonl")}
    )


__all__ = ["OPTIONAL_AUTH_ROUTES", "AnalyticsSummary", "RateLimiter", "admin_router", "router"]
