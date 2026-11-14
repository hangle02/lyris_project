"""Điều phối một lượt chat: lưu lượt người chơi, dựng prompt, stream LLM, lưu câu trả lời.

Mỗi story có một `asyncio.Lock`; trong lúc story đang sinh câu trả lời, mọi thao tác ghi khác
trên story đó (gửi, thử lại, regenerate, lật variant, sửa, xoá) bị từ chối bằng `Busy`.

Các method `send` / `respond` / `regenerate` trả về async generator. Mọi kiểm tra (story có tồn tại,
đang bận, thao tác hợp lệ) chạy ở lần `__anext__` đầu tiên, trước khi yield sự kiện nào, nên
tầng API có thể "mồi" sự kiện đầu để trả HTTP 404/409 bình thường.

Phase 4b (docs/auth.md §5.1): mọi lượt sinh (gửi, thử lại, regenerate, gợi ý) đi qua `GenerationGate` chung
của cả máy: tài khoản đang có lượt sinh ở story khác -> Busy (409) trước khi ghi gì; hết chỗ thì stream sự kiện
`waiting` rồi chờ theo thứ tự đến, quá 120 giây thì sự kiện `error` (tin người chơi đã lưu).

Phase 3 (docs/phase3.md §4, §6): có `StateService` thì prompt kèm `PromptState` (tóm tắt, chỉ dẫn diễn
xuất, cảnh, ký ức) và snapshot lưu kèm `state`; có `JobQueue` thì worker nền được báo khi lượt stream
bắt đầu/kết thúc (nhường model), và job trích xuất được xếp sau mỗi lượt lưu trọn vẹn / khi sửa.

F42 (docs/coins.md §3.2): có `CoinService` thì sau vé cổng sinh, TRƯỚC khi lưu lượt người chơi, giữ chỗ 6 coin
(`CoinsRequired` → 402 trước byte SSE đầu tiên, lượt người chơi không được lưu). Câu trả lời có chữ được lưu (kể cả
phần dở khi bị ngắt) thì trừ trong cùng transaction lưu câu trả lời; không có chữ thì nhả trong `finally` của `_run`
với lý do (error, empty, save_failed, queue_timeout, cancelled, invalid). `coins=None` (test dựng tay) = không tính.
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

import anyio

from lyris.chat.gate import (
    OTHER_WORK_DETAIL,
    WAIT_TIMEOUT_DETAIL,
    AccountBusy,
    GateTimeout,
    GenerationGate,
    Ticket,
    other_story_detail,
)
from lyris.coins.errors import HoldBusy
from lyris.db.repo import ANY_ACCOUNT, Repo
from lyris.llm.base import Done, LLMClient, LLMError, LLMEvent, TextDelta
from lyris.llm.errors import EMPTY_REPLY, SAVE_FAILED, UserFacingError, error_event, friendly
from lyris.llm.thought import ThoughtStreamParser, split_thought
from lyris.models import BuiltPrompt, CharacterCard, GenStats, Message, Persona, PromptLore, PromptState, Rating, Story
from lyris.prompt.builder import PromptBudget, build_prompt
from lyris.prompt.directives import extract_directives

if TYPE_CHECKING:
    from lyris.coins.wallet import CoinService, CoinTrack, Hold
    from lyris.jobs.queue import JobQueue
    from lyris.lore.service import LoreService
    from lyris.state.service import StateService

logger = logging.getLogger("lyris.chat")

EventName = Literal["user_message", "waiting", "start", "delta", "done", "error"]


@dataclass(frozen=True)
class ChatEvent:
    name: EventName
    data: dict[str, Any]


class Busy(RuntimeError):
    """Story đang sinh câu trả lời khác."""


class InvalidOperation(ValueError):
    """Thao tác không hợp lệ với trạng thái hiện tại của story (ví dụ regenerate lượt không phải lượt cuối)."""


class EmptyContent(InvalidOperation):
    """Nội dung gửi lên rỗng (dữ liệu sai, API trả 422 thay vì 409)."""


EMPTY_MESSAGE_DETAIL = "Tin nhắn trống: hãy viết lời nói, hành động hoặc ((chỉ đạo))."
EMPTY_EDIT_DETAIL = "Nội dung không được để trống."


BUSY_DETAIL = "Nhân vật đang trả lời trong story này. Hãy đợi xong hoặc bấm Dừng rồi thử lại."
SUGGEST_BUSY_DETAIL = "Đang nghĩ gợi ý cho bạn. Đợi một chút rồi thử lại nhé."
NO_REPLY_TO_SUGGEST = "Chỉ nhận gợi ý được khi nhân vật vừa trả lời xong và bạn chưa viết tiếp."


def message_out(msg: Message) -> dict[str, Any]:
    """Message dạng JSON cho API/SSE, không kèm prompt_snapshot."""
    return msg.model_dump(mode="json", exclude={"prompt_snapshot"})


@dataclass
class _Plan:
    """Mọi thứ cần để sinh một lượt trả lời, chuẩn bị xong khi đã giữ khoá story."""

    story: Story
    built: BuiltPrompt
    turn_index: int
    variant_index: int
    as_variant: bool
    prelude: list[ChatEvent] = field(default_factory=list)
    # Phase 3: state đã đưa vào prompt và lượt đầu tiên còn trong cửa sổ lịch sử (ghi vào snapshot).
    state: PromptState | None = None
    window_start_turn: int | None = None
    # Phase 4: mục thế giới đã chọn cho prompt (ghi lore_hits + snapshot sau khi lưu).
    lore: PromptLore | None = None
    # F42: giữ chỗ coin của lượt này (None: không tính coin); trừ cùng transaction lưu câu trả lời.
    hold: Hold | None = None
    save_failed: bool = False


@dataclass
class _Progress:
    raw_parts: list[str] = field(default_factory=list)
    started: float = field(default_factory=time.perf_counter)
    ttft_ms: float | None = None
    # Đã gửi cho người chơi ít nhất một `delta` có chữ (khác khoảng trắng). Chưa có (ví dụ mẩu "[Tho…" còn nằm
    # trong parser) thì dừng không trừ coin.
    shown: bool = False

    @property
    def raw(self) -> str:
        return "".join(self.raw_parts)


class ChatService:
    def __init__(
        self,
        repo: Repo,
        llm: LLMClient,
        *,
        budget: PromptBudget | None = None,
        state: StateService | None = None,
        jobs: JobQueue | None = None,
        lore: LoreService | None = None,
        gate: GenerationGate | None = None,
        coins: CoinService | None = None,
    ) -> None:
        self._repo = repo
        # F42: ví coin. None (test cũ dựng ChatService bằng tay) = không tính coin.
        self._coins = coins
        # Phase 4b: cổng sinh chung của cả máy (app truyền vào, dùng chung với chat thử / viết nháp).
        self.gate = gate or GenerationGate()
        self._llm = llm
        self._budget = budget or PromptBudget()
        self._state = state
        self._jobs = jobs
        # Phase 4: sổ thế giới. None (test cũ dựng ChatService bằng tay) = đúng đường Phase 3.
        self._lore = lore
        self._locks: dict[int, asyncio.Lock] = {}
        self._suggesting: set[int] = set()  # story đang giữ khoá để nghĩ gợi ý (Phase 3b)
        self.suggester: Callable[..., Awaitable[list[str]]] | None = None  # test thay bằng bản giả

    # ------------------------------------------------------------------ khoá

    def _lock(self, story_id: int) -> asyncio.Lock:
        lock = self._locks.get(story_id)
        if lock is None:
            lock = self._locks[story_id] = asyncio.Lock()
        return lock

    def is_busy(self, story_id: int) -> bool:
        lock = self._locks.get(story_id)
        return lock is not None and lock.locked()

    def _busy_detail(self, story_id: int) -> str:
        return SUGGEST_BUSY_DETAIL if story_id in self._suggesting else BUSY_DETAIL

    def ensure_idle(self, story_id: int) -> None:
        """Busy (409) nếu story đang sinh câu trả lời hoặc đang nghĩ gợi ý."""
        if self.is_busy(story_id):
            raise Busy(self._busy_detail(story_id))

    _ensure_idle = ensure_idle

    # ------------------------------------------------------------------ sinh câu trả lời

    def send(self, story_id: int, text: str, *, coin_track: CoinTrack | None = None) -> AsyncIterator[ChatEvent]:
        """Lưu lượt người chơi (lượt mới) rồi stream câu trả lời của nhân vật."""
        return self._run(lambda: story_id, lambda story: self._prepare_send(story, text), "send", coin_track)

    def respond(self, story_id: int, *, coin_track: CoinTrack | None = None) -> AsyncIterator[ChatEvent]:
        """Trả lời message người chơi cuối cùng (thử lại sau lỗi hoặc sau khi dừng)."""
        return self._run(lambda: story_id, self._prepare_respond, "retry", coin_track)

    def regenerate(self, message_id: int, *, coin_track: CoinTrack | None = None) -> AsyncIterator[ChatEvent]:
        """Sinh variant mới cho lượt AI cuối."""
        return self._run(
            lambda: self._repo.get_message(message_id, account_id=ANY_ACCOUNT).story_id,
            lambda story: self._prepare_regenerate(story, message_id),
            "regenerate",
            coin_track,
        )

    def _context(self, story: Story) -> tuple[CharacterCard, Persona]:
        # Việc nền / lượt sinh: route đã kiểm story thuộc tài khoản; card và persona luôn cùng tài khoản (§2.2).
        return (
            self._repo.get_card(story.card_id, account_id=ANY_ACCOUNT),
            self._repo.get_persona(story.persona_id, account_id=ANY_ACCOUNT),
        )

    async def _build(
        self, story: Story, history: list[Message]
    ) -> tuple[BuiltPrompt, PromptState | None, int | None, PromptLore | None]:
        """Dựng prompt (kèm PromptState nếu có StateService, PromptLore nếu có LoreService).
        Trả (prompt, state, lượt đầu trong cửa sổ, lore)."""
        card, persona = self._context(story)
        state: PromptState | None = None
        if self._state is not None and history:
            try:
                state = await self._state.prompt_state(story, card, persona, history)
            except Exception:  # state hỏng không được chặn lượt chat
                logger.exception("Không dựng được state cho prompt (story %s)", story.id)
                state = None
        # Phase 4: prompt_lore tự bắt lỗi (log rồi None), không bao giờ chặn lượt chat.
        lore = self._lore.prompt_lore(story, card, persona, history) if self._lore is not None else None
        try:
            built = build_prompt(card, persona, story, history, budget=self._budget, state=state, lore=lore)
        except ValueError as exc:
            raise InvalidOperation(f"Không dựng được prompt: {exc}") from exc
        dropped = built.dropped_turns
        window_start = history[dropped].turn_index if 0 <= dropped < len(history) else None
        return built, state, window_start, lore

    async def _prepare_send(self, story: Story, text: str) -> _Plan:
        assert story.id is not None
        visible, directive = extract_directives(text)
        if not visible and directive is None:
            raise EmptyContent(EMPTY_MESSAGE_DETAIL)
        turn_index = self._repo.next_turn_index(story.id)
        pending = Message(
            story_id=story.id,
            turn_index=turn_index,
            role="user",
            mode=story.mode,
            raw_content=text.strip(),
            visible_content=visible,
            directive=directive,
        )
        # Dựng prompt trước khi ghi: nếu dựng lỗi thì lượt người chơi không bị lưu dở.
        built, state, window_start, lore = await self._build(story, [*self._repo.active_messages(story.id), pending])
        user_msg = self._repo.insert_message(pending)
        return _Plan(
            story=story,
            built=built,
            turn_index=turn_index + 1,
            variant_index=0,
            as_variant=False,
            prelude=[ChatEvent("user_message", {"message": message_out(user_msg)})],
            state=state,
            window_start_turn=window_start,
            lore=lore,
        )

    async def _prepare_respond(self, story: Story) -> _Plan:
        assert story.id is not None
        history = self._repo.active_messages(story.id)
        if not history or history[-1].role != "user":
            raise InvalidOperation("Không có lượt nào của người chơi đang chờ nhân vật trả lời.")
        built, state, window_start, lore = await self._build(story, history)
        return _Plan(
            story=story,
            built=built,
            turn_index=self._repo.next_turn_index(story.id),
            variant_index=0,
            as_variant=False,
            state=state,
            window_start_turn=window_start,
            lore=lore,
        )

    async def _prepare_regenerate(self, story: Story, message_id: int) -> _Plan:
        assert story.id is not None
        msg = self._repo.get_message(message_id, account_id=ANY_ACCOUNT)
        if msg.role != "assistant":
            raise InvalidOperation("Chỉ tạo lại được lượt của nhân vật AI.")
        if msg.turn_index != self._repo.last_turn_index(story.id):
            raise InvalidOperation("Chỉ tạo lại được lượt cuối cùng.")
        if msg.turn_index == 0:
            raise InvalidOperation("Không tạo lại được lời mở đầu.")
        history = [m for m in self._repo.active_messages(story.id) if m.turn_index < msg.turn_index]
        if not history or history[-1].role != "user" or history[-1].turn_index != msg.turn_index - 1:
            raise InvalidOperation("Lượt ngay trước lượt này phải là của người chơi.")
        built, state, window_start, lore = await self._build(story, history)
        variants = self._repo.list_variants(story.id, msg.turn_index)
        return _Plan(
            story=story,
            built=built,
            turn_index=msg.turn_index,
            variant_index=max(v.variant_index for v in variants) + 1,
            as_variant=True,
            state=state,
            window_start_turn=window_start,
            lore=lore,
        )

    def _persist(self, plan: _Plan, raw: str, stats: GenStats, *, charge: bool = True) -> Message:
        """Ghi message assistant (đồng bộ; an toàn để gọi trong finally khi bị huỷ)."""
        assert plan.story.id is not None
        visible, thought = split_thought(raw)
        msg = Message(
            story_id=plan.story.id,
            turn_index=plan.turn_index,
            role="assistant",
            mode=plan.story.mode,
            raw_content=raw,
            visible_content=visible,
            thought=thought,
            model_output=raw,
            prompt_snapshot=self._snapshot(plan),
            model_name=plan.story.model_name,
            gen_stats=stats,
        )
        # F42: câu trả lời và dòng sổ trừ coin trong CÙNG một transaction. `charge` không bao giờ raise (lỗi coin
        # chỉ ghi log), nên không bao giờ làm mất câu trả lời.
        with self._repo.transaction():
            saved = self._repo.add_variant(msg) if plan.as_variant else self._repo.insert_message(msg)
            if charge and plan.hold is not None and self._coins is not None:
                self._coins.charge(plan.hold, saved.id)
        if self._lore is not None and plan.lore is not None and saved.id is not None:
            # Phase 4: lượt này đã dùng / đã gợi ra mục nào (cả lượt bị ngắt). Lỗi thì log, lượt vẫn lưu.
            self._lore.record_hits(plan.story.id, saved.id, plan.lore)
        if self._jobs is not None:
            try:
                if plan.as_variant:
                    self._jobs.messages_changed(plan.story.id)  # job của variant cũ thành thừa
                if not stats.aborted:
                    self._jobs.turn_saved(saved)
            except Exception:  # hàng đợi lỗi không được làm mất lượt vừa lưu
                logger.exception("Không xếp được job nền cho message %s", saved.id)
        return saved

    @staticmethod
    def _snapshot(plan: _Plan) -> dict[str, Any]:
        """Prompt snapshot: BuiltPrompt + `state` (PromptState đã dùng, Phase 5 train đúng định dạng)
        + `window_start_turn` (lượt đầu còn trong cửa sổ; worker dùng để quyết định tóm tắt)."""
        snapshot = plan.built.model_dump(mode="json")
        state: dict[str, Any] | None = None
        if plan.state is not None:
            # Chỉ lưu tóm tắt thật sự đã vào khối C (Phase 3b: builder chọn một mốc trong `summaries`).
            state = plan.state.model_dump(mode="json", exclude={"summaries"})
            if plan.state.summaries:
                used = plan.built.summary_upto_turn
                state["summary"] = next((p.text for p in plan.state.summaries if p.upto_turn == used), None)
        snapshot["state"] = state
        snapshot["window_start_turn"] = plan.window_start_turn
        if plan.lore is not None:
            # Phase 4: mục khớp nhưng không gửi (chỉ người chơi biết, người khác biết, hết chỗ), để dữ liệu
            # train dựng lại đúng prompt. Mục đã gửi nằm trong `lore_used` của BuiltPrompt.
            snapshot["lore_unsent"] = list(plan.lore.unsent_ids)
        return snapshot

    def reserve(self, story: Story) -> Ticket:
        """Phase 4b: vé của cổng sinh cho một lượt trên `story`. Tài khoản đang sinh ở story khác -> Busy."""
        assert story.id is not None
        account_id = self._repo.story_account_id(story.id)
        try:
            name = self._repo.get_card(story.card_id, account_id=ANY_ACCOUNT).name
        except Exception:
            name = ""
        try:
            return self.gate.reserve(account_id, other_story_detail(name))
        except AccountBusy as exc:
            raise Busy(str(exc)) from exc

    def _hold(self, story: Story, kind: str, track: CoinTrack | None) -> Hold | None:
        """F42: giữ chỗ coin cho lượt này (None: không tính coin). `CoinsRequired` lan ra (API: 402)."""
        if self._coins is None:
            return None
        assert story.id is not None
        account_id = self._repo.story_account_id(story.id)
        try:
            return self._coins.hold(account_id, story=story, mode=story.mode, kind=kind, track=track)
        except HoldBusy as exc:
            raise Busy(OTHER_WORK_DETAIL) from exc

    def _release(self, hold: Hold | None, reason: str) -> None:
        if hold is None or self._coins is None:
            return
        if reason == "save_failed":
            # Lưu lỗi: transaction có `charge` có thể đã bị cuộn lại sau khi `hold.settled` được đặt trong bộ nhớ.
            # Nhả theo DB (chỉ khi còn `held`), không tin cờ trong bộ nhớ.
            self._coins.release(hold, reason, force=True)
        elif not hold.settled:
            self._coins.release(hold, reason)

    async def _run(
        self,
        resolve_story_id: Callable[[], int],
        prepare: Callable[[Story], Awaitable[_Plan]],
        kind: str = "send",
        coin_track: CoinTrack | None = None,
    ) -> AsyncIterator[ChatEvent]:
        story_id = resolve_story_id()
        story = self._repo.get_story(story_id, account_id=ANY_ACCOUNT)
        lock = self._lock(story_id)
        if lock.locked():
            raise Busy(self._busy_detail(story_id))
        # Phase 4b: giữ chỗ ở cổng sinh trước khi ghi gì (409 nếu tài khoản đang sinh ở story khác).
        ticket = self.reserve(story)
        # Khoá đang rảnh nên acquire() trả về ngay, không nhường event loop: kiểm tra + giữ khoá là nguyên tử.
        try:
            await lock.acquire()
        except BaseException:
            ticket.release()
            raise
        # Báo worker nền ngay từ đầu (trước cả bước tìm ký ức) để model được nhường cho lượt chat.
        if self._jobs is not None:
            self._jobs.generation_started(story_id)
        hold: Hold | None = None
        # Lý do nhả giữ chỗ nếu lượt kết thúc mà không có câu trả lời nào được lưu (mặc định: bị ngắt).
        release_reason = "cancelled"
        try:
            # F42: giữ chỗ coin TRƯỚC khi lưu lượt người chơi (402 trước byte SSE đầu tiên, không lưu gì).
            hold = self._hold(story, kind, coin_track)
            try:
                plan = await prepare(story)
            except BaseException:
                release_reason = "invalid"
                raise
            plan.hold = hold
            for event in plan.prelude:
                yield event
            if not ticket.ready:
                # Hết chỗ: báo "đang chờ" rồi chờ theo thứ tự đến (§5.5). Tin người chơi đã lưu ở prepare.
                yield ChatEvent("waiting", {})
                try:
                    await ticket.wait()
                except GateTimeout:
                    release_reason = "queue_timeout"
                    yield ChatEvent("error", {"detail": WAIT_TIMEOUT_DETAIL, "technical": None})
                    return
            generation = self._generate(plan)
            try:
                async for event in generation:
                    if event.name == "error":
                        release_reason = _release_reason(event.data.get("detail"), plan.save_failed)
                    yield event
            finally:
                # Nếu chính generator này bị đóng khi đang dừng ở yield, generator con vẫn treo ở
                # yield của nó: đóng ngay để phần dở được lưu trước khi nhả khoá.
                with anyio.CancelScope(shield=True):
                    await generation.aclose()
                if plan.save_failed:
                    release_reason = "save_failed"
        finally:
            # Không có chữ được lưu (lỗi, rỗng, lưu lỗi, chờ quá lâu, dừng trước chữ đầu tiên): không mất coin.
            self._release(hold, release_reason)
            ticket.release()
            lock.release()
            if self._jobs is not None:
                self._jobs.generation_finished(story_id)

    async def _generate(self, plan: _Plan) -> AsyncIterator[ChatEvent]:
        """Stream một lượt trả lời. Chỉ được gọi từ `_run` (đang giữ khoá)."""
        yield ChatEvent("start", {"turn_index": plan.turn_index, "variant_index": plan.variant_index})

        progress = _Progress()
        parser = ThoughtStreamParser()
        stats: GenStats | None = None
        finished = False  # đã ghi xong, hoặc đã báo lỗi: không lưu phần dở nữa
        stream: AsyncIterator[LLMEvent] | None = None
        try:
            error: dict[str, Any] | None = None
            try:
                stream = self._llm.chat_stream(
                    plan.story.model_name,
                    plan.built.messages,
                    stop=plan.built.stop,
                    options=plan.built.options,
                )
                async for event in stream:
                    if isinstance(event, TextDelta):
                        if not event.text:
                            continue
                        if progress.ttft_ms is None:
                            progress.ttft_ms = (time.perf_counter() - progress.started) * 1000
                        progress.raw_parts.append(event.text)
                        for parsed in parser.feed(event.text):
                            if parsed.text.strip():
                                progress.shown = True
                            yield ChatEvent("delta", {"kind": parsed.kind, "text": parsed.text})
                    elif isinstance(event, Done):
                        stats = event.stats
            except LLMError as exc:
                error = error_event(exc, "reply")
            except Exception as exc:  # lỗi không lường trước từ client LLM: vẫn báo cho người chơi
                logger.exception("Lỗi không mong đợi khi stream câu trả lời")
                error = error_event(exc, "reply")

            if error is not None:
                finished = True
                yield ChatEvent("error", error)
                return

            for parsed in parser.flush():
                if parsed.text.strip():
                    progress.shown = True
                yield ChatEvent("delta", {"kind": parsed.kind, "text": parsed.text})

            raw = progress.raw.strip()
            if not raw:
                finished = True
                yield ChatEvent(
                    "error",
                    {"detail": EMPTY_REPLY, "technical": "Model không trả về nội dung nào (phản hồi rỗng)."},
                )
                return

            if stats is None:
                stats = GenStats(
                    ttft_ms=progress.ttft_ms,
                    total_ms=(time.perf_counter() - progress.started) * 1000,
                )
            try:
                saved = self._persist(plan, raw, stats)
            except Exception as exc:  # gồm cả sqlite3.Error (ví dụ "database is locked")
                finished = True
                plan.save_failed = True
                logger.exception("Không lưu được câu trả lời")
                yield ChatEvent("error", {"detail": SAVE_FAILED, "technical": f"{type(exc).__name__}: {exc}"})
                return
            finished = True
            yield ChatEvent("done", {"message": message_out(saved)})
        finally:
            if not finished:
                # Bị ngắt giữa chừng (client đóng kết nối → generator bị đóng hoặc task bị huỷ).
                # Ghi đồng bộ, không await, để chắc chắn chạy được kể cả khi đang bị huỷ.
                self._save_aborted(plan, progress)
            if stream is not None:
                await _close_quietly(stream)

    def _save_aborted(self, plan: _Plan, progress: _Progress) -> None:
        raw = progress.raw.strip()
        if not raw:
            return
        stats = GenStats(
            ttft_ms=progress.ttft_ms,
            total_ms=(time.perf_counter() - progress.started) * 1000,
            aborted=True,
        )
        try:
            # Người chơi chưa thấy chữ nào: vẫn lưu phần dở, nhưng không trừ (`_run` nhả với lý do `cancelled`).
            self._persist(plan, raw, stats, charge=progress.shown)
        except Exception:
            plan.save_failed = True
            logger.exception("Không lưu được phần câu trả lời bị ngắt giữa chừng")

    # ------------------------------------------------------------------ gợi ý theo yêu cầu (Phase 3b)

    async def suggest(self, story_id: int) -> list[str]:
        """Nghĩ 1-3 gợi ý cho lượt tiếp của người chơi và lưu vào message cuối (thay gợi ý cũ).

        Như một lượt sinh: giữ khoá story (đang sinh câu trả lời -> Busy; trong lúc nghĩ gợi ý, gửi/sửa/xoá
        -> Busy với câu riêng) và báo worker nhường model. Message active cuối phải là của nhân vật, không
        thì InvalidOperation (409). Lỗi model -> UserFacingError (502, câu dễ hiểu + chi tiết kỹ thuật).
        """
        story = self._repo.get_story(story_id, account_id=ANY_ACCOUNT)
        lock = self._lock(story_id)
        if lock.locked():
            raise Busy(self._busy_detail(story_id))
        ticket = self.reserve(story)  # Phase 4b: cổng sinh chung (409 nếu tài khoản đang sinh ở chỗ khác)
        try:
            await lock.acquire()
        except BaseException:
            ticket.release()
            raise
        self._suggesting.add(story_id)
        if self._jobs is not None:
            self._jobs.generation_started(story_id)
        try:
            try:
                await ticket.wait()
            except GateTimeout as exc:
                raise Busy(str(exc)) from exc
            history = self._repo.active_messages(story_id)
            if not history or history[-1].role != "assistant" or history[-1].id is None:
                raise InvalidOperation(NO_REPLY_TO_SUGGEST)
            last = history[-1]
            card, persona = self._context(story)
            scene = None
            summary = None
            previous: list[str] = []
            if self._state is not None:
                try:
                    folded = self._state.fold(story, card=card)
                    scene = folded.scene if (folded.scene.location or folded.scene.time) else None
                    summary = folded.summary.text if folded.summary is not None else None
                    previous = list(folded.suggestions)
                except Exception:  # state hỏng không được chặn gợi ý
                    logger.exception("Không đọc được state cho gợi ý (story %s)", story_id)
            suggester = self.suggester or _default_suggester
            try:
                items = await suggester(
                    self._llm,
                    model=story.model_name,
                    num_ctx=self._budget.num_ctx,
                    card=card,
                    persona=persona,
                    story=story,
                    history=history,
                    scene=scene,
                    summary=summary,
                    avoid=previous,
                )
            except LLMError as exc:
                detail, technical = friendly(exc, "suggest")
                raise UserFacingError(detail, status=502, technical=technical) from exc
            except (InvalidOperation, Busy):
                raise
            except Exception as exc:  # lỗi không lường trước: vẫn trả câu dễ hiểu
                logger.exception("Lỗi không mong đợi khi nghĩ gợi ý")
                detail, technical = friendly(exc, "suggest")
                raise UserFacingError(detail, status=502, technical=technical) from exc
            if not self._repo.replace_suggestions(last.id, items):
                raise InvalidOperation(NO_REPLY_TO_SUGGEST)
            return items
        finally:
            ticket.release()
            self._suggesting.discard(story_id)
            lock.release()
            if self._jobs is not None:
                self._jobs.generation_finished(story_id)

    # ------------------------------------------------------------------ thao tác khác trên message

    def _last_turn_assistant(self, message_id: int) -> Message:
        msg = self._repo.get_message(message_id, account_id=ANY_ACCOUNT)
        if msg.role != "assistant":
            raise InvalidOperation("Chỉ lượt của nhân vật AI mới có các phiên bản để lật.")
        if msg.turn_index != self._repo.last_turn_index(msg.story_id):
            raise InvalidOperation("Chỉ lật được phiên bản của lượt cuối cùng.")
        return msg

    def select_variant(self, message_id: int, variant_index: int) -> Message:
        msg = self._last_turn_assistant(message_id)
        self._ensure_idle(msg.story_id)
        selected = self._repo.select_variant(msg.story_id, msg.turn_index, variant_index)
        if self._jobs is not None:
            self._jobs.messages_changed(msg.story_id)
            self._jobs.ensure_extracted(selected)
        return selected

    def edit_message(self, message_id: int, content: str) -> Message:
        """Sửa nội dung; assistant: tách lại Thought; user: tách lại ((chỉ đạo))."""
        msg = self._repo.get_message(message_id, account_id=ANY_ACCOUNT)
        self._ensure_idle(msg.story_id)
        raw = content.strip()
        if msg.role == "assistant":
            visible, thought = split_thought(raw)
            if not visible and thought is None:
                raise EmptyContent(EMPTY_EDIT_DETAIL)
            edited = self._repo.edit_message(
                message_id, raw_content=raw, visible_content=visible, thought=thought, directive=None
            )
            if self._jobs is not None and edited.raw_content != msg.raw_content:
                # Nội dung đổi: state và ký ức của lượt này phải trích xuất lại từ nội dung mới.
                self._jobs.message_reset(edited)
            return edited
        visible, directive = extract_directives(raw)
        if not visible and directive is None:
            raise EmptyContent(EMPTY_EDIT_DETAIL)
        edited = self._repo.edit_message(
            message_id, raw_content=raw, visible_content=visible, thought=None, directive=directive
        )
        if self._jobs is not None and edited.raw_content != msg.raw_content:
            self._jobs.messages_changed(msg.story_id)  # lịch sử đổi: worker prefill lại phần đầu prompt mới
        return edited

    def delete_from(self, message_id: int) -> tuple[int, list[Message]]:
        """Xoá lượt chứa message này và mọi lượt sau. Trả (số message đã xoá, message active còn lại)."""
        msg = self._repo.get_message(message_id, account_id=ANY_ACCOUNT)
        self._ensure_idle(msg.story_id)
        deleted = self._repo.truncate_from(msg.story_id, msg.turn_index)
        if self._jobs is not None:
            self._jobs.messages_changed(msg.story_id)  # job của message đã xoá đi theo CASCADE
        return deleted, self._repo.active_messages(msg.story_id)

    def set_feedback(self, message_id: int, rating: Rating | None, note: str | None = None) -> Message:
        msg = self._repo.get_message(message_id, account_id=ANY_ACCOUNT)
        if msg.role != "assistant":
            raise InvalidOperation("Chỉ đánh giá được lượt của nhân vật AI.")
        return self._repo.set_feedback(message_id, rating, note)


def _release_reason(detail: Any, save_failed: bool) -> str:
    """Lý do nhả giữ chỗ coin theo sự kiện `error` của lượt (docs/coins.md §3.2)."""
    if save_failed or detail == SAVE_FAILED:
        return "save_failed"
    if detail == EMPTY_REPLY:
        return "empty"
    if detail == WAIT_TIMEOUT_DETAIL:
        return "queue_timeout"
    return "error"


async def _default_suggester(llm: Any, **kwargs: Any) -> list[str]:
    from lyris.state.suggest import suggest_replies

    return await suggest_replies(llm, **kwargs)


async def _close_quietly(stream: AsyncIterator[Any]) -> None:
    """Đóng generator của LLM (huỷ request HTTP), được che khỏi việc huỷ đang diễn ra."""
    aclose = getattr(stream, "aclose", None)
    if aclose is None:
        return
    with anyio.CancelScope(shield=True):
        try:
            await aclose()
        except Exception:
            logger.exception("Lỗi khi đóng stream của model")


__all__ = [
    "BUSY_DETAIL",
    "NO_REPLY_TO_SUGGEST",
    "SUGGEST_BUSY_DETAIL",
    "Busy",
    "ChatEvent",
    "ChatService",
    "EmptyContent",
    "InvalidOperation",
    "message_out",
]
