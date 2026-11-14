"""Test API + ChatService: FakeLLM, DB tạm, httpx.AsyncClient qua ASGITransport, đọc body SSE."""
from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from lyris.api.app import create_app
from lyris.api.sse import format_event
from lyris.chat.service import Busy, ChatEvent, ChatService, EmptyContent, InvalidOperation
from lyris.config import Settings
from lyris.db.repo import ANY_ACCOUNT, NotFound, Repo
from lyris.llm.base import LLMError
from lyris.llm.fake import FakeLLM
from lyris.llm.ollama import OllamaClient
from tests.authutil import owner_asgi_headers, owner_client

REPLY_1 = (
    "Lạc Dương khẽ cúi xuống, kéo lại chiếc áo khoác đang trượt khỏi vai cô.\n\n"
    "\"Ngủ đến chảy nước miếng rồi đấy, Vãn Vãn.\"\n\n"
    "[Thought: Ngốc thật, ngủ ở đâu cũng được.]"
)
REPLY_2 = (
    "Anh cầm lấy cặp sách của cô, thuận tay xoa nhẹ đỉnh đầu cô.\n\n"
    "\"Đi thôi, căn tin sắp đóng cửa rồi.\"\n\n"
    "[Thought: Hôm nay cô ấy có vẻ mệt.]"
)
REPLY_3 = "Anh khẽ nhíu mày. \"Lại thức khuya?\" [Thought: Phải bắt cô ấy ngủ sớm.] Anh rút điện thoại ra."
LONG_REPLY = ("Lạc Dương lặng lẽ nhìn cô thật lâu, ánh hoàng hôn rơi trên hàng mi anh. " * 12) + (
    "[Thought: Không muốn để cô ấy đi.]"
)

USER_TEXT = '*Dụi mắt, ngồi dậy* "Dương Dương, mấy giờ rồi?"'


# ---------------------------------------------------------------------------- helpers / fixtures


def parse_sse(body: str) -> list[tuple[str, dict[str, Any]]]:
    events: list[tuple[str, dict[str, Any]]] = []
    for block in body.split("\n\n"):
        if not block.strip():
            continue
        name: str | None = None
        data: dict[str, Any] | None = None
        for line in block.split("\n"):
            if line.startswith("event: "):
                name = line[len("event: ") :]
            elif line.startswith("data: "):
                data = json.loads(line[len("data: ") :])
            else:
                raise AssertionError(f"Dòng SSE lạ: {line!r}")
        assert name is not None and data is not None, block
        events.append((name, data))
    return events


def names(events: list[tuple[str, dict[str, Any]]]) -> list[str]:
    out: list[str] = []
    for name, _ in events:
        if name == "delta" and out and out[-1] == "delta*":
            continue
        out.append("delta*" if name == "delta" else name)
    return out


def joined(events: list[tuple[str, dict[str, Any]]], kind: str) -> str:
    return "".join(d["text"] for n, d in events if n == "delta" and d["kind"] == kind)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        db_path=tmp_path / "lyris.db",
        ollama_url="http://127.0.0.1:9",
        chat_model="gemma4:12b",
        num_ctx=8192,
        # Phase 2: không bao giờ đụng data/avatars thật (app dọn ảnh tạm khi khởi động).
        avatars_dir=tmp_path / "avatars",
    )


@pytest.fixture
def fake() -> FakeLLM:
    return FakeLLM(replies=[REPLY_1, REPLY_2, REPLY_3])


@pytest.fixture
async def app(settings: Settings, fake: FakeLLM) -> AsyncIterator[FastAPI]:
    application = create_app(settings, fake)
    async with application.router.lifespan_context(application):
        yield application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with owner_client(app, base_url="http://test") as c:
        yield c


def repo_of(app: FastAPI) -> Repo:
    repo: Repo = app.state.repo
    return repo


def chat_of(app: FastAPI) -> ChatService:
    chat: ChatService = app.state.chat
    return chat


async def story_id_of(client: httpx.AsyncClient) -> int:
    resp = await client.get("/api/stories")
    assert resp.status_code == 200
    return int(resp.json()[0]["id"])


async def send(client: httpx.AsyncClient, story_id: int, content: str) -> list[tuple[str, dict[str, Any]]]:
    resp = await client.post(f"/api/stories/{story_id}/messages", json={"content": content})
    assert resp.status_code == 200, resp.text
    return parse_sse(resp.text)


async def messages(client: httpx.AsyncClient, story_id: int) -> list[dict[str, Any]]:
    resp = await client.get(f"/api/stories/{story_id}/messages")
    assert resp.status_code == 200
    return list(resp.json())


# ---------------------------------------------------------------------------- SSE format


def test_format_event_is_one_json_line() -> None:
    text = format_event("delta", {"kind": "text", "text": "dòng 1\ndòng 2"})
    assert text == 'event: delta\ndata: {"kind": "text", "text": "dòng 1\\ndòng 2"}\n\n'


# ---------------------------------------------------------------------------- stories


async def test_seed_story_and_greeting(client: httpx.AsyncClient) -> None:
    stories = (await client.get("/api/stories")).json()
    assert len(stories) == 1
    assert stories[0]["card_name"] == "Lạc Dương"
    assert stories[0]["persona_name"] == "Lâm Vãn"
    msgs = await messages(client, stories[0]["id"])
    assert len(msgs) == 1
    assert msgs[0]["role"] == "assistant" and msgs[0]["turn_index"] == 0
    assert "prompt_snapshot" not in msgs[0]


async def test_create_get_patch_story(client: httpx.AsyncClient) -> None:
    resp = await client.post("/api/stories", json={"title": "  Lần thứ hai  "})
    assert resp.status_code == 200
    created = resp.json()
    assert created["title"] == "Lần thứ hai"
    assert created["card_name"] == "Lạc Dương"

    resp = await client.post("/api/stories")  # không có body
    assert resp.status_code == 200
    newest = resp.json()

    stories = (await client.get("/api/stories")).json()
    assert [s["id"] for s in stories][:2] == [newest["id"], created["id"]]

    detail = (await client.get(f"/api/stories/{created['id']}")).json()
    assert set(detail) == {"story", "card", "persona"}
    assert detail["card"]["name"] == "Lạc Dương"
    assert detail["persona"]["name"] == "Lâm Vãn"
    assert len(await messages(client, created["id"])) == 1  # lời mở đầu

    resp = await client.patch(f"/api/stories/{created['id']}", json={"mode": "dm", "scenario": "Tối thứ sáu."})
    assert resp.status_code == 200
    assert resp.json()["mode"] == "dm" and resp.json()["scenario"] == "Tối thứ sáu."

    assert created["thought_style"] == "inline"
    resp = await client.patch(f"/api/stories/{created['id']}", json={"thought_style": "end"})
    assert resp.status_code == 200 and resp.json()["thought_style"] == "end"
    resp = await client.patch(f"/api/stories/{created['id']}", json={"thought_style": "middle"})
    assert resp.status_code == 422

    resp = await client.patch(f"/api/stories/{created['id']}", json={"mode": "voice"})
    assert resp.status_code == 422
    assert isinstance(resp.json()["detail"], str)

    resp = await client.patch(f"/api/stories/{created['id']}", json={"title": "   "})
    assert resp.status_code == 422

    resp = await client.get("/api/stories/9999")
    assert resp.status_code == 404
    assert "9999" in resp.json()["detail"]
    assert (await client.patch("/api/stories/9999", json={"mode": "dm"})).status_code == 404
    assert (await client.get("/api/stories/9999/messages")).status_code == 404


# ---------------------------------------------------------------------------- send


async def test_full_send_flow(app: FastAPI, client: httpx.AsyncClient, fake: FakeLLM) -> None:
    story_id = await story_id_of(client)
    resp = await client.post(f"/api/stories/{story_id}/messages", json={"content": USER_TEXT})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    assert resp.headers["cache-control"] == "no-cache"
    assert resp.headers["x-accel-buffering"] == "no"

    events = parse_sse(resp.text)
    assert names(events) == ["user_message", "start", "delta*", "done"]

    user = events[0][1]["message"]
    assert user["role"] == "user" and user["turn_index"] == 1
    assert user["raw_content"] == USER_TEXT and user["visible_content"] == USER_TEXT
    assert user["directive"] is None
    assert events[1][1] == {"turn_index": 2, "variant_index": 0}

    done = events[-1][1]["message"]
    assert "prompt_snapshot" not in done
    assert done["role"] == "assistant" and done["turn_index"] == 2 and done["variant_index"] == 0
    assert done["visible_content"] == joined(events, "text")
    assert done["thought"] == joined(events, "thought") == "Ngốc thật, ngủ ở đâu cũng được."
    assert "[Thought" not in done["visible_content"]

    # Bản ghi trong DB đủ trường.
    saved = repo_of(app).get_message(done["id"], account_id=ANY_ACCOUNT)
    assert saved.raw_content == saved.model_output == REPLY_1
    assert saved.mode == "story"
    assert saved.model_name == "gemma4:12b"
    assert saved.gen_stats is not None and saved.gen_stats.aborted is False
    assert saved.gen_stats.done_reason == "stop" and saved.gen_stats.output_tokens
    assert saved.prompt_snapshot is not None
    assert saved.prompt_snapshot["messages"][0]["role"] == "system"
    assert saved.prompt_snapshot["options"]["num_predict"] == 900
    assert saved.prompt_snapshot["stop"][0] == "Lâm Vãn:"

    # LLM được gọi đúng prompt đó.
    call = fake.calls[-1]
    assert call["model"] == "gemma4:12b"
    assert [t.model_dump() for t in call["messages"]] == saved.prompt_snapshot["messages"]
    assert USER_TEXT in call["messages"][-1].content

    msgs = await messages(client, story_id)
    assert [m["turn_index"] for m in msgs] == [0, 1, 2]
    assert all("prompt_snapshot" not in m for m in msgs)

    snap = await client.get(f"/api/messages/{done['id']}/snapshot")
    assert snap.status_code == 200
    assert snap.json() == saved.prompt_snapshot
    assert (await client.get(f"/api/messages/{user['id']}/snapshot")).status_code == 404
    assert (await client.get("/api/messages/9999/snapshot")).status_code == 404


async def test_send_unknown_story_and_empty(client: httpx.AsyncClient) -> None:
    resp = await client.post("/api/stories/9999/messages", json={"content": "Chào"})
    assert resp.status_code == 404
    story_id = await story_id_of(client)
    # Nội dung rỗng là dữ liệu sai: 422, giống PATCH /api/messages/{id}.
    for content in ["   ", "(( ))", ""]:
        resp = await client.post(f"/api/stories/{story_id}/messages", json={"content": content})
        assert resp.status_code == 422, content
        assert "trống" in resp.json()["detail"]
    resp = await client.post(f"/api/stories/{story_id}/messages", json={})
    assert resp.status_code == 422
    assert isinstance(resp.json()["detail"], str)
    assert len(await messages(client, story_id)) == 1


async def test_directive_handling(client: httpx.AsyncClient, fake: FakeLLM) -> None:
    story_id = await story_id_of(client)
    events = await send(client, story_id, "Cô ngáp một cái. ((Lạc Dương nhắc chuyện thi giữa kỳ))")
    user = events[0][1]["message"]
    assert user["visible_content"] == "Cô ngáp một cái."
    assert user["directive"] == "Lạc Dương nhắc chuyện thi giữa kỳ"
    assert user["raw_content"] == "Cô ngáp một cái. ((Lạc Dương nhắc chuyện thi giữa kỳ))"

    last_user = fake.calls[-1]["messages"][-1]
    assert last_user.role == "user"
    assert "Lạc Dương nhắc chuyện thi giữa kỳ" in last_user.content
    assert "Chỉ đạo của người chơi" in last_user.content
    assert all("((" not in t.content for t in fake.calls[-1]["messages"])

    # Chỉ có chỉ đạo, không có chữ: vẫn hợp lệ.
    events = await send(client, story_id, "((Cảnh chuyển sang buổi tối ở căn tin))")
    user = events[0][1]["message"]
    assert user["visible_content"] == "" and user["directive"] == "Cảnh chuyển sang buổi tối ở căn tin"
    assert names(events) == ["user_message", "start", "delta*", "done"]


async def test_dm_mode_reply(app: FastAPI, client: httpx.AsyncClient, fake: FakeLLM) -> None:
    story_id = await story_id_of(client)
    assert (await client.patch(f"/api/stories/{story_id}", json={"mode": "dm"})).status_code == 200
    events = await send(client, story_id, "Cậu đang ở đâu đấy?")
    assert events[0][1]["message"]["mode"] == "dm"
    done = events[-1][1]["message"]
    assert done["mode"] == "dm"
    assert fake.calls[-1]["options"]["num_predict"] == 200


# ---------------------------------------------------------------------------- lỗi + thử lại


async def test_error_then_respond(app: FastAPI, client: httpx.AsyncClient, fake: FakeLLM) -> None:
    story_id = await story_id_of(client)
    fake.error = LLMError("Không kết nối được Ollama ở http://127.0.0.1:11434. Hãy mở app Ollama.", kind="connect")
    events = await send(client, story_id, USER_TEXT)
    assert names(events) == ["user_message", "start", "error"]
    # Phase 3b: câu dễ hiểu (không nhắc Ollama/model), chi tiết kỹ thuật ở "technical".
    detail, technical = events[-1][1]["detail"], events[-1][1]["technical"]
    assert "Ollama" not in detail and "model" not in detail.lower() and "kết nối" in detail
    assert "Ollama" in technical
    msgs = await messages(client, story_id)
    assert [m["role"] for m in msgs] == ["assistant", "user"]  # lượt người chơi vẫn còn
    assert not chat_of(app).is_busy(story_id)

    fake.error = None
    resp = await client.post(f"/api/stories/{story_id}/reply")
    assert resp.status_code == 200
    events = parse_sse(resp.text)
    assert names(events) == ["start", "delta*", "done"]
    assert events[0][1] == {"turn_index": 2, "variant_index": 0}
    assert [m["role"] for m in await messages(client, story_id)] == ["assistant", "user", "assistant"]

    # Lượt cuối đã là của AI: không có gì để trả lời.
    resp = await client.post(f"/api/stories/{story_id}/reply")
    assert resp.status_code == 409
    assert (await client.post("/api/stories/9999/reply")).status_code == 404


async def test_two_pending_user_turns_are_merged(client: httpx.AsyncClient, fake: FakeLLM) -> None:
    story_id = await story_id_of(client)
    fake.error = LLMError("Ollama lỗi")
    await send(client, story_id, "Câu thứ nhất.")
    await send(client, story_id, "Câu thứ hai.")
    fake.error = None
    events = parse_sse((await client.post(f"/api/stories/{story_id}/reply")).text)
    assert events[-1][0] == "done"
    last = fake.calls[-1]["messages"][-1]
    assert "Câu thứ nhất." in last.content and "Câu thứ hai." in last.content


async def test_empty_model_output_is_not_saved(client: httpx.AsyncClient, fake: FakeLLM) -> None:
    story_id = await story_id_of(client)
    fake.replies = ["   "]
    events = await send(client, story_id, USER_TEXT)
    assert names(events)[-1] == "error"
    assert [m["role"] for m in await messages(client, story_id)] == ["assistant", "user"]


# ---------------------------------------------------------------------------- regenerate + variant


async def test_regenerate_and_switch_variants(app: FastAPI, client: httpx.AsyncClient) -> None:
    story_id = await story_id_of(client)
    first = (await send(client, story_id, USER_TEXT))[-1][1]["message"]

    resp = await client.post(f"/api/messages/{first['id']}/regenerate")
    assert resp.status_code == 200
    events = parse_sse(resp.text)
    assert names(events) == ["start", "delta*", "done"]
    assert events[0][1] == {"turn_index": first["turn_index"], "variant_index": 1}
    second = events[-1][1]["message"]
    assert second["variant_index"] == 1 and second["variant_count"] == 2 and second["is_active"]
    assert second["raw_content"] == REPLY_2
    saved = repo_of(app).get_message(second["id"], account_id=ANY_ACCOUNT)
    assert saved.prompt_snapshot is not None and saved.model_output == REPLY_2

    msgs = await messages(client, story_id)
    assert len(msgs) == 3 and msgs[-1]["id"] == second["id"]

    # Regenerate từ variant cũ (không active) vẫn là lượt cuối → variant 2.
    events = parse_sse((await client.post(f"/api/messages/{first['id']}/regenerate")).text)
    assert events[-1][1]["message"]["variant_index"] == 2

    resp = await client.post(f"/api/messages/{second['id']}/variant", json={"variant_index": 0})
    assert resp.status_code == 200
    switched = resp.json()
    assert switched["id"] == first["id"] and switched["is_active"] and switched["variant_count"] == 3
    assert "prompt_snapshot" not in switched
    assert (await messages(client, story_id))[-1]["id"] == first["id"]

    resp = await client.post(f"/api/messages/{first['id']}/variant", json={"variant_index": 7})
    assert resp.status_code == 404
    resp = await client.post(f"/api/messages/{first['id']}/variant", json={"variant_index": -1})
    assert resp.status_code == 422
    user_id = (await messages(client, story_id))[1]["id"]
    resp = await client.post(f"/api/messages/{user_id}/variant", json={"variant_index": 0})
    assert resp.status_code == 409


async def test_regenerate_invalid_targets(client: httpx.AsyncClient) -> None:
    story_id = await story_id_of(client)
    greeting = (await messages(client, story_id))[0]
    resp = await client.post(f"/api/messages/{greeting['id']}/regenerate")
    assert resp.status_code == 409
    assert "mở đầu" in resp.json()["detail"]

    first = (await send(client, story_id, USER_TEXT))[-1][1]["message"]
    await send(client, story_id, "Ăn lẩu đi.")
    msgs = await messages(client, story_id)
    assert len(msgs) == 5

    resp = await client.post(f"/api/messages/{first['id']}/regenerate")  # không phải lượt cuối
    assert resp.status_code == 409
    assert "lượt cuối" in resp.json()["detail"]
    resp = await client.post(f"/api/messages/{msgs[3]['id']}/regenerate")  # lượt của người chơi
    assert resp.status_code == 409
    resp = await client.post(f"/api/messages/{greeting['id']}/variant", json={"variant_index": 0})
    assert resp.status_code == 409
    assert (await client.post("/api/messages/9999/regenerate")).status_code == 404


# ---------------------------------------------------------------------------- bận


async def test_concurrent_send_is_busy(app: FastAPI, client: httpx.AsyncClient, fake: FakeLLM) -> None:
    story_id = await story_id_of(client)
    fake.delay = 0.02
    first = asyncio.create_task(
        client.post(f"/api/stories/{story_id}/messages", json={"content": USER_TEXT})
    )
    chat = chat_of(app)
    for _ in range(200):
        if chat.is_busy(story_id):
            break
        await asyncio.sleep(0.005)
    assert chat.is_busy(story_id)

    resp = await client.post(f"/api/stories/{story_id}/messages", json={"content": "Còn tớ thì sao?"})
    assert resp.status_code == 409
    assert "đang trả lời" in resp.json()["detail"]
    assert (await client.post(f"/api/stories/{story_id}/reply")).status_code == 409
    greeting_id = (await messages(client, story_id))[0]["id"]
    assert (await client.patch(f"/api/messages/{greeting_id}", json={"content": "Sửa"})).status_code == 409
    assert (await client.delete(f"/api/messages/{greeting_id}")).status_code == 409

    # Phase 4b (docs/auth.md §5.1): mỗi tài khoản một lượt sinh cùng lúc; story khác của cùng tài khoản nhận
    # 409 (không ghi gì) cho tới khi lượt kia xong.
    other = (await client.post("/api/stories", json={"title": "Story khác"})).json()
    fake.delay = 0.0
    busy = await client.post(f"/api/stories/{other['id']}/messages", json={"content": "Chào cậu."})
    assert busy.status_code == 409
    assert busy.json()["detail"] == "Lạc Dương vẫn đang trả lời bạn ở story khác. Đợi xong rồi gửi tiếp nhé."
    assert len(await messages(client, other["id"])) == 1  # chỉ lời mở đầu

    resp = await first
    assert resp.status_code == 200
    assert names(parse_sse(resp.text)) == ["user_message", "start", "delta*", "done"]
    assert not chat.is_busy(story_id)
    other_events = await send(client, other["id"], "Chào cậu.")
    assert other_events[-1][0] == "done"
    assert (await send(client, story_id, "Đi thôi."))[-1][0] == "done"


async def test_busy_raised_before_any_event(app: FastAPI, fake: FakeLLM) -> None:
    chat = chat_of(app)
    story_id = repo_of(app).list_stories(account_id=ANY_ACCOUNT)[0].id
    assert story_id is not None
    gen1 = chat.send(story_id, USER_TEXT)
    first = await anext(gen1)
    assert first.name == "user_message"
    gen2 = chat.send(story_id, "Chen ngang")
    with pytest.raises(Busy):
        await anext(gen2)
    events = [first] + [e async for e in gen1]
    assert events[-1].name == "done"
    assert not chat.is_busy(story_id)
    # Lượt chen ngang không được lưu.
    assert [m.visible_content for m in repo_of(app).active_messages(story_id)][1] == USER_TEXT
    assert len(repo_of(app).active_messages(story_id)) == 3


# ---------------------------------------------------------------------------- sửa / xoá / đánh giá


async def test_edit_assistant_and_user(app: FastAPI, client: httpx.AsyncClient) -> None:
    story_id = await story_id_of(client)
    events = await send(client, story_id, USER_TEXT)
    user = events[0][1]["message"]
    reply = events[-1][1]["message"]

    resp = await client.patch(
        f"/api/messages/{reply['id']}",
        json={"content": "Anh bật cười.\n\n[Thought: Ngốc thật.]\n"},
    )
    assert resp.status_code == 200
    edited = resp.json()
    assert edited["raw_content"] == "Anh bật cười.\n\n[Thought: Ngốc thật.]"
    assert edited["visible_content"] == "Anh bật cười."
    assert edited["thought"] == "Ngốc thật."
    assert edited["edited_at"]
    assert edited["model_output"] == REPLY_1
    assert "prompt_snapshot" not in edited
    repo = repo_of(app)
    assert repo.get_message(reply["id"], account_id=ANY_ACCOUNT).prompt_snapshot is not None
    history = repo.message_edits(reply["id"])
    assert len(history) == 1
    assert history[0]["before_raw"] == REPLY_1

    resp = await client.patch(f"/api/messages/{user['id']}", json={"content": "Xin chào ((nói thật nhỏ))"})
    assert resp.status_code == 200
    edited_user = resp.json()
    assert edited_user["visible_content"] == "Xin chào"
    assert edited_user["directive"] == "nói thật nhỏ"
    assert edited_user["thought"] is None

    for empty in ["  ", "(( ))"]:
        resp = await client.patch(f"/api/messages/{user['id']}", json={"content": empty})
        assert resp.status_code == 422, empty
        assert resp.json()["detail"] == "Nội dung không được để trống."
    resp = await client.patch(f"/api/messages/{reply['id']}", json={"content": "[Thought: ]"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "Nội dung không được để trống."
    assert (await client.patch("/api/messages/9999", json={"content": "x"})).status_code == 404

    # Bản sửa được dùng ở lượt sau.
    await send(client, story_id, "Ừm.")
    assert any("Anh bật cười." in t.content for t in app.state.llm.calls[-1]["messages"])


async def test_delete_from_here(app: FastAPI, client: httpx.AsyncClient) -> None:
    story_id = await story_id_of(client)
    await send(client, story_id, USER_TEXT)
    second = await send(client, story_id, "Ăn lẩu đi.")
    last = second[-1][1]["message"]
    # Thêm một variant cho lượt cuối: xoá phải xoá cả hai.
    await client.post(f"/api/messages/{last['id']}/regenerate")
    msgs = await messages(client, story_id)
    assert [m["turn_index"] for m in msgs] == [0, 1, 2, 3, 4]

    resp = await client.delete(f"/api/messages/{msgs[3]['id']}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["deleted"] == 3  # lượt 3 + hai variant của lượt 4
    assert [m["turn_index"] for m in body["messages"]] == [0, 1, 2]
    assert all("prompt_snapshot" not in m for m in body["messages"])
    assert (await client.delete(f"/api/messages/{msgs[3]['id']}")).status_code == 404

    # Gửi tiếp sau khi tua lại.
    events = await send(client, story_id, "Thôi, về ký túc xá.")
    assert events[0][1]["message"]["turn_index"] == 3
    assert events[-1][1]["message"]["turn_index"] == 4


async def test_feedback(client: httpx.AsyncClient) -> None:
    story_id = await story_id_of(client)
    events = await send(client, story_id, USER_TEXT)
    user = events[0][1]["message"]
    reply = events[-1][1]["message"]

    resp = await client.put(f"/api/messages/{reply['id']}/feedback", json={"rating": "up", "note": "Đúng giọng"})
    assert resp.status_code == 200 and resp.json()["rating"] == "up"
    assert (await messages(client, story_id))[-1]["rating"] == "up"

    resp = await client.put(f"/api/messages/{reply['id']}/feedback", json={"rating": None})
    assert resp.status_code == 200 and resp.json()["rating"] is None

    resp = await client.put(f"/api/messages/{reply['id']}/feedback", json={"rating": "meh"})
    assert resp.status_code == 422
    resp = await client.put(f"/api/messages/{user['id']}/feedback", json={"rating": "down"})
    assert resp.status_code == 409
    resp = await client.put("/api/messages/9999/feedback", json={"rating": "down"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------- health


async def test_health_unreachable_ollama(settings: Settings) -> None:
    app = create_app(settings, OllamaClient("http://127.0.0.1:9", timeout=5))
    async with app.router.lifespan_context(app):
        async with owner_client(app, base_url="http://test") as c:
            resp = await c.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["chat_model"] == "gemma4:12b"
    assert body["ollama"]["reachable"] is False
    assert body["ollama"]["models"] == []
    assert "Ollama" in body["ollama"]["error"]


async def test_health_reports_missing_model(settings: Settings) -> None:
    class ListingLLM(FakeLLM):
        async def list_models(self) -> list[str]:
            return ["gemma4:e4b"]

    app = create_app(settings, ListingLLM())
    async with app.router.lifespan_context(app):
        async with owner_client(app, base_url="http://test") as c:
            body = (await c.get("/api/health")).json()
    assert body["ollama"]["reachable"] is True
    assert body["ollama"]["models"] == ["gemma4:e4b"]
    assert "ollama pull gemma4:12b" in body["ollama"]["error"]


async def test_health_with_fake_llm(client: httpx.AsyncClient) -> None:
    body = (await client.get("/api/health")).json()
    assert body["ok"] is True and body["ollama"]["reachable"] is True and body["ollama"]["error"] is None


async def test_no_cors_header(client: httpx.AsyncClient) -> None:
    # Phase 4b (docs/auth.md §3.3): frontend chỉ gọi /api qua proxy của Vite; không còn CORSMiddleware.
    resp = await client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert "access-control-allow-origin" not in resp.headers


# ---------------------------------------------------------------------------- ngắt giữa chừng


def _last_assistant(repo: Repo, story_id: int) -> Any:
    msgs = repo.active_messages(story_id)
    assert msgs[-1].role == "assistant"
    return msgs[-1]


async def test_aclose_mid_stream_persists_partial(app: FastAPI, fake: FakeLLM) -> None:
    fake.replies = [LONG_REPLY]
    fake.chunk_size = 5
    chat, repo = chat_of(app), repo_of(app)
    story_id = repo.list_stories(account_id=ANY_ACCOUNT)[0].id
    assert story_id is not None

    gen = chat.send(story_id, USER_TEXT)
    seen: list[ChatEvent] = []
    async for event in gen:
        seen.append(event)
        if sum(1 for e in seen if e.name == "delta") == 3:
            break
    await gen.aclose()  # client đóng kết nối

    assert not chat.is_busy(story_id)
    partial = _last_assistant(repo, story_id)
    assert partial.turn_index == 2
    assert partial.gen_stats is not None and partial.gen_stats.aborted is True
    assert partial.raw_content and LONG_REPLY.startswith(partial.raw_content)
    assert len(partial.raw_content) < len(LONG_REPLY)
    assert partial.model_output == partial.raw_content
    assert partial.prompt_snapshot is not None


async def test_cancel_while_waiting_for_model_persists_partial(app: FastAPI, fake: FakeLLM) -> None:
    fake.replies = [LONG_REPLY]
    fake.chunk_size = 5
    fake.delay = 0.01
    chat, repo = chat_of(app), repo_of(app)
    story_id = repo.list_stories(account_id=ANY_ACCOUNT)[0].id
    assert story_id is not None
    got_delta = asyncio.Event()

    async def consume() -> None:
        async for event in chat.send(story_id, USER_TEXT):
            if event.name == "delta":
                got_delta.set()

    task = asyncio.create_task(consume())
    await asyncio.wait_for(got_delta.wait(), 5)
    await asyncio.sleep(0.03)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert not chat.is_busy(story_id)
    partial = _last_assistant(repo, story_id)
    assert partial.gen_stats is not None and partial.gen_stats.aborted is True
    assert LONG_REPLY.startswith(partial.raw_content)


async def test_abort_before_any_text_saves_nothing(app: FastAPI, fake: FakeLLM) -> None:
    chat, repo = chat_of(app), repo_of(app)
    story_id = repo.list_stories(account_id=ANY_ACCOUNT)[0].id
    assert story_id is not None
    gen = chat.send(story_id, USER_TEXT)
    assert (await anext(gen)).name == "user_message"
    assert (await anext(gen)).name == "start"
    await gen.aclose()
    assert not chat.is_busy(story_id)
    assert [m.role for m in repo.active_messages(story_id)] == ["assistant", "user"]
    # Thử lại được.
    events = [e async for e in chat.respond(story_id)]
    assert events[-1].name == "done"


async def _post_with_disconnect(app: FastAPI, path: str, payload: dict[str, Any], *, spec_version: str,
                                after_deltas: int) -> list[bytes]:
    """Gọi app trực tiếp bằng ASGI và ngắt kết nối sau `after_deltas` sự kiện delta."""
    body = json.dumps(payload).encode()
    disconnected = asyncio.Event()
    chunks: list[bytes] = []
    request_sent = False

    async def receive() -> dict[str, Any]:
        nonlocal request_sent
        if not request_sent:
            request_sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        await disconnected.wait()
        return {"type": "http.disconnect"}

    async def send(message: dict[str, Any]) -> None:
        if disconnected.is_set():
            raise OSError("client đã ngắt kết nối")
        if message["type"] == "http.response.body":
            chunks.append(message["body"])
            if b"".join(chunks).count(b"event: delta") >= after_deltas:
                disconnected.set()

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": spec_version},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [(b"content-type", b"application/json"), (b"host", b"test"), *owner_asgi_headers(app)],
        "client": ("127.0.0.1", 50000),
        "server": ("test", 80),
        "state": {},
    }
    with contextlib.suppress(OSError, Exception):
        await asyncio.wait_for(app(scope, receive, send), 10)
    return chunks


@pytest.mark.parametrize("spec_version", ["2.3", "2.4"])
async def test_client_disconnect_over_asgi_persists_partial(
    app: FastAPI, fake: FakeLLM, spec_version: str
) -> None:
    fake.replies = [LONG_REPLY]
    fake.chunk_size = 5
    fake.delay = 0.005
    chat, repo = chat_of(app), repo_of(app)
    story_id = repo.list_stories(account_id=ANY_ACCOUNT)[0].id
    assert story_id is not None

    chunks = await _post_with_disconnect(
        app,
        f"/api/stories/{story_id}/messages",
        {"content": USER_TEXT},
        spec_version=spec_version,
        after_deltas=4,
    )
    assert b"event: user_message" in b"".join(chunks)
    assert b"event: done" not in b"".join(chunks)
    # Phần dở được lưu ngay (không chờ thu gom rác), khoá đã nhả.
    assert not chat.is_busy(story_id)
    partial = _last_assistant(repo, story_id)
    assert partial.gen_stats is not None and partial.gen_stats.aborted is True
    assert partial.raw_content and LONG_REPLY.startswith(partial.raw_content)
    assert len(partial.raw_content) < len(LONG_REPLY)


async def test_service_errors_are_typed(app: FastAPI) -> None:
    chat = chat_of(app)
    with pytest.raises(NotFound):
        await anext(chat.send(9999, "Chào"))
    with pytest.raises(NotFound):
        await anext(chat.regenerate(9999))
    story_id = repo_of(app).list_stories(account_id=ANY_ACCOUNT)[0].id
    assert story_id is not None
    with pytest.raises(InvalidOperation):
        await anext(chat.respond(story_id))
    with pytest.raises(EmptyContent):
        await anext(chat.send(story_id, " \n "))
    assert issubclass(EmptyContent, InvalidOperation)
    assert not chat.is_busy(story_id)


async def test_persist_failure_ends_stream_with_error(
    app: FastAPI, fake: FakeLLM, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Lỗi DB bất ngờ khi ghi câu trả lời (ví dụ "database is locked") vẫn kết thúc bằng sự kiện error."""
    import sqlite3

    chat, repo = chat_of(app), repo_of(app)
    story_id = repo.list_stories(account_id=ANY_ACCOUNT)[0].id
    assert story_id is not None
    real_insert = repo.insert_message

    def flaky_insert(msg):  # type: ignore[no-untyped-def]
        if msg.role == "assistant":
            raise sqlite3.OperationalError("database is locked")
        return real_insert(msg)

    monkeypatch.setattr(repo, "insert_message", flaky_insert)
    seen = [e async for e in chat.send(story_id, USER_TEXT)]
    assert seen[0].name == "user_message"
    assert seen[-1].name == "error"
    assert "Không lưu được câu trả lời" in seen[-1].data["detail"]
    assert "database is locked" in seen[-1].data["technical"]
    assert not chat.is_busy(story_id)
    assert [m.role for m in repo.active_messages(story_id)] == ["assistant", "user"]


async def test_validation_detail_is_vietnamese(client: httpx.AsyncClient) -> None:
    story_id = await story_id_of(client)
    resp = await client.post(f"/api/stories/{story_id}/messages", json={"content": "x" * 20_001})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "Dữ liệu không hợp lệ: content: dài quá 20000 ký tự"

    resp = await client.post(f"/api/stories/{story_id}/messages", json={})
    assert resp.json()["detail"] == "Dữ liệu không hợp lệ: content: thiếu trường bắt buộc"

    resp = await client.post(f"/api/stories/{story_id}/messages", json={"content": "a", "x": 1})
    assert resp.json()["detail"] == "Dữ liệu không hợp lệ: x: trường không được hỗ trợ"

    resp = await client.patch(f"/api/stories/{story_id}", json={"mode": "chat"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "Dữ liệu không hợp lệ: mode: phải là một trong: 'story' hoặc 'dm'"

    msgs = await messages(client, story_id)
    resp = await client.post(f"/api/messages/{msgs[0]['id']}/variant", json={"variant_index": -1})
    assert resp.json()["detail"] == "Dữ liệu không hợp lệ: variant_index: phải lớn hơn hoặc bằng 0"


async def test_emoticons_stay_in_player_text(client: httpx.AsyncClient, fake: FakeLLM) -> None:
    story_id = await story_id_of(client)
    events = await send(client, story_id, "Hic :(( cậu không đến thật à? =))")
    user = events[0][1]["message"]
    assert user["visible_content"] == "Hic :(( cậu không đến thật à? =))"
    assert user["directive"] is None
    note = fake.calls[-1]["messages"][-1].content
    assert "Chỉ đạo của người chơi" not in note
    assert "Hic :( cậu không đến thật à? =)" in note  # "((" / "))" vẫn bị gỡ khỏi prompt
