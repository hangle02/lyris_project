"""`/api/auth/*` (docs/auth.md §6.2). Route mở: `me`, `setup-owner`, `login`, `signup`; còn lại cần đăng nhập.

Không log body của các route này, kể cả khi lỗi (bộ xử lý 422 chỉ in tên trường và loại lỗi).
"""
from __future__ import annotations

from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field

from lyris.api.deps import CurrentAuth, PendingAccount
from lyris.auth import errors, service, store
from lyris.auth.store import AuthRow
from lyris.db.repo import Repo

router = APIRouter(prefix="/api/auth")

# Route không qua `current_account` (§6.1). Test xếp loại route đọc danh sách này.
OPEN_ROUTES: frozenset[tuple[str, str]] = frozenset(
    {
        ("GET", "/api/auth/me"),
        ("POST", "/api/auth/setup-owner"),
        ("POST", "/api/auth/login"),
        ("POST", "/api/auth/signup"),
    }
)

# Giới hạn thô cho body (luật thật: lyris.accounts, lyris.auth.passwords).
_RAW = 1024


class AuthAccount(BaseModel):
    id: int
    handle: str
    display_name: str
    avatar_url: str | None = None
    role: Literal["owner", "member"]
    must_change_password: bool
    profile_completed: bool


class AuthState(BaseModel):
    setup_required: bool
    # Chỉ true khi setup_required và chủ máy chưa đặt tên (DB mới tinh); không lộ handle.
    setup_needs_profile: bool = False
    account: AuthAccount | None = None


class LoginBody(BaseModel):
    handle: str = Field(max_length=_RAW)
    password: str = Field(max_length=_RAW)


class SetupBody(BaseModel):
    setup_code: str = Field(max_length=_RAW)
    password: str = Field(max_length=_RAW)
    display_name: str | None = Field(default=None, max_length=_RAW)
    handle: str | None = Field(default=None, max_length=_RAW)


class SignupBody(BaseModel):
    invite_code: str = Field(max_length=_RAW)
    handle: str = Field(max_length=_RAW)
    display_name: str = Field(max_length=_RAW)
    password: str = Field(max_length=_RAW)


class ChangePasswordBody(BaseModel):
    current_password: str = Field(max_length=_RAW)
    new_password: str = Field(max_length=_RAW)


def _repo(request: Request) -> Repo:
    repo: Repo = request.app.state.repo
    return repo


def auth_account(row: AuthRow) -> AuthAccount:
    avatar = f"/api/account/avatar?v={quote(row.avatar, safe='')}" if row.avatar else None
    return AuthAccount(
        id=row.id,
        handle=row.handle,
        display_name=row.display_name,
        avatar_url=avatar,
        role="owner" if row.role == "owner" else "member",
        must_change_password=row.must_change_password,
        profile_completed=row.profile_completed,
    )


def _signed_in(row: AuthRow) -> AuthState:
    return AuthState(setup_required=False, account=auth_account(row))


@router.get("/me", response_model=AuthState)
def me(request: Request) -> AuthState:
    """Luôn 200. Chưa thiết lập: `setup_required` (không có handle chủ máy); chưa đăng nhập: `account` null."""
    repo = _repo(request)
    with repo.locked() as conn:
        owner = store.owner(conn)
    if owner is None or owner.password is None:
        return AuthState(setup_required=True, setup_needs_profile=owner is None or not owner.profile_completed)
    resolved = service.resolve_session(request)
    if resolved.account is None:
        return AuthState(setup_required=False)
    return _signed_in(resolved.account)


@router.post("/setup-owner", response_model=AuthState)
async def setup_owner(request: Request, body: SetupBody) -> AuthState:
    row = await service.setup_owner(request, body.setup_code, body.password, body.display_name, body.handle)
    return _signed_in(row)


def setup_done(request: Request) -> None:
    """Chủ máy chưa có mật khẩu -> 409 `setup_required` trước cả khi xét body (§2.4)."""
    if service.setup_needed(_repo(request)):
        raise errors.setup_required()


@router.post("/login", response_model=AuthState, dependencies=[Depends(setup_done)])
async def login(request: Request, body: LoginBody) -> AuthState:
    return _signed_in(await service.login(request, body.handle, body.password))


@router.post("/signup", response_model=AuthState, dependencies=[Depends(setup_done)])
async def signup(request: Request, body: SignupBody) -> AuthState:
    row = await service.signup(request, body.invite_code, body.handle, body.display_name, body.password)
    return _signed_in(row)


@router.post("/logout", status_code=204)
def logout(request: Request, _account: PendingAccount) -> Response:
    service.logout(request)
    return Response(status_code=204)


@router.post("/logout-all", status_code=204)
def logout_all(request: Request, account: CurrentAuth) -> Response:
    service.logout_all(request, account)
    return Response(status_code=204)


@router.post("/change-password", response_model=AuthState)
async def change_password(request: Request, body: ChangePasswordBody, account: PendingAccount) -> AuthState:
    row = await service.change_password(request, account, body.current_password, body.new_password)
    return _signed_in(row)


__all__ = ["OPEN_ROUTES", "AuthAccount", "AuthState", "auth_account", "router"]
