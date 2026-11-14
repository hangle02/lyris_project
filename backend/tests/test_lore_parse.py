"""Phase 4 (docs/phase4.md §4): đọc world.md thành mục thế giới, trên 4 file thật trong worlds/ và các ca nhỏ."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from lyris.lore.match import LoreMatcher
from lyris.lore.parse import (
    META_SPOILER_TERMS,
    heading_keys,
    key_warnings,
    parse_world_md,
    slugify,
)

WORLDS = Path(__file__).resolve().parents[2] / "worlds"


def world(name: str) -> tuple[str, str]:
    """(nội dung world.md, tên nhân vật của card)."""
    text = (WORLDS / name / "world.md").read_text(encoding="utf-8")
    char = json.loads((WORLDS / name / "card.json").read_text(encoding="utf-8"))["data"]["name"]
    return text, char


# (số mục, theo loại, known_by của Mục lore, bỏ vì trùng) — §4.5
EXPECTED = {
    "co-hoai-da": (26, {"lore": 14, "character": 6, "place": 6}, {"*": 5, "{{char}}": 8, "{{user}}": 1}, ["Lục Tri Hành"]),
    "luc-bac-uyen": (27, {"lore": 14, "character": 7, "place": 6}, {"{{user}}": 6, "*": 6, "{{char}}": 2}, []),
    "tan-duong": (27, {"lore": 14, "character": 7, "place": 6}, {"*": 5, "{{char}}": 9}, []),
    "yen-hoanh-sinh": (
        25,
        {"lore": 14, "character": 7, "place": 4},
        {"*": 9, "{{char}}": 4, "{{user}}": 1},
        ["Hoàn Viên trạch", "Kim Thanh hí viện"],
    ),
}


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_real_worlds_entry_counts_and_known_by(name: str) -> None:
    text, char = world(name)
    res = parse_world_md(text, char)
    total, cats, known, dups = EXPECTED[name]
    assert len(res.entries) == total
    assert dict(Counter(e.category for e in res.entries)) == cats
    assert dict(Counter(",".join(e.known_by) for e in res.entries if e.category == "lore")) == known
    assert res.skipped_duplicates == dups
    # Slug ổn định, không trùng, đúng tiền tố.
    slugs = [e.slug for e in res.entries]
    assert len(set(slugs)) == len(slugs)
    assert all(s.startswith(f"md:{e.category}/") for s, e in zip(slugs, res.entries, strict=True))
    assert parse_world_md(text, char).entries == res.entries  # tất định


def test_real_worlds_total_is_105() -> None:
    assert sum(len(parse_world_md(*world(n)).entries) for n in EXPECTED) == 105


def test_known_by_without_char_name_keeps_raw_names() -> None:
    text, _ = world("co-hoai-da")
    res = parse_world_md(text)
    known = Counter(",".join(e.known_by) for e in res.entries if e.category == "lore")
    assert known == {"*": 5, "Cố Hoài Dã": 8, "{{user}}": 1}


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_secret_and_function_lines_never_imported(name: str) -> None:
    res = parse_world_md(*world(name))
    for e in res.entries:
        if e.category == "lore":
            continue
        for line in e.content.split("\n"):
            bare = line.lstrip("-* ").casefold()
            assert not bare.startswith("bí mật") and not bare.startswith("chức năng"), (e.title, line)
            assert "**" not in line
    assert any("Bí mật và Chức năng" in n for n in res.notes)


def test_both_field_styles_and_bold_paragraph_heads() -> None:
    # luc-bac-uyen: `- **keys:**`, `### Tên (中文)`; tan-duong: `- keys:` và đoạn `**Tên (中文)**, 52 tuổi.`
    luc = {e.title: e for e in parse_world_md(*world("luc-bac-uyen")).entries}
    assert luc["Hôn ước Lục - Ôn"].keys[:2] == ["hôn ước", "đính hôn"]
    assert luc["Hôn ước Lục - Ôn"].content.startswith("Năm 1979")
    assert luc["Câu nói đêm mưa"].known_by == ["{{char}}"]
    tan = {e.title: e for e in parse_world_md(*world("tan-duong")).entries}
    assert tan["Thẩm Kính Ngôn"].content.startswith("52 tuổi. Giám đốc kỹ thuật")
    assert "Thiên La" not in tan["Thẩm Kính Ngôn"].content  # dòng "Bí mật" đã bị bỏ
    assert tan["Phòng 402, nhà A3, Học viện Công nghệ thông tin"].content.startswith("Phòng học bậc thang")
    assert tan["ZERO"].keys[0] == "ZERO"


@pytest.mark.parametrize(
    ("name", "title", "keys"),
    [
        ("co-hoai-da", "Hạ Trì", ["Hạ Trì", "夏驰"]),
        ("tan-duong", "Thẩm Kính Ngôn", ["Thẩm Kính Ngôn", "沈敬言", "Kính Ngôn"]),
        ("luc-bac-uyen", "Lục trạch trên núi Vân Lộc", ["Lục trạch trên núi Vân Lộc", "Lục trạch", "núi Vân Lộc", "Vân Lộc"]),
        (
            "luc-bac-uyen",
            "Tiệm hoa Thu Đường và bệnh viện Nhân Hòa",
            ["Tiệm hoa Thu Đường và bệnh viện Nhân Hòa", "Tiệm hoa Thu Đường", "bệnh viện Nhân Hòa", "Thu Đường", "Nhân Hòa"],
        ),
        (
            "tan-duong",
            "Căn hộ 1701, chung cư Ngô Đồng",
            ["Căn hộ 1701, chung cư Ngô Đồng", "梧桐公寓", "Căn hộ 1701", "chung cư Ngô Đồng", "Ngô Đồng"],
        ),
        ("luc-bac-uyen", "Tầng 68 tòa nhà Lục thị", ["Tầng 68 tòa nhà Lục thị"]),
        ("yen-hoanh-sinh", "Lương ma ma", ["Lương ma ma", "梁秀琴", "Lương Tú Cầm"]),
        ("co-hoai-da", "Căn hộ Lâm Giang Uyển, tầng 17", ["Căn hộ Lâm Giang Uyển, tầng 17", "临江苑", "Căn hộ Lâm Giang Uyển", "Lâm Giang Uyển"]),
    ],
)
def test_generated_keys(name: str, title: str, keys: list[str]) -> None:
    entries = {e.title: e for e in parse_world_md(*world(name)).entries}
    assert entries[title].keys == keys


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_never_generates_single_syllable_keys(name: str) -> None:
    for e in parse_world_md(*world(name)).entries:
        if e.category == "lore":
            continue
        for key in e.keys:
            assert len(key.split()) >= 2 or any("一" <= c <= "鿿" for c in key), (e.title, key)
        assert "ma ma" not in [k.casefold() for k in e.keys]


def test_heading_keys_rules() -> None:
    assert heading_keys("Cố Diễn Chi (顾衍之)", "character") == ("Cố Diễn Chi", ["Cố Diễn Chi", "顾衍之", "Diễn Chi"])
    # Nơi chốn 3 âm tiết không có tên tắt; "chợ hoa đêm" viết thường bị bỏ.
    assert heading_keys("Phố Hoa Lăng và chợ hoa đêm", "place") == ("Phố Hoa Lăng và chợ hoa đêm", ["Phố Hoa Lăng và chợ hoa đêm", "Phố Hoa Lăng"])
    assert heading_keys("**Nghĩa trang Vọng Hải (望海).**", "place") == ("Nghĩa trang Vọng Hải", ["Nghĩa trang Vọng Hải", "望海", "Vọng Hải"])
    assert heading_keys("ZERO", "character") == ("ZERO", [])  # không bao giờ tự sinh khoá một âm tiết


def test_leak_filter_on_luc_bac_uyen() -> None:
    res = parse_world_md(*world("luc-bac-uyen"))
    by = {e.title: e for e in res.entries}
    assert res.player_only == ["Hứa Tri Ý", "Phó Cảnh Hành", "Tô Mạn Ninh", "Tiệm hoa Thu Đường và bệnh viện Nhân Hòa"]
    for title in res.player_only:
        assert by[title].known_by == ["{{user}}"]
    assert len(res.dropped_sentences) == 4
    dropped = " | ".join(res.dropped_sentences)
    assert dropped.count("nguyên chủ") == 2 and "hồ cá koi" in dropped and "mười bảy tháng ba" in dropped
    assert "Bỏ 4 câu nhắc tới điều chỉ bạn biết." in res.notes
    assert by["Lục trạch trên núi Vân Lộc"].content.startswith("Biệt thự kiểu cũ ba tầng")
    assert "Lục Chấn Đình" in by and by["Lục Chấn Đình"].known_by == ["*"]


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_no_everyone_person_or_place_leaks_player_only_terms(name: str) -> None:
    res = parse_world_md(*world(name))
    user_keys = [k for e in res.entries if e.category == "lore" and e.known_by == ["{{user}}"] for k in e.keys]
    matcher = LoreMatcher([(0, [*META_SPOILER_TERMS, *user_keys])], ignore=[world(name)[1]])
    for e in res.entries:
        if e.category == "lore" or e.known_by == ["{{user}}"]:
            continue
        assert not matcher.scan(e.content), (e.title, matcher.scan(e.content))
    if name != "luc-bac-uyen":
        assert res.player_only == [] and res.dropped_sentences == []


def test_slugify() -> None:
    assert slugify("Hôn ước Lục - Ôn") == "hon-uoc-luc-on"
    assert slugify("Đường Nhiễm") == "duong-nhiem"
    cjk = slugify("陆知行")
    assert cjk.startswith("h") and len(cjk) == 11 and cjk != slugify("夏驰")


def test_duplicate_titles_get_suffix_and_missing_known_by_warns() -> None:
    text = """# T

## Mục lore

### Hạ Trì
- keys: Hạ Trì
- content: Một.

### Hạ Trì
- keys: Hạ Trì
- known_by: Hoài Dã
- content: Hai dòng.
  Dòng tiếp theo của nội dung.

### Không khoá
- known_by: *
- content: Ba.
"""
    res = parse_world_md(text, "Cố Hoài Dã")
    assert [e.slug for e in res.entries] == ["md:lore/ha-tri", "md:lore/ha-tri-2", "md:lore/khong-khoa"]
    assert res.entries[0].known_by == ["*"]
    assert res.entries[1].known_by == ["Hoài Dã"]  # tên lệch: giữ nguyên chữ, kèm cảnh báo
    assert res.entries[1].content == "Hai dòng.\nDòng tiếp theo của nội dung."
    assert any("chưa ghi ai biết" in w for w in res.warnings)
    assert any("chỉ Hoài Dã biết" in w and "Cố Hoài Dã sẽ không dùng" in w for w in res.warnings)
    assert any("Không khoá" in w and "chưa có từ khoá" in w for w in res.warnings)


def test_file_without_known_sections_has_no_entries() -> None:
    assert parse_world_md("# Tiêu đề\n\n## Thế giới\n\n### Hoa Lăng\nThành phố.\n").entries == []
    assert parse_world_md("").entries == []


def test_key_warnings() -> None:
    assert key_warnings(["mẹ"]) == ["Từ khoá “mẹ” chỉ có một chữ nên sẽ gợi rất thường xuyên."]
    assert key_warnings(["nhẫn"]) == ["Từ khoá “nhẫn” chỉ có một chữ, cũng khớp trong những từ như “kiên nhẫn”."]
    assert key_warnings(["GHOST", "London", "hôn ước", "夏"]) == []
    assert key_warnings(["Lục Bắc Uyên"], "Lục Bắc Uyên") == ["Từ khoá “Lục Bắc Uyên” là tên nhân vật nên không dùng để gợi nhớ."]


# ---- Bản sửa sau review: dòng "Bí mật" không bao giờ lọt vào mục mọi người biết


SECRET = "em gái anh ta mổ tim"


def _people(text: str, char: str = "Lục Bắc Uyên"):
    res = parse_world_md(text, char)
    return res, [e for e in res.entries if e.category == "character"]


def test_bold_labels_inside_heading_entry_are_body_and_secret_is_dropped() -> None:
    text = """## Nhân vật xung quanh

### Trình Dịch (程奕)
Trợ lý thân cận của Lục Bắc Uyên.
**Tính cách:** điềm tĩnh, ít nói.
**Bí mật:** em gái anh ta mổ tim, Lục Bắc Uyên trả tiền.
**Chức năng:** đưa tin.
**Xưng hô**: gọi Lục Bắc Uyên là sếp.
"""
    res, people = _people(text)
    assert [e.title for e in res.entries] == ["Trình Dịch"]
    content = people[0].content
    assert "Trợ lý thân cận" in content
    assert "Tính cách: điềm tĩnh, ít nói." in content
    assert "Xưng hô: gọi Lục Bắc Uyên là sếp." in content
    assert SECRET not in content and "đưa tin" not in content
    assert any("Không nhập phần Bí mật" in n for n in res.notes)


def test_bold_label_secret_in_bold_head_style_is_not_an_entry() -> None:
    text = """## Nhân vật xung quanh

**Trình Dịch (程奕)**, 30 tuổi. Trợ lý.
**Bí mật:** em gái anh ta mổ tim.
**Tính cách:** điềm tĩnh.

**Hạ Trì (夏驰)**, 28 tuổi. Bạn cũ.
"""
    res, people = _people(text)
    assert [e.title for e in people] == ["Trình Dịch", "Hạ Trì"]
    assert all(SECRET not in e.content for e in res.entries)
    assert "Tính cách: điềm tĩnh." in people[0].content


def test_label_style_heads_still_start_new_people() -> None:
    text = """## Nhân vật xung quanh

**Trình Dịch:** trợ lý thân cận.
**Hạ Trì:** bạn cũ.
"""
    _, people = _people(text)
    assert [(e.title, e.content) for e in people] == [("Trình Dịch", "trợ lý thân cận."), ("Hạ Trì", "bạn cũ.")]


def test_secret_with_nested_bullets_is_dropped_whole() -> None:
    text = """## Nhân vật xung quanh

### Trình Dịch (程奕)
- Tính cách: điềm tĩnh.
- Bí mật:
  - em gái anh ta mổ tim, Lục Bắc Uyên trả tiền.
  - anh ta báo cáo cho lão gia.

    tiếp tục ý trên.
- Xưng hô: gọi sếp.
"""
    _, people = _people(text)
    assert people[0].content == "- Tính cách: điềm tĩnh.\n\n- Xưng hô: gọi sếp."


def test_secret_level4_heading_drops_until_next_heading() -> None:
    text = """## Nhân vật xung quanh

### Trình Dịch (程奕)
Tính cách điềm tĩnh.

#### Bí mật

Em gái anh ta mổ tim, Lục Bắc Uyên trả tiền.

- anh ta báo cáo cho lão gia.

##### Chi tiết
Viện phí do Lục Bắc Uyên trả.

#### Xưng hô
Gọi sếp.
"""
    res, people = _people(text)
    content = people[0].content
    assert "Tính cách điềm tĩnh." in content and "#### Xưng hô\nGọi sếp." in content
    assert "mổ tim" not in content and "báo cáo" not in content and "Viện phí" not in content
    assert "Bí mật" not in content
    assert any("Không nhập phần Bí mật" in n for n in res.notes)


def test_standalone_secret_label_drops_its_list_but_keeps_next_paragraph() -> None:
    text = """## Nhân vật xung quanh

### Trình Dịch (程奕)
Trợ lý.
**Bí mật:**
- em gái anh ta mổ tim.
- anh ta báo cáo cho lão gia.

Luôn mặc vest xám.
"""
    _, people = _people(text)
    assert people[0].content == "Trợ lý.\n\nLuôn mặc vest xám."
