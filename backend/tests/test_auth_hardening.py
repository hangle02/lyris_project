"""Phase 4b, sửa sau phản biện lần 2 (docs/auth.md §13, mục 49-54): lần thử song song không lọt qua giới hạn,
đăng nhập đang băm không sống sót qua lần đổi mật khẩu, băm mật khẩu không chiếm thread pool chung, luật đổi
mật khẩu theo tài khoản (không theo @handle), và hai tiến trình migrate cùng lúc.

DB tạm, FakeLLM, scrypt rẻ (fixture `scrypt_calls`) có thêm độ trễ khi cần mô phỏng thời gian băm thật.
"""
from __future__ import annotations

import asyncio
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

import anyio
import anyio.to_thread
import httpx
import pytest
from fastapi import FastAPI

from lyris.auth import errors, passwords
from lyris.db.connection import connect, migrate
from tests.test_auth_api import (  # noqa: F401
    LAN_PEER,
    MEMBER_PW,
    OWNER_PW,
    _fail_rows,
    add_member,
    app,
    client,
    count,
    fake_clock,
    login,
    ready_owner,
    repo_of,
    scrypt_calls,
    settings,
)

NEW_PW = "gió thổi qua đồi"


@pytest.fixture
def slow_scrypt(monkeypatch: pytest.MonkeyPatch, scrypt_calls: list[int]) -> list[int]:
    """scrypt rẻ nhưng mất 50 ms (chạy trong thread như thật), để các request song song chồng lên nhau."""
    cheap = passwords._scrypt

    def slow(password: bytes, salt: bytes, n: int, r: int, p: int) -> bytes:
        time.sleep(0.05)
        return cheap(password, salt, n, r, p)

    monkeypatch.setattr(passwords, "_scrypt", slow)
    return scrypt_calls


def codes(responses: list[httpx.Response]) -> dict[int, int]:
    out: dict[int, int] = {}
    for r in responses:
        out[r.status_code] = out.get(r.status_code, 0) + 1
    return out


# ---------------------------------------------------------------------------- lần thử song song


async def test_parallel_login_guesses_respect_pair_limit(app: FastAPI, slow_scrypt: list[int]) -> None:
    ready_owner(app)
    repo = repo_of(app)
    slow_scrypt.clear()
    async with client(app, peer=("192.168.1.172", 5555)) as c:
        burst = await asyncio.gather(*(login(c, "ban", f"đoán thử số {i}") for i in range(12)))
        assert codes(burst) == {401: 5, 429: 7}  # (handle, IP): 5 lần / 15 phút, kể cả khi gửi cùng lúc
        assert len(slow_scrypt) == 5  # chỉ 5 lần đoán được so
        assert count(repo, "SELECT COUNT(*) FROM auth_attempts WHERE ok = 0") == 5
        assert (await login(c, "ban", OWNER_PW)).status_code == 429


async def test_parallel_login_guesses_respect_ip_limit(
    app: FastAPI, slow_scrypt: list[int], monkeypatch: pytest.MonkeyPatch
) -> None:
    ready_owner(app)
    repo = repo_of(app)
    slow_scrypt.clear()
    monkeypatch.setattr(passwords, "MAX_PENDING_HASHES", 100)  # chỉ xét luật IP, không xét hàng chờ băm
    async with client(app, peer=("192.168.1.172", 5555)) as c:
        # 40 handle khác nhau: luật (handle, IP) không chạm, luật IP (30 / 15 phút) phải giữ.
        burst = await asyncio.gather(*(login(c, f"nguoi{i}", "đoán mò thôi") for i in range(40)))
    assert codes(burst) == {401: 30, 429: 10}
    assert len(slow_scrypt) == 30
    assert count(repo, "SELECT COUNT(*) FROM auth_attempts WHERE ok = 0") == 30


async def test_login_burst_over_the_hash_queue_records_only_evaluated(app: FastAPI, slow_scrypt: list[int]) -> None:
    ready_owner(app)
    repo = repo_of(app)
    slow_scrypt.clear()
    async with client(app, peer=("192.168.1.172", 5555)) as c:
        burst = await asyncio.gather(*(login(c, f"nguoi{i}", "đoán mò thôi") for i in range(40)))
    got = codes(burst)
    assert got == {401: passwords.MAX_PENDING_HASHES, 503: 40 - passwords.MAX_PENDING_HASHES}
    # 503: mật khẩu không được so, chỗ đã giữ bị bỏ (không tính là lần sai).
    assert len(slow_scrypt) == got[401]
    assert count(repo, "SELECT COUNT(*) FROM auth_attempts") == got[401]


async def test_parallel_change_password_guesses_respect_limit(app: FastAPI, slow_scrypt: list[int]) -> None:
    ready_owner(app)
    async with client(app) as c:
        assert (await login(c, "ban", OWNER_PW)).status_code == 200
        slow_scrypt.clear()
        burst = await asyncio.gather(
            *(
                c.post("/api/auth/change-password", json={"current_password": f"sai số {i}", "new_password": NEW_PW})
                for i in range(12)
            )
        )
        assert codes(burst) == {400: 5, 429: 7}
        assert len(slow_scrypt) == 5
        # Đúng mật khẩu hiện tại cũng phải đợi: 5 lần sai đã được tính.
        right = await c.post("/api/auth/change-password", json={"current_password": OWNER_PW, "new_password": NEW_PW})
        assert right.status_code == 429


async def test_success_settles_the_reserved_attempt(app: FastAPI) -> None:
    ready_owner(app)
    repo = repo_of(app)
    async with client(app, peer=LAN_PEER) as c:
        assert (await login(c, "ban", "sai mật khẩu")).status_code == 401
        assert (await login(c, "ban", OWNER_PW)).status_code == 200
    got = [tuple(r) for r in repo.conn.execute("SELECT handle, ok, device_hash IS NOT NULL FROM auth_attempts ORDER BY id")]
    assert got == [("ban", 0, 0), ("ban", 1, 1)]  # một dòng mỗi lần thử; lần đúng mang cookie thiết bị


# ---------------------------------------------------------------------------- đăng nhập đang băm vs đổi mật khẩu


def _pause_first_verify(monkeypatch: pytest.MonkeyPatch) -> tuple[asyncio.Event, asyncio.Event]:
    """Lần so mật khẩu đầu tiên dừng lại SAU khi scrypt xong (kết quả đã có), chờ `release`."""
    real_verify = passwords.verify_password
    reached, release = asyncio.Event(), asyncio.Event()
    calls = {"n": 0}

    async def gated(password: str, stored: passwords.PasswordHash | None) -> bool:
        result = await real_verify(password, stored)
        calls["n"] += 1
        if calls["n"] == 1:
            reached.set()
            await release.wait()
        return result

    monkeypatch.setattr(passwords, "verify_password", gated)
    return reached, release


async def test_login_in_flight_loses_to_password_change(app: FastAPI, monkeypatch: pytest.MonkeyPatch) -> None:
    oid = ready_owner(app)
    repo = repo_of(app)
    async with client(app) as owner, client(app, peer=("10.0.0.9", 1)) as attacker:
        assert (await login(owner, "ban", OWNER_PW)).status_code == 200
        reached, release = _pause_first_verify(monkeypatch)
        task = asyncio.create_task(login(attacker, "ban", OWNER_PW))
        await reached.wait()
        changed = await owner.post("/api/auth/change-password", json={"current_password": OWNER_PW, "new_password": NEW_PW})
        assert changed.status_code == 200, changed.text
        release.set()
        late = await task
        assert late.status_code == 401
        assert late.json()["detail"] == errors.BAD_LOGIN
        assert (await attacker.get("/api/account")).status_code == 401
        assert count(repo, "SELECT COUNT(*) FROM sessions WHERE account_id = ?", oid) == 1  # chỉ phiên của chủ máy
        assert (await owner.get("/api/account")).status_code == 200
    # Lần đăng nhập muộn được tính là một lần sai, không mang thiết bị.
    assert count(repo, "SELECT COUNT(*) FROM auth_attempts WHERE kind = 'login' AND ip = '10.0.0.9' AND ok = 0") == 1


async def test_login_in_flight_loses_to_disable(app: FastAPI, monkeypatch: pytest.MonkeyPatch) -> None:
    ready_owner(app)
    mid = add_member(app)
    async with client(app) as owner, client(app, peer=("10.0.0.9", 1)) as member:
        assert (await login(owner, "ban", OWNER_PW)).status_code == 200
        reached, release = _pause_first_verify(monkeypatch)
        task = asyncio.create_task(login(member, "mai", MEMBER_PW))
        await reached.wait()
        assert (await owner.post(f"/api/admin/accounts/{mid}/disable")).status_code == 200
        release.set()
        assert (await task).status_code == 401
        assert count(repo_of(app), "SELECT COUNT(*) FROM sessions WHERE account_id = ?", mid) == 0


async def test_change_password_in_flight_loses_to_admin_reset(app: FastAPI, monkeypatch: pytest.MonkeyPatch) -> None:
    ready_owner(app)
    mid = add_member(app)
    async with client(app) as owner, client(app, peer=("10.0.0.9", 1)) as member:
        assert (await login(owner, "ban", OWNER_PW)).status_code == 200
        assert (await login(member, "mai", MEMBER_PW)).status_code == 200
        reached, release = _pause_first_verify(monkeypatch)
        task = asyncio.create_task(
            member.post("/api/auth/change-password", json={"current_password": MEMBER_PW, "new_password": NEW_PW})
        )
        await reached.wait()
        reset = await owner.post(f"/api/admin/accounts/{mid}/reset-password")
        assert reset.status_code == 200
        release.set()
        assert (await task).status_code == 400  # không ghi đè mật khẩu tạm vừa đặt
        assert count(repo_of(app), "SELECT COUNT(*) FROM sessions WHERE account_id = ?", mid) == 0
    async with client(app) as fresh:
        assert (await login(fresh, "mai", reset.json()["temporary_password"])).status_code == 200


# ---------------------------------------------------------------------------- băm mật khẩu và thread pool


async def test_hashing_waits_outside_the_shared_thread_pool(slow_scrypt: list[int]) -> None:
    limiter = anyio.to_thread.current_default_thread_limiter()
    limiter.total_tokens = 4  # thu nhỏ pool chung (mặc định 40) để thấy rõ
    stored = passwords.hash_password_sync("mật khẩu nào đó")
    tasks = [asyncio.create_task(passwords.verify_password(f"đoán {i}", stored)) for i in range(10)]
    await asyncio.sleep(0.01)
    assert limiter.borrowed_tokens == 0  # các lần băm đang chờ không giữ thread của pool chung
    started = time.perf_counter()
    await anyio.to_thread.run_sync(lambda: None)  # một route/dependency `def` bất kỳ
    assert time.perf_counter() - started < 0.04
    assert await asyncio.gather(*tasks) == [False] * 10
    assert passwords.pending_hashes() == 0


async def test_parallel_hashes_are_at_most_two(monkeypatch: pytest.MonkeyPatch, scrypt_calls: list[int]) -> None:
    cheap = passwords._scrypt
    lock = threading.Lock()
    running = {"now": 0, "max": 0}

    def tracked(password: bytes, salt: bytes, n: int, r: int, p: int) -> bytes:
        with lock:
            running["now"] += 1
            running["max"] = max(running["max"], running["now"])
        time.sleep(0.02)
        try:
            return cheap(password, salt, n, r, p)
        finally:
            with lock:
                running["now"] -= 1

    monkeypatch.setattr(passwords, "_scrypt", tracked)
    await asyncio.gather(*(passwords.hash_password(f"mật khẩu {i}") for i in range(8)))
    assert running["max"] == passwords.MAX_PARALLEL_HASHES


async def test_hash_queue_is_capped(slow_scrypt: list[int]) -> None:
    stored = passwords.hash_password_sync("mật khẩu nào đó")
    extra = 5
    results = await asyncio.gather(
        *(passwords.verify_password("đoán", stored) for _ in range(passwords.MAX_PENDING_HASHES + extra)),
        return_exceptions=True,
    )
    busy = [r for r in results if isinstance(r, passwords.HashingBusy)]
    assert len(busy) == extra
    # Lần băm thứ hai của một request đã được nhận (mật khẩu mới) không bị từ chối.
    held = [asyncio.create_task(passwords.verify_password("đoán", stored)) for _ in range(passwords.MAX_PENDING_HASHES)]
    await asyncio.sleep(0)
    assert isinstance(await passwords.hash_password("mới", admit=False), passwords.PasswordHash)
    await asyncio.gather(*held)


async def test_signed_in_requests_stay_fast_during_a_login_burst(app: FastAPI, slow_scrypt: list[int]) -> None:
    ready_owner(app)
    anyio.to_thread.current_default_thread_limiter().total_tokens = 4
    async with client(app) as me:
        assert (await login(me, "ban", OWNER_PW)).status_code == 200
        peers = [client(app, peer=(f"10.1.0.{i}", 1)) for i in range(12)]
        try:
            burst = asyncio.gather(*(login(p, "ban", "đoán mò thôi") for p in peers))
            await asyncio.sleep(0.02)
            started = time.perf_counter()
            resp = await me.get("/api/account")  # route async + dependency đăng nhập `def` (thread pool chung)
            elapsed = time.perf_counter() - started
            done = await burst
        finally:
            for p in peers:
                await p.aclose()
    assert resp.status_code == 200
    assert elapsed < 0.25, elapsed  # trước khi sửa: chờ cả hàng băm (12 x 50 ms / 2)
    assert set(codes(done)) <= {401, 429}


async def test_full_hash_queue_answers_busy_and_records_nothing(
    app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    ready_owner(app)
    repo = repo_of(app)
    monkeypatch.setattr(passwords, "_pending", passwords.MAX_PENDING_HASHES)  # như đang có 16 lần băm
    async with client(app, peer=LAN_PEER) as c:
        resp = await login(c, "ban", OWNER_PW)
        assert resp.status_code == 503
        assert resp.json() == {"detail": "Lyris đang bận. Hãy thử lại sau giây lát.", "technical": None, "code": "busy"}
        assert resp.headers["retry-after"] == "5"
    assert count(repo, "SELECT COUNT(*) FROM auth_attempts") == 0


# ---------------------------------------------------------------------------- đổi @handle


async def _rename(c: httpx.AsyncClient, handle: str) -> None:
    resp = await c.put("/api/account", json={"display_name": "Bạn", "handle": handle, "bio": ""})
    assert resp.status_code == 200, resp.text


async def test_handle_rename_keeps_change_password_limit(app: FastAPI) -> None:
    ready_owner(app)
    async with client(app) as c:
        assert (await login(c, "ban", OWNER_PW)).status_code == 200
        evaluated = 0
        for new_handle in ("ban0", "ban1", "ban2"):
            for _ in range(5):
                resp = await c.post("/api/auth/change-password", json={"current_password": "sai mật khẩu", "new_password": NEW_PW})
                if resp.status_code == 400:
                    evaluated += 1
                else:
                    assert resp.status_code == 429
            await _rename(c, new_handle)
        assert evaluated == 5  # 5 lần / 15 phút cho tài khoản, đổi handle không làm mới
    # Không lưu @handle nào cho luật đổi mật khẩu.
    assert count(repo_of(app), "SELECT COUNT(*) FROM auth_attempts WHERE kind = 'change_password' AND handle NOT LIKE '#%'") == 0


async def test_handle_rename_keeps_known_browser(app: FastAPI) -> None:
    ready_owner(app)
    repo = repo_of(app)
    async with client(app) as mac:
        assert (await login(mac, "ban", OWNER_PW)).status_code == 200
        await _rename(mac, "ban_moi")
        await mac.post("/api/auth/logout")
        for i in range(50):  # người khác đoán @ban_moi 50 lần trong 1 giờ
            _fail_rows(repo, 1, handle="ban_moi", ip=f"10.0.0.{i}")
        async with client(app, peer=("10.0.1.1", 1)) as stranger:
            assert (await login(stranger, "ban_moi", OWNER_PW)).status_code == 429
        resp = await login(mac, "ban_moi", OWNER_PW)  # trình duyệt đã biết vẫn được miễn khoá theo handle
        assert resp.status_code == 200, resp.text


async def test_admin_reset_clears_change_password_failures(app: FastAPI) -> None:
    ready_owner(app)
    mid = add_member(app)
    async with client(app) as owner, client(app) as member:
        await login(owner, "ban", OWNER_PW)
        await login(member, "mai", MEMBER_PW)
        for _ in range(5):
            bad = await member.post("/api/auth/change-password", json={"current_password": "sai mật khẩu", "new_password": NEW_PW})
            assert bad.status_code == 400
        reset = await owner.post(f"/api/admin/accounts/{mid}/reset-password")
        temporary = reset.json()["temporary_password"]
    async with client(app) as member:
        assert (await login(member, "mai", temporary)).status_code == 200
        changed = await member.post("/api/auth/change-password", json={"current_password": temporary, "new_password": NEW_PW})
        assert changed.status_code == 200, changed.text


# ---------------------------------------------------------------------------- migrate cùng lúc


class _OtherProcessWinsRace:
    """Kết nối A; ngay sau lần đầu A đọc `user_version` NGOÀI transaction, "tiến trình khác" (kết nối B)
    migrate xong. Đúng khe hở cũ: đọc version trước khi giữ khoá ghi."""

    def __init__(self, conn: sqlite3.Connection, other: sqlite3.Connection) -> None:
        self._conn = conn
        self._other = other
        self.fired = False

    def execute(self, sql: str, *args: Any) -> sqlite3.Cursor:
        cur = self._conn.execute(sql, *args)
        if "user_version" in sql and not self._conn.in_transaction and not self.fired:
            self.fired = True
            value = cur.fetchone()
            migrate(self._other)
            return _Fixed(value)  # type: ignore[return-value]
        return cur

    def __getattr__(self, name: str) -> Any:
        return getattr(self._conn, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in ("_conn", "_other", "fired"):
            object.__setattr__(self, name, value)
        else:
            setattr(self._conn, name, value)


class _Fixed:
    def __init__(self, row: Any) -> None:
        self._row = row

    def fetchone(self) -> Any:
        return self._row


def test_second_process_skips_a_migration_applied_meanwhile(tmp_path: Path) -> None:
    path = tmp_path / "v7.db"
    base = connect(path)
    assert migrate(base, target=7) == 7
    base.close()
    a, b = connect(path), connect(path)
    try:
        racing = _OtherProcessWinsRace(a, b)
        final = migrate(racing)  # type: ignore[arg-type]
        assert racing.fired
        latest = int(b.execute("PRAGMA user_version").fetchone()[0])
        assert final == latest >= 8
        assert a.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert a.autocommit == sqlite3.LEGACY_TRANSACTION_CONTROL and not a.in_transaction
        assert a.execute("SELECT COUNT(*) FROM accounts WHERE role = 'owner'").fetchone()[0] == 1
    finally:
        a.close()
        b.close()


def test_two_threads_migrate_one_db(tmp_path: Path) -> None:
    for trial in range(3):
        path = tmp_path / f"v7-{trial}.db"
        base = connect(path)
        migrate(base, target=7)
        base.close()
        failures: list[BaseException] = []
        gate = threading.Barrier(2)

        def run() -> None:
            conn = connect(path)
            try:
                gate.wait()
                migrate(conn)
            except BaseException as exc:  # noqa: BLE001
                failures.append(exc)
            finally:
                conn.close()

        threads = [threading.Thread(target=run) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert failures == []


def test_failed_migration_rolls_back_and_restores_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from lyris.db import connection

    conn = connect(tmp_path / "x.db")
    try:
        migrate(conn, target=7)
        files = connection._migration_files()
        broken = tmp_path / "9999_broken.sql"
        broken.write_text("CREATE TABLE nua_chung (x INTEGER);\nTHIS IS NOT SQL;\n", encoding="utf-8")
        monkeypatch.setattr(connection, "_migration_files", lambda: [*files, (9999, broken)])
        with pytest.raises(sqlite3.OperationalError):
            migrate(conn)
        assert int(conn.execute("PRAGMA user_version").fetchone()[0]) == files[-1][0]
        assert conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'nua_chung'").fetchone() is None
        assert conn.autocommit == sqlite3.LEGACY_TRANSACTION_CONTROL and not conn.in_transaction
    finally:
        conn.close()
