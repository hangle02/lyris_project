"""Mã mời, mã thiết lập chủ máy, mật khẩu tạm (docs/auth.md §1.3, §2.4, §6.3).

- Mã 12 ký tự Crockford base32 (bỏ I, L, O, U): 60 bit từ `secrets`.
- Khi nhập: bỏ khoảng trắng và gạch, bỏ tiền tố `LYR`, viết hoa, đổi `O→0`, `I/L→1`.
- DB chỉ lưu `sha256` của mã đã chuẩn hoá. Mã không bao giờ vào log.

Bảng ca thử chuẩn hoá dùng chung với frontend: `frontend/src/lib/inviteCode.cases.json`.
"""
from __future__ import annotations

import hashlib
import re
import secrets

CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
CODE_LENGTH = 12
INVITE_PREFIX = "LYR"
_SEPARATORS = re.compile(r"[\s\-‐-―−]+")
_CONFUSABLE = str.maketrans({"O": "0", "I": "1", "L": "1"})

# Mật khẩu tạm: chữ thường không dễ nhầm (bỏ 0/o, 1/l/i), 12 ký tự nhóm 4 (khoảng 59 bit).
TEMP_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"


def random_code() -> str:
    """12 ký tự Crockford base32 ngẫu nhiên (60 bit), chưa có gạch."""
    return "".join(secrets.choice(CROCKFORD) for _ in range(CODE_LENGTH))


def group(code: str) -> str:
    """`7KQ2M9XD4TPA` -> `7KQ2-M9XD-4TPA`."""
    return "-".join(code[i : i + 4] for i in range(0, len(code), 4))


def format_invite(code: str) -> str:
    """Dạng hiện cho người dùng: `LYR-7KQ2-M9XD-4TPA`."""
    return f"{INVITE_PREFIX}-{group(code)}"


def normalize_code(raw: str | None) -> str | None:
    """Mã đã chuẩn hoá (12 ký tự Crockford, chữ hoa), hoặc None nếu sai dạng.

    Dùng cho cả mã mời (có hay không có `LYR-`) và mã thiết lập. Tiền tố bỏ TRƯỚC khi đổi `L→1`
    (mã thật không bao giờ bắt đầu bằng `L`, vì `L` không có trong bảng chữ).
    """
    if not raw or len(raw) > 100:
        return None
    text = _SEPARATORS.sub("", raw).upper()
    if text.startswith(INVITE_PREFIX) and len(text) == CODE_LENGTH + len(INVITE_PREFIX):
        text = text[len(INVITE_PREFIX) :]
    text = text.translate(_CONFUSABLE)
    if len(text) != CODE_LENGTH or any(c not in CROCKFORD for c in text):
        return None
    return text


def code_hash(normalized: str) -> bytes:
    """sha256 của mã đã chuẩn hoá (32 byte), để tìm qua index."""
    return hashlib.sha256(normalized.encode("ascii")).digest()


def code_hint(normalized: str) -> str:
    """4 ký tự cuối, để chủ máy nhận ra mã."""
    return normalized[-4:]


def temporary_password() -> str:
    """Mật khẩu tạm dạng `xxxx-xxxx-xxxx`."""
    raw = "".join(secrets.choice(TEMP_ALPHABET) for _ in range(CODE_LENGTH))
    return group(raw)


__all__ = [
    "CODE_LENGTH",
    "CROCKFORD",
    "TEMP_ALPHABET",
    "code_hash",
    "code_hint",
    "format_invite",
    "group",
    "normalize_code",
    "random_code",
    "temporary_password",
]
