"""Test backend cho giao diện Lyris (docs/design-impl.md §7): vai trò card, cài đặt chung, /api/system,
extras, lore status, story list mới, model của story, nhân vật mẫu (template).

Không bao giờ gọi Ollama thật: LLM giả, `httpx.MockTransport`, lệnh macOS giả.
"""
from __future__ import annotations

import importlib
import json
import re
import sys
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from lyris.api.app import create_app
from lyris.api.routes_lyris import lore_status, make_preview, model_present
from lyris.api.routes_studio import validate_card
from lyris.config import Settings
from lyris.db.repo import ANY_ACCOUNT, Repo
from lyris.llm.fake import FakeLLM
from lyris.models import AddressTerms, AppSettings, CharacterCard, Message, NarrationPronouns, Persona, Story
from lyris.prompt.builder import get_style_profile, list_style_profiles
from lyris.seed import load_seed_card, seed_card_for_create
from lyris.seed.templates import MAX_IMAGE_BYTES, TEMPLATES_DIR, load_templates
from lyris.studio.card_v2 import export_card_json, import_card
from lyris.studio.draft import DRAFT_SCHEMA, MAX_ROLE_CHARS, build_draft_messages, normalize_role, postprocess_draft
from lyris.system import (
    SystemMonitor,
    collect_machine,
    collect_ollama,
    parse_env_bool,
    parse_env_int,
    parse_low_power,
    parse_memsize,
    parse_on_battery,
    parse_ps,
    parse_tags,
    parse_vm_stat,
    run_command,
)
from tests.authutil import owner_client

HARNESS_DIR = Path(__file__).resolve().parents[2] / "harness"
if str(HARNESS_DIR) not in sys.path:
    sys.path.insert(0, str(HARNESS_DIR))
checks = importlib.import_module("checks")

VM_STAT = """Mach Virtual Memory Statistics: (page size of 16384 bytes)
Pages free:                                    23907.
Pages active:                                 426217.
Pages inactive:                               415596.
Pages wired down:                             587354.
"Translation faults":                      837722009.
Pages occupied by compressor:                  59129.
"""
PMSET = """System-wide power settings:
Currently in use:
 standby              1
 sleep                0 (sleep prevented by powerd)
 lowpowermode         1
 womp                 1
"""
TAGS = {
    "models": [
        {"name": "qwen2.5:7b", "size": 4_683_087_332, "details": {"parameter_size": "7.6B", "quantization_level": "Q4_K_M"}},
        {"name": "gemma4:12b", "size": 8_100_000_000, "details": {"parameter_size": "12B", "quantization_level": "Q4_K_M"}},
        {"model": "no-details:latest"},
        "rác",
    ]
}
PS = {"models": [{"name": "gemma4:12b", "size": 9_400_000_000, "expires_at": "2026-11-12T23:45:00Z"}]}

FAKE_COMMANDS: dict[tuple[str, ...], str] = {
    ("sysctl", "-n", "hw.memsize"): "25769803776\n",
    ("vm_stat",): VM_STAT,
    ("pmset", "-g", "batt"): "Now drawing from 'Battery Power'\n -InternalBattery-0 (id=1)\t80%; discharging;\n",
    ("pmset", "-g"): PMSET,
    ("launchctl", "getenv", "OLLAMA_KV_CACHE_TYPE"): "q8_0\n",
    ("launchctl", "getenv", "OLLAMA_FLASH_ATTENTION"): "1\n",
    ("launchctl", "getenv", "OLLAMA_NUM_PARALLEL"): "1\n",
    ("launchctl", "getenv", "OLLAMA_MAX_LOADED_MODELS"): "\n",
}


def fake_runner(args: list[str]) -> str | None:
    return FAKE_COMMANDS.get(tuple(args))


def ollama_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/api/version":
        return httpx.Response(200, json={"version": "0.12.3"})
    if request.url.path == "/api/tags":
        return httpx.Response(200, json=TAGS)
    if request.url.path == "/api/ps":
        return httpx.Response(200, json=PS)
    return httpx.Response(404, json={"error": "not found"})


def down_handler(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("refused", request=request)


# ---------------------------------------------------------------------------- fixtures


class ListingLLM(FakeLLM):
    """LLM giả có danh sách model như Ollama (để kiểm tra tên model)."""

    def __init__(self, models: list[str] | None = None, *, down: bool = False) -> None:
        super().__init__()
        self.models = models if models is not None else ["gemma4:12b", "qwen2.5:7b", "mistral-nemo:latest"]
        self.down = down

    async def list_models(self) -> list[str]:
        from lyris.llm.base import LLMError

        if self.down:
            raise LLMError("Không kết nối được Ollama")
        return list(self.models)


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
def llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture
async def app(settings: Settings, llm: FakeLLM, tmp_path: Path) -> AsyncIterator[FastAPI]:
    application = create_app(settings, llm)
    async with application.router.lifespan_context(application):
        application.state.lore_dir = tmp_path / "world_wiki"
        yield application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with owner_client(app, base_url="http://test") as c:
        yield c


def _repo(app: FastAPI) -> Repo:
    repo: Repo = app.state.repo
    return repo


def _card(**overrides: Any) -> CharacterCard:
    data: dict[str, Any] = {
        "name": "Hạ Vy",
        "role": "Chủ tiệm sách mùa thu",
        "gender": "female",
        "style_profile": "viet_hien_dai",
        "address_terms": AddressTerms(self_term="mình", player_term="cậu"),
    }
    data.update(overrides)
    return CharacterCard(**data)


def _story(repo: Repo, card_id: int, persona_id: int) -> Story:
    return repo.create_story(
        Story(
            card_id=card_id,
            persona_id=persona_id,
            title="Thử",
            narration_pronouns=NarrationPronouns(character="cô", player="anh"),
        )
    , account_id=repo.owner_id())


# ---------------------------------------------------------------------------- repo


def test_repo_card_role_roundtrip(repo: Repo) -> None:
    card = repo.create_card(_card(), account_id=repo.owner_id())
    assert card.role == "Chủ tiệm sách mùa thu"
    assert card.id is not None
    updated = repo.update_card(card.id, card.model_copy(update={"role": "Người giữ hải đăng"}), account_id=ANY_ACCOUNT)
    assert updated.role == "Người giữ hải đăng"
    assert repo.list_cards(account_id=ANY_ACCOUNT)[0].role == "Người giữ hải đăng"


def test_repo_app_settings(repo: Repo) -> None:
    assert repo.get_app_settings(account_id=repo.owner_id()) == AppSettings()
    persona = repo.create_persona(Persona(name="Vị khách chiều thu", gender="female"), account_id=repo.owner_id())
    assert persona.id is not None
    saved = repo.set_app_settings(AppSettings(default_persona_id=persona.id, default_chat_model="qwen2.5:7b"), account_id=repo.owner_id())
    assert saved == AppSettings(default_persona_id=persona.id, default_chat_model="qwen2.5:7b")
    # Ghi lại (upsert), rồi bỏ model.
    saved = repo.set_app_settings(AppSettings(default_persona_id=persona.id, default_chat_model=None), account_id=repo.owner_id())
    assert saved.default_chat_model is None and saved.default_persona_id == persona.id
    # Persona mặc định bị xoá -> đọc ra None.
    repo.delete_persona(persona.id, account_id=ANY_ACCOUNT)
    assert repo.get_app_settings(account_id=repo.owner_id()).default_persona_id is None


def test_repo_app_settings_ignores_bad_rows(repo: Repo) -> None:
    repo.conn.execute("INSERT INTO app_settings (key, value_json) VALUES ('default_chat_model', '{hỏng')")
    repo.conn.execute("INSERT INTO app_settings (key, value_json) VALUES ('khoa_la', '1')")
    assert repo.get_app_settings(account_id=repo.owner_id()) == AppSettings()


def test_repo_first_persona_and_exists(repo: Repo) -> None:
    assert repo.first_persona_id(account_id=ANY_ACCOUNT) is None
    a = repo.create_persona(Persona(name="A", gender="male"), account_id=repo.owner_id())
    repo.create_persona(Persona(name="B", gender="female"), account_id=repo.owner_id())
    assert a.id is not None
    assert repo.first_persona_id(account_id=ANY_ACCOUNT) == a.id
    assert repo.persona_exists(a.id, account_id=ANY_ACCOUNT) and not repo.persona_exists(9999, account_id=ANY_ACCOUNT)


def test_repo_story_rows(repo: Repo) -> None:
    card = repo.create_card(_card(), account_id=repo.owner_id())
    persona = repo.create_persona(Persona(name="Lâm Vãn", gender="female"), account_id=repo.owner_id())
    assert card.id is not None and persona.id is not None
    empty = _story(repo, card.id, persona.id)
    story = _story(repo, card.id, persona.id)
    assert story.id is not None and empty.id is not None
    repo.insert_message(
        Message(story_id=story.id, turn_index=0, role="assistant", mode="story",
                raw_content="Vy cười. [Thought: Lại tới.]", visible_content="Vy cười.", thought="Lại tới.")
    )
    repo.insert_message(
        Message(story_id=story.id, turn_index=1, role="user", mode="dm",
                raw_content="Chào Vy ((ngại ngùng))", visible_content="Chào Vy")
    )
    # Lượt mới nhất chỉ có chỉ đạo (phần hiển thị rỗng) -> bỏ qua, lấy tin trước đó.
    repo.insert_message(
        Message(story_id=story.id, turn_index=2, role="user", mode="dm",
                raw_content="((im lặng))", visible_content="   ")
    )
    rows = repo.story_rows(account_id=ANY_ACCOUNT)
    assert [r.story.id for r in rows] == [story.id, empty.id]
    top = rows[0]
    assert (top.card_name, top.card_role, top.persona_name) == ("Hạ Vy", "Chủ tiệm sách mùa thu", "Lâm Vãn")
    assert (top.last_visible, top.last_role, top.last_mode) == ("Chào Vy", "user", "dm")
    assert top.updated_at == repo.story_updated_at(story.id)
    assert rows[1].last_visible is None and rows[1].last_role is None
    assert [r.story.id for r in repo.story_rows(empty.id, account_id=ANY_ACCOUNT)] == [empty.id]
    assert repo.story_rows(9999, account_id=ANY_ACCOUNT) == []


def test_repo_template_lookup(repo: Repo) -> None:
    a = repo.create_card(_card(extensions={"lyris": {"template": "ha-vy"}}), account_id=repo.owner_id())
    repo.create_card(_card(extensions={"lyris": {"template": "ha-vy"}}), account_id=repo.owner_id())
    repo.create_card(_card(name="Khác", extensions={"lyris": {"template": 5}, "khac": True}), account_id=repo.owner_id())
    b = repo.create_card(_card(name=" Lạc Dương ", style_profile="trung_hien_dai"), account_id=repo.owner_id())
    assert repo.template_card_ids(account_id=ANY_ACCOUNT) == {"ha-vy": a.id}
    assert repo.card_ids_by_name("Lạc Dương", "trung_hien_dai", account_id=ANY_ACCOUNT) == [b.id]
    assert repo.card_ids_by_name("Lạc Dương", "viet_hien_dai", account_id=ANY_ACCOUNT) == []


# ---------------------------------------------------------------------------- xem trước tin nhắn


def test_make_preview() -> None:
    assert make_preview(None) is None
    assert make_preview("  \n ") is None
    assert make_preview("[Thought: chỉ có suy nghĩ]") is None
    assert make_preview("Vy cười.\n\n[Thought: Lại tới.]\n\n\"Chào cậu.\"") == 'Vy cười. "Chào cậu."'
    assert make_preview("Đi thôi ((nắm tay)) nhé") == "Đi thôi nhé"
    assert make_preview("Mở [Thought: chưa đóng") == "Mở"
    long = "Một " * 100
    out = make_preview(long)
    assert out is not None and len(out) <= 140 and out.endswith("…") and not out.endswith(" …")
    assert make_preview("x" * 200, limit=10) == "x" * 9 + "…"


def test_model_present() -> None:
    assert model_present("gemma4:12b", ["gemma4:12b"])
    assert model_present("mistral-nemo", ["mistral-nemo:latest"])
    assert not model_present("gemma4", ["gemma4:12b"])


# ---------------------------------------------------------------------------- system.py (hàm thuần)


def test_system_parsers() -> None:
    assert parse_memsize("25769803776\n") == 24.0
    assert parse_memsize("abc") is None and parse_memsize(None) is None and parse_memsize("0") is None
    used = parse_vm_stat(VM_STAT)
    assert used == round((426217 + 587354 + 59129) * 16384 / 1024**3, 1)
    assert parse_vm_stat("Pages active: 1.") is None
    assert parse_vm_stat(VM_STAT.replace("Pages wired down", "Pages wired")) is None
    assert parse_on_battery("Now drawing from 'Battery Power'") is True
    assert parse_on_battery("Now drawing from 'AC Power'\n -InternalBattery-0") is False
    assert parse_on_battery("Now drawing from 'UPS Power'") is None
    assert parse_on_battery("") is None
    assert parse_low_power(PMSET) is True
    assert parse_low_power(PMSET.replace("lowpowermode         1", "lowpowermode         0")) is False
    assert parse_low_power(" powermode 1\n") is True and parse_low_power(" powermode 2\n") is False
    assert parse_low_power(" standby 1\n") is None
    assert parse_env_bool("1\n") is True and parse_env_bool("false") is False and parse_env_bool("") is None
    assert parse_env_int("4\n") == 4 and parse_env_int("") is None and parse_env_int("x") is None
    tags = parse_tags(TAGS)
    assert [m.name for m in tags] == ["gemma4:12b", "no-details:latest", "qwen2.5:7b"]
    assert tags[2].size_gb == 4.7 and tags[2].parameter_size == "7.6B" and tags[2].quantization == "Q4_K_M"
    assert tags[1].size_gb is None and tags[1].parameter_size is None
    assert parse_tags({"models": "x"}) == [] and parse_tags(None) == []
    loaded = parse_ps(PS)
    assert loaded[0].name == "gemma4:12b" and loaded[0].size_gb == 9.4 and loaded[0].expires_at
    assert parse_ps([]) == []


def test_collect_machine_with_fake_runner() -> None:
    machine = collect_machine(fake_runner)
    assert machine == {
        "memory_total_gb": 24.0,
        "memory_used_gb": parse_vm_stat(VM_STAT),
        "on_battery": True,
        "low_power_mode": True,
        "kv_cache_type": "q8_0",
        "flash_attention": True,
        "num_parallel": 1,
        "max_loaded_models": None,
    }


def test_collect_machine_survives_broken_runner() -> None:
    def broken(args: list[str]) -> str | None:
        raise RuntimeError("hỏng")

    assert set(collect_machine(broken).values()) == {None}
    assert set(collect_machine(lambda args: None).values()) == {None}


def test_run_command_failures() -> None:
    assert run_command(["/khong/co/lenh/nay"]) is None
    assert run_command([sys.executable, "-c", "import sys; sys.exit(3)"]) is None
    assert run_command([sys.executable, "-c", "print('ok')"]) == "ok\n"
    assert run_command([sys.executable, "-c", "import time; time.sleep(5)"], timeout=0.2) is None


async def test_collect_ollama_ok_and_down() -> None:
    ok = await collect_ollama("http://ollama.test", httpx.MockTransport(ollama_handler))
    assert ok["ollama_reachable"] is True and ok["ollama_version"] == "0.12.3"
    assert [m.name for m in ok["models"]][0] == "gemma4:12b" and ok["loaded"][0].name == "gemma4:12b"
    assert "ollama_error" not in ok

    down = await collect_ollama("http://ollama.test", httpx.MockTransport(down_handler))
    assert down["ollama_reachable"] is False and down["models"] == [] and down["loaded"] == []
    assert "Ollama" in down["ollama_error"]

    def http_500(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="lỗi")

    broken = await collect_ollama("http://ollama.test", httpx.MockTransport(http_500))
    assert broken["ollama_reachable"] is False

    none = await collect_ollama(None)
    assert none["ollama_reachable"] is False and none["ollama_error"]


async def test_system_monitor_caches() -> None:
    calls: list[list[str]] = []
    now = [100.0]

    def runner(args: list[str]) -> str | None:
        calls.append(args)
        return fake_runner(args)

    monitor = SystemMonitor(
        base_url="http://ollama.test",
        transport=httpx.MockTransport(ollama_handler),
        runner=runner,
        clock=lambda: now[0],
    )
    first = await monitor.get("gemma4:12b")
    n = len(calls)
    assert first.memory_total_gb == 24.0 and first.ollama_reachable and first.chat_model_default == "gemma4:12b"
    now[0] += 4.0
    assert await monitor.get("gemma4:12b") is first and len(calls) == n
    # Đổi model mặc định -> đo lại ngay.
    other = await monitor.get("qwen2.5:7b")
    assert other.chat_model_default == "qwen2.5:7b" and len(calls) == 2 * n
    now[0] += 5.1
    await monitor.get("qwen2.5:7b")
    assert len(calls) == 3 * n
    monitor.invalidate()
    await monitor.get("qwen2.5:7b")
    assert len(calls) == 4 * n


# ---------------------------------------------------------------------------- API: cài đặt chung


async def test_settings_get_put(client: httpx.AsyncClient, app: FastAPI) -> None:
    assert (await client.get("/api/settings")).json() == {"default_persona_id": None, "default_chat_model": None}
    persona = (await client.post("/api/personas", json={"name": "Vị khách chiều thu", "gender": "female"})).json()

    resp = await client.put("/api/settings", json={"default_persona_id": persona["id"], "default_chat_model": " qwen2.5:7b "})
    assert resp.status_code == 200, resp.text
    # FakeLLM không liệt kê được model -> chấp nhận tên bất kỳ (đã bỏ khoảng trắng).
    assert resp.json() == {"default_persona_id": persona["id"], "default_chat_model": "qwen2.5:7b"}
    assert (await client.get("/api/settings")).json() == resp.json()

    # Gửi một phần: phần còn lại giữ nguyên; chuỗi rỗng = bỏ model.
    resp = await client.put("/api/settings", json={"default_chat_model": ""})
    assert resp.json() == {"default_persona_id": persona["id"], "default_chat_model": None}

    resp = await client.put("/api/settings", json={"default_persona_id": 9999})
    assert resp.status_code == 422 and "persona" in resp.json()["detail"]
    resp = await client.put("/api/settings", json={"default_persona_id": None, "x": 1})
    assert resp.status_code == 422
    resp = await client.put("/api/settings", json={"default_persona_id": None})
    assert resp.json()["default_persona_id"] is None


@pytest.mark.parametrize("llm", [ListingLLM()], ids=["listing"])
async def test_settings_model_checked_against_ollama(client: httpx.AsyncClient) -> None:
    resp = await client.put("/api/settings", json={"default_chat_model": "khong-co:1b"})
    assert resp.status_code == 422
    assert "ollama pull khong-co:1b" in resp.json()["detail"] and "gemma4:12b" in resp.json()["detail"]
    resp = await client.put("/api/settings", json={"default_chat_model": "mistral-nemo"})
    assert resp.status_code == 200 and resp.json()["default_chat_model"] == "mistral-nemo"


@pytest.mark.parametrize("llm", [ListingLLM(down=True)], ids=["down"])
async def test_settings_model_accepted_when_ollama_down(client: httpx.AsyncClient) -> None:
    resp = await client.put("/api/settings", json={"default_chat_model": "bat-ky:1b"})
    assert resp.status_code == 200 and resp.json()["default_chat_model"] == "bat-ky:1b"


async def test_default_persona_and_model_for_new_story(client: httpx.AsyncClient) -> None:
    card_id = (await client.get("/api/cards")).json()[0]["id"]
    other = (await client.post("/api/personas", json={"name": "Tô Hiểu", "gender": "male"})).json()
    await client.put("/api/settings", json={"default_persona_id": other["id"], "default_chat_model": "qwen2.5:7b"})

    defaults = (await client.get(f"/api/stories/defaults?card_id={card_id}")).json()
    assert defaults["title"].endswith("& Tô Hiểu")
    out = (await client.post("/api/stories", json={"card_id": card_id, "greeting_index": -1})).json()
    assert out["persona_id"] == other["id"] and out["persona_name"] == "Tô Hiểu"
    assert out["model_name"] == "qwen2.5:7b"
    # Story seed kiểu Phase 1 cũng theo model mặc định.
    seed = (await client.post("/api/stories", json={})).json()
    assert seed["model_name"] == "qwen2.5:7b"


async def test_story_defaults_without_any_persona(client: httpx.AsyncClient, app: FastAPI) -> None:
    repo = _repo(app)
    card_id = repo.list_cards(account_id=ANY_ACCOUNT)[0].id
    for p in repo.list_personas(account_id=ANY_ACCOUNT):
        assert p.id is not None
        repo.delete_persona(p.id, with_stories=True, account_id=ANY_ACCOUNT)
    resp = await client.get(f"/api/stories/defaults?card_id={card_id}")
    assert resp.status_code == 422 and "persona" in resp.json()["detail"]
    resp = await client.post("/api/stories", json={"card_id": card_id})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------- API: story


async def test_story_list_fields(client: httpx.AsyncClient) -> None:
    stories = (await client.get("/api/stories")).json()
    assert len(stories) == 1
    seed = stories[0]
    # Card seed tạo mới có vai trò lấy từ template Lạc Dương.
    assert seed["card_role"] == "Thanh mai trúc mã"
    assert seed["last_role"] == "assistant" and seed["last_mode"] == "story"
    preview = seed["last_preview"]
    assert preview and len(preview) <= 140 and "Thought" not in preview and "\n" not in preview
    assert preview.startswith("Nắng chiều cuối thu")

    resp = await client.patch(f"/api/stories/{seed['id']}", json={"mode": "dm"})
    async with client.stream(
        "POST", f"/api/stories/{seed['id']}/messages", json={"content": "Tớ dậy rồi ((dụi mắt))"}
    ) as r:
        async for _ in r.aiter_lines():
            pass
    top = (await client.get("/api/stories")).json()[0]
    assert top["last_role"] == "assistant" and top["last_mode"] == "dm"
    assert top["last_preview"].startswith("Lạc Dương khẽ liếc")  # câu trả lời của FakeLLM, không có Thought

    created = (await client.post("/api/stories", json={"card_id": seed["card_id"], "greeting_index": -1})).json()
    assert created["last_preview"] is None and created["last_role"] is None and created["card_role"]


async def test_patch_story_model_name_without_listing(client: httpx.AsyncClient) -> None:
    sid = (await client.get("/api/stories")).json()[0]["id"]
    resp = await client.patch(f"/api/stories/{sid}", json={"model_name": " qwen2.5:7b "})
    assert resp.status_code == 200 and resp.json()["model_name"] == "qwen2.5:7b"
    resp = await client.patch(f"/api/stories/{sid}", json={"model_name": "  "})
    assert resp.status_code == 422
    resp = await client.patch("/api/stories/9999", json={"model_name": "qwen2.5:7b"})
    assert resp.status_code == 404


@pytest.mark.parametrize("llm", [ListingLLM()], ids=["listing"])
async def test_patch_story_model_name_checked(client: httpx.AsyncClient) -> None:
    sid = (await client.get("/api/stories")).json()[0]["id"]
    resp = await client.patch(f"/api/stories/{sid}", json={"model_name": "khong-co:1b"})
    assert resp.status_code == 422 and "khong-co:1b" in resp.json()["detail"]
    resp = await client.patch(f"/api/stories/{sid}", json={"model_name": "qwen2.5:7b"})
    assert resp.status_code == 200 and resp.json()["model_name"] == "qwen2.5:7b"


async def test_story_extras(client: httpx.AsyncClient) -> None:
    sid = (await client.get("/api/stories")).json()[0]["id"]
    resp = await client.get(f"/api/stories/{sid}/extras")
    assert resp.status_code == 200
    body = resp.json()
    # Phase 3: quan hệ luôn có (điểm xuất phát khi chưa có event); chưa có lượt nào được trích xuất.
    relationship = body.pop("relationship")
    assert set(relationship) == {"affection", "trust", "attraction", "obsession", "fear", "aversion", "directive"}
    assert all(0 <= relationship[k] <= 100 for k in relationship if k != "directive")
    assert body == {
        "suggestions": [],
        "moment": None,
        "lore_tags": [],
        "lore_available": False,  # Phase 4: card seed chưa có mục thế giới nào
        "lore_count": 0,
        "location": None,
        "in_world_time": None,
        "memories": [],
        "pending": False,
        "unprocessed_turns": 1,  # Phase 3b: lời mở đầu chưa được trích xuất (LLM giả: không tự xếp job)
        "memory_search": "keyword",
        "summary": None,
    }
    assert (await client.get("/api/stories/9999/extras")).status_code == 404


# ---------------------------------------------------------------------------- API: /api/system, lore


async def test_system_endpoint(client: httpx.AsyncClient, app: FastAPI) -> None:
    app.state.system = SystemMonitor(
        base_url="http://ollama.test", transport=httpx.MockTransport(ollama_handler), runner=fake_runner
    )
    body = (await client.get("/api/system")).json()
    assert body["ollama_reachable"] is True and body["ollama_version"] == "0.12.3" and body["ollama_error"] is None
    assert body["memory_total_gb"] == 24.0 and body["memory_used_gb"] > 0
    assert body["on_battery"] is True and body["low_power_mode"] is True
    assert body["kv_cache_type"] == "q8_0" and body["flash_attention"] is True
    assert body["num_parallel"] == 1 and body["max_loaded_models"] is None
    assert body["models"][0] == {"name": "gemma4:12b", "size_gb": 8.1, "parameter_size": "12B", "quantization": "Q4_K_M"}
    assert body["loaded"][0]["name"] == "gemma4:12b"
    assert body["chat_model_default"] == "gemma4:12b"

    # Đổi model mặc định: cache bị bỏ, chat_model_default cập nhật ngay.
    await client.put("/api/settings", json={"default_chat_model": "qwen2.5:7b"})
    assert (await client.get("/api/system")).json()["chat_model_default"] == "qwen2.5:7b"


async def test_system_endpoint_never_500(client: httpx.AsyncClient, app: FastAPI) -> None:
    def broken(args: list[str]) -> str | None:
        raise OSError("không chạy được")

    app.state.system = SystemMonitor(
        base_url="http://ollama.test", transport=httpx.MockTransport(down_handler), runner=broken
    )
    resp = await client.get("/api/system")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ollama_reachable"] is False and body["ollama_error"]
    assert body["memory_total_gb"] is None and body["models"] == [] and body["on_battery"] is None


async def test_system_endpoint_with_fake_llm_does_not_call_ollama(client: httpx.AsyncClient, app: FastAPI) -> None:
    monitor: SystemMonitor = app.state.system
    assert monitor.base_url is None  # FakeLLM: không có Ollama để gọi
    monitor.runner = fake_runner
    body = (await client.get("/api/system")).json()
    assert body["ollama_reachable"] is False and "thử nghiệm" in body["ollama_error"]
    assert body["memory_total_gb"] == 24.0


async def test_lore_status(client: httpx.AsyncClient, app: FastAPI, tmp_path: Path) -> None:
    # Phase 4: sổ thế giới nằm trong DB theo card; thư mục world_wiki không còn được đọc hay tạo.
    wiki: Path = app.state.lore_dir
    body = (await client.get("/api/lore/status")).json()
    assert body == {"enabled": True, "dir": "", "files": 0, "entries": 0, "last_sync": None}
    assert not wiki.exists()  # không tạo thư mục
    card_id = (await client.get("/api/cards")).json()[0]["id"]
    resp = await client.post(f"/api/cards/{card_id}/lore", json={"title": "Tiệm sách", "keys": ["tiệm sách"]})
    assert resp.status_code == 200, resp.text
    assert (await client.get("/api/lore/status")).json()["entries"] == 1
    assert lore_status(-1).entries == 0


# ---------------------------------------------------------------------------- API: nhân vật mẫu


async def test_templates_list(client: httpx.AsyncClient, app: FastAPI) -> None:
    rows = (await client.get("/api/templates")).json()
    slugs = [r["slug"] for r in rows]
    assert slugs[0] == "ha-vy" and rows[0]["featured"] is True
    assert set(slugs) == {"ha-vy", "tran-minh-khang", "ta-van-lan", "lac-duong", "morwenna-penrose"}
    assert sum(r["featured"] for r in rows) == 1
    by_slug = {r["slug"]: r for r in rows}
    # Card seed Lạc Dương được nhận là đã cài; các template khác chưa.
    seed_id = next(c.id for c in _repo(app).list_cards(account_id=ANY_ACCOUNT) if c.name == "Lạc Dương")
    assert by_slug["lac-duong"]["installed_card_id"] == seed_id
    assert all(by_slug[s]["installed_card_id"] is None for s in slugs if s != "lac-duong")
    ha_vy = by_slug["ha-vy"]
    assert ha_vy["vibes"] == ["Chữa lành", "Dịu dàng", "Tình đầu"]
    assert ha_vy["card"]["id"] is None and ha_vy["card"]["avatar"] is None
    assert ha_vy["card"]["role"] == "Chủ tiệm sách mùa thu"
    assert ha_vy["card"]["extensions"]["lyris"]["template"] == "ha-vy"
    assert ha_vy["image_url"] == "/api/templates/ha-vy/image"
    assert set(ha_vy["image_credit"]) == {"title", "creator", "licence", "licence_url", "source_url", "changes"}
    assert by_slug["lac-duong"]["image_url"] is None and by_slug["lac-duong"]["image_credit"] is None


async def test_template_image(client: httpx.AsyncClient) -> None:
    resp = await client.get("/api/templates/ha-vy/image")
    assert resp.status_code == 200 and resp.headers["content-type"] == "image/jpeg"
    assert resp.content[:3] == b"\xff\xd8\xff"
    assert (await client.get("/api/templates/lac-duong/image")).status_code == 404
    assert (await client.get("/api/templates/khong-co/image")).status_code == 404


async def test_template_install_idempotent(client: httpx.AsyncClient, settings: Settings) -> None:
    resp = await client.post("/api/templates/ha-vy/install")
    assert resp.status_code == 200, resp.text
    card = resp.json()
    assert card["name"] == "Hạ Vy" and card["role"] == "Chủ tiệm sách mùa thu" and card["story_count"] == 0
    assert card["extensions"]["lyris"]["template"] == "ha-vy"
    assert card["avatar"] and card["avatar_url"].startswith(f"/api/cards/{card['id']}/avatar?v=")
    assert (settings.avatars_dir / card["avatar"]).is_file()
    avatar = await client.get(card["avatar_url"])
    assert avatar.status_code == 200 and avatar.content[:8] == b"\x89PNG\r\n\x1a\n"

    again = (await client.post("/api/templates/ha-vy/install")).json()
    assert again["id"] == card["id"]
    names = [c["name"] for c in (await client.get("/api/cards")).json()]
    assert names.count("Hạ Vy") == 1
    rows = {r["slug"]: r for r in (await client.get("/api/templates")).json()}
    assert rows["ha-vy"]["installed_card_id"] == card["id"]

    # Cài xong thì tạo story ngay được (persona mặc định).
    story = (await client.post("/api/stories", json={"card_id": card["id"]})).json()
    assert story["card_role"] == "Chủ tiệm sách mùa thu"
    first = (await client.get(f"/api/stories/{story['id']}/messages")).json()[0]
    assert "{{user}}" not in first["raw_content"] and "Lâm Vãn" in first["raw_content"]


async def test_template_install_seed_returns_existing(client: httpx.AsyncClient, app: FastAPI) -> None:
    seed_id = next(c.id for c in _repo(app).list_cards(account_id=ANY_ACCOUNT) if c.name == "Lạc Dương")
    card = (await client.post("/api/templates/lac-duong/install")).json()
    assert card["id"] == seed_id
    assert (await client.post("/api/templates/khong-co/install")).status_code == 404


async def test_template_install_after_seed_deleted(client: httpx.AsyncClient, app: FastAPI) -> None:
    repo = _repo(app)
    seed = next(c for c in repo.list_cards(account_id=ANY_ACCOUNT) if c.name == "Lạc Dương")
    assert seed.id is not None
    resp = await client.delete(f"/api/cards/{seed.id}?with_stories=true")
    assert resp.status_code == 200
    card = (await client.post("/api/templates/lac-duong/install")).json()
    # Card mới (SQLite có thể dùng lại id đã xoá): nội dung là bản phổ quát của template.
    assert card["role"] == "Thanh mai trúc mã" and card["avatar"] is None
    assert "{{user}}" in card["description"] and card["extensions"]["lyris"]["template"] == "lac-duong"
    assert len([c for c in (await client.get("/api/cards")).json() if c["name"] == "Lạc Dương"]) == 1


async def test_old_seed_card_without_tag_still_counts_as_installed(client: httpx.AsyncClient, app: FastAPI) -> None:
    """DB cũ: card seed tạo trước Lyris không có extensions.lyris.template -> nhận qua tên + style."""
    repo = _repo(app)
    seed = next(c for c in repo.list_cards(account_id=ANY_ACCOUNT) if c.name == "Lạc Dương")
    assert seed.id is not None
    repo.update_card(seed.id, seed.model_copy(update={"extensions": {}, "role": ""}), account_id=ANY_ACCOUNT)
    rows = {r["slug"]: r for r in (await client.get("/api/templates")).json()}
    assert rows["lac-duong"]["installed_card_id"] == seed.id


# ---------------------------------------------------------------------------- nội dung template


def _template_rules(card: CharacterCard) -> dict[str, Any]:
    profile = get_style_profile(card.style_profile)
    allowed = {v.casefold() for v in profile.narration.get(card.language, {}).values() if v}
    terms = [card.address_terms.self_term, card.address_terms.player_term, *card.address_terms.nicknames]
    return {
        "thought_count": 2,
        "min_thoughts": 2,
        "max_thoughts": 2,
        "no_adjacent_thoughts": True,
        "narration_forbidden": [t for t in terms if t.casefold() not in allowed],
        "forbidden_phrases": ["bầu không khí", "the atmosphere", "{{char}}", "Lâm Vãn"],
        "language": card.language,
        "dialogue_required_any": [card.address_terms.self_term, card.address_terms.player_term],
        "min_words": 100,
        "max_words": 260,
    }


@pytest.mark.parametrize("template", load_templates(), ids=lambda t: t.slug)
def test_template_content(template: Any) -> None:
    card: CharacterCard = template.card
    # Nạp lại qua CharacterCard từ JSON thô và qua kiểm tra của API.
    raw = json.loads((TEMPLATES_DIR / f"{template.slug}.json").read_text(encoding="utf-8"))
    CharacterCard.model_validate(raw["card"])
    validated = validate_card(card)
    assert validated.name == card.name and validated.role == card.role
    assert card.style_profile in {s.name for s in list_style_profiles()}
    assert card.extensions["lyris"]["template"] == template.slug
    assert 0 < len(card.role) <= MAX_ROLE_CHARS and "{{" not in card.role
    assert template.vibes and all(v == v.strip() for v in template.vibes)

    g = card.greeting
    names = [card.name, "{{user}}", "WeChat", "Penmorrow", "Atlantic", "Morwenna"]
    assert checks.run_checks(g, _template_rules(card), names=names) == []
    assert "{{user}}" in g
    paragraphs = [p.strip() for p in g.split("\n\n") if p.strip()]
    thought_idx = [i for i, p in enumerate(paragraphs) if p.startswith("[Thought:")]
    # Thought đứng riêng thành đoạn, rải ra: không mở đầu, không kết thúc, cách nhau ít nhất một đoạn.
    assert len(thought_idx) == 2 and all(paragraphs[i].endswith("]") for i in thought_idx)
    assert thought_idx[0] > 0 and thought_idx[1] < len(paragraphs) - 1
    assert thought_idx[1] - thought_idx[0] >= 2
    for body in checks.thought_bodies(g):
        sentences = len(re.findall(r"[.!?…]+(?=\s|$)", body))
        assert 2 <= sentences <= 3, body
    # Kết bằng lời thoại hướng về người chơi (câu hỏi hoặc lời mời), không phải Thought.
    assert paragraphs[-1].rstrip().endswith(('?"', '."', '?”', '.”'))
    examples = [line for line in card.example_dialogues.split("\n") if line.strip()]
    assert len(examples) == 3 and all(line.startswith("{{char}}: ") for line in examples)
    if card.language == "vi":
        assert not re.search(r"\b(the|and|you)\b", g)


@pytest.mark.parametrize("template", [t for t in load_templates() if t.image is not None], ids=lambda t: t.slug)
def test_template_image_file(template: Any) -> None:
    path = template.image_path
    assert path is not None and path.stat().st_size < MAX_IMAGE_BYTES
    assert template.image.source_url.startswith("https://")
    assert template.image.licence in {"CC0", "CC BY 4.0", "CC BY-SA 3.0", "CC BY-SA 4.0", "Public domain"}


def test_featured_template_is_ha_vy() -> None:
    featured = [t for t in load_templates() if t.featured]
    assert [t.slug for t in featured] == ["ha-vy"]
    card = featured[0].card
    assert card.style_profile == "viet_hien_dai" and card.gender == "female"
    assert "gác xép mùi gỗ thông" in card.greeting + card.scenario + card.background
    assert "thư" in card.greeting and "Đà Lạt" in card.description


def test_lac_duong_template_matches_seed() -> None:
    seed = load_seed_card()
    template = next(t for t in load_templates() if t.slug == "lac-duong")
    assert template.adopt_existing
    for field in ("name", "gender", "language", "style_profile", "appearance"):
        assert getattr(template.card, field) == getattr(seed, field)
    assert template.card.address_terms.self_term == seed.address_terms.self_term
    created = seed_card_for_create()
    assert created.role == template.card.role and created.extensions["lyris"]["template"] == "lac-duong"
    assert created.greeting == seed.greeting  # card seed giữ nguyên văn


# ---------------------------------------------------------------------------- draft + card_v2


def test_draft_schema_and_prompt_have_role() -> None:
    props = list(DRAFT_SCHEMA["properties"])
    assert props.index("role") == props.index("style_profile") + 1 and "role" in DRAFT_SCHEMA["required"]
    styles = list_style_profiles()
    vi = build_draft_messages(idea="chủ tiệm sách", language="vi", gender=None, style_profile=None, styles=styles)
    en = build_draft_messages(idea="lighthouse keeper", language="en", gender=None, style_profile=None, styles=styles)
    assert "- role:" in vi[0].content and "- role:" in en[0].content


def test_normalize_role() -> None:
    assert normalize_role('  "chủ tiệm sách mùa thu."  ') == ("Chủ tiệm sách mùa thu", False)
    assert normalize_role("Sư tỷ của {{user}}") == ("Sư tỷ", False)
    assert normalize_role("Childhood friend of {user}") == ("Childhood friend", False)
    assert normalize_role("Kiến trúc sư\nở Sài Gòn") == ("Kiến trúc sư", False)
    assert normalize_role("") == ("", False)
    long_role, cut = normalize_role("Người giữ hải đăng " * 10)
    assert cut and len(long_role) <= MAX_ROLE_CHARS and not long_role.endswith(" ")


def test_postprocess_draft_role() -> None:
    styles = list_style_profiles()
    data = {"name": "Hạ Vy", "gender": "female", "style_profile": "viet_hien_dai", "role": "chủ tiệm sách."}
    card, _ = postprocess_draft(data, language="vi", gender=None, style_profile=None, styles=styles)
    assert card.role == "Chủ tiệm sách"
    card, warnings = postprocess_draft(
        {**data, "role": "Một người " * 20}, language="vi", gender=None, style_profile=None, styles=styles
    )
    assert len(card.role) <= MAX_ROLE_CHARS and any("Vai trò" in w for w in warnings)
    card, warnings = postprocess_draft(
        {k: v for k, v in data.items() if k != "role"}, language="vi", gender=None, style_profile=None, styles=styles
    )
    assert card.role == "" and not any("Vai trò" in w for w in warnings)


def test_card_v2_role_roundtrip() -> None:
    card = _card(extensions={"lyris": {"template": "ha-vy"}})
    exported = export_card_json(card)
    assert exported["data"]["extensions"]["lyris"]["role"] == "Chủ tiệm sách mùa thu"
    styles = [s.name for s in list_style_profiles()]
    back = import_card(json.dumps(exported).encode(), "application/json", styles=styles)
    assert back.card.role == "Chủ tiệm sách mùa thu"
    # Card nhập lại là card của người dùng: dấu "đã cài từ Khám Phá" không đi theo.
    assert "template" not in back.card.extensions.get("lyris", {})
    exported["data"]["extensions"]["lyris"]["role"] = 5
    bad = import_card(json.dumps(exported).encode(), "application/json", styles=styles)
    assert bad.card.role == "" and any("vai trò" in w for w in bad.warnings)


def test_validate_card_role() -> None:
    assert validate_card(_card(role="  Chủ   tiệm\nsách ")).role == "Chủ tiệm sách"
    with pytest.raises(Exception) as exc:
        validate_card(_card(role="x" * 81))
    assert "Vai trò" in str(getattr(exc.value, "detail", exc.value))


@pytest.mark.parametrize("llm", [ListingLLM(["qwen2.5:7b"])], ids=["listing"])
async def test_health_uses_default_chat_model(client: httpx.AsyncClient) -> None:
    body = (await client.get("/api/health")).json()
    assert body["chat_model"] == "gemma4:12b" and "ollama pull gemma4:12b" in body["ollama"]["error"]
    assert (await client.put("/api/settings", json={"default_chat_model": "qwen2.5:7b"})).status_code == 200
    body = (await client.get("/api/health")).json()
    assert body["chat_model"] == "qwen2.5:7b" and body["ollama"]["error"] is None
