"""Dependency dùng chung cho mọi route: tài khoản đang dùng app.

Đây là chỗ DUY NHẤT quyết định "ai đang dùng app" (docs/accounts.md §2, docs/auth.md §2.5). Từ Phase 4b
tài khoản đọc từ cookie phiên (`lyris.auth.service.require_account`):

- chủ máy chưa có mật khẩu                       -> 409 `setup_required`
- không có cookie / phiên không có hoặc hết hạn  -> 401 `auth_required` (xoá cookie)
- tài khoản bị tạm khoá                          -> xoá mọi phiên, 401 `auth_required`
- đang dùng mật khẩu tạm (trừ `PendingAccount`)  -> 403 `password_change_required`
- phiên cũ hơn 1 giờ                             -> gia hạn trượt, gửi lại cookie

`OwnerAccount`: thêm 403 `owner_only` nếu không phải chủ máy. `PendingAccount`: cho phép tài khoản đang
chờ đổi mật khẩu (chỉ dùng ở `auth/me`, `auth/change-password`, `auth/logout`).

Mọi router gắn `Depends(current_account)` ở cấp router (mặc định là cấm); chỉ router `/api/auth` có route mở,
và `POST /api/events` (docs/tracking-plan.md) đọc phiên nếu có: chưa đăng nhập chỉ nhận vài sự kiện ẩn danh.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, Request

from lyris.auth import errors, service
from lyris.auth.errors import AuthError
from lyris.auth.store import AuthRow
from lyris.db.repo import Repo
from lyris.models import Account

if TYPE_CHECKING:
    from lyris.jobs.queue import JobQueue
    from lyris.state.service import StateService


def current_account(request: Request) -> Account:
    """Tài khoản đang đăng nhập (active, không chờ đổi mật khẩu); không thì AuthError (401/403/409)."""
    row = service.require_account(request, allow_pending=False)
    repo: Repo = request.app.state.repo
    return repo.get_account(row.id)


def current_auth(request: Request) -> AuthRow:
    """Như `current_account` nhưng trả dòng của phần đăng nhập (vai trò, trạng thái)."""
    return service.require_account(request, allow_pending=False)


def pending_auth(request: Request) -> AuthRow:
    """Cho phép tài khoản đang chờ đổi mật khẩu (`me`, `change-password`, `logout`)."""
    return service.require_account(request, allow_pending=True)


def owner_auth(request: Request) -> AuthRow:
    """Chỉ chủ máy; thành viên -> 403 `owner_only`."""
    row = service.require_account(request, allow_pending=False)
    if row.role != "owner":
        raise AuthError(403, errors.OWNER_ONLY, "owner_only")
    return row


def is_owner(account: Account) -> bool:
    return account.role == "owner"


def account_id_of(account: Account) -> int:
    assert account.id is not None
    return account.id


CurrentAccount = Annotated[Account, Depends(current_account)]
CurrentAuth = Annotated[AuthRow, Depends(current_auth)]
PendingAccount = Annotated[AuthRow, Depends(pending_auth)]
OwnerAccount = Annotated[AuthRow, Depends(owner_auth)]


def state_service(request: Request) -> StateService:
    """StateService của app (Phase 3), tạo trong lifespan."""
    state: StateService = request.app.state.state
    return state


def job_queue(request: Request) -> JobQueue:
    """Hàng đợi job nền của app (Phase 3), tạo trong lifespan."""
    jobs: JobQueue = request.app.state.jobs
    return jobs


__all__ = [
    "CurrentAccount",
    "CurrentAuth",
    "OwnerAccount",
    "PendingAccount",
    "account_id_of",
    "current_account",
    "current_auth",
    "is_owner",
    "job_queue",
    "owner_auth",
    "pending_auth",
    "state_service",
]
