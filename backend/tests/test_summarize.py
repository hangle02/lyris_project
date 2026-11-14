"""Test tóm tắt nối tiếp (lyris/memory/summarize.py) bằng FakeLLM."""
from __future__ import annotations

import pytest

from lyris.llm.base import LLMError, LLMOutputError
from lyris.llm.fake import FakeLLM
from lyris.memory.summarize import HARD_MAX_WORDS, MAX_WORDS, SCHEMA, clip_words, summarize
from lyris.models import Message
from tests.test_prompt import make_card, make_persona, make_story


def msg(turn: int, role: str, text: str) -> Message:
    return Message(
        story_id=1, turn_index=turn, role=role, mode="story", raw_content=text + "\n[Thought: điều giấu kín XYZ]", visible_content=text  # type: ignore[arg-type]
    )


MESSAGES = [msg(1, "user", "Tớ mời cậu ăn lẩu nhé."), msg(2, "assistant", "Lạc Dương gật đầu, đi theo cô.")]


async def call(fake: FakeLLM, **kw: object) -> str:
    args: dict[str, object] = dict(
        model="gemma4:12b", num_ctx=8192, card=make_card(), persona=make_persona(), story=make_story(),
        previous="Hai người học ở thư viện.", messages=MESSAGES,
    )
    args.update(kw)
    return await summarize(fake, **args)  # type: ignore[arg-type]


async def test_summarize_prompt_and_options() -> None:
    fake = FakeLLM(json_replies=[{"summary": "  Lâm Vãn mời   Lạc Dương ăn lẩu. "}])
    out = await call(fake)
    assert out == "Lâm Vãn mời Lạc Dương ăn lẩu."
    c = fake.calls[0]
    assert c["schema"] == SCHEMA and "maxLength" not in str(SCHEMA)
    assert c["options"] == {"num_ctx": 8192, "num_predict": 600, "temperature": 0.3}
    user = c["messages"][1].content
    assert "Tóm tắt trước đó:\nHai người học ở thư viện." in user
    assert "Lâm Vãn: Tớ mời cậu ăn lẩu nhé." in user
    assert "Lạc Dương: Lạc Dương gật đầu, đi theo cô." in user
    assert "XYZ" not in user  # dùng visible_content
    assert f"tối đa {MAX_WORDS} từ" in user and "ngôi thứ ba" in user and "lời hứa" in user


async def test_summarize_en_without_previous() -> None:
    fake = FakeLLM(json_replies=[{"summary": "They had hotpot."}])
    out = await call(fake, story=make_story(language="en"), previous=None)
    assert out == "They had hotpot."
    user = fake.calls[0]["messages"][1].content
    assert "Summary so far: (none yet)" in user and "third person" in user


async def test_summarize_empty_result_is_output_error() -> None:
    with pytest.raises(LLMOutputError):
        await call(FakeLLM(json_replies=[{"summary": "  "}]))
    with pytest.raises(LLMOutputError):
        await call(FakeLLM(json_replies=[{"other": 1}]))


async def test_summarize_llm_error_propagates() -> None:
    with pytest.raises(LLMError):
        await call(FakeLLM(error=LLMError("mất kết nối")))


async def test_summarize_nothing_new_keeps_previous() -> None:
    fake = FakeLLM(json_replies=[{"summary": "x"}])
    assert await call(fake, messages=[msg(1, "user", "  ")]) == "Hai người học ở thư viện."
    assert fake.calls == []
    with pytest.raises(LLMOutputError):
        await call(fake, messages=[], previous=None)


async def test_summarize_drops_oldest_when_transcript_too_long() -> None:
    long_msgs = [msg(i, "user" if i % 2 else "assistant", f"Lượt {i} " + "chữ " * 600) for i in range(1, 30)]
    fake = FakeLLM(json_replies=[{"summary": "ok"}])
    await call(fake, messages=long_msgs, num_ctx=4096)
    user = fake.calls[0]["messages"][1].content
    assert "Lượt 29" in user and "Lượt 1 " not in user
    assert len(user) < 4096 * 3


def test_clip_words_cuts_at_sentence() -> None:
    short = "Một câu ngắn."
    assert clip_words(short) == short
    long = " ".join(f"Câu số {i} có năm từ." for i in range(100))
    out = clip_words(long)
    assert len(out.split()) <= HARD_MAX_WORDS and out.endswith(".")
    assert clip_words("từ " * 300).endswith("…")
