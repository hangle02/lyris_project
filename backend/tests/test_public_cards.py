"""Phase 4b (docs/auth.md §4.3-§4.6, §6.4, §8.1 "Nhân vật công khai"): card công khai, bản sao khi bắt đầu
story, hồ sơ chỉ đọc, Khám phá, ảnh, tạm khoá người tạo."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from lyris.api.routes_studio import PublicCardView
from lyris.db.repo import ANY_ACCOUNT, NO_LONGER_SHARED, NotFound
from lyris.llm.fake import FakeLLM
from lyris.models import CharacterCard
from tests.authutil import add_member, client_for
from tests.twoaccounts import (
    LORE,
    PUBLIC_NAME,
    PUBLIC_SECRET,
    REPLY,
    TRIGGER,
    World,
    card_body,
    ok,
    parse_sse,
    png_bytes,
    send,
    two_accounts,
)

WHITELIST = {
    "id", "uid", "name", "role", "gender", "language", "description", "appearance", "scenario", "greeting",
    "alternate_greetings", "tags", "style_profile", "address_terms", "speech_style", "avatar_url",
    "creator_handle", "creator_name", "visibility", "extensions",
}
HIDDEN_TEXT = ("Tính cách riêng tư", "Hoàn cảnh riêng tư", "Mục tiêu riêng tư", PUBLIC_SECRET, "Ví dụ thoại riêng tư",
               "Ghi chú người tạo riêng tư", "khoa_la", "character_book")


def card_row(w: World, card_id: int) -> dict[str, Any]:
    with w.repo.locked() as conn:
        row = conn.execute("SELECT * FROM character_cards WHERE id = ?", (card_id,)).fetchone()
    assert row is not None
    return dict(row)


def count(w: World, sql: str, *params: Any) -> int:
    with w.repo.locked() as conn:
        return int(conn.execute(sql, params).fetchone()[0])


# ---------------------------------------------------------------------------- bản sao


async def test_start_story_makes_a_full_copy(tmp_path: Path) -> None:
    async with two_accounts(tmp_path) as w:
        original, copy = card_row(w, w.a_public), card_row(w, w.b_copy)
        assert copy["account_id"] == w.b_id and copy["story_copy"] == 1 and copy["visibility"] == "private"
        assert copy["origin_card_id"] == w.a_public and copy["origin_account_id"] == w.a_id
        assert copy["origin_updated_at"] == original["updated_at"]
        assert copy["uid"] != original["uid"]
        for col in ("name", "role", "personality", "background", "goals", "secrets", "greeting", "example_dialogues",
                    "scenario", "address_terms_json", "tags_json", "style_profile", "speech_style"):
            assert copy[col] == original[col], col
        # Ảnh riêng: file khác, cùng nội dung.
        assert copy["avatar"] and copy["avatar"] != original["avatar"]
        assert copy["avatar"].startswith(f"card-{w.b_copy}-")
        assert (w.avatars_dir / copy["avatar"]).read_bytes() == (w.avatars_dir / original["avatar"]).read_bytes()
        # Sổ thế giới: chỉ mục bật (3 trên 4).
        titles = {e.title for e in w.repo.list_lore(w.b_copy)}
        assert titles == {e["title"] for e in LORE if e.get("enabled", True)}
        assert w.repo.card_origin(w.b_copy).story_copy and not w.repo.card_origin(w.a_public).story_copy
        story = (await ok(await w.b.get(f"/api/stories/{w.b_story}")))
        assert story["story"]["card_id"] == w.b_copy


async def test_story_detail_of_copy_is_public_view(tmp_path: Path) -> None:
    async with two_accounts(tmp_path) as w:
        detail = await ok(await w.b.get(f"/api/stories/{w.b_story}"))
        card = detail["card"]
        assert set(card) == WHITELIST
        raw = json.dumps(card, ensure_ascii=False)
        assert not any(t in raw for t in HIDDEN_TEXT), raw
        assert card["creator_handle"] == w.a_handle and card["name"] == PUBLIC_NAME
        assert card["extensions"] == {"lyris": {"narration_character": "hắn", "signature_lines": ["Biển hôm nay lặng."]}}
        # Story của chính A vẫn nhận card đầy đủ.
        own = await ok(await w.a.get(f"/api/stories/{w.a_story}"))
        assert own["card"]["secrets"] == PUBLIC_SECRET


async def test_public_card_view_whitelist(tmp_path: Path) -> None:
    async with two_accounts(tmp_path) as w:
        assert set(PublicCardView.model_fields) == WHITELIST
        public = await ok(await w.b.get(f"/api/cards/{w.a_public}/public"))
        assert set(public) == WHITELIST | {"can_start"} and public["can_start"] is True
        assert not any(t in json.dumps(public, ensure_ascii=False) for t in HIDDEN_TEXT)
        assert public["creator_handle"] == w.a_handle and public["visibility"] == "public"
        assert public["avatar_url"] == f"/api/cards/{w.a_public}/avatar?v={card_row(w, w.a_public)['avatar']}"
        copy = await ok(await w.b.get(f"/api/cards/{w.b_copy}/public"))
        assert copy["can_start"] is False and copy["creator_handle"] == w.a_handle
        mine = await ok(await w.a.get(f"/api/cards/{w.a_public}/public"))  # người tạo xem "người khác thấy gì"
        assert set(mine) == WHITELIST | {"can_start"}
        assert (await w.b.get(f"/api/cards/{w.a_private}/public")).status_code == 404
        summary = await ok(await w.b.get(f"/api/cards/{w.a_public}/lore/summary"))
        assert summary["places"] == ["Bến cảng"] and summary["people"] == []
        assert "Kỷ niệm" not in json.dumps(summary, ensure_ascii=False)


async def test_owner_edits_do_not_reach_the_copy(tmp_path: Path) -> None:
    fake = FakeLLM(replies=[REPLY])
    async with two_accounts(tmp_path, fake) as w:
        before_copy = card_row(w, w.b_copy)
        before_lore = [e.model_dump() for e in w.repo.list_lore(w.b_copy)]
        jobs_before = len(w.repo.list_jobs(w.b_story))
        await ok(await w.a.put(f"/api/cards/{w.a_public}", json=card_body("Tên mới của A", visibility="public",
                                                                           secrets="Bí mật mới của A")))
        await ok(await w.a.post(f"/api/cards/{w.a_public}/lore", json={"title": "Mục mới", "keys": ["bến cảng"],
                                                                         "content": "Nội dung mới của A."}))
        await ok(await w.a.patch(f"/api/cards/{w.a_public}/lore/{w.a_entries[0]}", json={"enabled": False}))
        await ok(await w.a.delete(f"/api/cards/{w.a_public}/avatar"))
        assert card_row(w, w.b_copy) == before_copy
        assert [e.model_dump() for e in w.repo.list_lore(w.b_copy)] == before_lore
        assert len(w.repo.list_jobs(w.b_story)) == jobs_before  # không job nào của B được xếp
        assert (w.avatars_dir / before_copy["avatar"]).is_file()
        await send(w.b, w.b_story, "Bến cảng hôm nay sao rồi?")
        prompt = "\n".join(m.content for m in fake.calls[-1]["messages"])
        assert "Tên mới của A" not in prompt and "Bí mật mới của A" not in prompt and "Nội dung mới của A" not in prompt
        assert PUBLIC_NAME in prompt and PUBLIC_SECRET in prompt  # bản sao chụp lúc bắt đầu


async def test_owner_hides_card_and_player_keeps_playing(tmp_path: Path) -> None:
    async with two_accounts(tmp_path) as w:
        await ok(await w.a.put(f"/api/cards/{w.a_public}", json=card_body(PUBLIC_NAME, visibility="private")))
        assert (await ok(await w.b.get("/api/public-cards"))) == []
        assert (await ok(await w.b.get(f"/api/accounts/{w.a_handle}")))["cards"] == []
        assert (await w.b.get(f"/api/cards/{w.a_public}/public")).status_code == 404
        assert (await w.b.get(f"/api/cards/{w.a_public}/avatar")).status_code == 404
        events = await send(w.b, w.b_story, "Mình vẫn ở đây.")
        assert events[-1][0] == "done"
        cards_before = count(w, "SELECT COUNT(*) FROM character_cards")
        resp = await w.b.post("/api/stories", json={"card_id": w.a_public, "persona_id": w.b_persona})
        assert resp.status_code == 404
        assert count(w, "SELECT COUNT(*) FROM character_cards") == cards_before
        assert (await w.b.get(f"/api/cards/{w.b_copy}/avatar")).status_code == 200  # ảnh của bản sao vẫn còn


async def test_owner_deletes_card_and_copy_survives(tmp_path: Path) -> None:
    async with two_accounts(tmp_path) as w:
        resp = await w.a.delete(f"/api/cards/{w.a_public}?with_stories=true")
        assert resp.status_code == 200 and resp.json() == {"deleted_stories": 1}  # chỉ story của A
        assert w.repo.get_story(w.b_story, account_id=w.b_id).card_id == w.b_copy
        origin = w.repo.card_origin(w.b_copy)
        assert origin.story_copy and origin.origin_card_id is None and origin.origin_account_id == w.a_id
        copy = await ok(await w.b.get(f"/api/cards/{w.b_copy}/public"))
        assert copy["creator_handle"] == w.a_handle  # "bởi @handle" còn
        assert len(w.repo.list_lore(w.b_copy)) == 3
        assert (await send(w.b, w.b_story, "Còn ai không?"))[-1][0] == "done"


async def test_copy_is_closed_to_studio_routes(tmp_path: Path) -> None:
    async with two_accounts(tmp_path) as w:
        for method, url in [
            ("GET", f"/api/cards/{w.b_copy}"),
            ("GET", f"/api/cards/{w.b_copy}/lore"),
            ("GET", f"/api/cards/{w.b_copy}/export"),
            ("POST", f"/api/cards/{w.b_copy}/duplicate"),
            ("DELETE", f"/api/cards/{w.b_copy}"),
            ("GET", f"/api/stories/defaults?card_id={w.b_copy}"),
        ]:
            assert (await w.b.request(method, url)).status_code == 404, (method, url)
        snap = await w.b.get(f"/api/messages/{w.b_message}/snapshot")
        assert snap.status_code == 403
        assert snap.json()["detail"] == "Nhân vật này của người khác nên không xem được phần này."
        own_lore = await ok(await w.a.get(f"/api/stories/{w.a_story}/lore"))
        assert own_lore["can_edit"] is True
        lore = await ok(await w.b.get(f"/api/stories/{w.b_story}/lore"))
        assert lore["can_edit"] is False
        audiences = {e["title"]: e["audience"] for e in lore["entries"]}
        assert audiences == {"Bến cảng": "everyone", "Kỷ niệm": "player", "Bí mật nhỏ": "character"}
        assert next(e for e in lore["entries"] if e["title"] == "Kỷ niệm")["content"] == "Kỷ niệm của Mai."
        # Copy không có trong danh sách / số đếm của B.
        assert (await ok(await w.b.get("/api/cards"))) == []
        assert (await ok(await w.b.get("/api/account")))["card_count"] == 0
        assert (await ok(await w.b.get("/api/lore/status")))["entries"] == 0
        assert (await ok(await w.b.get("/api/accounts/mai")))["cards"] == []
        assert (await ok(await w.a.get("/api/public-cards"))) == []


async def test_preview_and_test_chat_never_load_the_copy_lore(tmp_path: Path) -> None:
    fake = FakeLLM(replies=[REPLY])
    async with two_accounts(tmp_path, fake) as w:
        def body(card_id: int, persona_id: int) -> dict[str, Any]:
            return {
                "card": card_body(PUBLIC_NAME, id=card_id, greeting=TRIGGER),
                "persona_id": persona_id,
                "settings": {"narration_pronouns": {"character": "anh", "player": "cô"}},
            }

        def lore_text(text: str) -> bool:
            return "Bến cảng cũ." in text or "Chỉ Hải Đăng biết" in text

        # Xem trước dùng lượt người chơi mẫu (không có từ khoá); `_lore_for` là chung với chat thử bên dưới.
        theirs = await ok(await w.b.post("/api/cards/preview-prompt", json=body(w.b_copy, w.b_persona)))
        assert not lore_text(json.dumps(theirs, ensure_ascii=False))
        public = await ok(await w.b.post("/api/cards/preview-prompt", json=body(w.a_public, w.b_persona)))
        assert not lore_text(json.dumps(public, ensure_ascii=False))  # id card công khai của A: cũng không

        history = [{"role": "user", "content": TRIGGER}]
        resp = await w.b.post("/api/cards/test-chat", json={**body(w.b_copy, w.b_persona), "messages": history})
        assert resp.status_code == 200 and parse_sse(resp.text)[-1][0] == "done", resp.text
        prompt = "\n".join(m.content for m in fake.calls[-1]["messages"])
        assert not lore_text(prompt)
        resp = await w.a.post("/api/cards/test-chat", json={**body(w.a_public, w.a_persona), "messages": history})
        assert resp.status_code == 200
        assert lore_text("\n".join(m.content for m in fake.calls[-1]["messages"]))


async def test_deleting_last_story_drops_the_copy(tmp_path: Path) -> None:
    async with two_accounts(tmp_path) as w:
        second = await ok(await w.b.post("/api/stories", json={"card_id": w.a_public, "persona_id": w.b_persona}))
        assert second["card_id"] not in (w.b_copy, w.a_public)  # mỗi story một bản sao
        avatar = card_row(w, w.b_copy)["avatar"]
        assert (await w.b.delete(f"/api/stories/{w.b_story}")).status_code == 200
        with pytest.raises(NotFound):
            w.repo.get_card(w.b_copy, account_id=ANY_ACCOUNT)
        assert count(w, "SELECT COUNT(*) FROM lore_entries WHERE card_id = ?", w.b_copy) == 0
        assert not (w.avatars_dir / avatar).exists()
        assert w.repo.get_card(second["card_id"], account_id=w.b_id)  # bản sao của story còn lại giữ nguyên


async def test_deleting_persona_with_stories_drops_their_copies(tmp_path: Path) -> None:
    async with two_accounts(tmp_path) as w:
        await ok(await w.b.post("/api/stories", json={"card_id": w.a_public, "persona_id": w.b_persona}))
        assert count(w, "SELECT COUNT(*) FROM character_cards WHERE story_copy = 1") == 2
        avatars = [r for r in (w.avatars_dir).iterdir() if r.name.startswith("card-")]
        resp = await w.b.delete(f"/api/personas/{w.b_persona}?with_stories=true")
        assert resp.status_code == 200 and resp.json() == {"deleted_stories": 2}
        assert count(w, "SELECT COUNT(*) FROM character_cards WHERE story_copy = 1") == 0
        orphans = count(
            w, "SELECT COUNT(*) FROM character_cards c WHERE story_copy = 1"
            " AND NOT EXISTS (SELECT 1 FROM stories s WHERE s.card_id = c.id)"
        )
        assert orphans == 0
        left = [r for r in (w.avatars_dir).iterdir() if r.name.startswith("card-")]
        assert len(left) == len(avatars) - 2
        assert card_row(w, w.a_public)  # card gốc của A không bị đụng


async def test_hidden_right_when_starting_creates_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A chuyển Riêng tư đúng lúc B bấm bắt đầu: 404 "không còn được chia sẻ", không có dòng card/story nào."""
    async with two_accounts(tmp_path) as w:
        real = w.repo.copy_public_card

        def flip_then_copy(card_id: int, *, account_id: int) -> CharacterCard:
            with w.repo.transaction():
                w.repo.conn.execute("UPDATE character_cards SET visibility = 'private' WHERE id = ?", (card_id,))
            return real(card_id, account_id=account_id)

        monkeypatch.setattr(w.repo, "copy_public_card", flip_then_copy)
        cards = count(w, "SELECT COUNT(*) FROM character_cards")
        stories = count(w, "SELECT COUNT(*) FROM stories")
        resp = await w.b.post("/api/stories", json={"card_id": w.a_public, "persona_id": w.b_persona})
        assert resp.status_code == 404 and resp.json()["detail"] == NO_LONGER_SHARED
        assert count(w, "SELECT COUNT(*) FROM character_cards") == cards
        assert count(w, "SELECT COUNT(*) FROM stories") == stories


async def test_copy_drops_template_marker(tmp_path: Path) -> None:
    async with two_accounts(tmp_path) as w:
        with w.repo.transaction():
            w.repo.conn.execute(
                "UPDATE character_cards SET extensions_json = ? WHERE id = ?",
                (json.dumps({"lyris": {"template": "ha-vy", "narration_character": "y"},
                             "v2": {"character_book": {"entries": []}}}), w.a_public),
            )
        copy = w.repo.copy_public_card(w.a_public, account_id=w.b_id)
        assert copy.extensions == {"lyris": {"narration_character": "y"}}
        with pytest.raises(NotFound, match=NO_LONGER_SHARED):
            w.repo.copy_public_card(w.a_public, account_id=w.a_id)  # gốc của chính mình: không chép
        with pytest.raises(NotFound, match=NO_LONGER_SHARED):
            w.repo.copy_public_card(w.a_private, account_id=w.b_id)
        with pytest.raises(NotFound, match=NO_LONGER_SHARED):
            w.repo.copy_public_card(w.b_copy, account_id=w.a_id)  # bản sao không bao giờ là gốc


# ---------------------------------------------------------------------------- công tắc, Khám phá, tạm khoá


async def test_visibility_switch_rules(tmp_path: Path) -> None:
    async with two_accounts(tmp_path) as w:
        body = card_body(PUBLIC_NAME, visibility="unlisted")
        resp = await w.a.put(f"/api/cards/{w.a_public}", json=body)
        assert resp.status_code == 422
        assert (await w.a.post("/api/cards", json={"card": body})).status_code == 422
        installed = await ok(await w.a.post("/api/templates/lac-duong/install"))
        template = {**installed, "visibility": "public"}
        resp = await w.a.put(f"/api/cards/{installed['id']}", json=template)
        assert resp.status_code == 422 and resp.json()["detail"] == "Nhân vật mẫu đã có sẵn cho mọi người."
        marked = card_body("Mẫu giả", visibility="public", extensions={"lyris": {"template": "ha-vy"}})
        assert (await w.a.post("/api/cards", json={"card": marked})).status_code == 422
        # Card cũ không gửi visibility thì giữ nguyên giá trị đang lưu.
        plain = {k: v for k, v in card_body(PUBLIC_NAME).items() if k != "visibility"}
        assert (await ok(await w.a.put(f"/api/cards/{w.a_public}", json=plain)))["visibility"] == "public"


async def test_explore_lists_other_accounts_public_cards(tmp_path: Path) -> None:
    async with two_accounts(tmp_path) as w:
        cards = await ok(await w.b.get("/api/public-cards"))
        assert [c["id"] for c in cards] == [w.a_public]
        expected = {"id", "uid", "visibility", "name", "role", "gender", "language", "style_profile", "description",
                    "tags", "avatar_url", "updated_at", "creator_handle", "creator_name", "creator_avatar_url"}
        assert set(cards[0]) == expected
        await ok(await w.a.put("/api/account/avatar", content=png_bytes(), headers={"Content-Type": "image/png"}))
        cards = await ok(await w.b.get("/api/public-cards"))
        assert cards[0]["creator_avatar_url"].startswith(f"/api/accounts/{w.a_handle}/avatar?v=account-")
        assert (await w.b.get(cards[0]["creator_avatar_url"])).status_code == 200
        assert (await w.b.get(cards[0]["avatar_url"])).status_code == 200


async def test_disabled_creator_is_hidden_and_comes_back(tmp_path: Path) -> None:
    async with two_accounts(tmp_path) as w:
        lan = add_member(w.repo, "lan", "Lan")
        async with client_for(w.app, lan) as c:
            card = await ok(await c.post("/api/cards", json={"card": card_body("Của Lan", visibility="public")}))
            await ok(await c.put(f"/api/cards/{card['id']}/avatar", content=png_bytes(),
                                 headers={"Content-Type": "image/png"}))
            await ok(await c.put("/api/account/avatar", content=png_bytes(), headers={"Content-Type": "image/png"}))
        b_story = await ok(await w.b.post("/api/stories", json={"card_id": card["id"], "persona_id": w.b_persona}))
        assert {c["id"] for c in await ok(await w.b.get("/api/public-cards"))} == {w.a_public, card["id"]}

        await ok(await w.a.post(f"/api/admin/accounts/{lan}/disable"))
        assert {c["id"] for c in await ok(await w.b.get("/api/public-cards"))} == {w.a_public}
        assert (await w.b.get("/api/accounts/lan")).status_code == 404
        assert (await w.b.get("/api/accounts/lan/avatar")).status_code == 404
        assert (await w.a.get("/api/accounts/lan/avatar")).status_code == 200  # chủ máy vẫn thấy ảnh
        assert (await w.b.get(f"/api/cards/{card['id']}/public")).status_code == 404
        assert (await w.b.get(f"/api/cards/{card['id']}/avatar")).status_code == 404
        resp = await w.b.post("/api/stories", json={"card_id": card["id"], "persona_id": w.b_persona})
        assert resp.status_code == 404
        # Story B đã bắt đầu vẫn chơi tiếp (bản sao của B).
        assert (await send(w.b, b_story["id"], "Lan đâu rồi?"))[-1][0] == "done"

        await ok(await w.a.post(f"/api/admin/accounts/{lan}/enable"))
        assert {c["id"] for c in await ok(await w.b.get("/api/public-cards"))} == {w.a_public, card["id"]}
        assert [c["id"] for c in (await ok(await w.b.get("/api/accounts/lan")))["cards"]] == [card["id"]]


async def test_import_avatar_token_belongs_to_importer(tmp_path: Path) -> None:
    async with two_accounts(tmp_path) as w:
        exported = (await w.a.get(f"/api/cards/{w.a_private}/export?format=png")).content
        imported = await ok(await w.a.post("/api/cards/import", content=exported, headers={"Content-Type": "image/png"}))
        token = imported["avatar_token"]
        assert token
        stolen = await ok(await w.b.post("/api/cards", json={"card": imported["card"], "avatar_token": token}))
        assert stolen["avatar"] is None  # B không lấy được ảnh tạm của A
        mine = await ok(await w.a.post("/api/cards", json={"card": imported["card"], "avatar_token": token}))
        assert mine["avatar"] and mine["avatar"].startswith(f"card-{mine['id']}-")


async def test_member_without_cards_gets_own_seed_story(tmp_path: Path) -> None:
    """`POST /api/stories` không body với thành viên chưa có card: card Lạc Dương và persona Lâm Vãn CỦA RIÊNG HỌ
    (không bao giờ là bản sao hay card của chủ máy, §4.1)."""
    async with two_accounts(tmp_path) as w:
        story = await ok(await w.b.post("/api/stories"))
        card = w.repo.get_card(story["card_id"], account_id=w.b_id, copies=False)
        assert card.name == "Lạc Dương" and story["card_id"] != w.b_copy
        assert w.repo.get_persona(story["persona_id"], account_id=w.b_id)
