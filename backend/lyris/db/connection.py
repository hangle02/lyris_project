"""Mở kết nối SQLite và áp dụng migration theo PRAGMA user_version."""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

MIGRATIONS_DIR: Path = Path(__file__).resolve().parent / "migrations"
_MIGRATION_NAME = re.compile(r"^(\d{4})_[A-Za-z0-9_\-]+\.sql$")


def connect(path: Path | str) -> sqlite3.Connection:
    """Mở kết nối dùng chung giữa các thread.

    Kết nối ở chế độ autocommit (isolation_level=None): Repo tự mở transaction tường minh
    cho các thao tác nhiều câu lệnh. ":memory:" được phép; thư mục cha được tạo nếu chưa có.
    """
    target = str(path)
    if target != ":memory:" and not target.startswith("file:"):
        Path(target).expanduser().parent.mkdir(parents=True, exist_ok=True)
        target = str(Path(target).expanduser())
    conn = sqlite3.connect(
        target,
        check_same_thread=False,
        isolation_level=None,
        uri=target.startswith("file:"),
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def _migration_files() -> list[tuple[int, Path]]:
    found: dict[int, Path] = {}
    for file in sorted(MIGRATIONS_DIR.glob("*.sql")):
        match = _MIGRATION_NAME.match(file.name)
        if match is None:
            continue
        version = int(match.group(1))
        if version in found:
            raise RuntimeError(
                f"Trùng số migration {version:04d}: {found[version].name} và {file.name}"
            )
        found[version] = file
    return sorted(found.items())


def migrate(conn: sqlite3.Connection, target: int | None = None) -> int:
    """Áp dụng các file migrations/NNNN_*.sql có số > PRAGMA user_version (và <= `target` nếu có;
    `target` chỉ dùng để dựng DB cũ trong test).

    Mỗi file chạy trong một transaction `BEGIN IMMEDIATE` riêng (kèm cập nhật user_version), nên lỗi giữa
    chừng không để lại schema dở dang. `user_version` được đọc lại SAU khi đã giữ khoá ghi: hai tiến trình
    khởi động cùng lúc trên một DB cũ thì tiến trình sau thấy file đã được áp dụng và bỏ qua, không chạy lại
    (trước đây nó chạy lại `ALTER TABLE ... ADD COLUMN` và chết vì "duplicate column"). Trả về version sau
    khi áp dụng.
    """
    current = int(conn.execute("PRAGMA user_version").fetchone()[0])
    for version, file in _migration_files():
        if version <= current:
            continue
        if target is not None and version > target:
            break
        sql = file.read_text(encoding="utf-8")
        current = _apply(conn, version, sql)
    return current


def _apply(conn: sqlite3.Connection, version: int, sql: str) -> int:
    """Chạy một file migration nếu DB chưa có nó. Trả user_version sau đó."""
    # Chế độ autocommit của sqlite3: executescript() không tự COMMIT transaction đang mở, nên khoá ghi giữ
    # nguyên từ lúc đọc version tới lúc COMMIT. Trả lại chế độ cũ khi xong.
    previous = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            applied = int(conn.execute("PRAGMA user_version").fetchone()[0])
            if applied >= version:  # tiến trình khác vừa áp dụng xong
                conn.execute("COMMIT")
                return applied
            conn.executescript(f"{sql}\n;\nPRAGMA user_version = {version};\n")
            conn.execute("COMMIT")
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
    finally:
        conn.autocommit = previous
    return version
