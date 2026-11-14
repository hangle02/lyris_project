"""Phase 4b (docs/auth.md §2.5, §4.1, §8.1): mọi route phải được xếp loại, và cổng đăng nhập đúng với từng loại.

Danh sách route lấy từ `app.openapi()["paths"]` (FastAPI 0.162: `app.routes` cấp ngoài có `_IncludedRouter`
không có `.path`), có kiểm số lượng. Route mới chưa xếp loại thì test đỏ; route đã bỏ mà còn trong bảng
cũng đỏ.

Loại:
- `open`: không qua `current_account` (đúng 4 route của §6.1);
- `pending`: cần đăng nhập, cho phép tài khoản đang chờ đổi mật khẩu (`logout`, `change-password`);
- `member`: cần đăng nhập (Đ), dữ liệu của chính mình;
- `public_read`: cần đăng nhập, đọc thêm phần công khai của tài khoản khác (profile, ảnh, teaser);
- `owner`: chỉ chủ máy (403 `owner_only`);
- `optional`: đăng nhập là tuỳ chọn (`POST /api/events`, docs/tracking-plan.md): chưa đăng nhập vẫn 202 nhưng chỉ
  nhận vài sự kiện trước đăng nhập; test riêng ở `test_analytics_api.py`.
- `public`: không cần đăng nhập, kể cả lúc chủ máy chưa thiết lập (văn bản pháp lý, docs/compliance.md §3); chỉ đọc
  file chung, không có dữ liệu tài khoản. Test riêng ở `test_compliance.py`.
"""
from __future__ import annotations

import re
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Literal

import httpx
import pytest
from fastapi import FastAPI

from lyris.api.app import create_app
from lyris.api.routes_analytics import OPTIONAL_AUTH_ROUTES
from lyris.api.routes_auth import OPEN_ROUTES
from lyris.api.routes_compliance import PUBLIC_ROUTES
from lyris.auth import clock, store
from lyris.compliance.legal import LEGAL_VERSION
from lyris.config import Settings
from lyris.llm.fake import FakeLLM
from tests.authutil import add_member, anon_client, client_for, ensure_owner_password, repo_of

Rule = Literal["open", "pending", "member", "public_read", "owner", "optional", "public"]

ROUTE_RULES: dict[tuple[str, str], Rule] = {
    # ---- /api/auth (§6.2)
    ("GET", "/api/auth/me"): "open",
    ("POST", "/api/auth/setup-owner"): "open",
    ("POST", "/api/auth/login"): "open",
    ("POST", "/api/auth/signup"): "open",
    ("POST", "/api/auth/logout"): "pending",
    ("POST", "/api/auth/change-password"): "pending",
    ("POST", "/api/auth/logout-all"): "member",
    # ---- /api/admin (§6.3)
    ("GET", "/api/admin/accounts"): "owner",
    ("POST", "/api/admin/accounts/{account_id}/reset-password"): "owner",
    ("POST", "/api/admin/accounts/{account_id}/disable"): "owner",
    ("POST", "/api/admin/accounts/{account_id}/enable"): "owner",
    ("GET", "/api/admin/invites"): "owner",
    ("POST", "/api/admin/invites"): "owner",
    ("DELETE", "/api/admin/invites/{invite_id}"): "owner",
    # ---- event tracking (docs/tracking-plan.md)
    ("GET", "/api/admin/analytics/summary"): "owner",
    ("GET", "/api/admin/analytics/export.csv"): "owner",
    ("GET", "/api/admin/analytics/export.jsonl"): "owner",
    ("POST", "/api/events"): "optional",
    # ---- tuân thủ (docs/compliance.md)
    ("GET", "/api/legal/{doc}"): "public",
    ("POST", "/api/messages/{message_id}/report"): "member",
    ("POST", "/api/cards/{card_id}/report"): "member",
    ("POST", "/api/admin/cards/{card_id}/unpublish"): "owner",
    ("GET", "/api/admin/reports"): "owner",
    ("PATCH", "/api/admin/reports/{report_id}"): "owner",
    ("DELETE", "/api/account"): "member",
    ("GET", "/api/account/export"): "member",
    ("POST", "/api/account/terms"): "member",
    # ---- máy
    ("GET", "/api/health"): "member",  # thành viên không thấy tên model (§4.1)
    ("GET", "/api/system"): "owner",
    ("GET", "/api/settings"): "member",
    ("PUT", "/api/settings"): "member",  # đổi default_chat_model: chỉ chủ máy (test riêng)
    ("GET", "/api/styles"): "member",
    ("GET", "/api/lore/status"): "member",
    ("GET", "/api/templates"): "member",
    ("POST", "/api/templates/{slug}/install"): "member",
    ("GET", "/api/templates/{slug}/image"): "member",
    # ---- story
    ("GET", "/api/stories"): "member",
    ("POST", "/api/stories"): "member",
    ("GET", "/api/stories/defaults"): "member",
    ("GET", "/api/stories/{story_id}"): "member",
    ("PATCH", "/api/stories/{story_id}"): "member",  # model_name: chỉ chủ máy (test riêng)
    ("DELETE", "/api/stories/{story_id}"): "member",
    ("GET", "/api/stories/{story_id}/messages"): "member",
    ("POST", "/api/stories/{story_id}/messages"): "member",
    ("POST", "/api/stories/{story_id}/reply"): "member",
    ("GET", "/api/stories/{story_id}/extras"): "member",
    ("GET", "/api/stories/{story_id}/lore"): "member",
    ("GET", "/api/stories/{story_id}/timeline"): "member",
    ("DELETE", "/api/stories/{story_id}/memories/{memory_id}"): "member",
    ("POST", "/api/stories/{story_id}/state/rebuild"): "member",
    ("POST", "/api/stories/{story_id}/suggestions"): "member",
    ("POST", "/api/messages/{message_id}/regenerate"): "member",
    ("POST", "/api/messages/{message_id}/variant"): "member",
    ("PATCH", "/api/messages/{message_id}"): "member",
    ("DELETE", "/api/messages/{message_id}"): "member",
    ("PUT", "/api/messages/{message_id}/feedback"): "member",
    ("GET", "/api/messages/{message_id}/snapshot"): "member",
    # ---- card
    ("GET", "/api/cards"): "member",
    ("POST", "/api/cards"): "member",
    ("POST", "/api/cards/import"): "member",
    ("POST", "/api/cards/draft"): "member",
    ("POST", "/api/cards/preview-prompt"): "member",
    ("POST", "/api/cards/test-chat"): "member",
    ("GET", "/api/cards/{card_id}"): "member",
    ("PUT", "/api/cards/{card_id}"): "member",
    ("DELETE", "/api/cards/{card_id}"): "member",
    ("POST", "/api/cards/{card_id}/duplicate"): "member",
    ("PUT", "/api/cards/{card_id}/avatar"): "member",
    ("DELETE", "/api/cards/{card_id}/avatar"): "member",
    ("GET", "/api/cards/{card_id}/avatar"): "public_read",
    ("GET", "/api/cards/{card_id}/export"): "member",
    ("GET", "/api/cards/{card_id}/public"): "public_read",  # Phase 4b §6.4
    ("GET", "/api/public-cards"): "public_read",  # Phase 4b §6.4
    ("GET", "/api/cards/{card_id}/lore"): "member",
    ("POST", "/api/cards/{card_id}/lore"): "member",
    ("POST", "/api/cards/{card_id}/lore/import"): "member",
    ("POST", "/api/cards/{card_id}/lore/import-book"): "member",
    ("GET", "/api/cards/{card_id}/lore/summary"): "public_read",
    ("PUT", "/api/cards/{card_id}/lore/{entry_id}"): "member",
    ("PATCH", "/api/cards/{card_id}/lore/{entry_id}"): "member",
    ("DELETE", "/api/cards/{card_id}/lore/{entry_id}"): "member",
    # ---- persona
    ("GET", "/api/personas"): "member",
    ("POST", "/api/personas"): "member",
    ("PUT", "/api/personas/{persona_id}"): "member",
    ("DELETE", "/api/personas/{persona_id}"): "member",
    ("PUT", "/api/personas/{persona_id}/avatar"): "member",
    ("DELETE", "/api/personas/{persona_id}/avatar"): "member",
    ("GET", "/api/personas/{persona_id}/avatar"): "member",
    # ---- tài khoản
    ("GET", "/api/account"): "member",
    ("PUT", "/api/account"): "member",
    ("PATCH", "/api/account"): "member",  # chia sẻ dữ liệu sử dụng (analytics_opt_out)
    ("PUT", "/api/account/avatar"): "member",
    ("DELETE", "/api/account/avatar"): "member",
    ("GET", "/api/account/avatar"): "member",
    ("PUT", "/api/account/banner"): "member",
    ("DELETE", "/api/account/banner"): "member",
    ("GET", "/api/account/banner"): "member",
    ("GET", "/api/accounts/{handle}"): "public_read",
    ("GET", "/api/accounts/{handle}/avatar"): "public_read",
    ("GET", "/api/accounts/{handle}/banner"): "public_read",
}

PARAMS = {"handle": "ban", "slug": "lac-duong", "doc": "terms"}


def all_routes(app: FastAPI) -> set[tuple[str, str]]:
    paths = app.openapi()["paths"]
    return {(method.upper(), path) for path, ops in paths.items() for method in ops}


def concrete(path: str) -> str:
    return re.sub(r"\{(\w+)\}", lambda m: PARAMS.get(m.group(1), "1"), path)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        db_path=tmp_path / "lyris.db",
        ollama_url="http://127.0.0.1:9",
        chat_model="chat-model:test",
        num_ctx=8192,
        avatars_dir=tmp_path / "avatars",
    )


@pytest.fixture
async def app(settings: Settings) -> AsyncIterator[FastAPI]:
    application = create_app(settings, FakeLLM(replies=["Chào."]))
    async with application.router.lifespan_context(application):
        yield application


def test_every_route_is_classified(app: FastAPI) -> None:
    routes = all_routes(app)
    # 70 route trước Phase 4b + 7 /api/auth + 7 /api/admin + /api/public-cards + /api/cards/{id}/public
    # + event tracking: /api/events, PATCH /api/account, 3 /api/admin/analytics
    # + tuân thủ: /api/legal/{doc}, báo cáo tin nhắn, 2 /api/admin/reports, xoá/xuất tài khoản, đồng ý điều khoản
    # + báo cáo nhân vật công khai, ẩn nhân vật công khai (chủ máy)
    assert len(routes) == 100
    missing = sorted(routes - ROUTE_RULES.keys())
    stale = sorted(ROUTE_RULES.keys() - routes)
    assert not missing, f"Route chưa xếp loại trong ROUTE_RULES (docs/auth.md §4.1): {missing}"
    assert not stale, f"ROUTE_RULES còn route không tồn tại: {stale}"
    opened = {route for route, rule in ROUTE_RULES.items() if rule == "open"}
    assert opened == set(OPEN_ROUTES) and len(opened) == 4
    optional = {route for route, rule in ROUTE_RULES.items() if rule == "optional"}
    assert optional == set(OPTIONAL_AUTH_ROUTES) == {("POST", "/api/events")}
    public = {route for route, rule in ROUTE_RULES.items() if rule == "public"}
    assert public == set(PUBLIC_ROUTES) == {("GET", "/api/legal/{doc}")}


async def test_fastapi_docs_are_off(app: FastAPI) -> None:
    async with anon_client(app) as client:
        for path in ("/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"):
            assert (await client.get(path)).status_code == 404, path
    assert app.openapi()["paths"]  # test vẫn đọc được danh sách route


async def test_setup_mode_blocks_everything_but_me_and_setup(app: FastAPI) -> None:
    """Chủ máy chưa có mật khẩu: mọi API trừ `me` và `setup-owner` trả 409 `setup_required` (§2.4)."""
    async with anon_client(app) as client:
        for (method, path), rule in sorted(ROUTE_RULES.items()):
            if path in ("/api/auth/me", "/api/auth/setup-owner") or rule in ("optional", "public"):
                continue
            resp = await client.request(method, concrete(path))
            assert resp.status_code == 409, (method, path, resp.status_code, resp.text)
            assert resp.json()["code"] == "setup_required", (method, path)
        me = await client.get("/api/auth/me")
        assert me.status_code == 200 and me.json()["setup_required"] is True


async def test_no_cookie_is_401_except_open_routes(app: FastAPI) -> None:
    ensure_owner_password(repo_of(app))
    async with anon_client(app) as client:
        for (method, path), rule in sorted(ROUTE_RULES.items()):
            if rule in ("open", "optional", "public"):
                continue
            resp = await client.request(method, concrete(path))
            assert resp.status_code == 401, (method, path, resp.status_code, resp.text)
            body = resp.json()
            assert body["code"] == "auth_required" and body["detail"] == "Bạn cần đăng nhập."
            assert "technical" in body
        assert (await client.get("/api/auth/me")).json() == {
            "setup_required": False, "setup_needs_profile": False, "account": None, "legal_version": LEGAL_VERSION,
            "contact": None,
        }


async def test_member_gets_403_on_owner_routes(app: FastAPI) -> None:
    repo = repo_of(app)
    member = add_member(repo, "mai")
    owner_id = ensure_owner_password(repo)
    async with client_for(app, member) as client, client_for(app, owner_id) as owner:
        for (method, path), rule in sorted(ROUTE_RULES.items()):
            if rule != "owner":
                continue
            resp = await client.request(method, concrete(path))
            assert resp.status_code == 403, (method, path, resp.status_code)
            assert resp.json() == {"detail": "Chỉ chủ máy làm được việc này.", "technical": None, "code": "owner_only"}
            # Chủ máy thì qua được cổng (lỗi nếu có là của route: 404/409/422, không phải 401/403).
            got = await owner.request(method, concrete(path))
            assert got.status_code not in (401, 403), (method, path, got.status_code, got.text)


async def test_pending_account_only_reaches_pending_routes(app: FastAPI) -> None:
    """Đang dùng mật khẩu tạm: mọi route trừ `me`, `change-password`, `logout` trả 403 (§1.2)."""
    repo = repo_of(app)
    member = add_member(repo, "mai")
    with repo.transaction():
        repo.conn.execute("UPDATE accounts SET must_change_password = 1 WHERE id = ?", (member,))
    async with client_for(app, member) as client:
        for (method, path), rule in sorted(ROUTE_RULES.items()):
            if rule in ("open", "pending", "optional", "public"):
                continue
            resp = await client.request(method, concrete(path))
            assert resp.status_code == 403, (method, path, resp.status_code)
            assert resp.json()["code"] == "password_change_required"
        me = (await client.get("/api/auth/me")).json()
        assert me["account"]["handle"] == "mai" and me["account"]["must_change_password"] is True
        # Hai route "pending" qua được cổng: lỗi (nếu có) là của chính route.
        bad = await client.post("/api/auth/change-password", json={"current_password": "x", "new_password": "y"})
        assert bad.status_code == 422
        assert (await client.post("/api/auth/logout")).status_code == 204
    with repo.locked() as conn:
        assert conn.execute("SELECT COUNT(*) FROM sessions WHERE account_id = ?", (member,)).fetchone()[0] == 0


async def test_member_settings_model_rule(app: FastAPI) -> None:
    """PUT /api/settings: thành viên gửi lại đúng model đang lưu thì 200; khác thì 403 (§4.1)."""
    repo = repo_of(app)
    owner_id = ensure_owner_password(repo)
    member = add_member(repo, "mai")
    async with client_for(app, owner_id) as owner, client_for(app, member) as client:
        assert (await owner.put("/api/settings", json={"default_chat_model": "custom:7b"})).status_code == 200
        persona = (await client.post("/api/personas", json={"name": "Mai", "gender": "female"})).json()
        same = await client.put("/api/settings", json={"default_persona_id": persona["id"], "default_chat_model": "custom:7b"})
        assert same.status_code == 200, same.text
        assert same.json() == {"default_persona_id": persona["id"], "default_chat_model": "custom:7b"}
        other = await client.put("/api/settings", json={"default_persona_id": None, "default_chat_model": "khac:1b"})
        assert other.status_code == 403 and other.json()["code"] == "owner_only"
        cleared = await client.put("/api/settings", json={"default_chat_model": None})
        assert cleared.status_code == 403
        # Persona mặc định là của từng tài khoản.
        assert (await owner.get("/api/settings")).json()["default_persona_id"] != persona["id"]
        assert (await client.get("/api/settings")).json()["default_persona_id"] == persona["id"]
        # Model của máy không đổi.
        assert (await owner.get("/api/settings")).json()["default_chat_model"] == "custom:7b"


async def test_member_cannot_change_story_model_and_health_hides_models(app: FastAPI) -> None:
    repo = repo_of(app)
    owner_id = ensure_owner_password(repo)
    member = add_member(repo, "mai")
    async with client_for(app, owner_id) as owner, client_for(app, member) as client:
        story = (await client.post("/api/stories")).json()
        same = await client.patch(f"/api/stories/{story['id']}", json={"model_name": story["model_name"], "title": "Mới"})
        assert same.status_code == 200 and same.json()["title"] == "Mới"
        other = await client.patch(f"/api/stories/{story['id']}", json={"model_name": "khac:1b"})
        assert other.status_code == 403 and other.json()["code"] == "owner_only"
        own_story = (await owner.get("/api/stories")).json()[0]
        assert (await owner.patch(f"/api/stories/{own_story['id']}", json={"model_name": "khac:1b"})).status_code == 200

        health = (await client.get("/api/health")).json()
        assert health["chat_model"] == "" and health["ollama"]["models"] == []
        assert (await owner.get("/api/health")).json()["chat_model"] == "chat-model:test"


async def test_disabled_account_session_is_dropped(app: FastAPI) -> None:
    repo = repo_of(app)
    member = add_member(repo, "mai")
    async with client_for(app, member) as client:
        assert (await client.get("/api/stories")).status_code == 200
        with repo.transaction():
            store.set_status(repo.conn, member, "disabled", clock.now())
        resp = await client.get("/api/stories")
        assert resp.status_code == 401 and resp.json()["detail"] == "Bạn đã bị đăng xuất. Hãy đăng nhập lại."
        assert "lyris_session=;" in resp.headers["set-cookie"]
    with repo.locked() as conn:
        assert conn.execute("SELECT COUNT(*) FROM sessions WHERE account_id = ?", (member,)).fetchone()[0] == 0


async def test_unknown_cookie_is_logged_out(app: FastAPI) -> None:
    ensure_owner_password(repo_of(app))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test", cookies={"lyris_session": "x" * 43}
    ) as client:
        resp = await client.get("/api/stories")
        assert resp.status_code == 401 and resp.json()["detail"] == "Bạn đã bị đăng xuất. Hãy đăng nhập lại."
        assert resp.headers["set-cookie"].startswith("lyris_session=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax")
