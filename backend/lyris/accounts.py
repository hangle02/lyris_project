"""Luật của tài khoản (docs/accounts.md §2): @handle, tên hiển thị, giới thiệu.

Hàm thuần, không đụng DB: kiểm tra trùng handle là việc của Repo (`handle_taken`, `HandleTaken`).
Thông điệp lỗi là câu tiếng Việt hoàn chỉnh để hiện thẳng cho người dùng.
"""
from __future__ import annotations

import re

from lyris.models import AccountUpdate

HANDLE_MIN = 3
HANDLE_MAX = 30
DISPLAY_NAME_MAX = 60
BIO_MAX = 500

_HANDLE_CHARS = re.compile(r"^[a-z0-9_.]+$")


class AccountInputError(ValueError):
    """Dữ liệu tài khoản sai luật; thông điệp tiếng Việt cho người dùng."""


def normalize_handle(raw: str) -> str:
    """Bỏ khoảng trắng hai đầu, bỏ một dấu `@` ở đầu nếu có, chuyển về chữ thường."""
    text = raw.strip()
    if text.startswith("@"):
        text = text[1:]
    return text.lower()


def validate_handle(raw: str) -> str:
    """Handle đã chuẩn hoá nếu đúng luật: 3-30 ký tự a-z 0-9 _ . , không bắt đầu hay kết thúc bằng
    dấu chấm. Sai luật -> AccountInputError. Không kiểm tra trùng."""
    handle = normalize_handle(raw)
    if not handle:
        raise AccountInputError("Handle không được để trống.")
    if len(handle) < HANDLE_MIN:
        raise AccountInputError(f"Handle phải có ít nhất {HANDLE_MIN} ký tự.")
    if len(handle) > HANDLE_MAX:
        raise AccountInputError(f"Handle dài tối đa {HANDLE_MAX} ký tự.")
    if not _HANDLE_CHARS.fullmatch(handle):
        raise AccountInputError(
            "Handle chỉ được dùng chữ cái a-z không dấu, chữ số, dấu gạch dưới (_) và dấu chấm (.)."
        )
    if handle.startswith(".") or handle.endswith("."):
        raise AccountInputError("Handle không được bắt đầu hay kết thúc bằng dấu chấm.")
    return handle


def validate_display_name(raw: str) -> str:
    name = " ".join(raw.split())
    if not name:
        raise AccountInputError("Tên hiển thị không được để trống.")
    if len(name) > DISPLAY_NAME_MAX:
        raise AccountInputError(f"Tên hiển thị dài tối đa {DISPLAY_NAME_MAX} ký tự.")
    return name


def validate_bio(raw: str) -> str:
    bio = raw.strip()
    if len(bio) > BIO_MAX:
        raise AccountInputError(f"Phần giới thiệu dài tối đa {BIO_MAX} ký tự.")
    return bio


def validate_account_update(display_name: str, handle: str, bio: str) -> AccountUpdate:
    """Kiểm tra và chuẩn hoá cả ba trường; lỗi đầu tiên -> AccountInputError."""
    return AccountUpdate(
        display_name=validate_display_name(display_name),
        handle=validate_handle(handle),
        bio=validate_bio(bio),
    )


__all__ = [
    "BIO_MAX",
    "DISPLAY_NAME_MAX",
    "HANDLE_MAX",
    "HANDLE_MIN",
    "AccountInputError",
    "normalize_handle",
    "validate_account_update",
    "validate_bio",
    "validate_display_name",
    "validate_handle",
]
