"""Hàng đợi việc nền (bảng `jobs`) và tín hiệu ưu tiên lượt chat.

ChatService chỉ nói chuyện với `JobQueue`:
- `generation_started` / `generation_finished` quanh mỗi lượt stream (send, respond, regenerate);
- `turn_saved` sau khi lưu một lượt trả lời trọn vẹn;
- `message_reset` khi sửa nội dung message của nhân vật;
- `messages_changed` khi variant/active thay đổi (regenerate, lật variant, xoá).

Worker đăng ký làm listener để bị huỷ job đang chạy khi có lượt chat, hoặc khi message của job hết active.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Protocol

from lyris.db.repo import ANY_ACCOUNT, JobKind, Repo
from lyris.models import Message
from lyris.state.service import StateService, window_start_turn

logger = logging.getLogger("lyris.jobs")


class QueueListener(Protocol):
    def on_generation_started(self, story_id: int) -> None: ...

    def on_generation_finished(self, story_id: int) -> None: ...

    def on_messages_changed(self, story_id: int) -> None: ...

    def on_message_reset(self, message_id: int, story_id: int) -> None: ...

    # Tuỳ chọn, gọi qua getattr: `on_lore_changed(story_ids: list[int])` (Phase 4),
    # `on_story_focused(story_id: int)` (story vừa tạo qua API).


class JobQueue:
    def __init__(self, repo: Repo, state: StateService | None = None) -> None:
        self._repo = repo
        self._state = state
        self._wake = asyncio.Event()
        self._idle = asyncio.Event()
        self._idle.set()
        self._streams = 0
        self._listeners: list[QueueListener] = []

    @property
    def repo(self) -> Repo:
        return self._repo

    def attach(self, listener: QueueListener) -> None:
        self._listeners.append(listener)

    # ------------------------------------------------------------------ ưu tiên lượt chat

    @property
    def streaming(self) -> bool:
        """Đang có ít nhất một lượt chat stream: worker không bắt đầu job mới."""
        return self._streams > 0

    def generation_started(self, story_id: int) -> None:
        self._streams += 1
        self._idle.clear()
        for listener in self._listeners:
            try:
                listener.on_generation_started(story_id)
            except Exception:
                logger.exception("Listener lỗi khi bắt đầu lượt chat (story %s)", story_id)

    def generation_finished(self, story_id: int) -> None:
        self._streams = max(0, self._streams - 1)
        for listener in self._listeners:
            try:
                listener.on_generation_finished(story_id)
            except Exception:
                logger.exception("Listener lỗi khi kết thúc lượt chat (story %s)", story_id)
        if self._streams == 0:
            self._idle.set()
            self._wake.set()

    async def wait_idle(self) -> None:
        await self._idle.wait()

    def clear_wake(self) -> None:
        self._wake.clear()

    async def wait_for_work(self, timeout: float) -> None:
        """Chờ tới khi có job mới được xếp (hoặc hết `timeout` giây)."""
        try:
            await asyncio.wait_for(self._wake.wait(), timeout)
        except TimeoutError:
            pass

    # ------------------------------------------------------------------ xếp job

    def enqueue(self, story_id: int, kind: JobKind, message_id: int | None = None) -> int:
        job_id = self._repo.enqueue_job(story_id, kind, message_id)
        self._wake.set()
        return job_id

    @staticmethod
    def extractable(message: Message) -> bool:
        """Lượt của nhân vật (kể cả lời mở đầu lượt 0, Phase 3b: chỉ ghi cảnh và ký ức), không bị ngắt."""
        aborted = message.gen_stats is not None and message.gen_stats.aborted
        return message.role == "assistant" and message.turn_index >= 0 and not aborted

    def turn_saved(self, message: Message) -> int | None:
        """Lượt trả lời vừa lưu trọn vẹn: xếp `extract`. Lượt bị ngắt (aborted) thì không."""
        if message.id is None or not self.extractable(message):
            return None
        return self.enqueue(message.story_id, "extract", message.id)

    def ensure_extracted(self, message: Message) -> int | None:
        """Lật lại một variant chưa từng được trích xuất (job cũ đã bị huỷ): xếp `extract`."""
        if message.id is None or not message.is_active or not self.extractable(message):
            return None
        if self._repo.message_has_extract_job(message.id, ("done", "queued", "running")):
            return None
        return self.enqueue(message.story_id, "extract", message.id)

    def message_reset(self, message: Message) -> int | None:
        """Sửa nội dung message của nhân vật: xoá kết quả trích xuất + ký ức của nó và trích xuất lại.

        Tóm tắt dồn neo ở message này được giữ (xem `Repo.delete_message_state`)."""
        assert message.id is not None
        self._repo.delete_message_state(message.id)
        self._repo.forget_extract_jobs(message.id)
        for listener in self._listeners:
            listener.on_message_reset(message.id, message.story_id)
        if message.role != "assistant" or message.turn_index < 0 or not message.is_active:
            return None
        return self.enqueue(message.story_id, "extract", message.id)

    def story_created(self, story_id: int, *, focus: bool = False) -> int | None:
        """Story mới có lời mở đầu: xếp `extract` cho nó (cảnh + ký ức), để lượt đầu đã có cảnh.

        `focus=True` (người chơi vừa tạo story qua API, app mở story đó ngay): báo listener story này là story
        đang chơi, để prefill sau job lời mở đầu là của story mới chứ không phải story chơi trước đó."""
        if focus:
            for listener in self._listeners:
                handler = getattr(listener, "on_story_focused", None)
                if handler is None:
                    continue
                try:
                    handler(story_id)
                except Exception:
                    logger.exception("Listener lỗi khi đổi story đang chơi (story %s)", story_id)
        active = self._repo.active_messages(story_id)
        opening = next((m for m in active if m.turn_index == 0 and m.role == "assistant"), None)
        if opening is None or opening.id is None or not opening.visible_content.strip():
            return None
        return self.enqueue(story_id, "extract", opening.id)

    def messages_changed(self, story_id: int) -> int:
        """Variant active đổi hoặc message bị xoá: huỷ job thừa. Trả số job `queued` đã huỷ."""
        cancelled = self._repo.cancel_stale_jobs(story_id)
        for listener in self._listeners:
            listener.on_messages_changed(story_id)
        return cancelled

    def lore_changed(self, card_id: int) -> list[int]:
        """Phase 4: sổ thế giới của card đổi (tạo, sửa, bật/tắt, xoá, nhập). Prefill đang chạy / đang chờ của
        story thuộc card đó được huỷ và hẹn lại (docs/phase4.md §6.5). Trả id các story của card."""
        story_ids = self._repo.card_story_ids(card_id)
        if not story_ids:
            return []
        for listener in self._listeners:
            handler = getattr(listener, "on_lore_changed", None)
            if handler is None:
                continue
            try:
                handler(story_ids)
            except Exception:
                logger.exception("Listener lỗi khi sổ thế giới đổi (card %s)", card_id)
        self._wake.set()
        return story_ids

    def rebuild(self, story_id: int) -> int:
        """Xếp `extract` cho mọi lượt trả lời active chưa được trích xuất (kể cả lời mở đầu, lượt 0), theo
        lượt; rồi `summarize` sau cùng nếu tóm tắt chưa phủ tới mốc khúc cần thiết. Trả số job đã xếp."""
        queued = 0
        for message in self._repo.messages_needing_extract(story_id):
            assert message.id is not None
            self.enqueue(story_id, "extract", message.id)
            queued += 1
        if self.summarize_if_needed(story_id) is not None:
            queued += 1
        return queued

    def mode_changed(self, story_id: int) -> int | None:
        """Người chơi đổi Story <-> DM. Ngân sách lịch sử đổi theo chế độ (phần trả lời dài/ngắn), nên cửa sổ
        có thể sắp dịch ở chế độ mới: tóm tắt trước ngay lúc này (đổi chế độ vốn đã làm prompt đổi từ khối
        luật, nên gọi model tóm tắt không làm mất thêm cache nào)."""
        return self.summarize_if_needed(story_id)

    def summarize_if_needed(self, story_id: int) -> int | None:
        """Xếp `summarize` (neo ở lượt trả lời cuối) nếu tóm tắt chưa phủ tới mốc khúc cần thiết và chưa có
        job tóm tắt đang chờ. Trả id job, hoặc None."""
        if self._state is None:
            return None
        active = self._repo.active_messages(story_id)
        last = next((m for m in reversed(active) if m.role == "assistant" and m.turn_index > 0), None)
        if last is None or last.id is None or self._repo.has_pending_jobs(story_id, kinds=("summarize",)):
            return None
        story = self._repo.get_story(story_id, account_id=ANY_ACCOUNT)
        history = [m for m in active if m.turn_index <= last.turn_index]
        target = self._state.summary_target(story, history, window_start_turn(last, active))
        if not self._state.needs_summary(story, target):
            return None
        return self.enqueue(story_id, "summarize", last.id)

    def pending(self, story_id: int) -> bool:
        """Story còn job `queued`/`running`."""
        return self._repo.has_pending_jobs(story_id)


__all__ = ["JobQueue", "QueueListener"]
