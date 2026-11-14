"""Phase 4b (docs/auth.md §4.1, §8.1): quét tách dữ liệu trên MỌI route với hai tài khoản.

Chủ máy A và thành viên B (`tests/twoaccounts.py`). Với mỗi route trong `ROUTE_RULES` (bảng §4.1, chính bảng
mà `test_auth_routes.py` kiểm là đủ và đúng số route), B gọi với id dữ liệu CỦA A (story, tin nhắn, ký ức,
card riêng tư, card công khai ở route "chỉ Mình", persona, mục sổ thế giới, mã mời...) và với bản sao của
chính B ở route "Không bản sao":
- nhận đúng mã (404 khi là dữ liệu riêng, không phải 403, để không lộ là có; 403 ở route Chủ và snapshot của
  story dùng bản sao; 200 ở route đọc phần Công khai);
- DB không đổi (so `iterdump()` trước và sau mỗi request);
- route danh sách không có phần tử nào của A, trừ card công khai ở `/public-cards` và profile.

Route không nhận id nào của người khác (tạo mới của chính mình, route mở của /api/auth...) được ghi rõ lý do
trong `SWEEP`; test đỏ nếu có route chưa có trong `SWEEP`.
"""
from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from typing import Any

import httpx
import pytest
import pytest_asyncio

from tests.test_auth_routes import ROUTE_RULES
from tests.twoaccounts import (
    PRIVATE_NAME,
    PUBLIC_NAME,
    PUBLIC_SECRET,
    World,
    card_body,
    png_bytes,
    two_accounts,
)

pytestmark = pytest.mark.asyncio(loop_scope="module")

PNG = {"content": png_bytes(), "headers": {"Content-Type": "image/png"}}
LORE_IN = {"title": "Mới", "keys": ["mới"], "content": "Nội dung mới."}
PERSONA_IN = {"name": "Đổi tên", "gender": "male"}


@dataclass
class Call:
    url: str
    expect: set[int]
    kwargs: dict[str, Any] = field(default_factory=dict)
    check: Callable[[httpx.Response, World], None] | None = None


@dataclass
class Skip:
    reason: str


Case = Callable[[World], list[Call]] | Skip


def _not_found(*urls: str, **kwargs: Any) -> Callable[[World], list[Call]]:
    """B gọi từng URL (định dạng bằng thuộc tính của World) -> 404."""

    def build(w: World) -> list[Call]:
        return [Call(u.format(w=w), {404}, dict(kwargs)) for u in urls]

    return build


CARD_IDS = ("{w.a_private}", "{w.a_public}", "{w.b_copy}")  # riêng tư của A, công khai của A, bản sao của B


def _cards(suffix: str, **kwargs: Any) -> Callable[[World], list[Call]]:
    """Route "Mình, Không bản sao" của card: cả ba loại id đều 404."""
    return _not_found(*(f"/api/cards/{cid}{suffix}" for cid in CARD_IDS), **kwargs)


def _owner_only(url: str, **kwargs: Any) -> Callable[[World], list[Call]]:
    def check(resp: httpx.Response, _: World) -> None:
        assert resp.json()["code"] == "owner_only"

    def build(w: World) -> list[Call]:
        return [Call(url.format(w=w), {403}, dict(kwargs), check)]

    return build


def _public_read(suffix: str) -> Callable[[World], list[Call]]:
    """Đ, Mình (cả bản sao) hoặc Công khai: card riêng tư của A 404; card công khai của A và bản sao của B 200."""

    def build(w: World) -> list[Call]:
        return [
            Call(f"/api/cards/{w.a_private}{suffix}", {404}),
            Call(f"/api/cards/{w.a_public}{suffix}", {200}),
            Call(f"/api/cards/{w.b_copy}{suffix}", {200}),
        ]

    return build


def _no_a_text(resp: httpx.Response, w: World) -> None:
    """Danh sách của B không chứa gì của A (tên card riêng, bí mật, persona, story của A)."""
    text = resp.text
    assert PRIVATE_NAME not in text and PUBLIC_SECRET not in text and "Lâm Vãn" not in text, text


def _list(url: str, check: Callable[[httpx.Response, World], None] = _no_a_text) -> Callable[[World], list[Call]]:
    return lambda w: [Call(url, {200}, {}, check)]


def _check_stories(resp: httpx.Response, w: World) -> None:
    _no_a_text(resp, w)
    assert {s["id"] for s in resp.json()} == {w.b_story}


def _check_cards(resp: httpx.Response, w: World) -> None:
    ids = {c["id"] for c in resp.json()}
    assert not ids & {w.a_private, w.a_public, w.b_copy}  # không card của A, không bản sao


def _check_personas(resp: httpx.Response, w: World) -> None:
    assert {p["id"] for p in resp.json()} == {w.b_persona}


def _check_public_cards(resp: httpx.Response, w: World) -> None:
    body = resp.json()
    assert [c["id"] for c in body] == [w.a_public]  # chỉ card công khai của A; không bản sao, không riêng tư
    assert body[0]["creator_handle"] == w.a_handle and PUBLIC_SECRET not in resp.text
    assert "story_count" not in body[0]


def _check_profile(resp: httpx.Response, w: World) -> None:
    body = resp.json()
    assert [c["id"] for c in body["cards"]] == [w.a_public]
    assert all(c["story_count"] == 0 for c in body["cards"])
    assert PUBLIC_SECRET not in resp.text and PRIVATE_NAME not in resp.text


def _check_settings(resp: httpx.Response, w: World) -> None:
    assert resp.json()["default_persona_id"] in (None, w.b_persona)


def _check_lore_status(resp: httpx.Response, w: World) -> None:
    assert resp.json()["entries"] == 0  # B không có sổ thế giới; sổ của bản sao không được đếm


def _check_account(resp: httpx.Response, w: World) -> None:
    body = resp.json()
    assert (body["card_count"], body["story_count"], body["persona_count"]) == (0, 1, 1)


def _check_health(resp: httpx.Response, w: World) -> None:
    body = resp.json()
    assert body["chat_model"] == "" and body["ollama"]["models"] == []


def _check_templates(resp: httpx.Response, w: World) -> None:
    assert all(t["installed_card_id"] is None for t in resp.json())


def _snapshot(w: World) -> list[Call]:
    def forbidden(resp: httpx.Response, _: World) -> None:
        assert resp.json()["detail"] == "Nhân vật này của người khác nên không xem được phần này."

    return [
        Call(f"/api/messages/{w.a_message}/snapshot", {404}),
        Call(f"/api/messages/{w.b_message}/snapshot", {403}, {}, forbidden),  # story của B dùng bản sao
    ]


def _create_story(w: World) -> list[Call]:
    return [
        Call("/api/stories", {404}, {"json": {"card_id": w.a_private, "persona_id": w.b_persona}}),
        Call("/api/stories", {404}, {"json": {"card_id": w.a_public, "persona_id": w.a_persona}}),
        Call("/api/stories", {404}, {"json": {"card_id": w.b_copy, "persona_id": w.b_persona}}),
    ]


def _defaults(w: World) -> list[Call]:
    return [
        Call(f"/api/stories/defaults?card_id={w.a_private}&persona_id={w.b_persona}", {404}),
        Call(f"/api/stories/defaults?card_id={w.b_copy}&persona_id={w.b_persona}", {404}),
        Call(f"/api/stories/defaults?card_id={w.a_public}&persona_id={w.a_persona}", {404}),
        Call(f"/api/stories/defaults?card_id={w.a_public}&persona_id={w.b_persona}", {200}),  # Công khai
    ]


def _preview_body(w: World, persona_id: int) -> dict[str, Any]:
    return {
        "card": card_body("Thử", id=w.a_public),
        "persona_id": persona_id,
        "settings": {"narration_pronouns": {"character": "anh", "player": "cô"}},
    }


def _preview(w: World) -> list[Call]:
    return [Call("/api/cards/preview-prompt", {404}, {"json": _preview_body(w, w.a_persona)})]


def _test_chat(w: World) -> list[Call]:
    return [Call("/api/cards/test-chat", {404}, {"json": {**_preview_body(w, w.a_persona), "messages": []}})]


def _put_settings(w: World) -> list[Call]:
    return [Call("/api/settings", {422}, {"json": {"default_persona_id": w.a_persona}})]


def _lore_entry(method_suffix: str = "", **kwargs: Any) -> Callable[[World], list[Call]]:
    def build(w: World) -> list[Call]:
        entry = w.a_entries[0]
        return [
            Call(f"/api/cards/{w.a_public}/lore/{entry}{method_suffix}", {404}, dict(kwargs)),
            Call(f"/api/cards/{w.a_private}/lore/{entry}{method_suffix}", {404}, dict(kwargs)),
            Call(f"/api/cards/{w.b_copy}/lore/{entry}{method_suffix}", {404}, dict(kwargs)),
        ]

    return build


def _memories(w: World) -> list[Call]:
    return [
        Call(f"/api/stories/{w.a_story}/memories/{w.a_memory}", {404}),
        Call(f"/api/stories/{w.b_story}/memories/{w.a_memory}", {404}),  # ký ức của A qua story của B
    ]


def _profile(w: World) -> list[Call]:
    return [Call(f"/api/accounts/{w.a_handle}", {200}, {}, _check_profile)]


def _profile_image(kind: str, status: int) -> Callable[[World], list[Call]]:
    # Ảnh tài khoản là phần công khai (§4.6); A có avatar, chưa có ảnh bìa. Tài khoản bị khoá: test_public_cards.
    return lambda w: [Call(f"/api/accounts/{w.a_handle}/{kind}", {status})]


def _events(w: World) -> list[Call]:
    """B gắn story của A vào sự kiện: sự kiện vẫn nhận nhưng không mang story_id của A (DB: chỉ dòng của B)."""

    def check(resp: httpx.Response, _: World) -> None:
        assert resp.json() == {"accepted": 0, "dropped": 1}  # tên sự kiện của server: client không gửi được

    return [
        Call("/api/events", {202}, {"json": {"events": [{"name": "story_started", "story_id": w.a_story}]}}, check),
    ]


OWN = Skip("chỉ đụng dữ liệu của chính người gọi, không nhận id của người khác")
OPEN = Skip("route mở của /api/auth (test_auth_api.py)")

SWEEP: dict[tuple[str, str], Case] = {
    # ---- /api/auth
    ("GET", "/api/auth/me"): OPEN,
    ("POST", "/api/auth/setup-owner"): OPEN,
    ("POST", "/api/auth/login"): OPEN,
    ("POST", "/api/auth/signup"): OPEN,
    ("POST", "/api/auth/logout"): OWN,
    ("POST", "/api/auth/change-password"): OWN,
    ("POST", "/api/auth/logout-all"): OWN,
    # ---- /api/admin: Chủ
    ("GET", "/api/admin/accounts"): _owner_only("/api/admin/accounts"),
    ("POST", "/api/admin/accounts/{account_id}/reset-password"): _owner_only("/api/admin/accounts/{w.a_id}/reset-password"),
    ("POST", "/api/admin/accounts/{account_id}/disable"): _owner_only("/api/admin/accounts/{w.a_id}/disable"),
    ("POST", "/api/admin/accounts/{account_id}/enable"): _owner_only("/api/admin/accounts/{w.a_id}/enable"),
    ("GET", "/api/admin/invites"): _owner_only("/api/admin/invites"),
    ("GET", "/api/admin/analytics/summary"): _owner_only("/api/admin/analytics/summary"),
    ("GET", "/api/admin/analytics/export.csv"): _owner_only("/api/admin/analytics/export.csv"),
    ("GET", "/api/admin/analytics/export.jsonl"): _owner_only("/api/admin/analytics/export.jsonl"),
    ("POST", "/api/events"): _events,
    # ---- tuân thủ (docs/compliance.md; test riêng: test_compliance.py)
    ("GET", "/api/legal/{doc}"): Skip("văn bản pháp lý chung, không có dữ liệu tài khoản"),
    ("POST", "/api/messages/{message_id}/report"): _not_found(
        "/api/messages/{w.a_message}/report", json={"reason": "other", "share_text": True}
    ),
    ("POST", "/api/cards/{card_id}/report"): _not_found("/api/cards/{w.a_private}/report", json={"reason": "other"}),
    ("GET", "/api/admin/reports"): _owner_only("/api/admin/reports"),
    ("PATCH", "/api/admin/reports/{report_id}"): _owner_only("/api/admin/reports/1", json={"status": "reviewed"}),
    ("POST", "/api/admin/cards/{card_id}/unpublish"): _owner_only("/api/admin/cards/{w.a_public}/unpublish"),
    ("DELETE", "/api/account"): Skip("chỉ xoá tài khoản của chính người gọi; ghi lần thử mật khẩu (test_compliance.py)"),
    ("GET", "/api/account/export"): Skip("chỉ xuất dữ liệu của chính người gọi; ghi sự kiện (test_compliance.py)"),
    ("POST", "/api/account/terms"): OWN,
    ("POST", "/api/admin/invites"): _owner_only("/api/admin/invites", json={"note": "x"}),
    ("DELETE", "/api/admin/invites/{invite_id}"): _owner_only("/api/admin/invites/1"),
    # ---- máy
    ("GET", "/api/health"): _list("/api/health", _check_health),
    ("GET", "/api/system"): _owner_only("/api/system"),
    ("GET", "/api/settings"): _list("/api/settings", _check_settings),
    ("PUT", "/api/settings"): _put_settings,
    ("GET", "/api/styles"): Skip("file chung, không có dữ liệu tài khoản"),
    ("GET", "/api/lore/status"): _list("/api/lore/status", _check_lore_status),
    ("GET", "/api/templates"): _list("/api/templates", _check_templates),
    ("POST", "/api/templates/{slug}/install"): OWN,
    ("GET", "/api/templates/{slug}/image"): Skip("ảnh nhân vật mẫu, chung cho mọi người"),
    # ---- story
    ("GET", "/api/stories"): _list("/api/stories", _check_stories),
    ("POST", "/api/stories"): _create_story,
    ("GET", "/api/stories/defaults"): _defaults,
    ("GET", "/api/stories/{story_id}"): _not_found("/api/stories/{w.a_story}"),
    ("PATCH", "/api/stories/{story_id}"): _not_found("/api/stories/{w.a_story}", json={"title": "Của B"}),
    ("DELETE", "/api/stories/{story_id}"): _not_found("/api/stories/{w.a_story}"),
    ("GET", "/api/stories/{story_id}/messages"): _not_found("/api/stories/{w.a_story}/messages"),
    ("POST", "/api/stories/{story_id}/messages"): _not_found("/api/stories/{w.a_story}/messages", json={"content": "x"}),
    ("POST", "/api/stories/{story_id}/reply"): _not_found("/api/stories/{w.a_story}/reply"),
    ("GET", "/api/stories/{story_id}/extras"): _not_found("/api/stories/{w.a_story}/extras"),
    ("GET", "/api/stories/{story_id}/lore"): _not_found("/api/stories/{w.a_story}/lore"),
    ("GET", "/api/stories/{story_id}/timeline"): _not_found("/api/stories/{w.a_story}/timeline"),
    ("DELETE", "/api/stories/{story_id}/memories/{memory_id}"): _memories,
    ("POST", "/api/stories/{story_id}/state/rebuild"): _not_found("/api/stories/{w.a_story}/state/rebuild"),
    ("POST", "/api/stories/{story_id}/suggestions"): _not_found("/api/stories/{w.a_story}/suggestions"),
    ("POST", "/api/messages/{message_id}/regenerate"): _not_found("/api/messages/{w.a_message}/regenerate"),
    ("POST", "/api/messages/{message_id}/variant"): _not_found(
        "/api/messages/{w.a_message}/variant", json={"variant_index": 0}
    ),
    ("PATCH", "/api/messages/{message_id}"): _not_found(
        "/api/messages/{w.a_message}", "/api/messages/{w.a_user_message}", json={"content": "Của B"}
    ),
    ("DELETE", "/api/messages/{message_id}"): _not_found("/api/messages/{w.a_message}", "/api/messages/{w.a_user_message}"),
    ("PUT", "/api/messages/{message_id}/feedback"): _not_found(
        "/api/messages/{w.a_message}/feedback", json={"rating": "down", "note": "B"}
    ),
    ("GET", "/api/messages/{message_id}/snapshot"): _snapshot,
    # ---- card
    ("GET", "/api/cards"): _list("/api/cards", _check_cards),
    ("POST", "/api/cards"): OWN,
    ("POST", "/api/cards/import"): OWN,
    ("POST", "/api/cards/draft"): Skip("không nhận id; cổng sinh: test_generation_gate.py"),
    ("POST", "/api/cards/preview-prompt"): _preview,
    ("POST", "/api/cards/test-chat"): _test_chat,
    ("GET", "/api/cards/{card_id}"): _cards(""),
    ("PUT", "/api/cards/{card_id}"): lambda w: [
        Call(f"/api/cards/{cid}", {404}, {"json": card_body("Của B", visibility="private")})
        for cid in (w.a_private, w.a_public, w.b_copy)
    ],
    ("DELETE", "/api/cards/{card_id}"): _cards("?with_stories=true"),
    ("POST", "/api/cards/{card_id}/duplicate"): _cards("/duplicate"),
    ("PUT", "/api/cards/{card_id}/avatar"): _cards("/avatar", **PNG),
    ("DELETE", "/api/cards/{card_id}/avatar"): _cards("/avatar"),
    ("GET", "/api/cards/{card_id}/avatar"): _public_read("/avatar"),
    ("GET", "/api/cards/{card_id}/export"): lambda w: [
        Call(f"/api/cards/{cid}/export?format={fmt}", {404})
        for cid in (w.a_private, w.a_public, w.b_copy)
        for fmt in ("json", "png")
    ],
    ("GET", "/api/cards/{card_id}/public"): _public_read("/public"),
    ("GET", "/api/public-cards"): _list("/api/public-cards", _check_public_cards),
    ("GET", "/api/cards/{card_id}/lore"): _cards("/lore"),
    ("POST", "/api/cards/{card_id}/lore"): _cards("/lore", json=LORE_IN),
    ("POST", "/api/cards/{card_id}/lore/import"): _cards(
        "/lore/import", json={"text": "## Mục lore\n\n### Mới\nKhoá: mới\nNội dung."}
    ),
    ("POST", "/api/cards/{card_id}/lore/import-book"): _cards("/lore/import-book", json={"dry_run": False}),
    ("GET", "/api/cards/{card_id}/lore/summary"): _public_read("/lore/summary"),
    ("PUT", "/api/cards/{card_id}/lore/{entry_id}"): _lore_entry(json=LORE_IN),
    ("PATCH", "/api/cards/{card_id}/lore/{entry_id}"): _lore_entry(json={"enabled": False}),
    ("DELETE", "/api/cards/{card_id}/lore/{entry_id}"): _lore_entry(),
    # ---- persona
    ("GET", "/api/personas"): _list("/api/personas", _check_personas),
    ("POST", "/api/personas"): OWN,
    ("PUT", "/api/personas/{persona_id}"): _not_found("/api/personas/{w.a_persona}", json=PERSONA_IN),
    ("DELETE", "/api/personas/{persona_id}"): _not_found("/api/personas/{w.a_persona}?with_stories=true"),
    ("PUT", "/api/personas/{persona_id}/avatar"): _not_found("/api/personas/{w.a_persona}/avatar", **PNG),
    ("DELETE", "/api/personas/{persona_id}/avatar"): _not_found("/api/personas/{w.a_persona}/avatar"),
    ("GET", "/api/personas/{persona_id}/avatar"): _not_found("/api/personas/{w.a_persona}/avatar"),
    # ---- tài khoản
    ("GET", "/api/account"): _list("/api/account", _check_account),
    ("PUT", "/api/account"): OWN,
    ("PATCH", "/api/account"): OWN,
    ("PUT", "/api/account/avatar"): OWN,
    ("DELETE", "/api/account/avatar"): OWN,
    ("GET", "/api/account/avatar"): OWN,
    ("PUT", "/api/account/banner"): OWN,
    ("DELETE", "/api/account/banner"): OWN,
    ("GET", "/api/account/banner"): OWN,
    ("GET", "/api/accounts/{handle}"): _profile,
    ("GET", "/api/accounts/{handle}/avatar"): _profile_image("avatar", 200),
    ("GET", "/api/accounts/{handle}/banner"): _profile_image("banner", 404),
}


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def world(tmp_path_factory: pytest.TempPathFactory) -> AsyncIterator[World]:
    async with two_accounts(tmp_path_factory.mktemp("sweep")) as w:
        yield w


async def test_sweep_covers_every_route() -> None:
    assert SWEEP.keys() == ROUTE_RULES.keys()
    assert len(SWEEP) == 100
    # Mọi route "Chủ" đều được quét bằng thành viên.
    for route, rule in ROUTE_RULES.items():
        if rule == "owner":
            assert not isinstance(SWEEP[route], Skip), route


@pytest.mark.parametrize("route", sorted(ROUTE_RULES), ids=lambda r: f"{r[0]} {r[1]}")
async def test_member_cannot_reach_owner_data(world: World, route: tuple[str, str]) -> None:
    """B (thành viên) với id dữ liệu của A (chủ máy): đúng mã, và DB không đổi."""
    case = SWEEP[route]
    if isinstance(case, Skip):
        pytest.skip(case.reason)
    method = route[0]
    calls = case(world)
    assert calls, route
    for call in calls:
        before = world.dump()
        resp = await world.b.request(method, call.url, **call.kwargs)
        assert resp.status_code in call.expect, (method, call.url, resp.status_code, resp.text[:300])
        if resp.status_code == 404 and resp.headers.get("content-type", "").startswith("application/json"):
            # 404 không nói gì về chủ sở hữu (không có chữ "người khác", không có tên của A).
            assert PRIVATE_NAME not in resp.text and PUBLIC_NAME not in resp.text, resp.text
        if call.check is not None:
            call.check(resp, world)
        assert world.dump() == before, (method, call.url, "DB đã đổi")


def _kwargs_for(method: str, path: str) -> dict[str, Any]:
    """Body hợp lệ cho route ghi (để request tới được bước kiểm chủ sở hữu, không dừng ở 422)."""
    if method in ("GET", "DELETE") or path.endswith(("/regenerate", "/reply", "/rebuild", "/suggestions", "/duplicate")):
        return {}
    if path.endswith("/avatar"):
        return dict(PNG)
    bodies: dict[str, Any] = {
        "/api/stories/{story_id}": {"title": "Của A"},
        "/api/stories/{story_id}/messages": {"content": "x"},
        "/api/messages/{message_id}": {"content": "Của A"},
        "/api/messages/{message_id}/variant": {"variant_index": 0},
        "/api/messages/{message_id}/feedback": {"rating": "up"},
        "/api/messages/{message_id}/report": {"reason": "other", "share_text": True},
        "/api/cards/{card_id}/report": {"reason": "other"},
        "/api/personas/{persona_id}": PERSONA_IN,
        "/api/cards/{card_id}": card_body("Của A"),
        "/api/cards/{card_id}/lore": LORE_IN,
        "/api/cards/{card_id}/lore/import": {"text": "## Mục lore\n\n### Mới\nKhoá: mới\nNội dung."},
        "/api/cards/{card_id}/lore/import-book": {"dry_run": False},
    }
    return {"json": bodies[path]} if path in bodies else {}


@pytest.mark.parametrize("route", sorted(ROUTE_RULES), ids=lambda r: f"{r[0]} {r[1]}")
async def test_owner_cannot_reach_member_data(world: World, route: tuple[str, str]) -> None:
    """Chiều ngược lại: chủ máy A với id story / tin nhắn / persona / bản sao card của B nhận 404, DB không đổi.

    Chủ máy không đọc được dữ liệu của thành viên (docs/auth.md §0, §1.1); bản sao là của B, A không thấy."""
    method, path = route
    w = world
    ids = {"story_id": w.b_story, "message_id": w.b_message, "persona_id": w.b_persona, "card_id": w.b_copy}
    if "{entry_id}" in path or "{memory_id}" in path or not any(f"{{{k}}}" in path for k in ids):
        pytest.skip("route không nhận id story / tin nhắn / persona / card của B")
    url = path
    for key, value in ids.items():
        url = url.replace(f"{{{key}}}", str(value))
    before = w.dump()
    resp = await w.a.request(method, url, **_kwargs_for(method, path))
    assert resp.status_code == 404, (method, url, resp.status_code, resp.text[:300])
    assert w.dump() == before, (method, url, "DB đã đổi")


async def test_lists_of_owner_hide_member(world: World) -> None:
    """A không thấy story, persona, bản sao của B ở bất kỳ danh sách nào."""
    w = world
    stories = (await w.a.get("/api/stories")).json()
    assert w.b_story not in {s["id"] for s in stories}
    cards = (await w.a.get("/api/cards")).json()
    assert w.b_copy not in {c["id"] for c in cards}
    personas = (await w.a.get("/api/personas")).json()
    assert w.b_persona not in {p["id"] for p in personas}
    assert (await w.a.get("/api/public-cards")).json() == []  # card công khai của chính mình không vào Khám phá
    # Số story trên card công khai của A chỉ đếm story của A (B chơi trên bản sao: A không biết ai đang chơi).
    card = (await w.a.get(f"/api/cards/{w.a_public}")).json()
    assert card["story_count"] == 1
    mai = (await w.a.get("/api/accounts/mai")).json()
    assert mai["cards"] == []


async def test_generic_404_is_the_same_for_missing_and_foreign(world: World) -> None:
    """Không phân biệt "không có" với "của người khác": cùng mã, cùng câu."""
    w = world
    foreign = await w.b.get(f"/api/stories/{w.a_story}")
    missing = await w.b.get("/api/stories/999999")
    assert foreign.status_code == missing.status_code == 404
    assert foreign.json()["detail"].replace(str(w.a_story), "#") == missing.json()["detail"].replace("999999", "#")
    foreign = await w.b.get(f"/api/cards/{w.a_private}")
    missing = await w.b.get("/api/cards/999999")
    assert foreign.json()["detail"].replace(str(w.a_private), "#") == missing.json()["detail"].replace("999999", "#")


async def test_routes_never_read_across_accounts() -> None:
    """§4.2: `ANY_ACCOUNT` (đọc không lọc) chỉ dùng ở việc nền; không route nào được dùng."""
    from pathlib import Path

    import lyris.api

    api = Path(lyris.api.__file__).parent
    routes = sorted(api.glob("routes*.py"))
    assert len(routes) >= 8
    for path in routes:
        assert "ANY_ACCOUNT" not in path.read_text(encoding="utf-8"), path.name
