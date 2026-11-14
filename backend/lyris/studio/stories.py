"""Tạo story mới từ một cặp card + persona: thiết lập mặc định, tiêu đề, lời mở đầu lượt 0."""
from __future__ import annotations

from collections.abc import Mapping

from lyris.db.repo import Repo
from lyris.models import (
    CharacterCard,
    Gender,
    Language,
    Message,
    NarrationPronouns,
    Persona,
    RelationshipType,
    Story,
    StorySettings,
)
from lyris.state.fold import initial_relationship

# Đại từ dẫn truyện ngôi thứ ba khi profile không ghi (hoặc để trống). vi "other" = tên nhân vật.
_FALLBACK_NARRATION: dict[str, dict[str, str]] = {
    "vi": {"male": "anh", "female": "cô", "other": ""},
    "en": {"male": "he", "female": "she", "other": "they"},
}

NO_GREETING = -1


def _profile_narration(style_profile: str) -> Mapping[str, Mapping[str, str]]:
    """narration[language][gender] từ frontmatter của style profile; {} nếu không đọc được."""
    try:
        from lyris.prompt import builder
    except ImportError:
        return {}
    getter = getattr(builder, "get_style_profile", None)
    if getter is None:
        return {}
    try:
        return getter(style_profile).narration
    except ValueError:
        return {}


def _pronoun(
    narration: Mapping[str, Mapping[str, str]], language: Language, gender: Gender, name: str
) -> str:
    value = (narration.get(language) or {}).get(gender, "").strip()
    if not value:
        value = _FALLBACK_NARRATION[language][gender]
    return value or name.strip()


def _relationship(a: Gender, b: Gender) -> RelationshipType:
    pair = {a, b}
    if "other" in pair:
        return "none"
    if pair == {"male", "female"}:
        return "het"
    return "bl" if pair == {"male"} else "gl"


def fill_placeholders(text: str, card: CharacterCard, persona: Persona) -> str:
    """Thay `{{char}}`/`{{user}}` đúng như prompt builder (PromptContext.fill)."""
    from lyris.prompt.templates import PromptContext

    dummy = Story(
        card_id=card.id or 0,
        persona_id=persona.id or 0,
        title="",
        narration_pronouns=NarrationPronouns(character="", player=""),
    )
    return PromptContext(card=card, persona=persona, story=dummy, style="").fill(text)


def card_narration_pronoun(card: CharacterCard, language: Language) -> str | None:
    """Đại từ dẫn truyện riêng của card, nếu card đặt (ví dụ "hắn" thay vì "anh" của style).

    Lưu ở card.extensions["lyris"]["narration_character"]: chuỗi (dùng cho tiếng Việt) hoặc
    {"vi": "...", "en": "..."}. Không có hoặc rỗng thì trả None (dùng mặc định của style profile).
    """
    own = card.extensions.get("lyris")
    value = own.get("narration_character") if isinstance(own, dict) else None
    if isinstance(value, dict):
        value = value.get(language)
    elif language != "vi":
        value = None
    return value.strip() if isinstance(value, str) and value.strip() else None


def default_settings(card: CharacterCard, persona: Persona, language: Language | None = None) -> StorySettings:
    """Thiết lập mặc định cho story mới của cặp card + persona."""
    lang: Language = language or card.language
    narration = _profile_narration(card.style_profile)
    return StorySettings(
        scenario=fill_placeholders(card.scenario, card, persona),
        language=lang,
        mode="story",
        relationship_type=_relationship(card.gender, persona.gender),
        pov="third",
        thought_style="inline",
        narration_pronouns=NarrationPronouns(
            character=card_narration_pronoun(card, lang) or _pronoun(narration, lang, card.gender, card.name),
            player=_pronoun(narration, lang, persona.gender, persona.name),
        ),
    )


def default_title(card: CharacterCard, persona: Persona) -> str:
    return f"{card.name.strip()} & {persona.name.strip()}"


def greeting_options(card: CharacterCard) -> list[str]:
    """Các lời mở đầu theo chỉ số: 0 = greeting, i = alternate_greetings[i-1]."""
    return [card.greeting, *card.alternate_greetings]


def insert_greeting(repo: Repo, story: Story, raw: str) -> Message | None:
    """Chèn lời mở đầu làm message assistant lượt 0 (tách Thought). Chuỗi rỗng -> None."""
    if not raw.strip():
        return None
    if story.id is None:
        raise ValueError("Story chưa được lưu")
    # Import muộn: lyris.llm.thought do module khác phụ trách (test có thể thay bằng bản tạm).
    from lyris.llm.thought import split_thought

    visible, thought = split_thought(raw)
    return repo.insert_message(
        Message(
            story_id=story.id,
            turn_index=0,
            role="assistant",
            mode=story.mode,
            raw_content=raw,
            visible_content=visible,
            thought=thought,
        )
    )


def create_story_for(
    repo: Repo,
    card_id: int,
    persona_id: int,
    *,
    title: str | None = None,
    greeting_index: int = 0,
    settings: StorySettings | None = None,
    model_name: str,
    account_id: int,
    show_thoughts: bool = True,
) -> Story:
    """Tạo story cho card + persona, chèn lời mở đầu đã chọn (đã thay {{char}}/{{user}}).

    greeting_index: 0 = greeting, i = alternate_greetings[i-1], -1 = không có lời mở đầu.
    `account_id`: chủ story (bắt buộc, Phase 4b); card/persona phải thuộc account đó (card có thể là bản sao
    của chính account, §4.3).
    NotFound nếu card/persona không có; ValueError nếu greeting_index ngoài phạm vi.
    Story ghi lại điểm xuất phát quan hệ của card lúc tạo (`stories.initial_relationship_json`).
    """
    with repo.transaction():
        card = repo.get_card(card_id, account_id=account_id)
        persona = repo.get_persona(persona_id, account_id=account_id)
        options = greeting_options(card)
        if greeting_index == NO_GREETING:
            raw_greeting = ""
        elif 0 <= greeting_index < len(options):
            raw_greeting = options[greeting_index]
        else:
            raise ValueError(
                f"Không có lời mở đầu số {greeting_index}; nhân vật này có {len(options)} lời mở đầu"
                f" (chỉ số 0 đến {len(options) - 1}, hoặc -1 để bỏ trống)."
            )
        cfg = settings if settings is not None else default_settings(card, persona)
        story = repo.create_story(
            Story(
                card_id=card_id,
                persona_id=persona_id,
                title=(title or "").strip() or default_title(card, persona),
                scenario=cfg.scenario,
                language=cfg.language,
                mode=cfg.mode,
                relationship_type=cfg.relationship_type,
                pov=cfg.pov,
                thought_style=cfg.thought_style,
                narration_pronouns=cfg.narration_pronouns,
                model_name=model_name,
                show_thoughts=show_thoughts,
            ),
            account_id=account_id,
            # Phase 3: chụp điểm xuất phát của 6 chỉ số cảm xúc; sửa card sau này không đổi story đã có.
            initial_relationship=initial_relationship(None, card.extensions),
        )
        if raw_greeting.strip():
            insert_greeting(repo, story, fill_placeholders(raw_greeting, card, persona))
    return story


__all__ = [
    "NO_GREETING",
    "create_story_for",
    "default_settings",
    "default_title",
    "fill_placeholders",
    "greeting_options",
    "insert_greeting",
]
