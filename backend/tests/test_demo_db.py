"""scripts/make_demo_db.py: builds a complete demo DB offline and never writes into data/."""
from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

from lyris.db.connection import connect
from lyris.db.repo import ANY_ACCOUNT, Repo
from lyris.llm.fake import FakeLLM
from lyris.state.extract import is_warm
from lyris.state.service import StateService

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "make_demo_db.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("lyris_make_demo_db", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses need the module registered
    spec.loader.exec_module(module)
    return module


def test_demo_db_contents(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    demo = _load()
    db = tmp_path / "demo" / "lyris.db"
    assert demo.main([str(db), str(tmp_path / "avatars")]) == 0
    assert "Đã tạo" in capsys.readouterr().out

    repo = Repo(connect(db))
    rows = repo.story_rows(account_id=ANY_ACCOUNT)
    assert [r.card_name for r in rows] == ["Hạ Vy", "Trần Minh Khang", "Morwenna Penrose", "Tạ Vân Lan"]
    by_name = {r.card_name: r for r in rows}
    assert by_name["Trần Minh Khang"].story.mode == "dm" and by_name["Trần Minh Khang"].last_mode == "dm"
    assert by_name["Morwenna Penrose"].story.language == "en"
    assert all(r.card_avatar for r in rows), "template images become avatars"
    personas = {p.name: p for p in repo.list_personas(account_id=ANY_ACCOUNT)}
    assert set(personas) >= {"Ngọc Anh", "Gia Huy"}
    for name in ("Ngọc Anh", "Gia Huy"):
        avatar = personas[name].avatar
        assert avatar and (tmp_path / "avatars" / avatar).is_file(), "demo personas have avatars"
    # Phase 2c: a completed account profile (fictional), an own card, everything owned by the owner.
    owner = repo.owner_account()
    assert owner.id is not None
    assert (owner.display_name, owner.handle) == (demo.ACCOUNT["display_name"], demo.ACCOUNT["handle"])
    assert owner.bio == demo.ACCOUNT["bio"] and owner.profile_completed
    assert owner.avatar and (tmp_path / "avatars" / owner.avatar).is_file()
    own = [c for c in repo.list_cards(account_id=ANY_ACCOUNT) if c.name == demo.OWN_CARD["name"]]
    assert len(own) == 1 and own[0].avatar and own[0].visibility == "private"
    assert "template" not in (own[0].extensions.get("lyris") or {})
    conn = repo.conn
    for table in ("character_cards", "personas", "stories"):
        assert conn.execute(f"SELECT COUNT(*) FROM {table} WHERE account_id IS NOT ?", (owner.id,)).fetchone()[0] == 0
    default = repo.get_app_settings(account_id=repo.owner_id()).default_persona_id
    assert default is not None and repo.get_persona(default, account_id=ANY_ACCOUNT).name == "Ngọc Anh"

    ha_vy = by_name["Hạ Vy"].story
    assert ha_vy.id is not None
    msgs = repo.active_messages(ha_vy.id)
    assert len(msgs) == len(demo.HA_VY) + 1  # + greeting
    assert sum(1 for m in msgs if m.role == "assistant" and m.thought) >= 4
    assert any(m.directive for m in msgs if m.role == "user")
    assert "[Thought:" not in "".join(m.visible_content for m in msgs)
    assert len(repo.list_variants(ha_vy.id, msgs[-1].turn_index)) == 2
    # Timestamps were moved into the past: the oldest story is days old.
    assert rows[-1].updated_at is not None and rows[0].updated_at is not None
    assert rows[-1].updated_at < rows[0].updated_at

    # Phase 3: state as if the worker had extracted every turn (except the oldest story).
    state = StateService(repo, FakeLLM())
    by_story = {r.card_name: r.story for r in rows}
    for name in ("Hạ Vy", "Trần Minh Khang", "Morwenna Penrose"):
        story = by_story[name]
        assert story.id is not None
        extras = asyncio.run(state.extras(story))
        assert extras.unprocessed_turns == 0 and not extras.pending, name
        assert extras.location, name
        # Phase 3b: gợi ý chỉ có ở Hạ Vy (như thể vừa bấm "Nhận gợi ý").
        assert len(extras.suggestions) == (3 if name == "Hạ Vy" else 0), name
        kinds = {m.kind for m in extras.memories}
        assert kinds == {"memory", "fact"}, name
        assert extras.relationship is not None and extras.relationship.directive, name
        emotion, location = state.hub_info(story)
        assert emotion is not None and location == extras.location
        # Dòng thời gian: lời mở đầu có cảnh + ký ức (không đổi cảm xúc), mỗi lượt đổi tối đa 3 chỉ số
        # (3 chỉ khi lượt có thay đổi tổn thương: ghen, bị đẩy ra..., xem `pick_changes`).
        timeline = state.timeline(story)
        assert timeline and timeline[0].turn_index == 0 and timeline[0].scene and timeline[0].memory, name
        assert timeline[0].delta == {} and any(e.delta for e in timeline), name
        assert all(len(e.delta) <= 2 or (len(e.delta) == 3 and not all(is_warm(k, v) for k, v in e.delta.items()))
                   for e in timeline), name
        assert not repo.state_events(story.id, kinds=("relationship_delta",), upto_turn=0), name
    ha_vy_extras = asyncio.run(state.extras(ha_vy))
    assert ha_vy_extras.summary and ha_vy_extras.in_world_time == "Chiều tối"
    assert ha_vy_extras.location == "Gác xép tiệm sách"
    # Only the active (last) variant of the final turn counts; the other variant keeps its own state.
    assert any("Tôi gật đầu" in s for s in ha_vy_extras.suggestions)
    assert sum(1 for m in ha_vy_extras.memories if "đòi thêm một buổi chiều" in m.text) == 1
    assert not any("tám giờ tiệm mở cửa" in m.text for m in ha_vy_extras.memories)
    van_lan = by_story["Tạ Vân Lan"]
    van_lan_extras = asyncio.run(state.extras(van_lan))
    # Story "cũ": cả lời mở đầu lẫn lượt trả lời chưa được ghi nhớ.
    assert van_lan_extras.unprocessed_turns == 2 and van_lan_extras.memories == []
    assert state.timeline(van_lan) == []
    assert state.hub_info(van_lan) == (None, None)
    assert conn.execute("SELECT COUNT(*) FROM jobs WHERE status != 'done'").fetchone()[0] == 0

    # Existing DB: refused without --force, rebuilt with it.
    assert demo.main([str(db), str(tmp_path / "avatars")]) == 1
    assert demo.main([str(db), str(tmp_path / "avatars"), "--force"]) == 0


def test_demo_db_fresh_account(tmp_path: Path) -> None:
    demo = _load()
    db = tmp_path / "fresh" / "lyris.db"
    assert demo.main([str(db), str(tmp_path / "avatars"), "--fresh-account"]) == 0
    owner = Repo(connect(db)).owner_account()
    assert (owner.handle, owner.display_name, owner.profile_completed, owner.avatar) == ("ban", "Bạn", False, None)


def test_initials_png_is_flat_png() -> None:
    from io import BytesIO

    from PIL import Image

    demo = _load()
    img = Image.open(BytesIO(demo.initials_png("Ngọc Anh", "#9A5A4A", size=64)))
    assert img.format == "PNG" and img.size == (64, 64)
    assert img.getpixel((0, 0)) == (0x9A, 0x5A, 0x4A)


def test_demo_db_refuses_repo_data_dir() -> None:
    demo = _load()
    data_dir = demo.REPO_ROOT / "data"
    assert demo.main([str(data_dir / "demo-should-not-exist.db"), "/tmp/lyris-demo-avatars-unused"]) == 2
    assert not (data_dir / "demo-should-not-exist.db").exists()
