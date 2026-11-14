"""Gợi ý trả lời theo yêu cầu (Phase 3b, docs/phase3.md §10).

Chỉ chạy khi người chơi bấm "Nhận gợi ý" (hoặc "Gợi ý khác") ở menu "+" của ô nhập; không bao giờ tự
chạy sau mỗi lượt. Một lời gọi structured output (`chat_json`) bằng model chat của story, cùng `num_ctx`
(Ollama không nạp lại model). Đọc đoạn gần nhất của story (phần hiển thị, không có Thought: người chơi
không biết suy nghĩ thầm của nhân vật) và trả 3 gợi ý viết bằng giọng người chơi.

Schema không dùng `maxLength` (grammar của Ollama làm hỏng escape và xuống dòng khi có nó).
"""
from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from lyris.llm.base import LLMOutputError
from lyris.models import CharacterCard, ChatTurn, Message, Mode, Persona, SceneState, Story
from lyris.state.extract import GENDER_EN, GENDER_VI, normalize, player_address

NUM_PREDICT = 400
TEMPERATURE = 0.8  # "Gợi ý khác" phải ra hướng khác: cao hơn trích xuất (0.3)
MAX_SUGGESTIONS = 3
MAX_WORDS = 25
RECENT_MESSAGES = 6
_MAX_MESSAGE_CHARS = 1200
_MAX_RECENT_CHARS = 4000
_MAX_SUMMARY_CHARS = 800

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"suggestions": {"type": "array", "items": {"type": "string"}}},
    "required": ["suggestions"],
}

_QUOTE_PAIRS = {'"': '"', "“": "”", "'": "'", "«": "»"}
_BULLET = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")
_WS = re.compile(r"\s+")


def _clip(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + " …"


def _mode(story: Story, history: Sequence[Message]) -> Mode:
    for msg in reversed(history):
        if msg.role == "assistant":
            return msg.mode
    return story.mode


def _recent_lines(card: CharacterCard, persona: Persona, history: Sequence[Message], nothing: str) -> list[str]:
    """Các message cuối (tối đa RECENT_MESSAGES, tổng tối đa _MAX_RECENT_CHARS), cũ trước."""
    c, p = card.name.strip(), persona.name.strip()
    lines: list[str] = []
    total = 0
    for msg in reversed(history[-RECENT_MESSAGES:]):
        text = _clip(msg.visible_content, _MAX_MESSAGE_CHARS) or (nothing if msg.role == "user" else "")
        if not text:
            continue
        line = f"{p if msg.role == 'user' else c}: {text}"
        if lines and total + len(line) > _MAX_RECENT_CHARS:
            break
        lines.append(line)
        total += len(line)
    return list(reversed(lines))


def _scene_text(scene: SceneState | None) -> str:
    if scene is None:
        return ""
    return ", ".join(p.strip() for p in (scene.location, scene.time) if p and p.strip())


def _prompt_vi(
    card: CharacterCard,
    persona: Persona,
    story: Story,
    history: Sequence[Message],
    scene: SceneState | None,
    summary: str | None,
    avoid: Sequence[str],
) -> list[ChatTurn]:
    c, p = card.name.strip(), persona.name.strip()
    mode = _mode(story, history)
    role = f", {card.role.strip()}" if card.role.strip() else ""
    head = [
        f"Nhân vật AI: {c} ({GENDER_VI[card.gender]}{role}). Người chơi: {p} ({GENDER_VI[persona.gender]}).",
        "Kiểu story: "
        + ("Story (có dẫn truyện, hành động và lời thoại)." if mode == "story" else "Nhắn tin (DM), chỉ có tin nhắn."),
    ]
    at = card.address_terms
    player_self, player_calls = player_address(card)
    if at.self_term.strip() and at.player_term.strip():
        line = f'Xưng hô: {c} tự xưng "{at.self_term.strip()}", gọi {p} là "{at.player_term.strip()}".'
        if player_self:
            line += f' Khi {p} nói với {c}: {p} xưng "{player_self}", gọi {c} là "{player_calls}".'
        else:
            line += f" Khi {p} nói với {c}: gọi {c} là {player_calls}."
        head.append(line)
    where = _scene_text(scene)
    if where:
        head.append(f"Cảnh hiện tại: {where}.")
    if summary and summary.strip():
        head.append(f"Chuyện trước đó: {_clip(summary, _MAX_SUMMARY_CHARS)}")

    recent = ["Đoạn gần nhất của story:", *_recent_lines(card, persona, history, "(không viết gì)")]

    if mode == "story":
        call = f'"{player_calls}"' if player_self else player_calls
        style = (
            f'Viết ở ngôi "tôi" (tôi là {p}), như cách {p} vẫn viết: một hành động vài chữ rồi một câu thoại '
            f"trong ngoặc kép. Trong lời thoại, {p} gọi {c} là {call}"
            + (f' và xưng "{player_self}"' if player_self else "")
            + f'. Ví dụ: Tôi khẽ kéo tay áo {player_calls if player_self else c}. "..."'
        )
    else:
        style = "Mỗi gợi ý là một tin nhắn ngắn như người chơi tự gõ, không mô tả hành động" + (
            f', {p} xưng "{player_self}" và gọi {c} là "{player_calls}".' if player_self else "."
        )
    task = [
        f"Viết đúng 3 gợi ý cho lượt tiếp theo của {p}, như chính {p} tự gõ để đáp lại {c}, theo 3 hướng khác "
        "nhau (ví dụ một gợi ý ngọt ngào, một trêu chọc, một làm story rẽ sang hướng mới). Mỗi gợi ý tối đa "
        f"{MAX_WORDS} từ. {style} Không viết thay lời {c}. Không lặp lại câu {p} đã viết."
    ]
    taken = [a.strip() for a in avoid if a.strip()]
    if taken:
        task.append("Các gợi ý đã đưa trước đó (lần này phải khác hẳn):")
        task.extend(f"- {a}" for a in taken)
    user = "\n\n".join(["\n".join(head), "\n".join(recent), "\n".join(task)])
    system = (
        "Bạn giúp người chơi một story roleplay tương tác nghĩ ra lượt tiếp theo của họ. Viết bằng tiếng Việt, "
        "đúng giọng và đúng xưng hô của người chơi. Chỉ trả JSON."
    )
    return [ChatTurn(role="system", content=system), ChatTurn(role="user", content=user)]


def _prompt_en(
    card: CharacterCard,
    persona: Persona,
    story: Story,
    history: Sequence[Message],
    scene: SceneState | None,
    summary: str | None,
    avoid: Sequence[str],
) -> list[ChatTurn]:
    c, p = card.name.strip(), persona.name.strip()
    mode = _mode(story, history)
    role = f", {card.role.strip()}" if card.role.strip() else ""
    head = [
        f"AI character: {c} ({GENDER_EN[card.gender]}{role}). Player: {p} ({GENDER_EN[persona.gender]}).",
        "Story type: " + ("Story (narration, actions and dialogue)." if mode == "story" else "Text messages (DM) only."),
    ]
    where = _scene_text(scene)
    if where:
        head.append(f"Current scene: {where}.")
    if summary and summary.strip():
        head.append(f"Earlier in the story: {_clip(summary, _MAX_SUMMARY_CHARS)}")
    recent = ["Latest part of the story:", *_recent_lines(card, persona, history, "(wrote nothing)")]
    if mode == "story":
        style = (
            f'Write in first person as {p} would ("I ..."): a short action, then one line of dialogue in '
            'double quotes. Example: I tug at his sleeve. "..."'
        )
    else:
        style = "Each one is a short text message the player would type, with no action descriptions."
    task = [
        f"Write exactly 3 options for {p}'s next turn, as {p} would type them in reply to {c}, each going a "
        "different direction (e.g. one sweet, one teasing, one that takes the story somewhere new). At most "
        f"{MAX_WORDS} words each. {style} Never write {c}'s lines. Do not repeat what {p} already wrote."
    ]
    taken = [a.strip() for a in avoid if a.strip()]
    if taken:
        task.append("Options already offered (this time they must be clearly different):")
        task.extend(f"- {a}" for a in taken)
    user = "\n\n".join(["\n".join(head), "\n".join(recent), "\n".join(task)])
    system = (
        "You help the player of an interactive roleplay story come up with their next turn. Write in English, "
        "in the player's own voice. Reply with JSON only."
    )
    return [ChatTurn(role="system", content=system), ChatTurn(role="user", content=user)]


def build_messages(
    *,
    card: CharacterCard,
    persona: Persona,
    story: Story,
    history: Sequence[Message],
    scene: SceneState | None = None,
    summary: str | None = None,
    avoid: Sequence[str] = (),
) -> list[ChatTurn]:
    """System + user message cho lời gọi gợi ý, theo `story.language`."""
    build = _prompt_en if story.language == "en" else _prompt_vi
    return build(card, persona, story, history, scene, summary, avoid)


def _unwrap_quotes(text: str) -> str:
    """Bỏ cặp ngoặc kép bọc cả câu (`"Đi thôi"` -> `Đi thôi`) nếu bên trong không còn ngoặc kép nào."""
    if len(text) >= 2 and _QUOTE_PAIRS.get(text[0]) == text[-1]:
        inner = text[1:-1].strip()
        if not any(q in inner for q in ('"', "“", "”")):
            return inner
    return text


def validate(data: Any, *, player_texts: Sequence[str] = (), avoid: Sequence[str] = ()) -> list[str]:
    """Danh sách gợi ý sạch, tối đa 3: bỏ gạch đầu dòng/số thứ tự, ngoặc kép bọc cả câu, gợi ý rỗng, trùng
    nhau, trùng lời người chơi đã viết hoặc trùng gợi ý lần trước (`avoid`). Không bao giờ raise."""
    raw = data.get("suggestions") if isinstance(data, dict) else None
    taken = {normalize(t) for t in (*player_texts, *avoid) if t and t.strip()}
    out: list[str] = []
    for item in raw if isinstance(raw, list) else []:
        if len(out) >= MAX_SUGGESTIONS:
            break
        if not isinstance(item, str):
            continue
        text = _unwrap_quotes(_BULLET.sub("", _WS.sub(" ", item).strip()))
        key = normalize(text)
        if not key or key in taken:
            continue
        taken.add(key)
        out.append(text)
    return out


async def suggest_replies(
    llm,  # noqa: ANN001 - LLMClient
    *,
    model: str,
    num_ctx: int,
    card: CharacterCard,
    persona: Persona,
    story: Story,
    history: Sequence[Message],
    scene: SceneState | None = None,
    summary: str | None = None,
    avoid: Sequence[str] = (),
) -> list[str]:
    """1-3 gợi ý cho lượt tiếp của người chơi. `history`: message active, message cuối là của nhân vật.

    `avoid`: gợi ý lần trước (bấm "Gợi ý khác"), không được lặp lại. Raise LLMError khi gọi model lỗi,
    LLMOutputError khi model không cho gợi ý nào dùng được.
    """
    if not history or history[-1].role != "assistant":
        raise ValueError("Chỉ gợi ý được khi message cuối là của nhân vật (role 'assistant').")
    messages = build_messages(
        card=card, persona=persona, story=story, history=history, scene=scene, summary=summary, avoid=avoid
    )
    data = await llm.chat_json(
        model,
        messages,
        schema=SCHEMA,
        options={"num_ctx": num_ctx, "num_predict": NUM_PREDICT, "temperature": TEMPERATURE},
    )
    items = validate(data, player_texts=[m.visible_content for m in history if m.role == "user"], avoid=avoid)
    if not items:
        raise LLMOutputError("Model không trả gợi ý nào dùng được.")
    return items


__all__ = ["NUM_PREDICT", "SCHEMA", "TEMPERATURE", "build_messages", "suggest_replies", "validate"]
