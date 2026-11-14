"""Phase 3b (docs/phase3.md §10): gợi ý theo yêu cầu, dòng thời gian, lời mở đầu được trích xuất, lỗi dễ
hiểu, tóm tắt theo mốc khúc của cửa sổ lịch sử. FakeLLM / hàm giả, không gọi Ollama thật."""
from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from lyris.chat.service import BUSY_DETAIL, NO_REPLY_TO_SUGGEST, SUGGEST_BUSY_DETAIL, ChatService
from lyris.db.repo import ANY_ACCOUNT, Repo
from lyris.jobs import JobQueue, Worker
from lyris.llm.base import LLMError, LLMOutputError
from lyris.llm.errors import friendly
from lyris.llm.fake import FakeLLM
from lyris.models import ExtractionResult, FactDraft, Message, RelationshipDelta, SceneState
from lyris.prompt.builder import PromptBudget, window_boundaries
from lyris.state import suggest as suggest_module
from lyris.state.service import ModelCatalog, StateService
from tests.test_api_state import app, client, first_story, ok, other_account_story, repo_of, run_jobs, send, settings  # noqa: F401
from tests.test_jobs import FakeExtractor, FakeSummarizer
from tests.test_prompt import assistant, make_card, make_persona, make_story, user

SUGGESTIONS = {"suggestions": ['"Đi ăn kem không?"', 'Tôi cười. "Cậu ghen à?"', "Tôi kéo tay áo cậu ấy.", "Thừa"]}


class SlowSuggester:
    """Hàm gợi ý giả: chờ `gate` (nếu có) rồi trả gợi ý đánh số theo lần gọi."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.gate: asyncio.Event | None = None
        self.started = asyncio.Event()
        self.error: BaseException | None = None

    async def __call__(self, llm: Any, **kw: Any) -> list[str]:
        self.calls.append(kw)
        self.started.set()
        if self.gate is not None:
            await self.gate.wait()
        if self.error is not None:
            raise self.error
        n = len(self.calls)
        return [f"Gợi ý {n}.{i}" for i in (1, 2, 3)]


def chat_of(app: FastAPI) -> ChatService:  # noqa: F811
    chat: ChatService = app.state.chat
    return chat


# ---------------------------------------------------------------------------- POST /suggestions


async def test_suggestions_on_demand_and_replace(app: FastAPI, client: httpx.AsyncClient) -> None:  # noqa: F811
    fake = SlowSuggester()
    chat_of(app).suggester = fake
    sid = await first_story(client)
    # Story vừa có lời mở đầu: nhân vật nói cuối nên gợi ý được ngay.
    reply = await send(client, sid)
    assert (await ok(await client.get(f"/api/stories/{sid}/extras")))["suggestions"] == []
    got = await ok(await client.post(f"/api/stories/{sid}/suggestions"))
    assert got == {"items": ["Gợi ý 1.1", "Gợi ý 1.2", "Gợi ý 1.3"]}
    call = fake.calls[0]
    assert call["model"] == "gemma4:12b" and call["num_ctx"] == 8192 and call["avoid"] == []
    assert call["history"][-1].id == reply["id"]
    assert (await ok(await client.get(f"/api/stories/{sid}/extras")))["suggestions"] == got["items"]

    # "Gợi ý khác": thay gợi ý cũ (một event duy nhất), gợi ý cũ được đưa vào `avoid`.
    again = await ok(await client.post(f"/api/stories/{sid}/suggestions"))
    assert again["items"][0] == "Gợi ý 2.1" and fake.calls[1]["avoid"] == got["items"]
    kinds = [e.kind for e in repo_of(app).message_state_events(reply["id"])]
    assert kinds.count("suggestions") == 1

    # Trích xuất chạy sau đó không xoá gợi ý theo yêu cầu.
    await run_jobs(app)
    assert (await ok(await client.get(f"/api/stories/{sid}/extras")))["suggestions"] == again["items"]

    # Người chơi trả lời: gợi ý biến mất.
    await send(client, sid, '"Đi thôi."')
    assert (await ok(await client.get(f"/api/stories/{sid}/extras")))["suggestions"] == []


async def test_suggestions_real_module_with_fake_llm(app: FastAPI, client: httpx.AsyncClient) -> None:  # noqa: F811
    llm: FakeLLM = app.state.llm
    llm.json_replies = [SUGGESTIONS]
    sid = await first_story(client)
    got = await ok(await client.post(f"/api/stories/{sid}/suggestions"))
    assert got == {"items": ["Đi ăn kem không?", 'Tôi cười. "Cậu ghen à?"', "Tôi kéo tay áo cậu ấy."]}
    call = llm.calls[-1]
    assert call["schema"] == suggest_module.SCHEMA and "maxLength" not in json.dumps(call["schema"])
    assert call["options"] == {"num_ctx": 8192, "num_predict": suggest_module.NUM_PREDICT, "temperature": 0.8}


async def test_suggestions_need_character_last(app: FastAPI, client: httpx.AsyncClient) -> None:  # noqa: F811
    chat_of(app).suggester = SlowSuggester()
    sid = await first_story(client)
    llm: FakeLLM = app.state.llm
    llm.error = LLMError("hỏng", kind="server")
    resp = await client.post(f"/api/stories/{sid}/messages", json={"content": '"Chào."'})
    assert resp.status_code == 200 and "event: error" in resp.text  # lượt người chơi vẫn được lưu
    resp = await client.post(f"/api/stories/{sid}/suggestions")
    assert resp.status_code == 409 and resp.json()["detail"] == NO_REPLY_TO_SUGGEST


async def test_suggestions_busy_both_ways(app: FastAPI, client: httpx.AsyncClient) -> None:  # noqa: F811
    chat = chat_of(app)
    fake = SlowSuggester()
    chat.suggester = fake
    sid = await first_story(client)

    # Story đang sinh câu trả lời: 409.
    lock = chat._lock(sid)
    await lock.acquire()
    try:
        resp = await client.post(f"/api/stories/{sid}/suggestions")
        assert resp.status_code == 409 and resp.json()["detail"] == BUSY_DETAIL
    finally:
        lock.release()

    # Đang nghĩ gợi ý: worker nhường model; gửi tin / gợi ý lần nữa -> 409 với câu riêng.
    fake.gate = asyncio.Event()
    jobs: JobQueue = app.state.jobs
    pending = asyncio.create_task(client.post(f"/api/stories/{sid}/suggestions"))
    await asyncio.wait_for(fake.started.wait(), 5)
    assert jobs.streaming and chat.is_busy(sid)
    resp = await client.post(f"/api/stories/{sid}/messages", json={"content": '"Chào."'})
    assert resp.status_code == 409 and resp.json()["detail"] == SUGGEST_BUSY_DETAIL
    resp = await client.post(f"/api/stories/{sid}/suggestions")
    assert resp.status_code == 409 and resp.json()["detail"] == SUGGEST_BUSY_DETAIL
    fake.gate.set()
    assert (await pending).status_code == 200
    assert not jobs.streaming and not chat.is_busy(sid)


async def test_suggestions_error_is_plain_with_technical_detail(app: FastAPI, client: httpx.AsyncClient) -> None:  # noqa: F811
    fake = SlowSuggester()
    fake.error = LLMError("Không kết nối được Ollama ở http://127.0.0.1:11434.", kind="connect")
    chat_of(app).suggester = fake
    sid = await first_story(client)
    resp = await client.post(f"/api/stories/{sid}/suggestions")
    assert resp.status_code == 502
    body = resp.json()
    assert set(body) == {"detail", "technical"}
    assert "Ollama" not in body["detail"] and "model" not in body["detail"].lower()
    assert "Ollama" in body["technical"]
    assert not chat_of(app).is_busy(sid)
    fake.error = LLMOutputError("Model không trả gợi ý nào dùng được.")
    body = (await client.post(f"/api/stories/{sid}/suggestions")).json()
    assert body["detail"] == "Chưa nghĩ ra được gợi ý. Hãy thử lại." and "Model" in body["technical"]


async def test_suggestions_other_account_is_404(app: FastAPI, client: httpx.AsyncClient) -> None:  # noqa: F811
    chat_of(app).suggester = SlowSuggester()
    other_sid, _ = other_account_story(repo_of(app))
    assert (await client.post(f"/api/stories/{other_sid}/suggestions")).status_code == 404
    assert (await client.post("/api/stories/9999/suggestions")).status_code == 404
    assert repo_of(app).state_events(other_sid, kinds=("suggestions",)) == []


async def test_edit_clears_suggestions(app: FastAPI, client: httpx.AsyncClient) -> None:  # noqa: F811
    chat_of(app).suggester = SlowSuggester()
    sid = await first_story(client)
    reply = await send(client, sid)
    await ok(await client.post(f"/api/stories/{sid}/suggestions"))
    await ok(await client.patch(f"/api/messages/{reply['id']}", json={"content": "Anh lắc đầu."}))
    assert (await ok(await client.get(f"/api/stories/{sid}/extras")))["suggestions"] == []


def test_repo_replace_suggestions_only_on_last_character_message(seeded_repo: Repo) -> None:
    story = seeded_repo.list_stories(account_id=ANY_ACCOUNT)[0]
    assert story.id is not None
    opening = seeded_repo.active_messages(story.id)[0]
    assert opening.id is not None
    assert seeded_repo.replace_suggestions(opening.id, ["a", "b"])
    assert seeded_repo.replace_suggestions(opening.id, ["c"])
    events = seeded_repo.state_events(story.id, kinds=("suggestions",))
    assert [e.payload for e in events] == [{"items": ["c"]}]
    seeded_repo.insert_message(
        Message(story_id=story.id, turn_index=1, role="user", mode="story", raw_content="x", visible_content="x")
    )
    assert not seeded_repo.replace_suggestions(opening.id, ["d"])


def test_suggest_validate_and_prompt() -> None:
    items = suggest_module.validate(
        {"suggestions": ["1. Đi thôi", "  ", "đi thôi!", '"Lặp lại"', "Cũ", "- Mới", "Thêm"]},
        player_texts=["Lặp lại"],
        avoid=["Cũ"],
    )
    assert items == ["Đi thôi", "Mới", "Thêm"]
    assert suggest_module.validate(None) == []
    history = [assistant(0, "Chào. [Thought: bí mật]"), user(1, "*Tớ cười.* \"Chào cậu.\""), assistant(2, "Anh gật đầu.")]
    history[0] = history[0].model_copy(update={"visible_content": "Chào."})
    msgs = suggest_module.build_messages(
        card=make_card(), persona=make_persona(), story=make_story(), history=history,
        scene=SceneState(location="Sân bóng"), summary="Hai người quen nhau từ nhỏ.", avoid=["Gợi ý cũ"],
    )
    text = msgs[1].content
    assert "bí mật" not in text and "Lâm Vãn: *Tớ cười.*" in text and "Lạc Dương: Anh gật đầu." in text
    assert 'Lâm Vãn xưng "tớ", gọi Lạc Dương là "cậu"' in text
    assert 'Viết ở ngôi "tôi"' in text and "tối đa 25 từ" in text and "3 hướng khác nhau" in text
    assert "Cảnh hiện tại: Sân bóng." in text and "Chuyện trước đó: Hai người quen nhau từ nhỏ." in text
    assert "- Gợi ý cũ" in text
    dm = suggest_module.build_messages(
        card=make_card(), persona=make_persona(), story=make_story(mode="dm"),
        history=[assistant(0, "Ngủ chưa?").model_copy(update={"mode": "dm"})],
    )[1].content
    assert "tin nhắn ngắn" in dm and 'Viết ở ngôi "tôi"' not in dm
    en = suggest_module.build_messages(
        card=make_card(), persona=make_persona(), story=make_story(language="en"), history=history
    )
    assert "English" in en[0].content and "first person" in en[1].content


async def test_suggest_replies_errors() -> None:
    history = [assistant(0, "Chào.")]
    kw: dict[str, Any] = dict(model="m", num_ctx=8192, card=make_card(), persona=make_persona(), story=make_story())
    with pytest.raises(LLMOutputError):
        await suggest_module.suggest_replies(FakeLLM(json_replies=[{"suggestions": []}]), history=history, **kw)
    with pytest.raises(ValueError):
        await suggest_module.suggest_replies(FakeLLM(json_replies=[SUGGESTIONS]), history=[user(1, "x")], **kw)


# ---------------------------------------------------------------------------- lỗi dễ hiểu


def test_friendly_errors_never_mention_ollama_or_model() -> None:
    for kind in ("connect", "timeout", "missing_model", "server", "output", "unknown"):
        for action in ("reply", "suggest", "draft", "preview"):
            detail, technical = friendly(LLMError("Ollama chưa có model x", kind=kind), action)  # type: ignore[arg-type]
            assert "Ollama" not in detail and "model" not in detail.lower()
            assert technical == "Ollama chưa có model x"
    detail, technical = friendly(RuntimeError("boom"), "reply")
    assert detail == "Nhân vật chưa trả lời được. Hãy thử lại." and technical == "RuntimeError: boom"


# ---------------------------------------------------------------------------- GET /timeline


class TimelineExtractor(FakeExtractor):
    async def __call__(self, llm: Any, **kw: Any) -> ExtractionResult:
        self.calls.append(kw)
        reply: Message = kw["turn"][-1]
        if reply.turn_index == 0:
            return ExtractionResult(scene=SceneState(location="Sân bóng", time="Chiều"), memory="Lạc Dương đứng đợi.")
        if reply.turn_index == 2:
            return ExtractionResult(
                relationship_delta=RelationshipDelta(affection=2, fear=-1),
                memory="Hai người đi ăn kem.",
                facts=[FactDraft(subject="Lâm Vãn", text="Lâm Vãn thích kem dâu.")],
            )
        return ExtractionResult()  # lượt không có gì: không vào dòng thời gian


async def test_timeline(app: FastAPI, client: httpx.AsyncClient) -> None:  # noqa: F811
    worker: Worker = app.state.worker
    worker.extractor = TimelineExtractor()
    sid = await first_story(client)
    assert await ok(await client.get(f"/api/stories/{sid}/timeline")) == []
    first = await send(client, sid)
    await send(client, sid, '"Nữa."')
    assert await ok(await client.post(f"/api/stories/{sid}/state/rebuild")) == {"queued": 1}  # lời mở đầu
    await run_jobs(app)
    opening = repo_of(app).active_messages(sid)[0]
    entries = await ok(await client.get(f"/api/stories/{sid}/timeline"))
    assert [e["turn_index"] for e in entries] == [0, 2]
    assert entries[0] == {
        "turn_index": 0,
        "message_id": opening.id,
        "mode": "story",
        "created_at": opening.created_at,
        "memory": "Lạc Dương đứng đợi.",
        "facts": [],
        "delta": {},
        "scene": {"location": "Sân bóng", "time": "Chiều"},
    }
    assert entries[1]["message_id"] == first["id"] and entries[1]["delta"] == {"affection": 2, "fear": -1}
    assert entries[1]["facts"] == ["Lâm Vãn thích kem dâu."] and entries[1]["scene"] is None
    assert list(entries[1]["delta"]) == ["affection", "fear"]  # thứ tự EMOTION_KEYS

    other_sid, _ = other_account_story(repo_of(app))
    assert (await client.get(f"/api/stories/{other_sid}/timeline")).status_code == 404
    assert (await client.get("/api/stories/9999/timeline")).status_code == 404


# ---------------------------------------------------------------------------- lời mở đầu (lượt 0)


async def test_new_story_extracts_its_opening(app: FastAPI, client: httpx.AsyncClient) -> None:  # noqa: F811
    worker: Worker = app.state.worker
    worker.extractor = TimelineExtractor()
    stories = await ok(await client.get("/api/stories"))
    detail = await ok(await client.get(f"/api/stories/{stories[0]['id']}"))
    created = await ok(
        await client.post("/api/stories", json={"card_id": detail["card"]["id"], "persona_id": detail["persona"]["id"]})
    )
    sid = created["id"]
    # App mở story mới ngay sau khi tạo: nó thành story đang chơi (prefill sau job lời mở đầu là của nó).
    assert worker._focus == sid
    jobs = repo_of(app).list_jobs(sid)
    opening = repo_of(app).active_messages(sid)[0]
    assert [(j.kind, j.message_id) for j in jobs] == [("extract", opening.id)]
    extras = await ok(await client.get(f"/api/stories/{sid}/extras"))
    assert extras["pending"] is True and extras["unprocessed_turns"] == 0
    await run_jobs(app)
    extras = await ok(await client.get(f"/api/stories/{sid}/extras"))
    assert extras["location"] == "Sân bóng" and extras["in_world_time"] == "Chiều"
    assert [m["turn_index"] for m in extras["memories"]] == [0]
    # Không có thay đổi cảm xúc cho lượt 0 (chip ở hub chưa hiện).
    assert repo_of(app).state_events(sid, kinds=("relationship_delta",)) == []
    card = next(s for s in await ok(await client.get("/api/stories")) if s["id"] == sid)
    assert card["dominant_emotion"] is None and card["location"] == "Sân bóng"
    # Lượt đầu tiên của người chơi đã có cảnh trong prompt.
    await send(client, sid)
    llm: FakeLLM = app.state.llm
    assert "- Cảnh hiện tại: Sân bóng, Chiều." in llm.calls[-1]["messages"][-1].content


async def test_story_without_opening_queues_nothing(app: FastAPI, client: httpx.AsyncClient) -> None:  # noqa: F811
    stories = await ok(await client.get("/api/stories"))
    detail = await ok(await client.get(f"/api/stories/{stories[0]['id']}"))
    created = await ok(
        await client.post(
            "/api/stories",
            json={"card_id": detail["card"]["id"], "persona_id": detail["persona"]["id"], "greeting_index": -1},
        )
    )
    assert repo_of(app).list_jobs(created["id"]) == []


# ---------------------------------------------------------------------------- tóm tắt theo mốc khúc


LONG_REPLY = "[Thought: Lại bày trò.]\nLạc Dương khẽ cười. " + "Anh nhìn cô rất lâu, không nói gì. " * 18


async def test_summary_follows_chunk_boundaries_and_block_c_moves_with_window(seeded_repo: Repo) -> None:
    budget = PromptBudget(num_ctx=6144)
    llm = FakeLLM(replies=[LONG_REPLY])
    state = StateService(seeded_repo, llm, catalog=ModelCatalog(None), budget=budget)
    queue = JobQueue(seeded_repo, state)
    summarizer = FakeSummarizer()
    worker = Worker(seeded_repo, queue, state, llm, budget=budget, extractor=FakeExtractor(), summarizer=summarizer)
    chat = ChatService(seeded_repo, llm, budget=budget, state=state, jobs=queue)
    story = seeded_repo.list_stories(account_id=ANY_ACCOUNT)[0]
    assert story.id is not None
    sid = story.id

    seen: list[tuple[int, str, int | None]] = []
    for i in range(40):
        async for _ in chat.send(sid, f'*Tớ kéo tay áo cậu ấy.* "Lượt {i} nè, kể tiếp đi mà."'):
            pass
        reply = seeded_repo.active_messages(sid)[-1]
        snap = reply.prompt_snapshot
        assert snap is not None
        system = str(llm.calls[-1]["messages"][0].content)
        seen.append((snap["window_start_turn"], system, snap["summary_upto_turn"]))
        await worker.run_until_idle()

    starts = [s for s, _, _ in seen]
    assert max(starts) > 0 and starts == sorted(starts)
    trimmed_starts = [s for s in starts if s > 0]
    assert len(set(trimmed_starts)) * 2 <= len(trimmed_starts)  # mỗi điểm bắt đầu giữ ít nhất ~2 lượt
    for (s1, sys1, _), (s2, sys2, _) in zip(seen, seen[1:], strict=False):
        if s1 == s2:
            assert sys1 == sys2  # cửa sổ đứng yên thì khối C (system) giữ nguyên từng byte
    # Khi đã cắt, tóm tắt đã sẵn đúng tới ngay trước cửa sổ (được làm trước khi khúc rơi ra).
    trimmed = [(s, upto) for s, _, upto in seen if s > 0]
    assert trimmed and all(upto == s - 1 for s, upto in trimmed)
    # Mỗi event tóm tắt kết thúc ở một mốc khúc (trước mốc một lượt).
    history = seeded_repo.active_messages(sid)
    card, persona = seeded_repo.get_card(story.card_id, account_id=ANY_ACCOUNT), seeded_repo.get_persona(story.persona_id, account_id=ANY_ACCOUNT)
    marks = set(window_boundaries(card, persona, seeded_repo.get_story(sid, account_id=ANY_ACCOUNT), history, budget=budget))
    uptos = [p.upto_turn for p in state.summary_points(seeded_repo.get_story(sid, account_id=ANY_ACCOUNT))]
    assert uptos and all(u + 1 in marks for u in uptos)
    # Tóm tắt chỉ chạy khi cần (không phải sau mỗi lượt).
    assert len(summarizer.calls) < len(seen) // 2
