"""Test tìm ký ức (lyris/memory/retrieval.py): từ khoá, RRF, vector blob, fallback khi embed lỗi."""
from __future__ import annotations

import struct

import pytest

from lyris.llm.base import LLMError
from lyris.llm.fake import FakeLLM, fake_vector
from lyris.memory.retrieval import (
    IMPORTANCE_WEIGHT,
    RRF_K,
    cosine,
    fuse,
    keyword_terms,
    name_tokens,
    pack_vector,
    query_terms,
    query_text,
    retrieve,
    unpack_vector,
)
from lyris.models import MemoryItem, Message
from tests.test_prompt import make_story


def item(memory_id: int, text: str, *, turn: int = 1, importance: int = 3, kind: str = "memory") -> MemoryItem:
    return MemoryItem(
        id=memory_id, story_id=1, message_id=memory_id, turn_index=turn, kind=kind, text=text, importance=importance  # type: ignore[arg-type]
    )


def msg(turn: int, role: str, text: str) -> Message:
    return Message(story_id=1, turn_index=turn, role=role, mode="story", raw_content=text, visible_content=text)  # type: ignore[arg-type]


# ---- vector blob -------------------------------------------------------------------------------------


def test_pack_unpack_roundtrip_float32_le() -> None:
    vec = [0.0, 1.0, -2.5, 0.125, 3.4028234663852886e38]
    blob = pack_vector(vec)
    assert len(blob) == 4 * len(vec)
    assert blob == struct.pack("<5f", *vec)
    assert unpack_vector(blob) == vec
    assert unpack_vector(pack_vector([])) == []


def test_unpack_rejects_bad_length() -> None:
    with pytest.raises(ValueError):
        unpack_vector(b"\x00\x00\x00")


def test_cosine() -> None:
    assert cosine([1, 0], [1, 0]) == pytest.approx(1.0)
    assert cosine([1, 0], [0, 1]) == pytest.approx(0.0)
    assert cosine([1, 0], [-1, 0]) == pytest.approx(-1.0)
    assert cosine([0, 0], [1, 0]) == 0.0
    assert cosine([1, 0], [1, 0, 0]) == 0.0


# ---- từ khoá --------------------------------------------------------------------------------------------


def test_query_terms_vi_stopwords_bigrams_nfc() -> None:
    terms = query_terms("Cậu còn nhớ THƯ VIỆN tầng ba không? Tớ mời cậu trà sữa nhé!", "vi")
    assert "thư viện" in terms and "trà sữa" in terms and "tầng ba" in terms
    assert "thư" in terms and "viện" in terms
    for stop in ("cậu", "tớ", "không", "nhé", "còn"):
        assert stop not in terms
    assert all(len(t) >= 2 for t in terms)
    assert len(terms) == len(set(terms))
    # Bigram không bắc qua stopword: "tớ mời" không có, "mời" vẫn có.
    assert "mời" in terms and not any(t.startswith("tớ ") or t.endswith(" tớ") for t in terms)
    nfd = query_terms("thú viện", "vi")  # dạng NFD
    assert nfd == query_terms("thú viện", "vi")


def test_query_terms_drops_short_tokens_and_keeps_order() -> None:
    assert query_terms("a b anh đi chơi xa", "vi") == ["chơi", "chơi xa", "xa"]


def test_query_terms_en_has_no_bigrams() -> None:
    terms = query_terms("Do you remember the library on the third floor?", "en")
    assert terms == ["remember", "library", "third", "floor"]


def test_query_terms_capped() -> None:
    text = " ".join(f"từ{i} khoá{i}" for i in range(40))
    terms = query_terms(text, "vi")
    assert len(terms) == 32
    assert sum(" " in t for t in terms) >= 16


def test_query_text_last_user_plus_previous_reply() -> None:
    history = [msg(0, "assistant", "Lời mở đầu"), msg(1, "user", "Một"), msg(2, "assistant", "Trả lời"), msg(3, "user", "Hai"), msg(4, "user", "Ba")]
    assert query_text(history) == "Trả lời\nHai\nBa"
    assert query_text([msg(0, "user", "Chỉ có tôi")]) == "Chỉ có tôi"


# ---- fuse -------------------------------------------------------------------------------------------------


def test_fuse_rrf_and_importance() -> None:
    items = {1: item(1, "a", importance=3), 2: item(2, "b", importance=3), 3: item(3, "c", importance=3)}
    hits = fuse([(2, -5.0), (1, -1.0)], [(1, 0.9), (3, 0.5)], items)
    assert [h.memory_id for h in hits] == [1, 2, 3]
    expected_1 = 1 / (RRF_K + 2) + 1 / (RRF_K + 1) + IMPORTANCE_WEIGHT * 3
    assert hits[0].score == pytest.approx(expected_1)
    assert hits[1].score == pytest.approx(1 / (RRF_K + 1) + IMPORTANCE_WEIGHT * 3)


def test_fuse_one_side_missing_and_unknown_ids() -> None:
    items = [item(1, "a"), item(2, "b", importance=5)]
    only_kw = fuse([(1, -3.0), (2, -1.0), (99, -9.0)], [], items)
    assert [h.memory_id for h in only_kw] == [2, 1]  # importance 5 kéo b lên
    only_vec = fuse([], [(1, 0.2), (2, 0.8)], items)
    assert [h.memory_id for h in only_vec] == [2, 1]
    assert fuse([], [], items) == []


def test_fuse_carries_fields_and_tie_breaks_newer_first() -> None:
    items = {1: item(1, "cũ", turn=2), 2: item(2, "fact", turn=8, kind="fact")}
    hits = fuse([], [], items)
    assert hits == []
    hits = fuse([(1, -1.0)], [(2, 0.5)], items)  # cùng hạng 1 ở hai phía, cùng importance
    assert [h.memory_id for h in hits] == [2, 1]
    assert hits[0].kind == "fact" and hits[0].text == "fact" and hits[0].turn_index == 8


# ---- retrieve -------------------------------------------------------------------------------------------


class FakeRepo:
    def __init__(self, memories: list[MemoryItem], embed_model: str | None = "bge-m3") -> None:
        self.memories = memories
        self.embed_model = embed_model
        self.fts_calls: list[tuple[int, list[str], int]] = []
        self.embedding_calls: list[tuple[int, str]] = []

    def search_memories_fts(self, story_id: int, terms: list[str], limit: int) -> list[tuple[MemoryItem, float]]:
        self.fts_calls.append((story_id, list(terms), limit))
        scored = []
        for m in self.memories:
            hits = sum(1 for t in terms if t in m.text.lower())
            if hits:
                scored.append((m, -float(hits)))
        scored.sort(key=lambda p: p[1])
        return scored[:limit]

    def memory_embeddings(self, story_id: int, embed_model: str) -> list[tuple[MemoryItem, bytes]]:
        self.embedding_calls.append((story_id, embed_model))
        if embed_model != self.embed_model:
            return []
        return [(m, pack_vector(fake_vector(m.text))) for m in self.memories]


MEMORIES = [
    item(1, "Lạc Dương mua trà sữa khoai môn cho Lâm Vãn ở thư viện", turn=4, importance=3),
    item(2, "Lâm Vãn hứa cuối tuần về quê cùng Lạc Dương", turn=8, importance=5),
    item(3, "Hai người cãi nhau ở quán lẩu", turn=12, importance=2),
    item(4, "Lạc Dương không ăn được cay", turn=12, importance=3, kind="fact"),
]
HISTORY = [msg(20, "assistant", "Anh nhìn cô."), msg(21, "user", "Cậu còn nhớ trà sữa khoai môn ở thư viện không?")]


async def test_retrieve_hybrid() -> None:
    repo, llm = FakeRepo(MEMORIES), FakeLLM()
    hits = await retrieve(repo, llm, make_story(), HISTORY, embed_model="bge-m3", limit=8)
    assert hits[0].memory_id == 1
    assert llm.embed_calls == [{"model": "bge-m3", "texts": ["Anh nhìn cô.\nCậu còn nhớ trà sữa khoai môn ở thư viện không?"]}]
    story_id, terms, limit = repo.fts_calls[0]
    assert story_id == 1 and limit == 16 and "trà sữa" in terms and "thư viện" in terms


async def test_retrieve_keyword_only_without_embed_model() -> None:
    repo, llm = FakeRepo(MEMORIES), FakeLLM()
    hits = await retrieve(repo, llm, make_story(), HISTORY, embed_model=None)
    assert [h.memory_id for h in hits] == [1]
    assert llm.embed_calls == [] and repo.embedding_calls == []


async def test_retrieve_skips_embed_when_no_stored_vectors() -> None:
    repo, llm = FakeRepo(MEMORIES, embed_model="khác"), FakeLLM()
    hits = await retrieve(repo, llm, make_story(), HISTORY, embed_model="bge-m3")
    assert [h.memory_id for h in hits] == [1]
    assert llm.embed_calls == []


async def test_retrieve_falls_back_to_keyword_on_embed_error() -> None:
    repo, llm = FakeRepo(MEMORIES), FakeLLM(embed_error=LLMError("chưa pull bge-m3"))
    hits = await retrieve(repo, llm, make_story(), HISTORY, embed_model="bge-m3")
    assert [h.memory_id for h in hits] == [1]
    assert len(llm.embed_calls) == 1


def test_keyword_terms_put_player_message_first_and_skip_names() -> None:
    # Lượt trả lời dài của nhân vật từng chiếm hết 32 cụm, đẩy mất "sinh nhật", "hứa" của người chơi.
    reply = " ".join(f"từ{i} khoá{i}" for i in range(40))
    history = [msg(10, "assistant", f"Lạc Dương nhìn Lâm Vãn. {reply}"), msg(11, "user", "Cậu còn nhớ đã hứa gì vào sinh nhật tớ không?")]
    old = query_terms(query_text(history), "vi")
    assert "hứa" not in old and "sinh nhật" not in old
    terms = keyword_terms(history, "vi", exclude=name_tokens(["Lạc Dương", "Lâm Vãn"]))
    assert terms[:5] == ["nhớ", "hứa", "sinh", "sinh nhật", "nhật"]
    assert len(terms) == 32
    assert not any(t in ("lạc", "dương", "lâm", "vãn", "lạc dương") or "lâm vãn" in t for t in terms)


async def test_retrieve_ignores_name_only_matches() -> None:
    repo, llm = FakeRepo(MEMORIES), FakeLLM()
    history = [msg(20, "assistant", "Lạc Dương nhìn Lâm Vãn."), msg(21, "user", "Lạc Dương ơi, quán lẩu hôm trước ấy")]
    with_names = await retrieve(repo, llm, make_story(), history, embed_model=None)
    assert {h.memory_id for h in with_names} >= {1, 2, 3}  # tên khớp mọi ký ức
    hits = await retrieve(repo, llm, make_story(), history, embed_model=None, names=["Lạc Dương", "Lâm Vãn"])
    assert [h.memory_id for h in hits] == [3]


async def test_retrieve_limit_and_empty_cases() -> None:
    repo, llm = FakeRepo(MEMORIES), FakeLLM()
    hits = await retrieve(repo, llm, make_story(), HISTORY, embed_model="bge-m3", limit=1)
    assert len(hits) == 1
    assert await retrieve(repo, llm, make_story(id=None), HISTORY, embed_model=None) == []
    assert await retrieve(repo, llm, make_story(), [msg(1, "user", "  ")], embed_model=None) == []
    # Chỉ có stopword: không gọi FTS.
    repo2 = FakeRepo(MEMORIES)
    assert await retrieve(repo2, llm, make_story(), [msg(1, "user", "cậu ơi tớ đây")], embed_model=None) == []
    assert repo2.fts_calls == []


async def test_retrieve_vector_finds_semantic_match_without_keyword_overlap() -> None:
    memories = [item(1, "alpha beta gamma"), item(2, "delta epsilon")]
    repo, llm = FakeRepo(memories), FakeLLM()
    # Từ khoá trùng nhưng sắp xếp khác: FakeRepo FTS so khớp chuỗi con, vector so theo từ.
    hits = await retrieve(repo, llm, make_story(language="en"), [msg(1, "user", "gamma alpha beta")], embed_model="bge-m3")
    assert hits and hits[0].memory_id == 1
    assert all(h.memory_id != 2 for h in hits)  # cosine thấp bị loại
