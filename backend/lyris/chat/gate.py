"""Cổng sinh chung cho cả máy (Phase 4b, docs/auth.md §5.1).

Một Ollama phục vụ nhiều tài khoản:
- tối đa `slots` lượt sinh cùng lúc trên cả máy (`LYRIS_CHAT_SLOTS`, mặc định 2 = số slot của Ollama);
- mỗi tài khoản tối đa MỘT lượt sinh cùng lúc (trên mọi story, chat thử, viết nháp của họ). Lượt thứ hai của
  cùng tài khoản bị từ chối ngay (`AccountBusy`, API trả 409), không xếp hàng;
- hết chỗ thì xếp hàng vào trước ra trước, không ưu tiên chủ máy. Chờ quá `wait_timeout` (120 giây) thì bỏ
  (`GateTimeout`).

Dùng hai bước để lượt chat báo được "đang chờ" trước khi chờ (sự kiện SSE `waiting`):

    ticket = gate.reserve(account_id, label)   # AccountBusy ngay nếu tài khoản đang có lượt sinh khác
    try:
        if not ticket.ready:
            ...báo đang chờ...
        await ticket.wait()                    # GateTimeout sau wait_timeout giây
        ...sinh...
    finally:
        ticket.release()

Khoá theo story (`ChatService`) vẫn giữ nguyên; cổng này nằm thêm ở ngoài.
"""
from __future__ import annotations

import asyncio
import collections
from dataclasses import dataclass, field

DEFAULT_WAIT_TIMEOUT_S = 120.0

# docs/auth.md §5.5: không nói tới model, slot, Ollama.
WAIT_TIMEOUT_DETAIL = "Lyris đang bận. Tin của bạn đã lưu, hãy thử lại sau ít phút."
GATE_TIMEOUT_DETAIL = "Lyris đang bận. Hãy thử lại sau ít phút."
OTHER_WORK_DETAIL = "Bạn đang có một việc khác của AI chưa xong. Đợi xong rồi thử lại nhé."


def other_story_detail(name: str) -> str:
    """Tài khoản đang có lượt sinh ở story khác (§5.5)."""
    name = " ".join(name.split()) or "Nhân vật"
    return f"{name} vẫn đang trả lời bạn ở story khác. Đợi xong rồi gửi tiếp nhé."


class AccountBusy(RuntimeError):
    """Tài khoản đang có một lượt sinh khác (API: 409). `str(exc)` là câu cho người dùng."""


class GateTimeout(RuntimeError):
    """Chờ chỗ quá lâu (API: 409 hoặc sự kiện lỗi trong stream)."""


@dataclass(eq=False)
class Ticket:
    """Chỗ của một lượt sinh: giữ quyền "tài khoản đang sinh" từ lúc `reserve`, và một slot sau `wait()`."""

    gate: GenerationGate
    account_id: int
    label: str
    ready: bool = False  # đã có slot (ngay lúc reserve, hoặc sau khi chờ)
    released: bool = False
    _future: asyncio.Future[None] | None = field(default=None, repr=False)

    async def wait(self) -> None:
        """Chờ tới lượt (FIFO). Quá `wait_timeout` -> GateTimeout (vé được trả lại luôn)."""
        if self.ready:
            return
        assert self._future is not None
        try:
            await asyncio.wait_for(asyncio.shield(self._future), self.gate.wait_timeout)
        except TimeoutError as exc:
            self.release()
            raise GateTimeout(GATE_TIMEOUT_DETAIL) from exc
        except BaseException:
            self.release()
            raise
        self.ready = True

    def release(self) -> None:
        """Trả slot (nếu đang giữ) và quyền "tài khoản đang sinh". Gọi nhiều lần không sao."""
        if self.released:
            return
        self.released = True
        self.gate._release(self)

    async def __aenter__(self) -> Ticket:
        await self.wait()
        return self

    async def __aexit__(self, *exc: object) -> None:
        self.release()


class GenerationGate:
    def __init__(self, slots: int = 2, *, wait_timeout: float = DEFAULT_WAIT_TIMEOUT_S) -> None:
        if slots < 1:
            raise ValueError("Cần ít nhất 1 chỗ sinh")
        self.slots = slots
        self.wait_timeout = wait_timeout
        self._active = 0  # số slot đang dùng
        self._waiting: collections.deque[Ticket] = collections.deque()
        self._holders: dict[int, Ticket] = {}  # tài khoản -> vé đang giữ (đang sinh hoặc đang chờ)

    @property
    def active(self) -> int:
        return self._active

    @property
    def queued(self) -> int:
        return sum(1 for t in self._waiting if not t.released)

    def holder(self, account_id: int) -> Ticket | None:
        return self._holders.get(account_id)

    def reserve(self, account_id: int, label: str = "") -> Ticket:
        """Nhận vé cho `account_id`. Tài khoản đang giữ vé khác -> AccountBusy (câu theo `label` của vé đó).

        Còn slot và không ai đang chờ thì vé `ready` ngay; không thì vé vào cuối hàng (gọi `wait()`).
        Không nhường event loop: kiểm tra + giữ chỗ là nguyên tử với các coroutine khác.
        """
        current = self._holders.get(account_id)
        if current is not None and not current.released:
            raise AccountBusy(current.label or OTHER_WORK_DETAIL)
        ticket = Ticket(gate=self, account_id=account_id, label=label)
        self._holders[account_id] = ticket
        if self._active < self.slots and not self.queued:
            self._active += 1
            ticket.ready = True
        else:
            ticket._future = asyncio.get_running_loop().create_future()
            self._waiting.append(ticket)
        return ticket

    def _release(self, ticket: Ticket) -> None:
        if self._holders.get(ticket.account_id) is ticket:
            del self._holders[ticket.account_id]
        fut = ticket._future
        if fut is not None and not fut.done():
            # Chưa tới lượt: rời hàng, không trả slot nào.
            fut.cancel()
            return
        # Đang giữ slot (ready ngay, hoặc future đã được trao): chuyển slot cho người chờ tiếp theo.
        self._handoff()

    def _handoff(self) -> None:
        while self._waiting:
            nxt = self._waiting.popleft()
            fut = nxt._future
            if nxt.released or fut is None or fut.done():
                continue
            fut.set_result(None)  # slot chuyển thẳng cho vé này (FIFO), `_active` giữ nguyên
            return
        self._active = max(0, self._active - 1)


__all__ = [
    "AccountBusy",
    "DEFAULT_WAIT_TIMEOUT_S",
    "GATE_TIMEOUT_DETAIL",
    "GateTimeout",
    "GenerationGate",
    "OTHER_WORK_DETAIL",
    "Ticket",
    "WAIT_TIMEOUT_DETAIL",
    "other_story_detail",
]
