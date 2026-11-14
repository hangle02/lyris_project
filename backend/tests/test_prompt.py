"""Test prompt builder, chỉ đạo ((...)), ước lượng token và style profile. Không cần Ollama."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lyris.models import AddressTerms, CharacterCard, Message, NarrationPronouns, Persona, Story
from lyris.prompt.builder import PromptBudget, build_prompt, load_style, window_boundaries
from lyris.prompt.directives import extract_directives
from lyris.prompt.tokens import estimate_tokens

PROMPTS_JSON = Path(__file__).resolve().parents[2] / "harness" / "prompts.json"

GREETING = (
    "Nắng chiều rơi trên sân bóng rổ. Lạc Dương đứng dưới gốc ngô đồng, tay cầm hai cốc trà sữa.\n"
    "[Thought: Lại trễ mười phút. Chắc lại ngủ quên.]\n"
    '"Vãn Vãn, ra đây."'
)


# ---- fixture dựng từ models.py -----------------------------------------------------------


def make_card(**overrides: object) -> CharacterCard:
    data: dict[str, object] = dict(
        id=1,
        name="Lạc Dương",
        gender="male",
        language="vi",
        description="20 tuổi, sinh viên",
        personality=(
            "Lạnh lùng, ít nói, giữ khoảng cách với mọi người xung quanh. Riêng với Lâm Vãn thì dịu dàng, "
            "kiên nhẫn và chiều chuộng hết mực, dù ít khi nói ra thành lời mà thể hiện qua hành động"
        ),
        appearance="Cao gầy, mắt đen sâu",
        background="Thanh mai trúc mã của Lâm Vãn, lớn lên cùng nhau từ nhỏ",
        speech_style="Câu ngắn, giọng trầm",
        style_profile="trung_hien_dai",
        address_terms=AddressTerms(
            self_term="tớ",
            player_term="cậu",
            nicknames=["Vãn Vãn", "A Vãn"],
            others='"bạn học + họ", "học trưởng", "học tỷ", "thầy/cô + họ"; xưng "tôi"',
        ),
        greeting=GREETING,
    )
    data.update(overrides)
    return CharacterCard.model_validate(data)


def make_persona(**overrides: object) -> Persona:
    data: dict[str, object] = dict(
        id=1,
        name="Lâm Vãn",
        gender="female",
        description="20 tuổi, tính cách lạc quan, yêu đời, là thanh mai trúc mã của Lạc Dương",
    )
    data.update(overrides)
    return Persona.model_validate(data)


def make_story(**overrides: object) -> Story:
    data: dict[str, object] = dict(
        id=1,
        card_id=1,
        persona_id=1,
        title="Thanh mai",
        scenario="Trung Quốc hiện đại, vườn trường đại học. Chiều thứ sáu, sau giờ học.",
        language="vi",
        mode="story",
        relationship_type="het",
        pov="third",
        narration_pronouns=NarrationPronouns(character="anh", player="cô"),
    )
    data.update(overrides)
    return Story.model_validate(data)


def user(turn: int, text: str) -> Message:
    visible, directive = extract_directives(text)
    return Message(
        story_id=1, turn_index=turn, role="user", mode="story",
        raw_content=text, visible_content=visible, directive=directive,
    )


def assistant(turn: int, raw: str, visible: str | None = None) -> Message:
    return Message(
        story_id=1, turn_index=turn, role="assistant", mode="story",
        raw_content=raw, visible_content=visible if visible is not None else raw,
    )


def all_text(built) -> str:  # type: ignore[no-untyped-def]
    return "\n".join(m.content for m in built.messages)


# ---- tokens ------------------------------------------------------------------------------


def test_estimate_tokens() -> None:
    assert estimate_tokens("") == 4
    assert estimate_tokens("abc") == 5
    assert estimate_tokens("abcd") == 6
    assert estimate_tokens("x" * 300) == 104


# ---- directives --------------------------------------------------------------------------


def test_extract_directives_none() -> None:
    assert extract_directives("  Chào cậu  ") == ("Chào cậu", None)


def test_extract_directives_multiple_and_multiline() -> None:
    text = "*Tớ cúi đầu.* ((cho anh ấy\nhơi ghen)) Cậu đến muộn đó. ((trời bắt đầu mưa))"
    visible, directive = extract_directives(text)
    assert visible == "*Tớ cúi đầu.* Cậu đến muộn đó."
    assert directive == "cho anh ấy hơi ghen; trời bắt đầu mưa"


def test_extract_directives_only_directive_and_empty() -> None:
    assert extract_directives("((để Lạc Dương chủ động))") == ("", "để Lạc Dương chủ động")
    assert extract_directives("Chào (( ))!") == ("Chào!", None)


def test_extract_directives_unclosed_is_directive() -> None:
    assert extract_directives("Đi thôi. ((cho trời đổ mưa") == ("Đi thôi.", "cho trời đổ mưa")


def test_extract_directives_keeps_paragraphs() -> None:
    visible, _ = extract_directives("Dòng một.\n\n\n\nDòng hai ((x))")
    assert visible == "Dòng một.\n\nDòng hai"


# ---- style -------------------------------------------------------------------------------


def test_load_style_sections() -> None:
    vi = load_style("trung_hien_dai")
    en = load_style("trung_hien_dai", "en")
    assert "Hán Việt" in vi and "học tỷ" in vi and "<!--" not in vi and "# en" not in vi
    assert en.startswith("Setting and style") and "Hán Việt" not in en


@pytest.mark.parametrize("name", ["khong_ton_tai", "../models", "", "a/b"])
def test_load_style_unknown(name: str) -> None:
    with pytest.raises(ValueError):
        load_style(name)


# ---- build_prompt: cấu trúc --------------------------------------------------------------


def test_block_order_and_stable_system_message() -> None:
    card, persona, story = make_card(), make_persona(), make_story(scene_summary="Hai người vừa tan học.")
    h1 = [assistant(0, GREETING), user(1, "Tớ đến rồi đây!")]
    h3 = h1 + [assistant(2, "[Thought: Ồn ào.]\nAnh đưa cốc trà sữa cho cô."), user(3, "*Tớ nhận lấy.* Cảm ơn nha ((anh ấy cười))")]
    b1 = build_prompt(card, persona, story, h1)
    b3 = build_prompt(card, persona, story, h3)

    system = b1.messages[0]
    assert system.role == "system"
    assert b3.messages[0].content == system.content  # byte-identical giữa các lượt
    s = system.content
    # A (luật) -> B (nhân vật + style) -> C (bối cảnh + tóm tắt)
    assert s.index("Luật:") < s.index("Nhân vật: Lạc Dương") < s.index("Bối cảnh và văn phong") < s.index("Bối cảnh: ")
    assert s.index("Bối cảnh: ") < s.index("Tóm tắt những gì đã xảy ra: Hai người vừa tan học.")
    # Không có nội dung theo lượt trong system.
    assert "Tớ đến rồi đây" not in s and "anh ấy cười" not in s
    assert set(b3.token_estimate) == {"A", "B", "C", "E", "F", "total"}
    assert b3.token_estimate["total"] == sum(v for k, v in b3.token_estimate.items() if k != "total")


def test_options_and_stop() -> None:
    built = build_prompt(make_card(), make_persona(), make_story(), [user(0, "Chào")])
    assert built.stop == ["Lâm Vãn:", "\nLâm Vãn:", "\nPlayer:", "\nUser:"]
    assert built.options == {"num_ctx": 8192, "num_predict": 900, "temperature": 0.8, "top_p": 0.95}
    dm = build_prompt(make_card(), make_persona(), make_story(mode="dm"), [user(0, "Chào")])
    assert dm.options["num_predict"] == 200
    custom = build_prompt(make_card(), make_persona(), make_story(), [user(0, "Chào")], budget=PromptBudget(num_ctx=4096))
    assert custom.options["num_ctx"] == 4096


@pytest.mark.parametrize("history", [[], [user(0, "a"), assistant(1, "b")], [assistant(0, GREETING)]])
def test_last_message_must_be_user(history: list[Message]) -> None:
    with pytest.raises(ValueError):
        build_prompt(make_card(), make_persona(), make_story(), history)


def test_greeting_first_inserts_fake_user_turn() -> None:
    built = build_prompt(make_card(), make_persona(), make_story(), [assistant(0, GREETING), user(1, "Tớ tới rồi!")])
    roles = [m.role for m in built.messages]
    assert roles == ["system", "user", "assistant", "user"]
    assert built.messages[1].content == "(Câu chuyện bắt đầu.)"
    assert built.messages[2].content == GREETING  # assistant giữ raw_content kèm Thought
    assert built.messages[3].content.startswith("Tớ tới rồi!\n\n[Ghi chú cho người dẫn truyện")
    assert built.dropped_turns == 0

    en = build_prompt(make_card(), make_persona(), make_story(language="en"), [assistant(0, "Hi."), user(1, "Hey")])
    assert en.messages[1].content == "(The story begins.)"


def test_assistant_uses_raw_user_uses_visible() -> None:
    a = assistant(0, "[Thought: Ngốc.]\nAnh khẽ cười.", visible="Anh khẽ cười.")
    built = build_prompt(make_card(), make_persona(), make_story(), [user(0, "Hi"), a, user(2, "Cậu cười gì?")])
    assert built.messages[2].content == "[Thought: Ngốc.]\nAnh khẽ cười."


def test_merges_consecutive_same_role() -> None:
    history = [
        assistant(0, GREETING),
        user(1, "Cậu ơi"),
        user(2, "Sao không trả lời tớ? ((anh ấy đang giận))"),
    ]
    built = build_prompt(make_card(), make_persona(), make_story(), history)
    assert [m.role for m in built.messages] == ["system", "user", "assistant", "user"]
    last = built.messages[-1].content
    assert last.startswith("Cậu ơi\n\nSao không trả lời tớ?\n\n[Ghi chú")
    assert "Chỉ đạo của người chơi cho lượt này: anh ấy đang giận." in last

    # Hai lượt assistant liền nhau cũng được gộp.
    h2 = [user(0, "A"), assistant(1, "B1"), assistant(2, "B2"), user(3, "C")]
    b2 = build_prompt(make_card(), make_persona(), make_story(), h2)
    assert [m.role for m in b2.messages] == ["system", "user", "assistant", "user"]
    assert b2.messages[2].content == "B1\n\nB2"


# ---- chỉ đạo -----------------------------------------------------------------------------


def test_directives_go_to_f_not_history_and_no_double_parens_anywhere() -> None:
    history = [
        assistant(0, GREETING),
        user(1, "*Tớ vẫy tay.* ((cho trời đổ mưa))"),
        assistant(2, "[Thought: Mưa rồi.]\nAnh kéo cô vào mái hiên. ((lỡ in lại chỉ đạo))"),
        user(3, "*Tớ run run.* Lạnh quá ((để anh ấy cởi áo khoác))"),
    ]
    built = build_prompt(make_card(), make_persona(), make_story(), history)
    text = all_text(built)
    assert "((" not in text and "))" not in text
    # Chỉ đạo cũ không còn trong lịch sử.
    assert "cho trời đổ mưa" not in text
    assert "lỡ in lại chỉ đạo" not in text
    last = built.messages[-1].content
    body, note = last.split("\n\n[Ghi chú cho người dẫn truyện", 1)
    assert body == "*Tớ run run.* Lạnh quá"
    assert "Chỉ đạo của người chơi cho lượt này: để anh ấy cởi áo khoác." in note
    assert "không in lại" in note
    assert "[Thought: ...]" in note and '"anh" hoặc "Lạc Dương"' in note
    # F không lọt vào các lượt khác.
    assert all("Ghi chú" not in m.content for m in built.messages[1:-1])


def test_no_double_parens_even_from_card_or_unclosed_input() -> None:
    card = make_card(speech_style="Hay nói ((ừ))")
    msg = Message(
        story_id=1, turn_index=0, role="user", mode="story",
        raw_content="((( hi", visible_content="a (((b)))", directive=None,
    )
    built = build_prompt(card, make_persona(), make_story(), [msg])
    assert "((" not in all_text(built)


def test_directive_only_turn() -> None:
    built = build_prompt(make_card(), make_persona(), make_story(), [assistant(0, GREETING), user(1, "((để Lạc Dương chủ động bắt chuyện))")])
    last = built.messages[-1].content
    assert last.startswith("[Ghi chú cho người dẫn truyện, không phải lời của Lâm Vãn]")
    assert "không nói hay làm gì thêm" in last
    assert "Chỉ đạo của người chơi cho lượt này: để Lạc Dương chủ động bắt chuyện." in last

    # Lượt cũ chỉ có chỉ đạo được thay bằng ghi chú trung tính, không để trống.
    history = [user(0, "((mở đầu bằng cơn mưa))"), assistant(1, "Mưa."), user(2, "Ồ")]
    b2 = build_prompt(make_card(), make_persona(), make_story(), history)
    assert b2.messages[1].content == "(Lượt này người chơi không viết gì.)"


# ---- ngân sách ---------------------------------------------------------------------------


def _long_history(turns: int) -> list[Message]:
    history: list[Message] = [assistant(0, GREETING)]
    for t in range(1, turns + 1):
        if t % 2:
            history.append(user(t, f"Lượt người chơi số {t}. " + "Tớ kể chuyện tiếp nhé. " * 20))
        else:
            history.append(assistant(t, f"[Thought: Lượt {t}.]\nLượt nhân vật số {t}. " + "Anh lặng lẽ nghe. " * 30))
    history.append(user(turns + 1, "Lượt cuối của tớ."))
    return history


def test_budget_drops_oldest_first() -> None:
    card, persona, story = make_card(), make_persona(), make_story()
    history = _long_history(24)
    full = build_prompt(card, persona, story, history)
    assert full.dropped_turns == 0

    budget = PromptBudget(num_ctx=full.token_estimate["total"] // 2 + 900 + 256)
    built = build_prompt(card, persona, story, history, budget=budget)
    assert built.dropped_turns > 0
    assert built.token_estimate["total"] <= budget.num_ctx - 900 - 256
    assert built.messages[0].content == full.messages[0].content  # system không đổi

    convo = built.messages[1:]
    assert convo[-1].content.startswith("Lượt cuối của tớ.")
    # Phần còn lại là một hậu tố liên tục: lượt cũ nhất bị bỏ trước.
    kept = history[built.dropped_turns:]
    first_kept = kept[0]
    if first_kept.role == "assistant":
        assert convo[0].content == "(Câu chuyện tiếp tục.)"
        assert convo[1].content == first_kept.raw_content
    else:
        assert convo[0].content == first_kept.visible_content
    assert "(Câu chuyện bắt đầu.)" not in all_text(built)
    assert GREETING not in all_text(built)

    # Ngân sách lớn hơn một chút thì giữ được nhiều lượt hơn hoặc bằng.
    bigger = build_prompt(card, persona, story, history, budget=PromptBudget(num_ctx=budget.num_ctx + 2000))
    assert bigger.dropped_turns <= built.dropped_turns


def test_budget_trims_to_a_chunk_boundary() -> None:
    # Phase 3b: không cắt sát từng lượt nữa; cửa sổ bắt đầu ở mốc khúc sớm nhất còn vừa.
    card, persona, story = make_card(), make_persona(), make_story()
    history = _long_history(20)
    budget = PromptBudget(num_ctx=3400)
    built = build_prompt(card, persona, story, history, budget=budget)
    limit = budget.num_ctx - budget.reply_tokens_story - budget.safety_tokens
    assert built.token_estimate["total"] <= limit
    assert built.dropped_turns > 0
    marks = window_boundaries(card, persona, story, history, budget=budget)
    assert history[built.dropped_turns].turn_index in marks
    assert history[built.dropped_turns].role == "user"
    # Mốc sớm hơn liền trước thì không vừa (không cắt thừa cả một khúc).
    earlier = [m for m in marks if m < history[built.dropped_turns].turn_index]
    if earlier:
        idx = next(i for i, m in enumerate(history) if m.turn_index == earlier[-1])
        wider = build_prompt(card, persona, story, history[idx:], budget=PromptBudget(num_ctx=10**6))
        assert wider.token_estimate["total"] > limit - 400  # gần hoặc vượt ngân sách (đã tính phần dự phòng F)


def test_budget_never_drops_last_user_message() -> None:
    huge = "Tớ nói rất dài. " * 2000
    history = [assistant(0, GREETING), user(1, "a"), assistant(2, "b"), user(3, huge)]
    built = build_prompt(make_card(), make_persona(), make_story(), history, budget=PromptBudget(num_ctx=2048))
    assert built.dropped_turns == 3
    assert [m.role for m in built.messages] == ["system", "user"]
    assert built.messages[1].content.startswith(huge.strip())
    assert "[Ghi chú cho người dẫn truyện" in built.messages[1].content


# ---- ngôn ngữ, mode, ngôi kể ---------------------------------------------------------------


def _changed_on_purpose(line: str) -> bool:
    """Dòng của bản Phase 0 được đổi có chủ ý sau góp ý của người dùng (Thought lồng giữa truyện, độ dài)."""
    return "[Thought: ...]" in line or "120-200" in line


def test_vi_story_rules_match_verified_prompt() -> None:
    if not PROMPTS_JSON.exists():
        pytest.skip("harness/prompts.json không có")
    systems = json.loads(PROMPTS_JSON.read_text(encoding="utf-8"))["systems"]
    built = build_prompt(make_card(), make_persona(), make_story(), [user(0, "Chào")])
    s = built.messages[0].content
    ref = systems["vi_story"]
    # Mọi dòng thiết lập và luật của bản đã kiểm chứng, trừ dòng nói về ((...)), có nguyên văn.
    setup_and_rules = ref.split("Thiết lập câu chuyện:")[1]
    setup, rules = setup_and_rules.split("Bối cảnh và văn phong:")[0], ref.split("Luật:")[1]
    for line in (setup + "\n" + rules).splitlines():
        line = line.strip()
        if line and "((" not in line and not _changed_on_purpose(line):
            assert line in s, line
    assert "lồng vào giữa truyện: 2-3 dòng Thought mỗi lượt" in s
    assert "- Viết tiếng Việt tự nhiên, câu rõ nghĩa" in s
    assert "- Chỉ dùng tiếng Việt. Phần dẫn truyện và lời thoại dài khoảng 120-200 từ, không tính Thought." in s
    assert ref.splitlines()[0] in s
    # Xưng hô và người chơi vẫn có, chỉ được chuyển sang khối B.
    assert 'Lạc Dương tự xưng "tớ", gọi Lâm Vãn là "cậu"; lúc thân mật hoặc dỗ dành có thể gọi "Vãn Vãn" hoặc "A Vãn".' in s
    assert "Người chơi: Lâm Vãn, nữ, 20 tuổi, tính cách lạc quan, yêu đời" in s
    assert "Nhân vật: Lạc Dương, nam, 20 tuổi, sinh viên." in s
    assert "- Giới tính: Lạc Dương là nam, Lâm Vãn là nữ." in s
    assert "đưa chỉ đạo trong ghi chú cuối lượt" in s


def test_vi_dm_rules() -> None:
    systems = json.loads(PROMPTS_JSON.read_text(encoding="utf-8"))["systems"] if PROMPTS_JSON.exists() else None
    built = build_prompt(make_card(), make_persona(), make_story(mode="dm"), [assistant(0, GREETING), user(1, "cậu còn thức không 🥺")])
    s = built.messages[0].content
    assert s.startswith("Bạn đóng vai Lạc Dương đang nhắn tin với Lâm Vãn bằng tiếng Việt.")
    assert "1-3 câu ngắn" in s and "không có dòng [Thought: ...]" in s
    assert "- Không viết tin nhắn thay Lâm Vãn." in s
    assert "Ngôi kể" not in s and "Dài khoảng 120-200 từ" not in s
    if systems:
        assert "- Kiểu quan hệ: nam - nữ (ngôn tình)." in systems["vi_dm"] and "- Kiểu quan hệ: nam - nữ (ngôn tình)." in s
    note = built.messages[-1].content.split("\n\n", 1)[1]
    assert note.startswith("[Ghi chú cho người viết, không phải tin nhắn của Lâm Vãn]")
    assert "1-3 câu" in note and "Thought" in note
    assert "Dẫn truyện" not in note


def test_en_story_rules_match_verified_prompt() -> None:
    story = make_story(language="en", narration_pronouns=NarrationPronouns(character="he", player="she"))
    built = build_prompt(make_card(), make_persona(), story, [user(0, "Hey, *I wave.* ((make him blush))")])
    s = built.messages[0].content
    assert s.startswith("You are the narrator and play the character Lạc Dương in an interactive story in English.")
    assert "Setting and style: modern China" in s and "Bối cảnh và văn phong" not in s
    assert 'Nicknames: Lạc Dương sometimes calls Lâm Vãn "Vãn Vãn" or "A Vãn" when being gentle.' in s
    if PROMPTS_JSON.exists():
        ref = json.loads(PROMPTS_JSON.read_text(encoding="utf-8"))["systems"]["en_story"]
        for line in ref.split("Rules:")[1].splitlines():
            line = line.strip()
            if line and "((" not in line and not _changed_on_purpose(line):
                assert line in s, line
        assert "woven into the story: 2-3 Thought lines per turn" in s
        assert "- Write plain, natural prose." in s
        assert "- Relationship type: male - female romance." in s
        assert 'Refer to Lạc Dương as "he" and Lâm Vãn as "she" in narration.' in s
    last = built.messages[-1].content
    assert last.startswith("Hey, *I wave.*\n\n[Note to the narrator, not Lâm Vãn's words]")
    assert "The player's direction for this turn: make him blush." in last
    assert "((" not in all_text(built)


def test_en_derives_pronouns_when_story_holds_vietnamese_ones() -> None:
    built = build_prompt(make_card(), make_persona(), make_story(language="en"), [user(0, "Hi")])
    s = built.messages[0].content
    assert 'Refer to Lạc Dương as "he" and Lâm Vãn as "she" in narration.' in s
    assert '"anh"' not in s


def test_en_dm() -> None:
    built = build_prompt(make_card(), make_persona(), make_story(language="en", mode="dm"), [user(0, "you up?")])
    s = built.messages[0].content
    assert s.startswith("You play Lạc Dương, texting Lâm Vãn in English.")
    assert "1-3 short sentences" in s and "- Never write messages for Lâm Vãn." in s and "- English only." in s
    assert built.messages[-1].content.startswith("you up?\n\n[Note for the writer, not a message from Lâm Vãn]")
    assert built.options["num_predict"] == 200


def test_pov_first() -> None:
    story = make_story(pov="first", narration_pronouns=NarrationPronouns(character="tôi", player="cô"))
    built = build_prompt(make_card(), make_persona(), story, [user(0, "Chào cậu")])
    s = built.messages[0].content
    assert "Ngôi kể: ngôi thứ nhất" in s
    assert 'Lạc Dương tự gọi mình là "tôi", gọi Lâm Vãn là "cô" hoặc "Lâm Vãn".' in s
    assert 'Không dùng "tớ", "cậu" trong phần dẫn truyện' in s
    assert "ngôi thứ ba" not in s and 'không xưng "tôi"' not in s
    note = built.messages[-1].content
    assert 'Lạc Dương kể ở ngôi thứ nhất, tự gọi mình là "tôi"' in note

    en = build_prompt(
        make_card(), make_persona(),
        make_story(language="en", pov="first", narration_pronouns=NarrationPronouns(character="I", player="she")),
        [user(0, "Hi")],
    )
    assert 'Point of view: first person. Lạc Dương narrates the story as "I".' in en.messages[0].content


def test_relationship_and_gender_parameters() -> None:
    card = make_card(name="Cố Ngôn")
    persona = make_persona(name="Thẩm Dịch", gender="male", description="")
    story = make_story(relationship_type="bl", narration_pronouns=NarrationPronouns(character="hắn", player="y"))
    built = build_prompt(card, persona, story, [user(0, "Chào")])
    s = built.messages[0].content
    assert "- Kiểu quan hệ: nam - nam (đam mỹ)." in s
    assert "- Giới tính: Cố Ngôn là nam, Thẩm Dịch là nam." in s
    assert 'gọi Cố Ngôn là "hắn" hoặc "Cố Ngôn", gọi Thẩm Dịch là "y" hoặc "Thẩm Dịch".' in s
    assert "Người chơi: Thẩm Dịch, nam." in s
    assert built.stop[0] == "Thẩm Dịch:"
    assert "Lâm Vãn" not in s.split("Xưng hô (chỉ dùng")[0].split("Nhân vật:")[0]

    gl = build_prompt(make_card(gender="female"), make_persona(), make_story(relationship_type="gl"), [user(0, "x")])
    assert "nữ - nữ (bách hợp)" in gl.messages[0].content
    none = build_prompt(make_card(), make_persona(), make_story(relationship_type="none"), [user(0, "x")])
    assert "Kiểu quan hệ: không lãng mạn" in none.messages[0].content


def test_address_terms_overlapping_narration_pronoun() -> None:
    # Xưng hô anh/em, dẫn truyện cũng gọi nhân vật là "anh": không được cấm "anh" trong dẫn truyện.
    card = make_card(address_terms=AddressTerms(self_term="anh", player_term="em"))
    built = build_prompt(card, make_persona(), make_story(), [user(0, "Anh ơi")])
    s = built.messages[0].content
    assert 'Không dùng "em" trong phần dẫn truyện; từ này chỉ xuất hiện trong lời thoại và Thought.' in s
    assert 'Người dẫn truyện đứng ngoài, không xưng "tôi".' in s


def test_card_placeholders_filled() -> None:
    card = make_card(example_dialogues="{{user}}: Cậu đi đâu đó?\n{{char}}: Đón cậu.")
    built = build_prompt(card, make_persona(), make_story(), [user(0, "x")])
    s = built.messages[0].content
    assert "Lâm Vãn: Cậu đi đâu đó?\nLạc Dương: Đón cậu." in s
    assert "{{" not in s


# ---- mặt cười, hiệu năng, câu trả lời của model --------------------------------------------


def test_extract_directives_ignores_emoticons() -> None:
    assert extract_directives("Hic :(( cậu không đến thật à?") == ("Hic :(( cậu không đến thật à?", None)
    assert extract_directives("Tớ buồn quá :(( Cậu đi đâu vậy :))") == ("Tớ buồn quá :(( Cậu đi đâu vậy :))", None)
    assert extract_directives("Haha =)) đồ ngốc") == ("Haha =)) đồ ngốc", None)
    assert extract_directives("Buồn ghê :((( thật") == ("Buồn ghê :((( thật", None)
    assert extract_directives("Ừ ;)) đi thôi") == ("Ừ ;)) đi thôi", None)
    # Chỉ đạo thật vẫn được tách khi đi cùng mặt cười.
    assert extract_directives("Tớ đến rồi :)) ((cho anh ấy bật cười))") == ("Tớ đến rồi :))", "cho anh ấy bật cười")
    assert extract_directives("Hic :(( ((cho trời mưa)) thôi") == ("Hic :(( thôi", "cho trời mưa")


def test_extract_directives_unclosed_only_at_word_start() -> None:
    assert extract_directives("((cho trời đổ mưa") == ("", "cho trời đổ mưa")
    assert extract_directives("Dòng một\n((cho trời đổ mưa") == ("Dòng một", "cho trời đổ mưa")
    # "((" lẻ không có chữ sau, hoặc dính vào chữ trước: giữ nguyên như văn bản.
    assert extract_directives("Buồn ghê ((") == ("Buồn ghê ((", None)
    assert extract_directives("abc((def") == ("abc((def", None)


def test_extract_directives_keeps_space_before_colon() -> None:
    assert extract_directives("Anh nói : đi thôi ((x))") == ("Anh nói : đi thôi", "x")
    assert extract_directives("Chào ((x)) , cậu") == ("Chào, cậu", "x")


def test_extract_directives_is_linear() -> None:
    import time

    for text in ["((" * 10_000, "((a" * 6_666, ":((" * 6_666, "((a))" * 4_000 + "((" * 5_000]:
        started = time.perf_counter()
        extract_directives(text)
        assert time.perf_counter() - started < 0.1, text[:20]


def test_assistant_history_keeps_emoticons_and_text_after_lone_parens() -> None:
    raw = "Cậu lại thế rồi :(( Thôi được, tớ đợi cậu ở cổng nhé.\n\n[Thought: Ngốc thật.]"
    built = build_prompt(make_card(), make_persona(), make_story(), [assistant(0, raw), user(1, "Ừ")])
    history = built.messages[2].content
    assert history.startswith("Cậu lại thế rồi :( Thôi được, tớ đợi cậu ở cổng nhé.")
    assert "[Thought: Ngốc thật.]" in history
    # Cặp ((...)) hoàn chỉnh model lỡ in lại vẫn bị bỏ.
    built = build_prompt(make_card(), make_persona(), make_story(), [assistant(0, "Anh cười. ((ghen)) Đi thôi."), user(1, "Ừ")])
    assert built.messages[2].content == "Anh cười. Đi thôi."


def test_story_note_reminds_no_echo_and_length() -> None:
    built = build_prompt(make_card(), make_persona(), make_story(), [assistant(0, GREETING), user(1, '"Tớ đói rồi."')])
    note = built.messages[-1].content
    assert "Không chép lại lời Lâm Vãn vừa nói" in note
    assert "cảm xúc mới cho Lâm Vãn" in note
    assert "khoảng 120-200 từ, không quá 200 từ." in note
    system = built.messages[0].content
    assert "không chép lại lời thoại của Lâm Vãn" in system
    assert "mở đầu lượt bằng phản ứng của Lạc Dương" in system


def test_seed_block_b_has_no_repeated_lead_in() -> None:
    seed_dir = Path(__file__).resolve().parents[1] / "lyris" / "seed"
    card_data = json.loads((seed_dir / "lac_duong.json").read_text(encoding="utf-8"))
    persona_data = json.loads((seed_dir / "lam_van.json").read_text(encoding="utf-8"))
    card = make_card(**{k: v for k, v in card_data.items() if k in {"description", "address_terms"}})
    persona = Persona.model_validate({**persona_data, "id": 1})
    system = build_prompt(card, persona, make_story(), [user(0, "Chào")]).messages[0].content
    assert "Nhân vật: Lạc Dương, nam, 20 tuổi, sinh viên năm hai." in system
    assert "Người chơi: Lâm Vãn, nữ, 20 tuổi, sinh viên năm hai." in system
    assert '- Với người khác: xưng "tôi"; gọi kiểu Trung' in system
    assert "Với người khác: Với người khác" not in system
    assert "nam. Nam" not in system and "nữ. Nữ" not in system


# ---------------------------------------------------------------- thought_style


def test_thought_style_end_asks_for_one_longer_thought() -> None:
    built = build_prompt(make_card(), make_persona(), make_story(thought_style="end"), [assistant(0, GREETING), user(1, "Chào")])
    system = built.messages[0].content
    assert "Kết thúc lượt bằng đúng một dòng suy nghĩ thầm của Lạc Dương" in system and "dài 2-4 câu" in system
    assert "lồng vào giữa truyện" not in system
    assert "Kết thúc bằng đúng một dòng [Thought: ...] của Lạc Dương, 2-4 câu." in built.messages[-1].content


def test_thought_style_inline_is_default_and_in_note() -> None:
    built = build_prompt(make_card(), make_persona(), make_story(), [assistant(0, GREETING), user(1, "Chào")])
    assert "2-3 dòng [Thought: ...] của Lạc Dương rải ở các chỗ khác nhau trong truyện, không đặt hai Thought liền nhau" in built.messages[-1].content


def test_thought_style_en() -> None:
    story = make_story(language="en", thought_style="end", narration_pronouns=NarrationPronouns(character="he", player="she"))
    built = build_prompt(make_card(), make_persona(), story, [user(0, "Hi")])
    assert "End the turn with exactly one line of Lạc Dương's inner monologue" in built.messages[0].content
    assert "End with exactly one [Thought: ...] line for Lạc Dương, 2-4 sentences." in built.messages[-1].content
