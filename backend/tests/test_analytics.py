"""Event tracking (docs/tracking-plan.md): bảng sự kiện, chia khoảng, chuyển tiếp PostHog, dọn sự kiện cũ, migration.

Không gọi Ollama, không đụng `data/`: DB dựng trong thư mục tạm của test. Bộ chuyển tiếp PostHog dùng
`httpx.MockTransport` (không ra mạng).
"""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
import pytest

from lyris.analytics import buckets, events, store
from lyris.analytics.forwarder import MAX_ATTEMPTS, PostHogForwarder, backoff, to_posthog
from lyris.analytics.replies import failure_reason
from lyris.analytics.tracker import TrackContext, Tracker
from lyris.auth import clock
from lyris.chat.gate import WAIT_TIMEOUT_DETAIL
from lyris.compliance import legal
from lyris.config import get_settings
from lyris.db.connection import MIGRATIONS_DIR, connect, migrate
from lyris.db.repo import Repo, new_uid
from lyris.llm import errors as llm_errors

DOC = Path(__file__).resolve().parents[2] / "docs" / "tracking-plan.md"
T0 = datetime(2026, 11, 14, 3, 0, tzinfo=timezone.utc)


class Clock:
    def __init__(self, start: datetime = T0) -> None:
        self.t = start

    def __call__(self) -> datetime:
        return self.t

    def advance(self, **kw: float) -> None:
        self.t += timedelta(**kw)


@pytest.fixture
def repo() -> Repo:
    conn = connect(":memory:")
    migrate(conn)
    return Repo(conn)


def owner_id(repo: Repo) -> int:
    account = repo.owner_account()
    assert account.id is not None
    return account.id


def rows(repo: Repo, sql: str = "SELECT * FROM analytics_events ORDER BY id", *params: Any) -> list[sqlite3.Row]:
    with repo.locked() as conn:
        return conn.execute(sql, params).fetchall()


# ---------------------------------------------------------------------------- bảng sự kiện


def test_catalog_is_focused_snake_case_and_documented() -> None:
    names = set(events.EVENTS)
    assert 30 <= len(names) <= 40, len(names)
    assert all(re.fullmatch(r"[a-z][a-z0-9_]*", n) for n in names)
    doc = DOC.read_text(encoding="utf-8")
    # Dòng của bảng sự kiện: | `tên` | S/C/S, C | ...
    documented = set(re.findall(r"^\|\s*`([a-z0-9_]+)`\s*\|\s*(?:S|C|S, C)\s*\|", doc, flags=re.M))
    assert names == documented, (sorted(names - documented), sorted(documented - names))
    for name, src in re.findall(r"^\|\s*`([a-z0-9_]+)`\s*\|\s*(S|C|S, C)\s*\|", doc, flags=re.M):
        expected = {"S": {"server"}, "C": {"client"}, "S, C": {"server", "client"}}[src]
        assert set(events.EVENTS[name].sources) == expected, name
    # Mọi enum chỉ có mã ASCII ngắn (không có chữ người dùng).
    for spec in events.EVENTS.values():
        for rule in spec.props.values():
            if isinstance(rule, events.Choice):
                assert all(re.fullmatch(r"[a-z0-9_]{1,24}", v) for v in rule.values), spec.name
        assert spec.required <= set(spec.props), spec.name
    assert events.PRE_AUTH_EVENTS == {"app_opened", "signup_viewed"}
    assert events.PRE_AUTH_EVENTS <= events.CLIENT_EVENTS


@pytest.mark.parametrize(
    ("name", "props", "source"),
    [
        ("unknown_event", {}, "server"),
        ("message_sent", {"mode": "story"}, "server"),  # thiếu thuộc tính bắt buộc
        ("story_started", {"mode": "story", "source": "own", "language": "vi", "title": "x"}, "server"),  # lạ
        ("story_started", {"mode": "novel", "source": "own", "language": "vi"}, "server"),  # ngoài enum
        ("story_started", {"mode": "Cô ấy nói: chào anh", "source": "own", "language": "vi"}, "server"),  # chữ tự do
        ("lore_unlocked", {"count": 0}, "server"),  # ngoài khoảng
        ("lore_unlocked", {"count": True}, "server"),  # bool không phải số
        ("lore_unlocked", {"count": "3"}, "server"),  # chuỗi không phải số
        ("show_thoughts_toggled", {"enabled": 1}, "server"),  # số không phải bool
        ("invite_created", {"expires_days": 3}, "server"),  # ngoài tập
        ("story_started", {"mode": "story", "source": "own", "language": "vi"}, "client"),  # client không gửi được
        ("explore_viewed", {}, "server"),  # server không tự bịa sự kiện giao diện
        ("app_opened", {f"k{i}": True for i in range(11)}, "client"),  # quá nhiều thuộc tính
    ],
)
def test_validate_rejects(name: str, props: dict[str, Any], source: events.Source) -> None:
    with pytest.raises(events.EventRejected):
        events.validate(name, props, source=source)


def test_validate_accepts_and_copies() -> None:
    props = {"mode": "dm", "source": "public", "language": "en"}
    clean = events.validate("story_started", props, source="server")
    assert clean == props and clean is not props
    assert events.validate("content_reported", {"reason": "minor_safety", "target": "message"}, source="server")
    with pytest.raises(events.EventRejected):  # chỉ server ghi (không gắn ai), client không gửi được
        events.validate("content_reported", {"reason": "minor_safety", "target": "message"}, source="client")
    assert events.validate("app_opened", {}, source="client") == {}


def test_buckets() -> None:
    assert [buckets.length_bucket(n) for n in (0, 20, 21, 80, 81, 200, 201, 500, 501)] == [
        "1_20", "1_20", "21_80", "21_80", "81_200", "81_200", "201_500", "201_500", "501_plus"
    ]
    assert [buckets.turn_bucket(n) for n in (1, 2, 4, 5, 9, 10, 19, 20)] == [
        "1", "2_4", "2_4", "5_9", "5_9", "10_19", "10_19", "20_plus"
    ]
    assert [buckets.ttft_bucket(v) for v in (None, 999, 1000, 9999, 10_000, 30_000)] == [
        "none", "lt_1s", "1_3s", "3_10s", "10_30s", "30s_plus"
    ]
    assert [buckets.days_bucket(d) for d in (1, 1.9, 2, 3.5, 4, 7.9, 8, 30.5, 31)] == [
        "1", "1", "2_3", "2_3", "4_7", "4_7", "8_30", "8_30", "31_plus"
    ]
    assert [buckets.small_count_bucket(n) for n in (1, 2, 5, 6)] == ["1", "2_5", "2_5", "6_plus"]
    assert [buckets.age_bucket(s) for s in (10, 3600, 86_400, 7 * 86_400)] == ["lt_1h", "lt_1d", "lt_7d", "7d_plus"]
    assert buckets.has_action("Mình *mỉm cười* rồi đi.") and not buckets.has_action("Không có hành động.")
    assert buckets.clamp(1234.5, 0, 10_000, step=100) == 1200 and buckets.clamp(-5, 0, 10) == 0
    for fn, enum in (
        (buckets.length_bucket, events.LENGTH_BUCKET),
        (buckets.turn_bucket, events.TURN_BUCKET),
        (buckets.days_bucket, events.DAYS_BUCKET),
        (buckets.small_count_bucket, events.SMALL_COUNT_BUCKET),
    ):
        assert all(fn(n) in enum.values for n in range(0, 1000, 7))


def test_failure_reason_codes() -> None:
    assert failure_reason(llm_errors._BY_KIND["connect"]) == "connect"
    assert failure_reason(llm_errors._BY_KIND["timeout"]) == "timeout"
    assert failure_reason(llm_errors._MISSING_MODEL["reply"]) == "missing_model"
    assert failure_reason(llm_errors.EMPTY_REPLY) == "empty_reply"
    assert failure_reason(llm_errors.SAVE_FAILED) == "save_failed"
    assert failure_reason(WAIT_TIMEOUT_DETAIL) == "queue_timeout"
    assert failure_reason("bất kỳ câu nào khác") == "other" and failure_reason(None) == "other"


# ---------------------------------------------------------------------------- Tracker


def test_tracker_sessions_opt_out_and_gpc(repo: Repo) -> None:
    clk = Clock()
    tracker = Tracker(repo, version="9.9.9", now=clk)
    me = TrackContext(account_id=owner_id(repo), anon_id="a" * 22)
    assert tracker.emit(me, "persona_created")
    clk.advance(minutes=29)
    assert tracker.emit(me, "memory_forgotten", story_id=5)
    clk.advance(minutes=31)
    assert tracker.emit(me, "persona_created")
    got = rows(repo)
    assert [r["name"] for r in got] == [
        "session_started", "persona_created", "memory_forgotten", "session_started", "persona_created"
    ]
    assert got[0]["session_id"] == got[1]["session_id"] == got[2]["session_id"] != got[3]["session_id"]
    assert got[2]["story_id"] == 5 and got[2]["app_version"] == "9.9.9"
    assert {r["posthog_state"] for r in got} == {"local"}  # chưa có khoá PostHog: chỉ lưu ở máy

    # Sai bảng: không ghi, không raise.
    assert not tracker.emit(me, "story_started", {"mode": "story"})
    # Global Privacy Control: không ghi gì.
    assert not tracker.emit(TrackContext(account_id=None, anon_id="b" * 22, do_not_track=True), "app_opened",
                            source="client")
    # Tắt chia sẻ: xoá sự kiện đã lưu của tài khoản, không ghi thêm.
    with repo.transaction():
        assert store.set_opt_out(repo.conn, owner_id(repo), True) == 5
    assert not tracker.emit(me, "persona_created")
    assert rows(repo) == []
    with repo.transaction():
        store.set_opt_out(repo.conn, owner_id(repo), False)
    assert tracker.emit(me, "persona_created")


def test_props_json_is_bounded_by_schema(repo: Repo) -> None:
    with repo.transaction(), pytest.raises(sqlite3.IntegrityError):
        store.insert(
            repo.conn, ts=clock.iso(T0), name="x", account_id=None, anon_id="", session_id="", story_id=None,
            props_json="{" + '"a":"' + "x" * 2000 + '"}', source="server", app_version="", pending=False,
        )
    with repo.transaction(), pytest.raises(sqlite3.IntegrityError):
        store.insert(
            repo.conn, ts=clock.iso(T0), name="x", account_id=None, anon_id="", session_id="", story_id=None,
            props_json="không phải json", source="server", app_version="", pending=False,
        )


def test_purge_drops_events_older_than_180_days(repo: Repo) -> None:
    clk = Clock(T0 - timedelta(days=181))
    tracker = Tracker(repo, now=clk)
    ctx = TrackContext(account_id=None, anon_id="c" * 22)
    tracker.emit(ctx, "app_opened", source="client")
    clk.t = T0 - timedelta(days=179)
    tracker.emit(ctx, "app_opened", source="client")
    with repo.transaction():
        assert store.purge(repo.conn, T0) == 2  # session_started + app_opened cũ
    assert len(rows(repo)) == 2


async def test_hourly_cleanup_purges_analytics(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Dọn 180 ngày chạy cùng vòng dọn mỗi giờ của phần đăng nhập (và lúc khởi động)."""
    import asyncio

    from lyris.api import app as app_module

    conn = connect(tmp_path / "x.db")
    migrate(conn)
    repo = Repo(conn)
    old = clock.iso(clock.now() - timedelta(days=200))
    with repo.transaction():
        store.insert(
            repo.conn, ts=old, name="app_opened", account_id=None, anon_id="d" * 22, session_id="s",
            story_id=None, props_json="{}", source="client", app_version="", pending=False,
        )
    monkeypatch.setattr(app_module, "AUTH_CLEANUP_SECONDS", 0.01)
    task = asyncio.create_task(app_module._auth_cleanup_loop(repo))
    for _ in range(100):
        await asyncio.sleep(0.01)
        if not rows(repo):
            break
    task.cancel()
    assert rows(repo) == []
    with repo.transaction():
        store.insert(
            repo.conn, ts=old, name="app_opened", account_id=None, anon_id="d" * 22, session_id="s",
            story_id=None, props_json="{}", source="client", app_version="", pending=False,
        )
    app_module.prepare_auth(repo)  # lúc khởi động
    assert rows(repo) == []
    conn.close()


# ---------------------------------------------------------------------------- PostHog


class FakePostHog:
    """Transport giả: ghi lại từng lô; `statuses` là mã trả lần lượt (hết thì 200); `raise_next` giả lỗi mạng."""

    def __init__(self, statuses: list[int] | None = None) -> None:
        self.statuses = list(statuses or [])
        self.batches: list[dict[str, Any]] = []
        self.urls: list[str] = []
        self.raise_next = 0

    def handler(self, request: httpx.Request) -> httpx.Response:
        if self.raise_next:
            self.raise_next -= 1
            raise httpx.ConnectError("mạng hỏng", request=request)
        self.urls.append(str(request.url))
        self.batches.append(json.loads(request.content))
        status = self.statuses.pop(0) if self.statuses else 200
        return httpx.Response(status, json={"status": 1})

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handler)


def states(repo: Repo) -> list[tuple[str, int]]:
    return [(r["posthog_state"], r["posthog_attempts"]) for r in rows(repo)]


async def test_forwarder_batches_and_payload(repo: Repo) -> None:
    clk = Clock()
    fake = FakePostHog()
    fwd = PostHogForwarder(
        repo, api_key="phc_test_key", host="https://ph.example/", transport=fake.transport(), batch_size=3, now=clk
    )
    tracker = Tracker(repo, forward=True, version="1.2.3", now=clk)
    notified: list[int] = []
    tracker.on_pending = lambda: notified.append(1)
    owner = repo.owner_account()
    with repo.transaction():
        legal.accept(repo.conn, owner.id, clk())  # đã đồng ý chính sách: được gửi
    me = TrackContext(account_id=owner.id, anon_id="e" * 22)
    tracker.emit(me, "login_succeeded")
    tracker.emit(me, "story_started", {"mode": "dm", "source": "own", "language": "vi"}, story_id=7)
    tracker.emit(TrackContext(account_id=None, anon_id="f" * 22), "signup_viewed", {"has_invite_code": True},
                 source="client")
    assert notified and {s for s, _ in states(repo)} == {"pending"}
    assert await fwd.flush() == 5  # 2 session_started + 3 sự kiện, lô 3 + lô 2
    assert [len(b["batch"]) for b in fake.batches] == [4, 2]  # login_succeeded kèm một `$identify`
    assert fake.urls == ["https://ph.example/batch/"] * 2
    assert {s for s, _ in states(repo)} == {"sent"}
    items = [item for b in fake.batches for item in b["batch"]]
    assert all(b["api_key"] == "phc_test_key" for b in fake.batches)
    by_name = {i["event"]: i for i in items}
    login = by_name["login_succeeded"]
    assert login["distinct_id"] == owner.uid and login["timestamp"].endswith("Z")
    assert login["properties"]["$ip"] is None and login["properties"]["$geoip_disable"] is True
    assert login["properties"]["$process_person_profile"] is True and login["properties"]["app_version"] == "1.2.3"
    identify = by_name["$identify"]
    assert identify["distinct_id"] == owner.uid and identify["properties"]["$anon_distinct_id"] == "e" * 22
    story = by_name["story_started"]
    assert story["properties"]["story_id"] == 7 and story["properties"]["mode"] == "dm"
    anon = by_name["signup_viewed"]
    assert anon["distinct_id"] == "f" * 22 and anon["properties"]["$process_person_profile"] is False
    assert len({i["uuid"] for i in items}) == len(items)
    text = json.dumps(fake.batches, ensure_ascii=False)
    assert owner.handle not in text and owner.display_name not in text
    assert await fwd.flush() == 0 and len(fake.batches) == 2  # không gửi lại
    assert "phc_test_key" not in repr(fwd)
    await fwd.stop()


async def test_forwarder_retries_with_backoff_then_gives_up(repo: Repo) -> None:
    clk = Clock()
    fake = FakePostHog(statuses=[500, 429])
    fwd = PostHogForwarder(repo, api_key="k", transport=fake.transport(), now=clk)
    tracker = Tracker(repo, forward=True, now=clk)
    tracker.emit(TrackContext(account_id=None, anon_id="g" * 22), "app_opened", source="client")
    first_uuids = None
    assert await fwd.flush_once() == 0  # 500
    assert states(repo) == [("pending", 1), ("pending", 1)]
    first_uuids = [i["uuid"] for i in fake.batches[0]["batch"]]
    assert await fwd.flush_once() == 0 and len(fake.batches) == 1  # chưa tới hạn: không gọi
    clk.advance(seconds=backoff(1).total_seconds())
    assert await fwd.flush_once() == 0  # 429
    assert states(repo) == [("pending", 2), ("pending", 2)]
    clk.advance(seconds=backoff(2).total_seconds() - 1)
    assert await fwd.flush_once() == 0 and len(fake.batches) == 2
    clk.advance(seconds=1)
    fake.raise_next = 1
    assert await fwd.flush_once() == 0  # lỗi mạng: cũng hẹn lại
    assert states(repo) == [("pending", 3), ("pending", 3)]
    clk.advance(seconds=backoff(3).total_seconds())
    assert await fwd.flush_once() == 2
    assert states(repo) == [("sent", 4), ("sent", 4)]
    assert [i["uuid"] for i in fake.batches[-1]["batch"]] == first_uuids  # gửi lại không tạo bản trùng
    assert backoff(1) == timedelta(seconds=30) and backoff(2) == timedelta(minutes=1)
    assert backoff(30) == timedelta(hours=6)

    # Lỗi mãi: bỏ sau MAX_ATTEMPTS lần.
    fake.statuses = [503] * (MAX_ATTEMPTS + 2)
    tracker.emit(TrackContext(account_id=None, anon_id="g" * 22), "app_opened", source="client")
    for _ in range(MAX_ATTEMPTS):
        clk.advance(hours=7)
        await fwd.flush_once()
    assert states(repo)[-1] == ("failed", MAX_ATTEMPTS)
    # Dữ liệu bị từ chối (400): bỏ ngay.
    fake.statuses = [400]
    clk.advance(hours=7)
    tracker.emit(TrackContext(account_id=None, anon_id="h" * 22), "app_opened", source="client")
    assert await fwd.flush_once() == 0
    assert states(repo)[-2:] == [("failed", 1), ("failed", 1)]
    await fwd.stop()


async def test_forwarder_skips_opted_out_accounts(repo: Repo) -> None:
    clk = Clock()
    fake = FakePostHog()
    fwd = PostHogForwarder(repo, api_key="k", transport=fake.transport(), now=clk)
    tracker = Tracker(repo, forward=True, now=clk)
    owner = owner_id(repo)
    tracker.emit(TrackContext(account_id=owner, anon_id="i" * 22), "persona_created")
    # Cờ bật thẳng trong DB (không qua set_opt_out, nên sự kiện còn): vẫn không được gửi.
    with repo.transaction():
        repo.conn.execute("UPDATE accounts SET analytics_opt_out = 1 WHERE id = ?", (owner,))
    assert await fwd.flush() == 0 and fake.batches == []
    assert {s for s, _ in states(repo)} == {"local"}
    await fwd.stop()


async def test_forwarder_background_task_sends_on_notify(repo: Repo) -> None:
    import asyncio

    fake = FakePostHog()
    fwd = PostHogForwarder(repo, api_key="k", transport=fake.transport(), interval=60)
    tracker = Tracker(repo, forward=True)
    tracker.on_pending = fwd.notify
    await fwd.start()
    tracker.emit(TrackContext(account_id=None, anon_id="j" * 22), "app_opened", source="client")
    for _ in range(100):
        await asyncio.sleep(0.01)
        if fake.batches:
            break
    await fwd.stop()
    assert fake.batches and {s for s, _ in states(repo)} == {"sent"}


def test_to_posthog_never_has_identify_for_anonymous() -> None:
    row = store.OutboxRow(
        id=1, ts=clock.iso(T0), name="login_succeeded", distinct_id="anon", anon_id="anon", session_id="s",
        story_id=None, props_json="{}", source="server", app_version="1", identified=False, attempts=0,
    )
    assert [i["event"] for i in to_posthog(row)] == ["login_succeeded"]


def test_settings_read_posthog_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LYRIS_POSTHOG_KEY", raising=False)
    monkeypatch.delenv("NORA_POSTHOG_KEY", raising=False)
    monkeypatch.delenv("LYRIS_POSTHOG_HOST", raising=False)
    monkeypatch.delenv("NORA_POSTHOG_HOST", raising=False)
    cfg = get_settings()
    assert cfg.posthog_key is None and cfg.posthog_host == "https://us.i.posthog.com"
    monkeypatch.setenv("LYRIS_POSTHOG_KEY", "phc_secret_value")
    monkeypatch.setenv("LYRIS_POSTHOG_HOST", "https://eu.i.posthog.com/")
    cfg = get_settings()
    assert cfg.posthog_key == "phc_secret_value" and cfg.posthog_host == "https://eu.i.posthog.com"
    assert "phc_secret_value" not in repr(cfg)
    monkeypatch.setenv("LYRIS_POSTHOG_HOST", "eu.i.posthog.com")
    with pytest.raises(ValueError):
        get_settings()
    # http:// (không mã hoá) cũng bị từ chối, như docs/deploy.md nói.
    monkeypatch.setenv("LYRIS_POSTHOG_HOST", "http://eu.i.posthog.com")
    with pytest.raises(ValueError):
        get_settings()


# ---------------------------------------------------------------------------- tổng hợp


def _insert(repo: Repo, ts: datetime, name: str, *, account: int | None = None, anon: str = "", story: int | None = None) -> None:
    with repo.transaction():
        store.insert(
            repo.conn, ts=clock.iso(ts), name=name, account_id=account, anon_id=anon, session_id="s",
            story_id=story, props_json="{}", source="server", app_version="", pending=False,
        )


def _add_account(repo: Repo, handle: str) -> int:
    from lyris.auth import store as auth_store

    with repo.transaction():
        return auth_store.insert_member(repo.conn, uid=new_uid(), handle=handle, display_name=handle, invited_by=None)


def test_summary_counts_funnel_and_retention(repo: Repo) -> None:
    now = datetime(2026, 11, 20, 5, 0, tzinfo=timezone.utc)  # 12:00 giờ Việt Nam
    u1, u2, u3, u4 = owner_id(repo), _add_account(repo, "hai"), _add_account(repo, "ba"), _add_account(repo, "bon")
    day = timedelta(days=1)
    # u1: đủ phễu, 5 lượt trong một story; quay lại hôm sau (D1) và sau 7 ngày (D7).
    start = now - 10 * day
    for name in ("explore_viewed", "character_profile_viewed", "story_started"):
        _insert(repo, start, name, account=u1, story=1 if name == "story_started" else None)
    for _ in range(5):
        _insert(repo, start, "message_sent", account=u1, story=1)
    _insert(repo, start + day, "message_sent", account=u1, story=1)
    _insert(repo, start + 7 * day, "message_sent", account=u1, story=1)
    # u2: xem Khám phá, bắt đầu story (không xem hồ sơ), gửi 2 lượt ở hai story khác nhau; không quay lại.
    _insert(repo, start, "explore_viewed", account=u2)
    _insert(repo, start, "story_started", account=u2, story=2)
    _insert(repo, start, "message_sent", account=u2, story=2)
    _insert(repo, start, "message_sent", account=u2, story=3)
    # u3: chỉ hôm nay. Khách chưa đăng nhập: hôm nay.
    _insert(repo, now - timedelta(hours=1), "explore_viewed", account=u3)
    _insert(repo, now - timedelta(hours=1), "app_opened", anon="k" * 22)
    # u4: lần đầu cách đây 3 ngày, không quay lại.
    _insert(repo, now - 3 * day, "app_opened", account=u4)
    # Ngoài khoảng 30 ngày: không vào số đếm.
    _insert(repo, now - 40 * day, "persona_created", account=u2)

    data = store.summary(repo.conn, now, 30)
    counts = {c["name"]: c["count"] for c in data["counts"]}
    assert counts["message_sent"] == 9 and counts["explore_viewed"] == 3 and "persona_created" not in counts
    assert data["total_events"] == sum(counts.values())
    assert data["dau"] == 2 and data["wau"] == 4 and data["mau"] == 5  # u1 có mặt 3 ngày trước ngày 7
    assert len(data["daily"]) == 30 and data["daily"][-1] == {"date": "2026-11-20", "active": 2}
    funnel = {f["step"]: (f["users"], f["converted"]) for f in data["funnel"]}
    assert funnel == {
        "explore_viewed": (3, 3),
        "character_profile_viewed": (1, 1),
        "story_started": (2, 1),
        "message_sent": (2, 1),
        "messages_5": (1, 1),
    }
    # Đoàn hệ: người có ngày đầu trong 30 ngày qua và đã đủ 1 (7) ngày. u2 có ngày đầu cách đây 40 ngày; u3 và
    # khách mới có hôm nay; u4 mới 3 ngày (chưa vào đoàn hệ D7).
    assert data["retention"]["d1"] == {"cohort": 2, "retained": 1, "rate": 0.5}  # u1 quay lại, u4 không
    assert data["retention"]["d7"] == {"cohort": 1, "retained": 1, "rate": 1.0}


# ---------------------------------------------------------------------------- migration 0009 trên bản sao DB v8


def _build_v8(path: Path) -> None:
    conn = connect(path)
    try:
        assert migrate(conn, target=8) == 8
        repo = Repo(conn)
        owner = repo.owner_account()
        conn.execute(
            "INSERT INTO personas (name, gender, description, account_id, uid) VALUES ('Mai', 'female', '', ?, ?)",
            (owner.id, new_uid()),
        )
    finally:
        conn.close()


def test_migration_0009_on_copy_of_v8_db(tmp_path: Path) -> None:
    source = tmp_path / "v8.db"
    _build_v8(source)
    copy = tmp_path / "v8-copy.db"
    src = sqlite3.connect(source)
    dst = sqlite3.connect(copy)
    try:
        src.backup(dst)  # bản sao bằng backup API (như sao lưu DB thật), không đụng file gốc
    finally:
        dst.close()
        src.close()

    def counts(conn: sqlite3.Connection) -> dict[str, int]:
        names = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")]
        return {n: conn.execute(f'SELECT COUNT(*) FROM "{n}"').fetchone()[0] for n in names}

    conn = connect(copy)
    try:
        before = counts(conn)
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 8
        assert migrate(conn, target=9) == 9
        after = counts(conn)
        assert after.pop("analytics_events") == 0
        assert after == before
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert {r[0] for r in conn.execute("SELECT analytics_opt_out FROM accounts")} == {0}  # mặc định đang chia sẻ
        names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master")}
        assert {"idx_analytics_ts", "idx_analytics_name_ts", "idx_analytics_anon", "idx_analytics_account",
                "idx_analytics_outbox"} <= names
        assert migrate(conn, target=9) == 9  # chạy lại không làm gì
        # Xoá tài khoản: sự kiện thành ẩn danh, không mất.
        repo = Repo(conn)
        member = _add_account(repo, "khach")
        _insert(repo, T0, "persona_created", account=member)
        with repo.transaction():
            conn.execute("DELETE FROM accounts WHERE id = ?", (member,))
        assert [tuple(r) for r in conn.execute("SELECT name, account_id FROM analytics_events")] == [
            ("persona_created", None)
        ]
    finally:
        conn.close()
    raw = sqlite3.connect(source)
    try:
        assert raw.execute("PRAGMA user_version").fetchone()[0] == 8  # file gốc không đổi
    finally:
        raw.close()


def test_migration_file_is_additive() -> None:
    sql = (MIGRATIONS_DIR / "0009_analytics.sql").read_text(encoding="utf-8")
    code = "\n".join(line.split("--")[0] for line in sql.splitlines()).upper()
    assert not re.search(r"\b(DROP\s+(TABLE|INDEX|COLUMN)|DELETE\s+FROM|UPDATE\s+\w+\s+SET|ALTER\s+TABLE\s+\w+\s+(DROP|RENAME))\b", code)
    assert code.count("ALTER TABLE") == code.count("ALTER TABLE ACCOUNTS ADD COLUMN") == 1
