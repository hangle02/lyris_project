"""Phase 3 end-to-end qua HTTP: chat -> worker -> /extras, với các hàm thật (extract_turn, summarize, retrieve,
embed) chạy trên một LLM giả có kịch bản. Không gọi Ollama thật.

Khác test_api_state.py (extractor giả gán vào worker): ở đây worker dùng đúng các hàm mặc định mà lifespan
nối vào, nên kiểm tra được cả chỗ nối: prompt trích xuất -> validate -> repo -> fold -> prompt lượt sau.
"""
from __future__ import annotations

import asyncio
import json
import re
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from lyris.api.app import create_app
from lyris.config import Settings
from lyris.db.repo import ANY_ACCOUNT, NewMemory, Repo
from lyris.jobs import Worker
from lyris.llm.fake import FakeLLM
from lyris.models import ChatTurn, Persona
from lyris.seed import load_seed_card
from lyris.studio.stories import create_story_for
from tests.authutil import owner_client

# Mỗi câu trả lời của nhân vật có một "dấu" riêng; LLM giả đọc dấu trong prompt trích xuất để trả JSON tương ứng.
REPLY_TEA = (
    "Lạc Dương kéo Lâm Vãn ra quán trà sữa đầu ngõ, gọi sẵn ly trân châu đường đen.\n\n"
    "[Thought: Cậu ấy mê món này từ hồi cấp hai.]\n\n"
    '"Uống đi, tớ mời."'
)
REPLY_LIBRARY = (
    "Lạc Dương lắc đầu, kéo Lâm Vãn vào thư viện trường tránh mưa.\n\n"
    "[Thought: Ướt hết rồi còn đòi đi đâu.]\n\n"
    '"Ngồi yên đây, mưa tạnh rồi tính."'
)
REPLY_FOREHEAD = (
    "Lạc Dương gõ nhẹ lên trán Lâm Vãn.\n\n[Thought: Ngốc thật.]\n\n"
    '"Ngon thì uống chậm thôi, ai giành của cậu."'
)

EXTRACTIONS: dict[str, dict[str, Any]] = {
    "gọi sẵn ly": {
        "relationship_delta": {"affection": 3, "trust": 2, "attraction": 1, "obsession": 0, "fear": 0, "aversion": 0},
        "location": "Quán trà sữa đầu ngõ",
        "time": "Chiều tan học",
        "memory": {"text": "Lạc Dương mời Lâm Vãn ly trà sữa trân châu đường đen ở quán đầu ngõ.", "importance": 4},
        "facts": [{"subject": "Lâm Vãn", "text": "Lâm Vãn mê trà sữa trân châu đường đen từ hồi cấp hai"}],
        "suggestions": [
            'Tôi nhận ly trà, cười tít mắt. "Cậu nhớ dai ghê."',
            '"Hôm nay sao tốt bụng vậy?"',
            "Tôi uống một ngụm rồi đẩy ly sang cho cậu ấy.",
        ],
    },
    "tránh mưa": {
        "relationship_delta": {"affection": 0, "trust": 0, "attraction": 0, "obsession": 0, "fear": 1, "aversion": 2},
        "location": "Thư viện trường",
        "time": "",
        "memory": {"text": "Lạc Dương kéo Lâm Vãn vào thư viện trường trú mưa.", "importance": 2},
        "facts": [],
        "suggestions": ['"Mưa thế này chắc phải tới tối."', "Tôi ngồi xuống cạnh cậu ấy."],
    },
    "gõ nhẹ lên trán": {
        "relationship_delta": {"affection": 2, "trust": 0, "attraction": 2, "obsession": 1, "fear": 0, "aversion": 0},
        "location": "không đổi",
        "time": "",
        "memory": {"text": "Lạc Dương gõ trán Lâm Vãn, bảo cô uống chậm.", "importance": 3},
        "facts": [],
        "suggestions": ['"Đau đó nha!"'],
    },
}


class ScriptedLLM(FakeLLM):
    """FakeLLM có `list_models` (để bật tìm ký ức lai) và `chat_json` theo nội dung prompt.

    - Prompt trích xuất: tìm dấu của EXTRACTIONS trong lượt cần đọc, trả JSON tương ứng (không thấy -> JSON rỗng).
    - Prompt tóm tắt (schema có `summary`): trả một tóm tắt ghi rõ số message đã đọc.
    - `gate`: nếu đặt, chat_json chờ nó trước khi trả (để thử nhường lượt chat); `json_started` báo đã vào.
    """

    def __init__(self, replies: list[str], *, models: list[str] | None = None) -> None:
        super().__init__(replies=replies)
        self.models = models if models is not None else ["gemma4:12b", "bge-m3:latest"]
        self.gate: asyncio.Event | None = None
        self.json_started = asyncio.Event()
        self.json_cancelled = 0

    async def list_models(self) -> list[str]:
        return list(self.models)

    async def chat_json(
        self, model: str, messages: list[ChatTurn], *, schema: dict[str, Any], options: dict[str, Any]
    ) -> dict[str, Any]:
        self.calls.append({"model": model, "messages": list(messages), "options": dict(options), "schema": schema})
        self.json_started.set()
        if self.gate is not None:
            try:
                await self.gate.wait()
            except asyncio.CancelledError:
                self.json_cancelled += 1
                raise
        if "summary" in schema.get("properties", {}):
            return {"summary": f"Tóm tắt chuyện cũ của Lạc Dương và Lâm Vãn (call {len(self.json_calls())})."}
        if "suggestions" in schema.get("properties", {}):
            n = len([c for c in self.json_calls() if "suggestions" in c["schema"].get("properties", {})])
            return {"suggestions": [f'"Gợi ý {n}.1"', f"Tôi cười. \"Gợi ý {n}.2\"", f"Gợi ý {n}.3"]}
        text = messages[-1].content
        for mark, data in EXTRACTIONS.items():
            if mark in text:
                return json.loads(json.dumps(data))
        return {"relationship_delta": {}, "location": "", "time": "", "memory": {"text": "", "importance": 3},
                "facts": [], "suggestions": []}

    def json_calls(self) -> list[dict[str, Any]]:
        return [c for c in self.calls if "schema" in c]

    def chat_calls(self) -> list[dict[str, Any]]:
        return [c for c in self.calls if "schema" not in c]


def make_settings(tmp_path: Path, num_ctx: int = 8192) -> Settings:
    return Settings(
        db_path=tmp_path / "lyris.db",
        ollama_url="http://127.0.0.1:9",
        chat_model="gemma4:12b",
        num_ctx=num_ctx,
        avatars_dir=tmp_path / "avatars",
    )


@pytest.fixture
def llm() -> ScriptedLLM:
    return ScriptedLLM([REPLY_TEA, REPLY_LIBRARY, REPLY_FOREHEAD])


@pytest.fixture
async def app(tmp_path: Path, llm: ScriptedLLM) -> AsyncIterator[FastAPI]:
    application = create_app(make_settings(tmp_path), llm)
    async with application.router.lifespan_context(application):
        yield application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with owner_client(app, base_url="http://test") as c:
        yield c


def repo_of(app: FastAPI) -> Repo:
    repo: Repo = app.state.repo
    return repo


def worker_of(app: FastAPI) -> Worker:
    worker: Worker = app.state.worker
    return worker


async def ok(resp: httpx.Response) -> Any:
    assert resp.status_code == 200, resp.text
    return resp.json()


def done_message(body: str) -> dict[str, Any]:
    for block in body.split("\n\n"):
        if block.startswith("event: done"):
            return dict(json.loads(block.split("data: ", 1)[1])["message"])
    raise AssertionError(body)


async def send(client: httpx.AsyncClient, sid: int, text: str) -> dict[str, Any]:
    resp = await client.post(f"/api/stories/{sid}/messages", json={"content": text})
    assert resp.status_code == 200, resp.text
    return done_message(resp.text)


async def regenerate(client: httpx.AsyncClient, message_id: int) -> dict[str, Any]:
    resp = await client.post(f"/api/messages/{message_id}/regenerate")
    assert resp.status_code == 200, resp.text
    return done_message(resp.text)


async def first_story(client: httpx.AsyncClient) -> int:
    return int((await ok(await client.get("/api/stories")))[0]["id"])


async def extras(client: httpx.AsyncClient, sid: int) -> dict[str, Any]:
    return dict(await ok(await client.get(f"/api/stories/{sid}/extras")))


def rel(data: dict[str, Any]) -> dict[str, int]:
    return {k: v for k, v in data["relationship"].items() if k != "directive"}


def plus(base: dict[str, int], **delta: int) -> dict[str, int]:
    return {k: max(0, min(100, v + delta.get(k, 0))) for k, v in base.items()}


def final_note(call: dict[str, Any]) -> str:
    return str(call["messages"][-1].content)


# ---------------------------------------------------------------------------- một lượt trọn vẹn


async def test_turn_flows_into_extras_and_next_prompt(app: FastAPI, client: httpx.AsyncClient, llm: ScriptedLLM) -> None:
    sid = await first_story(client)
    start = await extras(client, sid)
    # Story seed (LLM giả: lời mở đầu không tự được xếp trích xuất) còn 1 lượt chưa ghi nhớ.
    assert start["memories"] == [] and start["suggestions"] == [] and start["unprocessed_turns"] == 1
    assert start["memory_search"] == "hybrid"  # list_models có bge-m3
    assert start["relationship"]["directive"] and not re.search(r"\d", start["relationship"]["directive"])

    reply = await send(client, sid, '"Đi uống trà sữa không?"')
    assert (await extras(client, sid))["pending"] is True
    assert await worker_of(app).run_until_idle() == 2  # extract rồi embed

    # Lời gọi trích xuất: model của story, num_ctx của budget (Ollama không nạp lại model).
    call = llm.json_calls()[0]
    assert call["model"] == "gemma4:12b"
    assert call["options"] == {"num_ctx": 8192, "num_predict": 500, "temperature": 0.3}
    assert "gọi sẵn ly" in call["messages"][-1].content

    data = await extras(client, sid)
    assert data["pending"] is False and data["unprocessed_turns"] == 1
    # Chỉ giữ 2 thay đổi lớn nhất (rung động +1 bị bỏ).
    assert rel(data) == plus(rel(start), affection=3, trust=2)
    assert data["relationship"]["directive"] and not re.search(r"\d", data["relationship"]["directive"])
    assert (data["location"], data["in_world_time"]) == ("Quán trà sữa đầu ngõ", "Chiều tan học")
    # Phase 3b: không có gợi ý tự động; chỉ khi người chơi bấm "Nhận gợi ý".
    assert data["suggestions"] == []
    got = await ok(await client.post(f"/api/stories/{sid}/suggestions"))
    # Ngoặc kép bọc cả câu bị bỏ; gợi ý có ngoặc bên trong giữ nguyên.
    assert got == {"items": ["Gợi ý 1.1", 'Tôi cười. "Gợi ý 1.2"', "Gợi ý 1.3"]}
    sug_call = llm.json_calls()[-1]
    assert sug_call["model"] == "gemma4:12b" and sug_call["options"]["num_ctx"] == 8192
    assert "[Thought" not in sug_call["messages"][-1].content  # người chơi không biết suy nghĩ thầm
    assert (await extras(client, sid))["suggestions"] == got["items"]
    # "Gợi ý khác": thay gợi ý cũ, prompt dặn không lặp lại chúng.
    again = await ok(await client.post(f"/api/stories/{sid}/suggestions"))
    assert again["items"][0] == "Gợi ý 2.1"
    assert "Gợi ý 1.1" in llm.json_calls()[-1]["messages"][-1].content
    assert (await extras(client, sid))["suggestions"] == again["items"]
    events = repo_of(app).message_state_events(reply["id"])
    assert [e.kind for e in events].count("suggestions") == 1
    kinds = {m["kind"]: m for m in data["memories"]}
    assert set(kinds) == {"memory", "fact"}
    assert kinds["memory"]["importance"] == 4 and kinds["memory"]["turn_index"] == reply["turn_index"]
    assert kinds["fact"]["subject"] == "Lâm Vãn"
    assert {j.kind: j.status for j in repo_of(app).list_jobs(sid)} == {"extract": "done", "embed": "done"}
    assert len(repo_of(app).memory_embeddings(sid, "bge-m3")) == 2
    assert llm.embed_calls and llm.embed_calls[0]["model"] == "bge-m3"

    card = next(s for s in await ok(await client.get("/api/stories")) if s["id"] == sid)
    assert card["location"] == "Quán trà sữa đầu ngõ"
    assert card["dominant_emotion"]["key"] in {"affection", "trust", "attraction", "obsession", "fear", "aversion"}

    # Lượt sau: khối F có cảnh, thái độ và fact (tìm theo từ khoá + vector); gợi ý cũ biến mất.
    second = await send(client, sid, "Tôi uống một ngụm. \"Trà sữa trân châu ngon ghê.\"")
    note = final_note(llm.chat_calls()[-1])
    assert "- Cảnh hiện tại: Quán trà sữa đầu ngõ, Chiều tan học." in note
    assert "- Thái độ của Lạc Dương lúc này:" in note
    assert "- Điều Lạc Dương biết:" in note and "Lâm Vãn mê trà sữa trân châu đường đen" in note
    # Ký ức của lượt 2 vẫn nằm trong cửa sổ lịch sử: không nhắc lại trong "Chuyện cũ".
    assert "Chuyện cũ" not in note
    assert (await extras(client, sid))["suggestions"] == []
    snapshot = await ok(await client.get(f"/api/messages/{second['id']}/snapshot"))
    assert snapshot["state"]["directive"] and snapshot["state"]["scene"]["location"] == "Quán trà sữa đầu ngõ"
    assert any(m["kind"] == "fact" for m in snapshot["state"]["memories"])
    assert snapshot["window_start_turn"] == 0

    await worker_of(app).run_until_idle()
    data = await extras(client, sid)
    assert data["suggestions"] == []
    # Cảnh mới đè nơi chốn; thời gian rỗng = không đổi.
    assert (data["location"], data["in_world_time"]) == ("Thư viện trường", "Chiều tan học")
    # Lời gọi trích xuất thứ hai thấy cảnh hiện tại và fact đã biết (để không ghi lại).
    prompt = llm.json_calls()[-1]["messages"][-1].content
    assert "Quán trà sữa đầu ngõ" in prompt and "Lâm Vãn mê trà sữa trân châu đường đen" in prompt


# ---------------------------------------------------------------------------- regenerate, lật variant, xoá, sửa


async def test_variants_edit_and_delete_roll_state(app: FastAPI, client: httpx.AsyncClient, llm: ScriptedLLM) -> None:
    sid = await first_story(client)
    start = rel(await extras(client, sid))
    reply = await send(client, sid, '"Đi uống trà sữa không?"')
    await worker_of(app).run_until_idle()
    tea = await extras(client, sid)
    assert tea["location"] == "Quán trà sữa đầu ngõ"

    # Regenerate: variant mới (thư viện) thay hiệu ứng của variant cũ.
    regen = await regenerate(client, reply["id"])
    assert "thư viện" in regen["visible_content"] and regen["turn_index"] == reply["turn_index"]
    mid = await extras(client, sid)
    assert rel(mid) == start and mid["memories"] == [] and mid["suggestions"] == [] and mid["location"] is None
    assert mid["pending"] is True
    await worker_of(app).run_until_idle()
    lib = await extras(client, sid)
    assert rel(lib) == plus(start, fear=1, aversion=2)
    assert lib["location"] == "Thư viện trường" and lib["in_world_time"] is None
    assert [m["text"] for m in lib["memories"]] == ["Lạc Dương kéo Lâm Vãn vào thư viện trường trú mưa."]
    assert lib["suggestions"] == []

    # Lật lại variant đầu: hiệu ứng cũ quay lại, không trích xuất lại (đã có).
    calls_before = len(llm.json_calls())
    await ok(await client.post(f"/api/messages/{reply['id']}/variant", json={"variant_index": 0}))
    back = await extras(client, sid)
    assert rel(back) == rel(tea) and back["location"] == "Quán trà sữa đầu ngõ"
    assert {m["text"] for m in back["memories"]} == {m["text"] for m in tea["memories"]}
    assert back["suggestions"] == tea["suggestions"] and back["pending"] is False
    assert await worker_of(app).run_until_idle() == 0 and len(llm.json_calls()) == calls_before

    # Sửa nội dung message của nhân vật: xoá state của nó, trích xuất lại từ nội dung mới.
    edited = REPLY_FOREHEAD
    await ok(await client.patch(f"/api/messages/{reply['id']}", json={"content": edited}))
    cleared = await extras(client, sid)
    assert rel(cleared) == start and cleared["memories"] == [] and cleared["pending"] is True
    await worker_of(app).run_until_idle()
    redo = await extras(client, sid)
    assert rel(redo) == plus(start, affection=2, attraction=2)  # nhung nhớ +1 bị bỏ (chỉ 2 thay đổi)
    assert [m["text"] for m in redo["memories"]] == ["Lạc Dương gõ trán Lâm Vãn, bảo cô uống chậm."]
    assert redo["location"] is None and redo["suggestions"] == []  # "không đổi" = không có cảnh mới
    assert "gõ nhẹ lên trán" in llm.json_calls()[-1]["messages"][-1].content

    # Xoá lượt: CASCADE xoá event, ký ức, job của cả hai variant.
    repo = repo_of(app)
    await ok(await client.delete(f"/api/messages/{reply['id']}"))
    gone = await extras(client, sid)
    assert rel(gone) == start and gone["memories"] == [] and gone["location"] is None and gone["suggestions"] == []
    assert repo.state_events(sid) == [] and repo.list_jobs(sid, statuses=("queued", "running")) == []
    count = repo.conn.execute("SELECT COUNT(*) FROM memories WHERE story_id = ?", (sid,)).fetchone()[0]
    assert count == 0
    assert repo.conn.execute("SELECT COUNT(*) FROM memories_fts WHERE memories_fts MATCH '\"trà\"'").fetchone()[0] == 0


# ---------------------------------------------------------------------------- ưu tiên lượt chat


async def test_chat_stream_preempts_inflight_job(app: FastAPI, client: httpx.AsyncClient, llm: ScriptedLLM) -> None:
    sid = await first_story(client)
    first = await send(client, sid, '"Đi uống trà sữa không?"')
    repo = repo_of(app)
    job = repo.list_jobs(sid, statuses=("queued",))[0]

    llm.gate = asyncio.Event()
    runner = asyncio.create_task(worker_of(app).run_once())
    await asyncio.wait_for(llm.json_started.wait(), 5)
    assert repo.get_job(job.id).status == "running"

    # Người chơi gửi tiếp: job đang chạy bị huỷ, về hàng đợi, không tính attempts.
    second = await send(client, sid, '"Thôi về đi."')
    await asyncio.wait_for(runner, 5)
    assert llm.json_cancelled == 1
    requeued = repo.get_job(job.id)
    assert (requeued.status, requeued.attempts) == ("queued", 0)
    assert (await extras(client, sid))["pending"] is True

    # Stream xong: worker chạy tiếp, xong cả hai lượt theo thứ tự.
    llm.gate = None
    await worker_of(app).run_until_idle()
    extract_jobs = [j for j in repo.list_jobs(sid) if j.kind == "extract"]
    assert [(j.message_id, j.status, j.attempts) for j in extract_jobs] == [
        (first["id"], "done", 1),
        (second["id"], "done", 1),
    ]
    data = await extras(client, sid)
    assert data["pending"] is False and data["unprocessed_turns"] == 1  # lời mở đầu của story seed


async def test_worker_waits_while_streaming(app: FastAPI, client: httpx.AsyncClient) -> None:
    sid = await first_story(client)
    await send(client, sid, '"Đi uống trà sữa không?"')
    jobs = app.state.jobs
    jobs.generation_started(sid)
    try:
        assert await worker_of(app).run_once() is None  # đang có stream: không bắt đầu job
    finally:
        jobs.generation_finished(sid)
    assert await worker_of(app).run_once() is not None


# ---------------------------------------------------------------------------- story cũ: dựng lại + tóm tắt


async def test_rebuild_old_story_with_summary(tmp_path: Path) -> None:
    """Story dài có trước Phase 3 (không event, không job): /extras mời dựng lại, rebuild xếp extract theo lượt
    rồi summarize; sau đó prompt có tóm tắt (khối C) và ký ức cũ nằm ngoài cửa sổ (khối F)."""
    llm = ScriptedLLM([REPLY_TEA, REPLY_FOREHEAD], models=[])  # không có embed model: chỉ tìm theo từ khoá
    application = create_app(make_settings(tmp_path, num_ctx=3000), llm)
    async with application.router.lifespan_context(application):
        repo = repo_of(application)
        async with owner_client(application, base_url="http://t") as client:
            sid = await first_story(client)
            filler = " Gió thổi qua hàng cây, lá rơi đầy sân trường." * 25
            await send(client, sid, '"Đi uống trà sữa không?"')
            for i in range(7):
                await send(client, sid, f'"Lượt {i}."{filler}')
            last = repo.active_messages(sid)[-1]
            assert last.prompt_snapshot is not None and last.prompt_snapshot["window_start_turn"] > 2
            # Giả làm story cũ: chưa từng trích xuất.
            repo.conn.execute("DELETE FROM jobs")
            repo.conn.commit()
            data = await extras(client, sid)
            assert data["unprocessed_turns"] == 9 and data["pending"] is False and data["memories"] == []
            assert data["memory_search"] == "keyword"

            queued = (await ok(await client.post(f"/api/stories/{sid}/state/rebuild")))["queued"]
            jobs = repo.list_jobs(sid, statuses=("queued",))
            assert queued == len(jobs) == 10 and [j.kind for j in jobs] == ["extract"] * 9 + ["summarize"]
            turns = [repo.get_message(j.message_id or 0, account_id=ANY_ACCOUNT).turn_index for j in jobs[:-1]]
            assert turns == sorted(turns)
            assert (await ok(await client.post(f"/api/stories/{sid}/state/rebuild")))["queued"] == 0

            await worker_of(application).run_until_idle()
            assert [j.status for j in repo.list_jobs(sid)] == ["done"] * 10
            assert not any(j.kind == "embed" for j in repo.list_jobs(sid))
            data = await extras(client, sid)
            assert data["unprocessed_turns"] == 0 and data["summary"] and data["summary"].startswith("Tóm tắt")
            # Lượt 2 (trà sữa) được trích xuất với state tính tới lượt trước nó.
            assert data["location"] == "Quán trà sữa đầu ngõ"

            await send(client, sid, '"Mai lại đi trà sữa nhé."')
            call = llm.chat_calls()[-1]
            system, note = str(call["messages"][0].content), final_note(call)
            assert "Những gì đã xảy ra trước đó:" in system and data["summary"] in system
            assert "- Chuyện cũ Lạc Dương còn nhớ" in note
            assert "Lạc Dương mời Lâm Vãn ly trà sữa trân châu đường đen ở quán đầu ngõ." in note


# ---------------------------------------------------------------------------- account


async def test_other_accounts_state_is_isolated(app: FastAPI, client: httpx.AsyncClient, llm: ScriptedLLM) -> None:
    repo = repo_of(app)
    other = repo.create_account("khac", "Người khác")
    assert other.id is not None
    card = repo.create_card(load_seed_card().model_copy(update={"name": "Nhân vật lạ"}), account_id=other.id)
    persona = repo.create_persona(Persona(name="Persona lạ", gender="female"), account_id=other.id)
    assert card.id and persona.id
    story = create_story_for(repo, card.id, persona.id, model_name="m", account_id=other.id)
    assert story.id is not None
    greeting = repo.active_messages(story.id)[0]
    saved = repo.replace_extraction(
        greeting.id or 0, [], [NewMemory(kind="fact", text="Persona lạ mê trà sữa trân châu đường đen", subject="x")]
    )
    assert saved is not None and saved[0].id is not None
    other_memory = saved[0].id
    repo.enqueue_job(story.id, "embed", None)

    for method, path in (
        ("GET", f"/api/stories/{story.id}/extras"),
        ("POST", f"/api/stories/{story.id}/state/rebuild"),
        ("DELETE", f"/api/stories/{story.id}/memories/{other_memory}"),
    ):
        assert (await client.request(method, path)).status_code == 404, path
    sid = await first_story(client)
    assert (await client.delete(f"/api/stories/{sid}/memories/{other_memory}")).status_code == 404
    assert repo.get_memory(other_memory).text.startswith("Persona lạ")

    # Ký ức của story khác không lọt vào prompt hay /extras của story này.
    await send(client, sid, '"Trà sữa trân châu đường đen không?"')
    note = final_note(llm.chat_calls()[-1])
    assert "Persona lạ" not in note
    await worker_of(app).run_until_idle()
    assert all("Persona lạ" not in m["text"] for m in (await extras(client, sid))["memories"])
    assert story.id not in {s["id"] for s in await ok(await client.get("/api/stories"))}
