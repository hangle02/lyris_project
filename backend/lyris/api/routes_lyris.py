"""Endpoint cho giao diện Lyris (Phase 2b, docs/design-impl.md §7): cài đặt chung, trạng thái máy,
trạng thái wiki, nhân vật mẫu (dữ liệu phụ của story nằm ở routes_state.py).

Các hàm tiện ích ở đây (model mặc định, persona mặc định, kiểm tra tên model, xem trước tin nhắn) cũng
được routes.py dùng cho story.
"""
from __future__ import annotations

import asyncio
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from lyris.api.deps import CurrentAccount, account_id_of, current_account, is_owner, owner_auth
from lyris.api.routes_studio import CardOut, card_out, effective_chat_model, validate_card
from lyris.auth import errors
from lyris.auth.errors import AuthError
from lyris.config import REPO_ROOT, Settings
from lyris.db.repo import Repo
from lyris.llm.base import LLMClient, LLMError
from lyris.models import AppSettings, LoreStatus, SystemInfo, TemplateInfo
from lyris.seed.templates import Template, TemplateImage, get_template, image_media_type, load_templates
from lyris.state.service import StateService
from lyris.studio import avatars
from lyris.system import SystemMonitor

# Phase 4b: mặc định là cấm — mọi route ở đây cần đăng nhập (docs/auth.md §2.5).
router = APIRouter(prefix="/api", dependencies=[Depends(current_account)])

PREVIEW_CHARS = 140
MAX_MODEL_NAME_CHARS = 200
# Phase 2b: thư mục wiki dự kiến (plan.md). Phase 4 không dùng nữa (sổ thế giới nằm trong DB theo card).
LORE_DIR_NAME = "world_wiki"
DEFAULT_LORE_DIR: Path = REPO_ROOT / LORE_DIR_NAME


# ---------------------------------------------------------------------------- tiện ích dùng chung


def _repo(request: Request) -> Repo:
    repo: Repo = request.app.state.repo
    return repo


def _settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def default_persona_id(repo: Repo, account_id: int) -> int | None:
    """Persona cho story mới khi không chọn: `default_persona_id`, không có thì persona tạo sớm nhất.

    Chỉ xét persona của `account_id` (persona mặc định của account khác bị bỏ qua).
    """
    chosen = repo.get_app_settings(account_id=account_id).default_persona_id
    if chosen is not None and repo.persona_exists(chosen, account_id=account_id):
        return chosen
    return repo.first_persona_id(account_id=account_id)


def model_present(name: str, models: list[str]) -> bool:
    """`name` có trong danh sách model của Ollama (tên không kèm tag khớp với `:latest`)."""
    if name in models:
        return True
    return ":" not in name and f"{name}:latest" in models


async def ollama_model_names(llm: LLMClient) -> list[str] | None:
    """Danh sách model Ollama; None khi client không dò được (LLM giả) hoặc Ollama không kết nối được."""
    list_models = getattr(llm, "list_models", None)
    if list_models is None:
        return None
    try:
        return list(await list_models())
    except LLMError:
        return None
    except Exception:  # client lạ lỗi kiểu khác: coi như không dò được, không chặn người dùng
        return None


async def check_model_name(request: Request, raw: str) -> str:
    """Chuẩn hoá tên model; 422 nếu rỗng, hoặc nếu Ollama kết nối được mà không có model đó."""
    name = raw.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Tên model không được để trống.")
    llm: LLMClient = request.app.state.llm
    models = await ollama_model_names(llm)
    if models is not None and not model_present(name, models):
        listed = ", ".join(models[:8]) or "(chưa có model nào)"
        raise HTTPException(
            status_code=422,
            detail=f"Ollama chưa có model {name}. Các model hiện có: {listed}. Muốn dùng thì chạy: ollama pull {name}",
        )
    return name


_THOUGHT_BLOCK = re.compile(r"\[[ \t]*thought[ \t]*:[^\]]*(?:\]|\Z)", re.I)
_DIRECTIVE = re.compile(r"\(\([^)]*(?:\)\)|\Z)", re.S)


def make_preview(text: str | None, limit: int = PREVIEW_CHARS) -> str | None:
    """Một dòng xem trước: bỏ Thought và chỉ đạo ((...)), gộp khoảng trắng, tối đa `limit` ký tự
    (cắt ở ranh giới từ, thêm "…"). Rỗng -> None."""
    if not text:
        return None
    cleaned = _DIRECTIVE.sub(" ", _THOUGHT_BLOCK.sub(" ", text))
    cleaned = " ".join(cleaned.split())
    if not cleaned:
        return None
    if len(cleaned) <= limit:
        return cleaned
    cut = cleaned[: limit - 1]
    space = cut.rfind(" ")
    if space >= limit // 2:
        cut = cut[:space]
    return cut.rstrip(" ,;:.-–—") + "…"


# ---------------------------------------------------------------------------- cài đặt chung


class SettingsBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    default_persona_id: int | None = None
    default_chat_model: str | None = Field(default=None, max_length=MAX_MODEL_NAME_CHARS)


@router.get("/settings", response_model=AppSettings)
async def get_settings(request: Request, account: CurrentAccount) -> AppSettings:
    """`default_persona_id` của tài khoản (Phase 4b); `default_chat_model` của máy. Persona mặc định không
    thuộc account hiện tại thì trả None."""
    repo = _repo(request)
    saved = repo.get_app_settings(account_id=account_id_of(account))
    chosen = saved.default_persona_id
    if chosen is not None and not repo.persona_exists(chosen, account_id=account_id_of(account)):
        saved = saved.model_copy(update={"default_persona_id": None})
    return saved


@router.put("/settings", response_model=AppSettings)
async def put_settings(request: Request, body: SettingsBody, account: CurrentAccount) -> AppSettings:
    """Ghi cài đặt. Trường không gửi thì giữ nguyên; gửi `null` để bỏ.

    Phase 4b: persona mặc định ghi vào tài khoản; đổi `default_chat_model` (của máy) chỉ chủ máy làm được.
    Thành viên gửi lại ĐÚNG giá trị đang lưu (client gửi cả hai trường mỗi lần lưu) thì bỏ qua, không 403.
    """
    repo = _repo(request)
    account_id = account_id_of(account)
    current = repo.get_app_settings(account_id=account_id)
    fields = body.model_dump(exclude_unset=True)
    if "default_chat_model" in fields and not is_owner(account):
        sent = (fields["default_chat_model"] or "").strip() or None
        if sent != current.default_chat_model:
            raise AuthError(403, errors.OWNER_ONLY, "owner_only")
        del fields["default_chat_model"]
    persona_id = fields.get("default_persona_id", current.default_persona_id)
    if persona_id is not None and not repo.persona_exists(persona_id, account_id=account_id_of(account)):
        raise HTTPException(status_code=422, detail=f"Không có persona {persona_id}; hãy chọn persona khác.")
    model = fields.get("default_chat_model", current.default_chat_model)
    if "default_chat_model" in fields:
        if model is not None and model.strip():
            # Chỉ kiểm tra với Ollama khi model thật sự đổi: model đã lưu mà Ollama không còn thì
            # vẫn phải đổi được persona mặc định (client gửi lại cả model cũ).
            if model.strip() != current.default_chat_model:
                model = await check_model_name(request, model)
            else:
                model = current.default_chat_model
        else:
            model = None
    saved = repo.set_app_settings(
        AppSettings(default_persona_id=persona_id, default_chat_model=model), account_id=account_id
    )
    if saved.default_persona_id is not None and not repo.persona_exists(saved.default_persona_id, account_id=account_id):
        saved = saved.model_copy(update={"default_persona_id": None})
    monitor: SystemMonitor | None = getattr(request.app.state, "system", None)
    if monitor is not None:
        monitor.invalidate()
    return saved


# ---------------------------------------------------------------------------- máy & Ollama


def system_monitor(request: Request) -> SystemMonitor:
    monitor: SystemMonitor | None = getattr(request.app.state, "system", None)
    if monitor is None:
        llm = request.app.state.llm
        monitor = SystemMonitor(
            base_url=getattr(llm, "base_url", None), transport=getattr(llm, "_transport", None)
        )
        request.app.state.system = monitor
    return monitor


@router.get("/system", response_model=SystemInfo, dependencies=[Depends(owner_auth)])
async def get_system(request: Request) -> SystemInfo:
    """Thông tin máy (RAM, Ollama, model): chỉ chủ máy (docs/auth.md §1.1)."""
    settings = _settings(request)
    default_model = effective_chat_model(_repo(request), settings)
    try:
        info = await system_monitor(request).get(default_model)
    except Exception:  # không bao giờ 500: modal vẫn mở được, chỉ thiếu số liệu
        info = SystemInfo(ollama_reachable=False, chat_model_default=default_model)
    # Phase 3: tìm ký ức theo nghĩa khi Ollama có embed model (danh sách model cache 60 giây).
    state: StateService | None = getattr(request.app.state, "state", None)
    search = await state.memory_search() if state is not None else "keyword"
    return info.model_copy(update={"memory_search": search, "embed_model": settings.embed_model or None})


# Dữ liệu phụ của story (GET /api/stories/{id}/extras): routes_state.py (Phase 3).


# ---------------------------------------------------------------------------- wiki / lorebook


def lore_status(entries: int) -> LoreStatus:
    """Phase 4: sổ thế giới nằm trong DB theo từng card (không còn thư mục world_wiki đồng bộ). Giữ kiểu cũ
    để client cũ không vỡ: `enabled` true, `entries` = số mục của account, `files` 0, `dir` rỗng."""
    return LoreStatus(enabled=True, dir="", files=0, entries=max(0, entries), last_sync=None)


@router.get("/lore/status", response_model=LoreStatus)
async def get_lore_status(request: Request, account: CurrentAccount) -> LoreStatus:
    return lore_status(_repo(request).count_lore_for_account(account_id_of(account)))


# ---------------------------------------------------------------------------- nhân vật mẫu


class ImageCredit(BaseModel):
    title: str
    creator: str
    licence: str
    licence_url: str | None = None
    source_url: str
    changes: str | None = None


class TemplateOut(TemplateInfo):
    """TemplateInfo (hợp đồng) + ảnh bối cảnh: `image_url` (GET /api/templates/{slug}/image) và nguồn ảnh."""

    image_url: str | None = None
    image_credit: ImageCredit | None = None


def installed_template_ids(repo: Repo, templates: list[Template], account_id: int) -> dict[str, int]:
    """slug -> card đã cài của account (chỉ xét card của account đó).

    Đây là luật DUY NHẤT để biết card nào là nhân vật mẫu (frontend `isInstalledTemplate` cũng theo
    `installed_card_id` này): dấu `extensions.lyris.template`, hoặc card seed cũ trùng tên (adopt_existing).
    """
    tagged = repo.template_card_ids(account_id=account_id)
    out: dict[str, int] = {}
    for t in templates:
        if t.slug in tagged:
            out[t.slug] = tagged[t.slug]
        elif t.adopt_existing:
            same = repo.card_ids_by_name(t.card.name, t.card.style_profile, account_id=account_id)
            if same:
                out[t.slug] = same[0]
    return out


def template_out(t: Template, installed_card_id: int | None) -> TemplateOut:
    has_image = t.image is not None and t.image_path is not None
    return TemplateOut(
        slug=t.slug,
        featured=t.featured,
        vibes=list(t.vibes),
        card=t.card,
        installed_card_id=installed_card_id,
        image_url=f"/api/templates/{t.slug}/image" if has_image else None,
        image_credit=ImageCredit(**t.image.model_dump(exclude={"file"})) if has_image and t.image else None,
    )


@router.get("/templates", response_model=list[TemplateOut])
async def list_templates(request: Request, account: CurrentAccount) -> list[TemplateOut]:
    templates = load_templates()
    installed = installed_template_ids(_repo(request), templates, account_id_of(account))
    return [template_out(t, installed.get(t.slug)) for t in templates]


def _template_or_404(slug: str) -> Template:
    template = get_template(slug)
    if template is None:
        raise HTTPException(status_code=404, detail=f"Không có nhân vật mẫu {slug}.")
    return template


def _install_lock(request: Request) -> asyncio.Lock:
    lock: asyncio.Lock | None = getattr(request.app.state, "template_lock", None)
    if lock is None:
        lock = asyncio.Lock()
        request.app.state.template_lock = lock
    return lock


def image_credit_line(image: TemplateImage) -> str:
    """Một dòng ghi công ảnh (tác giả, giấy phép, nguồn, phần đã sửa) theo yêu cầu của CC BY / BY-SA."""
    licence = f"{image.licence} ({image.licence_url})" if image.licence_url else image.licence
    line = f"Ảnh: \u201c{image.title}\u201d của {image.creator}, giấy phép {licence}; nguồn: {image.source_url}."
    if image.changes:
        line += f" {image.changes.strip()}"
    return line


@router.post("/templates/{slug}/install", response_model=CardOut)
async def install_template(request: Request, slug: str, account: CurrentAccount) -> CardOut:
    """Cài nhân vật mẫu thành card của account hiện tại; đã cài thì trả card cũ (không tạo bản sao).

    Ảnh bối cảnh của template (nếu có) thành ảnh đại diện của card.
    """
    template = _template_or_404(slug)
    repo = _repo(request)
    account_id = account_id_of(account)
    async with _install_lock(request):
        existing = installed_template_ids(repo, [template], account_id).get(slug)
        if existing is not None:
            return card_out(repo, repo.get_card(existing, account_id=account_id), account)
        base = validate_card(template.card)
        notes = base.creator_notes
        if template.image is not None and template.image_path is not None:
            # Ảnh thành avatar và đi theo card khi xuất JSON/PNG: ghi công ngay trong creator_notes.
            notes = f"{notes}\n\n{image_credit_line(template.image)}".strip()
        card = base.model_copy(
            update={"id": None, "uid": None, "avatar": None, "visibility": "private", "creator_notes": notes}
        )
        created = repo.create_card(card, account_id=account_id)
        assert created.id is not None
        path = template.image_path
        if path is not None:
            avatars_dir = _settings(request).avatars_dir
            try:
                name: str | None = avatars.save_card_avatar(avatars_dir, created.id, path.read_bytes())
            except (avatars.AvatarError, OSError):
                name = None  # card vẫn cài được, chỉ thiếu ảnh
            if name:
                created = repo.set_card_avatar(created.id, name, account_id=account_id)
    return card_out(repo, created, account)


@router.get("/templates/{slug}/image")
async def template_image(slug: str) -> FileResponse:
    template = _template_or_404(slug)
    path = template.image_path
    if path is None:
        raise HTTPException(status_code=404, detail="Nhân vật mẫu này không có ảnh.")
    return FileResponse(path, media_type=image_media_type(path), headers={"Cache-Control": "public, max-age=86400"})


__all__ = [
    "TemplateOut",
    "check_model_name",
    "default_persona_id",
    "effective_chat_model",
    "installed_template_ids",
    "lore_status",
    "make_preview",
    "model_present",
    "ollama_model_names",
    "router",
]
