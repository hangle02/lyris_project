"""F46 (docs/coins.md §2.2, §5.2): bảng "Nhân vật hot".

Hot = tổng người chơi từ trước tới nay (PO 2C). Chỉ nhân vật gốc đang công khai, người tạo active, ≥ 1 người chơi; thứ tự
người chơi giảm dần, rồi `MAX(qualified_at)`, rồi `card_id`; lưu 100 hạng đầu; tính lại khi lần tính cuối cũ hơn 60 phút.
"""
from __future__ import annotations

import re
import sqlite3
import threading
from pathlib import Path
from typing import Any

import pytest

from lyris.auth import clock
from lyris.coins import hot
from lyris.db.connection import connect, migrate
from lyris.db.repo import Repo
from lyris.seed import load_seed_card
from tests.authutil import client_for
from tests.coinutil import coin_env
from tests.hotutil import Clock, compute, fillers, give_players, make_card, ok, rank_of

MIGRATION = Path(__file__).resolve().parents[1] / "lyris" / "db" / "migrations" / "0014_hot_board.sql"


def _board(env: Any) -> list[tuple[int, int, int]]:
    return [(int(r[0]), int(r[1]), int(r[2])) for r in env.rows("SELECT rank, card_id, players FROM hot_board ORDER BY rank")]


async def test_rank_orders_by_players_then_reach_time_then_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    Clock(monkeypatch)
    async with coin_env(tmp_path, ("havy", "lan")) as env:
        a = make_card(env, "havy", "A")
        b = make_card(env, "havy", "B")
        c = make_card(env, "lan", "C")
        d = make_card(env, "lan", "D")
        e = make_card(env, "havy", "E")
        give_players(env, a, 3, when="2026-11-10T00:00:00.000Z")
        give_players(env, b, 5, when="2026-11-12T00:00:00.000Z")  # cùng 5 người chơi với C, đạt muộn hơn
        give_players(env, c, 5, when="2026-11-11T00:00:00.000Z")
        give_players(env, d, 5, when="2026-11-12T00:00:00.000Z")  # bằng B cả số lẫn lúc đạt: id nhỏ hơn trước
        give_players(env, e, 7, when="2026-11-13T00:00:00.000Z")
        # Một người chơi của B đạt sớm hơn: MAX(qualified_at) của B vẫn là lúc người chơi thứ 5 đạt.
        with env.repo.transaction():
            env.repo.conn.execute(
                "UPDATE creator_players SET qualified_at = '2026-11-01T00:00:00.000Z' WHERE card_id = ? AND player_id ="
                " (SELECT MIN(player_id) FROM creator_players WHERE card_id = ?)", (b, b),
            )
        with env.repo.locked() as conn:
            top, ranked = hot.rank_cards(conn)
        assert ranked == 5
        assert [(r.rank, r.card_id, r.players) for r in top] == [
            (1, e, 7), (2, c, 5), (3, b, 5), (4, d, 5), (5, a, 3),
        ]
        assert b < d
        compute(env)
        assert _board(env) == [(1, e, 7), (2, c, 5), (3, b, 5), (4, d, 5), (5, a, 3)]
        ranks = [r for r, _, _ in _board(env)]
        assert ranks == list(range(1, 6)) and len(set(ranks)) == len(ranks)


async def test_board_only_public_active_with_player_top_100(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    Clock(monkeypatch)
    async with coin_env(tmp_path, ("havy", "lan", "khoa")) as env:
        owner = env.clients["owner"]
        shown = make_card(env, "havy", "Công khai")
        private = make_card(env, "havy", "Riêng tư", visibility="private")
        nobody = make_card(env, "havy", "Không ai chơi")
        disabled = make_card(env, "khoa", "Của người bị khoá")
        give_players(env, shown, 2)
        give_players(env, private, 4)
        give_players(env, disabled, 4)
        # Bản sao (story_copy = 1) của nhân vật công khai: lan bắt đầu một story với nó.
        lan = env.clients["lan"]
        await ok(await lan.post("/api/personas", json={"name": "Lan", "gender": "female"}))
        story = await ok(await lan.post("/api/stories", json={"card_id": shown}))
        copy = env.rows("SELECT card_id FROM stories WHERE id = ?", story["id"])[0][0]
        assert env.rows("SELECT story_copy FROM character_cards WHERE id = ?", copy)[0][0] == 1
        with env.repo.transaction():
            env.repo.conn.execute(
                "INSERT INTO creator_players (card_id, player_id, creator_id, qualified_at) VALUES (?, ?, ?, ?)",
                (copy, env.ids["havy"], env.ids["lan"], clock.iso(clock.now())),
            )
        await ok(await owner.post(f"/api/admin/accounts/{env.ids['khoa']}/disable"))
        # Nhân vật mẫu đã cài (riêng tư, không bao giờ công khai được).
        installed = await ok(await env.clients["havy"].post("/api/templates/ha-vy/install"))
        template_card = int(installed["id"])
        give_players(env, template_card, 6)

        compute(env)
        assert _board(env) == [(1, shown, 2)]
        assert env.rows("SELECT ranked FROM hot_board_runs")[0][0] == 1
        for card in (private, nobody, disabled, copy, template_card):
            assert rank_of(env, card) is None, card

        # 130 nhân vật đủ điều kiện: lưu đúng 100 hạng (1–100), ranked = 130 + 1.
        fillers(env, 130, 1)
        compute(env)
        rows = _board(env)
        assert len(rows) == 100 and [r for r, _, _ in rows] == list(range(1, 101))
        assert env.rows("SELECT ranked FROM hot_board_runs")[0][0] == 131
        assert env.rows("SELECT COUNT(*) FROM hot_board_runs")[0][0] == 1
        assert rows[0] == (1, shown, 2)


async def test_disabled_players_never_count_on_board_or_bonus(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    clk = Clock(monkeypatch)
    async with coin_env(tmp_path, ("havy", "lan")) as env:
        owner = env.clients["owner"]
        x = make_card(env, "havy", "X")
        y = make_card(env, "lan", "Y")
        give_players(env, x, 5)
        give_players(env, y, 1)  # người chơi duy nhất của Y cũng là người chơi đầu tiên của X
        players = [int(r[0]) for r in env.rows("SELECT player_id FROM creator_players WHERE card_id = ? ORDER BY player_id", x)]
        # Chủ máy tạm khoá 2 người chơi (kể cả người chơi duy nhất của Y).
        for p in players[:2]:
            await ok(await owner.post(f"/api/admin/accounts/{p}/disable"))
        clk.days(1)  # X và Y đã công khai đủ 24 giờ
        result = compute(env)
        assert _board(env) == [(1, x, 3)]
        assert (result.ranked, result.creators) == (1, 1)
        assert rank_of(env, y) is None
        with env.repo.locked() as conn:
            assert hot.progress(conn, x)["players"] == 3
            assert hot.progress(conn, y)["players"] == 0
        # Y không có người chơi đang hoạt động: lan không có thưởng công khai lần đầu; havy (X có 3) thì có.
        assert env.rows("SELECT COUNT(*) FROM coin_ledger WHERE idem_key = ?", f"first_public:{env.ids['lan']}")[0][0] == 0
        assert env.rows("SELECT COUNT(*) FROM coin_ledger WHERE idem_key = ?", f"first_public:{env.ids['havy']}")[0][0] == 1
        # Mở khoá lại: được đếm lại ở lần tính sau.
        for p in players[:2]:
            await ok(await owner.post(f"/api/admin/accounts/{p}/enable"))
        clk.minutes(61)
        compute(env)
        assert _board(env) == [(1, x, 5), (2, y, 1)]
        assert env.rows("SELECT COUNT(*) FROM coin_ledger WHERE idem_key = ?", f"first_public:{env.ids['lan']}")[0][0] == 1


async def test_fresh_board_read_takes_no_write_lock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    clk = Clock(monkeypatch)
    async with coin_env(tmp_path, ("havy",)) as env:
        coins = env.app.state.coins
        x = make_card(env, "havy", "X")
        give_players(env, x, 1)
        seen: list[str] = []
        env.repo.conn.set_trace_callback(seen.append)
        try:
            # Bảng chưa có: lần đọc đầu tính bảng (có transaction ghi).
            assert [it["card_id"] for it in coins.hot_board(100)["items"]] == [x]
            assert any(s.strip().upper().startswith("BEGIN") for s in seen)
            # Bảng còn mới (59 phút): đọc không mở transaction ghi nào.
            clk.minutes(59)
            seen.clear()
            assert [it["card_id"] for it in coins.hot_board(100)["items"]] == [x]
            assert coins.refresh_hot() is None
            assert not [s for s in seen if s.strip().upper().startswith(("BEGIN", "SAVEPOINT", "INSERT", "DELETE", "UPDATE"))], seen
            # Cũ (61 phút): tính lại.
            clk.minutes(2)
            seen.clear()
            assert coins.refresh_hot() is not None
            assert any(s.strip().upper().startswith("BEGIN") for s in seen)
        finally:
            env.repo.conn.set_trace_callback(None)


def _race(fns: list[Any]) -> list[Any]:
    barrier = threading.Barrier(len(fns))
    out: list[Any] = [None] * len(fns)

    def run(i: int) -> None:
        barrier.wait()
        try:
            out[i] = fns[i]()
        except Exception as exc:  # noqa: BLE001 - trả lỗi về cho test xem
            out[i] = exc

    threads = [threading.Thread(target=run, args=(i,)) for i in range(len(fns))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return out


async def test_refresh_if_stale_once_per_hour(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    clk = Clock(monkeypatch)
    async with coin_env(tmp_path, ("havy",)) as env:
        x = make_card(env, "havy", "X")
        give_players(env, x, 1)
        with env.repo.transaction():
            first = hot.refresh_if_stale(env.repo.conn)
        assert first is not None
        computed = env.rows("SELECT id, computed_at FROM hot_board_runs")
        assert [tuple(r) for r in computed] == [(computed[0][0], clock.iso(clk.t))]
        # 59 phút sau: không tính lại.
        clk.minutes(59)
        with env.repo.transaction():
            assert hot.refresh_if_stale(env.repo.conn) is None
        assert [tuple(r) for r in env.rows("SELECT id, computed_at FROM hot_board_runs")] == [tuple(computed[0])]
        # 61 phút sau lần tính: tính lại, chỉ còn một dòng hot_board_runs.
        clk.minutes(2)
        with env.repo.transaction():
            assert hot.refresh_if_stale(env.repo.conn) is not None
        runs = env.rows("SELECT computed_at FROM hot_board_runs")
        assert [r[0] for r in runs] == [clock.iso(clk.t)]

        # Hai lời gọi cùng lúc (hai kết nối, hai luồng) khi bảng đã cũ: chỉ một lần tính.
        clk.minutes(61)
        db = tmp_path / "lyris.db"
        conns = [connect(db), connect(db)]
        try:
            results = _race([lambda c=c: hot.refresh_if_stale(c, clk.t) for c in conns])
        finally:
            for c in conns:
                c.close()
        assert not any(isinstance(r, Exception) for r in results), results
        assert sum(1 for r in results if r is not None) == 1
        assert env.rows("SELECT COUNT(*) FROM hot_board_runs")[0][0] == 1
        # Đã tính lại bằng hai kết nối kia: id lần tính tăng đúng một.
        assert env.rows("SELECT computed_at FROM hot_board_runs")[0][0] == clock.iso(clk.t)


async def test_hot_api_shape_limit_and_hides_private(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    clk = Clock(monkeypatch)
    async with coin_env(tmp_path, ("havy", "lan")) as env:
        havy, lan = env.clients["havy"], env.clients["lan"]
        cards = []
        for i in range(5):
            card = make_card(env, "havy", f"Nhân vật {i}")
            give_players(env, card, 5 - i)
            cards.append(card)
        body = await ok(await lan.get("/api/explore/hot"))
        assert set(body) == {"updated_at", "ranked", "items"}
        assert body["updated_at"] == clock.iso(clk.t) and body["ranked"] == 5
        assert [it["rank"] for it in body["items"]] == [1, 2, 3, 4, 5]
        assert [it["card_id"] for it in body["items"]] == cards
        for it in body["items"]:
            assert set(it) == {"rank", "card_id", "name", "avatar_url", "creator_handle", "players"}
        top = body["items"][0]
        assert (top["name"], top["creator_handle"], top["players"]) == ("Nhân vật 0", "havy", 5)
        flat = repr(body)
        for secret in ("account_id", "description", "secrets", "personality", "Lạc Dương"):
            assert secret not in flat, secret

        three = await ok(await lan.get("/api/explore/hot", params={"limit": 3}))
        assert [it["rank"] for it in three["items"]] == [1, 2, 3]
        for bad in (0, 101, -1):
            assert (await lan.get("/api/explore/hot", params={"limit": bad})).status_code == 422, bad

        # Nhân vật hạng 2 về Riêng tư sau lần tính: không còn trong items, hạng của nhân vật khác giữ nguyên.
        card = env.repo.get_card(cards[1], account_id=env.ids["havy"])
        await ok(await havy.put(f"/api/cards/{cards[1]}", json={**card.model_dump(), "visibility": "private"}))
        after = await ok(await lan.get("/api/explore/hot"))
        assert [(it["rank"], it["card_id"]) for it in after["items"]] == [
            (1, cards[0]), (3, cards[2]), (4, cards[3]), (5, cards[4]),
        ]
        assert after["updated_at"] == body["updated_at"]

        # Chưa đăng nhập: 401.
        anon = client_for(env.app, None)
        try:
            assert (await anon.get("/api/explore/hot")).status_code == 401
        finally:
            await anon.aclose()


def _statements(sql: str) -> list[str]:
    no_comments = "\n".join(line.split("--", 1)[0] for line in sql.splitlines())
    return [s.strip() for s in no_comments.split(";") if s.strip()]


def _old_db(path: Path) -> sqlite3.Connection:
    """DB ở migration 0013 có dữ liệu thật: thành viên có ví và sổ, nhân vật công khai và riêng tư."""
    conn = connect(path)
    migrate(conn, target=13)
    repo = Repo(conn)
    from lyris.auth import store

    with repo.transaction():
        owner = repo.owner_id()
        members = [
            store.insert_member(conn, uid=f"u{i}", handle=f"tv{i}", display_name="TV", invited_by=owner) for i in range(3)
        ]
    for i, acc in enumerate(members):
        base = load_seed_card().model_copy(update={"id": None, "uid": None, "name": f"NV {i}"})
        repo.create_card(base.model_copy(update={"visibility": "public"}), account_id=acc)
        repo.create_card(base.model_copy(update={"visibility": "private", "name": f"Riêng {i}"}), account_id=acc)
    return conn


def test_migration_0014_is_additive(tmp_path: Path) -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    statements = _statements(sql)
    assert statements, "migration rỗng"
    for stmt in statements:
        head = " ".join(stmt.split()[:3]).upper()
        assert head.startswith(("CREATE TABLE", "CREATE INDEX", "INSERT INTO CARD_PUBLIC_SINCE")), stmt[:60]
        assert not re.search(r"\b(ALTER|DROP|UPDATE)\b", stmt, flags=re.I), stmt[:60]
        assert not re.search(r"\bDELETE\s+FROM\b", stmt, flags=re.I), stmt[:60]
        if not head.startswith("INSERT"):
            assert not re.search(r"\bINSERT\b", stmt, flags=re.I), stmt[:60]

    conn = _old_db(tmp_path / "v13.db")
    try:
        def snapshot() -> dict[str, Any]:
            return {
                t: conn.execute(f"SELECT * FROM {t} ORDER BY 1").fetchall()
                for t in ("coin_wallets", "coin_ledger", "character_cards", "accounts")
            }

        before = snapshot()
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 13
        assert migrate(conn) == 14
        after = snapshot()
        assert {t: [tuple(r) for r in rows] for t, rows in after.items()} == {
            t: [tuple(r) for r in rows] for t, rows in before.items()
        }
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        assert {"card_public_since", "hot_board_runs", "hot_board", "creator_rank_tiers", "creator_first_public"} <= tables
        # Nhân vật đang công khai (không phải bản sao) có lúc bật Công khai = lúc áp migration.
        public = {r[0] for r in conn.execute("SELECT id FROM character_cards WHERE visibility = 'public'")}
        assert {r[0] for r in conn.execute("SELECT card_id FROM card_public_since")} == public
        assert len(public) == 3
        assert migrate(conn) == 14  # chạy lại không làm gì
    finally:
        conn.close()
