"""Event tracking qua API (docs/tracking-plan.md): sự kiện của server ở đúng chỗ, `POST /api/events`, tắt chia sẻ,
không lọt chữ của người dùng, xuất dữ liệu và số liệu tổng cho chủ máy.

LLM giả (FakeLLM), DB trong thư mục tạm; PostHog giả bằng `httpx.MockTransport`. Không gọi Ollama, không ra mạng.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from lyris.analytics import events as catalog
from lyris.analytics.replies import tracked_reply
from lyris.analytics.tracker import TrackContext, Tracker
from lyris.api.app import create_app
from lyris.auth import clock, passwords
from lyris.compliance import legal
from lyris.chat.service import ChatEvent
from lyris.config import Settings
from lyris.db.connection import connect, migrate
from lyris.db.repo import Repo
from lyris.llm.base import LLMError
from lyris.llm.fake import FakeLLM
from tests.authutil import (
    MEMBER_PASSWORD,
    OWNER_PASSWORD,
    add_member,
    anon_client,
    client_for,
    ensure_owner_password,
    repo_of,
)
from tests.twoaccounts import (
    LORE,
    PRIVATE_NAME,
    PUBLIC_NAME,
    PUBLIC_SECRET,
    REPLY,
    TRIGGER,
    _build,
    card_body,
    make_settings,
    parse_sse,
)

WORLD_MD = "## Mục lore\n\n### Ngọn hải đăng bí ẩn\nKhoá: hải đăng\nNgọn hải đăng cũ ở cuối đảo, chỉ sáng vào đêm mưa."
SECRET_MESSAGE = "Tớ kể cậu nghe chuyện thầm kín nhất đời tớ *thì thầm* ((hãy dịu dàng))"


class FakePostHog:
    def __init__(self) -> None:
        self.batches: list[dict[str, Any]] = []

    def transport(self) -> httpx.MockTransport:
        def handler(request: httpx.Request) -> httpx.Response:
            self.batches.append(json.loads(request.content))
            return httpx.Response(200, json={"status": 1})

        return httpx.MockTransport(handler)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return make_settings(tmp_path)


@pytest.fixture
async def app(settings: Settings) -> AsyncIterator[FastAPI]:
    application = create_app(settings, FakeLLM(replies=[REPLY]))
    async with application.router.lifespan_context(application):
        yield application


@pytest.fixture
def cheap_scrypt(monkeypatch: pytest.MonkeyPatch) -> None:
    def cheap(password: bytes, salt: bytes, n: int, r: int, p: int) -> bytes:
        return hashlib.scrypt(password, salt=salt + n.to_bytes(4, "big"), n=16, r=1, p=1, dklen=32)

    monkeypatch.setattr(passwords, "_scrypt", cheap)


def accept_terms(repo: Repo, *account_ids: int) -> None:
    """Tài khoản đồng ý bản Điều khoản / Chính sách hiện tại (tài khoản trong test được chèn thẳng, chưa đồng ý)."""
    with repo.transaction():
        for account_id in account_ids:
            legal.accept(repo.conn, account_id, clock.now())


def events_of(app: FastAPI, sql_where: str = "1", *params: Any) -> list[dict[str, Any]]:
    with repo_of(app).locked() as conn:
        rows = conn.execute(f"SELECT * FROM analytics_events WHERE {sql_where} ORDER BY id", params).fetchall()
    out = []
    for r in rows:
        item = dict(r)
        item["props"] = json.loads(item.pop("props_json"))
        out.append(item)
    return out


def names(app: FastAPI, *, skip_sessions: bool = True) -> list[str]:
    return [e["name"] for e in events_of(app) if not (skip_sessions and e["name"] == "session_started")]


def last(app: FastAPI, name: str) -> dict[str, Any]:
    found = [e for e in events_of(app) if e["name"] == name]
    assert found, (name, names(app))
    return found[-1]


async def ok(resp: httpx.Response) -> Any:
    assert resp.status_code in (200, 202), (resp.request.method, str(resp.request.url), resp.status_code, resp.text)
    return resp.json()


async def send(client: httpx.AsyncClient, story_id: int, content: str) -> list[tuple[str, dict[str, Any]]]:
    resp = await client.post(f"/api/stories/{story_id}/messages", json={"content": content})
    assert resp.status_code == 200, resp.text
    return parse_sse(resp.text)


# ---------------------------------------------------------------------------- sự kiện của server


async def test_server_events_along_the_core_loop(app: FastAPI) -> None:
    repo = repo_of(app)
    owner = ensure_owner_password(repo)
    async with client_for(app, owner) as c:
        persona = await ok(await c.post("/api/personas", json={"name": "Ngọc", "gender": "female"}))
        card = await ok(await c.post("/api/cards?via=ai_draft", json={"card": card_body("Hải", visibility="public")}))
        assert (await c.post("/api/cards?via=bịa", json={"card": card_body("Sai")})).status_code == 422
        story = await ok(await c.post("/api/stories", json={"card_id": card["id"], "persona_id": persona["id"]}))
        sid = story["id"]
        sse = await send(c, sid, SECRET_MESSAGE)
        assert sse[-1][0] == "done"
        reply_id = sse[-1][1]["message"]["id"]
        user_id = next(d["message"]["id"] for n, d in sse if n == "user_message")
        assert "lyris_anon" in c.cookies

        regen = await c.post(f"/api/messages/{reply_id}/regenerate")
        assert regen.status_code == 200 and parse_sse(regen.text)[-1][0] == "done"
        await ok(await c.post(f"/api/messages/{reply_id}/variant", json={"variant_index": 0}))
        await ok(await c.patch(f"/api/messages/{reply_id}", json={"content": "Đã sửa câu trả lời."}))
        await ok(await c.put(f"/api/messages/{reply_id}/feedback", json={"rating": "down", "note": "dở quá"}))
        await ok(await c.put(f"/api/messages/{reply_id}/feedback", json={"rating": None}))

        async def suggester(llm: Any, **kw: Any) -> list[str]:
            return ["Gợi ý một", "Gợi ý hai"]

        app.state.chat.suggester = suggester
        await ok(await c.post(f"/api/stories/{sid}/suggestions"))
        await ok(await c.patch(f"/api/stories/{sid}", json={"mode": "dm"}))
        await ok(await c.patch(f"/api/stories/{sid}", json={"mode": "dm", "title": "Không đổi chế độ"}))
        await ok(await c.patch(f"/api/stories/{sid}", json={"show_thoughts": False}))
        await ok(await c.delete(f"/api/messages/{user_id}"))
        imported = await ok(await c.post(f"/api/cards/{card['id']}/lore/import", json={"text": WORLD_MD}))
        assert imported["created"] == 1
        await ok(await c.post(f"/api/cards/{card['id']}/lore/import", json={"text": WORLD_MD, "dry_run": True}))
        await ok(await c.post(f"/api/cards/{card['id']}/duplicate"))
        await ok(await c.post("/api/admin/invites", json={"expires_in_days": 7}))

    assert names(app) == [
        "persona_created",
        "character_created",
        "character_published",
        "story_started",
        "message_sent",
        "reply_completed",
        "regenerate_used",  # ghi khi lượt tạo lại bắt đầu; reply_completed khi stream xong
        "reply_completed",
        "variant_switched",
        "message_edited",
        "reply_rated",
        "reply_rated",
        "suggestions_requested",
        "mode_switched",
        "show_thoughts_toggled",
        "message_deleted",
        "lore_imported",
        "character_created",
        "invite_created",
    ]
    rows = events_of(app)
    assert rows[0]["name"] == "session_started" and len({r["session_id"] for r in rows}) == 1
    assert {r["account_id"] for r in rows} == {owner} and len({r["anon_id"] for r in rows}) == 1
    by = {n: [e for e in rows if e["name"] == n] for n in {e["name"] for e in rows}}
    assert by["character_created"][0]["props"] == {"via": "ai_draft", "visibility": "public", "has_avatar": False}
    assert by["character_created"][1]["props"]["via"] == "duplicate"
    assert by["story_started"][0]["props"] == {"mode": "story", "source": "own", "language": "vi"}
    assert by["story_started"][0]["story_id"] == sid
    assert by["message_sent"][0]["props"] == {
        "mode": "story", "length_bucket": "21_80", "has_action": True, "has_directive": True, "user_turn": "1"
    }
    first, second = by["reply_completed"]
    assert first["props"]["kind"] == "send" and second["props"]["kind"] == "regenerate"
    assert first["props"]["aborted"] is False and first["props"]["waited"] is False
    assert first["props"]["ttft_bucket"] in catalog.TTFT_BUCKET.values and first["props"]["output_tokens"] > 0
    assert isinstance(first["props"]["duration_ms"], int) and first["props"]["duration_ms"] % 100 == 0
    assert by["message_edited"][0]["props"] == {"role": "assistant", "mode": "story"}
    assert [e["props"]["rating"] for e in by["reply_rated"]] == ["down", "cleared"]
    assert by["suggestions_requested"][0]["props"] == {"ok": True, "items": 2, "mode": "story"}
    assert by["mode_switched"][0]["props"] == {"to": "dm"}
    assert by["show_thoughts_toggled"][0]["props"] == {"enabled": False}
    assert by["message_deleted"][0]["props"] == {"count_bucket": "2_5", "mode": "dm"}
    assert by["lore_imported"][0]["props"] == {"format": "world_md", "entries": 1}
    assert by["invite_created"][0]["props"] == {"expires_days": 7}
    assert {r["source"] for r in rows} == {"server"} and {r["posthog_state"] for r in rows} == {"local"}


async def test_reply_failed_story_sources_and_resume(settings: Settings) -> None:
    fake = FakeLLM(replies=[REPLY])
    app = create_app(settings, fake)
    async with app.router.lifespan_context(app):
        repo = repo_of(app)
        owner = ensure_owner_password(repo)
        async with client_for(app, owner) as c:
            default = await ok(await c.post("/api/stories", json={}))
            template = await ok(await c.post("/api/templates/lac-duong/install"))
            persona = (await ok(await c.get("/api/personas")))[0]
            await ok(await c.post("/api/stories", json={"card_id": template["id"], "persona_id": persona["id"]}))
            fake.error = LLMError("không kết nối được", kind="connect")
            sse = await send(c, default["id"], "Chào.")
            assert sse[-1][0] == "error"
            fake.error = None
            retry = await c.post(f"/api/stories/{default['id']}/reply")
            assert parse_sse(retry.text)[-1][0] == "done"
            # Lâu không chơi: lùi mốc của mọi tin nhắn 3 ngày.
            with repo.transaction():
                repo.conn.execute(
                    "UPDATE messages SET created_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now', '-3 days')"
                    " WHERE story_id = ?",
                    (default["id"],),
                )
            await send(c, default["id"], "Mình quay lại rồi.")
        assert [e["props"]["source"] for e in events_of(app) if e["name"] == "story_started"] == ["default", "template"]
        failed = last(app, "reply_failed")
        assert failed["props"] == {"mode": "story", "kind": "send", "reason": "connect", "waited": False}
        assert last(app, "reply_completed")["props"]["kind"] == "send"
        assert [e["props"]["kind"] for e in events_of(app) if e["name"] == "reply_completed"] == ["retry", "send"]
        resumed = last(app, "story_resumed")
        assert resumed["props"] == {"days_since_last": "2_3", "mode": "story"} and resumed["story_id"] == default["id"]
        assert len([e for e in events_of(app) if e["name"] == "story_resumed"]) == 1
        assert last(app, "message_sent")["props"]["user_turn"] == "2_4"


async def test_failed_requests_record_nothing(app: FastAPI) -> None:
    """Lỗi trước khi làm được việc (404, 409, 422) không ghi sự kiện nào."""
    repo = repo_of(app)
    owner = ensure_owner_password(repo)
    async with client_for(app, owner) as c:
        assert (await c.post("/api/stories/999/messages", json={"content": "x"})).status_code == 404
        story = await ok(await c.post("/api/stories", json={}))
        before = len(events_of(app))
        assert (await c.post(f"/api/stories/{story['id']}/messages", json={"content": "   "})).status_code == 422
        assert (await c.post(f"/api/stories/{story['id']}/reply")).status_code == 409
        assert (await c.post("/api/messages/999/regenerate")).status_code == 404
        assert (await c.post(f"/api/cards/999/duplicate")).status_code == 404
        assert len(events_of(app)) == before


async def test_reply_aborted_is_tracked() -> None:
    conn = connect(":memory:")
    migrate(conn)
    repo = Repo(conn)
    tracker = Tracker(repo)

    async def stream() -> AsyncIterator[ChatEvent]:
        yield ChatEvent("start", {"turn_index": 1, "variant_index": 0})
        yield ChatEvent("delta", {"kind": "text", "text": "Một"})
        await asyncio.sleep(10)
        yield ChatEvent("done", {"message": {}})

    wrapped = tracked_reply(
        stream(), tracker=tracker, ctx=TrackContext(account_id=None, anon_id="x" * 22), story_id=3, mode="dm",
        kind="send",
    )
    assert (await anext(wrapped)).name == "start"
    assert (await anext(wrapped)).name == "delta"
    await wrapped.aclose()  # người chơi bấm Dừng / đóng tab
    rows = conn.execute("SELECT name, story_id, props_json FROM analytics_events ORDER BY id").fetchall()
    assert [r[0] for r in rows] == ["session_started", "reply_completed"]
    props = json.loads(rows[1][2])
    assert props["aborted"] is True and props["mode"] == "dm" and "output_tokens" not in props
    assert rows[1][1] == 3
    conn.close()


async def test_lore_unlocked_on_first_reveal(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path), FakeLLM(replies=[REPLY]))
    async with app.router.lifespan_context(app):
        repo = repo_of(app)
        owner = ensure_owner_password(repo)
        async with client_for(app, owner) as c:
            persona = await ok(await c.post("/api/personas", json={"name": "Ngọc", "gender": "female"}))
            card = await ok(await c.post("/api/cards", json={"card": card_body("Hải")}))
            for entry in LORE:
                await ok(await c.post(f"/api/cards/{card['id']}/lore", json=entry))
            story = await ok(await c.post("/api/stories", json={"card_id": card["id"], "persona_id": persona["id"]}))
            await send(c, story["id"], TRIGGER)
            first = last(app, "lore_unlocked")
            assert first["props"]["count"] >= 1 and first["story_id"] == story["id"]
            count = len([e for e in events_of(app) if e["name"] == "lore_unlocked"])
            await send(c, story["id"], "Không nhắc gì tới thế giới cả.")
            await send(c, story["id"], TRIGGER)  # mục đã mở rồi: không ghi lại
            assert len([e for e in events_of(app) if e["name"] == "lore_unlocked"]) == count


# ---------------------------------------------------------------------------- đăng nhập, tạo tài khoản, mời


async def test_auth_events_link_anon_to_account(app: FastAPI, cheap_scrypt: None) -> None:
    repo = repo_of(app)
    owner = ensure_owner_password(repo)
    async with client_for(app, owner) as o:
        code = (await ok(await o.post("/api/admin/invites", json={"expires_in_days": 1})))["code"]
    async with anon_client(app) as c:
        assert (await ok(await c.post("/api/events", json={"events": [
            {"name": "signup_viewed", "props": {"has_invite_code": True}}
        ]})))["accepted"] == 1
        anon = c.cookies["lyris_anon"]
        resp = await c.post(
            "/api/auth/signup",
            json={"accept_terms": True, "invite_code": code, "handle": "hoa", "display_name": "Hoa", "password": MEMBER_PASSWORD},
        )
        assert resp.status_code == 200, resp.text
        new_id = resp.json()["account"]["id"]
        assert (await c.get("/api/auth/me")).json()["account"]["handle"] == "hoa"  # cookie phiên vẫn đúng
        assert (await c.post("/api/auth/logout")).status_code == 204
        bad = await c.post("/api/auth/login", json={"handle": "hoa", "password": "sai mật khẩu rồi"})
        assert bad.status_code == 401
        good = await c.post("/api/auth/login", json={"handle": "hoa", "password": MEMBER_PASSWORD})
        assert good.status_code == 200
        assert (await c.get("/api/auth/me")).json()["account"]["handle"] == "hoa"
        assert c.cookies["lyris_anon"] == anon  # cùng thiết bị
    rows = [e for e in events_of(app) if e["anon_id"] == anon]
    assert [(e["name"], e["account_id"]) for e in rows if e["name"] != "session_started"] == [
        ("signup_viewed", None),
        ("signup_completed", new_id),
        ("invite_redeemed", new_id),
        ("login_failed", None),
        ("login_succeeded", new_id),
    ]
    assert last(app, "invite_redeemed")["props"] == {"invite_age": "lt_1h"}
    assert last(app, "login_failed")["props"] == {"reason": "bad_credentials"}
    text = json.dumps(events_of(app), ensure_ascii=False)
    assert '"hoa"' not in text and '"Hoa"' not in text
    assert code not in text and MEMBER_PASSWORD not in text and OWNER_PASSWORD not in text


# ---------------------------------------------------------------------------- POST /api/events


async def test_events_endpoint_rules(app: FastAPI) -> None:
    repo = repo_of(app)
    owner = ensure_owner_password(repo)
    member = add_member(repo, "mai")
    async with anon_client(app) as anon:
        got = await ok(await anon.post("/api/events", json={"events": [
            {"name": "app_opened", "props": {"display_mode": "standalone", "authed": False}},
            {"name": "explore_viewed"},  # cần đăng nhập
            {"name": "story_started", "props": {"mode": "story", "source": "own", "language": "vi"}},  # của server
            {"name": "khong_co"},
            {"name": "app_opened", "props": {"display_mode": "Một câu tự do"}},
            {"name": "app_opened", "props": {"note": "x"}},
        ]}))
        assert got == {"accepted": 1, "dropped": 5}
        row = last(app, "app_opened")
        assert row["account_id"] is None and row["anon_id"] == anon.cookies["lyris_anon"] and row["source"] == "client"
        too_many = await anon.post("/api/events", json={"events": [{"name": "app_opened"}] * 21})
        assert too_many.status_code == 422
        assert (await anon.post("/api/events", json={"events": []})).status_code == 422
        assert (await anon.post("/api/events", json={"events": [{"name": "app_opened", "x": 1}]})).status_code == 422
        long_value = {"events": [{"name": "app_opened", "props": {"display_mode": "x" * 65}}]}
        assert (await anon.post("/api/events", json=long_value)).status_code == 422
        gpc = await anon.post("/api/events", json={"events": [{"name": "app_opened"}]}, headers={"Sec-GPC": "1"})
        assert (await ok(gpc)) == {"accepted": 0, "dropped": 1}
    async with anon_client(app, headers={"X-Lyris": ""}) as no_csrf:
        resp = await no_csrf.post("/api/events", json={"events": [{"name": "app_opened"}]})
        assert resp.status_code == 403 and resp.json()["code"] == "csrf"

    async with client_for(app, owner) as a, client_for(app, member) as b:
        a_story = (await ok(await a.post("/api/stories", json={})))["id"]
        await ok(await b.post("/api/personas", json={"name": "Mai", "gender": "female"}))
        b_story = (await ok(await b.post("/api/stories", json={})))["id"]
        await ok(await a.patch(f"/api/stories/{a_story}", json={"mode": "dm"}))
        got = await ok(await a.post("/api/events", json={"events": [
            {"name": "explore_viewed"},
            {"name": "vibe_filter_used", "props": {"vibe": "tinh_dau", "position": 2}},
            {"name": "character_profile_viewed", "props": {"source": "template", "from": "explore"}},
            {"name": "thought_revealed", "story_id": a_story},
            {"name": "heart_drawer_opened", "story_id": b_story},  # story của người khác: bỏ story_id
            {"name": "explore_viewed", "story_id": a_story},  # không phải sự kiện của story: bỏ story_id
            {"name": "suggestion_used", "props": {"position": 2, "mode": "story"}, "story_id": a_story},
            # Chỉ server ghi báo cáo (không gắn ai): client gửi thì bị bỏ.
            {"name": "content_reported", "props": {"reason": "minor_safety", "target": "message"}, "story_id": a_story},
        ]}))
        assert got == {"accepted": 7, "dropped": 1}
        rows = {e["name"]: e for e in events_of(app, "source = 'client' AND account_id = ?", owner)}
        assert rows["thought_revealed"]["story_id"] == a_story and rows["thought_revealed"]["props"] == {"mode": "dm"}
        assert rows["heart_drawer_opened"]["story_id"] is None and rows["heart_drawer_opened"]["props"] == {}
        assert rows["explore_viewed"]["story_id"] is None
        assert rows["suggestion_used"]["props"] == {"position": 2, "mode": "dm"}  # chế độ thật của story
        assert "content_reported" not in rows

    # Tài khoản đang chờ đổi mật khẩu: coi như chưa đăng nhập.
    with repo.transaction():
        repo.conn.execute("UPDATE accounts SET must_change_password = 1 WHERE id = ?", (member,))
    async with client_for(app, member) as pending:
        got = await ok(await pending.post("/api/events", json={"events": [{"name": "explore_viewed"}, {"name": "app_opened"}]}))
        assert got == {"accepted": 1, "dropped": 1}
        assert last(app, "app_opened")["account_id"] is None


async def test_events_rate_limit(app: FastAPI) -> None:
    owner = ensure_owner_password(repo_of(app))
    async with client_for(app, owner) as c:
        for _ in range(30):
            assert (await c.post("/api/events", json={"events": [{"name": "explore_viewed"}]})).status_code == 202
        limited = await c.post("/api/events", json={"events": [{"name": "explore_viewed"}]})
        assert limited.status_code == 429 and limited.headers["retry-after"] == "60"
        assert limited.json()["code"] == "rate_limited"
    async with anon_client(app) as other:  # khoá khác (IP khi chưa đăng nhập): không bị chặn chung
        assert (await other.post("/api/events", json={"events": [{"name": "app_opened"}]})).status_code == 202


async def test_events_in_setup_mode(app: FastAPI) -> None:
    """Chủ máy chưa thiết lập: vẫn nhận sự kiện trước đăng nhập (màn thiết lập), không gì khác."""
    async with anon_client(app) as c:
        got = await ok(await c.post("/api/events", json={"events": [{"name": "app_opened"}, {"name": "explore_viewed"}]}))
        assert got == {"accepted": 1, "dropped": 1}


# ---------------------------------------------------------------------------- tắt chia sẻ


async def test_opt_out_honoured_server_and_client(app: FastAPI) -> None:
    repo = repo_of(app)
    owner = ensure_owner_password(repo)
    member = add_member(repo, "mai")
    async with client_for(app, owner) as c, client_for(app, member) as m:
        assert (await ok(await c.get("/api/account")))["analytics_opt_out"] is False  # mặc định đang chia sẻ
        await ok(await c.post("/api/personas", json={"name": "Ngọc", "gender": "female"}))
        await ok(await c.post("/api/events", json={"events": [{"name": "explore_viewed"}]}))
        await ok(await m.post("/api/personas", json={"name": "Mai", "gender": "female"}))
        assert events_of(app, "account_id = ?", owner)

        out = await ok(await c.patch("/api/account", json={"analytics_opt_out": True}))
        assert out["analytics_opt_out"] is True and out["handle"] == repo.get_account(owner).handle
        assert events_of(app, "account_id = ?", owner) == []  # đã xoá sự kiện đã lưu
        marker = last(app, "analytics_opt_out")
        assert marker["account_id"] is None and marker["anon_id"] == "" and marker["posthog_state"] == "local"
        # Server không ghi gì nữa...
        await ok(await c.post("/api/personas", json={"name": "Lan", "gender": "female"}))
        story = await ok(await c.post("/api/stories", json={}))
        await send(c, story["id"], "Chào.")
        # ...và sự kiện client gửi lên cũng bị bỏ.
        got = await ok(await c.post("/api/events", json={"events": [{"name": "explore_viewed"}, {"name": "app_opened"}]}))
        assert got == {"accepted": 0, "dropped": 2}
        assert events_of(app, "account_id = ?", owner) == []
        assert (await ok(await c.get("/api/account")))["analytics_opt_out"] is True
        # Tắt lần nữa không ghi thêm dòng đếm.
        await ok(await c.patch("/api/account", json={"analytics_opt_out": True}))
        assert len([e for e in events_of(app) if e["name"] == "analytics_opt_out"]) == 1
        # Thành viên khác không bị ảnh hưởng.
        assert events_of(app, "account_id = ?", member)
        assert (await ok(await m.get("/api/account")))["analytics_opt_out"] is False
        # Bật lại: ghi tiếp.
        await ok(await c.patch("/api/account", json={"analytics_opt_out": False}))
        await ok(await c.post("/api/personas", json={"name": "Hà", "gender": "female"}))
        assert [e["name"] for e in events_of(app, "account_id = ?", owner)] == ["session_started", "persona_created"]
        # PATCH chỉ nhận trường đã biết; PUT /api/account bỏ qua trường này.
        assert (await c.patch("/api/account", json={"handle": "khac"})).status_code == 422
        assert (await c.patch("/api/account", json={"analytics_opt_out": "có"})).status_code == 422
        current = await ok(await c.get("/api/account"))
        await ok(await c.put("/api/account", json={**current, "analytics_opt_out": True}))
        assert (await ok(await c.get("/api/account")))["analytics_opt_out"] is False


# ---------------------------------------------------------------------------- không lọt chữ


def _strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for k, v in value.items():
            yield str(k)
            yield from _strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from _strings(v)


async def test_no_free_text_reaches_events_or_posthog(tmp_path: Path) -> None:
    """Một phiên đầy đủ với chữ riêng tư khắp nơi: không chữ nào vào DB số liệu hay vào lô gửi PostHog."""
    settings = Settings(**{**make_settings(tmp_path).__dict__, "posthog_key": "phc_test"})
    posthog = FakePostHog()
    app = create_app(settings, FakeLLM(replies=[REPLY]), start_forwarder=False, posthog_transport=posthog.transport())
    async with app.router.lifespan_context(app):
        repo = repo_of(app)
        a_id = ensure_owner_password(repo)
        b_id = add_member(repo, "mai", "Mai Thị Thầm Kín")
        accept_terms(repo, a_id, b_id)  # chưa đồng ý thì sự kiện chỉ ở máy, không gửi PostHog
        async with client_for(app, a_id) as a, client_for(app, b_id) as b:
            world = await _build(app, repo, settings.avatars_dir, a, b, a_id, b_id)
            await send(b, world.b_story, SECRET_MESSAGE)
            await ok(await a.patch(f"/api/stories/{world.a_story}", json={"title": "Tựa đề bí mật của story"}))
            await ok(await a.post(f"/api/cards/{world.a_private}/lore/import", json={"text": WORLD_MD}))
            await ok(await b.post(f"/api/messages/{world.b_message}/report", json={"reason": "other", "note": SECRET_MESSAGE}))
        assert await app.state.posthog.flush() > 0
        rows = events_of(app)
        a_handle = repo.get_account(a_id).handle
    assert len(rows) >= 15 and posthog.batches
    secrets = [
        PUBLIC_SECRET, PRIVATE_NAME, PUBLIC_NAME, TRIGGER, SECRET_MESSAGE, "Lại là cô ấy", "Gió ngoài bến cảng",
        "Tính cách riêng tư", "Hoàn cảnh riêng tư", "Mục tiêu riêng tư", "Ghi chú người tạo", "Một hải đăng cuối đảo",
        "Lâm Vãn", "Mai Thị Thầm Kín", "Tựa đề bí mật", "Ngọn hải đăng bí ẩn", "Bến cảng cũ", "Chỉ sáng vào đêm mưa",
        "thầm kín", "dịu dàng", "Biển hôm nay lặng", "Người gác hải đăng",
        *[e["content"] for e in LORE], *[e["title"] for e in LORE],
    ]
    dumped = json.dumps(rows, ensure_ascii=False) + json.dumps(posthog.batches, ensure_ascii=False)
    for secret in secrets:
        assert secret.lower() not in dumped.lower(), secret
    for handle in ("mai", a_handle):
        assert f'"{handle}"' not in dumped
    # Mọi giá trị thuộc tính: true/false, số, hoặc mã enum ngắn.
    for row in rows:
        for key, value in row["props"].items():
            assert re.fullmatch(r"[a-z_]{1,32}", key), key
            assert isinstance(value, (bool, int)) or re.fullmatch(r"[a-z0-9_]{1,24}", value), (row["name"], key, value)
    for item in (i for batch in posthog.batches for i in batch["batch"]):
        for key, value in item["properties"].items():
            if isinstance(value, str) and key not in ("app_version", "$session_id", "$anon_distinct_id", "$lib"):
                assert re.fullmatch(r"[a-z0-9_]{1,24}", value), (item["event"], key, value)
        assert item["properties"]["$ip"] is None


# ---------------------------------------------------------------------------- chủ máy: tổng hợp, xuất


async def test_owner_summary_and_export(app: FastAPI) -> None:
    repo = repo_of(app)
    owner = ensure_owner_password(repo)
    member = add_member(repo, "mai")
    async with client_for(app, owner) as c, client_for(app, member) as m:
        await ok(await c.post("/api/events", json={"events": [
            {"name": "explore_viewed"}, {"name": "character_profile_viewed", "props": {"source": "template"}}
        ]}))
        story = await ok(await c.post("/api/stories", json={}))
        for i in range(5):
            await send(c, story["id"], f"Lượt {i}.")
        await ok(await m.post("/api/events", json={"events": [{"name": "explore_viewed"}]}))

        summary = await ok(await c.get("/api/admin/analytics/summary?days=7"))
        counts = {x["name"]: x["count"] for x in summary["counts"]}
        assert counts["message_sent"] == 5 and counts["explore_viewed"] == 2 and counts["reply_completed"] == 5
        assert summary["dau"] == 2 and summary["posthog_enabled"] is False and len(summary["daily"]) == 7
        funnel = {f["step"]: (f["users"], f["converted"]) for f in summary["funnel"]}
        assert funnel == {
            "explore_viewed": (2, 2), "character_profile_viewed": (1, 1), "story_started": (1, 1),
            "message_sent": (1, 1), "messages_5": (1, 1),
        }
        assert summary["retention"]["d1"]["cohort"] == 0
        assert (await c.get("/api/admin/analytics/summary?days=0")).status_code == 422
        assert (await m.get("/api/admin/analytics/summary")).status_code == 403

        csv_resp = await c.get("/api/admin/analytics/export.csv")
        assert csv_resp.status_code == 200 and csv_resp.headers["content-type"].startswith("text/csv")
        assert csv_resp.headers["content-disposition"].startswith('attachment; filename="lyris-events-')
        lines = csv_resp.text.strip().split("\n")
        assert lines[0] == "event_id,ts,name,distinct_id,anon_id,session_id,story_id,source,app_version,props"
        assert len(lines) - 1 == len(events_of(app))
        owner_uid = repo.get_account(owner).uid
        assert owner_uid is not None and owner_uid in csv_resp.text

        jsonl = await c.get("/api/admin/analytics/export.jsonl")
        items = [json.loads(line) for line in jsonl.text.strip().split("\n")]
        assert len(items) == len(events_of(app)) and all(isinstance(i["props"], dict) for i in items)
        sent = [i for i in items if i["name"] == "message_sent"]
        assert sent[0]["distinct_id"] == owner_uid and sent[0]["story_id"] == story["id"]
        assert sent[0]["props"]["mode"] == "story"
        future = await c.get("/api/admin/analytics/export.jsonl?since=2099-01-01")
        assert future.status_code == 200 and future.text == ""
        today = await c.get("/api/admin/analytics/export.csv?since=2020-01-01&until=2099-12-31")
        assert len(today.text.strip().split("\n")) == len(lines)

        # Tài khoản tắt chia sẻ: không còn trong bản xuất.
        await ok(await m.patch("/api/account", json={"analytics_opt_out": True}))
        member_uid = repo.get_account(member).uid
        assert member_uid is not None
        assert member_uid not in (await c.get("/api/admin/analytics/export.csv")).text


async def test_posthog_enabled_app_marks_events_pending(tmp_path: Path) -> None:
    settings = Settings(**{**make_settings(tmp_path).__dict__, "posthog_key": "phc_test"})
    posthog = FakePostHog()
    app = create_app(settings, FakeLLM(replies=[REPLY]), posthog_transport=posthog.transport())
    async with app.router.lifespan_context(app):  # task gửi nền chạy thật (start_forwarder mặc định)
        owner = ensure_owner_password(repo_of(app))
        accept_terms(repo_of(app), owner)
        async with client_for(app, owner) as c:
            await ok(await c.post("/api/personas", json={"name": "Ngọc", "gender": "female"}))
            assert (await ok(await c.get("/api/admin/analytics/summary")))["posthog_enabled"] is True
        for _ in range(200):
            await asyncio.sleep(0.01)
            if {e["posthog_state"] for e in events_of(app)} == {"sent"}:
                break
        assert {e["posthog_state"] for e in events_of(app)} == {"sent"}
    sent = [i["event"] for b in posthog.batches for i in b["batch"]]
    assert "persona_created" in sent
