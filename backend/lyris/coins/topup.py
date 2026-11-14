"""Mã nạp và nhật ký coin của chủ máy (F43, docs/coins.md §4.3, §4.5).

Mã nạp như mã mời (`lyris.auth.codes`): 12 ký tự Crockford base32 (~60 bit), DB chỉ có `sha256` của mã đã chuẩn hoá và
4 ký tự cuối; mã đầy đủ chỉ trả về một lần lúc tạo. Dùng một lần, ai nhập trước được (tạm chọn). Tối đa 50 mã còn
hiệu lực (tạm chọn).

Nhập mã (`redeem`) chạy trọn trong MỘT transaction của người gọi (`Repo.transaction()`, `BEGIN IMMEDIATE`): đếm lần sai
trong 60 phút → xoá lần thử > 30 ngày của tài khoản → tìm mã → `UPDATE … WHERE used_at IS NULL AND revoked_at IS NULL
AND expires_at > now` (hai người cùng nhập: chỉ một dòng đổi) → `post(+amount, 'topup:<id>')` → ghi lần thử. Hàm trả
kết quả thay vì raise để lần thử sai vẫn được ghi (raise trong transaction thì cuộn lại cả lần thử).
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from lyris.auth import clock as auth_clock
from lyris.auth import codes
from lyris.coins import hot, ledger
from lyris.coins.errors import CoinError
from lyris.coins.packs import pack as find_pack

MAX_ACTIVE_CODES = 50
CODE_DAYS = (1, 7, 30)
AMOUNT_MIN = 1
AMOUNT_MAX = 10_000
NOTE_MAX = 60
FAIL_LIMIT = 10
FAIL_WINDOW = timedelta(minutes=60)
ATTEMPT_KEEP = timedelta(days=30)
LOG_LIMIT = 50
LOG_DAYS = 30
LOG_KINDS = ("topup_code", "admin_adjust", "creator_milestone")
GRANT_KINDS = ("signup_grant", "backfill_grant", "daily_login", "mission", "creator_milestone")

# §4.3, §10.5: một câu cho mọi lý do sai (không lộ mã nào có thật).
INVALID_DETAIL = "Mã nạp không đúng hoặc đã hết hạn."
OWNER_DETAIL = "Tài khoản quản lý không cần nạp coin."
LIMIT_DETAIL = "Đã có 50 mã nạp còn hiệu lực. Huỷ bớt mã cũ rồi tạo mã mới."
RATE_DETAIL = "Bạn đã thử sai nhiều lần. Hãy đợi một lúc rồi thử lại."
USED_DETAIL = "Mã nạp này đã được dùng, không huỷ được."
NOT_FOUND_DETAIL = "Không tìm thấy mã nạp."


class TopupRejected(CoinError):
    """Lỗi mã nạp trả thẳng cho giao diện: `{detail, code}` với HTTP `status`."""

    def __init__(self, status: int, code: str, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.code = code
        self.detail = detail

    def payload(self) -> dict[str, Any]:
        return {"detail": self.detail, "code": self.code}


def invalid() -> TopupRejected:
    return TopupRejected(422, "topup_code_invalid", INVALID_DETAIL)


def owner_rejected() -> TopupRejected:
    return TopupRejected(422, "topup_code_owner", OWNER_DETAIL)


def rate_limited() -> TopupRejected:
    return TopupRejected(429, "rate_limited", RATE_DETAIL)


_SELECT = (
    "SELECT c.id, c.code_hint, c.amount, c.pack_id, c.note, c.created_at, c.expires_at, c.used_at, c.revoked_at,"
    " u.handle AS used_by_handle FROM coin_topup_codes c LEFT JOIN accounts u ON u.id = c.used_by"
)


def code_status(row: sqlite3.Row, now: datetime) -> str:
    if row["used_at"] is not None:
        return "used"
    if row["revoked_at"] is not None:
        return "revoked"
    if str(row["expires_at"]) <= auth_clock.iso(now):
        return "expired"
    return "active"


def code_item(row: sqlite3.Row, now: datetime) -> dict[str, Any]:
    """Một mã như chủ máy thấy: không bao giờ có mã đầy đủ (chỉ 4 ký tự cuối)."""
    return {
        "id": int(row["id"]),
        "hint": str(row["code_hint"]),
        "amount": int(row["amount"]),
        "pack_id": row["pack_id"],
        "note": str(row["note"]),
        "created_at": str(row["created_at"]),
        "expires_at": str(row["expires_at"]),
        "status": code_status(row, now),
        "used_by_handle": row["used_by_handle"],
    }


def list_codes(conn: sqlite3.Connection, now: datetime) -> list[dict[str, Any]]:
    rows = conn.execute(f"{_SELECT} ORDER BY c.created_at DESC, c.id DESC").fetchall()
    return [code_item(r, now) for r in rows]


def get_code(conn: sqlite3.Connection, code_id: int, now: datetime) -> dict[str, Any] | None:
    row = conn.execute(f"{_SELECT} WHERE c.id = ?", (code_id,)).fetchone()
    return None if row is None else code_item(row, now)


def active_count(conn: sqlite3.Connection, now: datetime) -> int:
    row = conn.execute(
        "SELECT COUNT(*) FROM coin_topup_codes WHERE used_at IS NULL AND revoked_at IS NULL AND expires_at > ?",
        (auth_clock.iso(now),),
    ).fetchone()
    return int(row[0])


def create_code(
    conn: sqlite3.Connection, *, actor_id: int, amount: int, pack_id: str | None, note: str, days: int, now: datetime
) -> tuple[dict[str, Any], str]:
    """Mã mới (gọi trong transaction). Trả (mã như chủ máy thấy, mã đầy đủ dạng `XXXX-XXXX-XXXX` — chỉ lần này)."""
    if pack_id is not None:
        found = find_pack(pack_id)
        if found is None or found.coins != amount:
            raise ValueError("gói không hợp lệ")
    if not AMOUNT_MIN <= amount <= AMOUNT_MAX or days not in CODE_DAYS or len(note) > NOTE_MAX:
        raise ValueError("mã nạp không hợp lệ")
    if active_count(conn, now) >= MAX_ACTIVE_CODES:
        raise TopupRejected(422, "topup_code_limit", LIMIT_DETAIL)
    code = codes.random_code()
    cur = conn.execute(
        "INSERT INTO coin_topup_codes (code_hash, code_hint, amount, pack_id, note, created_by, created_at, expires_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            codes.code_hash(code), codes.code_hint(code), amount, pack_id, note, actor_id, auth_clock.iso(now),
            auth_clock.iso(now + timedelta(days=days)),
        ),
    )
    assert cur.lastrowid is not None
    item = get_code(conn, int(cur.lastrowid), now)
    assert item is not None
    return item, codes.group(code)


def revoke_code(conn: sqlite3.Connection, code_id: int, now: datetime) -> dict[str, Any]:
    """Huỷ mã chưa dùng (gọi lại với mã đã huỷ/hết hạn: không đổi gì). Mã đã dùng: 409."""
    from lyris.db.repo import NotFound

    item = get_code(conn, code_id, now)
    if item is None:
        raise NotFound(NOT_FOUND_DETAIL)
    if item["status"] == "used":
        raise TopupRejected(409, "topup_code_used", USED_DETAIL)
    conn.execute(
        "UPDATE coin_topup_codes SET revoked_at = ? WHERE id = ? AND used_at IS NULL AND revoked_at IS NULL",
        (auth_clock.iso(now), code_id),
    )
    out = get_code(conn, code_id, now)
    assert out is not None
    return out


@dataclass(frozen=True)
class RedeemOutcome:
    """`reason`: 'ok', hoặc lý do sai cho số liệu ('invalid', 'used', 'expired', 'revoked', 'rate_limited')."""

    reason: str
    amount: int = 0
    pack: str = "custom"
    code_id: int | None = None

    @property
    def ok(self) -> bool:
        return self.reason == "ok"


def redeem(conn: sqlite3.Connection, account_id: int, raw: str | None, now: datetime) -> RedeemOutcome:
    """Thành viên nhập mã (gọi trong MỘT transaction). Không raise cho mã sai: lần thử vẫn được ghi."""
    fails = conn.execute(
        "SELECT COUNT(*) FROM coin_code_attempts WHERE account_id = ? AND ok = 0 AND created_at > ?",
        (account_id, auth_clock.iso(now - FAIL_WINDOW)),
    ).fetchone()[0]
    if int(fails) >= FAIL_LIMIT:
        return RedeemOutcome("rate_limited")  # không ghi lần thử: chờ đủ 60 phút là thử lại được
    conn.execute(
        "DELETE FROM coin_code_attempts WHERE account_id = ? AND created_at < ?",
        (account_id, auth_clock.iso(now - ATTEMPT_KEEP)),
    )
    norm = codes.normalize_code(raw)
    row = None
    if norm is not None:
        row = conn.execute(
            "SELECT id, amount, pack_id, created_by, used_at, revoked_at, expires_at FROM coin_topup_codes"
            " WHERE code_hash = ?",
            (codes.code_hash(norm),),
        ).fetchone()
    outcome: RedeemOutcome
    if row is None:
        outcome = RedeemOutcome("invalid")
    elif row["used_at"] is not None:
        outcome = RedeemOutcome("used")
    elif row["revoked_at"] is not None:
        outcome = RedeemOutcome("revoked")
    elif str(row["expires_at"]) <= auth_clock.iso(now):
        outcome = RedeemOutcome("expired")
    else:
        claimed = conn.execute(
            "UPDATE coin_topup_codes SET used_by = ?, used_at = ? WHERE id = ? AND used_at IS NULL"
            " AND revoked_at IS NULL AND expires_at > ?",
            (account_id, auth_clock.iso(now), int(row["id"]), auth_clock.iso(now)),
        ).rowcount
        if claimed != 1:
            outcome = RedeemOutcome("used")
        else:
            code_id = int(row["id"])
            amount = int(row["amount"])
            ledger.post(
                conn, account_id, amount, "topup_code", f"topup:{code_id}", code_id=code_id,
                actor_id=row["created_by"], now=now,
            )
            outcome = RedeemOutcome("ok", amount=amount, pack=str(row["pack_id"] or "custom"), code_id=code_id)
    conn.execute(
        "INSERT INTO coin_code_attempts (account_id, ok, created_at) VALUES (?, ?, ?)",
        (account_id, 1 if outcome.ok else 0, auth_clock.iso(now)),
    )
    return outcome


def admin_log(conn: sqlite3.Connection, now: datetime) -> dict[str, Any]:
    """50 dòng mới nhất của nạp bằng mã, chủ máy điều chỉnh, thưởng sáng tác (xếp hạng, công khai lần đầu, mốc cũ); và ba
    tổng của 30 ngày.
    Không có story, nhân vật hay tin nhắn của ai (chỉ @handle, số coin, lý do điều chỉnh, ghi chú của mã)."""
    marks = ", ".join("?" for _ in LOG_KINDS)
    rows = conn.execute(
        "SELECT l.id, l.created_at, l.kind, l.delta, l.reason, l.milestone, l.idem_key, a.handle, c.note AS code_note"
        " FROM coin_ledger l LEFT JOIN accounts a ON a.id = l.account_id"
        " LEFT JOIN coin_topup_codes c ON c.id = l.code_id"
        f" WHERE l.kind IN ({marks}) ORDER BY l.id DESC LIMIT ?",
        (*LOG_KINDS, LOG_LIMIT),
    ).fetchall()
    items: list[dict[str, Any]] = []
    for r in rows:
        kind = str(r["kind"])
        items.append(
            {
                "id": int(r["id"]),
                "created_at": str(r["created_at"]),
                "kind": kind,
                "handle": r["handle"],
                "delta": int(r["delta"]),
                "reason": r["reason"] if kind == "admin_adjust" else None,
                "note": (r["code_note"] or None) if kind == "topup_code" else None,
                "milestone": int(r["milestone"]) if kind == "creator_milestone" and r["milestone"] is not None else None,
                "label": hot.admin_label(str(r["idem_key"]), r["milestone"]) if kind == "creator_milestone" else None,
            }
        )
    since = auth_clock.iso(now - timedelta(days=LOG_DAYS))
    grant_marks = ", ".join("?" for _ in GRANT_KINDS)
    granted = conn.execute(
        f"SELECT COALESCE(SUM(delta), 0) FROM coin_ledger WHERE kind IN ({grant_marks}) AND delta > 0"
        " AND created_at >= ?",
        (*GRANT_KINDS, since),
    ).fetchone()[0]
    topped = conn.execute(
        "SELECT COALESCE(SUM(delta), 0) FROM coin_ledger WHERE kind = 'topup_code' AND created_at >= ?", (since,)
    ).fetchone()[0]
    spent = conn.execute(
        "SELECT COALESCE(SUM(delta), 0) FROM coin_ledger WHERE kind = 'chat' AND created_at >= ?", (since,)
    ).fetchone()[0]
    return {
        "items": items,
        "totals": {"days": LOG_DAYS, "granted": int(granted), "topped_up": int(topped), "spent": -int(spent)},
    }


__all__ = [
    "AMOUNT_MAX",
    "CODE_DAYS",
    "FAIL_LIMIT",
    "MAX_ACTIVE_CODES",
    "NOTE_MAX",
    "RedeemOutcome",
    "TopupRejected",
    "active_count",
    "admin_log",
    "create_code",
    "invalid",
    "list_codes",
    "owner_rejected",
    "rate_limited",
    "redeem",
    "revoke_code",
]
