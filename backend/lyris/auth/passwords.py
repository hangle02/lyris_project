"""Mật khẩu (docs/auth.md §3.1): luật, chuẩn hoá NFC, băm scrypt, so sánh an toàn thời gian.

Không bao giờ băm khi đang giữ khoá của `Repo` hay đang mở transaction: đọc dòng tài khoản -> nhả khoá ->
băm/so sánh (`hash_password`, `verify_password`, chạy trong thread, tối đa 2 lần cùng lúc) -> mới mở
transaction để ghi.

Hàng chờ băm nằm trong event loop, không nằm trong thread pool chung: lần băm thứ 3 trở đi chờ một
`anyio.CapacityLimiter(2)` riêng rồi mới lấy thread, nên login dồn dập không giữ thread của anyio (40 thread
mà FastAPI dùng cho mọi route/dependency `def` đồng bộ). Quá `MAX_PENDING_HASHES` lần đang chạy + đang chờ
thì từ chối ngay (`HashingBusy`), không xếp hàng thêm.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import os
import threading
import unicodedata
import weakref
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TypeVar

import anyio
import anyio.to_thread

from lyris.accounts import AccountInputError

MIN_LENGTH = 8
MAX_LENGTH = 128

# Mức tối thiểu OWASP cho scrypt. 128 MiB RAM mỗi lần băm; đo 0,27 giây trên M2 Pro (2026-11-14).
SCRYPT_N = 2**17
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_MAXMEM = 256 * 1024 * 1024
SALT_BYTES = 16
DKLEN = 32
MAX_PARALLEL_HASHES = 2
# Đang chạy + đang chờ. Mỗi lần băm ~0,27 giây, 2 lần song song: lần thứ 16 chờ khoảng 2 giây.
MAX_PENDING_HASHES = 16

COMMON_PASSWORDS_FILE = Path(__file__).resolve().parent / "common_passwords.txt"

TOO_SHORT = "Mật khẩu cần ít nhất 8 ký tự."
TOO_LONG = "Mật khẩu dài tối đa 128 ký tự."
TOO_COMMON = "Mật khẩu này quá dễ đoán. Hãy chọn mật khẩu khác."
SAME_AS_HANDLE = "Mật khẩu không được giống tên đăng nhập."
SAME_AS_OLD = "Mật khẩu mới phải khác mật khẩu cũ."

# Cho lời gọi đồng bộ (lệnh trên Mac, script). Đường async đã giới hạn bằng `_limiter()` trước khi vào thread.
_slots = threading.BoundedSemaphore(MAX_PARALLEL_HASHES)
# Một limiter cho mỗi event loop (test mở nhiều loop; primitive của anyio gắn với loop tạo ra nó).
_limiters: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, anyio.CapacityLimiter] = weakref.WeakKeyDictionary()
_pending = 0

T = TypeVar("T")


class HashingBusy(Exception):
    """Đã có `MAX_PENDING_HASHES` lần băm đang chạy hoặc đang chờ: từ chối thay vì xếp hàng thêm."""


class PasswordRuleError(AccountInputError):
    """Mật khẩu sai luật (422); thông điệp là câu tiếng Việt, không chứa mật khẩu."""


@dataclass(frozen=True)
class PasswordHash:
    salt: bytes
    digest: bytes
    n: int
    r: int
    p: int

    def current_params(self) -> bool:
        """Băm bằng tham số hiện hành (không thì băm lại sau lần đăng nhập đúng)."""
        return (self.n, self.r, self.p) == (SCRYPT_N, SCRYPT_R, SCRYPT_P)


def normalize(password: str) -> str:
    """NFC: bàn phím iPhone và Mac có thể sinh hai dạng Unicode khác nhau cho cùng một chữ có dấu."""
    return unicodedata.normalize("NFC", password)


@lru_cache(maxsize=1)
def common_passwords() -> frozenset[str]:
    lines = COMMON_PASSWORDS_FILE.read_text(encoding="utf-8").splitlines()
    return frozenset(normalize(line.strip()).casefold() for line in lines if line.strip() and not line.startswith("#"))


def check_rules(password: str, *, handle: str | None, current: str | None = None) -> str:
    """Mật khẩu đã chuẩn hoá NFC nếu đúng luật; sai -> PasswordRuleError. Không cắt khoảng trắng."""
    value = normalize(password)
    if len(value) < MIN_LENGTH:
        raise PasswordRuleError(TOO_SHORT)
    if len(value) > MAX_LENGTH:
        raise PasswordRuleError(TOO_LONG)
    folded = value.casefold()
    if handle and folded in (handle.casefold(), "@" + handle.casefold()):
        raise PasswordRuleError(SAME_AS_HANDLE)
    if folded in common_passwords():
        raise PasswordRuleError(TOO_COMMON)
    if current is not None and normalize(current) == value:
        raise PasswordRuleError(SAME_AS_OLD)
    return value


def _scrypt(password: bytes, salt: bytes, n: int, r: int, p: int) -> bytes:
    """Một lần scrypt (test đếm số lần gọi bằng monkeypatch)."""
    with _slots:
        return hashlib.scrypt(password, salt=salt, n=n, r=r, p=p, maxmem=SCRYPT_MAXMEM, dklen=DKLEN)


def hash_password_sync(password: str, *, n: int | None = None, r: int | None = None, p: int | None = None) -> PasswordHash:
    params = (n or SCRYPT_N, r or SCRYPT_R, p or SCRYPT_P)
    salt = os.urandom(SALT_BYTES)
    digest = _scrypt(normalize(password).encode("utf-8"), salt, *params)
    return PasswordHash(salt=salt, digest=digest, n=params[0], r=params[1], p=params[2])


def verify_password_sync(password: str, stored: PasswordHash | None) -> bool:
    """So với hash đã lưu. `stored` None (handle không có, chưa đặt mật khẩu) vẫn chạy một lần scrypt với
    salt giả, để thời gian trả lời không cho biết handle có hay không."""
    target = stored or _DUMMY
    digest = _scrypt(normalize(password).encode("utf-8"), target.salt, target.n, target.r, target.p)
    return stored is not None and hmac.compare_digest(digest, stored.digest)


def _limiter() -> anyio.CapacityLimiter:
    loop = asyncio.get_running_loop()
    limiter = _limiters.get(loop)
    if limiter is None:
        limiter = anyio.CapacityLimiter(MAX_PARALLEL_HASHES)
        _limiters[loop] = limiter
    return limiter


def pending_hashes() -> int:
    return _pending


async def _in_thread(fn: Callable[[], T], *, admit: bool) -> T:
    """Chạy `fn` trong thread, tối đa 2 cùng lúc; chờ chỗ ngay trong event loop (không giữ thread nào).

    `admit`: hàng đầy (`MAX_PENDING_HASHES`) thì `HashingBusy` ngay, trước khi chờ. False cho lần băm thứ hai
    của một request đã được nhận (mật khẩu mới sau khi mật khẩu cũ đúng): không bỏ dở việc đã làm.
    """
    global _pending
    if admit and _pending >= MAX_PENDING_HASHES:
        raise HashingBusy
    _pending += 1
    try:
        return await anyio.to_thread.run_sync(fn, limiter=_limiter())
    finally:
        _pending -= 1


async def hash_password(password: str, *, admit: bool = True) -> PasswordHash:
    return await _in_thread(lambda: hash_password_sync(password), admit=admit)


async def verify_password(password: str, stored: PasswordHash | None) -> bool:
    return await _in_thread(lambda: verify_password_sync(password, stored), admit=True)


_DUMMY = PasswordHash(salt=os.urandom(SALT_BYTES), digest=bytes(DKLEN), n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P)


__all__ = [
    "MAX_LENGTH",
    "MAX_PENDING_HASHES",
    "MIN_LENGTH",
    "SCRYPT_N",
    "SCRYPT_P",
    "SCRYPT_R",
    "HashingBusy",
    "PasswordHash",
    "PasswordRuleError",
    "check_rules",
    "common_passwords",
    "hash_password",
    "hash_password_sync",
    "normalize",
    "pending_hashes",
    "verify_password",
    "verify_password_sync",
]
