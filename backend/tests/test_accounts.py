"""Phase 2c (docs/accounts.md): tài khoản, chủ sở hữu, uid, visibility, avatar/ảnh bìa, tác giả khi export,
profile công khai, migration 0005 trên DB Phase 2b có dữ liệu."""
from __future__ import annotations

import base64
import io
import json
import re
import sqlite3
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from PIL import Image

from lyris.accounts import AccountInputError, validate_account_update, validate_handle
from lyris.api.app import create_app
from lyris.config import Settings
from lyris.db.connection import connect, migrate
from lyris.db.repo import ANY_ACCOUNT, DEFAULT_ACCOUNT_HANDLE, HandleTaken, NotFound, Repo
from lyris.llm.fake import FakeLLM
from lyris.models import AccountUpdate, CharacterCard, Persona
from lyris.seed import load_seed_card, load_seed_persona
from lyris.seed.templates import load_templates
from lyris.studio import avatars
from lyris.studio.card_v2 import CardCreator, export_card_json, export_card_png, import_card
from lyris.studio.stories import create_story_for
from tests.authutil import owner_client

HEX32 = re.compile(r"^[0-9a-f]{32}$")
REPLY = "Anh mỉm cười. [Thought: Ổn rồi.] \"Ừ.\""


def png_bytes(size: tuple[int, int] = (64, 48), color: tuple[int, int, int] = (200, 30, 30)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def jpeg_with_exif(size: tuple[int, int]) -> bytes:
    img = Image.new("RGB", size, (10, 120, 200))
    exif = Image.Exif()
    exif[0x010F] = "MayAnhBiMat"  # Make
    exif[0x0131] = "PhanMemBiMat"  # Software
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif.tobytes())
    return buf.getvalue()


def card_body(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "name": "Trần Minh Khang",
        "gender": "male",
        "language": "vi",
        "description": "Kiến trúc sư 27 tuổi.",
        "style_profile": "trung_hien_dai",
        "address_terms": {"self_term": "anh", "player_term": "em", "nicknames": [], "others": ""},
        "greeting": "{{char}} ngẩng lên. \"{{user}}, em tới rồi à?\"",
        "tags": [],
    }
    body.update(overrides)
    return body


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
async def app(settings: Settings) -> AsyncIterator[FastAPI]:
    application = create_app(settings, FakeLLM(replies=[REPLY]))
    async with application.router.lifespan_context(application):
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


async def create_card(client: httpx.AsyncClient, **overrides: Any) -> dict[str, Any]:
    return dict(await ok(await client.post("/api/cards", json={"card": card_body(**overrides)})))


def files_in(directory: Path) -> list[str]:
    return sorted(p.name for p in directory.glob("*.png")) if directory.is_dir() else []


# ---------------------------------------------------------------------------- luật handle


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("abc", "abc"),
        ("lan_anh.92", "lan_anh.92"),
        ("  @Lan.Anh  ", "lan.anh"),
        ("A_B", "a_b"),
        ("a" * 30, "a" * 30),
        ("x..y", "x..y"),
        ("_ab_", "_ab_"),
        ("123", "123"),
    ],
)
def test_valid_handles(raw: str, expected: str) -> None:
    assert validate_handle(raw) == expected


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        ("", "không được để trống"),
        ("   ", "không được để trống"),
        ("@", "không được để trống"),
        ("ab", "ít nhất 3 ký tự"),
        ("a" * 31, "tối đa 30 ký tự"),
        ("lan anh", "chỉ được dùng"),
        ("lan-anh", "chỉ được dùng"),
        ("lân_anh", "chỉ được dùng"),
        ("đức", "chỉ được dùng"),
        ("a@b", "chỉ được dùng"),
        (".abc", "dấu chấm"),
        ("abc.", "dấu chấm"),
        ("..a", "dấu chấm"),
    ],
)
def test_invalid_handles(raw: str, message: str) -> None:
    with pytest.raises(AccountInputError) as info:
        validate_handle(raw)
    assert message in str(info.value)


def test_validate_account_update_normalizes() -> None:
    update = validate_account_update("  Lan   Anh ", "@Lan_Anh", "  Thích mưa.  ")
    assert update == AccountUpdate(display_name="Lan Anh", handle="lan_anh", bio="Thích mưa.")
    with pytest.raises(AccountInputError, match="Tên hiển thị không được để trống"):
        validate_account_update("   ", "abc", "")
    with pytest.raises(AccountInputError, match="tối đa 60"):
        validate_account_update("x" * 61, "abc", "")
    with pytest.raises(AccountInputError, match="tối đa 500"):
        validate_account_update("Lan", "abc", "x" * 501)


# ---------------------------------------------------------------------------- repo: account


def test_fresh_db_has_owner_account(repo: Repo) -> None:
    owner = repo.owner_account()
    assert owner.handle == DEFAULT_ACCOUNT_HANDLE and owner.display_name == "Bạn"
    assert owner.profile_completed is False and owner.bio == ""
    assert owner.uid is not None and HEX32.fullmatch(owner.uid)


def test_owner_account_recreated_when_missing(repo: Repo) -> None:
    repo.conn.execute("DELETE FROM accounts")
    owner = repo.owner_account()
    assert owner.handle == DEFAULT_ACCOUNT_HANDLE and owner.uid and HEX32.fullmatch(owner.uid)


def test_handle_unique_case_insensitive(repo: Repo) -> None:
    owner = repo.owner_account()
    other = repo.create_account("khac", "Người khác")
    assert repo.find_account_by_handle("KHAC") == other
    assert repo.handle_taken("Khac") and not repo.handle_taken("khac", exclude_account_id=other.id)
    with pytest.raises(HandleTaken):
        repo.create_account("BAN", "Trùng")
    assert owner.id is not None
    with pytest.raises(HandleTaken):
        repo.update_account(owner.id, AccountUpdate(display_name="A", handle="KHAC", bio=""))
    saved = repo.update_account(owner.id, AccountUpdate(display_name="Lan", handle="lan", bio="hi"))
    assert saved.profile_completed is True and saved.uid == owner.uid and saved.handle == "lan"


def test_inserts_get_owner_and_unique_uid(seeded_repo: Repo) -> None:
    repo = seeded_repo
    owner_id = repo.owner_account().id
    for table in ("character_cards", "personas", "stories"):
        rows = repo.conn.execute(f"SELECT account_id, uid FROM {table}").fetchall()
        assert rows, table
        assert all(r["account_id"] == owner_id and HEX32.fullmatch(r["uid"]) for r in rows), table
    a = repo.create_card(load_seed_card(), account_id=repo.owner_id())
    b = repo.create_card(load_seed_card().model_copy(update={"uid": a.uid}), account_id=repo.owner_id())  # uid gửi vào bị bỏ qua
    assert a.uid != b.uid
    assert a.id is not None
    updated = repo.update_card(a.id, a.model_copy(update={"uid": "f" * 32, "visibility": "public"}), account_id=ANY_ACCOUNT)
    assert updated.uid == a.uid and updated.visibility == "public"


# ---------------------------------------------------------------------------- migration 0005


def _build_phase2b_db(path: Path) -> None:
    """DB đúng schema Phase 2b (migration 0001-0004) có dữ liệu, ghi bằng SQL thuần."""
    conn = connect(path)
    try:
        assert migrate(conn, target=4) == 4
        assert conn.execute("SELECT name FROM sqlite_master WHERE name = 'accounts'").fetchone() is None
        card = load_seed_card()
        for name in ("Lạc Dương", "Hạ Vy", "Morwenna"):
            conn.execute(
                "INSERT INTO character_cards (name, gender, language, style_profile, address_terms_json, greeting)"
                " VALUES (?, 'male', 'vi', ?, ?, 'Chào.')",
                (name, card.style_profile, json.dumps(card.address_terms.model_dump(), ensure_ascii=False)),
            )
        for name in ("Lâm Vãn", "Gia Huy"):
            conn.execute("INSERT INTO personas (name, gender, description) VALUES (?, 'female', '')", (name,))
        for i, (card_id, persona_id) in enumerate(((1, 1), (2, 1), (3, 2), (1, 2))):
            conn.execute(
                "INSERT INTO stories (card_id, persona_id, title, narration_pronouns_json)"
                " VALUES (?, ?, ?, '{\"character\": \"anh\", \"player\": \"cô\"}')",
                (card_id, persona_id, f"Story {i}"),
            )
        conn.execute(
            "INSERT INTO messages (story_id, turn_index, role, mode, raw_content, visible_content)"
            " VALUES (1, 0, 'assistant', 'story', 'Chào.', 'Chào.')"
        )
        conn.execute("INSERT INTO app_settings (key, value_json) VALUES ('seeded', 'true')")
    finally:
        conn.close()


async def test_phase2b_database_migrates_to_owner(tmp_path: Path, avatars_dir: Path) -> None:
    db = tmp_path / "phase2b.db"
    _build_phase2b_db(db)

    conn = connect(db)
    try:
        assert migrate(conn) == 8
        accounts = conn.execute("SELECT * FROM accounts").fetchall()
        assert len(accounts) == 1
        owner = accounts[0]
        assert owner["handle"] == "ban" and owner["display_name"] == "Bạn" and owner["profile_completed"] == 0
        assert HEX32.fullmatch(owner["uid"])
        uids: list[str] = [owner["uid"]]
        for table, count in (("character_cards", 3), ("personas", 2), ("stories", 4)):
            rows = conn.execute(f"SELECT account_id, uid FROM {table}").fetchall()
            assert len(rows) == count
            assert all(r["account_id"] == owner["id"] for r in rows), table
            assert all(HEX32.fullmatch(r["uid"]) for r in rows), table
            uids += [r["uid"] for r in rows]
        assert len(set(uids)) == len(uids)
        visibilities = {r[0] for r in conn.execute("SELECT visibility FROM character_cards")}
        assert visibilities == {"private"}
        with pytest.raises(sqlite3.IntegrityError):  # index unique trên uid
            conn.execute("UPDATE personas SET uid = (SELECT uid FROM personas WHERE id = 2) WHERE id = 1")
    finally:
        conn.close()

    settings = Settings(
        db_path=db, ollama_url="http://127.0.0.1:9", chat_model="chat-model:test", num_ctx=8192,
        avatars_dir=avatars_dir,
    )
    app = create_app(settings, FakeLLM(replies=[REPLY]))
    async with app.router.lifespan_context(app):
        async with owner_client(app, base_url="http://test") as client:
            account = await ok(await client.get("/api/account"))
            assert account["handle"] == "ban" and account["profile_completed"] is False
            # card_count không tính nhân vật mẫu: card seed "Lạc Dương" được template lac-duong nhận (adopt_existing).
            assert (account["card_count"], account["story_count"], account["persona_count"]) == (2, 4, 2)
            stories = await ok(await client.get("/api/stories"))
            assert len(stories) == 4 and all(HEX32.fullmatch(s["uid"]) for s in stories)
            cards = await ok(await client.get("/api/cards"))
            assert {c["creator_handle"] for c in cards} == {"ban"}


# ---------------------------------------------------------------------------- GET/PUT /api/account


async def test_get_and_update_account(client: httpx.AsyncClient) -> None:
    account = await ok(await client.get("/api/account"))
    assert set(account) >= {
        "id", "uid", "handle", "display_name", "bio", "profile_completed", "created_at",
        "avatar_url", "banner_url", "card_count", "story_count", "persona_count",
    }
    assert account["handle"] == "ban" and account["display_name"] == "Bạn"
    assert account["profile_completed"] is False
    assert account["avatar_url"] is None and account["banner_url"] is None
    # DB mới được seed: một nhân vật (là nhân vật mẫu Lạc Dương nên card_count không tính), một persona, một story.
    assert (account["card_count"], account["story_count"], account["persona_count"]) == (0, 1, 1)

    saved = await ok(
        await client.put("/api/account", json={"display_name": " Lan  Anh ", "handle": "@Lan.Anh", "bio": " Hi "})
    )
    assert saved["display_name"] == "Lan Anh" and saved["handle"] == "lan.anh" and saved["bio"] == "Hi"
    assert saved["profile_completed"] is True and saved["uid"] == account["uid"] and saved["id"] == account["id"]
    assert (await ok(await client.get("/api/account")))["handle"] == "lan.anh"

    # Gửi lại cả AccountOut (trường thừa bị bỏ qua), uid không đổi được.
    again = await ok(await client.put("/api/account", json={**saved, "uid": "0" * 32, "bio": "Mới"}))
    assert again["uid"] == account["uid"] and again["bio"] == "Mới"


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ({"display_name": "Lan", "handle": "ab"}, "Handle phải có ít nhất 3 ký tự."),
        ({"display_name": "Lan", "handle": "lan anh"}, "Handle chỉ được dùng"),
        ({"display_name": "Lan", "handle": ".lan"}, "không được bắt đầu hay kết thúc bằng dấu chấm"),
        ({"display_name": "Lan", "handle": "a" * 31}, "Handle dài tối đa 30 ký tự."),
        ({"display_name": "   ", "handle": "lan"}, "Tên hiển thị không được để trống."),
        ({"display_name": "Lan", "handle": "lan", "bio": "x" * 501}, "tối đa 500 ký tự"),
        ({"display_name": "Lan"}, "handle: thiếu trường bắt buộc"),
    ],
)
async def test_update_account_rejects_bad_input(
    client: httpx.AsyncClient, body: dict[str, Any], message: str
) -> None:
    resp = await client.put("/api/account", json=body)
    assert resp.status_code == 422
    assert message in resp.json()["detail"]
    assert (await ok(await client.get("/api/account")))["profile_completed"] is False


async def test_update_account_handle_taken(app: FastAPI, client: httpx.AsyncClient) -> None:
    repo_of(app).create_account("khac.nguoi", "Người khác")
    resp = await client.put("/api/account", json={"display_name": "Lan", "handle": "Khac.Nguoi", "bio": ""})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "@khac.nguoi đã có người dùng. Hãy chọn handle khác."
    # Đổi hoa thường handle của chính mình thì được.
    assert (await ok(await client.put("/api/account", json={"display_name": "Lan", "handle": "BAN"})))["handle"] == "ban"


# ---------------------------------------------------------------------------- avatar + ảnh bìa tài khoản


async def test_account_avatar_and_banner(client: httpx.AsyncClient, avatars_dir: Path) -> None:
    acc = await ok(await client.put("/api/account/avatar", content=png_bytes((2000, 1000)),
                                    headers={"Content-Type": "image/png"}))
    assert re.fullmatch(rf"account-{acc['id']}-[0-9a-f]{{8}}\.png", acc["avatar"])
    assert acc["avatar_url"] == f"/api/account/avatar?v={acc['avatar']}"
    got = await client.get(acc["avatar_url"])
    assert got.status_code == 200 and got.headers["content-type"] == "image/png"
    assert got.headers["cache-control"].endswith("immutable")
    assert Image.open(io.BytesIO(got.content)).size == (768, 384)

    # Ảnh bìa: vừa khung 1500x500, giữ tỉ lệ, PNG, không metadata.
    for size, expected in (((3000, 600), (1500, 300)), ((400, 1000), (200, 500)), ((300, 100), (300, 100))):
        acc = await ok(await client.put("/api/account/banner", content=jpeg_with_exif(size),
                                        headers={"Content-Type": "image/jpeg"}))
        assert re.fullmatch(rf"banner-{acc['id']}-[0-9a-f]{{8}}\.png", acc["banner"])
        data = (await client.get(acc["banner_url"])).content
        with Image.open(io.BytesIO(data)) as img:
            assert img.format == "PNG" and img.size == expected
            assert not img.getexif() and "exif" not in img.info
        assert b"MayAnhBiMat" not in data and b"PhanMemBiMat" not in data
    # Mỗi lần thay ảnh, file cũ bị xoá: chỉ còn một avatar và một ảnh bìa.
    assert files_in(avatars_dir) == sorted([acc["avatar"], acc["banner"]])

    bad = await client.put("/api/account/banner", content=b"khong phai anh", headers={"Content-Type": "image/png"})
    assert bad.status_code == 422 and "Định dạng ảnh không hỗ trợ" in bad.json()["detail"]

    cleared = await ok(await client.delete("/api/account/banner"))
    assert cleared["banner"] is None and cleared["banner_url"] is None and cleared["avatar"] == acc["avatar"]
    assert files_in(avatars_dir) == [acc["avatar"]]
    missing = await client.get("/api/account/banner")
    assert missing.status_code == 404 and missing.json()["detail"] == "Tài khoản này chưa có ảnh bìa."
    cleared = await ok(await client.delete("/api/account/avatar"))
    assert cleared["avatar_url"] is None and files_in(avatars_dir) == []


def test_normalize_image_size_parameter() -> None:
    out = avatars.normalize_image(png_bytes((3000, 1500)), avatars.BANNER_SIZE)
    assert Image.open(io.BytesIO(out)).size == (1000, 500)
    assert Image.open(io.BytesIO(avatars.normalize_image(png_bytes((3000, 1500))))).size == (768, 384)
    with pytest.raises(ValueError):
        avatars.normalize_image(png_bytes(), (0, 10))


# ---------------------------------------------------------------------------- avatar persona


async def test_persona_avatar(client: httpx.AsyncClient, avatars_dir: Path) -> None:
    persona = await ok(await client.post("/api/personas", json={"name": "Gia Huy", "gender": "male"}))
    assert persona["avatar"] is None and persona["avatar_url"] is None and HEX32.fullmatch(persona["uid"])
    pid = persona["id"]
    up = await ok(await client.put(f"/api/personas/{pid}/avatar", content=png_bytes((900, 900)),
                                   headers={"Content-Type": "image/png"}))
    assert re.fullmatch(rf"persona-{pid}-[0-9a-f]{{8}}\.png", up["avatar"])
    assert up["avatar_url"] == f"/api/personas/{pid}/avatar?v={up['avatar']}"
    got = await client.get(up["avatar_url"])
    assert got.status_code == 200 and Image.open(io.BytesIO(got.content)).size == (768, 768)

    # Sửa persona (gửi lại cả PersonaOut) không đổi avatar hay uid.
    edited = await ok(await client.put(f"/api/personas/{pid}", json={**up, "name": "Huy", "avatar": None,
                                                                     "uid": "0" * 32}))
    assert edited["avatar"] == up["avatar"] and edited["uid"] == persona["uid"] and edited["name"] == "Huy"
    listed = next(p for p in await ok(await client.get("/api/personas")) if p["id"] == pid)
    assert listed["avatar_url"] == up["avatar_url"]

    card = await create_card(client)
    story = await ok(await client.post("/api/stories", json={"card_id": card["id"], "persona_id": pid}))
    detail = await ok(await client.get(f"/api/stories/{story['id']}"))
    assert detail["persona"]["avatar_url"] == up["avatar_url"]
    await ok(await client.delete(f"/api/stories/{story['id']}"))

    second = await ok(await client.put(f"/api/personas/{pid}/avatar", content=png_bytes(color=(0, 0, 0)),
                                       headers={"Content-Type": "image/png"}))
    assert files_in(avatars_dir) == [second["avatar"]]
    cleared = await ok(await client.delete(f"/api/personas/{pid}/avatar"))
    assert cleared["avatar_url"] is None and files_in(avatars_dir) == []
    assert (await client.get(f"/api/personas/{pid}/avatar")).status_code == 404

    # Xoá persona thì xoá luôn file avatar.
    await ok(await client.put(f"/api/personas/{pid}/avatar", content=png_bytes(), headers={"Content-Type": "image/png"}))
    assert len(files_in(avatars_dir)) == 1
    await ok(await client.delete(f"/api/personas/{pid}"))
    assert files_in(avatars_dir) == []
    assert (await client.put("/api/personas/9999/avatar", content=png_bytes(),
                             headers={"Content-Type": "image/png"})).status_code == 404


# ---------------------------------------------------------------------------- uid, visibility, tác giả


async def test_card_uid_visibility_and_creator(client: httpx.AsyncClient) -> None:
    account = await ok(await client.get("/api/account"))
    card = await create_card(client, uid="a" * 32)
    assert HEX32.fullmatch(card["uid"]) and card["uid"] != "a" * 32
    assert card["visibility"] == "private"
    assert card["creator_handle"] == "ban" and card["creator_name"] == "Bạn"

    put = await ok(await client.put(f"/api/cards/{card['id']}", json={**card, "uid": "b" * 32, "visibility": "public"}))
    assert put["uid"] == card["uid"] and put["visibility"] == "public"
    got = await ok(await client.get(f"/api/cards/{card['id']}"))
    assert got["visibility"] == "public" and got["uid"] == card["uid"]
    summary = next(c for c in await ok(await client.get("/api/cards")) if c["id"] == card["id"])
    assert summary["uid"] == card["uid"] and summary["visibility"] == "public"
    assert summary["creator_handle"] == "ban" and summary["creator_name"] == "Bạn"

    bad = await client.put(f"/api/cards/{card['id']}", json={**card, "visibility": "friends"})
    assert bad.status_code == 422 and "visibility" in bad.json()["detail"]

    # A body without the field (older editor, script) keeps the stored visibility instead of resetting it.
    without = {k: v for k, v in card.items() if k not in ("visibility", "uid")}
    kept = await ok(await client.put(f"/api/cards/{card['id']}", json={**without, "role": "Đổi vai"}))
    assert kept["visibility"] == "public" and kept["role"] == "Đổi vai" and kept["uid"] == card["uid"]
    await ok(await client.put(f"/api/cards/{card['id']}", json={**card, "visibility": "public"}))

    dup = await ok(await client.post(f"/api/cards/{card['id']}/duplicate"))
    assert dup["uid"] != card["uid"] and dup["visibility"] == "private"

    # Đổi handle: tác giả hiện theo handle mới.
    await ok(await client.put("/api/account", json={"display_name": "Lan Anh", "handle": "lan_anh"}))
    got = await ok(await client.get(f"/api/cards/{card['id']}"))
    assert got["creator_handle"] == "lan_anh" and got["creator_name"] == "Lan Anh"
    assert account["uid"]


async def test_story_and_persona_uid(client: httpx.AsyncClient) -> None:
    card = await create_card(client)
    persona = await ok(await client.post("/api/personas", json={"name": "Ngọc Anh", "gender": "female"}))
    story = await ok(await client.post("/api/stories", json={"card_id": card["id"], "persona_id": persona["id"]}))
    assert HEX32.fullmatch(story["uid"])
    detail = await ok(await client.get(f"/api/stories/{story['id']}"))
    assert detail["story"]["uid"] == story["uid"] and detail["persona"]["uid"] == persona["uid"]
    assert detail["card"]["uid"] == card["uid"]
    patched = await ok(await client.patch(f"/api/stories/{story['id']}", json={"title": "Mưa"}))
    assert patched["uid"] == story["uid"]
    seed = await ok(await client.post("/api/stories", json={}))
    assert HEX32.fullmatch(seed["uid"]) and seed["uid"] != story["uid"]
    assert len({s["uid"] for s in await ok(await client.get("/api/stories"))}) == 3


# ---------------------------------------------------------------------------- export: tác giả


def test_export_functions_take_creator() -> None:
    card = load_seed_card()
    plain = export_card_json(card)
    assert plain["data"]["creator"] == "" and "creator_uid" not in plain["data"]["extensions"]["lyris"]
    creator = CardCreator(handle="lan_anh", uid="c" * 32)
    data = export_card_json(card, creator)["data"]
    assert data["creator"] == "@lan_anh"
    assert data["extensions"]["lyris"]["creator_uid"] == "c" * 32
    # Tác giả cũ giữ lại từ lúc import bị thay bằng account đang giữ card.
    kept = card.model_copy(update={"extensions": {"v2": {"creator": "ai đó"}}})
    assert export_card_json(kept)["data"]["creator"] == "ai đó"
    assert export_card_json(kept, creator)["data"]["creator"] == "@lan_anh"

    png = export_card_png(card, None, creator)
    again = import_card(png, "image/png", styles=[card.style_profile])
    # Import không lấy tác giả: card nhập vào chưa có chủ, uid; không giữ creator/creator_uid.
    assert again.card.uid is None and again.card.visibility == "private"
    assert "creator" not in json.dumps(again.card.extensions)
    # File của app khác: tác giả vẫn được giữ trong dữ liệu V2 như trước.
    foreign = {"spec": "chara_card_v2", "spec_version": "2.0",
               "data": {"name": "X", "description": "", "first_mes": "", "creator": "someone"}}
    res = import_card(json.dumps(foreign).encode(), "application/json", styles=[card.style_profile])
    assert res.card.extensions["v2"]["creator"] == "someone"


def _png_card_json(png: bytes) -> dict[str, Any]:
    marker = b"tEXtchara\x00"
    start = png.index(marker) + len(marker)
    length = int.from_bytes(png[png.index(marker) - 4 : png.index(marker)], "big")
    payload = png[start : start + length - len(b"chara\x00")]
    result: dict[str, Any] = json.loads(base64.b64decode(payload))
    return result


async def test_export_writes_creator(client: httpx.AsyncClient) -> None:
    await ok(await client.put("/api/account", json={"display_name": "Lan Anh", "handle": "lan_anh"}))
    account = await ok(await client.get("/api/account"))
    card = await create_card(client)
    data = (await ok(await client.get(f"/api/cards/{card['id']}/export?format=json")))["data"]
    assert data["creator"] == "@lan_anh"
    assert data["extensions"]["lyris"]["creator_uid"] == account["uid"]

    png = (await client.get(f"/api/cards/{card['id']}/export?format=png")).content
    embedded = _png_card_json(png)["data"]
    assert embedded["creator"] == "@lan_anh" and embedded["extensions"]["lyris"]["creator_uid"] == account["uid"]

    # Nhập lại file của chính mình: card mới thuộc account hiện tại, uid mới.
    draft = await ok(await client.post("/api/cards/import", content=png, headers={"Content-Type": "image/png"}))
    assert draft["card"]["uid"] is None and draft["warnings"] == []
    saved = await ok(await client.post("/api/cards", json={"card": draft["card"]}))
    assert saved["creator_handle"] == "lan_anh" and saved["uid"] != card["uid"]


# ---------------------------------------------------------------------------- profile công khai


async def test_public_profile(client: httpx.AsyncClient) -> None:
    profile = await ok(await client.get("/api/accounts/ban"))
    assert set(profile) == {"handle", "display_name", "bio", "avatar_url", "banner_url", "created_at", "cards"}
    assert profile["handle"] == "ban" and profile["cards"] == []  # card seed riêng tư

    card = await create_card(client)
    hidden = await create_card(client, name="Bí mật")
    # Phase 4b (docs/auth.md §6.4): chỉ Riêng tư / Công khai; "unlisted" bị từ chối.
    unlisted = await client.put(f"/api/cards/{card['id']}", json={**card, "visibility": "unlisted"})
    assert unlisted.status_code == 422
    await ok(await client.put(f"/api/cards/{card['id']}", json={**card, "visibility": "public"}))
    await ok(await client.put("/api/account/avatar", content=png_bytes(), headers={"Content-Type": "image/png"}))
    await ok(await client.put("/api/account/banner", content=png_bytes((1600, 400)),
                              headers={"Content-Type": "image/png"}))
    await ok(await client.put("/api/account", json={"display_name": "Lan", "handle": "lan", "bio": "Xin chào"}))

    profile = await ok(await client.get("/api/accounts/@LAN"))
    assert profile["display_name"] == "Lan" and profile["bio"] == "Xin chào"
    assert [c["id"] for c in profile["cards"]] == [card["id"]]
    assert hidden["id"] not in {c["id"] for c in profile["cards"]}
    shown = profile["cards"][0]
    assert shown["visibility"] == "public" and shown["creator_handle"] == "lan" and shown["story_count"] == 0
    assert profile["avatar_url"].startswith("/api/accounts/lan/avatar?v=account-")
    assert profile["banner_url"].startswith("/api/accounts/lan/banner?v=banner-")
    assert (await client.get(profile["avatar_url"])).status_code == 200
    banner = await client.get(profile["banner_url"])
    assert banner.status_code == 200 and Image.open(io.BytesIO(banner.content)).size == (1500, 375)

    missing = await client.get("/api/accounts/khong_co")
    assert missing.status_code == 404 and missing.json()["detail"] == "Không tìm thấy tài khoản @khong_co."
    assert (await client.get("/api/accounts/ban")).status_code == 404  # đã đổi handle


# ---------------------------------------------------------------------------- hai tài khoản: không lộ dữ liệu


async def test_two_accounts_never_leak(app: FastAPI, client: httpx.AsyncClient, avatars_dir: Path) -> None:
    repo = repo_of(app)
    # Account thứ hai chèn thẳng vào DB (chưa có cách tạo qua API ở phase này).
    repo.conn.execute(
        "INSERT INTO accounts (uid, handle, display_name) VALUES (?, 'khac', 'Người khác')", ("e" * 32,)
    )
    other = repo.find_account_by_handle("khac")
    assert other is not None and other.id is not None
    oid = other.id
    o_card = repo.create_card(load_seed_card().model_copy(update={"name": "Nhân vật lạ"}), account_id=oid)
    o_public = repo.create_card(
        load_seed_card().model_copy(update={"name": "Công khai", "visibility": "public"}), account_id=oid
    )
    o_persona = repo.create_persona(Persona(name="Persona lạ", gender="female"), account_id=oid)
    assert o_card.id and o_public.id and o_persona.id
    o_story = create_story_for(repo, o_card.id, o_persona.id, model_name="m", account_id=oid)
    assert o_story.id is not None
    o_msg = repo.active_messages(o_story.id)[0]
    assert o_msg.id is not None
    o_avatar = avatars.save_card_avatar(avatars_dir, o_card.id, png_bytes())
    repo.set_card_avatar(o_card.id, o_avatar, account_id=ANY_ACCOUNT)
    o_pub_avatar = avatars.save_card_avatar(avatars_dir, o_public.id, png_bytes())
    repo.set_card_avatar(o_public.id, o_pub_avatar, account_id=ANY_ACCOUNT)
    o_p_avatar = avatars.save_persona_avatar(avatars_dir, o_persona.id, png_bytes())
    repo.set_persona_avatar(o_persona.id, o_p_avatar, account_id=ANY_ACCOUNT)
    template = next(t for t in load_templates() if t.slug != "lac-duong")  # mẫu chủ máy chưa cài
    slug = template.slug
    # Account kia đã "cài" mẫu này (kể cả card trùng tên); với account chủ máy thì chưa.
    repo.create_card(
        template.card.model_copy(update={"extensions": {"lyris": {"template": slug}}}), account_id=oid
    )
    before = {
        t: repo.conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        for t in ("character_cards", "personas", "stories", "messages")
    }

    other_names = {"Nhân vật lạ", "Công khai", "Persona lạ", template.card.name}
    # ---- danh sách
    cards = await ok(await client.get("/api/cards"))
    assert not {c["name"] for c in cards} & other_names
    assert all(c["creator_handle"] == "ban" for c in cards)
    personas = await ok(await client.get("/api/personas"))
    assert o_persona.id not in {p["id"] for p in personas}
    stories = await ok(await client.get("/api/stories"))
    assert o_story.id not in {s["id"] for s in stories}
    account = await ok(await client.get("/api/account"))
    # card_count không tính nhân vật mẫu (card seed Lạc Dương); card của account khác cũng không lọt vào.
    assert (account["card_count"], account["story_count"], account["persona_count"]) == (0, 1, 1)
    tmpl = next(t for t in await ok(await client.get("/api/templates")) if t["slug"] == slug)
    assert tmpl["installed_card_id"] is None

    # ---- card của account khác: như không tồn tại
    for method, url, kwargs in [
        ("GET", f"/api/cards/{o_card.id}", {}),
        ("PUT", f"/api/cards/{o_card.id}", {"json": card_body()}),
        ("DELETE", f"/api/cards/{o_card.id}?with_stories=true", {}),
        ("POST", f"/api/cards/{o_card.id}/duplicate", {}),
        ("PUT", f"/api/cards/{o_card.id}/avatar", {"content": png_bytes(), "headers": {"Content-Type": "image/png"}}),
        ("DELETE", f"/api/cards/{o_card.id}/avatar", {}),
        ("GET", f"/api/cards/{o_card.id}/avatar", {}),
        ("GET", f"/api/cards/{o_card.id}/export", {}),
        ("GET", f"/api/cards/{o_public.id}", {}),  # card công khai của người khác cũng không sửa/đọc qua đây
        ("PUT", f"/api/cards/{o_public.id}", {"json": card_body()}),
        ("GET", f"/api/cards/{o_public.id}/export?format=png", {}),
        # ---- persona
        ("PUT", f"/api/personas/{o_persona.id}", {"json": {"name": "X", "gender": "male"}}),
        ("DELETE", f"/api/personas/{o_persona.id}?with_stories=true", {}),
        ("PUT", f"/api/personas/{o_persona.id}/avatar", {"content": png_bytes(), "headers": {"Content-Type": "image/png"}}),
        ("DELETE", f"/api/personas/{o_persona.id}/avatar", {}),
        ("GET", f"/api/personas/{o_persona.id}/avatar", {}),
        # ---- story
        ("GET", f"/api/stories/{o_story.id}", {}),
        ("PATCH", f"/api/stories/{o_story.id}", {"json": {"title": "Đổi"}}),
        ("PATCH", f"/api/stories/{o_story.id}", {"json": {"model_name": "gemma4:12b"}}),
        ("DELETE", f"/api/stories/{o_story.id}", {}),
        ("GET", f"/api/stories/{o_story.id}/messages", {}),
        ("GET", f"/api/stories/{o_story.id}/extras", {}),
        ("POST", f"/api/stories/{o_story.id}/messages", {"json": {"content": "Chào"}}),
        ("POST", f"/api/stories/{o_story.id}/reply", {}),
        ("GET", f"/api/stories/defaults?card_id={o_card.id}", {}),
        ("POST", "/api/stories", {"json": {"card_id": o_card.id, "persona_id": o_persona.id}}),
        ("POST", "/api/stories", {"json": {"card_id": cards[0]["id"], "persona_id": o_persona.id}}),
        # ---- message trong story của account khác
        ("POST", f"/api/messages/{o_msg.id}/regenerate", {}),
        ("POST", f"/api/messages/{o_msg.id}/variant", {"json": {"variant_index": 0}}),
        ("PATCH", f"/api/messages/{o_msg.id}", {"json": {"content": "Sửa"}}),
        ("DELETE", f"/api/messages/{o_msg.id}", {}),
        ("PUT", f"/api/messages/{o_msg.id}/feedback", {"json": {"rating": "up"}}),
        ("GET", f"/api/messages/{o_msg.id}/snapshot", {}),
        # ---- xem trước prompt / chat thử với persona của account khác
        ("POST", "/api/cards/preview-prompt", {"json": {
            "card": card_body(), "persona_id": o_persona.id,
            "settings": {"narration_pronouns": {"character": "anh", "player": "cô"}}}}),
        ("POST", "/api/cards/test-chat", {"json": {
            "card": card_body(), "persona_id": o_persona.id, "messages": [],
            "settings": {"narration_pronouns": {"character": "anh", "player": "cô"}}}}),
    ]:
        resp = await client.request(method, url, **kwargs)
        assert resp.status_code == 404, (method, url, resp.status_code, resp.text)
        assert "Persona lạ" not in resp.text and "Nhân vật lạ" not in resp.text

    # Persona mặc định trỏ sang persona của account khác: không chọn được, không lộ ra.
    bad = await client.put("/api/settings", json={"default_persona_id": o_persona.id})
    assert bad.status_code == 422
    repo.set_app_settings(repo.get_app_settings(account_id=repo.owner_id()).model_copy(update={"default_persona_id": o_persona.id}), account_id=repo.owner_id())
    assert (await ok(await client.get("/api/settings")))["default_persona_id"] is None
    # Story mới không có persona_id: dùng persona của mình, không phải persona mặc định của người khác.
    mine = await ok(await client.post("/api/stories", json={"card_id": cards[0]["id"]}))
    assert mine["persona_name"] != "Persona lạ"

    # Card công khai của account khác: chỉ ảnh đọc được (hiện ở profile công khai), card riêng tư thì không.
    assert (await client.get(f"/api/cards/{o_public.id}/avatar")).status_code == 200
    profile = await ok(await client.get("/api/accounts/khac"))
    assert [c["name"] for c in profile["cards"]] == ["Công khai"]
    assert profile["cards"][0]["creator_handle"] == "khac" and profile["cards"][0]["story_count"] == 0

    # Không có gì của account kia bị đổi hay xoá.
    after = {
        t: repo.conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        for t in ("character_cards", "personas", "stories", "messages")
    }
    assert after["character_cards"] == before["character_cards"]
    assert after["personas"] == before["personas"]
    assert after["stories"] == before["stories"] + 1 and after["messages"] >= before["messages"]
    assert repo.get_card(o_card.id, account_id=ANY_ACCOUNT).name == "Nhân vật lạ" and repo.get_card(o_card.id, account_id=ANY_ACCOUNT).avatar == o_avatar
    assert repo.get_persona(o_persona.id, account_id=ANY_ACCOUNT).avatar == o_p_avatar
    assert repo.get_story(o_story.id, account_id=ANY_ACCOUNT).title == o_story.title
    assert repo.get_message(o_msg.id, account_id=ANY_ACCOUNT).raw_content == o_msg.raw_content
    assert {o_avatar, o_pub_avatar, o_p_avatar} <= set(files_in(avatars_dir))
    for row_account in (repo.card_account_id(o_card.id), repo.card_account_id(o_public.id)):
        assert row_account == oid

    # Repo: id của account khác -> NotFound khi lọc theo account.
    owner_id = repo.owner_account().id
    assert owner_id is not None
    with pytest.raises(NotFound):
        repo.get_card(o_card.id, account_id=owner_id)
    with pytest.raises(NotFound):
        repo.get_story(o_story.id, account_id=owner_id)
    with pytest.raises(NotFound):
        repo.get_message(o_msg.id, account_id=owner_id)
    with pytest.raises(NotFound):
        repo.update_persona(o_persona.id, Persona(name="X", gender="male"), account_id=owner_id)


async def test_template_installs_into_current_account(app: FastAPI, client: httpx.AsyncClient) -> None:
    templates = await ok(await client.get("/api/templates"))
    slug = next(t["slug"] for t in templates if t["installed_card_id"] is None)
    card = await ok(await client.post(f"/api/templates/{slug}/install"))
    assert card["creator_handle"] == "ban" and card["visibility"] == "private" and HEX32.fullmatch(card["uid"])
    owner = repo_of(app).owner_account()
    assert repo_of(app).card_account_id(card["id"]) == owner.id


def test_seed_belongs_to_owner(seeded_repo: Repo) -> None:
    owner = seeded_repo.owner_account()
    assert owner.id is not None
    counts = seeded_repo.account_counts(owner.id)
    assert counts == {"card_count": 1, "story_count": 1, "persona_count": 1}
    card = seeded_repo.list_cards(account_id=owner.id)[0]
    assert isinstance(card, CharacterCard) and card.visibility == "private"
    assert load_seed_persona().name in {p.name for p in seeded_repo.list_personas(account_id=owner.id)}
