"""Dựng prompt cho một lượt chat.

Thứ tự khối (cố định để phần đầu được Ollama cache):
  system = A (luật) + B (nhân vật, persona, xưng hô, style) + C (bối cảnh, tóm tắt cảnh)
  E = lịch sử (cắt lượt cũ nhất trước khi vượt ngân sách)
  F = ghi chú cho người dẫn truyện, nối vào cuối message user cuối
System message chỉ phụ thuộc card, persona, story, file style và tóm tắt tự động (Phase 3, chỉ đổi khi
job summarize chạy): không có thời gian hay nội dung theo lượt, nên giữ nguyên từng byte giữa các lượt.

Phase 3: `state` (PromptState) thêm tóm tắt vào C và các dòng cảnh / thái độ / ký ức / fact vào F.
`state=None` cho ra đúng prompt như trước Phase 3 (Studio chat thử, harness).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from lyris.lore.select import block_lines, line_tokens
from lyris.models import (
    MAX_PROMPT_FACTS,
    MAX_PROMPT_MEMORIES,
    BuiltPrompt,
    CharacterCard,
    ChatTurn,
    Language,
    LoreUse,
    MemoryHit,
    Message,
    Persona,
    PromptLore,
    PromptState,
    Role,
    Story,
    StyleProfileInfo,
    SummaryPoint,
)
from lyris.prompt.directives import extract_directives, remove_directives
from lyris.prompt.repetition import RECENT_REPLIES, recent_phrases
from lyris.prompt.templates import PromptContext, Template, get_template
from lyris.prompt.tokens import estimate_tokens

STYLES_DIR = Path(__file__).resolve().parent / "styles"

_STYLE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_LANG_HEADING = re.compile(r"^#[ \t]*(vi|en)[ \t]*$", re.MULTILINE)
# Frontmatter: dòng đầu là "---", kết thúc ở dòng "---" (hoặc "...") tiếp theo.
_FRONTMATTER = re.compile(r"\A---[ \t]*\r?\n(.*?)^(?:---|\.\.\.)[ \t]*(?:\r?\n|\Z)", re.DOTALL | re.MULTILINE)

TEMPERATURE = 0.8
TOP_P = 0.95
# Phần state của khối F (cảnh, thái độ, ký ức, fact) tối đa khoảng chừng này token; dư thì bỏ bớt ký ức/fact.
STATE_TOKEN_LIMIT = 350
MAX_STATE_ITEM_CHARS = 240


@dataclass(frozen=True)
class PromptBudget:
    num_ctx: int = 8192
    reply_tokens_story: int = 900
    reply_tokens_dm: int = 200
    safety_tokens: int = 256


def available_styles() -> list[str]:
    return sorted(p.stem for p in STYLES_DIR.glob("*.md") if _STYLE_NAME.fullmatch(p.stem))


def _style_path(name: str) -> Path:
    if not _STYLE_NAME.fullmatch(name or ""):
        raise ValueError(f'Tên style profile không hợp lệ: "{name}"')
    path = STYLES_DIR / f"{name}.md"
    if not path.is_file():
        known = ", ".join(available_styles()) or "(chưa có)"
        raise ValueError(f'Không tìm thấy style profile "{name}". Các profile hiện có: {known}')
    return path


def _split_frontmatter(text: str) -> tuple[str | None, str]:
    """Tách YAML frontmatter (`---` ở dòng đầu ... `---`) khỏi phần thân. Không có thì trả (None, text)."""
    match = _FRONTMATTER.match(text)
    if not match:
        return None, text
    return match.group(1), text[match.end() :]


def _read_style(name: str) -> tuple[str | None, str]:
    text = _style_path(name).read_text(encoding="utf-8")
    if text.startswith("﻿"):
        text = text[1:]
    return _split_frontmatter(text)


def _as_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):  # YAML 1.1: yes/no/on/off -> bool; trả lại dạng chữ
        return "true" if value else "false"
    return str(value).strip()


def _parse_profile(name: str, frontmatter: str | None) -> StyleProfileInfo:
    if frontmatter is None or not frontmatter.strip():
        return StyleProfileInfo(name=name, title=name)
    try:
        data = yaml.safe_load(frontmatter)
    except yaml.YAMLError as exc:
        raise ValueError(f'Frontmatter của style profile "{name}" không đọc được: {exc}') from exc
    if data is None:
        return StyleProfileInfo(name=name, title=name)
    if not isinstance(data, dict):
        raise ValueError(f'Frontmatter của style profile "{name}" phải là một bảng khoá: giá trị.')

    narration: dict[str, dict[str, str]] = {}
    raw_narration = data.get("narration") or {}
    if not isinstance(raw_narration, dict):
        raise ValueError(f'Mục "narration" của style profile "{name}" phải là bảng ngôn ngữ -> giới tính.')
    for lang, by_gender in raw_narration.items():
        if not isinstance(by_gender, dict):
            raise ValueError(f'Mục "narration.{lang}" của style profile "{name}" phải là bảng giới tính -> đại từ.')
        narration[_as_text(lang)] = {_as_text(g): _as_text(p) for g, p in by_gender.items()}

    examples: list[dict[str, str]] = []
    raw_examples = data.get("address_examples") or []
    if not isinstance(raw_examples, list):
        raise ValueError(f'Mục "address_examples" của style profile "{name}" phải là một danh sách.')
    for item in raw_examples:
        if not isinstance(item, dict):
            raise ValueError(f'Mỗi mục trong "address_examples" của style profile "{name}" phải là một bảng.')
        examples.append({_as_text(k): _as_text(v) for k, v in item.items() if v is not None})

    title = _as_text(data.get("title")) or name
    return StyleProfileInfo(
        name=name,
        title=title,
        description=_as_text(data.get("description")),
        narration=narration,
        address_examples=examples,
    )


def get_style_profile(name: str) -> StyleProfileInfo:
    """Thông tin profile từ frontmatter của `styles/<name>.md`; ValueError nếu không có.

    File thiếu frontmatter vẫn đọc được (title = name, các trường khác rỗng).
    """
    frontmatter, _ = _read_style(name)
    return _parse_profile(name, frontmatter)


def list_style_profiles() -> list[StyleProfileInfo]:
    """Mọi style profile, sắp theo tên."""
    return [get_style_profile(name) for name in available_styles()]


def load_style(name: str, language: Language = "vi") -> str:
    """Đọc phần thân của `styles/<name>.md` để chèn vào prompt; ValueError nếu không có.

    YAML frontmatter ở đầu file luôn bị bỏ (không bao giờ vào prompt).
    File có thể chia mục theo ngôn ngữ bằng dòng `# vi` / `# en`; khi đó trả mục của `language`
    (thiếu thì lấy mục `vi`). File không chia mục thì trả cả file. Chú thích `<!-- -->` bị bỏ.
    """
    _, body = _read_style(name)
    text = _HTML_COMMENT.sub("", body)
    headings = list(_LANG_HEADING.finditer(text))
    if not headings:
        return text.strip()
    sections: dict[str, str] = {}
    for i, match in enumerate(headings):
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        sections[match.group(1)] = text[match.end() : end].strip()
    return sections.get(language) or sections.get("vi") or next(iter(sections.values()))


def _scrub(text: str) -> str:
    """Bảo đảm "((" và "))" không bao giờ lọt vào prompt (model sẽ bắt chước và in ra)."""
    while "((" in text or "))" in text:
        text = text.replace("((", "(").replace("))", ")")
    return text


@dataclass
class _Item:
    role: Role
    content: str  # đã bỏ chỉ đạo; rỗng với lượt user chỉ có chỉ đạo
    directive: str | None


def _to_item(msg: Message, dm_label: str | None = None) -> _Item:
    """Một message của lịch sử thành một lượt. `dm_label`: nhãn đặt trước lượt DM (Story và DM chung
    một dòng thời gian; ở Story Mode, thiếu nhãn thì model coi tin nhắn như lời nói trực tiếp hoặc bỏ qua,
    vd. quên rằng nhân vật đã xưng tên qua tin nhắn). Chi phí token cho mốc khúc luôn đo với nhãn
    để mốc khúc không phụ thuộc mode đang chơi."""

    def labelled(text: str) -> str:
        if dm_label and msg.mode == "dm" and text.strip():
            return f"{dm_label} {text}"
        return text

    if msg.role == "user":
        content, extra = extract_directives(msg.visible_content)
        directives = [d for d in (msg.directive, extra) if d and d.strip()]
        return _Item("user", labelled(content), "; ".join(d.strip() for d in directives) or None)
    # Assistant: giữ Thought để model giữ format; chỉ bỏ cặp ((...)) hoàn chỉnh nếu model lỡ in lại
    # chỉ đạo ở lượt trước (không bỏ phần đuôi sau "((" lẻ, không đụng mặt cười ":((").
    return _Item("assistant", labelled(remove_directives(msg.raw_content)), None)


@dataclass
class _Assembled:
    turns: list[ChatTurn]  # lịch sử (E) kèm F ở message cuối
    e_tokens: int
    f_tokens: int


def _clip_item(text: str) -> str:
    text = " ".join(text.split())
    if len(text) <= MAX_STATE_ITEM_CHARS:
        return text
    return text[:MAX_STATE_ITEM_CHARS].rsplit(" ", 1)[0] + "…"


def _pick(hits: list[MemoryHit], limit: int) -> list[MemoryHit]:
    """Tối đa `limit` hit đầu (đã xếp hạng), bỏ hit trùng chữ."""
    out: list[MemoryHit] = []
    seen: set[str] = set()
    for hit in hits:
        key = " ".join(hit.text.split()).casefold()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(hit)
        if len(out) >= limit:
            break
    return out


def state_lines(tpl: Template, ctx: PromptContext, state: PromptState | None, first_turn: int) -> list[str]:
    """Các dòng state của khối F khi cửa sổ lịch sử bắt đầu ở lượt `first_turn`.

    Ký ức (kind 'memory') chỉ lấy những lượt trước cửa sổ (lượt trong cửa sổ model đã thấy), tối đa 3,
    viết theo thứ tự thời gian; fact lấy luôn, tối đa 3. Dài quá STATE_TOKEN_LIMIT thì bỏ dần hit hạng
    thấp nhất (fact trước khi hai bên bằng nhau).
    """
    if state is None:
        return []
    memories = _pick([h for h in state.memories if h.kind == "memory" and h.turn_index < first_turn], MAX_PROMPT_MEMORIES)
    # Fact trùng chữ một ký ức đã chọn thì bỏ, không in cùng một câu hai lần.
    told = {" ".join(h.text.split()).casefold() for h in memories}
    facts = _pick(
        [h for h in state.memories if h.kind == "fact" and " ".join(h.text.split()).casefold() not in told],
        MAX_PROMPT_FACTS,
    )

    def render() -> list[str]:
        return tpl.state_lines(
            ctx,
            scene=state.scene,
            directive=state.directive,
            memories=[_clip_item(h.text) for h in sorted(memories, key=lambda h: (h.turn_index, h.memory_id))],
            facts=[_clip_item(h.text) for h in facts],
        )

    lines = render()
    while (memories or facts) and estimate_tokens("\n".join(lines)) > STATE_TOKEN_LIMIT:
        if len(facts) >= len(memories):
            facts.pop()
        else:
            memories.pop()
        lines = render()
    return lines


def _assemble(
    items: list[_Item],
    start: int,
    tail_start: int,
    tpl: Template,
    ctx: PromptContext,
    avoid: list[str],
    state: list[str] | None = None,
    lore_block: str | None = None,
) -> _Assembled:
    """Ghép lịch sử từ `items[start:]`. `items[tail_start:]` là các lượt user cuối chưa được trả lời.

    `lore_block` (Phase 4, khối D): đặt ở ĐẦU message user cuối, sau khi đã tính `e_tokens` (D không thuộc
    lịch sử; builder cộng nó riêng), như F được nối vào cuối."""
    pairs: list[tuple[Role, str]] = []
    for item in items[start:tail_start]:
        if item.role == "assistant" and not item.content:
            continue
        content = item.content or (tpl.empty_user_turn if item.role == "user" else "")
        pairs.append((item.role, content))

    tail = items[max(start, tail_start) :]
    tail_text = "\n\n".join(i.content for i in tail if i.content)
    directives = [i.directive for i in tail if i.directive]
    directive = "; ".join(directives) if directives else None
    pairs.append(("user", tail_text))

    if pairs[0][0] == "assistant":
        pairs.insert(0, ("user", tpl.story_start if start == 0 else tpl.story_continues))

    merged: list[tuple[Role, str]] = []
    for role, content in pairs:
        if merged and merged[-1][0] == role:
            prev = merged[-1][1]
            merged[-1] = (role, f"{prev}\n\n{content}" if prev and content else prev or content)
        else:
            merged.append((role, content))

    e_tokens = sum(estimate_tokens(c) for _, c in merged)
    note = tpl.final_note(ctx, directive=directive, player_wrote=bool(tail_text), avoid=avoid, state=state or ())
    last_role, last_text = merged[-1]
    merged[-1] = (last_role, f"{last_text}\n\n{note}" if last_text else note)
    if lore_block:
        merged[-1] = (last_role, f"{lore_block}\n\n{merged[-1][1]}")
    turns = [ChatTurn(role=role, content=_scrub(content)) for role, content in merged]
    return _Assembled(turns=turns, e_tokens=e_tokens, f_tokens=estimate_tokens(note))


# ---- Phase 3b: cửa sổ lịch sử cắt theo khúc (hysteresis) --------------------------------------------
#
# Khi lịch sử vượt ngân sách, không cắt từng lượt một (điểm đầu cửa sổ dịch mỗi lượt -> Ollama đọc lại
# toàn bộ prompt, TTFT ~60 giây). Thay vào đó cửa sổ chỉ được bắt đầu ở các "mốc khúc": chia lịch sử từ
# ĐẦU story thành các khúc khoảng TRIM_CHUNK_FRACTION ngân sách lịch sử, mỗi mốc là đầu một lượt người
# chơi. Mốc chỉ phụ thuộc phần lịch sử phía trước nó, nên không dịch khi story dài thêm: builder chọn mốc
# sớm nhất còn vừa, và mốc đó giữ nguyên qua nhiều lượt cho tới khi không vừa nữa. Mỗi lần cắt bỏ cả một
# khúc, nên sau khi cắt lịch sử chỉ dùng khoảng (1 - TRIM_CHUNK_FRACTION) ngân sách. Không cần lưu gì.
#
# 1/3: với num_ctx 8192 và card seed, ngân sách lịch sử story ~5000 token nên một khúc ~1700 token, tức
# khoảng 2-3 lượt story thật (lượt trả lời ~500-700 token): cửa sổ đứng yên 2-3 lượt rồi mới dịch một lần.
TRIM_CHUNK_FRACTION = 1 / 3
MIN_CHUNK_TOKENS = 200


def _turn_start(items: list[_Item], i: int) -> bool:
    """Vị trí i là đầu một lượt người chơi (user ngay sau assistant)."""
    return 0 < i < len(items) and items[i].role == "user" and items[i - 1].role == "assistant"


def _chunk_tokens(stable_fixed: int, limit: int) -> int:
    return max(MIN_CHUNK_TOKENS, int(TRIM_CHUNK_FRACTION * (limit - stable_fixed)))


def _boundaries(items: list[_Item], costs: list[int], last: int, chunk: int) -> list[int]:
    """Các vị trí cửa sổ được phép bắt đầu: 0 và đầu lượt người chơi đầu tiên sau mỗi `chunk` token,
    đếm từ đầu story (chỉ phụ thuộc phần phía trước, nên ổn định khi lịch sử dài thêm)."""
    out = [0]
    acc = 0
    for i in range(1, last + 1):
        acc += costs[i - 1]
        if acc >= chunk and _turn_start(items, i):
            out.append(i)
            acc = 0
    return out


@dataclass(frozen=True)
class _Frame:
    """Phần cố định của một story cho việc cắt lịch sử (không phụ thuộc lượt)."""

    tpl: Template
    ctx: PromptContext
    block_a: str
    block_b: str
    limit: int
    reply_tokens: int
    stable_fixed: int  # A + B + C (không kèm tóm tắt tự động)


def _frame(card: CharacterCard, persona: Persona, story: Story, budget: PromptBudget) -> _Frame:
    tpl = get_template(story.language)
    ctx = PromptContext(card=card, persona=persona, story=story, style=load_style(card.style_profile, story.language))
    block_a = _scrub(tpl.rules(ctx))
    block_b = _scrub(tpl.character(ctx))
    bare_c = _scrub(tpl.context(ctx, summary=None))
    reply_tokens = budget.reply_tokens_story if story.mode == "story" else budget.reply_tokens_dm
    stable = estimate_tokens(block_a) + estimate_tokens(block_b) + (estimate_tokens(bare_c) if bare_c else 0)
    return _Frame(
        tpl=tpl,
        ctx=ctx,
        block_a=block_a,
        block_b=block_b,
        limit=budget.num_ctx - reply_tokens - budget.safety_tokens,
        reply_tokens=reply_tokens,
        stable_fixed=stable,
    )


def _story_chunk(card: CharacterCard, persona: Persona, story: Story, budget: PromptBudget) -> int:
    """Cỡ một khúc, KHÔNG phụ thuộc chế độ Story/DM: tính theo chế độ chật hơn (phần trả lời dài hơn, luật
    dài hơn). Nhờ vậy hai chế độ có cùng các mốc, đổi chế độ giữa chừng thì mốc tóm tắt vẫn khớp cửa sổ."""
    stable = max(_frame(card, persona, story.model_copy(update={"mode": m}), budget).stable_fixed for m in ("story", "dm"))
    limit = budget.num_ctx - max(budget.reply_tokens_story, budget.reply_tokens_dm) - budget.safety_tokens
    return _chunk_tokens(stable, limit)


# Phần dự phòng cố định cho khối F khi xét cắt lịch sử: ghi chú dài nhất có thể (đủ RECENT_REPLIES câu cần
# tránh, mỗi câu tới AVOID_PHRASE_CHARS ký tự) + STATE_TOKEN_LIMIT cho các dòng state. Không phụ thuộc lượt
# (fact, ký ức, chỉ dẫn diễn xuất của lượt này), nên điểm bắt đầu cửa sổ không nhảy tới lui giữa các lượt.
AVOID_PHRASE_CHARS = 100


def _f_reserve(frame: _Frame, *, with_state: bool) -> int:
    filler = ["x" * AVOID_PHRASE_CHARS] * RECENT_REPLIES
    note = max(
        estimate_tokens(frame.tpl.final_note(frame.ctx, directive=None, player_wrote=wrote, avoid=filler))
        for wrote in (True, False)
    )
    return note + (STATE_TOKEN_LIMIT if with_state else 0)


def window_boundaries(
    card: CharacterCard,
    persona: Persona,
    story: Story,
    history: list[Message],
    *,
    budget: PromptBudget | None = None,
) -> list[int]:
    """turn_index của các mốc khúc (trừ mốc 0) mà cửa sổ lịch sử có thể bắt đầu, như `build_prompt`
    tính. Giống nhau ở Story và DM. Worker dùng để tóm tắt theo đúng các khúc (docs/phase3.md §10)."""
    if not history:
        return []
    budget = budget or PromptBudget()
    tpl = get_template(story.language)
    items = [_to_item(m, tpl.dm_label) for m in history]
    costs = [estimate_tokens(i.content or tpl.empty_user_turn) for i in items]
    chunk = _story_chunk(card, persona, story, budget)
    return [history[i].turn_index for i in _boundaries(items, costs, len(items) - 1, chunk) if i > 0]


def next_window_start(
    card: CharacterCard,
    persona: Persona,
    story: Story,
    history: list[Message],
    *,
    next_user_chars: int,
    summaries: list[SummaryPoint] | None = None,
    budget: PromptBudget | None = None,
    lore_reserve: int = 0,
) -> int:
    """turn_index lượt đầu cửa sổ mà `build_prompt` (có state) sẽ chọn ở lượt kế tiếp, nếu người chơi viết
    thêm một lượt dài `next_user_chars` ký tự sau `history`. Phép kiểm tra cắt chỉ dùng phần dự phòng cố
    định cho F, nên kết quả không phụ thuộc ký ức / fact của lượt đó. Worker dùng để biết cửa sổ sắp dịch
    (tóm tắt trước đúng lúc đó, không sớm hơn). `lore_reserve` (Phase 4): phần dự phòng cố định của khối D,
    phải bằng đúng phần chat thật dùng, không thì đoán lệch cửa sổ."""
    if not history:
        return 0
    last = history[-1]
    probe = Message(
        story_id=last.story_id,
        turn_index=last.turn_index + 1,
        role="user",
        mode=story.mode,
        raw_content="x" * max(1, next_user_chars),
        visible_content="x" * max(1, next_user_chars),
    )
    hist = [*history, probe]
    lore = PromptLore(reserve_tokens=lore_reserve) if lore_reserve > 0 else None
    # Đoán thận trọng (không lùi mốc theo khối D thật, xem build_prompt): tóm tắt được làm trước lúc cửa sổ
    # có thể dịch, không bao giờ trễ.
    built = build_prompt(
        card,
        persona,
        story,
        hist,
        budget=budget,
        state=PromptState(summaries=list(summaries or [])),
        lore=lore,
        lore_fallback=False,
    )
    return hist[built.dropped_turns].turn_index


def pick_summary(summaries: list[SummaryPoint], first_turn: int) -> SummaryPoint | None:
    """Mốc tóm tắt mới nhất nằm hẳn trước cửa sổ (upto_turn < lượt đầu trong cửa sổ)."""
    best: SummaryPoint | None = None
    for point in summaries:
        if point.upto_turn < first_turn and (best is None or point.upto_turn >= best.upto_turn):
            best = point
    return best


def build_prompt(
    card: CharacterCard,
    persona: Persona,
    story: Story,
    history: list[Message],
    *,
    budget: PromptBudget | None = None,
    state: PromptState | None = None,
    lore: PromptLore | None = None,
    lore_fallback: bool = True,
) -> BuiltPrompt:
    """Dựng prompt cho lượt trả lời tiếp theo. `history` = các message active theo thứ tự lượt.

    `state` (Phase 3): tóm tắt tự động vào khối C; cảnh, chỉ dẫn diễn xuất, ký ức trước cửa sổ lịch sử
    và fact vào khối F. None = đúng prompt như trước Phase 3.

    `lore` (Phase 4, docs/phase4.md §6): khối D (thông tin thế giới) ở đầu message user cuối, KHÔNG BAO GIỜ ở
    system. Có `state` thì phép kiểm tra cắt dùng phần dự phòng cố định `lore.reserve_tokens` (điểm bắt đầu
    cửa sổ không phụ thuộc lượt này gợi ra mục nào); không có `state` thì D được tính đúng như thật. None, hoặc
    không có mục nào với reserve 0: prompt giống hệt Phase 3 từng byte.

    Khi phần dự phòng D làm mốc vừa sớm nhất chỉ còn các lượt người chơi chưa trả lời (mất cả câu trả lời
    trước của nhân vật), thử lại mốc ngay trước với khối D thật của lượt này (`lore_fallback`, phase4.md
    §6.4). `next_window_start` tắt bước này để đoán thận trọng.

    Lịch sử vừa ngân sách thì giữ trọn (như cũ). Không vừa thì cửa sổ bắt đầu ở mốc khúc sớm nhất còn
    vừa (Phase 3b, xem `_boundaries`); không mốc nào vừa thì cắt từng lượt từ mốc cuối như trước.
    """
    if not history:
        raise ValueError("Lịch sử trống: cần ít nhất một tin nhắn của người chơi.")
    if history[-1].role != "user":
        raise ValueError("Tin nhắn cuối phải là của người chơi (role 'user').")
    budget = budget or PromptBudget()
    frame = _frame(card, persona, story, budget)
    tpl, ctx, limit = frame.tpl, frame.ctx, frame.limit
    a_tokens = estimate_tokens(frame.block_a)
    b_tokens = estimate_tokens(frame.block_b)

    points = sorted(state.summaries, key=lambda p: p.upto_turn) if state is not None else []

    def summary_for(start: int) -> SummaryPoint | None:
        if state is None:
            return None
        if points:
            return pick_summary(points, history[start].turn_index)
        if state.summary and state.summary.strip():
            return SummaryPoint(text=state.summary, upto_turn=-1)
        return None

    c_cache: dict[int | None, str] = {}

    def block_c(point: SummaryPoint | None) -> str:
        key = None if point is None else point.upto_turn
        if key not in c_cache:
            c_cache[key] = _scrub(tpl.context(ctx, summary=point.text if point else None))
        return c_cache[key]

    def c_tokens_of(text: str) -> int:
        return estimate_tokens(text) if text else 0

    # Story Mode: lượt DM có nhãn. DM Mode: không nhãn (model sẽ bắt chước nhãn vào tin của nó). Mốc khúc
    # luôn tính với nhãn để giống nhau ở hai mode (`window_boundaries`).
    items = [_to_item(m, tpl.dm_label if story.mode == "story" else None) for m in history]
    tail_start = len(items) - 1
    while tail_start > 0 and items[tail_start - 1].role == "user":
        tail_start -= 1
    last = len(items) - 1  # không bao giờ bỏ message user cuối

    costs = [estimate_tokens(i.content or tpl.empty_user_turn) for i in (_to_item(m, tpl.dm_label) for m in history)]
    avoid = recent_phrases(history, story.mode)

    # Phase 4: khối D không phụ thuộc điểm cắt; được cộng riêng (không thuộc E), như F.
    d_lines = block_lines(tpl, ctx, lore) if lore is not None else []
    lore_block = "\n".join(d_lines) if d_lines else None
    d_tokens = sum(line_tokens(line) for line in d_lines)
    d_reserve = lore.reserve_tokens if lore is not None else 0

    def lines_for(start: int) -> list[str]:
        # Ký ức phụ thuộc điểm cắt: chỉ lượt trước cửa sổ. Mỗi lần thử điểm cắt thì đo lại F.
        lines = state_lines(tpl, ctx, state, history[start].turn_index)
        if story.mode == "story" and any(m.mode == "dm" for m in history[start:]):
            lines = [tpl.dm_note(ctx), *lines]
        return lines

    def assemble(start: int) -> tuple[_Assembled, str, SummaryPoint | None]:
        point = summary_for(start)
        assembled = _assemble(items, start, tail_start, tpl, ctx, avoid, lines_for(start), lore_block)
        return assembled, block_c(point), point

    def total(built: _Assembled, c_text: str) -> int:
        return a_tokens + b_tokens + c_tokens_of(c_text) + built.e_tokens + built.f_tokens + d_tokens

    # Phần dự phòng cố định cho F (không phụ thuộc fact / ký ức / câu cần tránh của lượt này) và cho C
    # (tóm tắt dài nhất): mọi phép kiểm tra cắt dùng chúng, để điểm bắt đầu chỉ phụ thuộc lịch sử và không
    # nhảy tới lui giữa các lượt chỉ vì F/C dao động.
    f_reserve = _f_reserve(frame, with_state=state is not None)
    c_reserve = max((c_tokens_of(block_c(p)) for p in points), default=0)
    if state is not None and not points and state.summary:
        c_reserve = c_tokens_of(block_c(summary_for(0)))

    def fits(candidate: _Assembled, cand_c: str, d_term: int | None = None) -> bool:
        return (
            a_tokens
            + b_tokens
            + max(c_tokens_of(cand_c), c_reserve)
            + candidate.e_tokens
            + max(candidate.f_tokens, f_reserve)
            + (max(d_tokens, d_reserve) if d_term is None else d_term)
        ) <= limit

    start = 0
    built, c_text, point = assemble(0)
    # state=None (Studio, harness): giữ đúng phép kiểm tra cũ để prompt không đổi byte nào khi chưa đầy.
    overflow = total(built, c_text) > limit if state is None else not fits(built, c_text)
    if overflow:
        chunk = _story_chunk(card, persona, story, budget)
        marks = _boundaries(items, costs, last, chunk)
        # Cận dưới rẻ của E để bỏ qua nhanh các mốc chắc chắn không vừa (lịch sử rất dài).
        chars = [len(i.content) for i in items]
        suffix_chars = [0] * (len(items) + 1)
        for i in range(len(items) - 1, -1, -1):
            suffix_chars[i] = suffix_chars[i + 1] + chars[i]
        chosen: int | None = None
        chosen_at = 0
        for at, mark in enumerate(marks[1:], start=1):
            if a_tokens + b_tokens + suffix_chars[mark] * 0.95 / 3.0 > limit:
                continue
            candidate, cand_c, cand_point = assemble(mark)
            if fits(candidate, cand_c):
                chosen, chosen_at = mark, at
                built, c_text, point = candidate, cand_c, cand_point
                break
        # Phase 4: phần dự phòng D (cố định, kể cả lượt không gợi mục nào) có thể đẩy cửa sổ tới mốc chỉ còn
        # lượt người chơi mới. Khi đó mốc ngay trước vẫn được dùng nếu vừa với khối D THẬT của lượt này (vẫn
        # giữ dự phòng F, C). Cửa sổ chỉ dịch chậm đi một lượt, vẫn ở một mốc khúc; tóm tắt cho mốc trước đã có.
        if (
            lore_fallback
            and chosen is not None
            and chosen >= tail_start
            and d_reserve > d_tokens
        ):
            prev = marks[chosen_at - 1]
            candidate, cand_c, cand_point = assemble(prev)
            if fits(candidate, cand_c, d_term=d_tokens):
                chosen = prev
                built, c_text, point = candidate, cand_c, cand_point
        if chosen is not None:
            start = chosen
        else:
            # Không mốc nào vừa (vd. một lượt khổng lồ): cắt từng lượt từ mốc cuối, như trước Phase 3b.
            start = marks[-1]
            built, c_text, point = assemble(start)
            while start < last and total(built, c_text) > limit:
                start += 1
                built, c_text, point = assemble(start)

    system = "\n\n".join(block for block in (frame.block_a, frame.block_b, c_text) if block)
    token_estimate = {
        "A": a_tokens,
        "B": b_tokens,
        "C": c_tokens_of(c_text),
        "E": built.e_tokens,
        "F": built.f_tokens,
    }
    if d_lines:
        token_estimate["D"] = d_tokens
    token_estimate["total"] = sum(token_estimate.values())

    lore_head: str | None = None
    lore_used: list[LoreUse] = []
    if lore is not None and d_lines:
        lore_used = [
            LoreUse(entry_id=s.entry_id, title=s.title, slot=s.slot, tokens=s.tokens) for s in (*lore.carried, *lore.fresh)
        ]
        if lore.carried:
            head = "\n".join(d_lines[: 1 + len(lore.carried)])
            # Cửa sổ bắt đầu ngay ở tail và một lượt user cũ bị gộp lên trước (hiếm): không gửi trước được.
            lore_head = head if built.turns and built.turns[-1].content.startswith(head) else None

    return BuiltPrompt(
        messages=[ChatTurn(role="system", content=system), *built.turns],
        stop=[f"{persona.name}:", f"\n{persona.name}:", "\nPlayer:", "\nUser:"],
        options={
            "num_ctx": budget.num_ctx,
            "num_predict": frame.reply_tokens,
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
        },
        token_estimate=token_estimate,
        dropped_turns=start,
        summary_upto_turn=point.upto_turn if point is not None and point.upto_turn >= 0 else None,
        lore_head=lore_head,
        lore_used=lore_used,
    )
