"""Phase 3b: cửa sổ lịch sử cắt theo khúc (hysteresis) để Ollama dùng lại prompt cache.

Không cần Ollama: chỉ dựng prompt cho một story lớn dần từng lượt và xem điểm bắt đầu cửa sổ.
"""
from __future__ import annotations

from lyris.models import Message, PromptState, SummaryPoint
from lyris.prompt.builder import (
    TRIM_CHUNK_FRACTION,
    PromptBudget,
    build_prompt,
    pick_summary,
    window_boundaries,
)
from tests.test_prompt import GREETING, assistant, make_card, make_persona, make_story, user

BUDGET = PromptBudget(num_ctx=4096)


def reply(t: int) -> str:
    return f"[Thought: Lượt {t}.]\nLạc Dương nhìn cô, lượt {t}. " + "Anh lặng lẽ nghe cô kể. " * (14 + t % 5)


def player(t: int) -> str:
    return f"*Tớ kéo tay áo cậu ấy.* Lượt {t} nè, " + "kể tiếp đi mà. " * (3 + t % 3)


def grow(turns: int) -> list[list[Message]]:
    """Lịch sử dựng prompt cho từng lượt: [..., user(t)] với t = 1, 3, 5, ..."""
    hist: list[Message] = [assistant(0, GREETING)]
    builds: list[list[Message]] = []
    t = 1
    while t < turns:
        hist.append(user(t, player(t)))
        builds.append(list(hist))
        hist.append(assistant(t + 1, reply(t + 1)))
        t += 2
    return builds


def starts(builds: list[list[Message]], **kwargs) -> list[int]:  # type: ignore[no-untyped-def]
    card, persona, story = make_card(), make_persona(), make_story()
    out = []
    for hist in builds:
        built = build_prompt(card, persona, story, hist, budget=BUDGET, **kwargs)
        out.append(hist[built.dropped_turns].turn_index)
    return out


def test_window_start_is_stable_between_chunk_boundaries() -> None:
    builds = grow(90)
    seq = starts(builds)
    trimmed = [s for s in seq if s > 0]
    assert len(trimmed) >= 12, "story phải đủ dài để cắt nhiều lần"
    # Không bao giờ lùi lại, và mỗi điểm bắt đầu giữ nguyên qua nhiều lượt liên tiếp.
    assert seq == sorted(seq)
    changes = sum(1 for a, b in zip(seq, seq[1:], strict=False) if a != b)
    assert changes <= len(trimmed) // 2
    runs: list[int] = []
    for i, s in enumerate(seq):
        if s == 0:
            continue
        if i and seq[i - 1] == s:
            runs[-1] += 1
        else:
            runs.append(1)
    # Mọi lần cắt (trừ lần đang dở ở cuối) giữ cửa sổ ít nhất 2 lượt.
    assert all(r >= 2 for r in runs[:-1])
    # Điểm bắt đầu luôn là mốc khúc tính từ đầu story (không phụ thuộc phần sau).
    card, persona, story = make_card(), make_persona(), make_story()
    marks = set(window_boundaries(card, persona, story, builds[-1], budget=BUDGET))
    assert set(trimmed) <= marks


def test_prompt_prefix_reused_while_start_unchanged() -> None:
    card, persona, story = make_card(), make_persona(), make_story()
    builds = grow(90)
    prev = None
    reused = 0
    for hist in builds:
        built = build_prompt(card, persona, story, hist, budget=BUDGET)
        if prev is not None and prev[0] == built.dropped_turns and built.dropped_turns > 0:
            # Mọi message trừ message cuối (có ghi chú F) của lượt trước là tiền tố của prompt lượt này.
            head = prev[1].messages[:-1]
            assert built.messages[: len(head)] == head
            reused += 1
        prev = (built.dropped_turns, built)
    assert reused >= 6


def test_trim_leaves_headroom_of_about_one_chunk() -> None:
    card, persona, story = make_card(), make_persona(), make_story()
    builds = grow(90)
    limit = BUDGET.num_ctx - BUDGET.reply_tokens_story - BUDGET.safety_tokens
    prev_start = 0
    for hist in builds:
        built = build_prompt(card, persona, story, hist, budget=BUDGET)
        assert built.token_estimate["total"] <= limit
        if built.dropped_turns != prev_start and built.dropped_turns > 0:
            # Ngay sau khi cắt: phần lịch sử dùng không quá ~(1 - TRIM_CHUNK_FRACTION) ngân sách + một lượt.
            fixed = built.token_estimate["A"] + built.token_estimate["B"] + built.token_estimate["C"]
            history_budget = limit - fixed
            assert built.token_estimate["E"] + built.token_estimate["F"] <= history_budget * (1 - TRIM_CHUNK_FRACTION) + 500
        prev_start = built.dropped_turns


def test_not_full_history_is_untouched() -> None:
    card, persona, story = make_card(), make_persona(), make_story()
    # 2026-11-15: khối A có thêm luật an toàn nội dung (~115 token, docs/compliance.md §1), nên 10 lượt không còn vừa
    # 4096 nữa; 8 lượt vẫn chưa đầy (còn ~600 token trống).
    hist = grow(8)[-1]
    built = build_prompt(card, persona, story, hist, budget=BUDGET)
    huge = build_prompt(card, persona, story, hist, budget=PromptBudget(num_ctx=10**6))
    assert built.dropped_turns == 0
    assert built.messages == huge.messages
    assert build_prompt(card, persona, story, hist, budget=BUDGET, state=None).messages == huge.messages


def test_boundaries_depend_only_on_the_prefix() -> None:
    card, persona, story = make_card(), make_persona(), make_story()
    builds = grow(90)
    short = window_boundaries(card, persona, story, builds[10], budget=BUDGET)
    long = window_boundaries(card, persona, story, builds[-1], budget=BUDGET)
    assert short and long[: len(short)] == short
    # Mốc là đầu lượt người chơi.
    by_turn = {m.turn_index: m for m in builds[-1]}
    assert all(by_turn[t].role == "user" for t in long)


def test_summary_in_block_c_changes_only_with_the_window() -> None:
    card, persona, story = make_card(), make_persona(), make_story()
    builds = grow(90)
    marks = window_boundaries(card, persona, story, builds[-1], budget=BUDGET)
    # Tóm tắt sẵn cho mọi khúc (kể cả khúc còn trong cửa sổ): builder chỉ dùng mốc nằm trước cửa sổ.
    points = [SummaryPoint(text=f"Tóm tắt tới lượt {m - 1}.", upto_turn=m - 1) for m in marks]
    state = PromptState(summaries=points, summary=points[-1].text)
    prev = None
    for hist in builds:
        built = build_prompt(card, persona, story, hist, budget=BUDGET, state=state)
        first = hist[built.dropped_turns].turn_index
        system = built.messages[0].content
        if built.dropped_turns == 0:
            assert "Những gì đã xảy ra trước đó" not in system
            assert built.summary_upto_turn is None
        else:
            assert built.summary_upto_turn == first - 1
            assert f"Tóm tắt tới lượt {first - 1}." in system
        if prev is not None and prev[0] == first:
            assert prev[1] == system  # cửa sổ không dịch thì khối C giữ nguyên từng byte
        prev = (first, system)


def test_pick_summary() -> None:
    points = [SummaryPoint(text="a", upto_turn=4), SummaryPoint(text="b", upto_turn=9), SummaryPoint(text="c", upto_turn=15)]
    assert pick_summary(points, 0) is None
    assert pick_summary(points, 5) == points[0]
    assert pick_summary(points, 10) == points[1]
    assert pick_summary(points, 15) == points[1]
    assert pick_summary(points, 99) == points[2]


def test_legacy_single_summary_still_used() -> None:
    hist = grow(6)[-1]
    built = build_prompt(make_card(), make_persona(), make_story(), hist, state=PromptState(summary="Chuyện cũ."))
    assert "Những gì đã xảy ra trước đó: Chuyện cũ." in built.messages[0].content


def test_window_start_never_goes_back_when_facts_and_memories_change() -> None:
    """DM story, lượt ngắn, fact / ký ức dài có ở lượt chẵn và không có ở lượt lẻ: phần F dao động mạnh giữa
    các lượt, nhưng phép kiểm tra cắt dùng phần dự phòng cố định nên điểm bắt đầu không bao giờ lùi."""
    from lyris.models import MemoryHit

    card, persona, story = make_card(), make_persona(), make_story(mode="dm")
    long_fact = "Lâm Vãn từng kể rằng hồi nhỏ cô sợ sấm sét và hay trốn dưới gầm bàn học của Lạc Dương. " * 2
    hist: list[Message] = [assistant(0, GREETING)]
    seq: list[int] = []
    for n, t in enumerate(range(1, 400, 2)):
        hist.append(user(t, f"Lượt {t} nè, cậu đang làm gì đó? Kể tớ nghe với." + " hihi" * (t % 4)))
        hits = (
            [MemoryHit(memory_id=i, turn_index=max(0, t - 40 + i), kind="fact", text=f"{i}. {long_fact}") for i in range(3)]
            + [MemoryHit(memory_id=10 + i, turn_index=max(0, t - 60 + i), kind="memory", text=f"Ký ức {i}. {long_fact}") for i in range(3)]
            if n % 2 == 0
            else []
        )
        state = PromptState(memories=hits, directive="Lạc Dương đang hơi giận." if n % 3 == 0 else None)
        built = build_prompt(card, persona, story, hist, budget=BUDGET, state=state)
        seq.append(hist[built.dropped_turns].turn_index)
        hist.append(assistant(t + 1, f"Tớ đang đọc sách, lượt {t + 1}. Cậu ăn tối chưa?" + " ừm" * (t % 5)))
    assert any(s > 0 for s in seq), "story phải đủ dài để cắt"
    assert seq == sorted(seq), [(a, b) for a, b in zip(seq, seq[1:], strict=False) if b < a]
    # Điểm bắt đầu vẫn đứng yên qua nhiều lượt giữa hai lần dịch.
    changes = sum(1 for a, b in zip(seq, seq[1:], strict=False) if a != b)
    assert changes <= len({s for s in seq if s > 0}) and changes < len(seq) // 4


def test_chunk_marks_do_not_depend_on_mode() -> None:
    card, persona = make_card(), make_persona()
    hist = grow(90)[-1]
    story_marks = window_boundaries(card, persona, make_story(mode="story"), hist, budget=BUDGET)
    dm_marks = window_boundaries(card, persona, make_story(mode="dm"), hist, budget=BUDGET)
    assert story_marks and story_marks == dm_marks


def test_mode_switch_window_always_uses_the_summary_right_before_it() -> None:
    """Đổi Story <-> DM giữa chừng: cửa sổ ở chế độ nào cũng bắt đầu ở một mốc chung, nên mốc tóm tắt
    `mốc - 1` (worker viết cho mọi mốc) luôn phủ đúng tới ngay trước cửa sổ, không có lượt nào bị bỏ sót."""
    card, persona = make_card(), make_persona()
    builds = grow(90)
    marks = window_boundaries(card, persona, make_story(), builds[-1], budget=BUDGET)
    points = [SummaryPoint(text=f"Tóm tắt tới lượt {m - 1}.", upto_turn=m - 1) for m in marks]
    state = PromptState(summaries=points, summary=points[-1].text)
    dropped_any = 0
    for n, hist in enumerate(builds):
        story = make_story(mode="story" if (n // 4) % 2 == 0 else "dm")
        built = build_prompt(card, persona, story, hist, budget=BUDGET, state=state)
        if built.dropped_turns > 0:
            dropped_any += 1
            first = hist[built.dropped_turns].turn_index
            assert first in marks
            assert built.summary_upto_turn == first - 1, (n, story.mode, first, built.summary_upto_turn)
    assert dropped_any >= 10
