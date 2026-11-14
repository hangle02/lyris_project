"""Phase 4 (docs/phase4.md §1): migration 0007 chỉ thêm cột/bảng; DB version 6 có dữ liệu nâng cấp giữ đủ hàng.

DB version 6 được dựng bằng chính `migrate(conn, target=6)` trong test (không đọc hay copy data/).
"""
from __future__ import annotations

import re
import shutil
import sqlite3
from pathlib import Path

from lyris.db.connection import MIGRATIONS_DIR, connect, migrate
from lyris.db.repo import ANY_ACCOUNT, Repo
from lyris.models import AddressTerms, CharacterCard, LoreEntry, Message, Persona

TABLES = ("character_cards", "personas", "stories", "messages", "accounts")


def build_v6(path: Path) -> dict[str, int]:
    """DB file ở version 6 với card, persona, 2 story (raw SQL: bảng stories v6 chưa có show_thoughts), message."""
    conn = connect(path)
    try:
        assert migrate(conn, target=6) == 6
        repo = Repo(conn)
        card = repo.create_card(
            CharacterCard(
                name="Lạc Dương",
                gender="male",
                style_profile="trung_hien_dai",
                address_terms=AddressTerms(self_term="tớ", player_term="cậu"),
            )
        , account_id=repo.owner_id())
        persona = repo.create_persona(Persona(name="Lâm Vãn", gender="female"), account_id=repo.owner_id())
        account = repo.owner_account()
        for title in ("Story một", "Story hai"):
            conn.execute(
                "INSERT INTO stories (uid, account_id, card_id, persona_id, title, narration_pronouns_json)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (title.encode().hex()[:32].ljust(32, "0"), account.id, card.id, persona.id, title,
                 '{"character": "anh", "player": "cô"}'),
            )
        sid = int(conn.execute("SELECT MIN(id) FROM stories").fetchone()[0])
        # Repo.get_story đọc được hàng KHÔNG có cột show_thoughts (app cũ chưa áp 0007): coi như bật.
        assert repo.get_story(sid, account_id=ANY_ACCOUNT).show_thoughts is True
        for turn, role in enumerate(("assistant", "user", "assistant")):
            repo.insert_message(
                Message(story_id=sid, turn_index=turn, role=role, mode="story", raw_content=f"m{turn}", visible_content=f"m{turn}")  # type: ignore[arg-type]
            )
        return {t: int(conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]) for t in TABLES}
    finally:
        conn.close()


def test_v6_copy_upgrades_and_keeps_every_row(tmp_path: Path) -> None:
    original = tmp_path / "v6.db"
    counts = build_v6(original)
    copy = tmp_path / "v6-copy.db"
    shutil.copy(original, copy)
    conn = connect(copy)
    try:
        assert migrate(conn, target=7) == 7
        assert {t: int(conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]) for t in TABLES} == counts
        assert [r[0] for r in conn.execute("SELECT show_thoughts FROM stories")] == [1, 1]
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master")}
        assert {"lore_entries", "lore_hits", "idx_lore_hits_message", "idx_lore_entries_card"} <= names
        repo = Repo(conn)
        assert all(story.show_thoughts is True for story in repo.list_stories(account_id=ANY_ACCOUNT))
        assert migrate(conn, target=7) == 7  # chạy lại không làm gì
    finally:
        conn.close()
    # Bản gốc không bị đụng.
    conn = sqlite3.connect(original)
    try:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 6
    finally:
        conn.close()


def test_hits_cascade_with_messages_and_entries(tmp_path: Path) -> None:
    path = tmp_path / "db.sqlite"
    build_v6(path)
    conn = connect(path)
    try:
        migrate(conn)
        repo = Repo(conn)
        story = repo.get_story(min(s.id or 0 for s in repo.list_stories(account_id=ANY_ACCOUNT)), account_id=ANY_ACCOUNT)  # story có message
        assert story.id is not None
        msgs = repo.active_messages(story.id)
        assert len(msgs) == 3
        a = repo.insert_lore(LoreEntry(card_id=story.card_id, slug="manual:a", title="A", keys=["aa bb"]))
        b = repo.insert_lore(LoreEntry(card_id=story.card_id, slug="md:lore/b", title="B", source="world_md"))
        assert a.id is not None and b.id is not None and msgs[-1].id is not None
        assert repo.record_lore_hits(story.id, msgs[-1].id, [(a.id, "fresh"), (b.id, "unsent")]) == 2
        assert repo.record_lore_hits(story.id, msgs[-1].id, [(a.id, "fresh")]) == 0  # UNIQUE: không nhân đôi
        assert [r.entry.id for r in repo.unlocked_lore(story.id)] == sorted([a.id, b.id])
        repo.tombstone_lore(b.id)
        assert [r.entry.id for r in repo.unlocked_lore(story.id)] == [a.id]
        assert repo.list_lore(story.card_id) == [repo.get_lore(story.card_id, a.id)]
        repo.truncate_from(story.id, msgs[-1].turn_index)  # xoá message -> hit đi theo
        assert conn.execute("SELECT COUNT(*) FROM lore_hits").fetchone()[0] == 0
        assert repo.record_lore_hits(story.id, msgs[0].id or 0, [(999, "fresh")]) == 0  # mục không còn: bỏ qua
    finally:
        conn.close()


def test_migration_0007_is_additive_only() -> None:
    sql = (MIGRATIONS_DIR / "0007_lore.sql").read_text(encoding="utf-8")
    code = "\n".join(line.split("--")[0] for line in sql.splitlines()).upper()
    assert not re.search(r"\bDROP\b|\bRENAME\b|\bDELETE\b|\bUPDATE\b", code.replace("ON DELETE CASCADE", ""))
    statements = [s.strip() for s in code.split(";") if s.strip()]
    assert all(s.startswith(("ALTER TABLE STORIES ADD COLUMN", "CREATE TABLE", "CREATE INDEX")) for s in statements)
    for needed in ("REMOVED", "UNIQUE (MESSAGE_ID, ENTRY_ID)", "IDX_LORE_HITS_MESSAGE", "UNIQUE (CARD_ID, SLUG)"):
        assert needed in code
