"""Phase 4b (docs/auth.md §8.1): thế giới hai tài khoản dùng chung cho test tách dữ liệu và nhân vật công khai.

Chủ máy A (đã đặt mật khẩu) và thành viên B, mỗi người một client với cookie riêng và header `X-Lyris`:
- A có persona (kèm ảnh), card riêng tư, card công khai (kèm ảnh) có sổ thế giới (mục mọi người biết, mục
  `{{user}}`, mục chỉ nhân vật biết, mục đã tắt), story với card công khai có tin nhắn, ký ức, lore hit,
  đánh giá, prompt snapshot;
- B có persona và một story bắt đầu từ card công khai của A (bản sao), đã chat một lượt.
"""
from __future__ import annotations

import io
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI
from PIL import Image

from lyris.api.app import create_app
from lyris.config import Settings
from lyris.db.repo import ANY_ACCOUNT, NewMemory, Repo
from lyris.llm.fake import FakeLLM
from tests.authutil import add_member, client_for, ensure_owner_password, repo_of

REPLY = "Gió ngoài bến cảng thổi lồng lộng.\n\n[Thought: Lại là cô ấy.]"
PUBLIC_SECRET = "Bí mật của A: từng là hải tặc."
PRIVATE_NAME = "Nhân vật riêng của A"
PUBLIC_NAME = "Hải Đăng"
TRIGGER = "Mình ra bến cảng, nhớ kỷ niệm cũ và bí mật nhỏ."


def png_bytes(size: tuple[int, int] = (40, 40), color: tuple[int, int, int] = (20, 120, 200)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def card_body(name: str, **extra: Any) -> dict[str, Any]:
    return {
        "name": name,
        "role": "Người gác hải đăng",
        "gender": "male",
        "style_profile": "trung_hien_dai",
        "description": "Trầm tính, ít nói.",
        "personality": "Tính cách riêng tư của A.",
        "appearance": "Cao, tóc rối.",
        "background": "Hoàn cảnh riêng tư của A.",
        "goals": "Mục tiêu riêng tư của A.",
        "secrets": PUBLIC_SECRET,
        "speech_style": "Nói chậm.",
        "address_terms": {"self_term": "tôi", "player_term": "cô"},
        "greeting": "Chào {{user}}, tôi là {{char}}.",
        "example_dialogues": "Ví dụ thoại riêng tư.",
        "creator_notes": "Ghi chú người tạo riêng tư.",
        "scenario": "Một hải đăng cuối đảo.",
        "tags": ["biển"],
        "extensions": {
            "lyris": {"narration_character": "hắn", "signature_lines": ["Biển hôm nay lặng."], "khoa_la": 1},
            "khac": {"x": 1},
        },
        **extra,
    }


LORE = [
    {"title": "Bến cảng", "category": "place", "keys": ["bến cảng"], "known_by": ["*"], "content": "Bến cảng cũ."},
    {"title": "Kỷ niệm", "keys": ["kỷ niệm"], "known_by": ["{{user}}"], "content": "Kỷ niệm của {{user}}."},
    {"title": "Bí mật nhỏ", "keys": ["bí mật nhỏ"], "known_by": ["{{char}}"], "content": "Chỉ {{char}} biết điều này."},
    {"title": "Mục đã tắt", "keys": ["đã tắt"], "known_by": ["*"], "content": "Không chép.", "enabled": False},
]


def parse_sse(body: str) -> list[tuple[str, dict[str, Any]]]:
    events: list[tuple[str, dict[str, Any]]] = []
    for block in body.split("\n\n"):
        if not block.strip():
            continue
        name = data = None
        for line in block.split("\n"):
            if line.startswith("event: "):
                name = line[len("event: "):]
            elif line.startswith("data: "):
                data = json.loads(line[len("data: "):])
        assert name is not None and data is not None, block
        events.append((name, data))
    return events


async def ok(resp: httpx.Response) -> Any:
    assert resp.status_code == 200, (resp.request.method, str(resp.request.url), resp.status_code, resp.text)
    return resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text


@dataclass
class World:
    app: FastAPI
    repo: Repo
    avatars_dir: Path
    a: httpx.AsyncClient
    b: httpx.AsyncClient
    a_id: int
    b_id: int
    a_handle: str
    a_persona: int
    a_private: int
    a_public: int
    a_entries: list[int]
    a_story: int
    a_user_message: int
    a_message: int
    a_memory: int
    b_persona: int
    b_story: int
    b_copy: int
    b_message: int

    def dump(self) -> str:
        """Toàn bộ DB dạng SQL, để so trước/sau (§8.1: "DB không đổi")."""
        with self.repo.locked() as conn:
            return "\n".join(conn.iterdump())


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        db_path=tmp_path / "lyris.db",
        ollama_url="http://127.0.0.1:9",
        chat_model="chat-model:test",
        num_ctx=8192,
        avatars_dir=tmp_path / "avatars",
    )


async def send(client: httpx.AsyncClient, story_id: int, content: str) -> list[tuple[str, dict[str, Any]]]:
    resp = await client.post(f"/api/stories/{story_id}/messages", json={"content": content})
    assert resp.status_code == 200, resp.text
    return parse_sse(resp.text)


@asynccontextmanager
async def two_accounts(tmp_path: Path, llm: FakeLLM | None = None) -> AsyncIterator[World]:
    settings = make_settings(tmp_path)
    app = create_app(settings, llm or FakeLLM(replies=[REPLY]))
    async with app.router.lifespan_context(app):
        repo = repo_of(app)
        a_id = ensure_owner_password(repo)
        b_id = add_member(repo, "mai", "Mai")
        async with client_for(app, a_id) as a, client_for(app, b_id) as b:
            yield await _build(app, repo, settings.avatars_dir, a, b, a_id, b_id)


async def _build(
    app: FastAPI, repo: Repo, avatars_dir: Path, a: httpx.AsyncClient, b: httpx.AsyncClient, a_id: int, b_id: int
) -> World:
    a_handle = repo.get_account(a_id).handle
    await ok(await a.put("/api/account/avatar", content=png_bytes(), headers={"Content-Type": "image/png"}))
    a_persona = (await ok(await a.post("/api/personas", json={"name": "Lâm Vãn", "gender": "female"})))["id"]
    await ok(await a.put(f"/api/personas/{a_persona}/avatar", content=png_bytes(), headers={"Content-Type": "image/png"}))
    a_private = (await ok(await a.post("/api/cards", json={"card": card_body(PRIVATE_NAME)})))["id"]
    await ok(await a.put(f"/api/cards/{a_private}/avatar", content=png_bytes(), headers={"Content-Type": "image/png"}))
    public = await ok(await a.post("/api/cards", json={"card": card_body(PUBLIC_NAME, visibility="public")}))
    a_public = public["id"]
    assert public["visibility"] == "public"
    await ok(await a.put(f"/api/cards/{a_public}/avatar", content=png_bytes(), headers={"Content-Type": "image/png"}))
    a_entries = [(await ok(await a.post(f"/api/cards/{a_public}/lore", json=e)))["id"] for e in LORE]

    story = await ok(await a.post("/api/stories", json={"card_id": a_public, "persona_id": a_persona}))
    a_story = story["id"]
    assert story["card_id"] == a_public  # card của chính A: không có bản sao
    events = await send(a, a_story, TRIGGER)
    assert events[-1][0] == "done", events
    a_user_message = next(d["message"]["id"] for n, d in events if n == "user_message")
    a_message = next(d["message"]["id"] for n, d in events if n == "done")
    await ok(await a.put(f"/api/messages/{a_message}/feedback", json={"rating": "up", "note": "hay"}))
    message = repo.get_message(a_message, account_id=ANY_ACCOUNT)
    assert message.prompt_snapshot is not None
    memories = repo.replace_extraction(
        a_message, [], [NewMemory(kind="fact", text="A từng đi biển.")], story_id=a_story, turn_index=message.turn_index
    )
    assert memories
    a_memory = memories[0].id
    assert a_memory is not None
    assert repo.unlocked_lore(a_story)  # lore hit của A

    b_persona = (await ok(await b.post("/api/personas", json={"name": "Mai", "gender": "female"})))["id"]
    b_story_out = await ok(await b.post("/api/stories", json={"card_id": a_public, "persona_id": b_persona}))
    b_story = b_story_out["id"]
    b_copy = b_story_out["card_id"]
    assert b_copy != a_public
    events = await send(b, b_story, TRIGGER)
    assert events[-1][0] == "done", events
    b_message = next(d["message"]["id"] for n, d in events if n == "done")
    return World(
        app=app,
        repo=repo,
        avatars_dir=avatars_dir,
        a=a,
        b=b,
        a_id=a_id,
        b_id=b_id,
        a_handle=a_handle,
        a_persona=a_persona,
        a_private=a_private,
        a_public=a_public,
        a_entries=a_entries,
        a_story=a_story,
        a_user_message=a_user_message,
        a_message=a_message,
        a_memory=a_memory,
        b_persona=b_persona,
        b_story=b_story,
        b_copy=b_copy,
        b_message=b_message,
    )


__all__ = [
    "LORE",
    "PRIVATE_NAME",
    "PUBLIC_NAME",
    "PUBLIC_SECRET",
    "REPLY",
    "TRIGGER",
    "World",
    "card_body",
    "make_settings",
    "ok",
    "parse_sse",
    "png_bytes",
    "send",
    "two_accounts",
]
