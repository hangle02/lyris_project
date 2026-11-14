"""Đổi tên app Nora -> Lyris: biến môi trường cũ và file DB cũ vẫn dùng được."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from lyris.config import get_settings, migrate_legacy_db


def test_legacy_env_names_still_read(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    for name in ("LYRIS_DB_PATH", "LYRIS_CHAT_MODEL", "NORA_DB_PATH", "NORA_CHAT_MODEL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("NORA_DB_PATH", str(tmp_path / "x.db"))
    monkeypatch.setenv("NORA_CHAT_MODEL", "old-model")
    s = get_settings()
    assert s.db_path == tmp_path / "x.db" and s.chat_model == "old-model"
    monkeypatch.setenv("LYRIS_CHAT_MODEL", "new-model")
    assert get_settings().chat_model == "new-model"


def test_legacy_db_file_is_renamed(tmp_path: Path) -> None:
    old = tmp_path / "nora.db"
    conn = sqlite3.connect(old)
    conn.execute("CREATE TABLE t (x)")
    conn.execute("INSERT INTO t VALUES (1)")
    conn.commit()
    conn.close()
    (tmp_path / "nora.db-wal").write_bytes(b"")
    new = tmp_path / "lyris.db"
    assert migrate_legacy_db(new) is True
    assert new.exists() and not old.exists()
    assert (tmp_path / "lyris.db-wal").exists()
    assert sqlite3.connect(new).execute("SELECT x FROM t").fetchone() == (1,)
    assert migrate_legacy_db(new) is False  # đã có DB mới: không làm gì


def test_no_rename_when_both_exist_or_memory(tmp_path: Path) -> None:
    (tmp_path / "nora.db").write_bytes(b"old")
    (tmp_path / "lyris.db").write_bytes(b"new")
    assert migrate_legacy_db(tmp_path / "lyris.db") is False
    assert (tmp_path / "nora.db").read_bytes() == b"old"
    assert migrate_legacy_db(Path(":memory:")) is False
