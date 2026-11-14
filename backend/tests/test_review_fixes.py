"""Hồi quy cho các lỗi đã sửa sau đợt review: cài đặt model, model của Studio, ảnh MPO, persona mặc
định bị xoá, seed một lần, dấu template khi nhân bản/nhập, xưng hô trong prompt tiếng Anh, ghi công ảnh
template, lời mở đầu Morwenna và card mẫu của harness."""
from __future__ import annotations

import io
import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from PIL import Image

from lyris.api.app import create_app
from lyris.config import Settings
from lyris.db.connection import connect, migrate
from lyris.db.repo import ANY_ACCOUNT, Repo
from lyris.llm.base import LLMError
from lyris.llm.fake import FakeLLM
from lyris.models import AddressTerms, CharacterCard, Message, NarrationPronouns, Persona, Story
from lyris.prompt.builder import build_prompt
from lyris.seed import SEEDED_FLAG, ensure_seed
from lyris.seed.templates import get_template
from lyris.studio.avatars import normalize_image
from lyris.studio.card_v2 import export_card_json, import_card, strip_template_marker
from tests.authutil import owner_client

REPO_ROOT = Path(__file__).resolve().parents[2]

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
    "tags": ["Hiện đại"],
}


class ListingLLM(FakeLLM):
    """LLM giả liệt kê model như Ollama; `models` sửa được giữa chừng (giả lập xoá model)."""

    def __init__(self, models: list[str]) -> None:
        super().__init__(json_replies=[DRAFT_JSON])
        self.models = models

    async def list_models(self) -> list[str]:
        if not self.models:
            raise LLMError("Không kết nối được Ollama")
        return list(self.models)


def make_settings(tmp_path: Path, *, draft_model: str | None = None) -> Settings:
    return Settings(
        db_path=tmp_path / "lyris.db",
        ollama_url="http://127.0.0.1:9",
        chat_model="env-model",
        num_ctx=8192,
        avatars_dir=tmp_path / "avatars",
        draft_model=draft_model or "env-model",
    )


async def _open(settings: Settings, llm: FakeLLM) -> AsyncIterator[tuple[FastAPI, httpx.AsyncClient]]:
    app = create_app(settings, llm)
    async with app.router.lifespan_context(app):
        async with owner_client(app, base_url="http://test") as c:
            yield app, c


@pytest.fixture
def llm() -> ListingLLM:
    return ListingLLM(["gemma4:12b", "custom:7b"])


@pytest.fixture
async def env(tmp_path: Path, llm: ListingLLM) -> AsyncIterator[tuple[FastAPI, httpx.AsyncClient]]:
    async for pair in _open(make_settings(tmp_path), llm):
        yield pair


def _repo(app: FastAPI) -> Repo:
    repo: Repo = app.state.repo
    return repo


def card_body(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "name": "Trần Minh Khang",
        "gender": "male",
        "language": "vi",
        "description": "Kiến trúc sư 27 tuổi ở Sài Gòn, thân với {{user}} từ hồi đại học.",
        "style_profile": "viet_hien_dai",
        "address_terms": {"self_term": "anh", "player_term": "em", "nicknames": [], "others": ""},
        "greeting": "{{char}} ngẩng lên. \"{{user}}, em tới rồi à?\"",
    }
    body.update(overrides)
    return body


# ---------------------------------------------------------------------------- PUT /api/settings


async def test_unchanged_missing_model_does_not_block_persona_change(
    env: tuple[FastAPI, httpx.AsyncClient], llm: ListingLLM
) -> None:
    _, client = env
    resp = await client.put("/api/settings", json={"default_persona_id": None, "default_chat_model": "custom:7b"})
    assert resp.status_code == 200, resp.text
    persona = (await client.post("/api/personas", json={"name": "Tô Hiểu", "gender": "male"})).json()

    llm.models = ["gemma4:12b"]  # người dùng xoá custom:7b khỏi Ollama
    # Client gửi lại cả model cũ khi chỉ đổi persona: không được 422.
    resp = await client.put(
        "/api/settings", json={"default_persona_id": persona["id"], "default_chat_model": "custom:7b"}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"default_persona_id": persona["id"], "default_chat_model": "custom:7b"}
    resp = await client.put("/api/settings", json={"default_chat_model": " custom:7b "})
    assert resp.status_code == 200 and resp.json()["default_chat_model"] == "custom:7b"
    # Đổi sang một model khác vẫn được kiểm tra.
    resp = await client.put("/api/settings", json={"default_chat_model": "khong-co:1b"})
    assert resp.status_code == 422 and "ollama pull khong-co:1b" in resp.json()["detail"]


# ---------------------------------------------------------------------------- model của Studio


def _test_chat_body(persona_id: int) -> dict[str, Any]:
    return {
        "card": card_body(),
        "persona_id": persona_id,
        "settings": {
            "scenario": "Quán cà phê quen.",
            "language": "vi",
            "mode": "story",
            "relationship_type": "het",
            "pov": "third",
            "thought_style": "inline",
            "narration_pronouns": {"character": "anh", "player": "cô"},
        },
        "messages": [{"role": "user", "content": "Chào anh."}],
    }


async def test_studio_uses_default_chat_model(env: tuple[FastAPI, httpx.AsyncClient], llm: ListingLLM) -> None:
    app, client = env
    persona_id = _repo(app).first_persona_id(account_id=ANY_ACCOUNT)
    assert persona_id is not None

    # Chưa chọn model mặc định: dùng model của biến môi trường.
    resp = await client.post("/api/cards/test-chat", json=_test_chat_body(persona_id))
    assert resp.status_code == 200 and llm.calls[-1]["model"] == "env-model"

    assert (await client.put("/api/settings", json={"default_chat_model": "custom:7b"})).status_code == 200
    resp = await client.post("/api/cards/test-chat", json=_test_chat_body(persona_id))
    assert resp.status_code == 200, resp.text
    assert llm.calls[-1]["model"] == "custom:7b"

    resp = await client.post("/api/cards/draft", json={"idea": "Kiến trúc sư trầm tính", "language": "vi"})
    assert resp.status_code == 200, resp.text
    assert llm.calls[-1]["model"] == "custom:7b"


async def test_explicit_draft_model_still_wins(tmp_path: Path) -> None:
    llm = ListingLLM(["gemma4:12b", "custom:7b"])
    async for _, client in _open(make_settings(tmp_path, draft_model="draft:3b"), llm):
        assert (await client.put("/api/settings", json={"default_chat_model": "custom:7b"})).status_code == 200
        resp = await client.post("/api/cards/draft", json={"idea": "Kiến trúc sư trầm tính", "language": "vi"})
        assert resp.status_code == 200, resp.text
        assert llm.calls[-1]["model"] == "draft:3b"


# ---------------------------------------------------------------------------- ảnh MPO


def test_normalize_accepts_mpo_camera_jpeg() -> None:
    primary = Image.new("RGB", (64, 48), (200, 30, 30))
    preview = Image.new("RGB", (32, 24), (30, 30, 200))
    buf = io.BytesIO()
    primary.save(buf, format="MPO", save_all=True, append_images=[preview])
    data = buf.getvalue()
    assert data[:3] == b"\xff\xd8\xff"
    with Image.open(io.BytesIO(data)) as probe:
        assert probe.format == "MPO"

    out = normalize_image(data)
    with Image.open(io.BytesIO(out)) as img:
        assert img.format == "PNG" and img.size == (64, 48)
        r, g, b = img.convert("RGB").getpixel((10, 10))  # type: ignore[misc]
        assert r > 150 and b < 100  # khung chính, không phải ảnh preview


# ---------------------------------------------------------------------------- persona mặc định bị xoá


def test_deleted_default_persona_not_revived_by_reused_id(tmp_path: Path) -> None:


    conn = connect(tmp_path / "lyris.db")
    try:
        migrate(conn)
        repo = Repo(conn)
        repo.create_persona(Persona(name="A", gender="female"), account_id=repo.owner_id())
        b = repo.create_persona(Persona(name="B", gender="male"), account_id=repo.owner_id())
        assert b.id is not None
        from lyris.models import AppSettings

        repo.set_app_settings(AppSettings(default_persona_id=b.id, default_chat_model="custom:7b"), account_id=repo.owner_id())
        repo.delete_persona(b.id, account_id=ANY_ACCOUNT)
        new = repo.create_persona(Persona(name="Mới", gender="female"), account_id=repo.owner_id())
        assert new.id == b.id  # SQLite dùng lại id lớn nhất đã xoá
        settings = repo.get_app_settings(account_id=repo.owner_id())
        assert settings.default_persona_id is None
        assert settings.default_chat_model == "custom:7b"  # cài đặt khác giữ nguyên
    finally:
        conn.close()


# ---------------------------------------------------------------------------- seed một lần


def test_seed_runs_once_per_db(tmp_path: Path) -> None:


    path = tmp_path / "lyris.db"
    conn = connect(path)
    try:
        migrate(conn)
        repo = Repo(conn)
        first = ensure_seed(repo)
        assert first is not None and repo.get_flag(SEEDED_FLAG)
        assert [c.name for c in repo.list_cards(account_id=ANY_ACCOUNT)] == ["Lạc Dương"]
        for card in repo.list_cards(account_id=ANY_ACCOUNT):
            assert card.id is not None
            repo.delete_card(card.id, with_stories=True, account_id=ANY_ACCOUNT)
        for persona in repo.list_personas(account_id=ANY_ACCOUNT):
            assert persona.id is not None
            repo.delete_persona(persona.id, with_stories=True, account_id=ANY_ACCOUNT)
    finally:
        conn.close()

    conn = connect(path)
    try:
        repo = Repo(conn)
        assert ensure_seed(repo) is None  # khởi động lại: không tạo lại thứ người dùng đã xoá
        assert repo.list_cards(account_id=ANY_ACCOUNT) == [] and repo.list_personas(account_id=ANY_ACCOUNT) == [] and repo.list_stories(account_id=ANY_ACCOUNT) == []
    finally:
        conn.close()


def test_seed_marks_existing_db_without_reseeding(tmp_path: Path) -> None:
    """DB cũ có dữ liệu nhưng chưa có cờ: chỉ đánh dấu, không thêm card/persona/story seed."""


    conn = connect(tmp_path / "lyris.db")
    try:
        migrate(conn)
        repo = Repo(conn)
        repo.create_card(CharacterCard.model_validate(card_body(greeting="Chào.")), account_id=repo.owner_id())
        assert ensure_seed(repo) is None
        assert repo.get_flag(SEEDED_FLAG)
        assert [c.name for c in repo.list_cards(account_id=ANY_ACCOUNT)] == ["Trần Minh Khang"]
        assert repo.list_personas(account_id=ANY_ACCOUNT) == [] and repo.list_stories(account_id=ANY_ACCOUNT) == []
    finally:
        conn.close()


# ---------------------------------------------------------------------------- dấu template


async def test_duplicate_template_card_drops_marker(env: tuple[FastAPI, httpx.AsyncClient]) -> None:
    _, client = env
    original = (await client.post("/api/templates/ha-vy/install")).json()
    assert original["extensions"]["lyris"]["template"] == "ha-vy"
    copy = (await client.post(f"/api/cards/{original['id']}/duplicate")).json()
    assert "template" not in copy["extensions"].get("lyris", {})

    assert (await client.delete(f"/api/cards/{original['id']}")).status_code == 200
    rows = {r["slug"]: r for r in (await client.get("/api/templates")).json()}
    assert rows["ha-vy"]["installed_card_id"] is None
    again = (await client.post("/api/templates/ha-vy/install")).json()
    assert again["id"] != copy["id"] and again["name"] == "Hạ Vy"


def test_import_drops_template_marker_keeps_other_extensions() -> None:
    card = CharacterCard.model_validate(
        card_body(extensions={"lyris": {"template": "ha-vy", "khac": 1}, "ngoai": {"a": 1}})
    )
    data = json.dumps(export_card_json(card)).encode("utf-8")
    out = import_card(data, "application/json", styles=["chung", "viet_hien_dai"]).card
    assert out.extensions.get("lyris") == {"khac": 1}
    assert out.extensions.get("ngoai") == {"a": 1}
    assert strip_template_marker({"lyris": {"template": "x"}, "b": 2}) == {"b": 2}


# ---------------------------------------------------------------------------- ghi công ảnh template


async def test_installed_template_carries_image_credit(env: tuple[FastAPI, httpx.AsyncClient]) -> None:
    _, client = env
    card = (await client.post("/api/templates/morwenna-penrose/install")).json()
    notes = card["creator_notes"]
    assert notes.startswith("Sample character bundled with Lyris.")
    assert "Tom Corser" in notes and "CC BY-SA 3.0" in notes
    assert "https://commons.wikimedia.org/wiki/File:Pendeen_Watch_lighthouse_Cornwall.jpg" in notes
    exported = (await client.get(f"/api/cards/{card['id']}/export?format=json")).json()
    assert "Tom Corser" in exported["data"]["creator_notes"]

    lac = (await client.post("/api/templates/lac-duong/install")).json()  # không có ảnh
    assert "Ảnh:" not in lac["creator_notes"]


# ---------------------------------------------------------------------------- prompt tiếng Anh


def _en_prompt(card: CharacterCard) -> str:
    persona = Persona(id=1, name="Lâm Vãn", gender="female", description="A newcomer.")
    story = Story(
        id=1, card_id=1, persona_id=1, title="T", scenario="", language="en", mode="story",
        relationship_type="het", pov="third", narration_pronouns=NarrationPronouns(character="she", player="she"),
    )
    history = [
        Message(story_id=1, turn_index=0, role="user", mode="story", raw_content="Hello.", visible_content="Hello.")
    ]
    return build_prompt(card, persona, story, history).messages[0].content


def test_english_prompt_keeps_address_forms() -> None:
    template = get_template("morwenna-penrose")
    assert template is not None
    s = _en_prompt(template.card.model_copy(update={"id": 1}))
    assert "Forms of address (dialogue and Thoughts only):" in s
    assert "- With others: Calls villagers by their first names" in s
    assert 'calls Lâm Vãn "you"' not in s  # I/you mặc định không cần nhắc

    master = template.card.model_copy(
        update={"id": 1, "address_terms": AddressTerms(self_term="I", player_term="Master", nicknames=[], others="")}
    )
    assert 'Morwenna Penrose calls Lâm Vãn "Master".' in _en_prompt(master)


def test_english_prompt_skips_vietnamese_card_address_text() -> None:
    card = CharacterCard.model_validate(
        {**card_body(), "id": 1, "address_terms": {"self_term": "anh", "player_term": "em", "nicknames": [], "others": "Xưng tôi với đồng nghiệp."}}
    )
    s = _en_prompt(card)
    assert "Xưng tôi" not in s and '"em"' not in s and "Forms of address" not in s


# ---------------------------------------------------------------------------- nội dung


def test_morwenna_greeting_leaves_player_outside() -> None:
    template = get_template("morwenna-penrose")
    assert template is not None
    greeting = template.card.greeting
    assert "{{user}} reached" not in greeting and "into {{user}}'s hands" not in greeting
    assert greeting.rstrip().endswith('?"')
    assert template.image is not None and template.image.creator.startswith("Tom Corser")


@pytest.mark.parametrize("name", ["trung_co_dai.json", "viet_hien_dai.json"])
def test_harness_example_dialogues_have_no_player_lines(name: str) -> None:
    card = json.loads((REPO_ROOT / "harness" / "cards" / name).read_text(encoding="utf-8"))
    lines = [ln for ln in card["card"]["example_dialogues"].splitlines() if ln.strip()] if "card" in card else [
        ln for ln in card["example_dialogues"].splitlines() if ln.strip()
    ]
    assert lines and all(ln.startswith('{{char}}: "') and ln.endswith('"') for ln in lines)
    assert "ngươi" not in "\n".join(lines)
