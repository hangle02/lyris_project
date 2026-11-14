from __future__ import annotations

import importlib
import re
import sqlite3
import threading
from pathlib import Path

import pytest

from lyris.config import REPO_ROOT, Settings, get_settings
from lyris.db.connection import connect, migrate
from lyris.db.repo import ANY_ACCOUNT, InUse, NotFound, Repo
from lyris.models import (
    AddressTerms,
    CharacterCard,
    GenStats,
    Message,
    NarrationPronouns,
    Persona,
    Story,
)
from lyris.seed import create_default_story, ensure_seed, load_seed_card


# ---------------------------------------------------------------- helpers


def make_card(**overrides: object) -> CharacterCard:
    data: dict[str, object] = {
        "name": "Thẩm Dịch",
        "gender": "male",
        "description": "Nam, 22 tuổi",
        "personality": "Trầm tĩnh",
        "style_profile": "trung_hien_dai",
        "address_terms": AddressTerms(self_term="tớ", player_term="cậu", nicknames=["Tiểu Ngư"], others="xưng tôi"),
        "greeting": "Xin chào. [Thought: Lại là cô ấy.]",
        "tags": ["vườn trường", "ngôn tình"],
    }
    data.update(overrides)
    return CharacterCard.model_validate(data)


def make_story(repo: Repo, **overrides: object) -> Story:
    card = repo.create_card(make_card(), account_id=repo.owner_id())
    persona = repo.create_persona(Persona(name="Tô Ngư", gender="female", description="Nữ, 20 tuổi"), account_id=repo.owner_id())
    assert card.id is not None and persona.id is not None
    data: dict[str, object] = {
        "card_id": card.id,
        "persona_id": persona.id,
        "title": "Thử",
        "narration_pronouns": NarrationPronouns(character="anh", player="cô"),
    }
    data.update(overrides)
    return repo.create_story(Story.model_validate(data), account_id=repo.owner_id())


def user_msg(story_id: int, turn: int, text: str = "Chào cậu") -> Message:
    return Message(
        story_id=story_id, turn_index=turn, role="user", mode="story", raw_content=text, visible_content=text
    )


def ai_msg(story_id: int, turn: int, text: str = "Anh gật đầu.", thought: str | None = "Ừ.") -> Message:
    raw = text if thought is None else f"{text}\n[Thought: {thought}]"
    return Message(
        story_id=story_id,
        turn_index=turn,
        role="assistant",
        mode="story",
        raw_content=raw,
        visible_content=text,
        thought=thought,
        model_output=raw,
        prompt_snapshot={"messages": [{"role": "system", "content": "Luật"}], "dropped_turns": 0},
        model_name="gemma4:12b",
        gen_stats=GenStats(ttft_ms=120.5, total_ms=3000.0, prompt_tokens=900, output_tokens=200, tok_per_s=18.2),
    )


def active_count(repo: Repo, story_id: int, turn: int) -> int:
    row = repo.conn.execute(
        "SELECT COUNT(*) FROM messages WHERE story_id = ? AND turn_index = ? AND is_active = 1",
        (story_id, turn),
    ).fetchone()
    return int(row[0])


# ---------------------------------------------------------------- config


def test_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("LYRIS_DB_PATH", "OLLAMA_URL", "LYRIS_CHAT_MODEL", "LYRIS_NUM_CTX", "LYRIS_AVATARS_DIR", "LYRIS_DRAFT_MODEL"):
        monkeypatch.delenv(name, raising=False)
    s = get_settings()
    assert s == Settings(
        db_path=REPO_ROOT / "data" / "lyris.db",
        ollama_url="http://127.0.0.1:11434",
        chat_model="gemma4:12b",
        num_ctx=8192,
    )
    assert s.avatars_dir == REPO_ROOT / "data" / "avatars"
    assert s.draft_model == "gemma4:12b"
    assert (REPO_ROOT / "backend" / "lyris" / "config.py").is_file()


def test_settings_phase2_fields(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    for name in ("LYRIS_AVATARS_DIR", "LYRIS_DRAFT_MODEL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LYRIS_DB_PATH", str(tmp_path / "db" / "x.db"))
    monkeypatch.setenv("LYRIS_CHAT_MODEL", "gemma4:e4b")
    s = get_settings()
    assert s.avatars_dir == tmp_path / "db" / "avatars"
    assert s.draft_model == "gemma4:e4b"  # mặc định theo chat_model

    monkeypatch.setenv("LYRIS_DB_PATH", ":memory:")
    assert get_settings().avatars_dir == REPO_ROOT / "data" / "avatars"

    monkeypatch.setenv("LYRIS_AVATARS_DIR", str(tmp_path / "anh"))
    monkeypatch.setenv("LYRIS_DRAFT_MODEL", "gemma4:12b")
    s = get_settings()
    assert s.avatars_dir == tmp_path / "anh"
    assert s.draft_model == "gemma4:12b"

    # Tạo Settings bằng tay (như test cũ) vẫn chạy nhờ giá trị mặc định.
    manual = Settings(db_path=Path(":memory:"), ollama_url="http://x", chat_model="m", num_ctx=1024)
    assert manual.avatars_dir == REPO_ROOT / "data" / "avatars"
    assert manual.draft_model == "gemma4:12b"


def test_settings_from_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LYRIS_DB_PATH", str(tmp_path / "x.db"))
    monkeypatch.setenv("OLLAMA_URL", "http://localhost:9999/")
    monkeypatch.setenv("LYRIS_CHAT_MODEL", "gemma4:e4b")
    monkeypatch.setenv("LYRIS_NUM_CTX", "4096")
    s = get_settings()
    assert s.db_path == tmp_path / "x.db"
    assert s.ollama_url == "http://localhost:9999"
    assert s.chat_model == "gemma4:e4b"
    assert s.num_ctx == 4096
    monkeypatch.setenv("LYRIS_NUM_CTX", "nhiều")
    with pytest.raises(ValueError):
        get_settings()


# ---------------------------------------------------------------- connection / migrations

LATEST = 14  # số migration mới nhất trong lyris/db/migrations (0012: coin, F42; 0013: sổ coin chặn DELETE; 0014: bảng Nhân vật hot, F46)


def test_v1_database_upgrades_with_default_thought_style(tmp_path: Path) -> None:
    """DB tạo từ Phase 1 (chỉ có 0001) nâng cấp được, story cũ nhận thought_style mặc định."""
    from lyris.db.connection import MIGRATIONS_DIR

    db = tmp_path / "old.db"
    conn = connect(db)
    conn.executescript((MIGRATIONS_DIR / "0001_init.sql").read_text(encoding="utf-8"))
    conn.execute("PRAGMA user_version = 1")
    conn.execute(
        "INSERT INTO character_cards (name, gender, style_profile, address_terms_json) VALUES ('A', 'male', 's', '{}')"
    )
    conn.execute("INSERT INTO personas (name, gender) VALUES ('B', 'female')")
    conn.execute(
        "INSERT INTO stories (card_id, persona_id, title, narration_pronouns_json) VALUES (1, 1, 't', '{}')"
    )
    conn.commit()
    assert migrate(conn) == LATEST
    assert conn.execute("SELECT thought_style FROM stories").fetchone()[0] == "inline"
    conn.close()


def test_migrations_idempotent() -> None:
    conn = connect(":memory:")
    assert migrate(conn) == LATEST
    assert migrate(conn) == LATEST
    assert conn.execute("PRAGMA user_version").fetchone()[0] == LATEST
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert {"character_cards", "personas", "stories", "messages", "feedback", "message_edits"} <= tables
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    conn.close()


def test_connect_file_creates_parent_and_uses_wal(tmp_path: Path) -> None:
    db = tmp_path / "nested" / "dir" / "lyris.db"
    conn = connect(db)
    assert db.parent.is_dir()
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert migrate(conn) == LATEST
    conn.close()
    conn2 = connect(db)
    assert migrate(conn2) == LATEST
    conn2.close()


# ---------------------------------------------------------------- cards / personas / stories


def test_card_round_trip(repo: Repo) -> None:
    card = make_card()
    created = repo.create_card(card, account_id=repo.owner_id())
    assert created.id is not None
    assert created.model_dump(exclude={"id", "uid"}) == card.model_dump(exclude={"id", "uid"})
    assert created.uid is not None and re.fullmatch(r"[0-9a-f]{32}", created.uid)
    assert repo.get_card(created.id, account_id=ANY_ACCOUNT) == created
    assert repo.list_cards(account_id=ANY_ACCOUNT) == [created]
    with pytest.raises(NotFound):
        repo.get_card(9999, account_id=ANY_ACCOUNT)


def test_persona_round_trip(repo: Repo) -> None:
    p = repo.create_persona(Persona(name="Lâm Vãn", gender="female", description="lạc quan"), account_id=repo.owner_id())
    assert p.id is not None
    assert repo.get_persona(p.id, account_id=ANY_ACCOUNT) == p
    assert repo.list_personas(account_id=ANY_ACCOUNT) == [p]
    with pytest.raises(NotFound):
        repo.get_persona(42, account_id=ANY_ACCOUNT)


def test_story_round_trip_and_update(repo: Repo) -> None:
    story = make_story(repo, scenario="Vườn trường", relationship_type="bl", pov="first")
    assert story.id is not None and story.created_at
    got = repo.get_story(story.id, account_id=ANY_ACCOUNT)
    assert got == story
    assert got.narration_pronouns == NarrationPronouns(character="anh", player="cô")

    updated = repo.update_story(
        story.id,
        mode="dm",
        title="Mới",
        scene_summary="Hai người ở thư viện.",
        narration_pronouns={"character": "hắn", "player": "nàng"}, account_id=ANY_ACCOUNT
    )
    assert updated.mode == "dm" and updated.title == "Mới"
    assert updated.scene_summary == "Hai người ở thư viện."
    assert updated.narration_pronouns == NarrationPronouns(character="hắn", player="nàng")
    assert repo.get_story(story.id, account_id=ANY_ACCOUNT) == updated
    assert repo.update_story(story.id, account_id=ANY_ACCOUNT) == updated

    with pytest.raises(ValueError):
        repo.update_story(story.id, card_id=5, account_id=ANY_ACCOUNT)
    with pytest.raises(ValueError):
        repo.update_story(story.id, mode="voice", account_id=ANY_ACCOUNT)
    assert repo.get_story(story.id, account_id=ANY_ACCOUNT).mode == "dm"
    with pytest.raises(NotFound):
        repo.update_story(999, title="x", account_id=ANY_ACCOUNT)
    with pytest.raises(NotFound):
        repo.get_story(999, account_id=ANY_ACCOUNT)


def test_create_story_requires_card_and_persona(repo: Repo) -> None:
    with pytest.raises(NotFound):
        repo.create_story(
            Story(card_id=1, persona_id=1, title="x", narration_pronouns=NarrationPronouns(character="anh", player="cô"))
        , account_id=repo.owner_id())


def test_list_stories_newest_first(repo: Repo) -> None:
    first = make_story(repo, title="Một")
    second = repo.create_story(first.model_copy(update={"id": None, "title": "Hai"}), account_id=repo.owner_id())
    third = repo.create_story(first.model_copy(update={"id": None, "title": "Ba"}), account_id=repo.owner_id())
    assert [s.id for s in repo.list_stories(account_id=ANY_ACCOUNT)] == [third.id, second.id, first.id]


# ---------------------------------------------------------------- messages


def test_insert_message_round_trip(repo: Repo) -> None:
    story = make_story(repo)
    assert story.id is not None
    assert repo.last_turn_index(story.id) is None
    assert repo.next_turn_index(story.id) == 0

    u = repo.insert_message(user_msg(story.id, 0, "Chào ((nhẹ nhàng))").model_copy(update={"directive": "nhẹ nhàng"}))
    a = repo.insert_message(ai_msg(story.id, 1))
    assert u.variant_index == 0 and u.is_active and u.variant_count == 1 and u.rating is None
    assert u.directive == "nhẹ nhàng"
    assert a.prompt_snapshot == {"messages": [{"role": "system", "content": "Luật"}], "dropped_turns": 0}
    assert a.gen_stats == GenStats(ttft_ms=120.5, total_ms=3000.0, prompt_tokens=900, output_tokens=200, tok_per_s=18.2)
    assert a.model_output == a.raw_content and a.model_name == "gemma4:12b"
    assert a.created_at and a.edited_at is None
    assert repo.get_message(a.id or 0, account_id=ANY_ACCOUNT) == a
    assert repo.last_turn_index(story.id) == 1
    assert repo.next_turn_index(story.id) == 2

    with pytest.raises(ValueError):
        repo.insert_message(user_msg(story.id, 1))
    with pytest.raises(NotFound):
        repo.insert_message(user_msg(999, 0))
    with pytest.raises(NotFound):
        repo.get_message(12345, account_id=ANY_ACCOUNT)
    with pytest.raises(NotFound):
        repo.active_messages(999)
    with pytest.raises(NotFound):
        repo.last_turn_index(999)


def test_add_variant_and_select_variant(repo: Repo) -> None:
    story = make_story(repo)
    sid = story.id or 0
    repo.insert_message(user_msg(sid, 0))
    v0 = repo.insert_message(ai_msg(sid, 1, "Bản một."))

    v1 = repo.add_variant(ai_msg(sid, 1, "Bản hai."))
    assert v1.variant_index == 1 and v1.is_active and v1.variant_count == 2
    assert active_count(repo, sid, 1) == 1
    assert repo.get_message(v0.id or 0, account_id=ANY_ACCOUNT).is_active is False

    v2 = repo.add_variant(ai_msg(sid, 1, "Bản ba."))
    assert v2.variant_index == 2 and v2.variant_count == 3
    assert active_count(repo, sid, 1) == 1
    assert [m.variant_index for m in repo.list_variants(sid, 1)] == [0, 1, 2]

    chosen = repo.select_variant(sid, 1, 0)
    assert chosen.id == v0.id and chosen.is_active and chosen.variant_count == 3
    assert active_count(repo, sid, 1) == 1
    assert repo.active_messages(sid)[-1].id == v0.id

    # Chọn lại variant đang active không lỗi.
    assert repo.select_variant(sid, 1, 0).id == v0.id
    assert active_count(repo, sid, 1) == 1

    with pytest.raises(NotFound):
        repo.select_variant(sid, 1, 7)
    with pytest.raises(NotFound):
        repo.add_variant(ai_msg(sid, 5))
    with pytest.raises(ValueError):
        repo.add_variant(user_msg(sid, 0))
    with pytest.raises(ValueError):
        # Lượt 0 là của người chơi: không thêm variant assistant vào đó.
        repo.add_variant(ai_msg(sid, 0))
    assert active_count(repo, sid, 0) == 1
    assert active_count(repo, sid, 1) == 1
    assert len(repo.list_variants(sid, 1)) == 3


def test_one_active_index_enforced(repo: Repo) -> None:
    story = make_story(repo)
    sid = story.id or 0
    repo.insert_message(ai_msg(sid, 0))
    with pytest.raises(sqlite3.IntegrityError):
        repo.conn.execute(
            "INSERT INTO messages (story_id, turn_index, variant_index, is_active, role, mode, raw_content,"
            " visible_content) VALUES (?, 0, 1, 1, 'assistant', 'story', 'x', 'x')",
            (sid,),
        )


def test_edit_message_records_history(repo: Repo) -> None:
    story = make_story(repo)
    sid = story.id or 0
    a = repo.insert_message(ai_msg(sid, 0, "Anh cười.", "Vui."))
    original = a.raw_content

    e1 = repo.edit_message(
        a.id or 0, raw_content="Anh mỉm cười.\n[Thought: Vui lắm.]", visible_content="Anh mỉm cười.",
        thought="Vui lắm.", directive=None,
    )
    assert e1.raw_content == "Anh mỉm cười.\n[Thought: Vui lắm.]"
    assert e1.visible_content == "Anh mỉm cười." and e1.thought == "Vui lắm."
    assert e1.model_output == original
    assert e1.edited_at is not None
    assert e1.prompt_snapshot == a.prompt_snapshot and e1.gen_stats == a.gen_stats

    e2 = repo.edit_message(a.id or 0, raw_content="Anh im lặng.", visible_content="Anh im lặng.", thought=None, directive=None)
    assert e2.thought is None and e2.model_output == original

    edits = repo.message_edits(a.id or 0)
    assert [(e["before_raw"], e["after_raw"]) for e in edits] == [
        (original, "Anh mỉm cười.\n[Thought: Vui lắm.]"),
        ("Anh mỉm cười.\n[Thought: Vui lắm.]", "Anh im lặng."),
    ]
    with pytest.raises(NotFound):
        repo.edit_message(999, raw_content="x", visible_content="x", thought=None, directive=None)


def test_truncate_from(repo: Repo) -> None:
    story = make_story(repo)
    sid = story.id or 0
    repo.insert_message(ai_msg(sid, 0))
    repo.insert_message(user_msg(sid, 1))
    a2 = repo.insert_message(ai_msg(sid, 2))
    repo.add_variant(ai_msg(sid, 2, "khác"))
    repo.set_feedback(a2.id or 0, "up")
    repo.edit_message(a2.id or 0, raw_content="y", visible_content="y", thought=None, directive=None)
    repo.insert_message(user_msg(sid, 3))

    other = repo.create_story(story.model_copy(update={"id": None}), account_id=repo.owner_id())
    repo.insert_message(user_msg(other.id or 0, 0))
    repo.insert_message(user_msg(other.id or 0, 1))

    assert repo.truncate_from(sid, 2) == 3
    assert [m.turn_index for m in repo.active_messages(sid)] == [0, 1]
    assert repo.next_turn_index(sid) == 2
    # Feedback và lịch sử sửa đi theo message (ON DELETE CASCADE).
    assert repo.conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0] == 0
    assert repo.conn.execute("SELECT COUNT(*) FROM message_edits").fetchone()[0] == 0
    # Story khác không bị ảnh hưởng.
    assert len(repo.active_messages(other.id or 0)) == 2
    assert repo.truncate_from(sid, 10) == 0
    with pytest.raises(NotFound):
        repo.truncate_from(999, 0)


def test_set_feedback(repo: Repo) -> None:
    story = make_story(repo)
    a = repo.insert_message(ai_msg(story.id or 0, 0))
    mid = a.id or 0

    up = repo.set_feedback(mid, "up", "hay")
    assert up.rating == "up"
    assert repo.get_feedback_note(mid) == "hay"

    down = repo.set_feedback(mid, "down")
    assert down.rating == "down"
    assert repo.get_feedback_note(mid) == "hay"  # note=None giữ ghi chú cũ

    cleared = repo.set_feedback(mid, None, "")
    assert cleared.rating is None
    assert repo.get_feedback_note(mid) == ""
    assert repo.conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0] == 1

    with pytest.raises(NotFound):
        repo.set_feedback(999, "up")
    with pytest.raises(ValueError):
        repo.set_feedback(mid, "meh")  # type: ignore[arg-type]


def test_active_messages_order_variant_count_rating(repo: Repo) -> None:
    story = make_story(repo)
    sid = story.id or 0
    # Chèn lệch thứ tự để chắc chắn sắp theo turn_index chứ không theo id.
    repo.insert_message(user_msg(sid, 3, "bốn"))
    repo.insert_message(ai_msg(sid, 0, "một"))
    repo.insert_message(user_msg(sid, 1, "hai"))
    a2 = repo.insert_message(ai_msg(sid, 2, "ba"))
    repo.add_variant(ai_msg(sid, 2, "ba-b"))
    v2c = repo.add_variant(ai_msg(sid, 2, "ba-c"))
    repo.set_feedback(v2c.id or 0, "down")
    repo.set_feedback(a2.id or 0, "up")

    msgs = repo.active_messages(sid)
    assert [m.turn_index for m in msgs] == [0, 1, 2, 3]
    assert [m.variant_count for m in msgs] == [1, 1, 3, 1]
    assert msgs[2].id == v2c.id and msgs[2].visible_content == "ba-c" and msgs[2].rating == "down"
    assert all(m.is_active for m in msgs)
    assert [m.rating for m in msgs] == [None, None, "down", None]
    assert repo.get_message(a2.id or 0, account_id=ANY_ACCOUNT).rating == "up"


def test_transaction_rolls_back(repo: Repo) -> None:
    story = make_story(repo)
    sid = story.id or 0
    with pytest.raises(RuntimeError):
        with repo.transaction():
            repo.insert_message(user_msg(sid, 0))
            with repo.transaction():
                repo.insert_message(ai_msg(sid, 1))
            raise RuntimeError("huỷ")
    assert repo.active_messages(sid) == []
    assert not repo.conn.in_transaction


def test_concurrent_writes(tmp_path: Path) -> None:
    conn = connect(tmp_path / "t.db")
    migrate(conn)
    repo = Repo(conn)
    story = make_story(repo)
    sid = story.id or 0
    repo.insert_message(user_msg(sid, 0))
    repo.insert_message(ai_msg(sid, 1))
    errors: list[BaseException] = []

    def worker(n: int) -> None:
        try:
            for i in range(10):
                repo.add_variant(ai_msg(sid, 1, f"t{n}-{i}"))
                repo.active_messages(sid)
        except BaseException as exc:  # pragma: no cover - chỉ để báo lỗi
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    assert len(repo.list_variants(sid, 1)) == 41
    assert active_count(repo, sid, 1) == 1
    conn.close()


# ---------------------------------------------------------------- seed


def _narration_only(text: str) -> str:
    text = re.sub(r"\[Thought:.*?\]", "", text, flags=re.S)
    return re.sub(r"[\"“][^\"”]*[\"”]", "", text)


def test_seed_greeting_follows_content_rules() -> None:
    card = load_seed_card()
    g = card.greeting
    assert card.name == "Lạc Dương" and card.gender == "male"
    assert card.style_profile == "trung_hien_dai"
    assert card.address_terms.self_term == "tớ" and card.address_terms.player_term == "cậu"
    assert card.address_terms.nicknames == ["Vãn Vãn", "A Vãn"]
    # Lời mở đầu là ví dụ đầu tiên model thấy: thể hiện kiểu Thought mặc định (inline), 2 dòng rải ra.
    assert g.count("[Thought:") == 2
    assert not re.search(r"\]\s*\[Thought:", g)
    assert not g.rstrip().endswith("]")
    assert not re.search(r"[一-鿿]", g)
    assert not re.search(r"\b(tớ|cậu|tôi)\b", _narration_only(g), flags=re.I)
    assert "Lâm Vãn:" not in g
    visible = re.sub(r"\[Thought:[^\]]*\]", "", g)
    assert 120 <= len(visible.split()) <= 185


def test_ensure_seed_idempotent(seeded_repo: Repo) -> None:
    repo = seeded_repo
    stories = repo.list_stories(account_id=ANY_ACCOUNT)
    assert len(stories) == 1
    story = stories[0]
    assert story.title == "Thanh mai trúc mã"
    assert story.relationship_type == "het" and story.pov == "third" and story.mode == "story"
    assert story.language == "vi" and story.model_name == "gemma4:12b"
    assert story.narration_pronouns == NarrationPronouns(character="anh", player="cô")
    card = repo.get_card(story.card_id, account_id=ANY_ACCOUNT)
    persona = repo.get_persona(story.persona_id, account_id=ANY_ACCOUNT)
    assert card.name == "Lạc Dương" and persona.name == "Lâm Vãn" and persona.gender == "female"

    msgs = repo.active_messages(story.id or 0)
    assert len(msgs) == 1
    greeting = msgs[0]
    assert greeting.turn_index == 0 and greeting.role == "assistant" and greeting.mode == "story"
    assert greeting.raw_content == card.greeting
    assert greeting.model_output is None

    assert ensure_seed(repo) == story.id
    assert ensure_seed(repo) == story.id
    assert len(repo.list_cards(account_id=ANY_ACCOUNT)) == 1
    assert len(repo.list_personas(account_id=ANY_ACCOUNT)) == 1
    assert len(repo.list_stories(account_id=ANY_ACCOUNT)) == 1
    assert len(repo.active_messages(story.id or 0)) == 1


def test_seed_greeting_split(seeded_repo: Repo) -> None:
    # seeded_repo cài bản tạm (LYRIS_TEST_STUB) nếu lyris.llm.thought thật chưa có.
    if getattr(importlib.import_module("lyris.llm.thought"), "LYRIS_TEST_STUB", False):
        pytest.skip("lyris.llm.thought chưa có (module [llm] đang viết song song)")
    story = seeded_repo.list_stories(account_id=ANY_ACCOUNT)[0]
    greeting = seeded_repo.active_messages(story.id or 0)[0]
    assert greeting.thought is not None and greeting.thought.startswith("Lại thức khuya") and "\nNgủ say" in greeting.thought
    assert "[Thought" not in greeting.visible_content
    assert greeting.visible_content.startswith("Nắng chiều")
    assert greeting.visible_content.endswith("tớ đưa cậu đi.\"")


def test_create_default_story_and_ensure_returns_newest(seeded_repo: Repo) -> None:
    repo = seeded_repo
    first_id = repo.list_stories(account_id=ANY_ACCOUNT)[0].id
    s2 = create_default_story(repo, title="  Lần hai  ", account_id=repo.owner_id())
    assert s2.title == "Lần hai"
    assert s2.id != first_id
    assert len(repo.list_cards(account_id=ANY_ACCOUNT)) == 1 and len(repo.list_personas(account_id=ANY_ACCOUNT)) == 1
    assert [m.turn_index for m in repo.active_messages(s2.id or 0)] == [0]
    assert ensure_seed(repo) == s2.id
    s3 = create_default_story(repo, account_id=repo.owner_id())
    assert s3.title == "Thanh mai trúc mã"


# ---------------------------------------------------------------- Phase 2: card/persona CRUD, xoá, đếm


def set_time(repo: Repo, table: str, row_id: int, column: str, value: str) -> None:
    repo.conn.execute(f"UPDATE {table} SET {column} = ? WHERE id = ?", (value, row_id))


def full_card() -> CharacterCard:
    return make_card(
        scenario="Vườn trường, {{char}} và {{user}} cùng lớp.",
        alternate_greetings=["Mở đầu hai", "Mở đầu ba [Thought: ừ.]"],
        creator_notes="Ghi chú riêng",
        avatar="card-1-0123abcd.png",
        extensions={"v2": {"creator": "ai đó", "character_book": {"entries": [{"keys": ["x"]}]}}, "khác": 1},
    )


def test_card_phase2_fields_round_trip(repo: Repo) -> None:
    card = full_card()
    created = repo.create_card(card, account_id=repo.owner_id())
    assert created.model_dump(exclude={"id", "uid"}) == card.model_dump(exclude={"id", "uid"})
    assert created.uid is not None and re.fullmatch(r"[0-9a-f]{32}", created.uid)
    assert repo.get_card(created.id or 0, account_id=ANY_ACCOUNT) == created
    row = repo.conn.execute(
        "SELECT alternate_greetings_json, extensions_json FROM character_cards WHERE id = ?", (created.id,)
    ).fetchone()
    assert "Mở đầu hai" in row[0] and "ai đó" in row[1]  # JSON giữ nguyên tiếng Việt


def test_update_card_replaces_all_but_keeps_id_and_avatar(repo: Repo) -> None:
    created = repo.create_card(full_card(), account_id=repo.owner_id())
    cid = created.id or 0
    set_time(repo, "character_cards", cid, "updated_at", "2020-01-01T00:00:00.000Z")
    new = make_card(name="Tên mới", gender="female", tags=[], greeting="", avatar=None, id=555)
    updated = repo.update_card(cid, new, account_id=ANY_ACCOUNT)
    assert updated.id == cid
    assert updated.name == "Tên mới" and updated.gender == "female" and updated.tags == []
    assert updated.scenario == "" and updated.alternate_greetings == [] and updated.extensions == {}
    assert updated.avatar == "card-1-0123abcd.png"  # avatar chỉ đổi qua set_card_avatar
    assert repo.card_updated_at(cid) != "2020-01-01T00:00:00.000Z"
    with pytest.raises(NotFound):
        repo.update_card(999, new, account_id=ANY_ACCOUNT)
    assert not repo._exists("character_cards", 555)


def test_set_card_avatar(repo: Repo) -> None:
    cid = repo.create_card(make_card(), account_id=repo.owner_id()).id or 0
    assert repo.get_card(cid, account_id=ANY_ACCOUNT).avatar is None
    set_time(repo, "character_cards", cid, "updated_at", "2020-01-01T00:00:00.000Z")
    assert repo.set_card_avatar(cid, "card-1-aaaaaaaa.png", account_id=ANY_ACCOUNT).avatar == "card-1-aaaaaaaa.png"
    assert (repo.card_updated_at(cid) or "") > "2020-01-01T00:00:00.000Z"
    assert repo.set_card_avatar(cid, None, account_id=ANY_ACCOUNT).avatar is None
    with pytest.raises(NotFound):
        repo.set_card_avatar(999, "x.png", account_id=ANY_ACCOUNT)
    assert repo.card_updated_at(999) is None


def test_list_cards_and_personas_recently_updated_first(repo: Repo) -> None:
    a = repo.create_card(make_card(name="A"), account_id=repo.owner_id())
    b = repo.create_card(make_card(name="B"), account_id=repo.owner_id())
    c = repo.create_card(make_card(name="C"), account_id=repo.owner_id())
    for card, ts in ((a, "2024-01-01"), (b, "2024-01-03"), (c, "2024-01-02")):
        set_time(repo, "character_cards", card.id or 0, "updated_at", ts)
    assert [x.name for x in repo.list_cards(account_id=ANY_ACCOUNT)] == ["B", "C", "A"]
    repo.update_card(a.id or 0, make_card(name="A2"), account_id=ANY_ACCOUNT)
    assert [x.name for x in repo.list_cards(account_id=ANY_ACCOUNT)] == ["A2", "B", "C"]

    p1 = repo.create_persona(Persona(name="P1", gender="female"), account_id=repo.owner_id())
    p2 = repo.create_persona(Persona(name="P2", gender="male"), account_id=repo.owner_id())
    set_time(repo, "personas", p1.id or 0, "updated_at", "2024-01-02")
    set_time(repo, "personas", p2.id or 0, "updated_at", "2024-01-01")
    assert [x.name for x in repo.list_personas(account_id=ANY_ACCOUNT)] == ["P1", "P2"]
    repo.update_persona(p2.id or 0, Persona(name="P2b", gender="other", description="mới"), account_id=ANY_ACCOUNT)
    assert [x.name for x in repo.list_personas(account_id=ANY_ACCOUNT)] == ["P2b", "P1"]


def test_update_persona(repo: Repo) -> None:
    p = repo.create_persona(Persona(name="Lâm Vãn", gender="female"), account_id=repo.owner_id())
    pid = p.id or 0
    got = repo.update_persona(pid, Persona(id=77, name="Tô Ngư", gender="other", description="mô tả"), account_id=ANY_ACCOUNT)
    assert got == Persona(id=pid, uid=p.uid, name="Tô Ngư", gender="other", description="mô tả")
    assert p.uid is not None  # uid giữ nguyên khi sửa
    assert repo.get_persona(pid, account_id=ANY_ACCOUNT) == got
    with pytest.raises(NotFound):
        repo.update_persona(999, got, account_id=ANY_ACCOUNT)


def _story_with_history(repo: Repo, card_id: int, persona_id: int) -> int:
    story = repo.create_story(
        Story(card_id=card_id, persona_id=persona_id, title="t", narration_pronouns=NarrationPronouns(character="anh", player="cô"))
    , account_id=repo.owner_id())
    sid = story.id or 0
    repo.insert_message(user_msg(sid, 0))
    a = repo.insert_message(ai_msg(sid, 1))
    repo.add_variant(ai_msg(sid, 1, "khác"))
    repo.set_feedback(a.id or 0, "up", "hay")
    repo.edit_message(a.id or 0, raw_content="y", visible_content="y", thought=None, directive=None)
    return sid


def counts(repo: Repo) -> tuple[int, ...]:
    return tuple(
        int(repo.conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0])
        for t in ("stories", "messages", "feedback", "message_edits")
    )


def test_delete_card_in_use(repo: Repo) -> None:
    card = repo.create_card(make_card(), account_id=repo.owner_id())
    other = repo.create_card(make_card(name="Khác"), account_id=repo.owner_id())
    persona = repo.create_persona(Persona(name="P", gender="female"), account_id=repo.owner_id())
    cid, pid = card.id or 0, persona.id or 0
    _story_with_history(repo, cid, pid)
    _story_with_history(repo, cid, pid)
    keep = _story_with_history(repo, other.id or 0, pid)
    assert repo.card_story_count(cid) == 2
    assert repo.persona_story_count(pid) == 3

    with pytest.raises(InUse) as info:
        repo.delete_card(cid, account_id=ANY_ACCOUNT)
    assert info.value.count == 2 and isinstance(info.value, ValueError)
    assert "2 story" in str(info.value)
    assert repo.get_card(cid, account_id=ANY_ACCOUNT) == card and counts(repo) == (3, 9, 3, 3)

    assert repo.delete_card(cid, with_stories=True, account_id=ANY_ACCOUNT) == 2
    with pytest.raises(NotFound):
        repo.get_card(cid, account_id=ANY_ACCOUNT)
    assert counts(repo) == (1, 3, 1, 1)
    assert len(repo.active_messages(keep)) == 2
    with pytest.raises(NotFound):
        repo.card_story_count(cid)
    with pytest.raises(NotFound):
        repo.delete_card(cid, account_id=ANY_ACCOUNT)


def test_delete_unused_card_and_persona(repo: Repo) -> None:
    card = repo.create_card(make_card(), account_id=repo.owner_id())
    persona = repo.create_persona(Persona(name="P", gender="female"), account_id=repo.owner_id())
    assert repo.card_story_count(card.id or 0) == 0
    assert repo.delete_card(card.id or 0, account_id=ANY_ACCOUNT) == 0
    assert repo.list_cards(account_id=ANY_ACCOUNT) == []
    assert repo.delete_persona(persona.id or 0, account_id=ANY_ACCOUNT) == 0
    assert repo.list_personas(account_id=ANY_ACCOUNT) == []
    with pytest.raises(NotFound):
        repo.delete_persona(persona.id or 0, account_id=ANY_ACCOUNT)
    with pytest.raises(NotFound):
        repo.persona_story_count(persona.id or 0)


def test_delete_persona_in_use(repo: Repo) -> None:
    card = repo.create_card(make_card(), account_id=repo.owner_id())
    p1 = repo.create_persona(Persona(name="P1", gender="female"), account_id=repo.owner_id())
    p2 = repo.create_persona(Persona(name="P2", gender="male"), account_id=repo.owner_id())
    _story_with_history(repo, card.id or 0, p1.id or 0)
    keep = _story_with_history(repo, card.id or 0, p2.id or 0)
    with pytest.raises(InUse) as info:
        repo.delete_persona(p1.id or 0, account_id=ANY_ACCOUNT)
    assert info.value.count == 1
    assert repo.delete_persona(p1.id or 0, with_stories=True, account_id=ANY_ACCOUNT) == 1
    assert [s.id for s in repo.list_stories(account_id=ANY_ACCOUNT)] == [keep]
    assert counts(repo) == (1, 3, 1, 1)
    assert repo.card_story_count(card.id or 0) == 1


def test_delete_story_cascades(repo: Repo) -> None:
    story = make_story(repo)
    sid = story.id or 0
    a = repo.insert_message(ai_msg(sid, 0))
    repo.set_feedback(a.id or 0, "down")
    repo.edit_message(a.id or 0, raw_content="y", visible_content="y", thought=None, directive=None)
    other = repo.create_story(story.model_copy(update={"id": None}), account_id=repo.owner_id())
    repo.insert_message(user_msg(other.id or 0, 0))

    repo.delete_story(sid, account_id=ANY_ACCOUNT)
    with pytest.raises(NotFound):
        repo.get_story(sid, account_id=ANY_ACCOUNT)
    assert counts(repo) == (1, 1, 0, 0)
    assert repo.story_updated_at(sid) is None
    with pytest.raises(NotFound):
        repo.delete_story(sid, account_id=ANY_ACCOUNT)
    # Card và persona vẫn còn.
    assert repo.card_story_count(story.card_id) == 1


def test_story_activity_and_list_order(repo: Repo) -> None:
    first = make_story(repo, title="Một")
    second = repo.create_story(first.model_copy(update={"id": None, "title": "Hai"}), account_id=repo.owner_id())
    third = repo.create_story(first.model_copy(update={"id": None, "title": "Ba"}), account_id=repo.owner_id())
    s1, s2, s3 = first.id or 0, second.id or 0, third.id or 0
    for sid, ts in ((s1, "2024-01-01T00:00:00.000Z"), (s2, "2024-01-02T00:00:00.000Z"), (s3, "2024-01-03T00:00:00.000Z")):
        set_time(repo, "stories", sid, "updated_at", ts)
    assert repo.story_updated_at(s1) == "2024-01-01T00:00:00.000Z"
    assert [s.id for s in repo.list_stories(account_id=ANY_ACCOUNT)] == [s3, s2, s1]

    # Message mới nhất đưa story cũ nhất lên đầu.
    m = repo.insert_message(user_msg(s1, 0))
    set_time(repo, "messages", m.id or 0, "created_at", "2024-02-01T00:00:00.000Z")
    assert repo.story_updated_at(s1) == "2024-02-01T00:00:00.000Z"
    assert [s.id for s in repo.list_stories(account_id=ANY_ACCOUNT)] == [s1, s3, s2]

    # Sửa thiết lập cũng tính là hoạt động.
    repo.update_story(s2, title="Hai mới", account_id=ANY_ACCOUNT)
    assert (repo.story_updated_at(s2) or "") > "2024-02-01"
    assert [s.id for s in repo.list_stories(account_id=ANY_ACCOUNT)] == [s2, s1, s3]
    assert repo.story_updated_at(999) is None
