"""Dữ liệu seed: nhân vật Lạc Dương, persona Lâm Vãn và story mặc định."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from lyris.db.repo import ANY_ACCOUNT, Repo
from lyris.models import CharacterCard, Persona, Story
from lyris.studio.stories import create_story_for, insert_greeting

SEED_DIR: Path = Path(__file__).resolve().parent


def _load_json(name: str) -> dict[str, Any]:
    data = json.loads((SEED_DIR / name).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"File seed {name} phải là một object JSON")
    return data


def load_seed_card() -> CharacterCard:
    return CharacterCard.model_validate(_load_json("lac_duong.json"))


SEED_TEMPLATE_SLUG = "lac-duong"


def seed_card_for_create() -> CharacterCard:
    """Card seed như lúc tạo mới trong DB: nội dung của lac_duong.json, thêm vai trò (lấy từ template
    cùng nhân vật) và đánh dấu `extensions.lyris.template` để trang Khám Phá nhận ra là đã cài."""
    card = load_seed_card()
    from lyris.seed.templates import get_template

    template = get_template(SEED_TEMPLATE_SLUG)
    role = card.role or (template.card.role if template is not None else "")
    ext = dict(card.extensions)
    lyris_ext = ext.get("lyris") if isinstance(ext.get("lyris"), dict) else {}
    ext["lyris"] = {**lyris_ext, "template": SEED_TEMPLATE_SLUG}
    return card.model_copy(update={"role": role, "extensions": ext})


def load_seed_persona() -> Persona:
    return Persona.model_validate(_load_json("lam_van.json"))


def load_default_story_settings() -> dict[str, Any]:
    """Thiết lập story mặc định (chưa có card_id/persona_id)."""
    return _load_json("default_story.json")


def _seed_card_and_persona(repo: Repo, account_id: int) -> tuple[CharacterCard, Persona]:
    """Card và persona seed của account; tạo nếu chưa có. Ưu tiên bản trùng tên với file seed (id nhỏ
    nhất), không có thì lấy bản tạo sớm nhất (list_cards/list_personas sắp theo lần sửa gần nhất)."""
    seed_card = load_seed_card()
    seed_persona = load_seed_persona()

    cards = sorted(repo.list_cards(account_id=account_id), key=lambda c: c.id or 0)
    card = next((c for c in cards if c.name == seed_card.name), None)
    if card is None:
        card = cards[0] if cards else repo.create_card(seed_card_for_create(), account_id=account_id)

    personas = sorted(repo.list_personas(account_id=account_id), key=lambda p: p.id or 0)
    persona = next((p for p in personas if p.name == seed_persona.name), None)
    if persona is None:
        persona = personas[0] if personas else repo.create_persona(seed_persona, account_id=account_id)
    return card, persona


def create_default_story(repo: Repo, title: str | None = None, *, account_id: int) -> Story:
    """Tạo story mới với card/persona seed và chèn lời mở đầu làm message assistant lượt 0.
    Mọi thứ thuộc `account_id` (bắt buộc, Phase 4b). Thành viên chưa có card nào thì được card Lạc Dương và
    persona Lâm Vãn CỦA RIÊNG HỌ (docs/auth.md §4.1); `list_cards` không bao giờ trả bản sao (§4.2).

    Card và persona seed còn nguyên (đúng tên) -> y hệt Phase 1: thiết lập trong default_story.json,
    lời mở đầu nguyên văn. Người dùng đã xoá card/persona seed nên phải dùng cặp khác -> thiết lập và
    lời mở đầu tính theo chính cặp đó (`create_story_for`), không mượn bối cảnh/đại từ của Lạc Dương.
    """
    with repo.transaction():
        owner = account_id
        card, persona = _seed_card_and_persona(repo, owner)
        assert card.id is not None and persona.id is not None
        settings = load_default_story_settings()
        if card.name != load_seed_card().name or persona.name != load_seed_persona().name:
            return create_story_for(
                repo,
                card.id,
                persona.id,
                title=title,
                model_name=str(settings.get("model_name") or Story.model_fields["model_name"].default),
                account_id=owner,
            )
        if title is not None and title.strip():
            settings["title"] = title.strip()
        story = repo.create_story(
            Story.model_validate({**settings, "card_id": card.id, "persona_id": persona.id}), account_id=owner
        )
        assert story.id is not None
        # Lời mở đầu seed giữ nguyên văn (card Lạc Dương viết thẳng tên, không dùng placeholder).
        insert_greeting(repo, story, card.greeting)
    return story


SEEDED_FLAG = "seeded"


def ensure_seed(repo: Repo) -> int | None:
    """Seed một lần cho mỗi DB: DB mới tinh (không card, persona, story) -> tạo card, persona và story
    mặc định cho account chủ máy, rồi đánh dấu cờ `seeded` trong app_settings. Những lần khởi động sau
    không seed lại, nên card/persona/story người dùng đã xoá không tự quay về. DB cũ (đã có dữ liệu)
    chỉ được đánh dấu. Trả id story mới nhất của account chủ máy, không có story nào -> None."""
    with repo.transaction():
        owner = repo.owner_id()
        if not repo.get_flag(SEEDED_FLAG):
            if not (
                repo.list_cards(account_id=ANY_ACCOUNT)
                or repo.list_personas(account_id=ANY_ACCOUNT)
                or repo.list_stories(account_id=ANY_ACCOUNT)
            ):
                create_default_story(repo, account_id=owner)
            repo.set_flag(SEEDED_FLAG)
        stories = repo.list_stories(account_id=owner)
        return stories[0].id if stories else None


__all__ = [
    "SEED_DIR",
    "SEEDED_FLAG",
    "create_default_story",
    "ensure_seed",
    "load_default_story_settings",
    "load_seed_card",
    "load_seed_persona",
    "seed_card_for_create",
]
