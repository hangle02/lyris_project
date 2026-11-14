"""Test style profile: frontmatter, list/get, load_style bỏ frontmatter. Không cần Ollama."""
from __future__ import annotations

from pathlib import Path

import pytest

from lyris.models import StyleProfileInfo
from lyris.prompt import builder
from lyris.prompt.builder import available_styles, get_style_profile, list_style_profiles, load_style

EXPECTED = ["chung", "trung_co_dai", "trung_dan_quoc", "trung_hien_dai", "viet_hien_dai"]
NARRATION_VI = {
    "chung": ("anh", "cô"),
    "trung_co_dai": ("hắn", "nàng"),
    "trung_dan_quoc": ("hắn", "cô"),
    "trung_hien_dai": ("anh", "cô"),
    "viet_hien_dai": ("anh", "cô"),
}


def test_list_has_all_profiles_sorted() -> None:
    profiles = list_style_profiles()
    names = [p.name for p in profiles]
    assert names == sorted(names)
    assert set(EXPECTED) <= set(names)
    assert all(isinstance(p, StyleProfileInfo) for p in profiles)


@pytest.mark.parametrize("name", EXPECTED)
def test_profile_frontmatter_parses(name: str) -> None:
    info = get_style_profile(name)
    assert info.name == name
    assert info.title and info.title != name
    assert info.description
    male_vi, female_vi = NARRATION_VI[name]
    assert info.narration["vi"]["male"] == male_vi
    assert info.narration["vi"]["female"] == female_vi
    assert info.narration["en"]["male"] == "he"
    assert info.narration["en"]["female"] == "she"
    assert len(info.address_examples) >= 3
    for example in info.address_examples:
        assert example["self"] and example["player"] and example.get("note")
        assert all(isinstance(v, str) for v in example.values())


@pytest.mark.parametrize("name", EXPECTED)
def test_profile_has_vi_and_en_sections(name: str) -> None:
    raw = (builder.STYLES_DIR / f"{name}.md").read_text(encoding="utf-8")
    assert "\n# vi\n" in raw and "\n# en\n" in raw
    vi = load_style(name, "vi")
    en = load_style(name, "en")
    assert vi != en
    assert vi.startswith("Bối cảnh và văn phong")
    assert en.startswith("Setting and style")
    for text in (vi, en):
        bullets = [line for line in text.splitlines() if line.startswith("- ")]
        samples = [line for line in text.splitlines() if line.startswith("  - ")]
        assert len(bullets) >= 6
        assert 3 <= len(samples) <= 4


@pytest.mark.parametrize("name", EXPECTED)
@pytest.mark.parametrize("language", ["vi", "en"])
def test_frontmatter_never_reaches_prompt(name: str, language: str) -> None:
    text = load_style(name, language)  # type: ignore[arg-type]
    assert not text.startswith("---")
    for marker in ("title:", "description:", "narration:", "address_examples:", "<!--", "-->", "# vi", "# en"):
        assert marker not in text


def test_trung_hien_dai_body_unchanged() -> None:
    vi = load_style("trung_hien_dai")
    assert vi.startswith("Bối cảnh và văn phong: Trung Quốc hiện đại.")
    assert vi.endswith("mùi hoành thánh nóng hòa với mùi trà sữa khoai môn.")
    en = load_style("trung_hien_dai", "en")
    assert en.startswith("Setting and style: modern China.")
    assert en.endswith("the smell of hot wontons mixing with taro milk tea.")


def test_profile_content_matches_setting() -> None:
    co_dai = load_style("trung_co_dai")
    assert all(w in co_dai for w in ("ngươi", "sư tôn", "đồ nhi", "tại hạ", "thần thiếp", "bổn vương"))
    viet = load_style("viet_hien_dai")
    assert all(w in viet for w in ("xe máy", "phở", "Zalo", "tao/mày"))
    # Cụm văn dịch Trung chỉ xuất hiện trong mục "Tránh".
    avoid = next(line for line in viet.splitlines() if line.startswith("- Tránh"))
    assert "khóe môi khẽ cong" in avoid and "đáy mắt" in avoid
    assert viet.count("khóe môi khẽ cong") == 1
    chung = load_style("chung")
    assert "Trung Quốc hiện đại" not in chung and "Việt Nam hiện đại" not in chung


@pytest.mark.parametrize("name", ["khong_co", "../secrets", "", "a b", "trung hien dai"])
def test_unknown_or_invalid_name_raises(name: str) -> None:
    with pytest.raises(ValueError):
        get_style_profile(name)
    with pytest.raises(ValueError):
        load_style(name)


def test_available_styles_matches_list() -> None:
    assert available_styles() == [p.name for p in list_style_profiles()]


# ---- file tạm: frontmatter thiếu, hỏng, giá trị lạ --------------------------------------


@pytest.fixture
def styles_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(builder, "STYLES_DIR", tmp_path)
    return tmp_path


def test_file_without_frontmatter(styles_dir: Path) -> None:
    (styles_dir / "tho.md").write_text("# vi\nThân tiếng Việt\n# en\nEnglish body\n", encoding="utf-8")
    info = get_style_profile("tho")
    assert info == StyleProfileInfo(name="tho", title="tho")
    assert load_style("tho") == "Thân tiếng Việt"
    assert load_style("tho", "en") == "English body"


def test_frontmatter_stripped_and_parsed(styles_dir: Path) -> None:
    (styles_dir / "moi.md").write_text(
        "---\n"
        "title: Mới\n"
        "description: Mô tả\n"
        "narration:\n"
        "  vi: {male: anh, female: cô, other: ''}\n"
        "address_examples:\n"
        "  - {self: tớ, player: cậu, note: bạn thân}\n"
        "  - {self: yes, player: 1, note: null}\n"
        "---\n"
        "Thân không chia mục\n",
        encoding="utf-8",
    )
    info = get_style_profile("moi")
    assert info.title == "Mới" and info.description == "Mô tả"
    assert info.narration == {"vi": {"male": "anh", "female": "cô", "other": ""}}
    assert info.address_examples[0] == {"self": "tớ", "player": "cậu", "note": "bạn thân"}
    # YAML 1.1 đổi "yes" thành bool, 1 thành int: vẫn trả chuỗi; null bị bỏ.
    assert info.address_examples[1] == {"self": "true", "player": "1"}
    assert load_style("moi") == "Thân không chia mục"
    assert load_style("moi", "en") == "Thân không chia mục"


def test_empty_frontmatter_and_bom(styles_dir: Path) -> None:
    (styles_dir / "rong.md").write_text("﻿---\n---\nThân\n", encoding="utf-8")
    assert get_style_profile("rong").title == "rong"
    assert load_style("rong") == "Thân"


def test_dashes_later_in_body_are_not_frontmatter(styles_dir: Path) -> None:
    (styles_dir / "gach.md").write_text("Dòng đầu\n---\ntitle: không phải frontmatter\n---\n", encoding="utf-8")
    assert get_style_profile("gach").title == "gach"
    assert "title: không phải frontmatter" in load_style("gach")


@pytest.mark.parametrize(
    "frontmatter",
    [
        "title: [chưa đóng\n",  # YAML hỏng
        "- danh sách\n- không phải bảng\n",
        "title: X\nnarration: chuỗi\n",
        "title: X\nnarration:\n  vi: anh\n",
        "title: X\naddress_examples: chuỗi\n",
        "title: X\naddress_examples:\n  - chuỗi\n",
    ],
)
def test_malformed_frontmatter_raises(styles_dir: Path, frontmatter: str) -> None:
    (styles_dir / "hong.md").write_text(f"---\n{frontmatter}---\nThân\n", encoding="utf-8")
    with pytest.raises(ValueError):
        get_style_profile("hong")
