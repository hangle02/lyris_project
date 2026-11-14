"""Mã thiết lập chủ máy (docs/auth.md §2.4).

Mỗi lần backend khởi động mà chủ máy chưa có mật khẩu: sinh mã 12 ký tự (60 bit), lưu sha256 + hạn 24 giờ
vào `app_settings.owner_setup` (ghi đè mã cũ), in ra stderr bằng `print` (không qua `logging`, để mã không
vào file log nào). Lệnh trên Mac `setup-code` dùng cùng hàm.
"""
from __future__ import annotations

import hashlib
import hmac
import sqlite3
import sys
from datetime import datetime
from typing import TextIO

from lyris.auth import clock, codes, store

RULE = "─" * 56


def write_new_code(conn: sqlite3.Connection, now: datetime) -> str:
    """Sinh mã mới, ghi hash + hạn (trong transaction của caller). Trả mã dạng `7KQ2-M9XD-4TPA`."""
    code = codes.random_code()
    store.write_setup(conn, hashlib.sha256(code.encode("ascii")).hexdigest(), now + store.SETUP_CODE_TTL)
    return codes.group(code)


def banner(code: str) -> str:
    return "\n".join(
        [
            RULE,
            " Lyris: đặt mật khẩu cho tài khoản chủ máy",
            " Mở http://localhost:5173 trên Mac này và nhập mã thiết lập:",
            "",
            f"     {code}",
            "",
            " Mã dùng một lần. Mỗi lần Lyris khởi động lại sẽ có mã mới.",
            RULE,
        ]
    )


def check_code(conn: sqlite3.Connection, raw: str, now: datetime) -> bool:
    """Mã nhập vào khớp mã đang dùng và chưa hết hạn (so sánh hash bằng `compare_digest`)."""
    saved = store.read_setup(conn)
    normalized = codes.normalize_code(raw)
    if saved is None or normalized is None:
        return False
    hash_hex, expires_at = saved
    try:
        if clock.parse(expires_at) <= now:
            return False
    except ValueError:
        return False
    given = hashlib.sha256(normalized.encode("ascii")).hexdigest()
    return hmac.compare_digest(given, hash_hex)


def print_banner(code: str, stream: TextIO | None = None) -> None:
    print("\n" + banner(code) + "\n", file=stream or sys.stderr, flush=True)


__all__ = ["banner", "check_code", "print_banner", "write_new_code"]
