"""`/api/auth/*` (docs/auth.md §6.2). Route mở: `me`, `setup-owner`, `login`, `signup`; còn lại cần đăng nhập.

Không log body của các route này, kể cả khi lỗi (bộ xử lý 422 chỉ in tên trường và loại lỗi).
"""
from __future__ import annotations

from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field

from lyris.analytics import buckets
from lyris.analytics import track
from lyris.analytics.tracker import honour_opt_out_on_login
from lyris.api.deps import CurrentAuth, PendingAccount
from lyris.auth import clock, codes, errors, service, store
from lyris.auth.store import AuthRow
from lyris.compliance import legal
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
    # docs/compliance.md §3: chưa đồng ý bản Điều khoản / Chính sách quyền riêng tư hiện tại -> giao diện hỏi một lần
    # (`POST /api/account/terms`).
    terms_required: bool = False


class AuthState(BaseModel):
    setup_required: bool
    # Chỉ true khi setup_required và chủ máy chưa đặt tên (DB mới tinh); không lộ handle.
    setup_needs_profile: bool = False
    account: AuthAccount | None = None
    # Phiên bản bộ văn bản pháp lý hiện tại (`GET /api/legal/{doc}`); trang tạo tài khoản gửi lại khi đồng ý.
    legal_version: str = legal.LEGAL_VERSION
    # Liên hệ của người vận hành (LYRIS_CONTACT), cho "Xin mã mời" / "Quên mật khẩu" ở trang đăng nhập; None nếu chưa đặt.
    contact: str | None = None


class LoginBody(BaseModel):
    handle: str = Field(max_length=_RAW)
    password: str = Field(max_length=_RAW)


class SetupBody(BaseModel):
    setup_code: str = Field(max_length=_RAW)
    password: str = Field(max_length=_RAW)
    display_name: str | None = Field(default=None, max_length=_RAW)
    handle: str | None = Field(default=None, max_length=_RAW)
    # docs/compliance.md §3: bắt buộc true (đã đọc và đồng ý Điều khoản + Chính sách quyền riêng tư).
    accept_terms: bool = False
    terms_version: str | None = Field(default=None, max_length=32)


class SignupBody(BaseModel):
    invite_code: str = Field(max_length=_RAW)
    handle: str = Field(max_length=_RAW)
    display_name: str = Field(max_length=_RAW)
    password: str = Field(max_length=_RAW)
    accept_terms: bool = False
    terms_version: str | None = Field(default=None, max_length=32)


class ChangePasswordBody(BaseModel):
    current_password: str = Field(max_length=_RAW)
    new_password: str = Field(max_length=_RAW)


def _repo(request: Request) -> Repo:
    repo: Repo = request.app.state.repo
    return repo


def auth_account(row: AuthRow, *, terms_required: bool = False) -> AuthAccount:
    avatar = f"/api/account/avatar?v={quote(row.avatar, safe='')}" if row.avatar else None
    return AuthAccount(
        id=row.id,
        handle=row.handle,
        display_name=row.display_name,
        avatar_url=avatar,
        role="owner" if row.role == "owner" else "member",
        must_change_password=row.must_change_password,
        profile_completed=row.profile_completed,
        terms_required=terms_required,
    )


def _contact(request: Request) -> str | None:
    settings = getattr(request.app.state, "settings", None)
    return getattr(settings, "contact", None)


def _signed_in(request: Request, row: AuthRow) -> AuthState:
    with _repo(request).locked() as conn:
        required = legal.terms_required(conn, row.id)
    return AuthState(setup_required=False, account=auth_account(row, terms_required=required), contact=_contact(request))


def _require_terms(accept_terms: bool, version: str | None) -> None:
    """Tạo tài khoản / thiết lập chủ máy cần đồng ý Điều khoản (400 `terms_required`), đúng bản hiện tại (409)."""
    if accept_terms is not True:
        raise errors.AuthError(400, legal.TERMS_REQUIRED, "terms_required")
    if version is not None and version != legal.LEGAL_VERSION:
        raise errors.AuthError(409, legal.TERMS_OUTDATED, "terms_outdated")


@router.get("/me", response_model=AuthState)
def me(request: Request) -> AuthState:
    """Luôn 200. Chưa thiết lập: `setup_required` (không có handle chủ máy); chưa đăng nhập: `account` null."""
    repo = _repo(request)
    with repo.locked() as conn:
        owner = store.owner(conn)
    if owner is None or owner.password is None:
        return AuthState(
            setup_required=True, setup_needs_profile=owner is None or not owner.profile_completed,
            contact=_contact(request),
        )
    resolved = service.resolve_session(request)
    if resolved.account is None:
        return AuthState(setup_required=False, contact=_contact(request))
    return _signed_in(request, resolved.account)


@router.post("/setup-owner", response_model=AuthState)
async def setup_owner(request: Request, body: SetupBody) -> AuthState:
    _require_terms(body.accept_terms, body.terms_version)
    row = await service.setup_owner(
        request, body.setup_code, body.password, body.display_name, body.handle, terms_version=legal.LEGAL_VERSION
    )
    track(request, "owner_setup_completed", account_id=row.id)
    return _signed_in(request, row)


def setup_done(request: Request) -> None:
    """Chủ máy chưa có mật khẩu -> 409 `setup_required` trước cả khi xét body (§2.4)."""
    if service.setup_needed(_repo(request)):
        raise errors.setup_required()


# Mã lỗi đăng nhập -> lý do trong số liệu (không ghi handle hay chữ đã gõ).
_LOGIN_FAIL: dict[str | None, str] = {
    None: "bad_credentials",
    "rate_limited": "rate_limited",
    "account_disabled": "account_disabled",
    "temporary_password_expired": "temporary_expired",
    "setup_required": "setup_required",
    "busy": "busy",
}


@router.post("/login", response_model=AuthState, dependencies=[Depends(setup_done)])
async def login(request: Request, body: LoginBody) -> AuthState:
    try:
        row = await service.login(request, body.handle, body.password)
    except errors.AuthError as exc:
        track(request, "login_failed", {"reason": _LOGIN_FAIL.get(exc.code, "other")}, account_id=None)
        raise
    track(request, "login_succeeded", account_id=row.id)
    honour_opt_out_on_login(request, row.id, _repo(request))
    return _signed_in(request, row)


def _invite_age(request: Request, invite_code: str) -> str | None:
    """Tuổi của mã mời vừa dùng (đã chia khoảng), đọc trước khi tạo tài khoản. Không ghi mã."""
    try:
        normalized = codes.normalize_code(invite_code)
        if not normalized:
            return None
        with _repo(request).locked() as conn:
            invite = store.find_invite(conn, codes.code_hash(normalized))
        if invite is None:
            return None
        return buckets.age_bucket((clock.now() - clock.parse(invite.created_at)).total_seconds())
    except Exception:
        return None


@router.post("/signup", response_model=AuthState, dependencies=[Depends(setup_done)])
async def signup(request: Request, body: SignupBody) -> AuthState:
    _require_terms(body.accept_terms, body.terms_version)
    age = _invite_age(request, body.invite_code)
    row = await service.signup(
        request, body.invite_code, body.handle, body.display_name, body.password, terms_version=legal.LEGAL_VERSION
    )
    track(request, "signup_completed", account_id=row.id)
    if age is not None:
        track(request, "invite_redeemed", {"invite_age": age}, account_id=row.id)
    return _signed_in(request, row)


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
    return _signed_in(request, row)


__all__ = ["OPEN_ROUTES", "AuthAccount", "AuthState", "auth_account", "router"]
