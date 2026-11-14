"""Test AI viết nháp (lyris.studio.draft) bằng FakeLLM: prompt, schema, options, hậu xử lý, cảnh báo."""
from __future__ import annotations

import copy
from typing import Any

import pytest

from lyris.llm.base import LLMError
from lyris.llm.fake import FakeLLM
from lyris.models import StyleProfileInfo
from lyris.studio.draft import (
    DRAFT_OPTIONS,
    DRAFT_SCHEMA,
    FIELD_MAX_CHARS,
    DraftError,
    build_draft_messages,
    draft_card,
    draft_schema,
    fix_thoughts,
    normalize_term,
    postprocess_draft,
)

STYLES = [
    StyleProfileInfo(
        name="chung",
        title="Trung tính",
        description="Theo bối cảnh của card.",
        narration={"vi": {"male": "anh", "female": "cô", "other": ""}, "en": {"male": "he", "female": "she", "other": "they"}},
    ),
    StyleProfileInfo(
        name="trung_co_dai",
        title="Cổ trang Trung Quốc",
        description="Tiên hiệp, cung đấu; ta/ngươi.",
        narration={"vi": {"male": "hắn", "female": "nàng", "other": ""}, "en": {"male": "he", "female": "she", "other": "they"}},
        address_examples=[
            {"self": "ta", "player": "ngươi", "note": "người lạ"},
            {"self": "sư tỷ", "player": "sư đệ", "note": "đồng môn"},
        ],
    ),
    StyleProfileInfo(
        name="trung_hien_dai",
        title="Ngôn tình Trung Quốc hiện đại",
        description="Vườn trường, đô thị.",
        narration={"vi": {"male": "anh", "female": "cô", "other": ""}, "en": {"male": "he", "female": "she", "other": "they"}},
        address_examples=[{"self": "tớ", "player": "cậu", "note": "bạn thân"}],
    ),
    StyleProfileInfo(
        name="viet_hien_dai",
        title="Việt Nam hiện đại",
        description="Sài Gòn, Hà Nội; anh/em.",
        narration={"vi": {"male": "anh", "female": "cô", "other": ""}, "en": {"male": "he", "female": "she", "other": "they"}},
    ),
]
STYLE_NAMES = [s.name for s in STYLES]

GOOD_GREETING = (
    "Tuyết đầu mùa phủ trắng bậc đá trước Tàng Kinh Các của Thanh Vân Tông. Tạ Vân Lan đứng dưới mái hiên, "
    "tay áo trắng khẽ lay theo gió, ánh mắt dừng trên bóng người đang quét tuyết dưới sân.\n\n"
    "{{user}} cúi đầu, chổi tre cào trên nền đá kêu sột soạt, chóp mũi đã đỏ lên vì lạnh.\n\n"
    "[Thought: Lại là đệ ấy. Trưởng lão phạt quét sân ba ngày, vậy mà đệ ấy chẳng than lấy một câu.]\n\n"
    "Nàng bước xuống từng bậc đá, tiếng giày giẫm lên tuyết nghe rất khẽ. Vài đệ tử ngoại môn đi ngang qua, "
    "vội vàng cúi chào rồi lảng đi chỗ khác.\n\n"
    "Tạ Vân Lan dừng lại cách {{user}} ba bước, rút từ trong tay áo ra một bình sứ nhỏ, đặt lên lan can đá. "
    "Hơi ấm từ bình thuốc bốc lên thành một làn khói mỏng.\n\n"
    "[Thought: Tay đệ ấy nứt nẻ cả rồi. Nếu mình không mang thuốc tới, chắc đệ ấy cũng chẳng biết tự lo.]\n\n"
    "Nàng khẽ hắng giọng, giọng vẫn lạnh nhạt như thường ngày: \"Thuốc trị nẻ. Bôi xong thì vào trong uống chén trà "
    "nóng. Ngươi định đứng đây chịu rét đến bao giờ?\""
)


def good_reply(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "name": "Tạ Vân Lan",
        "gender": "female",
        "style_profile": "trung_co_dai",
        "description": "Hai mươi hai tuổi, đại sư tỷ của Thanh Vân Tông, phụ trách dạy kiếm cho đệ tử mới, trong đó có {{user}}.",
        "personality": "Lạnh lùng, nghiêm khắc, ít khi cười. Bên ngoài khắt khe với {{user}} nhưng luôn âm thầm che chở.",
        "appearance": "Dáng cao gầy, luôn mặc bạch y, tóc búi gọn bằng một cây trâm ngọc.",
        "background": "Được sư tôn nhặt về từ chiến loạn khi lên năm. Mười năm khổ luyện, nay là kiếm tu mạnh nhất thế hệ trẻ.",
        "goals": "Muốn bảo vệ tông môn và giúp {{user}} trụ lại ở nội môn.",
        "secrets": "Từng thấy {{user}} trong một giấc mộng tiên tri từ nhiều năm trước.",
        "speech_style": "Nói ngắn, giọng nhạt; với {{user}} vẫn ngắn nhưng hay kèm một lời dặn dò.",
        "self_term": "ta",
        "player_term": "ngươi",
        "nicknames": ["tiểu sư đệ"],
        "others": "Với trưởng lão xưng đệ tử; với đệ tử khác xưng ta, gọi thẳng tên.",
        "scenario": "Mùa đông ở Thanh Vân Tông; {{user}} đang chịu phạt quét sân trước Tàng Kinh Các.",
        "greeting": GOOD_GREETING,
        "example_dialogues": '{{char}}: "Kiếm cầm chưa vững, đã muốn học chiêu mới?"\n{{char}}: "Đứng sau ta."',
        "tags": ["cổ trang", "tiên hiệp", "sư tỷ"],
    }
    data.update(overrides)
    return data


def post(data: dict[str, Any], *, language: str = "vi", gender: str | None = None, style: str | None = None):
    return postprocess_draft(
        data, language=language, gender=gender, style_profile=style, styles=STYLES, idea="sư tỷ lạnh lùng"
    )


# ---- schema ----------------------------------------------------------------------------------------


def test_schema_has_all_fields_required_in_order() -> None:
    props = list(DRAFT_SCHEMA["properties"])
    assert props == DRAFT_SCHEMA["required"]
    assert props[:3] == ["name", "gender", "style_profile"]
    assert props.index("self_term") < props.index("greeting")
    assert DRAFT_SCHEMA["properties"]["gender"]["enum"] == ["male", "female", "other"]
    assert DRAFT_SCHEMA["properties"]["nicknames"]["type"] == "array"
    assert DRAFT_SCHEMA["properties"]["tags"]["maxItems"] == 6
    assert "language" not in props
    assert DRAFT_SCHEMA["additionalProperties"] is False


def test_draft_schema_enums_and_forced_values() -> None:
    s = draft_schema(STYLE_NAMES)
    assert s["properties"]["style_profile"]["enum"] == STYLE_NAMES
    assert s["properties"]["gender"]["enum"] == ["male", "female", "other"]
    forced = draft_schema(STYLE_NAMES, gender="male", style_profile="viet_hien_dai")
    assert forced["properties"]["style_profile"]["enum"] == ["viet_hien_dai"]
    assert forced["properties"]["gender"]["enum"] == ["male"]
    # Không đụng vào hằng số gốc.
    assert "enum" not in DRAFT_SCHEMA["properties"]["style_profile"]
    assert draft_schema([])["properties"]["style_profile"]["enum"] == ["chung"]


# ---- prompt ----------------------------------------------------------------------------------------


def test_vi_prompt_contents() -> None:
    msgs = build_draft_messages(idea="sư tỷ lạnh lùng", language="vi", gender=None, style_profile=None, styles=STYLES)
    assert [m.role for m in msgs] == ["system", "user"]
    system, user = msgs[0].content, msgs[1].content
    for needle in [
        "{{user}}",
        "[Thought: ...]",
        "120-180 từ",
        "đúng 2 dòng",
        "bầu không khí",
        "ngôi thứ ba",
        "không dùng dấu \"/\"",
        "Hán Việt",
        "Không viết lời thoại, hành động có chủ đích",
        "Kết thúc ở chỗ {{user}} cần đáp lại",
        "\\n\\n",
    ]:
        assert needle in system, needle
    for name in STYLE_NAMES:
        assert f"- {name}: " in system
    assert 'Dẫn truyện: nam "hắn", nữ "nàng".' in system
    assert "Xưng hô gợi ý: ta/ngươi (người lạ); sư tỷ/sư đệ (đồng môn)." in system
    assert "Ý tưởng nhân vật: sư tỷ lạnh lùng" in user
    assert "Giới tính nhân vật" not in user and "Style profile:" not in user


def test_forced_values_in_prompt_and_only_forced_profile_listed() -> None:
    msgs = build_draft_messages(
        idea="kiến trúc sư", language="vi", gender="male", style_profile="viet_hien_dai", styles=STYLES
    )
    system, user = msgs[0].content, msgs[1].content
    assert '- Giới tính nhân vật: nam (gender = "male").' in user
    assert '- Style profile: viet_hien_dai (style_profile = "viet_hien_dai").' in user
    assert "- viet_hien_dai: " in system
    assert "- trung_co_dai: " not in system


def test_en_prompt_is_english() -> None:
    msgs = build_draft_messages(idea="a cold senior", language="en", gender="female", style_profile=None, styles=STYLES)
    system, user = msgs[0].content, msgs[1].content
    assert system.startswith("You are an editor")
    assert "120-180 words" in system and "[Thought: ...]" in system and "{{user}}" in system
    assert 'Narration pronouns: male "he", female "she".' in system
    assert "Xưng hô gợi ý" not in system
    assert "Character idea: a cold senior" in user
    assert '(gender = "female")' in user


# ---- draft_card ------------------------------------------------------------------------------------


async def test_draft_card_calls_llm_with_schema_and_options() -> None:
    fake = FakeLLM(json_replies=[good_reply()])
    card, warnings = await draft_card(
        fake, "gemma4:12b", idea="  sư tỷ lạnh lùng  ", language="vi", gender=None, style_profile=None, styles=STYLES
    )
    assert warnings == []
    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call["model"] == "gemma4:12b"
    assert call["options"] == {"temperature": 0.8, "num_predict": 2048, "num_ctx": 8192}
    assert call["options"] == DRAFT_OPTIONS
    assert call["schema"]["properties"]["style_profile"]["enum"] == STYLE_NAMES
    assert "Ý tưởng nhân vật: sư tỷ lạnh lùng" in call["messages"][1].content

    assert card.id is None and card.avatar is None
    assert card.name == "Tạ Vân Lan"
    assert card.gender == "female"
    assert card.language == "vi"
    assert card.style_profile == "trung_co_dai"
    assert card.address_terms.self_term == "ta"
    assert card.address_terms.player_term == "ngươi"
    assert card.address_terms.nicknames == ["tiểu sư đệ"]
    assert card.greeting == GOOD_GREETING
    assert card.greeting.count("[Thought:") == 2
    assert card.tags == ["cổ trang", "tiên hiệp", "sư tỷ"]
    assert card.scenario.startswith("Mùa đông")
    assert card.alternate_greetings == []
    assert "sư tỷ lạnh lùng" in card.creator_notes


async def test_forced_gender_and_style_override_model_output() -> None:
    fake = FakeLLM(json_replies=[good_reply(gender="female", style_profile="trung_co_dai")])
    card, _ = await draft_card(
        fake, "m", idea="sư huynh", language="vi", gender="male", style_profile="trung_hien_dai", styles=STYLES
    )
    assert card.gender == "male"
    assert card.style_profile == "trung_hien_dai"
    schema = fake.calls[0]["schema"]
    assert schema["properties"]["gender"]["enum"] == ["male"]
    assert schema["properties"]["style_profile"]["enum"] == ["trung_hien_dai"]


@pytest.mark.parametrize(
    ("idea", "style", "message"),
    [
        ("", None, "Hãy nhập ý tưởng"),
        ("   \n ", None, "Hãy nhập ý tưởng"),
        ("x" * 2001, None, "quá dài"),
        ("ok", "khong_co", "Không có style profile"),
    ],
)
async def test_draft_errors(idea: str, style: str | None, message: str) -> None:
    fake = FakeLLM(json_replies=[good_reply()])
    with pytest.raises(DraftError, match=message):
        await draft_card(fake, "m", idea=idea, language="vi", gender=None, style_profile=style, styles=STYLES)
    assert fake.calls == []


async def test_idea_of_exactly_2000_chars_is_accepted() -> None:
    fake = FakeLLM(json_replies=[good_reply()])
    await draft_card(fake, "m", idea="y" * 2000, language="vi", gender=None, style_profile=None, styles=STYLES)
    assert len(fake.calls) == 1


async def test_llm_error_propagates() -> None:
    fake = FakeLLM(error=LLMError("Model viết quá dài, bị cắt giữa chừng. Hãy thử lại."))
    with pytest.raises(LLMError, match="quá dài"):
        await draft_card(fake, "m", idea="ok", language="vi", gender=None, style_profile=None, styles=STYLES)


# ---- hậu xử lý: xưng hô ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "language", "expected"),
    [
        ("Sư tỷ", "vi", "sư tỷ"),
        ("Sư Tỷ", "vi", "sư tỷ"),
        ("Đệ tử/Đệ muội", "vi", "đệ tử"),
        ("tớ, mình", "vi", "tớ"),
        ("ta hoặc bổn cung", "vi", "ta"),
        ("ngươi (khi giận)", "vi", "ngươi"),
        ('"Cậu"', "vi", "cậu"),
        ("  anh  ", "vi", "anh"),
        ("I", "en", "I"),
        ("I/me", "en", "I"),
        ("You", "en", "you"),
        ("you or sweetheart", "en", "you"),
        ("Your Highness", "en", "your highness"),
        ("", "vi", ""),
        ("/", "vi", ""),
    ],
)
def test_normalize_term(raw: str, language: str, expected: str) -> None:
    assert normalize_term(raw, language) == expected  # type: ignore[arg-type]


def test_terms_with_alternatives_warn() -> None:
    card, warnings = post(good_reply(self_term="Sư tỷ", player_term="Đệ tử/Đệ muội"))
    assert card.address_terms.self_term == "sư tỷ"
    assert card.address_terms.player_term == "đệ tử"
    assert any("nhiều lựa chọn" in w and "đệ tử" in w for w in warnings)
    assert not any("Tự xưng" in w for w in warnings)  # "Sư tỷ" chỉ viết hoa, không phải nhiều lựa chọn


def test_empty_terms_warn_in_vi_and_default_in_en() -> None:
    _, warnings = post(good_reply(self_term="", player_term=""))
    assert any('Chưa có "Tự xưng"' in w for w in warnings)
    assert any('Chưa có "Gọi người chơi"' in w for w in warnings)
    card, warnings = post(good_reply(self_term="", player_term="", greeting=""), language="en")
    assert card.address_terms.self_term == "I" and card.address_terms.player_term == "you"
    assert not any("Chưa có" in w for w in warnings)


def test_nicknames_dedup_split_and_cap() -> None:
    card, _ = post(
        good_reply(
            nicknames=["Tiểu sư đệ", "tiểu sư đệ", "Nhóc con, Đồ ngốc", "A Đệ/A Muội", "Bé con", "Tiểu Bạch", "ngươi", "{user}"]
        )
    )
    assert card.address_terms.nicknames == ["Tiểu sư đệ", "Nhóc con", "Đồ ngốc", "A Đệ"]


def test_tags_lowercase_dedup_and_cap() -> None:
    card, _ = post(good_reply(tags=["#Cổ Trang", "cổ trang", "Tiên Hiệp, Sư Tỷ", "", "a", "b", "c", "d"]))
    assert card.tags == ["cổ trang", "tiên hiệp", "sư tỷ", "a", "b", "c"]


# ---- hậu xử lý: style, giới tính, chuỗi ---------------------------------------------------------


def test_unknown_style_falls_back_to_chung_with_warning() -> None:
    card, warnings = post(good_reply(style_profile="tien_hiep"))
    assert card.style_profile == "chung"
    assert any("tien_hiep" in w and '"chung"' in w for w in warnings)


def test_invalid_gender_becomes_other_with_warning() -> None:
    card, warnings = post(good_reply(gender="nữ"))
    assert card.gender == "other"
    assert any("giới tính" in w for w in warnings)
    card, _ = post(good_reply(gender="Female"))
    assert card.gender == "female"


def test_strings_trimmed_and_placeholders_normalized() -> None:
    card, _ = post(
        good_reply(
            name='  "Tạ Vân Lan" (谢云澜) ',
            description="  Đại sư tỷ của {user}.  ",
            scenario="{{ User }} đến muộn; <char> chờ.",
            personality="Dòng một.\r\n\r\n\r\n\r\nDòng hai.",
        )
    )
    assert card.name == "Tạ Vân Lan"
    assert card.description == "Đại sư tỷ của {{user}}."
    assert card.scenario == "{{user}} đến muộn; {{char}} chờ."
    assert card.personality == "Dòng một.\n\nDòng hai."


def test_missing_and_wrong_typed_fields_do_not_crash() -> None:
    data = good_reply(appearance=None, goals=["không phải chuỗi"], nicknames="Nhóc con", tags=None)
    del data["secrets"]
    card, warnings = post(data)
    assert card.appearance == "" and card.secrets == "" and card.goals == ""
    assert card.address_terms.nicknames == ["Nhóc con"]
    assert card.tags == []
    assert any("Mục tiêu" in w and "sai kiểu" in w for w in warnings)


def test_missing_name_warns() -> None:
    card, warnings = post(good_reply(name="  "))
    assert card.name == ""
    assert any("tên" in w for w in warnings)


def test_overlong_field_is_cut_to_sentence_with_warning() -> None:
    limit = FIELD_MAX_CHARS["background"]
    text = ("Nàng lớn lên ở núi Thanh Vân. " * 40)[: limit - 7] + "rồi một"
    assert len(text) >= limit
    card, warnings = post(good_reply(background=text))
    assert card.background.endswith("Thanh Vân.")
    assert len(card.background) < limit
    assert any('"Hoàn cảnh" quá dài' in w for w in warnings)


def test_escaped_newlines_are_unescaped() -> None:
    card, _ = post(good_reply(example_dialogues='{{char}}: "Một."\\n{{char}}: "Hai."'))
    assert card.example_dialogues == '{{char}}: "Một."\n{{char}}: "Hai."'


# ---- hậu xử lý: lời mở đầu -----------------------------------------------------------------------


def test_good_greeting_has_no_warnings() -> None:
    _, warnings = post(good_reply())
    assert warnings == []


def test_greeting_without_thought_warns() -> None:
    greeting = GOOD_GREETING.replace("[Thought: ", "(").replace("]", ")")
    _, warnings = post(good_reply(greeting=greeting))
    assert any("không có dòng [Thought: ...]" in w for w in warnings)


def test_greeting_with_one_thought_warns_count() -> None:
    first, _, rest = GOOD_GREETING.partition("[Thought: Tay")
    greeting = first + rest.split("\n\n", 1)[1]
    _, warnings = post(good_reply(greeting=greeting))
    assert any("có 1 dòng Thought" in w for w in warnings)


def test_lowercase_and_vietnamese_thought_tags_are_normalized() -> None:
    greeting = GOOD_GREETING.replace("[Thought: Lại", "[thought:Lại").replace("[Thought: Tay", "[ Suy nghĩ : Tay")
    card, warnings = post(good_reply(greeting=greeting))
    assert card.greeting == GOOD_GREETING
    assert warnings == []


def test_unclosed_thought_is_closed_at_paragraph_end() -> None:
    greeting = GOOD_GREETING.replace("chẳng than lấy một câu.]", "chẳng than lấy một câu.")
    card, warnings = post(good_reply(greeting=greeting))
    assert card.greeting == GOOD_GREETING
    assert any('thêm dấu "]"' in w for w in warnings)


def test_fix_thoughts_two_tags_in_one_paragraph() -> None:
    text, fixed = fix_thoughts("Mở đầu. [Thought: một [thought: hai] cuối.")
    assert text == "Mở đầu. [Thought: một] [Thought: hai] cuối."
    assert fixed == 1


def test_address_terms_in_narration_warn() -> None:
    greeting = GOOD_GREETING.replace("{{user}} cúi đầu", "Ngươi cúi đầu")
    _, warnings = post(good_reply(greeting=greeting))
    assert any("xưng hô trong dẫn truyện" in w and '"ngươi"' in w for w in warnings)


def test_terms_only_inside_dialogue_and_thought_do_not_warn() -> None:
    # "ngươi" có trong lời thoại, "ta" không có trong dẫn truyện (chỉ có trong "tay", "Tàng"...: không tính).
    _, warnings = post(good_reply())
    assert not any("dẫn truyện" in w for w in warnings)


def test_term_equal_to_narration_pronoun_is_not_flagged() -> None:
    # viet_hien_dai: nhân vật nam tự xưng "anh", dẫn truyện cũng gọi "anh" -> hợp lệ.
    greeting = GOOD_GREETING.replace("Nàng bước xuống", "Anh bước xuống")
    _, warnings = post(good_reply(style_profile="viet_hien_dai", gender="male", self_term="anh", greeting=greeting))
    assert not any("dẫn truyện" in w for w in warnings)


def test_greeting_length_user_placeholder_and_atmosphere_warnings() -> None:
    short = "Tạ Vân Lan đứng dưới mái hiên.\n\n[Thought: Lạnh quá.]\n\nBầu không khí lặng đi.\n\n[Thought: Thôi.]\n\n\"Vào đi.\""
    _, warnings = post(good_reply(greeting=short))
    assert any("Lời mở đầu dài" in w for w in warnings)
    assert any("{{user}}" in w for w in warnings)
    assert any("bầu không khí" in w for w in warnings)


def test_empty_greeting_warns() -> None:
    _, warnings = post(good_reply(greeting=""))
    assert any("không viết lời mở đầu" in w for w in warnings)


def test_postprocess_does_not_mutate_input() -> None:
    data = good_reply(nicknames=["A", "a"], tags=["X"])
    before = copy.deepcopy(data)
    post(data)
    assert data == before


async def test_english_draft() -> None:
    reply = good_reply(
        name="Tạ Vân Lan",
        self_term="I",
        player_term="You",
        nicknames=["little junior brother"],
        greeting=(
            "Snow covered the stone steps of the library hall. Tạ Vân Lan stood under the eaves, watching {{user}} sweep.\n\n"
            "[Thought: Again. The elders punished them for three days and they never complained once.]\n\n"
            "She walked down the steps and set a small porcelain jar on the stone railing beside {{user}}.\n\n"
            "[Thought: Their hands are cracked from the cold. Someone has to look after them.]\n\n"
            "\"Ointment for the cold. Put it on, then come inside for some tea. How long do you plan to stand out here?\""
        ),
        tags=["Xianxia", "Cold Senior"],
    )
    fake = FakeLLM(json_replies=[reply])
    card, warnings = await draft_card(
        fake, "m", idea="cold senior sister", language="en", gender=None, style_profile=None, styles=STYLES
    )
    assert card.language == "en"
    assert card.address_terms.self_term == "I"
    assert card.address_terms.player_term == "you"
    assert card.tags == ["xianxia", "cold senior"]
    # Lời mở đầu mẫu ngắn (< 80 từ) nên chỉ có cảnh báo độ dài.
    assert [w for w in warnings if not w.startswith("Lời mở đầu dài")] == []
    assert fake.calls[0]["messages"][0].content.startswith("You are an editor")

    leaked = reply["greeting"].replace("She walked down", "I walked down")
    _, warnings = postprocess_draft(
        {**reply, "greeting": leaked}, language="en", gender=None, style_profile=None, styles=STYLES
    )
    assert any("xưng hô trong dẫn truyện" in w and '"I"' in w for w in warnings)


def test_schema_strings_have_no_max_length() -> None:
    # Ollama: chuỗi có maxLength không cho escape ("\n") và làm model kẹt khi chạm giới hạn.
    def walk(node: Any) -> None:
        if isinstance(node, dict):
            assert "maxLength" not in node
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(draft_schema(STYLE_NAMES))


def test_overlong_unbounded_field_is_truncated_within_limit() -> None:
    limit = FIELD_MAX_CHARS["goals"]
    text = "Muốn giữ bình yên cho tông môn. " * 40
    card, warnings = post(good_reply(goals=text))
    assert len(card.goals) <= limit
    assert card.goals.endswith("tông môn.")
    assert any('"Mục tiêu" quá dài' in w for w in warnings)


def test_examples_are_normalized() -> None:
    raw = (
        '{{char}}: "Em lại quên uống thuốc rồi à?\n\n'
        'Tạ Vân Lan: "Đứng sau ta."\n'
        "{{char}}: “Ngươi định đứng đây tới bao giờ?"
    )
    card, _ = post(good_reply(example_dialogues=raw))
    assert card.example_dialogues == (
        '{{char}}: "Em lại quên uống thuốc rồi à?"\n'
        '{{char}}: "Đứng sau ta."\n'
        "{{char}}: “Ngươi định đứng đây tới bao giờ?”"
    )
