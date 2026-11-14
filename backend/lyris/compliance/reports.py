"""Báo cáo lời trả lời của AI và nhân vật công khai (bảng `content_reports`, migration 0010 + 0011;
docs/compliance.md §2).

Luật riêng tư: chủ máy rà soát báo cáo nhưng không đọc được story của người khác. Bản chụp câu trả lời
(`message_text`) chỉ được lưu khi người báo cáo tự bật "Gửi kèm câu trả lời này cho chủ máy xem xét"
(`share_text`). Danh sách cho chủ máy không có người báo cáo, không có id story, không có tên nhân vật riêng tư.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from lyris.auth import clock
from lyris.coins.hot import sync_public_since

ReportReason = Literal["sexual", "minor_safety", "violent", "hateful", "self_harm", "harassment", "other"]
ReportStatus = Literal["open", "reviewed", "dismissed"]
ReportTarget = Literal["message", "character"]

NOTE_MAX = 300
# Bản chụp câu trả lời: đủ cho một lượt dài (120-200 từ + Thought), cắt bớt phần thừa.
SNAPSHOT_MAX = 6000

# Lý do của API -> lý do trong số liệu (`content_reported.reason`, lyris.analytics.events.REPORT_REASON).
ANALYTICS_REASON: dict[str, str] = {
    "sexual": "sexual_content",
    "minor_safety": "minor_safety",
    "violent": "violence",
    "hateful": "hate",
    "self_harm": "self_harm",
    "harassment": "harassment",
    "other": "other",
}


@dataclass(frozen=True)
class ReportRow:
    id: int
    created_at: str
    updated_at: str
    reason: str
    note: str
    mode: str | None
    language: str | None
    model_name: str | None
    shared_text: bool
    message_text: str | None
    status: str
    reviewed_at: str | None
    public_card_id: int | None
    public_card_name: str | None
    public_card_creator: str | None
    target: str = "message"


@dataclass(frozen=True)
class NewReport:
    reporter_id: int
    message_id: int
    story_id: int
    public_card_id: int | None
    reason: str
    note: str
    mode: str | None
    language: str | None
    model_name: str | None
    message_text: str | None  # None = không chia sẻ


def upsert(conn: sqlite3.Connection, report: NewReport, now: datetime) -> tuple[int, bool]:
    """Ghi báo cáo; người này đã báo cáo tin này rồi thì cập nhật (lý do, ghi chú, chia sẻ) và mở lại.
    Trả (id, là báo cáo mới)."""
    ts = clock.iso(now)
    shared = 1 if report.message_text is not None else 0
    existing = conn.execute(
        "SELECT id FROM content_reports WHERE reporter_id = ? AND message_id = ?",
        (report.reporter_id, report.message_id),
    ).fetchone()
    if existing is not None:
        report_id = int(existing[0])
        conn.execute(
            "UPDATE content_reports SET reason = ?, note = ?, shared_text = ?, message_text = ?, updated_at = ?,"
            " status = 'open', reviewed_at = NULL WHERE id = ?",
            (report.reason, report.note, shared, report.message_text, ts, report_id),
        )
        return report_id, False
    cur = conn.execute(
        "INSERT INTO content_reports (created_at, updated_at, reporter_id, message_id, story_id, public_card_id,"
        " reason, note, mode, language, model_name, shared_text, message_text)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            ts, ts, report.reporter_id, report.message_id, report.story_id, report.public_card_id, report.reason,
            report.note, report.mode, report.language, report.model_name, shared, report.message_text,
        ),
    )
    assert cur.lastrowid is not None
    return int(cur.lastrowid), True


def upsert_card(
    conn: sqlite3.Connection, *, reporter_id: int, card_id: int, reason: str, note: str, language: str | None,
    now: datetime,
) -> tuple[int, bool]:
    """Báo cáo một nhân vật công khai (`target = 'character'`); người này đã báo cáo nhân vật này rồi thì cập nhật lý
    do, ghi chú và mở lại. Trả (id, là báo cáo mới)."""
    ts = clock.iso(now)
    existing = conn.execute(
        "SELECT id FROM content_reports WHERE target = 'character' AND reporter_id = ? AND public_card_id = ?",
        (reporter_id, card_id),
    ).fetchone()
    if existing is not None:
        report_id = int(existing[0])
        conn.execute(
            "UPDATE content_reports SET reason = ?, note = ?, updated_at = ?, status = 'open', reviewed_at = NULL"
            " WHERE id = ?",
            (reason, note, ts, report_id),
        )
        return report_id, False
    cur = conn.execute(
        "INSERT INTO content_reports (created_at, updated_at, reporter_id, public_card_id, reason, note, language,"
        " target) VALUES (?, ?, ?, ?, ?, ?, ?, 'character')",
        (ts, ts, reporter_id, card_id, reason, note, language),
    )
    assert cur.lastrowid is not None
    return int(cur.lastrowid), True


def unpublish_card(conn: sqlite3.Connection, card_id: int, now: datetime) -> bool:
    """Người quản lý ẩn một nhân vật công khai bị báo cáo (chuyển về Riêng tư; người tạo vẫn giữ nhân vật).
    Trả False nếu không có nhân vật công khai nào như vậy."""
    cur = conn.execute(
        "UPDATE character_cards SET visibility = 'private', updated_at = ?"
        " WHERE id = ? AND visibility = 'public' AND story_copy = 0",
        (clock.iso(now), card_id),
    )
    # F44 (docs/coins.md §5.5): về Riêng tư thì xoá lúc bật Công khai (công khai lại thì đếm 24 giờ lại).
    sync_public_since(conn, card_id, now)
    return cur.rowcount == 1


_SELECT = (
    "SELECT r.id, r.created_at, r.updated_at, r.reason, r.note, r.mode, r.language, r.model_name, r.shared_text,"
    " r.message_text, r.status, r.reviewed_at, r.public_card_id, c.name AS card_name, a.handle AS creator,"
    " r.target"
    " FROM content_reports r"
    # Tên nhân vật chỉ hiện khi nó vẫn đang công khai (người tạo chuyển về Riêng tư thì chỉ còn id).
    " LEFT JOIN character_cards c ON c.id = r.public_card_id AND c.visibility = 'public' AND c.story_copy = 0"
    " LEFT JOIN accounts a ON a.id = c.account_id"
)


def _row(r: sqlite3.Row) -> ReportRow:
    return ReportRow(
        id=int(r["id"]),
        created_at=r["created_at"],
        updated_at=r["updated_at"],
        reason=r["reason"],
        note=r["note"],
        mode=r["mode"],
        language=r["language"],
        model_name=r["model_name"],
        shared_text=bool(r["shared_text"]),
        message_text=r["message_text"],
        status=r["status"],
        reviewed_at=r["reviewed_at"],
        public_card_id=r["public_card_id"],
        public_card_name=r["card_name"],
        public_card_creator=r["creator"],
        target=r["target"],
    )


def list_reports(conn: sqlite3.Connection, *, status: ReportStatus | None = None, limit: int = 200) -> list[ReportRow]:
    """Mới nhất trước. `status` None = mọi trạng thái."""
    where = " WHERE r.status = ?" if status is not None else ""
    params: tuple[object, ...] = (status,) if status is not None else ()
    rows = conn.execute(_SELECT + where + " ORDER BY r.created_at DESC, r.id DESC LIMIT ?", (*params, int(limit)))
    return [_row(r) for r in rows.fetchall()]


def get_report(conn: sqlite3.Connection, report_id: int) -> ReportRow | None:
    row = conn.execute(_SELECT + " WHERE r.id = ?", (report_id,)).fetchone()
    return None if row is None else _row(row)


def set_status(conn: sqlite3.Connection, report_id: int, status: ReportStatus, now: datetime) -> bool:
    cur = conn.execute(
        "UPDATE content_reports SET status = ?, reviewed_at = ? WHERE id = ?",
        (status, None if status == "open" else clock.iso(now), report_id),
    )
    return cur.rowcount == 1


def reports_by(conn: sqlite3.Connection, account_id: int) -> list[dict[str, object]]:
    """Báo cáo của chính tài khoản (cho bản xuất dữ liệu cá nhân)."""
    rows = conn.execute(
        "SELECT id, created_at, target, message_id, story_id, public_card_id, reason, note, shared_text, message_text,"
        " status FROM content_reports WHERE reporter_id = ? ORDER BY id",
        (account_id,),
    ).fetchall()
    return [
        {
            "id": int(r["id"]),
            "created_at": r["created_at"],
            "target": r["target"],
            "message_id": r["message_id"],
            "story_id": r["story_id"],
            "card_id": r["public_card_id"] if r["target"] == "character" else None,
            "reason": r["reason"],
            "note": r["note"],
            "shared_text": bool(r["shared_text"]),
            "message_text": r["message_text"],
            "status": r["status"],
        }
        for r in rows
    ]


def scrub_reporter(conn: sqlite3.Connection, account_id: int) -> int:
    """Xoá tài khoản: bỏ ghi chú và bản chụp câu trả lời của mọi báo cáo người này gửi, tách khỏi tài khoản.
    Chỉ còn lý do, thời điểm, chế độ (để đếm). Trả số báo cáo đã làm ẩn danh."""
    cur = conn.execute(
        "UPDATE content_reports SET note = '', message_text = NULL, shared_text = 0, reporter_id = NULL,"
        " message_id = NULL, story_id = NULL WHERE reporter_id = ?",
        (account_id,),
    )
    return cur.rowcount


__all__ = [
    "ANALYTICS_REASON",
    "NOTE_MAX",
    "SNAPSHOT_MAX",
    "NewReport",
    "ReportReason",
    "ReportRow",
    "ReportStatus",
    "ReportTarget",
    "get_report",
    "list_reports",
    "reports_by",
    "scrub_reporter",
    "set_status",
    "unpublish_card",
    "upsert",
    "upsert_card",
]
