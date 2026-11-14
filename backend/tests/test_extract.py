"""Test trích xuất state (lyris/state/extract.py) bằng FakeLLM: prompt, schema, options, kiểm tra kết quả."""
from __future__ import annotations

import json
import unicodedata

import pytest

from lyris.llm.base import LLMError
from lyris.llm.fake import FakeLLM
from lyris.models import AddressTerms, Message, RelationshipValues, SceneState
from lyris.state.extract import (
    NUM_PREDICT,
    OPENING_SCHEMA,
    SCHEMA,
    TEMPERATURE,
    WARM_SIGN,
    build_messages,
    example_texts,
    extract_turn,
    is_opening,
    is_warm,
    normalize,
    player_address,
    top_delta,
    validate,
)
from tests.test_prompt import make_card, make_persona, make_story

BEFORE = RelationshipValues(affection=62, trust=70, attraction=45, obsession=25, fear=10, aversion=15)
SCENE = SceneState(location="Thư viện tầng ba", time="Buổi chiều")
REPLY = (
    'Lạc Dương bước tới, đứng chắn giữa cô và người lạ.\n\n"Bạn học này, cô ấy không tiện tiếp chuyện."\n\n'
    "[Thought: Không ai được chạm vào người của tớ.]"
)

GOOD = {
    "relationship_delta": {"affection": 1, "trust": 0, "attraction": 2, "obsession": 3, "fear": 0, "aversion": 0},
    "location": "",
    "time": "",
    "memory": {"text": "Lạc Dương đuổi khéo người lạ mời Lâm Vãn trà sữa.", "importance": 3},
    "facts": [{"subject": "Lâm Vãn", "text": "Lâm Vãn không nhận trà sữa của người lạ."}],
}


def msg(turn: int, role: str, text: str, mode: str = "story") -> Message:
    return Message(
        story_id=1, turn_index=turn, role=role, mode=mode, raw_content=text, visible_content=text  # type: ignore[arg-type]
    )


def turn(mode: str = "story") -> list[Message]:
    return [msg(15, "user", "Có người mời tôi trà sữa, tôi khách sáo từ chối.", mode), msg(16, "assistant", REPLY, mode)]


async def run(fake: FakeLLM, **kw: object):  # type: ignore[no-untyped-def]
    args: dict[str, object] = dict(
        model="gemma4:12b",
        num_ctx=8192,
        card=make_card(),
        persona=make_persona(),
        story=make_story(),
        before=BEFORE,
        scene=SCENE,
        summary=None,
        turn=turn(),
    )
    args.update(kw)
    return await extract_turn(fake, **args)  # type: ignore[arg-type]


# ---- lời gọi ---------------------------------------------------------------------------------------


async def test_extract_turn_calls_chat_json_with_schema_and_options() -> None:
    fake = FakeLLM(json_replies=[GOOD])
    result = await run(fake, known_facts=["Lạc Dương và Lâm Vãn là thanh mai trúc mã"])
    call = fake.calls[0]
    assert call["model"] == "gemma4:12b"
    assert call["options"] == {"num_ctx": 8192, "num_predict": NUM_PREDICT, "temperature": TEMPERATURE}
    assert call["options"]["num_predict"] == 500 and call["options"]["temperature"] == 0.3
    assert call["schema"] == SCHEMA
    assert [m.role for m in call["messages"]] == ["system", "user"]
    # Chỉ giữ 2 thay đổi lớn nhất (nhung nhớ 3, rung động 2); thương mến 1 bị bỏ.
    d = result.relationship_delta
    assert (d.affection, d.attraction, d.obsession) == (0, 2, 3)
    assert result.memory == "Lạc Dương đuổi khéo người lạ mời Lâm Vãn trà sữa."
    assert result.memory_importance == 3
    assert [f.text for f in result.facts] == ["Lâm Vãn không nhận trà sữa của người lạ."]
    assert result.suggestions == []  # Phase 3b: trích xuất không sinh gợi ý
    assert result.scene.location is None and result.scene.time is None


def test_schema_has_no_max_length_and_bounded_ints() -> None:
    text = json.dumps(SCHEMA)
    assert "maxLength" not in text
    delta = SCHEMA["properties"]["relationship_delta"]["properties"]
    assert all(v == {"type": "integer", "minimum": -5, "maximum": 5} for v in delta.values())
    assert set(SCHEMA["required"]) == {"reason", "tone", "relationship_delta", "location", "time", "memory", "facts"}
    # `reason` rồi `tone` đứng đầu để model nghĩ và gọi tên lượt trước khi chấm số (grammar giữ thứ tự thuộc tính).
    assert list(SCHEMA["properties"])[:3] == ["reason", "tone", "relationship_delta"]
    assert SCHEMA["properties"]["reason"] == {"type": "string"}
    assert SCHEMA["properties"]["tone"] == {"type": "string", "enum": ["everyday", "warm", "hurt", "mixed"]}
    assert "suggestions" not in SCHEMA["properties"]
    assert "maxLength" not in json.dumps(OPENING_SCHEMA)
    assert set(OPENING_SCHEMA["required"]) == {"location", "time", "memory"}


def test_schema_caps_facts_so_output_fits_num_predict() -> None:
    # Lượt dày fact từng làm model ghi 14 fact, chạm NUM_PREDICT 500 ("length") và mất cả lượt trích xuất.
    from lyris.state.extract import MAX_FACTS

    assert SCHEMA["properties"]["facts"]["maxItems"] == MAX_FACTS == 3


async def test_extract_requires_assistant_message() -> None:
    with pytest.raises(ValueError):
        await run(FakeLLM(json_replies=[GOOD]), turn=[msg(1, "user", "Chào")])


async def test_extract_propagates_llm_error() -> None:
    with pytest.raises(LLMError):
        await run(FakeLLM(error=LLMError("mất kết nối")))


async def test_extract_turn_without_user_message() -> None:
    fake = FakeLLM(json_replies=[GOOD])
    result = await run(fake, turn=[msg(16, "assistant", REPLY)])
    assert result.memory and fake.calls[0]["schema"] == SCHEMA


# ---- prompt ----------------------------------------------------------------------------------------


def user_prompt(**kw: object) -> str:
    args: dict[str, object] = dict(
        card=make_card(), persona=make_persona(), story=make_story(), before=BEFORE, scene=SCENE, summary=None, turn=turn()
    )
    args.update(kw)
    # System (phần cố định) + user (phần đổi theo lượt), xem test_prompt_stable_part_first.
    return "\n\n".join(m.content for m in build_messages(**args))  # type: ignore[arg-type]


def test_prompt_vi_contains_state_turn_and_rules() -> None:
    text = user_prompt(summary="Hai người đi ăn lẩu.", known_facts=["Lâm Vãn thích trà sữa"])
    assert "thương mến 62, tin cậy 70, rung động 45, nhung nhớ 25, lo sợ mất mát 10, khoảng cách 15" in text
    assert "Cảnh hiện tại: Thư viện tầng ba, Buổi chiều." in text
    assert "Chuyện trước đó: Hai người đi ăn lẩu." in text
    assert "  - Lâm Vãn thích trà sữa" in text
    assert "Lâm Vãn: Có người mời tôi trà sữa" in text
    assert f"Lạc Dương: {REPLY}" in text  # raw_content, có Thought
    assert "[Thought: ...] là suy nghĩ thầm của Lạc Dương" in text
    assert "Không ghi nhận xét về tính cách" in text
    assert "mảng rỗng []" in text
    assert "Kiểu lượt: Story" in text
    assert "suggestions" not in text and "gợi ý" not in text
    assert "-5 đến 5" in text and "Phần lớn các lượt là chuyện thường ngày: để tất cả 0" in text


def test_prompt_vi_delta_rules_go_both_ways() -> None:
    # Phase 3b: chỉ số phải giảm được khi có chuyện xấu (ghen, nói dối, bị đẩy ra), không chỉ nhích lên.
    text = user_prompt()
    assert "- reason: viết TRƯỚC" in text and text.index("- reason:") < text.index("- relationship_delta:")
    assert text.index("- reason:") < text.index("- tone:") < text.index("- relationship_delta:")
    assert '"everyday": chuyện thường ngày như mọi khi' in text and "everyday thì mọi chỉ số đều 0" in text
    # Bị quên, lỡ hẹn, thờ ơ cũng là "hurt", kể cả khi nhân vật bỏ qua (verifier: quên sinh nhật -> aff +1).
    assert "quên điều quan trọng với Lạc Dương, lỡ hẹn, huỷ hẹn, thờ ơ" in text
    assert "Lâm Vãn quên mất ngày quan trọng của Lạc Dương, hoặc huỷ hẹn vào phút chót: hurt; affection -1" in text
    assert 'ngoài mặt cười bảo "không sao", vẫn dịu dàng hay dung túng thì trong lòng vẫn hụt hẫng' in text
    # Nhờ giảng bài như mọi chiều mà nhân vật tự rướn lại gần: model gọi là warm, rung động +2 (2/2). Tone theo
    # điều người chơi làm, không theo việc nhân vật vui đến đâu.
    assert "Chọn tone theo điều Lâm Vãn làm ở lượt này, không theo việc Lạc Dương vui hay rung động" in text
    assert "lỡ hẹn hay huỷ hẹn không báo trước" in text
    assert "không tăng vì những lần ngồi gần, giúp đỡ như mọi ngày" in text
    for key, label in (
        ("affection", "thương mến"), ("trust", "tin cậy"), ("attraction", "rung động"),
        ("obsession", "nhung nhớ/chiếm hữu"), ("fear", "lo sợ mất mát"), ("aversion", "khoảng cách/dè chừng"),
    ):
        line = next(ln for ln in text.splitlines() if ln.startswith(f"  - {key} ({label}):"))
        assert "tăng khi" in line and "giảm khi" in line, line
    assert "Lâm Vãn nói dối và bị Lạc Dương phát hiện: hurt; trust -3, aversion 2." in text
    assert "hurt; obsession 2, fear 2, trust -1 (không tăng affection)" in text
    assert "warm; trust 1, aversion -2" in text
    assert "trêu đùa như mọi khi: everyday; tất cả 0, kể cả khi Lạc Dương vẫn thấy vui" in text
    assert "kể cả khi Lạc Dương ngoài mặt vẫn dịu dàng bỏ qua, lòng tin vẫn sứt mẻ" in text
    assert "Nhân vật chiếm hữu, nhạy cảm hay đa nghi phản ứng mạnh hơn" in text
    # Tính cách và bí mật của nhân vật nằm trong prompt để chấm theo đúng con người đó.
    assert "Tính cách Lạc Dương: Lạnh lùng, ít nói" in text
    card = make_card(secrets="Thích Lâm Vãn từ lâu")
    assert "Bí mật của Lạc Dương: Thích Lâm Vãn từ lâu" in user_prompt(card=card)
    assert "Bí mật của" not in text  # card không có bí mật thì không có dòng này


def test_prompt_vi_dm_mode_follows_turn_mode() -> None:
    text = user_prompt(turn=turn(mode="dm"))
    assert "Kiểu lượt: Nhắn tin (DM)" in text
    assert "suggestions" not in text


def test_prompt_vi_scene_rules() -> None:
    # gemma4:12b hay để "" mãi (cảnh kẹt ở "Thư viện" khi hai người đã đi ăn, đã về nhà): dặn rõ khi nào phải đổi.
    text = user_prompt()
    assert "đã sang chỗ khác" in text and "phải ghi nơi hay lúc mới" in text
    assert "time là buổi hay mốc thời gian" in text
    # Câu cho lượt DM luôn có (luật nằm trong phần cố định, chung cho Story và DM).
    assert "Lượt nhắn tin (DM): location là nơi Lâm Vãn đang ở, chỉ khi tin nhắn nói rõ Lâm Vãn đang ở đâu lúc này" in text
    assert "nơi hẹn gặp sau này không phải cảnh hiện tại; không đoán nơi" in text
    # Không có nơi mẫu: gemma4:12b chép nguyên ví dụ cũ "Nhà <người chơi>" cho DM không nói nơi nào (3/3 lần).
    assert "Nhà Lâm Vãn" not in text


def test_prompt_unknown_scene_and_no_summary() -> None:
    text = user_prompt(scene=SceneState(), known_facts=[])
    assert "Cảnh hiện tại: chưa rõ." in text
    assert "Chuyện trước đó" not in text and "Điều đã biết" not in text


def test_prompt_en() -> None:
    msgs = build_messages(
        card=make_card(), persona=make_persona(), story=make_story(language="en"), before=BEFORE, scene=SceneState(),
        summary="They argued.", turn=turn(), known_facts=["Lâm Vãn likes milk tea"],
    )
    system, text = msgs[0].content, "\n\n".join(m.content for m in msgs)
    assert "English" in system and "JSON" in system
    assert "affection 62, trust 70, attraction 45, longing 25, fear of loss 10, distance 15" in text
    assert "Current scene: unknown." in text
    assert "Earlier in the story: They argued." in text
    assert "No judgments about personality" in text
    assert "Most turns are everyday: leave everything at 0" in text and "suggestions" not in text
    assert "- reason: write this FIRST" in text and "Lạc Dương's personality: Lạnh lùng" in text
    assert "up when" in text and "down when" in text and "Lâm Vãn lied and Lạc Dương finds out: hurt; trust -3" in text
    assert text.index("- reason:") < text.index("- tone:") < text.index("- relationship_delta:")
    assert '"everyday": ordinary as usual' in text and "cancels plans at the last minute: hurt; affection -1" in text
    assert "they are still let down inside and it still counts as hurtful" in text
    assert "Pick the tone by what Lâm Vãn did this turn, not by how happy or flustered Lạc Dương feels" in text
    assert "Already known" in text


@pytest.mark.parametrize("language", ["vi", "en"])
def test_prompt_general_sign_rule_matches_warm_sign(language: str) -> None:
    # Câu luật chung về dấu phải khớp WARM_SIGN và các ví dụ: chuyện làm đau thì obsession/fear/aversion TĂNG.
    # Câu cũ ("làm đau thì giảm (hoặc tăng khoảng cách)", "values still drop") khiến model chấm ghen thành
    # fear -2, obsession -2 dưới tone hurt, rồi pick_changes bỏ như nhiễu chiều ngược lại.
    text = user_prompt(story=make_story(language=language))
    rule = next(ln for ln in text.splitlines() if ln.startswith("- relationship_delta:"))
    if language == "vi":
        assert "ấm lòng thì affection, trust, attraction tăng còn obsession, fear, aversion giảm" in rule
        assert "làm xa cách thì ngược lại: affection, trust, attraction giảm còn obsession, fear, aversion tăng" in rule
        assert "chỉ số vẫn giảm" not in rule and "hoặc tăng khoảng cách" not in rule
    else:
        assert "warms the heart raises affection, trust and attraction and lowers obsession, fear and aversion" in rule
        assert "affection, trust and attraction drop, obsession, fear and aversion rise" in rule
        assert "values still drop" not in rule and "or raises distance" not in rule
    for key, sign in WARM_SIGN.items():
        assert is_warm(key, sign) and not is_warm(key, -sign)


@pytest.mark.parametrize("language", ["vi", "en"])
def test_prompt_stable_part_first(language: str) -> None:
    # §10.7: luật ghi (~2000 token) nằm SAU lượt cần đọc thì Ollama không bao giờ dùng lại được cache; đặt phần cố
    # định (vai trò, nhân vật, luật) vào system, giống hệt nhau giữa các lượt của một story, Story lẫn DM. Phần
    # đổi theo lượt (kiểu lượt, chỉ số, cảnh, tóm tắt, fact, lượt cần đọc) nằm ở user.
    story = make_story(language=language)
    a = build_messages(
        card=make_card(), persona=make_persona(), story=story, before=BEFORE, scene=SCENE, summary=None, turn=turn()
    )
    b = build_messages(
        card=make_card(), persona=make_persona(), story=story, before=BEFORE.model_copy(update={"affection": 10}),
        scene=SceneState(), summary="Hai người cãi nhau.", turn=turn(mode="dm"), known_facts=["Lâm Vãn thích mưa"],
    )
    assert a[0].content == b[0].content
    system, user = a[0].content, a[1].content
    assert "- relationship_delta:" in system and "- facts:" in system and "Lạnh lùng, ít nói" in system
    assert REPLY not in system and "62" not in system and "Thư viện tầng ba, Buổi chiều" not in system
    assert REPLY in user and "62" in user and "relationship_delta" not in user
    assert ("Kiểu lượt: Story" if language == "vi" else "Turn type: Story") in user
    assert ("Kiểu lượt: Nhắn tin" if language == "vi" else "Turn type: Text messages") in b[1].content
    # Output ngắn: reason một câu, JSON gọn một dòng (JSON thụt lề tốn ~35% token output).
    if language == "vi":
        assert "đúng một câu ngắn (dưới 25 từ)" in system and "JSON gọn trên một dòng" in system
    else:
        assert "one short sentence (under 25 words)" in system and "compact JSON on a single line" in system


@pytest.mark.parametrize("language", ["vi", "en"])
def test_prompt_recap_sizes_after_the_turn(language: str) -> None:
    # §10.7: luật ở system (xa lượt cần đọc) thì gemma4:12b chấm nhẹ tay (xin lỗi toàn ±1). Một dòng mức mẫu ở cuối
    # user, sau lượt cần đọc, đưa lại đúng mức. Không có ở system (giữ system giống hệt nhau để cache) và lời mở đầu.
    msgs = build_messages(
        card=make_card(), persona=make_persona(), story=make_story(language=language), before=BEFORE, scene=SCENE,
        summary=None, turn=turn(),
    )
    system, user = msgs[0].content, msgs[1].content
    recap = "Mức mẫu (" if language == "vi" else "Reference sizes ("
    assert recap not in system
    assert user.rindex(recap) > user.index(REPLY)
    assert user.endswith("trust tăng." if language == "vi" else "raises trust.")
    assert "aversion -2" in user.split(recap)[1]
    opening = build_messages(
        card=make_card(), persona=make_persona(), story=make_story(language=language), before=BEFORE,
        scene=SceneState(), summary=None, turn=[msg(0, "assistant", REPLY)],
    )
    assert recap not in "\n".join(m.content for m in opening)


def test_prompt_examples_use_card_names() -> None:
    text = user_prompt()
    for ex in example_texts(make_card(), make_persona(), "vi"):
        assert ex in text


# ---- xưng hô -----------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("self_term", "player_term", "gender", "expected"),
    [
        ("tớ", "cậu", "male", ("tớ", "cậu")),
        ("mình", "cậu", "female", ("mình", "cậu")),
        ("tao", "mày", "male", ("tao", "mày")),
        ("tôi", "bạn", "male", ("tôi", "bạn")),
        ("ta", "ngươi", "male", ("ta", "ngươi")),
        ("anh", "em", "male", ("em", "anh")),
        ("chị", "em", "female", ("em", "chị")),
        ("em", "anh", "female", ("anh", "em")),
        ("chú", "cháu", "male", ("cháu", "chú")),
        ("tôi", "em", "male", ("em", "anh")),
        ("tôi", "em", "female", ("em", "chị")),
        ("tôi", "cô", "male", ("tôi", "anh")),
        ("bổn vương", "nàng", "male", (None, "Lạc Dương")),
        ("", "cậu", "male", (None, "Lạc Dương")),
    ],
)
def test_player_address(self_term: str, player_term: str, gender: str, expected: tuple) -> None:
    card = make_card(gender=gender, address_terms=AddressTerms(self_term=self_term, player_term=player_term))
    assert player_address(card) == expected


def test_prompt_with_unknown_address_falls_back_to_name() -> None:
    card = make_card(address_terms=AddressTerms(self_term="bổn vương", player_term="nàng"))
    text = user_prompt(card=card)
    assert "Khi Lâm Vãn nói với Lạc Dương: gọi Lạc Dương là Lạc Dương." in text


# ---- kiểm tra kết quả ------------------------------------------------------------------------------


def test_validate_clamps_and_coerces_delta() -> None:
    data = {"relationship_delta": {"affection": 9, "trust": -12, "attraction": "3", "obsession": 2.6, "fear": True, "aversion": None}}
    d = validate(data, scene=SCENE).relationship_delta
    # Kẹp ±5; có cả tăng lẫn giảm nên giữ 3 thay đổi lớn nhất (rung động 3 thắng nhung nhớ 3 theo thứ tự khoá).
    assert (d.affection, d.trust, d.attraction, d.obsession, d.fear, d.aversion) == (5, -5, 3, 0, 0, 0)


Z = dict.fromkeys(("affection", "trust", "attraction", "obsession", "fear", "aversion"), 0)


def changed(raw: dict[str, int], tone: str | None = None) -> dict[str, int]:
    return {k: v for k, v in top_delta(raw, tone=tone).items() if v}


def test_top_delta_with_explicit_keep_keeps_largest_with_ties_in_key_order() -> None:
    assert top_delta({"affection": 1, "trust": 1, "attraction": 1}, keep=2) == {**Z, "affection": 1, "trust": 1}
    assert top_delta({"affection": 1, "fear": -3, "aversion": 2, "trust": 2}, keep=2) == {**Z, "trust": 2, "fear": -3}
    assert top_delta({}) == Z


def test_is_warm_follows_meaning_not_sign() -> None:
    assert is_warm("affection", 1) and is_warm("trust", 2) and is_warm("aversion", -1) and is_warm("fear", -2)
    assert not is_warm("obsession", 2) and not is_warm("aversion", 1) and not is_warm("trust", -1)


def test_top_delta_everyday_keeps_nothing() -> None:
    # gemma4:12b chấm "nhờ giảng bài như mọi chiều" là attraction +1 ở 4/4 lần: lượt thường ngày thì không đổi gì.
    assert changed({"attraction": 1}, "everyday") == {}
    assert changed({"affection": 2, "trust": -1}, "everyday") == {}


def test_top_delta_warm_turn_keeps_only_warm_changes() -> None:
    # Bênh vực trước lớp: obsession +1, fear +1 là nhiễu ngược chiều; aversion -1 ấm lòng nhưng chỉ giữ 2.
    raw = {"affection": 2, "trust": 1, "attraction": 3, "obsession": 1, "fear": 1, "aversion": -1}
    assert changed(raw, "warm") == {"affection": 2, "attraction": 3}
    assert changed(raw) == {"affection": 2, "attraction": 3}  # không có tone: đoán ra "warm"
    assert changed({"trust": 2, "aversion": -2, "affection": 1}, "warm") == {"trust": 2, "aversion": -2}
    # Model nói warm mà chỉ cho số tổn thương: mâu thuẫn, không giữ gì.
    assert changed({"obsession": 2}, "warm") == {}


def test_top_delta_warm_plus_one_drift_keeps_one() -> None:
    # "affection +1, attraction +1" ở mọi lượt làm cảm xúc trôi dần lên: đều ±1 ấm lòng thì chỉ giữ một.
    assert changed({"affection": 1, "attraction": 1}) == {"affection": 1}
    assert changed({"affection": 1, "trust": 1, "attraction": 1}) == {"affection": 1}
    # aversion -1 là ấm lòng (không phải "chiều ngược lại"): aff +1, ave -1 vẫn chỉ giữ một.
    # Cái được giữ chọn theo nghĩa: dấu hiệu làm lành (khoảng cách, lo sợ, nhung nhớ giảm) trước thương mến +1.
    assert changed({"fear": -1, "aversion": -1}) == {"aversion": -1}
    assert changed({"affection": 1, "aversion": -1}, "warm") == {"aversion": -1}
    assert changed({"affection": 1, "obsession": -1, "fear": -1}, "warm") == {"fear": -1}
    # Xin lỗi mà model chỉ cho toàn ±1 (gemma4:12b thật): giữ khoảng cách -1, không phải thương mến +1.
    assert changed({"affection": 1, "trust": 1, "attraction": 1, "aversion": -1}, "warm") == {"aversion": -1}
    # Không có dấu hiệu làm lành: theo thứ tự khoá.
    assert changed({"trust": 1, "attraction": 1}, "warm") == {"trust": 1}


def test_top_delta_hurt_turn_keeps_three_hurtful_changes() -> None:
    # Ghen: chiếm hữu và lo sợ tăng, tin cậy giảm; attraction +1 lúc đang ghen là nhiễu.
    raw = {"trust": -1, "attraction": 1, "obsession": 2, "fear": 2}
    assert changed(raw, "hurt") == {"trust": -1, "obsession": 2, "fear": 2}
    assert changed(raw) == {"trust": -1, "obsession": 2, "fear": 2}
    assert changed({"affection": 1, "trust": -1, "obsession": 2, "fear": 2}) == {"trust": -1, "obsession": 2, "fear": 2}
    # Toàn ±1 nhưng đều tổn thương (bị lừa nhẹ): giữ cả ba, không chọn bừa một cái theo thứ tự khoá.
    assert changed({"trust": -1, "attraction": 1, "obsession": 1, "fear": 1}, "hurt") == {
        "trust": -1, "obsession": 1, "fear": 1
    }
    assert changed({"affection": -1, "obsession": 1, "fear": 1}) == {"affection": -1, "obsession": 1, "fear": 1}
    # Bị đẩy ra: thương mến -2, lo sợ +2, khoảng cách +2.
    assert changed({"affection": -2, "trust": -1, "attraction": -1, "obsession": 1, "fear": 2, "aversion": 2}) == {
        "affection": -2, "fear": 2, "aversion": 2
    }
    assert changed({"trust": -3, "aversion": 2, "affection": -1, "fear": 1}, "hurt") == {
        "affection": -1, "trust": -3, "aversion": 2
    }
    # Cùng cỡ thì tin cậy giảm đứng trước thương mến -1 (con số model rắc vào mọi lượt tổn thương). gemma4:12b thật,
    # ghen / huỷ hẹn để đi với người khác: trước đây còn affection -1, obsession 2, fear 2 (mất trust -1).
    raw = {"affection": -1, "trust": -1, "attraction": -1, "obsession": 2, "fear": 2, "aversion": 1}
    assert changed(raw, "hurt") == {"trust": -1, "obsession": 2, "fear": 2}
    assert changed({"affection": -1, "trust": -1, "obsession": 1, "fear": 1, "aversion": 1}, "hurt") == {
        "affection": -1, "trust": -1, "obsession": 1
    }
    assert changed({"attraction": 2, "affection": -1, "trust": -1}, "mixed") == {"trust": -1, "attraction": 2}
    # Quên sinh nhật mà model vẫn cho affection +1: nói hurt thì phần ấm lòng bị bỏ.
    assert changed({"affection": 1, "trust": -1, "aversion": 1}, "hurt") == {"trust": -1, "aversion": 1}
    assert changed({"affection": 1}, "hurt") == {}


def test_top_delta_mixed_keeps_both_sides() -> None:
    raw = {"trust": -3, "affection": 2, "fear": 2, "aversion": 1}
    assert changed(raw, "mixed") == {"trust": -3, "affection": 2, "fear": 2}
    assert changed(raw) == {"trust": -3, "affection": 2, "fear": 2}  # cả hai phía đều từ 2: đoán "mixed"
    # Phía còn lại chỉ ±1: vẫn giữ cái lớn nhất của mỗi phía, ±1 lẻ khác thì bỏ.
    assert changed({"trust": 1, "obsession": 2, "fear": 1}, "mixed") == {"trust": 1, "obsession": 2}
    # Nói mixed mà chỉ có một phía: xử như phía đó.
    assert changed({"affection": 1, "attraction": 1}, "mixed") == {"affection": 1}
    # Tone lạ: đoán theo số.
    assert changed({"obsession": 2, "trust": -1}, "ghen") == {"trust": -1, "obsession": 2}


def test_validate_creeping_deltas_are_cut() -> None:
    # Model nhỏ hay cho mọi chỉ số cùng +1/+2 mỗi lượt: chỉ 2 thay đổi ấm lòng được giữ, nhiễu ngược chiều bị bỏ.
    data = {"relationship_delta": {"affection": 2, "trust": 1, "attraction": 2, "obsession": 1, "fear": 1, "aversion": -1}}
    d = validate(data, scene=SCENE).relationship_delta
    assert d.model_dump() == {**Z, "affection": 2, "attraction": 2}
    data = {"tone": "everyday", "relationship_delta": {"affection": 1, "attraction": 1}}
    assert validate(data, scene=SCENE).relationship_delta.model_dump() == Z
    data = {"tone": " Hurt ", "relationship_delta": {"affection": 1, "trust": -1, "obsession": 2}}
    assert validate(data, scene=SCENE).relationship_delta.model_dump() == {**Z, "trust": -1, "obsession": 2}


def test_validate_drops_reason() -> None:
    r = validate({"reason": "Lạc Dương ghen.", "relationship_delta": {"obsession": 2}}, scene=SCENE)
    assert r.relationship_delta.obsession == 2
    assert "Lạc Dương ghen" not in r.model_dump_json()


def test_validate_garbage_never_raises() -> None:
    for data in (None, [], "x", {"relationship_delta": "x", "memory": 5, "facts": "x", "suggestions": {"a": 1}}):
        r = validate(data, scene=SCENE)
        assert r.memory is None and r.facts == [] and r.suggestions == []


@pytest.mark.parametrize(
    "raw",
    [
        '{"relationship_delta": {"trust": Infinity, "fear": -Infinity, "affection": NaN}}',
        '{"relationship_delta": {"trust": 1e999, "fear": "inf", "affection": "-Infinity"}}',
        '{"relationship_delta": {"trust": 2}, "memory": {"text": "Lạc Dương cười.", "importance": "Infinity"}}',
        '{"relationship_delta": {"trust": 2}, "memory": {"text": "Lạc Dương cười.", "importance": 1e999}}',
    ],
)
def test_validate_non_finite_numbers_never_raise(raw: str) -> None:
    # json.loads (đường fallback khi model chạy không có grammar) nhận Infinity/NaN/1e999: round(inf) từng
    # raise OverflowError làm job extract thất bại sau mọi lần thử. Giờ coi như giá trị hỏng (mặc định).
    r = validate(json.loads(raw), scene=SCENE)
    d = r.relationship_delta
    assert (d.affection, d.fear) == (0, 0) and d.trust in (0, 2)
    if r.memory is not None:
        assert r.memory_importance == 3


def test_validate_scene_unchanged_and_none_values() -> None:
    r = validate({"location": "  thư viện tầng ba. ", "time": "Chiều tối"}, scene=SCENE)
    assert r.scene.location is None  # trùng cảnh hiện tại
    assert r.scene.time == "Chiều tối"
    r = validate({"location": "không rõ", "time": "unknown"}, scene=SceneState())
    assert r.scene.location is None and r.scene.time is None
    r = validate({"location": "Quán lẩu", "time": ""}, scene=SceneState())
    assert r.scene.location == "Quán lẩu"


def test_validate_memory() -> None:
    r = validate({"memory": {"text": "  Lạc Dương   cười. ", "importance": 9}}, scene=SCENE)
    assert r.memory == "Lạc Dương cười." and r.memory_importance == 5
    r = validate({"memory": {"text": "", "importance": 0}}, scene=SCENE)
    assert r.memory is None and r.memory_importance == 1
    assert validate({"memory": "Một câu."}, scene=SCENE).memory == "Một câu."


def test_validate_facts_dedup_limit_and_judgments() -> None:
    data = {
        "facts": [
            {"subject": "Lâm Vãn", "text": "Lâm Vãn thích trà sữa."},
            {"subject": "Lâm Vãn", "text": "lâm vãn thích trà sữa"},  # trùng trong cùng lần
            {"subject": "Lạc Dương", "text": "Lạc Dương là thanh mai trúc mã của Lâm Vãn!"},  # trùng fact đã có
            {"subject": "Lạc Dương", "text": "Lạc Dương có tính chiếm hữu cao."},  # nhận xét tính cách
            {"subject": "", "text": "  "},
            "Mẹ Lâm Vãn hay hỏi thăm Lạc Dương.",
            {"subject": "Lạc Dương", "text": "Lạc Dương không ăn được hành."},
            {"subject": "Lạc Dương", "text": "Lạc Dương học ngành kiến trúc."},
            {"subject": "Lạc Dương", "text": "Lạc Dương có xe đạp."},
        ]
    }
    r = validate(data, scene=SCENE, known_facts=["Lạc Dương là thanh mai trúc mã của Lâm Vãn"])
    assert [f.text for f in r.facts] == [
        "Lâm Vãn thích trà sữa.",
        "Mẹ Lâm Vãn hay hỏi thăm Lạc Dương.",
        "Lạc Dương không ăn được hành.",
    ]
    assert r.facts[1].subject == ""


def test_validate_drops_fact_that_repeats_the_memory() -> None:
    data = {
        "memory": {"text": "Lạc Dương hứa sẽ đưa Lâm Vãn đi Cáp Nhĩ Tân vào ngày 20 tháng 12.", "importance": 4},
        "facts": [
            {"subject": "Lạc Dương", "text": "Lạc Dương hứa sẽ đưa Lâm Vãn đi Cáp Nhĩ Tân vào ngày 20 tháng 12"},
            {"subject": "Lâm Vãn", "text": "Sinh nhật Lâm Vãn là ngày 20 tháng 12."},
        ],
    }
    r = validate(data, scene=SCENE)
    assert r.memory is not None and [f.text for f in r.facts] == ["Sinh nhật Lâm Vãn là ngày 20 tháng 12."]


def test_validate_drops_copied_prompt_examples() -> None:
    ex = example_texts(make_card(), make_persona(), "vi")
    data = {"memory": {"text": ex[0], "importance": 3}, "facts": [{"subject": "x", "text": ex[1]}]}
    r = validate(data, scene=SCENE, examples=ex)
    assert r.memory is None and r.facts == []


def test_validate_ignores_suggestions_from_model() -> None:
    r = validate({"suggestions": ["Đi ăn tối thôi", "Gợi ý hai"]}, scene=SCENE, player_texts=["x"])
    assert r.suggestions == []


# ---- lời mở đầu (lượt 0, Phase 3b) -------------------------------------------------------------------


def test_is_opening() -> None:
    assert is_opening([msg(0, "assistant", "Chào")])
    assert not is_opening(turn())


async def test_extract_opening_scene_and_memory_only() -> None:
    data = {
        "relationship_delta": {"affection": 5},
        "location": "Sân bóng rổ",
        "time": "Chiều",
        "memory": {"text": "Lạc Dương đứng đợi Lâm Vãn dưới gốc ngô đồng với hai cốc trà sữa.", "importance": 2},
        "facts": [{"subject": "Lạc Dương", "text": "Lạc Dương thích trà sữa."}],
    }
    fake = FakeLLM(json_replies=[data])
    result = await run(fake, turn=[msg(0, "assistant", REPLY)], before=BEFORE, scene=SceneState())
    assert fake.calls[0]["schema"] == OPENING_SCHEMA
    text = "\n\n".join(m.content for m in fake.calls[0]["messages"])
    assert "Lời mở đầu của story" in text and "relationship_delta" not in text and "facts" not in text
    assert result.relationship_delta.model_dump() == dict.fromkeys(result.relationship_delta.model_dump(), 0)
    assert result.facts == []
    assert (result.scene.location, result.scene.time) == ("Sân bóng rổ", "Chiều")
    assert result.memory and result.memory_importance == 2


def test_opening_prompt_en() -> None:
    msgs = build_messages(
        card=make_card(), persona=make_persona(), story=make_story(language="en"), before=BEFORE, scene=SceneState(),
        summary=None, turn=[msg(0, "assistant", "Hi.")],
    )
    text = "\n\n".join(m.content for m in msgs)
    assert "Opening of the story" in text and "relationship_delta" not in text and "facts:" not in text
    assert "memory:" in text and "location, time:" in text


def test_normalize() -> None:
    assert normalize("  Lâm Vãn   THÍCH trà sữa!! ") == "lâm vãn thích trà sữa"
    assert normalize(unicodedata.normalize("NFD", "Lâm Vãn")) == normalize("Lâm Vãn")
