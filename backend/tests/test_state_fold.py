"""Phase 3: phép gộp state (lyris/state/fold.py), dữ liệu state/ký ức trong repo (migration 0006).

Không gọi model: chỉ hàm thuần và SQLite trong bộ nhớ.
"""
from __future__ import annotations

import math
import sqlite3
from typing import Any

import pytest

from lyris.db.repo import ANY_ACCOUNT, NewMemory, NotFound, Repo, fts_match_expression
from lyris.models import (
    DEFAULT_INITIAL_RELATIONSHIP,
    GenStats,
    Message,
    NarrationPronouns,
    Persona,
    RelationshipDelta,
    RelationshipValues,
    SceneState,
    Story,
)
from lyris.seed import load_seed_card
from lyris.state.fold import (
    StateEvent,
    apply_delta,
    clamp_emotion,
    dominant_emotion,
    fold_events,
    fold_relationship,
    fold_scene,
    initial_relationship,
    latest_summary,
)
from lyris.studio.stories import create_story_for

# ---------------------------------------------------------------------------- hàm thuần


def values(**kw: int) -> RelationshipValues:
    return RelationshipValues(**{**DEFAULT_INITIAL_RELATIONSHIP, **kw})


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (50, 50),
        (49.5, 50),  # làm tròn nửa lên như Math.round
        (2.4, 2),
        (150, 100),
        (-3, 0),
        (None, 7),
        ("50", 7),
        (True, 7),
        (math.nan, 7),
        (math.inf, 7),
    ],
)
def test_clamp_emotion_matches_frontend(raw: Any, expected: int) -> None:
    assert clamp_emotion(raw, 7) == expected


def test_initial_relationship_sources_in_order() -> None:
    card_ext = {"lyris": {"initial_relationship": {"affection": 80, "trust": "x", "fear": 300}}}
    # Không có ảnh chụp: card, giá trị hỏng của card -> mặc định; giá trị ngoài khoảng -> kẹp.
    got = initial_relationship(None, card_ext)
    assert got.affection == 80 and got.trust == DEFAULT_INITIAL_RELATIONSHIP["trust"] and got.fear == 100
    # Ảnh chụp của story thắng card; khoá thiếu/hỏng trong ảnh chụp thì xét card rồi mặc định.
    got = initial_relationship({"affection": 10, "aversion": None}, card_ext)
    assert got.affection == 10 and got.fear == 100 and got.aversion == DEFAULT_INITIAL_RELATIONSHIP["aversion"]
    # Card không có / extensions lạ -> mặc định.
    assert initial_relationship(None, None).model_dump() == DEFAULT_INITIAL_RELATIONSHIP
    assert initial_relationship(None, {"lyris": "rác"}).model_dump() == DEFAULT_INITIAL_RELATIONSHIP
    assert initial_relationship(None, {"lyris": {"initial_relationship": [1, 2]}}).model_dump() == DEFAULT_INITIAL_RELATIONSHIP


def test_fold_relationship_clamps_after_every_step() -> None:
    start = values(affection=98, aversion=2)
    up = RelationshipDelta(affection=5, aversion=-5)
    down = RelationshipDelta(affection=-5, aversion=5)
    # Kẹp sau mỗi bước: 98 -> 100 -> 95 (cộng dồn rồi mới kẹp sẽ ra 98).
    got = fold_relationship(start, [up, down])
    assert got.affection == 95 and got.aversion == 5
    assert apply_delta(values(trust=0), RelationshipDelta(trust=-5)).trust == 0


def test_fold_scene_keeps_latest_non_empty_field() -> None:
    got = fold_scene(
        [
            SceneState(location="Thư viện", time="Chiều"),
            SceneState(location=None, time="Tối"),
            SceneState(location="  ", time=None),
        ]
    )
    assert got == SceneState(location="Thư viện", time="Tối")


def ev(i: int, turn: int, kind: str, payload: dict[str, Any], message_id: int | None = None) -> StateEvent:
    return StateEvent(id=i, story_id=1, message_id=message_id or turn * 10, turn_index=turn, kind=kind, payload=payload)  # type: ignore[arg-type]


def test_fold_events_order_upto_and_suggestions() -> None:
    events = [
        ev(5, 3, "relationship_delta", {"affection": 5}),
        ev(1, 1, "relationship_delta", {"affection": 2}),
        ev(2, 1, "scene", {"location": "Sân trường", "time": None}),
        ev(3, 1, "summary", {"text": "Tóm tắt A", "upto_turn": 0}),
        ev(6, 3, "suggestions", {"items": ["Một", " Hai ", "", "Một", "Ba", "Bốn"]}),
        ev(7, 3, "relationship_delta", {"affection": 99}),  # hỏng (ngoài ±5): bỏ qua
        ev(8, 3, "summary", {"text": "", "upto_turn": 2}),  # hỏng: bỏ qua
    ]
    base = values(affection=50)
    got = fold_events(base, events, last_message_id=30, last_message_role="assistant")
    assert got.relationship.affection == 57 and got.has_relationship_events
    assert got.scene.location == "Sân trường"
    assert got.summary is not None and got.summary.text == "Tóm tắt A"
    assert got.suggestions == ["Một", "Hai", "Ba"]
    # Người chơi đã trả lời (message cuối là của user) -> không có gợi ý.
    assert fold_events(base, events, last_message_id=40, last_message_role="user").suggestions == []
    # State như tại lượt 2: chỉ event của lượt <= 2.
    early = fold_events(base, events, upto_turn=2, last_message_id=30, last_message_role="assistant")
    assert early.relationship.affection == 52 and early.suggestions == []
    assert not fold_events(base, []).has_relationship_events
    assert latest_summary(events) is not None and latest_summary(events, upto_turn=0) is None


def test_dominant_emotion_tie_follows_key_order() -> None:
    assert dominant_emotion(values(), has_events=False) is None
    tie = RelationshipValues(affection=60, trust=60, attraction=60, obsession=0, fear=0, aversion=0)
    got = dominant_emotion(tie, has_events=True)
    assert got is not None and got.key == "affection" and got.value == 60
    got = dominant_emotion(RelationshipValues(affection=1, trust=2, attraction=3, obsession=4, fear=91, aversion=91), has_events=True)
    assert got is not None and got.key == "fear"


def test_fts_match_expression_is_safe() -> None:
    assert fts_match_expression([]) is None
    assert fts_match_expression(["", "  "]) is None
    assert fts_match_expression(["thư viện", "trà"]) == '"thư viện" OR "trà"'
    assert fts_match_expression(['a" OR NEAR(b', "x*"]) == '"a"" OR NEAR(b" OR "x*"'
    assert fts_match_expression(["trà", "trà"]) == '"trà"'


# ---------------------------------------------------------------------------- repo


def _story(repo: Repo, *, extensions: dict[str, Any] | None = None) -> Story:
    card = load_seed_card()
    if extensions is not None:
        card = card.model_copy(update={"extensions": extensions})
    card = repo.create_card(card, account_id=repo.owner_id())
    persona = repo.create_persona(Persona(name="Lâm Vãn", gender="female"), account_id=repo.owner_id())
    assert card.id and persona.id
    return create_story_for(repo, card.id, persona.id, model_name="m", account_id=repo.owner_id())


def _msg(repo: Repo, story: Story, turn: int, role: str, text: str = "x", *, aborted: bool = False) -> Message:
    assert story.id is not None
    m = Message(
        story_id=story.id,
        turn_index=turn,
        role=role,  # type: ignore[arg-type]
        mode="story",
        raw_content=text,
        visible_content=text,
        gen_stats=GenStats(aborted=aborted) if role == "assistant" else None,
    )
    return repo.insert_message(m)


def _extract(repo: Repo, msg: Message, *, delta: dict[str, int] | None = None, memory: str | None = None,
             facts: list[str] = (), scene: dict[str, Any] | None = None) -> None:  # type: ignore[assignment]
    assert msg.id is not None
    events: list[tuple[Any, dict[str, Any]]] = [("relationship_delta", RelationshipDelta(**(delta or {})).model_dump())]
    if scene:
        events.append(("scene", scene))
    mems = [NewMemory(kind="memory", text=memory)] if memory else []
    mems += [NewMemory(kind="fact", text=f, subject="Lâm Vãn") for f in facts]
    assert repo.replace_extraction(msg.id, events, mems) is not None


def test_create_story_snapshots_initial_relationship(seeded_repo: Repo) -> None:
    repo = seeded_repo
    story = _story(repo, extensions={"lyris": {"initial_relationship": {"affection": 77}}})
    assert story.id is not None
    snap = repo.story_initial_relationship(story.id)
    assert snap is not None and snap["affection"] == 77 and snap["trust"] == DEFAULT_INITIAL_RELATIONSHIP["trust"]
    # Sửa card sau đó không đổi story đã có.
    card = repo.get_card(story.card_id, account_id=ANY_ACCOUNT)
    repo.update_card(story.card_id, card.model_copy(update={"extensions": {}}), account_id=ANY_ACCOUNT)
    assert repo.story_initial_relationship(story.id)["affection"] == 77  # type: ignore[index]
    # Story tạo thẳng qua repo (seed) cũng có ảnh chụp, tính từ card.
    plain = repo.create_story(
        Story(card_id=story.card_id, persona_id=story.persona_id, title="t",
              narration_pronouns=NarrationPronouns(character="anh", player="cô"))
    , account_id=repo.owner_id())
    assert plain.id is not None and repo.story_initial_relationship(plain.id) == DEFAULT_INITIAL_RELATIONSHIP
    # Story cũ (trước Phase 3): NULL.
    repo.set_story_initial_relationship(plain.id, None)
    assert repo.story_initial_relationship(plain.id) is None
    with pytest.raises(NotFound):
        repo.story_initial_relationship(99999)


def test_state_events_only_from_active_messages(seeded_repo: Repo) -> None:
    repo = seeded_repo
    story = _story(repo)
    assert story.id is not None
    _msg(repo, story, 1, "user")
    a = _msg(repo, story, 2, "assistant")
    _extract(repo, a, delta={"trust": 3}, memory="Cậu ấy mượn sách.")
    assert [e.kind for e in repo.state_events(story.id)] == ["relationship_delta"]
    # Regenerate: variant mới active -> event của variant cũ biến mất.
    b = repo.add_variant(a.model_copy(update={"raw_content": "y", "visible_content": "y"}))
    assert repo.state_events(story.id) == [] and repo.list_memories(story.id) == []
    _extract(repo, b, delta={"trust": -2})
    assert repo.state_events(story.id)[0].payload["trust"] == -2
    # Lật lại variant cũ: hiệu ứng cũ quay lại.
    repo.select_variant(story.id, 2, 0)
    assert repo.state_events(story.id)[0].payload["trust"] == 3
    assert [m.text for m in repo.list_memories(story.id)] == ["Cậu ấy mượn sách."]
    # Event của message không active vẫn đọc được theo message.
    assert b.id is not None and len(repo.message_state_events(b.id)) == 1
    # Xoá lượt -> CASCADE.
    repo.truncate_from(story.id, 2)
    assert repo.state_events(story.id) == [] and repo.list_memories(story.id, limit=None) == []
    assert repo.conn.execute("SELECT COUNT(*) FROM state_events").fetchone()[0] == 0


def test_replace_extraction_replaces_and_skips_inactive(seeded_repo: Repo) -> None:
    repo = seeded_repo
    story = _story(repo)
    assert story.id is not None
    _msg(repo, story, 1, "user")
    a = _msg(repo, story, 2, "assistant")
    assert a.id is not None
    _extract(repo, a, delta={"trust": 3}, memory="Một", facts=["F1"])
    repo.add_summary(a.id, "Tóm tắt", 1)
    _extract(repo, a, delta={"trust": 1}, memory="Hai")
    kinds = sorted(e.kind for e in repo.state_events(story.id))
    assert kinds == ["relationship_delta", "summary"]  # tóm tắt không bị trích xuất lại xoá
    assert [m.text for m in repo.list_memories(story.id)] == ["Hai"]
    repo.add_variant(a.model_copy(update={"raw_content": "y"}))
    assert repo.replace_extraction(a.id, [("relationship_delta", {})], []) is None
    with pytest.raises(ValueError):
        b = repo.list_variants(story.id, 2)[-1]
        assert b.id is not None
        repo.replace_extraction(b.id, [("summary", {"text": "x", "upto_turn": 0})], [])
    # delete_message_state (khi sửa): xoá kết quả trích xuất, GIỮ tóm tắt dồn neo ở message.
    repo.select_variant(story.id, 2, 0)
    assert repo.delete_message_state(a.id) >= 1
    assert [e.kind for e in repo.state_events(story.id)] == ["summary"]
    assert repo.list_memories(story.id) == []


def test_memory_fts_keeps_vietnamese_marks_and_tracks_changes(seeded_repo: Repo) -> None:
    repo = seeded_repo
    story = _story(repo)
    other = _story(repo)
    assert story.id is not None and other.id is not None
    _msg(repo, story, 1, "user")
    a = _msg(repo, story, 2, "assistant")
    _extract(repo, a, memory="Lâm Vãn khen má lúm của Lạc Dương.", facts=["Lâm Vãn thích trà sữa ở thư viện."])
    _msg(repo, other, 1, "user")
    o = _msg(repo, other, 2, "assistant")
    _extract(repo, o, memory="Trà sữa của story khác.")

    hits = repo.search_memories_fts(story.id, ["má"], 10)
    assert [h[0].text for h in hits] == ["Lâm Vãn khen má lúm của Lạc Dương."]
    assert repo.search_memories_fts(story.id, ["mà"], 10) == []  # giữ dấu: mà khác má
    hits = repo.search_memories_fts(story.id, ["trà sữa", "thư viện"], 10)
    assert len(hits) == 1 and hits[0][0].kind == "fact" and isinstance(hits[0][1], float)
    assert repo.search_memories_fts(story.id, [], 10) == []
    assert repo.search_memories_fts(story.id, ['"; DROP TABLE memories; --', "NEAR(", "*"], 10) == []
    # Sửa text (trigger update) và xoá (trigger delete) đồng bộ FTS.
    mem = repo.list_memories(story.id, kind="memory")[0]
    assert mem.id is not None
    repo.conn.execute("UPDATE memories SET text = 'Đi xem pháo hoa.' WHERE id = ?", (mem.id,))
    assert repo.search_memories_fts(story.id, ["má"], 10) == []
    assert len(repo.search_memories_fts(story.id, ["pháo hoa"], 10)) == 1
    repo.delete_memory(story.id, mem.id, account_id=ANY_ACCOUNT)
    assert repo.search_memories_fts(story.id, ["pháo hoa"], 10) == []
    with pytest.raises(NotFound):
        repo.delete_memory(story.id, mem.id, account_id=ANY_ACCOUNT)
    fact = repo.list_memories(story.id)[0]
    assert fact.id is not None
    with pytest.raises(NotFound):
        repo.delete_memory(other.id, fact.id, account_id=ANY_ACCOUNT)  # ký ức không thuộc story đó
    # Variant không active: không tìm thấy.
    repo.add_variant(a.model_copy(update={"raw_content": "z"}))
    assert repo.search_memories_fts(story.id, ["trà sữa"], 10) == []
    integrity = repo.conn.execute("INSERT INTO memories_fts(memories_fts) VALUES ('integrity-check')")
    assert integrity is not None


def test_memory_embeddings_active_and_model_scoped(seeded_repo: Repo) -> None:
    repo = seeded_repo
    story = _story(repo)
    assert story.id is not None
    _msg(repo, story, 1, "user")
    a = _msg(repo, story, 2, "assistant")
    _extract(repo, a, memory="Một", facts=["Hai"])
    missing = repo.memories_missing_embedding(story.id, "bge-m3")
    assert [m.text for m in missing] == ["Một", "Hai"]
    assert missing[0].id is not None
    assert repo.set_memory_embedding(missing[0].id, b"\x00\x00\x80?", "bge-m3")
    assert [(m.text, b) for m, b in repo.memory_embeddings(story.id, "bge-m3")] == [("Một", b"\x00\x00\x80?")]
    assert repo.memory_embeddings(story.id, "khac") == []
    assert [m.text for m in repo.memories_missing_embedding(story.id, "bge-m3")] == ["Hai"]
    assert not repo.set_memory_embedding(987654, b"", "bge-m3")
    repo.add_variant(a.model_copy(update={"raw_content": "z"}))
    assert repo.memory_embeddings(story.id, "bge-m3") == []


def test_job_queue_tables(seeded_repo: Repo) -> None:
    repo = seeded_repo
    story = _story(repo)
    assert story.id is not None
    _msg(repo, story, 1, "user")
    a = _msg(repo, story, 2, "assistant")
    assert a.id is not None
    j1 = repo.enqueue_job(story.id, "extract", a.id)
    assert repo.enqueue_job(story.id, "extract", a.id) == j1  # đã có job queued giống hệt
    j2 = repo.enqueue_job(story.id, "embed")
    # Chỉ còn lời mở đầu (lượt 0, Phase 3b) chưa có job trích xuất.
    assert repo.has_pending_jobs(story.id) and repo.unprocessed_turns(story.id) == 1
    claimed = repo.claim_next_job()
    assert claimed is not None and claimed.id == j1 and claimed.status == "running"  # FIFO
    assert repo.requeue_job(j1) and repo.get_job(j1).status == "queued" and repo.get_job(j1).attempts == 0
    assert repo.claim_next_job().id == j1  # type: ignore[union-attr]
    assert repo.reset_running_jobs() == 1 and repo.get_job(j1).status == "queued"
    repo.claim_next_job()
    repo.finish_job(j1, "done", attempts=1)
    assert repo.get_job(j1).attempts == 1 and repo.unprocessed_turns(story.id) == 1  # còn lời mở đầu
    with pytest.raises(ValueError):
        repo.finish_job(j2, "running")  # type: ignore[arg-type]
    # Regenerate: job queued của variant cũ bị huỷ.
    j3 = repo.enqueue_job(story.id, "extract", a.id)
    repo.add_variant(a.model_copy(update={"raw_content": "y"}))
    assert repo.cancel_stale_jobs(story.id) == 1 and repo.get_job(j3).status == "cancelled"
    assert repo.unprocessed_turns(story.id) == 2  # variant mới + lời mở đầu
    assert [(m.turn_index, m.variant_index) for m in repo.messages_needing_extract(story.id)] == [(0, 0), (2, 1)]
    with pytest.raises(sqlite3.IntegrityError):
        repo.conn.execute(
            "INSERT INTO jobs (story_id, kind, status, created_at, updated_at) VALUES (?, 'nope', 'queued', '', '')",
            (story.id,),
        )
    # Xoá message: job đi theo CASCADE.
    repo.truncate_from(story.id, 2)
    assert all(j.message_id is None for j in repo.list_jobs(story.id))
