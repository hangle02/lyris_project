"""Phase 4 (docs/phase4.md §8, §4.4, §4.6, §12.1): API sổ thế giới, nhập world.md / Card V2, và show_thoughts."""
from __future__ import annotations

import copy
import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from lyris.api.app import create_app
from lyris.db.repo import ANY_ACCOUNT, Repo
from lyris.llm.fake import FakeLLM
from tests.test_phase3_e2e import make_settings, repo_of
from tests.authutil import owner_client

WORLDS = Path(__file__).resolve().parents[2] / "worlds"


@pytest.fixture
async def app(tmp_path: Path) -> AsyncIterator[FastAPI]:
    application = create_app(make_settings(tmp_path), FakeLLM())
    async with application.router.lifespan_context(application):
        yield application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with owner_client(app, base_url="http://test") as c:
        yield c


async def ok(resp: httpx.Response) -> Any:
    assert resp.status_code == 200, resp.text
    return resp.json()


async def world_card(client: httpx.AsyncClient, name: str) -> dict[str, Any]:
    draft = await ok(await client.post("/api/cards/import", content=(WORLDS / name / "card.json").read_bytes()))
    return dict(await ok(await client.post("/api/cards", json={"card": draft["card"]})))


def world_md(name: str) -> str:
    return (WORLDS / name / "world.md").read_text(encoding="utf-8")


async def import_md(client: httpx.AsyncClient, card_id: int, text: str, **kw: Any) -> dict[str, Any]:
    return dict(await ok(await client.post(f"/api/cards/{card_id}/lore/import", json={"text": text, **kw})))


async def entries(client: httpx.AsyncClient, card_id: int) -> list[dict[str, Any]]:
    return list(await ok(await client.get(f"/api/cards/{card_id}/lore")))


async def seed_card_id(client: httpx.AsyncClient) -> int:
    return int((await client.get("/api/cards")).json()[0]["id"])


# ---------------------------------------------------------------------------- CRUD


async def test_crud_and_validation(client: httpx.AsyncClient, app: FastAPI) -> None:
    cid = await seed_card_id(client)
    assert await entries(client, cid) == []
    body = {"title": "  Tiệm   sách cũ ", "keys": ["tiệm sách", " tiệm sách ", "", "Tiệm Sách"], "content": "Ba đời.", "known_by": ["Lạc Dương"]}
    created = await ok(await client.post(f"/api/cards/{cid}/lore", json=body))
    assert created["title"] == "Tiệm sách cũ" and created["keys"] == ["tiệm sách"]
    assert created["known_by"] == ["{{char}}"] and created["audience"] == "character"
    assert created["source"] == "manual" and created["slug"].startswith("manual:") and created["edited"] is False
    eid = created["id"]

    one = await ok(await client.post(f"/api/cards/{cid}/lore", json={"title": "Mẹ", "keys": ["mẹ"]}))
    assert one["warnings"] == ["Từ khoá “mẹ” chỉ có một chữ nên sẽ gợi rất thường xuyên."]
    assert one["position"] == created["position"] + 1 and one["audience"] == "everyone"

    updated = await ok(await client.put(f"/api/cards/{cid}/lore/{eid}", json={**body, "content": "Bốn đời."}))
    assert updated["content"] == "Bốn đời." and updated["edited"] is False  # mục tự thêm: không có "đã sửa"
    patched = await ok(await client.patch(f"/api/cards/{cid}/lore/{eid}", json={"enabled": False, "position": 9}))
    assert patched["enabled"] is False and patched["position"] == 9
    assert [e["id"] for e in await entries(client, cid)] == [one["id"], eid]

    assert (await ok(await client.delete(f"/api/cards/{cid}/lore/{eid}"))) == {"deleted": 1}
    assert [e["id"] for e in await entries(client, cid)] == [one["id"]]
    assert (await client.delete(f"/api/cards/{cid}/lore/{eid}")).status_code == 404
    # Mục tự thêm bị xoá hẳn (không giữ bia mộ).
    assert app.state.repo.lore_by_slug(cid).get(created["slug"]) is None


@pytest.mark.parametrize(
    ("body", "detail"),
    [
        ({"title": "   "}, "Mục thế giới cần có tên."),
        ({"title": "A", "keys": [f"khoá {i}" for i in range(33)]}, "Mỗi mục có tối đa 32 từ khoá."),
        ({"title": "A", "known_by": []}, "Cần chọn ai biết điều này."),
        ({"title": "A", "known_by": ["  "]}, "Cần chọn ai biết điều này."),
    ],
)
async def test_validation_messages(client: httpx.AsyncClient, body: dict[str, Any], detail: str) -> None:
    cid = await seed_card_id(client)
    resp = await client.post(f"/api/cards/{cid}/lore", json=body)
    assert resp.status_code == 422 and resp.json()["detail"] == detail


async def test_other_account_and_other_card_are_404(client: httpx.AsyncClient, app: FastAPI) -> None:
    repo: Repo = repo_of(app)
    cid = await seed_card_id(client)
    mine = await ok(await client.post(f"/api/cards/{cid}/lore", json={"title": "A", "keys": ["aa bb"]}))
    other_account = repo.create_account("khac", "Người khác")
    seed = repo.get_card(cid, account_id=ANY_ACCOUNT)
    other_card = repo.create_card(seed.model_copy(update={"id": None}), account_id=other_account.id)
    assert other_card.id is not None
    for method, path, body in [
        ("GET", f"/api/cards/{other_card.id}/lore", None),
        ("POST", f"/api/cards/{other_card.id}/lore", {"title": "X"}),
        ("POST", f"/api/cards/{other_card.id}/lore/import", {"text": world_md("luc-bac-uyen"), "dry_run": True}),
        ("GET", f"/api/cards/{other_card.id}/lore/summary", None),
        ("PUT", f"/api/cards/{other_card.id}/lore/{mine['id']}", {"title": "X"}),
        ("DELETE", f"/api/cards/{other_card.id}/lore/{mine['id']}", None),
        ("GET", "/api/cards/999999/lore", None),
    ]:
        resp = await client.request(method, path, json=body)
        assert resp.status_code == 404, (method, path, resp.text)
    # Mục của card khác (cùng account) trong path của card này: 404.
    second = await ok(await client.post("/api/cards/{}/duplicate".format(cid)))
    resp = await client.patch(f"/api/cards/{second['id']}/lore/{mine['id']}", json={"enabled": False})
    assert resp.status_code == 404


async def test_too_many_entries_is_409(client: httpx.AsyncClient, app: FastAPI, monkeypatch: pytest.MonkeyPatch) -> None:
    import lyris.lore.service as svc

    monkeypatch.setattr(svc, "MAX_LORE_ENTRIES_PER_CARD", 1)
    cid = await seed_card_id(client)
    await ok(await client.post(f"/api/cards/{cid}/lore", json={"title": "A"}))
    resp = await client.post(f"/api/cards/{cid}/lore", json={"title": "B"})
    assert resp.status_code == 409


# ---------------------------------------------------------------------------- nhập world.md


async def test_import_dry_run_then_import_then_reimport_idempotent(client: httpx.AsyncClient, app: FastAPI) -> None:
    card = await world_card(client, "luc-bac-uyen")
    cid = card["id"]
    text = world_md("luc-bac-uyen")
    dry = await import_md(client, cid, text, dry_run=True, filename="world.md")
    assert dry["dry_run"] is True and dry["created"] == 27 and await entries(client, cid) == []
    assert dry["player_only"] == ["Hứa Tri Ý", "Phó Cảnh Hành", "Tô Mạn Ninh", "Tiệm hoa Thu Đường và bệnh viện Nhân Hòa"]
    assert len(dry["dropped_sentences"]) == 4 and all(": " in s for s in dry["dropped_sentences"])
    assert any("Bí mật và Chức năng của 7 nhân vật" in n and "Lục Bắc Uyên" in n for n in dry["notes"])
    assert "Từ khoá “nhẫn” chỉ có một chữ, cũng khớp trong những từ như “kiên nhẫn”." in dry["warnings"]
    assert {i["action"] for i in dry["items"]} == {"create"}

    real = await import_md(client, cid, text)
    assert real["created"] == 27
    rows = await entries(client, cid)
    assert len(rows) == 27 and all(r["source"] == "world_md" for r in rows)
    by = {r["title"]: r for r in rows}
    assert by["Hứa Tri Ý"]["audience"] == "player" and by["Câu nói đêm mưa"]["audience"] == "character"
    assert by["Hôn ước Lục - Ôn"]["known_by"] == ["*"]

    again = await import_md(client, cid, text)
    assert (again["created"], again["updated"], again["unchanged"], again["missing"]) == (0, 0, 27, 0)
    assert len(await entries(client, cid)) == 27
    assert len(app.state.repo.lore_by_slug(cid)) == 27


async def test_edit_keep_edited_delete_tombstone_and_missing(client: httpx.AsyncClient, app: FastAPI) -> None:
    card = await world_card(client, "luc-bac-uyen")
    cid = card["id"]
    text = world_md("luc-bac-uyen")
    await import_md(client, cid, text)
    rows = {r["title"]: r for r in await entries(client, cid)}
    ring = rows["Chiếc nhẫn sapphire"]
    body = {k: ring[k] for k in ("title", "category", "keys", "known_by", "content", "enabled", "priority")}

    # PUT không đổi gì: không thành "đã sửa". PATCH bật/tắt: cũng không.
    same = await ok(await client.put(f"/api/cards/{cid}/lore/{ring['id']}", json=body))
    assert same["edited"] is False
    toggled = await ok(await client.patch(f"/api/cards/{cid}/lore/{ring['id']}", json={"enabled": False}))
    assert toggled["edited"] is False
    # PUT có đổi: thành "đã sửa", nhập lại không ghi đè.
    edited = await ok(await client.put(f"/api/cards/{cid}/lore/{ring['id']}", json={**body, "keys": ["sapphire"]}))
    assert edited["edited"] is True
    again = await import_md(client, cid, text)
    assert again["kept_edited"] == 1 and again["unchanged"] == 26
    assert {r["title"]: r for r in await entries(client, cid)}["Chiếc nhẫn sapphire"]["keys"] == ["sapphire"]

    # Xoá một mục từ file: bia mộ; nhập lại -> skip_removed, không quay lại, không hiện trong GET.
    eyes = rows["Đôi mắt xanh lam"]
    await ok(await client.delete(f"/api/cards/{cid}/lore/{eyes['id']}"))
    again = await import_md(client, cid, text)
    assert again["skipped_removed"] == 1 and again["created"] == 0
    assert "Bỏ qua 1 mục bạn đã xoá." in again["notes"]
    assert [i for i in again["items"] if i["action"] == "skip_removed"][0]["slug"] == eyes["slug"]
    titles = [r["title"] for r in await entries(client, cid)]
    assert "Đôi mắt xanh lam" not in titles and len(titles) == 26
    assert (await client.get(f"/api/cards/{cid}/lore/{eyes['id']}")).status_code in (404, 405)
    assert (await client.put(f"/api/cards/{cid}/lore/{eyes['id']}", json=body)).status_code == 404

    # File mới thiếu một mục: mặc định giữ (keep_missing); delete_missing xoá mục chưa sửa, giữ mục đã sửa.
    manual = await ok(await client.post(f"/api/cards/{cid}/lore", json={"title": "Tự thêm", "keys": ["tự thêm"]}))
    cut = text.split("### Lục Thừa An")[0] + "### Lục Thừa An" + text.split("### Lục Thừa An")[1].split("### Câu nói đêm mưa")[0]
    partial = await import_md(client, cid, cut, dry_run=True)
    assert partial["missing"] > 0 and partial["deleted"] == 0
    assert all(i["action"] != "delete" for i in partial["items"])
    kept = await import_md(client, cid, cut)
    assert kept["missing"] == partial["missing"] and len(await entries(client, cid)) == 27
    dele = await import_md(client, cid, cut, delete_missing=True)
    assert dele["missing"] == partial["missing"]
    assert dele["deleted"] == dele["missing"] - 1 and dele["kept_edited"] == 1  # nhẫn sapphire đã sửa: giữ
    titles = [r["title"] for r in await entries(client, cid)]
    assert "Chiếc nhẫn sapphire" in titles and "Tự thêm" in titles and manual["title"] == "Tự thêm"


async def test_two_files_do_not_delete_each_other(client: httpx.AsyncClient) -> None:
    cid = await seed_card_id(client)
    a = "## Mục lore\n\n### Một\n- keys: một hai\n- content: A.\n"
    b = "## Mục lore\n\n### Hai\n- keys: ba bốn\n- content: B.\n"
    await import_md(client, cid, a)
    res = await import_md(client, cid, b)
    assert res["created"] == 1 and res["missing"] == 1 and res["deleted"] == 0
    assert sorted(r["title"] for r in await entries(client, cid)) == ["Hai", "Một"]


@pytest.mark.parametrize(
    ("text", "detail"),
    [
        ("# Không có gì\n\nChỉ là ghi chú.", "Không tìm thấy mục thế giới nào."),
        ("## Mục lore\n" + "x" * 600_000, "File quá lớn (tối đa 500 KB)."),
    ],
)
async def test_import_422(client: httpx.AsyncClient, text: str, detail: str) -> None:
    cid = await seed_card_id(client)
    resp = await client.post(f"/api/cards/{cid}/lore/import", json={"text": text})
    assert resp.status_code == 422 and resp.json()["detail"].startswith(detail)


# ---------------------------------------------------------------------------- Card V2 character_book


BOOK = {
    "name": "Sổ cũ",
    "entries": [
        {"id": 7, "keys": ["Andromeda"], "secondary_keys": ["ship"], "content": "A ship.", "enabled": True,
         "insertion_order": 3, "priority": 5, "selective": True, "constant": False, "comment": "Con tàu",
         "extensions": {"depth": 4}},
        {"keys": ["cha của {{char}}"], "content": "Ông mất năm ấy.", "name": "Cha",
         "extensions": {"lyris": {"known_by": ["Aria"], "category": "character"}}},
        {"keys": ["bí mật"], "content": "Chỉ người chơi.", "comment": "Riêng",
         "extensions": {"lyris": {"known_by": ["{{user}}"]}}},
    ],
}


def v2_card(book: dict[str, Any]) -> bytes:
    return json.dumps(
        {
            "spec": "chara_card_v2",
            "spec_version": "2.0",
            "data": {
                "name": "Aria",
                "description": "She is a pilot.",
                "first_mes": "Hi.",
                "character_book": book,
                "extensions": {"lyris": {"language": "en", "gender": "female", "style_profile": "trung_hien_dai"}},
            },
        }
    ).encode()


async def test_card_book_import_save_reput_export_roundtrip(client: httpx.AsyncClient, app: FastAPI) -> None:
    draft = await ok(await client.post("/api/cards/import", content=v2_card(BOOK)))
    assert draft["card"]["extensions"]["v2"]["character_book"]["entries"]  # nháp vẫn mang book
    assert not any("Phase 4" in w for w in draft["warnings"])
    saved = await ok(await client.post("/api/cards", json={"card": draft["card"]}))
    cid = saved["id"]
    assert "character_book" not in saved["extensions"].get("v2", {})
    rows = await entries(client, cid)
    assert [(r["slug"], r["title"], r["source"]) for r in rows] == [
        ("book:cha", "Cha", "card_book"),
        ("book:rieng", "Riêng", "card_book"),
        ("book:id-7", "Con tàu", "card_book"),
    ]
    by = {r["title"]: r for r in rows}
    assert by["Cha"]["known_by"] == ["{{char}}"] and by["Cha"]["category"] == "character"
    assert by["Riêng"]["audience"] == "player" and by["Con tàu"]["priority"] == 5
    assert by["Con tàu"]["extra"]["secondary_keys"] == ["ship"] and by["Con tàu"]["extra"]["extensions"] == {"depth": 4}

    # Trình sửa còn giữ extensions của nháp: PUT lại card kèm book -> không nhân đôi, book lại bị bỏ.
    card = {**draft["card"], "name": "Aria"}
    put = await ok(await client.put(f"/api/cards/{cid}", json=card))
    assert "character_book" not in put["extensions"].get("v2", {})
    assert len(await entries(client, cid)) == 3

    # Book bị sắp lại thứ tự: slug không đổi, vẫn không nhân đôi.
    shuffled = copy.deepcopy(BOOK)
    shuffled["entries"].reverse()
    draft2 = copy.deepcopy(draft["card"])
    draft2["extensions"]["v2"]["character_book"] = shuffled
    await ok(await client.put(f"/api/cards/{cid}", json=draft2))
    assert len(await entries(client, cid)) == 3

    exported = await ok(await client.get(f"/api/cards/{cid}/export?format=json"))
    book = exported["data"]["character_book"]
    assert book["name"] == "Aria · Thế giới" and len(book["entries"]) == 3
    ship = next(e for e in book["entries"] if e["name"] == "Con tàu")
    assert ship["secondary_keys"] == ["ship"] and ship["selective"] is True and ship["id"] == 7
    assert ship["extensions"]["depth"] == 4 and ship["extensions"]["lyris"]["slug"] == "book:id-7"
    assert ship["insertion_order"] == 3 and ship["priority"] == 5 and ship["keys"] == ["Andromeda"]
    father = next(e for e in book["entries"] if e["name"] == "Cha")
    assert father["extensions"]["lyris"] == {"known_by": ["{{char}}"], "category": "character", "slug": "book:cha"}

    # Nhập lại file vừa export thành card mới: cùng các mục.
    draft3 = await ok(await client.post("/api/cards/import", content=json.dumps(exported).encode()))
    again = await ok(await client.post("/api/cards", json={"card": draft3["card"]}))
    assert sorted((r["slug"], r["title"]) for r in await entries(client, again["id"])) == sorted((r["slug"], r["title"]) for r in rows)


async def test_import_book_for_old_card_and_duplicate_and_delete(client: httpx.AsyncClient, app: FastAPI) -> None:
    repo: Repo = repo_of(app)
    cid = await seed_card_id(client)
    seed = repo.get_card(cid, account_id=ANY_ACCOUNT)
    # Card cũ (import trước Phase 4): book còn nằm trong extensions.v2.
    old = repo.create_card(seed.model_copy(update={"id": None, "extensions": {"v2": {"character_book": BOOK, "creator": "x"}}}), account_id=repo.owner_id())
    assert old.id is not None
    dry = await ok(await client.post(f"/api/cards/{old.id}/lore/import-book", json={"dry_run": True}))
    assert dry["created"] == 3 and await entries(client, old.id) == []
    res = await ok(await client.post(f"/api/cards/{old.id}/lore/import-book", json={"dry_run": False}))
    assert res["created"] == 3 and len(await entries(client, old.id)) == 3
    assert repo.get_card(old.id, account_id=ANY_ACCOUNT).extensions == {"v2": {"creator": "x"}}
    resp = await client.post(f"/api/cards/{old.id}/lore/import-book", json={})
    assert resp.status_code == 422

    # Nhân bản card: sao chép mục, giữ slug, source.
    copy_card = await ok(await client.post(f"/api/cards/{old.id}/duplicate"))
    copied = await entries(client, copy_card["id"])
    assert [(r["slug"], r["source"]) for r in copied] == [(r["slug"], r["source"]) for r in await entries(client, old.id)]

    # Xoá card: mục và hit đi theo (CASCADE).
    await ok(await client.delete(f"/api/cards/{copy_card['id']}"))
    assert repo.conn.execute("SELECT COUNT(*) FROM lore_entries WHERE card_id = ?", (copy_card["id"],)).fetchone()[0] == 0


# ---------------------------------------------------------------------------- hồ sơ nhân vật


async def test_summary_only_lists_public_people_and_places(client: httpx.AsyncClient) -> None:
    card = await world_card(client, "luc-bac-uyen")
    cid = card["id"]
    await import_md(client, cid, world_md("luc-bac-uyen"))
    summary = await ok(await client.get(f"/api/cards/{cid}/lore/summary"))
    assert summary["total"] == 27
    assert summary["people"] == ["Lục Chấn Đình", "Tống Nghi Lan", "Trình Dịch", "Ôn Chính Đức"]
    assert "Hứa Tri Ý" not in summary["people"] and len(summary["places"]) == 5
    assert "Tiệm hoa Thu Đường và bệnh viện Nhân Hòa" not in summary["places"]
    assert summary["people_more"] == 0 and summary["places_more"] == 0
    text = json.dumps(summary, ensure_ascii=False)
    assert "Câu nói đêm mưa" not in text and "Kết cục" not in text
    assert (await client.get("/api/cards/999999/lore/summary")).status_code == 404


# ---------------------------------------------------------------------------- B: show_thoughts


async def test_show_thoughts_create_patch_and_list(client: httpx.AsyncClient, app: FastAPI) -> None:
    repo: Repo = repo_of(app)
    cid = await seed_card_id(client)
    pid = (await client.get("/api/personas")).json()[0]["id"]
    off = await ok(await client.post("/api/stories", json={"card_id": cid, "persona_id": pid, "show_thoughts": False}))
    on = await ok(await client.post("/api/stories", json={"card_id": cid, "persona_id": pid}))
    assert off["show_thoughts"] is False and on["show_thoughts"] is True
    listed = {s["id"]: s for s in await ok(await client.get("/api/stories"))}
    assert listed[off["id"]]["show_thoughts"] is False and listed[on["id"]]["show_thoughts"] is True
    detail = await ok(await client.get(f"/api/stories/{off['id']}"))
    assert detail["story"]["show_thoughts"] is False

    # PATCH chỉ show_thoughts: không đổi updated_at, không đổi thứ tự hub.
    order = [s["id"] for s in await ok(await client.get("/api/stories"))]
    before = repo.conn.execute("SELECT updated_at FROM stories WHERE id = ?", (off["id"],)).fetchone()[0]
    patched = await ok(await client.patch(f"/api/stories/{off['id']}", json={"show_thoughts": True}))
    assert patched["show_thoughts"] is True
    patched = await ok(await client.patch(f"/api/stories/{off['id']}", json={"show_thoughts": False}))
    assert patched["show_thoughts"] is False
    after = repo.conn.execute("SELECT updated_at FROM stories WHERE id = ?", (off["id"],)).fetchone()[0]
    assert after == before
    assert [s["id"] for s in await ok(await client.get("/api/stories"))] == order
    # PATCH kèm trường khác vẫn đổi updated_at như cũ.
    await ok(await client.patch(f"/api/stories/{off['id']}", json={"show_thoughts": True, "title": "Đổi tên"}))
    assert repo.conn.execute("SELECT updated_at FROM stories WHERE id = ?", (off["id"],)).fetchone()[0] != before
    # Seed story (không có card_id) cũng nhận show_thoughts.
    seed_story = await ok(await client.post("/api/stories", json={"show_thoughts": False}))
    assert seed_story["show_thoughts"] is False


async def test_show_thoughts_does_not_change_prompt(client: httpx.AsyncClient, app: FastAPI) -> None:
    fake: FakeLLM = app.state.llm
    cid = await seed_card_id(client)
    pid = (await client.get("/api/personas")).json()[0]["id"]
    prompts = []
    for show in (True, False):
        story = await ok(await client.post("/api/stories", json={"card_id": cid, "persona_id": pid, "show_thoughts": show}))
        resp = await client.post(f"/api/stories/{story['id']}/messages", json={"content": "Chào cậu."})
        assert resp.status_code == 200
        prompts.append(fake.calls[-1]["messages"])
    assert prompts[0] == prompts[1]


def test_story_model_default_show_thoughts() -> None:
    from lyris.models import NarrationPronouns, Story

    story = Story(card_id=1, persona_id=1, title="t", narration_pronouns=NarrationPronouns(character="anh", player="cô"))
    assert story.show_thoughts is True


# ---------------------------------------------------------------------------- Studio: chat thử / xem trước


async def test_test_chat_uses_saved_card_lore_without_recording(client: httpx.AsyncClient, app: FastAPI) -> None:
    fake: FakeLLM = app.state.llm
    repo: Repo = repo_of(app)
    cid = await seed_card_id(client)
    await ok(await client.post(f"/api/cards/{cid}/lore", json={"title": "Hôn ước", "keys": ["hôn ước"], "content": "Hai nhà hứa gả con."}))
    card = (await ok(await client.get(f"/api/cards/{cid}")))
    pid = (await client.get("/api/personas")).json()[0]["id"]
    defaults = await ok(await client.get(f"/api/stories/defaults?card_id={cid}&persona_id={pid}"))
    body = {"card": card, "persona_id": pid, "settings": defaults["settings"], "messages": [{"role": "user", "content": "Hôn ước là sao?"}]}
    resp = await client.post("/api/cards/test-chat", json=body)
    assert resp.status_code == 200, resp.text
    last = fake.calls[-1]["messages"][-1].content
    assert last.startswith("[Thông tin thế giới") and "- Hôn ước: Hai nhà hứa gả con." in last
    assert repo.conn.execute("SELECT COUNT(*) FROM lore_hits").fetchone()[0] == 0
    # Card chưa lưu (không có id) hoặc của người khác: không có khối D.
    resp = await client.post("/api/cards/test-chat", json={**body, "card": {**card, "id": None}})
    assert resp.status_code == 200 and not fake.calls[-1]["messages"][-1].content.startswith("[Thông tin thế giới")
    preview = await ok(
        await client.post("/api/cards/preview-prompt", json={"card": card, "persona_id": pid, "settings": defaults["settings"]})
    )
    assert "D" not in preview["token_estimate"]  # xem trước chỉ có lời mở đầu: thường không có mục nào
