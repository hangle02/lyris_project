"""Chống lặp giữa các lượt (lyris/prompt/repetition.py) và ghi chú cuối lượt (khối F)."""
from __future__ import annotations

from lyris.models import Message
from lyris.prompt.builder import build_prompt
from lyris.prompt.repetition import recent_phrases
from tests.test_prompt import make_card, make_persona, make_story


def msg(turn: int, role: str, mode: str, text: str) -> Message:
    return Message(
        story_id=1, turn_index=turn, role=role, mode=mode, raw_content=text, visible_content=text,  # type: ignore[arg-type]
    )


GREETING = msg(0, "assistant", "story", "Nắng chiều cuối thu. Lạc Dương khép giáo trình lại.")


def dm_history() -> list[Message]:
    return [
        GREETING,
        msg(1, "user", "dm", "tớ về đến nhà rồi"),
        msg(2, "assistant", "dm", "Cậu bảo với mẹ thế nào rồi?\nCậu nghỉ ngơi đi, đừng thức khuya quá."),
        msg(3, "user", "dm", "mẹ tớ hỏi thăm cậu suốt"),
        msg(4, "assistant", "dm", "Cậu lại trêu tớ rồi.\n\nCậu ngủ sớm đi."),
        msg(5, "user", "dm", "chả biết đâu"),
    ]


def test_dm_takes_last_line_of_recent_dm_replies() -> None:
    assert recent_phrases(dm_history(), "dm") == ["Cậu nghỉ ngơi đi, đừng thức khuya quá.", "Cậu ngủ sớm đi."]


def test_greeting_and_other_mode_are_ignored() -> None:
    hist = [GREETING, msg(1, "user", "story", "chào"), msg(2, "assistant", "dm", "Ừ.")]
    assert recent_phrases(hist, "story") == []
    assert recent_phrases(hist, "dm") == ["Ừ."]


def test_story_takes_clipped_first_sentence_of_last_three() -> None:
    hist: list[Message] = [GREETING]
    for i in range(1, 5):
        hist.append(msg(2 * i - 1, "user", "story", "..."))
        hist.append(
            msg(2 * i, "assistant", "story", f"Lạc Dương khẽ nhíu mày lần thứ {i} khi nghe giọng nói còn ngái ngủ. Rồi anh cười.")
        )
    hist.append(msg(9, "user", "story", "tiếp"))
    phrases = recent_phrases(hist, "story")
    assert len(phrases) == 3
    assert phrases[0].startswith("Lạc Dương khẽ nhíu mày lần thứ 2")
    assert all(p.endswith("…") for p in phrases)
    assert all(len(p.split()) <= 9 for p in phrases)


def test_duplicates_collapse() -> None:
    hist = [
        GREETING,
        msg(1, "user", "dm", "a"),
        msg(2, "assistant", "dm", "Ngủ sớm đi."),
        msg(3, "user", "dm", "b"),
        msg(4, "assistant", "dm", "Ngủ sớm đi."),
        msg(5, "user", "dm", "c"),
    ]
    assert recent_phrases(hist, "dm") == ["Ngủ sớm đi."]


def test_dm_note_lists_phrases_and_system_is_unchanged() -> None:
    story = make_story(mode="dm")
    hist = dm_history()
    built = build_prompt(make_card(), make_persona(), story, hist)
    note = built.messages[-1].content
    assert "«Cậu ngủ sớm đi.»" in note
    assert "không kết bằng lời dặn dò" in note
    # Phần system không phụ thuộc lịch sử (giữ prompt cache).
    shorter = build_prompt(make_card(), make_persona(), story, hist[:2])
    assert built.messages[0].content == shorter.messages[0].content
    assert "lời dặn dò" in built.messages[0].content


def test_no_note_without_earlier_replies() -> None:
    built = build_prompt(make_card(), make_persona(), make_story(mode="dm"), dm_history()[:2])
    assert "kết bằng:" not in built.messages[-1].content


def test_english_dm_note() -> None:
    story = make_story(mode="dm", language="en")
    built = build_prompt(make_card(), make_persona(), story, dm_history())
    assert '"Cậu ngủ sớm đi."' in built.messages[-1].content
    assert "do not end with advice" in built.messages[-1].content
