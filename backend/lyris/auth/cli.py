"""Lệnh trên Mac cho chủ máy (docs/auth.md §2.4). Gọi qua `scripts/lyris-admin.sh`:

    bash scripts/lyris-admin.sh setup-code              # in mã thiết lập mới (khi chủ máy chưa có mật khẩu)
    bash scripts/lyris-admin.sh reset-password <handle> # đặt mật khẩu tạm, in ra, buộc đổi, xoá mọi phiên
    bash scripts/lyris-admin.sh enable <handle>         # mở khoá tài khoản
    bash scripts/lyris-admin.sh list                    # handle, vai trò, trạng thái, lần đăng nhập cuối

Mở thẳng DB (`LYRIS_DB_PATH`, mặc định data/lyris.db; SQLite WAL nên chạy được khi app đang chạy) và từ chối
DB chưa ở version 8. Ai chạy được lệnh này đã giữ máy và file DB, nên không hỏi mật khẩu. Không ghi gì vào
log: mã thiết lập và mật khẩu tạm chỉ in ra cửa sổ Terminal này.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import TextIO

from lyris.accounts import normalize_handle
from lyris.auth import clock, codes, passwords, setup, store
from lyris.config import get_settings
from lyris.db.connection import connect

AUTH_VERSION = 8


class CliError(Exception):
    """Lỗi in ra cho người dùng (câu tiếng Việt), mã thoát 1."""


def open_db(path: Path) -> sqlite3.Connection:
    target = str(path)
    if target != ":memory:" and not target.startswith("file:") and not path.is_file():
        raise CliError(f"Không thấy dữ liệu Lyris ở {path}. Hãy chạy Lyris một lần để tạo dữ liệu.")
    conn = connect(path)
    if store.schema_version(conn) < AUTH_VERSION:
        conn.close()
        raise CliError("Dữ liệu chưa được cập nhật. Hãy chạy Lyris một lần để cập nhật dữ liệu.")
    return conn


@contextmanager
def write(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


def _account(conn: sqlite3.Connection, raw: str) -> store.AuthRow:
    row = store.account_by_handle(conn, normalize_handle(raw))
    if row is None:
        raise CliError(f"Không có tài khoản @{normalize_handle(raw)}. Xem danh sách: bash scripts/lyris-admin.sh list")
    return row


def cmd_setup_code(conn: sqlite3.Connection, out: TextIO) -> None:
    if not store.owner_needs_setup(conn):
        raise CliError(
            "Chủ máy đã có mật khẩu. Quên mật khẩu thì chạy: bash scripts/lyris-admin.sh reset-password <handle>"
        )
    with write(conn):
        code = setup.write_new_code(conn, clock.now())
    print(setup.banner(code), file=out, flush=True)


def cmd_reset_password(conn: sqlite3.Connection, handle: str, out: TextIO) -> None:
    target = _account(conn, handle)
    temporary = codes.temporary_password()
    hashed = passwords.hash_password_sync(temporary)  # băm trước, rồi mới mở transaction
    with write(conn):
        store.write_password(conn, target.id, hashed, clock.now(), temporary=True)
        store.delete_sessions(conn, target.id)
        store.clear_failures(conn, target.handle, target.id)
    print(f"Mật khẩu tạm cho @{target.handle}:", file=out)
    print("", file=out)
    print(f"    {temporary}", file=out)
    print("", file=out)
    print("Dùng được 3 ngày. Đăng nhập xong sẽ phải đặt mật khẩu mới ngay.", file=out)
    print("Mọi thiết bị đang đăng nhập tài khoản này đã bị đăng xuất.", file=out, flush=True)


def cmd_enable(conn: sqlite3.Connection, handle: str, out: TextIO) -> None:
    target = _account(conn, handle)
    if target.status == "active":
        print(f"@{target.handle} đang dùng bình thường, không cần mở khoá.", file=out, flush=True)
        return
    with write(conn):
        store.set_status(conn, target.id, "active", clock.now())
    print(f"Đã mở khoá @{target.handle}.", file=out, flush=True)


def _state(row: store.AdminRow) -> str:
    if not row.has_password:
        return "chưa đặt mật khẩu"
    if row.status == "disabled":
        return "tạm khoá" + (", chờ đổi mật khẩu" if row.must_change_password else "")
    return "chờ đổi mật khẩu" if row.must_change_password else "đang dùng"


def cmd_list(conn: sqlite3.Connection, out: TextIO) -> None:
    rows = store.admin_accounts(conn, clock.now())
    table = [("Tài khoản", "Vai trò", "Trạng thái", "Lần đăng nhập cuối")]
    for r in rows:
        last = r.last_login_at[:16].replace("T", " ") + " UTC" if r.last_login_at else "chưa"
        table.append((f"@{r.handle}", "chủ máy" if r.role == "owner" else "thành viên", _state(r), last))
    widths = [max(len(line[i]) for line in table) for i in range(4)]
    for line in table:
        print("  ".join(cell.ljust(widths[i]) for i, cell in enumerate(line)).rstrip(), file=out)
    out.flush()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lyris-admin.sh", description="Lệnh quản lý tài khoản Lyris trên Mac.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("setup-code", help="in mã thiết lập mới (khi chủ máy chưa có mật khẩu)")
    reset = sub.add_parser("reset-password", help="đặt mật khẩu tạm, buộc đổi, đăng xuất mọi thiết bị")
    reset.add_argument("handle")
    enable = sub.add_parser("enable", help="mở khoá tài khoản")
    enable.add_argument("handle")
    sub.add_parser("list", help="danh sách tài khoản")
    return parser


def main(argv: Sequence[str] | None = None, *, db_path: Path | None = None, out: TextIO | None = None) -> int:
    stream = out or sys.stdout
    args = build_parser().parse_args(argv)
    path = db_path or get_settings().db_path
    try:
        conn = open_db(path)
    except CliError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    try:
        if args.command == "setup-code":
            cmd_setup_code(conn, stream)
        elif args.command == "reset-password":
            cmd_reset_password(conn, args.handle, stream)
        elif args.command == "enable":
            cmd_enable(conn, args.handle, stream)
        else:
            cmd_list(conn, stream)
    except CliError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
