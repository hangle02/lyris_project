"""Endpoint tài khoản (Phase 2c, docs/accounts.md §4): account hiện tại, avatar, ảnh bìa, profile công khai.

Account hiện tại luôn lấy qua `current_account` (lyris/api/deps.py). Upload ảnh dùng raw body như avatar
card. Lỗi trả `{"detail": "..."}` tiếng Việt.
"""
from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from lyris.accounts import AccountInputError, normalize_handle, validate_account_update
from lyris.analytics import store as analytics_store
from lyris.analytics.tracker import allow_device, device_anon, forget_device, tracker_of
from lyris.api.deps import CurrentAccount, account_id_of, current_account, is_owner
from lyris.api.routes_lyris import installed_template_ids
from lyris.api.routes_studio import CardSummary, card_summary, image_file_response, read_body
from lyris.compliance import legal
from lyris.config import Settings
from lyris.db.repo import AccountImage, HandleTaken, NotFound, Repo
from lyris.models import Account
from lyris.seed.templates import load_templates
from lyris.studio import avatars

# Phase 4b: mặc định là cấm — mọi route ở đây cần đăng nhập (docs/auth.md §2.5).
router = APIRouter(prefix="/api", dependencies=[Depends(current_account)])

# Giới hạn thô cho body; luật thật (độ dài handle, tên, giới thiệu) nằm ở lyris/accounts.py.
_MAX_FIELD_CHARS = 10_000

_IMAGE_LABEL: dict[AccountImage, str] = {"avatar": "ảnh đại diện", "banner": "ảnh bìa"}


# ---------------------------------------------------------------------------- body / response


class AccountOut(Account):
    avatar_url: str | None = None
    banner_url: str | None = None
    card_count: int
    story_count: int
    persona_count: int
    # Event tracking (docs/tracking-plan.md): true = đã tắt "Chia sẻ dữ liệu sử dụng ẩn danh để cải thiện Lyris".
    analytics_opt_out: bool = False
    # docs/compliance.md §3: lần đồng ý Điều khoản / Chính sách quyền riêng tư.
    terms_required: bool = False
    terms_accepted_at: str | None = None
    privacy_version: str | None = None
    legal_version: str = legal.LEGAL_VERSION


class AccountPatch(BaseModel):
    """Body của PATCH /api/account: cài đặt riêng của tài khoản (hiện chỉ có chia sẻ dữ liệu sử dụng)."""

    model_config = ConfigDict(extra="forbid")
    analytics_opt_out: bool | None = None


class AccountBody(BaseModel):
    """Body của PUT /api/account (hợp đồng: AccountUpdate). Bỏ qua trường lạ để client gửi lại cả AccountOut."""

    model_config = ConfigDict(extra="ignore")
    display_name: str = Field(max_length=_MAX_FIELD_CHARS)
    handle: str = Field(max_length=_MAX_FIELD_CHARS)
    bio: str = Field(default="", max_length=_MAX_FIELD_CHARS)


class PublicProfile(BaseModel):
    handle: str
    display_name: str
    bio: str
    avatar_url: str | None = None
    banner_url: str | None = None
    created_at: str | None = None
    cards: list[CardSummary]


# ---------------------------------------------------------------------------- tiện ích


def _repo(request: Request) -> Repo:
    repo: Repo = request.app.state.repo
    return repo


def _avatars_dir(request: Request) -> Path:
    settings: Settings = request.app.state.settings
    return settings.avatars_dir


def _image_url(base: str, name: str | None) -> str | None:
    """URL ảnh; `v` là tên file (đổi mỗi lần upload) để trình duyệt không dùng cache cũ."""
    return f"{base}?v={quote(name, safe='')}" if name else None


def own_card_count(repo: Repo, account_id: int, total: int) -> int:
    """Số nhân vật account tự tạo: tổng trừ nhân vật mẫu đã cài (cùng luật với trang profile/Khám phá)."""
    try:
        templates = load_templates()
    except Exception:  # thư mục template hỏng: đếm hết, không làm hỏng trang tài khoản
        return total
    installed = set(installed_template_ids(repo, templates, account_id).values())
    return max(0, total - len(installed))


def account_out(repo: Repo, account: Account) -> AccountOut:
    """`card_count` không tính nhân vật mẫu đã cài (docs/phase3.md §7)."""
    account_id = account_id_of(account)
    counts = repo.account_counts(account_id)
    with repo.locked() as conn:
        opted_out = analytics_store.opted_out(conn, account_id)
        accepted_at, accepted_version = legal.accepted_version(conn, account_id)
        terms_required = legal.terms_required(conn, account_id)
    return AccountOut(
        **account.model_dump(),
        avatar_url=_image_url("/api/account/avatar", account.avatar),
        banner_url=_image_url("/api/account/banner", account.banner),
        card_count=own_card_count(repo, account_id, counts["card_count"]),
        story_count=counts["story_count"],
        persona_count=counts["persona_count"],
        analytics_opt_out=opted_out,
        terms_required=terms_required,
        terms_accepted_at=accepted_at,
        privacy_version=accepted_version,
    )


def _find_by_handle(repo: Repo, handle: str, viewer: Account, *, owner_sees_disabled: bool = False) -> Account:
    """Tài khoản theo @handle. Phase 4b (docs/auth.md §4.1, §4.6): tài khoản đang tạm khoá thì 404 với người
    khác (trừ chủ máy khi `owner_sees_disabled`: ảnh đại diện, ảnh bìa)."""
    found = repo.find_account_by_handle(normalize_handle(handle))
    missing = NotFound(f"Không tìm thấy tài khoản @{normalize_handle(handle)}.")
    if found is None:
        raise missing
    if found.status != "active" and found.id != viewer.id and not (owner_sees_disabled and is_owner(viewer)):
        raise missing
    return found


async def _upload_image(request: Request, account: Account, kind: AccountImage) -> AccountOut:
    repo = _repo(request)
    account_id = account_id_of(account)
    data = await read_body(request, what="Ảnh")
    avatars_dir = _avatars_dir(request)
    if kind == "avatar":
        name = avatars.save_account_avatar(avatars_dir, account_id, data)
    else:
        name = avatars.save_account_banner(avatars_dir, account_id, data)
    old = account.avatar if kind == "avatar" else account.banner
    try:
        updated = repo.set_account_image(account_id, kind, name)
    except Exception:
        avatars.remove_avatar(avatars_dir, name)
        raise
    if old and old != name:
        avatars.remove_avatar(avatars_dir, old)
    return account_out(repo, updated)


def _delete_image(request: Request, account: Account, kind: AccountImage) -> AccountOut:
    repo = _repo(request)
    old = account.avatar if kind == "avatar" else account.banner
    updated = repo.set_account_image(account_id_of(account), kind, None)
    avatars.remove_avatar(_avatars_dir(request), old)
    return account_out(repo, updated)


def _image_file(request: Request, account: Account, kind: AccountImage) -> FileResponse:
    name = account.avatar if kind == "avatar" else account.banner
    return image_file_response(_avatars_dir(request), name, f"Tài khoản này chưa có {_IMAGE_LABEL[kind]}.")


# ---------------------------------------------------------------------------- account hiện tại


@router.get("/account", response_model=AccountOut)
async def get_account(request: Request, account: CurrentAccount) -> AccountOut:
    return account_out(_repo(request), account)


@router.put("/account", response_model=AccountOut)
async def update_account(request: Request, body: AccountBody, account: CurrentAccount) -> AccountOut:
    """Lưu tên hiển thị, @handle, giới thiệu; lần lưu đầu đặt `profile_completed`. Sai luật/trùng -> 422."""
    repo = _repo(request)
    account_id = account_id_of(account)
    try:
        update = validate_account_update(body.display_name, body.handle, body.bio)
    except AccountInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    taken = HTTPException(status_code=422, detail=f"@{update.handle} đã có người dùng. Hãy chọn handle khác.")
    if repo.handle_taken(update.handle, exclude_account_id=account_id):
        raise taken
    try:
        saved = repo.update_account(account_id, update)
    except HandleTaken as exc:
        raise taken from exc
    return account_out(repo, saved)


@router.patch("/account", response_model=AccountOut)
async def patch_account(request: Request, body: AccountPatch, account: CurrentAccount) -> AccountOut:
    """Tắt/bật chia sẻ dữ liệu sử dụng. Tắt: xoá mọi sự kiện đã lưu của tài khoản, kể cả sự kiện lúc chưa đăng nhập
    trên các thiết bị của tài khoản (chưa gửi thì không bao giờ gửi), và ngừng ghi; thiết bị này đổi định danh và
    được đánh dấu không chia sẻ (không ghi gì cả khi đã đăng xuất). Chỉ còn một dòng `analytics_opt_out` không gắn
    tài khoản để đếm tỉ lệ tắt. Bật lại: gỡ dấu không chia sẻ của thiết bị này."""
    repo = _repo(request)
    account_id = account_id_of(account)
    if body.analytics_opt_out is not None:
        with repo.transaction():
            before = analytics_store.opted_out(repo.conn, account_id)
            analytics_store.set_opt_out(
                repo.conn, account_id, body.analytics_opt_out, device_anon=device_anon(request)
            )
        if body.analytics_opt_out:
            forget_device(request, opt_out=True)
        else:
            allow_device(request)
        tracker = tracker_of(request)
        if body.analytics_opt_out and not before and tracker is not None:
            tracker.record_opt_out()
    return account_out(repo, repo.get_account(account_id))


@router.put("/account/avatar", response_model=AccountOut)
async def upload_account_avatar(request: Request, account: CurrentAccount) -> AccountOut:
    """Ảnh raw -> `account-<id>-<hex>.png` tối đa 768x768, bỏ metadata."""
    return await _upload_image(request, account, "avatar")


@router.delete("/account/avatar", response_model=AccountOut)
async def delete_account_avatar(request: Request, account: CurrentAccount) -> AccountOut:
    return _delete_image(request, account, "avatar")


@router.get("/account/avatar")
async def get_account_avatar(request: Request, account: CurrentAccount) -> FileResponse:
    return _image_file(request, account, "avatar")


@router.put("/account/banner", response_model=AccountOut)
async def upload_account_banner(request: Request, account: CurrentAccount) -> AccountOut:
    """Ảnh raw -> `banner-<id>-<hex>.png` vừa khung 1500x500 (giữ tỉ lệ), bỏ metadata."""
    return await _upload_image(request, account, "banner")


@router.delete("/account/banner", response_model=AccountOut)
async def delete_account_banner(request: Request, account: CurrentAccount) -> AccountOut:
    return _delete_image(request, account, "banner")


@router.get("/account/banner")
async def get_account_banner(request: Request, account: CurrentAccount) -> FileResponse:
    return _image_file(request, account, "banner")


# ---------------------------------------------------------------------------- profile công khai


@router.get("/accounts/{handle}", response_model=PublicProfile)
async def get_profile(request: Request, handle: str, account: CurrentAccount) -> PublicProfile:
    """Những gì người khác sẽ thấy: tên, handle, ảnh, giới thiệu và các nhân vật công khai (không bản sao).

    Không có số story hay persona (riêng tư); `story_count` của từng nhân vật luôn 0. Tài khoản tạm khoá: 404
    với người khác.
    """
    repo = _repo(request)
    owner = _find_by_handle(repo, handle, account)
    base = f"/api/accounts/{quote(owner.handle, safe='')}"
    cards = repo.list_cards(account_id=account_id_of(owner), public_only=True)
    return PublicProfile(
        handle=owner.handle,
        display_name=owner.display_name,
        bio=owner.bio,
        avatar_url=_image_url(f"{base}/avatar", owner.avatar),
        banner_url=_image_url(f"{base}/banner", owner.banner),
        created_at=owner.created_at,
        cards=[card_summary(repo, c, owner, include_story_count=False) for c in cards],
    )


@router.get("/accounts/{handle}/avatar")
async def get_profile_avatar(request: Request, handle: str, account: CurrentAccount) -> FileResponse:
    owner = _find_by_handle(_repo(request), handle, account, owner_sees_disabled=True)
    return _image_file(request, owner, "avatar")


@router.get("/accounts/{handle}/banner")
async def get_profile_banner(request: Request, handle: str, account: CurrentAccount) -> FileResponse:
    owner = _find_by_handle(_repo(request), handle, account, owner_sees_disabled=True)
    return _image_file(request, owner, "banner")


__all__ = ["AccountBody", "AccountOut", "PublicProfile", "account_out", "router"]
