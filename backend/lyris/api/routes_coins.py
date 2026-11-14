"""`/api/coins/*` (docs/coins.md §7): ví, quà đăng nhập trong ngày, lịch sử của CHÍNH tài khoản đang đăng nhập; gói giá
(chế độ thử) và nhập mã nạp (F43). Và `/api/admin/coins/*` + `POST /api/admin/accounts/{id}/coins` (§4.3–§4.5, chỉ chủ
máy): mã nạp, nhật ký coin, cộng/trừ coin có lý do.

Không có route nào nhận thông tin thẻ, ví điện tử hay thanh toán.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from lyris.analytics import context as analytics_context
from lyris.analytics import tracker_of
from lyris.api.deps import CurrentAccount, OwnerAccount, account_id_of, current_account, owner_auth
from lyris.coins import topup
from lyris.coins.wallet import ADJUST_MAX, HISTORY_MAX, HISTORY_PAGE, CoinService, CoinTrack

router = APIRouter(prefix="/api/coins", dependencies=[Depends(current_account)])
admin_router = APIRouter(prefix="/api/admin", dependencies=[Depends(owner_auth)])
# F46 (docs/coins.md §5.2): bảng "Nhân vật hot" ở Khám phá. Ngoài tiền tố /api/coins/ (không phải route coin).
explore_router = APIRouter(prefix="/api/explore", dependencies=[Depends(current_account)])


def coin_service(request: Request) -> CoinService:
    coins: CoinService = request.app.state.coins
    return coins


def coin_track(request: Request) -> CoinTrack | None:
    """Ghi sự kiện coin (§11) với ngữ cảnh của request này (chốt ngay, dùng được sau khi stream đã bắt đầu)."""
    tracker = tracker_of(request)
    if tracker is None:
        return None
    try:
        ctx = analytics_context(request)
    except Exception:
        return None

    def track(name: str, props: Mapping[str, Any]) -> None:
        tracker.emit(ctx, name, props)

    return track


class Wallet(BaseModel):
    balance: int
    available: int
    unlimited: bool
    price_per_reply: int
    enabled: bool


class Checkin(BaseModel):
    granted: bool
    amount: int
    # Quà đăng nhập của hôm nay đã có (60) hay chưa có (0: chủ máy, coin tắt); giao diện hiện "+60 coin cho hôm nay"
    # một lần mỗi ngày kể cả khi quà đã được cộng lúc đăng nhập bằng mật khẩu.
    today: int
    coin_day: str
    wallet: Wallet


class HistoryItem(BaseModel):
    id: int
    delta: int
    kind: str
    label: str
    created_at: str
    balance_after: int
    coin_day: str
    story_id: int | None = None
    name: str | None = None


class History(BaseModel):
    items: list[HistoryItem]
    next: int | None = None


@router.get("/wallet", response_model=Wallet)
def get_wallet(request: Request, account: CurrentAccount) -> Wallet:
    return Wallet(**coin_service(request).wallet(account_id_of(account)))


@router.post("/checkin", response_model=Checkin)
def checkin(request: Request, account: CurrentAccount) -> Checkin:
    result = coin_service(request).checkin(account_id_of(account), track=coin_track(request))
    return Checkin(**result)


@router.get("/history", response_model=History)
def history(
    request: Request,
    account: CurrentAccount,
    before: int | None = Query(default=None, ge=1),
    limit: int = Query(default=HISTORY_PAGE, ge=1, le=HISTORY_MAX),
) -> History:
    data = coin_service(request).history(account_id_of(account), before=before, limit=limit)
    return History(items=[HistoryItem(**i) for i in data["items"]], next=data["next"])


# ---------------------------------------------------------------------------- nhiệm vụ ngày, quảng cáo mẫu (F45, §6)


class MissionOut(BaseModel):
    id: Literal["ad", "characters", "turns"]
    progress: int
    target: int
    reward: int
    claimed: bool
    claimable: bool
    remaining: int


class Missions(BaseModel):
    coin_day: str
    earned_today: int
    cap: int
    missions: list[MissionOut]
    unlimited: bool
    enabled: bool


class Claimed(BaseModel):
    amount: int
    wallet: Wallet


class AdStarted(BaseModel):
    ad_id: int
    seconds: int


class AdCancelled(BaseModel):
    ok: Literal[True] = True


@router.get("/missions", response_model=Missions)
def get_missions(request: Request, account: CurrentAccount) -> Missions:
    return Missions(**coin_service(request).missions(account_id_of(account)))


@router.post("/missions/{mission}/claim", response_model=Claimed)
def claim_mission(request: Request, account: CurrentAccount, mission: Literal["characters", "turns"]) -> Claimed:
    """Nút "Nhận" của "Trò chuyện với 3 nhân vật khác nhau" / "Gửi 20 lượt". Quảng cáo nhận trong hộp (`ads/{id}/claim`)."""
    result = coin_service(request).claim_mission(account_id_of(account), mission, track=coin_track(request))
    return Claimed(amount=result["amount"], wallet=Wallet(**result["wallet"]))


@router.post("/ads/start", response_model=AdStarted)
def start_ad(request: Request, account: CurrentAccount) -> AdStarted:
    return AdStarted(**coin_service(request).start_ad(account_id_of(account), track=coin_track(request)))


@router.post("/ads/{ad_id}/claim", response_model=Claimed)
def claim_ad(request: Request, account: CurrentAccount, ad_id: int) -> Claimed:
    result = coin_service(request).claim_ad(account_id_of(account), ad_id, track=coin_track(request))
    return Claimed(amount=result["amount"], wallet=Wallet(**result["wallet"]))


@router.post("/ads/{ad_id}/cancel", response_model=AdCancelled)
def cancel_ad(request: Request, account: CurrentAccount, ad_id: int) -> AdCancelled:
    """"Đóng" hộp quảng cáo trước khi nhận: lượt xem đó không nhận được nữa. Gọi lại không lỗi."""
    coin_service(request).cancel_ad(account_id_of(account), ad_id)
    return AdCancelled()


class AdjustBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    delta: int = Field(ge=-ADJUST_MAX, le=ADJUST_MAX)
    reason: str = Field(max_length=400)
    request_id: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")

    @field_validator("delta")
    @classmethod
    def _nonzero(cls, value: int) -> int:
        if value == 0:
            raise ValueError("phải khác 0")
        return value

    @field_validator("reason")
    @classmethod
    def _reason(cls, value: str) -> str:
        clean = " ".join(value.split())
        if not 3 <= len(clean) <= 120:
            raise ValueError("lý do cần từ 3 đến 120 ký tự")
        return clean


class Adjusted(BaseModel):
    balance: int
    available: int


@admin_router.post("/accounts/{account_id}/coins", response_model=Adjusted)
def adjust_coins(request: Request, account_id: int, body: AdjustBody, actor: OwnerAccount) -> Adjusted:
    result = coin_service(request).adjust(
        account_id, body.delta, body.reason, body.request_id, actor_id=actor.id, track=coin_track(request)
    )
    return Adjusted(**result)


# ---------------------------------------------------------------------------- nạp coin, chế độ thử (F43, §4)


class PackOut(BaseModel):
    id: str
    coins: int
    bonus: int
    price_vnd: int


class Packs(BaseModel):
    test_mode: bool
    packs: list[PackOut]
    contact: None = None


@router.get("/packs", response_model=Packs)
def packs(request: Request) -> Packs:
    return Packs(**coin_service(request).packs())


class RedeemBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(max_length=200)


class Redeemed(BaseModel):
    amount: int
    wallet: Wallet


@router.post("/redeem", response_model=Redeemed)
def redeem(request: Request, account: CurrentAccount, body: RedeemBody) -> Redeemed:
    result = coin_service(request).redeem(account_id_of(account), body.code, track=coin_track(request))
    return Redeemed(amount=result["amount"], wallet=Wallet(**result["wallet"]))


class TopupCode(BaseModel):
    id: int
    hint: str
    amount: int
    pack_id: str | None = None
    note: str
    created_at: str
    expires_at: str
    status: Literal["active", "used", "expired", "revoked"]
    used_by_handle: str | None = None


class CodeCreated(BaseModel):
    code: str
    item: TopupCode


class CodeBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pack_id: Literal["p100", "p550", "p1200", "p2500"] | None = None
    amount: int | None = Field(default=None, ge=topup.AMOUNT_MIN, le=topup.AMOUNT_MAX)
    note: str = Field(default="", max_length=topup.NOTE_MAX)
    expires_days: Literal[1, 7, 30] = 7

    @model_validator(mode="after")
    def _one_of(self) -> CodeBody:
        if (self.pack_id is None) == (self.amount is None):
            raise ValueError("chọn một gói hoặc nhập số coin")
        return self


@admin_router.get("/coins/codes", response_model=list[TopupCode])
def list_codes(request: Request) -> list[TopupCode]:
    return [TopupCode(**i) for i in coin_service(request).list_codes()]


@admin_router.post("/coins/codes", response_model=CodeCreated)
def create_code(request: Request, body: CodeBody, actor: OwnerAccount) -> CodeCreated:
    item, code = coin_service(request).create_code(
        actor.id, amount=None if body.pack_id else body.amount, pack_id=body.pack_id,
        note=" ".join(body.note.split()), days=int(body.expires_days), track=coin_track(request),
    )
    return CodeCreated(code=code, item=TopupCode(**item))


@admin_router.post("/coins/codes/{code_id}/revoke", response_model=TopupCode)
def revoke_code(request: Request, code_id: int) -> TopupCode:
    return TopupCode(**coin_service(request).revoke_code(code_id))


class LogItem(BaseModel):
    id: int
    created_at: str
    kind: Literal["topup_code", "admin_adjust", "creator_milestone"]
    handle: str | None = None
    delta: int
    reason: str | None = None
    note: str | None = None
    milestone: int | None = None
    # Thưởng sáng tác (§4.5): "Thưởng xếp hạng top {N}", "Thưởng công khai lần đầu", dòng cũ "Thưởng mốc {m} người chơi".
    label: str | None = None


class LogTotals(BaseModel):
    days: int
    granted: int
    topped_up: int
    spent: int


class CoinLog(BaseModel):
    items: list[LogItem]
    totals: LogTotals


@admin_router.get("/coins/log", response_model=CoinLog)
def coin_log(request: Request) -> CoinLog:
    return CoinLog(**coin_service(request).admin_log())


class HotItem(BaseModel):
    """Một hàng của bảng: chỉ trường công khai (không account_id, mô tả hay trường bí mật)."""

    rank: int
    card_id: int
    name: str
    avatar_url: str | None
    creator_handle: str
    players: int


class HotBoard(BaseModel):
    updated_at: str | None
    ranked: int
    items: list[HotItem]


@explore_router.get("/hot", response_model=HotBoard)
def hot_board(request: Request, limit: int = Query(default=100, ge=1, le=100)) -> HotBoard:
    """Bảng "Nhân vật hot" (100 hạng đầu, tính lại khi đã cũ hơn 60 phút; lỗi khi tính thì trả bảng cũ)."""
    from lyris.api.routes_studio import avatar_url_for

    data = coin_service(request).hot_board(limit)
    items = [
        HotItem(
            rank=it["rank"], card_id=it["card_id"], name=it["name"], avatar_url=avatar_url_for(it["card_id"], it["avatar"]),
            creator_handle=it["creator_handle"], players=it["players"],
        )
        for it in data["items"]
    ]
    return HotBoard(updated_at=data["updated_at"], ranked=data["ranked"], items=items)


__all__ = ["admin_router", "coin_service", "coin_track", "explore_router", "router"]
