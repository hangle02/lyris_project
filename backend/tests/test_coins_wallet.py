"""F42 (docs/coins.md §1–§3.4): migration 0012, sổ coin chỉ thêm, ví của mọi thành viên, quà tạo tài khoản và quà
đăng nhập trong ngày (giờ Việt Nam), chủ máy không giới hạn, `LYRIS_COINS=0`."""
from __future__ import annotations

import random
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from lyris.auth import clock, store
from lyris.coins import holds, ledger
from lyris.coins.errors import CoinsRequired, IdemConflict, InsufficientCoins
from lyris.coins.wallet import CoinService
from lyris.compliance import legal
from lyris.config import get_settings
from lyris.db.connection import connect, migrate
from lyris.db.repo import Repo, new_uid
from tests.authutil import MEMBER_PASSWORD, anon_client
from tests.coinutil import coin_env, names, new_story, studio_chat_body


def _db() -> sqlite3.Connection:
    conn = connect(":memory:")
    migrate(conn)
    return conn


def _member(conn: sqlite3.Connection, handle: str) -> int:
    with ledger.atomic(conn):
        return store.insert_member(conn, uid=new_uid(), handle=handle, display_name=handle.title(), invited_by=None)


def _sum(conn: sqlite3.Connection, account_id: int) -> int:
    return int(conn.execute("SELECT COALESCE(SUM(delta), 0) FROM coin_ledger WHERE account_id = ?", (account_id,)).fetchone()[0])


async def _signup(app: object, owner_client: object, handle: str) -> int:
    invite = await owner_client.post("/api/admin/invites", json={"note": handle})  # type: ignore[attr-defined]
    assert invite.status_code == 200, invite.text
    body = {
        "invite_code": invite.json()["code"], "handle": handle, "display_name": handle.title(),
        "password": MEMBER_PASSWORD, "accept_terms": True, "terms_version": legal.LEGAL_VERSION,
    }
    async with anon_client(app) as c:  # type: ignore[arg-type]
        resp = await c.post("/api/auth/signup", json=body)
    assert resp.status_code == 200, resp.text
    return int(resp.json()["account"]["id"])


# ---------------------------------------------------------------------------- migration và sổ


def test_migration_0012_ledger_append_only_and_balance_matches_sum() -> None:
    conn = _db()
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert {"coin_wallets", "coin_ledger", "coin_holds"} <= tables
    a, b = _member(conn, "mai"), _member(conn, "lan")
    row_id = conn.execute("SELECT id FROM coin_ledger WHERE account_id = ?", (a,)).fetchone()[0]
    for sql in (
        "UPDATE coin_ledger SET delta = 1 WHERE id = ?",
        "UPDATE coin_ledger SET actor_id = 5 WHERE id = ?",
        "UPDATE coin_ledger SET reason = 'sửa' WHERE id = ?",
    ):
        with pytest.raises(sqlite3.DatabaseError, match="chỉ thêm"):
            conn.execute(sql, (row_id,))
    conn.execute("UPDATE coin_ledger SET actor_id = NULL WHERE id = ?", (row_id,))  # đúng việc ON DELETE SET NULL làm

    rng = random.Random(20261114)
    open_hold: dict[int, int | None] = {a: None, b: None}
    for step in range(200):
        who = rng.choice((a, b))
        op = rng.choice(("grant", "spend", "hold", "settle", "settle"))
        if op == "grant":
            ledger.post(conn, who, rng.randint(1, 40), "mission", f"t:{step}", mission="ad")
        elif op == "spend":
            try:
                ledger.post(conn, who, -rng.randint(1, 400), "admin_adjust", f"t:{step}", reason="x")
            except InsufficientCoins:
                pass
        elif op == "hold" and open_hold[who] is None:
            try:
                open_hold[who] = holds.open_hold(
                    conn, who, story_id=None, char_key=None, origin_card_id=None, mode="test", kind="send", amount=6
                )
            except CoinsRequired:
                pass
        elif op == "settle" and open_hold[who] is not None:
            hold_id = open_hold[who]
            assert hold_id is not None
            if rng.random() < 0.5:
                assert holds.charge_hold(conn, hold_id, message_id=None, story_id=None, card_id=None) is not None
            else:
                assert holds.release_hold(conn, hold_id, "error")
            open_hold[who] = None
        for acc in (a, b):
            bal = ledger.balance(conn, acc)
            assert bal == _sum(conn, acc) and bal >= 0
            assert bal - ledger.held(conn, acc) >= 0
    assert conn.execute("SELECT COUNT(*) FROM coin_ledger WHERE kind = 'chat'").fetchone()[0] > 0


def test_ledger_rows_cannot_be_deleted_only_cascade_with_account() -> None:
    """Sổ chỉ thêm cũng chặn DELETE (migration 0013): xoá thẳng một dòng sổ bị chặn, số dư vẫn bằng tổng sổ; xoá
    tài khoản (ON DELETE CASCADE) vẫn xoá được mọi dòng của tài khoản đó."""
    conn = _db()
    a, b = _member(conn, "mai"), _member(conn, "lan")
    for sql, params in (
        ("DELETE FROM coin_ledger WHERE account_id = ?", (a,)),
        ("DELETE FROM coin_ledger", ()),
    ):
        with pytest.raises(sqlite3.DatabaseError, match="chỉ thêm"):
            conn.execute(sql, params)
    assert ledger.balance(conn, a) == _sum(conn, a) == 300
    conn.execute("DELETE FROM accounts WHERE id = ?", (a,))
    assert conn.execute("SELECT COUNT(*) FROM coin_ledger WHERE account_id = ?", (a,)).fetchone()[0] == 0
    assert ledger.balance(conn, b) == _sum(conn, b) == 300


def test_idem_key_never_posts_twice_conflict_on_other_payload() -> None:
    conn = _db()
    a = _member(conn, "mai")
    first = ledger.post(conn, a, 25, "mission", "mission:x", mission="ad")
    again = ledger.post(conn, a, 25, "mission", "mission:x", mission="ad")
    assert first.created and not again.created and again.id == first.id
    assert ledger.balance(conn, a) == 325 == _sum(conn, a)
    with pytest.raises(IdemConflict):
        ledger.post(conn, a, 30, "mission", "mission:x", mission="ad")
    with pytest.raises(IdemConflict):
        ledger.post(conn, a, 25, "topup_code", "mission:x")
    assert ledger.balance(conn, a) == 325
    assert conn.execute("SELECT COUNT(*) FROM coin_ledger WHERE idem_key = 'mission:x'").fetchone()[0] == 1


# ---------------------------------------------------------------------------- ví của mọi thành viên


async def test_every_member_creation_path_opens_wallet_with_300(tmp_path: Path) -> None:
    for coins_on in (True, False):
        async with coin_env(tmp_path / str(coins_on), (), coins=coins_on) as env:
            via_signup = await _signup(env.app, env.clients["owner"], "moi")
            with env.repo.transaction():
                direct = store.insert_member(env.repo.conn, uid=new_uid(), handle="thang", display_name="Thắng", invited_by=None)
            for acc in (via_signup, direct):
                wallets = env.rows("SELECT balance FROM coin_wallets WHERE account_id = ?", acc)
                grants = env.rows("SELECT delta, kind, idem_key FROM coin_ledger WHERE account_id = ?", acc)
                assert [tuple(w) for w in wallets] == [(300,)], coins_on
                assert [tuple(g) for g in grants] == [(300, "signup_grant", f"signup:{acc}")], coins_on


def test_missing_wallet_is_created_not_error() -> None:
    conn = _db()
    conn.execute("INSERT INTO accounts (uid, handle, display_name, role) VALUES ('u-x', 'cu', 'Cũ', 'member')")
    acc = int(conn.execute("SELECT id FROM accounts WHERE handle = 'cu'").fetchone()[0])
    assert not ledger.has_wallet(conn, acc)
    entry = ledger.post(conn, acc, 10, "mission", "m:1", mission="ad")
    assert entry.balance_after == 10 and ledger.balance(conn, acc) == 10
    conn.execute("INSERT INTO accounts (uid, handle, display_name, role) VALUES ('u-y', 'cu2', 'Cũ 2', 'member')")
    acc2 = int(conn.execute("SELECT id FROM accounts WHERE handle = 'cu2'").fetchone()[0])
    with pytest.raises(CoinsRequired):  # không có ví: số dư 0, chỉ là không đủ coin (không lỗi khác)
        holds.open_hold(conn, acc2, story_id=None, char_key=None, origin_card_id=None, mode="test", kind="send", amount=6)
    wallet = CoinService(Repo(conn)).wallet(acc2)
    assert wallet["balance"] == 0 and wallet["available"] == 0 and wallet["unlimited"] is False
    assert ledger.has_wallet(conn, acc2) and ledger.balance(conn, acc2) == 0


async def test_signup_grants_300_once_owner_gets_nothing(tmp_path: Path) -> None:
    async with coin_env(tmp_path, ()) as env:
        acc = await _signup(env.app, env.clients["owner"], "moi")
        with env.repo.transaction():
            again = ledger.open_wallet(env.repo.conn, acc)
        assert not again.created
        assert [tuple(r) for r in env.rows("SELECT delta FROM coin_ledger WHERE account_id = ?", acc)] == [(300,)]
        owner = env.clients["owner"]
        story = await new_story(owner)
        assert names((await owner.post(f"/api/stories/{story}/messages", json={"content": "Chào."})).text)[-1] == "done"
        checkin = await owner.post("/api/coins/checkin")
        assert checkin.status_code == 200 and checkin.json()["granted"] is False
        assert env.ledger("owner") == [] and env.holds("owner") == []
        assert env.rows("SELECT * FROM coin_wallets WHERE account_id = ?", env.ids["owner"]) == []


def test_existing_members_get_backfill_grant() -> None:
    conn = connect(":memory:")
    assert migrate(conn, target=11) == 11
    repo = Repo(conn)
    owner = repo.owner_account().id
    conn.execute("INSERT INTO accounts (uid, handle, display_name, role) VALUES ('u-1', 'mai', 'Mai', 'member')")
    conn.execute("INSERT INTO accounts (uid, handle, display_name, role) VALUES ('u-2', 'lan', 'Lan', 'member')")
    assert migrate(conn) == 14
    members = [int(r[0]) for r in conn.execute("SELECT id FROM accounts WHERE role = 'member' ORDER BY id")]
    for acc in members:
        assert ledger.balance(conn, acc) == 300
        rows = conn.execute("SELECT delta, balance_after, kind, idem_key FROM coin_ledger WHERE account_id = ?", (acc,)).fetchall()
        assert [tuple(r) for r in rows] == [(300, 300, "backfill_grant", f"backfill:{acc}")]
    assert conn.execute("SELECT COUNT(*) FROM coin_ledger WHERE account_id = ?", (owner,)).fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM coin_wallets WHERE account_id = ?", (owner,)).fetchone()[0] == 0
    assert migrate(conn) == 14  # chạy lại không cộng lần hai
    assert conn.execute("SELECT COUNT(*) FROM coin_ledger").fetchone()[0] == len(members)


# ---------------------------------------------------------------------------- quà đăng nhập trong ngày


def _at(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=timezone.utc)


async def test_daily_checkin_once_per_vietnam_day(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    now = {"t": _at("2026-11-14T16:59:00")}
    monkeypatch.setattr(clock, "now", lambda: now["t"])
    async with coin_env(tmp_path, ("mai",)) as env:
        mai = env.clients["mai"]
        first = (await mai.post("/api/coins/checkin")).json()
        assert first["granted"] is True and first["amount"] == 60 and first["coin_day"] == "2026-11-14"
        again = (await mai.post("/api/coins/checkin")).json()
        assert again["granted"] is False and again["amount"] == 0 and again["wallet"]["balance"] == 360
        now["t"] = _at("2026-11-14T17:00:00")  # cùng ngày UTC, nhưng đã sang 15/11 giờ Việt Nam
        second = (await mai.post("/api/coins/checkin")).json()
        assert second["granted"] is True and second["coin_day"] == "2026-11-15"
        assert second["wallet"]["balance"] == 420
        assert [r["idem_key"] for r in env.ledger("mai", "daily_login")] == [
            f"daily:{env.ids['mai']}:2026-11-14", f"daily:{env.ids['mai']}:2026-11-15"
        ]
        async with anon_client(env.app) as c:
            login = await c.post("/api/auth/login", json={"handle": "mai", "password": MEMBER_PASSWORD})
            assert login.status_code == 200, login.text
            assert (await c.post("/api/coins/checkin")).json()["granted"] is False
        assert len(env.ledger("mai", "daily_login")) == 2 and env.balance("mai") == 420
        now["t"] = _at("2026-11-15T18:00:00")  # 16/11 giờ Việt Nam: đăng nhập bằng mật khẩu cũng là mở app trong ngày
        async with anon_client(env.app) as c:
            assert (await c.post("/api/auth/login", json={"handle": "mai", "password": MEMBER_PASSWORD})).status_code == 200
            after = (await c.post("/api/coins/checkin")).json()
            assert after["granted"] is False and after["today"] == 60
        assert len(env.ledger("mai", "daily_login")) == 3 and env.balance("mai") == 480


async def test_first_day_is_300_plus_60(tmp_path: Path) -> None:
    async with coin_env(tmp_path, ()) as env:
        invite = await env.clients["owner"].post("/api/admin/invites", json={"note": "moi"})
        body = {
            "invite_code": invite.json()["code"], "handle": "moi", "display_name": "Mới", "password": MEMBER_PASSWORD,
            "accept_terms": True, "terms_version": legal.LEGAL_VERSION,
        }
        async with anon_client(env.app) as c:
            assert (await c.post("/api/auth/signup", json=body)).status_code == 200
            checkin = (await c.post("/api/coins/checkin")).json()
            assert checkin["granted"] is True
            assert checkin["wallet"]["balance"] == 360
            wallet = (await c.get("/api/coins/wallet")).json()
        assert wallet == {"balance": 360, "available": 360, "unlimited": False, "price_per_reply": 6, "enabled": True}


# ---------------------------------------------------------------------------- chủ máy, LYRIS_COINS=0


async def test_owner_unlimited_and_coins_off_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async with coin_env(tmp_path / "on", ("mai",)) as env:
        owner = env.clients["owner"]
        story = await new_story(owner)
        body = await studio_chat_body(owner)
        for i in range(10):
            assert names((await owner.post(f"/api/stories/{story}/messages", json={"content": f"Lượt {i}."})).text)[-1] == "done"
            assert names((await owner.post("/api/cards/test-chat", json=body)).text)[-1] == "done"
        assert env.holds("owner") == [] and env.ledger("owner") == []
        wallet = (await owner.get("/api/coins/wallet")).json()
        assert wallet["unlimited"] is True and wallet["enabled"] is True
    async with coin_env(tmp_path / "off", ("mai",), coins=False) as env:
        mai = env.clients["mai"]
        story = await new_story(mai)
        for i in range(3):
            assert names((await mai.post(f"/api/stories/{story}/messages", json={"content": f"Lượt {i}."})).text)[-1] == "done"
        assert env.balance("mai") == 300 and env.holds("mai") == [] and env.ledger("mai", "chat") == []
        wallet = (await mai.get("/api/coins/wallet")).json()
        assert wallet["enabled"] is False
    for name in ("LYRIS_COINS", "NORA_COINS"):
        monkeypatch.delenv(name, raising=False)
    assert get_settings().coins_enabled is True
    monkeypatch.setenv("NORA_COINS", "0")
    assert get_settings().coins_enabled is False
    monkeypatch.setenv("LYRIS_COINS", "1")
    assert get_settings().coins_enabled is True
    monkeypatch.setenv("LYRIS_COINS", "0")
    assert get_settings().coins_enabled is False
