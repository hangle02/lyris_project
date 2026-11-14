"""Tuân thủ khi ra mắt (docs/compliance.md): luật an toàn trong prompt, văn bản pháp lý, đồng ý điều khoản, báo cáo
nội dung AI, xoá tài khoản và xuất dữ liệu. Mọi luật được kiểm với hai tài khoản (`tests/twoaccounts.py`):
B không báo cáo / xoá / xuất được dữ liệu của A và ngược lại."""
from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio

from lyris.api.app import create_app
from lyris.auth import clock, store
from lyris.auth import setup as owner_setup
from lyris.compliance import legal
from lyris.llm.fake import FakeLLM
from lyris.prompt.builder import build_prompt
from lyris.prompt.templates import en, vi
from lyris.studio.draft import build_draft_messages
from tests.authutil import (
    MEMBER_PASSWORD,
    OWNER_PASSWORD,
    anon_client,
    client_for,
    ensure_owner_password,
    repo_of,
)
from tests.test_prompt import assistant, make_card, make_persona, make_story, user
from tests.twoaccounts import (
    PRIVATE_NAME,
    PUBLIC_NAME,
    PUBLIC_SECRET,
    World,
    card_body,
    make_settings,
    ok,
    png_bytes,
    send,
    two_accounts,
)

B_SECRET = "Chuyện riêng của Mai: chiếc vòng bạc dưới gối."
B_CARD = "Nhân vật của Mai"
B_LORE = "Sổ thế giới riêng của Mai."
B_NOTE = "Câu này làm mình khó chịu."
PNG = {"content": png_bytes(), "headers": {"Content-Type": "image/png"}}


@pytest_asyncio.fixture
async def world(tmp_path: Path) -> AsyncIterator[World]:
    async with two_accounts(tmp_path) as w:
        yield w


def rows(w: World, sql: str, *params: object) -> list[tuple[object, ...]]:
    with w.repo.locked() as conn:
        return [tuple(r) for r in conn.execute(sql, params).fetchall()]


def count(w: World, sql: str, *params: object) -> int:
    return int(rows(w, sql, *params)[0][0])


# ---------------------------------------------------------------------------- luật an toàn trong prompt


@pytest.mark.parametrize("language", ["vi", "en"])
@pytest.mark.parametrize("mode", ["story", "dm"])
@pytest.mark.parametrize("pov", ["third", "first"])
def test_safety_rule_in_story_and_dm_prompts(language: str, mode: str, pov: str) -> None:
    card = make_card()
    history = [assistant(0, "Chào."), user(1, "Chào cậu.")]
    built = build_prompt(card, make_persona(), make_story(language=language, mode=mode, pov=pov), history)
    system = built.messages[0].content
    tpl = vi if language == "vi" else en
    assert tpl.safety_rule(card.name) in system
    under_18 = "người dưới 18 tuổi" if language == "vi" else "anyone under 18"
    assert system.count(under_18) == 1


def test_safety_rule_wording() -> None:
    """Đủ các ý của quyết định nội dung mặc định (docs/compliance.md §1), và ngắn (ngân sách prompt)."""
    v, e = vi.safety_rule("Lạc Dương"), en.safety_rule("Lạc Dương")
    for needle in ("tình dục", "dưới 18 tuổi", "máu me", "tự hại", "quan tâm", "lảng đi", "ghen tuông", "chiếm hữu"):
        assert needle in v, needle
    for needle in ("sexual", "under 18", "gore", "self-harm", "with care", "deflects in character", "possessiveness"):
        assert needle in e, needle
    assert len(v) < 400 and len(e) < 400


@pytest.mark.parametrize("language", ["vi", "en"])
def test_safety_rule_in_draft_prompt(language: str) -> None:
    messages = build_draft_messages(idea="x", language=language, gender=None, style_profile=None, styles=[])  # type: ignore[arg-type]
    system = messages[0].content
    if language == "vi":
        assert "tuyệt đối không có gì tình dục liên quan tới người dưới 18 tuổi" in system
        assert "viết phiên bản an toàn của ý tưởng" in system
    else:
        assert "never anything sexual involving anyone under 18" in system
        assert "write a safe version of it" in system


@pytest.mark.parametrize("language", ["vi", "en"])
def test_safety_line_in_reply_suggestions(language: str) -> None:
    from lyris.state.suggest import build_messages

    history = [assistant(0, "Chào."), user(1, "Chào cậu.")]
    messages = build_messages(card=make_card(), persona=make_persona(), story=make_story(language=language), history=history)
    system = messages[0].content
    assert ("không tình dục hay gợi dục" if language == "vi" else "nothing sexual or suggestive") in system


# ---------------------------------------------------------------------------- văn bản pháp lý


def test_legal_files_state_the_current_version() -> None:
    for doc in legal.LEGAL_DOCS:
        text = legal.load(doc).markdown
        assert legal.LEGAL_VERSION in text, doc
        assert "## English" in text, doc  # tiếng Việt trước, bản tiếng Anh sau
        assert "[ĐIỀN EMAIL LIÊN HỆ]" in text, doc  # chỗ nhóm điền email liên hệ, đánh dấu rõ


async def test_legal_is_public_even_in_setup_mode(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path), FakeLLM(replies=["Chào."]))
    async with app.router.lifespan_context(app):
        async with anon_client(app) as c:
            assert (await c.get("/api/stories")).json()["code"] == "setup_required"
            for doc in ("terms", "privacy"):
                resp = await c.get(f"/api/legal/{doc}")
                assert resp.status_code == 200, resp.text
                body = resp.json()
                assert body["doc"] == doc and body["version"] == legal.LEGAL_VERSION
                assert body["markdown"] == legal.load(doc).markdown  # type: ignore[arg-type]
            assert (await c.get("/api/legal/cookies")).status_code == 422
            assert (await c.post("/api/legal/terms")).status_code == 405


# ---------------------------------------------------------------------------- đồng ý điều khoản


async def test_signup_requires_terms(world: World) -> None:
    w = world
    invite = await ok(await w.a.post("/api/admin/invites", json={"note": "Lan"}))
    code = invite["code"]
    body = {"invite_code": code, "handle": "lan", "display_name": "Lan", "password": MEMBER_PASSWORD}
    async with anon_client(w.app) as c:
        for extra in ({}, {"accept_terms": False}):
            resp = await c.post("/api/auth/signup", json={**body, **extra})
            assert resp.status_code == 400 and resp.json()["code"] == "terms_required", resp.text
        old = await c.post("/api/auth/signup", json={**body, "accept_terms": True, "terms_version": "2000-01-01"})
        assert old.status_code == 409 and old.json()["code"] == "terms_outdated"
        assert count(w, "SELECT COUNT(*) FROM accounts WHERE handle = 'lan'") == 0
        assert count(w, "SELECT COUNT(*) FROM invites WHERE used_at IS NOT NULL") == 0  # mã chưa bị dùng
        resp = await c.post(
            "/api/auth/signup", json={**body, "accept_terms": True, "terms_version": legal.LEGAL_VERSION}
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["account"]["terms_required"] is False
        assert resp.json()["legal_version"] == legal.LEGAL_VERSION
    accepted = rows(w, "SELECT terms_accepted_at, privacy_version FROM accounts WHERE handle = 'lan'")[0]
    assert accepted[0] is not None and accepted[1] == legal.LEGAL_VERSION


async def test_owner_setup_requires_terms(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path), FakeLLM(replies=["Chào."]))
    async with app.router.lifespan_context(app):
        repo = repo_of(app)
        with repo.transaction():
            code = owner_setup.write_new_code(repo.conn, clock.now())
        body = {"setup_code": code, "password": OWNER_PASSWORD, "display_name": "Chủ", "handle": "chu"}
        async with anon_client(app) as c:
            resp = await c.post("/api/auth/setup-owner", json=body)
            assert resp.status_code == 400 and resp.json()["code"] == "terms_required"
            with repo.locked() as conn:
                assert store.owner_needs_setup(conn)  # chưa đặt mật khẩu, mã vẫn dùng được
            done = await c.post("/api/auth/setup-owner", json={**body, "accept_terms": True})
            assert done.status_code == 200, done.text
            assert done.json()["account"]["terms_required"] is False
        with repo.locked() as conn:
            owner = store.owner(conn)
            assert owner is not None
            assert legal.accepted_version(conn, owner.id)[1] == legal.LEGAL_VERSION


async def test_existing_account_is_asked_once(world: World, monkeypatch: pytest.MonkeyPatch) -> None:
    """Tài khoản có từ trước (chưa đồng ý bản nào): `terms_required` cho tới khi đồng ý; bản mới thì hỏi lại."""
    w = world
    me = (await w.b.get("/api/auth/me")).json()
    assert me["account"]["terms_required"] is True and me["legal_version"] == legal.LEGAL_VERSION
    account = (await w.b.get("/api/account")).json()
    assert account["terms_required"] is True and account["terms_accepted_at"] is None
    refused = await w.b.post("/api/account/terms", json={"accept_terms": False, "version": legal.LEGAL_VERSION})
    assert refused.status_code == 422
    stale = await w.b.post("/api/account/terms", json={"accept_terms": True, "version": "2000-01-01"})
    assert stale.status_code == 409
    assert (await w.b.post("/api/account/terms", json={"accept_terms": True})).status_code == 422
    done = await ok(await w.b.post("/api/account/terms", json={"accept_terms": True, "version": legal.LEGAL_VERSION}))
    assert done["terms_required"] is False and done["privacy_version"] == legal.LEGAL_VERSION
    assert (await w.b.get("/api/auth/me")).json()["account"]["terms_required"] is False
    assert (await w.a.get("/api/auth/me")).json()["account"]["terms_required"] is True  # A chưa đồng ý
    monkeypatch.setattr(legal, "LEGAL_VERSION", "2099-01-01")
    assert (await w.b.get("/api/auth/me")).json()["account"]["terms_required"] is True


# ---------------------------------------------------------------------------- báo cáo nội dung


async def test_report_without_consent_stores_reason_only(world: World) -> None:
    w = world
    out = await ok(await w.b.post(f"/api/messages/{w.b_message}/report", json={"reason": "sexual", "note": f"  {B_NOTE} "}))
    assert out == {"id": out["id"], "reason": "sexual", "shared_text": False, "status": "open"}
    row = rows(w, "SELECT reporter_id, message_id, reason, note, shared_text, message_text, public_card_id FROM content_reports")
    assert row == [(w.b_id, w.b_message, "sexual", B_NOTE, 0, None, w.a_public)]  # bản sao -> card công khai gốc
    listed = await ok(await w.a.get("/api/admin/reports"))
    assert len(listed) == 1
    report = listed[0]
    assert report["message_text"] is None and report["shared_text"] is False
    assert report["public_card_id"] == w.a_public and report["public_card_name"] == PUBLIC_NAME
    assert report["public_card_creator"] == w.a_handle
    # Không lộ ai báo cáo, story nào, tin nhắn nào.
    assert not {"reporter_id", "story_id", "message_id", "reporter_handle"} & report.keys()
    assert "mai" not in json.dumps(report)
    # Số liệu: lý do đã đổi sang bảng sự kiện, không có chữ nào, và không gắn ai (người quản lý không biết ai báo
    # cáo, kể cả qua bản xuất số liệu): không tài khoản, thiết bị, lượt hay story, không gửi PostHog.
    events = rows(
        w, "SELECT account_id, anon_id, session_id, story_id, posthog_state, props_json FROM analytics_events"
        " WHERE name = 'content_reported'",
    )
    assert events == [(None, "", "", None, "local", json.dumps({"mode": "story", "reason": "sexual_content", "target": "message"}, separators=(",", ":")))]


async def test_report_with_consent_snapshots_the_reply(world: World) -> None:
    w = world
    await ok(await w.b.post(f"/api/messages/{w.b_message}/report", json={"reason": "violent"}))
    again = await ok(await w.b.post(
        f"/api/messages/{w.b_message}/report", json={"reason": "minor_safety", "share_text": True}
    ))
    assert again["shared_text"] is True
    assert count(w, "SELECT COUNT(*) FROM content_reports") == 1  # báo cáo lại thì cập nhật
    visible = w.repo.get_message(w.b_message, account_id=w.b_id).visible_content
    listed = await ok(await w.a.get("/api/admin/reports?status=open"))
    assert [(r["reason"], r["message_text"]) for r in listed] == [("minor_safety", visible)]
    reviewed = await ok(await w.a.patch(f"/api/admin/reports/{listed[0]['id']}", json={"status": "reviewed"}))
    assert reviewed["status"] == "reviewed" and reviewed["reviewed_at"] is not None
    assert await ok(await w.a.get("/api/admin/reports?status=open")) == []
    assert (await w.a.patch("/api/admin/reports/999", json={"status": "dismissed"})).status_code == 404
    assert (await w.a.get("/api/admin/reports?status=nope")).status_code == 422
    # Tên nhân vật chỉ hiện khi nó còn công khai.
    await ok(await w.a.put(f"/api/cards/{w.a_public}", json=card_body(PUBLIC_NAME, visibility="private")))
    assert (await ok(await w.a.get("/api/admin/reports")))[0]["public_card_name"] is None


async def test_report_rules(world: World) -> None:
    w = world
    user_msg = next(m.id for m in w.repo.active_messages(w.b_story) if m.role == "user")
    assert (await w.b.post(f"/api/messages/{user_msg}/report", json={"reason": "other"})).status_code == 422
    assert (await w.b.post(f"/api/messages/{w.b_message}/report", json={"reason": "spam"})).status_code == 422
    long = await w.b.post(f"/api/messages/{w.b_message}/report", json={"reason": "other", "note": "x" * 301})
    assert long.status_code == 422
    assert (await w.b.post(f"/api/messages/{w.b_message}/report", json={"reason": "other", "x": 1})).status_code == 422
    # Tách dữ liệu: không ai báo cáo được tin nhắn trong story của người khác (404, không ghi gì).
    for client, message in ((w.b, w.a_message), (w.a, w.b_message), (w.b, 99999)):
        resp = await client.post(f"/api/messages/{message}/report", json={"reason": "other", "share_text": True})
        assert resp.status_code == 404, resp.text
    assert count(w, "SELECT COUNT(*) FROM content_reports") == 0
    # Thành viên không xem được danh sách.
    assert (await w.b.get("/api/admin/reports")).json()["code"] == "owner_only"
    # Story bằng nhân vật riêng của chính mình: không ghi card nào.
    await ok(await w.a.post(f"/api/messages/{w.a_message}/report", json={"reason": "hateful"}))
    assert rows(w, "SELECT public_card_id FROM content_reports") == [(None,)]  # card của A, không phải bản sao


# ---------------------------------------------------------------------------- xoá tài khoản


async def _give_b_everything(w: World) -> dict[str, int]:
    """B có thêm: avatar, ảnh bìa, card công khai (kèm sổ thế giới, ảnh) mà A đã chơi bằng bản sao, tin nhắn riêng,
    báo cáo có chia sẻ câu trả lời, cài đặt persona mặc định."""
    await ok(await w.b.put("/api/account/avatar", **PNG))
    await ok(await w.b.put("/api/account/banner", **PNG))
    await ok(await w.b.put(f"/api/personas/{w.b_persona}/avatar", **PNG))
    card = await ok(await w.b.post("/api/cards", json={"card": card_body(B_CARD, visibility="public", secrets=B_SECRET)}))
    await ok(await w.b.put(f"/api/cards/{card['id']}/avatar", **PNG))
    await ok(await w.b.post(f"/api/cards/{card['id']}/lore", json={"title": "Vòng bạc", "keys": ["vòng"], "content": B_LORE}))
    events = await send(w.b, w.b_story, B_SECRET)
    assert events[-1][0] == "done"
    await ok(await w.b.post(f"/api/messages/{w.b_message}/report", json={"reason": "other", "note": B_NOTE, "share_text": True}))
    await ok(await w.b.put("/api/settings", json={"default_persona_id": w.b_persona}))
    a_story_on_b = await ok(await w.a.post("/api/stories", json={"card_id": card["id"], "persona_id": w.a_persona}))
    return {"b_card": card["id"], "a_copy": a_story_on_b["card_id"], "a_story_on_b": a_story_on_b["id"]}


ACCOUNT_COLUMNS = (
    ("personas", "account_id"),
    ("character_cards", "account_id"),
    ("character_cards", "origin_account_id"),
    ("stories", "account_id"),
    ("sessions", "account_id"),
    ("invites", "created_by"),
    ("invites", "used_by"),
    ("analytics_events", "account_id"),
    ("content_reports", "reporter_id"),
    ("accounts", "invited_by"),
    ("accounts", "id"),
)


async def test_member_deletes_account_and_everything_goes(world: World) -> None:
    w = world
    extra = await _give_b_everything(w)
    b_handle = "mai"
    b_files = {
        str(r[0])
        for r in rows(w, "SELECT avatar FROM accounts WHERE id = ? UNION SELECT banner FROM accounts WHERE id = ?"
                      " UNION SELECT avatar FROM personas WHERE account_id = ? UNION SELECT avatar FROM character_cards"
                      " WHERE account_id = ?", w.b_id, w.b_id, w.b_id, w.b_id)
        if r[0]
    }
    assert len(b_files) == 5 and all((w.avatars_dir / n).exists() for n in b_files)
    a_files = {p.name for p in w.avatars_dir.iterdir()} - b_files
    a_before = {
        table: count(w, f"SELECT COUNT(*) FROM {table} WHERE account_id = ?", w.a_id)
        for table in ("personas", "character_cards", "stories")
    }
    a_messages = count(w, "SELECT COUNT(*) FROM messages WHERE story_id IN (SELECT id FROM stories WHERE account_id = ?)", w.a_id)
    b_stories = [int(r[0]) for r in rows(w, "SELECT id FROM stories WHERE account_id = ?", w.b_id)]

    wrong = await w.b.request("DELETE", "/api/account", json={"password": "sai mật khẩu"})
    assert wrong.status_code == 400 and wrong.json()["code"] == "bad_password"
    # B gõ mật khẩu của A: vẫn là mật khẩu sai của B, không xoá được A.
    assert (await w.b.request("DELETE", "/api/account", json={"password": OWNER_PASSWORD})).status_code == 400
    assert (await w.b.request("DELETE", "/api/account")).status_code == 422
    assert count(w, "SELECT COUNT(*) FROM accounts") == 2

    resp = await w.b.request("DELETE", "/api/account", json={"password": MEMBER_PASSWORD})
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"deleted": True, "setup_required": False}
    assert "lyris_session=;" in resp.headers.get("set-cookie", "")
    assert (await w.b.get("/api/stories")).status_code == 401

    # Không còn dòng nào gắn với B.
    for table, column in ACCOUNT_COLUMNS:
        assert count(w, f"SELECT COUNT(*) FROM {table} WHERE {column} = ?", w.b_id) == 0, (table, column)
    for story in b_stories:
        for table in ("messages", "memories", "state_events", "jobs", "lore_hits"):
            assert count(w, f"SELECT COUNT(*) FROM {table} WHERE story_id = ?", story) == 0, table
    assert count(w, "SELECT COUNT(*) FROM auth_attempts WHERE handle IN (?, ?)", b_handle, store.account_key(w.b_id)) == 0
    assert count(w, "SELECT COUNT(*) FROM character_cards WHERE id IN (?, ?)", w.b_copy, extra["b_card"]) == 0
    assert count(w, "SELECT COUNT(*) FROM lore_entries WHERE card_id IN (?, ?)", w.b_copy, extra["b_card"]) == 0
    # Chữ riêng của B không còn ở đâu trong DB (kể cả báo cáo đã chia sẻ: chỉ còn lý do).
    assert B_NOTE not in w.dump()
    # A đã chơi bằng bản sao card công khai của B: bản sao (kèm sổ thế giới đã chụp) là dữ liệu của A, ở lại nhưng
    # không còn ghi người tạo. Ngoài bản sao đó, chữ của B không còn ở đâu.
    assert count(w, "SELECT COUNT(*) FROM messages WHERE raw_content LIKE ?", f"%{B_SECRET}%") == 0
    assert rows(w, "SELECT id FROM character_cards WHERE secrets = ?", B_SECRET) == [(extra["a_copy"],)]
    assert rows(w, "SELECT card_id FROM lore_entries WHERE content = ?", B_LORE) == [(extra["a_copy"],)]
    assert rows(w, "SELECT reporter_id, message_id, story_id, note, shared_text, message_text, reason FROM content_reports") == [
        (None, None, None, "", 0, None, "other")
    ]
    copy = rows(w, "SELECT account_id, origin_card_id, origin_account_id, story_copy FROM character_cards WHERE id = ?", extra["a_copy"])
    assert copy == [(w.a_id, None, None, 1)]
    assert (await w.a.get(f"/api/stories/{extra['a_story_on_b']}")).status_code == 200
    # Sự kiện: tách khỏi tài khoản, có một dòng account_deleted không gắn tài khoản.
    assert count(w, "SELECT COUNT(*) FROM analytics_events WHERE name = 'account_deleted' AND account_id IS NULL") == 1
    # File ảnh của B bị xoá, của A còn nguyên.
    assert not any((w.avatars_dir / n).exists() for n in b_files)
    assert all((w.avatars_dir / n).exists() for n in a_files)
    # Dữ liệu của A không đổi.
    for table, n in a_before.items():
        assert count(w, f"SELECT COUNT(*) FROM {table} WHERE account_id = ?", w.a_id) == n
    assert count(w, "SELECT COUNT(*) FROM messages WHERE story_id IN (SELECT id FROM stories WHERE account_id = ?)", w.a_id) >= a_messages
    with w.repo.locked() as conn:
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


async def test_delete_password_attempts_are_limited(world: World) -> None:
    w = world
    for _ in range(5):
        assert (await w.b.request("DELETE", "/api/account", json={"password": "sai"})).status_code == 400
    blocked = await w.b.request("DELETE", "/api/account", json={"password": MEMBER_PASSWORD})
    assert blocked.status_code == 429
    assert count(w, "SELECT COUNT(*) FROM accounts WHERE id = ?", w.b_id) == 1


async def test_owner_cannot_delete_while_members_exist(world: World) -> None:
    w = world
    before = w.dump()
    resp = await w.a.request("DELETE", "/api/account", json={"password": OWNER_PASSWORD})
    assert resp.status_code == 409
    assert "thành viên" in resp.json()["detail"] and "tự xoá" in resp.json()["detail"]
    assert w.dump() == before  # kiểm trước khi so mật khẩu: không ghi lần thử nào


async def test_owner_alone_deletes_and_lyris_returns_to_setup(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    app = create_app(make_settings(tmp_path), FakeLLM(replies=["Chào."]))
    async with app.router.lifespan_context(app):
        repo = repo_of(app)
        owner_id = ensure_owner_password(repo)
        old_uid = repo.get_account(owner_id).uid
        async with client_for(app, owner_id) as c:
            stories = await ok(await c.get("/api/stories"))
            assert stories  # story seed
            capsys.readouterr()
            resp = await c.request("DELETE", "/api/account", json={"password": OWNER_PASSWORD})
            assert resp.status_code == 200, resp.text
            assert resp.json() == {"deleted": True, "setup_required": True}
            assert "mã thiết lập" in capsys.readouterr().err
            me = (await c.get("/api/auth/me")).json()
            assert me["setup_required"] is True and me["setup_needs_profile"] is True
        with repo.locked() as conn:
            # SQLite có thể cấp lại id cũ cho chủ máy mới; uid thì luôn mới.
            assert conn.execute("SELECT COUNT(*) FROM accounts WHERE uid = ?", (old_uid,)).fetchone()[0] == 0
            assert conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0] == 1
            for table in ("stories", "personas", "character_cards", "sessions", "messages"):
                assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0, table
            new_owner = store.owner(conn)
            assert new_owner is not None and new_owner.password is None
            assert store.read_setup(conn) is not None


# ---------------------------------------------------------------------------- xuất dữ liệu


async def test_export_contains_all_own_data_and_nothing_else(world: World) -> None:
    w = world
    extra = await _give_b_everything(w)
    resp = await w.b.get("/api/account/export")
    assert resp.status_code == 200
    assert resp.headers["content-disposition"].startswith('attachment; filename="lyris-mai-')
    data = resp.json()
    text = resp.text
    assert data["format"] == "lyris-account-export" and data["account"]["handle"] == "mai"
    assert "password_hash" not in text and "token_hash" not in text and "prompt_snapshot" not in text
    # Đủ: mọi persona, card (kèm sổ thế giới), story, tin nhắn (cả biến thể), ký ức của B.
    assert {p["id"] for p in data["personas"]} == {int(r[0]) for r in rows(w, "SELECT id FROM personas WHERE account_id = ?", w.b_id)}
    own_cards = {int(r[0]) for r in rows(w, "SELECT id FROM character_cards WHERE account_id = ? AND story_copy = 0", w.b_id)}
    assert {c["id"] for c in data["characters"]} == own_cards == {extra["b_card"]}
    assert data["characters"][0]["secrets"] == B_SECRET and data["characters"][0]["lore"][0]["content"] == B_LORE
    assert data["characters"][0]["avatar_file"]
    assert [c["id"] for c in data["story_characters"]] == [w.b_copy]
    assert data["story_characters"][0]["creator_handle"] == w.a_handle
    assert {s["id"] for s in data["stories"]} == {w.b_story}
    n_messages = count(w, "SELECT COUNT(*) FROM messages WHERE story_id = ?", w.b_story)
    assert len(data["stories"][0]["messages"]) == n_messages
    assert any(B_SECRET in m["content"] for m in data["stories"][0]["messages"])
    assert data["reports"][0]["note"] == B_NOTE and data["reports"][0]["shared_text"] is True
    assert data["sessions"] and data["usage_events"]
    assert data["account"]["avatar_file"] and data["account"]["banner_file"]
    # Không có gì của A: card riêng tư, bí mật và sổ thế giới của card công khai (B chỉ thấy phần công khai), persona.
    for secret in (PRIVATE_NAME, PUBLIC_SECRET, "Lâm Vãn"):
        assert secret not in text, secret
    hidden = {"personality", "background", "goals", "secrets", "example_dialogues", "creator_notes", "lore", "extensions"}
    assert not hidden & data["story_characters"][0].keys()
    # Sự kiện data_exported của B.
    assert count(w, "SELECT COUNT(*) FROM analytics_events WHERE name = 'data_exported' AND account_id = ?", w.b_id) == 1


async def test_owner_export_does_not_include_members(world: World) -> None:
    w = world
    await _give_b_everything(w)
    text = (await w.a.get("/api/account/export")).text
    data = json.loads(text)
    assert {s["id"] for s in data["stories"]} == {int(r[0]) for r in rows(w, "SELECT id FROM stories WHERE account_id = ?", w.a_id)}
    assert "Mai" not in {p["name"] for p in data["personas"]}
    assert B_NOTE not in text and B_LORE not in text
    # A chơi bằng bản sao card công khai của B: chỉ thấy phần công khai, không có bí mật của B.
    assert B_SECRET not in json.dumps(data["story_characters"], ensure_ascii=False)
    assert all(B_SECRET not in json.dumps(s["messages"], ensure_ascii=False) for s in data["stories"])


# ---------------------------------------------------------------------------- migration 0010, số liệu khi xoá


def test_migration_0010_on_a_v9_db(tmp_path: Path) -> None:
    """0010 chỉ thêm cột và bảng: dòng cũ giữ nguyên, chưa ai đồng ý điều khoản, CHECK chặn bản chụp không có
    đồng ý chia sẻ."""
    import sqlite3

    from lyris.db.connection import connect, migrate

    conn = connect(tmp_path / "v9.db")
    try:
        assert migrate(conn, target=9) == 9
        conn.execute("INSERT INTO accounts (uid, handle, display_name, role) VALUES ('u1', 'mai', 'Mai', 'member')")
        before = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
        assert migrate(conn) == 11
        assert migrate(conn) == 11  # chạy lại không làm gì
        assert conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0] == before
        terms = [tuple(r) for r in conn.execute("SELECT terms_accepted_at, privacy_version FROM accounts")]
        assert terms == [(None, None)] * before
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        insert = (
            "INSERT INTO content_reports (created_at, updated_at, reason, shared_text, message_text)"
            " VALUES ('t', 't', ?, ?, ?)"
        )
        conn.execute(insert, ("other", 1, "chữ"))
        for bad in (("other", 0, "chữ"), ("spam", 0, None)):
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(insert, bad)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO content_reports (created_at, updated_at, reason, note) VALUES ('t', 't', 'other', ?)",
                ("x" * 301,),
            )
    finally:
        conn.close()


async def test_deleted_account_events_are_not_forwarded(world: World) -> None:
    from lyris.analytics import store as analytics_store

    w = world
    with w.repo.transaction():
        analytics_store.insert(
            w.repo.conn, ts=clock.iso(clock.now()), name="persona_created", account_id=w.b_id, anon_id="x",
            session_id="s", story_id=None, props_json="{}", source="server", app_version="t", pending=True,
        )
    resp = await w.b.request("DELETE", "/api/account", json={"password": MEMBER_PASSWORD})
    assert resp.status_code == 200
    assert count(w, "SELECT COUNT(*) FROM analytics_events WHERE posthog_state = 'pending'") == 0
    # Còn lại để đếm, nhưng đã đổi anon_id / session_id (PostHog từng nối anon_id cũ với tài khoản).
    assert count(w, "SELECT COUNT(*) FROM analytics_events WHERE name = 'persona_created' AND anon_id = 'x'") == 0
    assert count(w, "SELECT COUNT(*) FROM analytics_events WHERE session_id = 's'") == 0
    assert count(w, "SELECT COUNT(*) FROM analytics_events WHERE name = 'persona_created' AND account_id IS NULL") >= 1
