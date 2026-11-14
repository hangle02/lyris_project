"""Tự phục vụ dữ liệu cá nhân (docs/compliance.md §4): xoá tài khoản và xuất dữ liệu.

`delete_account` xoá trong MỘT transaction mọi thứ thuộc tài khoản:
- story (tin nhắn, biến thể, đánh giá, lịch sử sửa, state, ký ức, job, lore đã mở đi theo ON DELETE CASCADE);
- nhân vật của tài khoản, kể cả nhân vật công khai và bản sao (story_copy) mà tài khoản đang dùng, kèm sổ thế giới;
- persona, phiên đăng nhập, lần thử đăng nhập (theo @handle và theo khoá tài khoản), mã mời đã tạo (chủ máy);
- báo cáo đã gửi: bỏ ghi chú và bản chụp câu trả lời, chỉ còn lý do (ẩn danh);
- sự kiện sử dụng: tách khỏi tài khoản (`account_id` -> NULL), sự kiện chưa gửi PostHog thì không gửi nữa.
File ảnh (avatar tài khoản, ảnh bìa, avatar persona, avatar nhân vật) được trả về để caller xoá SAU khi commit.

Bản sao nhân vật công khai của tài khoản này mà người KHÁC đã dùng để bắt đầu story vẫn ở lại trong story của
họ (đó là dữ liệu của họ), chỉ không còn ghi người tạo (`origin_account_id` -> NULL).

`export_account` trả một dict JSON được: hồ sơ, cài đặt, persona, nhân vật (kèm sổ thế giới), nhân vật đang chơi
bằng bản sao (chỉ phần công khai, như giao diện cho xem), story kèm toàn bộ tin nhắn và ký ức, báo cáo đã gửi,
thiết bị đăng nhập và sự kiện sử dụng. Ảnh chỉ ghi tên file. Không có hash mật khẩu, token, prompt snapshot.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from typing import Any

from lyris.analytics import store as analytics_store
from lyris.auth import clock
from lyris.auth import store as auth_store
from lyris.compliance import legal, reports
from lyris.db.repo import NotFound, Repo, _row_to_card, _row_to_lore

EXPORT_FORMAT = "lyris-account-export"
EXPORT_VERSION = 1

# Trường hồ sơ nhân vật mà người chơi bằng bản sao được thấy (giống PublicCardView, docs/auth.md §4.4).
_COPY_FIELDS = (
    "name", "role", "gender", "language", "description", "appearance", "scenario", "greeting",
    "alternate_greetings", "tags", "style_profile", "speech_style",
)


class OwnerHasMembers(Exception):
    """Chủ máy còn thành viên khác: không xoá được tài khoản chủ máy."""


@dataclass
class Deleted:
    account_id: int
    handle: str
    was_owner: bool
    story_ids: list[int] = field(default_factory=list)
    files: list[str] = field(default_factory=list)  # tên file ảnh còn mồ côi, caller xoá sau commit
    counts: dict[str, int] = field(default_factory=dict)


def other_accounts(conn: sqlite3.Connection, account_id: int) -> int:
    row = conn.execute("SELECT COUNT(*) FROM accounts WHERE id != ?", (account_id,)).fetchone()
    return int(row[0])


def _ids(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...]) -> list[int]:
    return [int(r[0]) for r in conn.execute(sql, params).fetchall()]


def _files_of(conn: sqlite3.Connection, account_id: int) -> list[str]:
    names: list[str] = []
    row = conn.execute("SELECT avatar, banner FROM accounts WHERE id = ?", (account_id,)).fetchone()
    if row is not None:
        names += [str(v) for v in (row[0], row[1]) if v]
    for table in ("personas", "character_cards"):
        names += [
            str(r[0])
            for r in conn.execute(f"SELECT avatar FROM {table} WHERE account_id = ? AND avatar IS NOT NULL", (account_id,))
        ]
    return list(dict.fromkeys(names))


def _still_used(conn: sqlite3.Connection, name: str) -> bool:
    for sql in (
        "SELECT 1 FROM accounts WHERE avatar = ? OR banner = ?",
        "SELECT 1 FROM personas WHERE avatar = ? OR avatar = ?",
        "SELECT 1 FROM character_cards WHERE avatar = ? OR avatar = ?",
    ):
        if conn.execute(sql, (name, name)).fetchone() is not None:
            return True
    return False


def delete_account(
    repo: Repo, account_id: int, *, password_digest: bytes | None = None, device_anon: str | None = None
) -> Deleted:
    """Xoá tài khoản và mọi dữ liệu của nó (một transaction). `device_anon`: anon_id của thiết bị đang xoá (sự kiện
    lúc chưa đăng nhập trên thiết bị đó cũng được tách). `password_digest`: hash mật khẩu vừa so khớp;
    mật khẩu vừa bị đổi trong lúc so thì không xoá (PermissionError). Chủ máy còn tài khoản khác -> OwnerHasMembers.
    NotFound nếu không có tài khoản."""
    with repo.transaction():
        conn = repo.conn
        account = auth_store.account_by_id(conn, account_id)
        if account is None:
            raise NotFound("Không tìm thấy tài khoản.")
        if password_digest is not None and not auth_store.password_current(conn, account_id, password_digest):
            raise PermissionError("password changed")
        was_owner = account.role == "owner"
        if was_owner and other_accounts(conn, account_id):
            raise OwnerHasMembers()
        out = Deleted(account_id=account_id, handle=account.handle, was_owner=was_owner)
        files = _files_of(conn, account_id)
        out.story_ids = _ids(conn, "SELECT id FROM stories WHERE account_id = ?", (account_id,))
        counts: dict[str, int] = {}
        counts["reports"] = reports.scrub_reporter(conn, account_id)
        conn.execute("UPDATE accounts SET default_persona_id = NULL WHERE id = ?", (account_id,))
        counts["stories"] = conn.execute("DELETE FROM stories WHERE account_id = ?", (account_id,)).rowcount
        counts["cards"] = conn.execute("DELETE FROM character_cards WHERE account_id = ?", (account_id,)).rowcount
        counts["personas"] = conn.execute("DELETE FROM personas WHERE account_id = ?", (account_id,)).rowcount
        counts["sessions"] = auth_store.delete_sessions(conn, account_id)
        counts["auth_attempts"] = conn.execute(
            "DELETE FROM auth_attempts WHERE handle = ? OR handle = ?",
            (account.handle, auth_store.account_key(account_id)),
        ).rowcount
        counts["invites"] = conn.execute("DELETE FROM invites WHERE created_by = ?", (account_id,)).rowcount
        counts["events"] = analytics_store.anonymise_account(conn, account_id, device_anon=device_anon)
        conn.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
        out.files = [n for n in files if not _still_used(conn, n)]
        out.counts = counts
    return out


# ---------------------------------------------------------------------------- xuất dữ liệu


def _card_json(card_row: sqlite3.Row) -> dict[str, Any]:
    card = _row_to_card(card_row)
    data = card.model_dump(mode="json")
    data["avatar_file"] = data.pop("avatar", None)
    data["created_at"] = card_row["created_at"]
    data["updated_at"] = card_row["updated_at"]
    return data


def _copy_json(conn: sqlite3.Connection, card_row: sqlite3.Row) -> dict[str, Any]:
    card = _row_to_card(card_row).model_dump(mode="json")
    out: dict[str, Any] = {"id": card_row["id"], **{k: card.get(k) for k in _COPY_FIELDS}}
    out["avatar_file"] = card_row["avatar"]
    origin = card_row["origin_account_id"]
    creator = None
    if origin is not None:
        row = conn.execute("SELECT handle FROM accounts WHERE id = ?", (origin,)).fetchone()
        creator = None if row is None else row[0]
    out["creator_handle"] = creator
    out["copied_at"] = card_row["created_at"]
    return out


def _messages(conn: sqlite3.Connection, story_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT m.id, m.turn_index, m.variant_index, m.is_active, m.role, m.mode, m.raw_content, m.visible_content,"
        " m.thought, m.directive, m.model_name, m.created_at, m.edited_at, f.rating, f.note"
        " FROM messages m LEFT JOIN feedback f ON f.message_id = m.id"
        " WHERE m.story_id = ? ORDER BY m.turn_index, m.variant_index",
        (story_id,),
    ).fetchall()
    return [
        {
            "id": r["id"],
            "turn_index": r["turn_index"],
            "variant_index": r["variant_index"],
            "is_active": bool(r["is_active"]),
            "role": r["role"],
            "mode": r["mode"],
            "content": r["visible_content"],
            "raw_content": r["raw_content"],
            "thought": r["thought"],
            "directive": r["directive"],
            "model_name": r["model_name"],
            "created_at": r["created_at"],
            "edited_at": r["edited_at"],
            "rating": r["rating"],
            "feedback_note": r["note"] or "",
        }
        for r in rows
    ]


def _memories(conn: sqlite3.Connection, story_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT id, turn_index, kind, subject, text, importance, created_at FROM memories"
        " WHERE story_id = ? ORDER BY turn_index, id",
        (story_id,),
    ).fetchall()
    return [{k: r[k] for k in r.keys()} for r in rows]


def _story_json(conn: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    story_id = int(row["id"])
    keys = row.keys()
    pronouns: Any
    try:
        pronouns = json.loads(row["narration_pronouns_json"])
    except (TypeError, json.JSONDecodeError):
        pronouns = None
    return {
        "id": story_id,
        "uid": row["uid"],
        "title": row["title"],
        "card_id": row["card_id"],
        "persona_id": row["persona_id"],
        "scenario": row["scenario"],
        "language": row["language"],
        "mode": row["mode"],
        "relationship_type": row["relationship_type"],
        "pov": row["pov"],
        "thought_style": row["thought_style"],
        "narration_pronouns": pronouns,
        "show_thoughts": bool(row["show_thoughts"]) if "show_thoughts" in keys else True,
        "scene_summary": row["scene_summary"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "messages": _messages(conn, story_id),
        "memories": _memories(conn, story_id),
    }


def _account_json(conn: sqlite3.Connection, account_id: int) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
    if row is None:
        raise NotFound("Không tìm thấy tài khoản.")
    keys = row.keys()

    def opt(key: str) -> Any:
        return row[key] if key in keys else None

    return {
        "uid": row["uid"],
        "handle": row["handle"],
        "display_name": row["display_name"],
        "bio": row["bio"],
        "role": opt("role"),
        "created_at": row["created_at"],
        "last_login_at": opt("last_login_at"),
        "password_changed_at": opt("password_changed_at"),
        "avatar_file": row["avatar"],
        "banner_file": row["banner"],
        "default_persona_id": opt("default_persona_id"),
        "training_opt_in": bool(opt("training_opt_in") or 0),
        "analytics_opt_out": bool(opt("analytics_opt_out") or 0),
        "terms_accepted_at": opt("terms_accepted_at"),
        "privacy_version": opt("privacy_version"),
    }


def export_account(repo: Repo, account_id: int) -> dict[str, Any]:
    """Mọi dữ liệu của tài khoản dưới dạng dict JSON được (đọc trong một lần giữ khoá)."""
    with repo.locked() as conn:
        account = _account_json(conn, account_id)
        personas = [
            {
                "id": r["id"], "uid": r["uid"], "name": r["name"], "gender": r["gender"],
                "description": r["description"], "avatar_file": r["avatar"],
                "created_at": r["created_at"], "updated_at": r["updated_at"],
            }
            for r in conn.execute("SELECT * FROM personas WHERE account_id = ? ORDER BY id", (account_id,))
        ]
        characters: list[dict[str, Any]] = []
        copies: list[dict[str, Any]] = []
        for r in conn.execute("SELECT * FROM character_cards WHERE account_id = ? ORDER BY id", (account_id,)).fetchall():
            if "story_copy" in r.keys() and r["story_copy"]:
                copies.append(_copy_json(conn, r))
                continue
            card = _card_json(r)
            lore_rows = conn.execute(
                "SELECT * FROM lore_entries WHERE card_id = ? AND removed = 0 ORDER BY position, id", (r["id"],)
            ).fetchall()
            card["lore"] = [_row_to_lore(x).model_dump(mode="json") for x in lore_rows]
            characters.append(card)
        stories = [
            _story_json(conn, r)
            for r in conn.execute("SELECT * FROM stories WHERE account_id = ? ORDER BY id", (account_id,)).fetchall()
        ]
        sessions = [
            {"device": r["device_label"], "ip": r["ip"], "created_at": r["created_at"], "last_seen_at": r["last_seen_at"]}
            for r in conn.execute(
                "SELECT device_label, ip, created_at, last_seen_at FROM sessions WHERE account_id = ? ORDER BY id",
                (account_id,),
            )
        ]
        own_reports = reports.reports_by(conn, account_id)
        events = analytics_store.events_of(conn, account_id)
    return {
        "format": EXPORT_FORMAT,
        "version": EXPORT_VERSION,
        "exported_at": clock.iso(clock.now()),
        "legal_version": legal.LEGAL_VERSION,
        "account": account,
        "personas": personas,
        "characters": characters,
        "story_characters": copies,
        "stories": stories,
        "reports": own_reports,
        "sessions": sessions,
        "usage_events": events,
    }


__all__ = [
    "EXPORT_FORMAT",
    "EXPORT_VERSION",
    "Deleted",
    "OwnerHasMembers",
    "delete_account",
    "export_account",
    "other_accounts",
]
