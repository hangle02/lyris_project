"""Điều khoản và Chính sách quyền riêng tư (docs/legal/, docs/compliance.md §3).

- Văn bản nằm ở `docs/legal/{terms,privacy}.md` (một nguồn duy nhất). Backend phục vụ chúng ở
  `GET /api/legal/{doc}` (mở, không cần đăng nhập: trang tạo tài khoản và màn thiết lập chủ máy cần đọc được).
- `LEGAL_VERSION`: phiên bản chung của bộ văn bản. Đổi nội dung đáng kể thì tăng số này: mọi tài khoản đã đồng ý
  bản cũ sẽ được hỏi lại một lần (`terms_required`). Test kiểm cả hai file đều ghi đúng phiên bản này.
- Đồng ý được lưu ở `accounts.terms_accepted_at` + `accounts.privacy_version` (migration 0010).
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Literal

from lyris.auth import clock
from lyris.config import REPO_ROOT

LEGAL_VERSION = "2026-11-16"  # F42: thêm mục Coin (docs/coins.md §12)
LEGAL_DIR: Path = REPO_ROOT / "docs" / "legal"

LegalDoc = Literal["terms", "privacy"]
LEGAL_DOCS: tuple[LegalDoc, ...] = ("terms", "privacy")

TERMS_REQUIRED = (
    "Bạn cần đồng ý với Điều khoản sử dụng và Chính sách quyền riêng tư để tiếp tục."
)
TERMS_OUTDATED = "Điều khoản vừa được cập nhật. Hãy tải lại trang để đọc bản mới."


@dataclass(frozen=True)
class LegalText:
    doc: LegalDoc
    version: str
    markdown: str


@lru_cache(maxsize=4)
def _read(path: Path, mtime_ns: int) -> str:
    del mtime_ns  # chỉ để cache mất hiệu lực khi file đổi
    return path.read_text(encoding="utf-8")


def load(doc: LegalDoc, directory: Path | None = None) -> LegalText:
    """Văn bản `doc`. FileNotFoundError nếu thiếu file (route trả 404)."""
    path = (directory or LEGAL_DIR) / f"{doc}.md"
    text = _read(path, path.stat().st_mtime_ns)
    return LegalText(doc=doc, version=LEGAL_VERSION, markdown=text)


CONTACT_PLACEHOLDER = "[ĐIỀN EMAIL LIÊN HỆ]"
# Ghi chú cạnh chỗ trống (chỉ có nghĩa khi chưa điền): bỏ đi khi đã có liên hệ.
_PLACEHOLDER_NOTES = (
    " *(nhóm phát triển sẽ điền trước khi ra mắt)*",
    " *(contact email, to be filled in by the team before launch)*",
)


def with_contact(markdown: str, contact: str | None) -> str:
    """Văn bản với liên hệ của người vận hành (LYRIS_CONTACT) thay cho `[ĐIỀN EMAIL LIÊN HỆ]`; chưa đặt thì giữ nguyên."""
    if not contact:
        return markdown
    out = markdown
    for note in _PLACEHOLDER_NOTES:
        out = out.replace(CONTACT_PLACEHOLDER + "**" + note, CONTACT_PLACEHOLDER + "**")
    return out.replace(CONTACT_PLACEHOLDER, contact)


def _has_columns(conn: sqlite3.Connection) -> bool:
    return any(r[1] == "terms_accepted_at" for r in conn.execute("PRAGMA table_info(accounts)"))


def accepted_version(conn: sqlite3.Connection, account_id: int) -> tuple[str | None, str | None]:
    """(terms_accepted_at, privacy_version) của tài khoản; DB trước 0010 thì (None, None)."""
    if not _has_columns(conn):
        return None, None
    row = conn.execute(
        "SELECT terms_accepted_at, privacy_version FROM accounts WHERE id = ?", (account_id,)
    ).fetchone()
    if row is None:
        return None, None
    return row[0], row[1]


def terms_required(conn: sqlite3.Connection, account_id: int) -> bool:
    """Tài khoản chưa đồng ý bản hiện tại (chưa bao giờ đồng ý, hoặc đồng ý bản cũ) -> giao diện hỏi một lần."""
    accepted_at, version = accepted_version(conn, account_id)
    return accepted_at is None or version != LEGAL_VERSION


def accept(conn: sqlite3.Connection, account_id: int, now: datetime, version: str = LEGAL_VERSION) -> None:
    """Ghi lần đồng ý (gọi trong transaction của caller)."""
    conn.execute(
        "UPDATE accounts SET terms_accepted_at = ?, privacy_version = ? WHERE id = ?",
        (clock.iso(now), version, account_id),
    )


__all__ = [
    "LEGAL_DIR",
    "LEGAL_DOCS",
    "LEGAL_VERSION",
    "TERMS_OUTDATED",
    "TERMS_REQUIRED",
    "LegalDoc",
    "LegalText",
    "accept",
    "accepted_version",
    "load",
    "terms_required",
]
