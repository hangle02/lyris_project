"""Phase 4b (docs/auth.md §2.4, §8.1 "CLI"): lệnh trên Mac `scripts/lyris-admin.sh` (lyris.auth.cli)."""
from __future__ import annotations

import io
import logging
import os
import sqlite3
import subprocess
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

from lyris.api.app import create_app
from lyris.auth import cli, clock, codes, store
from lyris.config import REPO_ROOT, Settings
from lyris.db.connection import connect, migrate
from lyris.llm.fake import FakeLLM
from tests.authutil import add_member, client_for, ensure_owner_password, repo_of

SCRIPT = REPO_ROOT / "scripts" / "lyris-admin.sh"


def run(db: Path, *args: str) -> tuple[int, str]:
    out = io.StringIO()
    code = cli.main(list(args), db_path=db, out=out)
    return code, out.getvalue()


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        db_path=tmp_path / "lyris.db", ollama_url="http://127.0.0.1:9", chat_model="m:test", num_ctx=8192,
        avatars_dir=tmp_path / "avatars",
    )


@pytest.fixture
async def app(settings: Settings) -> AsyncIterator[FastAPI]:
    application = create_app(settings, FakeLLM(replies=["Chào."]))
    async with application.router.lifespan_context(application):
        yield application


def test_refuses_old_or_missing_db(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert run(tmp_path / "khong-co.db", "list")[0] == 1
    assert "Không thấy dữ liệu Lyris" in capsys.readouterr().err
    assert not (tmp_path / "khong-co.db").exists()
    old = tmp_path / "v7.db"
    conn = connect(old)
    migrate(conn, target=7)
    conn.close()
    code, out = run(old, "setup-code")
    assert code == 1 and out == ""
    assert "Hãy chạy Lyris một lần để cập nhật dữ liệu" in capsys.readouterr().err
    raw = sqlite3.connect(old)
    try:
        assert raw.execute("PRAGMA user_version").fetchone()[0] == 7  # lệnh không tự migrate
    finally:
        raw.close()


async def test_setup_code_takes_effect_while_app_runs(app: FastAPI, settings: Settings, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    code, out = run(settings.db_path, "setup-code")
    assert code == 0 and "Lyris: đặt mật khẩu cho tài khoản chủ máy" in out
    printed = next(line.strip() for line in out.splitlines() if line.startswith("     "))
    assert codes.normalize_code(printed) is not None
    assert printed not in caplog.text
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t", headers={"X-Lyris": "1"}) as c:
        resp = await c.post("/api/auth/setup-owner", json={"setup_code": printed, "password": "đèn lồng đỏ rực"})
        assert resp.status_code == 200, resp.text
    code, _ = run(settings.db_path, "setup-code")
    assert code == 1  # đã có mật khẩu


async def test_reset_password_while_app_runs(app: FastAPI, settings: Settings, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    repo = repo_of(app)
    owner_id = ensure_owner_password(repo)
    member = add_member(repo, "mai")
    with repo.transaction():
        store.record_attempt(repo.conn, "login", handle="ban", ip="10.0.0.1", ok=False, now=clock.now())
    async with client_for(app, owner_id) as owner_tab, client_for(app, member) as member_tab:
        assert (await owner_tab.get("/api/stories")).status_code == 200
        code, out = run(settings.db_path, "reset-password", "@BAN")
        assert code == 0
        temporary = next(line.strip() for line in out.splitlines() if line.startswith("    "))
        assert len(temporary) == 14 and "@ban" in out
        assert temporary not in caplog.text
        # Kết nối của app thấy ngay (không cache): phiên cũ mất, lần sai bị xoá.
        assert (await owner_tab.get("/api/stories")).status_code == 401
        assert (await member_tab.get("/api/stories")).status_code == 200
        with repo.locked() as conn:
            assert conn.execute("SELECT COUNT(*) FROM auth_attempts WHERE handle = 'ban' AND ok = 0").fetchone()[0] == 0
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t", headers={"X-Lyris": "1"}) as c:
        resp = await c.post("/api/auth/login", json={"handle": "ban", "password": temporary})
        assert resp.status_code == 200 and resp.json()["account"]["must_change_password"] is True
        assert (await c.get("/api/stories")).json()["code"] == "password_change_required"
    assert run(settings.db_path, "reset-password", "khong_co")[0] == 1


async def test_enable_and_list(app: FastAPI, settings: Settings) -> None:
    repo = repo_of(app)
    ensure_owner_password(repo)
    member = add_member(repo, "mai")
    with repo.transaction():
        repo.conn.execute("UPDATE accounts SET status = 'disabled' WHERE id = ?", (member,))
    code, out = run(settings.db_path, "list")
    assert code == 0
    lines = out.splitlines()
    assert lines[0].split()[:2] == ["Tài", "khoản"]
    assert "@ban" in lines[1] and "chủ máy" in lines[1] and "đang dùng" in lines[1]
    assert "@mai" in lines[2] and "thành viên" in lines[2] and "tạm khoá" in lines[2]
    assert run(settings.db_path, "enable", "mai") == (0, "Đã mở khoá @mai.\n")
    with repo.locked() as conn:
        assert conn.execute("SELECT status, disabled_at FROM accounts WHERE id = ?", (member,)).fetchone()[:] == ("active", None)
    assert run(settings.db_path, "enable", "mai")[1].startswith("@mai đang dùng bình thường")


def test_shell_script(tmp_path: Path) -> None:
    db = tmp_path / "lyris.db"
    conn = connect(db)
    migrate(conn)
    conn.close()
    env = {**os.environ, "LYRIS_DB_PATH": str(db)}
    result = subprocess.run(["bash", str(SCRIPT), "list"], capture_output=True, text=True, env=env, timeout=60)
    assert result.returncode == 0, result.stderr
    assert "@ban" in result.stdout and "chưa đặt mật khẩu" in result.stdout
    result = subprocess.run(["bash", str(SCRIPT), "setup-code"], capture_output=True, text=True, env=env, timeout=60)
    assert result.returncode == 0 and "Mã dùng một lần" in result.stdout
    bad = subprocess.run(["bash", str(SCRIPT), "lam-gi-do"], capture_output=True, text=True, env=env, timeout=60)
    assert bad.returncode != 0
