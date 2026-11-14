"""Regression test cho các lỗi đã xác nhận ở vòng rà soát ra mắt (web mở, số liệu, quyền riêng tư, tuân thủ).

Mỗi test gắn với một lỗi: số liệu đếm một người thành hai; `POST /api/events` bị bơm khi chưa đăng nhập; tắt chia
sẻ chỉ theo tài khoản; GPC vẫn nhận cookie; `has_avatar` sai; lộ người báo cáo qua bản xuất số liệu; dữ liệu sau khi
xoá tài khoản vẫn nối lại được; gửi PostHog trước khi đồng ý chính sách; nhân vật công khai không báo cáo được; không
có lối vào cho người lạ; cùng các lỗi tài liệu / script kiểm được bằng máy.

LLM giả (FakeLLM), DB trong thư mục tạm, PostHog giả bằng `httpx.MockTransport`. Không gọi Ollama, không mở cổng.
"""
from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI

from lyris.analytics import store
from lyris.api.app import create_app
from lyris.api.routes_analytics import NEW_DEVICE_MAX, PRE_AUTH_MAX_REQUESTS, RateLimiter
from lyris.auth import clock
from lyris.auth import setup as owner_setup
from lyris.compliance import legal
from lyris.config import REPO_ROOT, Settings, get_settings
from lyris.db.connection import connect, migrate
from lyris.db.repo import Repo, new_uid
from lyris.llm.fake import FakeLLM
from tests.authutil import MEMBER_PASSWORD, add_member, anon_client, ensure_owner_password, repo_of
from tests.twoaccounts import REPLY, World, card_body, make_settings, png_bytes, two_accounts

PNG = {"content": png_bytes(), "headers": {"Content-Type": "image/png"}}
EVENTS = "/api/events"


class FakePostHog:
    def __init__(self) -> None:
        self.batches: list[dict[str, Any]] = []

    def transport(self) -> httpx.MockTransport:
        def handler(request: httpx.Request) -> httpx.Response:
            self.batches.append(json.loads(request.content))
            return httpx.Response(200, json={"status": 1})

        return httpx.MockTransport(handler)

    def items(self) -> list[dict[str, Any]]:
        return [i for b in self.batches for i in b["batch"]]


@pytest_asyncio.fixture
async def app(tmp_path: Path) -> AsyncIterator[FastAPI]:
    application = create_app(make_settings(tmp_path), FakeLLM(replies=[REPLY]))
    async with application.router.lifespan_context(application):
        yield application


@pytest_asyncio.fixture
async def ph_app(tmp_path: Path) -> AsyncIterator[tuple[FastAPI, FakePostHog]]:
    """App có khoá PostHog (giả); không chạy task gửi nền, test gọi `flush()`."""
    settings = Settings(**{**make_settings(tmp_path).__dict__, "posthog_key": "phc_test"})
    posthog = FakePostHog()
    application = create_app(settings, FakeLLM(replies=[REPLY]), start_forwarder=False, posthog_transport=posthog.transport())
    async with application.router.lifespan_context(application):
        yield application, posthog


@pytest_asyncio.fixture
async def world(tmp_path: Path) -> AsyncIterator[World]:
    async with two_accounts(tmp_path) as w:
        yield w


async def ok(resp: httpx.Response) -> Any:
    assert resp.status_code in (200, 202), (resp.request.method, str(resp.request.url), resp.status_code, resp.text)
    return resp.json()


def rows(app: FastAPI, where: str = "1", *params: Any) -> list[dict[str, Any]]:
    with repo_of(app).locked() as conn:
        return [dict(r) for r in conn.execute(f"SELECT * FROM analytics_events WHERE {where} ORDER BY id", params)]


def set_cookies(resp: httpx.Response) -> list[str]:
    return resp.headers.get_list("set-cookie")


def accept_terms(repo: Repo, *ids: int) -> None:
    with repo.transaction():
        for account_id in ids:
            legal.accept(repo.conn, account_id, clock.now())


async def login(client: httpx.AsyncClient, handle: str, password: str = MEMBER_PASSWORD) -> int:
    resp = await client.post("/api/auth/login", json={"handle": handle, "password": password})
    assert resp.status_code == 200, resp.text
    return int(resp.json()["account"]["id"])


# ---------------------------------------------------------------------------- 1. một người, không phải hai


def test_summary_counts_a_signup_as_one_person(tmp_path: Path) -> None:
    """Mở trang khi chưa đăng nhập (anon A) rồi tạo tài khoản u cùng thiết bị: DAU/MAU = 1, D1 = 1/1."""
    repo = Repo(connect(tmp_path / "x.db"))
    migrate(repo.conn)
    with repo.transaction():
        from lyris.auth import store as auth_store

        u = auth_store.insert_member(repo.conn, uid=new_uid(), handle="hoa", display_name="Hoa", invited_by=None)
    d0 = datetime(2026, 11, 10, 3, 0, tzinfo=timezone.utc)  # 10:00 giờ Việt Nam

    def put(ts: datetime, name: str, account: int | None) -> None:
        with repo.transaction():
            store.insert(
                repo.conn, ts=clock.iso(ts), name=name, account_id=account, anon_id="A", session_id="s",
                story_id=None, props_json="{}", source="server", app_version="", pending=False,
            )

    put(d0, "app_opened", None)
    put(d0 + timedelta(minutes=1), "signup_viewed", None)
    put(d0 + timedelta(minutes=2), "signup_completed", u)
    put(d0 + timedelta(days=1), "app_opened", u)
    # Một người khác chỉ ghé (không bao giờ đăng nhập): vẫn là một người riêng.
    with repo.transaction():
        store.insert(
            repo.conn, ts=clock.iso(d0), name="app_opened", account_id=None, anon_id="B", session_id="t",
            story_id=None, props_json="{}", source="client", app_version="", pending=False,
        )
    with repo.locked() as conn:
        got = store.summary(conn, d0 + timedelta(days=1, hours=1), 30)
    daily = {d["date"]: d["active"] for d in got["daily"]}
    assert daily["2026-11-10"] == 2  # hoa + người ghé B (không phải 3)
    assert daily["2026-11-11"] == 1
    assert got["mau"] == 2
    assert got["retention"]["d1"] == {"cohort": 2, "retained": 1, "rate": 0.5}  # hoa quay lại, B thì không


# ---------------------------------------------------------------------------- 2. chặn bơm sự kiện khi chưa đăng nhập


async def test_signed_out_events_cannot_flood(app: FastAPI) -> None:
    async with anon_client(app) as c:
        got = await ok(await c.post(EVENTS, json={"events": [{"name": "app_opened"}] * 20}))
        assert got == {"accepted": 1, "dropped": 19}  # mỗi tên một lần mỗi request
        for _ in range(PRE_AUTH_MAX_REQUESTS - 1):
            assert (await c.post(EVENTS, json={"events": [{"name": "signup_viewed"}]})).status_code == 202
        limited = await c.post(EVENTS, json={"events": [{"name": "app_opened"}]})
        assert limited.status_code == 429 and limited.json()["code"] == "rate_limited"
    assert len([r for r in rows(app) if r["name"] == "app_opened"]) == 1


async def test_cookieless_requests_cannot_mint_endless_visitors(app: FastAPI) -> None:
    app.state.events_anon_limiter = RateLimiter(10_000)  # chỉ thử giới hạn thiết bị mới
    for _ in range(NEW_DEVICE_MAX):
        async with anon_client(app) as c:
            assert (await ok(await c.post(EVENTS, json={"events": [{"name": "app_opened"}]})))["accepted"] == 1
    async with anon_client(app) as c:
        resp = await c.post(EVENTS, json={"events": [{"name": "app_opened"}]})
        assert (await ok(resp)) == {"accepted": 0, "dropped": 1}
        assert not any(h.startswith("lyris_anon=") for h in set_cookies(resp))  # không sinh định danh mới
    visitors = {r["anon_id"] for r in rows(app) if r["name"] == "app_opened"}
    assert len(visitors) == NEW_DEVICE_MAX
    # Thiết bị đã có cookie vẫn gửi được.
    async with anon_client(app) as c:
        c.cookies.set("lyris_anon", next(iter(visitors)))
        assert (await ok(await c.post(EVENTS, json={"events": [{"name": "app_opened"}]})))["accepted"] == 1


# ---------------------------------------------------------------------------- 3. GPC: không cookie nào


async def test_gpc_browser_gets_no_identifier_cookie(app: FastAPI) -> None:
    ensure_owner_password(repo_of(app))
    async with anon_client(app, headers={"Sec-GPC": "1"}) as c:
        resp = await c.post(EVENTS, json={"events": [{"name": "app_opened"}]})
        assert (await ok(resp)) == {"accepted": 0, "dropped": 1}
        assert not any(h.startswith("lyris_anon=") for h in set_cookies(resp))
        bad = await c.post("/api/auth/login", json={"handle": "khong_co", "password": "sai mật khẩu"})
        assert bad.status_code == 401
        assert not any(h.startswith("lyris_anon=") for h in set_cookies(bad))
        assert "lyris_anon" not in c.cookies
    assert rows(app) == []


# ---------------------------------------------------------------------------- 4. tắt chia sẻ: cả thiết bị


async def test_opt_out_covers_the_device_after_sign_out(ph_app: tuple[FastAPI, FakePostHog]) -> None:
    app, posthog = ph_app
    repo = repo_of(app)
    ensure_owner_password(repo)
    mai = add_member(repo, "mai")
    accept_terms(repo, mai)
    async with anon_client(app) as c:
        await ok(await c.post(EVENTS, json={"events": [{"name": "app_opened", "props": {"authed": False}}]}))
        anon = c.cookies["lyris_anon"]
        assert await login(c, "mai") == mai
        out = await c.patch("/api/account", json={"analytics_opt_out": True})
        assert out.status_code == 200
        cookies = set_cookies(out)
        assert any(h.startswith("lyris_anon=;") and "Max-Age=0" in h for h in cookies), cookies
        assert any(h.startswith("lyris_noshare=1") for h in cookies), cookies
        # Sự kiện của tài khoản VÀ sự kiện lúc chưa đăng nhập trên thiết bị đó đều đã xoá.
        assert rows(app, "anon_id = ?", anon) == []
        assert rows(app, "account_id = ?", mai) == []
        assert (await c.post("/api/auth/logout")).status_code == 204
        # Đăng xuất rồi: trình duyệt này không bị ghi gì nữa, không nhận lại lyris_anon.
        resp = await c.post(EVENTS, json={"events": [{"name": "app_opened"}, {"name": "signup_viewed"}]})
        assert (await ok(resp)) == {"accepted": 0, "dropped": 2}
        assert not any(h.startswith("lyris_anon=") for h in set_cookies(resp))
        bad = await c.post("/api/auth/login", json={"handle": "mai", "password": "sai mật khẩu"})
        assert bad.status_code == 401
    assert [r["name"] for r in rows(app)] == ["analytics_opt_out"]  # chỉ còn dòng đếm không gắn ai
    assert await app.state.posthog.flush() == 0 and posthog.items() == []

    # Bật lại: gỡ dấu không chia sẻ của thiết bị.
    async with anon_client(app) as c:
        c.cookies.set("lyris_noshare", "1")
        await login(c, "mai")
        back = await c.patch("/api/account", json={"analytics_opt_out": False})
        assert any(h.startswith("lyris_noshare=;") and "Max-Age=0" in h for h in set_cookies(back))


async def test_opted_out_account_signing_in_on_a_new_device_marks_it(app: FastAPI) -> None:
    repo = repo_of(app)
    ensure_owner_password(repo)
    mai = add_member(repo, "mai")
    with repo.transaction():
        store.set_opt_out(repo.conn, mai, True)
    async with anon_client(app) as c:
        await ok(await c.post(EVENTS, json={"events": [{"name": "app_opened"}]}))
        anon = c.cookies["lyris_anon"]
        assert rows(app, "anon_id = ?", anon)
        resp = await c.post("/api/auth/login", json={"handle": "mai", "password": MEMBER_PASSWORD})
        assert resp.status_code == 200
        assert any(h.startswith("lyris_noshare=1") for h in set_cookies(resp))
    assert rows(app, "anon_id = ?", anon) == []  # thao tác lúc chưa đăng nhập của thiết bị này cũng xoá


# ---------------------------------------------------------------------------- 5. has_avatar


async def test_form_card_with_picture_counts_has_avatar(app: FastAPI) -> None:
    from tests.authutil import client_for

    owner = ensure_owner_password(repo_of(app))
    async with client_for(app, owner) as c:
        card = await ok(await c.post("/api/cards?via=form&with_avatar=true", json={"card": card_body("Có ảnh")}))
        await ok(await c.put(f"/api/cards/{card['id']}/avatar", **PNG))
        await ok(await c.post("/api/cards?via=form", json={"card": card_body("Không ảnh")}))
    created = [json.loads(r["props_json"]) for r in rows(app) if r["name"] == "character_created"]
    assert created == [
        {"has_avatar": True, "via": "form", "visibility": "private"},
        {"has_avatar": False, "via": "form", "visibility": "private"},
    ]


# ---------------------------------------------------------------------------- 6. không lộ người báo cáo


async def test_report_event_is_not_linkable_in_the_owner_export(world: World) -> None:
    w = world
    await ok(await w.b.post(f"/api/messages/{w.b_message}/report", json={"reason": "sexual"}))
    await ok(await w.b.post(f"/api/cards/{w.a_public}/report", json={"reason": "hateful"}))
    b_uid = w.repo.get_account(w.b_id).uid
    assert b_uid
    export = await w.a.get("/api/admin/analytics/export.jsonl")
    items = [json.loads(line) for line in export.text.strip().split("\n")]
    reports = [i for i in items if i["name"] == "content_reported"]
    assert len(reports) == 2
    for item in reports:
        assert item["distinct_id"] == "" and item["anon_id"] == "" and item["session_id"] == ""
        assert item["story_id"] is None
    assert {i["props"]["target"] for i in reports} == {"message", "character"}
    assert all(r["posthog_state"] == "local" for r in rows(w.app, "name = 'content_reported'"))


# ---------------------------------------------------------------------------- 7. xoá tài khoản: không nối lại được


async def test_deleted_account_cannot_be_linked_back(ph_app: tuple[FastAPI, FakePostHog]) -> None:
    app, posthog = ph_app
    repo = repo_of(app)
    ensure_owner_password(repo)
    mai = add_member(repo, "mai")
    accept_terms(repo, mai)
    async with anon_client(app) as c:
        await ok(await c.post(EVENTS, json={"events": [{"name": "app_opened"}]}))
        anon = c.cookies["lyris_anon"]
        await login(c, "mai")
        await ok(await c.post("/api/personas", json={"name": "Mai", "gender": "female"}))
        await app.state.posthog.flush()
        sent_before = {i["distinct_id"] for i in posthog.items()}
        identify = [i for i in posthog.items() if i["event"] == "$identify"]
        assert identify and identify[0]["properties"]["$anon_distinct_id"] == anon
        old_sessions = {r["session_id"] for r in rows(app)}

        resp = await c.request("DELETE", "/api/account", json={"password": MEMBER_PASSWORD})
        assert resp.status_code == 200, resp.text
        assert any(h.startswith("lyris_anon=;") and "Max-Age=0" in h for h in set_cookies(resp))
        left = rows(app)
        assert left and all(r["account_id"] is None for r in left)
        assert not any(r["anon_id"] == anon for r in left)  # bí danh mới
        assert not ({r["session_id"] for r in left} & old_sessions)
        deleted = [r for r in left if r["name"] == "account_deleted"]
        assert len(deleted) == 1 and deleted[0]["anon_id"] == "" and deleted[0]["session_id"] == ""
        assert deleted[0]["posthog_state"] == "local"
        # Trình duyệt quay lại sau khi xoá: là một thiết bị mới, không phải anon cũ.
        c.cookies.delete("lyris_anon")
        await ok(await c.post(EVENTS, json={"events": [{"name": "app_opened"}]}))
        assert c.cookies["lyris_anon"] != anon
    posthog.batches.clear()
    await app.state.posthog.flush()
    after = posthog.items()
    assert not any(i["distinct_id"] in sent_before or i["distinct_id"] == anon for i in after), after
    assert not any(i["event"] == "account_deleted" for i in after)


# ---------------------------------------------------------------------------- 8. chưa đồng ý chính sách: không gửi PostHog


async def test_no_forwarding_before_the_policy_is_accepted(ph_app: tuple[FastAPI, FakePostHog]) -> None:
    app, posthog = ph_app
    repo = repo_of(app)
    ensure_owner_password(repo)
    mai = add_member(repo, "mai")  # như tài khoản có từ trước 0010: chưa đồng ý bản nào
    async with anon_client(app) as c:
        await login(c, "mai")
        assert (await c.get("/api/auth/me")).json()["account"]["terms_required"] is True
        mine = rows(app, "account_id = ?", mai)
        assert {r["name"] for r in mine} >= {"login_succeeded"}
        assert {r["posthog_state"] for r in mine} == {"local"}
        assert await app.state.posthog.flush() == 0 and posthog.items() == []
        await ok(await c.post("/api/account/terms", json={"accept_terms": True, "version": legal.LEGAL_VERSION}))
        await ok(await c.post("/api/personas", json={"name": "Mai", "gender": "female"}))
    assert rows(app, "name = 'persona_created'")[0]["posthog_state"] == "pending"
    await app.state.posthog.flush()
    names = [i["event"] for i in posthog.items()]
    assert "persona_created" in names and "login_succeeded" not in names and "$identify" not in names


# ---------------------------------------------------------------------------- 9. báo cáo nhân vật công khai


async def test_public_character_can_be_reported_and_hidden(world: World) -> None:
    w = world
    out = await ok(await w.b.post(f"/api/cards/{w.a_public}/report", json={"reason": "hateful", "note": "  Tên xúc phạm  "}))
    assert out["status"] == "open" and out["shared_text"] is False
    again = await ok(await w.b.post(f"/api/cards/{w.a_public}/report", json={"reason": "sexual"}))
    assert again["id"] == out["id"]  # báo cáo lại thì cập nhật
    # Từ bản sao trong story của mình: báo cáo nhân vật gốc.
    via_copy = await ok(await w.b.post(f"/api/cards/{w.b_copy}/report", json={"reason": "sexual"}))
    assert via_copy["id"] == out["id"]
    # Nhân vật của chính mình: 422; nhân vật riêng tư của người khác / không có: 404 (không lộ gì).
    assert (await w.a.post(f"/api/cards/{w.a_public}/report", json={"reason": "other"})).status_code == 422
    assert (await w.a.post(f"/api/cards/{w.a_private}/report", json={"reason": "other"})).status_code == 422
    assert (await w.b.post(f"/api/cards/{w.a_private}/report", json={"reason": "other"})).status_code == 404
    assert (await w.b.post("/api/cards/99999/report", json={"reason": "other"})).status_code == 404
    assert (await w.b.post(f"/api/cards/{w.a_public}/report", json={"reason": "spam"})).status_code == 422

    listed = await ok(await w.a.get("/api/admin/reports"))
    card_reports = [r for r in listed if r["target"] == "character"]
    assert len(card_reports) == 1
    report = card_reports[0]
    assert report["public_card_id"] == w.a_public and report["reason"] == "sexual" and report["message_text"] is None
    assert not {"reporter_id", "story_id", "message_id"} & report.keys() and "mai" not in json.dumps(report)
    # Thành viên không ẩn được; chủ máy ẩn được (về Riêng tư, người tạo vẫn giữ).
    assert (await w.b.post(f"/api/admin/cards/{w.a_public}/unpublish")).status_code == 403
    assert (await ok(await w.a.post(f"/api/admin/cards/{w.a_public}/unpublish"))) == {"unpublished": True}
    assert (await w.b.get(f"/api/cards/{w.a_public}/public")).status_code == 404
    assert (await ok(await w.a.get(f"/api/cards/{w.a_public}")))["visibility"] == "private"
    assert (await w.a.post(f"/api/admin/cards/{w.a_public}/unpublish")).status_code == 404
    assert (await w.a.post(f"/api/admin/cards/{w.b_copy}/unpublish")).status_code == 404  # bản sao: không
    # Bản xuất dữ liệu của người báo cáo có báo cáo nhân vật.
    export = await ok(await w.b.get("/api/account/export"))
    text = json.dumps(export, ensure_ascii=False)
    assert '"target": "character"' in text


def test_migration_0011_is_additive_and_old_reports_are_message_reports(tmp_path: Path) -> None:
    conn = connect(tmp_path / "m.db")
    assert migrate(conn, target=10) == 10
    conn.execute("INSERT INTO content_reports (created_at, updated_at, reason, note) VALUES ('t', 't', 'other', '')")
    conn.commit()
    assert migrate(conn) == 14
    assert conn.execute("SELECT target FROM content_reports").fetchall()[0][0] == "message"
    sql = (REPO_ROOT / "backend" / "lyris" / "db" / "migrations" / "0011_card_reports.sql").read_text(encoding="utf-8")
    code = "\n".join(line.split("--")[0] for line in sql.splitlines()).upper()
    assert "DROP" not in code and "DELETE" not in code and "UPDATE" not in code


# ---------------------------------------------------------------------------- 10. lối vào cho người lạ


async def test_contact_reaches_login_page_and_legal_texts(tmp_path: Path) -> None:
    settings = Settings(**{**make_settings(tmp_path).__dict__, "contact": "hotro@lyris.example.com"})
    application = create_app(settings, FakeLLM(replies=[REPLY]))
    async with application.router.lifespan_context(application):
        ensure_owner_password(repo_of(application))
        async with anon_client(application) as c:
            me = (await c.get("/api/auth/me")).json()
            assert me["account"] is None and me["contact"] == "hotro@lyris.example.com"
            for doc in ("privacy", "terms"):
                text = (await c.get(f"/api/legal/{doc}")).json()["markdown"]
                assert legal.CONTACT_PLACEHOLDER not in text and "hotro@lyris.example.com" in text
                assert "sẽ điền trước khi ra mắt" not in text and "to be filled in" not in text


async def test_without_contact_the_placeholder_stays(app: FastAPI) -> None:
    async with anon_client(app) as c:
        assert (await c.get("/api/auth/me")).json()["contact"] is None
        assert legal.CONTACT_PLACEHOLDER in (await c.get("/api/legal/privacy")).json()["markdown"]


def test_contact_setting_is_an_email_or_https(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LYRIS_CONTACT", "hotro@lyris.vn")
    assert get_settings().contact == "hotro@lyris.vn"
    monkeypatch.setenv("LYRIS_CONTACT", "https://lyris.vn/lien-he")
    assert get_settings().contact == "https://lyris.vn/lien-he"
    for bad in ("http://lyris.vn", "javascript:alert(1)", "không phải email"):
        monkeypatch.setenv("LYRIS_CONTACT", bad)
        with pytest.raises(ValueError):
            get_settings()


async def test_auth_errors_do_not_send_visitors_to_a_machine_owner(app: FastAPI) -> None:
    from lyris.auth import errors

    for text in (errors.ACCOUNT_DISABLED, errors.TEMP_EXPIRED):
        assert "chủ máy" not in text and "người quản lý Lyris" in text


# ---------------------------------------------------------------------------- 11. script, banner, tài liệu


def test_setup_banner_names_no_port_or_mac() -> None:
    text = owner_setup.banner("7KQ2-M9XD-4TPA")
    assert "5173" not in text and "Mac" not in text and "7KQ2-M9XD-4TPA" in text


def test_serve_sh_hint_keeps_the_custom_database() -> None:
    script = (REPO_ROOT / "scripts" / "serve.sh").read_text(encoding="utf-8")
    assert "LYRIS_DB_PATH=$(printf '%q' \"$LYRIS_DB_PATH\") bash scripts/lyris-admin.sh setup-code" in script


def test_deploy_opens_the_home_dir_for_caddy_and_limits_logs() -> None:
    doc = (REPO_ROOT / "docs" / "deploy.md").read_text(encoding="utf-8")
    useradd = doc.index("sudo useradd --system --create-home --home-dir /opt/lyris")
    chmod = doc.index("sudo chmod 755 /opt/lyris")
    clone = doc.index("sudo -u lyris git clone")
    assert useradd < chmod < clone
    assert "MaxRetentionSec=30day" in doc and "LYRIS_CONTACT" in doc


def test_privacy_policy_discloses_server_logs_and_new_cookie() -> None:
    text = (REPO_ROOT / "docs" / "legal" / "privacy.md").read_text(encoding="utf-8")
    vi, en = text.split("## English")
    assert "Nhật ký máy chủ" in vi and "30 ngày" in vi and "lyris_noshare" in vi
    assert "Server logs" in en and "30 days" in en and "lyris_noshare" in en
    assert "Chia sẻ dữ liệu sử dụng ẩn danh để cải thiện Lyris" not in text


def test_readme_test_block_runs_from_the_root_and_versions_agree() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "(cd backend && .venv/bin/pytest -q)" in readme
    assert "(cd frontend && npm test && npm run typecheck && npm run build)" in readme
    assert "\ncd backend && .venv/bin/pytest" not in readme
    english, vietnamese = readme.split("## Tiếng Việt")
    assert "Self-hosting enthusiasts" in english and "Self-hosting stays free" in english
    assert "Người thích tự chạy AI" in vietnamese and "Tự chạy trên máy mình vẫn miễn phí" in vietnamese
