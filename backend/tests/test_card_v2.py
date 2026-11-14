"""Test import/export Character Card V1/V2/V3 (JSON, PNG) của lyris.studio.card_v2."""
from __future__ import annotations

import base64
import io
import json
import struct
import zlib
from typing import Any

import pytest
from PIL import Image

from lyris.models import AddressTerms, CharacterCard
from lyris.studio.card_v2 import (
    MAX_CARD_BYTES,
    CardImportError,
    ImportResult,
    export_card_json,
    export_card_png,
    import_card,
)

STYLES = ["chung", "trung_co_dai", "trung_hien_dai", "viet_hien_dai"]

V2_REQUIRED = {
    "name", "description", "personality", "scenario", "first_mes", "mes_example", "creator_notes",
    "system_prompt", "post_history_instructions", "alternate_greetings", "tags", "creator",
    "character_version", "extensions",
}

# ---------------------------------------------------------------- fixtures


def st_v2_card() -> dict[str, Any]:
    """Card tiếng Anh kiểu SillyTavern export: V2 + các trường V1 ở gốc."""
    data = {
        "name": "Elara Voss",
        "description": (
            "{{char}} is the night librarian of the Ashgrove Archive, a 27-year-old woman with ink-stained "
            "fingers and a quiet, dry wit. She has catalogued every forbidden book in the building and "
            "knows {{user}} has been sneaking into the restricted wing."
        ),
        "personality": "Reserved, observant, secretly lonely; her humor is sharp but never cruel.",
        "scenario": "Midnight in the Archive. {{user}} has just been caught holding a sealed grimoire.",
        "first_mes": (
            "*The lamp on the reading desk flickers as Elara steps out from between the shelves.* "
            "\"That book is sealed for a reason, {{user}}.\" *She holds out her hand, palm up.*"
        ),
        "mes_example": (
            "<START>\n{{user}}: Why do you work nights?\n"
            "{{char}}: *She doesn't look up from the ledger.* \"Books are better company than people.\"\n"
            "<START>\n{{user}}: Can I stay a little longer?\n"
            "{{char}}: \"Ten minutes. Then I'm locking you in with the ghosts.\""
        ),
        "creator_notes": "Works best with slow-burn roleplay.",
        "system_prompt": "You are {{char}}. Never break character.",
        "post_history_instructions": "Keep replies under 200 words.",
        "alternate_greetings": [
            "*Rain hammers the Archive's skylight.* \"You again. Shoes off, you're dripping on the Codex.\"",
            "*Elara is asleep at the desk, glasses askew.*",
        ],
        "character_book": {
            "name": "Ashgrove Archive",
            "entries": [
                {
                    "keys": ["grimoire", "sealed book"],
                    "content": "The sealed grimoires whisper to whoever holds them.",
                    "enabled": True,
                    "insertion_order": 100,
                    "extensions": {},
                }
            ],
            "extensions": {},
        },
        "tags": ["Female", "fantasy", "librarian", "slow burn"],
        "creator": "inkwell",
        "character_version": "1.2",
        "extensions": {
            "talkativeness": "0.5",
            "fav": False,
            "world": "Ashgrove",
            "depth_prompt": {"prompt": "", "depth": 4, "role": "system"},
        },
    }
    root = {k: data[k] for k in ("name", "description", "personality", "scenario", "first_mes", "mes_example")}
    root.update({"spec": "chara_card_v2", "spec_version": "2.0", "data": data, "create_date": "2024-5-1"})
    return root


def v1_card() -> dict[str, Any]:
    return {
        "name": "Captain Rourke",
        "description": (
            "Captain Rourke commands the airship Kestrel. He is gruff, scarred, and loyal to his crew. "
            "His left arm is clockwork; he lost the real one saving <USER>'s father."
        ),
        "personality": "gruff, protective, he hates liars",
        "scenario": "The Kestrel is caught in a storm over the Shattered Coast.",
        "first_mes": "*<BOT> grips the wheel as lightning splits the sky.* \"Hold on to something, kid!\"",
        "mes_example": "<START>\n<USER>: Are we going to make it?\n<BOT>: \"We always do.\"",
        "metadata": {"version": 1, "created": 1690000000},
    }


def v3_card() -> dict[str, Any]:
    return {
        "spec": "chara_card_v3",
        "spec_version": "3.0",
        "data": {
            "name": "Nguyễn Thu Hà",
            "description": (
                "Thu Hà là chủ quán cà phê nhỏ ở góc phố Hàng Bạc. Cô ấy hai mươi sáu tuổi, hay cười, "
                "nhớ tên từng vị khách quen và luôn để dành cho {{user}} chỗ ngồi cạnh cửa sổ."
            ),
            "personality": "Dịu dàng, tinh ý, hơi bướng; cô ấy ghét bị thương hại.",
            "scenario": "Chiều mưa Hà Nội, quán vắng khách.",
            "first_mes": "Cô đặt ly cà phê muối xuống bàn. \"Hôm nay về muộn thế?\"",
            "mes_example": "",
            "creator_notes": "",
            "system_prompt": "",
            "post_history_instructions": "",
            "alternate_greetings": [],
            "group_only_greetings": ["Chào cả nhóm, hôm nay quán có bánh mới."],
            "tags": ["đời thường", "Hà Nội"],
            "creator": "hanoi_writer",
            "character_version": "",
            "nickname": "Hà",
            "creation_date": 1700000000,
            "assets": [{"type": "icon", "uri": "ccdefault:", "name": "main", "ext": "png"}],
            "extensions": {},
        },
    }


def lyris_card() -> CharacterCard:
    return CharacterCard(
        id=7,
        name="Lạc Dương",
        gender="male",
        language="vi",
        description="20 tuổi, sinh viên năm hai. Thanh mai trúc mã của {{user}}.",
        personality="Lạnh lùng, ít nói; riêng với {{user}} thì dịu dàng.",
        appearance="Cao gầy, da trắng, mắt sâu.",
        background="Lớn lên cùng một tiểu khu với {{user}}.",
        goals="Ở bên cạnh {{user}}.",
        secrets="Đã thích {{user}} từ lâu.",
        speech_style="Ngắn gọn, điềm đạm.",
        style_profile="trung_hien_dai",
        address_terms=AddressTerms(self_term="tớ", player_term="cậu", nicknames=["Vãn Vãn", "A Vãn"],
                                   others='xưng "tôi" với người lạ'),
        greeting=(
            "Lạc Dương khép giáo trình lại.\n\n[Thought: Lại thức khuya rồi.]\n\n"
            "\"Dậy thôi, thư viện sắp đóng cửa.\""
        ),
        example_dialogues=(
            "{{user}}: Cậu đợi lâu chưa?\n{{char}}: \"Mới tới.\"\n\n"
            "{{user}}: Tối nay ăn gì?\n{{char}}: \"Cậu chọn.\""
        ),
        tags=["ngôn tình", "vườn trường"],
        scenario="Thư viện trường, cuối thu.",
        alternate_greetings=["Sân bóng rổ lúc hoàng hôn. \"Đợi tớ chút.\""],
        creator_notes="Card mẫu.",
        avatar="card-7-abcdef12.png",
        extensions={},
    )


def as_bytes(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False).encode("utf-8")


def chunk(ctype: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + ctype + payload + struct.pack(">I", zlib.crc32(ctype + payload))


def plain_png(size: tuple[int, int] = (64, 48), color: tuple[int, int, int] = (200, 30, 30)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def png_with_chunks(*extra: bytes, base: bytes | None = None) -> bytes:
    """Chèn các chunk vào trước IEND của một PNG thật."""
    png = base or plain_png()
    iend = png.rindex(b"IEND") - 4
    return png[:iend] + b"".join(extra) + png[iend:]


def b64json(obj: Any) -> bytes:
    return base64.b64encode(as_bytes(obj))


def text_chunks(png: bytes) -> list[tuple[bytes, bytes]]:
    pos, out = 8, []
    while pos < len(png):
        (length,) = struct.unpack(">I", png[pos : pos + 4])
        ctype = png[pos + 4 : pos + 8]
        payload = png[pos + 8 : pos + 8 + length]
        (crc,) = struct.unpack(">I", png[pos + 8 + length : pos + 12 + length])
        assert crc == zlib.crc32(ctype + payload), "CRC sai"
        if ctype in (b"tEXt", b"iTXt", b"zTXt"):
            out.append((ctype, payload))
        pos += 12 + length
    return out


def comparable(card: CharacterCard) -> dict[str, Any]:
    return card.model_dump(exclude={"id", "avatar"})


def has_warning(result: ImportResult, *needles: str) -> bool:
    return any(all(n in w for n in needles) for w in result.warnings)


# ---------------------------------------------------------------- V2 JSON


def test_import_sillytavern_v2_json() -> None:
    res = import_card(as_bytes(st_v2_card()), "application/json", styles=STYLES)
    card = res.card
    assert res.image is None
    assert card.id is None and card.avatar is None
    assert card.name == "Elara Voss"
    assert card.description.startswith("{{char}} is the night librarian")
    assert card.scenario.startswith("Midnight in the Archive")
    assert card.greeting.startswith("*The lamp")
    assert len(card.alternate_greetings) == 2
    assert card.creator_notes == "Works best with slow-burn roleplay."
    assert card.tags == ["Female", "fantasy", "librarian", "slow burn"]
    # <START> -> dòng trống, giữ {{char}}:/{{user}}:
    assert "<START>" not in card.example_dialogues
    assert card.example_dialogues.startswith("{{user}}: Why do you work nights?")
    assert "\n\n{{user}}: Can I stay a little longer?" in card.example_dialogues
    # Heuristic
    assert card.language == "en"
    assert card.gender == "female"
    assert card.style_profile == "chung"
    assert card.address_terms.self_term == "I" and card.address_terms.player_term == "you"
    assert card.appearance == "" and card.secrets == ""
    # Phần chưa dùng được giữ lại
    kept = card.extensions["v2"]
    assert kept["system_prompt"] == "You are {{char}}. Never break character."
    assert kept["post_history_instructions"] == "Keep replies under 200 words."
    assert kept["character_book"]["entries"][0]["keys"] == ["grimoire", "sealed book"]
    assert kept["creator"] == "inkwell"
    assert kept["character_version"] == "1.2"
    assert kept["extensions"]["world"] == "Ashgrove"
    assert "lyris" not in kept["extensions"]
    # Cảnh báo tiếng Việt
    assert has_warning(res, "giới tính", "nữ")
    assert has_warning(res, "system_prompt", "chưa được dùng")
    # Phase 4: character_book không còn là phần "chưa dùng": báo số mục sẽ thêm vào phần Thế giới khi lưu.
    assert not has_warning(res, "character_book")
    assert has_warning(res, "1 mục thế giới", "Thế giới")
    assert has_warning(res, "post_history_instructions")
    assert has_warning(res, "style profile", "chung")
    assert not has_warning(res, "creator")  # siêu dữ liệu vô hại: không cảnh báo


def test_v2_reexport_puts_preserved_parts_back() -> None:
    original = st_v2_card()
    card = import_card(as_bytes(original), None, styles=STYLES).card
    out = export_card_json(card)
    assert out["spec"] == "chara_card_v2" and out["spec_version"] == "2.0"
    data = out["data"]
    assert V2_REQUIRED <= set(data)
    src = original["data"]
    for key in ("system_prompt", "post_history_instructions", "character_book", "creator", "character_version"):
        assert data[key] == src[key]
    for key in ("talkativeness", "fav", "world", "depth_prompt"):
        assert data["extensions"][key] == src["extensions"][key]
    assert data["extensions"]["lyris"]["gender"] == "female"
    assert data["mes_example"].count("<START>") == 2
    assert data["alternate_greetings"] == src["alternate_greetings"]
    # Import lại lần nữa: giống hệt lần đầu, không còn đoán giới tính
    again = import_card(as_bytes(out), "application/json", styles=STYLES)
    assert comparable(again.card) == comparable(card)
    assert not has_warning(again, "giới tính")


def test_v2_without_spec_but_with_data_object() -> None:
    obj = {"data": {"name": "Mira", "first_mes": "Hi {{user}}.", "description": "She is a she-wolf; she bites."}}
    res = import_card(as_bytes(obj), None, styles=STYLES)
    assert res.card.name == "Mira"
    assert res.card.greeting == "Hi {{user}}."


# ---------------------------------------------------------------- V1


def test_import_v1_card() -> None:
    res = import_card(as_bytes(v1_card()), "application/json", styles=STYLES)
    card = res.card
    assert card.name == "Captain Rourke"
    assert card.gender == "male"
    assert card.language == "en"
    # <USER>/<BOT> cũ -> {{user}}/{{char}}
    assert "{{user}}'s father" in card.description
    assert card.greeting.startswith("*{{char}} grips the wheel")
    assert card.example_dialogues == '{{user}}: Are we going to make it?\n{{char}}: "We always do."'
    assert card.alternate_greetings == [] and card.tags == []
    # V1: không giữ rác của app khác
    assert card.extensions == {}
    assert has_warning(res, "đoán là nam")


def test_import_pygmalion_style_v1_aliases() -> None:
    obj = {
        "char_name": "Bram",
        "char_persona": "A tired blacksmith. He works too much and he never sleeps.",
        "world_scenario": "A village forge at dawn.",
        "char_greeting": "*Bram wipes his brow.* Morning.",
        "example_dialogue": "<START>\nYou: Hi\nBram: Hm.",
    }
    card = import_card(as_bytes(obj), None, styles=STYLES).card
    assert card.name == "Bram"
    assert card.description.startswith("A tired blacksmith")
    assert card.scenario == "A village forge at dawn."
    assert card.greeting.startswith("*Bram wipes")
    assert card.example_dialogues == "You: Hi\nBram: Hm."
    assert card.gender == "male"


# ---------------------------------------------------------------- V3


def test_import_v3_json_vietnamese() -> None:
    res = import_card(as_bytes(v3_card()), "application/json", styles=STYLES)
    card = res.card
    assert card.name == "Nguyễn Thu Hà"
    assert card.language == "vi"
    assert card.gender == "female"
    assert card.style_profile == "chung"
    # vi: xưng hô để trống + cảnh báo phải điền
    assert card.address_terms.self_term == "" and card.address_terms.player_term == ""
    assert has_warning(res, "xưng hô", "điền")
    assert has_warning(res, "tiếng Việt")
    kept = card.extensions["v2"]
    assert kept["nickname"] == "Hà"
    assert kept["group_only_greetings"] == ["Chào cả nhóm, hôm nay quán có bánh mới."]
    assert kept["creator"] == "hanoi_writer"
    assert "system_prompt" not in kept  # rỗng thì không giữ
    assert has_warning(res, "group_only_greetings")
    assert has_warning(res, "assets")
    # export V2 trả các khoá V3 về trong data
    data = export_card_json(card)["data"]
    assert data["nickname"] == "Hà"
    assert data["creation_date"] == 1700000000


# ---------------------------------------------------------------- PNG


def test_import_png_chara_text_chunk() -> None:
    png = png_with_chunks(chunk(b"tEXt", b"chara\x00" + b64json(st_v2_card())))
    res = import_card(png, "image/png", styles=STYLES)
    assert res.card.name == "Elara Voss"
    assert res.image == png


def test_import_png_prefers_ccv3_over_chara() -> None:
    v2 = st_v2_card()
    v3 = v3_card()
    png = png_with_chunks(
        chunk(b"tEXt", b"chara\x00" + b64json(v2)),
        chunk(b"tEXt", b"ccv3\x00" + b64json(v3)),
    )
    assert import_card(png, None, styles=STYLES).card.name == "Nguyễn Thu Hà"


def test_import_png_falls_back_to_chara_when_ccv3_broken() -> None:
    png = png_with_chunks(
        chunk(b"tEXt", b"ccv3\x00" + b"!!!not-base64!!!"),
        chunk(b"tEXt", b"chara\x00" + b64json(v1_card())),
    )
    assert import_card(png, None, styles=STYLES).card.name == "Captain Rourke"


def test_import_png_itxt_compressed_and_ztxt() -> None:
    payload = b64json(v1_card())
    itxt = b"chara\x00" + b"\x01\x00" + b"\x00" + b"\x00" + zlib.compress(payload)
    res = import_card(png_with_chunks(chunk(b"iTXt", itxt)), None, styles=STYLES)
    assert res.card.name == "Captain Rourke"
    ztxt = b"chara\x00\x00" + zlib.compress(payload)
    assert import_card(png_with_chunks(chunk(b"zTXt", ztxt)), None, styles=STYLES).card.name == "Captain Rourke"


def test_import_png_raw_json_and_unpadded_base64() -> None:
    raw = png_with_chunks(chunk(b"tEXt", b"chara\x00" + as_bytes(v1_card())))
    assert import_card(raw, None, styles=STYLES).card.name == "Captain Rourke"
    unpadded = b64json(v1_card()).rstrip(b"=")
    png = png_with_chunks(chunk(b"tEXt", b"chara\x00" + unpadded))
    assert import_card(png, None, styles=STYLES).card.name == "Captain Rourke"


# ---------------------------------------------------------------- Lyris round-trip


def test_lyris_json_round_trip() -> None:
    card = lyris_card()
    exported = export_card_json(card)
    data = exported["data"]
    assert V2_REQUIRED <= set(data)
    lyris = data["extensions"]["lyris"]
    assert lyris["gender"] == "male" and lyris["style_profile"] == "trung_hien_dai"
    assert lyris["address_terms"]["nicknames"] == ["Vãn Vãn", "A Vãn"]
    # App khác vẫn đọc được ngoại hình... trong description
    assert "Ngoại hình: Cao gầy, da trắng, mắt sâu." in data["description"]
    assert "Bí mật: Đã thích {{user}} từ lâu." in data["description"]
    assert data["first_mes"] == card.greeting
    assert data["mes_example"].startswith("<START>\n{{user}}: Cậu đợi lâu chưa?")
    assert "avatar" not in data
    # JSON thật (qua chuỗi) rồi import lại
    res = import_card(json.dumps(exported, ensure_ascii=False).encode(), "application/json", styles=STYLES)
    assert comparable(res.card) == comparable(card)
    assert res.card.id is None and res.card.avatar is None
    assert res.card.description == card.description  # không nhân đôi
    assert res.warnings == []


def test_lyris_round_trip_keeps_own_extensions_and_empty_extras() -> None:
    card = lyris_card().model_copy(
        update={"appearance": "", "background": "", "goals": "", "secrets": "", "speech_style": "",
                "language": "en", "address_terms": AddressTerms(self_term="I", player_term="you"),
                "extensions": {"custom": {"a": 1}, "v2": {"creator": "me", "extensions": {"x": 2}}}}
    )
    data = export_card_json(card)["data"]
    assert data["description"] == card.description
    assert data["creator"] == "me"
    assert data["extensions"]["x"] == 2
    again = import_card(as_bytes(export_card_json(card)), None, styles=STYLES)
    assert comparable(again.card) == comparable(card)


def test_lyris_png_round_trip_without_avatar() -> None:
    card = lyris_card()
    png = export_card_png(card, None)
    with Image.open(io.BytesIO(png)) as img:
        img.load()
        assert img.size == (512, 512)
        r, g, b = img.convert("RGB").getpixel((5, 5))
        assert max(r, g, b) < 90  # nền tối
    texts = text_chunks(png)
    assert [c for c, _ in texts] == [b"tEXt"]
    res = import_card(png, "image/png", styles=STYLES)
    assert comparable(res.card) == comparable(card)
    assert res.image == png


def test_export_png_keeps_avatar_and_replaces_old_card_chunk() -> None:
    avatar = png_with_chunks(
        chunk(b"tEXt", b"chara\x00" + b64json(v1_card())),
        chunk(b"tEXt", b"Comment\x00hello"),
        base=plain_png((300, 200)),
    )
    card = lyris_card()
    png = export_card_png(card, avatar)
    with Image.open(io.BytesIO(png)) as img:
        assert img.size == (300, 200)
    keys = [p.split(b"\x00", 1)[0] for _, p in text_chunks(png)]
    assert keys.count(b"chara") == 1
    assert b"Comment" in keys
    assert comparable(import_card(png, None, styles=STYLES).card) == comparable(card)


def test_export_png_converts_non_png_avatar_and_survives_garbage() -> None:
    buf = io.BytesIO()
    Image.new("RGB", (40, 40), (10, 200, 10)).save(buf, format="JPEG")
    png = export_card_png(lyris_card(), buf.getvalue())
    with Image.open(io.BytesIO(png)) as img:
        assert img.size == (40, 40)
    fallback = export_card_png(lyris_card(), b"not an image at all")
    with Image.open(io.BytesIO(fallback)) as img:
        assert img.size == (512, 512)
    assert import_card(fallback, None, styles=STYLES).card.name == "Lạc Dương"


@pytest.mark.parametrize("name", ["Đặng Vy", "林晚", "  ", "Émile"])
def test_export_png_placeholder_any_name(name: str) -> None:
    card = lyris_card().model_copy(update={"name": name})
    png = export_card_png(card, None)
    assert import_card(png, None, styles=STYLES).card.name == name.strip()


# ---------------------------------------------------------------- heuristics


def test_gender_unclear_becomes_other_with_warning() -> None:
    obj = {"spec": "chara_card_v2", "data": {"name": "Echo", "description": "A voice in the static. He said, she said."}}
    res = import_card(as_bytes(obj), None, styles=STYLES)
    assert res.card.gender == "other"
    assert has_warning(res, "giới tính", "khác")


def test_vietnamese_pronoun_gender_guess() -> None:
    obj = {"spec": "chara_card_v2", "data": {
        "name": "Tạ Vân Lan",
        "description": "Nàng là sư tỷ lạnh lùng của Thanh Vân Tông. Nàng ít nói, kiếm pháp cao siêu.",
        "first_mes": "Nàng thu kiếm, liếc nhìn {{user}}.",
    }}
    res = import_card(as_bytes(obj), None, styles=STYLES)
    assert res.card.gender == "female"
    assert res.card.language == "vi"


def test_style_fallback_when_chung_missing_and_unknown_lyris_style() -> None:
    exported = export_card_json(lyris_card())
    exported["data"]["extensions"]["lyris"]["style_profile"] = "khong_ton_tai"
    res = import_card(as_bytes(exported), None, styles=["trung_hien_dai", "viet_hien_dai"])
    assert res.card.style_profile == "trung_hien_dai"
    assert has_warning(res, "khong_ton_tai")
    res2 = import_card(as_bytes(v1_card()), None, styles=[])
    assert res2.card.style_profile == "chung"


# ---------------------------------------------------------------- robustness


def test_wrong_types_are_skipped_with_warnings() -> None:
    obj = {"spec": "chara_card_v2", "spec_version": "2.0", "data": {
        "name": "Kai",
        "description": 12345,
        "personality": None,
        "scenario": ["not", "a", "string"],
        "first_mes": "Hey {{user}}. He waves.",
        "mes_example": {"bad": True},
        "alternate_greetings": "Only one greeting as a string",
        "tags": ["ok", 3, None, "ok", " spaced "],
        "creator_notes": False,
        "extensions": {"lyris": {
            "gender": "robot", "language": 5, "appearance": 7, "style_profile": None,
            "address_terms": {"self_term": "I", "player_term": 9},
        }},
    }}
    res = import_card(as_bytes(obj), None, styles=STYLES)
    card = res.card
    assert card.name == "Kai"
    assert card.description == "" and card.scenario == "" and card.personality == ""
    assert card.example_dialogues == "" and card.creator_notes == ""
    assert card.alternate_greetings == ["Only one greeting as a string"]
    assert card.tags == ["ok", "spaced"]
    assert card.appearance == ""
    assert card.address_terms.self_term == "I"  # en -> mặc định
    assert has_warning(res, "mô tả", "kiểu dữ liệu")
    assert has_warning(res, "tag")
    assert has_warning(res, "xưng hô", "sai định dạng")


def test_extensions_and_lyris_wrong_types() -> None:
    obj = {"spec": "chara_card_v2", "data": {"name": "Z", "extensions": "oops"}}
    res = import_card(as_bytes(obj), None, styles=STYLES)
    assert res.card.extensions == {}
    assert has_warning(res, "extensions")
    obj2 = {"spec": "chara_card_v2", "data": {"name": "Z", "extensions": {"lyris": [1, 2]}}}
    res2 = import_card(as_bytes(obj2), None, styles=STYLES)
    assert has_warning(res2, "Lyris", "sai định dạng")


def test_missing_name_warns_and_long_fields_warn() -> None:
    obj = {"spec": "chara_card_v2", "data": {"description": "x " * 15000, "first_mes": "hi"}}
    res = import_card(as_bytes(obj), None, styles=STYLES)
    assert res.card.name == ""
    assert has_warning(res, "không có tên")
    assert has_warning(res, "20.000", "mô tả")


def test_too_many_tags_truncated() -> None:
    obj = {"spec": "chara_card_v2", "data": {"name": "T", "tags": [f"t{i}" for i in range(30)]}}
    res = import_card(as_bytes(obj), None, styles=STYLES)
    assert len(res.card.tags) == 20
    assert has_warning(res, "30 tag")


def test_utf8_bom_and_crlf() -> None:
    obj = {"name": "Bom", "description": "line one\r\nline two", "first_mes": "x"}
    res = import_card(b"\xef\xbb\xbf" + as_bytes(obj), "application/json", styles=STYLES)
    assert res.card.description == "line one\nline two"


@pytest.mark.parametrize(
    ("payload", "ctype", "needle"),
    [
        (b"", None, "rỗng"),
        (b"   \n", None, "rỗng"),
        (b"{not json", "application/json", "JSON không hợp lệ"),
        (b"[1, 2, 3]", None, "object"),
        (b'{"hello": "world"}', None, "Không nhận ra"),
        (b'{"spec": "chara_card_v2", "data": "nope"}', None, "data"),
        (b"\xff\xd8\xff\xe0garbage", "image/jpeg", "PNG hoặc JSON"),
        (b"GIF89a....", None, "PNG hoặc JSON"),
        (b"just text", "image/png", "PNG"),
        (b"\xc3\x28\xa0\xa1", None, "mã hoá"),
        (b"[" * 100000 + b"]" * 100000, None, "JSON"),
    ],
)
def test_bad_inputs_raise_card_import_error(payload: bytes, ctype: str | None, needle: str) -> None:
    with pytest.raises(CardImportError) as exc:
        import_card(payload, ctype, styles=STYLES)
    assert needle in str(exc.value)


def test_too_large_file() -> None:
    big = b"{" + b" " * MAX_CARD_BYTES + b"}"
    with pytest.raises(CardImportError, match="8MB"):
        import_card(big, "application/json", styles=STYLES)


def test_png_errors() -> None:
    with pytest.raises(CardImportError, match="không chứa dữ liệu nhân vật"):
        import_card(plain_png(), "image/png", styles=STYLES)
    bad = png_with_chunks(chunk(b"tEXt", b"chara\x00" + b"%%%%"))
    with pytest.raises(CardImportError, match="bị hỏng"):
        import_card(bad, None, styles=STYLES)
    not_json = png_with_chunks(chunk(b"tEXt", b"chara\x00" + base64.b64encode(b"hello world")))
    with pytest.raises(CardImportError, match="bị hỏng"):
        import_card(not_json, None, styles=STYLES)
    with pytest.raises(CardImportError, match="hỏng"):
        import_card(b"\x89PNG\r\n\x1a\n\x00\x00", None, styles=STYLES)


def test_truncated_png_still_reads_card_before_cut() -> None:
    png = png_with_chunks(chunk(b"tEXt", b"chara\x00" + b64json(v1_card())))
    cut = png[: png.rindex(b"IEND") - 2]
    assert import_card(cut, None, styles=STYLES).card.name == "Captain Rourke"


def test_ztxt_bomb_is_rejected() -> None:
    bomb = zlib.compress(b"A" * (20 * 1024 * 1024), 9)
    png = png_with_chunks(chunk(b"zTXt", b"chara\x00\x00" + bomb))
    with pytest.raises(CardImportError):
        import_card(png, None, styles=STYLES)


def test_placeholder_without_system_fonts(monkeypatch: pytest.MonkeyPatch) -> None:
    import lyris.studio.card_v2 as mod

    monkeypatch.setattr(mod, "_FONT_CANDIDATES", ())
    png = export_card_png(lyris_card().model_copy(update={"name": "Đặng Vy"}), None)
    with Image.open(io.BytesIO(png)) as img:
        assert img.size == (512, 512)
        # Có vẽ chữ: phải có điểm ảnh sáng
        lo, hi = img.convert("L").getextrema()
        assert hi > 200 and lo < 90


def test_legacy_nora_extension_key_still_imports() -> None:
    """Card export bởi bản trước khi đổi tên (khoá extensions.nora) vẫn giữ đủ trường riêng."""
    exported = export_card_json(lyris_card())
    data = exported["data"]
    data["extensions"]["nora"] = data["extensions"].pop("lyris")
    result = import_card(json.dumps(exported).encode("utf-8"), "application/json", styles=STYLES)
    assert result.card.gender == lyris_card().gender
    assert result.card.address_terms == lyris_card().address_terms
    assert "nora" not in result.card.extensions
