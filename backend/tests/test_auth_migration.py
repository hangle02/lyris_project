"""Phase 4b (docs/auth.md §2.1, §8.1 "Migration"): 0008_auth.sql trên một DB version 7 dựng trong test (không đọc
hay copy data/): giữ mọi dòng cũ, khoá ngoại và toàn vẹn ổn, đúng một chủ máy, persona mặc định chuyển sang cột
của chủ máy, dòng `account_id` NULL về chủ máy, card `unlisted` thành `private`."""
from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

import pytest

from lyris.db.connection import connect, migrate

OLD_TABLES = (
    "accounts", "personas", "character_cards", "stories", "messages", "feedback", "message_edits",
    "state_events", "memories", "jobs", "lore_entries", "lore_hits", "app_settings",
)
NEW_TABLES = ("sessions", "invites", "auth_attempts")


def _counts(conn: sqlite3.Connection, tables: tuple[str, ...]) -> dict[str, int]:
    return {t: int(conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]) for t in tables}


def build_v7(path: Path, *, default_persona: str = "owner") -> dict[str, int]:
    """DB version 7 giống DB thật: chủ máy đã đặt profile, một tài khoản khác, nhiều persona/card/story,
    một card `unlisted`, một persona `account_id` NULL, persona mặc định trong app_settings."""
    conn = connect(path)
    try:
        assert migrate(conn, target=7) == 7
        conn.execute("UPDATE accounts SET handle = 'chu_may', display_name = 'Chủ máy', profile_completed = 1")
        conn.execute("INSERT INTO accounts (uid, handle, display_name) VALUES ('b' || hex(randomblob(15)), 'khach', 'Khách')")
        owner, guest = (int(r[0]) for r in conn.execute("SELECT id FROM accounts ORDER BY id"))
        for name, account in (("Lâm Vãn", owner), ("Gia Huy", owner), ("Người lạ", guest)):
            conn.execute(
                "INSERT INTO personas (name, gender, description, account_id, uid) VALUES (?, 'female', '', ?, hex(randomblob(16)))",
                (name, account),
            )
        conn.execute("INSERT INTO personas (name, gender, description, uid) VALUES ('Mồ côi', 'male', '', hex(randomblob(16)))")
        for name, account, visibility in (
            ("Lạc Dương", owner, "private"), ("Hạ Vy", owner, "unlisted"), ("Morwenna", owner, "public"),
            ("Của khách", guest, "private"), ("Không chủ", None, "private"),
        ):
            conn.execute(
                "INSERT INTO character_cards (name, gender, language, style_profile, address_terms_json, greeting,"
                " account_id, uid, visibility) VALUES (?, 'male', 'vi', 'trung_hien_dai',"
                " '{\"self_term\": \"tớ\", \"player_term\": \"cậu\"}', 'Chào.', ?, hex(randomblob(16)), ?)",
                (name, account, visibility),
            )
        for i, (card, persona, account) in enumerate(((1, 1, owner), (2, 2, owner), (4, 3, guest), (1, 1, None))):
            conn.execute(
                "INSERT INTO stories (card_id, persona_id, title, narration_pronouns_json, account_id, uid)"
                " VALUES (?, ?, ?, '{\"character\": \"anh\", \"player\": \"cô\"}', ?, hex(randomblob(16)))",
                (card, persona, f"Story {i}", account),
            )
        for turn, role in enumerate(("assistant", "user", "assistant")):
            conn.execute(
                "INSERT INTO messages (story_id, turn_index, role, mode, raw_content, visible_content)"
                " VALUES (1, ?, ?, 'story', 'm', 'm')",
                (turn, role),
            )
        conn.execute("INSERT INTO feedback (message_id, rating) VALUES (1, 'up')")
        conn.execute(
            "INSERT INTO lore_entries (card_id, slug, title, content, keys_json, position, created_at, updated_at)"
            " VALUES (1, 'truong', 'Trường', 'Một ngôi trường.', '[\"trường\"]', 0, '2026-01-01', '2026-01-01')"
        )
        persona_id = {"owner": 2, "guest": 3, "orphan": 4}[default_persona]
        conn.execute("INSERT INTO app_settings (key, value_json) VALUES ('default_persona_id', ?)", (str(persona_id),))
        conn.execute("INSERT INTO app_settings (key, value_json) VALUES ('default_chat_model', '\"gemma4:12b\"')")
        conn.execute("INSERT INTO app_settings (key, value_json) VALUES ('seeded', 'true')")
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        return _counts(conn, OLD_TABLES)
    finally:
        conn.close()


@pytest.fixture
def v7_copy(tmp_path: Path) -> tuple[Path, Path, dict[str, int]]:
    original = tmp_path / "v7.db"
    counts = build_v7(original)
    copy = tmp_path / "v7-copy.db"
    shutil.copy(original, copy)
    return original, copy, counts


def test_0008_keeps_rows_and_moves_owner_data(v7_copy: tuple[Path, Path, dict[str, int]]) -> None:
    original, copy, before = v7_copy
    conn = connect(copy)
    try:
        assert migrate(conn) == 14
        after = _counts(conn, OLD_TABLES)
        assert after == {**before, "app_settings": before["app_settings"] - 1}
        assert _counts(conn, NEW_TABLES) == {t: 0 for t in NEW_TABLES}
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"

        accounts = conn.execute(
            "SELECT id, handle, role, status, must_change_password, password_hash, training_opt_in, default_persona_id"
            " FROM accounts ORDER BY id"
        ).fetchall()
        owner, guest = accounts
        assert (owner["handle"], owner["role"], owner["status"], owner["training_opt_in"]) == ("chu_may", "owner", "active", 1)
        assert owner["password_hash"] is None and owner["must_change_password"] == 0
        assert owner["default_persona_id"] == 2  # persona mặc định của máy chuyển sang chủ máy
        assert (guest["role"], guest["training_opt_in"], guest["default_persona_id"]) == ("member", 0, None)
        assert conn.execute("SELECT 1 FROM app_settings WHERE key = 'default_persona_id'").fetchone() is None
        assert conn.execute("SELECT value_json FROM app_settings WHERE key = 'default_chat_model'").fetchone()[0] == '"gemma4:12b"'

        # Lưới an toàn: không còn dòng "không của ai".
        for table in ("personas", "character_cards", "stories"):
            assert conn.execute(f"SELECT COUNT(*) FROM {table} WHERE account_id IS NULL").fetchone()[0] == 0, table
        assert conn.execute("SELECT account_id FROM personas WHERE name = 'Mồ côi'").fetchone()[0] == owner["id"]
        assert conn.execute("SELECT account_id FROM character_cards WHERE name = 'Không chủ'").fetchone()[0] == owner["id"]
        assert conn.execute("SELECT account_id FROM character_cards WHERE name = 'Của khách'").fetchone()[0] == guest["id"]

        visibility = dict(conn.execute("SELECT name, visibility FROM character_cards").fetchall())
        assert visibility["Hạ Vy"] == "private" and visibility["Morwenna"] == "public"
        assert set(visibility.values()) == {"private", "public"}
        copies = conn.execute("SELECT DISTINCT story_copy, origin_card_id, origin_account_id FROM character_cards").fetchall()
        assert [tuple(r) for r in copies] == [(0, None, None)]

        # Đúng một chủ máy.
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("UPDATE accounts SET role = 'owner' WHERE id = ?", (guest["id"],))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO accounts (uid, handle, display_name, role) VALUES ('x', 'chu2', 'Chủ 2', 'owner')")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("UPDATE accounts SET role = 'admin' WHERE id = ?", (guest["id"],))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO invites (code_hash, code_hint, created_by, created_at, expires_at, max_uses) VALUES (x'00', 'AAAA', 1, 'a', 'b', 2)")
        assert migrate(conn) == 14  # chạy lại không làm gì
    finally:
        conn.close()
    # Bản gốc không bị đụng.
    raw = sqlite3.connect(original)
    try:
        assert raw.execute("PRAGMA user_version").fetchone()[0] == 7
    finally:
        raw.close()


@pytest.mark.parametrize("which", ["guest", "orphan"])
def test_default_persona_of_another_account_is_not_moved(tmp_path: Path, which: str) -> None:
    db = tmp_path / "v7.db"
    build_v7(db, default_persona=which)
    conn = connect(db)
    try:
        migrate(conn)
        owner = conn.execute("SELECT default_persona_id FROM accounts WHERE role = 'owner'").fetchone()[0]
        # Persona của khách: không chuyển. Persona mồ côi (account_id NULL) về chủ máy trước, nên được chuyển.
        assert owner == (None if which == "guest" else 4)
        assert conn.execute("SELECT 1 FROM app_settings WHERE key = 'default_persona_id'").fetchone() is None
        assert conn.execute("SELECT default_persona_id FROM accounts WHERE role = 'member'").fetchone()[0] is None
    finally:
        conn.close()


def test_0008_on_fresh_db_makes_default_account_owner() -> None:
    conn = connect(":memory:")
    try:
        assert migrate(conn) == 14
        row = conn.execute("SELECT handle, role, training_opt_in, profile_completed FROM accounts").fetchone()
        assert tuple(row) == ("ban", "owner", 1, 0)
        names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master")}
        assert {"sessions", "invites", "auth_attempts", "idx_accounts_one_owner", "idx_sessions_account",
                "idx_sessions_expires", "idx_auth_attempts_device", "idx_cards_origin", "idx_cards_visibility"} <= names
    finally:
        conn.close()


def test_account_delete_cascades_sessions_and_nulls_invites(tmp_path: Path) -> None:
    conn = connect(tmp_path / "x.db")
    try:
        migrate(conn)
        conn.execute("INSERT INTO accounts (uid, handle, display_name) VALUES ('u2', 'mai', 'Mai')")
        conn.execute("INSERT INTO sessions (account_id, token_hash, created_at, last_seen_at, expires_at) VALUES (2, x'01', 'a', 'a', 'b')")
        conn.execute("INSERT INTO invites (code_hash, code_hint, created_by, created_at, expires_at, used_by, used_at) VALUES (x'02', 'AAAA', 1, 'a', 'b', 2, 'a')")
        conn.execute("DELETE FROM accounts WHERE id = 2")
        assert conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0
        assert conn.execute("SELECT used_by FROM invites").fetchone()[0] is None
    finally:
        conn.close()
