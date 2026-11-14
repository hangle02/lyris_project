"""`/api/admin/*` (docs/auth.md §6.3): chỉ chủ máy. Mã mời, danh sách tài khoản, đặt lại mật khẩu, tạm khoá.

Không trả số story, số nhân vật riêng tư hay bất cứ gì bên trong tài khoản người khác.
"""
from __future__ import annotations

from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from lyris.analytics import track
from lyris.api.deps import OwnerAccount, owner_auth
from lyris.auth import clock, service, store
from lyris.db.repo import Repo

router = APIRouter(prefix="/api/admin", dependencies=[Depends(owner_auth)])

NOTE_MAX = 60


class AdminAccount(BaseModel):
    id: int
    handle: str
    display_name: str
    avatar_url: str | None = None
    role: Literal["owner", "member"]
    status: Literal["active", "disabled"]
    must_change_password: bool
    created_at: str
    last_login_at: str | None = None
    invited_by_handle: str | None = None
    session_count: int


class ResetPasswordOut(BaseModel):
    account: AdminAccount
    temporary_password: str


class InviteOut(BaseModel):
    id: int
    hint: str
    note: str
    created_at: str
    expires_at: str
    status: Literal["active", "used", "expired", "revoked"]
    used_by_handle: str | None = None


class InviteCreated(BaseModel):
    invite: InviteOut
    code: str


class InviteBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    note: str = Field(default="", max_length=NOTE_MAX)
    expires_in_days: Literal[1, 7, 30] = store.DEFAULT_INVITE_DAYS  # type: ignore[assignment]


def _repo(request: Request) -> Repo:
    repo: Repo = request.app.state.repo
    return repo


def admin_account(row: store.AdminRow) -> AdminAccount:
    avatar = (
        f"/api/accounts/{quote(row.handle, safe='')}/avatar?v={quote(row.avatar, safe='')}" if row.avatar else None
    )
    return AdminAccount(
        id=row.id,
        handle=row.handle,
        display_name=row.display_name,
        avatar_url=avatar,
        role="owner" if row.role == "owner" else "member",
        status="disabled" if row.status == "disabled" else "active",
        must_change_password=row.must_change_password,
        created_at=row.created_at,
        last_login_at=row.last_login_at,
        invited_by_handle=row.invited_by_handle,
        session_count=row.session_count,
    )


def invite_out(row: store.InviteRow) -> InviteOut:
    return InviteOut(
        id=row.id,
        hint=row.hint,
        note=row.note,
        created_at=row.created_at,
        expires_at=row.expires_at,
        status=row.status(clock.now()),
        used_by_handle=row.used_by_handle,
    )


@router.get("/accounts", response_model=list[AdminAccount])
def list_accounts(request: Request) -> list[AdminAccount]:
    with _repo(request).locked() as conn:
        rows = store.admin_accounts(conn, clock.now())
    return [admin_account(r) for r in rows]


@router.post("/accounts/{account_id}/reset-password", response_model=ResetPasswordOut)
async def reset_password(request: Request, account_id: int, actor: OwnerAccount) -> ResetPasswordOut:
    row, temporary = await service.reset_password(request, actor, account_id)
    return ResetPasswordOut(account=admin_account(row), temporary_password=temporary)


@router.post("/accounts/{account_id}/disable", response_model=AdminAccount)
def disable_account(request: Request, account_id: int, actor: OwnerAccount) -> AdminAccount:
    return admin_account(service.set_disabled(request, actor, account_id, True))


@router.post("/accounts/{account_id}/enable", response_model=AdminAccount)
def enable_account(request: Request, account_id: int, actor: OwnerAccount) -> AdminAccount:
    return admin_account(service.set_disabled(request, actor, account_id, False))


@router.get("/invites", response_model=list[InviteOut])
def list_invites(request: Request) -> list[InviteOut]:
    with _repo(request).locked() as conn:
        rows = store.list_invites(conn)
    return [invite_out(r) for r in rows]


@router.post("/invites", response_model=InviteCreated)
def create_invite(request: Request, actor: OwnerAccount, body: InviteBody | None = None) -> InviteCreated:
    body = body or InviteBody()
    note = " ".join(body.note.split())
    invite, code = service.create_invite(request, actor, note, int(body.expires_in_days))
    track(request, "invite_created", {"expires_days": int(body.expires_in_days)})
    return InviteCreated(invite=invite_out(invite), code=code)


@router.delete("/invites/{invite_id}", status_code=204)
def revoke_invite(request: Request, invite_id: int, actor: OwnerAccount) -> Response:
    service.revoke_invite(request, actor, invite_id)
    return Response(status_code=204)


__all__ = ["AdminAccount", "InviteOut", "router"]
