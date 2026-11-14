"""Endpoint state và trí nhớ của story (Phase 3, docs/phase3.md §7).

- GET    /api/stories/{id}/extras                 StoryExtras đầy đủ (quan hệ + chỉ dẫn, cảnh, gợi ý, ký ức...)
- DELETE /api/stories/{id}/memories/{memory_id}   quên một ký ức hoặc fact
- POST   /api/stories/{id}/state/rebuild          xếp job dựng lại state cho các lượt chưa trích xuất
- POST   /api/stories/{id}/suggestions            Phase 3b: nghĩ gợi ý trả lời theo yêu cầu -> {"items": [...]}
- GET    /api/stories/{id}/timeline               Phase 3b: dòng thời gian (các lượt có state, cũ trước)

Mọi route lọc theo account hiện tại: story/ký ức của account khác coi như không có (404).
Không có kênh SSE: frontend hỏi lại /extras khi `pending` là true.
"""
from __future__ import annotations

import asyncio
import contextlib

import anyio
from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel

from lyris.api.deps import CurrentAccount, account_id_of, current_account, job_queue, state_service
from lyris.chat.service import Busy, ChatService
from lyris.db.repo import Repo
from lyris.models import StoryExtras, SuggestionsOut, TimelineEntry

SUGGEST_DISCONNECT_POLL_S = 0.25

# Phase 4b: mặc định là cấm — mọi route ở đây cần đăng nhập (docs/auth.md §2.5).
router = APIRouter(prefix="/api", dependencies=[Depends(current_account)])


class RebuildOut(BaseModel):
    queued: int


def _repo(request: Request) -> Repo:
    repo: Repo = request.app.state.repo
    return repo


@router.get("/stories/{story_id}/extras", response_model=StoryExtras)
async def story_extras(request: Request, story_id: int, account: CurrentAccount) -> StoryExtras:
    """`relationship` luôn có (giá trị khởi đầu nếu chưa có event), kèm `directive`."""
    story = _repo(request).get_story(story_id, account_id=account_id_of(account))  # 404 nếu không có
    return await state_service(request).extras(story)


@router.delete("/stories/{story_id}/memories/{memory_id}")
async def forget_memory(request: Request, story_id: int, memory_id: int, account: CurrentAccount) -> dict[str, int]:
    """Quên một ký ức/fact (xoá dòng). 404 nếu không thuộc story hoặc story không thuộc account."""
    _repo(request).delete_memory(story_id, memory_id, account_id=account_id_of(account))
    return {"deleted": 1}


@router.post("/stories/{story_id}/state/rebuild", response_model=RebuildOut)
async def rebuild_state(request: Request, story_id: int, account: CurrentAccount) -> RebuildOut:
    """Xếp `extract` cho mọi lượt trả lời active chưa được trích xuất (theo lượt), `summarize` sau cùng nếu cần."""
    _repo(request).get_story(story_id, account_id=account_id_of(account))
    chat: ChatService = request.app.state.chat
    if chat.is_busy(story_id):
        raise Busy("Nhân vật đang trả lời trong story này. Hãy đợi xong rồi đọc lại story.")
    return RebuildOut(queued=job_queue(request).rebuild(story_id))


@router.post("/stories/{story_id}/suggestions", response_model=SuggestionsOut)
async def suggestions(request: Request, story_id: int, account: CurrentAccount) -> SuggestionsOut | Response:
    """Phase 3b: nghĩ 1-3 gợi ý cho lượt tiếp của người chơi, chỉ khi người chơi yêu cầu.

    Gọi lại thì thay gợi ý cũ ("Gợi ý khác"); /extras trả chúng tới khi người chơi trả lời.
    409: story đang sinh câu trả lời / đang nghĩ gợi ý, hoặc message cuối không phải của nhân vật.
    502: lỗi model, dạng `{"detail": câu dễ hiểu, "technical": chi tiết}`.
    Người dùng bỏ đi (client ngắt kết nối) thì huỷ lời gọi model và nhả khoá story.
    """
    _repo(request).get_story(story_id, account_id=account_id_of(account))  # 404 nếu không có
    chat: ChatService = request.app.state.chat
    chat.ensure_idle(story_id)  # 409 ngay, trước khi tạo task
    task = asyncio.create_task(chat.suggest(story_id))
    try:
        while not task.done():
            await asyncio.wait({task}, timeout=SUGGEST_DISCONNECT_POLL_S)
            if not task.done() and await request.is_disconnected():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await task
                return Response(status_code=499)
        return SuggestionsOut(items=task.result())
    finally:
        if not task.done():
            task.cancel()
            with anyio.CancelScope(shield=True), contextlib.suppress(asyncio.CancelledError, Exception):
                await task


@router.get("/stories/{story_id}/timeline", response_model=list[TimelineEntry])
async def timeline(request: Request, story_id: int, account: CurrentAccount) -> list[TimelineEntry]:
    """Phase 3b: các lượt active có state (ký ức, fact, thay đổi cảm xúc khác 0, cảnh), lượt cũ trước."""
    story = _repo(request).get_story(story_id, account_id=account_id_of(account))
    return state_service(request).timeline(story)


__all__ = ["RebuildOut", "router"]
