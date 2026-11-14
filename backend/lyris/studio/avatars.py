"""Ảnh đại diện (nhân vật, persona, tài khoản) và ảnh bìa tài khoản: chuẩn hoá bằng Pillow, lưu file,
giữ ảnh tạm theo token, dọn file cũ.

Mọi ảnh lưu ra là PNG đã xoay theo EXIF và bỏ hết metadata, thu nhỏ vừa khung (giữ tỉ lệ, không crop):
avatar tối đa 768x768, ảnh bìa tối đa 1500x500.
Tên file: `<loại>-<id>-<8 hex>.png` với loại là `card`, `persona`, `account` (avatar tài khoản) hoặc
`banner` (ảnh bìa tài khoản); phần hex đổi mỗi lần upload để trình duyệt không dùng cache cũ.
Ảnh tạm (từ card PNG import, chưa lưu) nằm ở `<avatars_dir>/tmp/<account>-<token>.png` (Phase 4b,
docs/auth.md §4.6: token gắn với tài khoản đã nhập, tài khoản khác không lấy được).
"""
from __future__ import annotations

import io
import os
import re
import secrets
import time
import warnings
from pathlib import Path
from typing import Literal

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_AVATAR_BYTES = 8 * 1024 * 1024
MAX_SIDE = 768
AVATAR_SIZE: tuple[int, int] = (MAX_SIDE, MAX_SIDE)
BANNER_SIZE: tuple[int, int] = (1500, 500)
# Chặn "bom giải nén": ảnh nhỏ về dung lượng nhưng cực lớn về số điểm ảnh.
MAX_PIXELS = 40_000_000
# MPO: JPEG có segment MPF (ảnh máy ảnh/điện thoại kèm preview lớn hoặc gain map HDR); khung đầu là ảnh chính.
ALLOWED_FORMATS = frozenset({"PNG", "JPEG", "MPO", "WEBP", "GIF"})
TEMP_SUBDIR = "tmp"

ImageKind = Literal["card", "persona", "account", "banner"]
_KINDS: frozenset[str] = frozenset({"card", "persona", "account", "banner"})

_AVATAR_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,120}\.png$")
_TOKEN = re.compile(r"^[0-9a-f]{32}$")
_PART_SUFFIX = ".part"


class AvatarError(ValueError):
    """Ảnh không dùng được (định dạng không hỗ trợ, quá lớn, ảnh hỏng, tên file lạ)."""


def _has_alpha(img: Image.Image) -> bool:
    return img.mode in ("RGBA", "LA", "PA") or (img.mode == "P" and "transparency" in img.info)


def normalize_image(data: bytes, max_size: tuple[int, int] = AVATAR_SIZE) -> bytes:
    """PNG/JPEG/WebP/GIF (khung đầu) -> PNG vừa khung `max_size` (mặc định 768x768, giữ tỉ lệ),
    xoay theo EXIF, không metadata."""
    max_w, max_h = max_size
    if max_w <= 0 or max_h <= 0:
        raise ValueError(f"Khung ảnh không hợp lệ: {max_size!r}")
    if not data:
        raise AvatarError("File ảnh rỗng.")
    if len(data) > MAX_AVATAR_BYTES:
        raise AvatarError("Ảnh quá lớn (tối đa 8MB).")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as img:
                if img.format not in ALLOWED_FORMATS:
                    raise AvatarError("Định dạng ảnh không hỗ trợ. Hãy dùng PNG, JPEG, WebP hoặc GIF.")
                width, height = img.size
                if width <= 0 or height <= 0 or width * height > MAX_PIXELS:
                    raise AvatarError("Kích thước ảnh quá lớn.")
                img.seek(0)  # GIF/WebP động: lấy khung đầu
                img.load()
                oriented = ImageOps.exif_transpose(img)
                converted = oriented.convert("RGBA" if _has_alpha(oriented) else "RGB")
                converted.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
                # Dựng ảnh mới chỉ từ điểm ảnh: không mang theo EXIF, ICC, chú thích hay chunk lạ.
                clean = Image.frombytes(converted.mode, converted.size, converted.tobytes())
    except AvatarError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise AvatarError("Kích thước ảnh quá lớn.") from exc
    except UnidentifiedImageError as exc:
        raise AvatarError("Định dạng ảnh không hỗ trợ. Hãy dùng PNG, JPEG, WebP hoặc GIF.") from exc
    except (OSError, SyntaxError, ValueError, EOFError) as exc:
        raise AvatarError("Ảnh bị hỏng hoặc không đọc được.") from exc
    out = io.BytesIO()
    clean.save(out, format="PNG", optimize=True)
    return out.getvalue()


def _write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + _PART_SUFFIX)
    try:
        part.write_bytes(data)
        os.replace(part, path)
    except BaseException:
        part.unlink(missing_ok=True)
        raise


def _new_name(kind: ImageKind, owner_id: int) -> str:
    if kind not in _KINDS:
        raise AvatarError("Loại ảnh không hợp lệ.")
    if isinstance(owner_id, bool) or not isinstance(owner_id, int) or owner_id < 0:
        raise AvatarError("Mã nhân vật không hợp lệ." if kind == "card" else "Mã không hợp lệ.")
    return f"{kind}-{owner_id}-{secrets.token_hex(4)}.png"


def _new_card_name(card_id: int) -> str:
    return _new_name("card", card_id)


def avatar_path(avatars_dir: Path, name: str) -> Path:
    """Đường dẫn file avatar `name` trong `avatars_dir`; AvatarError nếu tên lạ (chặn path traversal)."""
    if not isinstance(name, str) or not _AVATAR_NAME.fullmatch(name):
        raise AvatarError("Tên file ảnh không hợp lệ.")
    base = Path(avatars_dir).resolve()
    path = (base / name).resolve()
    if path.parent != base:
        raise AvatarError("Tên file ảnh không hợp lệ.")
    return path


def save_image(
    avatars_dir: Path, kind: ImageKind, owner_id: int, data: bytes, *, max_size: tuple[int, int] = AVATAR_SIZE
) -> str:
    """Chuẩn hoá (vừa khung `max_size`) và lưu ảnh `<kind>-<owner_id>-<hex>.png`; trả tên file mới
    (file cũ do caller xoá)."""
    png = normalize_image(data, max_size)
    name = _new_name(kind, owner_id)
    _write_atomic(avatar_path(avatars_dir, name), png)
    return name


def save_card_avatar(avatars_dir: Path, card_id: int, data: bytes) -> str:
    """Chuẩn hoá và lưu ảnh làm avatar của card; trả tên file mới (file cũ do caller xoá)."""
    return save_image(avatars_dir, "card", card_id, data)


def save_persona_avatar(avatars_dir: Path, persona_id: int, data: bytes) -> str:
    """Avatar persona: `persona-<id>-<hex>.png`, tối đa 768x768."""
    return save_image(avatars_dir, "persona", persona_id, data)


def save_account_avatar(avatars_dir: Path, account_id: int, data: bytes) -> str:
    """Avatar tài khoản: `account-<id>-<hex>.png`, tối đa 768x768."""
    return save_image(avatars_dir, "account", account_id, data)


def save_account_banner(avatars_dir: Path, account_id: int, data: bytes) -> str:
    """Ảnh bìa tài khoản: `banner-<id>-<hex>.png`, vừa khung 1500x500 (giữ tỉ lệ)."""
    return save_image(avatars_dir, "banner", account_id, data, max_size=BANNER_SIZE)


def remove_avatar(avatars_dir: Path, name: str | None) -> None:
    """Xoá file avatar; không lỗi nếu không có hoặc tên lạ."""
    if not name:
        return
    try:
        path = avatar_path(avatars_dir, name)
    except AvatarError:
        return
    path.unlink(missing_ok=True)


def _temp_dir(avatars_dir: Path) -> Path:
    return Path(avatars_dir) / TEMP_SUBDIR


def _temp_name(account_id: int, token: str) -> str:
    if isinstance(account_id, bool) or not isinstance(account_id, int) or account_id < 0:
        raise AvatarError("Mã không hợp lệ.")
    return f"{account_id}-{token}.png"


def hold_temp(avatars_dir: Path, data: bytes, account_id: int) -> str:
    """Chuẩn hoá và giữ ảnh tạm của tài khoản `account_id` ở tmp/<account>-<token>.png; trả token (32 hex)."""
    png = normalize_image(data)
    token = secrets.token_hex(16)
    _write_atomic(_temp_dir(avatars_dir) / _temp_name(account_id, token), png)
    return token


def claim_temp(avatars_dir: Path, token: str, card_id: int, account_id: int) -> str | None:
    """Chuyển ảnh tạm của `account_id` thành avatar của card; trả tên file mới. Token lạ/hết hạn/của tài
    khoản khác -> None."""
    if not isinstance(token, str) or not _TOKEN.fullmatch(token):
        return None
    try:
        src = _temp_dir(avatars_dir) / _temp_name(account_id, token)
    except AvatarError:
        return None
    if not src.is_file():
        return None
    name = _new_card_name(card_id)
    dest = avatar_path(avatars_dir, name)
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.replace(src, dest)
    except FileNotFoundError:
        return None  # vừa bị dọn hoặc đã được dùng
    return name


def cleanup_temp(avatars_dir: Path, max_age_s: float = 86400) -> int:
    """Xoá ảnh tạm (và file ghi dở) cũ hơn max_age_s giây; trả số file đã xoá."""
    tmp = _temp_dir(avatars_dir)
    if not tmp.is_dir():
        return 0
    cutoff = time.time() - max_age_s
    removed = 0
    for entry in tmp.iterdir():
        if not entry.is_file() or not (entry.name.endswith(".png") or entry.name.endswith(_PART_SUFFIX)):
            continue
        try:
            if entry.stat().st_mtime <= cutoff:
                entry.unlink()
                removed += 1
        except FileNotFoundError:
            continue
    return removed


__all__ = [
    "ALLOWED_FORMATS",
    "AVATAR_SIZE",
    "BANNER_SIZE",
    "MAX_AVATAR_BYTES",
    "MAX_SIDE",
    "AvatarError",
    "ImageKind",
    "avatar_path",
    "claim_temp",
    "cleanup_temp",
    "hold_temp",
    "normalize_image",
    "remove_avatar",
    "save_account_avatar",
    "save_account_banner",
    "save_card_avatar",
    "save_image",
    "save_persona_avatar",
]
