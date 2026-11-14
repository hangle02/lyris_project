"""Phase 4 (docs/phase4.md §6.3-§6.5): khối D trong prompt, phần dự phòng, cache của Ollama và prefill.

- Không có lore (hoặc PromptLore rỗng, reserve 0): prompt giống hệt Phase 3 từng byte.
- Lore không bao giờ nằm trong system; system giữ nguyên giữa các lượt gợi ra mục khác nhau.
- Khối D ở đầu message user cuối: mở -> carried -> fresh -> đóng -> lời người chơi -> F.
- D không tính vào E; điểm bắt đầu cửa sổ không phụ thuộc lượt này gợi ra mục nào (phần dự phòng cố định).
- Prefill: mặc định `messages[:-1]` đúng như prompt thật; bật `LORE_PREFILL_OPEN_TURN` thì văn bản raw
  (`render_prefix(..., open_last=True)`) là chuỗi đầu của văn bản prompt thật, kể cả lượt cửa sổ dịch.
"""
from __future__ import annotations

from lyris.db.repo import ANY_ACCOUNT

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from lyris.api.app import create_app
from lyris.llm.render import render_prefix
from lyris.lore import select as lore_select
from lyris.lore.select import LORE_TOKEN_LIMIT, block_lines, lore_for_history
from lyris.models import LoreEntry, Message, Persona, PromptLore, PromptState, Story, SummaryPoint
from lyris.prompt.builder import PromptBudget, build_prompt
from lyris.prompt.templates import PromptContext, get_template
from lyris.studio.card_v2 import import_card
from lyris.studio.stories import default_settings
from tests.test_phase3_e2e import ScriptedLLM, first_story, make_settings, repo_of, send, worker_of
from tests.test_phase3b_e2e import long_reply
from tests.test_prompt import GREETING, assistant, make_card, make_persona, make_story, user
from tests.authutil import owner_client

WORLDS = Path(__file__).resolve().parents[2] / "worlds"

ENTRIES = [
    LoreEntry(id=1, card_id=1, slug="m:1", title="Hôn ước", keys=["hôn ước"], content="Hai nhà hứa gả con từ năm 1979. " * 4),
    LoreEntry(id=2, card_id=1, slug="m:2", title="Gác mái", keys=["gác mái"], known_by=["{{char}}"],
              content="Lạc Dương giấu hộp thư cũ trên gác mái tiệm sách."),
    LoreEntry(id=3, card_id=1, slug="m:3", title="Kiếp trước", keys=["kiếp trước"], known_by=["{{user}}"],
              content="BÍ MẬT CHỈ NGƯỜI CHƠI BIẾT: đây là lần sống thứ hai."),
    LoreEntry(id=4, card_id=1, slug="m:4", title="Bà ngoại", keys=["bà ngoại"], content="Bà ngoại của Lâm Vãn ((mở)) quán chè."),
]


def lore_of(history: list[Message], entries: list[LoreEntry] = ENTRIES, story: Story | None = None) -> PromptLore:
    ctx = PromptContext(card=make_card(), persona=make_persona(), story=story or make_story(), style="")
    return lore_for_history(entries, tpl=get_template("vi"), ctx=ctx, history=history)


def build(history: list[Message], lore: PromptLore | None, **kw: Any):  # type: ignore[no-untyped-def]
    return build_prompt(make_card(), make_persona(), make_story(), history, lore=lore, **kw)


def dump(built) -> str:  # type: ignore[no-untyped-def]
    return built.model_dump_json(exclude={"lore_head", "open_last", "lore_used"})


# ---------------------------------------------------------------------------- giống hệt Phase 3


@pytest.mark.parametrize("state", [None, PromptState()], ids=["no-state", "empty-state"])
def test_no_lore_or_empty_lore_is_byte_identical(state: PromptState | None) -> None:
    hist = [assistant(0, GREETING), user(1, "Hôm nay đi đâu?")]
    plain = build(hist, None, state=state)
    assert dump(build(hist, PromptLore(), state=state)) == dump(plain)
    assert dump(build(hist, PromptLore(reserve_tokens=0, unsent_ids=[3]), state=state)) == dump(plain)
    assert plain.lore_head is None and plain.lore_used == [] and "D" not in plain.token_estimate
    # Card có sổ thế giới mà lượt này không gợi mục nào: các message giống hệt khi lịch sử còn vừa.
    assert build(hist, PromptLore(reserve_tokens=LORE_TOKEN_LIMIT), state=state).messages == plain.messages


def test_block_d_position_and_order() -> None:
    hist = [assistant(0, GREETING), user(1, "Kể chuyện hôn ước đi."), assistant(2, "Ừ."), user(3, "Bà ngoại thì sao? Gác mái nữa. ((kể kiếp trước))")]
    lore = lore_of(hist)
    assert [s.entry_id for s in lore.carried] == [1]
    assert [s.entry_id for s in lore.fresh] == [4, 2]  # theo vị trí khớp đầu tiên trong lời người chơi
    assert lore.unsent_ids == [3]
    built = build(hist, lore, state=PromptState())
    last = built.messages[-1].content
    lines = block_lines(get_template("vi"), PromptContext(make_card(), make_persona(), make_story(), ""), lore)
    head = "\n".join(lines)
    assert last.startswith(head + "\n\nBà ngoại thì sao? Gác mái nữa.")
    assert lines[0].startswith("[Thông tin thế giới cho người dẫn truyện, không phải lời của Lâm Vãn.")
    assert lines[1].startswith("- Hôn ước: ") and lines[2].startswith("- Bà ngoại: ") and lines[3].startswith("- Gác mái (chuyện riêng")
    assert lines[-1] == "[Hết thông tin thế giới.]"
    assert last.index("[Ghi chú cho người dẫn truyện") > last.index("Gác mái nữa.")
    assert "BÍ MẬT CHỈ NGƯỜI CHƠI BIẾT" not in "\n".join(m.content for m in built.messages)
    assert "((" not in last and "Bà ngoại của Lâm Vãn (mở) quán chè." in last
    # Lore không bao giờ nằm trong system.
    assert "Hôn ước" not in built.messages[0].content and "Thông tin thế giới" not in built.messages[0].content
    assert built.lore_head == "\n".join(lines[:2]) and last.startswith(built.lore_head)
    assert built.token_estimate["D"] == sum(lore_select.line_tokens(line) for line in lines)
    assert [(u.entry_id, u.slot) for u in built.lore_used] == [(1, "carried"), (4, "fresh"), (2, "fresh")]
    assert built.token_estimate["total"] == sum(v for k, v in built.token_estimate.items() if k != "total")


def test_directive_only_turn() -> None:
    hist = [assistant(0, GREETING), user(1, "((nhắc tới hôn ước))")]
    built = build(hist, lore_of(hist), state=PromptState())
    last = built.messages[-1].content
    assert last.startswith("[Thông tin thế giới") and "\n[Hết thông tin thế giới.]\n\n[Ghi chú cho người dẫn truyện" in last


def test_dm_header() -> None:
    hist = [assistant(0, "Chào."), user(1, "Hôn ước là sao?")]
    story = make_story(mode="dm")
    lore = lore_of(hist, story=story)
    built = build_prompt(make_card(), make_persona(), story, hist, lore=lore)
    assert built.messages[-1].content.startswith("[Thông tin thế giới cho người viết, không phải tin nhắn của Lâm Vãn.")


def test_d_not_counted_in_e() -> None:
    hist = [assistant(0, GREETING), user(1, "Hôn ước là sao?")]
    with_d = build(hist, lore_of(hist), state=PromptState())
    without = build(hist, None, state=PromptState())
    assert with_d.token_estimate["E"] == without.token_estimate["E"]
    assert with_d.token_estimate["total"] == without.token_estimate["total"] + with_d.token_estimate["D"]


# ---------------------------------------------------------------------------- cửa sổ lịch sử


def reply(t: int) -> str:
    return f"[Thought: Lượt {t}.]\nLạc Dương nhìn cô, lượt {t}. " + "Anh lặng lẽ nghe cô kể. " * (14 + t % 5)


KEYWORDS = ["hôn ước", "", "bà ngoại", "gác mái", "", "hôn ước bà ngoại gác mái kiếp trước", "", ""]


def player(t: int) -> str:
    return f"*Tớ kéo tay áo cậu ấy.* Lượt {t}, {KEYWORDS[(t // 2) % len(KEYWORDS)]} " + "kể tiếp đi mà. " * 3


def test_window_start_and_system_do_not_depend_on_triggered_entries() -> None:
    budget = PromptBudget(num_ctx=4096)
    hist: list[Message] = [assistant(0, GREETING)]
    prev_system: str | None = None
    prev_start: int | None = None
    starts: list[int] = []
    for t in range(1, 61, 2):
        hist.append(user(t, player(t)))
        lore = lore_of(hist)
        reserve_only = PromptLore(reserve_tokens=lore.reserve_tokens)
        built = build(hist, lore, budget=budget, state=PromptState())
        same = build(hist, reserve_only, budget=budget, state=PromptState())
        assert built.dropped_turns == same.dropped_turns, t  # gợi ra mục nào cũng không làm cửa sổ nhảy
        assert built.messages[:-1] == same.messages[:-1]
        assert built.token_estimate["total"] <= budget.num_ctx - budget.reply_tokens_story - budget.safety_tokens
        start = hist[built.dropped_turns].turn_index
        if prev_start == start:
            assert built.messages[0].content == prev_system  # system giữ nguyên từng byte
        prev_system, prev_start = built.messages[0].content, start
        starts.append(start)
        hist.append(assistant(t + 1, reply(t + 1)))
    assert len(set(starts)) >= 3, starts
    assert starts == sorted(starts)


def world_card(name: str):  # type: ignore[no-untyped-def]
    from lyris.prompt.builder import available_styles

    return import_card((WORLDS / name / "card.json").read_bytes(), "application/json", styles=available_styles()).card


@pytest.mark.parametrize("name", ["co-hoai-da", "luc-bac-uyen", "tan-duong", "yen-hoanh-sinh"])
def test_real_cards_with_longest_summary_keep_a_full_pair_after_shift(name: str) -> None:
    """§6.2: với phần dự phòng 520 và tóm tắt dài, sau mỗi lần dịch cửa sổ còn ít nhất một cặp lượt trọn vẹn
    (lượt nhân vật + lượt người chơi trước lượt mới), và tổng ước lượng luôn ≤ limit."""
    card = world_card(name).model_copy(update={"id": 1})
    persona = Persona(id=1, name="Ngọc Anh", gender="female")
    settings = default_settings(card, persona)
    story = Story(id=1, card_id=1, persona_id=1, title="t", **settings.model_dump())
    budget = PromptBudget()
    limit = budget.num_ctx - budget.reply_tokens_story - budget.safety_tokens
    fat = [
        LoreEntry(id=i, card_id=1, slug=f"m:{i}", title=f"Mục dài {i}", keys=[f"khoá {i}"], content="Một câu khá dài về thế giới. " * 30)
        for i in range(1, 6)
    ]
    summary = "Tóm tắt dài về mọi chuyện đã qua. " * 60  # ~2000 ký tự, như tóm tắt dài nhất
    hist: list[Message] = [assistant(0, card.greeting)]
    min_window = 10**9
    for t in range(1, 81, 2):
        text = f"Lượt {t}: khoá 1 khoá 2 khoá 3 khoá 4 khoá 5. " + "Tôi kể tiếp chuyện hôm qua cho hắn nghe. " * 4
        hist.append(user(t, text))
        ctx = PromptContext(card=card, persona=persona, story=story, style="")
        lore = lore_for_history(fat, tpl=get_template(story.language), ctx=ctx, history=hist)
        state = PromptState(summaries=[SummaryPoint(text=summary, upto_turn=max(0, t - 30))])
        built = build_prompt(card, persona, story, hist, budget=budget, state=state, lore=lore)
        assert built.token_estimate["total"] <= limit, (name, t, built.token_estimate)
        window = hist[built.dropped_turns:]
        if built.dropped_turns:
            roles = [m.role for m in window]
            assert roles[-3:] == ["user", "assistant", "user"], (name, t, roles)
            min_window = min(min_window, built.token_estimate["E"])
        hist.append(assistant(t + 1, long_reply(t)))
    # Số đo ghi lại để thấy khi ai đó tăng LORE_TOKEN_LIMIT (lịch sử nhỏ nhất ngay sau lần dịch).
    # 2026-11-15: 700 -> 600. Khối A có thêm luật an toàn nội dung (~115 token, docs/compliance.md §1), phần cố định
    # lớn hơn nên cửa sổ nhỏ nhất của yen-hoanh-sinh còn 618 token (vẫn giữ trọn một cặp lượt, kiểm ở trên).
    assert min_window >= 600, (name, min_window)


def test_lore_reserve_never_leaves_only_the_new_turn_on_yen_hoanh_sinh() -> None:
    """Review: với lượt trả lời thật (500-750 token) và lượt người chơi dài (~1200 ký tự), phần dự phòng 520
    từng làm 20/58 lượt chỉ còn [system, lượt mới]. Lượt không gợi mục nào thì cửa sổ phải giống hệt khi
    không có sổ thế giới, và luôn ở một mốc khúc; prompt luôn ≤ limit."""
    import random

    from lyris.memory.summarize import clip_words
    from lyris.prompt.builder import window_boundaries

    card = world_card("yen-hoanh-sinh").model_copy(update={"id": 1})
    persona = Persona(id=1, name="Ngọc Anh", gender="female")
    story = Story(id=1, card_id=1, persona_id=1, title="t", **default_settings(card, persona).model_dump())
    budget = PromptBudget()
    limit = budget.num_ctx - budget.reply_tokens_story - budget.safety_tokens
    summary = clip_words("Ngọc Anh gặp lại hắn ở bến đò cũ, hai người cãi nhau vì chuyện hôn ước rồi làm lành. " * 30)
    sent = "Anh kể chuyện tiệm sách cũ, chuyện mưa dầm và con mèo mướp hay nằm trên bậu cửa. "
    psent = "Tôi kể tiếp chuyện hôm qua cho hắn nghe, rồi hỏi thêm. "
    rnd = random.Random(7)
    hist: list[Message] = [assistant(0, card.greeting)]
    trimmed = tail_only = 0
    for t in range(1, 101, 2):
        hist.append(user(t, (f"P{t} " + psent * 40)[: int(1200 * rnd.uniform(0.7, 1.3))]))
        state = PromptState(summaries=[SummaryPoint(text=summary, upto_turn=u) for u in range(0, t, 6)])
        with_lore = build_prompt(card, persona, story, hist, budget=budget, state=state, lore=PromptLore(reserve_tokens=520))
        without = build_prompt(card, persona, story, hist, budget=budget, state=state)
        assert with_lore.token_estimate["total"] <= limit
        if with_lore.dropped_turns:
            trimmed += 1
            assert hist[with_lore.dropped_turns].turn_index in window_boundaries(card, persona, story, hist, budget=budget)
            tail_only += [m.role for m in with_lore.messages] == ["system", "user"]
            assert [m.role for m in without.messages] != ["system", "user"]
            assert with_lore.dropped_turns == without.dropped_turns, t
        hist.append(assistant(t + 1, (f"R{t + 1} " + sent * 100)[: rnd.randint(1600, 2400)]))
    assert trimmed >= 30 and tail_only == 0, (trimmed, tail_only)


def test_next_window_start_stays_conservative_with_lore_reserve() -> None:
    """`next_window_start` (đoán để tóm tắt trước) không dùng bước lùi mốc theo khối D thật: đoán của nó
    không bao giờ sớm hơn cửa sổ của lượt thật, nên tóm tắt không bao giờ trễ."""
    import random

    from lyris.prompt.builder import next_window_start

    card = world_card("yen-hoanh-sinh").model_copy(update={"id": 1})
    persona = Persona(id=1, name="Ngọc Anh", gender="female")
    story = Story(id=1, card_id=1, persona_id=1, title="t", **default_settings(card, persona).model_dump())
    rnd = random.Random(3)
    hist: list[Message] = [assistant(0, card.greeting)]
    for t in range(1, 81, 2):
        chars = int(1200 * rnd.uniform(0.7, 1.3))
        guess = next_window_start(card, persona, story, hist, next_user_chars=chars, lore_reserve=520)
        hist.append(user(t, "x" * chars))
        real = build_prompt(card, persona, story, hist, state=PromptState(), lore=PromptLore(reserve_tokens=520))
        assert guess >= hist[real.dropped_turns].turn_index, t
        hist.append(assistant(t + 1, "Anh kể chuyện tiệm sách cũ. " * rnd.randint(55, 85)))


# ---------------------------------------------------------------------------- prefill qua chat thật


SEED_ENTRIES = [
    {"title": "Hôn ước", "keys": ["hôn ước"], "content": "Hai nhà hứa gả con từ năm 1979. Ai trong trường cũng biết."},
    {"title": "Gác mái", "keys": ["gác mái"], "known_by": ["{{char}}"], "content": "Lạc Dương giấu hộp thư cũ trên gác mái."},
    {"title": "Kiếp trước", "keys": ["kiếp trước"], "known_by": ["{{user}}"], "content": "CHỈ NGƯỜI CHƠI: lần sống thứ hai."},
    {"title": "Bà ngoại", "keys": ["bà ngoại"], "content": "Bà ngoại của Lâm Vãn mở quán chè đầu ngõ."},
]


def fixed_turn(t: int, chars: int = 140) -> str:
    text = f"*Tớ chống cằm nghe.* P{t:02d} {KEYWORDS[t % len(KEYWORDS)]}. " + "Kể tiếp đi mà, kể thêm chút nữa thôi. " * 6
    return text[:chars]


async def run_prefill_turns(tmp_path: Path, turns: int) -> list[tuple[Any, list[Any]]]:
    """(prefix trước lượt, messages thật của lượt) cho từng lượt; người chơi luôn viết đúng độ dài trung vị."""
    llm = ScriptedLLM([long_reply(n) for n in range(1, turns + 5)])
    application = create_app(make_settings(tmp_path), llm)
    out: list[tuple[Any, list[Any]]] = []
    async with application.router.lifespan_context(application):
        async with owner_client(application, base_url="http://test") as client:
            sid = await first_story(client)
            repo = repo_of(application)
            card_id = repo.get_story(sid, account_id=ANY_ACCOUNT).card_id
            for body in SEED_ENTRIES:
                assert (await client.post(f"/api/cards/{card_id}/lore", json=body)).status_code == 200
            state = application.state.state
            prefix = None
            for t in range(turns):
                await send(client, sid, fixed_turn(t))
                messages = llm.chat_calls()[-1]["messages"]
                if prefix is not None:
                    out.append((prefix, messages))
                await worker_of(application).run_until_idle()
                prefix = state.next_prompt_prefix(repo.get_story(sid, account_id=ANY_ACCOUNT))
                assert prefix is not None
    return out


async def test_prefill_prefix_matches_real_prompt_with_lore_default_off(tmp_path: Path) -> None:
    assert lore_select.LORE_PREFILL_OPEN_TURN is False  # mặc định tắt (§6.5)
    pairs = await run_prefill_turns(tmp_path, 30)
    with_d = 0
    systems = set()
    for i, (prefix, messages) in enumerate(pairs):
        assert prefix.open_last is False
        assert prefix.messages == messages[:-1], f"lượt {i + 1}: prefill lệch prompt thật"
        if messages[-1].content.startswith("[Thông tin thế giới"):
            with_d += 1
        assert "Thông tin thế giới" not in messages[0].content and "CHỈ NGƯỜI CHƠI" not in messages[-1].content
        systems.add(messages[0].content)
    assert with_d >= 10
    assert len(systems) >= 2  # có lượt cửa sổ dịch trong 30 lượt (có tóm tắt mới vào C)


async def test_prefill_open_turn_is_exact_text_prefix_when_enabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lore_select, "LORE_PREFILL_OPEN_TURN", True)
    pairs = await run_prefill_turns(tmp_path, 30)
    opened = 0
    shifted = 0
    prev_system = None
    for i, (prefix, messages) in enumerate(pairs):
        real = render_prefix("gemma4-large", messages)
        head = render_prefix("gemma4-large", prefix.messages, open_last=prefix.open_last)
        assert real is not None and head is not None
        assert real.startswith(head), f"lượt {i + 1}: phần gửi trước không phải chuỗi đầu của prompt thật"
        if prefix.open_last:
            opened += 1
            assert prefix.messages[-1].role == "user" and prefix.messages[:-1] == messages[:-1]
            assert messages[-1].content.startswith(prefix.messages[-1].content)
            assert not head.endswith("<turn|>\n")
        else:
            assert prefix.messages == messages[:-1]
        if prev_system is not None and messages[0].content != prev_system:
            shifted += 1
        prev_system = messages[0].content
    assert opened >= 8
    assert shifted >= 1


def test_render_prefix_open_last() -> None:
    from lyris.models import ChatTurn

    msgs = [ChatTurn(role="system", content="S"), ChatTurn(role="user", content="  [Thông tin]\n- A")]
    assert render_prefix("gemma4-large", msgs, open_last=True) == "<bos><|turn>system\nS<turn|>\n<|turn>user\n[Thông tin]\n- A"
    full = [msgs[0], ChatTurn(role="user", content="[Thông tin]\n- A\n- B\n[Hết]\n\nChào.")]
    assert render_prefix("gemma4-large", full).startswith(render_prefix("gemma4-large", msgs, open_last=True))  # type: ignore[arg-type]
    assert render_prefix("unknown", msgs, open_last=True) is None


def test_lore_head_none_without_carried() -> None:
    hist = [assistant(0, GREETING), user(1, "Hôn ước là sao?")]
    built = build(hist, lore_of(hist), state=PromptState())
    assert built.lore_used and built.lore_head is None


def test_json_dump_of_snapshot_fields() -> None:
    hist = [assistant(0, GREETING), user(1, "hôn ước"), assistant(2, "Ừ."), user(3, "Kể tiếp.")]
    built = build(hist, lore_of(hist), state=PromptState())
    data = json.loads(built.model_dump_json())
    assert data["lore_used"] == [{"entry_id": 1, "title": "Hôn ước", "slot": "carried", "tokens": built.lore_used[0].tokens}]
    assert data["open_last"] is False and data["lore_head"].startswith("[Thông tin thế giới")
