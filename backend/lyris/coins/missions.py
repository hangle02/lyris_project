"""Nhiệm vụ ngày và quảng cáo mẫu (F45, docs/coins.md §6; quyết định nhiem-vu-va-quang-cao-mau).

Ba nhiệm vụ mỗi ngày coin (giờ Việt Nam, `coins.clock.coin_day`):

- `ad` "Xem quảng cáo": +5 mỗi lần, tối đa 3 lần; nhận trong hộp "Quảng cáo mẫu" (`claim_ad`).
- `characters` "Trò chuyện với 3 nhân vật khác nhau": +10 khi giữ chỗ `charged` của ngày có 3 `char_key` khác nhau.
- `turns` "Gửi 20 lượt": +5 khi có 20 giữ chỗ `charged` loại `send`/`retry` (không tính `regenerate`, tạm chọn).

Chat thử ở Studio (`mode = 'test'`) không tính cho `characters` hay `turns` (tạm chọn). Tiến độ đọc thẳng từ `coin_holds`.

`post_mission()` làm trong MỘT `BEGIN IMMEDIATE` (`ledger.atomic`): đọc tổng `delta` các dòng `kind = 'mission'` của ngày,
(quảng cáo) đếm số lần đã nhận `n` để dựng `idem_key …:ad:<n+1>`, kiểm điều kiện, kiểm tổng + phần sắp nhận ≤ 30, rồi
`ledger.post()`. Không đọc ở một transaction rồi ghi ở transaction khác.

Quảng cáo mẫu: server ghi giờ bắt đầu (`coin_ad_views.started_at`); chỉ nhận được khi đã đủ `seconds` (15) theo đồng hồ
server, trong vòng 10 phút, cùng ngày coin, đúng tài khoản, chưa bị huỷ. "Đóng" gọi `cancel_ad`. `start_ad` huỷ lượt xem dở
trước đó của tài khoản. Giới hạn biết trước: script gọi thẳng `start`, đợi đủ 15 giây rồi `claim` vẫn nhận được (tối đa
15 coin/ngày).
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from lyris.auth import clock as auth_clock
from lyris.coins.clock import coin_day
from lyris.coins.errors import CoinError
from lyris.coins.ledger import Entry, atomic, post
from lyris.db.repo import NotFound

AD_SECONDS = 15
AD_TTL = timedelta(minutes=10)
DAILY_CAP = 30


@dataclass(frozen=True)
class MissionSpec:
    id: str
    target: int
    reward: int


SPECS: dict[str, MissionSpec] = {
    "ad": MissionSpec("ad", 3, 5),
    "characters": MissionSpec("characters", 3, 10),
    "turns": MissionSpec("turns", 20, 5),
}
ORDER = ("ad", "characters", "turns")

# §6.2, §10.5: chữ của lỗi (giao diện hiện nguyên câu).
AD_LIMIT_DETAIL = "Hôm nay bạn đã xem đủ 3 quảng cáo."
AD_NOT_FINISHED_DETAIL = "Quảng cáo chưa xem xong."
AD_EXPIRED_DETAIL = "Lượt xem này đã hết hạn. Hãy xem lại."
MISSION_CAP_DETAIL = "Hôm nay bạn đã nhận đủ 30 coin từ nhiệm vụ. Quay lại sau 0:00 nhé."
MISSION_NOT_DONE_DETAIL = "Nhiệm vụ này chưa xong."
NO_MISSIONS_DETAIL = "Tài khoản này không có nhiệm vụ."
AD_NOT_FOUND_DETAIL = "Không tìm thấy lượt xem quảng cáo."


class MissionRejected(CoinError):
    """Nhận thưởng / bắt đầu quảng cáo bị từ chối: `{detail, code}` với HTTP `status` (409)."""

    def __init__(self, code: str, detail: str, status: int = 409) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.status = status

    def payload(self) -> dict[str, Any]:
        return {"detail": self.detail, "code": self.code}


def _now(now: datetime | None) -> datetime:
    return now if now is not None else auth_clock.now()


def mission_key(account_id: int, day: str, mission: str, n: int | None = None) -> str:
    """`mission:<tài khoản>:<ngày coin>:<nhiệm vụ>[:<n>]` (§2.1)."""
    base = f"mission:{account_id}:{day}:{mission}"
    return base if n is None else f"{base}:{n}"


# ---------------------------------------------------------------------------- đọc tiến độ


def earned_today(conn: sqlite3.Connection, account_id: int, day: str) -> int:
    """Tổng coin từ nhiệm vụ trong ngày coin (mọi dòng `kind = 'mission'`, kể cả nhiệm vụ thêm sau này)."""
    row = conn.execute(
        "SELECT COALESCE(SUM(delta), 0) FROM coin_ledger WHERE account_id = ? AND coin_day = ? AND kind = 'mission'",
        (account_id, day),
    ).fetchone()
    return int(row[0])


def ad_claims(conn: sqlite3.Connection, account_id: int, day: str) -> int:
    row = conn.execute(
        "SELECT COUNT(*) FROM coin_ledger WHERE account_id = ? AND coin_day = ? AND kind = 'mission' AND mission = 'ad'"
        " AND idem_key LIKE ?",
        (account_id, day, mission_key(account_id, day, "ad") + ":%"),
    ).fetchone()
    return int(row[0])


def characters_count(conn: sqlite3.Connection, account_id: int, day: str) -> int:
    """Nhân vật khác nhau (`char_key`: bản sao tính theo nhân vật gốc) đã trả lời mình trong ngày (đã trả coin)."""
    row = conn.execute(
        "SELECT COUNT(DISTINCT char_key) FROM coin_holds WHERE account_id = ? AND coin_day = ? AND status = 'charged'"
        " AND mode IN ('story', 'dm') AND char_key IS NOT NULL",
        (account_id, day),
    ).fetchone()
    return int(row[0])


def turns_count(conn: sqlite3.Connection, account_id: int, day: str) -> int:
    """Câu trả lời đã trả coin của lượt gửi mới và "Trả lời" (không tính "Tạo lại", không tính chat thử)."""
    row = conn.execute(
        "SELECT COUNT(*) FROM coin_holds WHERE account_id = ? AND coin_day = ? AND status = 'charged'"
        " AND mode IN ('story', 'dm') AND kind IN ('send', 'retry')",
        (account_id, day),
    ).fetchone()
    return int(row[0])


def _done(conn: sqlite3.Connection, account_id: int, day: str, mission: str) -> int:
    if mission == "characters":
        return characters_count(conn, account_id, day)
    if mission == "turns":
        return turns_count(conn, account_id, day)
    raise ValueError(f"nhiệm vụ không hợp lệ: {mission}")


def _claimed(conn: sqlite3.Connection, account_id: int, day: str, mission: str) -> bool:
    key = mission_key(account_id, day, mission)
    return conn.execute("SELECT 1 FROM coin_ledger WHERE idem_key = ?", (key,)).fetchone() is not None


def view(conn: sqlite3.Connection, account_id: int, now: datetime | None = None) -> dict[str, Any]:
    """`GET /api/coins/missions` của một thành viên (§7)."""
    day = coin_day(_now(now))
    earned = earned_today(conn, account_id, day)
    room = DAILY_CAP - earned
    items: list[dict[str, Any]] = []
    for mission in ORDER:
        spec = SPECS[mission]
        if mission == "ad":
            n = ad_claims(conn, account_id, day)
            items.append({
                "id": mission, "progress": min(n, spec.target), "target": spec.target, "reward": spec.reward,
                "claimed": n >= spec.target, "claimable": False, "remaining": max(0, spec.target - n),
            })
            continue
        done = _done(conn, account_id, day, mission)
        claimed = _claimed(conn, account_id, day, mission)
        items.append({
            "id": mission, "progress": min(done, spec.target), "target": spec.target, "reward": spec.reward,
            "claimed": claimed, "claimable": not claimed and done >= spec.target and spec.reward <= room,
            "remaining": max(0, spec.target - done),
        })
    return {"coin_day": day, "earned_today": earned, "cap": DAILY_CAP, "missions": items}


# ---------------------------------------------------------------------------- nhận thưởng


def post_mission(conn: sqlite3.Connection, account_id: int, mission: str, *, now: datetime | None = None) -> Entry:
    """Nhận thưởng một nhiệm vụ: đọc, kiểm và ghi sổ trong một `BEGIN IMMEDIATE`.

    `characters`/`turns`: đã nhận hôm nay → trả dòng cũ (`created=False`); chưa đủ → `mission_not_done`.
    `ad`: lần thứ n+1 (`…:ad:<n+1>`); đã 3 lần → `ad_limit` (gọi từ `claim_ad`, cùng transaction với lượt xem).
    Tổng nhiệm vụ của ngày + thưởng > 30 → `mission_cap`."""
    spec = SPECS.get(mission)
    if spec is None:
        raise ValueError(f"nhiệm vụ không hợp lệ: {mission}")
    moment = _now(now)
    day = coin_day(moment)
    with atomic(conn):
        if mission == "ad":
            n = ad_claims(conn, account_id, day)
            if n >= spec.target:
                raise MissionRejected("ad_limit", AD_LIMIT_DETAIL)
            key = mission_key(account_id, day, "ad", n + 1)
        else:
            key = mission_key(account_id, day, mission)
            old = conn.execute("SELECT 1 FROM coin_ledger WHERE idem_key = ?", (key,)).fetchone()
            if old is not None:
                return post(conn, account_id, spec.reward, "mission", key, mission=mission, now=moment)
            if _done(conn, account_id, day, mission) < spec.target:
                raise MissionRejected("mission_not_done", MISSION_NOT_DONE_DETAIL)
        if earned_today(conn, account_id, day) + spec.reward > DAILY_CAP:
            raise MissionRejected("mission_cap", MISSION_CAP_DETAIL)
        return post(conn, account_id, spec.reward, "mission", key, mission=mission, now=moment)


# ---------------------------------------------------------------------------- quảng cáo mẫu


def start_ad(
    conn: sqlite3.Connection, account_id: int, *, now: datetime | None = None, seconds: int = AD_SECONDS
) -> dict[str, Any]:
    """Bắt đầu một lượt xem: còn lượt (< 3 lần đã nhận hôm nay) thì huỷ lượt xem dở trước đó và ghi giờ bắt đầu."""
    moment = _now(now)
    day = coin_day(moment)
    stamp = auth_clock.iso(moment)
    with atomic(conn):
        if ad_claims(conn, account_id, day) >= SPECS["ad"].target:
            raise MissionRejected("ad_limit", AD_LIMIT_DETAIL)
        conn.execute(
            "UPDATE coin_ad_views SET cancelled_at = ? WHERE account_id = ? AND claimed_at IS NULL AND cancelled_at IS NULL",
            (stamp, account_id),
        )
        cur = conn.execute(
            "INSERT INTO coin_ad_views (account_id, coin_day, started_at) VALUES (?, ?, ?)", (account_id, day, stamp)
        )
        assert cur.lastrowid is not None
        return {"ad_id": int(cur.lastrowid), "seconds": seconds}


def _own_view(conn: sqlite3.Connection, account_id: int, ad_id: int) -> sqlite3.Row:
    row = conn.execute(
        "SELECT id, coin_day, started_at, claimed_at, cancelled_at FROM coin_ad_views WHERE id = ? AND account_id = ?",
        (ad_id, account_id),
    ).fetchone()
    if row is None:
        raise NotFound(AD_NOT_FOUND_DETAIL)
    return row  # type: ignore[no-any-return]


def claim_ad(
    conn: sqlite3.Connection, account_id: int, ad_id: int, *, now: datetime | None = None, seconds: int = AD_SECONDS
) -> tuple[int, bool]:
    """Nhận 5 coin cho một lượt xem (kiểm theo đồng hồ server, cùng transaction với `post_mission`).

    Trả (số coin, vừa cộng?). Đã nhận rồi → (5, False), không cộng thêm. Không có / của người khác → `NotFound` (404)."""
    moment = _now(now)
    reward = SPECS["ad"].reward
    with atomic(conn):
        row = _own_view(conn, account_id, ad_id)
        if row["claimed_at"] is not None:
            return reward, False
        started = auth_clock.parse(str(row["started_at"]))
        if row["cancelled_at"] is not None or moment - started > AD_TTL or str(row["coin_day"]) != coin_day(moment):
            raise MissionRejected("ad_expired", AD_EXPIRED_DETAIL)
        if moment - started < timedelta(seconds=seconds):
            raise MissionRejected("ad_not_finished", AD_NOT_FINISHED_DETAIL)
        entry = post_mission(conn, account_id, "ad", now=moment)
        conn.execute("UPDATE coin_ad_views SET claimed_at = ? WHERE id = ?", (auth_clock.iso(moment), ad_id))
        return reward, entry.created


def cancel_ad(conn: sqlite3.Connection, account_id: int, ad_id: int, *, now: datetime | None = None) -> None:
    """"Đóng" trước khi nhận: lượt xem đó không bao giờ nhận được nữa. Gọi lại (hay lượt đã nhận) không lỗi."""
    with atomic(conn):
        _own_view(conn, account_id, ad_id)
        conn.execute(
            "UPDATE coin_ad_views SET cancelled_at = ? WHERE id = ? AND claimed_at IS NULL AND cancelled_at IS NULL",
            (auth_clock.iso(_now(now)), ad_id),
        )


__all__ = [
    "AD_SECONDS",
    "AD_TTL",
    "DAILY_CAP",
    "ORDER",
    "SPECS",
    "MissionRejected",
    "MissionSpec",
    "ad_claims",
    "cancel_ad",
    "characters_count",
    "claim_ad",
    "earned_today",
    "mission_key",
    "post_mission",
    "start_ad",
    "turns_count",
    "view",
]
