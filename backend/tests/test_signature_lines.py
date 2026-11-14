"""`extensions.lyris.signature_lines` ("Lời nói đặc trưng" trên trang nhân vật): làm sạch khi lưu card
(dễ dãi, không báo lỗi), giữ nguyên qua export/import Character Card V2."""
from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from lyris.api.app import create_app
from lyris.api.routes_studio import clean_signature_lines, validate_card
from lyris.config import Settings
from lyris.llm.fake import FakeLLM
from lyris.models import AddressTerms, CharacterCard
from lyris.studio.card_v2 import export_card_json, import_card
from tests.authutil import owner_client


def card(**extensions: Any) -> CharacterCard:
    return CharacterCard(
        id=None,
        name="Hạ Vy",
        gender="female",
        language="vi",
        style_profile="viet_hien_dai",
        address_terms=AddressTerms(self_term="mình", player_term="cậu", nicknames=[], others=""),
        extensions=extensions,
    )


def test_clean_signature_lines_is_lenient() -> None:
    assert clean_signature_lines(None) == []
    assert clean_signature_lines("một câu") == []
    assert clean_signature_lines(
        ["  “Trà gừng cho cậu nè.”  ", "", 5, "trà GỪNG cho cậu nè.", '"Mưa  dai lắm."', "a b c", "d e f"]
    ) == ["Trà gừng cho cậu nè.", "Mưa dai lắm.", "a b c"]
    long = "ơ" * 300
    assert clean_signature_lines([long]) == ["ơ" * 140]


def test_validate_card_cleans_signature_lines_and_keeps_other_keys() -> None:
    out = validate_card(
        card(lyris={"template": "ha-vy", "signature_lines": ["“Mưa dai lắm.”", " "], "initial_relationship": {"trust": 40}})
    )
    assert out.extensions["lyris"] == {
        "template": "ha-vy",
        "signature_lines": ["Mưa dai lắm."],
        "initial_relationship": {"trust": 40},
    }
    # Nothing usable: the key goes away, the rest stays.
    out = validate_card(card(lyris={"signature_lines": "không phải list", "narration_character": "nàng"}))
    assert out.extensions["lyris"] == {"narration_character": "nàng"}
    # No lyris block or no key: untouched.
    assert validate_card(card(other={"x": 1})).extensions == {"other": {"x": 1}}


def test_signature_lines_survive_export_and_import() -> None:
    original = card(lyris={"signature_lines": ["Mưa Đà Lạt không lớn mà dai.", "Cậu đọc chậm thôi nha."]})
    exported = export_card_json(original)
    data = exported["data"]["extensions"]["lyris"]
    assert data["extensions"]["lyris"]["signature_lines"] == ["Mưa Đà Lạt không lớn mà dai.", "Cậu đọc chậm thôi nha."]
    back = import_card(json.dumps(exported, ensure_ascii=False).encode(), "application/json", styles=["viet_hien_dai"]).card
    assert back.extensions["lyris"]["signature_lines"] == ["Mưa Đà Lạt không lớn mà dai.", "Cậu đọc chậm thôi nha."]


# ---------------------------------------------------------------------------- API


@pytest.fixture
async def client(tmp_path: Path) -> AsyncIterator[httpx.AsyncClient]:
    settings = Settings(
        db_path=tmp_path / "lyris.db",
        ollama_url="http://127.0.0.1:9",
        chat_model="gemma4:12b",
        num_ctx=8192,
        avatars_dir=tmp_path / "avatars",
        draft_model="draft-model:test",
    )
    app: FastAPI = create_app(settings, FakeLLM(replies=["x"]))
    async with app.router.lifespan_context(app):
        async with owner_client(app, base_url="http://test") as c:
            yield c


def body(**extensions: Any) -> dict[str, Any]:
    return card(**extensions).model_dump(mode="json")


async def test_api_stores_clean_signature_lines(client: httpx.AsyncClient) -> None:
    resp = await client.post(
        "/api/cards", json={"card": body(lyris={"signature_lines": ["  “Ai đợi cậu.”", "", "Ai đợi cậu.", "x " * 100]})}
    )
    assert resp.status_code == 200, resp.text
    saved = resp.json()
    lines = saved["extensions"]["lyris"]["signature_lines"]
    assert lines[0] == "Ai đợi cậu."
    assert len(lines) == 2 and len(lines[1]) <= 140

    saved["extensions"]["lyris"]["signature_lines"] = []
    resp = await client.put(f"/api/cards/{saved['id']}", json=saved)
    assert resp.status_code == 200, resp.text
    assert "signature_lines" not in resp.json()["extensions"].get("lyris", {})
