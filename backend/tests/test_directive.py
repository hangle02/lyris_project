"""Test chỉ dẫn diễn xuất (lyris/state/directive.py): bảng luật, không có số, ổn định."""
from __future__ import annotations

import itertools
import re

import pytest

from lyris.models import EMOTION_KEYS, RelationshipValues
from lyris.state.directive import acting_directive, level

C, P = "Lạc Dương", "Lâm Vãn"
LEVEL_VALUES = (0, 29, 30, 50, 69, 70, 100)


def values(**kw: int) -> RelationshipValues:
    base = {"affection": 50, "trust": 50, "attraction": 10, "obsession": 0, "fear": 0, "aversion": 10}
    base.update(kw)
    return RelationshipValues(**base)


def vi(v: RelationshipValues) -> str:
    return acting_directive(v, char=C, player=P, language="vi", player_pronoun="cô", char_pronoun="anh")


def en(v: RelationshipValues) -> str:
    return acting_directive(v, char=C, player=P, language="en")


def test_levels() -> None:
    assert [level(x) for x in (0, 29, 30, 69, 70, 100)] == ["low", "low", "mid", "mid", "high", "high"]


def test_spec_example() -> None:
    v = values(affection=91, trust=80, attraction=75, aversion=40)
    assert vi(v) == (
        "Lạc Dương rất thương mến và tin cậy Lâm Vãn; đang rung động nhưng vẫn giữ trong lòng, chưa nói ra."
    )


def test_attraction_high_with_high_distance_holds_back() -> None:
    v = values(affection=50, trust=50, attraction=80, aversion=75)
    assert "muốn lại gần cô nhưng vẫn còn giữ ý" in vi(v)
    assert "holds back" in en(v)
    # Rung động cao thì khoảng cách cao không biến thành "lạnh nhạt".
    assert "lạnh nhạt" not in vi(v)


def test_attraction_high_with_low_distance_shows() -> None:
    v = values(affection=80, trust=80, attraction=85, aversion=5)
    assert "khó giấu được cảm xúc" in vi(v)
    assert "smitten" in en(v)


def test_fear_and_longing_high_is_jealous() -> None:
    v = values(affection=80, trust=60, obsession=75, fear=80)
    assert "dễ ghen, chỉ muốn giữ chặt cô bên mình" in vi(v)
    assert "jealous" in en(v)


def test_low_trust_high_affection_cares_but_closed() -> None:
    v = values(affection=85, trust=10)
    assert "quan tâm nhưng chưa dám mở lòng" in vi(v)
    assert "not ready to open up" in en(v)


def test_high_distance_low_affection_is_cold() -> None:
    v = values(affection=10, trust=10, aversion=90)
    assert "lạnh nhạt" in vi(v)
    assert "cold" in en(v)


def test_high_distance_with_affection_keeps_distance_once() -> None:
    v = values(affection=60, trust=10, aversion=80)
    text = vi(v)
    assert "giữ khoảng cách" in text
    assert text.count("nhưng") == 1


def test_only_fear_high() -> None:
    assert "rất sợ mất cô" in vi(values(fear=75))
    assert "afraid of losing" in en(values(fear=75))


def test_only_obsession_high() -> None:
    assert "lúc nào cũng nghĩ về cô" in vi(values(obsession=90))


def test_neutral_low_values() -> None:
    assert vi(values(affection=10, trust=40)) == "Lạc Dương đối xử với Lâm Vãn bình thường, chưa thân thiết."


def test_second_inner_feeling_is_second_sentence() -> None:
    text = vi(values(affection=80, trust=80, attraction=50, obsession=75, fear=75))
    assert text.count(".") == 2
    # Câu thứ hai dùng đại từ dẫn truyện của nhân vật, không lặp tên ("Lạc Dương còn ...").
    assert "Anh còn đôi lúc thấy lòng xao động vì cô." in text
    assert text.count(C) == 1


def test_second_inner_feeling_without_char_pronoun_joins_first_sentence() -> None:
    v = values(affection=80, trust=80, attraction=50, obsession=75, fear=75)
    for pronoun in (None, "", "tôi", "cô"):  # không có, ngôi thứ nhất, hoặc trùng đại từ người chơi
        text = acting_directive(v, char=C, player=P, language="vi", player_pronoun="cô", char_pronoun=pronoun)
        assert text == (
            "Lạc Dương rất thương mến và tin cậy Lâm Vãn; dễ ghen, chỉ muốn giữ chặt cô bên mình, "
            "và còn đôi lúc thấy lòng xao động vì cô."
        )


def test_pronoun_that_is_a_name_is_not_used() -> None:
    # Giới tính "khác": hồ sơ văn phong tiếng Việt để trống đại từ nên story lưu TÊN vào chỗ đại từ dẫn truyện.
    # Dùng nó như đại từ là lặp tên (§10.5): nhân vật gộp câu, người chơi thành "người ấy".
    v = values(affection=80, trust=80, attraction=50, obsession=75, fear=75)
    text = acting_directive(v, char=C, player=P, language="vi", player_pronoun=P, char_pronoun=C)
    assert text == (
        "Lạc Dương rất thương mến và tin cậy Lâm Vãn; dễ ghen, chỉ muốn giữ chặt người ấy bên mình, "
        "và còn đôi lúc thấy lòng xao động vì người ấy."
    )
    assert text.count(C) == 1 and text.count(P) == 1
    # So khớp không phân biệt hoa thường / khoảng trắng thừa; đại từ một bên là tên bên kia cũng không dùng.
    swapped = acting_directive(v, char=C, player=P, language="vi", player_pronoun=" lạc  dương ", char_pronoun="lâm vãn")
    assert swapped.count(C) == 1 and swapped.count(P) == 1 and "lạc" not in swapped and "lâm" not in swapped
    only_char = acting_directive(v, char=C, player=P, language="vi", player_pronoun="cô", char_pronoun=C)
    assert only_char.count(C) == 1 and "giữ chặt cô bên mình, và còn" in only_char


def test_capitalised_pronoun_is_lowercased_mid_sentence() -> None:
    v = values(affection=80, trust=80, attraction=50, obsession=75, fear=75)
    text = acting_directive(v, char=C, player=P, language="vi", player_pronoun="Cô", char_pronoun="Anh")
    assert "chỉ muốn giữ chặt cô bên mình. Anh còn đôi lúc thấy lòng xao động vì cô." in text
    assert "Cô" not in text


def test_second_inner_feeling_en() -> None:
    v = values(affection=80, trust=80, attraction=50, obsession=75, fear=75)
    he = acting_directive(v, char=C, player=P, language="en", char_pronoun="he")
    assert he.startswith("Lạc Dương deeply cares for and trusts Lâm Vãn. He gets jealous easily")
    other = acting_directive(v, char=C, player=P, language="en", char_pronoun="they")
    # Không có he/she: một danh sách "A, B, and C", không nối ", and" hai lần.
    assert other == (
        "Lạc Dương deeply cares for and trusts Lâm Vãn, gets jealous easily, wanting to hold on to them tightly, "
        "and sometimes feels a flutter around them."
    )
    assert other.count(", and") == 1
    one = acting_directive(values(affection=80, trust=80, attraction=50), char=C, player=P, language="en")
    assert one == "Lạc Dương deeply cares for and trusts Lâm Vãn, and sometimes feels a flutter around them."
    assert he.count(C) == 1 and other.count(C) == 1


def test_names_are_stripped() -> None:
    assert acting_directive(values(), char="  Lạc Dương ", player=" Lâm Vãn ", language="vi").startswith("Lạc Dương ")


ALL_COMBOS = list(itertools.product((0, 40, 80), repeat=6))


@pytest.mark.parametrize("language", ["vi", "en"])
def test_every_level_combo_non_empty_number_free_deterministic(language: str) -> None:
    seen: set[str] = set()
    for combo in ALL_COMBOS:
        v = RelationshipValues(**dict(zip(EMOTION_KEYS, combo, strict=True)))
        text = acting_directive(v, char=C, player=P, language=language)  # type: ignore[arg-type]
        assert text and text == acting_directive(v, char=C, player=P, language=language)  # type: ignore[arg-type]
        assert not re.search(r"\d", text), text
        assert "{" not in text and "}" not in text
        assert text.startswith(C) and text.endswith(".")
        assert text.count(". ") <= 1, text  # 1-2 câu
        assert "  " not in text and ";;" not in text and ",," not in text
        seen.add(text)
    assert len(seen) > 40  # bảng luật thật sự phân biệt các tổ hợp


@pytest.mark.parametrize("language", ["vi", "en"])
@pytest.mark.parametrize("char_pronoun", [None, "anh", "he"])
def test_player_and_char_names_appear_once(language: str, char_pronoun: str | None) -> None:
    for combo in ALL_COMBOS:
        v = RelationshipValues(**dict(zip(EMOTION_KEYS, combo, strict=True)))
        text = acting_directive(
            v, char=C, player=P, language=language, player_pronoun="cô", char_pronoun=char_pronoun  # type: ignore[arg-type]
        )
        assert text.count(P) == 1, text
        assert text.count(C) == 1, text
        assert text.count(". ") <= 1 and text.endswith("."), text


def test_pronoun_fallbacks() -> None:
    v = values(affection=50, trust=50, attraction=80, aversion=75)
    # Không có đại từ, hoặc đại từ ngôi thứ nhất/hai: dùng "người ấy".
    assert "muốn lại gần người ấy" in acting_directive(v, char=C, player=P, language="vi")
    assert "muốn lại gần người ấy" in acting_directive(v, char=C, player=P, language="vi", player_pronoun="tôi")
    assert "get closer to them" in acting_directive(v, char=C, player=P, language="en", player_pronoun="she")


@pytest.mark.parametrize("raw", LEVEL_VALUES)
def test_boundary_values_never_emit_numbers(raw: int) -> None:
    for key in EMOTION_KEYS:
        v = values(**{key: raw})
        for text in (vi(v), en(v)):
            assert not re.search(r"\d", text)
