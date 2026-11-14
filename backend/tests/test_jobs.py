"""Phase 3: hàng đợi job nền, worker, StateService và các móc trong ChatService (docs/phase3.md §4).

Không bao giờ gọi Ollama thật: chat dùng FakeLLM; trích xuất, tóm tắt, embed là hàm giả tiêm vào worker.
Worker chạy tất định bằng `run_until_idle()`; test ưu tiên lượt chat thì chạy vòng lặp thật (`start()`).
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

import httpx
import pytest

from lyris.chat.service import ChatEvent, ChatService
from lyris.db.repo import ANY_ACCOUNT, Repo
from lyris.jobs import JobQueue, Worker
from lyris.jobs import worker as worker_module
from lyris.jobs.worker import normalize_fact, pack_embedding, unpack_embedding
from lyris.llm.base import LLMError
from lyris.llm.fake import FakeLLM
from lyris.models import (
    DEFAULT_INITIAL_RELATIONSHIP,
    ExtractionResult,
    FactDraft,
    GenStats,
    Message,
    RelationshipDelta,
    SceneState,
    Story,
)
from lyris.state.service import ModelCatalog, StateService, window_start_turn

REPLIES = ["Lạc Dương mỉm cười. [Thought: Vui.]", "Anh gật đầu.", "Anh quay đi.", "Anh lại cười."]


# ---------------------------------------------------------------------------- giả lập phần gọi model


@dataclass
class FakeExtractor:
    """Trả ExtractionResult theo lượt; `errors` raise lần lượt trước khi trả kết quả."""

    delta: dict[str, int] = field(default_factory=lambda: {"affection": 5})
    errors: list[BaseException] = field(default_factory=list)
    gate: asyncio.Event | None = None
    calls: list[dict[str, Any]] = field(default_factory=list)
    started: asyncio.Event = field(default_factory=asyncio.Event)
    cancelled: int = 0
    facts: list[FactDraft] = field(default_factory=list)

    async def __call__(self, llm: Any, **kw: Any) -> ExtractionResult:
        self.calls.append(kw)
        self.started.set()
        if self.gate is not None:
            try:
                await self.gate.wait()
            except asyncio.CancelledError:
                self.cancelled += 1
                raise
        if self.errors:
            raise self.errors.pop(0)
        turn: list[Message] = kw["turn"]
        reply = turn[-1]
        return ExtractionResult(
            relationship_delta=RelationshipDelta(**self.delta),
            scene=SceneState(location=f"Nơi {reply.turn_index}", time=None),
            memory=f"Sự việc lượt {reply.turn_index}: {reply.visible_content[:20]}",
            memory_importance=4,
            facts=list(self.facts),
            suggestions=[f"Gợi ý {reply.turn_index}", "Hai", "Ba"],
        )


@dataclass
class FakeSummarizer:
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def __call__(self, llm: Any, **kw: Any) -> str:
        self.calls.append(kw)
        turns = [m.turn_index for m in kw["messages"]]
        return f"Tóm tắt tới lượt {turns[-1]} (trước: {kw['previous'] or 'không'})"


@dataclass
class FakeEmbedder:
    calls: list[tuple[str, list[str]]] = field(default_factory=list)

    async def __call__(self, model: str, texts: list[str]) -> list[list[float]]:
        self.calls.append((model, list(texts)))
        return [[float(len(t)), 1.0, 0.5] for t in texts]


def lister(names: list[str] | None, *, fail: bool = False) -> Callable[[], Awaitable[list[str]]]:
    async def _list() -> list[str]:
        if fail:
            raise LLMError("Ollama tắt")
        return list(names or [])

    return _list


@dataclass
class Env:
    repo: Repo
    llm: FakeLLM
    state: StateService
    queue: JobQueue
    worker: Worker
    chat: ChatService
    extractor: FakeExtractor
    summarizer: FakeSummarizer
    embedder: FakeEmbedder

    @property
    def story(self) -> Story:
        return self.repo.list_stories(account_id=ANY_ACCOUNT)[0]

    @property
    def sid(self) -> int:
        sid = self.story.id
        assert sid is not None
        return sid


def make_env(
    repo: Repo, *, models: list[str] | None = None, extractor: FakeExtractor | None = None, **worker_kw: Any
) -> Env:
    llm = FakeLLM(replies=REPLIES)
    state = StateService(repo, llm, embed_model="bge-m3", catalog=ModelCatalog(lister(models) if models is not None else None))
    queue = JobQueue(repo, state)
    ex, su, em = extractor or FakeExtractor(), FakeSummarizer(), FakeEmbedder()
    worker = Worker(repo, queue, state, llm, extractor=ex, summarizer=su, embedder=em, poll_interval=0.05, **worker_kw)
    chat = ChatService(repo, llm, state=state, jobs=queue)
    return Env(repo, llm, state, queue, worker, chat, ex, su, em)


@pytest.fixture
def env(seeded_repo: Repo) -> Env:
    return make_env(seeded_repo)


async def drain(events: AsyncIterator[ChatEvent]) -> list[ChatEvent]:
    return [e async for e in events]


async def send(env: Env, text: str = '"Chào cậu."') -> Message:
    events = await drain(env.chat.send(env.sid, text))
    done = [e for e in events if e.name == "done"]
    assert done, events
    return env.repo.get_message(done[0].data["message"]["id"], account_id=ANY_ACCOUNT)


async def until(cond: Callable[[], bool], timeout: float = 2.0) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while not cond():
        if asyncio.get_running_loop().time() > deadline:
            raise AssertionError("Hết thời gian chờ điều kiện")
        await asyncio.sleep(0.005)


# ---------------------------------------------------------------------------- luồng chính


async def test_turn_enqueues_extract_and_worker_writes_state(env: Env) -> None:
    initial = env.state.initial(env.story)
    reply = await send(env)
    jobs = env.repo.list_jobs(env.sid)
    assert [(j.kind, j.status, j.message_id) for j in jobs] == [("extract", "queued", reply.id)]
    assert env.queue.pending(env.sid)
    extras = await env.state.extras(env.story)
    # Lời mở đầu của story seed (tạo thẳng bằng repo, không qua API) chưa được trích xuất: 1 lượt chưa ghi nhớ.
    assert extras.pending and extras.unprocessed_turns == 1
    assert extras.relationship is not None and extras.relationship.affection == initial.affection

    assert await env.worker.run_until_idle() == 1
    call = env.extractor.calls[0]
    assert call["model"] == env.story.model_name and call["num_ctx"] == 8192
    assert [m.role for m in call["turn"]] == ["user", "assistant"] and call["turn"][-1].id == reply.id
    assert call["before"] == initial and call["summary"] is None and call["known_facts"] == []
    job = env.repo.list_jobs(env.sid)[0]
    assert job.status == "done" and job.attempts == 1

    extras = await env.state.extras(env.story)
    assert extras.relationship is not None and extras.relationship.affection == min(100, initial.affection + 5)
    # Phase 3b: trích xuất không còn ghi gợi ý (chỉ sinh khi người chơi bấm "Nhận gợi ý").
    assert extras.location == f"Nơi {reply.turn_index}" and extras.suggestions == []
    assert [m.kind for m in extras.memories] == ["memory"] and extras.memories[0].importance == 4
    assert not extras.pending and extras.unprocessed_turns == 1
    dominant, location = env.state.hub_info(env.story)
    assert dominant is not None and location == f"Nơi {reply.turn_index}"


async def test_second_turn_prompt_uses_state_and_snapshot(env: Env) -> None:
    first = await send(env)
    assert first.prompt_snapshot is not None
    assert "state" in first.prompt_snapshot and first.prompt_snapshot["window_start_turn"] == 0
    await env.worker.run_until_idle()
    second = await send(env, '"Đi đâu thế?"')
    snap = second.prompt_snapshot
    assert snap is not None and snap["state"] is not None
    assert snap["state"]["scene"] == {"location": f"Nơi {first.turn_index}", "time": None}
    # Gợi ý chỉ dành cho lượt người chơi chưa trả lời: sau lượt mới, gợi ý cũ không còn.
    extras = await env.state.extras(env.story)
    assert extras.suggestions == []


async def test_regenerate_and_select_variant_roll_state_back(env: Env) -> None:
    initial = env.state.initial(env.story).affection
    first = await send(env)
    await env.worker.run_until_idle()
    assert (await env.state.extras(env.story)).relationship.affection == initial + 5  # type: ignore[union-attr]

    env.extractor.delta = {"affection": -5}
    assert first.id is not None
    events = await drain(env.chat.regenerate(first.id))
    new = env.repo.get_message(next(e for e in events if e.name == "done").data["message"]["id"], account_id=ANY_ACCOUNT)
    # Variant mới active: hiệu ứng của variant cũ biến mất ngay, chưa cần worker.
    extras = await env.state.extras(env.story)
    assert extras.relationship.affection == initial and extras.memories == []  # type: ignore[union-attr]
    assert extras.suggestions == []
    await env.worker.run_until_idle()
    assert (await env.state.extras(env.story)).relationship.affection == initial - 5  # type: ignore[union-attr]
    # Prompt của bản regenerate không chứa state của variant cũ (tính tới lượt trước đó).
    assert new.prompt_snapshot is not None and new.prompt_snapshot["state"]["scene"] is None

    env.chat.select_variant(new.id or 0, 0)
    extras = await env.state.extras(env.story)
    assert extras.relationship.affection == initial + 5  # type: ignore[union-attr]
    assert [m.message_id for m in extras.memories] == [first.id]
    assert not env.queue.pending(env.sid)  # variant cũ đã trích xuất rồi: không xếp lại


async def test_regenerate_cancels_queued_job_and_flip_back_requeues(env: Env) -> None:
    first = await send(env)
    assert first.id is not None
    await drain(env.chat.regenerate(first.id))
    jobs = {j.message_id: j for j in env.repo.list_jobs(env.sid)}
    assert jobs[first.id].status == "cancelled"
    await env.worker.run_until_idle()
    assert len(env.extractor.calls) == 1  # chỉ variant mới
    env.chat.select_variant(first.id, 0)
    assert env.queue.pending(env.sid)  # variant cũ chưa từng được trích xuất -> xếp lại
    await env.worker.run_until_idle()
    assert env.extractor.calls[-1]["turn"][-1].id == first.id


async def test_aborted_turn_is_not_extracted(env: Env) -> None:
    env.llm.delay = 0.01
    gen = env.chat.send(env.sid, '"Ơi?"')
    async for event in gen:
        if event.name == "delta":
            break
    await gen.aclose()
    saved = env.repo.active_messages(env.sid)[-1]
    assert saved.role == "assistant" and saved.gen_stats is not None and saved.gen_stats.aborted
    assert env.repo.list_jobs(env.sid) == []
    # Lượt bị Dừng không tính là "chưa ghi nhớ": drawer không mời "Đọc lại story", rebuild bỏ qua.
    # (Chỉ còn lời mở đầu lượt 0 của story seed là chưa trích xuất.)
    assert env.repo.unprocessed_turns(env.sid) == 1
    assert [m.turn_index for m in env.repo.messages_needing_extract(env.sid)] == [0]
    assert env.queue.rebuild(env.sid) == 1
    assert env.queue.turn_saved(saved) is None


async def test_edit_assistant_resets_and_reextracts(env: Env) -> None:
    reply = await send(env)
    await env.worker.run_until_idle()
    assert reply.id is not None
    env.chat.edit_message(reply.id, "Anh im lặng rất lâu.")
    assert env.repo.message_state_events(reply.id) == []
    assert env.repo.list_memories(env.sid) == []
    assert env.queue.pending(env.sid)
    await env.worker.run_until_idle()
    assert env.extractor.calls[-1]["turn"][-1].raw_content == "Anh im lặng rất lâu."
    assert [m.text for m in env.repo.list_memories(env.sid)][0].startswith("Sự việc lượt")
    # Sửa mà nội dung giữ nguyên: không trích xuất lại.
    before = len(env.extractor.calls)
    env.chat.edit_message(reply.id, "Anh im lặng rất lâu.")
    assert not env.queue.pending(env.sid) and len(env.extractor.calls) == before
    # Sửa lượt người chơi: không đụng state.
    user = env.repo.active_messages(env.sid)[-2]
    env.chat.edit_message(user.id or 0, "Xin chào")
    assert not env.queue.pending(env.sid) and env.repo.state_events(env.sid)


async def test_delete_removes_state_and_jobs(env: Env) -> None:
    reply = await send(env)
    await env.worker.run_until_idle()
    second = await send(env, '"Rồi sao?"')
    assert second.id is not None and reply.id is not None
    env.chat.delete_from(second.id)
    assert env.repo.list_jobs(env.sid, statuses=("queued",)) == []
    assert all(e.message_id == reply.id for e in env.repo.state_events(env.sid))
    env.chat.delete_from(reply.id)
    assert env.repo.state_events(env.sid) == [] and env.repo.list_memories(env.sid) == []
    extras = await env.state.extras(env.story)
    assert extras.relationship is not None and extras.relationship.model_dump(exclude={"directive"}) == env.state.initial(env.story).model_dump()


async def test_fact_dedupe_and_extract_model_override(seeded_repo: Repo) -> None:
    ex = FakeExtractor(facts=[FactDraft(subject="Lâm Vãn", text="Lâm Vãn thích trà sữa."), FactDraft(subject="", text="  ")])
    env = make_env(seeded_repo, extractor=ex, extract_model="nhe:1b")
    await send(env)
    await env.worker.run_until_idle()
    ex.facts = [FactDraft(subject="Lâm Vãn", text="lâm vãn THÍCH trà sữa!"), FactDraft(subject="Lạc Dương", text="Lạc Dương sợ ma.")]
    await send(env, '"Thật à?"')
    await env.worker.run_until_idle()
    facts = [m.text for m in env.repo.list_memories(env.sid, kind="fact")]
    assert sorted(facts) == ["Lâm Vãn thích trà sữa.", "Lạc Dương sợ ma."]
    assert env.extractor.calls[-1]["known_facts"] == ["Lâm Vãn thích trà sữa."]
    assert {c["model"] for c in ex.calls} == {"nhe:1b"}
    assert normalize_fact(" Lâm  Vãn, thích TRÀ sữa. ") == "lâm vãn thích trà sữa"


# ---------------------------------------------------------------------------- lỗi và thử lại


async def test_bad_json_retried_once(env: Env) -> None:
    env.extractor.errors = [LLMError("Model trả JSON hỏng")]
    await send(env)
    await env.worker.run_until_idle()
    job = env.repo.list_jobs(env.sid)[0]
    assert job.status == "done" and job.attempts == 2 and len(env.extractor.calls) == 2


async def test_bad_json_twice_fails(env: Env) -> None:
    env.extractor.errors = [ValueError("hỏng 1"), ValueError("hỏng 2")]
    await send(env)
    await env.worker.run_until_idle()
    job = env.repo.list_jobs(env.sid)[0]
    assert job.status == "failed" and job.attempts == 2 and job.error == "hỏng 2"
    assert env.repo.state_events(env.sid) == []
    assert env.repo.unprocessed_turns(env.sid) == 2  # mời dựng lại (lượt này + lời mở đầu của story seed)


async def test_connection_error_fails_without_retry(env: Env) -> None:
    try:
        raise httpx.ConnectError("refused")
    except httpx.ConnectError as exc:
        err = LLMError("Không kết nối được Ollama")
        err.__cause__ = exc
    env.extractor.errors = [err]
    await send(env)
    await env.worker.run_until_idle()
    job = env.repo.list_jobs(env.sid)[0]
    assert job.status == "failed" and job.attempts == 1 and "Không kết nối" in (job.error or "")


async def test_worker_loop_survives_errors_and_recovers_running(env: Env) -> None:
    first = await send(env)
    second = await send(env, '"Nữa."')
    env.extractor.errors = [RuntimeError("bất ngờ"), RuntimeError("bất ngờ")]
    # Job "running" còn sót từ lần chạy trước -> quay về hàng đợi khi khởi động.
    env.repo.conn.execute("UPDATE jobs SET status = 'running' WHERE message_id = ?", (first.id,))
    await env.worker.start()
    try:
        await until(lambda: not env.queue.pending(env.sid))
    finally:
        await env.worker.stop()
    status = {j.message_id: j.status for j in env.repo.list_jobs(env.sid)}
    assert status == {first.id: "failed", second.id: "done"}
    assert not env.worker.running


async def test_job_for_deleted_or_inactive_message_is_cancelled(env: Env) -> None:
    reply = await send(env)
    assert reply.id is not None
    # Đổi variant thẳng trong DB (không qua ChatService): worker tự phát hiện lúc chạy.
    env.repo.add_variant(reply.model_copy(update={"raw_content": "khác"}))
    await env.worker.run_until_idle()
    assert env.repo.list_jobs(env.sid)[0].status == "cancelled" and env.extractor.calls == []


# ---------------------------------------------------------------------------- ưu tiên lượt chat


async def test_chat_preempts_running_job_without_counting_attempt(env: Env) -> None:
    gate = asyncio.Event()
    env.extractor.gate = gate
    reply = await send(env)
    await env.worker.start()
    try:
        await asyncio.wait_for(env.extractor.started.wait(), 2)
        assert env.worker.current_job is not None
        env.queue.generation_started(env.sid)
        await until(lambda: env.repo.list_jobs(env.sid)[0].status == "queued")
        job = env.repo.list_jobs(env.sid)[0]
        assert job.attempts == 0 and env.extractor.cancelled == 1
        # Trong lúc stream: không bắt đầu job mới.
        env.extractor.started.clear()
        await asyncio.sleep(0.15)
        assert not env.extractor.started.is_set() and len(env.extractor.calls) == 1
        gate.set()
        env.queue.generation_finished(env.sid)
        await until(lambda: env.repo.list_jobs(env.sid)[0].status == "done")
    finally:
        await env.worker.stop()
    job = env.repo.list_jobs(env.sid)[0]
    assert job.attempts == 1 and job.message_id == reply.id and len(env.extractor.calls) == 2


async def test_chat_service_signals_stream_start_and_end(env: Env) -> None:
    seen: list[str] = []

    class Spy:
        def on_generation_started(self, story_id: int) -> None:
            seen.append(f"start {story_id} streaming={env.queue.streaming}")

        def on_generation_finished(self, story_id: int) -> None:
            seen.append(f"end {story_id} streaming={env.queue.streaming}")

        def on_messages_changed(self, story_id: int) -> None:
            seen.append("changed")

        def on_message_reset(self, message_id: int, story_id: int) -> None:
            seen.append("reset")

    env.queue.attach(Spy())
    await send(env)
    assert seen == [f"start {env.sid} streaming=True", f"end {env.sid} streaming=False"]
    assert not env.queue.streaming
    # Lỗi khi dựng prompt (respond khi không có lượt người chơi chờ): vẫn nhả cờ stream.
    with pytest.raises(Exception):
        await drain(env.chat.respond(env.sid))
    assert not env.queue.streaming


async def test_inflight_job_cancelled_when_message_becomes_inactive(env: Env) -> None:
    gate = asyncio.Event()
    env.extractor.gate = gate
    reply = await send(env)
    await env.worker.start()
    try:
        await asyncio.wait_for(env.extractor.started.wait(), 2)
        env.repo.add_variant(reply.model_copy(update={"raw_content": "khác"}))
        env.queue.messages_changed(env.sid)
        await until(lambda: env.repo.list_jobs(env.sid)[0].status == "cancelled")
    finally:
        await env.worker.stop()
    assert env.repo.state_events(env.sid) == [] and env.extractor.cancelled == 1


async def test_worker_stop_requeues_inflight(env: Env) -> None:
    env.extractor.gate = asyncio.Event()
    await send(env)
    await env.worker.start()
    await asyncio.wait_for(env.extractor.started.wait(), 2)
    await env.worker.stop()
    job = env.repo.list_jobs(env.sid)[0]
    assert job.status == "queued" and job.attempts == 0


# ---------------------------------------------------------------------------- dựng lại, tóm tắt, embed


def _add_turns(repo: Repo, story: Story, count: int, *, snapshot: dict[str, Any] | None = None) -> list[Message]:
    """Thêm `count` cặp (user, assistant) thẳng vào DB, không xếp job (như story cũ trước Phase 3)."""
    assert story.id is not None
    out: list[Message] = []
    for _ in range(count):
        turn = repo.next_turn_index(story.id)
        repo.insert_message(Message(story_id=story.id, turn_index=turn, role="user", mode="story",
                                    raw_content=f"Người chơi {turn}", visible_content=f"Người chơi {turn}"))
        out.append(repo.insert_message(Message(
            story_id=story.id, turn_index=turn + 1, role="assistant", mode="story",
            raw_content=f"Nhân vật {turn + 1}", visible_content=f"Nhân vật {turn + 1}", prompt_snapshot=snapshot,
            gen_stats=GenStats(),
        )))
    return out


async def test_rebuild_extracts_old_turns_in_order_with_upto_state(env: Env) -> None:
    replies = _add_turns(env.repo, env.story, 3)
    extras = await env.state.extras(env.story)
    # 3 lượt trả lời + lời mở đầu (lượt 0, Phase 3b).
    assert extras.unprocessed_turns == 4 and not extras.pending
    assert env.queue.rebuild(env.sid) == 4
    assert env.queue.rebuild(env.sid) == 0  # đã xếp: không xếp trùng
    await env.worker.run_until_idle()
    opening = env.repo.active_messages(env.sid)[0]
    assert [c["turn"][-1].id for c in env.extractor.calls] == [opening.id] + [m.id for m in replies]
    assert [m.role for m in env.extractor.calls[0]["turn"]] == ["assistant"]
    base = env.state.initial(env.story).affection
    # Lời mở đầu không ghi thay đổi cảm xúc (chỉ cảnh + ký ức).
    assert [c["before"].affection for c in env.extractor.calls] == [base, base, base + 5, base + 10]
    assert [c["scene"].location for c in env.extractor.calls] == [
        None, "Nơi 0", f"Nơi {replies[0].turn_index}", f"Nơi {replies[1].turn_index}"
    ]
    assert [e.kind for e in env.repo.message_state_events(opening.id or 0)] == ["scene"]
    extras = await env.state.extras(env.story)
    assert extras.unprocessed_turns == 0 and len(extras.memories) == 4
    assert extras.suggestions == []


async def test_summary_enqueued_when_window_drops_turns(env: Env, monkeypatch: pytest.MonkeyPatch) -> None:
    replies = _add_turns(env.repo, env.story, 5)  # lượt 1..10
    last = replies[-1]
    env.repo.conn.execute(
        "UPDATE messages SET prompt_snapshot_json = ? WHERE id = ?",
        ('{"dropped_turns": 7, "messages": []}', last.id),
    )
    last = env.repo.get_message(last.id or 0, account_id=ANY_ACCOUNT)
    active = env.repo.active_messages(env.sid)
    assert window_start_turn(last, active) == 7  # suy ra từ dropped_turns khi snapshot cũ
    monkeypatch.setattr(worker_module, "SUMMARY_CHUNK_TOKENS", 1)  # mỗi lượt một lần gọi
    assert env.queue.rebuild(env.sid) == 7  # 5 extract + lời mở đầu + summarize sau cùng
    kinds = [j.kind for j in env.repo.list_jobs(env.sid, statuses=("queued",))]
    assert kinds[-1] == "summarize"
    await env.worker.run_until_idle()
    calls = env.summarizer.calls
    assert [[m.turn_index for m in c["messages"]] for c in calls] == [[0], [1], [2], [3], [4], [5], [6]]
    assert calls[0]["previous"] is None and calls[1]["previous"].startswith("Tóm tắt tới lượt 0")
    assert calls[0]["model"] == env.story.model_name and calls[0]["num_ctx"] == 8192
    summary = env.state.current_summary(env.story)
    assert summary is not None and summary.upto_turn == 6
    assert (await env.state.extras(env.story)).summary == summary.text
    # Đã bao phủ: không xếp tóm tắt nữa.
    assert not env.state.needs_summary(env.story, 6)
    # Phase 3b: khối C chỉ dùng tóm tắt nằm hẳn trước cửa sổ. Lượt kế tiếp vừa trọn ngân sách (cửa sổ từ
    # lượt 0) nên chưa dùng tóm tắt; snapshot ghi đúng cái đã vào prompt.
    reply = await send(env)
    assert reply.prompt_snapshot is not None and reply.prompt_snapshot["window_start_turn"] == 0
    assert reply.prompt_snapshot["state"]["summary"] is None
    assert "summaries" not in reply.prompt_snapshot["state"]


async def test_summary_threshold(env: Env) -> None:
    assert not env.state.needs_summary(env.story, None)
    assert not env.state.needs_summary(env.story, -1)
    assert env.state.needs_summary(env.story, 0)
    assert env.state.needs_summary(env.story, 4)


async def test_embed_job_when_model_available(seeded_repo: Repo) -> None:
    env = make_env(seeded_repo, models=["gemma4:12b", "bge-m3:latest"])
    assert await env.state.memory_search() == "hybrid"
    await send(env)
    await env.worker.run_until_idle()
    kinds = [(j.kind, j.status) for j in env.repo.list_jobs(env.sid)]
    assert kinds == [("extract", "done"), ("embed", "done")]
    assert env.embedder.calls and env.embedder.calls[0][0] == "bge-m3"
    stored = env.repo.memory_embeddings(env.sid, "bge-m3")
    assert len(stored) == 1 and unpack_embedding(stored[0][1]) == [float(len(stored[0][0].text)), 1.0, 0.5]
    assert (await env.state.extras(env.story)).memory_search == "hybrid"


async def test_no_embed_job_without_model(seeded_repo: Repo) -> None:
    env = make_env(seeded_repo, models=["gemma4:12b"])
    assert await env.state.memory_search() == "keyword"
    await send(env)
    await env.worker.run_until_idle()
    assert [j.kind for j in env.repo.list_jobs(env.sid)] == ["extract"]


async def test_model_catalog_caches_and_tolerates_failure() -> None:
    now = [0.0]
    calls = [0]

    async def names() -> list[str]:
        calls[0] += 1
        return ["bge-m3"]

    catalog = ModelCatalog(names, ttl=60, clock=lambda: now[0])
    assert await catalog.names() == ["bge-m3"] and await catalog.names() == ["bge-m3"] and calls[0] == 1
    now[0] = 61
    await catalog.names()
    assert calls[0] == 2
    assert await ModelCatalog(lister(None, fail=True)).names() is None
    assert await ModelCatalog(None).names() is None


def test_pack_embedding_little_endian() -> None:
    blob = pack_embedding([1.0, -2.5])
    assert blob == b"\x00\x00\x80?\x00\x00 \xc0" and unpack_embedding(blob) == [1.0, -2.5]


async def test_initial_relationship_used_for_old_story_without_snapshot(env: Env) -> None:
    env.repo.set_story_initial_relationship(env.sid, None)
    card = env.repo.get_card(env.story.card_id, account_id=ANY_ACCOUNT)
    env.repo.update_card(card.id or 0, card.model_copy(update={"extensions": {"lyris": {"initial_relationship": {"trust": 90}}}}), account_id=ANY_ACCOUNT)
    extras = await env.state.extras(env.story)
    assert extras.relationship is not None and extras.relationship.trust == 90
    assert extras.relationship.fear == DEFAULT_INITIAL_RELATIONSHIP["fear"]


# ---------------------------------------------------------------------------- prefill lượt sau (§10.6)


def prefill_calls(env: Env) -> list[dict[str, Any]]:
    return [c for c in env.llm.calls if c["options"].get("num_predict") == 1]


async def test_worker_prefills_next_prompt_head_when_idle(seeded_repo: Repo) -> None:
    env = make_env(seeded_repo, prefill=True)
    reply = await send(env)
    await env.worker.start()
    try:
        await until(lambda: bool(prefill_calls(env)))
        await until(lambda: env.worker._prefill_task is None)
    finally:
        await env.worker.stop()
    assert env.repo.list_jobs(env.sid)[0].status == "done"  # prefill chạy SAU job, khi hàng đợi rỗng
    calls = prefill_calls(env)
    assert len(calls) == 1
    call = calls[0]
    assert call["model"] == env.story.model_name and call["options"]["num_ctx"] == 8192
    # Kết thúc bằng câu trả lời vừa viết (chưa có lượt người chơi kế tiếp, chưa có ghi chú F).
    assert call["messages"][-1].role == "assistant" and call["messages"][-1].content.startswith("Lạc Dương mỉm cười")
    assert call["messages"] == env.state.next_prompt_prefix(env.story).messages  # type: ignore[union-attr]
    assert reply.id is not None


async def test_prefill_uses_raw_prefix_and_falls_back_to_chat(seeded_repo: Repo) -> None:
    # §10.6: client có `prefill_prefix` (raw, kết thúc đúng chỗ prompt thật rẽ ra) thì dùng nó, không gọi
    # chat_stream. Không render được model (False) hoặc raw lỗi: prefill bằng chat_stream như cũ.
    env = make_env(seeded_repo, prefill=True)
    await send(env)
    await env.worker.run_until_idle()
    n_chat = sum(1 for c in env.llm.calls if "raw" not in c)
    assert await env.worker.prefill(env.sid) is True
    last = env.llm.calls[-1]
    assert last.get("raw") is True and sum(1 for c in env.llm.calls if "raw" not in c) == n_chat
    assert last["messages"] == env.state.next_prompt_prefix(env.story).messages  # type: ignore[union-attr]

    env.llm.raw_prefill = False
    assert await env.worker.prefill(env.sid) is True
    assert "raw" not in env.llm.calls[-1] and env.llm.calls[-1]["options"]["num_predict"] == 1

    env.llm.raw_prefill = True

    async def broken(model: str, messages: Any, *, options: dict[str, Any]) -> bool:
        raise LLMError("raw not allowed")

    env.llm.prefill_prefix = broken  # type: ignore[method-assign]
    before = len(env.llm.calls)
    assert await env.worker.prefill(env.sid) is True
    assert len(env.llm.calls) == before + 1 and "raw" not in env.llm.calls[-1]


async def test_prefill_is_off_by_default_and_needs_a_reply_last(env: Env) -> None:
    await send(env)
    await env.worker.start()
    try:
        await until(lambda: env.repo.list_jobs(env.sid)[0].status == "done")
        await asyncio.sleep(0.12)
    finally:
        await env.worker.stop()
    assert prefill_calls(env) == []
    # Lượt cuối là của người chơi (chưa có câu trả lời): không có gì để gửi trước.
    env.repo.insert_message(
        Message(story_id=env.sid, turn_index=env.repo.next_turn_index(env.sid), role="user", mode="story",
                raw_content="Ơ", visible_content="Ơ")
    )
    assert env.state.next_prompt_prefix(env.story) is None
    assert await env.worker.prefill(env.sid) is False and prefill_calls(env) == []


async def test_chat_cancels_running_prefill(seeded_repo: Repo) -> None:
    env = make_env(seeded_repo, prefill=True)
    await send(env)
    await env.worker.run_until_idle()
    env.llm.delay = 0.05  # prefill chậm: đủ thời gian để lượt chat chen vào
    task = asyncio.create_task(env.worker.prefill(env.sid))
    await until(lambda: env.worker._prefill_task is not None)
    env.queue.generation_started(env.sid)
    assert await task is False
    assert env.worker._prefill_task is None
    # Đang có lượt chat stream: không prefill.
    assert await env.worker.prefill(env.sid) is False
    env.queue.generation_finished(env.sid)


async def test_prefill_error_is_swallowed(seeded_repo: Repo) -> None:
    env = make_env(seeded_repo, prefill=True)
    await send(env)
    await env.worker.run_until_idle()
    env.llm.error = LLMError("Ollama tắt")
    assert await env.worker.prefill(env.sid) is False
    assert await env.worker.prefill(10_000) is False  # story không tồn tại


async def test_prefill_only_the_story_being_played(seeded_repo: Repo) -> None:
    # Cache prompt của Ollama chỉ giữ một prompt: người chơi đang ở story B mà story A (model khác) vừa có job
    # (tạo story, sửa, rebuild) thì chỉ prefill B. Trước đây worker prefill lần lượt mọi story có job, A sau
    # cùng: đẩy cache (và cả model) của B ra.
    from lyris.studio.stories import create_story_for

    env = make_env(seeded_repo, prefill=True)
    b = env.story
    assert b.id is not None
    card, persona = env.repo.list_cards(account_id=ANY_ACCOUNT)[0], env.repo.list_personas(account_id=ANY_ACCOUNT)[0]
    assert card.id is not None and persona.id is not None
    a = create_story_for(env.repo, card.id, persona.id, model_name="model-A", account_id=env.repo.owner_id())
    assert a.id is not None
    await drain(env.chat.send(b.id, '"Chào cậu."'))
    assert env.queue.story_created(a.id) is not None  # job của A chạy SAU lượt chat ở B
    await env.worker.start()
    try:
        await until(lambda: env.repo.list_jobs(a.id)[0].status == "done" and bool(prefill_calls(env)))  # type: ignore[arg-type]
        await until(lambda: env.worker._prefill_task is None and env.worker._prefill_due is None)
        await asyncio.sleep(0.12)
    finally:
        await env.worker.stop()
    assert {c["model"] for c in prefill_calls(env)} == {b.model_name}
    assert prefill_calls(env)[-1]["messages"] == env.state.next_prompt_prefix(env.repo.get_story(b.id, account_id=ANY_ACCOUNT)).messages  # type: ignore[union-attr]


async def test_story_created_via_api_becomes_the_story_being_played(seeded_repo: Repo) -> None:
    # Người chơi ở story B rồi tạo story A (POST /stories, app mở A ngay): prefill sau job lời mở đầu của A phải
    # là của A. Trước đây focus vẫn là B, nên lượt đầu của A đọc cả prompt (~29 giây trên gemma4:12b thật).
    from lyris.studio.stories import create_story_for

    env = make_env(seeded_repo, prefill=True)
    b = env.story
    assert b.id is not None
    await drain(env.chat.send(b.id, '"Chào cậu."'))
    await env.worker.run_until_idle()
    card, persona = env.repo.list_cards(account_id=ANY_ACCOUNT)[0], env.repo.list_personas(account_id=ANY_ACCOUNT)[0]
    assert card.id is not None and persona.id is not None
    a = create_story_for(env.repo, card.id, persona.id, model_name="model-A", account_id=env.repo.owner_id())
    assert a.id is not None
    env.llm.calls.clear()
    assert env.queue.story_created(a.id, focus=True) is not None
    await env.worker.start()
    try:
        await until(lambda: env.repo.list_jobs(a.id)[0].status == "done" and bool(prefill_calls(env)))  # type: ignore[arg-type]
        await until(lambda: env.worker._prefill_task is None and env.worker._prefill_due is None)
        await asyncio.sleep(0.12)
    finally:
        await env.worker.stop()
    assert {c["model"] for c in prefill_calls(env)} == {"model-A"}
    assert prefill_calls(env)[-1]["messages"] == env.state.next_prompt_prefix(env.repo.get_story(a.id, account_id=ANY_ACCOUNT)).messages  # type: ignore[union-attr]


async def test_suggest_cancelling_or_evicting_prefill_prefills_again(seeded_repo: Repo) -> None:
    # "Nhận gợi ý" gọi model chat với prompt khác (đẩy phần đã prefill ra khỏi cache) và huỷ prefill đang chạy,
    # nhưng không xếp job nào: worker phải tự prefill lại sau đó.
    env = make_env(seeded_repo, prefill=True)

    async def suggester(llm: Any, **kw: Any) -> list[str]:
        return ["Đi thôi."]

    env.chat.suggester = suggester
    await send(env)
    await env.worker.start()
    try:
        await until(lambda: len(prefill_calls(env)) == 1 and env.worker._prefill_task is None)
        await env.chat.suggest(env.sid)  # prefill đã xong, gợi ý đẩy nó ra khỏi cache
        await until(lambda: len(prefill_calls(env)) == 2 and env.worker._prefill_task is None)
        env.llm.delay = 0.05
        await env.chat.suggest(env.sid)
        await until(lambda: env.worker._prefill_task is not None)
        await env.chat.suggest(env.sid)  # huỷ prefill đang chạy
        await until(lambda: len(prefill_calls(env)) == 4 and env.worker._prefill_task is None)
    finally:
        await env.worker.stop()
    assert env.worker._prefill_due is None


async def test_history_change_cancels_running_prefill_and_prefills_new_prefix(seeded_repo: Repo) -> None:
    env = make_env(seeded_repo, prefill=True)
    await send(env)
    second = await send(env, "Lượt hai")
    await env.worker.run_until_idle()
    env.llm.delay = 0.05
    # Xoá lượt cuối khi đang prefill: phần đầu cũ bị huỷ, story được hẹn prefill lại (phần đầu mới).
    task = asyncio.create_task(env.worker.prefill(env.sid))
    await until(lambda: env.worker._prefill_task is not None)
    turn_two = next(m for m in env.repo.active_messages(env.sid) if m.role == "user" and m.raw_content == "Lượt hai")
    assert second.id is not None and turn_two.id is not None
    env.chat.delete_from(turn_two.id)  # xoá lượt người chơi thứ hai và câu trả lời sau nó
    assert await task is False and env.worker._prefill_due == env.sid
    # Sửa câu trả lời của nhân vật (message_reset) cũng vậy.
    env.worker._prefill_due = None
    last = env.repo.active_messages(env.sid)[-1]
    assert last.role == "assistant" and last.id is not None
    task = asyncio.create_task(env.worker.prefill(env.sid))
    await until(lambda: env.worker._prefill_task is not None)
    env.chat.edit_message(last.id, "Lạc Dương gật đầu.")
    assert await task is False and env.worker._prefill_due == env.sid
    # Sửa lượt người chơi: không có job nào, nhưng phần đầu đổi nên vẫn hẹn prefill lại.
    env.worker._prefill_due = None
    user = next(m for m in reversed(env.repo.active_messages(env.sid)) if m.role == "user")
    assert user.id is not None
    env.chat.edit_message(user.id, "Ơ, kể lại đi.")
    assert env.worker._prefill_due == env.sid
    # Prefill story khác (story vừa xoá) không bị huỷ nhầm, và story đã xoá không còn được hẹn.
    env.worker.on_messages_changed(10_000)
    assert env.worker._prefill_due == env.sid


async def test_prefill_not_scheduled_when_disabled(env: Env) -> None:
    await send(env)
    env.queue.generation_started(env.sid)
    env.queue.generation_finished(env.sid)
    env.worker.on_messages_changed(env.sid)
    assert env.worker._prefill_due is None
