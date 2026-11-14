"""Xem trước prompt và "chat thử" cho card chưa lưu (Studio). Không ghi gì vào DB.

- `build_preview` dựng prompt bằng đúng `build_prompt` của chat thật, với một story giả (id 0)
  lấy từ `StorySettings`.
- `test_chat_stream` stream một lượt trả lời theo cùng định dạng sự kiện với chat thật:
  `start {}` -> `delta {kind, text}`* -> `done {raw, visible, thought, stats}` hoặc `error {detail}`.
  Người gọi đóng generator (client ngắt kết nối) thì request tới LLM bị huỷ ngay.
"""
from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator, Callable
from typing import Any, Literal

import anyio
from pydantic import BaseModel, Field

from lyris.chat.service import ChatEvent
from lyris.llm.base import Done, LLMClient, LLMError, LLMEvent, TextDelta
from lyris.llm.errors import EMPTY_PREVIEW, error_event
from lyris.llm.thought import ThoughtStreamParser, split_thought
from lyris.models import (
    BuiltPrompt,
    CharacterCard,
    GenStats,
    Language,
    Message,
    Persona,
    PromptLore,
    Story,
    StorySettings,
)
from lyris.prompt.builder import PromptBudget, build_prompt
from lyris.prompt.directives import extract_directives
from lyris.prompt.templates import PromptContext

logger = logging.getLogger("lyris.studio.preview")

MAX_TURN_CHARS = 20_000

SAMPLE_PLAYER_TURN: dict[Language, str] = {
    "vi": "(Lượt mẫu của người chơi)",
    "en": "(Sample player turn)",
}


class TestTurn(BaseModel):
    """Một lượt trong cuộc chat thử (client giữ toàn bộ lịch sử và gửi lại mỗi lượt)."""

    __test__ = False  # không phải test class cho pytest

    role: Literal["user", "assistant"]
    content: str = Field(max_length=MAX_TURN_CHARS)


def preview_story(card: CharacterCard, persona: Persona, settings: StorySettings) -> Story:
    """Story giả (id 0) dựng từ thiết lập; không bao giờ được lưu."""
    return Story(
        id=0,
        card_id=card.id or 0,
        persona_id=persona.id or 0,
        title=card.name.strip() or "Chat thử",
        scenario=settings.scenario,
        language=settings.language,
        mode=settings.mode,
        relationship_type=settings.relationship_type,
        pov=settings.pov,
        thought_style=settings.thought_style,
        narration_pronouns=settings.narration_pronouns,
    )


def _fill(card: CharacterCard, persona: Persona, story: Story, text: str) -> str:
    """Thay `{{char}}`/`{{user}}` như khi tạo story thật (lời mở đầu được thay trước khi lưu)."""
    return PromptContext(card=card, persona=persona, story=story, style="").fill(text)


def _history_messages(
    card: CharacterCard, persona: Persona, story: Story, history: list[TestTurn]
) -> list[Message]:
    """Chuyển lịch sử chat thử thành Message như chat thật (user: tách ((...)); assistant: tách Thought)."""
    out: list[Message] = []
    for index, turn in enumerate(history):
        if turn.role == "user":
            raw = turn.content.strip()
            visible, directive = extract_directives(raw)
            if not visible and directive is None:
                raise ValueError(f"lượt {index + 1} của người chơi đang trống.")
            out.append(
                Message(
                    story_id=0,
                    turn_index=index,
                    role="user",
                    mode=story.mode,
                    raw_content=raw,
                    visible_content=visible,
                    directive=directive,
                )
            )
        else:
            raw = _fill(card, persona, story, turn.content)
            if not raw:
                continue
            visible, thought = split_thought(raw)
            out.append(
                Message(
                    story_id=0,
                    turn_index=index,
                    role="assistant",
                    mode=story.mode,
                    raw_content=raw,
                    visible_content=visible,
                    thought=thought,
                )
            )
    return out


def _sample_history(card: CharacterCard, persona: Persona, story: Story) -> list[Message]:
    """Lời mở đầu của card (nếu có) + một lượt user mẫu, để thấy đủ khối E và F."""
    out: list[Message] = []
    greeting = _fill(card, persona, story, card.greeting)
    if greeting:
        visible, thought = split_thought(greeting)
        out.append(
            Message(
                story_id=0,
                turn_index=0,
                role="assistant",
                mode=story.mode,
                raw_content=greeting,
                visible_content=visible,
                thought=thought,
            )
        )
    sample = SAMPLE_PLAYER_TURN[story.language]
    out.append(
        Message(
            story_id=0,
            turn_index=len(out),
            role="user",
            mode=story.mode,
            raw_content=sample,
            visible_content=sample,
        )
    )
    return out


def build_preview(
    card: CharacterCard,
    persona: Persona,
    settings: StorySettings,
    *,
    budget: PromptBudget,
    history: list[TestTurn] | None = None,
    lore_for: Callable[[Story, list[Message]], PromptLore | None] | None = None,
) -> BuiltPrompt:
    """Dựng prompt cho card (có thể chưa lưu). ValueError nếu lịch sử sai hoặc style profile không có.

    `lore_for` (Phase 4): card đã lưu thì Studio truyền hàm dựng PromptLore từ sổ thế giới của card, để tác
    giả thử từ khoá trong chat thử (không ghi lại gì)."""
    story = preview_story(card, persona, settings)
    if history is None:
        messages = _sample_history(card, persona, story)
    else:
        if not history:
            raise ValueError("cuộc chat thử chưa có lượt nào của người chơi.")
        if history[-1].role != "user":
            raise ValueError("lượt cuối của cuộc chat thử phải là của người chơi.")
        messages = _history_messages(card, persona, story, history)
    lore = lore_for(story, messages) if lore_for is not None else None
    return build_prompt(card, persona, story, messages, budget=budget, lore=lore)


async def _close_quietly(stream: AsyncIterator[Any]) -> None:
    aclose = getattr(stream, "aclose", None)
    if aclose is None:
        return
    with anyio.CancelScope(shield=True):
        try:
            await aclose()
        except Exception:
            logger.exception("Lỗi khi đóng stream của model (chat thử)")


async def test_chat_stream(llm: LLMClient, model: str, built: BuiltPrompt) -> AsyncIterator[ChatEvent]:
    """Stream một lượt chat thử. Không ghi DB; đóng generator giữa chừng thì huỷ request tới LLM."""
    yield ChatEvent("start", {})
    parser = ThoughtStreamParser()
    parts: list[str] = []
    started = time.perf_counter()
    ttft_ms: float | None = None
    stats: GenStats | None = None
    stream: AsyncIterator[LLMEvent] | None = None
    try:
        error: dict[str, Any] | None = None
        try:
            stream = llm.chat_stream(model, built.messages, stop=built.stop, options=built.options)
            async for event in stream:
                if isinstance(event, TextDelta):
                    if not event.text:
                        continue
                    if ttft_ms is None:
                        ttft_ms = (time.perf_counter() - started) * 1000
                    parts.append(event.text)
                    for parsed in parser.feed(event.text):
                        yield ChatEvent("delta", {"kind": parsed.kind, "text": parsed.text})
                elif isinstance(event, Done):
                    stats = event.stats
        except LLMError as exc:
            error = error_event(exc, "preview")
        except Exception as exc:  # lỗi không lường trước từ client LLM: vẫn báo cho người dùng
            logger.exception("Lỗi không mong đợi khi chat thử")
            error = error_event(exc, "preview")

        if error is not None:
            yield ChatEvent("error", error)
            return

        for parsed in parser.flush():
            yield ChatEvent("delta", {"kind": parsed.kind, "text": parsed.text})

        raw = "".join(parts).strip()
        if not raw:
            yield ChatEvent(
                "error", {"detail": EMPTY_PREVIEW, "technical": "Model không trả về nội dung nào (phản hồi rỗng)."}
            )
            return
        if stats is None:
            stats = GenStats(ttft_ms=ttft_ms, total_ms=(time.perf_counter() - started) * 1000)
        visible, thought = split_thought(raw)
        yield ChatEvent(
            "done",
            {"raw": raw, "visible": visible, "thought": thought, "stats": stats.model_dump(mode="json")},
        )
    finally:
        if stream is not None:
            await _close_quietly(stream)


# pytest không được coi hàm này là test khi nó được import vào file test.
test_chat_stream.__test__ = False  # type: ignore[attr-defined]


__all__ = [
    "SAMPLE_PLAYER_TURN",
    "TestTurn",
    "build_preview",
    "preview_story",
    "test_chat_stream",
]
