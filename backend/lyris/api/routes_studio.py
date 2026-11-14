"""Endpoint của Character Studio (Phase 2): style profile, card, avatar, import/export, AI viết nháp,
xem trước prompt, chat thử, persona.

Lỗi trả `{"detail": "..."}` tiếng Việt (xem bộ xử lý lỗi trong app.py). Upload ảnh/file dùng raw body
(không multipart): server đọc `Content-Type` và các byte.
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import re
import unicodedata
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any, Literal
from urllib.parse import quote

import anyio
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, ConfigDict, Field

from lyris.api.deps import CurrentAccount, account_id_of, current_account
from lyris.api.sse import EventStreamResponse, event_stream_response
from lyris.chat.gate import GATE_TIMEOUT_DETAIL, AccountBusy, GateTimeout, GenerationGate, Ticket
from lyris.chat.service import Busy, ChatEvent, ChatService
from lyris.config import Settings
from lyris.db.repo import InUse, NotFound, Repo
from lyris.llm.base import LLMClient, LLMError
from lyris.llm.errors import UserFacingError, friendly
from lyris.lore.book import book_of, without_book
from lyris.models import (
    Account,
    AddressTerms,
    CharacterCard,
    ChatTurn,
    Gender,
    Language,
    Message,
    Persona,
    PromptLore,
    Story,
    StorySettings,
    StyleProfileInfo,
    Visibility,
)
from lyris.prompt.builder import PromptBudget, list_style_profiles
from lyris.studio import avatars
from lyris.studio.card_v2 import CardCreator, export_card_json, export_card_png, import_card, strip_template_marker
from lyris.studio.draft import draft_card
from lyris.studio.preview import TestTurn, build_preview, test_chat_stream

# Phase 4b: mặc định là cấm — mọi route ở đây cần đăng nhập (docs/auth.md §2.5).
router = APIRouter(prefix="/api", dependencies=[Depends(current_account)])

MAX_TEXT_CHARS = 20_000
MAX_TEXT_LABEL = "20.000"
MAX_NAME_CHARS = 80
MAX_ROLE_CHARS = 80
MAX_TAGS = 20
MAX_TAG_CHARS = 60
MAX_TERM_CHARS = 200
MAX_ALT_GREETINGS = 50
MAX_TEST_TURNS = 400
MAX_UPLOAD_BYTES = avatars.MAX_AVATAR_BYTES
SUMMARY_CHARS = 160
DRAFT_DISCONNECT_POLL_S = 0.5
COPY_SUFFIX = " (bản sao)"

# Phase 4b (docs/auth.md §5.4, §5.5): khoá viết nháp / chat thử vẫn chung cả máy; câu báo bận không đổ lỗi
# cho người dùng hiện tại (bản nháp kia có thể của người khác, hoặc của chính họ ở tab khác).
DRAFT_BUSY_DETAIL = "AI đang viết một bản nháp khác. Thử lại sau ít phút."
TEST_CHAT_BUSY_DETAIL = "Đang có người chat thử. Thử lại sau ít phút."
TEMPLATE_PUBLIC_DETAIL = "Nhân vật mẫu đã có sẵn cho mọi người."
UNLISTED_DETAIL = "Chế độ hiển thị chỉ có Riêng tư hoặc Công khai."
COPY_SNAPSHOT_DETAIL = "Nhân vật này của người khác nên không xem được phần này."
# Phase 4b (§4.4): khoá hồ sơ trong `extensions.lyris` mà trang nhân vật đang đọc (frontend/src/pages/character,
# lib/cardForm.ts, lib/signatureLines.ts). Danh sách trắng: khoá mới mặc định không lộ.
PUBLIC_LYRIS_KEYS: tuple[str, ...] = ("initial_relationship", "narration_character", "signature_lines")
PUBLIC_CARDS_LIMIT = 200

_CARD_TEXT_FIELDS: dict[str, str] = {
    "description": "mô tả",
    "personality": "tính cách",
    "appearance": "ngoại hình",
    "background": "hoàn cảnh",
    "goals": "mục tiêu",
    "secrets": "bí mật",
    "speech_style": "cách nói",
    "greeting": "lời mở đầu",
    "example_dialogues": "ví dụ thoại",
    "scenario": "bối cảnh",
    "creator_notes": "ghi chú người tạo",
}


# ---------------------------------------------------------------------------- body / response


class CardOut(CharacterCard):
    # Phase 2c: account tạo card (None nếu không xác định được)
    creator_handle: str | None = None
    creator_name: str | None = None
    avatar_url: str | None
    story_count: int
    updated_at: str | None


class CardSummary(BaseModel):
    id: int
    # Phase 2c
    uid: str | None = None
    visibility: Visibility = "private"
    creator_handle: str | None = None
    creator_name: str | None = None
    name: str
    role: str = ""  # Lyris design: không có trong CardSummary của types.ts (trường thêm)
    gender: Gender
    language: Language
    style_profile: str
    description: str
    tags: list[str]
    avatar_url: str | None
    story_count: int
    updated_at: str | None


class PublicCardView(BaseModel):
    """Phase 4b (docs/auth.md §4.4): những gì tài khoản khác thấy của một nhân vật công khai. Danh sách TRẮNG:
    không có tính cách, hoàn cảnh, mục tiêu, bí mật, ví dụ thoại, ghi chú người tạo, sổ thế giới, số story."""

    id: int
    uid: str | None = None
    name: str
    role: str = ""
    gender: Gender
    language: Language
    description: str = ""
    appearance: str = ""
    scenario: str = ""
    greeting: str = ""
    alternate_greetings: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    style_profile: str
    address_terms: AddressTerms = Field(default_factory=AddressTerms)
    speech_style: str = ""
    avatar_url: str | None = None
    creator_handle: str | None = None
    creator_name: str | None = None
    visibility: Visibility = "private"
    extensions: dict[str, Any] = Field(default_factory=dict)


class PublicCardOut(PublicCardView):
    """GET /api/cards/{id}/public: PublicCardView + `can_start` (false với bản sao)."""

    can_start: bool


class PublicCardSummary(BaseModel):
    """GET /api/public-cards (§6.4): CardSummary rút gọn + người tạo."""

    id: int
    uid: str | None = None
    visibility: Visibility = "public"
    name: str
    role: str = ""
    gender: Gender
    language: Language
    style_profile: str
    description: str
    tags: list[str]
    avatar_url: str | None
    updated_at: str | None
    creator_handle: str
    creator_name: str
    creator_avatar_url: str | None = None


class CardCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    card: CharacterCard
    avatar_token: str | None = Field(default=None, max_length=200)


class CardDraftResult(BaseModel):
    card: CharacterCard
    warnings: list[str]
    avatar_token: str | None


class DraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    idea: str = Field(max_length=MAX_TEXT_CHARS)
    language: Language = "vi"
    gender: Gender | None = None
    style_profile: str | None = Field(default=None, max_length=100)


class PreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    card: CharacterCard
    persona_id: int
    settings: StorySettings


class PromptPreview(BaseModel):
    messages: list[ChatTurn]
    token_estimate: dict[str, int]
    num_ctx: int


class TestChatRequest(PreviewRequest):
    __test__ = False  # không phải test class cho pytest

    messages: list[TestTurn] = Field(max_length=MAX_TEST_TURNS)


class PersonaBody(BaseModel):
    # Body theo hợp đồng là `Persona` (bỏ qua trường lạ): trang Persona gửi lại nguyên PersonaOut
    # (có `story_count`) khi sửa, nên không được từ chối trường thừa.
    model_config = ConfigDict(extra="ignore")
    id: int | None = None  # bỏ qua: id lấy từ đường dẫn hoặc do DB cấp
    name: str = Field(max_length=MAX_NAME_CHARS * 2)
    gender: Gender
    description: str = Field(default="", max_length=MAX_TEXT_CHARS)


class PersonaOut(Persona):
    story_count: int
    avatar_url: str | None = None  # Phase 2c


class DeletedStories(BaseModel):
    deleted_stories: int


# ---------------------------------------------------------------------------- truy cập state


def _repo(request: Request) -> Repo:
    repo: Repo = request.app.state.repo
    return repo


def _settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def _chat(request: Request) -> ChatService:
    chat: ChatService = request.app.state.chat
    return chat


def _avatars_dir(request: Request) -> Path:
    return _settings(request).avatars_dir


def _lore(request: Request) -> Any:
    """LoreService của app (Phase 4); None khi app chưa có (không chặn route nào)."""
    return getattr(request.app.state, "lore", None)


def _lore_for(request: Request, card: CharacterCard, persona: Persona, account_id: int) -> Any:
    """Phase 4: hàm dựng PromptLore cho xem trước / chat thử khi card đã lưu và thuộc account; None nếu không.

    Phase 4b (docs/auth.md §4.3): bản sao nhân vật công khai của người khác KHÔNG có sổ thế giới ở đây (gửi
    `card.id` của bản sao kèm lịch sử tự chế là đọc được từng mục sổ trong prompt trả về)."""
    lore = _lore(request)
    if lore is None or card.id is None:
        return None
    try:
        stored = _repo(request).get_card(card.id, account_id=account_id, copies=False)
    except NotFound:
        return None

    def build(story: Story, messages: list[Message]) -> PromptLore | None:
        # Dùng sổ thế giới đã lưu của card, với tên trong form đang sửa (fill {{char}} theo bản nháp).
        return lore.prompt_lore(story, card.model_copy(update={"id": stored.id}), persona, messages)

    return build


def _save_card_book(request: Request, card_id: int, extensions: dict[str, Any]) -> None:
    """Phase 4: `extensions.v2.character_book` của card vừa lưu thành các mục thế giới (theo slug)."""
    lore = _lore(request)
    if lore is not None and book_of(extensions) is not None:
        lore.apply_card_book(card_id, extensions)


def _budget(request: Request) -> PromptBudget:
    return PromptBudget(num_ctx=_settings(request).num_ctx)


def _lock(request: Request, name: str) -> asyncio.Lock:
    lock: asyncio.Lock | None = getattr(request.app.state, name, None)
    if lock is None:
        lock = asyncio.Lock()
        setattr(request.app.state, name, lock)
    return lock


# ---------------------------------------------------------------------------- tiện ích


def avatar_url_for(card_id: int | None, avatar: str | None) -> str | None:
    """URL ảnh đại diện; tham số `v` là tên file (đổi mỗi lần upload) để trình duyệt không dùng cache cũ."""
    if card_id is None or not avatar:
        return None
    return f"/api/cards/{card_id}/avatar?v={quote(avatar, safe='')}"


def avatar_url(card: CharacterCard) -> str | None:
    return avatar_url_for(card.id, card.avatar)


def persona_avatar_url(persona: Persona) -> str | None:
    if persona.id is None or not persona.avatar:
        return None
    return f"/api/personas/{persona.id}/avatar?v={quote(persona.avatar, safe='')}"


def card_out(repo: Repo, card: CharacterCard, creator: Account | None) -> CardOut:
    """CardOut; `creator` là account sở hữu card (route đã lọc theo account nên thường là account hiện tại)."""
    assert card.id is not None
    return CardOut(
        **card.model_dump(),
        creator_handle=creator.handle if creator else None,
        creator_name=creator.display_name if creator else None,
        avatar_url=avatar_url(card),
        story_count=repo.card_story_count(card.id),
        updated_at=repo.card_updated_at(card.id),
    )


def _public_extensions(extensions: dict[str, Any]) -> dict[str, Any]:
    """Chỉ những khoá hồ sơ của `extensions.lyris` (PUBLIC_LYRIS_KEYS); mọi thứ khác (sổ thế giới, dấu mẫu,
    khoá lạ của Card V2) bị bỏ."""
    own = extensions.get("lyris")
    if not isinstance(own, dict):
        return {}
    kept = {k: own[k] for k in PUBLIC_LYRIS_KEYS if k in own}
    return {"lyris": kept} if kept else {}


def public_card_view(card: CharacterCard, creator: Account | None) -> PublicCardView:
    """PublicCardView (§4.4) của `card`. `creator`: người tạo (với bản sao: người tạo card gốc, có thể None)."""
    assert card.id is not None
    return PublicCardView(
        id=card.id,
        uid=card.uid,
        name=card.name,
        role=card.role,
        gender=card.gender,
        language=card.language,
        description=card.description,
        appearance=card.appearance,
        scenario=card.scenario,
        greeting=card.greeting,
        alternate_greetings=list(card.alternate_greetings),
        tags=list(card.tags),
        style_profile=card.style_profile,
        address_terms=card.address_terms,
        speech_style=card.speech_style,
        avatar_url=avatar_url(card),
        creator_handle=creator.handle if creator else None,
        creator_name=creator.display_name if creator else None,
        visibility=card.visibility,
        extensions=_public_extensions(card.extensions),
    )


def copy_creator(repo: Repo, card_id: int) -> Account | None:
    """Người tạo card gốc của một bản sao ("bởi @handle", handle hiện tại); None nếu không xác định."""
    origin = repo.card_origin(card_id)
    if origin.origin_account_id is None:
        return None
    try:
        return repo.get_account(origin.origin_account_id)
    except NotFound:
        return None


def is_template_card(repo: Repo, card_id: int | None, extensions: dict[str, Any], account_id: int) -> bool:
    """Card là nhân vật mẫu đã cài (dấu `extensions.lyris.template`, hoặc được nhận là mẫu theo luật duy nhất
    `installed_template_ids`)."""
    own = extensions.get("lyris")
    if isinstance(own, dict) and own.get("template") is not None:
        return True
    if card_id is None:
        return False
    from lyris.api.routes_lyris import installed_template_ids
    from lyris.seed.templates import load_templates

    try:
        templates = load_templates()
    except Exception:
        return False
    return card_id in installed_template_ids(repo, templates, account_id).values()


def check_visibility(repo: Repo, card: CharacterCard, card_id: int | None, account_id: int) -> None:
    """Phase 4b (§6.4, §4.3): `visibility` chỉ nhận private | public; nhân vật mẫu đã cài không công khai được."""
    if card.visibility == "unlisted":
        raise _invalid(UNLISTED_DETAIL)
    if card.visibility == "public" and is_template_card(repo, card_id, card.extensions, account_id):
        raise _invalid(TEMPLATE_PUBLIC_DETAIL)


def _summary_text(text: str) -> str:
    text = " ".join(text.split())
    if len(text) <= SUMMARY_CHARS:
        return text
    return text[: SUMMARY_CHARS - 1].rstrip() + "…"


def card_summary(
    repo: Repo, card: CharacterCard, creator: Account | None, *, include_story_count: bool = True
) -> CardSummary:
    """`include_story_count=False`: luôn 0 (profile công khai không để lộ số story riêng tư)."""
    assert card.id is not None
    return CardSummary(
        id=card.id,
        uid=card.uid,
        visibility=card.visibility,
        creator_handle=creator.handle if creator else None,
        creator_name=creator.display_name if creator else None,
        name=card.name,
        role=card.role,
        gender=card.gender,
        language=card.language,
        style_profile=card.style_profile,
        description=_summary_text(card.description),
        tags=card.tags,
        avatar_url=avatar_url(card),
        story_count=repo.card_story_count(card.id) if include_story_count else 0,
        updated_at=repo.card_updated_at(card.id),
    )


def _invalid(detail: str) -> HTTPException:
    return HTTPException(status_code=422, detail=detail)


def _style_names() -> list[str]:
    return [s.name for s in list_style_profiles()]


def _check_style(name: str) -> None:
    names = _style_names()
    if name not in names:
        known = ", ".join(names) or "(chưa có)"
        raise _invalid(f'Không có style profile "{name}". Các profile hiện có: {known}.')


MAX_SIGNATURE_LINES = 3
MAX_SIGNATURE_CHARS = 140
_SIGNATURE_QUOTES = " \t\n\"'“”‘’«»「」"


def clean_signature_lines(raw: Any) -> list[str]:
    """`extensions.lyris.signature_lines` ("Lời nói đặc trưng" trên trang nhân vật), đọc dễ dãi.

    Giữ chuỗi, gộp khoảng trắng, bỏ ngoặc kép bao ngoài, bỏ dòng rỗng và dòng lặp (không phân biệt
    hoa thường), tối đa 3 dòng, mỗi dòng cắt còn 140 ký tự. Không phải list thì coi như không có.
    """
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, str):
            continue
        line = " ".join(item.split()).strip(_SIGNATURE_QUOTES)[:MAX_SIGNATURE_CHARS].strip()
        if not line or line.casefold() in seen:
            continue
        seen.add(line.casefold())
        out.append(line)
        if len(out) == MAX_SIGNATURE_LINES:
            break
    return out


def _clean_lyris_extensions(extensions: dict[str, Any]) -> dict[str, Any]:
    """Bản sao `extensions` với `lyris.signature_lines` đã làm sạch (bỏ khoá khi không còn dòng nào)."""
    lyris = extensions.get("lyris")
    if not isinstance(lyris, dict) or "signature_lines" not in lyris:
        return extensions
    lines = clean_signature_lines(lyris.get("signature_lines"))
    rest = {k: v for k, v in lyris.items() if k != "signature_lines"}
    if lines:
        rest["signature_lines"] = lines
    return {**extensions, "lyris": rest}


def validate_card(card: CharacterCard, *, require_name: bool = True) -> CharacterCard:
    """Kiểm tra card gửi lên và chuẩn hoá nhẹ (bỏ khoảng trắng thừa ở tên, tag, xưng hô).

    HTTP 422 với thông điệp tiếng Việt nếu sai.
    """
    name = card.name.strip()
    if require_name and not name:
        raise _invalid("Tên nhân vật không được để trống.")
    if len(name) > MAX_NAME_CHARS:
        raise _invalid(f"Tên nhân vật dài quá {MAX_NAME_CHARS} ký tự.")
    role = " ".join(card.role.split())
    if len(role) > MAX_ROLE_CHARS:
        raise _invalid(f"Vai trò dài quá {MAX_ROLE_CHARS} ký tự.")
    _check_style(card.style_profile)
    for field, label in _CARD_TEXT_FIELDS.items():
        if len(getattr(card, field)) > MAX_TEXT_CHARS:
            raise _invalid(f"Phần {label} dài quá {MAX_TEXT_LABEL} ký tự.")
    if len(card.alternate_greetings) > MAX_ALT_GREETINGS:
        raise _invalid(f"Tối đa {MAX_ALT_GREETINGS} lời mở đầu khác.")
    for i, text in enumerate(card.alternate_greetings, start=1):
        if len(text) > MAX_TEXT_CHARS:
            raise _invalid(f"Lời mở đầu khác số {i} dài quá {MAX_TEXT_LABEL} ký tự.")

    tags: list[str] = []
    seen: set[str] = set()
    for tag in card.tags:
        tag = tag.strip()
        if not tag or tag.casefold() in seen:
            continue
        if len(tag) > MAX_TAG_CHARS:
            raise _invalid(f'Tag "{tag[:20]}…" dài quá {MAX_TAG_CHARS} ký tự.')
        seen.add(tag.casefold())
        tags.append(tag)
    if len(tags) > MAX_TAGS:
        raise _invalid(f"Tối đa {MAX_TAGS} tag.")

    terms = card.address_terms
    for value, label in ((terms.self_term, "tự xưng"), (terms.player_term, "gọi người chơi")):
        if len(value) > MAX_TERM_CHARS:
            raise _invalid(f"Xưng hô ({label}) dài quá {MAX_TERM_CHARS} ký tự.")
    if len(terms.others) > MAX_TEXT_CHARS:
        raise _invalid(f"Xưng hô với người khác dài quá {MAX_TEXT_LABEL} ký tự.")
    nicknames = [n.strip() for n in terms.nicknames if n.strip()]
    if any(len(n) > MAX_TERM_CHARS for n in nicknames):
        raise _invalid(f"Tên gọi thân mật dài quá {MAX_TERM_CHARS} ký tự.")
    address = terms.model_copy(
        update={
            "self_term": terms.self_term.strip(),
            "player_term": terms.player_term.strip(),
            "nicknames": nicknames,
            "others": terms.others.strip(),
        }
    )
    try:
        size = len(json.dumps(card.extensions, ensure_ascii=False))
    except (TypeError, ValueError) as exc:
        raise _invalid("Phần extensions của card không phải JSON hợp lệ.") from exc
    if size > MAX_UPLOAD_BYTES:
        raise _invalid("Phần extensions của card quá lớn.")
    return card.model_copy(
        update={
            "name": name,
            "role": role,
            "tags": tags,
            "address_terms": address,
            "extensions": _clean_lyris_extensions(card.extensions),
        }
    )


def validate_persona(body: PersonaBody) -> Persona:
    name = body.name.strip()
    if not name:
        raise _invalid("Tên persona không được để trống.")
    if len(name) > MAX_NAME_CHARS:
        raise _invalid(f"Tên persona dài quá {MAX_NAME_CHARS} ký tự.")
    return Persona(name=name, gender=body.gender, description=body.description.strip())


async def read_body(request: Request, *, limit: int = MAX_UPLOAD_BYTES, what: str = "File") -> bytes:
    """Đọc raw body, dừng ngay khi vượt `limit` byte (không đọc hết file quá lớn vào bộ nhớ)."""
    too_big = _invalid(f"{what} quá lớn (tối đa {limit // (1024 * 1024)}MB).")
    length = request.headers.get("content-length")
    if length is not None and length.isdigit() and int(length) > limit:
        raise too_big
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit:
            raise too_big
        chunks.append(chunk)
    data = b"".join(chunks)
    if not data:
        raise _invalid(f"{what} trống.")
    return data


def _in_use_detail(count: int, what: str) -> str:
    return f"Có {count} story đang dùng {what}. Xoá luôn các story đó?"


def _ensure_stories_idle(
    request: Request, field: Literal["card_id", "persona_id"], target_id: int, account_id: int
) -> None:
    chat = _chat(request)
    for story in _repo(request).list_stories(account_id=account_id):
        if getattr(story, field) == target_id and story.id is not None and chat.is_busy(story.id):
            raise Busy(f'Story "{story.title}" đang sinh câu trả lời. Hãy đợi xong hoặc bấm Dừng rồi thử lại.')


def remove_orphan_avatars(request: Request) -> None:
    """Phase 4b (§4.3): xoá file avatar của các bản sao vừa bị dọn theo story (sau khi commit)."""
    avatars_dir = _avatars_dir(request)
    for name in _repo(request).pop_orphan_avatars():
        avatars.remove_avatar(avatars_dir, name)


def _stories_deleted(request: Request, story_ids: list[int]) -> None:
    """Báo hàng đợi job: worker dừng job đang chạy của các story vừa xoá (job đi theo CASCADE)."""
    jobs = getattr(request.app.state, "jobs", None)
    if jobs is None:
        return
    for story_id in story_ids:
        jobs.messages_changed(story_id)


_UNSAFE_FILENAME = re.compile(r'[\x00-\x1f\x7f/\\:*?"<>|]+')


def _file_stem(name: str) -> str:
    stem = _UNSAFE_FILENAME.sub(" ", name)
    stem = " ".join(stem.split()).strip(" .")
    return stem[:100] or "card"


def _ascii_fallback(stem: str) -> str:
    text = stem.replace("đ", "d").replace("Đ", "D")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = "".join(ch if 32 <= ord(ch) < 127 and ch not in '"\\;%' else "_" for ch in text)
    return text.strip(" ._") or "card"


def content_disposition(name: str, ext: str) -> str:
    """`attachment` với tên file UTF-8 theo RFC 5987 (`filename*`) và bản ASCII cho trình duyệt cũ."""
    stem = _file_stem(name)
    return (
        f'attachment; filename="{_ascii_fallback(stem)}.{ext}"; '
        f"filename*=UTF-8''{quote(stem, safe='')}.{ext}"
    )


def image_file_response(avatars_dir: Path, name: str | None, missing_detail: str) -> FileResponse:
    """File PNG trong avatars_dir, cache vĩnh viễn (tên file đổi mỗi lần upload). Không có -> 404.

    Phase 4b (docs/auth.md §3.2): ảnh cần đăng nhập nên `private` (trình duyệt dùng chung không để cache
    chung giữ ảnh của tài khoản khác); ảnh nhân vật mẫu (`/api/templates/{slug}/image`) vẫn `public`."""
    missing = HTTPException(status_code=404, detail=missing_detail)
    if not name:
        raise missing
    try:
        path = avatars.avatar_path(avatars_dir, name)
    except ValueError as exc:
        raise missing from exc
    if not path.is_file():
        raise missing
    return FileResponse(
        path,
        media_type="image/png",
        headers={"Cache-Control": "private, max-age=31536000, immutable"},
    )


def _read_avatar(avatars_dir: Path, name: str | None) -> bytes | None:
    if not name:
        return None
    try:
        path = avatars.avatar_path(avatars_dir, name)
    except ValueError:
        return None
    try:
        return path.read_bytes()
    except OSError:
        return None


# ---------------------------------------------------------------------------- styles


@router.get("/styles", response_model=list[StyleProfileInfo])
async def list_styles() -> list[StyleProfileInfo]:
    return list_style_profiles()


# ---------------------------------------------------------------------------- cards


@router.get("/cards", response_model=list[CardSummary])
async def list_cards(request: Request, account: CurrentAccount) -> list[CardSummary]:
    repo = _repo(request)
    return [card_summary(repo, c, account) for c in repo.list_cards(account_id=account_id_of(account))]


@router.post("/cards", response_model=CardOut)
async def create_card(request: Request, body: CardCreate, account: CurrentAccount) -> CardOut:
    repo = _repo(request)
    account_id = account_id_of(account)
    card = validate_card(body.card).model_copy(update={"id": None, "uid": None, "avatar": None})
    check_visibility(repo, card, None, account_id)
    extensions = card.extensions
    if _lore(request) is not None and book_of(extensions) is not None:
        # Phase 4: book của card thành mục thế giới; DB chỉ giữ một nguồn sự thật.
        card = card.model_copy(update={"extensions": without_book(extensions)})
    with repo.transaction():
        created = repo.create_card(card, account_id=account_id)
        assert created.id is not None
        _save_card_book(request, created.id, extensions)
    if body.avatar_token:
        # Phase 4b (§4.6): chỉ ảnh tạm do chính tài khoản này nhập.
        name = avatars.claim_temp(_avatars_dir(request), body.avatar_token, created.id, account_id)
        if name:
            created = repo.set_card_avatar(created.id, name, account_id=account_id)
    return card_out(repo, created, account)


# Các đường dẫn cố định (/cards/import, /cards/draft, ...) khai báo trước /cards/{card_id}.


@router.post("/cards/import", response_model=CardDraftResult)
async def import_card_file(request: Request, account: CurrentAccount) -> CardDraftResult:
    data = await read_body(request, what="File card")
    result = import_card(data, request.headers.get("content-type"), styles=_style_names())
    warnings = list(result.warnings)
    token: str | None = None
    if result.image:
        try:
            token = avatars.hold_temp(_avatars_dir(request), result.image, account_id_of(account))
        except avatars.AvatarError as exc:
            warnings.append(f"Ảnh trong card không dùng được nên đã bỏ qua: {exc}")
    # Card nhập vào thuộc account nhập (khi lưu); tác giả ghi trong file không quyết định chủ sở hữu.
    card = result.card.model_copy(update={"id": None, "uid": None, "avatar": None, "visibility": "private"})
    return CardDraftResult(card=card, warnings=warnings, avatar_token=token)


def effective_chat_model(repo: Repo, settings: Settings) -> str:
    """Model cho story mới: `default_chat_model` trong cài đặt chung, không có thì Settings.chat_model."""
    return repo.default_chat_model() or settings.chat_model


def _draft_model(request: Request) -> str:
    """Model viết nháp: LYRIS_DRAFT_MODEL nếu đặt riêng, không thì model chat mặc định người dùng chọn.

    config.py đặt `draft_model = chat_model` khi biến môi trường trống, nên khác nhau nghĩa là đặt riêng.
    """
    settings = _settings(request)
    if settings.draft_model != settings.chat_model:
        return settings.draft_model
    return effective_chat_model(_repo(request), settings)


def generation_gate(request: Request) -> GenerationGate:
    """Cổng sinh chung của cả máy (Phase 4b, docs/auth.md §5.1); app tạo trong lifespan."""
    gate: GenerationGate | None = getattr(request.app.state, "gate", None)
    if gate is None:
        gate = GenerationGate(_settings(request).chat_slots)
        request.app.state.gate = gate
    return gate


def reserve_generation(request: Request, account_id: int) -> Ticket:
    """Vé của cổng sinh cho chat thử / viết nháp. Tài khoản đang có lượt sinh khác -> 409."""
    try:
        return generation_gate(request).reserve(account_id)
    except AccountBusy as exc:
        raise Busy(str(exc)) from exc


@router.post("/cards/draft", response_model=CardDraftResult)
async def draft(request: Request, body: DraftRequest, account: CurrentAccount) -> CardDraftResult | Response:
    styles = list_style_profiles()
    if body.style_profile is not None:
        _check_style(body.style_profile)
    lock = _lock(request, "draft_lock")
    if lock.locked():
        raise Busy(DRAFT_BUSY_DETAIL)
    llm: LLMClient = request.app.state.llm
    # Phase 4b (§5.1): viết nháp cũng là một lượt sinh (cổng chung); khoá viết nháp vẫn chung cả máy.
    ticket = reserve_generation(request, account_id_of(account))
    try:
        async with lock:
            try:
                await ticket.wait()
            except GateTimeout as exc:
                raise Busy(GATE_TIMEOUT_DETAIL) from exc
            task = asyncio.ensure_future(
                draft_card(
                    llm,
                    _draft_model(request),
                    idea=body.idea,
                    language=body.language,
                    gender=body.gender,
                    style_profile=body.style_profile,
                    styles=styles,
                )
            )
            try:
                # Viết nháp mất 1-2 phút: người dùng bấm Huỷ (client ngắt kết nối) thì huỷ luôn request tới
                # model và nhả khoá, để lần thử sau không bị 409.
                while not task.done():
                    await asyncio.wait({task}, timeout=DRAFT_DISCONNECT_POLL_S)
                    if not task.done() and await request.is_disconnected():
                        task.cancel()
                        with contextlib.suppress(asyncio.CancelledError, Exception):
                            await task
                        return Response(status_code=499)
                card, warnings = task.result()
            except LLMError as exc:
                detail, technical = friendly(exc, "draft")
                raise UserFacingError(detail, status=502, technical=technical) from exc
            finally:
                if not task.done():
                    # Chính request này bị huỷ (server tắt...): không để task chạy mồ côi.
                    task.cancel()
                    with anyio.CancelScope(shield=True), contextlib.suppress(asyncio.CancelledError, Exception):
                        await task
    finally:
        ticket.release()
    card = card.model_copy(update={"id": None, "avatar": None})
    return CardDraftResult(card=card, warnings=warnings, avatar_token=None)


@router.post("/cards/preview-prompt", response_model=PromptPreview)
async def preview_prompt(request: Request, body: PreviewRequest, account: CurrentAccount) -> PromptPreview:
    card = validate_card(body.card, require_name=False)
    account_id = account_id_of(account)
    persona = _repo(request).get_persona(body.persona_id, account_id=account_id)
    budget = _budget(request)
    built = build_preview(
        card, persona, body.settings, budget=budget, lore_for=_lore_for(request, card, persona, account_id)
    )
    return PromptPreview(messages=built.messages, token_estimate=built.token_estimate, num_ctx=budget.num_ctx)


async def _locked_stream(
    lock: asyncio.Lock,
    events: AsyncIterator[ChatEvent],
    reserve: Callable[[], Ticket] | None = None,
) -> AsyncIterator[ChatEvent]:
    """Giữ `lock` suốt lượt stream; bận thì Busy ngay ở lần `__anext__` đầu (trước khi yield gì).

    Phase 4b (§5.1): `reserve` lấy vé của cổng sinh chung (tài khoản đang sinh ở chỗ khác -> Busy ngay); hết
    chỗ thì sự kiện `waiting` trước, chờ theo thứ tự đến, quá 120 giây thì sự kiện `error`."""
    if lock.locked():
        await _aclose(events)
        raise Busy(TEST_CHAT_BUSY_DETAIL)
    try:
        ticket = reserve() if reserve is not None else None
    except BaseException:
        await _aclose(events)
        raise
    # Khoá rảnh nên acquire() trả về ngay, không nhường event loop: kiểm tra + giữ khoá là nguyên tử.
    await lock.acquire()
    try:
        if ticket is not None and not ticket.ready:
            yield ChatEvent("waiting", {})
            try:
                await ticket.wait()
            except GateTimeout:
                yield ChatEvent("error", {"detail": GATE_TIMEOUT_DETAIL, "technical": None})
                return
        async for event in events:
            yield event
    finally:
        try:
            await _aclose(events)
        finally:
            if ticket is not None:
                ticket.release()
            lock.release()


async def _aclose(events: AsyncIterator[Any]) -> None:
    aclose = getattr(events, "aclose", None)
    if aclose is None:
        return
    with anyio.CancelScope(shield=True):
        await aclose()


@router.post("/cards/test-chat", response_class=EventStreamResponse)
async def test_chat(request: Request, body: TestChatRequest, account: CurrentAccount) -> EventStreamResponse:
    card = validate_card(body.card, require_name=False)
    account_id = account_id_of(account)
    persona = _repo(request).get_persona(body.persona_id, account_id=account_id)
    # Dựng prompt trước khi mở stream: lỗi dữ liệu thành HTTP 422 bình thường. Phase 4: card đã lưu thì có
    # cả sổ thế giới (để tác giả thử từ khoá; không ghi lại gì).
    built = build_preview(
        card,
        persona,
        body.settings,
        budget=_budget(request),
        history=body.messages,
        lore_for=_lore_for(request, card, persona, account_id),
    )
    llm: LLMClient = request.app.state.llm
    # Thử chat xem trước một story mới với card này: dùng đúng model story mới sẽ dùng.
    events = test_chat_stream(llm, effective_chat_model(_repo(request), _settings(request)), built)
    return await event_stream_response(
        _locked_stream(
            _lock(request, "test_chat_lock"), events, lambda: reserve_generation(request, account_id)
        )
    )


@router.get("/public-cards", response_model=list[PublicCardSummary])
async def list_public_cards(request: Request, account: CurrentAccount) -> list[PublicCardSummary]:
    """Phase 4b (§6.4): nhân vật công khai của tài khoản KHÁC (người tạo active), mới sửa trước, tối đa 200.
    Không có bản sao, không có số story."""
    repo = _repo(request)
    out: list[PublicCardSummary] = []
    for card, creator in repo.list_public_cards(exclude_account_id=account_id_of(account), limit=PUBLIC_CARDS_LIMIT):
        assert card.id is not None
        out.append(
            PublicCardSummary(
                id=card.id,
                uid=card.uid,
                visibility=card.visibility,
                name=card.name,
                role=card.role,
                gender=card.gender,
                language=card.language,
                style_profile=card.style_profile,
                description=_summary_text(card.description),
                tags=card.tags,
                avatar_url=avatar_url(card),
                updated_at=repo.card_updated_at(card.id),
                creator_handle=creator.handle,
                creator_name=creator.display_name,
                creator_avatar_url=(
                    f"/api/accounts/{quote(creator.handle, safe='')}/avatar?v={quote(creator.avatar, safe='')}"
                    if creator.avatar
                    else None
                ),
            )
        )
    return out


@router.get("/cards/{card_id}", response_model=CardOut)
async def get_card(request: Request, card_id: int, account: CurrentAccount) -> CardOut:
    """Card đầy đủ: chỉ của chính mình, không phải bản sao (người khác dùng `/public`, §4.1)."""
    repo = _repo(request)
    return card_out(repo, repo.get_card(card_id, account_id=account_id_of(account), copies=False), account)


@router.get("/cards/{card_id}/public", response_model=PublicCardOut)
async def get_public_card(request: Request, card_id: int, account: CurrentAccount) -> PublicCardOut:
    """Phase 4b (§4.4, §6.4): hồ sơ chỉ đọc. Card của mình (người tạo xem "người khác thấy gì"), bản sao của
    mình (`can_start` false, "bởi @handle" của người tạo gốc), hoặc card công khai của người khác."""
    repo = _repo(request)
    account_id = account_id_of(account)
    try:
        card = repo.get_card(card_id, account_id=account_id)
    except NotFound:
        card = repo.get_public_card(card_id)  # NotFound -> 404
        owner_id = repo.card_account_id(card_id)
        creator = repo.get_account(owner_id) if owner_id is not None else None
        return PublicCardOut(**public_card_view(card, creator).model_dump(), can_start=True)
    if repo.card_origin(card_id).story_copy:
        return PublicCardOut(**public_card_view(card, copy_creator(repo, card_id)).model_dump(), can_start=False)
    return PublicCardOut(**public_card_view(card, account).model_dump(), can_start=True)


@router.put("/cards/{card_id}", response_model=CardOut)
async def update_card(request: Request, card_id: int, body: CharacterCard, account: CurrentAccount) -> CardOut:
    """Sửa card (gồm `visibility`); id, uid, avatar giữ nguyên dù body gửi gì."""
    repo = _repo(request)
    account_id = account_id_of(account)
    current = repo.get_card(card_id, account_id=account_id, copies=False)
    update: dict[str, object] = {"id": card_id, "uid": current.uid, "avatar": current.avatar}
    if "visibility" not in body.model_fields_set:
        # A client that does not know the field (an older editor, a script) keeps the stored value.
        update["visibility"] = current.visibility
    card = validate_card(body).model_copy(update=update)
    if "visibility" in body.model_fields_set or card.visibility == "public":
        check_visibility(repo, card, card_id, account_id)
    extensions = card.extensions
    if _lore(request) is not None and book_of(extensions) is not None:
        # Phase 4: như POST /cards (trình sửa còn giữ extensions của bản nháp): chuyển book thành mục theo
        # slug (không nhân đôi), rồi bỏ book.
        card = card.model_copy(update={"extensions": without_book(extensions)})
    with repo.transaction():
        updated = repo.update_card(card_id, card, account_id=account_id)
        _save_card_book(request, card_id, extensions)
    return card_out(repo, updated, account)


@router.delete("/cards/{card_id}", response_model=DeletedStories)
async def delete_card(
    request: Request, card_id: int, account: CurrentAccount, with_stories: bool = False
) -> DeletedStories:
    repo = _repo(request)
    account_id = account_id_of(account)
    card = repo.get_card(card_id, account_id=account_id, copies=False)
    _ensure_stories_idle(request, "card_id", card_id, account_id)
    try:
        deleted = repo.delete_card_stories(card_id, with_stories=with_stories, account_id=account_id)
    except InUse as exc:
        raise HTTPException(status_code=409, detail=_in_use_detail(exc.count, "nhân vật này")) from exc
    avatars.remove_avatar(_avatars_dir(request), card.avatar)
    remove_orphan_avatars(request)
    _stories_deleted(request, deleted)
    return DeletedStories(deleted_stories=len(deleted))


@router.post("/cards/{card_id}/duplicate", response_model=CardOut)
async def duplicate_card(request: Request, card_id: int, account: CurrentAccount) -> CardOut:
    """Bản sao là card mới của account hiện tại: uid mới, riêng tư, không mang dấu template."""
    repo = _repo(request)
    account_id = account_id_of(account)
    source = repo.get_card(card_id, account_id=account_id, copies=False)
    base = source.name.strip()[: MAX_NAME_CHARS - len(COPY_SUFFIX)].rstrip()
    copy = source.model_copy(
        update={"id": None, "uid": None, "avatar": None, "visibility": "private", "name": base + COPY_SUFFIX},
        deep=True,
    )
    copy = copy.model_copy(update={"extensions": strip_template_marker(copy.extensions)})
    created = repo.create_card(copy, account_id=account_id)
    assert created.id is not None
    lore = _lore(request)
    if lore is not None and source.id is not None:
        lore.copy(source.id, created.id)  # Phase 4: bản sao mang theo sổ thế giới
    image = _read_avatar(_avatars_dir(request), source.avatar)
    if image is not None:
        try:
            name = avatars.save_card_avatar(_avatars_dir(request), created.id, image)
        except avatars.AvatarError:
            name = None
        if name:
            created = repo.set_card_avatar(created.id, name, account_id=account_id)
    return card_out(repo, created, account)


@router.put("/cards/{card_id}/avatar", response_model=CardOut)
async def upload_avatar(request: Request, card_id: int, account: CurrentAccount) -> CardOut:
    repo = _repo(request)
    account_id = account_id_of(account)
    card = repo.get_card(card_id, account_id=account_id, copies=False)
    data = await read_body(request, what="Ảnh")
    avatars_dir = _avatars_dir(request)
    name = avatars.save_card_avatar(avatars_dir, card_id, data)
    try:
        updated = repo.set_card_avatar(card_id, name, account_id=account_id)
    except Exception:
        avatars.remove_avatar(avatars_dir, name)
        raise
    if card.avatar and card.avatar != name:
        avatars.remove_avatar(avatars_dir, card.avatar)
    return card_out(repo, updated, account)


@router.delete("/cards/{card_id}/avatar", response_model=CardOut)
async def delete_avatar(request: Request, card_id: int, account: CurrentAccount) -> CardOut:
    repo = _repo(request)
    account_id = account_id_of(account)
    card = repo.get_card(card_id, account_id=account_id, copies=False)
    updated = repo.set_card_avatar(card_id, None, account_id=account_id)
    avatars.remove_avatar(_avatars_dir(request), card.avatar)
    return card_out(repo, updated, account)


@router.get("/cards/{card_id}/avatar")
async def get_avatar(request: Request, card_id: int, account: CurrentAccount) -> FileResponse:
    """Ảnh của card mình (cả bản sao của mình), hoặc của card công khai của tài khoản khác (người tạo active,
    không phải bản sao; docs/auth.md §4.6). Còn lại 404."""
    repo = _repo(request)
    try:
        card = repo.get_card(card_id, account_id=account_id_of(account))
    except NotFound:
        card = repo.get_public_card(card_id)  # NotFound -> 404
    return image_file_response(_avatars_dir(request), card.avatar, "Nhân vật này chưa có ảnh đại diện.")


@router.get("/cards/{card_id}/export")
async def export_card(
    request: Request, card_id: int, account: CurrentAccount, format: Literal["json", "png"] = Query(default="json")
) -> Response:
    repo = _repo(request)
    card = repo.get_card(card_id, account_id=account_id_of(account), copies=False)
    assert account.uid is not None
    creator = CardCreator(handle=account.handle, uid=account.uid)
    lore = repo.list_lore(card_id)  # Phase 4: character_book dựng từ sổ thế giới
    if format == "json":
        payload = json.dumps(export_card_json(card, creator, lore), ensure_ascii=False, indent=2).encode("utf-8")
        media_type = "application/json; charset=utf-8"
    else:
        payload = export_card_png(card, _read_avatar(_avatars_dir(request), card.avatar), creator, lore)
        media_type = "image/png"
    return Response(
        content=payload,
        media_type=media_type,
        headers={"Content-Disposition": content_disposition(card.name, format), "Cache-Control": "no-store"},
    )


# ---------------------------------------------------------------------------- personas


def persona_out(repo: Repo, persona: Persona) -> PersonaOut:
    assert persona.id is not None
    return PersonaOut(
        **persona.model_dump(),
        story_count=repo.persona_story_count(persona.id),
        avatar_url=persona_avatar_url(persona),
    )


@router.get("/personas", response_model=list[PersonaOut])
async def list_personas(request: Request, account: CurrentAccount) -> list[PersonaOut]:
    repo = _repo(request)
    return [persona_out(repo, p) for p in repo.list_personas(account_id=account_id_of(account))]


@router.post("/personas", response_model=PersonaOut)
async def create_persona(request: Request, body: PersonaBody, account: CurrentAccount) -> PersonaOut:
    repo = _repo(request)
    return persona_out(repo, repo.create_persona(validate_persona(body), account_id=account_id_of(account)))


@router.put("/personas/{persona_id}", response_model=PersonaOut)
async def update_persona(
    request: Request, persona_id: int, body: PersonaBody, account: CurrentAccount
) -> PersonaOut:
    """Sửa tên, giới tính, mô tả; uid và avatar giữ nguyên (avatar đổi qua /personas/{id}/avatar)."""
    repo = _repo(request)
    account_id = account_id_of(account)
    repo.get_persona(persona_id, account_id=account_id)
    return persona_out(repo, repo.update_persona(persona_id, validate_persona(body), account_id=account_id))


@router.delete("/personas/{persona_id}", response_model=DeletedStories)
async def delete_persona(
    request: Request, persona_id: int, account: CurrentAccount, with_stories: bool = False
) -> DeletedStories:
    repo = _repo(request)
    account_id = account_id_of(account)
    persona = repo.get_persona(persona_id, account_id=account_id)
    _ensure_stories_idle(request, "persona_id", persona_id, account_id)
    try:
        deleted = repo.delete_persona_stories(persona_id, with_stories=with_stories, account_id=account_id)
    except InUse as exc:
        raise HTTPException(status_code=409, detail=_in_use_detail(exc.count, "persona này")) from exc
    avatars.remove_avatar(_avatars_dir(request), persona.avatar)
    remove_orphan_avatars(request)  # Phase 4b (§4.3): ảnh của bản sao vừa bị dọn theo story
    _stories_deleted(request, deleted)
    return DeletedStories(deleted_stories=len(deleted))


@router.put("/personas/{persona_id}/avatar", response_model=PersonaOut)
async def upload_persona_avatar(request: Request, persona_id: int, account: CurrentAccount) -> PersonaOut:
    """Ảnh raw (PNG/JPEG/WebP/GIF) -> `persona-<id>-<hex>.png` tối đa 768x768, bỏ metadata."""
    repo = _repo(request)
    account_id = account_id_of(account)
    persona = repo.get_persona(persona_id, account_id=account_id)
    data = await read_body(request, what="Ảnh")
    avatars_dir = _avatars_dir(request)
    name = avatars.save_persona_avatar(avatars_dir, persona_id, data)
    try:
        updated = repo.set_persona_avatar(persona_id, name, account_id=account_id)
    except Exception:
        avatars.remove_avatar(avatars_dir, name)
        raise
    if persona.avatar and persona.avatar != name:
        avatars.remove_avatar(avatars_dir, persona.avatar)
    return persona_out(repo, updated)


@router.delete("/personas/{persona_id}/avatar", response_model=PersonaOut)
async def delete_persona_avatar(request: Request, persona_id: int, account: CurrentAccount) -> PersonaOut:
    repo = _repo(request)
    account_id = account_id_of(account)
    persona = repo.get_persona(persona_id, account_id=account_id)
    updated = repo.set_persona_avatar(persona_id, None, account_id=account_id)
    avatars.remove_avatar(_avatars_dir(request), persona.avatar)
    return persona_out(repo, updated)


@router.get("/personas/{persona_id}/avatar")
async def get_persona_avatar(request: Request, persona_id: int, account: CurrentAccount) -> FileResponse:
    persona = _repo(request).get_persona(persona_id, account_id=account_id_of(account))
    return image_file_response(_avatars_dir(request), persona.avatar, "Persona này chưa có ảnh đại diện.")


__all__ = [
    "CardDraftResult",
    "CardOut",
    "CardSummary",
    "PersonaOut",
    "PublicCardOut",
    "PublicCardSummary",
    "PublicCardView",
    "avatar_url",
    "check_visibility",
    "copy_creator",
    "generation_gate",
    "public_card_view",
    "remove_orphan_avatars",
    "reserve_generation",
    "avatar_url_for",
    "card_out",
    "card_summary",
    "content_disposition",
    "image_file_response",
    "persona_avatar_url",
    "persona_out",
    "read_body",
    "router",
    "validate_card",
]
