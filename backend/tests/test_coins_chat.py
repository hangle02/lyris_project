"""F42 (docs/coins.md §3, quyết định giu-cho-coin-truoc-khi-sinh): giữ chỗ 6 coin trước khi sinh, trừ khi có chữ, nhả khi
không có chữ; 402 `coins_required` trước byte SSE đầu tiên; nhả lúc khởi động chỉ trong `lifespan`."""
from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from lyris.api.app import create_app
from lyris.auth import cli as auth_cli
from lyris.chat.service import ChatService
from lyris.coins import holds as holds_mod
from lyris.coins import ledger
from lyris.coins.wallet import CoinService
from lyris.db.connection import connect, migrate
from lyris.db.repo import Repo
from lyris.llm.base import LLMError
from lyris.llm.fake import FakeLLM
from tests.authutil import add_member, ensure_owner_password
from tests.coinutil import REPLY, coin_env, names, new_story, settings, studio_chat_body, until
from tests.test_draft import good_reply
from tests.twoaccounts import parse_sse

COINS_402 = {"code": "coins_required", "detail": "Bạn đã hết coin. Mỗi câu trả lời cần 6 coin."}


def _assert_chat_rows(env: Any, who: str, n: int) -> None:
    rows = env.ledger(who, "chat")
    assert len(rows) == n, [tuple(r) for r in rows]
    for r in rows:
        assert r["delta"] == -6 and r["kind"] == "chat" and r["idem_key"] == f"chat:{r['hold_id']}"


# ---------------------------------------------------------------------------- mỗi câu trả lời có chữ: 6 coin


async def test_each_saved_reply_costs_6_story_dm_retry_regenerate_test_chat(tmp_path: Path) -> None:
    async with coin_env(tmp_path) as env:
        mai = env.clients["mai"]
        spent = 0
        for mode in ("story", "dm"):
            story = await new_story(mai, mode)
            sent = await mai.post(f"/api/stories/{story}/messages", json={"content": "Chào anh."})
            assert names(sent.text)[-1] == "done"
            spent += 6
            assert env.balance("mai") == 300 - spent
            reply_id = [d for n, d in parse_sse(sent.text) if n == "done"][0]["message"]["id"]
            regen = await mai.post(f"/api/messages/{reply_id}/regenerate")
            assert names(regen.text)[-1] == "done"
            spent += 6
            assert env.balance("mai") == 300 - spent
            env.fake.error = LLMError("model hỏng")
            failed = await mai.post(f"/api/stories/{story}/messages", json={"content": "Còn đó không?"})
            assert names(failed.text)[-1] == "error"
            env.fake.error = None
            assert env.balance("mai") == 300 - spent  # lỗi: không mất coin
            retry = await mai.post(f"/api/stories/{story}/reply")
            assert names(retry.text)[-1] == "done"
            spent += 6
            assert env.balance("mai") == 300 - spent
            modes = {r["mode"] for r in env.holds("mai")}
            assert mode in modes
        body = await studio_chat_body(mai)
        tested = await mai.post("/api/cards/test-chat", json=body)
        assert names(tested.text)[-1] == "done"
        spent += 6
        assert env.balance("mai") == 300 - spent
        _assert_chat_rows(env, "mai", 7)
        test_holds = [h for h in env.holds("mai") if h["mode"] == "test"]
        assert len(test_holds) == 1 and test_holds[0]["story_id"] is None and test_holds[0]["status"] == "charged"
        assert test_holds[0]["kind"] == "send"
        kinds = sorted((h["mode"], h["kind"]) for h in env.holds("mai") if h["status"] == "charged")
        assert kinds == sorted(
            [("story", "send"), ("story", "regenerate"), ("story", "retry"),
             ("dm", "send"), ("dm", "regenerate"), ("dm", "retry"), ("test", "send")]
        )
        charged = [h for h in env.holds("mai") if h["status"] == "charged" and h["mode"] != "test"]
        assert all(h["message_id"] is not None for h in charged)


# ---------------------------------------------------------------------------- không có chữ: nhả


async def _released(env: Any, reason: str, *, charged: int = 0) -> None:
    """Giữ chỗ cuối bị nhả đúng lý do, số dư vẫn 300, không có dòng sổ nào ngoài `charged` câu trả lời trước đó."""
    holds = env.holds("mai")
    assert holds[-1]["status"] == "released" and holds[-1]["release_reason"] == reason, [tuple(h) for h in holds]
    assert env.balance("mai") == 300 and len(env.ledger("mai", "chat")) == charged
    assert all(h["status"] != "held" for h in holds)


async def test_no_text_releases_hold(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async with coin_env(tmp_path, ("mai", "lan"), slots=1) as env:
        mai = env.clients["mai"]
        story = await new_story(mai)
        # lỗi model
        env.fake.error = LLMError("model hỏng")
        assert names((await mai.post(f"/api/stories/{story}/messages", json={"content": "Một."})).text)[-1] == "error"
        env.fake.error = None
        await _released(env, "error")
        # câu trả lời rỗng
        env.fake.replies, env.fake._next = ["   "], 0
        assert names((await mai.post(f"/api/stories/{story}/reply")).text)[-1] == "error"
        await _released(env, "empty")
        env.fake.replies, env.fake._next = [REPLY], 0
        # lưu lỗi
        repo: Repo = env.repo
        original = repo.insert_message

        def broken(msg: Any) -> Any:
            if msg.role == "assistant":
                raise sqlite3.OperationalError("database is locked")
            return original(msg)

        monkeypatch.setattr(repo, "insert_message", broken)
        assert names((await mai.post(f"/api/stories/{story}/reply")).text)[-1] == "error"
        monkeypatch.setattr(repo, "insert_message", original)
        await _released(env, "save_failed")
        # InvalidOperation khi chuẩn bị (không có lượt nào đang chờ trả lời sau khi đã trả lời)
        assert names((await mai.post(f"/api/stories/{story}/reply")).text)[-1] == "done"
        env.set_balance("mai", 300)
        refused = await mai.post(f"/api/stories/{story}/reply")
        assert refused.status_code == 409
        await _released(env, "invalid", charged=1)
        # chờ quá 120 giây (ở đây: hết hạn chờ ngắn) khi Lan đang giữ chỗ duy nhất
        lan = env.clients["lan"]
        lan_story = await new_story(lan)
        env.app.state.gate.wait_timeout = 0.05
        env.fake.delay = 0.05
        busy = asyncio.create_task(lan.post(f"/api/stories/{lan_story}/messages", json={"content": "Dài."}))
        await until(lambda: env.app.state.gate.active == 1)
        timed = await mai.post(f"/api/stories/{story}/messages", json={"content": "Chờ."})
        assert names(timed.text) == ["user_message", "waiting", "error"]
        await _released(env, "queue_timeout", charged=1)
        await busy
        env.fake.delay = 0.0
        env.app.state.gate.wait_timeout = 120.0
        # đóng kết nối trước sự kiện delta đầu tiên
        chat: ChatService = env.app.state.chat
        env.fake.delay = 0.2
        stream = chat.send(story, "Thôi, không cần.")
        first = await anext(stream)
        assert first.name == "user_message"
        await stream.aclose()
        env.fake.delay = 0.0
        await _released(env, "cancelled", charged=1)


async def test_stop_after_first_delta_charges(tmp_path: Path) -> None:
    async with coin_env(tmp_path) as env:
        mai = env.clients["mai"]
        story = await new_story(mai)
        chat: ChatService = env.app.state.chat
        env.fake.delay = 0.02
        stream = chat.send(story, "Kể tiếp đi.")
        async for event in stream:
            if event.name == "delta":
                break
        await stream.aclose()
        env.fake.delay = 0.0
        holds = env.holds("mai")
        assert holds[-1]["status"] == "charged" and holds[-1]["message_id"] is not None
        _assert_chat_rows(env, "mai", 1)
        assert env.balance("mai") == 294
        saved = env.rows("SELECT gen_stats_json FROM messages WHERE id = ?", holds[-1]["message_id"])
        assert saved and '"aborted": true' in saved[0][0].replace('"aborted":true', '"aborted": true')


# ---------------------------------------------------------------------------- khởi động lại


async def test_open_holds_released_only_in_app_lifespan(tmp_path: Path) -> None:
    db = tmp_path / "lyris.db"
    conn = connect(db)
    migrate(conn)
    repo = Repo(conn)
    ensure_owner_password(repo)
    mai = add_member(repo, "mai", "Mai")
    with repo.transaction():
        conn.execute(
            "INSERT INTO coin_holds (account_id, mode, kind, amount, status, coin_day, created_at)"
            " VALUES (?, 'test', 'send', 6, 'held', '2026-11-14', '2026-11-14T00:00:00.000Z')",
            (mai,),
        )
    conn.close()

    def status() -> str:
        c = connect(db)
        try:
            return str(c.execute("SELECT status FROM coin_holds").fetchone()[0])
        finally:
            c.close()

    c2 = connect(db)
    migrate(c2)
    c2.close()
    assert status() == "held"
    assert auth_cli.main(["list"], db_path=db) == 0
    assert status() == "held"
    app = create_app(settings(tmp_path), FakeLLM(replies=[REPLY]))
    async with app.router.lifespan_context(app):
        rows = app.state.repo.conn.execute("SELECT status, release_reason FROM coin_holds").fetchall()
        assert [tuple(r) for r in rows] == [("released", "restart")]
        events = app.state.repo.conn.execute(
            "SELECT account_id, props_json FROM analytics_events WHERE name = 'coins_released'"
        ).fetchall()
        assert [tuple(e) for e in events] == [(None, '{"kind":"send","reason":"restart"}')]
    with connect(db) as c3:
        assert ledger.balance(c3, mai) == 300


# ---------------------------------------------------------------------------- trừ không bao giờ làm mất câu trả lời


async def test_charge_of_held_hold_never_loses_reply(tmp_path: Path) -> None:
    async with coin_env(tmp_path) as env:
        mai = env.clients["mai"]
        story = await new_story(mai)
        env.fake.delay = 0.02
        task = asyncio.create_task(mai.post(f"/api/stories/{story}/messages", json={"content": "Kể đi."}))
        await until(lambda: any(h["status"] == "held" for h in env.holds("mai")))
        # Chủ máy trừ tay xuống mức thấp nhất cho phép: số dư − giữ chỗ = 0.
        with env.repo.transaction():
            available = ledger.balance(env.repo.conn, env.ids["mai"]) - ledger.held(env.repo.conn, env.ids["mai"])
        env.set_balance("mai", 300 - available)
        assert env.balance("mai") == 6
        resp = await task
        env.fake.delay = 0.0
        assert names(resp.text)[-1] == "done"
        assert env.balance("mai") == 0
        _assert_chat_rows(env, "mai", 1)
        assert len(env.rows("SELECT id FROM messages WHERE story_id = ? AND role = 'assistant'", story)) == 2  # + lời chào
        # Giữ chỗ đã bị nhả (không thể xảy ra trong luồng thường): câu trả lời vẫn được lưu, không trừ.
        env.set_balance("mai", 300)
        env.fake.delay = 0.02
        task = asyncio.create_task(mai.post(f"/api/stories/{story}/messages", json={"content": "Nữa đi."}))
        await until(lambda: any(h["status"] == "held" for h in env.holds("mai")))
        with env.repo.transaction():
            env.repo.conn.execute("UPDATE coin_holds SET status = 'released', release_reason = 'restart' WHERE status = 'held'")
        resp = await task
        env.fake.delay = 0.0
        assert names(resp.text)[-1] == "done"
        assert len(env.rows("SELECT id FROM messages WHERE story_id = ? AND role = 'assistant'", story)) == 3
        assert env.balance("mai") == 300
        _assert_chat_rows(env, "mai", 1)


async def test_stuck_hold_never_blocks_next_turn(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Giữ chỗ kẹt `held` (nhả lỗi; hay lưu câu trả lời lỗi SAU khi đã trừ trong bộ nhớ) không chặn lượt sau,
    không cần khởi động lại app; số dư đúng."""
    async with coin_env(tmp_path) as env:
        mai = env.clients["mai"]
        story = await new_story(mai)
        # A. Nhả giữ chỗ lỗi một lần ("database is locked") sau một lượt lỗi model.
        real_release = holds_mod.release_hold
        calls = {"n": 0}

        def flaky(conn: Any, hold_id: int, reason: str, now: Any = None) -> Any:
            calls["n"] += 1
            if calls["n"] == 1:
                raise sqlite3.OperationalError("database is locked")
            return real_release(conn, hold_id, reason, now)

        monkeypatch.setattr(holds_mod, "release_hold", flaky)
        env.fake.error = LLMError("model hỏng")
        assert names((await mai.post(f"/api/stories/{story}/messages", json={"content": "Chào"})).text)[-1] == "error"
        env.fake.error = None
        retry = await mai.post(f"/api/stories/{story}/reply")
        assert retry.status_code == 200 and names(retry.text)[-1] == "done", retry.text
        for _ in range(2):
            again = await mai.post(f"/api/stories/{story}/messages", json={"content": "Tiếp."})
            assert again.status_code == 200, again.text
            assert names(again.text)[-1] == "done", again.text
        monkeypatch.setattr(holds_mod, "release_hold", real_release)
        holds = env.holds("mai")
        assert holds[0]["status"] == "released" and holds[0]["release_reason"] == "error"
        assert all(h["status"] != "held" for h in holds)
        _assert_chat_rows(env, "mai", 3)
        assert env.balance("mai") == 300 - 18
        # B. COMMIT của transaction lưu câu trả lời lỗi SAU khi `charge` đã đánh dấu giữ chỗ trong bộ nhớ.
        env.set_balance("mai", 300)
        coins: CoinService = env.app.state.coins
        real_charge = coins.charge

        def charge_then_fail(hold: Any, message_id: int | None) -> bool:
            real_charge(hold, message_id)
            raise sqlite3.OperationalError("disk I/O error (commit)")

        monkeypatch.setattr(coins, "charge", charge_then_fail)
        failed = await mai.post(f"/api/stories/{story}/messages", json={"content": "Chào lần nữa"})
        assert names(failed.text)[-1] == "error"
        monkeypatch.setattr(coins, "charge", real_charge)
        last = env.holds("mai")[-1]
        assert last["status"] == "released" and last["release_reason"] == "save_failed"
        _assert_chat_rows(env, "mai", 3)  # không có dòng sổ mới
        assert env.balance("mai") == 300
        nxt = await mai.post(f"/api/stories/{story}/reply")
        assert nxt.status_code == 200 and names(nxt.text)[-1] == "done", nxt.text
        assert env.balance("mai") == 294 and all(h["status"] != "held" for h in env.holds("mai"))


async def test_stop_before_visible_text_releases_hold(tmp_path: Path) -> None:
    """Dừng khi người chơi CHƯA nhận `delta` có chữ nào (chỉ mẩu "[Tho…" của suy nghĩ đang chờ trong parser):
    nhả `cancelled`, không trừ coin."""
    fake = FakeLLM(replies=["[Thought: " + "x" * 200 + "] Chào."], chunk_size=4, delay=0.05)
    async with coin_env(tmp_path, fake=fake) as env:
        story = await new_story(env.clients["mai"])
        fake.delay = 0.05
        chat: ChatService = env.app.state.chat
        seen: list[str] = []

        async def consume() -> None:
            async for ev in chat.send(story, "Chào"):
                seen.append(ev.name)

        task = asyncio.create_task(consume())
        await asyncio.sleep(0.12)  # 1-2 mẩu đã tới, parser còn giữ, chưa có delta
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        fake.delay = 0.0
        assert "delta" not in seen and "start" in seen, seen
        last = env.holds("mai")[-1]
        assert last["status"] == "released" and last["release_reason"] == "cancelled"
        assert env.ledger("mai", "chat") == [] and env.balance("mai") == 300


async def test_chat_service_without_coins_never_holds(tmp_path: Path) -> None:
    async with coin_env(tmp_path) as env:
        story = await new_story(env.clients["mai"])
        plain = ChatService(env.repo, FakeLLM(replies=[REPLY]))  # không có coins: không tính coin
        events = [e.name async for e in plain.send(story, "Chào.")]
        assert events[-1] == "done"
        assert env.holds("mai") == [] and env.balance("mai") == 300
        with_coins = ChatService(env.repo, FakeLLM(replies=[REPLY]), coins=CoinService(env.repo))
        assert [e.name async for e in with_coins.send(story, "Lần nữa.")][-1] == "done"
        assert len(env.holds("mai")) == 1 and env.balance("mai") == 294


# ---------------------------------------------------------------------------- hết coin


async def test_out_of_coins_402_before_user_turn_saved(tmp_path: Path) -> None:
    async with coin_env(tmp_path) as env:
        mai = env.clients["mai"]
        story = await new_story(mai)
        sent = await mai.post(f"/api/stories/{story}/messages", json={"content": "Chào."})
        assert names(sent.text)[-1] == "done"
        reply_id = env.rows("SELECT id FROM messages WHERE story_id = ? AND role = 'assistant' ORDER BY id DESC", story)[0][0]
        other = await new_story(mai)
        env.fake.error = LLMError("model hỏng")
        assert names((await mai.post(f"/api/stories/{other}/messages", json={"content": "Có đó không?"})).text)[-1] == "error"
        env.fake.error = None
        env.set_balance("mai", 4)
        before = {s: [m.id for m in env.repo.active_messages(s)] for s in (story, other)}
        body = await studio_chat_body(mai)
        calls = [
            ("send", mai.post(f"/api/stories/{story}/messages", json={"content": "Còn nữa không?"})),
            ("reply", mai.post(f"/api/stories/{other}/reply")),
            ("regenerate", mai.post(f"/api/messages/{reply_id}/regenerate")),
            ("test-chat", mai.post("/api/cards/test-chat", json=body)),
        ]
        for label, call in calls:
            resp = await call
            assert resp.status_code == 402, (label, resp.status_code, resp.text)
            assert resp.headers["content-type"].startswith("application/json"), label
            data = resp.json()
            assert {k: data[k] for k in COINS_402} == COINS_402, label
            assert data["balance"] == 4 and data["price"] == 6
        after = {s: [m.id for m in env.repo.active_messages(s)] for s in (story, other)}
        assert after == before
        assert env.balance("mai") == 4 and all(h["status"] != "held" for h in env.holds("mai"))
        events = env.rows("SELECT props_json FROM analytics_events WHERE name = 'coins_insufficient' ORDER BY id")
        assert [e[0] for e in events] == [
            '{"kind":"send","mode":"story"}', '{"kind":"retry","mode":"story"}',
            '{"kind":"regenerate","mode":"story"}', '{"kind":"send","mode":"test"}',
        ]
        # Có coin lại thì gửi được (không cần gì khác).
        env.set_balance("mai", 6)
        assert names((await mai.post(f"/api/stories/{story}/messages", json={"content": "Giờ thì sao?"})).text)[-1] == "done"
        assert env.balance("mai") == 0


async def test_two_tabs_cannot_overspend(tmp_path: Path) -> None:
    async with coin_env(tmp_path) as env:
        mai = env.clients["mai"]
        one, two = await new_story(mai), await new_story(mai)
        env.set_balance("mai", 6)
        env.fake.delay = 0.01
        a, b = await asyncio.gather(
            mai.post(f"/api/stories/{one}/messages", json={"content": "Tab một."}),
            mai.post(f"/api/stories/{two}/messages", json={"content": "Tab hai."}),
        )
        env.fake.delay = 0.0
        statuses = sorted([a.status_code, b.status_code])
        assert statuses in ([200, 402], [200, 409]), statuses
        ok = a if a.status_code == 200 else b
        assert names(ok.text)[-1] == "done"
        assert env.balance("mai") == 0
        _assert_chat_rows(env, "mai", 1)
        with env.repo.locked() as conn:
            assert ledger.balance(conn, env.ids["mai"]) >= 0


# ---------------------------------------------------------------------------- miễn phí


async def test_suggestions_and_draft_are_free(tmp_path: Path) -> None:
    fake = FakeLLM(
        replies=[REPLY],
        json_replies=[
            {"suggestions": ["\"Chào anh.\"", "*Mỉm cười* \"Đi dạo không?\"", "\"Kể em nghe đi.\""]},
            good_reply(),
        ],
    )
    async with coin_env(tmp_path, fake=fake) as env:
        mai = env.clients["mai"]
        story = await new_story(mai)
        assert names((await mai.post(f"/api/stories/{story}/messages", json={"content": "Chào."})).text)[-1] == "done"
        holds_before, balance_before = len(env.holds("mai")), env.balance("mai")
        suggested = await mai.post(f"/api/stories/{story}/suggestions")
        assert suggested.status_code == 200, suggested.text
        drafted = await mai.post("/api/cards/draft", json={"idea": "Một đại sư tỷ lạnh lùng", "language": "vi"})
        assert drafted.status_code == 200, drafted.text
        assert len(env.holds("mai")) == holds_before and env.balance("mai") == balance_before
        assert len(env.ledger("mai", "chat")) == 1
