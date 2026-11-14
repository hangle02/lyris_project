"""Bảng sự kiện (docs/tracking-plan.md): tên, nguồn, và luật cho từng thuộc tính.

Luật cứng: không bao giờ có chữ của người dùng trong số liệu. Thuộc tính chỉ có bốn loại:
- `Choice`: chuỗi trong một tập cố định (enum);
- `Flag`: true/false;
- `Count`: số nguyên trong [lo, hi] (thời gian, số token, số mục...), không phải dữ liệu nhạy cảm;
- `IntChoice`: số nguyên trong một tập cố định (1/7/30 ngày...).

Số có thể nói lên nội dung (độ dài tin nhắn, số ngày vắng, số lượt) được chia khoảng thành `Choice` ở phía server
(`lyris.analytics.buckets`) trước khi ghi.

`validate()` từ chối (EventRejected) sự kiện lạ, thuộc tính lạ, kiểu sai, giá trị ngoài enum/khoảng, và thiếu
thuộc tính bắt buộc. Server gọi sai là lỗi lập trình (test bắt); client gửi sai thì sự kiện đó bị bỏ.
"""
from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

Source = Literal["server", "client"]

MAX_PROPS = 10
MAX_PROPS_JSON = 1024


class EventRejected(ValueError):
    """Sự kiện không đúng bảng (tên lạ, thuộc tính lạ, giá trị không được phép)."""


@dataclass(frozen=True)
class Choice:
    values: frozenset[str]

    def check(self, value: Any) -> Any:
        if not isinstance(value, str) or value not in self.values:
            raise EventRejected("giá trị không thuộc enum")
        return value


@dataclass(frozen=True)
class Flag:
    def check(self, value: Any) -> Any:
        if not isinstance(value, bool):
            raise EventRejected("phải là true/false")
        return value


@dataclass(frozen=True)
class Count:
    lo: int
    hi: int

    def check(self, value: Any) -> Any:
        if isinstance(value, bool) or not isinstance(value, int) or not self.lo <= value <= self.hi:
            raise EventRejected("số ngoài khoảng cho phép")
        return value


@dataclass(frozen=True)
class IntChoice:
    values: frozenset[int]

    def check(self, value: Any) -> Any:
        if isinstance(value, bool) or not isinstance(value, int) or value not in self.values:
            raise EventRejected("số không thuộc tập cho phép")
        return value


Prop = Choice | Flag | Count | IntChoice


def choice(*values: str) -> Choice:
    return Choice(frozenset(values))


@dataclass(frozen=True)
class EventSpec:
    name: str
    sources: frozenset[Source]
    props: Mapping[str, Prop] = field(default_factory=dict)
    required: frozenset[str] = frozenset()
    pre_auth: bool = False  # client gửi được khi chưa đăng nhập (chỉ có anon_id)
    story_scoped: bool = False  # client được gửi kèm story_id (server kiểm story là của người gửi)


# --------------------------------------------------------------------------- tập giá trị dùng chung

MODE = choice("story", "dm")
LANGUAGE = choice("vi", "en")
STORY_SOURCE = choice("own", "template", "public", "default")
CARD_SOURCE = choice("own", "template", "public")
LENGTH_BUCKET = choice("1_20", "21_80", "81_200", "201_500", "501_plus")
TURN_BUCKET = choice("1", "2_4", "5_9", "10_19", "20_plus")
TTFT_BUCKET = choice("lt_1s", "1_3s", "3_10s", "10_30s", "30s_plus", "none")
DAYS_BUCKET = choice("1", "2_3", "4_7", "8_30", "31_plus")
SMALL_COUNT_BUCKET = choice("1", "2_5", "6_plus")
AGE_BUCKET = choice("lt_1h", "lt_1d", "lt_7d", "7d_plus")
REPLY_KIND = choice("send", "retry", "regenerate")
REPLY_FAIL = choice("connect", "timeout", "missing_model", "empty_reply", "save_failed", "queue_timeout", "other")
LOGIN_FAIL = choice(
    "bad_credentials", "rate_limited", "account_disabled", "temporary_expired", "setup_required", "busy", "other"
)
VIBE = choice("chua_lanh", "diu_dang", "bi_an_noi_tam", "tinh_dau", "other_template", "other_tag")
REPORT_REASON = choice("sexual_content", "minor_safety", "violence", "hate", "self_harm", "harassment", "other")
REPORT_TARGET = choice("message", "character")
PROFILE_FROM = choice("explore", "library", "profile", "story", "link")
CREATED_VIA = choice("form", "ai_draft", "import", "duplicate")
VISIBILITY = choice("private", "public")
DISPLAY_MODE = choice("standalone", "browser")
LORE_FORMAT = choice("world_md", "card_book")
RATING = choice("up", "down", "cleared")
MSG_ROLE = choice("user", "assistant")
# Coin (docs/coins.md §11). `test` = chat thử ở Studio. Quà mở ví (backfill) do migration ghi, không có sự kiện.
COIN_MODE = choice("story", "dm", "test")
COIN_RELEASE = choice("error", "empty", "cancelled", "queue_timeout", "save_failed", "invalid", "restart")
# F44 làm lại: `creator_milestone` (thưởng mốc người chơi) thay bằng `creator_rank` và `creator_first_public`.
COIN_SOURCE = choice(
    "signup", "daily", "mission_ad", "mission_characters", "mission_turns", "creator_rank", "creator_first_public",
    "topup_code",
)
WALLET_FROM = choice("header", "account", "composer", "link")
# Nạp coin (F43, docs/coins.md §11). `custom` = mã nạp số coin tự nhập (không theo gói).
PACK = choice("p100", "p550", "p1200", "p2500")
CODE_PACK = choice("p100", "p550", "p1200", "p2500", "custom")
TOPUP_FAIL = choice("invalid", "expired", "used", "revoked", "rate_limited")
TOPUP_FROM = choice("wallet", "composer", "link")
ADJUST_DIRECTION = choice("up", "down")
ADJUST_BUCKET = choice("1_50", "51_300", "301_plus")
# Nhiệm vụ ngày (F45, docs/coins.md §11).
MISSION = choice("ad", "characters", "turns")
MISSIONS_FROM = choice("wallet", "composer", "link")
# Bảng "Nhân vật hot" (F46): mở từ nút "Xem bảng xếp hạng" ở Khám phá hay từ link.
HOT_FROM = choice("explore", "link")

S: frozenset[Source] = frozenset({"server"})
C: frozenset[Source] = frozenset({"client"})


def _spec(
    name: str,
    sources: frozenset[Source],
    props: Mapping[str, Prop] | None = None,
    *,
    required: tuple[str, ...] = (),
    pre_auth: bool = False,
    story_scoped: bool = False,
) -> EventSpec:
    return EventSpec(
        name=name,
        sources=sources,
        props=dict(props or {}),
        required=frozenset(required),
        pre_auth=pre_auth,
        story_scoped=story_scoped,
    )


_SPECS: tuple[EventSpec, ...] = (
    # ---- thu hút / kích hoạt tài khoản
    _spec("app_opened", C, {"display_mode": DISPLAY_MODE, "authed": Flag()}, pre_auth=True),
    _spec("session_started", S),  # server tự ghi: sự kiện đầu tiên sau 30 phút không hoạt động
    _spec("signup_viewed", C, {"has_invite_code": Flag()}, pre_auth=True),
    _spec("signup_completed", S),
    _spec("invite_redeemed", S, {"invite_age": AGE_BUCKET}, required=("invite_age",)),
    _spec("owner_setup_completed", S),
    _spec("login_succeeded", S),
    _spec("login_failed", S, {"reason": LOGIN_FAIL}, required=("reason",)),
    _spec("invite_created", S, {"expires_days": IntChoice(frozenset({1, 7, 30}))}, required=("expires_days",)),
    # ---- khám phá
    _spec("explore_viewed", C),
    # F47: ô "Tìm nhân vật" ổn định sau debounce, một lần cho mỗi chuỗi tìm khác nhau; không bao giờ có chữ đã gõ
    _spec("explore_searched", C, {"has_results": Flag()}, required=("has_results",)),
    # F46: bảng "Nhân vật hot" (#/explore/hot) mở
    _spec("hot_board_viewed", C, {"from": HOT_FROM}),
    _spec("vibe_filter_used", C, {"vibe": VIBE, "position": Count(1, 20)}, required=("vibe",)),
    _spec("character_profile_viewed", C, {"source": CARD_SOURCE, "from": PROFILE_FROM}, required=("source",)),
    # ---- bắt đầu story
    _spec("story_start_clicked", C, {"source": CARD_SOURCE}, required=("source",)),
    _spec(
        "story_started", S, {"mode": MODE, "source": STORY_SOURCE, "language": LANGUAGE},
        required=("mode", "source", "language"),
    ),
    # ---- vòng lặp chính
    _spec(
        "message_sent", S,
        {"mode": MODE, "length_bucket": LENGTH_BUCKET, "has_action": Flag(), "has_directive": Flag(), "user_turn": TURN_BUCKET},
        required=("mode", "length_bucket", "has_action", "has_directive", "user_turn"),
    ),
    _spec(
        "reply_completed", S,
        {
            "mode": MODE, "kind": REPLY_KIND, "ttft_bucket": TTFT_BUCKET, "duration_ms": Count(0, 3_600_000),
            "output_tokens": Count(0, 100_000), "aborted": Flag(), "waited": Flag(),
        },
        required=("mode", "kind", "ttft_bucket", "duration_ms", "aborted"),
    ),
    _spec(
        "reply_failed", S, {"mode": MODE, "kind": REPLY_KIND, "reason": REPLY_FAIL, "waited": Flag()},
        required=("mode", "kind", "reason"),
    ),
    _spec("regenerate_used", S, {"mode": MODE}, required=("mode",)),
    _spec("message_edited", S, {"role": MSG_ROLE, "mode": MODE}, required=("role",)),
    _spec("message_deleted", S, {"count_bucket": SMALL_COUNT_BUCKET, "mode": MODE}, required=("count_bucket",)),
    _spec("variant_switched", S, {"mode": MODE}),
    _spec("reply_rated", S, {"rating": RATING, "mode": MODE}, required=("rating",)),
    _spec("suggestions_requested", S, {"ok": Flag(), "items": Count(0, 3), "mode": MODE}, required=("ok",)),
    _spec("suggestion_used", C, {"position": Count(1, 3), "mode": MODE}, required=("position",), story_scoped=True),
    _spec("thought_revealed", C, {"mode": MODE}, story_scoped=True),
    _spec("show_thoughts_toggled", S, {"enabled": Flag()}, required=("enabled",)),
    _spec("mode_switched", S, {"to": MODE}, required=("to",)),
    _spec("heart_drawer_opened", C, {"mode": MODE}, story_scoped=True),
    _spec("lore_unlocked", S, {"count": Count(1, 100), "mode": MODE}, required=("count",)),
    _spec("memory_forgotten", S),
    _spec("events_timeline_opened", C, {"mode": MODE}, story_scoped=True),
    # ---- sáng tạo
    _spec(
        "character_created", S, {"via": CREATED_VIA, "visibility": VISIBILITY, "has_avatar": Flag()},
        required=("via", "visibility"),
    ),
    _spec("character_published", S),
    _spec("lore_imported", S, {"format": LORE_FORMAT, "entries": Count(0, 10_000)}, required=("format", "entries")),
    _spec("persona_created", S),
    # ---- giữ chân
    _spec("story_resumed", S, {"days_since_last": DAYS_BUCKET, "mode": MODE}, required=("days_since_last",)),
    # ---- an toàn nội dung
    # Chỉ server ghi, không gắn ai (lyris.analytics.track_detached): người quản lý không biết ai báo cáo.
    _spec("content_reported", S, {"reason": REPORT_REASON, "target": REPORT_TARGET, "mode": MODE}, required=("reason", "target")),
    # ---- tài khoản và quyền riêng tư
    _spec("account_deleted", S),
    _spec("data_exported", S),
    _spec("analytics_opt_out", S),
    # ---- coin (F42, docs/coins.md §11): chỉ enum và số trong khoảng, không tên nhân vật, lý do hay mã nạp
    _spec("coins_spent", S, {"mode": COIN_MODE, "kind": REPLY_KIND}, required=("mode", "kind")),
    _spec("coins_released", S, {"kind": REPLY_KIND, "reason": COIN_RELEASE}, required=("kind", "reason")),
    _spec("coins_insufficient", S, {"mode": COIN_MODE, "kind": REPLY_KIND}, required=("mode", "kind")),
    _spec("coins_granted", S, {"source": COIN_SOURCE, "amount": Count(1, 10_000)}, required=("source", "amount")),
    _spec("wallet_viewed", C, {"from": WALLET_FROM}),
    # ---- nạp coin, chế độ thử (F43): không bao giờ có mã nạp, lý do điều chỉnh hay số coin chính xác của điều chỉnh
    _spec("coins_adjusted", S, {"direction": ADJUST_DIRECTION, "amount_bucket": ADJUST_BUCKET}, required=("direction", "amount_bucket")),
    _spec("topup_viewed", C, {"from": TOPUP_FROM}),
    _spec("topup_pack_selected", C, {"pack": PACK}, required=("pack",)),
    _spec("topup_code_redeemed", S, {"pack": CODE_PACK}, required=("pack",)),
    _spec("topup_code_failed", S, {"reason": TOPUP_FAIL}, required=("reason",)),
    _spec(
        "topup_code_created", S, {"pack": CODE_PACK, "expires_days": IntChoice(frozenset({1, 7, 30}))},
        required=("pack", "expires_days"),
    ),
    # ---- nhiệm vụ ngày, quảng cáo mẫu (F45): quảng cáo mẫu không gửi gì cho bên quảng cáo nào
    _spec("missions_viewed", C, {"from": MISSIONS_FROM}),
    _spec("ad_started", S),
    _spec("mission_claimed", S, {"mission": MISSION}, required=("mission",)),
    # ---- thưởng sáng tác theo bảng xếp hạng (F44 làm lại): ghi tách (không gắn người chơi), không tên nhân vật
    _spec(
        "creator_rank_reached", S, {"tier": IntChoice(frozenset({100, 50, 10})), "paid": Flag()},
        required=("tier", "paid"),
    ),
)

EVENTS: dict[str, EventSpec] = {spec.name: spec for spec in _SPECS}
assert len(EVENTS) == len(_SPECS), "trùng tên sự kiện"

CLIENT_EVENTS: frozenset[str] = frozenset(n for n, s in EVENTS.items() if "client" in s.sources)
PRE_AUTH_EVENTS: frozenset[str] = frozenset(n for n, s in EVENTS.items() if s.pre_auth)


def validate(name: str, props: Mapping[str, Any] | None, *, source: Source) -> dict[str, Any]:
    """Thuộc tính đã kiểm (bản sao) cho sự kiện `name` từ `source`; sai thì EventRejected."""
    spec = EVENTS.get(name)
    if spec is None:
        raise EventRejected("sự kiện không có trong bảng")
    if source not in spec.sources:
        raise EventRejected("nguồn này không được gửi sự kiện này")
    raw = dict(props or {})
    if len(raw) > MAX_PROPS:
        raise EventRejected("quá nhiều thuộc tính")
    clean: dict[str, Any] = {}
    for key, value in raw.items():
        rule = spec.props.get(key) if isinstance(key, str) else None
        if rule is None:
            raise EventRejected("thuộc tính lạ")
        clean[key] = rule.check(value)
    if not spec.required <= clean.keys():
        raise EventRejected("thiếu thuộc tính bắt buộc")
    if len(dumps(clean)) > MAX_PROPS_JSON:
        raise EventRejected("thuộc tính quá lớn")
    return clean


def dumps(props: Mapping[str, Any]) -> str:
    return json.dumps(dict(props), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


__all__ = [
    "CLIENT_EVENTS",
    "EVENTS",
    "PRE_AUTH_EVENTS",
    "EventRejected",
    "EventSpec",
    "dumps",
    "validate",
]
