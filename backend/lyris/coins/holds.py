"""Giữ chỗ coin cho một lượt sinh (docs/coins.md §3.2, quyết định giu-cho-coin-truoc-khi-sinh).

- `open_hold`: trong một `BEGIN IMMEDIATE`, kiểm số dùng được (số dư − giữ chỗ đang mở) ≥ giá rồi `INSERT` giữ chỗ
  `held`. Không đủ → `CoinsRequired`. Chỉ mục `idx_coin_holds_one_open` bảo đảm mỗi tài khoản một giữ chỗ (đã có →
  `HoldBusy`).
- `charge_hold`: `held` → `charged` rồi ghi dòng sổ `chat:<hold_id>` (−giá), cùng transaction với việc lưu câu trả
  lời. Theo bất biến "số dư − giữ chỗ ≥ 0", một giữ chỗ `held` luôn đủ coin. Giữ chỗ không còn `held` → None
  (không trừ; câu trả lời vẫn được lưu).
- `release_hold`: `held` → `released` với lý do; không ghi sổ, số dư không đổi.
- `release_open_holds`: nhả mọi giữ chỗ còn `held` (lý do `restart`). CHỈ gọi trong `lifespan` của app.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime

from lyris.auth import clock as auth_clock
from lyris.coins.clock import coin_day
from lyris.coins.errors import CoinsRequired, HoldBusy
from lyris.coins.ledger import Entry, atomic, balance, ensure_wallet, held, post

RELEASE_REASONS = frozenset({"error", "empty", "cancelled", "queue_timeout", "save_failed", "invalid", "restart"})


def _now(now: datetime | None) -> datetime:
    return now if now is not None else auth_clock.now()


def open_hold(
    conn: sqlite3.Connection,
    account_id: int,
    *,
    story_id: int | None,
    char_key: int | None,
    origin_card_id: int | None,
    mode: str,
    kind: str,
    amount: int,
    now: datetime | None = None,
) -> int:
    """Tạo giữ chỗ `held`; trả id. `CoinsRequired` nếu số dùng được < `amount`; `HoldBusy` nếu đã có giữ chỗ mở."""
    moment = _now(now)
    with atomic(conn):
        ensure_wallet(conn, account_id, moment)
        bal = balance(conn, account_id)
        available = bal - held(conn, account_id)
        if available < amount:
            raise CoinsRequired(bal, max(0, available), amount)
        try:
            cur = conn.execute(
                "INSERT INTO coin_holds (account_id, story_id, char_key, origin_card_id, mode, kind, amount, status,"
                " coin_day, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'held', ?, ?)",
                (account_id, story_id, char_key, origin_card_id, mode, kind, amount, coin_day(moment), auth_clock.iso(moment)),
            )
        except sqlite3.IntegrityError as exc:
            raise HoldBusy(str(exc)) from exc
        assert cur.lastrowid is not None
        return int(cur.lastrowid)


def charge_hold(
    conn: sqlite3.Connection,
    hold_id: int,
    *,
    message_id: int | None,
    story_id: int | None,
    card_id: int | None,
    now: datetime | None = None,
) -> Entry | None:
    """`held` → `charged` và ghi dòng sổ `chat:<hold_id>`. Giữ chỗ không còn `held` → None (không trừ)."""
    moment = _now(now)
    with atomic(conn):
        row = conn.execute(
            "SELECT account_id, amount FROM coin_holds WHERE id = ? AND status = 'held'", (hold_id,)
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            "UPDATE coin_holds SET status = 'charged', message_id = ?, settled_at = ? WHERE id = ? AND status = 'held'",
            (message_id, auth_clock.iso(moment), hold_id),
        )
        return post(
            conn, int(row[0]), -int(row[1]), "chat", f"chat:{hold_id}",
            story_id=story_id, card_id=card_id, hold_id=hold_id, now=moment,
        )


def release_hold(conn: sqlite3.Connection, hold_id: int, reason: str, now: datetime | None = None) -> bool:
    """`held` → `released` (không ghi sổ). True nếu vừa nhả."""
    if reason not in RELEASE_REASONS:
        raise ValueError(f"lý do nhả không hợp lệ: {reason}")
    with atomic(conn):
        changed = conn.execute(
            "UPDATE coin_holds SET status = 'released', release_reason = ?, settled_at = ? WHERE id = ? AND status = 'held'",
            (reason, auth_clock.iso(_now(now)), hold_id),
        ).rowcount
    return changed > 0


def release_open_holds(conn: sqlite3.Connection, reason: str = "restart", now: datetime | None = None) -> list[tuple[int, str]]:
    """Nhả mọi giữ chỗ còn `held`; trả [(account_id, kind)] đã nhả. Chỉ dùng lúc app khởi động (lifespan)."""
    if reason not in RELEASE_REASONS:
        raise ValueError(f"lý do nhả không hợp lệ: {reason}")
    with atomic(conn):
        rows = conn.execute("SELECT id, account_id, kind FROM coin_holds WHERE status = 'held' ORDER BY id").fetchall()
        stamp = auth_clock.iso(_now(now))
        for row in rows:
            conn.execute(
                "UPDATE coin_holds SET status = 'released', release_reason = ?, settled_at = ? WHERE id = ? AND status = 'held'",
                (reason, stamp, int(row[0])),
            )
    return [(int(r[1]), str(r[2])) for r in rows]


__all__ = ["RELEASE_REASONS", "charge_hold", "open_hold", "release_hold", "release_open_holds"]
