"""Server-Sent Events cho các endpoint stream câu trả lời.

Mỗi sự kiện:

    event: <name>
    data: <json một dòng>
    (dòng trống)

`event_stream_response` "mồi" sự kiện đầu tiên trước khi trả response: lỗi xảy ra trước khi stream
bắt đầu (NotFound, Busy, InvalidOperation) được raise ra endpoint và thành HTTP status bình thường.
"""
from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import anyio
from starlette.responses import StreamingResponse
from starlette.types import Receive, Scope, Send

from lyris.chat.service import ChatEvent

logger = logging.getLogger("lyris.api.sse")

SSE_HEADERS: dict[str, str] = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
}


def format_event(name: str, data: Any) -> str:
    """Một sự kiện SSE; JSON một dòng (json.dumps không bao giờ chèn xuống dòng khi không có indent)."""
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {name}\ndata: {payload}\n\n"


def encode_event(event: ChatEvent) -> bytes:
    return format_event(event.name, event.data).encode("utf-8")


async def _aclose_shielded(iterator: AsyncIterator[Any]) -> None:
    aclose = getattr(iterator, "aclose", None)
    if aclose is None:
        return
    with anyio.CancelScope(shield=True):
        await aclose()


class EventStreamResponse(StreamingResponse):
    """StreamingResponse luôn đóng body iterator khi kết thúc.

    Khi client ngắt kết nối, Starlette huỷ task đang stream. Nếu lúc đó generator đang dừng ở `yield`
    (chờ `send`), nó sẽ không được đóng cho tới khi bị thu gom rác; ở đây ta đóng ngay để phần trả lời
    dở được lưu và khoá story được nhả.
    """

    media_type = "text/event-stream"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        try:
            await super().__call__(scope, receive, send)
        finally:
            await _aclose_shielded(self.body_iterator)  # type: ignore[arg-type]


async def _frames(first: ChatEvent, events: AsyncIterator[ChatEvent]) -> AsyncIterator[bytes]:
    try:
        yield encode_event(first)
        async for event in events:
            yield encode_event(event)
    finally:
        await _aclose_shielded(events)


async def event_stream_response(events: AsyncIterator[ChatEvent]) -> EventStreamResponse:
    """Lấy sự kiện đầu tiên (ngoại lệ lan ra người gọi), rồi stream phần còn lại dưới dạng SSE."""
    first = await anext(events)
    return EventStreamResponse(_frames(first, events), headers=SSE_HEADERS)


__all__ = [
    "SSE_HEADERS",
    "EventStreamResponse",
    "encode_event",
    "event_stream_response",
    "format_event",
]
