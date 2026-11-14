"""Phase 4 (docs/phase4.md §6.1, §6.2): chọn mục cho prompt — ai biết, ngân sách, thứ tự, độ sâu quét."""
from __future__ import annotations

import random

import pytest

from lyris.lore.select import (
    LORE_CARRIED_TOKENS,
    LORE_MAX_ITEMS,
    LORE_TOKEN_LIMIT,
    MAX_LORE_ITEM_CHARS,
    ScanText,
    audience_of,
    block_lines,
    clip_text,
    line_tokens,
    select_lore,
)
from lyris.models import AddressTerms, CharacterCard, LoreEntry, NarrationPronouns, Persona, PromptLore, Story
from lyris.prompt.templates import PromptContext, get_template

CHAR = "Lục Bắc Uyên"
TPL = get_template("vi")


def ctx(mode: str = "story") -> PromptContext:
    card = CharacterCard(
        id=1, name=CHAR, gender="male", style_profile="trung_hien_dai", address_terms=AddressTerms(self_term="tôi", player_term="em")
    )
    story = Story(
        card_id=1, persona_id=1, title="t", mode=mode, narration_pronouns=NarrationPronouns(character="hắn", player="cô")  # type: ignore[arg-type]
    )
    return PromptContext(card=card, persona=Persona(name="Ngọc Anh", gender="female"), story=story, style="")


def entry(i: int, keys: list[str], known_by: list[str] | None = None, content: str = "", **kw: object) -> LoreEntry:
    return LoreEntry(
        id=i,
        card_id=1,
        slug=f"manual:{i}",
        title=kw.pop("title", f"Mục {i}"),  # type: ignore[arg-type]
        keys=keys,
        known_by=known_by or ["*"],
        content=content or f"Nội dung của mục {i}.",
        position=i,
        **kw,  # type: ignore[arg-type]
    )


def select(entries: list[LoreEntry], tail: str = "", earlier: list[tuple[str, bool]] | None = None) -> PromptLore:
    return select_lore(
        entries,
        tpl=TPL,
        ctx=ctx(),
        tail=[ScanText(tail, True)] if tail else [],
        earlier=[ScanText(t, p) for t, p in (earlier or [])],
    )


@pytest.mark.parametrize(
    ("known_by", "audience"),
    [
        (["*"], "everyone"),
        (["{{char}}"], "character"),
        ([CHAR], "character"),
        (["Lục Bắc Uyên (陆北渊)"], "character"),
        (["{{user}}", CHAR], "character"),
        (["{{user}}"], "player"),
        (["{{user}}", "Hạ Trì"], "player"),
        (["Hạ Trì"], "others"),
        (["*", "{{user}}"], "everyone"),
    ],
)
def test_audience(known_by: list[str], audience: str) -> None:
    assert audience_of(known_by, CHAR) == audience


def test_player_only_entry_is_never_sent_even_when_it_is_the_only_match() -> None:
    secret = entry(1, ["nguyên tác"], ["{{user}}"], "Theo nguyên tác, phản diện chết ở chương 87.")
    lore = select([secret], tail="Nguyên tác viết gì?", earlier=[("Nguyên tác ư?", True)])
    assert lore.carried == [] and lore.fresh == [] and lore.unsent_ids == [1]
    assert lore.reserve_tokens == 0  # card chỉ có mục {{user}}: không có phần dự phòng, prompt như Phase 3
    assert block_lines(TPL, ctx(), lore) == []


def test_character_entry_is_private_and_others_entry_is_never_sent() -> None:
    private = entry(1, ["đêm mưa"], ["{{char}}"])
    others = entry(2, ["đêm mưa"], ["Hạ Trì"])
    lore = select([private, others], tail="Kể chuyện đêm mưa đi.")
    assert [(s.entry_id, s.private) for s in lore.fresh] == [(1, True)]
    assert lore.unsent_ids == [2]
    line = block_lines(TPL, ctx(), lore)[1]
    assert "chuyện riêng của Lục Bắc Uyên" in line and "không tự nói ra" in line


def test_budget_carried_fresh_and_max_items() -> None:
    long = "Câu dài về chuyện cũ của gia tộc. " * 30
    entries = [entry(i, [f"khoá số {i}"], content=long) for i in range(1, 9)]
    earlier = [(" ".join(f"khoá số {i}" for i in range(1, 9)), True)]
    lore = select(entries, tail=" ".join(f"khoá số {i}" for i in range(1, 9)), earlier=earlier)
    carried_tokens = sum(s.tokens for s in lore.carried)
    assert carried_tokens <= LORE_CARRIED_TOKENS
    total = sum(line_tokens(line) for line in block_lines(TPL, ctx(), lore))
    assert total <= LORE_TOKEN_LIMIT
    assert len(lore.carried) + len(lore.fresh) <= LORE_MAX_ITEMS
    sent = {s.entry_id for s in (*lore.carried, *lore.fresh)}
    assert sent and set(lore.unsent_ids) == set(range(1, 9)) - sent
    assert all(len(s.text) <= MAX_LORE_ITEM_CHARS for s in (*lore.carried, *lore.fresh))


def test_room_for_one_long_private_fresh_item_after_full_carried() -> None:
    # Luôn còn chỗ cho ít nhất một mục fresh dài MAX_LORE_ITEM_CHARS, tên ≤ 40 ký tự, kể cả mục riêng tư.
    filler = "Một câu ghi chú ngắn gọn. " * 30
    carried = [entry(i, [f"chuyện cũ {i}"], content=filler[:200]) for i in range(1, 4)]
    fresh = entry(
        9, ["bí mật đêm mưa"], ["{{char}}"], content=("Đêm ấy trời mưa rất to và hắn đứng một mình. " * 20), title="T" * 40
    )
    lore = select(
        [*carried, fresh],
        tail="Bí mật đêm mưa là gì?",
        earlier=[(" ".join(f"chuyện cũ {i}" for i in range(1, 4)), True)],
    )
    assert lore.carried and sum(s.tokens for s in lore.carried) <= LORE_CARRIED_TOKENS
    assert [s.entry_id for s in lore.fresh] == [9] and lore.fresh[0].private


def test_order_is_deterministic_regardless_of_input_order() -> None:
    entries = [entry(i, ["hôn ước", f"riêng {i}"], priority=(i % 3)) for i in range(1, 12)]
    expected = select(entries, tail="Hôn ước riêng 5", earlier=[("hôn ước", True), ("riêng 7", True)])
    rng = random.Random(7)
    for _ in range(5):
        shuffled = entries[:]
        rng.shuffle(shuffled)
        assert select(shuffled, tail="Hôn ước riêng 5", earlier=[("hôn ước", True), ("riêng 7", True)]) == expected


def test_priority_wins_for_fresh() -> None:
    low = entry(1, ["hôn ước"], priority=0)
    high = entry(2, ["đính hôn"], priority=50)
    lore = select([low, high], tail="Hôn ước, rồi đính hôn.")
    assert [s.entry_id for s in lore.fresh] == [2, 1]


def test_scan_depth_four_messages_is_sticky_then_drops() -> None:
    e = entry(1, ["hôn ước"])
    # earlier: mới nhất trước. Nhắc ở P₋₂ (message thứ 4) còn; P₋₃ (message thứ 6) đã ra khỏi độ sâu quét.
    at_p2 = [("A-1", False), ("P-1", True), ("A-2", False), ("hôn ước", True)]
    assert [s.entry_id for s in select([e], earlier=at_p2).carried] == [1]
    # Người gọi cắt `earlier` ở LORE_SCAN_DEPTH (LoreService.prompt_lore): P₋₃ không được đưa vào.
    assert select([e], earlier=at_p2[:3]).carried == []


def test_carried_and_fresh_never_overlap() -> None:
    e = entry(1, ["hôn ước"])
    lore = select([e], tail="hôn ước", earlier=[("hôn ước", True)])
    assert [s.entry_id for s in lore.carried] == [1] and lore.fresh == []


def test_assistant_turns_only_trigger_name_like_keys() -> None:
    common = entry(1, ["căn hộ"])
    name = entry(2, ["Hạ Trì"])
    lore = select([common, name], earlier=[("Căn hộ tối om. Hạ Trì gọi tới.", False)])
    assert [s.entry_id for s in lore.carried] == [2]


def test_disabled_entries_are_ignored_and_reserve_is_zero_without_sendable_entries() -> None:
    off = entry(1, ["hôn ước"], enabled=False)
    assert select([off], tail="hôn ước") == PromptLore(reserve_tokens=0)
    assert select([], tail="hôn ước") == PromptLore(reserve_tokens=0)
    assert select([entry(2, [])], tail="hôn ước").reserve_tokens == LORE_TOKEN_LIMIT


def test_clip_text_cuts_at_sentence_end() -> None:
    text = "Câu một ngắn. " * 60
    clipped = clip_text(text)
    assert len(clipped) <= MAX_LORE_ITEM_CHARS and clipped.endswith(".")
    assert clip_text("a " * 400).endswith("…")
    assert clip_text("Dòng một.\n\nDòng hai.") == "Dòng một. Dòng hai."


def test_item_text_is_scrubbed_and_filled() -> None:
    e = entry(1, ["hôn ước"], content="{{user}} và {{char}} ((bí mật)) hẹn ước")
    lore = select([e], tail="hôn ước")
    text = lore.fresh[0].text
    assert "((" not in text and "))" not in text
    assert text == "Ngọc Anh và Lục Bắc Uyên (bí mật) hẹn ước."


def test_cjk_chars_cost_extra_tokens() -> None:
    assert line_tokens("夏驰夏驰") == line_tokens("abcd") + 4


def test_clip_text_keeps_closing_quote_after_sentence_end() -> None:
    text = "Ông nói: “Cháu phải giữ lời hứa.” " * 20
    clipped = clip_text(text)
    assert len(clipped) <= MAX_LORE_ITEM_CHARS
    assert clipped.endswith("hứa.”")
    assert clipped.count("“") == clipped.count("”")
    assert clip_text("(Cô ấy đi rồi.) " * 40).endswith("rồi.)")
