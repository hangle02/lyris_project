from __future__ import annotations

import pytest

from lyris.db.repo import ANY_ACCOUNT, NotFound, Repo
from lyris.models import (
    AddressTerms,
    CharacterCard,
    Gender,
    NarrationPronouns,
    Persona,
    StorySettings,
    StyleProfileInfo,
)
from lyris.prompt import builder
from lyris.seed import load_seed_card, load_seed_persona
from lyris.studio import stories
from lyris.studio.stories import (
    create_story_for,
    default_settings,
    default_title,
    fill_placeholders,
    insert_greeting,
)

GREETING = (
    "{{char}} ngẩng lên khi thấy {{user}} bước vào.\n"
    "[Thought: {{user}} lại đến muộn.]\n"
    '"Ngồi đi."'
)


def make_card(**overrides: object) -> CharacterCard:
    data: dict[str, object] = {
        "name": "Trần Minh Khang",
        "gender": "male",
        "style_profile": "trung_hien_dai",
        "address_terms": AddressTerms(self_term="anh", player_term="em"),
        "greeting": GREETING,
        "alternate_greetings": ["Mưa rơi. {{user}} đứng dưới hiên.", "   "],
        "scenario": "Sài Gòn. {{char}} và {{user}} là đồng nghiệp.",
    }
    data.update(overrides)
    return CharacterCard.model_validate(data)


def make_persona(**overrides: object) -> Persona:
    data: dict[str, object] = {"name": "Ngọc Anh", "gender": "female"}
    data.update(overrides)
    return Persona.model_validate(data)


@pytest.fixture
def no_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    """Giả lập [styles] chưa có get_style_profile: dùng mặc định có sẵn."""
    monkeypatch.delattr(builder, "get_style_profile", raising=False)


@pytest.fixture
def profile(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """get_style_profile giả; trả dict để test xem tên profile được hỏi."""
    asked: dict[str, str] = {}

    def fake(name: str) -> StyleProfileInfo:
        asked["name"] = name
        if name == "trung_co_dai":
            return StyleProfileInfo(
                name=name,
                title="Cổ trang",
                narration={"vi": {"male": "hắn", "female": "nàng", "other": ""}, "en": {"male": "he"}},
            )
        raise ValueError(f"Không tìm thấy style profile {name}")

    monkeypatch.setattr(builder, "get_style_profile", fake, raising=False)
    return asked


# ---------------------------------------------------------------- default_settings


@pytest.mark.parametrize(
    ("card_gender", "persona_gender", "expected"),
    [
        ("male", "female", "het"),
        ("female", "male", "het"),
        ("male", "male", "bl"),
        ("female", "female", "gl"),
        ("other", "female", "none"),
        ("male", "other", "none"),
        ("other", "other", "none"),
    ],
)
def test_relationship_type(no_profile: None, card_gender: Gender, persona_gender: Gender, expected: str) -> None:
    s = default_settings(make_card(gender=card_gender), make_persona(gender=persona_gender))
    assert s.relationship_type == expected


def test_defaults_without_profile(no_profile: None) -> None:
    s = default_settings(make_card(), make_persona())
    assert s == StorySettings(
        scenario="Sài Gòn. Trần Minh Khang và Ngọc Anh là đồng nghiệp.",
        language="vi",
        mode="story",
        relationship_type="het",
        pov="third",
        thought_style="inline",
        narration_pronouns=NarrationPronouns(character="anh", player="cô"),
    )
    other = default_settings(make_card(gender="other"), make_persona(gender="other", name=" Tiểu Bạch "))
    assert other.narration_pronouns == NarrationPronouns(character="Trần Minh Khang", player="Tiểu Bạch")


def test_language_param_overrides_card(no_profile: None) -> None:
    card = make_card(language="vi")
    en = default_settings(card, make_persona(), language="en")
    assert en.language == "en"
    assert en.narration_pronouns == NarrationPronouns(character="he", player="she")
    they = default_settings(make_card(language="en", gender="other"), make_persona(gender="other"))
    assert they.language == "en"
    assert they.narration_pronouns == NarrationPronouns(character="they", player="they")


def test_narration_from_style_profile(profile: dict[str, str]) -> None:
    card = make_card(style_profile="trung_co_dai", name="Tạ Vân Lan", gender="female")
    s = default_settings(card, make_persona(name="Lục Trần", gender="male"))
    assert profile["name"] == "trung_co_dai"
    assert s.narration_pronouns == NarrationPronouns(character="nàng", player="hắn")
    # Profile để trống "other" -> tên; thiếu en.female -> mặc định "she".
    s2 = default_settings(card.model_copy(update={"gender": "other"}), make_persona(gender="female"), "vi")
    assert s2.narration_pronouns == NarrationPronouns(character="Tạ Vân Lan", player="nàng")
    s3 = default_settings(card, make_persona(gender="male"), "en")
    assert s3.narration_pronouns == NarrationPronouns(character="she", player="he")


def test_unknown_profile_falls_back(profile: dict[str, str]) -> None:
    s = default_settings(make_card(style_profile="khong_co"), make_persona())
    assert profile["name"] == "khong_co"
    assert s.narration_pronouns == NarrationPronouns(character="anh", player="cô")


def test_real_profile_seed_pair() -> None:
    """Với builder thật (nếu [styles] đã có frontmatter) seed vẫn ra anh/cô như Phase 1."""
    s = default_settings(load_seed_card(), load_seed_persona())
    assert s.narration_pronouns == NarrationPronouns(character="anh", player="cô")
    assert s.relationship_type == "het" and s.language == "vi"


def test_default_title_and_fill() -> None:
    assert default_title(make_card(name=" Lạc Dương "), make_persona(name="Lâm Vãn")) == "Lạc Dương & Lâm Vãn"
    assert fill_placeholders("{{ Char }} gọi {{USER}}.", make_card(), make_persona()) == "Trần Minh Khang gọi Ngọc Anh."


# ---------------------------------------------------------------- create_story_for


def setup_pair(repo: Repo, **card_overrides: object) -> tuple[int, int]:
    card = repo.create_card(make_card(**card_overrides), account_id=repo.owner_id())
    persona = repo.create_persona(make_persona(), account_id=repo.owner_id())
    assert card.id is not None and persona.id is not None
    return card.id, persona.id


def test_create_story_with_defaults(repo: Repo, no_profile: None) -> None:
    card_id, persona_id = setup_pair(repo)
    story = create_story_for(repo, card_id, persona_id, model_name="gemma4:e4b", account_id=repo.owner_id())
    assert story.id is not None
    assert story.title == "Trần Minh Khang & Ngọc Anh"
    assert story.model_name == "gemma4:e4b"
    assert story.scenario == "Sài Gòn. Trần Minh Khang và Ngọc Anh là đồng nghiệp."
    assert story.relationship_type == "het" and story.mode == "story" and story.thought_style == "inline"
    assert story.narration_pronouns == NarrationPronouns(character="anh", player="cô")

    msgs = repo.active_messages(story.id)
    assert len(msgs) == 1
    g = msgs[0]
    assert g.turn_index == 0 and g.role == "assistant" and g.mode == "story" and g.model_output is None
    assert "{{" not in g.raw_content
    assert g.raw_content.startswith("Trần Minh Khang ngẩng lên khi thấy Ngọc Anh")
    assert g.thought == "Ngọc Anh lại đến muộn."
    assert "[Thought" not in g.visible_content and g.visible_content.endswith('"Ngồi đi."')


def test_create_story_alternate_and_no_greeting(repo: Repo, no_profile: None) -> None:
    card_id, persona_id = setup_pair(repo)
    alt = create_story_for(repo, card_id, persona_id, greeting_index=1, title="  Mưa  ", model_name="m", account_id=repo.owner_id())
    assert alt.title == "Mưa"
    [msg] = repo.active_messages(alt.id or 0)
    assert msg.raw_content == "Mưa rơi. Ngọc Anh đứng dưới hiên." and msg.thought is None

    blank = create_story_for(repo, card_id, persona_id, greeting_index=2, model_name="m", account_id=repo.owner_id())
    assert repo.active_messages(blank.id or 0) == []
    none = create_story_for(repo, card_id, persona_id, greeting_index=-1, title="   ", model_name="m", account_id=repo.owner_id())
    assert none.title == "Trần Minh Khang & Ngọc Anh"
    assert repo.active_messages(none.id or 0) == []


def test_create_story_bad_greeting_index_creates_nothing(repo: Repo) -> None:
    card_id, persona_id = setup_pair(repo)
    for bad in (3, -2, 99):
        with pytest.raises(ValueError, match="lời mở đầu"):
            create_story_for(repo, card_id, persona_id, greeting_index=bad, model_name="m", account_id=repo.owner_id())
    assert repo.list_stories(account_id=ANY_ACCOUNT) == []
    assert not repo.conn.in_transaction


def test_create_story_missing_card_or_persona(repo: Repo) -> None:
    card_id, persona_id = setup_pair(repo)
    with pytest.raises(NotFound):
        create_story_for(repo, 999, persona_id, model_name="m", account_id=repo.owner_id())
    with pytest.raises(NotFound):
        create_story_for(repo, card_id, 999, model_name="m", account_id=repo.owner_id())
    assert repo.list_stories(account_id=ANY_ACCOUNT) == []


def test_create_story_with_given_settings_dm(repo: Repo) -> None:
    card_id, persona_id = setup_pair(repo)
    settings = StorySettings(
        scenario="Bối cảnh riêng",
        language="en",
        mode="dm",
        relationship_type="none",
        pov="first",
        thought_style="end",
        narration_pronouns=NarrationPronouns(character="he", player="you"),
    )
    story = create_story_for(repo, card_id, persona_id, settings=settings, model_name="m", account_id=repo.owner_id())
    got = repo.get_story(story.id or 0, account_id=ANY_ACCOUNT)
    assert (got.scenario, got.language, got.mode, got.relationship_type, got.pov, got.thought_style) == (
        "Bối cảnh riêng",
        "en",
        "dm",
        "none",
        "first",
        "end",
    )
    assert got.narration_pronouns == NarrationPronouns(character="he", player="you")
    [greeting] = repo.active_messages(story.id or 0)
    assert greeting.mode == "dm"


def test_create_story_calls_style_profile(repo: Repo, profile: dict[str, str]) -> None:
    card_id, persona_id = setup_pair(repo, style_profile="trung_co_dai")
    story = create_story_for(repo, card_id, persona_id, model_name="m", account_id=repo.owner_id())
    assert profile["name"] == "trung_co_dai"
    assert story.narration_pronouns == NarrationPronouns(character="hắn", player="nàng")


def test_insert_greeting(repo: Repo) -> None:
    card_id, persona_id = setup_pair(repo)
    story = create_story_for(repo, card_id, persona_id, greeting_index=-1, model_name="m", account_id=repo.owner_id())
    assert insert_greeting(repo, story, "") is None
    assert insert_greeting(repo, story, "  \n ") is None
    raw = "  Anh cười.\n[Thought: Vui.]\n"
    msg = insert_greeting(repo, story, raw)
    assert msg is not None
    assert msg.raw_content == raw  # giữ nguyên văn
    assert msg.turn_index == 0 and msg.thought == "Vui." and msg.visible_content == "Anh cười."
    with pytest.raises(ValueError):
        insert_greeting(repo, story, "Lần hai")  # lượt 0 đã có


def test_module_exports() -> None:
    assert set(stories.__all__) >= {"create_story_for", "default_settings", "default_title", "insert_greeting"}


def test_card_narration_pronoun_overrides_style_default() -> None:
    from lyris.models import AddressTerms, CharacterCard, Persona
    from lyris.studio.stories import default_settings

    card = CharacterCard(
        name="Lục Bắc Uyên", gender="male", style_profile="trung_hien_dai",
        address_terms=AddressTerms(self_term="tôi", player_term="em"),
        extensions={"lyris": {"narration_character": "hắn"}},
    )
    persona = Persona(name="Ôn Dĩ", gender="female")
    assert default_settings(card, persona).narration_pronouns.character == "hắn"
    # Tiếng Anh: chuỗi đơn chỉ áp cho tiếng Việt, nên dùng mặc định của style.
    assert default_settings(card, persona, "en").narration_pronouns.character == "he"
    both = card.model_copy(update={"extensions": {"lyris": {"narration_character": {"vi": "y", "en": "he"}}}})
    assert default_settings(both, persona).narration_pronouns.character == "y"
    plain = card.model_copy(update={"extensions": {}})
    assert default_settings(plain, persona).narration_pronouns.character == "anh"
