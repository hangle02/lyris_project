"""Bảng "Nhân vật hot" (F46) và thưởng sáng tác theo bậc xếp hạng (F44 làm lại). docs/coins.md §2.2, §5.

- **Hot** = tổng người chơi từ trước tới nay (số dòng `creator_players` của nhân vật, PO 2C). Người chơi: `creator.py`.
  Người chơi có tài khoản đang bị tạm khoá không được đếm (bảng, thưởng công khai lần đầu, trình sửa; tạm chọn): chủ
  máy khoá tài khoản phụ thì nhân vật tụt hạng ở lần tính sau. Mở khoá thì được đếm lại.
- **Được xếp hạng** (tạm chọn): nhân vật gốc (`story_copy = 0`) đang công khai, người tạo `active`, ≥ 1 người chơi.
  Thứ tự: nhiều người chơi trước; bằng nhau thì `MAX(qualified_at)` nhỏ hơn trước; vẫn bằng thì `card_id` nhỏ hơn
  trước. Hạng 1, 2, 3… không trùng. Bảng lưu 100 hạng đầu (`hot_board`) và `hot_board_runs.ranked` (tổng đủ điều kiện).
- **Cập nhật mỗi giờ, tính khi cần** (tạm chọn): `refresh_if_stale` tính lại khi lần tính mới nhất cũ hơn 60 phút (hay
  chưa có); kiểm lại trong `BEGIN IMMEDIATE` nên hai request cùng lúc chỉ tính một lần. Lần tính mới xoá lần cũ.
- **Bậc** (PO 3A): hạng `r` đạt bậc N ∈ {100, 50, 10} khi `r ≤ N` và các nhân vật được xếp hạng thuộc ≥ N người tạo
  khác nhau (tạm chọn, chống tự lấp bảng: một người tạo có 10 nhân vật công khai chỉ tính là 1). Mỗi bậc một lần mỗi
  nhân vật (khoá chính `creator_rank_tiers`), cộng dồn: +100 / +200 / +300.
- **Trả** (`settle_rewards`, cuối mỗi lần tính, cùng transaction): bậc `waiting` được trả khi coin bật, nhân vật còn công
  khai, người tạo là thành viên `active`, và thưởng xếp hạng của người tạo trong 7 ngày coin gần nhất cộng bậc này ≤ 600
  (tạm chọn). Không thì chờ, không mất. Người tạo là chủ máy: `outcome = 'owner'`, không có coin.
- **Lỗi không lan** (tạm chọn): ghi bậc, mỗi dòng trả bậc và mỗi dòng +50 nằm trong SAVEPOINT riêng. Một dòng lỗi chỉ
  để chính dòng đó chờ lần tính sau; bậc đã đạt vẫn được ghi, người tạo khác vẫn được trả.
- **Công khai lần đầu** (PO 5A): +50 một lần mỗi tài khoản khi một nhân vật của tài khoản đã công khai liên tục ≥ 24 giờ
  (`card_public_since`) và có ≥ 1 người chơi. Chủ máy không bao giờ nhận.
- Sổ coin không có `kind` mới (CHECK không sửa được): `kind = 'creator_milestone'`, phân biệt bằng tiền tố `idem_key`
  (`rank:<X>:<N>`, `first_public:<account>`; dòng cũ `milestone:` giữ nguyên).
"""
from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from lyris.auth import clock as auth_clock
from lyris.coins.clock import coin_day
from lyris.coins.ledger import atomic, post

logger = logging.getLogger("lyris.coins")

TIERS: tuple[tuple[int, int], ...] = ((100, 100), (50, 200), (10, 300))  # (bậc top N, thưởng), thứ tự trả 100 → 50 → 10
TIER_REWARDS: dict[int, int] = dict(TIERS)
BOARD_SIZE = 100
STALE_AFTER = timedelta(minutes=60)
CAP_COINS = 600
CAP_WINDOW_DAYS = 7
FIRST_PUBLIC_REWARD = 50
FIRST_PUBLIC_AFTER = timedelta(hours=24)
RANK_PREFIX = "rank:"
FIRST_PUBLIC_PREFIX = "first_public:"
MILESTONE_PREFIX = "milestone:"

# Người chơi được đếm: tài khoản người chơi đang hoạt động (dùng với `creator_players p`).
_ACTIVE_PLAYER = "JOIN accounts pa ON pa.id = p.player_id AND pa.status = 'active'"
# Nhân vật được xếp hạng: gốc, đang công khai, người tạo đang hoạt động (dùng với `character_cards c`, `accounts a`).
_RANKABLE = "c.story_copy = 0 AND c.visibility = 'public' AND a.status = 'active'"


@dataclass(frozen=True)
class Ranked:
    rank: int
    card_id: int
    players: int


@dataclass(frozen=True)
class TierReached:
    """Một bậc vừa được ghi lần đầu. `paid`: trả ngay trong cùng lần tính."""

    card_id: int
    tier: int
    creator_id: int | None
    paid: bool


@dataclass(frozen=True)
class Payment:
    """Một dòng sổ thưởng vừa ghi. `source`: `creator_rank` hoặc `creator_first_public` (sự kiện `coins_granted`)."""

    account_id: int
    amount: int
    source: str


@dataclass
class Refresh:
    """Kết quả một lần tính bảng."""

    computed_at: str
    ranked: int
    creators: int = 0
    reached: list[TierReached] = field(default_factory=list)
    payments: list[Payment] = field(default_factory=list)


def _now(now: datetime | None) -> datetime:
    return now if now is not None else auth_clock.now()


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)).fetchone()
    return row is not None


# ---------------------------------------------------------------------------- lúc bật Công khai (§5.5)


def sync_public_since(conn: sqlite3.Connection, card_id: int, now: datetime | None = None) -> None:
    """Ghi `card_public_since (card_id, now)` khi nhân vật gốc đang công khai mà chưa có dòng; xoá dòng khi không còn
    công khai (hay là bản sao). Gọi sau mọi chỗ đổi `visibility` (tạo, sửa, chủ máy ẩn), cùng transaction."""
    if not _table_exists(conn, "card_public_since"):
        return
    row = conn.execute("SELECT visibility, story_copy FROM character_cards WHERE id = ?", (card_id,)).fetchone()
    if row is None:
        return
    if row[0] == "public" and not row[1]:
        conn.execute(
            "INSERT OR IGNORE INTO card_public_since (card_id, since) VALUES (?, ?)",
            (card_id, auth_clock.iso(_now(now))),
        )
    else:
        conn.execute("DELETE FROM card_public_since WHERE card_id = ?", (card_id,))


# ---------------------------------------------------------------------------- xếp hạng (§5.2)


def rank_cards(conn: sqlite3.Connection) -> tuple[list[Ranked], int]:
    """(100 hạng đầu, tổng số nhân vật đủ điều kiện xếp hạng)."""
    rows = conn.execute(
        "SELECT p.card_id, COUNT(*) AS players, MAX(p.qualified_at) AS reached FROM creator_players p"
        f" {_ACTIVE_PLAYER}"
        " JOIN character_cards c ON c.id = p.card_id"
        " JOIN accounts a ON a.id = c.account_id"
        f" WHERE {_RANKABLE}"
        " GROUP BY p.card_id ORDER BY players DESC, reached ASC, p.card_id ASC"
    ).fetchall()
    top = [Ranked(rank=i + 1, card_id=int(r[0]), players=int(r[1])) for i, r in enumerate(rows[:BOARD_SIZE])]
    return top, len(rows)


def ranked_creators(conn: sqlite3.Connection) -> int:
    """Số người tạo khác nhau có nhân vật được xếp hạng (cùng điều kiện với `rank_cards`). Bậc top N cần ≥ N."""
    row = conn.execute(
        "SELECT COUNT(DISTINCT c.account_id) FROM creator_players p"
        f" {_ACTIVE_PLAYER}"
        " JOIN character_cards c ON c.id = p.card_id"
        " JOIN accounts a ON a.id = c.account_id"
        f" WHERE {_RANKABLE}"
    ).fetchone()
    return int(row[0])


def latest_run(conn: sqlite3.Connection) -> Any:
    """(id, computed_at, ranked) của lần tính mới nhất, hay None."""
    return conn.execute("SELECT id, computed_at, ranked FROM hot_board_runs ORDER BY id DESC LIMIT 1").fetchone()


def is_stale(conn: sqlite3.Connection, now: datetime) -> bool:
    run = latest_run(conn)
    return run is None or auth_clock.parse(str(run[1])) <= now - STALE_AFTER


def compute(conn: sqlite3.Connection, now: datetime | None = None, *, coins: bool = True) -> Refresh:
    """Tính bảng ngay (không xét cũ/mới), ghi bậc mới, trả thưởng. Một transaction. Ghi bậc, trả bậc và thưởng công
    khai lần đầu là ba phần riêng (SAVEPOINT); bên trong, mỗi dòng trả cũng có SAVEPOINT riêng. Lỗi (lỗi DB,
    `IdemConflict`) chỉ cuộn lại phần lỗi: bảng vẫn cập nhật, bậc đã đạt vẫn được ghi, dòng lỗi chờ lần tính sau."""
    moment = _now(now)
    stamp = auth_clock.iso(moment)
    with atomic(conn):
        top, ranked = rank_cards(conn)
        creators = ranked_creators(conn)
        conn.execute("DELETE FROM hot_board_runs")
        run_id = conn.execute(
            "INSERT INTO hot_board_runs (computed_at, ranked) VALUES (?, ?)", (stamp, ranked)
        ).lastrowid
        conn.executemany(
            "INSERT INTO hot_board (run_id, rank, card_id, players) VALUES (?, ?, ?, ?)",
            [(run_id, r.rank, r.card_id, r.players) for r in top],
        )
        out = Refresh(computed_at=stamp, ranked=ranked, creators=creators)
        reached: list[TierReached] = []
        try:
            with atomic(conn):
                reached = reach_tiers(conn, top, ranked, moment, creators=creators)
        except Exception:
            logger.exception("Không ghi được bậc xếp hạng lúc tính bảng Nhân vật hot (thử lại ở lần tính sau)")
        payments: list[Payment] = []
        paid_keys: set[tuple[int, int]] = set()
        try:
            payments, paid_keys = settle_rewards(conn, moment, coins=coins)
        except Exception:
            logger.exception("Không trả được thưởng xếp hạng lúc tính bảng Nhân vật hot (thử lại ở lần tính sau)")
        try:
            payments = payments + first_public_check(conn, moment, coins=coins)
        except Exception:
            logger.exception("Không trả được thưởng công khai lần đầu lúc tính bảng Nhân vật hot (thử lại sau)")
        out.reached = [
            TierReached(r.card_id, r.tier, r.creator_id, paid=(r.card_id, r.tier) in paid_keys) for r in reached
        ]
        out.payments = payments
        return out


def refresh_if_stale(conn: sqlite3.Connection, now: datetime | None = None, *, coins: bool = True) -> Refresh | None:
    """Tính lại khi lần tính mới nhất cũ hơn 60 phút (hay chưa có). Kiểm lại trong `BEGIN IMMEDIATE`: hai lời gọi
    cùng lúc chỉ tính một lần. None: bảng còn mới."""
    moment = _now(now)
    if not is_stale(conn, moment):
        return None
    with atomic(conn):
        if not is_stale(conn, moment):  # request khác vừa tính xong
            return None
        return compute(conn, moment, coins=coins)


# ---------------------------------------------------------------------------- bậc và phần thưởng (§5.3, §5.4)


def _creator(conn: sqlite3.Connection, card_id: int) -> Any:
    """(người tạo, role, status, visibility, story_copy) của nhân vật; None nếu không có."""
    return conn.execute(
        "SELECT c.account_id, a.role, a.status, c.visibility, c.story_copy FROM character_cards c"
        " LEFT JOIN accounts a ON a.id = c.account_id WHERE c.id = ?",
        (card_id,),
    ).fetchone()


def reach_tiers(
    conn: sqlite3.Connection, top: list[Ranked], ranked: int, now: datetime, *, creators: int | None = None
) -> list[TierReached]:
    """Ghi các bậc đạt lần đầu ở lần tính này (`waiting`, hay `owner` khi người tạo là chủ máy). Bậc top N cần
    `r ≤ N` và các nhân vật được xếp hạng thuộc ≥ N người tạo khác nhau (`creators`, mặc định đếm lại)."""
    stamp = auth_clock.iso(now)
    makers = ranked_creators(conn) if creators is None else creators
    out: list[TierReached] = []
    for row in top:
        for tier, _reward in TIERS:
            if row.rank > tier or ranked < tier or makers < tier:
                continue
            exists = conn.execute(
                "SELECT 1 FROM creator_rank_tiers WHERE card_id = ? AND tier = ?", (row.card_id, tier)
            ).fetchone()
            if exists is not None:
                continue
            who = _creator(conn, row.card_id)
            creator_id = None if who is None or who[0] is None else int(who[0])
            outcome = "owner" if who is not None and who[1] == "owner" else "waiting"
            conn.execute(
                "INSERT INTO creator_rank_tiers (card_id, tier, creator_id, rank, outcome, ledger_id, reached_at,"
                " paid_at) VALUES (?, ?, ?, ?, ?, NULL, ?, NULL)",
                (row.card_id, tier, creator_id, row.rank, outcome, stamp),
            )
            out.append(TierReached(row.card_id, tier, creator_id, paid=False))
    return out


def window_start(moment: datetime) -> str:
    """Ngày coin đầu của 7 ngày coin gần nhất (hôm nay và 6 ngày trước)."""
    today = date.fromisoformat(coin_day(moment))
    return (today - timedelta(days=CAP_WINDOW_DAYS - 1)).isoformat()


def rank_paid_recently(conn: sqlite3.Connection, creator_id: int, moment: datetime) -> int:
    """Tổng thưởng xếp hạng đã trả cho người tạo trong 7 ngày coin gần nhất (đếm trong sổ, kể cả nhân vật đã xoá)."""
    row = conn.execute(
        "SELECT COALESCE(SUM(delta), 0) FROM coin_ledger WHERE account_id = ? AND kind = 'creator_milestone'"
        " AND idem_key LIKE 'rank:%' AND coin_day >= ?",
        (creator_id, window_start(moment)),
    ).fetchone()
    return int(row[0])


def rank_key(conn: sqlite3.Connection, card_id: int, tier: int) -> str:
    """`rank:<X>:<N>`. Bậc đang chờ chưa bao giờ có dòng sổ, nên khoá đã có trong sổ là của nhân vật cũ đã xoá cùng
    id (SQLite dùng lại id lớn nhất): thêm uid của nhân vật hiện tại (§5.6)."""
    key = f"{RANK_PREFIX}{card_id}:{tier}"
    if conn.execute("SELECT 1 FROM coin_ledger WHERE idem_key = ?", (key,)).fetchone() is None:
        return key
    uid = conn.execute("SELECT uid FROM character_cards WHERE id = ?", (card_id,)).fetchone()
    return f"{key}:{uid[0] if uid is not None else 'x'}"


def settle_rewards(
    conn: sqlite3.Connection, now: datetime | None = None, *, coins: bool = True
) -> tuple[list[Payment], set[tuple[int, int]]]:
    """Trả mọi bậc `waiting` được trả (cũ trước: `reached_at`, `card_id`, bậc 100 → 50 → 10). Trả (các dòng vừa ghi,
    tập (card_id, bậc) vừa trả). Coin tắt: không trả gì."""
    moment = _now(now)
    if not coins:
        return [], set()
    stamp = auth_clock.iso(moment)
    payments: list[Payment] = []
    paid: set[tuple[int, int]] = set()
    with atomic(conn):
        waiting = conn.execute(
            "SELECT card_id, tier FROM creator_rank_tiers WHERE outcome = 'waiting'"
            " ORDER BY reached_at, card_id, tier DESC"
        ).fetchall()
        for card_id, tier in ((int(r[0]), int(r[1])) for r in waiting):
            who = _creator(conn, card_id)
            if who is None or who[0] is None:
                continue
            creator_id, role, status, visibility, copy = int(who[0]), who[1], who[2], who[3], who[4]
            if role != "member" or status != "active" or visibility != "public" or copy:
                continue
            reward = TIER_REWARDS[tier]
            try:
                with atomic(conn):  # một dòng lỗi chỉ cuộn lại chính nó; các dòng khác vẫn được trả
                    if rank_paid_recently(conn, creator_id, moment) + reward > CAP_COINS:
                        continue  # trần 600 coin / 7 ngày coin: chờ, không mất
                    entry = post(
                        conn, creator_id, reward, "creator_milestone", rank_key(conn, card_id, tier),
                        card_id=card_id, milestone=tier, now=moment,
                    )
                    conn.execute(
                        "UPDATE creator_rank_tiers SET outcome = 'paid', ledger_id = ?, paid_at = ?, creator_id = ?"
                        " WHERE card_id = ? AND tier = ?",
                        (entry.id, stamp, creator_id, card_id, tier),
                    )
            except Exception:
                logger.exception("Không trả được bậc top %s của nhân vật %s (chờ lần tính sau)", tier, card_id)
                continue
            payments.append(Payment(creator_id, reward, "creator_rank"))
            paid.add((card_id, tier))
    return payments, paid


# ---------------------------------------------------------------------------- công khai lần đầu (§5.5)


def first_public_check(
    conn: sqlite3.Connection, now: datetime | None = None, *, coins: bool = True, account_id: int | None = None
) -> list[Payment]:
    """+50 `first_public:<tài khoản>` cho mỗi thành viên `active` chưa nhận, có một nhân vật gốc công khai liên tục
    ≥ 24 giờ với ≥ 1 người chơi. `account_id`: chỉ kiểm tài khoản đó (checkin). Coin tắt: không trả."""
    moment = _now(now)
    if not coins or not _table_exists(conn, "card_public_since"):
        return []
    cutoff = auth_clock.iso(moment - FIRST_PUBLIC_AFTER)
    only = " AND c.account_id = ?" if account_id is not None else ""
    params: tuple[Any, ...] = (cutoff, account_id) if account_id is not None else (cutoff,)
    out: list[Payment] = []
    with atomic(conn):
        rows = conn.execute(
            "SELECT c.account_id, MIN(c.id) FROM character_cards c"
            " JOIN card_public_since s ON s.card_id = c.id"
            " JOIN accounts a ON a.id = c.account_id"
            " WHERE c.story_copy = 0 AND c.visibility = 'public' AND a.role = 'member' AND a.status = 'active'"
            f" AND s.since <= ? AND EXISTS (SELECT 1 FROM creator_players p {_ACTIVE_PLAYER} WHERE p.card_id = c.id)"
            " AND NOT EXISTS (SELECT 1 FROM creator_first_public f WHERE f.account_id = c.account_id)"
            f"{only} GROUP BY c.account_id ORDER BY c.account_id",
            params,
        ).fetchall()
        stamp = auth_clock.iso(moment)
        for acc, card_id in ((int(r[0]), int(r[1])) for r in rows):
            try:
                with atomic(conn):  # một tài khoản lỗi không chặn tài khoản khác
                    entry = post(
                        conn, acc, FIRST_PUBLIC_REWARD, "creator_milestone", f"{FIRST_PUBLIC_PREFIX}{acc}",
                        card_id=card_id, now=moment,
                    )
                    conn.execute(
                        "INSERT INTO creator_first_public (account_id, card_id, ledger_id, paid_at) VALUES (?, ?, ?, ?)",
                        (acc, card_id, entry.id, stamp),
                    )
            except Exception:
                logger.exception("Không trả được thưởng công khai lần đầu của tài khoản %s (thử lại sau)", acc)
                continue
            out.append(Payment(acc, FIRST_PUBLIC_REWARD, "creator_first_public"))
    return out


# ---------------------------------------------------------------------------- đọc (§5.2, §5.7)


def board(conn: sqlite3.Connection, limit: int = BOARD_SIZE) -> dict[str, Any]:
    """`{updated_at, ranked, items}` của lần tính mới nhất. Bỏ nhân vật đã về Riêng tư, đã xoá hay có người tạo bị
    khoá kể từ lần tính (hạng của nhân vật khác giữ nguyên số tới lần tính sau). Mỗi hàng chỉ có trường công khai."""
    run = latest_run(conn)
    if run is None:
        return {"updated_at": None, "ranked": 0, "items": []}
    rows = conn.execute(
        "SELECT b.rank, b.card_id, b.players, c.name, c.avatar, a.handle FROM hot_board b"
        " JOIN character_cards c ON c.id = b.card_id JOIN accounts a ON a.id = c.account_id"
        " WHERE b.run_id = ? AND c.visibility = 'public' AND c.story_copy = 0 AND a.status = 'active'"
        " ORDER BY b.rank LIMIT ?",
        (int(run[0]), int(limit)),
    ).fetchall()
    items = [
        {
            "rank": int(r[0]),
            "card_id": int(r[1]),
            "players": int(r[2]),
            "name": str(r[3]),
            "avatar": r[4],
            "creator_handle": str(r[5]),
        }
        for r in rows
    ]
    return {"updated_at": str(run[1]), "ranked": int(run[2]), "items": items}


def card_rank(conn: sqlite3.Connection, card_id: int) -> int | None:
    run = latest_run(conn)
    if run is None:
        return None
    row = conn.execute(
        "SELECT rank FROM hot_board WHERE run_id = ? AND card_id = ?", (int(run[0]), card_id)
    ).fetchone()
    return None if row is None else int(row[0])


def next_tier_for(rank: int | None, reached: set[int] | dict[int, str]) -> int | None:
    """Bậc tiếp theo theo hạng hiện tại. Bậc chưa đạt mà hạng đã đủ (chỉ còn chờ bảng đủ người tạo): bậc nhỏ nhất trong
    số đó (bậc sẽ trả sớm nhất). Không thì bậc dễ nhất còn lại (lớn nhất). None khi đã đạt cả ba."""
    left = [t for t, _ in TIERS if t not in reached]
    if not left:
        return None
    within = [t for t in left if rank is not None and rank <= t]
    return min(within) if within else max(left)


def progress(conn: sqlite3.Connection, card_id: int, *, rewards: bool = True) -> dict[str, int | None]:
    """`{players, rank, next_tier, next_reward, waiting_coins, board_creators}` cho trình sửa nhân vật (§5.7). `players`:
    người chơi đang hoạt động. `rank` None: chưa có trên bảng. `next_tier`: `next_tier_for` (None khi đạt đủ).
    `board_creators`: số người tạo có nhân vật được xếp hạng (bậc top N chỉ trả khi ≥ N). `rewards=False` (chủ máy,
    coin tắt): `next_reward` None."""
    players = int(conn.execute(
        f"SELECT COUNT(*) FROM creator_players p {_ACTIVE_PLAYER} WHERE p.card_id = ?", (card_id,)
    ).fetchone()[0])
    tiers = {
        int(r[0]): str(r[1])
        for r in conn.execute("SELECT tier, outcome FROM creator_rank_tiers WHERE card_id = ?", (card_id,))
    }
    rank = card_rank(conn, card_id)
    next_tier = next_tier_for(rank, tiers)
    waiting = sum(TIER_REWARDS[t] for t, outcome in tiers.items() if outcome == "waiting")
    return {
        "players": players,
        "rank": rank,
        "next_tier": next_tier,
        "next_reward": TIER_REWARDS[next_tier] if next_tier is not None and rewards else None,
        "waiting_coins": waiting,
        "board_creators": ranked_creators(conn),
    }


def reward_label(idem_key: str, name: str, milestone: int | None) -> str:
    """Nhãn lịch sử ví của một dòng `creator_milestone` theo tiền tố `idem_key` (§5.7)."""
    if idem_key.startswith(RANK_PREFIX):
        return f"{name} vào top {milestone or 0} Nhân vật hot"
    if idem_key.startswith(FIRST_PUBLIC_PREFIX):
        return "Thưởng công khai nhân vật lần đầu"
    return f"{name} đạt {milestone or 0} người chơi"


def admin_label(idem_key: str, milestone: int | None) -> str:
    """Chữ "Nhật ký" của chủ máy cho một dòng thưởng sáng tác (§4.5)."""
    if idem_key.startswith(RANK_PREFIX):
        return f"Thưởng xếp hạng top {milestone or 0}"
    if idem_key.startswith(FIRST_PUBLIC_PREFIX):
        return "Thưởng công khai lần đầu"
    return f"Thưởng mốc {milestone or 0} người chơi"


__all__ = [
    "BOARD_SIZE",
    "CAP_COINS",
    "FIRST_PUBLIC_REWARD",
    "Payment",
    "Ranked",
    "Refresh",
    "STALE_AFTER",
    "TIERS",
    "TIER_REWARDS",
    "TierReached",
    "admin_label",
    "board",
    "card_rank",
    "compute",
    "first_public_check",
    "is_stale",
    "latest_run",
    "next_tier_for",
    "progress",
    "rank_cards",
    "ranked_creators",
    "rank_key",
    "refresh_if_stale",
    "reward_label",
    "settle_rewards",
    "sync_public_since",
]
