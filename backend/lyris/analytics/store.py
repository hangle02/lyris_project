"""SQL của event tracking (bảng `analytics_events`, cột `accounts.analytics_opt_out`; migration 0009).

Hàm nhận `sqlite3.Connection`; người gọi giữ khoá của Repo (`repo.transaction()` khi ghi, `repo.locked()` khi đọc).
"""
from __future__ import annotations

import json
import secrets
import sqlite3
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from lyris.auth import clock

RETENTION = timedelta(days=180)
SESSION_IDLE = timedelta(minutes=30)
# Ngày của số liệu theo giờ Việt Nam (thị trường chính): "hôm nay", DAU, D1/D7 tính theo UTC+7.
LOCAL_OFFSET = "+7 hours"
LOCAL_DELTA = timedelta(hours=7)

# Người dùng trong số liệu: tài khoản nếu có, không thì thiết bị (anon_id). Thiết bị đã từng đăng nhập (cùng anon_id
# xuất hiện với một tài khoản) được tính là tài khoản đó (`_actors`), để một người không thành hai.
_DISTINCT_ID = "COALESCE(a.uid, e.anon_id)"
_NOT_OPTED_OUT = "COALESCE(a.analytics_opt_out, 0) = 0"


# --------------------------------------------------------------------------- ghi


def insert(
    conn: sqlite3.Connection,
    *,
    ts: str,
    name: str,
    account_id: int | None,
    anon_id: str,
    session_id: str,
    story_id: int | None,
    props_json: str,
    source: str,
    app_version: str,
    pending: bool,
) -> int:
    cur = conn.execute(
        "INSERT INTO analytics_events (ts, name, account_id, anon_id, session_id, story_id, props_json, source,"
        " app_version, posthog_state, posthog_next_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            ts, name, account_id, anon_id, session_id, story_id, props_json, source, app_version,
            "pending" if pending else "local", ts if pending else None,
        ),
    )
    return int(cur.lastrowid or 0)


def last_session(conn: sqlite3.Connection, anon_id: str, account_id: int | None) -> tuple[str, str] | None:
    """(session_id, ts) của sự kiện gần nhất cùng thiết bị (không có anon_id thì cùng tài khoản)."""
    if anon_id:
        row = conn.execute(
            "SELECT session_id, ts FROM analytics_events WHERE anon_id = ? ORDER BY id DESC LIMIT 1", (anon_id,)
        ).fetchone()
    elif account_id is not None:
        row = conn.execute(
            "SELECT session_id, ts FROM analytics_events WHERE account_id = ? ORDER BY id DESC LIMIT 1",
            (account_id,),
        ).fetchone()
    else:
        return None
    return None if row is None else (str(row[0]), str(row[1]))


def opted_out(conn: sqlite3.Connection, account_id: int) -> bool:
    row = conn.execute("SELECT analytics_opt_out FROM accounts WHERE id = ?", (account_id,)).fetchone()
    return row is not None and bool(row[0])


def _anon_ids_of(conn: sqlite3.Connection, account_id: int, extra: str | None) -> list[str]:
    """Các thiết bị (anon_id) đã ghi sự kiện cùng tài khoản, kèm `extra` (thiết bị đang dùng)."""
    found = {
        str(r[0])
        for r in conn.execute(
            "SELECT DISTINCT anon_id FROM analytics_events WHERE account_id = ? AND anon_id != ''", (account_id,)
        )
    }
    if extra:
        found.add(extra)
    return sorted(found)


def set_opt_out(conn: sqlite3.Connection, account_id: int, value: bool, *, device_anon: str | None = None) -> int:
    """Đặt cờ; tắt chia sẻ thì xoá luôn mọi sự kiện đã lưu của tài khoản (chưa gửi thì không bao giờ gửi), kể cả
    sự kiện lúc chưa đăng nhập trên các thiết bị của tài khoản (cùng anon_id, chưa gắn tài khoản nào) và trên
    thiết bị đang dùng (`device_anon`). Trả số sự kiện đã xoá."""
    conn.execute("UPDATE accounts SET analytics_opt_out = ? WHERE id = ?", (1 if value else 0, account_id))
    if not value:
        return 0
    anons = _anon_ids_of(conn, account_id, device_anon)
    deleted = conn.execute("DELETE FROM analytics_events WHERE account_id = ?", (account_id,)).rowcount
    if anons:
        deleted += conn.execute(
            f"DELETE FROM analytics_events WHERE account_id IS NULL AND anon_id IN ({_marks(anons)})", anons
        ).rowcount
    return deleted


def forget_anon(conn: sqlite3.Connection, anon_id: str) -> int:
    """Xoá sự kiện lúc chưa đăng nhập (chưa gắn tài khoản nào) của một thiết bị. Trả số dòng đã xoá."""
    if not anon_id:
        return 0
    return conn.execute(
        "DELETE FROM analytics_events WHERE account_id IS NULL AND anon_id = ?", (anon_id,)
    ).rowcount


def anonymise_account(conn: sqlite3.Connection, account_id: int, *, device_anon: str | None = None) -> int:
    """Xoá tài khoản (docs/compliance.md §4): sự kiện còn lại tách khỏi tài khoản (`account_id` -> NULL) và khỏi mọi
    định danh từng gửi đi: anon_id đổi thành một bí danh mới, mỗi session_id thành một mã mới (PostHog đã nối
    anon_id cũ với tài khoản lúc đăng nhập). Gồm cả sự kiện lúc chưa đăng nhập trên các thiết bị của tài khoản
    (cùng anon_id, chưa gắn tài khoản nào) và thiết bị đang dùng (`device_anon`). Sự kiện chưa gửi PostHog thì giữ
    ở máy (không gửi nữa). Trả số sự kiện đã tách."""
    anons = _anon_ids_of(conn, account_id, device_anon)
    where = "account_id = ?"
    params: list[Any] = [account_id]
    if anons:
        where += f" OR (account_id IS NULL AND anon_id IN ({_marks(anons)}))"
        params += anons
    conn.execute(
        f"UPDATE analytics_events SET posthog_state = 'local', posthog_next_at = NULL"
        f" WHERE ({where}) AND posthog_state = 'pending'",
        params,
    )
    sessions = [str(r[0]) for r in conn.execute(f"SELECT DISTINCT session_id FROM analytics_events WHERE {where}", params)]
    alias = secrets.token_urlsafe(16)
    for old in sessions:
        conn.execute(
            f"UPDATE analytics_events SET session_id = ? WHERE ({where}) AND session_id = ?",
            [secrets.token_urlsafe(12) if old else "", *params, old],
        )
    return conn.execute(
        f"UPDATE analytics_events SET account_id = NULL, anon_id = ? WHERE {where}", [alias, *params]
    ).rowcount


def events_of(conn: sqlite3.Connection, account_id: int) -> list[dict[str, Any]]:
    """Sự kiện của tài khoản cho bản xuất dữ liệu cá nhân (tên, thời điểm, thuộc tính đã kiểm)."""
    rows = conn.execute(
        "SELECT ts, name, story_id, props_json, source FROM analytics_events WHERE account_id = ? ORDER BY id",
        (account_id,),
    ).fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        try:
            props = json.loads(r["props_json"])
        except (TypeError, ValueError):
            props = {}
        out.append({"ts": r["ts"], "name": r["name"], "story_id": r["story_id"], "props": props, "source": r["source"]})
    return out


def story_mode(conn: sqlite3.Connection, story_id: int, account_id: int) -> str | None:
    """Chế độ của story nếu story thuộc tài khoản; không thì None (client không gắn được story của người khác)."""
    row = conn.execute("SELECT mode FROM stories WHERE id = ? AND account_id = ?", (story_id, account_id)).fetchone()
    return None if row is None else str(row[0])


def purge(conn: sqlite3.Connection, now: datetime) -> int:
    """Xoá sự kiện cũ hơn 180 ngày. Trả số dòng đã xoá."""
    return conn.execute("DELETE FROM analytics_events WHERE ts < ?", (clock.iso(now - RETENTION),)).rowcount


# --------------------------------------------------------------------------- dữ liệu cho sự kiện của server


def last_activity(conn: sqlite3.Connection, story_id: int) -> str | None:
    row = conn.execute("SELECT MAX(created_at) FROM messages WHERE story_id = ?", (story_id,)).fetchone()
    return None if row is None or row[0] is None else str(row[0])


def user_turns(conn: sqlite3.Connection, story_id: int) -> int:
    row = conn.execute(
        "SELECT COUNT(*) FROM messages WHERE story_id = ? AND role = 'user' AND is_active = 1", (story_id,)
    ).fetchone()
    return int(row[0])


def new_lore_count(conn: sqlite3.Connection, story_id: int, message_id: int) -> int:
    """Số mục thế giới lượt `message_id` gợi ra lần đầu trong story (chưa lượt active nào khác gợi ra)."""
    row = conn.execute(
        "SELECT COUNT(*) FROM lore_hits h WHERE h.message_id = ? AND NOT EXISTS ("
        "  SELECT 1 FROM lore_hits o JOIN messages m ON m.id = o.message_id AND m.is_active = 1"
        "   WHERE o.story_id = ? AND o.entry_id = h.entry_id AND o.message_id != h.message_id)",
        (message_id, story_id),
    ).fetchone()
    return int(row[0])


# --------------------------------------------------------------------------- chuyển tiếp PostHog


@dataclass(frozen=True)
class OutboxRow:
    id: int
    ts: str
    name: str
    distinct_id: str
    anon_id: str
    session_id: str
    story_id: int | None
    props_json: str
    source: str
    app_version: str
    identified: bool  # có tài khoản (distinct_id là uid)
    attempts: int


def outbox(conn: sqlite3.Connection, now: datetime, limit: int) -> list[OutboxRow]:
    """Sự kiện chờ gửi đã tới hạn, cũ trước. Tài khoản đã tắt chia sẻ: chuyển về `local`, không gửi."""
    conn.execute(
        "UPDATE analytics_events SET posthog_state = 'local', posthog_next_at = NULL"
        " WHERE posthog_state = 'pending' AND account_id IN (SELECT id FROM accounts WHERE analytics_opt_out = 1)"
    )
    rows = conn.execute(
        f"SELECT e.id, e.ts, e.name, {_DISTINCT_ID} AS distinct_id, e.anon_id, e.session_id, e.story_id,"
        "        e.props_json, e.source, e.app_version, a.uid IS NOT NULL AS identified, e.posthog_attempts"
        "   FROM analytics_events e LEFT JOIN accounts a ON a.id = e.account_id"
        "  WHERE e.posthog_state = 'pending' AND e.posthog_next_at <= ?"
        "  ORDER BY e.posthog_next_at, e.id LIMIT ?",
        (clock.iso(now), limit),
    ).fetchall()
    return [
        OutboxRow(
            id=int(r["id"]), ts=str(r["ts"]), name=str(r["name"]), distinct_id=str(r["distinct_id"] or ""),
            anon_id=str(r["anon_id"]), session_id=str(r["session_id"]),
            story_id=None if r["story_id"] is None else int(r["story_id"]), props_json=str(r["props_json"]),
            source=str(r["source"]), app_version=str(r["app_version"]), identified=bool(r["identified"]),
            attempts=int(r["posthog_attempts"]),
        )
        for r in rows
    ]


def _marks(ids: list[int]) -> str:
    return ", ".join("?" for _ in ids)


def mark_sent(conn: sqlite3.Connection, ids: list[int]) -> None:
    if ids:
        conn.execute(
            f"UPDATE analytics_events SET posthog_state = 'sent', posthog_next_at = NULL,"
            f" posthog_attempts = posthog_attempts + 1 WHERE id IN ({_marks(ids)}) AND posthog_state = 'pending'",
            ids,
        )


def mark_failed(conn: sqlite3.Connection, ids: list[int]) -> None:
    if ids:
        conn.execute(
            f"UPDATE analytics_events SET posthog_state = 'failed', posthog_next_at = NULL,"
            f" posthog_attempts = posthog_attempts + 1 WHERE id IN ({_marks(ids)}) AND posthog_state = 'pending'",
            ids,
        )


def mark_retry(conn: sqlite3.Connection, ids: list[int], next_at: datetime, *, max_attempts: int) -> None:
    """Thêm một lần thử; đủ `max_attempts` thì bỏ (`failed`), không thì hẹn lại lúc `next_at`."""
    if not ids:
        return
    marks = _marks(ids)
    conn.execute(
        f"UPDATE analytics_events SET posthog_attempts = posthog_attempts + 1, posthog_next_at = ?"
        f" WHERE id IN ({marks}) AND posthog_state = 'pending'",
        [clock.iso(next_at), *ids],
    )
    conn.execute(
        f"UPDATE analytics_events SET posthog_state = 'failed', posthog_next_at = NULL"
        f" WHERE id IN ({marks}) AND posthog_state = 'pending' AND posthog_attempts >= ?",
        [*ids, max_attempts],
    )


# --------------------------------------------------------------------------- xuất cho Apero

EXPORT_COLUMNS: tuple[str, ...] = (
    "event_id", "ts", "name", "distinct_id", "anon_id", "session_id", "story_id", "source", "app_version", "props",
)


def export_rows(
    conn: sqlite3.Connection, *, since: str | None, until: str | None, after_id: int, limit: int
) -> list[dict[str, Any]]:
    """Một trang sự kiện (id > after_id), không gồm tài khoản đã tắt chia sẻ."""
    where = ["e.id > ?", _NOT_OPTED_OUT]
    params: list[Any] = [after_id]
    if since is not None:
        where.append("e.ts >= ?")
        params.append(since)
    if until is not None:
        where.append("e.ts < ?")
        params.append(until)
    rows = conn.execute(
        f"SELECT e.id, e.ts, e.name, {_DISTINCT_ID} AS distinct_id, e.anon_id, e.session_id, e.story_id, e.source,"
        "        e.app_version, e.props_json"
        "   FROM analytics_events e LEFT JOIN accounts a ON a.id = e.account_id"
        f" WHERE {' AND '.join(where)} ORDER BY e.id LIMIT ?",
        [*params, limit],
    ).fetchall()
    return [
        {
            "event_id": int(r["id"]), "ts": str(r["ts"]), "name": str(r["name"]),
            "distinct_id": str(r["distinct_id"] or ""), "anon_id": str(r["anon_id"]),
            "session_id": str(r["session_id"]), "story_id": r["story_id"], "source": str(r["source"]),
            "app_version": str(r["app_version"]), "props": str(r["props_json"]),
        }
        for r in rows
    ]


def iter_export(
    conn_factory: Any, *, since: str | None, until: str | None, page: int = 500
) -> Iterator[dict[str, Any]]:
    """Mọi dòng xuất, theo trang (`conn_factory()` là context manager giữ khoá và trả kết nối)."""
    after = 0
    while True:
        with conn_factory() as conn:
            rows = export_rows(conn, since=since, until=until, after_id=after, limit=page)
        if not rows:
            return
        yield from rows
        after = int(rows[-1]["event_id"])


# --------------------------------------------------------------------------- tổng hợp cho chủ máy

FUNNEL: tuple[tuple[str, str], ...] = (
    ("explore_viewed", "Xem Khám phá"),
    ("character_profile_viewed", "Xem hồ sơ nhân vật"),
    ("story_started", "Bắt đầu story"),
    ("message_sent", "Gửi lượt đầu"),
    ("messages_5", "Gửi từ 5 lượt trong một story"),
)


class _Actors:
    """Ai là "một người" trong số liệu: tài khoản nếu có; thiết bị chưa đăng nhập thì là tài khoản đầu tiên từng
    dùng cùng anon_id đó (người mở trang tạo tài khoản rồi tạo tài khoản là MỘT người), không có thì là thiết bị."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.alias: dict[str, str] = {
            str(r[0]): f"u{int(r[1])}"
            for r in conn.execute(
                "SELECT anon_id, MIN(account_id) FROM analytics_events"
                " WHERE account_id IS NOT NULL AND anon_id != '' GROUP BY anon_id"
            )
        }

    def of(self, account_id: int | None, anon_id: str) -> str:
        if account_id is not None:
            return f"u{int(account_id)}"
        return self.alias.get(anon_id, f"a{anon_id}")


def summary(conn: sqlite3.Connection, now: datetime, days: int) -> dict[str, Any]:
    since = clock.iso(now - timedelta(days=days))
    base = f"FROM analytics_events e LEFT JOIN accounts a ON a.id = e.account_id WHERE {_NOT_OPTED_OUT}"
    actors = _Actors(conn)
    counts = [
        {"name": str(r[0]), "count": int(r[1])}
        for r in conn.execute(
            f"SELECT e.name, COUNT(*) {base} AND e.ts >= ? GROUP BY e.name ORDER BY COUNT(*) DESC, e.name", (since,)
        )
    ]
    total = sum(c["count"] for c in counts)

    # (người, ngày địa phương) trên toàn bộ dữ liệu còn giữ: DAU/WAU/MAU, chuỗi theo ngày, D1/D7.
    active: dict[str, set[str]] = {}
    first_day: dict[str, str] = {}
    for account_id, anon, day in conn.execute(
        f"SELECT DISTINCT e.account_id, e.anon_id, date(e.ts, '{LOCAL_OFFSET}') {base} AND e.name != 'session_started'"
        " AND NOT (e.account_id IS NULL AND e.anon_id = '')"  # dòng không gắn ai (tắt chia sẻ, báo cáo...)
    ):
        actor = actors.of(account_id, str(anon))
        active.setdefault(str(day), set()).add(actor)
        if actor not in first_day or str(day) < first_day[actor]:
            first_day[actor] = str(day)

    today = now + LOCAL_DELTA

    def users_in(n_days: int) -> int:
        seen: set[str] = set()
        for i in range(n_days):
            seen |= active.get((today - timedelta(days=i)).strftime("%Y-%m-%d"), set())
        return len(seen)

    daily = [
        {"date": (today - timedelta(days=i)).strftime("%Y-%m-%d"),
         "active": len(active.get((today - timedelta(days=i)).strftime("%Y-%m-%d"), set()))}
        for i in reversed(range(days))
    ]

    def retention(offset: int) -> dict[str, Any]:
        cohort = retained = 0
        window_start = (today - timedelta(days=days)).strftime("%Y-%m-%d")
        last_cohort_day = (today - timedelta(days=offset)).strftime("%Y-%m-%d")
        for actor, d0 in first_day.items():
            if not window_start <= d0 <= last_cohort_day:
                continue
            cohort += 1
            target = (datetime.strptime(d0, "%Y-%m-%d") + timedelta(days=offset)).strftime("%Y-%m-%d")
            if actor in active.get(target, set()):
                retained += 1
        return {"cohort": cohort, "retained": retained, "rate": round(retained / cohort, 4) if cohort else None}

    # Phễu: người làm bước đó trong khoảng ngày, và người làm bước đó cùng mọi bước trước.
    did: dict[str, set[str]] = {}
    for step, _label in FUNNEL[:-1]:
        did[step] = {
            actors.of(r[0], str(r[1]))
            for r in conn.execute(
                f"SELECT DISTINCT e.account_id, e.anon_id {base} AND e.ts >= ? AND e.name = ?"
                " AND NOT (e.account_id IS NULL AND e.anon_id = '')",
                (since, step),
            )
        }
    did["messages_5"] = {
        actors.of(r[0], str(r[1]))
        for r in conn.execute(
            f"SELECT MAX(e.account_id), MIN(e.anon_id) {base} AND e.ts >= ? AND e.name = 'message_sent'"
            " AND e.story_id IS NOT NULL"
            " GROUP BY COALESCE('u' || e.account_id, 'a' || e.anon_id), e.story_id HAVING COUNT(*) >= 5",
            (since,),
        )
    }
    funnel: list[dict[str, Any]] = []
    carried: set[str] | None = None
    for step, label in FUNNEL:
        carried = set(did[step]) if carried is None else carried & did[step]
        funnel.append({"step": step, "label": label, "users": len(did[step]), "converted": len(carried)})

    return {
        "since": since,
        "until": clock.iso(now),
        "days": days,
        "total_events": total,
        "counts": counts,
        "dau": users_in(1),
        "wau": users_in(7),
        "mau": users_in(30),
        "daily": daily,
        "funnel": funnel,
        "retention": {"d1": retention(1), "d7": retention(7)},
    }


__all__ = [
    "EXPORT_COLUMNS",
    "FUNNEL",
    "RETENTION",
    "SESSION_IDLE",
    "OutboxRow",
    "anonymise_account",
    "events_of",
    "export_rows",
    "forget_anon",
    "insert",
    "iter_export",
    "last_activity",
    "last_session",
    "mark_failed",
    "mark_retry",
    "mark_sent",
    "new_lore_count",
    "opted_out",
    "outbox",
    "purge",
    "set_opt_out",
    "story_mode",
    "summary",
    "user_turns",
]
