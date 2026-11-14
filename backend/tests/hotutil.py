"""F44 làm lại, F46 (docs/coins.md §5): tiện ích dựng bảng "Nhân vật hot" trong DB tạm.

Luật "ai là người chơi" có test riêng (`test_coins_creator.py`); ở đây người chơi được ghi thẳng vào `creator_players`
(như sau khi `note_charged` đã kiểm), để dựng bảng có 100+ nhân vật với số người chơi và thời điểm đạt muốn có.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from lyris.auth import clock
from lyris.auth import store as auth_store
from lyris.coins import hot
from lyris.db.repo import new_uid
from lyris.seed import load_seed_card
from tests.coinutil import CoinEnv

DAY1 = "2026-11-14T03:00:00"  # 10:00 ngày 14/11 giờ Việt Nam
EARLY = "2026-11-01T00:00:00.000Z"  # thời điểm đạt của nhân vật "lấp chỗ" (đạt sớm hơn mọi nhân vật đang thử)


def at(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=timezone.utc)


class Clock:
    """Đồng hồ server giả (`lyris.auth.clock.now`)."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, start: str = DAY1) -> None:
        self.t = at(start)
        monkeypatch.setattr(clock, "now", lambda: self.t)

    def days(self, n: float) -> None:
        self.t = self.t + timedelta(days=n)

    def minutes(self, n: float) -> None:
        self.t = self.t + timedelta(minutes=n)


async def ok(resp: Any) -> Any:
    assert resp.status_code == 200, (resp.request.method, str(resp.request.url), resp.status_code, resp.text)
    return resp.json()


def make_card(env: CoinEnv, who: str, name: str, *, visibility: str = "public") -> int:
    """Một nhân vật gốc của `who`, tạo bằng `Repo.create_card` (như POST /api/cards: ghi cả `card_public_since`)."""
    card = load_seed_card().model_copy(update={"id": None, "uid": None, "name": name, "visibility": visibility})
    created = env.repo.create_card(card, account_id=env.ids[who])
    assert created.id is not None
    return created.id


def pool(env: CoinEnv, n: int, prefix: str = "choi") -> list[int]:
    """`n` thành viên dùng làm người chơi (tạo một lần, dùng lại)."""
    have: list[int] = env.__dict__.setdefault("_pool", [])
    if len(have) < n:
        with env.repo.transaction():
            for i in range(len(have), n):
                have.append(
                    auth_store.insert_member(
                        env.repo.conn, uid=new_uid(), handle=f"{prefix}{i:03d}", display_name="Người chơi",
                        invited_by=env.ids["owner"],
                    )
                )
    return have[:n]


def give_players(env: CoinEnv, card_id: int, n: int, *, when: str | None = None) -> None:
    """Nhân vật `card_id` có thêm người chơi tới đủ `n` (ghi thẳng `creator_players`, thời điểm đạt `when`)."""
    players = pool(env, n)
    stamp = when or clock.iso(clock.now())
    with env.repo.transaction():
        conn = env.repo.conn
        creator = conn.execute("SELECT account_id FROM character_cards WHERE id = ?", (card_id,)).fetchone()[0]
        conn.executemany(
            "INSERT OR IGNORE INTO creator_players (card_id, player_id, creator_id, qualified_at) VALUES (?, ?, ?, ?)",
            [(card_id, p, creator, stamp) for p in players],
        )


def drop_players(env: CoinEnv, card_id: int, keep: int) -> None:
    """Chỉ giữ `keep` người chơi đầu (như người chơi xoá tài khoản)."""
    with env.repo.transaction():
        env.repo.conn.execute(
            "DELETE FROM creator_players WHERE card_id = ? AND player_id NOT IN"
            " (SELECT player_id FROM creator_players WHERE card_id = ? ORDER BY player_id LIMIT ?)",
            (card_id, card_id, keep),
        )


def creators(env: CoinEnv, n: int) -> list[int]:
    """`n` thành viên khác nhau làm người tạo "lấp chỗ" (tạo một lần, dùng lại theo thứ tự)."""
    have: list[int] = env.__dict__.setdefault("_creators", [])
    if len(have) < n:
        with env.repo.transaction():
            for i in range(len(have), n):
                have.append(
                    auth_store.insert_member(
                        env.repo.conn, uid=new_uid(), handle=f"lap{i:03d}", display_name="Người tạo",
                        invited_by=env.ids["owner"],
                    )
                )
    return have[:n]


def fillers(
    env: CoinEnv, n: int, players: int, *, who: str | None = None, when: str = EARLY, tag: str = ""
) -> list[int]:
    """`n` nhân vật công khai "lấp chỗ", mỗi nhân vật `players` người chơi đạt lúc `when` (sớm hơn nhân vật đang thử,
    nên đứng trước khi bằng người chơi). Mặc định mỗi nhân vật của một người tạo khác (`lap000`, `lap001`…, mỗi lần
    gọi dùng người tạo mới): bậc top N cần bảng có nhân vật của ≥ N người tạo khác nhau. `who`: mọi nhân vật của
    một tài khoản có sẵn."""
    start = len(env.__dict__.get("_creators", []))
    owners = creators(env, start + n)[start:] if who is None else [env.ids[who]] * n
    out = []
    for i, account in enumerate(owners):
        card = load_seed_card().model_copy(
            update={"id": None, "uid": None, "name": f"Lấp chỗ {tag}{players}-{i}", "visibility": "public"}
        )
        created = env.repo.create_card(card, account_id=account)
        assert created.id is not None
        give_players(env, created.id, players, when=when)
        out.append(created.id)
    return out


def compute(env: CoinEnv) -> hot.Refresh:
    """Tính bảng ngay qua dịch vụ của app (như lần tính mỗi giờ), coin theo cấu hình của app."""
    result = env.app.state.coins.refresh_hot(force=True)
    assert result is not None
    return result


def rank_of(env: CoinEnv, card_id: int) -> int | None:
    with env.repo.locked() as conn:
        return hot.card_rank(conn, card_id)


def rank_rows(env: CoinEnv, who: str) -> list[Any]:
    """Dòng sổ thưởng xếp hạng (`rank:`) của `who`, cũ trước."""
    return env.rows(
        "SELECT * FROM coin_ledger WHERE account_id = ? AND idem_key LIKE 'rank:%' ORDER BY id", env.ids[who]
    )


def tiers(env: CoinEnv, card_id: int) -> dict[int, str]:
    return {int(r[0]): str(r[1]) for r in env.rows(
        "SELECT tier, outcome FROM creator_rank_tiers WHERE card_id = ?", card_id
    )}


__all__ = [
    "Clock", "DAY1", "EARLY", "at", "compute", "creators", "drop_players", "fillers", "give_players", "make_card", "ok",
    "pool",
    "rank_of", "rank_rows", "tiers",
]
