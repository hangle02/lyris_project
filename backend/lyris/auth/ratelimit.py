"""Giới hạn thử sai (docs/auth.md §3.4).

Mỗi luật: đếm lần sai của một khoá trong cửa sổ thời gian; đủ ngưỡng thì chặn tới `lần sai cuối + 15 phút`.
Khi bị chặn: không chạy scrypt, không ghi thêm dòng vào `auth_attempts` (caller kiểm tra TRƯỚC khi băm).
Không bị chặn: caller ghi luôn một dòng `ok = 0` trong CÙNG transaction với lần kiểm (giữ chỗ), rồi mới băm,
và chốt `ok = 1` khi đúng. Nhờ vậy N request song song không cùng lọt qua một bộ đếm còn trống.

| Khoá                         | Ngưỡng            | Lần đúng làm mới? |
| (handle, IP), login          | 5 / 15 phút       | có                |
| IP, login                    | 30 / 15 phút      | KHÔNG             |
| handle, login                | 50 / 1 giờ        | có                |
| (handle, thiết bị đã biết)   | 5 / 15 phút       | có                |
| IP, signup                   | 10 / 15 phút      | không             |
| IP, setup                    | 5 / 15 phút       | không             |
| tài khoản, change_password   | 5 / 15 phút       | có                |

Trình duyệt đã biết (cookie `lyris_device` từng đăng nhập đúng handle đó trong 30 ngày) chỉ chịu luật
(handle, thiết bị); kẻ tấn công không có cookie đó nên chịu đủ mọi ngưỡng.
"""
from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta

from lyris.auth import store
from lyris.auth.store import AttemptKind

BLOCK = timedelta(minutes=15)


@dataclass(frozen=True)
class Rule:
    threshold: int
    window: timedelta
    reset_on_ok: bool


LOGIN_PAIR = Rule(5, timedelta(minutes=15), reset_on_ok=True)
LOGIN_IP = Rule(30, timedelta(minutes=15), reset_on_ok=False)
LOGIN_HANDLE = Rule(50, timedelta(hours=1), reset_on_ok=True)
LOGIN_DEVICE = Rule(5, timedelta(minutes=15), reset_on_ok=True)
SIGNUP_IP = Rule(10, timedelta(minutes=15), reset_on_ok=False)
SETUP_IP = Rule(5, timedelta(minutes=15), reset_on_ok=False)
CHANGE_PASSWORD = Rule(5, timedelta(minutes=15), reset_on_ok=True)


def _retry_after(
    conn: sqlite3.Connection,
    rule: Rule,
    kind: AttemptKind,
    now: datetime,
    *,
    handle: str | None = None,
    ip: str | None = None,
    device: bytes | None = None,
) -> int | None:
    fails = store.failures(
        conn, kind, since=now - rule.window, reset_on_ok=rule.reset_on_ok, handle=handle, ip=ip, device=device
    )
    if len(fails) < rule.threshold:
        return None
    until = fails[0] + BLOCK
    if until <= now:
        return None
    return max(1, math.ceil((until - now).total_seconds()))


def _worst(*values: int | None) -> int | None:
    hits = [v for v in values if v is not None]
    return max(hits) if hits else None


def login_block(
    conn: sqlite3.Connection, now: datetime, *, handle: str | None, ip: str, device: bytes | None, known: bool
) -> int | None:
    """Số giây còn bị chặn khi đăng nhập, hoặc None. `handle` None: chữ gõ sai luật handle (chỉ khoá theo IP)."""
    if handle is not None and known and device is not None:
        return _retry_after(conn, LOGIN_DEVICE, "login", now, handle=handle, device=device)
    by_ip = _retry_after(conn, LOGIN_IP, "login", now, ip=ip)
    if handle is None:
        return by_ip
    return _worst(
        by_ip,
        _retry_after(conn, LOGIN_PAIR, "login", now, handle=handle, ip=ip),
        _retry_after(conn, LOGIN_HANDLE, "login", now, handle=handle),
    )


def signup_block(conn: sqlite3.Connection, now: datetime, *, ip: str) -> int | None:
    return _retry_after(conn, SIGNUP_IP, "signup", now, ip=ip)


def setup_block(conn: sqlite3.Connection, now: datetime, *, ip: str) -> int | None:
    return _retry_after(conn, SETUP_IP, "setup", now, ip=ip)


def change_password_block(conn: sqlite3.Connection, now: datetime, *, account_id: int) -> int | None:
    """Theo tài khoản (`store.account_key`), không theo @handle: đổi handle không làm mới bộ đếm."""
    return _retry_after(conn, CHANGE_PASSWORD, "change_password", now, handle=store.account_key(account_id))


__all__ = ["BLOCK", "Rule", "change_password_block", "login_block", "setup_block", "signup_block"]
