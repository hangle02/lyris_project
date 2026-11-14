"""Worker chạy job nền trong tiến trình app (docs/phase3.md §4).

- Một asyncio task (khởi động trong lifespan), xử lý lần lượt từng job theo FIFO.
- Có lượt chat đang stream thì không bắt đầu job mới; job đang chạy bị huỷ (huỷ luôn request HTTP tới
  Ollama) và quay về `queued`, không tính vào `attempts`.
- Job của message không còn active (regenerate, lật variant, xoá) -> `cancelled`, không gọi model.
- Model trả JSON hỏng: thử lại 1 lần. Lỗi kết nối: `failed` kèm thông báo. Worker không bao giờ chết.
- Hàng đợi rỗng sau khi chạy job của một story (và `prefill` bật): gửi trước phần đầu prompt chat lượt sau
  để Ollama giữ sẵn trong cache (`Worker.prefill`, docs/phase3.md §10.6). Không phải job trong DB.

Phần gọi model được tiêm vào (`extractor`, `summarizer`, `embedder`) để test dùng bản giả; mặc định
import muộn `lyris.state.extract.extract_turn`, `lyris.memory.summarize.summarize`, `llm.embed`.
Test chạy worker một cách tất định bằng `run_until_idle()` thay vì `start()`.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import re
import unicodedata
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Literal, TypeVar

from lyris.db.repo import ANY_ACCOUNT, Job, NewMemory, NotFound, Repo
from lyris.jobs.queue import JobQueue
from lyris.memory.retrieval import pack_vector, unpack_vector
from lyris.models import CharacterCard, ExtractionResult, Message, Persona, Story
from lyris.prompt.builder import PromptBudget, window_boundaries
from lyris.prompt.tokens import estimate_tokens
from lyris.state.service import StateService, window_start_turn

logger = logging.getLogger("lyris.jobs")

T = TypeVar("T")

Extractor = Callable[..., Awaitable[ExtractionResult]]
Summarizer = Callable[..., Awaitable[str]]
Embedder = Callable[[str, list[str]], Awaitable[list[list[float]]]]

MAX_ATTEMPTS = 2  # lần đầu + thử lại 1 lần khi model trả kết quả hỏng
POLL_INTERVAL = 5.0
SUMMARY_CHUNK_TOKENS = 3000  # mỗi lời gọi tóm tắt nhận tối đa chừng này token lượt cũ
EMBED_BATCH = 32
ERROR_CHARS = 500
MAX_FACTS = 3

StopReason = Literal["preempt", "stale", "stop"]


@dataclass
class _Outcome:
    status: Literal["done", "failed", "cancelled"]
    attempts: int = 0
    error: str | None = None


class _Cancelled(Exception):
    """Job không còn ý nghĩa (message đã xoá / hết active)."""


class _Failed(Exception):
    def __init__(self, message: str, attempts: int) -> None:
        super().__init__(message)
        self.attempts = attempts


@dataclass
class _InFlight:
    job: Job
    task: asyncio.Task[_Outcome]
    reason: StopReason | None = None


def pack_embedding(vector: list[float]) -> bytes:
    """Vector -> BLOB float32 little-endian (cột memories.embedding); cùng định dạng retrieval đọc."""
    return pack_vector(vector)


def unpack_embedding(blob: bytes) -> list[float]:
    return unpack_vector(blob)


def _is_connection_error(exc: BaseException) -> bool:
    """Lỗi kết nối/timeout tới Ollama (không thử lại): tìm trong chuỗi __cause__/__context__."""
    import httpx

    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, (httpx.TransportError, ConnectionError, TimeoutError)):
            return True
        current = current.__cause__ or current.__context__
    return False


_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)


def normalize_fact(text: str) -> str:
    """So khớp fact trùng: NFC, chữ thường, bỏ dấu câu, gộp khoảng trắng (giữ dấu tiếng Việt)."""
    t = unicodedata.normalize("NFC", text).casefold()
    return " ".join(_PUNCT.sub(" ", t).split())


def _short(exc: BaseException) -> str:
    text = str(exc).strip() or type(exc).__name__
    return text[:ERROR_CHARS]


def extraction_rows(
    message: Message, result: ExtractionResult, known_facts: list[str]
) -> tuple[list[tuple[Any, dict[str, Any]]], list[NewMemory]]:
    """ExtractionResult -> (event, ký ức/fact) để ghi bằng `Repo.replace_extraction`.

    Fact trùng `known_facts` (sau khi chuẩn hoá) bị bỏ; tối đa MAX_FACTS fact. Phase 3b: không ghi gợi ý
    (gợi ý chỉ sinh khi người chơi yêu cầu); lời mở đầu (lượt 0) không có event `relationship_delta`.
    Dùng chung cho worker và scripts/make_demo_db.py (state demo cùng định dạng thật).
    """
    assert message.id is not None
    events: list[tuple[Any, dict[str, Any]]] = []
    if message.turn_index > 0:
        events.append(("relationship_delta", result.relationship_delta.model_dump(mode="json")))
    location = (result.scene.location or "").strip() or None
    time = (result.scene.time or "").strip() or None
    if location or time:
        events.append(("scene", {"location": location, "time": time}))
    memories: list[NewMemory] = []
    if result.memory and result.memory.strip():
        memories.append(NewMemory(kind="memory", text=result.memory.strip(), importance=result.memory_importance))
    known = {normalize_fact(text) for text in known_facts}
    for fact in result.facts:
        key = normalize_fact(fact.text)
        if not key or key in known:
            continue
        known.add(key)
        memories.append(NewMemory(kind="fact", text=fact.text.strip(), subject=fact.subject.strip() or None))
        if sum(1 for m in memories if m.kind == "fact") >= MAX_FACTS:
            break
    return events, memories


async def _default_extractor(llm: Any, **kwargs: Any) -> ExtractionResult:
    from lyris.state.extract import extract_turn

    return await extract_turn(llm, **kwargs)


async def _default_summarizer(llm: Any, **kwargs: Any) -> str:
    from lyris.memory.summarize import summarize

    return await summarize(llm, **kwargs)


class Worker:
    def __init__(
        self,
        repo: Repo,
        queue: JobQueue,
        state: StateService,
        llm: Any,
        *,
        budget: PromptBudget | None = None,
        extract_model: str | None = None,
        extractor: Extractor | None = None,
        summarizer: Summarizer | None = None,
        embedder: Embedder | None = None,
        poll_interval: float = POLL_INTERVAL,
        prefill: bool = False,
    ) -> None:
        self._repo = repo
        self._queue = queue
        self._state = state
        self._llm = llm
        self._budget = budget or PromptBudget()
        self.extract_model = (extract_model or "").strip() or None
        self.extractor: Extractor = extractor or _default_extractor
        self.summarizer: Summarizer = summarizer or _default_summarizer
        self.embedder: Embedder | None = embedder
        self._poll = poll_interval
        self._task: asyncio.Task[None] | None = None
        self._current: _InFlight | None = None
        # Gửi trước phần đầu prompt chat lượt sau khi hàng đợi rảnh (§10.6). Tắt mặc định: app chỉ bật
        # với Ollama thật (LLM giả trong test không có cache prompt).
        self.prefill_enabled = prefill
        # Cache prompt của Ollama chỉ giữ một prompt, nên chỉ prefill MỘT story: story người chơi đang chơi
        # (lượt chat / gợi ý gần nhất). Prefill story khác sẽ đẩy cache của story đó ra.
        self._focus: int | None = None
        self._prefill_due: int | None = None  # story chờ prefill khi hàng đợi rảnh
        self._prefill_task: asyncio.Task[bool] | None = None
        self._prefill_story: int | None = None  # story của prefill đang chạy
        queue.attach(self)

    # ------------------------------------------------------------------ vòng đời

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    @property
    def current_job(self) -> Job | None:
        return None if self._current is None else self._current.job

    def recover(self) -> int:
        """Job `running` còn sót từ lần chạy trước -> `queued`."""
        count = self._repo.reset_running_jobs()
        if count:
            logger.info("Đưa lại %d job đang chạy dở vào hàng đợi", count)
        return count

    async def start(self) -> None:
        if self.running:
            return
        self.recover()
        self._task = asyncio.create_task(self._loop(), name="lyris-job-worker")

    async def stop(self) -> None:
        task, self._task = self._task, None
        if task is None:
            return
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    async def _loop(self) -> None:
        while True:
            try:
                await self._queue.wait_idle()
                self._queue.clear_wake()
                job = self._repo.claim_next_job()
                if job is None:
                    story_id, self._prefill_due = self._prefill_due, None
                    if story_id is not None:
                        await self.prefill(story_id)
                        continue
                    await self._queue.wait_for_work(self._poll)
                    continue
                await self._execute(job)
                if job.story_id is not None:
                    # Job (của story nào cũng vậy) có thể đã đẩy prompt chat ra khỏi cache: prefill lại story
                    # đang chơi; chưa có lượt chat nào từ lúc chạy app thì story của job.
                    self._mark_prefill(self._focus if self._focus is not None else job.story_id)
            except asyncio.CancelledError:
                raise
            except Exception:  # worker không bao giờ chết
                logger.exception("Worker gặp lỗi không mong đợi; chạy tiếp sau 1 giây")
                await asyncio.sleep(1.0)

    async def run_once(self) -> Job | None:
        """Chạy đúng một job (nếu có và không có lượt chat đang stream). Trả job đã chạy."""
        if self._queue.streaming:
            return None
        self._queue.clear_wake()
        job = self._repo.claim_next_job()
        if job is None:
            return None
        await self._execute(job)
        return job

    async def run_until_idle(self, max_jobs: int = 1000) -> int:
        """Chạy hết hàng đợi (dừng khi rỗng hoặc có lượt chat). Dành cho test và script."""
        count = 0
        while count < max_jobs and await self.run_once() is not None:
            count += 1
        return count

    # ------------------------------------------------------------------ tín hiệu từ hàng đợi

    def on_generation_started(self, story_id: int) -> None:
        self._focus = story_id
        self._interrupt("preempt")
        self._cancel_prefill()  # lượt chat / gợi ý tự đọc prompt; prefill dở không còn ích

    def on_generation_finished(self, story_id: int) -> None:
        # Lượt chat đã xếp extract trước khi tới đây (prefill chạy sau job đó). Gợi ý thì không xếp job nào
        # nhưng đã gọi model chat với prompt khác, đẩy phần đã prefill ra khỏi cache: prefill lại.
        self._mark_prefill(story_id)

    def on_story_focused(self, story_id: int) -> None:
        """Người chơi vừa tạo story `story_id` (và mở nó ngay): nó thành story đang chơi. Không có bước này thì
        prefill sau job lời mở đầu vẫn là của story chơi trước đó, và lượt đầu của story mới đọc cả prompt
        (~29 giây với gemma4:12b). Prefill đang chạy / đang chờ của story khác hết ích: huỷ."""
        self._focus = story_id
        if self._prefill_story not in (None, story_id):
            self._cancel_prefill()
        self._mark_prefill(story_id)

    def on_messages_changed(self, story_id: int) -> None:
        exists = self._repo.story_exists(story_id)
        # Lịch sử đổi (xoá, lật variant, sửa): phần đầu đang gửi trước đã cũ.
        self._cancel_prefill(story_id)
        if not exists:
            if self._focus == story_id:
                self._focus = None
            if self._prefill_due == story_id:
                self._prefill_due = None
        elif self._focus in (None, story_id):
            self._mark_prefill(story_id)
        current = self._current
        if current is None or current.job.story_id != story_id:
            return
        # Story đã xoá (xoá story, hoặc xoá card/persona kèm story): job nào cũng hết nghĩa, kể cả
        # embed (không gắn message).
        if not exists:
            self._interrupt("stale")
            return
        if current.job.message_id is not None and not self._repo.message_is_active(current.job.message_id):
            self._interrupt("stale")

    def on_message_reset(self, message_id: int, story_id: int) -> None:
        self._cancel_prefill(story_id)  # nội dung message đổi: phần đầu đang gửi trước đã cũ
        if self._focus in (None, story_id):
            self._mark_prefill(story_id)
        current = self._current
        if current is not None and current.job.message_id == message_id and current.job.kind == "extract":
            self._interrupt("stale")

    def on_lore_changed(self, story_ids: list[int]) -> None:
        """Phase 4: sổ thế giới của một card đổi (`story_ids` = các story của card đó). Prefill đang chạy hoặc
        đang chờ của một story trong đó được huỷ rồi hẹn lại (phần đầu prompt có thể đã đổi); story khác giữ
        nguyên. Prefill đã chạy xong (worker rảnh) mà story đang chơi thuộc card: hẹn prefill lại như
        `on_messages_changed` (phần dự phòng khối D đổi thì cửa sổ cũng đổi), và xếp tóm tắt nếu cửa sổ mới
        cần một mốc chưa có."""
        ids = set(story_ids)
        running = self._prefill_story if self._prefill_task is not None and not self._prefill_task.done() else None
        if running in ids:
            assert running is not None
            self._cancel_prefill(running)
            self._mark_prefill(running)
        elif self._prefill_due in ids:
            self._mark_prefill(self._prefill_due)  # chưa chạy: lúc chạy sẽ dựng từ sổ thế giới mới
        elif self._prefill_due is None and self._focus is not None and self._focus in ids:
            self._mark_prefill(self._focus)
        if self._focus is not None and self._focus in ids:
            try:
                self._summary_after_lore(self._focus)
            except Exception:  # chỉ để tăng tốc / đỡ hụt tóm tắt: lỗi thì để lượt sau xét lại
                logger.exception("Không xét được tóm tắt sau khi sổ thế giới đổi (story %s)", self._focus)

    def _summary_after_lore(self, story_id: int) -> None:
        """Phần dự phòng khối D đổi (thêm mục đầu tiên / xoá mục cuối) có thể dời cửa sổ của lượt sau tới mốc
        chưa được tóm tắt: xếp `summarize` ngay lúc người chơi còn ở Studio, như sau một lượt extract."""
        if not self._repo.story_exists(story_id) or self._repo.has_pending_jobs(story_id, kinds=("summarize",)):
            return
        story = self._repo.get_story(story_id, account_id=ANY_ACCOUNT)
        active = self._repo.active_messages(story_id)
        last = next((m for m in reversed(active) if m.role == "assistant" and m.id is not None), None)
        if last is None or last.id is None:
            return
        if self._state.needs_summary(story, self._summary_target(story, last, active)):
            self._queue.enqueue(story_id, "summarize", last.id)

    def _mark_prefill(self, story_id: int) -> None:
        if self.prefill_enabled:
            self._prefill_due = story_id

    def _cancel_prefill(self, story_id: int | None = None) -> None:
        """Huỷ prefill đang chạy (của `story_id`, hoặc của bất kỳ story nào khi None)."""
        task = self._prefill_task
        if task is not None and not task.done() and story_id in (None, self._prefill_story):
            task.cancel()

    def _interrupt(self, reason: StopReason) -> None:
        current = self._current
        if current is None or current.task.done():
            return
        if current.reason is None:
            current.reason = reason
        current.task.cancel()

    # ------------------------------------------------------------------ prefill (§10.6)

    async def prefill(self, story_id: int) -> bool:
        """Gửi trước cho model chat phần đầu prompt lượt sau (`StateService.next_prompt_prefix`), sinh 1
        token. Ollama (model có sliding window như gemma) chỉ khôi phục cache tại các điểm chụp: chỗ một
        request bắt đầu đọc, và cuối prompt của nó trừ vài token. Prompt chat luôn rẽ ở ghi chú F của lượt
        người chơi trước, nên không prefill thì lượt nào cũng đọc lại ~2 lượt, và lượt ngay sau khi cửa sổ
        dịch đọc lại cả prompt.

        Ưu tiên `llm.prefill_prefix` (nếu client có): văn bản raw kết thúc đúng chỗ prompt thật rẽ ra, nên
        lượt sau dùng lại gần hết prompt, kể cả lượt cửa sổ dịch. Client không có, không render được model
        này, hoặc lỗi: prefill bằng `chat_stream` như cũ (prompt kết thúc bằng generation prompt, lượt sau chỉ
        dùng lại được tới chỗ prefill bắt đầu đọc; §10.6).

        Không bao giờ raise; lượt chat bắt đầu thì bị huỷ. Trả True khi đã gửi xong.
        """
        if self._queue.streaming:
            return False
        try:
            story = self._repo.get_story(story_id, account_id=ANY_ACCOUNT)
            built = self._state.next_prompt_prefix(story)
        except NotFound:
            return False
        except Exception:
            logger.exception("Không dựng được prompt prefill (story %s)", story_id)
            return False
        if built is None:
            return False

        async def call() -> None:
            raw = getattr(self._llm, "prefill_prefix", None)
            if raw is not None:
                # Phase 4 (§6.5): lượt người chơi còn mở (phần đầu khối D) chỉ gửi được qua raw.
                extra: dict[str, Any] = {"open_last": True} if built.open_last else {}
                try:
                    if await raw(story.model_name, built.messages, options=built.options, **extra):
                        return
                except asyncio.CancelledError:
                    raise
                except Exception as exc:  # raw lỗi: thử lại bằng /api/chat
                    logger.info("Prefill raw story %s lỗi, dùng /api/chat: %s", story_id, _short(exc))
            # /api/chat không gửi được lượt còn mở (gửi lượt đã đóng thì rẽ ngay ở cuối nó): bỏ lượt đó.
            messages = built.messages[:-1] if built.open_last else built.messages
            stream = self._llm.chat_stream(story.model_name, messages, stop=built.stop, options=built.options)
            try:
                async for _ in stream:
                    pass
            finally:
                with contextlib.suppress(Exception):
                    await stream.aclose()  # type: ignore[attr-defined]

        async def run() -> bool:
            try:
                await call()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # prefill chỉ để tăng tốc: lỗi thì bỏ qua
                logger.info("Prefill story %s lỗi: %s", story_id, _short(exc))
                return False
            return True

        task = asyncio.create_task(run(), name=f"lyris-prefill-{story_id}")
        self._prefill_task = task
        self._prefill_story = story_id
        try:
            await asyncio.wait({task})
        except asyncio.CancelledError:
            task.cancel()
            with contextlib.suppress(BaseException):
                await asyncio.wait({task})
            raise
        finally:
            self._prefill_task = None
            self._prefill_story = None
        return not task.cancelled() and task.result()

    # ------------------------------------------------------------------ chạy một job

    async def _execute(self, job: Job) -> None:
        task = asyncio.create_task(self._process(job), name=f"lyris-job-{job.id}")
        inflight = _InFlight(job=job, task=task)
        self._current = inflight
        try:
            await asyncio.wait({task})
        except asyncio.CancelledError:
            # Worker bị dừng (app tắt): huỷ job, trả nó về hàng đợi cho lần chạy sau.
            inflight.reason = "stop"
            task.cancel()
            with contextlib.suppress(BaseException):
                await asyncio.wait({task})
            self._repo.requeue_job(job.id)
            raise
        finally:
            self._current = None

        if task.cancelled():
            if inflight.reason == "stale":
                self._repo.finish_job(job.id, "cancelled", error="Message không còn active")
            else:
                # Nhường cho lượt chat: về hàng đợi, attempts giữ nguyên.
                self._repo.requeue_job(job.id)
            return
        exc = task.exception()
        if exc is not None:
            logger.error("Job %s (%s) lỗi: %s", job.id, job.kind, exc, exc_info=exc)
            self._repo.finish_job(job.id, "failed", error=_short(exc), attempts=job.attempts + 1)
            return
        outcome = task.result()
        if outcome.status == "failed":
            logger.warning("Job %s (%s) thất bại: %s", job.id, job.kind, outcome.error)
        self._repo.finish_job(
            job.id, outcome.status, error=outcome.error, attempts=job.attempts + outcome.attempts
        )

    async def _process(self, job: Job) -> _Outcome:
        try:
            if job.kind == "extract":
                return await self._extract(job)
            if job.kind == "summarize":
                return await self._summarize(job)
            if job.kind == "embed":
                return await self._embed(job)
            return _Outcome("failed", error=f"Loại job lạ: {job.kind}")
        except _Cancelled as exc:
            return _Outcome("cancelled", error=str(exc) or None)
        except _Failed as exc:
            return _Outcome("failed", attempts=exc.attempts, error=_short(exc))
        except NotFound as exc:
            return _Outcome("cancelled", error=_short(exc))

    async def _with_retry(self, call: Callable[[], Awaitable[T]]) -> tuple[T, int]:
        attempts = 0
        while True:
            attempts += 1
            try:
                return await call(), attempts
            except Exception as exc:
                if _is_connection_error(exc) or attempts >= MAX_ATTEMPTS:
                    raise _Failed(_short(exc), attempts) from exc
                logger.info("Kết quả model hỏng (%s); thử lại", exc)

    # ------------------------------------------------------------------ dữ liệu chung

    def _active_message(self, job: Job) -> Message:
        if job.message_id is None:
            raise _Cancelled("Job thiếu message")
        message = self._repo.get_message(job.message_id, account_id=ANY_ACCOUNT)  # NotFound -> cancelled
        if not message.is_active:
            raise _Cancelled("Message không còn active")
        return message

    def _context(self, story_id: int) -> tuple[Story, CharacterCard, Persona]:
        story = self._repo.get_story(story_id, account_id=ANY_ACCOUNT)
        card = self._repo.get_card(story.card_id, account_id=ANY_ACCOUNT)
        return story, card, self._repo.get_persona(story.persona_id, account_id=ANY_ACCOUNT)

    def _model_for(self, story: Story) -> str:
        return self.extract_model or story.model_name

    # ------------------------------------------------------------------ extract

    async def _extract(self, job: Job) -> _Outcome:
        message = self._active_message(job)
        if message.role != "assistant" or message.turn_index < 0:
            raise _Cancelled("Chỉ trích xuất lượt của nhân vật")
        assert message.id is not None
        story, card, persona = self._context(message.story_id)
        active = self._repo.active_messages(story.id or 0)
        previous_reply = max(
            (m.turn_index for m in active if m.role == "assistant" and m.turn_index < message.turn_index),
            default=-1,
        )
        turn = [
            m for m in active if previous_reply < m.turn_index < message.turn_index and m.role == "user"
        ] + [message]
        before = self._state.fold(story, upto_turn=message.turn_index - 1, card=card)
        known_facts = [
            m.text for m in self._repo.list_memories(story.id or 0, kind="fact", limit=None) if m.message_id != message.id
        ]

        async def call() -> ExtractionResult:
            return await self.extractor(
                self._llm,
                model=self._model_for(story),
                num_ctx=self._budget.num_ctx,
                card=card,
                persona=persona,
                story=story,
                before=before.relationship,
                scene=before.scene,
                summary=before.summary.text if before.summary is not None else None,
                turn=turn,
                known_facts=known_facts,
            )

        result, attempts = await self._with_retry(call)
        if not isinstance(result, ExtractionResult):
            result = ExtractionResult.model_validate(result)
        saved = self._repo.replace_extraction(
            message.id,
            *extraction_rows(message, result, known_facts),
            story_id=message.story_id,
            turn_index=message.turn_index,
        )
        if saved is None:
            raise _Cancelled("Message không còn active")
        await self._after_extract(story, message, active, saved_any=bool(saved))
        return _Outcome("done", attempts=attempts)

    def _summary_target(self, story: Story, message: Message, active: list[Message]) -> int | None:
        history = [m for m in active if m.turn_index <= message.turn_index]
        return self._state.summary_target(story, history, window_start_turn(message, active))

    async def _after_extract(
        self, story: Story, message: Message, active: list[Message], *, saved_any: bool
    ) -> None:
        """Sau extract thành công: xếp `embed` (có ký ức mới và Ollama có embed model) và `summarize`
        (tóm tắt chưa phủ tới mốc khúc cần thiết, xem `StateService.summary_target`)."""
        assert story.id is not None and message.id is not None
        if saved_any and await self._state.active_embed_model() is not None:
            self._queue.enqueue(story.id, "embed", None)
        # Đã có job tóm tắt đang chờ (vd. rebuild xếp sau cùng) thì thôi: lượt sau sẽ xét lại nếu còn thiếu.
        if self._repo.has_pending_jobs(story.id, kinds=("summarize",)):
            return
        if self._state.needs_summary(story, self._summary_target(story, message, active)):
            self._queue.enqueue(story.id, "summarize", message.id)

    # ------------------------------------------------------------------ summarize

    async def _summarize(self, job: Job) -> _Outcome:
        """Tóm tắt dồn tới mốc khúc cần thiết. Mỗi khúc (giữa hai mốc) kết thúc bằng một event `summary`
        có `upto_turn` = ngay trước mốc, để builder chọn đúng mốc nằm trước cửa sổ (Phase 3b); khúc dài
        hơn SUMMARY_CHUNK_TOKENS thì chia nhỏ thêm."""
        message = self._active_message(job)
        story, card, persona = self._context(message.story_id)
        assert story.id is not None
        active = self._repo.active_messages(story.id)
        target = self._summary_target(story, message, active)
        if target is None or target < 0:
            return _Outcome("done")
        history = [m for m in active if m.turn_index <= message.turn_index]
        stops = sorted({m - 1 for m in window_boundaries(card, persona, story, history, budget=self._budget) if m - 1 < target})
        stops.append(target)
        total_attempts = 0
        while True:
            current = self._state.current_summary(story)
            covered = current.upto_turn if current is not None else -1
            stop = next((s for s in stops if s > covered), None)
            if stop is None:
                break
            pending = [m for m in active if covered < m.turn_index <= stop and m.visible_content.strip()]
            if not pending:
                # Khúc không có chữ nào (hiếm): đánh dấu đã phủ để đi tiếp.
                anchor_msg = next((m for m in reversed(active) if m.turn_index <= stop), None)
                if anchor_msg is None or anchor_msg.id is None or current is None:
                    break
                self._repo.add_summary(anchor_msg.id, current.text, stop)
                active = self._repo.active_messages(story.id)
                continue
            chunk: list[Message] = []
            tokens = 0
            for m in pending:
                cost = estimate_tokens(m.raw_content)
                if chunk and tokens + cost > SUMMARY_CHUNK_TOKENS:
                    break
                chunk.append(m)
                tokens += cost
            previous = current.text if current is not None else None

            async def call(chunk: list[Message] = chunk, previous: str | None = previous) -> str:
                text = await self.summarizer(
                    self._llm,
                    model=self._model_for(story),
                    num_ctx=self._budget.num_ctx,
                    card=card,
                    persona=persona,
                    story=story,
                    previous=previous,
                    messages=chunk,
                )
                if not isinstance(text, str) or not text.strip():
                    raise ValueError("Model trả tóm tắt rỗng")
                return text.strip()

            text, attempts = await self._with_retry(call)
            total_attempts += attempts
            anchor = chunk[-1]
            assert anchor.id is not None
            if not self._repo.message_is_active(anchor.id):
                raise _Cancelled("Lượt được tóm tắt không còn active")
            upto = stop if len(chunk) == len(pending) else anchor.turn_index
            self._repo.add_summary(anchor.id, text, upto)
            active = self._repo.active_messages(story.id)
        return _Outcome("done", attempts=total_attempts)

    # ------------------------------------------------------------------ embed

    async def _embed(self, job: Job) -> _Outcome:
        model = await self._state.active_embed_model()
        if model is None:
            return _Outcome("done", error="Không có embed model; chỉ tìm ký ức theo từ khoá")
        embedder = self.embedder or self._llm.embed
        total_attempts = 0
        while True:
            items = self._repo.memories_missing_embedding(job.story_id, model, limit=EMBED_BATCH)
            if not items:
                break

            async def call(texts: list[str] = [m.text for m in items]) -> list[list[float]]:  # noqa: B006
                vectors = await embedder(model, texts)
                if len(vectors) != len(texts) or any(not v for v in vectors):
                    raise ValueError("Số vector embed không khớp số ký ức")
                return vectors

            vectors, attempts = await self._with_retry(call)
            total_attempts += attempts
            stored = 0
            for item, vector in zip(items, vectors, strict=True):
                assert item.id is not None
                if self._repo.set_memory_embedding(item.id, pack_embedding(vector), model):
                    stored += 1
            if stored == 0:
                break
        return _Outcome("done", attempts=total_attempts)


__all__ = ["Worker", "extraction_rows", "normalize_fact", "pack_embedding", "unpack_embedding"]
