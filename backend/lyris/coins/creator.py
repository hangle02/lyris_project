"""Người chơi của nhân vật công khai (F44, docs/coins.md §5.1).

- **Người chơi** của nhân vật công khai X: tài khoản P không phải người tạo X, không phải chủ máy, có story chơi bằng
  bản sao của X, và có ít nhất 3 câu trả lời đã trả coin (giữ chỗ `charged`) cộng dồn trong các story đó, ở ít nhất 2
  ngày coin khác nhau (tạm chọn). `note_charged` kiểm ngay sau mỗi lần trừ coin có `origin_card_id`, cùng transaction,
  và ghi `creator_players (X, P, người tạo X)` một lần.
- F44 làm lại (2026-11-14 22:15, PO 1A): thưởng mốc 10/50/100 người chơi **bị thay hẳn**. `note_charged` chỉ ghi người
  chơi, không trả coin. Thưởng giờ theo bảng xếp hạng "Nhân vật hot" và thưởng công khai lần đầu: `lyris.coins.hot`.
  Dòng sổ `milestone:` cũ và bảng `creator_milestones` giữ nguyên (chỉ đọc).
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any

from lyris.auth import clock as auth_clock
from lyris.coins.ledger import atomic

PLAYER_REPLIES = 3
PLAYER_DAYS = 2


def _now(now: datetime | None) -> datetime:
    return now if now is not None else auth_clock.now()


def _origin(conn: sqlite3.Connection, card_id: int) -> Any:
    """(người tạo, visibility, role, status) của nhân vật gốc `card_id` (không phải bản sao); None nếu không có."""
    return conn.execute(
        "SELECT c.account_id, c.visibility, a.role, a.status FROM character_cards c"
        " LEFT JOIN accounts a ON a.id = c.account_id WHERE c.id = ? AND c.story_copy = 0",
        (card_id,),
    ).fetchone()


def player_count(conn: sqlite3.Connection, card_id: int) -> int:
    row = conn.execute("SELECT COUNT(*) FROM creator_players WHERE card_id = ?", (card_id,)).fetchone()
    return int(row[0])


def qualifies(conn: sqlite3.Connection, card_id: int, player_id: int) -> bool:
    """≥ 3 câu trả lời đã trả coin ở ≥ 2 ngày coin, trong các story CỦA `player_id` chơi bằng bản sao CÒN trỏ về X.

    Đi qua story và bản sao (không chỉ `coin_holds.origin_card_id`): id nhân vật có thể được dùng lại sau khi X bị xoá,
    còn bản sao của X đã xoá có `origin_card_id` NULL, nên giữ chỗ cũ không bao giờ được đếm cho nhân vật mới."""
    row = conn.execute(
        "SELECT COUNT(*), COUNT(DISTINCT h.coin_day) FROM coin_holds h"
        " JOIN stories s ON s.id = h.story_id AND s.account_id = h.account_id"
        " JOIN character_cards c ON c.id = s.card_id AND c.story_copy = 1 AND c.origin_card_id = h.origin_card_id"
        " WHERE h.account_id = ? AND h.origin_card_id = ? AND h.status = 'charged'",
        (player_id, card_id),
    ).fetchone()
    return int(row[0]) >= PLAYER_REPLIES and int(row[1]) >= PLAYER_DAYS


def note_charged(conn: sqlite3.Connection, hold_id: int, now: datetime | None = None) -> list[int]:
    """Sau khi giữ chỗ `hold_id` được trừ: người chơi vừa đủ điều kiện thì ghi `creator_players` một lần.
    Trả [id người chơi vừa được ghi] (hay []). Không bao giờ ghi dòng sổ coin (thưởng: `lyris.coins.hot`)."""
    moment = _now(now)
    with atomic(conn):
        hold = conn.execute(
            "SELECT h.account_id, h.origin_card_id, h.status, a.role FROM coin_holds h"
            " JOIN accounts a ON a.id = h.account_id WHERE h.id = ?",
            (hold_id,),
        ).fetchone()
        if hold is None or hold[1] is None or hold[2] != "charged" or hold[3] != "member":
            return []
        player_id, card_id = int(hold[0]), int(hold[1])
        origin = _origin(conn, card_id)
        if origin is None or origin[0] is None or int(origin[0]) == player_id:
            return []
        known = conn.execute(
            "SELECT 1 FROM creator_players WHERE card_id = ? AND player_id = ?", (card_id, player_id)
        ).fetchone()
        if known is not None or not qualifies(conn, card_id, player_id):
            return []
        conn.execute(
            "INSERT INTO creator_players (card_id, player_id, creator_id, qualified_at) VALUES (?, ?, ?, ?)",
            (card_id, player_id, int(origin[0]), auth_clock.iso(moment)),
        )
        return [player_id]


__all__ = [
    "PLAYER_DAYS",
    "PLAYER_REPLIES",
    "note_charged",
    "player_count",
    "qualifies",
]
