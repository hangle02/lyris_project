"""Tóm tắt nối tiếp: tóm tắt cũ + các lượt vừa rơi khỏi cửa sổ lịch sử -> tóm tắt mới ≤ 180 từ.

Kết quả vào khối C của prompt ("Những gì đã xảy ra trước đó"). Chỉ chạy trong job `summarize`, nên
system message của chat chỉ đổi khi tóm tắt đổi và Ollama vẫn dùng lại được prompt cache.
"""
from __future__ import annotations

import re
from collections.abc import Sequence

from lyris.llm.base import LLMOutputError
from lyris.models import CharacterCard, ChatTurn, Message, Persona, Story
from lyris.prompt.templates import get_template

MAX_WORDS = 180
# Model đôi khi viết dư một chút; quá mức này thì cắt ở cuối câu gần nhất.
HARD_MAX_WORDS = 220
NUM_PREDICT = 600
TEMPERATURE = 0.3
# Phần chữ của transcript tối đa ~ num_ctx - phần dành cho hướng dẫn và câu trả lời, tính 3 ký tự/token.
_RESERVED_TOKENS = 1500
_CHARS_PER_TOKEN = 3
_MAX_MESSAGE_CHARS = 2500

SCHEMA: dict = {
    "type": "object",
    "properties": {"summary": {"type": "string"}},
    "required": ["summary"],
}

_SENTENCE_END = re.compile(r"(?<=[.!?…])\s+")


def _transcript(
    card: CharacterCard, persona: Persona, messages: Sequence[Message], max_chars: int, dm_label: str = ""
) -> str:
    """Lượt DM mang `dm_label` sau tên người nói: tóm tắt phải biết đó là tin nhắn (Story và DM chung
    một dòng thời gian), vd. nhân vật đã xưng tên qua tin nhắn."""
    c, p = card.name.strip(), persona.name.strip()
    lines: list[str] = []
    for msg in messages:
        text = msg.visible_content.strip()
        if not text:
            continue
        if len(text) > _MAX_MESSAGE_CHARS:
            text = text[:_MAX_MESSAGE_CHARS].rsplit(" ", 1)[0] + " …"
        who = p if msg.role == "user" else c
        if dm_label and msg.mode == "dm":
            who = f"{who} {dm_label}"
        lines.append(f"{who}: {text}")
    # Quá dài thì bỏ các lượt đầu (người gọi nên chia nhỏ; đây chỉ là chốt an toàn để không vượt num_ctx).
    while len(lines) > 1 and sum(len(x) + 2 for x in lines) > max_chars:
        lines.pop(0)
    return "\n\n".join(lines)


def _prompt(
    card: CharacterCard, persona: Persona, story: Story, previous: str | None, transcript: str
) -> list[ChatTurn]:
    c, p = card.name.strip(), persona.name.strip()
    if story.language == "en":
        system = (
            "You keep a running summary of an interactive roleplay story. Write in English. "
            "Reply with JSON only."
        )
        user = "\n".join(
            [
                f"Characters: {c} (the AI character) and {p} (the player).",
                "",
                "Summary so far:" if previous else "Summary so far: (none yet)",
                *([previous.strip()] if previous else []),
                "",
                "New turns to fold into the summary:",
                transcript,
                "",
                f"Write the updated summary in at most {MAX_WORDS} words: third person, past tense, using names. "
                "Merge the old summary with the new turns into one continuous account; drop small talk. "
                f"Keep proper names, places, promises, secrets that came out, and every turning point in the "
                f"relationship between {c} and {p}. Do not invent anything that is not in the text.",
            ]
        )
    else:
        system = (
            "Bạn ghi tóm tắt nối tiếp cho một story roleplay tương tác. Viết bằng tiếng Việt. Chỉ trả JSON."
        )
        user = "\n".join(
            [
                f"Nhân vật: {c} (nhân vật AI) và {p} (người chơi).",
                "",
                "Tóm tắt trước đó:" if previous else "Tóm tắt trước đó: (chưa có)",
                *([previous.strip()] if previous else []),
                "",
                "Các lượt mới cần gộp vào tóm tắt:",
                transcript,
                "",
                f"Viết tóm tắt mới, tối đa {MAX_WORDS} từ: ngôi thứ ba, gọi bằng tên, kể theo thứ tự thời gian. "
                "Gộp tóm tắt cũ với các lượt mới thành một đoạn liền mạch, bỏ chuyện vụn vặt. "
                f"Giữ tên riêng, nơi chốn, lời hứa, bí mật đã lộ và mọi bước ngoặt trong quan hệ giữa {c} và {p}. "
                "Không bịa thêm điều không có trong văn bản.",
            ]
        )
    return [ChatTurn(role="system", content=system), ChatTurn(role="user", content=user)]


def clip_words(text: str, max_words: int = HARD_MAX_WORDS) -> str:
    """Giữ nguyên nếu ≤ `max_words` từ; không thì cắt ở cuối câu cuối cùng còn nằm trong giới hạn."""
    words = text.split()
    if len(words) <= max_words:
        return text
    kept: list[str] = []
    count = 0
    for sent in _SENTENCE_END.split(text):
        n = len(sent.split())
        if count + n > max_words:
            break
        kept.append(sent)
        count += n
    if kept:
        return " ".join(kept).strip()
    return " ".join(words[:max_words]) + "…"


async def summarize(
    llm,  # noqa: ANN001 - LLMClient
    *,
    model: str,
    num_ctx: int,
    card: CharacterCard,
    persona: Persona,
    story: Story,
    previous: str | None,
    messages: list[Message],
) -> str:
    """Tóm tắt mới (≤ 180 từ, chặn cứng ở 220) từ tóm tắt cũ `previous` cộng `messages` (theo thứ tự lượt).

    Raise LLMError khi gọi model lỗi; LLMOutputError khi model trả tóm tắt rỗng.
    """
    previous = (previous or "").strip() or None
    max_chars = max(2000, (num_ctx - _RESERVED_TOKENS) * _CHARS_PER_TOKEN - len(previous or ""))
    transcript = _transcript(card, persona, messages, max_chars, get_template(story.language).dm_label)
    if not transcript:
        if previous:
            return previous
        raise LLMOutputError("Không có lượt nào để tóm tắt.")
    data = await llm.chat_json(
        model,
        _prompt(card, persona, story, previous, transcript),
        schema=SCHEMA,
        options={"num_ctx": num_ctx, "num_predict": NUM_PREDICT, "temperature": TEMPERATURE},
    )
    text = data.get("summary") if isinstance(data, dict) else None
    if not isinstance(text, str) or not text.strip():
        raise LLMOutputError("Model trả về tóm tắt rỗng. Hãy thử lại.")
    text = re.sub(r"[ \t]+", " ", text.strip())
    text = re.sub(r"\n{3,}", "\n\n", text)
    return clip_words(text)
