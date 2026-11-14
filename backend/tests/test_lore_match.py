"""Phase 4 (docs/phase4.md §5): so khớp từ khoá tiếng Việt — mỗi dòng của bảng §5.4 là một ca."""
from __future__ import annotations

import json
import unicodedata
from pathlib import Path

import pytest

from lyris.lore.match import LoreMatcher, key_matches
from lyris.lore.normalize import canon_tone, is_name_like, match_form
from lyris.lore.parse import parse_world_md
from lyris.lore.select import ScanText, fill_key, select_lore
from lyris.models import AddressTerms, CharacterCard, LoreEntry, NarrationPronouns, Persona, Story
from lyris.prompt.templates import PromptContext, get_template

WORLDS = Path(__file__).resolve().parents[2] / "worlds"


def scan(key: str, text: str, *, player: bool = True, ignore: tuple[str, ...] = ()) -> bool:
    return bool(LoreMatcher([(1, [key])], ignore=ignore).scan(text, names_only=not player))


# (văn bản, khoá, lời người chơi?, khớp?) — bảng §5.4
TABLE = [
    ("lúc đó", "Lục", True, False),  # giữ dấu
    ("LỤC THỊ", "Lục thị", True, True),  # không phân biệt hoa thường
    ("lục tung tủ", "Lục", True, True),  # khoá một âm tiết dễ khớp nhầm
    ("Nhân Hoà", "Nhân Hòa", True, True),  # canon_tone
    ("Trình Dịch", "Trì", True, False),  # trọn âm tiết
    ("Yến Hoành Thiên", "Hoành Thiên", True, True),  # trọn cụm trong cụm dài hơn
    ("Lục Tổng, Em Không Cần Anh Nữa", "Lục Tổng Em Không Cần Anh Nữa", True, True),  # dấu câu = khoảng trắng
    ("夏驰说", "夏驰", True, True),  # chữ Hán: chuỗi con
    ("zero", "ZERO", True, True),
    ("Hắn kiên nhẫn chờ.", "nhẫn", True, True),  # trọn âm tiết ≠ trọn từ
    ("Hắn kiên nhẫn chờ.", "nhẫn", False, False),  # khoá viết thường không quét lượt nhân vật
    ("đôi mắt hắn tối lại", "đôi mắt", False, False),
    ("đôi mắt anh xanh thật à?", "đôi mắt", True, True),
    ("Hạ Trì gọi tới", "Hạ Trì", False, True),  # khoá tên riêng quét cả lượt nhân vật
    ("Tiệm hoa thu đường", "Tiệm hoa Thu Đường", True, True),
    ("Nhà a3", "nhà A3", True, True),
    ("nhà A3", "nhà A3", False, True),  # chữ số + chữ hoa = tên riêng
    ("Mĩ thuật", "Mỹ thuật", True, False),  # chưa chuẩn hoá i/y (chấp nhận)
    ("cầu Lan Giang cũ", "Lan Giang", True, True),
    ("ôn bài", "Ôn viên", True, False),
    ("云顶 澜江", "云顶·澜江", True, True),
    ("Lục-Ôn", "Lục - Ôn", True, True),
]


@pytest.mark.parametrize(("text", "key", "player", "want"), TABLE)
def test_vietnamese_match_table(text: str, key: str, player: bool, want: bool) -> None:
    assert scan(key, text, player=player) is want


def test_nfd_text_matches() -> None:
    nfd = unicodedata.normalize("NFD", "Lục thị hôm nay")
    assert nfd != unicodedata.normalize("NFC", nfd)
    assert scan("Lục", nfd) and scan(unicodedata.normalize("NFD", "Lục"), "Lục thị")


@pytest.mark.parametrize(
    ("a", "b", "same"),
    [
        ("hoà", "hòa", True),
        ("Nhân Hoà", "nhân hòa", True),
        ("thuý", "thúy", True),
        ("khoẻ", "khỏe", True),
        ("luỹ", "lũy", True),
        ("huỷ hôn", "hủy hôn", True),
        ("quý", "qúy", False),  # "qu" không đổi chỗ dấu
        ("hoàng", "hoàng", True),
        ("Lục", "lúc", False),
        ("Đ", "D", False),
    ],
)
def test_canon_tone(a: str, b: str, same: bool) -> None:
    assert (match_form(a) == match_form(b)) is same


def test_canon_tone_keeps_qu_and_final_consonant() -> None:
    assert canon_tone("quý") == "quý" and canon_tone("hoàng") == "hoàng" and canon_tone("thuyền") == "thuyền"
    assert canon_tone("hoà") == "hòa" and canon_tone("ủy") == "ủy" and canon_tone("uỷ") == "ủy"


def test_character_and_persona_names_are_ignored_but_keys_containing_them_match() -> None:
    names = ("Lục Bắc Uyên", "Ngọc Anh")
    assert not scan("Lục Bắc Uyên", "Lục Bắc Uyên nhìn cô", ignore=names)
    assert not scan("Ngọc Anh", "Ngọc Anh cười", ignore=names)
    assert not scan("Lục Bắc Uyên (陆北渊)", "Lục Bắc Uyên nhìn cô", ignore=names)
    assert scan("cha của Lục Bắc Uyên", "Ông là cha của Lục Bắc Uyên.", ignore=names)
    assert not scan("{{user}}", "{{user}} đến") and not scan("x", "x y z")


def test_placeholder_keys_are_filled_before_matching() -> None:
    card = CharacterCard(
        name="Lục Bắc Uyên",
        gender="male",
        style_profile="trung_hien_dai",
        address_terms=AddressTerms(self_term="tôi", player_term="em"),
    )
    persona = Persona(name="Ngọc Anh", gender="female")
    story = Story(card_id=1, persona_id=1, title="t", narration_pronouns=NarrationPronouns(character="hắn", player="cô"))
    ctx = PromptContext(card=card, persona=persona, story=story, style="")
    assert fill_key("cha của {{char}}", ctx) == "cha của Lục Bắc Uyên"
    assert fill_key("{{char}}", ctx) is None
    entry = LoreEntry(id=1, card_id=1, slug="book:x", title="Cha", keys=["cha của {{char}}", "{{char}}"], content="Ông mất.")
    lore = select_lore(
        [entry],
        tpl=get_template("vi"),
        ctx=ctx,
        tail=[ScanText("Kể về cha của Lục Bắc Uyên đi.", True)],
        earlier=[ScanText("Lục Bắc Uyên im lặng.", False)],
    )
    assert [s.entry_id for s in lore.fresh] == [1]


def test_messages_are_scanned_separately() -> None:
    entry = LoreEntry(id=1, card_id=1, slug="m", title="Hạ Trì", keys=["Hạ Trì"], content="Bạn thân.")
    card = CharacterCard(
        name="Cố Hoài Dã", gender="male", style_profile="trung_hien_dai", address_terms=AddressTerms(self_term="tôi", player_term="cậu")
    )
    ctx = PromptContext(
        card=card,
        persona=Persona(name="An", gender="female"),
        story=Story(card_id=1, persona_id=1, title="t", narration_pronouns=NarrationPronouns(character="hắn", player="cô")),
        style="",
    )
    lore = select_lore(
        [entry], tpl=get_template("vi"), ctx=ctx, tail=[ScanText("Trì đâu rồi?", True)], earlier=[ScanText("Gọi Hạ", True)]
    )
    assert lore.carried == [] and lore.fresh == []


def test_is_name_like() -> None:
    assert is_name_like("Hạ Trì") and is_name_like("GHOST") and is_name_like("phòng 402") and is_name_like("夏驰")
    assert not is_name_like("căn hộ") and not is_name_like("nhẫn") and not is_name_like("đôi mắt")


def test_key_matches_helper() -> None:
    assert key_matches("Hôn ước", "chuyện hôn ước ấy") and not key_matches("Hôn ước", "ước gì")


def test_real_opening_of_tan_duong_does_not_trigger_social_anxiety() -> None:
    # §5.3: lời mở đầu thật nhắc "nhịp tim", "tai nghe", "đám đông" (khoá viết thường của "Chứng lo âu xã hội").
    # Lượt nhân vật chỉ được quét bằng khoá tên riêng, nên mục đó không được gợi ra.
    card = json.loads((WORLDS / "tan-duong" / "card.json").read_text(encoding="utf-8"))["data"]
    world = parse_world_md((WORLDS / "tan-duong" / "world.md").read_text(encoding="utf-8"), card["name"])
    entries = {e.title: (i, e) for i, e in enumerate(world.entries)}
    anxiety_id, anxiety = entries["Chứng lo âu xã hội của Tần Dương"]
    matcher = LoreMatcher([(i, e.keys) for i, e in enumerate(world.entries)], ignore=[card["name"]])
    opening = card["first_mes"]
    assert matcher.scan(opening)  # nếu quét bằng mọi khoá thì có khớp...
    assert anxiety_id in LoreMatcher([(anxiety_id, anxiety.keys)]).scan(opening)
    assert anxiety_id not in matcher.scan(opening, names_only=True)  # ...nhưng lượt nhân vật thì không


def test_underscore_is_punctuation_not_part_of_a_word() -> None:
    # In nghiêng kiểu markdown và tên nối bằng "_" vẫn khớp (review: \w+ giữ "_" trong token).
    assert key_matches("hôn ước", "_hôn ước_")
    assert key_matches("hôn ước", "__hôn ước__ ấy")
    assert key_matches("Hạ Trì", "Hạ_Trì")
    assert key_matches("Hạ Trì", "_Hạ Trì_ đến")
    assert not key_matches("Hạ Trì", "Hạ_Trìa")
