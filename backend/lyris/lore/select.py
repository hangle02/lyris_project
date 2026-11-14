"""Chọn mục thế giới cho prompt của một lượt (docs/phase4.md §6.1, §6.2). Hàm thuần, tất định.

- Lọc theo người biết (`audience_of`): chỉ everyone/character được gửi cho model. Mục chỉ người chơi
  biết (`{{user}}`) KHÔNG BAO GIỜ vào `carried`/`fresh`, chỉ vào `unsent_ids` (để mở khoá cho người chơi).
- carried: mục khớp trong `earlier` (tối đa LORE_SCAN_DEPTH message ngay trước lượt người chơi mới), chỉ
  phụ thuộc lịch sử. fresh: mục khớp trong `tail` (các lượt người chơi chưa được trả lời), chưa có ở carried.
- Ngân sách cố định: cả khối (dòng mở + mục + dòng đóng) ≤ LORE_TOKEN_LIMIT, carried ≤ LORE_CARRIED_TOKENS,
  tối đa LORE_MAX_ITEMS mục. `reserve_tokens` = LORE_TOKEN_LIMIT khi card có mục gửi được (không đổi theo
  lượt), để điểm bắt đầu cửa sổ lịch sử không nhảy theo mục được gợi ra.
- Lượt của nhân vật (kể cả lời mở đầu) chỉ được quét bằng khoá dạng tên riêng (§5.3).
"""
from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from lyris.lore.match import PLACEHOLDER_ONLY, LoreMatcher
from lyris.lore.normalize import cjk_count, same_name
from lyris.models import LoreAudience, LoreEntry, LoreSnippet, Message, PromptLore
from lyris.prompt.templates import PromptContext, Template, sentence
from lyris.prompt.tokens import estimate_tokens

LORE_SCAN_DEPTH = 4  # message trước tail được quét (≈ 2 lượt "dính")
LORE_TOKEN_LIMIT = 520  # cả khối D, gồm dòng mở + dòng đóng; cũng là reserve_tokens
LORE_CARRIED_TOKENS = 240  # các mục carried (chỉ phụ thuộc lịch sử)
LORE_MAX_ITEMS = 4
MAX_LORE_ITEM_CHARS = 450  # cắt ở cuối câu gần nhất trước giới hạn
# §6.5: gửi trước phần carried của khối D (lượt người chơi "còn mở") khi prefill. TẮT mặc định: chưa đo trên
# Ollama thật rằng prefill của lượt sau không phải đọc lại cả prompt (phase4.md §6.5, §14.4).
LORE_PREFILL_OPEN_TURN = False

USER_TOKEN = "{{user}}"
CHAR_TOKEN = "{{char}}"
EVERYONE_TOKEN = "*"

_CHAR_RE = re.compile(r"^\{\{\s*char\s*\}\}$", re.IGNORECASE)
_USER_RE = re.compile(r"^\{\{\s*user\s*\}\}$", re.IGNORECASE)
_SENTENCE_END = re.compile(r"[.!?…][\"'”’)»]*(?=\s)")  # gồm cả ngoặc/nháy đóng ngay sau dấu câu


def audience_of(known_by: Sequence[str], char_name: str) -> LoreAudience:
    """everyone > character > player > others (§6.1). `["{{user}}", "Hạ Trì"]` là player."""
    values = [v.strip() for v in known_by if isinstance(v, str) and v.strip()]
    if any(v == EVERYONE_TOKEN for v in values):
        return "everyone"
    if any(_CHAR_RE.match(v) or same_name(v, char_name) for v in values):
        return "character"
    if any(_USER_RE.match(v) for v in values):
        return "player"
    return "others"


def sendable(audience: LoreAudience) -> bool:
    return audience in ("everyone", "character")


def line_tokens(line: str) -> int:
    """Ước lượng token của một dòng: `estimate_tokens` cộng số chữ Hán (chữ Hán tốn ~1 token mỗi chữ)."""
    return estimate_tokens(line) + cjk_count(line)


def clip_text(text: str, limit: int = MAX_LORE_ITEM_CHARS) -> str:
    """Gộp mọi khoảng trắng; dài quá `limit` thì cắt ở cuối câu gần nhất trước giới hạn (không có câu nào
    đủ dài thì cắt ở khoảng trắng và thêm "…")."""
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    head = text[:limit]
    ends = [m.end() for m in _SENTENCE_END.finditer(head + " ")]
    ends = [e for e in ends if e <= limit]
    if ends and ends[-1] >= limit // 3:
        return head[: ends[-1]].rstrip()
    cut = head[: limit - 1].rsplit(" ", 1)[0].rstrip(" ,;:")
    return cut + "…"


def _scrub(text: str) -> str:
    while "((" in text or "))" in text:
        text = text.replace("((", "(").replace("))", ")")
    return text


@dataclass(frozen=True)
class ScanText:
    """Một message cần quét: văn bản thuần + có phải lời người chơi không."""

    text: str
    from_player: bool


def fill_key(key: str, ctx: PromptContext) -> str | None:
    """Khoá sau khi thay `{{user}}`/`{{char}}` ở giữa; khoá chỉ là placeholder -> None (không bao giờ khớp)."""
    if PLACEHOLDER_ONLY.match(key):
        return None
    return ctx.fill(key)


def render_item(tpl: Template, ctx: PromptContext, entry: LoreEntry, private: bool) -> tuple[str, str, str]:
    """(tiêu đề, nội dung đã xử lý, dòng hoàn chỉnh) của một mục. Nội dung: fill, gộp dòng, cắt, kết thúc
    bằng dấu câu, `_scrub` từng mục (để "((" không hình thành ở chỗ ghép)."""
    title = _scrub(" ".join(ctx.fill(entry.title).split()))
    text = _scrub(sentence(clip_text(ctx.fill(entry.content))))
    return title, text, tpl.lore_item(ctx, title, text, private)


def reserve_for(entries: Sequence[LoreEntry], char_name: str) -> int:
    """Phần dự phòng cố định: LORE_TOKEN_LIMIT nếu có ít nhất một mục bật gửi được cho model, không thì 0."""
    for entry in entries:
        if entry.enabled and sendable(audience_of(entry.known_by, char_name)):
            return LORE_TOKEN_LIMIT
    return 0


def select_lore(
    entries: Sequence[LoreEntry],
    *,
    tpl: Template,
    ctx: PromptContext,
    tail: Sequence[ScanText],
    earlier: Sequence[ScanText],
    limit: int = LORE_TOKEN_LIMIT,
    carried_limit: int = LORE_CARRIED_TOKENS,
    max_items: int = LORE_MAX_ITEMS,
) -> PromptLore:
    """Chọn mục cho lượt sắp viết. `entries`: mục của card (chỉ mục bật, chưa xoá được xét). `earlier`:
    message trước tail, MỚI NHẤT TRƯỚC (đã cắt ở LORE_SCAN_DEPTH). Không có mục bật nào -> PromptLore rỗng
    với reserve 0 (prompt giống hệt Phase 3)."""
    active = sorted((e for e in entries if e.enabled and e.id is not None), key=lambda e: (e.position, e.id or 0))
    char = ctx.char
    reserve = reserve_for(active, char)
    if not active:
        return PromptLore(reserve_tokens=0)
    by_id = {e.id: e for e in active}
    keyed: list[tuple[int, list[str]]] = []
    for e in active:
        keys = [k for k in (fill_key(k, ctx) for k in e.keys if isinstance(k, str)) if k]
        keyed.append((e.id or 0, keys))
    matcher = LoreMatcher(keyed, ignore=(char, ctx.player))
    if matcher.empty:
        return PromptLore(reserve_tokens=reserve)

    # Quét từng message riêng (không nối), lượt nhân vật chỉ với khoá tên riêng.
    earlier_hits: dict[int, int] = {}  # entry_id -> chỉ số message khớp gần nhất (0 = mới nhất)
    for age, item in enumerate(earlier):
        for entry_id in matcher.scan(item.text, names_only=not item.from_player):
            earlier_hits.setdefault(entry_id, age)
    tail_hits: dict[int, int] = {}  # entry_id -> vị trí khớp đầu tiên trong tail
    offset = 0
    for item in tail:
        for entry_id, pos in matcher.scan(item.text, names_only=not item.from_player).items():
            tail_hits.setdefault(entry_id, offset + pos)
        offset += len(item.text) * 4 + 16  # vị trí trên dạng so khớp; chỉ cần tăng dần giữa các message

    unsent: list[int] = []
    rendered: dict[int, tuple[str, str, int, bool]] = {}

    def item_of(entry: LoreEntry) -> tuple[str, str, int, bool] | None:
        """(tiêu đề, nội dung, token, riêng tư) nếu gửi được; None nếu không bao giờ gửi cho model."""
        assert entry.id is not None
        if entry.id in rendered:
            return rendered[entry.id]
        audience = audience_of(entry.known_by, char)
        if not sendable(audience):
            return None
        private = audience == "character"
        title, text, line = render_item(tpl, ctx, entry, private)
        rendered[entry.id] = (title, text, line_tokens(line), private)
        return rendered[entry.id]

    header = line_tokens(tpl.lore_header(ctx))
    footer = line_tokens(tpl.lore_footer(ctx))

    carried: list[LoreSnippet] = []
    used = 0
    carried_order = sorted(
        earlier_hits, key=lambda i: (earlier_hits[i], -by_id[i].priority, by_id[i].position, i)
    )
    for entry_id in carried_order:
        info = item_of(by_id[entry_id])
        if info is None:
            unsent.append(entry_id)
            continue
        title, text, tokens, private = info
        if len(carried) >= max_items or used + tokens > carried_limit:
            continue  # có thể vẫn vào fresh nếu lượt người chơi mới nhắc lại
        carried.append(LoreSnippet(entry_id=entry_id, title=title, text=text, private=private, tokens=tokens, slot="carried"))
        used += tokens

    in_carried = {s.entry_id for s in carried}
    fresh: list[LoreSnippet] = []
    budget = limit - header - footer - used
    fresh_order = sorted(
        (i for i in tail_hits if i not in in_carried),
        key=lambda i: (-by_id[i].priority, tail_hits[i], by_id[i].position, i),
    )
    for entry_id in fresh_order:
        info = item_of(by_id[entry_id])
        if info is None:
            if entry_id not in unsent:
                unsent.append(entry_id)
            continue
        title, text, tokens, private = info
        if len(carried) + len(fresh) >= max_items or tokens > budget:
            if entry_id not in unsent:
                unsent.append(entry_id)
            continue
        fresh.append(LoreSnippet(entry_id=entry_id, title=title, text=text, private=private, tokens=tokens, slot="fresh"))
        budget -= tokens

    sent = in_carried | {s.entry_id for s in fresh}
    # Mục khớp ở earlier nhưng hết chỗ (không vào carried, không được nhắc lại ở tail): cũng là "unsent".
    for entry_id in carried_order:
        if entry_id not in sent and entry_id not in unsent:
            unsent.append(entry_id)
    return PromptLore(carried=carried, fresh=fresh, reserve_tokens=reserve, unsent_ids=unsent)


def player_text(msg: Message) -> str:
    """Lời người chơi để quét: phần hiển thị + chỉ đạo ((...)), vì chỉ đạo cũng có thể gọi lore."""
    parts = [msg.visible_content or ""]
    if msg.directive and msg.directive.strip():
        parts.append(msg.directive)
    return "\n".join(p for p in parts if p)


def lore_for_history(
    entries: Sequence[LoreEntry], *, tpl: Template, ctx: PromptContext, history: Sequence[Message]
) -> PromptLore:
    """`select_lore` trên lịch sử thật (kết thúc bằng lượt người chơi): tail = các lượt người chơi chưa được trả
    lời; earlier = tối đa LORE_SCAN_DEPTH message ngay trước tail (mới nhất trước; lượt nhân vật quét
    `raw_content`, gồm cả Thought). Không phụ thuộc cửa sổ lịch sử hay tóm tắt."""
    tail_start = len(history)
    while tail_start > 0 and history[tail_start - 1].role == "user":
        tail_start -= 1
    tail = [ScanText(player_text(m), True) for m in history[tail_start:]]
    before = history[max(0, tail_start - LORE_SCAN_DEPTH) : tail_start]
    earlier = [
        ScanText(player_text(m) if m.role == "user" else m.raw_content, m.role == "user") for m in reversed(before)
    ]
    return select_lore(entries, tpl=tpl, ctx=ctx, tail=tail, earlier=earlier)


def block_lines(tpl: Template, ctx: PromptContext, lore: PromptLore) -> list[str]:
    """Các dòng của khối D (rỗng nếu không có mục nào)."""
    if not lore.carried and not lore.fresh:
        return []
    return [
        tpl.lore_header(ctx),
        *(tpl.lore_item(ctx, s.title, s.text, s.private) for s in lore.carried),
        *(tpl.lore_item(ctx, s.title, s.text, s.private) for s in lore.fresh),
        tpl.lore_footer(ctx),
    ]


__all__ = [
    "CHAR_TOKEN",
    "EVERYONE_TOKEN",
    "LORE_CARRIED_TOKENS",
    "LORE_MAX_ITEMS",
    "LORE_PREFILL_OPEN_TURN",
    "LORE_SCAN_DEPTH",
    "LORE_TOKEN_LIMIT",
    "MAX_LORE_ITEM_CHARS",
    "USER_TOKEN",
    "ScanText",
    "audience_of",
    "block_lines",
    "clip_text",
    "line_tokens",
    "lore_for_history",
    "player_text",
    "render_item",
    "reserve_for",
    "select_lore",
    "sendable",
]
