"""Phase 3, sửa sau review: id bị cấp lại sau khi xoá theo CASCADE, lượt aborted, giữ tóm tắt khi sửa.

Không gọi Ollama thật: dùng FakeLLM và extractor/embedder giả của tests/test_jobs.py.
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from lyris.api.app import create_app
from lyris.config import Settings
from lyris.db.repo import ANY_ACCOUNT, Repo
from lyris.llm.fake import FakeLLM
from lyris.models import Persona
from lyris.seed import load_seed_card
from lyris.studio.stories import create_story_for
from tests.test_jobs import Env, make_env, send, until
from tests.test_state_fold import _extract, _msg, _story
from tests.authutil import owner_client


@dataclass
class GatedEmbedder:
    gate: asyncio.Event = field(default_factory=asyncio.Event)
    started: asyncio.Event = field(default_factory=asyncio.Event)
    cancelled: int = 0

    async def __call__(self, model: str, texts: list[str]) -> list[list[float]]:
        self.started.set()
        try:
            await self.gate.wait()
        except asyncio.CancelledError:
            self.cancelled += 1
            raise
        return [[1.0, 0.0] for _ in texts]


def _other_story(repo: Repo) -> int:
    card = repo.create_card(load_seed_card(), account_id=repo.owner_id())
    persona = repo.create_persona(Persona(name="Người khác", gender="male"), account_id=repo.owner_id())
    assert card.id and persona.id
    story = create_story_for(repo, card.id, persona.id, model_name="m", account_id=repo.owner_id())
    assert story.id is not None
    return story.id


# ---------------------------------------------------------------------------- repo


def test_finish_job_only_touches_running_job(seeded_repo: Repo) -> None:
    repo = seeded_repo
    story = _story(repo)
    assert story.id is not None
    _msg(repo, story, 1, "user")
    a = _msg(repo, story, 2, "assistant")
    queued = repo.enqueue_job(story.id, "extract", a.id)
    # Job chưa được claim (vd. id được cấp lại cho job mới): worker không được kết thúc nó.
    assert not repo.finish_job(queued, "done", attempts=1)
    assert repo.get_job(queued).status == "queued" and repo.get_job(queued).attempts == 0
    assert repo.claim_next_job() is not None
    assert repo.finish_job(queued, "done", attempts=1) and repo.get_job(queued).status == "done"
    assert not repo.finish_job(queued, "failed")  # đã kết thúc rồi: không đổi nữa
    assert repo.get_job(queued).status == "done"
    # Script ghi sẵn kết quả (make_demo_db) kết thúc job chưa từng chạy.
    other = repo.enqueue_job(story.id, "embed")
    assert repo.finish_job(other, "done", only_running=False) and repo.get_job(other).status == "done"


def test_replace_extraction_checks_expected_story_and_turn(seeded_repo: Repo) -> None:
    repo = seeded_repo
    story = _story(repo)
    assert story.id is not None
    _msg(repo, story, 1, "user")
    a = _msg(repo, story, 2, "assistant")
    assert a.id is not None
    events: list[tuple[Any, dict[str, Any]]] = [("relationship_delta", {"affection": 5})]
    assert repo.replace_extraction(a.id, events, [], story_id=story.id + 999, turn_index=2) is None
    assert repo.replace_extraction(a.id, events, [], story_id=story.id, turn_index=0) is None
    assert repo.state_events(story.id) == []
    assert repo.replace_extraction(a.id, events, [], story_id=story.id, turn_index=2) == []
    assert [e.kind for e in repo.state_events(story.id)] == ["relationship_delta"]


def test_delete_card_and_persona_return_deleted_story_ids(seeded_repo: Repo) -> None:
    repo = seeded_repo
    story = _story(repo)
    assert story.id is not None
    ids = repo.delete_card_stories(story.card_id, with_stories=True, account_id=ANY_ACCOUNT)
    assert ids == [story.id] and not repo.story_exists(story.id)
    second = _story(repo)
    assert second.id is not None
    assert repo.delete_persona_stories(second.persona_id, with_stories=True, account_id=ANY_ACCOUNT) == [second.id]
    assert not repo.story_exists(second.id)


def test_aborted_reply_is_not_unprocessed(seeded_repo: Repo) -> None:
    repo = seeded_repo
    story = _story(repo)
    assert story.id is not None
    _msg(repo, story, 1, "user")
    _msg(repo, story, 2, "assistant", aborted=True)
    # Lời mở đầu (lượt 0) cũng được trích xuất từ Phase 3b; lượt bị Dừng thì không.
    opening = repo.active_messages(story.id)[0]
    assert repo.unprocessed_turns(story.id) == 1
    assert [m.id for m in repo.messages_needing_extract(story.id)] == [opening.id]
    _msg(repo, story, 3, "user")
    full = _msg(repo, story, 4, "assistant")
    assert repo.unprocessed_turns(story.id) == 2
    assert [m.id for m in repo.messages_needing_extract(story.id)] == [opening.id, full.id]


def test_delete_message_state_keeps_summary_anchor(seeded_repo: Repo) -> None:
    repo = seeded_repo
    story = _story(repo)
    assert story.id is not None
    _msg(repo, story, 1, "user")
    a = _msg(repo, story, 2, "assistant")
    assert a.id is not None
    _extract(repo, a, delta={"trust": 3}, memory="Một", scene={"location": "Sân", "time": None})
    repo.add_summary(a.id, "Tóm tắt tới lượt 2", 2)
    repo.delete_message_state(a.id)
    assert [e.kind for e in repo.state_events(story.id)] == ["summary"]
    assert repo.list_memories(story.id, limit=None) == []


# ---------------------------------------------------------------------------- worker


@pytest.fixture
def env(seeded_repo: Repo) -> Env:
    return make_env(seeded_repo, models=["gemma4:12b", "bge-m3"])


async def test_edit_reply_keeps_cumulative_summary(env: Env) -> None:
    reply = await send(env)
    await env.worker.run_until_idle()
    assert reply.id is not None
    env.repo.add_summary(reply.id, "Tóm tắt dồn", reply.turn_index)
    before = env.state.current_summary(env.story)
    assert before is not None and before.upto_turn == reply.turn_index
    env.chat.edit_message(reply.id, "Anh im lặng rất lâu.")
    after = env.state.current_summary(env.story)
    assert after is not None and after.text == "Tóm tắt dồn" and after.upto_turn == reply.turn_index
    await env.worker.run_until_idle()
    again = env.state.current_summary(env.story)
    assert again is not None and again.text == "Tóm tắt dồn"


async def test_running_embed_job_stops_when_story_deleted_and_reused_id_is_untouched(env: Env) -> None:
    embedder = GatedEmbedder()
    env.worker.embedder = embedder
    sid = env.sid
    await send(env)
    assert await env.worker.run_once() is not None  # extract -> xếp embed
    other = _other_story(env.repo)
    embed = env.repo.list_jobs(sid, statuses=("queued",))
    assert [j.kind for j in embed] == ["embed"]
    await env.worker.start()
    try:
        await asyncio.wait_for(embedder.started.wait(), 2)
        assert env.worker.current_job is not None and env.worker.current_job.id == embed[0].id
        # Xoá story (như xoá card kèm story) rồi ngay lập tức story khác xếp job mới: SQLite cấp lại id.
        env.repo.delete_story(sid, account_id=ANY_ACCOUNT)
        env.queue.messages_changed(sid)
        _msg(env.repo, env.repo.get_story(other, account_id=ANY_ACCOUNT), 1, "user")
        reply = _msg(env.repo, env.repo.get_story(other, account_id=ANY_ACCOUNT), 2, "assistant")
        env.queue.generation_started(other)  # giữ worker không chạy job mới trong lúc kiểm tra
        env.repo.enqueue_job(other, "summarize", reply.id)  # lấy lại id 1 (job extract đã xoá)
        reused = env.repo.enqueue_job(other, "extract", reply.id)
        assert reused == embed[0].id
        await until(lambda: env.worker.current_job is None)
        assert embedder.cancelled == 1
        job = env.repo.get_job(reused)
        assert job.status == "queued" and job.story_id == other and job.attempts == 0
        # job còn chờ, chưa bị đánh dấu done nhầm (chỉ lời mở đầu của story kia là chưa có job)
        assert env.repo.unprocessed_turns(other) == 1
        env.queue.generation_finished(other)
        await until(lambda: env.repo.get_job(reused).status == "done")
    finally:
        await env.worker.stop()
    assert len(env.repo.state_events(other)) >= 1


# ---------------------------------------------------------------------------- API


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        db_path=tmp_path / "lyris.db",
        ollama_url="http://127.0.0.1:9",
        chat_model="gemma4:12b",
        num_ctx=8192,
        avatars_dir=tmp_path / "avatars",
    )


@pytest.fixture
async def app(settings: Settings) -> AsyncIterator[FastAPI]:
    application = create_app(settings, FakeLLM(replies=["Anh gật đầu."]))
    async with application.router.lifespan_context(application):
        yield application


async def test_delete_card_and_persona_with_stories_notify_job_queue(
    app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo: Repo = app.state.repo
    changed: list[int] = []
    monkeypatch.setattr(app.state.jobs, "messages_changed", lambda story_id: changed.append(story_id) or 0)
    card = repo.create_card(load_seed_card(), account_id=repo.owner_id())
    persona = repo.create_persona(Persona(name="Ai đó", gender="female"), account_id=repo.owner_id())
    assert card.id and persona.id
    s1 = create_story_for(repo, card.id, persona.id, model_name="m", account_id=repo.owner_id())
    s2 = create_story_for(repo, card.id, persona.id, model_name="m", account_id=repo.owner_id())
    async with owner_client(app, base_url="http://test") as c:
        resp = await c.delete(f"/api/cards/{card.id}", params={"with_stories": "true"})
        assert resp.status_code == 200, resp.text
        assert resp.json()["deleted_stories"] == 2
        assert sorted(changed) == sorted([s1.id, s2.id])
        changed.clear()
        card2 = repo.create_card(load_seed_card(), account_id=repo.owner_id())
        assert card2.id
        s3 = create_story_for(repo, card2.id, persona.id, model_name="m", account_id=repo.owner_id())
        resp = await c.delete(f"/api/personas/{persona.id}", params={"with_stories": "true"})
        assert resp.status_code == 200, resp.text
        assert resp.json()["deleted_stories"] == 1 and changed == [s3.id]
