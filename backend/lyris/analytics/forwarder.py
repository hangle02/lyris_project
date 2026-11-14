"""Chuyển tiếp sự kiện sang PostHog (docs/tracking-plan.md §PostHog).

Chỉ chạy khi có `LYRIS_POSTHOG_KEY`. Một asyncio task trong lifespan của app: thức dậy khi có sự kiện mới (hoặc
mỗi `interval` giây), lấy tối đa `batch_size` sự kiện tới hạn trong DB (`posthog_state = 'pending'`) và gửi một
lần `POST {host}/batch/` bằng httpx. Request của người dùng không bao giờ chờ việc gửi.

- Thành công (2xx): `sent`.
- 400/413 (dữ liệu bị từ chối): `failed` ngay, không gửi lại.
- Lỗi mạng, 429, 5xx, 401/403: thử lại với backoff (30 s, 1, 2, 4... phút, tối đa 6 giờ); quá `MAX_ATTEMPTS`
  lần thì `failed`.
- `distinct_id`: uid của tài khoản, chưa đăng nhập thì `anon_id`. Không gửi IP (`$ip` null, `$geoip_disable`),
  không gửi handle, tên hay bất kỳ chữ nào của người dùng: chỉ thuộc tính đã kiểm theo bảng sự kiện.
- `uuid` của mỗi sự kiện cố định theo dòng trong DB, nên gửi lại sau lỗi mạng không tạo bản trùng ở PostHog.
- Tài khoản đã tắt chia sẻ: sự kiện chưa gửi chuyển về `local` (thực tế đã bị xoá khi tắt).
- Không bao giờ ghi khoá API vào log.
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

import httpx

from lyris.analytics import store
from lyris.analytics.store import OutboxRow
from lyris.auth import clock
from lyris.db.repo import Repo

logger = logging.getLogger("lyris.analytics")

DEFAULT_HOST = "https://us.i.posthog.com"
BATCH_SIZE = 50
INTERVAL_S = 10.0
MAX_ATTEMPTS = 8
BASE_BACKOFF = timedelta(seconds=30)
MAX_BACKOFF = timedelta(hours=6)
TIMEOUT_S = 10.0
_UUID_NS = uuid.UUID("6f1b3c55-6a54-4c47-9f3e-2f0d6c1a7b21")
# Sự kiện nối các sự kiện lúc chưa đăng nhập (anon_id) với tài khoản: gửi kèm một `$identify`.
IDENTIFY_ON = frozenset({"signup_completed", "login_succeeded", "owner_setup_completed"})


def backoff(attempts: int) -> timedelta:
    """Chờ trước lần gửi thứ `attempts + 1` (attempts = số lần đã lỗi, kể cả lần vừa rồi)."""
    seconds = BASE_BACKOFF.total_seconds() * (2 ** max(0, attempts - 1))
    return min(MAX_BACKOFF, timedelta(seconds=seconds))


def event_uuid(row: OutboxRow, suffix: str = "") -> str:
    return str(uuid.uuid5(_UUID_NS, f"{row.id}|{row.ts}|{row.anon_id}|{row.name}{suffix}"))


def to_posthog(row: OutboxRow) -> list[dict[str, Any]]:
    """Một dòng DB -> một (hoặc hai, kèm `$identify`) sự kiện của PostHog batch API."""
    try:
        props: dict[str, Any] = json.loads(row.props_json)
    except ValueError:
        props = {}
    common = {
        "$lib": "lyris",
        "$ip": None,
        "$geoip_disable": True,
        "$process_person_profile": row.identified,
        "app_version": row.app_version,
        "source": row.source,
    }
    if row.session_id:
        common["$session_id"] = row.session_id
    properties = {**props, **common}
    if row.story_id is not None:
        properties["story_id"] = row.story_id
    out = [
        {
            "event": row.name,
            "distinct_id": row.distinct_id,
            "timestamp": row.ts,
            "uuid": event_uuid(row),
            "properties": properties,
        }
    ]
    if row.identified and row.name in IDENTIFY_ON and row.anon_id and row.anon_id != row.distinct_id:
        out.append(
            {
                "event": "$identify",
                "distinct_id": row.distinct_id,
                "timestamp": row.ts,
                "uuid": event_uuid(row, ":identify"),
                "properties": {"$anon_distinct_id": row.anon_id, **common},
            }
        )
    return out


class PostHogForwarder:
    def __init__(
        self,
        repo: Repo,
        *,
        api_key: str,
        host: str = DEFAULT_HOST,
        transport: httpx.AsyncBaseTransport | None = None,
        batch_size: int = BATCH_SIZE,
        interval: float = INTERVAL_S,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.repo = repo
        self._key = api_key
        self.url = host.rstrip("/") + "/batch/"
        self._transport = transport
        self.batch_size = batch_size
        self.interval = interval
        self._clock = now  # None = lyris.auth.clock.now (test giả được giờ)
        self._wake = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self._client: httpx.AsyncClient | None = None
        # Sau một lô lỗi: không gửi gì tới lúc này (sự kiện mới không kéo PostHog đang hỏng ra gọi liên tục).
        self._pause_until: datetime | None = None

    def _now_(self) -> datetime:
        return self._clock() if self._clock is not None else clock.now()

    def __repr__(self) -> str:  # không lộ khoá khi bị in ra
        return f"PostHogForwarder(url={self.url!r})"

    def notify(self) -> None:
        self._wake.set()

    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(transport=self._transport, timeout=TIMEOUT_S)
        return self._client

    async def flush_once(self) -> int:
        """Gửi một lô. Trả số sự kiện đã gửi thành công (0: không có gì, hoặc lỗi và đã hẹn lại)."""
        now = self._now_()
        if self._pause_until is not None and now < self._pause_until:
            return 0
        with self.repo.transaction():
            rows = store.outbox(self.repo.conn, now, self.batch_size)
        if not rows:
            return 0
        ids = [r.id for r in rows]
        batch: list[dict[str, Any]] = []
        for row in rows:
            batch.extend(to_posthog(row))
        status: int | None = None
        try:
            resp = await self._http().post(self.url, json={"api_key": self._key, "batch": batch})
            status = resp.status_code
        except (httpx.HTTPError, OSError) as exc:
            logger.info("Chưa gửi được %d sự kiện sang PostHog (%s); sẽ thử lại", len(rows), type(exc).__name__)
        with self.repo.transaction():
            conn = self.repo.conn
            if status is not None and 200 <= status < 300:
                store.mark_sent(conn, ids)
                self._pause_until = None
                return len(ids)
            if status in (400, 413):
                store.mark_failed(conn, ids)
                logger.warning("PostHog từ chối %d sự kiện (HTTP %s); bỏ lô này", len(ids), status)
                return 0
            attempts = max(r.attempts for r in rows) + 1
            retry_at = self._now_() + backoff(attempts)
            store.mark_retry(conn, ids, retry_at, max_attempts=MAX_ATTEMPTS)
            self._pause_until = retry_at
        if status is not None:
            logger.info("PostHog trả HTTP %s cho %d sự kiện; sẽ thử lại", status, len(ids))
        return 0

    async def flush(self) -> int:
        """Gửi tới khi hết sự kiện tới hạn hoặc một lô lỗi. Trả tổng số đã gửi."""
        total = 0
        while True:
            sent = await self.flush_once()
            if sent == 0:
                return total
            total += sent

    async def _loop(self) -> None:
        while True:
            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(self._wake.wait(), timeout=self.interval)
            self._wake.clear()
            try:
                await self.flush()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # không bao giờ để task chết
                logger.warning("Lỗi khi gửi sự kiện sang PostHog (%s)", type(exc).__name__)

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._loop(), name="lyris-posthog")

    async def stop(self) -> None:
        task, self._task = self._task, None
        if task is not None:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await task
        client, self._client = self._client, None
        if client is not None:
            with contextlib.suppress(Exception):
                await client.aclose()


__all__ = ["DEFAULT_HOST", "IDENTIFY_ON", "MAX_ATTEMPTS", "PostHogForwarder", "backoff", "to_posthog"]
