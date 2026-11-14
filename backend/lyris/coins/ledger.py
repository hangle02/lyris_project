"""Sổ coin (docs/coins.md §2.1): mọi thay đổi số dư đi qua `post()`, không chỗ nào khác đổi `coin_wallets.balance`.

`post(conn, account_id, delta, kind, idem_key, **refs)` chạy trong `BEGIN IMMEDIATE` (gọi bên trong một transaction
đang mở, ví dụ `Repo.transaction()`, thì thành SAVEPOINT):
- `idem_key` đã có và cùng nội dung (`account_id`, `delta`, `kind`) → trả dòng cũ (`created=False`), không cộng lần hai;
- đã có mà khác nội dung → `IdemConflict`;
- chưa có → tạo ví 0 nếu thiếu, `UPDATE … SET balance = balance + delta WHERE balance + delta >= 0` (không đổi dòng nào
  → `InsufficientCoins`), rồi `INSERT` dòng sổ với `balance_after`.

Ví luôn có: thành viên nào chưa có ví thì hàm đọc/ghi tự tạo ví 0, không bao giờ lỗi (§1).
"""
from __future__ import annotations

import itertools
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from lyris.auth import clock as auth_clock
from lyris.coins.clock import coin_day
from lyris.coins.errors import SIGNUP_GRANT, IdemConflict, InsufficientCoins

KINDS = frozenset(
    {"signup_grant", "backfill_grant", "daily_login", "chat", "mission", "creator_milestone", "topup_code", "admin_adjust"}
)
_savepoints = itertools.count(1)


@dataclass(frozen=True)
class Entry:
    """Một dòng sổ. `created`: dòng vừa được ghi bởi lần gọi này (False: dòng cũ cùng `idem_key`)."""

    id: int
    account_id: int
    delta: int
    balance_after: int
    kind: str
    idem_key: str
    coin_day: str
    created: bool


@contextmanager
def atomic(conn: sqlite3.Connection) -> Iterator[None]:
    """`BEGIN IMMEDIATE` … `COMMIT`; đang trong transaction thì SAVEPOINT (lỗi chỉ cuộn lại phần này)."""
    if conn.in_transaction:
        name = f"lyris_coin_{next(_savepoints)}"
        conn.execute(f"SAVEPOINT {name}")
        try:
            yield
        except BaseException:
            conn.execute(f"ROLLBACK TO {name}")
            conn.execute(f"RELEASE {name}")
            raise
        conn.execute(f"RELEASE {name}")
        return
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


def _now(now: datetime | None) -> datetime:
    return now if now is not None else auth_clock.now()


def ensure_wallet(conn: sqlite3.Connection, account_id: int, now: datetime | None = None) -> None:
    """Ví 0 cho tài khoản chưa có ví (không đổi ví đã có)."""
    conn.execute(
        "INSERT OR IGNORE INTO coin_wallets (account_id, balance, updated_at) VALUES (?, 0, ?)",
        (account_id, auth_clock.iso(_now(now))),
    )


def balance(conn: sqlite3.Connection, account_id: int) -> int:
    row = conn.execute("SELECT balance FROM coin_wallets WHERE account_id = ?", (account_id,)).fetchone()
    return 0 if row is None else int(row[0])


def held(conn: sqlite3.Connection, account_id: int) -> int:
    """Tổng coin đang giữ chỗ (giữ chỗ `held`)."""
    row = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM coin_holds WHERE account_id = ? AND status = 'held'", (account_id,)
    ).fetchone()
    return int(row[0])


def has_wallet(conn: sqlite3.Connection, account_id: int) -> bool:
    return conn.execute("SELECT 1 FROM coin_wallets WHERE account_id = ?", (account_id,)).fetchone() is not None


def _entry(row: sqlite3.Row | tuple[Any, ...], created: bool) -> Entry:
    return Entry(
        id=int(row[0]),
        account_id=int(row[1]),
        delta=int(row[2]),
        balance_after=int(row[3]),
        kind=str(row[4]),
        idem_key=str(row[5]),
        coin_day=str(row[6]),
        created=created,
    )


_ENTRY_COLS = "id, account_id, delta, balance_after, kind, idem_key, coin_day"


def post(
    conn: sqlite3.Connection,
    account_id: int,
    delta: int,
    kind: str,
    idem_key: str,
    *,
    story_id: int | None = None,
    card_id: int | None = None,
    hold_id: int | None = None,
    code_id: int | None = None,
    mission: str | None = None,
    milestone: int | None = None,
    actor_id: int | None = None,
    reason: str | None = None,
    now: datetime | None = None,
) -> Entry:
    """Ghi một dòng sổ và đổi số dư (một transaction). Xem docstring của module."""
    if kind not in KINDS:
        raise ValueError(f"kind coin không hợp lệ: {kind}")
    if isinstance(delta, bool) or not isinstance(delta, int) or delta == 0:
        raise ValueError("delta phải là số nguyên khác 0")
    if not idem_key:
        raise ValueError("thiếu idem_key")
    moment = _now(now)
    with atomic(conn):
        old = conn.execute(f"SELECT {_ENTRY_COLS} FROM coin_ledger WHERE idem_key = ?", (idem_key,)).fetchone()
        if old is not None:
            if int(old[1]) == account_id and int(old[2]) == delta and str(old[4]) == kind:
                return _entry(old, created=False)
            raise IdemConflict(idem_key)
        ensure_wallet(conn, account_id, moment)
        changed = conn.execute(
            "UPDATE coin_wallets SET balance = balance + ?, updated_at = ? WHERE account_id = ? AND balance + ? >= 0",
            (delta, auth_clock.iso(moment), account_id, delta),
        ).rowcount
        if changed == 0:
            raise InsufficientCoins(f"tài khoản {account_id} không đủ {-delta} coin")
        after = balance(conn, account_id)
        cur = conn.execute(
            "INSERT INTO coin_ledger (account_id, delta, balance_after, kind, idem_key, coin_day, story_id, card_id,"
            " hold_id, code_id, mission, milestone, actor_id, reason, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                account_id, delta, after, kind, idem_key, coin_day(moment), story_id, card_id, hold_id, code_id,
                mission, milestone, actor_id, reason, auth_clock.iso(moment),
            ),
        )
        assert cur.lastrowid is not None
        return Entry(
            id=int(cur.lastrowid), account_id=account_id, delta=delta, balance_after=after, kind=kind,
            idem_key=idem_key, coin_day=coin_day(moment), created=True,
        )


def open_wallet(conn: sqlite3.Connection, account_id: int, now: datetime | None = None) -> Entry:
    """Ví mới cho thành viên vừa tạo và quà tạo tài khoản +300 (`signup:<id>`), cùng transaction (§3.4).
    Ghi cả khi `LYRIS_COINS=0` (tắt coin chỉ là không trừ, không hiện)."""
    with atomic(conn):
        ensure_wallet(conn, account_id, now)
        return post(conn, account_id, SIGNUP_GRANT, "signup_grant", f"signup:{account_id}", now=now)


__all__ = [
    "KINDS",
    "Entry",
    "atomic",
    "balance",
    "ensure_wallet",
    "has_wallet",
    "held",
    "open_wallet",
    "post",
]
