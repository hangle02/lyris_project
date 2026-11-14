"""State của story cho API, ChatService và worker (docs/phase3.md §2, §6, §7).

- `extras(story)`: StoryExtras cho ngăn cảm xúc (quan hệ + chỉ dẫn, cảnh, gợi ý, ký ức, pending...).
- `prompt_state(...)`: PromptState đưa vào prompt (tóm tắt, chỉ dẫn diễn xuất, cảnh, ký ức tìm được).
- `hub_info(story)`: chip cảm xúc nổi bật và nơi chốn cho thẻ story ở hub.
- `summary_target(...)` / `needs_summary(...)`: tóm tắt cần phủ tới lượt nào, có cần xếp job tóm tắt không
  (Phase 3b: theo mốc khúc của cửa sổ lịch sử, docs/phase3.md §10).

Phần gọi model (`lyris.state.directive`, `lyris.memory.retrieval`) do module khác phụ trách; import muộn,
thiếu module hoặc lỗi thì phần đó bỏ trống, không làm hỏng lượt chat.
"""
from __future__ import annotations

import logging
import statistics
import time
from collections.abc import Awaitable, Callable, Mapping
from typing import TYPE_CHECKING, Any

from lyris.db.repo import ANY_ACCOUNT, Repo
from lyris.lore import select as lore_select
from lyris.models import (
    EMOTION_KEYS,
    BuiltPrompt,
    ChatTurn,
    SummaryPoint,
    TimelineEntry,
    TimelineScene,
    CharacterCard,
    DominantEmotion,
    MemoryHit,
    MemorySearch,
    Message,
    Persona,
    PromptState,
    RelationshipState,
    RelationshipValues,
    SceneState,
    Story,
    StoryExtras,
)
from lyris.prompt.builder import PromptBudget, build_prompt, next_window_start, window_boundaries
from lyris.state.fold import (
    FoldedState,
    Summary,
    dominant_emotion,
    fold_events,
    initial_relationship,
    latest_summary,
    parse_delta,
    parse_scene,
    parse_summary,
)

if TYPE_CHECKING:
    from lyris.lore.service import LoreService

logger = logging.getLogger("lyris.state")

MODEL_LIST_TTL = 60.0  # giây: cache danh sách model Ollama (để biết có embed model không)
EXTRAS_MEMORY_LIMIT = 50
RETRIEVE_LIMIT = 16  # builder bỏ ký ức còn trong cửa sổ lịch sử, nên lấy dư để còn chỗ cho chuyện cũ


def model_listed(name: str, models: list[str]) -> bool:
    """`name` có trong danh sách model của Ollama (tên không kèm tag khớp với `:latest`)."""
    if name in models:
        return True
    return ":" not in name and f"{name}:latest" in models


class ModelCatalog:
    """Danh sách model của Ollama, cache `ttl` giây. Không dò được (LLM giả, Ollama tắt) -> None."""

    def __init__(
        self,
        lister: Callable[[], Awaitable[list[str]]] | None,
        *,
        ttl: float = MODEL_LIST_TTL,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._lister = lister
        self._ttl = ttl
        self._clock = clock
        self._cached: list[str] | None = None
        self._at: float | None = None

    @classmethod
    def for_client(cls, llm: Any, **kwargs: Any) -> ModelCatalog:
        return cls(getattr(llm, "list_models", None), **kwargs)

    def invalidate(self) -> None:
        self._at = None

    async def names(self) -> list[str] | None:
        if self._lister is None:
            return None
        now = self._clock()
        if self._at is not None and now - self._at < self._ttl:
            return self._cached
        try:
            names: list[str] | None = list(await self._lister())
        except Exception as exc:  # gồm LLMError: coi như không biết, thử lại sau ttl
            logger.info("Không lấy được danh sách model Ollama: %s", exc)
            names = None
        self._cached, self._at = names, now
        return names


def _relationship_directive(
    values: RelationshipValues, card: CharacterCard, persona: Persona, story: Story
) -> str | None:
    try:
        from lyris.state.directive import acting_directive
    except ImportError:
        return None
    try:
        text = acting_directive(
            values,
            char=card.name,
            player=persona.name,
            language=story.language,
            player_pronoun=story.narration_pronouns.player,
            char_pronoun=story.narration_pronouns.character,
        )
    except Exception:
        logger.exception("Không dựng được chỉ dẫn diễn xuất")
        return None
    text = (text or "").strip()
    return text or None


def window_start_turn(message: Message, active: list[Message]) -> int | None:
    """Lượt đầu tiên còn trong cửa sổ lịch sử khi sinh `message` (từ prompt snapshot).

    Snapshot mới ghi sẵn `window_start_turn`; snapshot cũ chỉ có `dropped_turns` thì suy ra từ lịch sử
    active trước lượt đó. Không có snapshot -> None.
    """
    snap = message.prompt_snapshot
    if not isinstance(snap, Mapping):
        return None
    start = snap.get("window_start_turn")
    if isinstance(start, int) and not isinstance(start, bool):
        return start
    dropped = snap.get("dropped_turns")
    if not isinstance(dropped, int) or isinstance(dropped, bool) or dropped <= 0:
        return None
    history = [m for m in active if m.turn_index < message.turn_index]
    if dropped >= len(history):
        return message.turn_index
    return history[dropped].turn_index


# Lượt người chơi kế tiếp được giả định dài như lượt dài nhất trong chừng này lượt gần đây (cộng một chút).
NEXT_USER_LOOKBACK = 3
NEXT_USER_SLACK_CHARS = 120


def _next_user_chars(history: list[Message]) -> int:
    recent = [len(m.raw_content) for m in reversed(history) if m.role == "user"][:NEXT_USER_LOOKBACK]
    return max(recent, default=0) + NEXT_USER_SLACK_CHARS


# Prefill (§10.6) cần đoán ĐÚNG lượt người chơi kế tiếp, không đoán dư: đoán cửa sổ dịch mà thật ra không
# dịch (hay ngược lại) thì phần gửi trước lệch ngay ở system, mất trắng. Trung vị độ dài các lượt gần đây
# (không cộng thêm) làm sai lệch |đoán - thật| nhỏ nhất, nên ít khi rơi đúng vào mốc dịch nhất.
PREFILL_USER_LOOKBACK = 5


def _prefill_user_chars(history: list[Message]) -> int:
    recent = [len(m.raw_content) for m in reversed(history) if m.role == "user"][:PREFILL_USER_LOOKBACK]
    return statistics.median_low(recent) if recent else 0


class StateService:
    def __init__(
        self,
        repo: Repo,
        llm: Any,
        *,
        embed_model: str | None = None,
        catalog: ModelCatalog | None = None,
        budget: PromptBudget | None = None,
        lore: LoreService | None = None,
    ) -> None:
        self._repo = repo
        self.budget = budget or PromptBudget()
        # Phase 4: sổ thế giới (None = như Phase 3: không khối D, không phần dự phòng).
        self.lore = lore
        self._llm = llm
        self._embed_model = (embed_model or "").strip() or None
        self._catalog = catalog if catalog is not None else ModelCatalog.for_client(llm)

    @property
    def repo(self) -> Repo:
        return self._repo

    # ------------------------------------------------------------------ embed model

    async def active_embed_model(self) -> str | None:
        """Tên embed model nếu Ollama đang có nó; không thì None (chỉ tìm theo từ khoá)."""
        if self._embed_model is None:
            return None
        names = await self._catalog.names()
        if not names or not model_listed(self._embed_model, names):
            return None
        return self._embed_model

    async def memory_search(self) -> MemorySearch:
        return "hybrid" if await self.active_embed_model() is not None else "keyword"

    # ------------------------------------------------------------------ gộp state

    def initial(self, story: Story, card: CharacterCard | None = None) -> RelationshipValues:
        assert story.id is not None
        stored = self._repo.story_initial_relationship(story.id)
        if card is None:
            card = self._repo.get_card(story.card_id, account_id=ANY_ACCOUNT)
        return initial_relationship(stored, card.extensions)

    def fold(self, story: Story, *, upto_turn: int | None = None, card: CharacterCard | None = None) -> FoldedState:
        """State hiện tại (hoặc như tại lượt `upto_turn`) từ event của các message active."""
        assert story.id is not None
        last = self._repo.last_active_message_ref(story.id)
        last_id, last_role = (None, None) if last is None else (last[0], last[1])
        if upto_turn is not None and last is not None and last[2] > upto_turn:
            last_id, last_role = None, None  # state ở lượt cũ: không có gợi ý
        return fold_events(
            self.initial(story, card),
            self._repo.state_events(story.id, upto_turn=upto_turn),
            last_message_id=last_id,
            last_message_role=last_role,
            upto_turn=upto_turn,
        )

    def current_summary(self, story: Story) -> Summary | None:
        assert story.id is not None
        return latest_summary(self._repo.state_events(story.id, kinds=("summary",)))

    def hub_info(self, story: Story) -> tuple[DominantEmotion | None, str | None]:
        """(chip cảm xúc nổi bật, nơi chốn) cho thẻ story ở hub; None khi chưa có dữ liệu thật."""
        assert story.id is not None
        try:
            events = self._repo.state_events(story.id, kinds=("relationship_delta", "scene"))
            if not events:
                return None, None
            folded = fold_events(self.initial(story), events)
        except Exception:
            logger.exception("Không tính được state cho story %s", story.id)
            return None, None
        return dominant_emotion(folded.relationship, has_events=folded.has_relationship_events), folded.scene.location

    def summary_points(self, story: Story, *, upto_turn: int | None = None) -> list[SummaryPoint]:
        """Mọi mốc tóm tắt active (upto_turn tăng dần; cùng mốc thì lấy bản mới nhất)."""
        assert story.id is not None
        by_upto: dict[int, str] = {}
        for event in self._repo.state_events(story.id, kinds=("summary",), upto_turn=upto_turn):
            parsed = parse_summary(event.payload)
            if parsed is not None:
                by_upto[parsed[1]] = parsed[0]
        return [SummaryPoint(text=text, upto_turn=upto) for upto, text in sorted(by_upto.items())]

    def summary_target(
        self,
        story: Story,
        history: list[Message],
        window_start: int | None,
        *,
        card: CharacterCard | None = None,
        persona: Persona | None = None,
    ) -> int | None:
        """Lượt mà tóm tắt nên phủ tới, khi cửa sổ lịch sử đang bắt đầu ở `window_start` (Phase 3b).

        Khối C chỉ dùng mốc tóm tắt nằm hẳn trước cửa sổ, và cửa sổ chỉ dịch theo khúc (builder). Nên
        tóm tắt được làm theo đúng các mốc khúc: phủ mọi khúc đã rơi khỏi cửa sổ, và làm trước khúc sắp rơi
        tiếp theo, nhưng CHỈ khi cửa sổ sẽ dịch ngay ở lượt kế tiếp (`next_window_start` với một lượt người
        chơi dài như lượt dài nhất gần đây). Gọi model tóm tắt đẩy prompt của chat ra khỏi cache, nên làm
        đúng trước lượt vốn phải đọc lại prompt (lượt cửa sổ dịch): mỗi khúc chỉ một lượt chậm, và lúc cửa
        sổ dịch thì tóm tắt mới đã sẵn. None = chưa cần tóm tắt gì.
        """
        if not history:
            return None
        card = card or self._repo.get_card(story.card_id, account_id=ANY_ACCOUNT)
        persona = persona or self._repo.get_persona(story.persona_id, account_id=ANY_ACCOUNT)
        start = max(0, window_start or 0)
        marks = window_boundaries(card, persona, story, history, budget=self.budget)
        # Phase 4: cùng phần dự phòng khối D như lượt chat thật, không thì đoán lệch lượt cửa sổ dịch.
        lore_reserve = self.lore.reserve_for(card.id) if self.lore is not None and card.id is not None else 0
        targets = [m for m in marks if m <= start]
        if start > 0:
            targets.append(start)
        if any(m > start for m in marks):
            upto = history[-1].turn_index
            ahead = next_window_start(
                card,
                persona,
                story,
                history,
                next_user_chars=_next_user_chars(history),
                summaries=self.summary_points(story, upto_turn=upto) if story.id is not None else [],
                budget=self.budget,
                lore_reserve=lore_reserve,
            )
            if ahead > start:
                targets.append(ahead)
        return max(targets) - 1 if targets else None

    def needs_summary(self, story: Story, target: int | None) -> bool:
        """Tóm tắt hiện có chưa phủ tới `target` (từ `summary_target`)."""
        if target is None or target < 0:
            return False
        summary = self.current_summary(story)
        covered = summary.upto_turn if summary is not None else -1
        return covered < target

    # ------------------------------------------------------------------ extras cho giao diện

    async def extras(self, story: Story) -> StoryExtras:
        assert story.id is not None
        card = self._repo.get_card(story.card_id, account_id=ANY_ACCOUNT)
        persona = self._repo.get_persona(story.persona_id, account_id=ANY_ACCOUNT)
        folded = self.fold(story, card=card)
        relationship = RelationshipState(
            **folded.relationship.model_dump(),
            directive=_relationship_directive(folded.relationship, card, persona, story),
        )
        lore_tags: list[str] = []
        lore_count = 0
        lore_available = False
        if self.lore is not None:
            lore_tags, lore_count, lore_available = self.lore.extras_info(story)
        return StoryExtras(
            lore_tags=lore_tags,
            lore_available=lore_available,
            lore_count=lore_count,
            relationship=relationship,
            suggestions=folded.suggestions,
            location=folded.scene.location,
            in_world_time=folded.scene.time,
            memories=self._repo.list_memories(story.id, limit=EXTRAS_MEMORY_LIMIT),
            pending=self._repo.has_pending_jobs(story.id),
            unprocessed_turns=self._repo.unprocessed_turns(story.id),
            memory_search=await self.memory_search(),
            summary=folded.summary.text if folded.summary is not None else None,
        )

    # ------------------------------------------------------------------ dòng thời gian (Phase 3b)

    def timeline(self, story: Story) -> list[TimelineEntry]:
        """Các lượt active có state (ký ức, fact, thay đổi cảm xúc khác 0, cảnh), lượt cũ trước.

        Dữ liệu cho tab "Dòng thời gian" của "Xem sự kiện": chạm một mục thì nhảy tới lượt đó.
        """
        assert story.id is not None
        messages = {m.id: m for m in self._repo.active_messages(story.id) if m.id is not None}
        deltas: dict[int, dict[str, int]] = {}
        scenes: dict[int, TimelineScene] = {}
        for event in self._repo.state_events(story.id, kinds=("relationship_delta", "scene")):
            if event.kind == "relationship_delta":
                delta = parse_delta(event.payload)
                if delta is not None:
                    deltas[event.message_id] = {k: getattr(delta, k) for k in EMOTION_KEYS if getattr(delta, k)}
            else:
                scene = parse_scene(event.payload)
                if scene is not None and ((scene.location or "").strip() or (scene.time or "").strip()):
                    scenes[event.message_id] = TimelineScene(
                        location=(scene.location or "").strip() or None, time=(scene.time or "").strip() or None
                    )
        memory: dict[int, str] = {}
        facts: dict[int, list[str]] = {}
        for item in sorted(self._repo.list_memories(story.id, limit=None), key=lambda m: m.id or 0):
            if item.kind == "memory":
                memory.setdefault(item.message_id, item.text)
            else:
                facts.setdefault(item.message_id, []).append(item.text)
        entries: list[TimelineEntry] = []
        for message_id in set(deltas) | set(scenes) | set(memory) | set(facts):
            message = messages.get(message_id)
            delta = deltas.get(message_id, {})
            if message is None or not (delta or message_id in scenes or message_id in memory or message_id in facts):
                continue
            entries.append(
                TimelineEntry(
                    turn_index=message.turn_index,
                    message_id=message_id,
                    mode=message.mode,
                    created_at=message.created_at,
                    memory=memory.get(message_id),
                    facts=facts.get(message_id, []),
                    delta=delta,
                    scene=scenes.get(message_id),
                )
            )
        return sorted(entries, key=lambda e: e.turn_index)

    # ------------------------------------------------------------------ prompt

    def next_prompt_prefix(self, story: Story) -> BuiltPrompt | None:
        """Phần đầu prompt chat của lượt kế tiếp: system + lịch sử tới câu trả lời cuối, bỏ lượt người chơi
        (còn chưa viết) cùng ghi chú F (docs/phase3.md §10.6). Worker gửi trước phần này cho Ollama khi
        rảnh để lượt sau chỉ còn phải đọc lượt mới của người chơi.

        Phase 4 (docs/phase4.md §6.5): dựng với `PromptLore` thật của lượt sắp tới (cùng phần dự phòng khối D
        như lượt thật, không thì lệch cửa sổ). Khi `LORE_PREFILL_OPEN_TURN` bật và có mục carried, phần đầu
        còn kèm lượt người chơi "còn mở" (`lore_head`, `open_last=True`); mặc định tắt (như Phase 3).

        Lượt người chơi giả dài bằng trung vị các lượt gần đây (`_prefill_user_chars`, không cộng dư như
        `summary_target`): cửa sổ chỉ dịch ở phần đầu này khi lượt người chơi bình thường cũng làm nó dịch.
        State chỉ có tóm tắt (cảnh, thái độ, ký ức, fact nằm trong ghi chú F ở message cuối, không ảnh hưởng
        phần đầu).
        None = không có gì để dựng (story rỗng, lượt cuối không phải của nhân vật, dựng lỗi).
        """
        if story.id is None:
            return None
        history = self._repo.active_messages(story.id)
        if not history or history[-1].role != "assistant":
            return None
        card = self._repo.get_card(story.card_id, account_id=ANY_ACCOUNT)
        persona = self._repo.get_persona(story.persona_id, account_id=ANY_ACCOUNT)
        last = history[-1]
        chars = max(1, _prefill_user_chars(history))
        probe = Message(
            story_id=story.id,
            turn_index=last.turn_index + 1,
            role="user",
            mode=story.mode,
            raw_content="x" * chars,
            visible_content="x" * chars,
        )
        summary = self.current_summary(story)
        state = PromptState(
            summary=summary.text if summary is not None else None,
            summaries=self.summary_points(story, upto_turn=last.turn_index),
        )
        hist = [*history, probe]
        lore = self.lore.prompt_lore(story, card, persona, hist) if self.lore is not None else None
        try:
            built = build_prompt(card, persona, story, hist, budget=self.budget, state=state, lore=lore)
        except ValueError:
            return None
        if len(built.messages) < 2 or built.messages[-1].role != "user":
            return None
        messages = built.messages[:-1]
        open_last = False
        if lore_select.LORE_PREFILL_OPEN_TURN and built.lore_head:
            messages = [*messages, ChatTurn(role="user", content=built.lore_head)]
            open_last = True
        return built.model_copy(
            update={"messages": messages, "options": {**built.options, "num_predict": 1}, "open_last": open_last}
        )

    async def prompt_state(
        self, story: Story, card: CharacterCard, persona: Persona, history: list[Message]
    ) -> PromptState:
        """State cho lượt sắp viết. `history` là lịch sử đưa vào prompt (kết thúc bằng lượt người chơi):
        state được tính tới lượt cuối của history, nên khi regenerate, hiệu ứng của variant cũ không lọt vào.
        """
        upto = history[-1].turn_index if history else None
        folded = self.fold(story, upto_turn=upto, card=card)
        scene: SceneState | None = folded.scene if (folded.scene.location or folded.scene.time) else None
        memories = await self._retrieve(story, history, names=(card.name, persona.name))
        if upto is not None:
            memories = [m for m in memories if m.turn_index <= upto]
        return PromptState(
            summary=folded.summary.text if folded.summary is not None else None,
            summaries=self.summary_points(story, upto_turn=upto),
            directive=_relationship_directive(folded.relationship, card, persona, story),
            scene=scene,
            memories=memories,
        )

    async def _retrieve(self, story: Story, history: list[Message], *, names: tuple[str, ...] = ()) -> list[MemoryHit]:
        try:
            from lyris.memory.retrieval import retrieve
        except ImportError:
            return []
        try:
            embed_model = await self.active_embed_model()
            return list(
                await retrieve(
                    self._repo, self._llm, story, history, embed_model=embed_model, limit=RETRIEVE_LIMIT, names=names
                )
            )
        except Exception:
            logger.exception("Không tìm được ký ức cho story %s", story.id)
            return []

    def dominant_emotion(self, story: Story) -> DominantEmotion | None:
        return self.hub_info(story)[0]


__all__ = [
    "EXTRAS_MEMORY_LIMIT",
    "MODEL_LIST_TTL",
    "ModelCatalog",
    "StateService",
    "model_listed",
    "window_start_turn",
]
