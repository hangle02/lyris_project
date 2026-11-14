"""Story và DM chung một dòng thời gian: ở Story Mode lượt DM mang nhãn tin nhắn, F nhắc nhân vật nhớ
nội dung tin nhắn (vd. đã xưng tên qua tin nhắn). Story không có DM giữ nguyên từng byte."""
from __future__ import annotations

from lyris.memory.summarize import _transcript
from lyris.models import Message
from lyris.prompt.builder import build_prompt, window_boundaries
from lyris.prompt.templates import get_template
from tests.test_prompt import GREETING, assistant, make_card, make_persona, make_story, user

VI = get_template("vi").dm_label


def dm(msg: Message) -> Message:
    return msg.model_copy(update={"mode": "dm"})


def mixed_history() -> list[Message]:
    return [
        assistant(0, GREETING),
        user(1, "Chào cậu."),
        assistant(2, "Chào."),
        dm(user(3, "Chào cậu, tôi là hàng xóm mới")),
        dm(assistant(4, "Chào... chào cậu.\nTôi là Tần Dương.")),
        user(5, "Sáng hôm sau tôi chào cậu bằng tên."),
    ]


def test_story_mode_labels_dm_turns_and_explains_in_f() -> None:
    built = build_prompt(make_card(), make_persona(), make_story(), mixed_history())
    turns = [m.content for m in built.messages[1:]]
    assert any(t.startswith(f"{VI} Chào cậu, tôi là hàng xóm mới") or f"\n\n{VI} Chào cậu, tôi là hàng xóm mới" in t for t in turns)
    assert any(t.startswith(f"{VI} Chào... chào cậu.") for t in turns)
    # Lượt story không mang nhãn; lời giải thích nằm ở F (message cuối), không ở system.
    assert f"{VI} Chào cậu.\n" not in "\n".join(turns)
    assert get_template("vi").dm_note(_ctx()) in built.messages[-1].content
    assert VI not in built.messages[0].content


def _ctx():  # type: ignore[no-untyped-def]
    from lyris.prompt.templates import PromptContext

    return PromptContext(card=make_card(), persona=make_persona(), story=make_story(), style="")


def test_system_identical_with_or_without_dm_turns() -> None:
    plain = [m.model_copy(update={"mode": "story"}) for m in mixed_history()]
    a = build_prompt(make_card(), make_persona(), make_story(), mixed_history())
    b = build_prompt(make_card(), make_persona(), make_story(), plain)
    assert a.messages[0].content == b.messages[0].content
    assert VI not in "\n".join(m.content for m in b.messages)


def test_dm_mode_has_no_labels() -> None:
    hist = mixed_history()[:-1] + [dm(user(5, "Ê"))]
    built = build_prompt(make_card(), make_persona(), make_story(mode="dm"), hist)
    assert VI not in "\n".join(m.content for m in built.messages)


def test_window_marks_same_in_both_modes() -> None:
    hist = mixed_history()
    assert window_boundaries(make_card(), make_persona(), make_story(), hist) == window_boundaries(
        make_card(), make_persona(), make_story(mode="dm"), hist
    )


def test_summary_transcript_marks_dm_turns() -> None:
    text = _transcript(make_card(), make_persona(), mixed_history(), 10_000, VI)
    assert f"{VI}: Chào... chào cậu." in text
    assert f"{VI}: Chào cậu." not in text.split("\n\n")[1]
