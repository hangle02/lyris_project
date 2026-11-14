"""Phase 4b (docs/auth.md §8.1): đăng nhập, thiết lập chủ máy, phiên, đổi mật khẩu, giới hạn thử sai, CSRF, cache,
mã mời, quản trị. DB tạm, FakeLLM, httpx qua ASGITransport.

scrypt thật (n = 2^17) mất khoảng 0,3 giây, nên phần lớn test thay `passwords._scrypt` bằng bản rẻ (cùng một
hàm cho cả băm và so sánh, nên đúng/sai vẫn đúng); test_auth_units.py kiểm scrypt thật.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import unicodedata
from collections.abc import AsyncIterator, Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from lyris.api.app import create_app
from lyris.auth import clock, codes, passwords, store
from lyris.auth import setup as owner_setup
from lyris.compliance.legal import LEGAL_VERSION
from lyris.config import Settings
from lyris.db.repo import ANY_ACCOUNT, Repo
from lyris.llm.fake import FakeLLM
from lyris.models import Persona

OWNER_PW = "trăng sáng trên hồ"
MEMBER_PW = "mưa rơi ngoài hiên"
LAN_PEER = ("192.168.1.20", 50000)


# ---------------------------------------------------------------------------- fixtures


class FakeClock:
    def __init__(self) -> None:
        self.t = datetime(2026, 11, 14, 8, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.t

    def advance(self, **kwargs: float) -> None:
        self.t += timedelta(**kwargs)


@pytest.fixture
def fake_clock(monkeypatch: pytest.MonkeyPatch) -> FakeClock:
    fc = FakeClock()
    monkeypatch.setattr(clock, "now", fc)
    return fc


@pytest.fixture
def scrypt_calls(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """scrypt rẻ cho test (n nhỏ), đếm số lần gọi. Tham số lưu trong DB vẫn là tham số thật."""
    calls: list[int] = []

    def cheap(password: bytes, salt: bytes, n: int, r: int, p: int) -> bytes:
        calls.append(n)
        return hashlib.scrypt(password, salt=salt + n.to_bytes(4, "big"), n=16, r=1, p=1, dklen=32)

    monkeypatch.setattr(passwords, "_scrypt", cheap)
    return calls


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
async def app(settings: Settings, scrypt_calls: list[int], fake_clock: FakeClock) -> AsyncIterator[FastAPI]:
    application = create_app(settings, FakeLLM(replies=["Chào."]))
    async with application.router.lifespan_context(application):
        yield application


def repo_of(app: FastAPI) -> Repo:
    repo: Repo = app.state.repo
    return repo


def client(app: FastAPI, *, peer: tuple[str, int] | None = None, csrf: bool = True, **kwargs: Any) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app, client=peer or ("127.0.0.1", 123))
    headers = {"X-Lyris": "1"} if csrf else {}
    headers.update(kwargs.pop("headers", {}))
    return httpx.AsyncClient(transport=transport, base_url="http://test", headers=headers, **kwargs)


def set_password(repo: Repo, account_id: int, password: str, *, temporary: bool = False, **params: int) -> None:
    hashed = passwords.hash_password_sync(password, **params)
    with repo.transaction():
        store.write_password(repo.conn, account_id, hashed, clock.now(), temporary=temporary)
        if repo.owner_account().id == account_id:
            store.delete_setup(repo.conn)


def owner_id(app: FastAPI) -> int:
    owner = repo_of(app).owner_account()
    assert owner.id is not None
    return owner.id


def ready_owner(app: FastAPI, password: str = OWNER_PW) -> int:
    """Chủ máy đã đặt mật khẩu (handle `ban`)."""
    oid = owner_id(app)
    set_password(repo_of(app), oid, password)
    return oid


def add_member(app: FastAPI, handle: str = "mai", password: str = MEMBER_PW) -> int:
    repo = repo_of(app)
    with repo.transaction():
        mid = store.insert_member(repo.conn, uid=handle.ljust(32, "0"), handle=handle, display_name=handle.title(), invited_by=None)
    set_password(repo, mid, password)
    return mid


async def login(c: httpx.AsyncClient, handle: str, password: str) -> httpx.Response:
    return await c.post("/api/auth/login", json={"handle": handle, "password": password})


def rows(repo: Repo, sql: str, *params: Any) -> list[Any]:
    with repo.locked() as conn:
        return conn.execute(sql, params).fetchall()


def count(repo: Repo, sql: str, *params: Any) -> int:
    return int(rows(repo, sql, *params)[0][0])


def new_setup_code(app: FastAPI) -> str:
    repo = repo_of(app)
    with repo.transaction():
        return owner_setup.write_new_code(repo.conn, clock.now())


def dump(repo: Repo) -> str:
    with repo.locked() as conn:
        return "\n".join(conn.iterdump())


@pytest.fixture
def auth_log(caplog: pytest.LogCaptureFixture) -> Iterator[pytest.LogCaptureFixture]:
    caplog.set_level(logging.INFO, logger="lyris.auth")
    yield caplog


# ---------------------------------------------------------------------------- băm mật khẩu


async def test_login_nfc_and_nfd_are_the_same_password(app: FastAPI) -> None:
    nfc = unicodedata.normalize("NFC", "Mật khẩu của tôi")
    nfd = unicodedata.normalize("NFD", nfc)
    assert nfc != nfd
    ready_owner(app, nfc)
    async with client(app) as c:
        assert (await login(c, "ban", nfd)).status_code == 200
    async with client(app) as c:
        assert (await login(c, "ban", nfc)).status_code == 200


async def test_old_scrypt_params_are_upgraded_on_login(app: FastAPI) -> None:
    oid = owner_id(app)
    set_password(repo_of(app), oid, OWNER_PW, n=2**14)
    async with client(app) as c:
        assert (await login(c, "ban", OWNER_PW)).status_code == 200
    row = rows(repo_of(app), "SELECT scrypt_n, scrypt_r, scrypt_p FROM accounts WHERE id = ?", oid)[0]
    assert tuple(row) == (passwords.SCRYPT_N, passwords.SCRYPT_R, passwords.SCRYPT_P)
    async with client(app) as c:  # mật khẩu vẫn đúng sau khi băm lại
        assert (await login(c, "ban", OWNER_PW)).status_code == 200


async def test_unknown_handle_still_runs_scrypt(app: FastAPI, scrypt_calls: list[int]) -> None:
    ready_owner(app)
    scrypt_calls.clear()
    async with client(app) as c:
        missing = await login(c, "khong_co_ai", "bất kỳ mật khẩu nào")
        wrong = await login(c, "ban", "sai mật khẩu rồi")
    assert len(scrypt_calls) == 2
    assert missing.status_code == wrong.status_code == 401
    assert missing.json() == wrong.json() == {"detail": "Tên đăng nhập hoặc mật khẩu không đúng.", "technical": None}


# ---------------------------------------------------------------------------- thiết lập chủ máy


async def test_startup_prints_setup_code_to_stderr_only(settings: Settings, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    application = create_app(settings, FakeLLM(replies=["Chào."]))
    async with application.router.lifespan_context(application):
        captured = capsys.readouterr()
        assert "Lyris: đặt mật khẩu cho tài khoản chủ máy" in captured.err and captured.out == ""
        printed = next(line.strip() for line in captured.err.splitlines() if line.startswith("     "))
        assert codes.normalize_code(printed) is not None
        assert printed not in caplog.text
        saved = store.read_setup(repo_of(application).conn)
        assert saved is not None and saved[0] == hashlib.sha256(codes.normalize_code(printed).encode()).hexdigest()  # type: ignore[union-attr]
        async with client(application) as c:
            me = (await c.get("/api/auth/me")).json()
            assert me == {"setup_required": True, "setup_needs_profile": True, "account": None, "legal_version": LEGAL_VERSION, "contact": None}
            assert "ban" not in str(me)
            resp = await c.post("/api/auth/setup-owner", json={"accept_terms": True, "setup_code": printed.lower(), "password": OWNER_PW})
            assert resp.status_code == 200, resp.text
    # Khởi động lại khi đã có mật khẩu: không in mã, không còn owner_setup.
    application = create_app(settings, FakeLLM(replies=["Chào."]))
    async with application.router.lifespan_context(application):
        assert "mã thiết lập" not in capsys.readouterr().err
        assert store.read_setup(repo_of(application).conn) is None


async def test_setup_owner_flow(app: FastAPI) -> None:
    repo = repo_of(app)
    code = new_setup_code(app)
    async with client(app) as c:
        assert (await c.get("/api/stories")).json()["code"] == "setup_required"
        bad = await c.post("/api/auth/setup-owner", json={"accept_terms": True, "setup_code": "AAAA-BBBB-CCCC", "password": OWNER_PW})
        assert bad.status_code == 400
        assert bad.json()["detail"] == "Mã thiết lập không đúng. Xem lại dòng in trong cửa sổ Terminal đang chạy Lyris."
        weak = await c.post("/api/auth/setup-owner", json={"accept_terms": True, "setup_code": code, "password": "12345678"})
        assert weak.status_code == 422 and weak.json()["detail"] == "Mật khẩu này quá dễ đoán. Hãy chọn mật khẩu khác."
        ok = await c.post("/api/auth/setup-owner", json={"accept_terms": True, "setup_code": code, "password": OWNER_PW})
        assert ok.status_code == 200, ok.text
        body = ok.json()
        assert body["setup_required"] is False and body["account"]["role"] == "owner"
        assert body["account"]["handle"] == "ban" and body["account"]["must_change_password"] is False
        assert "lyris_session=" in ok.headers.get_list("set-cookie")[-1] or any(
            h.startswith("lyris_session=") for h in ok.headers.get_list("set-cookie")
        )
        assert store.read_setup(repo.conn) is None
        assert (await c.get("/api/stories")).status_code == 200
        again = await c.post("/api/auth/setup-owner", json={"accept_terms": True, "setup_code": code, "password": OWNER_PW})
        assert again.status_code == 409 and again.json()["detail"] == "Lyris đã được thiết lập. Hãy đăng nhập."
    async with client(app) as c:
        assert (await login(c, "ban", OWNER_PW)).status_code == 200


async def test_setup_owner_race_has_one_winner(app: FastAPI) -> None:
    code = new_setup_code(app)
    async with client(app) as a, client(app) as b:
        results = await asyncio.gather(
            a.post("/api/auth/setup-owner", json={"accept_terms": True, "setup_code": code, "password": OWNER_PW}),
            b.post("/api/auth/setup-owner", json={"accept_terms": True, "setup_code": code, "password": "một mật khẩu khác"}),
        )
    assert sorted(r.status_code for r in results) == [200, 409]
    assert count(repo_of(app), "SELECT COUNT(*) FROM sessions") == 1


async def test_setup_rate_limit_is_per_ip_and_never_burns_the_code(app: FastAPI, scrypt_calls: list[int]) -> None:
    code = new_setup_code(app)
    repo = repo_of(app)
    for ip in ("192.168.1.30", "192.168.1.31", "192.168.1.32"):
        async with client(app, peer=(ip, 1)) as c:
            for _ in range(5):
                resp = await c.post("/api/auth/setup-owner", json={"accept_terms": True, "setup_code": "AAAA-BBBB-CCCC", "password": OWNER_PW})
                assert resp.status_code == 400
            before = count(repo, "SELECT COUNT(*) FROM auth_attempts")
            blocked = await c.post("/api/auth/setup-owner", json={"accept_terms": True, "setup_code": code, "password": OWNER_PW})
            assert blocked.status_code == 429 and blocked.json()["code"] == "rate_limited"
            assert 0 < int(blocked.headers["retry-after"]) <= 900
            assert count(repo, "SELECT COUNT(*) FROM auth_attempts") == before  # bị chặn: không ghi dòng
    assert scrypt_calls == []  # mã sai và bị chặn đều không băm
    async with client(app, peer=("192.168.1.40", 1)) as c:  # mã vẫn dùng được từ IP khác
        assert (await c.post("/api/auth/setup-owner", json={"accept_terms": True, "setup_code": code, "password": OWNER_PW})).status_code == 200


async def test_setup_code_expires_after_24h(app: FastAPI, fake_clock: FakeClock) -> None:
    code = new_setup_code(app)
    fake_clock.advance(hours=24, seconds=1)
    async with client(app) as c:
        resp = await c.post("/api/auth/setup-owner", json={"accept_terms": True, "setup_code": code, "password": OWNER_PW})
        assert resp.status_code == 400


async def test_fresh_db_setup_takes_profile(app: FastAPI) -> None:
    code = new_setup_code(app)
    async with client(app) as c:
        assert (await c.get("/api/auth/me")).json()["setup_needs_profile"] is True
        resp = await c.post(
            "/api/auth/setup-owner",
            json={"accept_terms": True, "setup_code": code, "password": OWNER_PW, "display_name": "  Trăng  Non ", "handle": "@TrangNon"},
        )
        assert resp.status_code == 200, resp.text
        account = resp.json()["account"]
        assert (account["handle"], account["display_name"], account["profile_completed"]) == ("trangnon", "Trăng Non", True)
    async with client(app) as c:
        assert (await login(c, "trangnon", OWNER_PW)).status_code == 200


async def test_completed_profile_ignores_setup_profile_fields(app: FastAPI) -> None:
    repo = repo_of(app)
    with repo.transaction():
        repo.conn.execute("UPDATE accounts SET handle = 'chu', display_name = 'Chủ', profile_completed = 1 WHERE role = 'owner'")
    code = new_setup_code(app)
    async with client(app) as c:
        me = (await c.get("/api/auth/me")).json()
        assert me == {"setup_required": True, "setup_needs_profile": False, "account": None, "legal_version": LEGAL_VERSION, "contact": None}
        resp = await c.post("/api/auth/setup-owner", json={"accept_terms": True, "setup_code": code, "password": OWNER_PW, "handle": "khac"})
        assert resp.json()["account"]["handle"] == "chu"


# ---------------------------------------------------------------------------- đăng nhập, cookie


def _cookie(resp: httpx.Response, prefix: str) -> str:
    return next(h for h in resp.headers.get_list("set-cookie") if h.startswith(prefix))


async def test_login_cookie_flags_over_http(app: FastAPI) -> None:
    ready_owner(app)
    async with client(app, headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) Version/18.0 Mobile/15E148 Safari/604.1"}) as c:
        resp = await login(c, "@BAN", OWNER_PW)
        assert resp.status_code == 200, resp.text
        assert resp.headers["cache-control"] == "no-store"
        session = _cookie(resp, "lyris_session=")
        assert "HttpOnly" in session and "SameSite=Lax" in session and "Path=/" in session
        assert "Secure" not in session and "Domain" not in session
        assert f"Max-Age={30 * 24 * 3600}" in session
        device = _cookie(resp, "lyris_device=")
        assert "HttpOnly" in device and f"Max-Age={365 * 24 * 3600}" in device
        me = (await c.get("/api/auth/me")).json()
        assert me["account"]["handle"] == "ban" and me["account"]["role"] == "owner"
    label = rows(repo_of(app), "SELECT device_label FROM sessions")[0][0]
    assert label == "Safari · iPhone"


async def test_secure_cookie_only_from_trusted_https(app: FastAPI) -> None:
    ready_owner(app)
    async with client(app, headers={"X-Forwarded-Proto": "https"}) as c:  # peer 127.0.0.1 (proxy tin cậy)
        resp = await login(c, "ban", OWNER_PW)
        session = _cookie(resp, "__Host-lyris_session=")
        assert "Secure" in session and "HttpOnly" in session and "Path=/" in session
        assert _cookie(resp, "__Host-lyris_device=").endswith("Secure")
    # Điện thoại tự gửi X-Forwarded-Proto: https qua Vite -> "https,http": không Secure.
    async with client(app, headers={"X-Forwarded-Proto": "https,http"}) as c:
        assert "Secure" not in _cookie(await login(c, "ban", OWNER_PW), "lyris_session=")
    async with client(app, peer=LAN_PEER, headers={"X-Forwarded-Proto": "https"}) as c:
        assert "Secure" not in _cookie(await login(c, "ban", OWNER_PW), "lyris_session=")


async def test_cookie_secure_setting(settings: Settings, scrypt_calls: list[int]) -> None:
    from dataclasses import replace

    application = create_app(replace(settings, cookie_secure=True), FakeLLM(replies=["Chào."]))
    async with application.router.lifespan_context(application):
        ready_owner(application)
        async with client(application) as c:
            assert "Secure" in _cookie(await login(c, "ban", OWNER_PW), "__Host-lyris_session=")


async def test_disabled_and_expired_temp_only_with_right_password(app: FastAPI, fake_clock: FakeClock) -> None:
    repo = repo_of(app)
    ready_owner(app)
    mid = add_member(app)
    with repo.transaction():
        store.set_status(repo.conn, mid, "disabled", clock.now())
    async with client(app) as c:
        wrong = await login(c, "mai", "không phải mật khẩu")
        assert wrong.status_code == 401 and wrong.json()["detail"] == "Tên đăng nhập hoặc mật khẩu không đúng."
        right = await login(c, "mai", MEMBER_PW)
        assert right.status_code == 403
        assert right.json() == {"detail": "Tài khoản này đang tạm khoá. Hãy liên hệ người quản lý Lyris.", "technical": None, "code": "account_disabled"}
        assert not any(h.startswith("lyris_session=") for h in right.headers.get_list("set-cookie"))
    with repo.transaction():
        store.set_status(repo.conn, mid, "active", clock.now())
    set_password(repo, mid, "mật khẩu tạm thời", temporary=True)
    set_password(repo, owner_id(app), "mật khẩu tạm chủ máy", temporary=True)
    fake_clock.advance(hours=72, seconds=1)
    async with client(app) as c:
        assert (await login(c, "mai", "sai rồi nhé")).json()["detail"] == "Tên đăng nhập hoặc mật khẩu không đúng."
        expired = await login(c, "mai", "mật khẩu tạm thời")
        assert expired.status_code == 401 and expired.json()["detail"] == "Mật khẩu tạm đã hết hạn. Hãy nhờ người quản lý Lyris đặt lại."
        owner = await login(c, "ban", "mật khẩu tạm chủ máy")
        assert owner.json()["detail"] == "Mật khẩu tạm đã hết hạn. Chạy lại lệnh đặt lại mật khẩu trên Mac."


# ---------------------------------------------------------------------------- phiên


async def test_db_stores_only_token_hash(app: FastAPI) -> None:
    ready_owner(app)
    async with client(app) as c:
        resp = await login(c, "ban", OWNER_PW)
        token = c.cookies["lyris_session"]
        device = c.cookies["lyris_device"]
    assert len(token) >= 43 and token not in resp.text
    text = dump(repo_of(app))
    assert token not in text and device not in text
    assert hashlib.sha256(token.encode()).hexdigest().upper() in text.upper()  # BLOB in dump dạng X'..'


async def test_login_with_old_cookie_drops_that_session(app: FastAPI) -> None:
    ready_owner(app)
    repo = repo_of(app)
    async with client(app) as c:
        await login(c, "ban", OWNER_PW)
        first = c.cookies["lyris_session"]
        await login(c, "ban", OWNER_PW)
        second = c.cookies["lyris_session"]
        assert first != second
        hashes = {bytes(r[0]) for r in rows(repo, "SELECT token_hash FROM sessions")}
        assert hashes == {hashlib.sha256(second.encode()).digest()}
    # Phiên "cài sẵn" của người khác cũng bị xoá khi đăng nhập bằng cookie đó.
    add_member(app)
    async with client(app) as planted:
        await login(planted, "mai", MEMBER_PW)
        planted_token = planted.cookies["lyris_session"]
    async with client(app, cookies={"lyris_session": planted_token}) as c:
        await login(c, "ban", OWNER_PW)
    assert count(repo, "SELECT COUNT(*) FROM sessions WHERE token_hash = ?", hashlib.sha256(planted_token.encode()).digest()) == 0


async def test_session_limit_drops_oldest(app: FastAPI, fake_clock: FakeClock) -> None:
    oid = ready_owner(app)
    repo = repo_of(app)
    tokens = []
    for _ in range(store.MAX_SESSIONS + 1):
        fake_clock.advance(seconds=1)
        async with client(app) as c:
            await login(c, "ban", OWNER_PW)
            tokens.append(c.cookies["lyris_session"])
    assert count(repo, "SELECT COUNT(*) FROM sessions WHERE account_id = ?", oid) == store.MAX_SESSIONS
    async with client(app, cookies={"lyris_session": tokens[0]}) as c:
        assert (await c.get("/api/stories")).status_code == 401
    async with client(app, cookies={"lyris_session": tokens[1]}) as c:
        assert (await c.get("/api/stories")).status_code == 200


async def test_sliding_expiry_touches_at_most_hourly(app: FastAPI, fake_clock: FakeClock) -> None:
    ready_owner(app)
    repo = repo_of(app)
    async with client(app) as c:
        await login(c, "ban", OWNER_PW)
        start = rows(repo, "SELECT last_seen_at, expires_at FROM sessions")[0]
        fake_clock.advance(minutes=59)
        resp = await c.get("/api/stories")
        assert resp.status_code == 200 and "set-cookie" not in resp.headers
        assert tuple(rows(repo, "SELECT last_seen_at, expires_at FROM sessions")[0]) == tuple(start)
        fake_clock.advance(minutes=2)
        resp = await c.get("/api/stories")
        assert resp.status_code == 200
        refreshed = _cookie(resp, "lyris_session=")
        assert f"Max-Age={30 * 24 * 3600}" in refreshed
        last_seen, expires = rows(repo, "SELECT last_seen_at, expires_at FROM sessions")[0]
        assert last_seen == clock.iso(fake_clock.t) and expires == clock.iso(fake_clock.t + timedelta(days=30))
        # File ảnh (FileResponse) cũng mang cookie gia hạn: qua middleware, không qua response_model.
        fake_clock.advance(hours=2)
        avatar = await c.get("/api/account/avatar")
        assert avatar.status_code == 404 and any(h.startswith("lyris_session=") for h in avatar.headers.get_list("set-cookie"))


async def test_idle_30_days_logs_out(app: FastAPI, fake_clock: FakeClock) -> None:
    ready_owner(app)
    async with client(app) as c:
        await login(c, "ban", OWNER_PW)
        fake_clock.advance(days=30, seconds=1)
        resp = await c.get("/api/stories")
        assert resp.status_code == 401 and resp.json()["detail"] == "Bạn đã bị đăng xuất. Hãy đăng nhập lại."
        assert _cookie(resp, "lyris_session=").startswith("lyris_session=; Path=/; Max-Age=0")
    assert count(repo_of(app), "SELECT COUNT(*) FROM sessions") == 0


async def test_absolute_expiry_180_days(app: FastAPI, fake_clock: FakeClock) -> None:
    ready_owner(app)
    async with client(app) as c:
        await login(c, "ban", OWNER_PW)
        for _ in range(8):  # dùng đều 20 ngày một lần: hạn trượt luôn còn
            fake_clock.advance(days=20)
            assert (await c.get("/api/stories")).status_code == 200
        expires = rows(repo_of(app), "SELECT created_at, expires_at FROM sessions")[0]
        assert clock.parse(expires[1]) == clock.parse(expires[0]) + timedelta(days=180)
        fake_clock.advance(days=20, seconds=1)  # ngày 180 + 1 giây
        assert (await c.get("/api/stories")).status_code == 401


async def test_logout_and_logout_all(app: FastAPI) -> None:
    oid = ready_owner(app)
    repo = repo_of(app)
    async with client(app) as a, client(app) as b, client(app) as other:
        for c in (a, b, other):
            await login(c, "ban", OWNER_PW)
        resp = await a.post("/api/auth/logout")
        assert resp.status_code == 204 and _cookie(resp, "lyris_session=").startswith("lyris_session=;")
        assert not any(h.startswith("lyris_device=") for h in resp.headers.get_list("set-cookie"))  # giữ cookie thiết bị
        assert "lyris_device" in a.cookies
        assert (await a.get("/api/stories")).status_code == 401
        assert (await b.get("/api/stories")).status_code == 200
        assert count(repo, "SELECT COUNT(*) FROM sessions WHERE account_id = ?", oid) == 2
        assert (await b.post("/api/auth/logout-all")).status_code == 204
        assert (await other.get("/api/stories")).status_code == 401
    assert count(repo, "SELECT COUNT(*) FROM sessions") == 0


async def test_change_password_rotates_sessions(app: FastAPI, auth_log: pytest.LogCaptureFixture) -> None:
    ready_owner(app)
    async with client(app) as here, client(app) as elsewhere:
        await login(here, "ban", OWNER_PW)
        await login(elsewhere, "ban", OWNER_PW)
        old_token = here.cookies["lyris_session"]
        new_pw = "gió thổi qua đồi"
        bad = await here.post("/api/auth/change-password", json={"current_password": "sai mật khẩu", "new_password": new_pw})
        assert bad.status_code == 400 and bad.json()["detail"] == "Mật khẩu hiện tại không đúng."
        same = await here.post("/api/auth/change-password", json={"current_password": OWNER_PW, "new_password": OWNER_PW})
        assert same.status_code == 422 and same.json()["detail"] == "Mật khẩu mới phải khác mật khẩu cũ."
        short = await here.post("/api/auth/change-password", json={"current_password": OWNER_PW, "new_password": "ngắn"})
        assert short.json()["detail"] == "Mật khẩu cần ít nhất 8 ký tự."
        handle = await here.post("/api/auth/change-password", json={"current_password": OWNER_PW, "new_password": "BAN"})
        assert handle.json()["detail"] == "Mật khẩu cần ít nhất 8 ký tự."
        ok = await here.post("/api/auth/change-password", json={"current_password": OWNER_PW, "new_password": new_pw})
        assert ok.status_code == 200, ok.text
        assert here.cookies["lyris_session"] != old_token
        assert (await here.get("/api/stories")).status_code == 200
        assert (await elsewhere.get("/api/stories")).status_code == 401
    async with client(app) as c:
        assert (await login(c, "ban", OWNER_PW)).status_code == 401
        assert (await login(c, "ban", new_pw)).status_code == 200
    assert OWNER_PW not in auth_log.text and new_pw not in auth_log.text


async def test_password_rule_same_as_handle(app: FastAPI) -> None:
    ready_owner(app)
    with repo_of(app).transaction():
        repo_of(app).conn.execute("UPDATE accounts SET handle = 'trangsang' WHERE role = 'owner'")
    async with client(app) as c:
        await login(c, "trangsang", OWNER_PW)
        resp = await c.post("/api/auth/change-password", json={"current_password": OWNER_PW, "new_password": "@TrangSang"})
        assert resp.status_code == 422 and resp.json()["detail"] == "Mật khẩu không được giống tên đăng nhập."


# ---------------------------------------------------------------------------- đổi mật khẩu bắt buộc (mật khẩu tạm)


async def test_admin_reset_then_forced_change(app: FastAPI, fake_clock: FakeClock, auth_log: pytest.LogCaptureFixture) -> None:
    ready_owner(app)
    mid = add_member(app)
    repo = repo_of(app)
    async with client(app) as owner, client(app) as member:
        await login(owner, "ban", OWNER_PW)
        await login(member, "mai", MEMBER_PW)
        reset = await owner.post(f"/api/admin/accounts/{mid}/reset-password")
        assert reset.status_code == 200, reset.text
        assert reset.headers["cache-control"] == "no-store"
        temporary = reset.json()["temporary_password"]
        assert reset.json()["account"]["must_change_password"] is True
        assert len(temporary) == 14 and temporary.count("-") == 2
        assert not set(temporary.replace("-", "")) & set("0o1liI")
        assert (await member.get("/api/stories")).status_code == 401  # phiên cũ mất
        self_reset = await owner.post(f"/api/admin/accounts/{owner_id(app)}/reset-password")
        assert self_reset.status_code == 409 and self_reset.json()["detail"] == "Bạn hãy đổi mật khẩu của mình trong Tài khoản."
        assert (await owner.post("/api/admin/accounts/999/reset-password")).status_code == 404
    expires = rows(repo, "SELECT password_expires_at FROM accounts WHERE id = ?", mid)[0][0]
    assert clock.parse(expires) == fake_clock.t + timedelta(hours=72)
    assert temporary not in auth_log.text
    async with client(app) as member:
        assert (await login(member, "mai", MEMBER_PW)).status_code == 401
        resp = await login(member, "mai", temporary)
        assert resp.status_code == 200 and resp.json()["account"]["must_change_password"] is True
        blocked = await member.get("/api/stories")
        assert blocked.status_code == 403
        assert blocked.json() == {"detail": "Hãy đặt mật khẩu mới để tiếp tục.", "technical": None, "code": "password_change_required"}
        # Bỏ dở quá 72 giờ, phiên vẫn sống: vẫn đổi được bằng mật khẩu tạm (hạn chỉ xét lúc đăng nhập).
        fake_clock.advance(hours=73)
        changed = await member.post("/api/auth/change-password", json={"current_password": temporary, "new_password": "mật khẩu mới của Mai"})
        assert changed.status_code == 200, changed.text
        assert changed.json()["account"]["must_change_password"] is False
        assert (await member.get("/api/stories")).status_code == 200
    row = rows(repo, "SELECT must_change_password, password_expires_at FROM accounts WHERE id = ?", mid)[0]
    assert tuple(row) == (0, None)


# ---------------------------------------------------------------------------- giới hạn thử sai


def _fail_rows(repo: Repo, n: int, *, kind: str = "login", handle: str | None, ip: str, device: bytes | None = None) -> None:
    with repo.transaction():
        for _ in range(n):
            store.record_attempt(repo.conn, kind, handle=handle, ip=ip, ok=False, now=clock.now(), device=device)  # type: ignore[arg-type]


async def test_pair_limit_and_reset_by_success(app: FastAPI, scrypt_calls: list[int]) -> None:
    ready_owner(app)
    repo = repo_of(app)
    async with client(app, peer=LAN_PEER) as c:
        for _ in range(4):
            assert (await login(c, "ban", "sai mật khẩu")).status_code == 401
        async with client(app, peer=LAN_PEER) as same_ip:  # tab khác, cùng IP, chưa có cookie thiết bị
            assert (await login(same_ip, "ban", OWNER_PW)).status_code == 200  # lần đúng làm mới cặp (handle, IP)
        assert "lyris_device" not in c.cookies
        for _ in range(5):
            assert (await login(c, "ban", "sai mật khẩu")).status_code == 401
        scrypt_calls.clear()
        before = count(repo, "SELECT COUNT(*) FROM auth_attempts")
        blocked = await login(c, "ban", OWNER_PW)
        assert blocked.status_code == 429
        assert blocked.json() == {"detail": "Bạn đã thử sai nhiều lần. Hãy đợi 15 phút rồi thử lại.", "technical": None, "code": "rate_limited"}
        assert 890 <= int(blocked.headers["retry-after"]) <= 900
        assert scrypt_calls == [] and count(repo, "SELECT COUNT(*) FROM auth_attempts") == before
    async with client(app, peer=("192.168.1.21", 1)) as c:  # IP khác thì không bị cặp này chặn
        assert (await login(c, "ban", OWNER_PW)).status_code == 200


async def test_pair_block_lifts_after_15_minutes(app: FastAPI, fake_clock: FakeClock) -> None:
    ready_owner(app)
    async with client(app, peer=LAN_PEER) as c:
        for _ in range(5):
            await login(c, "ban", "sai mật khẩu")
        assert (await login(c, "ban", OWNER_PW)).status_code == 429
        fake_clock.advance(minutes=14)
        assert (await login(c, "ban", OWNER_PW)).status_code == 429
        fake_clock.advance(minutes=1, seconds=1)
        assert (await login(c, "ban", OWNER_PW)).status_code == 200


async def test_ip_limit_is_not_reset_by_success(app: FastAPI) -> None:
    ready_owner(app)
    add_member(app)
    repo = repo_of(app)
    ip = LAN_PEER[0]
    # 29 lần sai từ IP này vào nhiều handle (khoá theo cặp không chạm ngưỡng).
    for i in range(29):
        _fail_rows(repo, 1, handle=f"doan{i}", ip=ip)
    async with client(app, peer=LAN_PEER) as c:
        assert (await login(c, "mai", MEMBER_PW)).status_code == 200  # xen một lần đúng
        assert (await login(c, "ban", "đoán mò thôi")).status_code == 401  # lần sai thứ 30
        resp = await login(c, "ban", OWNER_PW)
        assert resp.status_code == 429  # lần đúng trước đó không làm mới bộ đếm theo IP
    async with client(app, peer=("192.168.1.99", 1)) as c:
        assert (await login(c, "ban", OWNER_PW)).status_code == 200


async def test_handle_limit_spares_known_browser(app: FastAPI) -> None:
    ready_owner(app)
    repo = repo_of(app)
    async with client(app) as mac:
        assert (await login(mac, "ban", OWNER_PW)).status_code == 200  # trình duyệt trên Mac: cookie thiết bị
        await mac.post("/api/auth/logout")
        assert "lyris_device" in mac.cookies
        # Người khác gõ sai 50 lần trong 1 giờ từ nhiều IP.
        for i in range(50):
            _fail_rows(repo, 1, handle="ban", ip=f"10.0.0.{i}")
        async with client(app, peer=("10.0.1.1", 1)) as stranger:
            assert (await login(stranger, "ban", OWNER_PW)).status_code == 429
        # Mac gửi cùng X-Forwarded-For giả cũng vậy nếu không có cookie thiết bị.
        async with client(app) as fresh_tab:
            assert (await login(fresh_tab, "ban", OWNER_PW)).status_code == 429
        resp = await login(mac, "ban", OWNER_PW)
        assert resp.status_code == 200, resp.text


async def test_known_device_has_its_own_limit(app: FastAPI) -> None:
    ready_owner(app)
    repo = repo_of(app)
    async with client(app) as c:
        await login(c, "ban", OWNER_PW)
        for _ in range(5):
            assert (await login(c, "ban", "sai mật khẩu")).status_code == 401
        assert count(repo, "SELECT COUNT(*) FROM auth_attempts WHERE ok = 0 AND device_hash IS NOT NULL") == 5
        assert (await login(c, "ban", OWNER_PW)).status_code == 429


async def test_invalid_handle_text_is_never_stored(app: FastAPI, auth_log: pytest.LogCaptureFixture) -> None:
    ready_owner(app)
    typed = "Mật Khẩu Bí Mật 99"
    async with client(app) as c:
        assert (await login(c, typed, "x")).status_code == 401
    stored = rows(repo_of(app), "SELECT handle, ip, ok FROM auth_attempts")
    assert [tuple(r) for r in stored] == [(None, "127.0.0.1", 0)]
    assert typed not in auth_log.text and typed not in dump(repo_of(app))


async def test_signup_and_change_password_limits(app: FastAPI) -> None:
    ready_owner(app)
    async with client(app, peer=LAN_PEER) as c:
        for _ in range(10):
            resp = await c.post("/api/auth/signup", json={"accept_terms": True, "invite_code": "LYR-AAAA-BBBB-CCCC", "handle": "lan", "display_name": "Lan", "password": MEMBER_PW})
            assert resp.status_code == 400
        assert (await c.post("/api/auth/signup", json={"accept_terms": True, "invite_code": "x", "handle": "lan", "display_name": "Lan", "password": MEMBER_PW})).status_code == 429
    async with client(app) as c:
        await login(c, "ban", OWNER_PW)
        for _ in range(5):
            bad = await c.post("/api/auth/change-password", json={"current_password": "sai mật khẩu", "new_password": "mật khẩu khác hẳn"})
            assert bad.status_code == 400
        blocked = await c.post("/api/auth/change-password", json={"current_password": OWNER_PW, "new_password": "mật khẩu khác hẳn"})
        assert blocked.status_code == 429


async def test_spoofed_forwarded_for_from_lan_is_ignored(app: FastAPI) -> None:
    ready_owner(app)
    for i in range(5):
        async with client(app, peer=LAN_PEER, headers={"X-Forwarded-For": f"1.2.3.{i}"}) as c:
            await login(c, "ban", "sai mật khẩu")
    async with client(app, peer=LAN_PEER, headers={"X-Forwarded-For": "127.0.0.1"}) as c:
        assert (await login(c, "ban", OWNER_PW)).status_code == 429
    ips = {r[0] for r in rows(repo_of(app), "SELECT ip FROM auth_attempts")}
    assert ips == {LAN_PEER[0]}
    # Qua Vite (peer 127.0.0.1): phần tử cuối là IP thật; phần client tự gửi phía trước bị bỏ qua.
    async with client(app, headers={"X-Forwarded-For": "127.0.0.1, 192.168.1.20"}) as c:
        assert (await login(c, "ban", OWNER_PW)).status_code == 429


# ---------------------------------------------------------------------------- CSRF, cache


async def test_csrf_rules(app: FastAPI) -> None:
    ready_owner(app)
    async with client(app, csrf=False) as c:
        resp = await login(c, "ban", OWNER_PW)  # login cũng bị chặn
        assert resp.status_code == 403
        assert resp.json() == {"detail": "Yêu cầu không hợp lệ. Hãy tải lại trang.", "technical": None, "code": "csrf"}
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            assert (await c.request(method, "/api/stories/1")).json().get("code") == "csrf", method
    async with client(app) as c:
        await login(c, "ban", OWNER_PW)
        assert (await c.get("/api/stories", headers={"X-Lyris": ""})).status_code == 200  # GET không cần
        body = {"name": "Mai", "gender": "female"}
        for headers in (
            {"Origin": "http://evil.example:5173"},
            {"Origin": "http://test:8080"},
            {"Origin": "null"},
            {"Sec-Fetch-Site": "cross-site"},
            {"X-Lyris": "0"},
        ):
            resp = await c.post("/api/personas", json=body, headers=headers)
            assert resp.status_code == 403 and resp.json()["code"] == "csrf", headers
        for headers in ({"Origin": "http://test"}, {"Origin": "http://TEST:80"}, {"Sec-Fetch-Site": "same-origin"}):
            assert (await c.post("/api/personas", json=body, headers=headers)).status_code == 200, headers
    async with client(app, headers={"Host": "192.168.1.5:5173"}) as c:
        await login(c, "ban", OWNER_PW)
        ok = await c.post("/api/personas", json={"name": "Lan", "gender": "female"}, headers={"Origin": "http://192.168.1.5:5173"})
        assert ok.status_code == 200
        bad = await c.post("/api/personas", json={"name": "Lan", "gender": "female"}, headers={"Origin": "http://192.168.1.5:8080"})
        assert bad.status_code == 403


async def test_cache_headers(app: FastAPI) -> None:
    from tests.test_api_studio import png_bytes

    ready_owner(app)
    async with client(app) as c:
        assert (await c.get("/api/auth/me")).headers["cache-control"] == "no-store"
        await login(c, "ban", OWNER_PW)
        assert (await c.get("/api/stories")).headers["cache-control"] == "no-store"
        persona = (await c.post("/api/personas", json={"name": "Mai", "gender": "female"})).json()
        png = {"content": png_bytes(), "headers": {"Content-Type": "image/png"}}
        assert (await c.put(f"/api/personas/{persona['id']}/avatar", **png)).status_code == 200
        assert (await c.get(f"/api/personas/{persona['id']}/avatar")).headers["cache-control"].startswith("private")
        card = (await c.get("/api/cards")).json()[0]
        assert (await c.put(f"/api/cards/{card['id']}/avatar", **png)).status_code == 200
        assert (await c.get(f"/api/cards/{card['id']}/avatar")).headers["cache-control"].startswith("private")
        assert (await c.put("/api/account/avatar", **png)).status_code == 200
        assert (await c.get("/api/account/avatar")).headers["cache-control"].startswith("private")
        assert (await c.get("/api/accounts/ban/avatar")).headers["cache-control"].startswith("private")
        templates = (await c.get("/api/templates")).json()
        image = next(t["image_url"] for t in templates if t["image_url"])
        assert (await c.get(image)).headers["cache-control"].startswith("public")


# ---------------------------------------------------------------------------- mã mời, tạo tài khoản


async def test_invites_and_signup(app: FastAPI, fake_clock: FakeClock, auth_log: pytest.LogCaptureFixture) -> None:
    ready_owner(app)
    repo = repo_of(app)
    async with client(app) as owner:
        await login(owner, "ban", OWNER_PW)
        created = await owner.post("/api/admin/invites", json={"note": "  cho   Mai ", "expires_in_days": 1})
        assert created.status_code == 200, created.text
        data = created.json()
        code = data["code"]
        normalized = codes.normalize_code(code)
        assert normalized is not None and code == codes.format_invite(normalized)
        invite = data["invite"]
        assert invite["hint"] == normalized[-4:] and invite["note"] == "cho Mai" and invite["status"] == "active"
        assert clock.parse(invite["expires_at"]) == fake_clock.t + timedelta(days=1)
        listing = (await owner.get("/api/admin/invites")).json()
        assert listing == [invite] and code not in str(listing)
        text = dump(repo)
        assert normalized not in text and code not in text and code not in auth_log.text
        assert hashlib.sha256(normalized.encode()).hexdigest().upper() in text.upper()

    # Mã gõ chữ thường, không gạch, đổi 0 thành O: vẫn nhận.
    typed = normalized.lower().replace("0", "o")
    async with client(app) as newbie:
        taken = await newbie.post("/api/auth/signup", json={"accept_terms": True, "invite_code": typed, "handle": "BAN", "display_name": "Mai", "password": MEMBER_PW})
        assert taken.status_code == 422 and "đã có người dùng" in taken.json()["detail"]
        weak = await newbie.post("/api/auth/signup", json={"accept_terms": True, "invite_code": typed, "handle": "mai", "display_name": "Mai", "password": "matkhau123"})
        assert weak.status_code == 422
        resp = await newbie.post("/api/auth/signup", json={"accept_terms": True, "invite_code": typed, "handle": "@Mai", "display_name": " Mai ", "password": MEMBER_PW})
        assert resp.status_code == 200, resp.text
        account = resp.json()["account"]
        assert (account["handle"], account["display_name"], account["role"], account["profile_completed"]) == ("mai", "Mai", "member", True)
        assert (await newbie.get("/api/stories")).json() == []
        # Lần dùng thứ hai: cùng chữ lỗi như mã sai.
    async with client(app) as again:
        reused = await again.post("/api/auth/signup", json={"accept_terms": True, "invite_code": code, "handle": "lan", "display_name": "Lan", "password": MEMBER_PW})
        assert reused.status_code == 400 and reused.json()["detail"] == "Mã mời không đúng hoặc đã hết hạn."
    row = rows(repo, "SELECT a.invited_by, i.used_by, i.used_at FROM accounts a JOIN invites i ON i.used_by = a.id WHERE a.handle = 'mai'")[0]
    assert row[0] == owner_id(app) and row[2] is not None
    async with client(app) as owner:
        await login(owner, "ban", OWNER_PW)
        used = (await owner.get("/api/admin/invites")).json()[0]
        assert used["status"] == "used" and used["used_by_handle"] == "mai"
        assert (await owner.delete(f"/api/admin/invites/{used['id']}")).json()["detail"] == "Mã này đã được dùng."


async def test_invite_errors_look_the_same(app: FastAPI, fake_clock: FakeClock) -> None:
    ready_owner(app)
    async with client(app) as owner:
        await login(owner, "ban", OWNER_PW)
        expired = (await owner.post("/api/admin/invites", json={"expires_in_days": 1})).json()
        revoked = (await owner.post("/api/admin/invites", json={})).json()
        assert revoked["invite"]["expires_at"] == clock.iso(fake_clock.t + timedelta(days=7))
        assert (await owner.delete(f"/api/admin/invites/{revoked['invite']['id']}")).status_code == 204
        assert (await owner.post("/api/admin/invites", json={"expires_in_days": 2})).status_code == 422
        assert (await owner.post("/api/admin/invites", json={"note": "x" * 61})).status_code == 422
    fake_clock.advance(days=1, seconds=1)
    async with client(app) as owner:
        await login(owner, "ban", OWNER_PW)
        statuses = {i["id"]: i["status"] for i in (await owner.get("/api/admin/invites")).json()}
        assert statuses == {expired["invite"]["id"]: "expired", revoked["invite"]["id"]: "revoked"}
    body = {"handle": "ban", "display_name": "Ai đó", "password": MEMBER_PW}
    async with client(app) as c:
        details = set()
        for code in (expired["code"], revoked["code"], "LYR-AAAA-BBBB-CCCC", "rác"):
            resp = await c.post("/api/auth/signup", json={"accept_terms": True, "invite_code": code, **body})
            assert resp.status_code == 400  # mã kiểm trước: handle "ban" đã có người dùng không bị lộ
            details.add(resp.json()["detail"])
        assert details == {"Mã mời không đúng hoặc đã hết hạn."}


async def test_signup_race_on_one_invite(app: FastAPI) -> None:
    ready_owner(app)
    async with client(app) as owner:
        await login(owner, "ban", OWNER_PW)
        code = (await owner.post("/api/admin/invites", json={})).json()["code"]
    async with client(app) as a, client(app) as b:
        results = await asyncio.gather(
            a.post("/api/auth/signup", json={"accept_terms": True, "invite_code": code, "handle": "mai", "display_name": "Mai", "password": MEMBER_PW}),
            b.post("/api/auth/signup", json={"accept_terms": True, "invite_code": code, "handle": "lan", "display_name": "Lan", "password": MEMBER_PW}),
        )
    assert sorted(r.status_code for r in results) == [200, 400]
    assert count(repo_of(app), "SELECT COUNT(*) FROM accounts WHERE role = 'member'") == 1


async def test_active_invite_cap(app: FastAPI) -> None:
    ready_owner(app)
    async with client(app) as owner:
        await login(owner, "ban", OWNER_PW)
        for _ in range(store.MAX_ACTIVE_INVITES):
            assert (await owner.post("/api/admin/invites", json={})).status_code == 200
        assert (await owner.post("/api/admin/invites", json={})).status_code == 409
        first = (await owner.get("/api/admin/invites")).json()[-1]
        assert (await owner.delete(f"/api/admin/invites/{first['id']}")).status_code == 204
        assert (await owner.post("/api/admin/invites", json={})).status_code == 200
        assert (await owner.delete("/api/admin/invites/9999")).status_code == 404


# ---------------------------------------------------------------------------- quản trị


async def test_admin_accounts_disable_enable(app: FastAPI, fake_clock: FakeClock) -> None:
    oid = ready_owner(app)
    mid = add_member(app)
    async with client(app) as owner, client(app) as member, client(app) as member2:
        await login(owner, "ban", OWNER_PW)
        fake_clock.advance(minutes=1)
        await login(member, "mai", MEMBER_PW)
        await login(member2, "mai", MEMBER_PW)
        listing = (await owner.get("/api/admin/accounts")).json()
        assert [a["handle"] for a in listing] == ["ban", "mai"]
        mai = listing[1]
        assert set(mai) == {
            "id", "handle", "display_name", "avatar_url", "role", "status", "must_change_password",
            "created_at", "last_login_at", "invited_by_handle", "session_count",
        }
        assert (mai["role"], mai["status"], mai["session_count"]) == ("member", "active", 2)
        assert mai["last_login_at"] == clock.iso(fake_clock.t)
        assert (await owner.post(f"/api/admin/accounts/{oid}/disable")).json()["detail"] == "Không tạm khoá được tài khoản chủ máy."
        disabled = await owner.post(f"/api/admin/accounts/{mid}/disable")
        assert disabled.status_code == 200 and disabled.json()["status"] == "disabled"
        assert disabled.json()["session_count"] == 0
        assert (await member.get("/api/stories")).status_code == 401
        assert (await login(member, "mai", MEMBER_PW)).json()["code"] == "account_disabled"
        enabled = await owner.post(f"/api/admin/accounts/{mid}/enable")
        assert enabled.json()["status"] == "active"
        assert (await login(member, "mai", MEMBER_PW)).status_code == 200
        assert (await owner.post("/api/admin/accounts/999/disable")).status_code == 404


async def test_auth_logging_has_no_secrets(app: FastAPI, auth_log: pytest.LogCaptureFixture) -> None:
    ready_owner(app)
    async with client(app, peer=LAN_PEER, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/130.0 Safari/537.36"}) as c:
        await login(c, "ban", "mật khẩu sai bét")
        await login(c, "ban", OWNER_PW)
        token = c.cookies["lyris_session"]
    text = auth_log.text
    assert "Đăng nhập sai: @ban, IP 192.168.1.20" in text
    assert "Đăng nhập: @ban, IP 192.168.1.20, Chrome · Mac" in text
    for secret in (OWNER_PW, "mật khẩu sai bét", token):
        assert secret not in text


async def test_persona_default_moves_with_account(app: FastAPI) -> None:
    """Persona mặc định là cột của tài khoản: xoá persona thì cột về NULL (ON DELETE SET NULL)."""
    repo = repo_of(app)
    oid = ready_owner(app)
    persona = repo.create_persona(Persona(name="Mai", gender="female"), account_id=repo.owner_id())
    assert persona.id is not None
    repo.set_app_settings(repo.get_app_settings(account_id=repo.owner_id()).model_copy(update={"default_persona_id": persona.id}), account_id=repo.owner_id())
    assert rows(repo, "SELECT default_persona_id FROM accounts WHERE id = ?", oid)[0][0] == persona.id
    assert count(repo, "SELECT COUNT(*) FROM app_settings WHERE key = 'default_persona_id'") == 0
    repo.delete_persona(persona.id, account_id=ANY_ACCOUNT)
    assert rows(repo, "SELECT default_persona_id FROM accounts WHERE id = ?", oid)[0][0] is None


async def test_startup_purges_expired_sessions_and_old_attempts(settings: Settings, fake_clock: FakeClock, scrypt_calls: list[int]) -> None:
    application = create_app(settings, FakeLLM(replies=["Chào."]))
    async with application.router.lifespan_context(application):
        ready_owner(application)
        async with client(application) as c:
            await login(c, "ban", "sai mật khẩu")
            await login(c, "ban", OWNER_PW)
        fake_clock.advance(days=29)
        async with client(application) as c:
            await login(c, "ban", OWNER_PW)  # phiên này còn hạn khi khởi động lại
        repo = repo_of(application)
        assert count(repo, "SELECT COUNT(*) FROM sessions") == 2
        assert count(repo, "SELECT COUNT(*) FROM auth_attempts") == 3
    fake_clock.advance(days=2)
    application = create_app(settings, FakeLLM(replies=["Chào."]))
    async with application.router.lifespan_context(application):
        repo = repo_of(application)
        assert count(repo, "SELECT COUNT(*) FROM sessions") == 1
        assert count(repo, "SELECT COUNT(*) FROM auth_attempts") == 1  # chỉ lần đúng ở ngày 29 còn trong 30 ngày
