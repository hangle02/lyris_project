"""Test khối C/F có state (Phase 3) và hồi quy: `state=None` cho đúng prompt như trước Phase 3."""
from __future__ import annotations

import hashlib

import pytest

from lyris.models import MemoryHit, PromptState, SceneState
from lyris.prompt.builder import STATE_TOKEN_LIMIT, PromptBudget, build_prompt, state_lines
from lyris.prompt.templates import PromptContext, get_template
from lyris.prompt.tokens import estimate_tokens
from tests.test_prompt import GREETING, assistant, make_card, make_persona, make_story, user

# ---- hồi quy: state=None ----------------------------------------------------------------------

# sha256 của BuiltPrompt.model_dump_json() đo bằng builder trước Phase 3 (2026-11-13). Nếu cố ý đổi
# template/style thì tính lại; nếu không, hash lệch nghĩa là prompt cũ (Studio, harness) đã bị đổi.
#
# Đổi có chủ ý 2026-11-15 (docs/compliance.md §1): khối A của story và nhắn tin (vi + en) có thêm đúng một dòng
# luật an toàn nội dung (`safety_rule`, ngay trước dòng "Chỉ dùng tiếng Việt" / "English only"). Đã kiểm: bỏ dòng
# đó khỏi template thì cả 7 kịch bản cho lại đúng hash cũ (vi_story c696e4d7…, vi_story_summary 54f83049…,
# vi_dm 2ec6392f…, en_first_end 1d9a5f8b…, en_dm 5b2600ea…, vi_long_cut d37f0d4f…, vi_long_full d5ac01a9…),
# nên ngoài dòng mới không có gì khác đổi. `test_safety_rule_is_the_only_change` bên dưới kiểm lại điều này.
GOLDEN = {
    "vi_story": "2c9ca73223add1cf39ccc4869a92185f2e0468273882fe050f988b6fc5c5b929",
    "vi_story_summary": "3d391be248da8715e6c8baaef30b59a43b78b0719610454e30868d57600a350f",
    "vi_dm": "2431303e7962b6d99e54d8b2c760b748f93b7b7d1c3c426deb7ebcc8b1957908",
    "en_first_end": "f449bffbba0d7848170ae490b47155d84cc5886a7e3109357e03e036408f8f76",
    "en_dm": "7b4c2f3a828c6562fd34a0a1e77c2841fc1665eab73b31cd87d54232ed9011eb",
    "vi_long_cut": "ec3dbed9495a64caccac82be10183eb5e151b9a4e73befedafad056fe5e7fc23",
    "vi_long_full": "14eb23267881f31418b1c7e4b6aa55412a3f5d49010894a2e1e8c3ee8bf387ff",
}

# Hash trước khi có luật an toàn (2026-11-13): bỏ dòng `safety_rule` thì phải cho lại đúng các hash này.
GOLDEN_BEFORE_SAFETY = {
    "vi_story": "c696e4d7c52a310201dc5bc4bd75b5b9fdb4f60dca502c56fc954bdaedfa4df2",
    "vi_story_summary": "54f83049986dde4e57df98c8d3010b1de532648930fe9afe4099d21189bbc80d",
    "vi_dm": "2ec6392fba702e46c452369e6fd5cfb662b40698173354979c7e7cfbbdad2bb0",
    "en_first_end": "1d9a5f8b103f0cc96e625ced6d57ef94c6c9589a136c8c16fde508dff88f0173",
    "en_dm": "5b2600eaca8fd6558d2222dbfb0a19293db6306795f3a5d244b3db647d14207c",
    "vi_long_cut": "d37f0d4faadd1a1ac9833c7a3b8ea0b4d2d50efed72204a9488e1fb0f360a2b8",
    "vi_long_full": "d5ac01a95c769f19a88491d36cb5c08efb342b0404ab01709c9c94be889d3d20",
}


def long_history() -> list:
    hist = [assistant(0, GREETING)]
    for t in range(1, 41, 2):
        hist.append(user(t, f"*Tớ kéo tay áo cậu ấy.* Lượt {t} nè, đi ăn kem không? ((cho trời mưa nhẹ))"))
        hist.append(
            assistant(
                t + 1,
                f"[Thought: Lại bày trò.]\nLạc Dương khẽ cười, lượt {t + 1}. \"Đi thì đi.\" "
                + "Anh nhìn cô rất lâu. " * 12,
            )
        )
    hist.append(user(41, "Tớ đói rồi."))
    return hist


def scenarios() -> dict:
    card, persona = make_card(), make_persona()
    dm_hist = [
        assistant(0, "Ngủ chưa?"),
        user(1, "chưa nè"),
        assistant(2, "Sao còn thức\nNgủ sớm đi"),
        user(3, "cậu còn thức không 🥺"),
    ]
    return {
        "vi_story": (card, persona, make_story(), [assistant(0, GREETING), user(1, "Tớ tới rồi!")], None),
        "vi_story_summary": (
            card,
            persona,
            make_story(scene_summary="Hai người vừa tan học."),
            [assistant(0, GREETING), user(1, "Tớ tới rồi!"), assistant(2, "Anh gật đầu."), user(3, "((để anh ấy chủ động))")],
            None,
        ),
        "vi_dm": (card, persona, make_story(mode="dm"), dm_hist, None),
        "en_first_end": (
            card,
            persona,
            make_story(language="en", pov="first", thought_style="end"),
            [assistant(0, "Hi."), user(1, "Hey ((make him blush))")],
            None,
        ),
        "en_dm": (card, persona, make_story(language="en", mode="dm"), dm_hist, None),
        "vi_long_cut": (card, persona, make_story(), long_history(), PromptBudget(num_ctx=3500)),
        "vi_long_full": (card, persona, make_story(), long_history(), None),
    }


def digest(built) -> str:  # type: ignore[no-untyped-def]
    # Trường thêm ở Phase 3b (summary_upto_turn) và Phase 4 (lore_head, open_last, lore_used) không thuộc nội dung
    # prompt: bỏ khỏi hash.
    exclude = {"summary_upto_turn", "lore_head", "open_last", "lore_used"}
    return hashlib.sha256(built.model_dump_json(exclude=exclude).encode()).hexdigest()


@pytest.mark.parametrize("name", sorted(GOLDEN))
def test_state_none_is_byte_identical_to_pre_phase3(name: str) -> None:
    card, persona, story, history, budget = scenarios()[name]
    built = build_prompt(card, persona, story, history, budget=budget)
    assert digest(built) == GOLDEN[name]
    assert digest(build_prompt(card, persona, story, history, budget=budget, state=None)) == GOLDEN[name]


@pytest.mark.parametrize("name", sorted(n for n in GOLDEN if n != "vi_long_cut"))
def test_empty_state_changes_nothing(name: str) -> None:
    card, persona, story, history, budget = scenarios()[name]
    built = build_prompt(card, persona, story, history, budget=budget, state=PromptState())
    assert digest(built) == GOLDEN[name]


def test_safety_rule_is_the_only_change(monkeypatch: pytest.MonkeyPatch) -> None:
    """Template không có dòng luật an toàn (docs/compliance.md §1) cho lại đúng prompt cũ: lần đổi hash 2026-11-15
    chỉ do dòng đó. Dựng lại lớp template từ mã nguồn đã bỏ `safety_rule(c),` (không sửa file)."""
    import types

    from lyris.prompt.templates import en, vi

    for mod in (vi, en):
        src = open(mod.__file__, encoding="utf-8").read()
        assert src.count("            safety_rule(c),\n") == 2  # story + nhắn tin
        clone = types.ModuleType(mod.__name__ + "_no_safety")
        exec(compile(src.replace("            safety_rule(c),\n", ""), mod.__file__, "exec"), clone.__dict__)
        monkeypatch.setattr(mod, "TEMPLATE", clone.TEMPLATE)
    for name, (card, persona, story, history, budget) in scenarios().items():
        assert digest(build_prompt(card, persona, story, history, budget=budget)) == GOLDEN_BEFORE_SAFETY[name], name


def test_empty_state_trims_with_fixed_reserve() -> None:
    """Lịch sử đã đầy: có state thì phép kiểm tra cắt dùng phần dự phòng cố định cho F (kể cả
    STATE_TOKEN_LIMIT), nên cửa sổ có thể bắt đầu muộn hơn bản state=None, nhưng phần còn lại y hệt."""
    card, persona, story, history, budget = scenarios()["vi_long_cut"]
    plain = build_prompt(card, persona, story, history, budget=budget)
    empty = build_prompt(card, persona, story, history, budget=budget, state=PromptState())
    assert empty.dropped_turns >= plain.dropped_turns > 0
    assert empty.messages[0] == plain.messages[0]
    assert empty.messages[-1] == plain.messages[-1]
    assert empty.token_estimate["total"] <= plain.token_estimate["total"]


# ---- state trong prompt ---------------------------------------------------------------------------

DIRECTIVE = "Lạc Dương rất thương mến và tin cậy Lâm Vãn; đang rung động nhưng vẫn giữ trong lòng, chưa nói ra."


def hit(memory_id: int, turn: int, text: str, kind: str = "memory", score: float = 1.0) -> MemoryHit:
    return MemoryHit(memory_id=memory_id, turn_index=turn, kind=kind, text=text, score=score)  # type: ignore[arg-type]


def full_state(**kw: object) -> PromptState:
    data: dict[str, object] = dict(
        summary="Lạc Dương và Lâm Vãn đã cãi nhau rồi làm lành ở quán lẩu.",
        directive=DIRECTIVE,
        scene=SceneState(location="Thư viện tầng ba", time="chiều tối"),
        memories=[
            hit(1, 2, "Lâm Vãn hứa mời Lạc Dương ăn tối"),
            hit(2, 4, "Lạc Dương không ăn được cay", kind="fact"),
        ],
    )
    data.update(kw)
    return PromptState.model_validate(data)


def two_turn_history() -> list:
    # Lượt 0..4 bị cắt bằng cách chỉ truyền lịch sử từ lượt 5 (cửa sổ bắt đầu ở lượt 5).
    return [assistant(5, "Anh đặt cuốn sách xuống."), user(6, "Tớ tới rồi!")]


def test_summary_goes_into_block_c_after_scene_summary() -> None:
    story = make_story(scene_summary="Hai người vừa tan học.")
    built = build_prompt(make_card(), make_persona(), story, two_turn_history(), state=full_state())
    system = built.messages[0].content
    assert system.endswith(
        "Tóm tắt những gì đã xảy ra: Hai người vừa tan học.\n\n"
        "Những gì đã xảy ra trước đó: Lạc Dương và Lâm Vãn đã cãi nhau rồi làm lành ở quán lẩu."
    )
    plain = build_prompt(make_card(), make_persona(), story, two_turn_history())
    assert built.token_estimate["C"] > plain.token_estimate["C"]


def test_system_message_stable_when_only_turn_state_changes() -> None:
    a = build_prompt(make_card(), make_persona(), make_story(), two_turn_history(), state=full_state())
    b = build_prompt(
        make_card(),
        make_persona(),
        make_story(),
        two_turn_history(),
        state=full_state(directive="Khác.", scene=SceneState(location="Sân bóng"), memories=[]),
    )
    assert a.messages[0].content == b.messages[0].content


def test_block_f_state_lines_before_turn_rules_vi() -> None:
    built = build_prompt(make_card(), make_persona(), make_story(), two_turn_history(), state=full_state())
    last = built.messages[-1].content
    note = last[last.index("[Ghi chú cho người dẫn truyện") :]
    lines = note.split("\n")
    assert lines[1] == "- Cảnh hiện tại: Thư viện tầng ba, chiều tối."
    assert lines[2] == f"- Thái độ của Lạc Dương lúc này: {DIRECTIVE}"
    assert lines[3] == "- Chuyện cũ Lạc Dương còn nhớ (chỉ nhắc khi hợp cảnh, không kể lại nguyên văn):"
    assert lines[4] == "  + Lâm Vãn hứa mời Lạc Dương ăn tối."
    assert lines[5] == "- Điều Lạc Dương biết:"
    assert lines[6] == "  + Lạc Dương không ăn được cay."
    assert lines[7].startswith("- Tiếp nối trực tiếp")
    assert not any(ch.isdigit() for ch in "\n".join(lines[1:3]))


def test_block_f_state_lines_en_and_dm() -> None:
    story = make_story(language="en", mode="dm")
    built = build_prompt(make_card(), make_persona(), story, two_turn_history(), state=full_state(directive="Lạc Dương is fond of Lâm Vãn."))
    last = built.messages[-1].content
    assert "[Note for the writer, not a message from Lâm Vãn]\n- Current scene: Thư viện tầng ba, chiều tối.\n" in last
    assert "- Lạc Dương's attitude right now: Lạc Dương is fond of Lâm Vãn.\n" in last
    assert "- Things Lạc Dương remembers from earlier" in last
    assert "- What Lạc Dương knows:\n  + Lạc Dương không ăn được cay.\n- Reply directly" in last
    assert "Earlier in the story: Lạc Dương và Lâm Vãn" in built.messages[0].content


def test_repetition_avoid_lines_kept_with_state() -> None:
    history = [
        assistant(0, GREETING),
        user(1, "Chào"),
        assistant(2, "Lạc Dương khẽ cười. Anh đứng dậy."),
        user(3, "Đi thôi"),
    ]
    built = build_prompt(make_card(), make_persona(), make_story(), history, state=full_state())
    last = built.messages[-1].content
    assert "Các lượt gần đây mở đầu bằng: «Lạc Dương khẽ cười.»" in last
    assert last.index("- Thái độ của") < last.index("Các lượt gần đây")


def test_memories_inside_window_are_skipped_facts_kept() -> None:
    history = [assistant(0, GREETING), user(1, "Chào"), assistant(2, "Ừ."), user(3, "Đi thôi")]
    state = full_state(
        memories=[hit(1, 2, "Ký ức trong cửa sổ"), hit(2, 1, "Fact cũ", kind="fact")],
    )
    built = build_prompt(make_card(), make_persona(), make_story(), history, state=state)
    last = built.messages[-1].content
    assert built.dropped_turns == 0
    assert "Ký ức trong cửa sổ" not in last and "Chuyện cũ" not in last
    assert "  + Fact cũ." in last


def test_memories_before_window_after_truncation() -> None:
    history = long_history()
    memories = [hit(i, i, f"Ký ức số {chr(64 + i)}", score=10 - i) for i in range(1, 6)]
    memories.append(hit(99, 40, "Ký ức mới trong cửa sổ", score=100))
    built = build_prompt(
        make_card(), make_persona(), make_story(), history, budget=PromptBudget(num_ctx=3500), state=full_state(memories=memories)
    )
    first_turn = history[built.dropped_turns].turn_index
    assert built.dropped_turns > 0 and first_turn > 5
    last = built.messages[-1].content
    # 3 ký ức hạng cao nhất trước cửa sổ, viết theo thứ tự thời gian.
    assert "  + Ký ức số A.\n  + Ký ức số B.\n  + Ký ức số C.\n" in last
    assert "Ký ức số D" not in last and "trong cửa sổ" not in last


def test_max_three_facts_and_dedup() -> None:
    facts = [hit(i, 0, f"Fact {chr(64 + i)}", kind="fact") for i in range(1, 6)]
    facts.insert(1, hit(50, 0, "fact  a", kind="fact"))
    built = build_prompt(make_card(), make_persona(), make_story(), two_turn_history(), state=full_state(memories=facts))
    last = built.messages[-1].content
    assert "  + Fact A.\n  + Fact B.\n  + Fact C.\n" in last
    assert "Fact D" not in last and "fact  a" not in last


def test_fact_repeating_a_shown_memory_is_dropped() -> None:
    # Model hay ghi cùng một câu (lời hứa) vào cả ký ức lẫn fact: in một lần ở "Chuyện cũ" thôi.
    same = "Lạc Dương hứa đưa Lâm Vãn đi Cáp Nhĩ Tân"
    hits = [hit(1, 2, same), hit(2, 2, same, kind="fact"), hit(3, 3, "Lâm Vãn thích trà sữa", kind="fact")]
    built = build_prompt(make_card(), make_persona(), make_story(), two_turn_history(), state=full_state(memories=hits))
    last = built.messages[-1].content
    assert last.count("Cáp Nhĩ Tân") == 1
    assert "  + Lâm Vãn thích trà sữa." in last


def test_state_lines_capped_near_350_tokens() -> None:
    card, persona, story = make_card(), make_persona(), make_story()
    ctx = PromptContext(card=card, persona=persona, story=story, style="")
    long = "Một chuyện rất dài " * 40
    hits = [hit(i, 1, f"{long} {i}") for i in range(1, 4)] + [hit(10 + i, 1, f"{long} f{i}", kind="fact") for i in range(1, 4)]
    lines = state_lines(get_template("vi"), ctx, full_state(memories=hits), first_turn=10)
    assert estimate_tokens("\n".join(lines)) <= STATE_TOKEN_LIMIT
    assert any(line.startswith("- Thái độ") for line in lines)
    assert any(line.startswith("  + ") for line in lines)  # vẫn giữ được ít nhất một mục
    assert all(len(line) < 300 for line in lines)  # mỗi mục bị cắt ngắn


def test_budget_accounts_for_larger_f() -> None:
    history = long_history()
    # 2026-11-15: 3500 -> 3600. Khối A có thêm luật an toàn nội dung (~115 token, docs/compliance.md §1): với 3500,
    # A + B + F dài đã chiếm gần hết chỗ, không còn cửa sổ lịch sử hợp lệ nào vừa giới hạn.
    budget = PromptBudget(num_ctx=3600)
    plain = build_prompt(make_card(), make_persona(), make_story(), history, budget=budget)
    long = "Một chuyện rất dài " * 10
    hits = [hit(i, i, f"{long} {i}") for i in range(1, 4)] + [hit(10 + i, 1, f"{long} f{i}", kind="fact") for i in range(1, 4)]
    built = build_prompt(make_card(), make_persona(), make_story(), history, budget=budget, state=full_state(memories=hits))
    limit = budget.num_ctx - budget.reply_tokens_story - budget.safety_tokens
    assert built.token_estimate["total"] <= limit
    assert built.token_estimate["F"] > plain.token_estimate["F"]
    assert built.dropped_turns >= plain.dropped_turns


def test_scene_partial_and_no_scene() -> None:
    built = build_prompt(
        make_card(), make_persona(), make_story(), two_turn_history(),
        state=PromptState(scene=SceneState(location="Sân bóng")),
    )
    assert "- Cảnh hiện tại: Sân bóng.\n" in built.messages[-1].content
    built = build_prompt(make_card(), make_persona(), make_story(), two_turn_history(), state=PromptState(scene=SceneState()))
    assert "Cảnh hiện tại" not in built.messages[-1].content


def test_state_never_leaks_double_parens() -> None:
    state = full_state(memories=[hit(1, 1, "Lâm Vãn viết ((chỉ đạo)) lạ", kind="fact")])
    built = build_prompt(make_card(), make_persona(), make_story(), two_turn_history(), state=state)
    assert all("((" not in m.content and "))" not in m.content for m in built.messages)
