"""Các endpoint /api. Lỗi trả `{"detail": "..."}` (xem bộ xử lý lỗi trong app.py)."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from lyris.analytics import buckets, track, tracker_of
from lyris.analytics import context as analytics_context
from lyris.analytics import store as analytics_store
from lyris.analytics.replies import tracked_reply
from lyris.api.deps import CurrentAccount, account_id_of, current_account, is_owner
from lyris.api.routes_lyris import (
    check_model_name,
    default_persona_id,
    effective_chat_model,
    make_preview,
    model_present,
)
from lyris.api.routes_studio import (
    COPY_SNAPSHOT_DETAIL,
    PublicCardView,
    avatar_url_for,
    copy_creator,
    is_template_card,
    persona_avatar_url,
    public_card_view,
    remove_orphan_avatars,
)
from lyris.api.sse import EventStreamResponse, event_stream_response
from lyris.auth import clock, errors
from lyris.auth.errors import AuthError
from lyris.chat.service import Busy, ChatService, message_out
from lyris.config import Settings
from lyris.db.repo import NotFound, Repo, StoryRow
from lyris.llm.base import LLMClient, LLMError
from lyris.models import (
    CharacterCard,
    Message,
    DominantEmotion,
    Language,
    Mode,
    NarrationPronouns,
    Persona,
    Pov,
    Rating,
    RelationshipType,
    Role,
    Story,
    StorySettings,
    ThoughtStyle,
)
from lyris.prompt.directives import extract_directives
from lyris.seed import create_default_story
from lyris.state.service import StateService
from lyris.studio.stories import create_story_for, default_settings, default_title

# Phase 4b: mặc định là cấm — mọi route ở đây cần đăng nhập (docs/auth.md §2.5).
router = APIRouter(prefix="/api", dependencies=[Depends(current_account)])

MAX_CONTENT_CHARS = 20_000


# ---------------------------------------------------------------------------- body / response


class StoryOut(Story):
    card_name: str
    persona_name: str
    card_avatar_url: str | None = None  # Phase 2
    updated_at: str | None = None  # Phase 2: hoạt động gần nhất (message mới nhất hoặc lần sửa thiết lập)
    # Lyris design
    card_role: str = ""
    last_preview: str | None = None  # phần hiển thị của tin active mới nhất, <= 140 ký tự
    last_role: Role | None = None
    last_mode: Mode | None = None
    # Phase 3: chip ở thẻ story trên hub; None khi chưa có dữ liệu thật
    dominant_emotion: DominantEmotion | None = None
    location: str | None = None


class StoryPersona(Persona):
    """Persona của story + URL avatar (Phase 2c: hiện cạnh bong bóng của người chơi)."""

    avatar_url: str | None = None


class StoryDetail(BaseModel):
    story: Story
    # Phase 4b (docs/auth.md §4.1, §4.4): story bắt đầu từ nhân vật công khai của người khác dùng một bản sao;
    # khi đó `card` là PublicCardView (không có bí mật, mục tiêu, sổ thế giới...), không phải card đầy đủ.
    card: CharacterCard | PublicCardView
    persona: StoryPersona


MAX_PRONOUN_CHARS = 40


class PronounsBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    character: str = Field(max_length=MAX_PRONOUN_CHARS)
    player: str = Field(max_length=MAX_PRONOUN_CHARS)


class SettingsPatch(BaseModel):
    """Thiết lập story gửi kèm khi tạo story; trường thiếu lấy từ `default_settings`."""

    model_config = ConfigDict(extra="forbid")
    scenario: str | None = Field(default=None, max_length=MAX_CONTENT_CHARS)
    language: Language | None = None
    mode: Mode | None = None
    relationship_type: RelationshipType | None = None
    pov: Pov | None = None
    thought_style: ThoughtStyle | None = None
    narration_pronouns: PronounsBody | None = None


class StoryCreate(BaseModel):
    """`{}` / `{title}`: story seed như Phase 1. Có `card_id` + `persona_id`: story cho cặp đó (Phase 2)."""

    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(default=None, max_length=200)
    card_id: int | None = None
    persona_id: int | None = None
    greeting_index: int = Field(default=0, ge=-1)
    settings: SettingsPatch | None = None
    # Phase 4 (B): hiện thẻ suy nghĩ hay không. Ở cấp ngoài (không thuộc thiết lập prompt); thiếu = bật.
    show_thoughts: bool | None = None


class StoryPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model_name: str | None = Field(default=None, max_length=200)  # Lyris design
    mode: Mode | None = None
    thought_style: ThoughtStyle | None = None
    title: str | None = Field(default=None, max_length=200)
    scenario: str | None = Field(default=None, max_length=MAX_CONTENT_CHARS)
    # Phase 2 (card và persona của story không đổi được)
    language: Language | None = None
    relationship_type: RelationshipType | None = None
    pov: Pov | None = None
    narration_pronouns: PronounsBody | None = None
    # Phase 4 (B): chỉ là cách hiển thị; đổi riêng trường này không đổi updated_at, không đụng job/prefill.
    show_thoughts: bool | None = None


class StoryDefaults(BaseModel):
    title: str
    settings: StorySettings


class ContentBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str = Field(max_length=MAX_CONTENT_CHARS)


class VariantBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    variant_index: int = Field(ge=0)


class FeedbackBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rating: Rating | None
    note: str | None = Field(default=None, max_length=MAX_CONTENT_CHARS)


class OllamaHealth(BaseModel):
    reachable: bool
    models: list[str]
    error: str | None


class Health(BaseModel):
    ok: bool
    chat_model: str
    ollama: OllamaHealth


# ---------------------------------------------------------------------------- truy cập state


def _repo(request: Request) -> Repo:
    repo: Repo = request.app.state.repo
    return repo


def _chat(request: Request) -> ChatService:
    chat: ChatService = request.app.state.chat
    return chat


def _state(request: Request) -> StateService | None:
    state: StateService | None = getattr(request.app.state, "state", None)
    return state


def _row_out(row: StoryRow, state: StateService | None = None) -> StoryOut:
    last_role = row.last_role if row.last_role in ("user", "assistant") else None
    last_mode = row.last_mode if row.last_mode in ("story", "dm") else None
    dominant, location = state.hub_info(row.story) if state is not None else (None, None)
    return StoryOut(
        **row.story.model_dump(),
        card_name=row.card_name,
        persona_name=row.persona_name,
        card_avatar_url=avatar_url_for(row.story.card_id, row.card_avatar),
        updated_at=row.updated_at,
        card_role=row.card_role,
        last_preview=make_preview(row.last_visible),
        last_role=last_role,
        last_mode=last_mode,
        dominant_emotion=dominant,
        location=location,
    )


def _story_out(repo: Repo, story: Story, account_id: int, state: StateService | None = None) -> StoryOut:
    assert story.id is not None
    rows = repo.story_rows(story.id, account_id=account_id)
    if not rows:
        repo.get_story(story.id, account_id=account_id)  # NotFound -> 404
        raise LookupError(f"Story {story.id} thiếu nhân vật hoặc persona")
    return _row_out(rows[0], state)


def _pronouns(body: PronounsBody) -> NarrationPronouns:
    character, player = body.character.strip(), body.player.strip()
    if not character or not player:
        raise HTTPException(status_code=422, detail="Đại từ dẫn truyện không được để trống.")
    return NarrationPronouns(character=character, player=player)


# ---------------------------------------------------------------------------- health


@router.get("/health", response_model=Health)
async def health(request: Request, account: CurrentAccount) -> Health:
    """`chat_model` là model story mới sẽ dùng (cài đặt chung, không có thì LYRIS_CHAT_MODEL).

    Phase 4b: thành viên không thấy tên model hay lệnh cài model (`models: []`, `chat_model: ""`, lỗi chỉ là
    một câu chung)."""
    full = await _health(request)
    if is_owner(account):
        return full
    error = None if full.ollama.error is None else "Lyris chưa sẵn sàng."
    return Health(ok=full.ok, chat_model="", ollama=OllamaHealth(reachable=full.ollama.reachable, models=[], error=error))


async def _health(request: Request) -> Health:
    settings: Settings = request.app.state.settings
    llm: LLMClient = request.app.state.llm
    chat_model = effective_chat_model(_repo(request), settings)
    list_models = getattr(llm, "list_models", None)
    if list_models is None:
        # Client không phải Ollama (ví dụ FakeLLM khi test): không có gì để dò.
        return Health(ok=True, chat_model=chat_model, ollama=OllamaHealth(reachable=True, models=[], error=None))
    try:
        models: list[str] = list(await list_models())
    except LLMError as exc:
        return Health(
            ok=True,
            chat_model=chat_model,
            ollama=OllamaHealth(reachable=False, models=[], error=str(exc)),
        )
    error = None
    if not model_present(chat_model, models):
        error = f"Ollama chưa có model {chat_model}. Hãy chạy: ollama pull {chat_model}"
    return Health(
        ok=True,
        chat_model=chat_model,
        ollama=OllamaHealth(reachable=True, models=models, error=error),
    )


# ---------------------------------------------------------------------------- stories


def _own_story(request: Request, account_id: int, story_id: int) -> Story:
    """Story của account hiện tại; story của account khác coi như không có (404)."""
    return _repo(request).get_story(story_id, account_id=account_id)


@router.get("/stories", response_model=list[StoryOut])
async def list_stories(request: Request, account: CurrentAccount) -> list[StoryOut]:
    state = _state(request)
    return [_row_out(row, state) for row in _repo(request).story_rows(account_id=account_id_of(account))]


@router.get("/stories/defaults", response_model=StoryDefaults)
async def story_defaults(
    request: Request,
    card_id: int,
    account: CurrentAccount,
    persona_id: int | None = None,
    language: Language | None = None,
) -> StoryDefaults:
    """Thiết lập mà POST /api/stories sẽ dùng cho cặp card + persona (khai báo trước /stories/{id}).

    Thiếu `persona_id` thì dùng persona mặc định (như POST /api/stories). Phase 4b: cùng luật card với
    POST /api/stories: card của mình (không phải bản sao) hoặc card công khai của người khác.
    """
    repo = _repo(request)
    account_id = account_id_of(account)
    card = _startable_card(repo, card_id, account_id)
    persona = repo.get_persona(_resolve_persona(repo, persona_id, account_id), account_id=account_id)
    return StoryDefaults(title=default_title(card, persona), settings=default_settings(card, persona, language))


def _startable_card(repo: Repo, card_id: int, account_id: int) -> CharacterCard:
    """Card bắt đầu story được (§4.1): của chính mình (không phải bản sao), hoặc công khai của người khác."""
    try:
        return repo.get_card(card_id, account_id=account_id, copies=False)
    except NotFound:
        if repo.card_account_id(card_id) == account_id:
            raise  # bản sao của chính mình: coi như không có
        return repo.get_public_card(card_id)


def _resolve_persona(repo: Repo, persona_id: int | None, account_id: int) -> int:
    if persona_id is not None:
        return persona_id
    resolved = default_persona_id(repo, account_id)
    if resolved is None:
        raise HTTPException(status_code=422, detail="Chưa có persona nào. Hãy tạo persona trước khi bắt đầu story.")
    return resolved


def _merged_settings(
    repo: Repo, card: CharacterCard, persona_id: int, patch: SettingsPatch | None, account_id: int
) -> StorySettings:
    persona = repo.get_persona(persona_id, account_id=account_id)
    fields: dict[str, Any] = {}
    if patch is not None:
        fields = {k: v for k, v in patch.model_dump(exclude_unset=True).items() if v is not None}
        if patch.narration_pronouns is not None:
            fields["narration_pronouns"] = _pronouns(patch.narration_pronouns)
    # Ngôn ngữ chọn khác ngôn ngữ card thì đại từ dẫn truyện mặc định theo ngôn ngữ đó.
    defaults = default_settings(card, persona, fields.get("language"))
    return StorySettings.model_validate({**defaults.model_dump(), **fields})


def _extract_opening(request: Request, story: Story) -> None:
    """Phase 3b: trích xuất lời mở đầu (cảnh + ký ức) ngay khi tạo story, để lượt đầu đã có cảnh."""
    jobs = getattr(request.app.state, "jobs", None)
    if jobs is None or story.id is None:
        return
    try:
        jobs.story_created(story.id, focus=True)  # app mở story mới ngay sau khi tạo
    except Exception:  # hàng đợi lỗi không được chặn việc tạo story
        logging.getLogger("lyris.api").exception("Không xếp được job cho lời mở đầu (story %s)", story.id)


@router.post("/stories", response_model=StoryOut)
async def create_story(
    request: Request, account: CurrentAccount, body: StoryCreate | None = Body(default=None)
) -> StoryOut:
    repo = _repo(request)
    account_id = account_id_of(account)
    settings: Settings = request.app.state.settings
    title = body.title.strip() if body and body.title else None
    if body is None or (body.card_id is None and body.persona_id is None):
        if body is not None and (body.settings is not None or body.greeting_index != 0):
            raise HTTPException(status_code=422, detail="Cần chọn nhân vật và persona cho story.")
        # Phase 1: story mới với nhân vật seed + lời mở đầu.
        story = create_default_story(repo, title, account_id=account_id)
        assert story.id is not None
        model = effective_chat_model(repo, settings)
        if story.model_name != model:
            story = repo.update_story(story.id, account_id=account_id, model_name=model)
        if body is not None and body.show_thoughts is False:
            story = repo.update_story(story.id, account_id=account_id, show_thoughts=False)
        _extract_opening(request, story)
        _track_story_started(request, story, "default")
        return _story_out(repo, story, account_id)
    if body.card_id is None:
        raise HTTPException(status_code=422, detail="Cần chọn nhân vật cho story.")
    card = _startable_card(repo, body.card_id, account_id)  # 404 trước khi xét persona
    public = repo.card_account_id(body.card_id) != account_id
    persona_id = _resolve_persona(repo, body.persona_id, account_id)
    story_settings = _merged_settings(repo, card, persona_id, body.settings, account_id)
    model_name = effective_chat_model(repo, settings)
    show_thoughts = body.show_thoughts if body.show_thoughts is not None else True
    if not public:
        story = create_story_for(
            repo,
            body.card_id,
            persona_id,
            title=title or None,
            greeting_index=body.greeting_index,
            settings=story_settings,
            model_name=model_name,
            account_id=account_id,
            show_thoughts=show_thoughts,
        )
    else:
        # Phase 4b (docs/auth.md §4.3): nhân vật công khai của người khác -> chụp thành bản sao CỦA NGƯỜI CHƠI
        # (card + sổ thế giới) và tạo story trỏ vào bản sao, trong MỘT transaction. Gốc vừa bị ẩn/xoá -> 404
        # "Nhân vật này không còn được chia sẻ." và không có dòng nào được tạo. Ảnh chép sau khi commit.
        with repo.transaction():
            copy = repo.copy_public_card(body.card_id, account_id=account_id)
            assert copy.id is not None
            story = create_story_for(
                repo,
                copy.id,
                persona_id,
                title=title or None,
                greeting_index=body.greeting_index,
                settings=story_settings,
                model_name=model_name,
                account_id=account_id,
                show_thoughts=show_thoughts,
            )
        copy_avatar_for(request, card, copy.id, account_id)
    _extract_opening(request, story)
    if public:
        source = "public"
    else:
        source = "template" if is_template_card(repo, body.card_id, card.extensions, account_id) else "own"
    _track_story_started(request, story, source)
    return _story_out(repo, story, account_id)


def _track_story_started(request: Request, story: Story, source: str) -> None:
    track(
        request, "story_started", {"mode": story.mode, "source": source, "language": story.language},
        story_id=story.id,
    )


def copy_avatar_for(request: Request, source: CharacterCard, copy_id: int, account_id: int) -> None:
    """Chép file avatar của card gốc thành file riêng của bản sao (§4.6): người tạo đổi/xoá ảnh không làm vỡ
    story của người khác. Lỗi thì bản sao không có ảnh, story vẫn tạo."""
    from lyris.studio import avatars

    if not source.avatar:
        return
    avatars_dir = request.app.state.settings.avatars_dir
    try:
        data = avatars.avatar_path(avatars_dir, source.avatar).read_bytes()
        name = avatars.save_card_avatar(avatars_dir, copy_id, data)
    except (OSError, ValueError):
        logging.getLogger("lyris.api").warning("Không chép được ảnh cho bản sao nhân vật %s", copy_id)
        return
    try:
        _repo(request).set_card_avatar(copy_id, name, account_id=account_id, copies=True)
    except Exception:
        avatars.remove_avatar(avatars_dir, name)
        raise


@router.get("/stories/{story_id}", response_model=StoryDetail)
async def get_story(request: Request, story_id: int, account: CurrentAccount) -> StoryDetail:
    repo = _repo(request)
    account_id = account_id_of(account)
    story = _own_story(request, account_id, story_id)
    persona = repo.get_persona(story.persona_id, account_id=account_id)
    card: CharacterCard | PublicCardView = repo.get_card(story.card_id, account_id=account_id)
    if repo.card_origin(story.card_id).story_copy:
        card = public_card_view(card, copy_creator(repo, story.card_id))
    return StoryDetail(
        story=story,
        card=card,
        persona=StoryPersona(**persona.model_dump(), avatar_url=persona_avatar_url(persona)),
    )


@router.patch("/stories/{story_id}", response_model=Story)
async def patch_story(request: Request, story_id: int, body: StoryPatch, account: CurrentAccount) -> Story:
    repo = _repo(request)
    account_id = account_id_of(account)
    current = _own_story(request, account_id, story_id)
    fields: dict[str, Any] = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    if "model_name" in fields and not is_owner(account):
        # Phase 4b: chỉ chủ máy đổi model của story; gửi lại đúng model đang dùng thì bỏ qua.
        if fields["model_name"].strip() != current.model_name:
            raise AuthError(403, errors.OWNER_ONLY, "owner_only")
        del fields["model_name"]
    if "title" in fields:
        fields["title"] = fields["title"].strip()
        if not fields["title"]:
            raise HTTPException(status_code=422, detail="Tên story không được để trống.")
    if body.narration_pronouns is not None:
        fields["narration_pronouns"] = _pronouns(body.narration_pronouns)
    if "model_name" in fields:
        fields["model_name"] = await check_model_name(request, fields["model_name"])
    before = current.mode
    updated = repo.update_story(story_id, account_id=account_id, **fields)
    if updated.mode != before:
        track(request, "mode_switched", {"to": updated.mode}, story_id=story_id)
    if updated.show_thoughts != current.show_thoughts:
        track(request, "show_thoughts_toggled", {"enabled": updated.show_thoughts}, story_id=story_id)
    jobs = getattr(request.app.state, "jobs", None)
    if jobs is not None and updated.mode != before:
        try:
            jobs.mode_changed(story_id)  # Phase 3b: cửa sổ có thể sắp dịch ở chế độ mới
        except Exception:
            logging.getLogger("lyris.api").exception("Không xếp được job tóm tắt khi đổi chế độ (story %s)", story_id)
    return updated


@router.delete("/stories/{story_id}")
async def delete_story(request: Request, story_id: int, account: CurrentAccount) -> dict[str, int]:
    repo = _repo(request)
    account_id = account_id_of(account)
    _own_story(request, account_id, story_id)
    if _chat(request).is_busy(story_id):
        raise Busy("Story đang sinh câu trả lời. Hãy đợi xong hoặc bấm Dừng rồi xoá lại.")
    repo.delete_story(story_id, account_id=account_id)
    remove_orphan_avatars(request)  # Phase 4b (§4.3): bản sao không còn story nào đã bị dọn cùng story
    jobs = getattr(request.app.state, "jobs", None)
    if jobs is not None:
        jobs.messages_changed(story_id)  # job đang chạy của story này dừng lại (job đi theo CASCADE)
    return {"deleted": 1}


@router.get("/stories/{story_id}/messages")
async def list_messages(request: Request, story_id: int, account: CurrentAccount) -> list[dict[str, Any]]:
    _own_story(request, account_id_of(account), story_id)
    return [message_out(m) for m in _repo(request).active_messages(story_id)]


def _with_tracking(request: Request, events: Any, story: Story, kind: str) -> Any:
    """Bọc stream để ghi reply_completed / reply_failed / lore_unlocked (docs/tracking-plan.md)."""
    assert story.id is not None
    return tracked_reply(
        events, tracker=tracker_of(request), ctx=analytics_context(request), story_id=story.id, mode=story.mode,
        kind=kind,
    )


def _track_message_sent(request: Request, story: Story, text: str, last_activity: str | None) -> None:
    """Chỉ ghi số liệu về lượt (độ dài theo khoảng, có hành động/chỉ đạo không), không bao giờ ghi chữ."""
    assert story.id is not None
    visible, directive = extract_directives(text)
    with _repo(request).locked() as conn:
        turns = analytics_store.user_turns(conn, story.id)
    track(
        request,
        "message_sent",
        {
            "mode": story.mode,
            "length_bucket": buckets.length_bucket(len(visible)),
            "has_action": buckets.has_action(visible),
            "has_directive": directive is not None,
            "user_turn": buckets.turn_bucket(turns),
        },
        story_id=story.id,
    )
    if last_activity is not None:
        days = (clock.now() - clock.parse(last_activity)).total_seconds() / 86_400
        if days >= 1:
            track(
                request, "story_resumed", {"days_since_last": buckets.days_bucket(days), "mode": story.mode},
                story_id=story.id,
            )


@router.post("/stories/{story_id}/messages", response_class=EventStreamResponse)
async def send_message(
    request: Request, story_id: int, body: ContentBody, account: CurrentAccount
) -> EventStreamResponse:
    story = _own_story(request, account_id_of(account), story_id)
    with _repo(request).locked() as conn:
        last = analytics_store.last_activity(conn, story_id)
    response = await event_stream_response(
        _with_tracking(request, _chat(request).send(story_id, body.content), story, "send")
    )
    _track_message_sent(request, story, body.content, last)  # lượt người chơi đã lưu (sự kiện đầu đã ra)
    return response


@router.post("/stories/{story_id}/reply", response_class=EventStreamResponse)
async def reply(request: Request, story_id: int, account: CurrentAccount) -> EventStreamResponse:
    story = _own_story(request, account_id_of(account), story_id)
    return await event_stream_response(_with_tracking(request, _chat(request).respond(story_id), story, "retry"))


# ---------------------------------------------------------------------------- messages


def _message_story(request: Request, account_id: int, message_id: int) -> tuple[Message, Story]:
    """Message và story của nó (404 nếu không thuộc tài khoản)."""
    repo = _repo(request)
    msg = repo.get_message(message_id, account_id=account_id)
    return msg, repo.get_story(msg.story_id, account_id=account_id)


@router.post("/messages/{message_id}/regenerate", response_class=EventStreamResponse)
async def regenerate(request: Request, message_id: int, account: CurrentAccount) -> EventStreamResponse:
    _, story = _message_story(request, account_id_of(account), message_id)
    response = await event_stream_response(
        _with_tracking(request, _chat(request).regenerate(message_id), story, "regenerate")
    )
    track(request, "regenerate_used", {"mode": story.mode}, story_id=story.id)
    return response


@router.post("/messages/{message_id}/variant")
async def select_variant(
    request: Request, message_id: int, body: VariantBody, account: CurrentAccount
) -> dict[str, Any]:
    _, story = _message_story(request, account_id_of(account), message_id)
    selected = message_out(_chat(request).select_variant(message_id, body.variant_index))
    track(request, "variant_switched", {"mode": story.mode}, story_id=story.id)
    return selected


@router.patch("/messages/{message_id}")
async def edit_message(
    request: Request, message_id: int, body: ContentBody, account: CurrentAccount
) -> dict[str, Any]:
    msg, story = _message_story(request, account_id_of(account), message_id)
    # Nội dung rỗng: ChatService raise EmptyContent → 422 (cùng mã với khi gửi tin nhắn rỗng).
    edited = message_out(_chat(request).edit_message(message_id, body.content))
    track(request, "message_edited", {"role": msg.role, "mode": story.mode}, story_id=story.id)
    return edited


@router.delete("/messages/{message_id}")
async def delete_from(request: Request, message_id: int, account: CurrentAccount) -> dict[str, Any]:
    _, story = _message_story(request, account_id_of(account), message_id)
    deleted, remaining = _chat(request).delete_from(message_id)
    if deleted:
        track(
            request, "message_deleted", {"count_bucket": buckets.small_count_bucket(deleted), "mode": story.mode},
            story_id=story.id,
        )
    return {"deleted": deleted, "messages": [message_out(m) for m in remaining]}


@router.put("/messages/{message_id}/feedback")
async def set_feedback(
    request: Request, message_id: int, body: FeedbackBody, account: CurrentAccount
) -> dict[str, Any]:
    _, story = _message_story(request, account_id_of(account), message_id)
    rated = message_out(_chat(request).set_feedback(message_id, body.rating, body.note))
    track(request, "reply_rated", {"rating": body.rating or "cleared", "mode": story.mode}, story_id=story.id)
    return rated


@router.get("/messages/{message_id}/snapshot")
async def get_snapshot(request: Request, message_id: int, account: CurrentAccount) -> dict[str, Any]:
    repo = _repo(request)
    account_id = account_id_of(account)
    msg = repo.get_message(message_id, account_id=account_id)
    story = repo.get_story(msg.story_id, account_id=account_id)
    if repo.card_origin(story.card_id).story_copy:
        # Phase 4b (§4.1): snapshot chứa bí mật và sổ thế giới của nhân vật người khác.
        raise HTTPException(status_code=403, detail=COPY_SNAPSHOT_DETAIL)
    if msg.prompt_snapshot is None:
        raise HTTPException(status_code=404, detail="Tin nhắn này không có prompt snapshot (chỉ lượt do model sinh mới có).")
    return msg.prompt_snapshot


__all__ = ["router", "StoryDefaults", "StoryOut", "StoryDetail"]
