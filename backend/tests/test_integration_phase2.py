"""Test tích hợp Phase 2 xuyên module: API -> repo -> studio (stories/avatars/card_v2/draft/preview)
-> prompt builder -> ChatService -> FakeLLM. DB, thư mục avatar tạm; không gọi Ollama thật."""
from __future__ import annotations

import io
import json
import sqlite3
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from PIL import Image

from lyris.api.app import create_app
from lyris.config import Settings
from lyris.db.connection import MIGRATIONS_DIR, connect, migrate
from lyris.db.repo import Repo
from lyris.llm.fake import FakeLLM
from lyris.models import ChatTurn
from lyris.prompt.builder import load_style
from lyris.seed import load_default_story_settings, load_seed_card, load_seed_persona
from tests.authutil import owner_client

REPLY = (
    "Khang đặt ly cà phê sữa đá xuống bàn.\n\n"
    "[Thought: Lại đến muộn. Thôi, bỏ qua lần này.]\n\n"
    "\"Em ngồi đi, anh gọi nước cho em rồi.\""
)

DRAFT_JSON: dict[str, Any] = {
    "name": "Trần Minh Khang",
    "gender": "male",
    "description": "Kiến trúc sư 27 tuổi ở Sài Gòn, quen {{user}} từ hồi đại học.",
    "personality": "Điềm tĩnh, ít nói, chu đáo.",
    "appearance": "Cao, đeo kính gọng mảnh.",
    "background": "Lớn lên ở Đà Lạt.",
    "goals": "Mở văn phòng thiết kế riêng.",
    "secrets": "Thích {{user}} từ lâu.",
    "speech_style": "Nói chậm, câu ngắn.",
    "style_profile": "viet_hien_dai",
    "self_term": "anh",
    "player_term": "em",
    "nicknames": ["bé"],
    "others": "Xưng tôi với đồng nghiệp.",
    "scenario": "Quán cà phê quen ở quận 3.",
    "greeting": (
        "Khang ngẩng lên khi chuông cửa reo.\n\n[Thought: Cuối cùng cũng tới. Mình đợi gần nửa tiếng rồi.]\n\n"
        "\"Em tới rồi à?\" anh hỏi {{user}}.\n\n[Thought: Đừng để cô ấy thấy mình hồi hộp. Bình tĩnh nào.]\n\n"
        "Anh đẩy ly nước về phía ghế đối diện."
    ),
    "example_dialogues": "",
    "tags": ["hiện đại", "sài gòn"],
}

CREATOR_NOTE = "GHI_CHU_NGUOI_TAO_KHONG_VAO_PROMPT"
ALT_GREETING = "LOI_MO_DAU_PHU {{char}} nhắn cho {{user}}."


def card_body(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "name": "Trần Minh Khang",
        "gender": "male",
        "language": "vi",
        "description": "Kiến trúc sư 27 tuổi ở Sài Gòn, thân với {{user}} từ hồi đại học.",
        "personality": "Điềm tĩnh, chu đáo.",
        "style_profile": "viet_hien_dai",
        "address_terms": {"self_term": "anh", "player_term": "em", "nicknames": ["bé"], "others": ""},
        "greeting": "{{char}} ngẩng lên. \"{{user}}, em tới rồi à?\" [Thought: Cuối cùng cũng tới.]",
        "tags": ["hiện đại"],
        "scenario": "{{user}} hẹn {{char}} ở quán cà phê quen.",
        "alternate_greetings": [ALT_GREETING],
        "creator_notes": CREATOR_NOTE,
    }
    body.update(overrides)
    return body


def png_bytes(size: tuple[int, int] = (64, 48), color: tuple[int, int, int] = (20, 120, 200)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def parse_sse(body: str) -> list[tuple[str, dict[str, Any]]]:
    events: list[tuple[str, dict[str, Any]]] = []
    for block in body.split("\n\n"):
        if not block.strip():
            continue
        name = data = None
        for line in block.split("\n"):
            if line.startswith("event: "):
                name = line[len("event: ") :]
            elif line.startswith("data: "):
                data = json.loads(line[len("data: ") :])
        assert name is not None and data is not None, block
        events.append((name, data))
    return events


def prompt_text(messages: list[ChatTurn]) -> str:
    return "\n\n".join(m.content for m in messages)


# ---------------------------------------------------------------------------- fixtures


@pytest.fixture
def avatars_dir(tmp_path: Path) -> Path:
    return tmp_path / "avatars"


@pytest.fixture
def settings(tmp_path: Path, avatars_dir: Path) -> Settings:
    return Settings(
        db_path=tmp_path / "lyris.db",
        ollama_url="http://127.0.0.1:9",
        chat_model="chat-model:test",
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


async def post_card(client: httpx.AsyncClient, card: dict[str, Any], token: str | None = None) -> dict[str, Any]:
    resp = await client.post("/api/cards", json={"card": card, "avatar_token": token})
    assert resp.status_code == 200, resp.text
    return dict(resp.json())


async def post_persona(client: httpx.AsyncClient, name: str, gender: str) -> dict[str, Any]:
    resp = await client.post("/api/personas", json={"name": name, "gender": gender, "description": "Sinh viên."})
    assert resp.status_code == 200, resp.text
    return dict(resp.json())


async def send(client: httpx.AsyncClient, story_id: int, content: str) -> list[tuple[str, dict[str, Any]]]:
    resp = await client.post(f"/api/stories/{story_id}/messages", json={"content": content})
    assert resp.status_code == 200, resp.text
    events = parse_sse(resp.text)
    assert events[-1][0] == "done", events
    return events


# ---------------------------------------------------------------------------- card -> story -> chat


async def test_card_persona_story_chat_uses_that_card(
    client: httpx.AsyncClient, fake: FakeLLM, settings: Settings
) -> None:
    card = await post_card(client, card_body())
    persona = await post_persona(client, "Ngọc Anh", "female")

    resp = await client.post("/api/stories", json={"card_id": card["id"], "persona_id": persona["id"]})
    assert resp.status_code == 200, resp.text
    story = resp.json()
    assert story["title"] == "Trần Minh Khang & Ngọc Anh"
    assert story["card_name"] == "Trần Minh Khang" and story["persona_name"] == "Ngọc Anh"
    assert story["scenario"] == "Ngọc Anh hẹn Trần Minh Khang ở quán cà phê quen."
    assert story["narration_pronouns"] == {"character": "anh", "player": "cô"}  # frontmatter viet_hien_dai
    assert story["relationship_type"] == "het"
    assert story["model_name"] == settings.chat_model

    msgs = (await client.get(f"/api/stories/{story['id']}/messages")).json()
    assert [m["role"] for m in msgs] == ["assistant"]
    assert msgs[0]["raw_content"] == "Trần Minh Khang ngẩng lên. \"Ngọc Anh, em tới rồi à?\" [Thought: Cuối cùng cũng tới.]"
    assert msgs[0]["thought"] == "Cuối cùng cũng tới."

    events = await send(client, story["id"], "Chào anh, em tới muộn.")
    assert [e[0] for e in events][:2] == ["user_message", "start"]
    first_reply = events[-1][1]["message"]
    assert first_reply["thought"] == "Lại đến muộn. Thôi, bỏ qua lần này."

    call = fake.calls[-1]
    assert call["model"] == settings.chat_model
    text = prompt_text(call["messages"])
    assert "Kiến trúc sư 27 tuổi ở Sài Gòn, thân với Ngọc Anh từ hồi đại học." in text
    assert "Điềm tĩnh, chu đáo." in text
    assert "Ngọc Anh hẹn Trần Minh Khang ở quán cà phê quen." in text
    # Văn phong của đúng style profile của card (không có frontmatter).
    style = load_style("viet_hien_dai", "vi")
    assert style.strip().splitlines()[0] in text
    assert "title:" not in text and "address_examples" not in text
    # Không bao giờ vào prompt: ghi chú người tạo, lời mở đầu phụ, placeholder chưa thay.
    assert CREATOR_NOTE not in text and "LOI_MO_DAU_PHU" not in text
    assert "{{user}}" not in text and "{{char}}" not in text
    roles = [m.role for m in call["messages"]]
    assert roles[0] == "system" and roles[-1] == "user"
    assert any(m.role == "assistant" and "Ngọc Anh, em tới rồi à?" in m.content for m in call["messages"])

    # Sửa card -> lượt sau dùng card mới; snapshot của lượt cũ giữ prompt cũ.
    current = (await client.get(f"/api/cards/{card['id']}")).json()
    resp = await client.put(f"/api/cards/{card['id']}", json={**current, "personality": "Nóng nảy, thẳng thắn."})
    assert resp.status_code == 200, resp.text
    await send(client, story["id"], "Anh giận em à?")
    text2 = prompt_text(fake.calls[-1]["messages"])
    assert "Nóng nảy, thẳng thắn." in text2 and "Điềm tĩnh, chu đáo." not in text2

    snap = (await client.get(f"/api/messages/{first_reply['id']}/snapshot")).json()
    old = "\n\n".join(m["content"] for m in snap["messages"])
    assert "Điềm tĩnh, chu đáo." in old and "Nóng nảy, thẳng thắn." not in old

    stories = (await client.get("/api/stories")).json()
    assert stories[0]["id"] == story["id"]  # hoạt động gần nhất lên đầu
    assert stories[0]["updated_at"] >= story["updated_at"]


async def test_dm_story_english_language_and_alternate_greeting(client: httpx.AsyncClient, fake: FakeLLM) -> None:
    card = await post_card(client, card_body())
    persona = await post_persona(client, "Lục Trần", "male")
    defaults = (
        await client.get(f"/api/stories/defaults?card_id={card['id']}&persona_id={persona['id']}&language=en")
    ).json()
    assert defaults["settings"]["relationship_type"] == "bl"
    assert defaults["settings"]["narration_pronouns"] == {"character": "he", "player": "he"}

    resp = await client.post(
        "/api/stories",
        json={
            "card_id": card["id"],
            "persona_id": persona["id"],
            "greeting_index": 1,
            "settings": {"language": "en", "mode": "dm"},
        },
    )
    assert resp.status_code == 200, resp.text
    story = resp.json()
    assert story["mode"] == "dm" and story["language"] == "en"
    assert story["narration_pronouns"] == {"character": "he", "player": "he"}
    msgs = (await client.get(f"/api/stories/{story['id']}/messages")).json()
    assert msgs[0]["raw_content"] == "LOI_MO_DAU_PHU Trần Minh Khang nhắn cho Lục Trần."
    assert msgs[0]["mode"] == "dm"

    await send(client, story["id"], "Hi.")
    call = fake.calls[-1]
    text = prompt_text(call["messages"])
    assert "LOI_MO_DAU_PHU Trần Minh Khang nhắn cho Lục Trần." in text
    assert load_style("viet_hien_dai", "en").strip().splitlines()[0] in text


# ---------------------------------------------------------------------------- preview == chat thật


async def test_test_chat_prompt_matches_real_story_prompt(client: httpx.AsyncClient, fake: FakeLLM) -> None:
    """Chat thử với card chưa lưu dựng đúng prompt mà story thật của card đó sẽ dùng."""
    body = card_body()
    persona = await post_persona(client, "Ngọc Anh", "female")
    card = await post_card(client, body)
    resp = await client.post("/api/stories", json={"card_id": card["id"], "persona_id": persona["id"]})
    story = resp.json()
    story_settings = {
        k: story[k]
        for k in ("scenario", "language", "mode", "relationship_type", "pov", "thought_style", "narration_pronouns")
    }

    await send(client, story["id"], "Chào anh.")
    real = fake.calls[-1]

    resp = await client.post(
        "/api/cards/test-chat",
        json={
            "card": body,
            "persona_id": persona["id"],
            "settings": story_settings,
            "messages": [
                {"role": "assistant", "content": body["greeting"]},
                {"role": "user", "content": "Chào anh."},
            ],
        },
    )
    assert resp.status_code == 200, resp.text
    assert parse_sse(resp.text)[-1][0] == "done"
    test = fake.calls[-1]
    # Phase 3: story thật có thêm các dòng state ở ghi chú cuối (khối F: chỉ dẫn diễn xuất, cảnh, ký ức);
    # chat thử trong Studio không có state (docs/phase3.md §6). Mọi phần còn lại phải giống hệt.
    test_msgs = [m.model_dump() for m in test["messages"]]
    real_msgs = [m.model_dump() for m in real["messages"]]
    assert test_msgs[:-1] == real_msgs[:-1]
    assert test_msgs[-1]["role"] == real_msgs[-1]["role"] == "user"
    test_lines, real_lines = test_msgs[-1]["content"].splitlines(), real_msgs[-1]["content"].splitlines()
    remaining = iter(real_lines)
    assert all(line in remaining for line in test_lines), "ghi chú của chat thử phải nằm trọn trong ghi chú thật"
    extra = [line for line in real_lines if line not in test_lines]
    assert all(line.startswith(("- ", "  ")) or not line.strip() for line in extra), extra
    assert test["stop"] == real["stop"] and test["options"] == real["options"]

    resp = await client.post(
        "/api/cards/preview-prompt", json={"card": body, "persona_id": persona["id"], "settings": story_settings}
    )
    assert resp.status_code == 200, resp.text
    preview = resp.json()
    assert preview["messages"][0] == real["messages"][0].model_dump()
    assert preview["num_ctx"] == 8192 and preview["token_estimate"]["total"] > 0


# ---------------------------------------------------------------------------- import / export


EXTERNAL_V2: dict[str, Any] = {
    "spec": "chara_card_v2",
    "spec_version": "2.0",
    "data": {
        "name": "Aria",
        "description": "She is a starship pilot who trusts {{user}} with her life.",
        "personality": "Bold, curious.",
        "scenario": "On the bridge of the Andromeda with {{user}}.",
        "first_mes": "Aria glances at {{user}}. \"Ready to jump?\"",
        "mes_example": "<START>\n{{user}}: Hi.\n{{char}}: Hey, rookie.",
        "creator_notes": "Made for testing.",
        "system_prompt": "You are Aria.",
        "post_history_instructions": "",
        "alternate_greetings": ["Aria is asleep at the helm."],
        "character_book": {"entries": [{"keys": ["Andromeda"], "content": "A ship."}]},
        "tags": ["Sci-Fi", "pilot"],
        "creator": "someone",
        "character_version": "1.2",
        "extensions": {"depth_prompt": {"prompt": "x", "depth": 4}},
    },
}


async def test_import_json_save_story_and_reexport_keeps_v2_data(client: httpx.AsyncClient, fake: FakeLLM) -> None:
    resp = await client.post(
        "/api/cards/import",
        content=json.dumps(EXTERNAL_V2).encode(),
        headers={"Content-Type": "application/octet-stream"},  # trình duyệt không biết kiểu file
    )
    assert resp.status_code == 200, resp.text
    draft = resp.json()
    assert draft["avatar_token"] is None
    assert draft["warnings"]
    assert draft["card"]["language"] == "en" and draft["card"]["gender"] == "female"

    # Bản nháp import phải lưu được qua đúng validation của API.
    saved = await post_card(client, draft["card"], draft["avatar_token"])
    assert saved["avatar"] is None and saved["alternate_greetings"] == ["Aria is asleep at the helm."]

    persona = await post_persona(client, "Lục Trần", "male")
    story = (await client.post("/api/stories", json={"card_id": saved["id"], "persona_id": persona["id"]})).json()
    assert story["language"] == "en" and story["narration_pronouns"] == {"character": "she", "player": "he"}
    await send(client, story["id"], "Let's go.")
    text = prompt_text(fake.calls[-1]["messages"])
    assert "She is a starship pilot who trusts Lục Trần with her life." in text
    # Dữ liệu V2 không dùng tới không vào prompt.
    assert "You are Aria." not in text and "A ship." not in text and "Made for testing." not in text

    exported = (await client.get(f"/api/cards/{saved['id']}/export?format=json")).json()
    data = exported["data"]
    # Phase 4: book thành mục thế giới khi lưu card (và bị bỏ khỏi extensions); export dựng lại book từ các mục.
    assert "character_book" not in saved["extensions"].get("v2", {})
    book_entries = data["character_book"]["entries"]
    assert [(e["keys"], e["content"]) for e in book_entries] == [(["Andromeda"], "A ship.")]
    assert book_entries[0]["extensions"]["lyris"]["known_by"] == ["*"]
    assert data["system_prompt"] == "You are Aria."
    # Phase 2c: tác giả là account đang giữ card (card nhập vào thuộc account nhập), không phải "someone".
    account = (await client.get("/api/account")).json()
    assert data["creator"] == f"@{account['handle']}" and data["character_version"] == "1.2"
    assert data["extensions"]["lyris"]["creator_uid"] == account["uid"]
    assert data["extensions"]["depth_prompt"] == {"prompt": "x", "depth": 4}
    assert data["first_mes"] == EXTERNAL_V2["data"]["first_mes"]
    assert data["mes_example"] == EXTERNAL_V2["data"]["mes_example"]


async def test_png_export_import_roundtrip_with_avatar(
    client: httpx.AsyncClient, avatars_dir: Path
) -> None:
    body = card_body(
        appearance="Cao, đeo kính.",
        background="Lớn lên ở Đà Lạt.",
        goals="Mở văn phòng riêng.",
        secrets="Thích {{user}} từ lâu.",
        speech_style="Nói chậm.",
        example_dialogues="{{user}}: Anh khoẻ không?\n{{char}}: Khoẻ, còn em?",
        extensions={"custom": {"a": 1}},
    )
    card = await post_card(client, body)
    resp = await client.put(
        f"/api/cards/{card['id']}/avatar", content=png_bytes((900, 600)), headers={"Content-Type": "image/png"}
    )
    assert resp.status_code == 200, resp.text
    card = resp.json()

    png = (await client.get(f"/api/cards/{card['id']}/export?format=png")).content
    resp = await client.post("/api/cards/import", content=png, headers={"Content-Type": "image/png"})
    assert resp.status_code == 200, resp.text
    result = resp.json()
    assert result["warnings"] == []
    assert result["avatar_token"]

    # uid là mã riêng của từng bản ghi; tác giả là account đang dùng, không đọc từ file.
    skip = {"id", "uid", "avatar", "avatar_url", "story_count", "updated_at", "creator_handle", "creator_name"}
    original = {k: v for k, v in card.items() if k not in skip}
    imported = {k: v for k, v in result["card"].items() if k not in skip}
    assert imported == original
    assert result["card"]["uid"] is None

    saved = await post_card(client, result["card"], result["avatar_token"])
    assert saved["avatar"] and saved["avatar"] != card["avatar"]
    got = await client.get(saved["avatar_url"])
    assert got.status_code == 200 and got.headers["cache-control"].endswith("immutable")
    with Image.open(io.BytesIO(got.content)) as img:
        assert img.format == "PNG" and max(img.size) <= 768 and img.size == (768, 512)
    assert not list((avatars_dir / "tmp").glob("*.png"))

    persona_id = (await client.get("/api/personas")).json()[0]["id"]
    story = (await client.post("/api/stories", json={"card_id": saved["id"], "persona_id": persona_id})).json()
    assert story["card_avatar_url"] == saved["avatar_url"]


# ---------------------------------------------------------------------------- draft -> save -> story


async def test_draft_save_and_open_story(client: httpx.AsyncClient, fake: FakeLLM, settings: Settings) -> None:
    resp = await client.post(
        "/api/cards/draft", json={"idea": "Kiến trúc sư ở Sài Gòn, thầm thích bạn đại học", "language": "vi"}
    )
    assert resp.status_code == 200, resp.text
    draft = resp.json()
    assert draft["avatar_token"] is None
    assert fake.calls[-1]["model"] == settings.draft_model
    assert draft["card"]["style_profile"] == "viet_hien_dai"

    saved = await post_card(client, draft["card"])
    persona_id = (await client.get("/api/personas")).json()[0]["id"]
    story = (await client.post("/api/stories", json={"card_id": saved["id"], "persona_id": persona_id})).json()
    msgs = (await client.get(f"/api/stories/{story['id']}/messages")).json()
    assert "Lâm Vãn" in msgs[0]["raw_content"] and "{{user}}" not in msgs[0]["raw_content"]
    assert msgs[0]["thought"] and msgs[0]["thought"].count("\n") == 1  # 2 Thought
    await send(client, story["id"], "Em xin lỗi, kẹt xe quá.")
    assert fake.calls[-1]["model"] == settings.chat_model


# ---------------------------------------------------------------------------- xoá có ràng buộc


async def test_delete_card_and_persona_409_then_with_stories(app: FastAPI, client: httpx.AsyncClient) -> None:
    repo: Repo = app.state.repo
    card = await post_card(client, card_body())
    persona = await post_persona(client, "Ngọc Anh", "female")
    other_persona = await post_persona(client, "Lục Trần", "male")
    s1 = (await client.post("/api/stories", json={"card_id": card["id"], "persona_id": persona["id"]})).json()
    s2 = (await client.post("/api/stories", json={"card_id": card["id"], "persona_id": other_persona["id"]})).json()
    events = await send(client, s1["id"], "Chào anh.")
    reply_id = events[-1][1]["message"]["id"]
    assert (await client.put(f"/api/messages/{reply_id}/feedback", json={"rating": "up"})).status_code == 200

    resp = await client.delete(f"/api/personas/{persona['id']}")
    assert resp.status_code == 409
    assert resp.json()["detail"] == "Có 1 story đang dùng persona này. Xoá luôn các story đó?"
    resp = await client.delete(f"/api/cards/{card['id']}")
    assert resp.status_code == 409
    assert resp.json()["detail"] == "Có 2 story đang dùng nhân vật này. Xoá luôn các story đó?"

    resp = await client.delete(f"/api/personas/{persona['id']}?with_stories=true")
    assert resp.status_code == 200 and resp.json() == {"deleted_stories": 1}
    assert (await client.get(f"/api/stories/{s1['id']}")).status_code == 404
    conn = repo.conn
    assert conn.execute("SELECT COUNT(*) FROM messages WHERE story_id = ?", (s1["id"],)).fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0] == 0
    assert (await client.get(f"/api/cards/{card['id']}")).json()["story_count"] == 1

    resp = await client.delete(f"/api/cards/{card['id']}?with_stories=true")
    assert resp.status_code == 200 and resp.json() == {"deleted_stories": 1}
    assert (await client.get(f"/api/stories/{s2['id']}")).status_code == 404
    personas = {p["name"]: p["story_count"] for p in (await client.get("/api/personas")).json()}
    assert personas["Lục Trần"] == 0
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


async def test_persona_edit_accepts_persona_out_as_sent_by_ui(client: httpx.AsyncClient) -> None:
    """Trang Persona gửi lại nguyên PersonaOut (có story_count) khi sửa: không được 422."""
    out = (await client.get("/api/personas")).json()[0]
    assert out["story_count"] == 1
    resp = await client.put(f"/api/personas/{out['id']}", json={**out, "description": "Đã sửa."})
    assert resp.status_code == 200, resp.text
    assert resp.json()["description"] == "Đã sửa." and resp.json()["story_count"] == 1
    resp = await client.post("/api/personas", json={**out, "id": None, "name": "Bản khác"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["story_count"] == 0


# ---------------------------------------------------------------------------- seed khi đã xoá card seed


async def test_seed_story_falls_back_to_users_own_card(settings: Settings) -> None:
    """Người dùng xoá card Lạc Dương: story "seed" (POST {} hoặc lúc khởi động) dùng card còn lại
    với thiết lập của chính card đó, không mượn bối cảnh Lạc Dương và không để {{user}} chưa thay."""
    fake = FakeLLM(replies=[REPLY])
    app = create_app(settings, fake)
    async with app.router.lifespan_context(app):
        async with owner_client(app, base_url="http://test") as client:
            seed_card = next(c for c in (await client.get("/api/cards")).json() if c["name"] == "Lạc Dương")
            mine = await post_card(client, card_body())
            assert (await client.delete(f"/api/cards/{seed_card['id']}?with_stories=true")).status_code == 200

            resp = await client.post("/api/stories", json={"title": "Thử"})
            assert resp.status_code == 200, resp.text
            story = resp.json()
            assert story["card_id"] == mine["id"] and story["persona_name"] == "Lâm Vãn"
            assert story["title"] == "Thử"
            assert story["scenario"] == "Lâm Vãn hẹn Trần Minh Khang ở quán cà phê quen."
            assert story["model_name"] == settings.chat_model
            msgs = (await client.get(f"/api/stories/{story['id']}/messages")).json()
            assert "{{user}}" not in msgs[0]["raw_content"] and "Lâm Vãn" in msgs[0]["raw_content"]

            for s in (await client.get("/api/stories")).json():
                assert (await client.delete(f"/api/stories/{s['id']}")).status_code == 200

    # Khởi động lại khi không còn story nào: seed chỉ chạy một lần cho mỗi DB, nên danh sách người dùng
    # đã xoá hết vẫn trống và card seed không tự quay lại.
    app = create_app(settings, fake)
    async with app.router.lifespan_context(app):
        async with owner_client(app, base_url="http://test") as client:
            assert (await client.get("/api/stories")).json() == []
            cards = [c["name"] for c in (await client.get("/api/cards")).json()]
            assert cards == ["Trần Minh Khang"]
            # Người dùng tự bấm tạo story mặc định thì vẫn được, với thiết lập của card còn lại.
            story = (await client.post("/api/stories", json={})).json()
            assert story["card_name"] == "Trần Minh Khang"
            assert story["title"] == "Trần Minh Khang & Lâm Vãn"
            assert story["model_name"] == settings.chat_model
            assert "Lạc Dương" not in story["scenario"]


async def test_seed_story_unchanged_while_seed_card_exists(client: httpx.AsyncClient) -> None:
    await post_card(client, card_body())  # card mới hơn không làm đổi story seed
    story = (await client.post("/api/stories", json={})).json()
    expected = load_default_story_settings()
    assert story["card_name"] == "Lạc Dương" and story["persona_name"] == "Lâm Vãn"
    assert story["title"] == expected["title"] and story["scenario"] == expected["scenario"]
    assert story["narration_pronouns"] == expected["narration_pronouns"]
    msgs = (await client.get(f"/api/stories/{story['id']}/messages")).json()
    assert msgs[0]["raw_content"] == load_seed_card().greeting


# ---------------------------------------------------------------------------- DB Phase 1 -> migration 0003


def _build_phase1_db(path: Path) -> None:
    """DB đúng schema Phase 1 (migration 0001-0002) với dữ liệu seed, ghi bằng SQL thuần."""
    conn = connect(path)
    try:
        for version, name in ((1, "0001_init.sql"), (2, "0002_thought_style.sql")):
            sql = (MIGRATIONS_DIR / name).read_text(encoding="utf-8")
            conn.executescript(f"BEGIN;\n{sql}\n;\nPRAGMA user_version = {version};\nCOMMIT;\n")
        card, persona, story = load_seed_card(), load_seed_persona(), load_default_story_settings()
        conn.execute(
            "INSERT INTO character_cards (name, gender, language, description, personality, style_profile,"
            " address_terms_json, greeting, tags_json, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '2026-01-01T00:00:00.000Z')",
            (
                card.name,
                card.gender,
                card.language,
                card.description,
                card.personality,
                card.style_profile,
                json.dumps(card.address_terms.model_dump(), ensure_ascii=False),
                card.greeting,
                json.dumps(card.tags, ensure_ascii=False),
            ),
        )
        conn.execute(
            "INSERT INTO personas (name, gender, description) VALUES (?, ?, ?)",
            (persona.name, persona.gender, persona.description),
        )
        for title in ("Cũ", "Mới hơn"):
            conn.execute(
                "INSERT INTO stories (card_id, persona_id, title, scenario, narration_pronouns_json, updated_at)"
                " VALUES (1, 1, ?, ?, ?, '2026-01-01T00:00:00.000Z')",
                (title, story["scenario"], json.dumps(story["narration_pronouns"], ensure_ascii=False)),
            )
        conn.execute(
            "INSERT INTO messages (story_id, turn_index, role, mode, raw_content, visible_content, created_at)"
            " VALUES (1, 0, 'assistant', 'story', 'Lượt cũ.', 'Lượt cũ.', '2026-02-01T00:00:00.000Z')"
        )
        conn.execute("INSERT INTO feedback (message_id, rating) VALUES (1, 'up')")
    finally:
        conn.close()


async def test_phase1_database_migrates_and_works(tmp_path: Path, avatars_dir: Path) -> None:
    db = tmp_path / "phase1.db"
    _build_phase1_db(db)
    settings = Settings(
        db_path=db, ollama_url="http://127.0.0.1:9", chat_model="chat-model:test", num_ctx=8192,
        avatars_dir=avatars_dir,
    )
    fake = FakeLLM(replies=[REPLY])
    app = create_app(settings, fake)
    async with app.router.lifespan_context(app):
        conn: sqlite3.Connection = app.state.repo.conn
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 11
        async with owner_client(app, base_url="http://test") as client:
            stories = (await client.get("/api/stories")).json()
            # Không tạo thêm story seed; story có message mới nhất lên đầu.
            assert [s["title"] for s in stories] == ["Cũ", "Mới hơn"]
            assert stories[0]["updated_at"] == "2026-02-01T00:00:00.000Z"
            assert stories[0]["card_avatar_url"] is None

            cards = (await client.get("/api/cards")).json()
            assert len(cards) == 1 and cards[0]["story_count"] == 2
            card = (await client.get(f"/api/cards/{cards[0]['id']}")).json()
            assert card["scenario"] == "" and card["alternate_greetings"] == [] and card["extensions"] == {}
            assert card["avatar"] is None and card["creator_notes"] == ""

            # Chat tiếp trên story cũ vẫn chạy.
            await send(client, stories[0]["id"], "Chào cậu.")
            msgs = (await client.get(f"/api/stories/{stories[0]['id']}/messages")).json()
            assert msgs[0]["rating"] == "up" and len(msgs) == 3

            # Card cũ sửa, gắn ảnh, mở story mới, export được.
            resp = await client.put(f"/api/cards/{card['id']}", json={**card, "scenario": "Vườn trường."})
            assert resp.status_code == 200, resp.text
            resp = await client.put(
                f"/api/cards/{card['id']}/avatar", content=png_bytes(), headers={"Content-Type": "image/png"}
            )
            assert resp.status_code == 200, resp.text
            new = (await client.post("/api/stories", json={"card_id": card["id"], "persona_id": 1})).json()
            assert new["scenario"] == "Vườn trường." and new["card_avatar_url"]
            assert (await client.get(f"/api/cards/{card['id']}/export?format=png")).status_code == 200
    # Mở lại: không migrate lại, không lỗi.
    conn2 = connect(db)
    try:
        assert migrate(conn2) == 11
        assert conn2.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        conn2.close()
