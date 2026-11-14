"""Gộp state_events thành state hiện tại (docs/phase3.md §2). Hàm thuần, không đụng DB.

Repo đọc event của các message active (kèm turn_index) rồi đưa vào đây. Không có bảng cache:
state luôn được tính lại từ event, nên regenerate/lật variant/xoá/sửa tự rollback.
"""
from __future__ import annotations

import logging
import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import ValidationError

from lyris.models import (
    DEFAULT_INITIAL_RELATIONSHIP,
    EMOTION_KEYS,
    DominantEmotion,
    RelationshipDelta,
    RelationshipValues,
    SceneState,
)

logger = logging.getLogger("lyris.state")

EventKind = Literal["relationship_delta", "scene", "summary", "suggestions"]
EVENT_KINDS: tuple[EventKind, ...] = ("relationship_delta", "scene", "summary", "suggestions")
# Các loại event do một lần trích xuất sinh ra (trích xuất lại thì thay đúng các loại này). Phase 3b: gợi ý
# không còn do trích xuất sinh ra (chỉ khi người chơi bấm "Nhận gợi ý"), nên trích xuất lại không xoá gợi ý.
EXTRACTION_KINDS: tuple[EventKind, ...] = ("relationship_delta", "scene")
# Event gắn với nội dung của một message: sửa nội dung thì xoá hết (gợi ý viết cho nội dung cũ cũng bỏ).
MESSAGE_STATE_KINDS: tuple[EventKind, ...] = ("relationship_delta", "scene", "suggestions")


@dataclass(frozen=True)
class StateEvent:
    """Một dòng state_events kèm turn_index của message chứa nó."""

    id: int
    story_id: int
    message_id: int
    turn_index: int
    kind: EventKind
    payload: dict[str, Any]
    created_at: str | None = None


@dataclass(frozen=True)
class Summary:
    text: str
    upto_turn: int
    message_id: int


@dataclass(frozen=True)
class FoldedState:
    relationship: RelationshipValues
    has_relationship_events: bool = False
    scene: SceneState = field(default_factory=SceneState)
    summary: Summary | None = None
    suggestions: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------- điểm xuất phát


def clamp_emotion(value: Any, fallback: int) -> int:
    """Giống `clampEmotion` ở frontend: số hữu hạn -> làm tròn (nửa lên) và kẹp 0-100; còn lại -> fallback."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return fallback
    if not math.isfinite(value):
        return fallback
    return min(100, max(0, math.floor(value + 0.5)))


def _valid_emotion(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def card_initial_raw(extensions: Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    """`extensions.lyris.initial_relationship` nếu là object, không thì None."""
    if not isinstance(extensions, Mapping):
        return None
    lyris = extensions.get("lyris")
    if not isinstance(lyris, Mapping):
        return None
    raw = lyris.get("initial_relationship")
    return raw if isinstance(raw, Mapping) else None


def initial_relationship(
    stored: Mapping[str, Any] | None, card_extensions: Mapping[str, Any] | None
) -> RelationshipValues:
    """Điểm xuất phát: từng chỉ số lấy từ story (ảnh chụp lúc tạo), rồi card, rồi mặc định.

    Giá trị không phải số hữu hạn thì bỏ qua và xét nguồn kế tiếp; giá trị dùng được thì kẹp 0-100.
    """
    sources = [s for s in (stored if isinstance(stored, Mapping) else None, card_initial_raw(card_extensions)) if s]
    values: dict[str, int] = {}
    for key in EMOTION_KEYS:
        default = DEFAULT_INITIAL_RELATIONSHIP[key]
        chosen = default
        for src in sources:
            if _valid_emotion(src.get(key)):
                chosen = clamp_emotion(src.get(key), default)
                break
        values[key] = chosen
    return RelationshipValues(**values)


# ---------------------------------------------------------------------------- phép gộp


def apply_delta(values: RelationshipValues, delta: RelationshipDelta) -> RelationshipValues:
    """Cộng một delta rồi kẹp 0-100."""
    return RelationshipValues(
        **{k: min(100, max(0, getattr(values, k) + getattr(delta, k))) for k in EMOTION_KEYS}
    )


def fold_relationship(initial: RelationshipValues, deltas: Iterable[RelationshipDelta]) -> RelationshipValues:
    """Cộng lần lượt các delta, kẹp 0-100 sau MỖI bước (thứ tự quan trọng khi chạm biên)."""
    values = initial
    for delta in deltas:
        values = apply_delta(values, delta)
    return values


def _clean(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def fold_scene(scenes: Iterable[SceneState]) -> SceneState:
    """Từng trường lấy giá trị khác None (và khác rỗng) mới nhất."""
    location: str | None = None
    time: str | None = None
    for scene in scenes:
        location = _clean(scene.location) or location
        time = _clean(scene.time) or time
    return SceneState(location=location, time=time)


def parse_delta(payload: Mapping[str, Any]) -> RelationshipDelta | None:
    try:
        return RelationshipDelta.model_validate(payload)
    except ValidationError:
        return None


def parse_scene(payload: Mapping[str, Any]) -> SceneState | None:
    try:
        return SceneState.model_validate(payload)
    except ValidationError:
        return None


def parse_summary(payload: Mapping[str, Any]) -> tuple[str, int] | None:
    text, upto = payload.get("text"), payload.get("upto_turn")
    if not isinstance(text, str) or not text.strip():
        return None
    if isinstance(upto, bool) or not isinstance(upto, int):
        return None
    return text.strip(), upto


def parse_suggestions(payload: Mapping[str, Any]) -> list[str]:
    items = payload.get("items")
    if not isinstance(items, list):
        return []
    out: list[str] = []
    for item in items:
        text = _clean(item)
        if text and text not in out:
            out.append(text)
    return out[:3]


def _ordered(events: Iterable[StateEvent]) -> list[StateEvent]:
    return sorted(events, key=lambda e: (e.turn_index, e.id))


def fold_events(
    initial: RelationshipValues,
    events: Iterable[StateEvent],
    *,
    last_message_id: int | None = None,
    last_message_role: str | None = None,
    upto_turn: int | None = None,
) -> FoldedState:
    """Gộp event (của message active) thành state.

    - `upto_turn`: chỉ tính event của các lượt <= upto_turn (state như tại lượt đó).
    - Gợi ý chỉ lấy khi message active cuối (`last_message_id`) là của nhân vật và có event gợi ý.
    """
    ordered = [e for e in _ordered(events) if upto_turn is None or e.turn_index <= upto_turn]
    deltas: list[RelationshipDelta] = []
    scenes: list[SceneState] = []
    summary: Summary | None = None
    suggestions: list[str] = []
    for event in ordered:
        if event.kind == "relationship_delta":
            delta = parse_delta(event.payload)
            if delta is None:
                logger.warning("Bỏ qua relationship_delta hỏng (event %s)", event.id)
                continue
            deltas.append(delta)
        elif event.kind == "scene":
            scene = parse_scene(event.payload)
            if scene is not None:
                scenes.append(scene)
        elif event.kind == "summary":
            parsed = parse_summary(event.payload)
            if parsed is not None:
                summary = Summary(text=parsed[0], upto_turn=parsed[1], message_id=event.message_id)
        elif event.kind == "suggestions":
            if last_message_id is not None and last_message_role == "assistant" and event.message_id == last_message_id:
                suggestions = parse_suggestions(event.payload)
    return FoldedState(
        relationship=fold_relationship(initial, deltas),
        has_relationship_events=bool(deltas),
        scene=fold_scene(scenes),
        summary=summary,
        suggestions=suggestions,
    )


def latest_summary(events: Iterable[StateEvent], *, upto_turn: int | None = None) -> Summary | None:
    """Event 'summary' hợp lệ mới nhất (theo lượt rồi id)."""
    found: Summary | None = None
    for event in _ordered(events):
        if event.kind != "summary" or (upto_turn is not None and event.turn_index > upto_turn):
            continue
        parsed = parse_summary(event.payload)
        if parsed is not None:
            found = Summary(text=parsed[0], upto_turn=parsed[1], message_id=event.message_id)
    return found


def dominant_emotion(values: RelationshipValues, *, has_events: bool) -> DominantEmotion | None:
    """Chỉ số cao nhất (bằng nhau thì theo thứ tự EMOTION_KEYS); None khi chưa có delta nào."""
    if not has_events:
        return None
    best = EMOTION_KEYS[0]
    for key in EMOTION_KEYS[1:]:
        if getattr(values, key) > getattr(values, best):
            best = key
    return DominantEmotion(key=best, value=getattr(values, best))


__all__ = [
    "EVENT_KINDS",
    "EXTRACTION_KINDS",
    "MESSAGE_STATE_KINDS",
    "EventKind",
    "FoldedState",
    "StateEvent",
    "Summary",
    "apply_delta",
    "card_initial_raw",
    "clamp_emotion",
    "dominant_emotion",
    "fold_events",
    "fold_relationship",
    "fold_scene",
    "initial_relationship",
    "latest_summary",
    "parse_delta",
    "parse_scene",
    "parse_suggestions",
    "parse_summary",
]
