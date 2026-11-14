"""F44 làm lại (docs/coins.md §5.3–§5.7; quyết định xep-hang-nhan-vat-hot): thưởng sáng tác theo bảng "Nhân vật hot".

Nhân vật công khai vào top 100 / top 50 / top 10 → người tạo +100 / +200 / +300 coin, mỗi bậc một lần mỗi nhân vật,
cộng dồn. Bậc top N chỉ trả khi bảng có ≥ N nhân vật được xếp hạng (tạm chọn). Trần 600 coin thưởng xếp hạng mỗi 7
ngày coin cho mỗi người tạo (tạm chọn; vượt thì chờ, không mất). Công khai lần đầu: +50 một lần mỗi tài khoản khi nhân
vật công khai liên tục ≥ 24 giờ và có ≥ 1 người chơi. Chủ máy không bao giờ nhận coin. Thưởng mốc người chơi cũ bị bỏ.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from lyris.analytics import events
from lyris.analytics.events import EventRejected
from lyris.coins import hot, ledger, topup
from lyris.coins.errors import IdemConflict
from tests.coinutil import coin_env
from tests.hotutil import (
    Clock,
    compute,
    drop_players,
    fillers,
    give_players,
    make_card,
    ok,
    rank_of,
    rank_rows,
    tiers,
)
from tests.test_coins_creator import _play, _public_card, _qualify

NAME = "Hạ Vy"


def _keys(rows: list[Any]) -> list[tuple[str, int]]:
    return [(str(r["idem_key"]), int(r["delta"])) for r in rows]


def _events(env: Any, name: str) -> list[dict[str, Any]]:
    return [json.loads(r[0]) for r in env.rows("SELECT props_json FROM analytics_events WHERE name = ? ORDER BY id", name)]


def _board_with_x_at_7(env: Any, x: int) -> None:
    """Bảng 100 nhân vật được xếp hạng, X hạng 7: 4 nhân vật 12 người chơi, 2 nhân vật 11, X 10, 93 nhân vật 1."""
    fillers(env, 4, 12, tag="a")
    fillers(env, 2, 11, tag="b")
    give_players(env, x, 10)
    fillers(env, 93, 1, tag="c")


# ---------------------------------------------------------------------------- mốc cũ bị bỏ


async def test_milestones_no_longer_paid_old_rows_keep_label(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    clk = Clock(monkeypatch)
    players = tuple(f"p{i:02d}" for i in range(1, 11))
    async with coin_env(tmp_path, ("havy", *players)) as env:
        x = await _public_card(env.clients["havy"])
        # Dòng thưởng mốc cũ (trước khi đổi luật), ghi bằng post() như bản cũ.
        with env.repo.transaction():
            old_id = ledger.post(
                env.repo.conn, env.ids["havy"], 100, "creator_milestone", f"milestone:{x}:10", card_id=x, milestone=10
            ).id
        before = env.balance("havy")
        # Người chơi thứ 10 đủ điều kiện qua đúng đường trừ coin của app: không có dòng sổ mới nào.
        await _qualify(env, clk, players, {w: await _play(env, w, x) for w in players})
        assert env.rows("SELECT COUNT(*) FROM creator_players WHERE card_id = ?", x)[0][0] == 10
        # Người chơi thứ 50 và 100 (dựng thẳng): vẫn không có dòng `milestone:` mới, kể cả sau checkin và tính bảng.
        give_players(env, x, 100)
        await ok(await env.clients["havy"].post("/api/coins/checkin"))
        milestones = env.rows("SELECT idem_key FROM coin_ledger WHERE idem_key LIKE 'milestone:%'")
        assert [r[0] for r in milestones] == [f"milestone:{x}:10"]
        assert env.rows("SELECT COUNT(*) FROM creator_milestones")[0][0] == 0
        # Chỉ quà đăng nhập (+60) và thưởng công khai lần đầu (+50: X công khai ≥ 24 giờ, có người chơi); không có mốc.
        assert env.balance("havy") == before + 60 + 50
        assert {r["idem_key"] for r in env.ledger("havy") if r["id"] > old_id} == {
            f"daily:{env.ids['havy']}:2026-11-15", f"first_public:{env.ids['havy']}",
        }
        # Dòng cũ vẫn hiện trong lịch sử ví với nhãn cũ.
        items = (await ok(await env.clients["havy"].get("/api/coins/history")))["items"]
        rewards = [(i["label"], i["delta"]) for i in items if i["kind"] == "creator_milestone"]
        assert rewards == [("Thưởng công khai nhân vật lần đầu", 50), (f"{NAME} đạt 10 người chơi", 100)]


# ---------------------------------------------------------------------------- bậc và phần thưởng


async def test_rank_tiers_pay_100_200_300_once_cumulative(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    clk = Clock(monkeypatch)
    async with coin_env(tmp_path, ("havy",)) as env:
        x = make_card(env, "havy", NAME)
        _board_with_x_at_7(env, x)
        start = env.balance("havy")
        result = compute(env)
        assert result.ranked == 100 and rank_of(env, x) == 7
        assert _keys(rank_rows(env, "havy")) == [(f"rank:{x}:100", 100), (f"rank:{x}:50", 200), (f"rank:{x}:10", 300)]
        assert [(r["milestone"], r["card_id"], r["kind"]) for r in rank_rows(env, "havy")] == [
            (100, x, "creator_milestone"), (50, x, "creator_milestone"), (10, x, "creator_milestone"),
        ]
        assert env.balance("havy") == start + 600
        assert tiers(env, x) == {100: "paid", 50: "paid", 10: "paid"}
        ledger_ids = {int(r[0]) for r in env.rows("SELECT ledger_id FROM creator_rank_tiers WHERE card_id = ?", x)}
        assert ledger_ids == {int(r["id"]) for r in rank_rows(env, "havy")}

        # settle_rewards thêm 3 lần; tính lại sau 61 phút với X vẫn hạng 7: vẫn chỉ ba dòng.
        with env.repo.transaction():
            for _ in range(3):
                assert hot.settle_rewards(env.repo.conn) == ([], set())
        clk.minutes(61)
        assert env.app.state.coins.refresh_hot() is not None
        assert rank_of(env, x) == 7
        assert len(rank_rows(env, "havy")) == 3 and env.balance("havy") == start + 600

        # X rớt hạng 120 (người chơi xoá tài khoản: còn 1 người chơi, đạt muộn nhất), rồi lên lại hạng 5.
        drop_players(env, x, 1)
        fillers(env, 20, 1, tag="d")
        dropped = compute(env)
        # 120 nhân vật được xếp hạng; X (1 người chơi, đạt muộn nhất) đứng cuối: hạng 120, ngoài 100 hạng được lưu.
        assert dropped.ranked == 120 and rank_of(env, x) is None
        with env.repo.locked() as conn:
            order = conn.execute(
                "SELECT p.card_id FROM creator_players p GROUP BY p.card_id"
                " ORDER BY COUNT(*) DESC, MAX(p.qualified_at), p.card_id"
            ).fetchall()
        assert [int(r[0]) for r in order].index(x) + 1 == 120
        give_players(env, x, 12)
        compute(env)
        assert rank_of(env, x) == 5
        assert len(rank_rows(env, "havy")) == 3 and env.balance("havy") == start + 600


async def test_tier_needs_board_of_at_least_n_creators(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    Clock(monkeypatch)
    async with coin_env(tmp_path, ("havy",)) as env:
        # Một người tạo tự lấp bảng: 12 nhân vật công khai, mỗi nhân vật 1 người chơi (cùng một người chơi). 12 nhân vật
        # được xếp hạng nhưng chỉ của 1 người tạo → không bậc nào, không dòng `rank:` nào.
        farm = [make_card(env, "havy", f"Trại {i}") for i in range(12)]
        for card in farm:
            give_players(env, card, 1)
        result = compute(env)
        assert (result.ranked, result.creators) == (12, 1)
        assert [rank_of(env, card) for card in farm] == list(range(1, 13))
        assert rank_rows(env, "havy") == [] and all(tiers(env, card) == {} for card in farm)

        x = make_card(env, "havy", NAME)
        give_players(env, x, 10)
        # 21 nhân vật được xếp hạng nhưng của 9 người tạo (havy + 8), X hạng 1: không có dòng `rank:` nào.
        fillers(env, 8, 1, tag="a")
        result = compute(env)
        assert (result.ranked, result.creators) == (21, 9)
        assert rank_of(env, x) == 1 and rank_rows(env, "havy") == [] and tiers(env, x) == {}
        # 60 người tạo (72 nhân vật), X hạng 7: chỉ top 50 và top 10 (+500), không có top 100.
        fillers(env, 6, 12, tag="b")
        fillers(env, 45, 1, tag="c")
        start = env.balance("havy")
        result = compute(env)
        assert (result.ranked, result.creators) == (72, 60)
        assert rank_of(env, x) == 7
        assert _keys(rank_rows(env, "havy")) == [(f"rank:{x}:50", 200), (f"rank:{x}:10", 300)]
        assert env.balance("havy") == start + 500
        # Bảng lên 100 người tạo mà X vẫn hạng ≤ 100: top 100 (+100) được trả ở lần tính đó; nhân vật "trại" vẫn không.
        fillers(env, 40, 1, tag="e")
        result = compute(env)
        assert (result.ranked, result.creators) == (112, 100)
        assert rank_of(env, x) == 7
        assert _keys(rank_rows(env, "havy"))[-1] == (f"rank:{x}:100", 100)
        assert env.balance("havy") == start + 600
        assert all(tiers(env, card) == {} for card in farm)


async def test_rank_rewards_capped_600_per_7_days_wait_not_lost(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    clk = Clock(monkeypatch)
    async with coin_env(tmp_path, ("havy",)) as env:
        # Thưởng mốc cũ không tính vào trần.
        with env.repo.transaction():
            ledger.post(env.repo.conn, env.ids["havy"], 600, "creator_milestone", "milestone:999:100", milestone=100)
        x1 = make_card(env, "havy", f"{NAME} 1")
        _board_with_x_at_7(env, x1)
        def rank_paid() -> int:
            return sum(int(r["delta"]) for r in rank_rows(env, "havy"))

        compute(env)
        assert rank_paid() == 600  # đủ 600 dù đã có dòng mốc cũ 600

        # Nhân vật thứ hai của cùng người tạo lên top 10 hôm sau: ba bậc chờ, không có dòng sổ.
        clk.days(1)
        x2 = make_card(env, "havy", f"{NAME} 2")
        give_players(env, x2, 12)
        compute(env)
        assert rank_of(env, x2) is not None and rank_of(env, x2) <= 10
        assert tiers(env, x2) == {100: "waiting", 50: "waiting", 10: "waiting"}
        assert env.rows("SELECT COUNT(*) FROM coin_ledger WHERE idem_key LIKE ?", f"rank:{x2}:%")[0][0] == 0
        assert rank_paid() == 600
        # 6 ngày coin sau lần trả đầu (vẫn trong 7 ngày coin): vẫn chờ.
        clk.days(5)
        compute(env)
        assert tiers(env, x2) == {100: "waiting", 50: "waiting", 10: "waiting"}
        # Đủ 7 ngày coin sau lần trả đầu: trả đủ 600, không mất.
        clk.days(1)
        compute(env)
        assert tiers(env, x2) == {100: "paid", 50: "paid", 10: "paid"}
        assert _keys(rank_rows(env, "havy"))[-3:] == [
            (f"rank:{x2}:100", 100), (f"rank:{x2}:50", 200), (f"rank:{x2}:10", 300),
        ]
        assert rank_paid() == 1200
        # Mọi cửa sổ 7 ngày coin có tối đa 600 coin thưởng xếp hạng.
        days = [(r["coin_day"], int(r["delta"])) for r in rank_rows(env, "havy")]
        from datetime import date, timedelta

        for d, _ in days:
            first = date.fromisoformat(d)
            total = sum(v for e, v in days if first <= date.fromisoformat(e) < first + timedelta(days=7))
            assert total <= 600, days


async def test_owner_coins_off_disabled_private_tiers_wait(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    clk = Clock(monkeypatch)
    async with coin_env(tmp_path, ("havy", "lan", "minh")) as env:
        coins = env.app.state.coins
        owner = env.clients["owner"]
        # Người tạo là chủ máy: có hạng, outcome 'owner', không có dòng sổ, không có first_public.
        o = make_card(env, "owner", "Của chủ máy")
        hv, ln, mn = (make_card(env, w, f"{NAME} {w}") for w in ("havy", "lan", "minh"))
        for card in (o, hv, ln, mn):
            give_players(env, card, 12)
        fillers(env, 96, 1)
        # Coin tắt lúc đạt bậc: bậc của thành viên chờ.
        coins.enabled = False
        compute(env)
        assert tiers(env, o) == {100: "owner", 50: "owner", 10: "owner"}
        for card in (hv, ln, mn):
            assert tiers(env, card) == {100: "waiting", 50: "waiting", 10: "waiting"}, card
        assert env.rows("SELECT COUNT(*) FROM coin_ledger WHERE idem_key LIKE 'rank:%'")[0][0] == 0
        # lan bị tạm khoá, nhân vật của minh về Riêng tư; bật coin lại → chỉ havy được trả.
        await ok(await owner.post(f"/api/admin/accounts/{env.ids['lan']}/disable"))
        card = env.repo.get_card(mn, account_id=env.ids["minh"])
        await ok(await env.clients["minh"].put(f"/api/cards/{mn}", json={**card.model_dump(), "visibility": "private"}))
        coins.enabled = True
        clk.minutes(61)
        compute(env)
        assert tiers(env, hv) == {100: "paid", 50: "paid", 10: "paid"}
        assert tiers(env, ln) == {100: "waiting", 50: "waiting", 10: "waiting"}
        assert tiers(env, mn) == {100: "waiting", 50: "waiting", 10: "waiting"}
        # Mở khoá, công khai lại → trả ở lần tính đầu tiên sau đó.
        await ok(await owner.post(f"/api/admin/accounts/{env.ids['lan']}/enable"))
        await ok(await env.clients["minh"].put(f"/api/cards/{mn}", json={**card.model_dump(), "visibility": "public"}))
        clk.minutes(61)
        assert coins.refresh_hot() is not None
        for card_id, who in ((ln, "lan"), (mn, "minh")):
            assert tiers(env, card_id) == {100: "paid", 50: "paid", 10: "paid"}
            assert sum(int(r["delta"]) for r in rank_rows(env, who)) == 600
        # Chủ máy: không có dòng sổ, không có ví, không có thưởng công khai lần đầu (kể cả sau 24 giờ).
        clk.days(2)
        compute(env)
        assert env.ledger("owner") == []
        assert env.rows("SELECT COUNT(*) FROM coin_wallets WHERE account_id = ?", env.ids["owner"])[0][0] == 0
        assert env.rows("SELECT COUNT(*) FROM creator_first_public WHERE account_id = ?", env.ids["owner"])[0][0] == 0


# ---------------------------------------------------------------------------- công khai lần đầu


async def test_first_public_bonus_50_after_24h_with_player_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    clk = Clock(monkeypatch)
    async with coin_env(tmp_path, ("havy", "lan")) as env:
        havy = env.clients["havy"]
        x = await _public_card(havy)
        since = env.rows("SELECT since FROM card_public_since WHERE card_id = ?", x)[0][0]
        give_players(env, x, 1)
        # 23 giờ 59 phút: chưa có.
        clk.minutes(24 * 60 - 1)
        await ok(await havy.post("/api/coins/checkin"))
        compute(env)
        assert env.rows("SELECT COUNT(*) FROM coin_ledger WHERE idem_key LIKE 'first_public:%'")[0][0] == 0
        # Đủ 24 giờ: đúng một dòng +50 (checkin của chính tài khoản).
        clk.minutes(1)
        before = env.balance("havy")
        await ok(await havy.post("/api/coins/checkin"))
        rows = env.rows("SELECT idem_key, delta, card_id FROM coin_ledger WHERE idem_key LIKE 'first_public:%'")
        assert [tuple(r) for r in rows] == [(f"first_public:{env.ids['havy']}", 50, x)]
        assert env.balance("havy") == before + 50
        assert [tuple(r) for r in env.rows("SELECT account_id, card_id FROM creator_first_public")] == [(env.ids["havy"], x)]
        # Nhân vật công khai thứ hai của cùng người tạo: không thêm dòng nào.
        y = await _public_card(havy, f"{NAME} 2")
        give_players(env, y, 1)
        clk.days(2)
        compute(env)
        await ok(await havy.post("/api/coins/checkin"))
        assert env.rows("SELECT COUNT(*) FROM coin_ledger WHERE idem_key LIKE 'first_public:%'")[0][0] == 1

        # Về Riêng tư rồi công khai lại: `since` đổi sang lúc bật lại (24 giờ đếm lại).
        body = env.repo.get_card(x, account_id=env.ids["havy"]).model_dump()
        await ok(await havy.put(f"/api/cards/{x}", json={**body, "visibility": "private"}))
        assert env.rows("SELECT COUNT(*) FROM card_public_since WHERE card_id = ?", x)[0][0] == 0
        clk.minutes(5)
        await ok(await havy.put(f"/api/cards/{x}", json={**body, "visibility": "public"}))
        again = env.rows("SELECT since FROM card_public_since WHERE card_id = ?", x)[0][0]
        assert again != since and again == hot.auth_clock.iso(clk.t)
        # Lưu lại khi vẫn công khai: `since` không đổi.
        clk.minutes(5)
        await ok(await havy.put(f"/api/cards/{x}", json={**body, "name": "Tên mới", "visibility": "public"}))
        assert env.rows("SELECT since FROM card_public_since WHERE card_id = ?", x)[0][0] == again

        # lan: nhân vật công khai đủ 24 giờ mà 0 người chơi → không trả; bật bằng cách lưu lại → vẫn chưa.
        z = await _public_card(env.clients["lan"], "Của Lan")
        clk.days(2)
        await ok(await env.clients["lan"].post("/api/coins/checkin"))
        compute(env)
        assert env.rows("SELECT COUNT(*) FROM coin_ledger WHERE idem_key = ?", f"first_public:{env.ids['lan']}")[0][0] == 0
        # Chủ máy ẩn nhân vật (sau báo cáo): dòng `card_public_since` bị xoá.
        give_players(env, z, 1)
        await ok(await env.clients["owner"].post(f"/api/admin/cards/{z}/unpublish"))
        assert env.rows("SELECT COUNT(*) FROM card_public_since WHERE card_id = ?", z)[0][0] == 0
        compute(env)
        assert env.rows("SELECT COUNT(*) FROM coin_ledger WHERE idem_key = ?", f"first_public:{env.ids['lan']}")[0][0] == 0


# ---------------------------------------------------------------------------- xoá, dùng lại id, lỗi


async def test_deleted_or_reused_card_and_settle_failure_never_500(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    clk = Clock(monkeypatch)
    async with coin_env(tmp_path, ("havy", "lan")) as env:
        havy, lan = env.clients["havy"], env.clients["lan"]
        fillers(env, 99, 1)
        x = await _public_card(havy)
        give_players(env, x, 12)
        compute(env)
        paid = rank_rows(env, "havy")
        assert len(paid) == 3
        # Xoá X: bậc, hàng trên bảng, lúc công khai bị xoá; dòng sổ vẫn còn.
        await ok(await havy.delete(f"/api/cards/{x}"))
        for table in ("creator_rank_tiers", "hot_board", "card_public_since"):
            assert env.rows(f"SELECT COUNT(*) FROM {table} WHERE card_id = ?", x)[0][0] == 0, table
        assert [r["id"] for r in rank_rows(env, "havy")] == [r["id"] for r in paid]

        # Id X được dùng lại cho nhân vật mới của người khác: khoá `rank:<X>:<N>:<uid>`, không IdemConflict.
        y = await _public_card(lan, "Nhân vật mới")
        assert y == x
        uid = env.rows("SELECT uid FROM character_cards WHERE id = ?", y)[0][0]
        give_players(env, y, 12)
        compute(env)
        assert _keys(rank_rows(env, "lan")) == [
            (f"rank:{y}:100:{uid}", 100), (f"rank:{y}:50:{uid}", 200), (f"rank:{y}:10:{uid}", 300),
        ]

        # Trả thưởng lỗi lúc tính bảng: GET /api/explore/hot và checkin vẫn 200, bảng vẫn cập nhật, thưởng chờ.
        settle, rank_cards = hot.settle_rewards, hot.rank_cards
        z = await _public_card(havy, f"{NAME} 3")
        give_players(env, z, 12)
        clk.days(8)
        for exc in (sqlite3.OperationalError("database is locked"), IdemConflict("rank:x:10")):

            def broken(*_a: Any, exc: Exception = exc, **_k: Any) -> Any:
                raise exc

            monkeypatch.setattr(hot, "settle_rewards", broken)
            clk.minutes(61)
            board = await ok(await lan.get("/api/explore/hot"))
            assert any(it["card_id"] == z for it in board["items"])
            clk.minutes(61)
            await ok(await havy.post("/api/coins/checkin"))
            # Bậc vẫn được ghi (ngoài phần trả); chỉ phần trả lỗi nên bậc chờ lần tính sau.
            assert tiers(env, z) == {100: "waiting", 50: "waiting", 10: "waiting"}
            assert env.rows("SELECT COUNT(*) FROM coin_ledger WHERE idem_key LIKE ?", f"rank:{z}:%")[0][0] == 0
        # Tính bảng lỗi hẳn: vẫn 200 (bảng cũ).
        monkeypatch.setattr(hot, "rank_cards", lambda *_a, **_k: (_ for _ in ()).throw(sqlite3.OperationalError("x")))
        clk.minutes(61)
        assert (await lan.get("/api/explore/hot")).status_code == 200
        assert (await havy.post("/api/coins/checkin")).status_code == 200
        monkeypatch.setattr(hot, "rank_cards", rank_cards)
        monkeypatch.setattr(hot, "settle_rewards", settle)
        compute(env)
        assert tiers(env, z) == {100: "paid", 50: "paid", 10: "paid"}


async def test_one_failed_reward_never_blocks_other_rewards(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    clk = Clock(monkeypatch)
    async with coin_env(tmp_path, ("havy", "lan")) as env:
        fillers(env, 98, 1)
        hv = make_card(env, "havy", NAME)
        ln = make_card(env, "lan", "Của Lan")
        give_players(env, hv, 12)
        give_players(env, ln, 11)
        # Ghi sổ lỗi cho mọi dòng thưởng của nhân vật havy (bậc và công khai lần đầu); dòng của người khác vẫn ghi được.
        real_post = hot.post

        def flaky(conn: Any, account_id: int, delta: int, kind: str, key: str, **kw: Any) -> Any:
            if account_id == env.ids["havy"]:
                raise sqlite3.OperationalError("database is locked")
            return real_post(conn, account_id, delta, kind, key, **kw)

        monkeypatch.setattr(hot, "post", flaky)
        clk.days(1)  # đủ 24 giờ công khai: cả hai đủ điều kiện +50
        result = compute(env)
        assert {r.card_id for r in result.reached} >= {hv, ln}
        # Bậc của havy được ghi và chờ; lan được trả đủ trong cùng lần tính, cả thưởng công khai lần đầu.
        assert tiers(env, hv) == {100: "waiting", 50: "waiting", 10: "waiting"}
        assert tiers(env, ln) == {100: "paid", 50: "paid", 10: "paid"}
        assert sum(int(r["delta"]) for r in rank_rows(env, "lan")) == 600
        assert env.rows("SELECT COUNT(*) FROM coin_ledger WHERE idem_key = ?", f"first_public:{env.ids['lan']}")[0][0] == 1
        assert rank_rows(env, "havy") == []
        assert env.rows("SELECT COUNT(*) FROM creator_first_public WHERE account_id = ?", env.ids["havy"])[0][0] == 0
        # Hết lỗi: lần tính sau trả phần đang chờ của havy.
        monkeypatch.setattr(hot, "post", real_post)
        clk.minutes(61)
        assert env.app.state.coins.refresh_hot() is not None
        assert tiers(env, hv) == {100: "paid", 50: "paid", 10: "paid"}
        assert sum(int(r["delta"]) for r in rank_rows(env, "havy")) == 600
        assert env.rows("SELECT COUNT(*) FROM coin_ledger WHERE idem_key = ?", f"first_public:{env.ids['havy']}")[0][0] == 1


# ---------------------------------------------------------------------------- người tạo thấy gì, nhật ký, sự kiện


async def test_card_api_history_admin_log_and_event_labels(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    clk = Clock(monkeypatch)
    async with coin_env(tmp_path, ("havy", "lan")) as env:
        havy, lan, owner = env.clients["havy"], env.clients["lan"], env.clients["owner"]
        x = await _public_card(havy)
        private = await _public_card(havy, "Riêng của Vy", visibility="private")

        mine = await ok(await havy.get(f"/api/cards/{x}"))
        assert mine["creator"] == {
            "players": 0, "rank": None, "next_tier": 100, "next_reward": 100, "waiting_coins": 0, "board_creators": 0,
        }
        assert (await ok(await havy.get(f"/api/cards/{private}"))).get("creator") is None
        assert (await lan.get(f"/api/cards/{x}")).status_code == 404
        assert "creator" not in await ok(await lan.get(f"/api/cards/{x}/public"))
        assert all("creator" not in c for c in await ok(await lan.get("/api/public-cards")))

        # X hạng 1 trên bảng chỉ có nhân vật của 1 người tạo: bậc tiếp theo theo hạng là top 10 (+300), chưa trả vì
        # bảng mới có 1 người tạo (`board_creators`).
        give_players(env, x, 10)
        compute(env)
        assert rank_of(env, x) == 1 and tiers(env, x) == {}
        assert (await ok(await havy.get(f"/api/cards/{x}")))["creator"] == {
            "players": 10, "rank": 1, "next_tier": 10, "next_reward": 300, "waiting_coins": 0, "board_creators": 1,
        }

        # X hạng 60 trong bảng 100 người tạo: đã nhận top 100 → bậc tiếp theo top 50 (+200).
        above = fillers(env, 59, 12, tag="a")
        give_players(env, x, 10)
        fillers(env, 40, 1, tag="b")
        compute(env)
        assert rank_of(env, x) == 60
        assert (await ok(await havy.get(f"/api/cards/{x}")))["creator"] == {
            "players": 10, "rank": 60, "next_tier": 50, "next_reward": 200, "waiting_coins": 0, "board_creators": 100,
        }
        # X lên hạng 7: đạt đủ ba bậc.
        drop_players(env, x, 0)
        give_players(env, x, 12)
        for card in above[6:]:
            drop_players(env, card, 1)  # 53 nhân vật tụt xuống 1 người chơi: bảng vẫn 100 nhân vật
        compute(env)
        assert rank_of(env, x) == 7
        saved = await ok(await havy.put(f"/api/cards/{x}", json={**env.repo.get_card(x, account_id=env.ids["havy"]).model_dump()}))
        assert saved["creator"] == {
            "players": 12, "rank": 7, "next_tier": None, "next_reward": None, "waiting_coins": 0, "board_creators": 100,
        }

        # Thưởng công khai lần đầu (đủ 24 giờ, có người chơi).
        clk.days(1)
        await ok(await havy.post("/api/coins/checkin"))
        labels = [(i["label"], i["delta"]) for i in (await ok(await havy.get("/api/coins/history")))["items"]
                  if i["kind"] == "creator_milestone"]
        assert (f"{NAME} vào top 10 Nhân vật hot", 300) in labels
        assert (f"{NAME} vào top 50 Nhân vật hot", 200) in labels
        assert (f"{NAME} vào top 100 Nhân vật hot", 100) in labels
        assert ("Thưởng công khai nhân vật lần đầu", 50) in labels
        # Người tạo "lấp chỗ" cũng được thưởng: nhật ký 50 dòng mới nhất không đủ chỗ, đọc hết rồi lọc theo @havy.
        monkeypatch.setattr(topup, "LOG_LIMIT", 10_000)
        log = (await ok(await owner.get("/api/admin/coins/log")))["items"]
        titles = {i["label"] for i in log if i["kind"] == "creator_milestone" and i["handle"] == "havy"}
        assert titles == {"Thưởng xếp hạng top 10", "Thưởng xếp hạng top 50", "Thưởng xếp hạng top 100", "Thưởng công khai lần đầu"}

        # Chủ máy: không có coin hứa hẹn.
        o = make_card(env, "owner", "Nhân vật của chủ máy")
        assert (await ok(await owner.get(f"/api/cards/{o}")))["creator"] == {
            "players": 0, "rank": None, "next_tier": 100, "next_reward": None, "waiting_coins": 0, "board_creators": 100,
        }

        # Sự kiện: creator_rank_reached {tier, paid}, coins_granted creator_rank / creator_first_public.
        # Sự kiện của server không gắn tài khoản; người tạo "lấp chỗ" cũng có sự kiện: mỗi bậc ghi đúng một sự kiện, mỗi
        # dòng sổ thưởng xếp hạng đúng một `coins_granted` cùng số coin.
        reached = _events(env, "creator_rank_reached")
        assert len(reached) == env.rows("SELECT COUNT(*) FROM creator_rank_tiers")[0][0]
        assert {"tier": 100, "paid": True} in reached and {"tier": 50, "paid": True} in reached
        assert {"tier": 10, "paid": True} in reached
        grants = _events(env, "coins_granted")
        assert {"source": "creator_first_public", "amount": 50} in grants
        rank_paid = sorted(int(r[0]) for r in env.rows("SELECT delta FROM coin_ledger WHERE idem_key LIKE 'rank:%'"))
        assert sorted(e["amount"] for e in grants if e["source"] == "creator_rank") == rank_paid
        assert {100, 200, 300} <= set(rank_paid)
        assert events.validate("creator_rank_reached", {"tier": 50, "paid": False}, source="server")
        for bad in ({"tier": 20, "paid": True}, {"tier": 10, "paid": "yes"}, {"tier": 10},
                    {"tier": 10, "paid": True, "name": "Hạ Vy"}):
            with pytest.raises(EventRejected):
                events.validate("creator_rank_reached", bad, source="server")
        with pytest.raises(EventRejected):
            events.validate("creator_rank_reached", {"tier": 10, "paid": True}, source="client")
        assert "creator_milestone_reached" not in events.EVENTS
