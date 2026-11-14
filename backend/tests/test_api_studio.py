"""Test API Phase 2 (Character Studio): card, avatar, import/export, viết nháp, xem trước, chat thử,
persona, tạo/sửa/xoá story. FakeLLM, DB và thư mục avatar tạm, httpx qua ASGITransport."""
from __future__ import annotations

import asyncio
import contextlib
import io
import json
import os
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx
import pytest
from fastapi import FastAPI
from PIL import Image

from lyris.api.app import create_app
from lyris.api.routes_studio import content_disposition
from lyris.chat.service import ChatService
from lyris.config import Settings
from lyris.db.repo import ANY_ACCOUNT, Repo
from lyris.llm.base import Done, LLMError, LLMEvent, TextDelta
from lyris.llm.fake import FakeLLM
from lyris.models import ChatTurn, GenStats
from tests.authutil import owner_asgi_headers, owner_client

REPLY = (
    "Khang đặt ly cà phê sữa đá xuống bàn, liếc nhìn cô.\n\n"
    "[Thought: Lại đến muộn. Nhưng nhìn cô ấy thở hổn hển thế kia, thôi bỏ qua.]\n\n"
    "\"Em ngồi đi, anh gọi cho em rồi.\""
)
LONG_REPLY = ("Khang lặng lẽ nhìn ra dòng xe máy ngoài cửa kính, ngón tay gõ nhẹ lên mặt bàn. " * 15) + (
    "[Thought: Không biết nên mở lời thế nào.]"
)

DRAFT_JSON: dict[str, Any] = {
    "name": "Trần Minh Khang",
    "gender": "male",
    "description": "Kiến trúc sư 27 tuổi ở Sài Gòn.",
    "personality": "Điềm tĩnh, ít nói, chu đáo.",
    "appearance": "Cao, đeo kính gọng mảnh.",
    "background": "Lớn lên ở Đà Lạt, vào Sài Gòn học đại học.",
    "goals": "Mở văn phòng thiết kế riêng.",
    "secrets": "Thích {{user}} từ hồi đại học.",
    "speech_style": "Nói chậm, câu ngắn.",
    "style_profile": "viet_hien_dai",
    "self_term": "anh",
    "player_term": "em",
    "nicknames": ["bé"],
    "others": "Xưng tôi với đồng nghiệp.",
    "scenario": "Quán cà phê quen ở quận 3.",
    "greeting": (
        "Khang ngẩng lên khi chuông cửa reo.\n\n[Thought: Cuối cùng cũng tới. Mình đã đợi gần nửa tiếng.]\n\n"
        "\"Em tới rồi à?\" anh hỏi.\n\n[Thought: Đừng để cô ấy thấy mình hồi hộp. Bình tĩnh nào.]"
    ),
    "example_dialogues": "",
    "tags": ["Hiện đại", "sài gòn"],
}


def card_body(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "name": "Trần Minh Khang",
        "gender": "male",
        "language": "vi",
        "description": "Kiến trúc sư 27 tuổi ở Sài Gòn, thân với {{user}} từ hồi đại học.",
        "personality": "Điềm tĩnh, chu đáo.",
        "style_profile": "trung_hien_dai",
        "address_terms": {"self_term": "anh", "player_term": "em", "nicknames": ["bé"], "others": ""},
        "greeting": "{{char}} ngẩng lên. \"{{user}}, em tới rồi à?\" [Thought: Cuối cùng cũng tới.]",
        "tags": ["hiện đại"],
        "scenario": "{{user}} hẹn {{char}} ở quán cà phê quen.",
        "alternate_greetings": ["{{char}} nhắn tin cho {{user}}: \"Đến chưa?\""],
        "creator_notes": "Không đưa vào prompt.",
    }
    body.update(overrides)
    return body


def png_bytes(size: tuple[int, int] = (64, 48), color: tuple[int, int, int] = (200, 30, 30)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


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


# ---------------------------------------------------------------------------- fixtures


@pytest.fixture
def avatars_dir(tmp_path: Path) -> Path:
    return tmp_path / "avatars"


@pytest.fixture
def settings(tmp_path: Path, avatars_dir: Path) -> Settings:
    return Settings(
        db_path=tmp_path / "lyris.db",
        ollama_url="http://127.0.0.1:9",
        chat_model="gemma4:12b",
        num_ctx=8192,
        avatars_dir=avatars_dir,
        draft_model="draft-model:test",
    )


@pytest.fixture
def fake() -> FakeLLM:
    return FakeLLM(replies=[REPLY], json_replies=[DRAFT_JSON])


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


async def seed_persona_id(client: httpx.AsyncClient) -> int:
    personas = (await client.get("/api/personas")).json()
    return int(next(p["id"] for p in personas if p["name"] == "Lâm Vãn"))


async def create_card(client: httpx.AsyncClient, **overrides: Any) -> dict[str, Any]:
    resp = await client.post("/api/cards", json={"card": card_body(**overrides)})
    assert resp.status_code == 200, resp.text
    return dict(resp.json())


async def upload_avatar(client: httpx.AsyncClient, card_id: int, data: bytes | None = None) -> dict[str, Any]:
    resp = await client.put(
        f"/api/cards/{card_id}/avatar", content=data or png_bytes(), headers={"Content-Type": "image/png"}
    )
    assert resp.status_code == 200, resp.text
    return dict(resp.json())


def avatar_files(avatars_dir: Path) -> list[str]:
    if not avatars_dir.is_dir():
        return []
    return sorted(p.name for p in avatars_dir.iterdir() if p.is_file())


def settings_body(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "scenario": "Quán cà phê quen.",
        "language": "vi",
        "mode": "story",
        "relationship_type": "het",
        "pov": "third",
        "thought_style": "inline",
        "narration_pronouns": {"character": "anh", "player": "cô"},
    }
    body.update(overrides)
    return body


# ---------------------------------------------------------------------------- styles


async def test_list_styles(client: httpx.AsyncClient) -> None:
    resp = await client.get("/api/styles")
    assert resp.status_code == 200
    styles = resp.json()
    names = [s["name"] for s in styles]
    assert "trung_hien_dai" in names
    assert names == sorted(names)
    for s in styles:
        assert set(s) == {"name", "title", "description", "narration", "address_examples"}


# ---------------------------------------------------------------------------- cards CRUD


async def test_card_crud(client: httpx.AsyncClient) -> None:
    cards = (await client.get("/api/cards")).json()
    assert [c["name"] for c in cards] == ["Lạc Dương"]
    assert cards[0]["story_count"] == 1
    assert len(cards[0]["description"]) <= 160

    created = await create_card(client)
    assert created["id"] is not None and created["name"] == "Trần Minh Khang"
    assert created["avatar_url"] is None and created["avatar"] is None
    assert created["story_count"] == 0
    assert created["updated_at"]
    assert created["alternate_greetings"] == card_body()["alternate_greetings"]
    assert created["creator_notes"] == "Không đưa vào prompt."

    got = (await client.get(f"/api/cards/{created['id']}")).json()
    assert got == created

    # PUT: bỏ qua id và avatar trong body.
    body = {**created, "id": 999, "avatar": "card-1-deadbeef.png", "personality": "Lạnh lùng."}
    for extra in ("avatar_url", "story_count", "updated_at"):
        body.pop(extra)
    resp = await client.put(f"/api/cards/{created['id']}", json=body)
    assert resp.status_code == 200, resp.text
    updated = resp.json()
    assert updated["id"] == created["id"]
    assert updated["avatar"] is None
    assert updated["personality"] == "Lạnh lùng."

    cards = (await client.get("/api/cards")).json()
    assert cards[0]["id"] == created["id"]  # sửa gần nhất trước
    assert set(cards[0]) == {
        "id", "name", "role", "gender", "language", "style_profile", "description",
        "tags", "avatar_url", "story_count", "updated_at",
        "uid", "visibility", "creator_handle", "creator_name",  # Phase 2c
    }

    assert (await client.get("/api/cards/9999")).status_code == 404
    resp = await client.put("/api/cards/9999", json=card_body())
    assert resp.status_code == 404


async def test_card_summary_description_is_cut(client: httpx.AsyncClient) -> None:
    await create_card(client, description="Rất dài. " * 100)
    cards = (await client.get("/api/cards")).json()
    assert len(cards[0]["description"]) == 160
    assert cards[0]["description"].endswith("…")


@pytest.mark.parametrize(
    ("overrides", "fragment"),
    [
        ({"name": "   "}, "Tên nhân vật không được để trống"),
        ({"name": "x" * 81}, "Tên nhân vật dài quá 80 ký tự"),
        ({"style_profile": "khong_co"}, 'Không có style profile "khong_co"'),
        ({"description": "x" * 20_001}, "Phần mô tả dài quá 20.000 ký tự"),
        ({"tags": [f"tag{i}" for i in range(21)]}, "Tối đa 20 tag"),
        ({"alternate_greetings": ["ok", "x" * 20_001]}, "Lời mở đầu khác số 2"),
    ],
)
async def test_card_validation(client: httpx.AsyncClient, overrides: dict[str, Any], fragment: str) -> None:
    resp = await client.post("/api/cards", json={"card": card_body(**overrides)})
    assert resp.status_code == 422
    assert fragment in resp.json()["detail"]


async def test_card_validation_pydantic_vietnamese(client: httpx.AsyncClient) -> None:
    resp = await client.post("/api/cards", json={"card": card_body(gender="robot")})
    assert resp.status_code == 422
    assert resp.json()["detail"].startswith("Dữ liệu không hợp lệ: card.gender")


async def test_card_tags_are_trimmed_and_deduplicated(client: httpx.AsyncClient) -> None:
    created = await create_card(client, tags=[" Hiện đại ", "hiện đại", "", "Sài Gòn"])
    assert created["tags"] == ["Hiện đại", "Sài Gòn"]


# ---------------------------------------------------------------------------- avatar


async def test_avatar_upload_get_replace_delete(client: httpx.AsyncClient, avatars_dir: Path) -> None:
    card = await create_card(client)
    cid = card["id"]
    assert (await client.get(f"/api/cards/{cid}/avatar")).status_code == 404

    out = await upload_avatar(client, cid, png_bytes((1600, 800)))
    first = out["avatar"]
    assert first.startswith(f"card-{cid}-") and first.endswith(".png")
    assert out["avatar_url"] == f"/api/cards/{cid}/avatar?v={first}"
    assert avatar_files(avatars_dir) == [first]

    resp = await client.get(out["avatar_url"])
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert "immutable" in resp.headers["cache-control"] and "max-age=31536000" in resp.headers["cache-control"]
    with Image.open(io.BytesIO(resp.content)) as img:
        assert img.format == "PNG" and max(img.size) <= 768

    out2 = await upload_avatar(client, cid, png_bytes(color=(0, 0, 255)))
    assert out2["avatar"] != first
    assert avatar_files(avatars_dir) == [out2["avatar"]]  # file cũ đã xoá

    resp = await client.delete(f"/api/cards/{cid}/avatar")
    assert resp.status_code == 200 and resp.json()["avatar_url"] is None
    assert avatar_files(avatars_dir) == []
    assert (await client.get(f"/api/cards/{cid}/avatar")).status_code == 404


async def test_avatar_rejects_bad_and_huge_images(client: httpx.AsyncClient, avatars_dir: Path) -> None:
    card = await create_card(client)
    cid = card["id"]
    resp = await client.put(f"/api/cards/{cid}/avatar", content=b"khong phai anh", headers={"Content-Type": "image/png"})
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert isinstance(detail, str) and detail

    resp = await client.put(f"/api/cards/{cid}/avatar", content=b"", headers={"Content-Type": "image/png"})
    assert resp.status_code == 422 and "trống" in resp.json()["detail"]

    resp = await client.put(
        f"/api/cards/{cid}/avatar",
        content=b"\0" * (8 * 1024 * 1024 + 1),
        headers={"Content-Type": "image/png"},
    )
    assert resp.status_code == 422
    assert "quá lớn" in resp.json()["detail"]
    assert avatar_files(avatars_dir) == []
    assert (await client.put("/api/cards/9999/avatar", content=png_bytes())).status_code == 404


# ---------------------------------------------------------------------------- duplicate / delete


async def test_duplicate_copies_avatar_to_new_file(client: httpx.AsyncClient, avatars_dir: Path) -> None:
    card = await create_card(client)
    with_avatar = await upload_avatar(client, card["id"])
    resp = await client.post(f"/api/cards/{card['id']}/duplicate")
    assert resp.status_code == 200, resp.text
    copy = resp.json()
    assert copy["id"] != card["id"]
    assert copy["name"] == "Trần Minh Khang (bản sao)"
    assert copy["greeting"] == card["greeting"] and copy["alternate_greetings"] == card["alternate_greetings"]
    assert copy["avatar"] and copy["avatar"] != with_avatar["avatar"]
    assert copy["avatar"].startswith(f"card-{copy['id']}-")
    assert sorted(avatar_files(avatars_dir)) == sorted([with_avatar["avatar"], copy["avatar"]])

    long_name = await create_card(client, name="y" * 80)
    copy2 = (await client.post(f"/api/cards/{long_name['id']}/duplicate")).json()
    assert len(copy2["name"]) <= 80 and copy2["name"].endswith(" (bản sao)")
    assert (await client.post("/api/cards/9999/duplicate")).status_code == 404


async def test_delete_card_with_stories(client: httpx.AsyncClient, avatars_dir: Path) -> None:
    card = await create_card(client)
    cid = card["id"]
    await upload_avatar(client, cid)
    persona_id = await seed_persona_id(client)
    for _ in range(2):
        resp = await client.post("/api/stories", json={"card_id": cid, "persona_id": persona_id})
        assert resp.status_code == 200, resp.text

    resp = await client.delete(f"/api/cards/{cid}")
    assert resp.status_code == 409
    assert resp.json()["detail"] == "Có 2 story đang dùng nhân vật này. Xoá luôn các story đó?"
    assert (await client.get(f"/api/cards/{cid}")).status_code == 200

    resp = await client.delete(f"/api/cards/{cid}?with_stories=true")
    assert resp.status_code == 200
    assert resp.json() == {"deleted_stories": 2}
    assert (await client.get(f"/api/cards/{cid}")).status_code == 404
    assert avatar_files(avatars_dir) == []
    stories = (await client.get("/api/stories")).json()
    assert all(s["card_id"] != cid for s in stories)

    plain = await create_card(client, name="Không ai dùng")
    resp = await client.delete(f"/api/cards/{plain['id']}")
    assert resp.status_code == 200 and resp.json() == {"deleted_stories": 0}
    assert (await client.delete("/api/cards/9999")).status_code == 404


async def test_delete_card_while_its_story_is_generating(app: FastAPI, client: httpx.AsyncClient) -> None:
    repo, chat = repo_of(app), chat_of(app)
    story = repo.list_stories(account_id=ANY_ACCOUNT)[0]
    assert story.id is not None
    lock = chat._lock(story.id)  # giả lập story đang sinh câu trả lời
    await lock.acquire()
    try:
        resp = await client.delete(f"/api/cards/{story.card_id}?with_stories=true")
        assert resp.status_code == 409
        resp = await client.delete(f"/api/personas/{story.persona_id}?with_stories=true")
        assert resp.status_code == 409
    finally:
        lock.release()
    assert repo.get_story(story.id, account_id=ANY_ACCOUNT).id == story.id


# ---------------------------------------------------------------------------- export / import


def test_content_disposition_rfc5987() -> None:
    header = content_disposition("Lạc Dương", "json")
    assert header == (
        "attachment; filename=\"Lac Duong.json\"; filename*=UTF-8''" + quote("Lạc Dương", safe="") + ".json"
    )
    assert "filename*=UTF-8''L%E1%BA%A1c%20D%C6%B0%C6%A1ng.json" in header
    # Ký tự nguy hiểm trong tên file bị thay.
    header = content_disposition('a/b\\c"d\n', "png")
    assert "/" not in header.split("filename*=")[1].replace("%2F", "")
    assert '"a b c d.png"' in header
    assert content_disposition("   ", "json").startswith('attachment; filename="card.json"')


async def test_export_json_and_png(client: httpx.AsyncClient) -> None:
    cards = (await client.get("/api/cards")).json()
    cid = cards[0]["id"]
    resp = await client.get(f"/api/cards/{cid}/export?format=json")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")
    cd = resp.headers["content-disposition"]
    assert cd.startswith("attachment;")
    assert "filename*=UTF-8''L%E1%BA%A1c%20D%C6%B0%C6%A1ng.json" in cd
    data = json.loads(resp.content.decode("utf-8"))
    assert data["spec"] == "chara_card_v2" and data["data"]["name"] == "Lạc Dương"

    resp = await client.get(f"/api/cards/{cid}/export?format=png")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.content.startswith(b"\x89PNG")
    assert resp.headers["content-disposition"].endswith(".png")

    resp = await client.get(f"/api/cards/{cid}/export?format=docx")
    assert resp.status_code == 422 and isinstance(resp.json()["detail"], str)
    assert (await client.get("/api/cards/9999/export")).status_code == 404


async def test_import_json_roundtrip(client: httpx.AsyncClient) -> None:
    card = await create_card(client, style_profile="trung_hien_dai")
    exported = (await client.get(f"/api/cards/{card['id']}/export?format=json")).content
    resp = await client.post("/api/cards/import", content=exported, headers={"Content-Type": "application/json"})
    assert resp.status_code == 200, resp.text
    result = resp.json()
    assert set(result) == {"card", "warnings", "avatar_token"}
    assert result["avatar_token"] is None
    draft = result["card"]
    assert draft["id"] is None and draft["avatar"] is None
    for key in ("name", "gender", "personality", "greeting", "alternate_greetings", "scenario", "style_profile"):
        assert draft[key] == card[key], key
    assert draft["address_terms"] == card["address_terms"]
    # Chưa lưu gì.
    assert len((await client.get("/api/cards")).json()) == 2


async def test_import_png_holds_avatar_until_saved(client: httpx.AsyncClient, avatars_dir: Path) -> None:
    card = await create_card(client)
    await upload_avatar(client, card["id"], png_bytes((300, 300), (10, 200, 10)))
    exported = (await client.get(f"/api/cards/{card['id']}/export?format=png")).content
    resp = await client.post("/api/cards/import", content=exported, headers={"Content-Type": "image/png"})
    assert resp.status_code == 200, resp.text
    result = resp.json()
    token = result["avatar_token"]
    assert isinstance(token, str) and token
    held = next((avatars_dir / "tmp").glob(f"*-{token}.png"))  # Phase 4b: tmp/<account>-<token>.png
    assert held.is_file()

    resp = await client.post("/api/cards", json={"card": result["card"], "avatar_token": token})
    assert resp.status_code == 200, resp.text
    saved = resp.json()
    assert saved["avatar"] and saved["avatar"].startswith(f"card-{saved['id']}-")
    assert saved["avatar_url"] is not None
    assert not held.exists()
    assert (await client.get(saved["avatar_url"])).status_code == 200

    # Token lạ hoặc đã dùng: lưu card bình thường, không có ảnh.
    resp = await client.post("/api/cards", json={"card": result["card"], "avatar_token": token})
    assert resp.status_code == 200 and resp.json()["avatar"] is None


async def test_import_rejects_garbage(client: httpx.AsyncClient) -> None:
    resp = await client.post("/api/cards/import", content=b"{ khong phai json", headers={"Content-Type": "application/json"})
    assert resp.status_code == 422
    assert isinstance(resp.json()["detail"], str) and resp.json()["detail"]
    resp = await client.post("/api/cards/import", content=b"", headers={"Content-Type": "application/json"})
    assert resp.status_code == 422
    resp = await client.post(
        "/api/cards/import", content=b" " * (8 * 1024 * 1024 + 10), headers={"Content-Type": "application/json"}
    )
    assert resp.status_code == 422 and "quá lớn" in resp.json()["detail"]


async def test_import_v1_card(client: httpx.AsyncClient) -> None:
    v1 = {
        "name": "Aria",
        "description": "She is a starship pilot.",
        "personality": "Bold, curious.",
        "scenario": "On the bridge of the Andromeda.",
        "first_mes": "Aria glances at {{user}}. \"Ready?\"",
        "mes_example": "",
    }
    resp = await client.post("/api/cards/import", content=json.dumps(v1).encode(), headers={"Content-Type": "application/json"})
    assert resp.status_code == 200, resp.text
    result = resp.json()
    assert result["card"]["name"] == "Aria"
    assert result["card"]["language"] == "en"
    assert result["warnings"]


# ---------------------------------------------------------------------------- AI viết nháp


async def test_draft_card(client: httpx.AsyncClient, fake: FakeLLM) -> None:
    resp = await client.post(
        "/api/cards/draft", json={"idea": "Kiến trúc sư trầm tính ở Sài Gòn", "language": "vi"}
    )
    assert resp.status_code == 200, resp.text
    result = resp.json()
    assert result["avatar_token"] is None
    assert result["card"]["name"] == "Trần Minh Khang"
    assert result["card"]["id"] is None
    assert result["card"]["language"] == "vi"
    assert isinstance(result["warnings"], list)
    assert fake.calls[-1]["model"] == "draft-model:test"
    assert "schema" in fake.calls[-1]
    # Chưa lưu gì.
    assert len((await client.get("/api/cards")).json()) == 1


async def test_draft_errors(app: FastAPI, client: httpx.AsyncClient, fake: FakeLLM) -> None:
    resp = await client.post("/api/cards/draft", json={"idea": "   ", "language": "vi"})
    assert resp.status_code == 422 and isinstance(resp.json()["detail"], str)

    resp = await client.post("/api/cards/draft", json={"idea": "Ý tưởng", "language": "vi", "style_profile": "xyz"})
    assert resp.status_code == 422 and 'Không có style profile "xyz"' in resp.json()["detail"]

    lock: asyncio.Lock = app.state.draft_lock
    await lock.acquire()
    try:
        resp = await client.post("/api/cards/draft", json={"idea": "Ý tưởng", "language": "vi"})
        assert resp.status_code == 409
        assert resp.json()["detail"] == "AI đang viết một bản nháp khác. Thử lại sau ít phút."
    finally:
        lock.release()

    fake.json_replies = []  # FakeLLM raise LLMError khi không có json_replies
    resp = await client.post("/api/cards/draft", json={"idea": "Ý tưởng", "language": "vi"})
    assert resp.status_code == 502
    body = resp.json()
    assert body["detail"] == "Chưa viết nháp được nhân vật. Hãy thử lại."
    assert body["technical"] == "FakeLLM chưa được cấu hình json_replies."
    assert not lock.locked()


async def test_draft_concurrent_requests_one_is_busy(client: httpx.AsyncClient, fake: FakeLLM) -> None:
    fake.delay = 0.6  # lâu hơn một chu kỳ dò ngắt kết nối: request còn kết nối thì không bị huỷ
    body = {"idea": "Kiến trúc sư trầm tính", "language": "vi"}
    first, second = await asyncio.gather(
        client.post("/api/cards/draft", json=body),
        client.post("/api/cards/draft", json=body),
    )
    assert sorted([first.status_code, second.status_code]) == [200, 409]


# ---------------------------------------------------------------------------- xem trước prompt


async def test_preview_prompt(client: httpx.AsyncClient, fake: FakeLLM) -> None:
    persona_id = await seed_persona_id(client)
    resp = await client.post(
        "/api/cards/preview-prompt",
        json={"card": card_body(), "persona_id": persona_id, "settings": settings_body()},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert set(data) == {"messages", "token_estimate", "num_ctx"}
    assert data["num_ctx"] == 8192
    assert set(data["token_estimate"]) >= {"A", "B", "C", "E", "F", "total"}
    msgs = data["messages"]
    assert msgs[0]["role"] == "system"
    assert "Trần Minh Khang" in msgs[0]["content"]
    assert msgs[-1]["role"] == "user"
    assert "(Lượt mẫu của người chơi)" in msgs[-1]["content"]
    # Lời mở đầu của card (đã thay {{char}}/{{user}}) nằm trong lịch sử mẫu.
    assistant = [m for m in msgs if m["role"] == "assistant"]
    assert assistant and "Lâm Vãn, em tới rồi à?" in assistant[0]["content"]
    assert all("{{" not in m["content"] for m in msgs)
    assert fake.calls == []  # không gọi model

    resp = await client.post(
        "/api/cards/preview-prompt",
        json={"card": card_body(), "persona_id": persona_id, "settings": settings_body(language="en")},
    )
    assert resp.status_code == 200
    assert "(Sample player turn)" in resp.json()["messages"][-1]["content"]

    # Card chưa đặt tên vẫn xem trước được; persona lạ -> 404; style lạ -> 422.
    resp = await client.post(
        "/api/cards/preview-prompt",
        json={"card": card_body(name=""), "persona_id": persona_id, "settings": settings_body()},
    )
    assert resp.status_code == 200
    resp = await client.post(
        "/api/cards/preview-prompt",
        json={"card": card_body(), "persona_id": 9999, "settings": settings_body()},
    )
    assert resp.status_code == 404
    resp = await client.post(
        "/api/cards/preview-prompt",
        json={"card": card_body(style_profile="nope"), "persona_id": persona_id, "settings": settings_body()},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------- chat thử


async def test_test_chat_streams_and_saves_nothing(app: FastAPI, client: httpx.AsyncClient, fake: FakeLLM) -> None:
    repo = repo_of(app)
    persona_id = await seed_persona_id(client)
    story_id = repo.list_stories(account_id=ANY_ACCOUNT)[0].id
    assert story_id is not None
    before = len(repo.active_messages(story_id))
    body = {
        "card": card_body(),
        "persona_id": persona_id,
        "settings": settings_body(),
        "messages": [
            {"role": "assistant", "content": card_body()["greeting"]},
            {"role": "user", "content": "*Ngồi xuống* \"Xin lỗi, em đến muộn.\" ((cho anh ấy dỗi một chút))"},
        ],
    }
    resp = await client.post("/api/cards/test-chat", json=body)
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("text/event-stream")
    assert resp.headers["cache-control"] == "no-cache"
    events = parse_sse(resp.text)
    assert events[0] == ("start", {})
    assert events[-1][0] == "done"
    kinds = {d["kind"] for n, d in events if n == "delta"}
    assert kinds == {"text", "thought"}
    done = events[-1][1]
    assert done["raw"] == REPLY
    assert "[Thought" not in done["visible"]
    assert done["thought"].startswith("Lại đến muộn.")
    assert set(done["stats"]) >= {"ttft_ms", "total_ms", "aborted"}
    text = "".join(d["text"] for n, d in events if n == "delta" and d["kind"] == "text")
    assert text == done["visible"]

    call = fake.calls[-1]
    assert call["model"] == "gemma4:12b"
    sent = call["messages"]
    assert sent[0].role == "system"
    assert sent[-1].role == "user"
    assert "Xin lỗi, em đến muộn." in sent[-1].content
    assert "((" not in sent[-1].content and "cho anh ấy dỗi một chút" in sent[-1].content
    assert any(m.role == "assistant" and "Lâm Vãn, em tới rồi à?" in m.content for m in sent)

    # Không ghi gì vào DB.
    assert len(repo.active_messages(story_id)) == before
    assert len(repo.list_stories(account_id=ANY_ACCOUNT)) == 1
    assert not app.state.test_chat_lock.locked()


async def test_test_chat_validation(client: httpx.AsyncClient) -> None:
    persona_id = await seed_persona_id(client)
    base = {"card": card_body(), "persona_id": persona_id, "settings": settings_body()}
    resp = await client.post("/api/cards/test-chat", json={**base, "messages": []})
    assert resp.status_code == 422 and "chưa có lượt nào" in resp.json()["detail"]
    resp = await client.post(
        "/api/cards/test-chat", json={**base, "messages": [{"role": "assistant", "content": "Chào."}]}
    )
    assert resp.status_code == 422 and "phải là của người chơi" in resp.json()["detail"]
    resp = await client.post("/api/cards/test-chat", json={**base, "messages": [{"role": "user", "content": "  "}]})
    assert resp.status_code == 422
    resp = await client.post(
        "/api/cards/test-chat", json={**base, "messages": [{"role": "system", "content": "x"}]}
    )
    assert resp.status_code == 422
    resp = await client.post(
        "/api/cards/test-chat",
        json={**base, "persona_id": 9999, "messages": [{"role": "user", "content": "Chào"}]},
    )
    assert resp.status_code == 404


async def test_test_chat_busy_and_llm_error(app: FastAPI, client: httpx.AsyncClient, fake: FakeLLM) -> None:
    persona_id = await seed_persona_id(client)
    body = {
        "card": card_body(),
        "persona_id": persona_id,
        "settings": settings_body(),
        "messages": [{"role": "user", "content": "Chào anh."}],
    }
    lock: asyncio.Lock = app.state.test_chat_lock
    await lock.acquire()
    try:
        resp = await client.post("/api/cards/test-chat", json=body)
        assert resp.status_code == 409
        assert "chat thử" in resp.json()["detail"]
    finally:
        lock.release()

    fake.error = LLMError("Không kết nối được Ollama.")
    resp = await client.post("/api/cards/test-chat", json=body)
    assert resp.status_code == 200
    events = parse_sse(resp.text)
    assert [n for n, _ in events] == ["start", "error"]
    assert events[-1][1] == {"detail": "Nhân vật chưa trả lời được. Hãy bấm Làm lại.", "technical": "Không kết nối được Ollama."}
    assert not lock.locked()

    fake.error = None
    fake.replies = ["   "]
    events = parse_sse((await client.post("/api/cards/test-chat", json=body)).text)
    assert events[-1][0] == "error"


class TrackingLLM:
    """LLM giả ghi lại việc stream bị đóng (client ngắt kết nối phải huỷ request tới model)."""

    def __init__(self) -> None:
        self.closed = False
        self.finished = False

    async def chat_stream(
        self, model: str, messages: list[ChatTurn], *, stop: list[str], options: dict[str, Any]
    ) -> AsyncIterator[LLMEvent]:
        try:
            for i in range(10_000):
                await asyncio.sleep(0.002)
                yield TextDelta(f"chữ {i} ")
            self.finished = True
            yield Done(GenStats())
        finally:
            self.closed = True

    async def chat_json(
        self, model: str, messages: list[ChatTurn], *, schema: dict[str, Any], options: dict[str, Any]
    ) -> dict[str, Any]:
        raise LLMError("không dùng")


async def _post_and_disconnect(app: FastAPI, path: str, payload: dict[str, Any], after_deltas: int) -> bytes:
    body = json.dumps(payload).encode()
    disconnected = asyncio.Event()
    chunks: list[bytes] = []
    sent_request = False

    async def receive() -> dict[str, Any]:
        nonlocal sent_request
        if not sent_request:
            sent_request = True
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
        "asgi": {"version": "3.0", "spec_version": "2.4"},
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
    return b"".join(chunks)


async def test_test_chat_disconnect_cancels_generation(settings: Settings) -> None:
    llm = TrackingLLM()
    application = create_app(settings, llm)  # type: ignore[arg-type]
    async with application.router.lifespan_context(application):
        repo = repo_of(application)
        persona = repo.list_personas(account_id=ANY_ACCOUNT)[0]
        payload = {
            "card": card_body(),
            "persona_id": persona.id,
            "settings": settings_body(),
            "messages": [{"role": "user", "content": "Chào anh."}],
        }
        raw = await _post_and_disconnect(application, "/api/cards/test-chat", payload, after_deltas=3)
        assert b"event: start" in raw and b"event: done" not in raw
        assert llm.closed and not llm.finished
        assert not application.state.test_chat_lock.locked()


# ---------------------------------------------------------------------------- personas


async def test_persona_crud(client: httpx.AsyncClient) -> None:
    personas = (await client.get("/api/personas")).json()
    assert [p["name"] for p in personas] == ["Lâm Vãn"]
    assert personas[0]["story_count"] == 1
    seed_id = personas[0]["id"]

    resp = await client.post("/api/personas", json={"name": "  Ngọc Anh ", "gender": "female", "description": "Nhân viên văn phòng."})
    assert resp.status_code == 200, resp.text
    created = resp.json()
    assert created["name"] == "Ngọc Anh" and created["story_count"] == 0

    resp = await client.put(
        f"/api/personas/{created['id']}", json={"id": 777, "name": "Ngọc Ánh", "gender": "female", "description": ""}
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"] and resp.json()["name"] == "Ngọc Ánh"

    assert (await client.post("/api/personas", json={"name": " ", "gender": "male"})).status_code == 422
    resp = await client.post("/api/personas", json={"name": "A", "gender": "robot"})
    assert resp.status_code == 422 and isinstance(resp.json()["detail"], str)
    assert (await client.put("/api/personas/9999", json={"name": "X", "gender": "male"})).status_code == 404

    resp = await client.delete(f"/api/personas/{seed_id}")
    assert resp.status_code == 409
    assert resp.json()["detail"] == "Có 1 story đang dùng persona này. Xoá luôn các story đó?"
    resp = await client.delete(f"/api/personas/{created['id']}")
    assert resp.status_code == 200 and resp.json() == {"deleted_stories": 0}
    resp = await client.delete(f"/api/personas/{seed_id}?with_stories=true")
    assert resp.status_code == 200 and resp.json() == {"deleted_stories": 1}
    assert (await client.get("/api/personas")).json() == []
    assert (await client.delete("/api/personas/9999")).status_code == 404


# ---------------------------------------------------------------------------- stories


async def test_phase1_story_creation_still_works(client: httpx.AsyncClient) -> None:
    resp = await client.post("/api/stories", json={})
    assert resp.status_code == 200
    out = resp.json()
    assert out["card_name"] == "Lạc Dương" and out["persona_name"] == "Lâm Vãn"
    assert out["card_avatar_url"] is None
    assert out["updated_at"]
    resp = await client.post("/api/stories", json={"title": "Chương hai"})
    assert resp.status_code == 200 and resp.json()["title"] == "Chương hai"
    resp = await client.post("/api/stories", json={"persona_id": 1})
    assert resp.status_code == 422 and resp.json()["detail"] == "Cần chọn nhân vật cho story."
    resp = await client.post("/api/stories", json={"greeting_index": 1})
    assert resp.status_code == 422


async def test_story_defaults(client: httpx.AsyncClient) -> None:
    card = await create_card(client)
    persona_id = await seed_persona_id(client)
    resp = await client.get(f"/api/stories/defaults?card_id={card['id']}&persona_id={persona_id}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["title"] == "Trần Minh Khang & Lâm Vãn"
    s = data["settings"]
    assert s["language"] == "vi" and s["mode"] == "story" and s["pov"] == "third"
    assert s["relationship_type"] == "het"
    assert s["scenario"] == "Lâm Vãn hẹn Trần Minh Khang ở quán cà phê quen."
    assert s["narration_pronouns"]["character"] and s["narration_pronouns"]["player"]

    resp = await client.get(f"/api/stories/defaults?card_id={card['id']}&persona_id={persona_id}&language=en")
    assert resp.json()["settings"]["language"] == "en"
    assert resp.json()["settings"]["narration_pronouns"] == {"character": "he", "player": "she"}

    assert (await client.get(f"/api/stories/defaults?card_id=9999&persona_id={persona_id}")).status_code == 404
    # Lyris design: thiếu persona_id -> persona mặc định (chưa đặt thì persona tạo sớm nhất = Lâm Vãn).
    resp = await client.get(f"/api/stories/defaults?card_id={card['id']}")
    assert resp.status_code == 200 and resp.json()["title"] == "Trần Minh Khang & Lâm Vãn"


async def test_create_story_for_card(client: httpx.AsyncClient) -> None:
    card = await create_card(client)
    await upload_avatar(client, card["id"])
    persona_id = await seed_persona_id(client)

    resp = await client.post(
        "/api/stories",
        json={
            "card_id": card["id"],
            "persona_id": persona_id,
            "title": "  Hẹn ở quán quen ",
            "settings": {"mode": "dm", "thought_style": "end"},
        },
    )
    assert resp.status_code == 200, resp.text
    out = resp.json()
    assert out["title"] == "Hẹn ở quán quen"
    assert out["card_name"] == "Trần Minh Khang" and out["persona_name"] == "Lâm Vãn"
    assert out["card_avatar_url"] and out["card_avatar_url"].startswith(f"/api/cards/{card['id']}/avatar?v=")
    assert out["updated_at"]
    assert out["mode"] == "dm" and out["thought_style"] == "end"
    assert out["scenario"] == "Lâm Vãn hẹn Trần Minh Khang ở quán cà phê quen."
    assert out["model_name"] == "gemma4:12b"
    msgs = (await client.get(f"/api/stories/{out['id']}/messages")).json()
    assert len(msgs) == 1 and msgs[0]["turn_index"] == 0 and msgs[0]["mode"] == "dm"
    assert "Lâm Vãn, em tới rồi à?" in msgs[0]["raw_content"]
    assert msgs[0]["thought"] == "Cuối cùng cũng tới."

    # Lời mở đầu thay thế, ngôn ngữ khác -> đại từ theo ngôn ngữ đó, tiêu đề mặc định.
    resp = await client.post(
        "/api/stories",
        json={"card_id": card["id"], "persona_id": persona_id, "greeting_index": 1, "settings": {"language": "en"}},
    )
    assert resp.status_code == 200, resp.text
    out2 = resp.json()
    assert out2["title"] == "Trần Minh Khang & Lâm Vãn"
    assert out2["language"] == "en"
    assert out2["narration_pronouns"] == {"character": "he", "player": "she"}
    msgs = (await client.get(f"/api/stories/{out2['id']}/messages")).json()
    assert msgs[0]["raw_content"] == 'Trần Minh Khang nhắn tin cho Lâm Vãn: "Đến chưa?"'

    # Không lời mở đầu; đại từ do người dùng chọn.
    resp = await client.post(
        "/api/stories",
        json={
            "card_id": card["id"],
            "persona_id": persona_id,
            "greeting_index": -1,
            "settings": {"narration_pronouns": {"character": " Khang ", "player": "nàng"}},
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["narration_pronouns"] == {"character": "Khang", "player": "nàng"}
    assert (await client.get(f"/api/stories/{resp.json()['id']}/messages")).json() == []

    # Lỗi dữ liệu.
    resp = await client.post("/api/stories", json={"card_id": card["id"], "persona_id": persona_id, "greeting_index": 5})
    assert resp.status_code == 422 and isinstance(resp.json()["detail"], str)
    resp = await client.post("/api/stories", json={"card_id": card["id"], "persona_id": persona_id, "settings": {"pov": "second"}})
    assert resp.status_code == 422
    resp = await client.post("/api/stories", json={"card_id": card["id"], "persona_id": persona_id, "settings": {"x": 1}})
    assert resp.status_code == 422
    # Lyris design: thiếu persona_id -> persona mặc định.
    resp = await client.post("/api/stories", json={"card_id": card["id"]})
    assert resp.status_code == 200 and resp.json()["persona_id"] == persona_id
    resp = await client.post("/api/stories", json={"persona_id": persona_id})
    assert resp.status_code == 422 and resp.json()["detail"] == "Cần chọn nhân vật cho story."
    resp = await client.post("/api/stories", json={"card_id": 9999, "persona_id": persona_id})
    assert resp.status_code == 404

    stories = (await client.get("/api/stories")).json()
    assert {"card_avatar_url", "updated_at", "card_role", "last_preview", "last_role", "last_mode"} <= set(stories[0])
    assert len(stories) == 5


async def test_patch_story_phase2_fields(client: httpx.AsyncClient) -> None:
    sid = (await client.get("/api/stories")).json()[0]["id"]
    resp = await client.patch(
        f"/api/stories/{sid}",
        json={
            "language": "en",
            "relationship_type": "none",
            "pov": "first",
            "narration_pronouns": {"character": "I", "player": "you"},
        },
    )
    assert resp.status_code == 200, resp.text
    story = resp.json()
    assert story["language"] == "en" and story["relationship_type"] == "none" and story["pov"] == "first"
    assert story["narration_pronouns"] == {"character": "I", "player": "you"}

    resp = await client.patch(f"/api/stories/{sid}", json={"narration_pronouns": {"character": " ", "player": "x"}})
    assert resp.status_code == 422 and resp.json()["detail"] == "Đại từ dẫn truyện không được để trống."
    resp = await client.patch(f"/api/stories/{sid}", json={"card_id": 2})
    assert resp.status_code == 422
    resp = await client.patch(f"/api/stories/{sid}", json={"language": "fr"})
    assert resp.status_code == 422


async def test_delete_story(app: FastAPI, client: httpx.AsyncClient) -> None:
    created = (await client.post("/api/stories", json={})).json()
    sid = created["id"]
    chat = chat_of(app)
    lock = chat._lock(sid)
    await lock.acquire()
    try:
        resp = await client.delete(f"/api/stories/{sid}")
        assert resp.status_code == 409
        assert "đang sinh câu trả lời" in resp.json()["detail"]
    finally:
        lock.release()

    resp = await client.delete(f"/api/stories/{sid}")
    assert resp.status_code == 200 and resp.json() == {"deleted": 1}
    assert (await client.get(f"/api/stories/{sid}")).status_code == 404
    assert (await client.get(f"/api/stories/{sid}/messages")).status_code == 404
    assert (await client.delete(f"/api/stories/{sid}")).status_code == 404


async def test_delete_story_during_real_generation(app: FastAPI, client: httpx.AsyncClient, fake: FakeLLM) -> None:
    fake.replies = [LONG_REPLY]
    fake.chunk_size = 5
    fake.delay = 0.003
    chat = chat_of(app)
    sid = (await client.get("/api/stories")).json()[0]["id"]
    gen = chat.send(sid, "Chào anh.")
    try:
        async for event in gen:
            if event.name == "delta":
                break
        assert chat.is_busy(sid)
        resp = await client.delete(f"/api/stories/{sid}")
        assert resp.status_code == 409
    finally:
        await gen.aclose()
    assert not chat.is_busy(sid)
    assert (await client.delete(f"/api/stories/{sid}")).status_code == 200


# ---------------------------------------------------------------------------- khởi động


async def test_startup_cleans_old_temp_avatars(settings: Settings, avatars_dir: Path) -> None:
    tmp = avatars_dir / "tmp"
    tmp.mkdir(parents=True)
    old = tmp / ("a" * 32 + ".png")
    fresh = tmp / ("b" * 32 + ".png")
    old.write_bytes(png_bytes())
    fresh.write_bytes(png_bytes())
    two_days_ago = time.time() - 2 * 86400
    os.utime(old, (two_days_ago, two_days_ago))

    application = create_app(settings, FakeLLM())
    async with application.router.lifespan_context(application):
        assert not old.exists()
        assert fresh.exists()


class SlowDraftLLM(TrackingLLM):
    """chat_json chạy rất lâu; ghi lại việc bị huỷ."""

    def __init__(self) -> None:
        super().__init__()
        self.json_started = asyncio.Event()
        self.json_cancelled = False

    async def chat_json(
        self, model: str, messages: list[ChatTurn], *, schema: dict[str, Any], options: dict[str, Any]
    ) -> dict[str, Any]:
        self.json_started.set()
        try:
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            self.json_cancelled = True
            raise
        return dict(DRAFT_JSON)


async def test_draft_client_disconnect_cancels_and_frees_lock(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    import lyris.api.routes_studio as routes_studio

    monkeypatch.setattr(routes_studio, "DRAFT_DISCONNECT_POLL_S", 0.01)
    llm = SlowDraftLLM()
    application = create_app(settings, llm)  # type: ignore[arg-type]
    async with application.router.lifespan_context(application):
        body = json.dumps({"idea": "Kiến trúc sư trầm tính", "language": "vi"}).encode()
        sent_request = False

        async def receive() -> dict[str, Any]:
            nonlocal sent_request
            if not sent_request:
                sent_request = True
                return {"type": "http.request", "body": body, "more_body": False}
            await llm.json_started.wait()
            return {"type": "http.disconnect"}

        async def send(message: dict[str, Any]) -> None:
            return None

        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.4"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/api/cards/draft",
            "raw_path": b"/api/cards/draft",
            "query_string": b"",
            "root_path": "",
            "headers": [(b"content-type", b"application/json"), (b"host", b"test"), *owner_asgi_headers(application)],
            "client": ("127.0.0.1", 50000),
            "server": ("test", 80),
            "state": {},
        }
        await asyncio.wait_for(application(scope, receive, send), 5)
        assert llm.json_cancelled
        assert not application.state.draft_lock.locked()
