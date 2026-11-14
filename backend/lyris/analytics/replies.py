"""Theo dõi một lượt trả lời đang stream (SSE) để ghi `reply_completed` / `reply_failed` / `lore_unlocked`.

`tracked_reply(...)` bọc async generator sự kiện chat của `ChatService.send/respond/regenerate`: chuyển nguyên mọi
sự kiện, chỉ nhìn tên sự kiện và số liệu (không đọc chữ). Ngữ cảnh (tài khoản, thiết bị) chốt trong route trước
khi stream bắt đầu. Lượt bị ngắt (người dùng bấm Dừng / đóng tab) ghi `reply_completed` với `aborted = true`.
Lỗi trước khi lượt bắt đầu (404, 409...) không ghi gì: sự kiện lan ra route như cũ.
"""
from __future__ import annotations

import time
from collections.abc import AsyncIterator
from typing import Any

import anyio

from lyris.analytics import buckets, store
from lyris.analytics.tracker import TrackContext, Tracker
from lyris.chat.gate import WAIT_TIMEOUT_DETAIL
from lyris.chat.service import ChatEvent
from lyris.llm import errors as llm_errors


def failure_reason(detail: Any) -> str:
    """Mã lý do (enum) từ câu lỗi của sự kiện SSE `error` (không ghi chính câu đó)."""
    text = str(detail or "")
    if text == llm_errors._BY_KIND["connect"]:
        return "connect"
    if text == llm_errors._BY_KIND["timeout"]:
        return "timeout"
    if text == llm_errors._MISSING_MODEL["reply"]:
        return "missing_model"
    if text == llm_errors.EMPTY_REPLY:
        return "empty_reply"
    if text == llm_errors.SAVE_FAILED:
        return "save_failed"
    if text == WAIT_TIMEOUT_DETAIL:
        return "queue_timeout"
    return "other"


async def tracked_reply(
    events: AsyncIterator[ChatEvent],
    *,
    tracker: Tracker | None,
    ctx: TrackContext | None,
    story_id: int,
    mode: str,
    kind: str,
) -> AsyncIterator[ChatEvent]:
    if tracker is None or ctx is None:
        async for event in events:
            yield event
        return
    started: float | None = None
    first_delta: float | None = None
    waited = False
    outcome: tuple[str, dict[str, Any]] | None = None
    try:
        async for event in events:
            if event.name == "waiting":
                waited = True
            elif event.name == "start":
                started = time.perf_counter()
            elif event.name == "delta" and first_delta is None:
                first_delta = time.perf_counter()
            elif event.name in ("done", "error"):
                outcome = (event.name, event.data)
            yield event
    finally:
        aclose = getattr(events, "aclose", None)
        if aclose is not None:
            with anyio.CancelScope(shield=True):
                await aclose()
        _record(tracker, ctx, story_id, mode, kind, started, first_delta, waited, outcome)


def _record(
    tracker: Tracker,
    ctx: TrackContext,
    story_id: int,
    mode: str,
    kind: str,
    started: float | None,
    first_delta: float | None,
    waited: bool,
    outcome: tuple[str, dict[str, Any]] | None,
) -> None:
    if outcome is not None and outcome[0] == "error":
        tracker.emit(
            ctx, "reply_failed",
            {"mode": mode, "kind": kind, "reason": failure_reason(outcome[1].get("detail")), "waited": waited},
            story_id=story_id,
        )
        return
    if started is None:
        return  # lượt chưa bắt đầu (bị ngắt khi đang chờ cổng sinh...)
    now = time.perf_counter()
    ttft = None if first_delta is None else (first_delta - started) * 1000
    props: dict[str, Any] = {
        "mode": mode,
        "kind": kind,
        "ttft_bucket": buckets.ttft_bucket(ttft),
        "duration_ms": buckets.clamp((now - started) * 1000, 0, 3_600_000, step=100),
        "aborted": outcome is None,
        "waited": waited,
    }
    message: dict[str, Any] = {}
    if outcome is not None:
        message = outcome[1].get("message") or {}
        stats = message.get("gen_stats") or {}
        tokens = stats.get("output_tokens") if isinstance(stats, dict) else None
        if isinstance(tokens, int) and not isinstance(tokens, bool):
            props["output_tokens"] = buckets.clamp(tokens, 0, 100_000)
    tracker.emit(ctx, "reply_completed", props, story_id=story_id)
    message_id = message.get("id")
    if isinstance(message_id, int):
        try:
            with tracker.repo.locked() as conn:
                unlocked = store.new_lore_count(conn, story_id, message_id)
        except Exception:
            unlocked = 0
        if unlocked > 0:
            tracker.emit(ctx, "lore_unlocked", {"count": min(unlocked, 100), "mode": mode}, story_id=story_id)


__all__ = ["failure_reason", "tracked_reply"]
