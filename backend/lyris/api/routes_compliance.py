"""Tuân thủ khi ra mắt (docs/compliance.md).

- `POST /api/messages/{id}/report`: người chơi báo cáo một câu trả lời của AI trong story CỦA MÌNH. Bản chụp câu
  trả lời chỉ được gửi cho chủ máy khi `share_text = true`.
- `POST /api/cards/{id}/report`: người chơi báo cáo một nhân vật công khai của người khác (hồ sơ: tên, mô tả, lời
  chào, ảnh). Mở từ bản sao trong story của mình thì báo cáo nhân vật gốc.
- `GET /api/admin/reports`, `PATCH /api/admin/reports/{id}`: chủ máy rà soát (không thấy ai báo cáo, không đọc
  được story; chỉ thấy lý do, ghi chú, bản chụp đã được đồng ý gửi và nhân vật công khai liên quan).
- `POST /api/admin/cards/{id}/unpublish`: chủ máy ẩn một nhân vật công khai (về Riêng tư; người tạo vẫn giữ).
- `DELETE /api/account`: xoá tài khoản của chính mình và mọi dữ liệu (cần mật khẩu hiện tại).
- `GET /api/account/export`: tải toàn bộ dữ liệu của chính mình (JSON).
- `POST /api/account/terms`: đồng ý bản Điều khoản / Chính sách quyền riêng tư hiện tại.
- `GET /api/legal/{terms|privacy}`: văn bản pháp lý (mở, không cần đăng nhập).
"""
from __future__ import annotations

import logging
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from lyris.analytics import store as analytics_store
from lyris.analytics import track, track_detached
from lyris.analytics.tracker import device_anon, forget_device
from lyris.api.deps import CurrentAccount, CurrentAuth, account_id_of, current_account, owner_auth
from lyris.auth import clock, errors, passwords, ratelimit, service
from lyris.auth import store as auth_store
from lyris.auth.errors import AuthError
from lyris.auth.net import client_ip
from lyris.chat.service import Busy
from lyris.compliance import account_data, legal, reports
from lyris.config import Settings
from lyris.db.repo import NotFound, Repo
from lyris.studio import avatars

logger = logging.getLogger("lyris.auth")

router = APIRouter(prefix="/api", dependencies=[Depends(current_account)])
admin_router = APIRouter(prefix="/api/admin", dependencies=[Depends(owner_auth)])
# Không qua `current_account`: văn bản pháp lý phải đọc được trước khi đăng nhập và cả ở màn thiết lập chủ máy.
public_router = APIRouter(prefix="/api/legal")

# Route công khai hoàn toàn (không cần đăng nhập, không phụ thuộc chế độ thiết lập). Test xếp loại route đọc.
PUBLIC_ROUTES: frozenset[tuple[str, str]] = frozenset({("GET", "/api/legal/{doc}")})

OWNER_HAS_MEMBERS = (
    "Bạn là chủ máy và Lyris vẫn còn tài khoản thành viên. Chủ máy giữ mã mời và là người duy nhất đặt lại "
    "mật khẩu hay mở khoá cho thành viên, nên chưa xoá được tài khoản này khi còn người khác dùng. "
    "Các thành viên cần tự xoá tài khoản của họ trước."
)
BAD_PASSWORD = "Mật khẩu không đúng."
STORY_BUSY = "Một story của bạn đang sinh câu trả lời. Hãy đợi xong hoặc bấm Dừng rồi thử lại."
ONLY_REPLIES = "Chỉ báo cáo được câu trả lời của nhân vật."
OWN_CARD = "Đây là nhân vật của bạn."
NOT_PUBLIC = "Nhân vật này không còn công khai."
_RAW = 1024


# ---------------------------------------------------------------------------- body / response


class ReportBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: reports.ReportReason
    note: str = Field(default="", max_length=reports.NOTE_MAX)
    # "Gửi kèm câu trả lời này cho chủ máy xem xét": không bật thì chỉ lưu lý do (và ghi chú).
    share_text: bool = False


class CardReportBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: reports.ReportReason
    note: str = Field(default="", max_length=reports.NOTE_MAX)


class ReportOut(BaseModel):
    id: int
    reason: reports.ReportReason
    shared_text: bool
    status: reports.ReportStatus


class UnpublishedOut(BaseModel):
    unpublished: bool


class AdminReport(BaseModel):
    id: int
    # "message": một câu trả lời của AI; "character": hồ sơ một nhân vật công khai.
    target: reports.ReportTarget = "message"
    created_at: str
    updated_at: str
    reason: reports.ReportReason
    note: str
    mode: Literal["story", "dm"] | None = None
    language: Literal["vi", "en"] | None = None
    model_name: str | None = None
    shared_text: bool
    message_text: str | None = None
    status: reports.ReportStatus
    reviewed_at: str | None = None
    public_card_id: int | None = None
    public_card_name: str | None = None
    public_card_creator: str | None = None


class ReportStatusBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: reports.ReportStatus


class DeleteAccountBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    password: str = Field(max_length=_RAW)


class DeletedOut(BaseModel):
    deleted: bool
    # Chủ máy vừa xoá tài khoản của mình: Lyris quay về màn thiết lập (mã thiết lập mới in ở Terminal).
    setup_required: bool


class TermsBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    accept_terms: bool
    version: str = Field(max_length=32)


class TermsState(BaseModel):
    terms_required: bool
    legal_version: str
    terms_accepted_at: str | None = None
    privacy_version: str | None = None


class LegalOut(BaseModel):
    doc: legal.LegalDoc
    version: str
    markdown: str


# ---------------------------------------------------------------------------- tiện ích


def _repo(request: Request) -> Repo:
    repo: Repo = request.app.state.repo
    return repo


def _admin_report(row: reports.ReportRow) -> AdminReport:
    return AdminReport(
        id=row.id,
        target=row.target,  # type: ignore[arg-type]
        created_at=row.created_at,
        updated_at=row.updated_at,
        reason=row.reason,  # type: ignore[arg-type]
        note=row.note,
        mode=row.mode,  # type: ignore[arg-type]
        language=row.language,  # type: ignore[arg-type]
        model_name=row.model_name,
        shared_text=row.shared_text,
        message_text=row.message_text,
        status=row.status,  # type: ignore[arg-type]
        reviewed_at=row.reviewed_at,
        public_card_id=row.public_card_id,
        public_card_name=row.public_card_name,
        public_card_creator=row.public_card_creator,
    )


def terms_state(repo: Repo, account_id: int) -> TermsState:
    with repo.locked() as conn:
        accepted_at, version = legal.accepted_version(conn, account_id)
        required = legal.terms_required(conn, account_id)
    return TermsState(
        terms_required=required, legal_version=legal.LEGAL_VERSION, terms_accepted_at=accepted_at,
        privacy_version=version,
    )


# ---------------------------------------------------------------------------- báo cáo nội dung


@router.post("/messages/{message_id}/report", response_model=ReportOut)
async def report_message(request: Request, message_id: int, body: ReportBody, account: CurrentAccount) -> ReportOut:
    repo = _repo(request)
    account_id = account_id_of(account)
    msg = repo.get_message(message_id, account_id=account_id)  # 404 nếu không phải story của mình
    if msg.role != "assistant":
        raise HTTPException(status_code=422, detail=ONLY_REPLIES)
    story = repo.get_story(msg.story_id, account_id=account_id)
    origin = repo.card_origin(story.card_id)
    note = " ".join(body.note.split())[: reports.NOTE_MAX]
    text = msg.visible_content[: reports.SNAPSHOT_MAX] if body.share_text else None
    assert msg.id is not None and story.id is not None
    new = reports.NewReport(
        reporter_id=account_id,
        message_id=msg.id,
        story_id=story.id,
        public_card_id=origin.origin_card_id if origin.story_copy else None,
        reason=body.reason,
        note=note,
        mode=msg.mode,
        language=story.language,
        model_name=msg.model_name,
        message_text=text,
    )
    with repo.transaction():
        report_id, _created = reports.upsert(repo.conn, new, clock.now())
    # Không gắn tài khoản, thiết bị, lượt hay story, không gửi PostHog: người quản lý không biết ai báo cáo.
    track_detached(
        request, "content_reported",
        {"reason": reports.ANALYTICS_REASON[body.reason], "target": "message", "mode": story.mode},
        account_id=account_id,
    )
    return ReportOut(id=report_id, reason=body.reason, shared_text=text is not None, status="open")


@router.post("/cards/{card_id}/report", response_model=ReportOut)
async def report_card(request: Request, card_id: int, body: CardReportBody, account: CurrentAccount) -> ReportOut:
    """Báo cáo hồ sơ một nhân vật công khai của người khác. Bản sao trong story của mình -> nhân vật gốc (còn công
    khai). Nhân vật của chính mình: 422. Không công khai / không có: 404 (không lộ nhân vật riêng tư)."""
    repo = _repo(request)
    account_id = account_id_of(account)
    target_id = card_id
    try:
        repo.get_card(card_id, account_id=account_id)
        own = True
    except NotFound:
        own = False
    if own:
        origin = repo.card_origin(card_id)
        if not origin.story_copy:
            raise HTTPException(status_code=422, detail=OWN_CARD)
        if origin.origin_card_id is None:
            raise NotFound(NOT_PUBLIC)
        target_id = origin.origin_card_id
    try:
        card = repo.get_public_card(target_id)
    except NotFound:
        raise NotFound(NOT_PUBLIC) from None
    if repo.card_account_id(target_id) == account_id:
        raise HTTPException(status_code=422, detail=OWN_CARD)
    note = " ".join(body.note.split())[: reports.NOTE_MAX]
    with repo.transaction():
        report_id, _created = reports.upsert_card(
            repo.conn, reporter_id=account_id, card_id=target_id, reason=body.reason, note=note,
            language=card.language, now=clock.now(),
        )
    track_detached(
        request, "content_reported",
        {"reason": reports.ANALYTICS_REASON[body.reason], "target": "character"},
        account_id=account_id,
    )
    return ReportOut(id=report_id, reason=body.reason, shared_text=False, status="open")


@admin_router.post("/cards/{card_id}/unpublish", response_model=UnpublishedOut)
def unpublish_card(request: Request, card_id: int) -> UnpublishedOut:
    repo = _repo(request)
    with repo.transaction():
        if not reports.unpublish_card(repo.conn, card_id, clock.now()):
            raise NotFound(NOT_PUBLIC)
    logger.info("Chủ máy đã ẩn nhân vật công khai số %d", card_id)
    return UnpublishedOut(unpublished=True)


@admin_router.get("/reports", response_model=list[AdminReport])
def list_reports(request: Request, status: reports.ReportStatus | None = None) -> list[AdminReport]:
    with _repo(request).locked() as conn:
        rows = reports.list_reports(conn, status=status)
    return [_admin_report(r) for r in rows]


@admin_router.patch("/reports/{report_id}", response_model=AdminReport)
def update_report(request: Request, report_id: int, body: ReportStatusBody) -> AdminReport:
    repo = _repo(request)
    with repo.transaction():
        if not reports.set_status(repo.conn, report_id, body.status, clock.now()):
            raise NotFound("Không tìm thấy báo cáo.")
        row = reports.get_report(repo.conn, report_id)
    assert row is not None
    return _admin_report(row)


# ---------------------------------------------------------------------------- dữ liệu cá nhân


async def _check_password(request: Request, account_id: int, password: str) -> bytes:
    """So mật khẩu hiện tại, cùng luật thử sai với đổi mật khẩu (theo tài khoản). Trả hash đã so khớp."""
    repo = _repo(request)
    now = clock.now()
    with repo.transaction():
        conn = repo.conn
        blocked = ratelimit.change_password_block(conn, now, account_id=account_id)
        row = auth_store.account_by_id(conn, account_id)
        attempt = None
        if blocked is None and row is not None:
            attempt = auth_store.record_attempt(
                conn, "change_password", handle=auth_store.account_key(account_id), ip=client_ip(request),
                ok=False, now=now,
            )
    if blocked is not None or attempt is None or row is None:
        raise errors.rate_limited(blocked or 1)
    stored = row.password
    try:
        ok = await passwords.verify_password(password, stored)
    except passwords.HashingBusy:
        with repo.transaction():
            auth_store.drop_attempt(repo.conn, attempt)
        raise errors.busy() from None
    if not ok or stored is None:
        raise AuthError(400, BAD_PASSWORD, "bad_password")
    with repo.transaction():
        auth_store.settle_attempt(repo.conn, attempt, ok=True, now=clock.now(), device=None)
    return stored.digest


@router.delete("/account", response_model=DeletedOut)
async def delete_account(request: Request, body: DeleteAccountBody, account: CurrentAuth) -> DeletedOut:
    """Xoá tài khoản của chính mình và mọi dữ liệu. Chủ máy chỉ xoá được khi không còn tài khoản nào khác."""
    repo = _repo(request)
    with repo.locked() as conn:
        if account.role == "owner" and account_data.other_accounts(conn, account.id):
            raise HTTPException(status_code=409, detail=OWNER_HAS_MEMBERS)
    chat = getattr(request.app.state, "chat", None)
    story_ids = [s.id for s in repo.list_stories(account_id=account.id) if s.id is not None]
    if chat is not None and any(chat.is_busy(sid) for sid in story_ids):
        raise Busy(STORY_BUSY)
    digest = await _check_password(request, account.id, body.password)
    with repo.locked() as conn:
        opted_out = analytics_store.opted_out(conn, account.id)
    try:
        deleted = account_data.delete_account(
            repo, account.id, password_digest=digest, device_anon=device_anon(request)
        )
    except PermissionError:
        raise AuthError(400, BAD_PASSWORD, "bad_password") from None
    except account_data.OwnerHasMembers:
        raise HTTPException(status_code=409, detail=OWNER_HAS_MEMBERS) from None
    settings: Settings = request.app.state.settings
    for name in deleted.files:
        avatars.remove_avatar(settings.avatars_dir, name)
    jobs = getattr(request.app.state, "jobs", None)
    if jobs is not None:
        for story_id in deleted.story_ids:
            jobs.messages_changed(story_id)  # job đang chạy của các story này dừng lại
    service.logout(request)  # xoá cookie phiên (dòng phiên đã bị xoá cùng tài khoản)
    forget_device(request, opt_out=None)  # cookie lyris_anon (đã nối với tài khoản) cũng bỏ
    if not opted_out:
        # Không gắn tài khoản, thiết bị hay lượt (đã xoá), chỉ lưu ở máy.
        track_detached(request, "account_deleted", account_id=None)
    logger.info("Tài khoản @%s đã tự xoá (%d story)", deleted.handle, len(deleted.story_ids))
    if deleted.was_owner:
        _back_to_setup(repo)
    return DeletedOut(deleted=True, setup_required=deleted.was_owner)


def _back_to_setup(repo: Repo) -> None:
    """Chủ máy (tài khoản cuối cùng) vừa tự xoá: tạo lại chủ máy trống và in mã thiết lập mới, như máy mới cài."""
    from lyris.api.app import prepare_auth
    from lyris.auth import setup as owner_setup

    code = prepare_auth(repo)
    if code is not None:
        owner_setup.print_banner(code)


@router.get("/account/export")
async def export_account(request: Request, account: CurrentAccount) -> JSONResponse:
    repo = _repo(request)
    account_id = account_id_of(account)
    data: dict[str, Any] = account_data.export_account(repo, account_id)
    track(request, "data_exported")
    stamp = clock.now().strftime("%Y%m%d")
    filename = f"lyris-{account.handle}-{stamp}.json"
    return JSONResponse(
        content=data,
        headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "no-store"},
    )


@router.post("/account/terms", response_model=TermsState)
async def accept_terms(request: Request, body: TermsBody, account: CurrentAccount) -> TermsState:
    if not body.accept_terms:
        raise HTTPException(status_code=422, detail=legal.TERMS_REQUIRED)
    if body.version != legal.LEGAL_VERSION:
        raise HTTPException(status_code=409, detail=legal.TERMS_OUTDATED)
    repo = _repo(request)
    account_id = account_id_of(account)
    with repo.transaction():
        legal.accept(repo.conn, account_id, clock.now())
    return terms_state(repo, account_id)


# ---------------------------------------------------------------------------- văn bản pháp lý


@public_router.get("/{doc}", response_model=LegalOut)
def get_legal(request: Request, doc: legal.LegalDoc) -> LegalOut:
    try:
        text = legal.load(doc)
    except FileNotFoundError:
        raise NotFound("Chưa có văn bản này.") from None
    settings: Settings | None = getattr(request.app.state, "settings", None)
    markdown = legal.with_contact(text.markdown, getattr(settings, "contact", None))
    return LegalOut(doc=text.doc, version=text.version, markdown=markdown)


__all__ = [
    "OWNER_HAS_MEMBERS",
    "PUBLIC_ROUTES",
    "TermsState",
    "admin_router",
    "public_router",
    "router",
    "terms_state",
]
