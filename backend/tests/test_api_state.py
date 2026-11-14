"""Phase 3 API (docs/phase3.md §7): /extras, quên ký ức, dựng lại state, StoryOut, card_count, lifespan worker.

FakeLLM cho chat; trích xuất là hàm giả gán vào `app.state.worker.extractor`. Không gọi Ollama thật.
"""
from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from lyris.api.app import create_app
from lyris.config import Settings
from lyris.db.repo import Repo
from lyris.jobs import Worker
from lyris.llm.fake import FakeLLM
from lyris.models import Persona
from lyris.seed import load_seed_card
from lyris.seed.templates import load_templates
from lyris.studio.stories import create_story_for
from tests.test_jobs import FakeExtractor
from tests.authutil import owner_client

REPLIES = ["Lạc Dương bật cười. [Thought: Ngốc.]", "Anh gật đầu.", "Anh quay đi."]


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
    application = create_app(settings, FakeLLM(replies=REPLIES))
    async with application.router.lifespan_context(application):
        worker: Worker = application.state.worker
        worker.extractor = FakeExtractor()
        yield application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with owner_client(app, base_url="http://test") as c:
        yield c


def repo_of(app: FastAPI) -> Repo:
    repo: Repo = app.state.repo
    return repo


async def ok(resp: httpx.Response) -> Any:
    assert resp.status_code == 200, resp.text
    return resp.json()


async def first_story(client: httpx.AsyncClient) -> int:
    return int((await ok(await client.get("/api/stories")))[0]["id"])


async def send(client: httpx.AsyncClient, sid: int, text: str = '"Chào."') -> dict[str, Any]:
    resp = await client.post(f"/api/stories/{sid}/messages", json={"content": text})
    assert resp.status_code == 200, resp.text
    for block in resp.text.split("\n\n"):
        if block.startswith("event: done"):
            return dict(json.loads(block.split("data: ", 1)[1])["message"])
    raise AssertionError(resp.text)


async def run_jobs(app: FastAPI) -> int:
    worker: Worker = app.state.worker
    return await worker.run_until_idle()


def other_account_story(repo: Repo) -> tuple[int, int]:
    """Story (có một ký ức) của một account khác: (story_id, memory_id)."""
    other = repo.create_account("khac", "Người khác")
    assert other.id is not None
    card = repo.create_card(load_seed_card().model_copy(update={"name": "Nhân vật lạ"}), account_id=other.id)
    persona = repo.create_persona(Persona(name="Persona lạ", gender="female"), account_id=other.id)
    assert card.id and persona.id
    story = create_story_for(repo, card.id, persona.id, model_name="m", account_id=other.id)
    msg = repo.active_messages(story.id or 0)[0]
    from lyris.db.repo import NewMemory

    # Lượt 0 không được trích xuất thật, nhưng ở đây chỉ cần một dòng ký ức thuộc story kia.
    saved = repo.replace_extraction(msg.id or 0, [], [NewMemory(kind="memory", text="Bí mật của người khác")])
    assert saved and saved[0].id is not None and story.id is not None
    return story.id, saved[0].id


# ---------------------------------------------------------------------------- /extras


async def test_extras_after_turn(app: FastAPI, client: httpx.AsyncClient) -> None:
    sid = await first_story(client)
    before = await ok(await client.get(f"/api/stories/{sid}/extras"))
    assert before["relationship"] is not None and before["pending"] is False and before["memories"] == []

    reply = await send(client, sid)
    pending = await ok(await client.get(f"/api/stories/{sid}/extras"))
    # Story seed (tạo lúc khởi động, LLM giả nên không tự xếp job) còn lời mở đầu chưa trích xuất.
    assert pending["pending"] is True and pending["unprocessed_turns"] == 1
    assert await run_jobs(app) == 1

    extras = await ok(await client.get(f"/api/stories/{sid}/extras"))
    assert extras["pending"] is False
    assert extras["relationship"]["affection"] == min(100, before["relationship"]["affection"] + 5)
    assert extras["location"] == f"Nơi {reply['turn_index']}" and extras["in_world_time"] is None
    assert extras["suggestions"] == []  # Phase 3b: gợi ý chỉ sinh theo yêu cầu
    assert [m["kind"] for m in extras["memories"]] == ["memory"]
    assert extras["memory_search"] == "keyword" and extras["summary"] is None
    assert "directive" in extras["relationship"]

    stories = await ok(await client.get("/api/stories"))
    card = next(s for s in stories if s["id"] == sid)
    assert card["location"] == f"Nơi {reply['turn_index']}"
    assert card["dominant_emotion"]["key"] in {"affection", "trust", "attraction", "obsession", "fear", "aversion"}

    snapshot = await ok(await client.get(f"/api/messages/{reply['id']}/snapshot"))
    assert "state" in snapshot and snapshot["window_start_turn"] == 0


async def test_story_out_has_no_chip_without_real_data(client: httpx.AsyncClient) -> None:
    stories = await ok(await client.get("/api/stories"))
    assert stories[0]["dominant_emotion"] is None and stories[0]["location"] is None


async def test_forget_memory(app: FastAPI, client: httpx.AsyncClient) -> None:
    sid = await first_story(client)
    await send(client, sid)
    await run_jobs(app)
    memory_id = (await ok(await client.get(f"/api/stories/{sid}/extras")))["memories"][0]["id"]
    other_sid, other_memory = other_account_story(repo_of(app))

    # Ký ức của account khác (qua story của mình hoặc story của họ): 404.
    assert (await client.delete(f"/api/stories/{sid}/memories/{other_memory}")).status_code == 404
    assert (await client.delete(f"/api/stories/{other_sid}/memories/{other_memory}")).status_code == 404
    assert repo_of(app).get_memory(other_memory).text == "Bí mật của người khác"

    assert await ok(await client.delete(f"/api/stories/{sid}/memories/{memory_id}")) == {"deleted": 1}
    assert (await ok(await client.get(f"/api/stories/{sid}/extras")))["memories"] == []
    assert (await client.delete(f"/api/stories/{sid}/memories/{memory_id}")).status_code == 404


async def test_other_account_story_is_404(app: FastAPI, client: httpx.AsyncClient) -> None:
    other_sid, _ = other_account_story(repo_of(app))
    assert (await client.get(f"/api/stories/{other_sid}/extras")).status_code == 404
    assert (await client.post(f"/api/stories/{other_sid}/state/rebuild")).status_code == 404
    assert (await client.get("/api/stories/9999/extras")).status_code == 404
    assert other_sid not in {s["id"] for s in await ok(await client.get("/api/stories"))}


async def test_rebuild_route(app: FastAPI, client: httpx.AsyncClient) -> None:
    sid = await first_story(client)
    await send(client, sid)
    await send(client, sid, '"Nữa."')
    # Như story cũ: bỏ hết job (chưa từng trích xuất).
    repo_of(app).conn.execute("DELETE FROM jobs")
    extras = await ok(await client.get(f"/api/stories/{sid}/extras"))
    assert extras["unprocessed_turns"] == 3 and extras["pending"] is False  # 2 lượt + lời mở đầu
    assert await ok(await client.post(f"/api/stories/{sid}/state/rebuild")) == {"queued": 3}
    assert (await ok(await client.get(f"/api/stories/{sid}/extras")))["pending"] is True
    assert await ok(await client.post(f"/api/stories/{sid}/state/rebuild")) == {"queued": 0}
    await run_jobs(app)
    extras = await ok(await client.get(f"/api/stories/{sid}/extras"))
    assert extras["unprocessed_turns"] == 0 and len(extras["memories"]) == 3  # 2 lượt + lời mở đầu


async def test_regenerate_and_delete_through_api_roll_back(app: FastAPI, client: httpx.AsyncClient) -> None:
    sid = await first_story(client)
    start = (await ok(await client.get(f"/api/stories/{sid}/extras")))["relationship"]
    reply = await send(client, sid)
    await run_jobs(app)
    resp = await client.post(f"/api/messages/{reply['id']}/regenerate")
    assert resp.status_code == 200
    extras = await ok(await client.get(f"/api/stories/{sid}/extras"))
    assert extras["relationship"] == start and extras["memories"] == [] and extras["pending"] is True
    await ok(await client.post(f"/api/messages/{reply['id']}/variant", json={"variant_index": 0}))
    extras = await ok(await client.get(f"/api/stories/{sid}/extras"))
    assert len(extras["memories"]) == 1 and extras["pending"] is False  # job của variant mới bị huỷ
    await ok(await client.delete(f"/api/messages/{reply['id']}"))
    extras = await ok(await client.get(f"/api/stories/{sid}/extras"))
    assert extras["relationship"] == start and extras["memories"] == [] and extras["suggestions"] == []


async def test_edit_through_api_requeues(app: FastAPI, client: httpx.AsyncClient) -> None:
    sid = await first_story(client)
    reply = await send(client, sid)
    await run_jobs(app)
    await ok(await client.patch(f"/api/messages/{reply['id']}", json={"content": "Anh đứng lặng."}))
    extras = await ok(await client.get(f"/api/stories/{sid}/extras"))
    assert extras["memories"] == [] and extras["pending"] is True
    await run_jobs(app)
    extras = await ok(await client.get(f"/api/stories/{sid}/extras"))
    assert extras["memories"][0]["text"].startswith("Sự việc lượt") and "Anh đứng lặng" in extras["memories"][0]["text"]


async def test_delete_story_with_queued_jobs(app: FastAPI, client: httpx.AsyncClient) -> None:
    sid = await first_story(client)
    await send(client, sid)
    await ok(await client.delete(f"/api/stories/{sid}"))
    assert repo_of(app).list_jobs() == []
    assert await run_jobs(app) == 0


# ---------------------------------------------------------------------------- tạo story, tài khoản


async def test_create_story_snapshots_card_relationship(app: FastAPI, client: httpx.AsyncClient) -> None:
    card = await ok(await client.post("/api/cards", json={"card": {
        "name": "Trần Minh Khang", "gender": "male", "language": "vi", "style_profile": "trung_hien_dai",
        "address_terms": {"self_term": "anh", "player_term": "em", "nicknames": [], "others": ""},
        "greeting": "Chào.", "extensions": {"lyris": {"initial_relationship": {"affection": 66, "trust": 12}}},
    }}))
    story = await ok(await client.post("/api/stories", json={"card_id": card["id"]}))
    snap = repo_of(app).story_initial_relationship(story["id"])
    assert snap is not None and snap["affection"] == 66 and snap["trust"] == 12
    extras = await ok(await client.get(f"/api/stories/{story['id']}/extras"))
    assert extras["relationship"]["affection"] == 66
    # Story seed (POST {}) cũng có ảnh chụp.
    seed = await ok(await client.post("/api/stories", json={}))
    assert repo_of(app).story_initial_relationship(seed["id"]) is not None


async def test_account_card_count_excludes_templates(client: httpx.AsyncClient) -> None:
    start = (await ok(await client.get("/api/account")))["card_count"]
    assert start == 0  # card seed là nhân vật mẫu Lạc Dương
    slug = next(t.slug for t in load_templates() if t.slug != "lac-duong")
    await ok(await client.post(f"/api/templates/{slug}/install"))
    assert (await ok(await client.get("/api/account")))["card_count"] == 0
    await ok(await client.post("/api/cards", json={"card": {
        "name": "Riêng", "gender": "female", "language": "vi", "style_profile": "trung_hien_dai",
        "address_terms": {"self_term": "tớ", "player_term": "cậu", "nicknames": [], "others": ""},
    }}))
    assert (await ok(await client.get("/api/account")))["card_count"] == 1


# ---------------------------------------------------------------------------- lifespan


async def test_worker_not_started_with_fake_llm(app: FastAPI) -> None:
    worker: Worker = app.state.worker
    assert not worker.running


async def test_lifespan_runs_worker_when_asked(settings: Settings) -> None:
    application = create_app(settings, FakeLLM(replies=REPLIES), start_worker=True)
    async with application.router.lifespan_context(application):
        worker: Worker = application.state.worker
        assert worker.running
        worker.extractor = FakeExtractor()
        async with owner_client(application, base_url="http://test") as c:
            sid = await first_story(c)
            await send(c, sid)
            for _ in range(200):
                if not (await ok(await c.get(f"/api/stories/{sid}/extras")))["pending"]:
                    break
                await asyncio.sleep(0.01)
            extras = await ok(await c.get(f"/api/stories/{sid}/extras"))
            # Worker thật tự chạy: lời mở đầu của story seed cũng được trích xuất (Phase 3b).
            assert extras["pending"] is False and len(extras["memories"]) == 2
            assert sorted(m["turn_index"] for m in extras["memories"]) == [0, 2]
    assert not worker.running


def test_settings_extract_and_embed_models(monkeypatch: pytest.MonkeyPatch) -> None:
    from lyris.config import get_settings

    for name in ("LYRIS_EXTRACT_MODEL", "LYRIS_EMBED_MODEL", "NORA_EXTRACT_MODEL", "NORA_EMBED_MODEL"):
        monkeypatch.delenv(name, raising=False)
    s = get_settings()
    assert s.extract_model is None and s.embed_model == "bge-m3"
    monkeypatch.setenv("LYRIS_EXTRACT_MODEL", " gemma4:e4b ")
    monkeypatch.setenv("LYRIS_EMBED_MODEL", "embeddinggemma")
    s = get_settings()
    assert s.extract_model == "gemma4:e4b" and s.embed_model == "embeddinggemma"


async def test_system_reports_memory_search(app: FastAPI, client: httpx.AsyncClient) -> None:
    """Sheet Tài khoản: dòng "Ký ức" (từ khoá / theo nghĩa) và tên embed model để gợi ý `ollama pull`."""
    body = await ok(await client.get("/api/system"))
    assert body["memory_search"] == "keyword" and body["embed_model"] == "bge-m3"

    async def listed() -> list[str]:
        return ["gemma4:12b", "bge-m3:latest"]

    from lyris.state.service import ModelCatalog

    app.state.state._catalog = ModelCatalog(listed)
    assert (await ok(await client.get("/api/system")))["memory_search"] == "hybrid"
