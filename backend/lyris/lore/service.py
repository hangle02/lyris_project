"""`LoreService`: sổ thế giới của từng card (docs/phase4.md §3-§8).

- CRUD mục (`create`, `update`, `patch`, `delete`), nhập `world.md` (`import_world_md`) và `character_book` của
  Card V2 (`import_card_book`, `apply_card_book`), có bước xem trước (`dry_run`).
- Prompt: `prompt_lore(story, card, persona, history)` -> PromptLore (đồng bộ, lỗi thì None: không bao giờ
  chặn lượt chat), `reserve_for(card_id)` (phần dự phòng cố định cho mọi chỗ dựng prompt để đoán cửa sổ),
  `record_hits` (ghi lượt nào đã mở mục nào).
- Giao diện: `story_lore` (ngăn cảm xúc), `extras_info` (lore_tags, lore_count, lore_available), `summary`
  (hồ sơ nhân vật: chỉ tên người và nơi chốn ai cũng biết).

Mọi thay đổi sổ thế giới gọi `on_change(card_id)` (app nối vào `JobQueue.lore_changed`: hẹn prefill lại).
"""
from __future__ import annotations

import logging
import secrets
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from lyris.db.repo import ANY_ACCOUNT, AccountScope, NotFound, Repo
from lyris.lore.book import book_entries, book_of, without_book
from lyris.lore.normalize import match_form, nfc
from lyris.lore.parse import META_SPOILER_TERMS, key_warnings, normalize_known_by, parse_world_md
from lyris.lore.select import audience_of, lore_for_history, reserve_for
from lyris.models import (
    MAX_LORE_CONTENT,
    MAX_LORE_ENTRIES_PER_CARD,
    MAX_LORE_IMPORT_BYTES,
    MAX_LORE_KEY_CHARS,
    MAX_LORE_KEYS,
    MAX_LORE_KNOWN_BY,
    MAX_LORE_TITLE,
    CharacterCard,
    LoreCategory,
    LoreEntry,
    LoreEntryIn,
    LoreEntryOut,
    LoreImportAction,
    LoreImportItem,
    LoreImportResult,
    LorePatch,
    LoreSource,
    LoreSummary,
    Message,
    Persona,
    PromptLore,
    Story,
    StoryLore,
    UnlockedLore,
)
from lyris.prompt.templates import PromptContext, get_template

logger = logging.getLogger("lyris.lore")

SUMMARY_NAMES = 8
NO_ENTRIES_DETAIL = (
    "Không tìm thấy mục thế giới nào. File cần có phần “## Mục lore”, “## Nhân vật xung quanh” hoặc “## Địa điểm”."
)
NO_BOOK_DETAIL = "Nhân vật này không có sổ thế giới đi kèm để dùng."
TOO_MANY_DETAIL = f"Mỗi nhân vật có tối đa {MAX_LORE_ENTRIES_PER_CARD} mục thế giới."
_EDIT_FIELDS = ("title", "category", "keys", "known_by", "content")


class LoreInputError(ValueError):
    """Dữ liệu mục thế giới / file nhập không hợp lệ (câu tiếng Việt hoàn chỉnh, API trả 422)."""


class LoreLimitError(Exception):
    """Card đã đủ MAX_LORE_ENTRIES_PER_CARD mục (API trả 409)."""


@dataclass
class _Incoming:
    slug: str
    title: str
    category: LoreCategory
    keys: list[str]
    known_by: list[str]
    content: str
    enabled: bool = True
    priority: int = 0
    position: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)


def entry_warnings(entry: LoreEntry, char_name: str) -> list[str]:
    """Câu nhắc cho Studio: chưa có khoá, khoá một chữ / trùng tên nhân vật, chỉ người khác biết."""
    out: list[str] = []
    if not entry.keys:
        out.append(f"Mục “{entry.title}” chưa có từ khoá gợi nhớ nên sẽ không bao giờ được nhắc tới.")
    out += key_warnings(entry.keys, char_name)
    if audience_of(entry.known_by, char_name) == "others":
        names = ", ".join(v for v in entry.known_by if v not in ("*", "{{user}}", "{{char}}"))
        out.append(f"Mục “{entry.title}” chỉ {names} biết, nên {char_name} sẽ không dùng mục này.")
    return out


def has_meta_terms(text: str) -> list[str]:
    """Các từ trong META_SPOILER_TERMS có trong `text` (để Studio nhắc chuyển sang "Chỉ bạn")."""
    form = match_form(text)
    return [t for t in META_SPOILER_TERMS if match_form(t) in form]


class LoreService:
    def __init__(self, repo: Repo, *, on_change: Callable[[int], object] | None = None) -> None:
        self._repo = repo
        self.on_change = on_change

    @property
    def repo(self) -> Repo:
        return self._repo

    def _changed(self, card_id: int) -> None:
        if self.on_change is None:
            return
        try:
            self.on_change(card_id)
        except Exception:  # hàng đợi lỗi không được làm hỏng thao tác đã lưu
            logger.exception("Không báo được thay đổi sổ thế giới (card %s)", card_id)

    def _card(self, card_id: int, account_id: AccountScope) -> CharacterCard:
        """Card mà người gọi được xem/sửa TOÀN BỘ sổ thế giới: của chính `account_id`, không phải bản sao
        (docs/auth.md §4.5: toàn bộ sổ chỉ người tạo đọc; bản sao 404)."""
        return self._repo.get_card(card_id, account_id=account_id, copies=False)

    # ------------------------------------------------------------------ đọc

    def entry_out(self, entry: LoreEntry, char_name: str) -> LoreEntryOut:
        return LoreEntryOut(
            **entry.model_dump(),
            audience=audience_of(entry.known_by, char_name),
            warnings=entry_warnings(entry, char_name),
        )

    def list_entries(self, card_id: int, *, account_id: AccountScope) -> list[LoreEntryOut]:
        card = self._card(card_id, account_id)
        return [self.entry_out(e, card.name) for e in self._repo.list_lore(card_id)]

    def available(self, card_id: int) -> bool:
        return any(e.enabled for e in self._repo.list_lore(card_id))

    # ------------------------------------------------------------------ sửa

    def _clean(self, body: LoreEntryIn, char_name: str) -> dict[str, Any]:
        title = " ".join(nfc(body.title).split())
        if not title:
            raise LoreInputError("Mục thế giới cần có tên.")
        if len(title) > MAX_LORE_TITLE:
            raise LoreInputError(f"Tên mục thế giới dài tối đa {MAX_LORE_TITLE} ký tự.")
        keys: list[str] = []
        seen: set[str] = set()
        for raw in body.keys:
            key = " ".join(nfc(raw).split())
            if not key:
                continue
            if len(key) > MAX_LORE_KEY_CHARS:
                raise LoreInputError(f"Mỗi từ khoá dài tối đa {MAX_LORE_KEY_CHARS} ký tự.")
            form = match_form(key)
            if form in seen:
                continue
            seen.add(form)
            keys.append(key)
        if len(keys) > MAX_LORE_KEYS:
            raise LoreInputError(f"Mỗi mục có tối đa {MAX_LORE_KEYS} từ khoá.")
        known_by = normalize_known_by(list(body.known_by), char_name)
        if not known_by:
            raise LoreInputError("Cần chọn ai biết điều này.")
        if len(known_by) > MAX_LORE_KNOWN_BY:
            raise LoreInputError(f"Mỗi mục có tối đa {MAX_LORE_KNOWN_BY} người biết.")
        content = nfc(body.content).strip()
        if len(content) > MAX_LORE_CONTENT:
            raise LoreInputError(f"Nội dung dài tối đa {MAX_LORE_CONTENT} ký tự.")
        return {
            "title": title,
            "category": body.category,
            "keys": keys,
            "known_by": known_by,
            "content": content,
            "enabled": body.enabled,
            "priority": body.priority,
        }

    def create(self, card_id: int, body: LoreEntryIn, *, account_id: AccountScope) -> LoreEntryOut:
        card = self._card(card_id, account_id)
        fields = self._clean(body, card.name)
        with self._repo.transaction():
            if self._repo.count_lore(card_id) >= MAX_LORE_ENTRIES_PER_CARD:
                raise LoreLimitError(TOO_MANY_DETAIL)
            entry = self._repo.insert_lore(
                LoreEntry(
                    card_id=card_id,
                    slug=f"manual:{secrets.token_hex(6)}",
                    source="manual",
                    position=self._repo.next_lore_position(card_id),
                    **fields,
                )
            )
        self._changed(card_id)
        return self.entry_out(entry, card.name)

    def update(
        self, card_id: int, entry_id: int, body: LoreEntryIn, *, account_id: AccountScope
    ) -> LoreEntryOut:
        """Thay nội dung. Mục từ file/card chỉ thành "đã sửa" khi một trong title, category, keys, known_by,
        content thật sự đổi (mở hộp sửa rồi Lưu mà không đổi gì thì nhập lại vẫn cập nhật được)."""
        card = self._card(card_id, account_id)
        current = self._repo.get_lore(card_id, entry_id)
        fields = self._clean(body, card.name)
        changed = any(fields[k] != getattr(current, k) for k in _EDIT_FIELDS)
        if changed and current.source != "manual":
            fields["edited"] = True
        entry = self._repo.update_lore(entry_id, **fields)
        self._changed(card_id)
        return self.entry_out(entry, card.name)

    def patch(self, card_id: int, entry_id: int, body: LorePatch, *, account_id: AccountScope) -> LoreEntryOut:
        """Bật/tắt hoặc đổi chỗ; không đổi `edited`."""
        card = self._card(card_id, account_id)
        self._repo.get_lore(card_id, entry_id)
        fields = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
        entry = self._repo.update_lore(entry_id, **fields)
        self._changed(card_id)
        return self.entry_out(entry, card.name)

    def delete(self, card_id: int, entry_id: int, *, account_id: AccountScope) -> None:
        """Mục tự thêm: xoá hẳn. Mục từ file/card: bia mộ (nhập lại không thêm lại), xoá hit của nó."""
        self._card(card_id, account_id)
        entry = self._repo.get_lore(card_id, entry_id)
        assert entry.id is not None
        if entry.source == "manual":
            self._repo.delete_lore(entry.id)
        else:
            self._repo.tombstone_lore(entry.id)
        self._changed(card_id)

    # ------------------------------------------------------------------ nhập

    def import_world_md(
        self,
        card_id: int,
        text: str,
        *,
        dry_run: bool = False,
        delete_missing: bool = False,
        account_id: AccountScope,
    ) -> LoreImportResult:
        if len(text.encode("utf-8")) > MAX_LORE_IMPORT_BYTES:
            raise LoreInputError("File quá lớn (tối đa 500 KB).")
        card = self._card(card_id, account_id)
        parsed = parse_world_md(text, card.name)
        if not parsed.entries:
            raise LoreInputError(NO_ENTRIES_DETAIL)
        incoming = [
            _Incoming(
                slug=e.slug, title=e.title, category=e.category, keys=e.keys, known_by=e.known_by, content=e.content
            )
            for e in parsed.entries
        ]
        result = self._apply(card_id, incoming, source="world_md", dry_run=dry_run, delete_missing=delete_missing)
        result.notes = [*parsed.notes, *result.notes]
        result.warnings = [*parsed.warnings, *result.warnings]
        result.player_only = list(parsed.player_only)
        result.dropped_sentences = list(parsed.dropped_sentences)
        return result

    def import_card_book(self, card_id: int, *, dry_run: bool = False, account_id: AccountScope) -> LoreImportResult:
        """Dùng `character_book` còn nằm trong `extensions.v2` của card cũ (import trước Phase 4). Xong (không
        dry_run) thì bỏ book khỏi extensions, để DB chỉ có một nguồn sự thật."""
        card = self._card(card_id, account_id)
        book = book_of(card.extensions)
        if book is None:
            raise LoreInputError(NO_BOOK_DETAIL)
        incoming = self._book_incoming(book, card.name)
        result = self._apply(card_id, incoming, source="card_book", dry_run=dry_run, delete_missing=False)
        if not dry_run:
            self._repo.update_card(
                card_id, card.model_copy(update={"extensions": without_book(card.extensions)}), account_id=account_id
            )
        return result

    def apply_card_book(self, card_id: int, extensions: dict[str, Any]) -> LoreImportResult | None:
        """POST/PUT card: chuyển `extensions.v2.character_book` (nếu có) thành mục `card_book` (theo slug,
        idempotent). Người gọi lưu card với `without_book(extensions)`."""
        book = book_of(extensions)
        if book is None:
            return None
        card = self._card(card_id, ANY_ACCOUNT)  # route vừa lưu card này cho chính người gọi
        return self._apply(card_id, self._book_incoming(book, card.name), source="card_book", dry_run=False)

    @staticmethod
    def _book_incoming(book: dict[str, Any], char_name: str) -> list[_Incoming]:
        return [
            _Incoming(
                slug=b.slug,
                title=b.title,
                category=b.category,
                keys=b.keys,
                known_by=b.known_by,
                content=b.content,
                enabled=b.enabled,
                priority=b.priority,
                position=b.position,
                extra=b.extra,
            )
            for b in book_entries(book, char_name)
        ]

    def _apply(
        self,
        card_id: int,
        incoming: Sequence[_Incoming],
        *,
        source: LoreSource,
        dry_run: bool,
        delete_missing: bool = False,
    ) -> LoreImportResult:
        """Áp các mục vào card theo slug, trong MỘT transaction (dry_run: không ghi gì)."""
        result = LoreImportResult(dry_run=dry_run)
        wrote = False

        def item(inc_slug: str, title: str, category: LoreCategory, action: LoreImportAction) -> None:
            result.items.append(LoreImportItem(slug=inc_slug, title=title, category=category, action=action))

        with self._repo.transaction():
            existing = self._repo.lore_by_slug(card_id)
            count = self._repo.count_lore(card_id)
            position = self._repo.next_lore_position(card_id)
            seen: set[str] = set()
            for inc in incoming:
                if inc.slug in seen:
                    continue
                seen.add(inc.slug)
                found = existing.get(inc.slug)
                if found is None:
                    if count >= MAX_LORE_ENTRIES_PER_CARD:
                        raise LoreLimitError(TOO_MANY_DETAIL)
                    count += 1
                    result.created += 1
                    item(inc.slug, inc.title, inc.category, "create")
                    if not dry_run:
                        self._repo.insert_lore(
                            LoreEntry(
                                card_id=card_id,
                                slug=inc.slug,
                                title=inc.title,
                                category=inc.category,
                                keys=inc.keys,
                                known_by=inc.known_by,
                                content=inc.content,
                                source=source,
                                enabled=inc.enabled,
                                priority=inc.priority,
                                position=inc.position if inc.position is not None else position,
                                extra=inc.extra,
                            )
                        )
                        wrote = True
                    if inc.position is None:
                        position += 1
                    continue
                entry, removed = found
                assert entry.id is not None
                if removed:
                    result.skipped_removed += 1
                    item(inc.slug, entry.title, entry.category, "skip_removed")
                elif entry.edited:
                    result.kept_edited += 1
                    item(inc.slug, entry.title, entry.category, "keep_edited")
                elif (
                    entry.title == inc.title
                    and entry.category == inc.category
                    and entry.keys == inc.keys
                    and entry.known_by == inc.known_by
                    and entry.content == inc.content
                    and (source != "card_book" or entry.extra == inc.extra)
                ):
                    result.unchanged += 1
                    item(inc.slug, entry.title, entry.category, "unchanged")
                else:
                    result.updated += 1
                    item(inc.slug, inc.title, inc.category, "update")
                    if not dry_run:
                        fields: dict[str, Any] = {
                            "title": inc.title,
                            "category": inc.category,
                            "keys": inc.keys,
                            "known_by": inc.known_by,
                            "content": inc.content,
                        }
                        if source == "card_book":
                            fields["extra"] = inc.extra
                        self._repo.update_lore(entry.id, **fields)
                        wrote = True
            for slug, (entry, removed) in sorted(existing.items(), key=lambda kv: (kv[1][0].position, kv[1][0].id or 0)):
                if removed or entry.source != source or slug in seen:
                    continue
                assert entry.id is not None
                result.missing += 1
                if not delete_missing:
                    item(slug, entry.title, entry.category, "keep_missing")
                elif entry.edited:
                    result.kept_edited += 1
                    item(slug, entry.title, entry.category, "keep_edited")
                else:
                    result.deleted += 1
                    item(slug, entry.title, entry.category, "delete")
                    if not dry_run:
                        self._repo.delete_lore(entry.id)
                        wrote = True
        if result.skipped_removed:
            result.notes.append(f"Bỏ qua {result.skipped_removed} mục bạn đã xoá.")
        if wrote:
            self._changed(card_id)
        return result

    def copy(self, src_card_id: int, dst_card_id: int) -> int:
        """Nhân bản card: sao chép mọi mục (giữ slug, source, edited)."""
        copied = self._repo.copy_lore(src_card_id, dst_card_id)
        if copied:
            self._changed(dst_card_id)
        return copied

    # ------------------------------------------------------------------ prompt

    def reserve_for(self, card_id: int) -> int:
        """Phần dự phòng cố định của khối D cho card (0 khi không có mục bật nào gửi được cho model). Mọi chỗ
        dựng prompt để đoán cửa sổ (prefill, tóm tắt) phải dùng đúng số này, như lượt chat thật."""
        try:
            card = self._repo.get_card(card_id, account_id=ANY_ACCOUNT)
            return reserve_for(self._repo.list_lore(card_id), card.name)
        except Exception:
            logger.exception("Không tính được phần dự phòng sổ thế giới (card %s)", card_id)
            return 0

    def prompt_lore(
        self, story: Story, card: CharacterCard, persona: Persona, history: Sequence[Message]
    ) -> PromptLore | None:
        """PromptLore cho lượt sắp viết (`history` kết thúc bằng lượt người chơi). Card không có mục nào ->
        None (prompt giống hệt Phase 3). Lỗi -> log rồi None, không bao giờ chặn lượt chat."""
        if card.id is None or not history:
            return None
        try:
            entries = self._repo.list_lore(card.id)
            if not entries:
                return None
            ctx = PromptContext(card=card, persona=persona, story=story, style="")
            return lore_for_history(entries, tpl=get_template(story.language), ctx=ctx, history=history)
        except Exception:
            logger.exception("Không chọn được mục thế giới cho prompt (story %s)", story.id)
            return None

    def record_hits(self, story_id: int, message_id: int, lore: PromptLore | None) -> None:
        """Ghi các mục lượt `message_id` đã dùng / đã gợi ra. Lỗi thì log, lượt vẫn lưu."""
        if lore is None:
            return
        hits: list[tuple[int, Any]] = [
            *((s.entry_id, "carried") for s in lore.carried),
            *((s.entry_id, "fresh") for s in lore.fresh),
            *((i, "unsent") for i in lore.unsent_ids),
        ]
        if not hits:
            return
        try:
            self._repo.record_lore_hits(story_id, message_id, hits)
        except Exception:
            logger.exception("Không ghi được mục thế giới đã mở (message %s)", message_id)

    # ------------------------------------------------------------------ giao diện

    def _unlocked(self, story: Story) -> tuple[list[UnlockedLore], CharacterCard]:
        assert story.id is not None
        # Route đã kiểm story thuộc người gọi; card (kể cả bản sao) và persona cùng tài khoản với story (§2.2).
        card = self._repo.get_card(story.card_id, account_id=ANY_ACCOUNT)
        persona = self._repo.get_persona(story.persona_id, account_id=ANY_ACCOUNT)
        ctx = PromptContext(card=card, persona=persona, story=story, style="")
        out: list[UnlockedLore] = []
        for row in self._repo.unlocked_lore(story.id):
            audience = audience_of(row.entry.known_by, card.name)
            if audience == "others":
                continue
            if audience in ("everyone", "character") and not row.sent:
                continue  # khớp nhưng chưa bao giờ tới được model (hết chỗ): chưa coi là đã mở khoá
            assert row.entry.id is not None
            out.append(
                UnlockedLore(
                    entry_id=row.entry.id,
                    title=" ".join(ctx.fill(row.entry.title).split()),
                    category=row.entry.category,
                    audience=audience,
                    content=ctx.fill(row.entry.content),
                    first_turn=row.first_turn,
                    last_turn=row.last_turn,
                    turns=row.turns,
                )
            )
        return out, card

    def story_lore(self, story: Story, *, account_id: AccountScope) -> StoryLore:
        """Ngăn "Cảm xúc & ký ức". `can_edit`: người gọi sửa được sổ thế giới của card (card của chính họ, không
        phải bản sao: bản sao 404 ở Studio, docs/auth.md §4.1)."""
        entries, card = self._unlocked(story)
        assert card.id is not None
        owner = self._repo.card_account_id(card.id)
        mine = account_id is ANY_ACCOUNT or owner == account_id
        can_edit = mine and not self._repo.card_origin(card.id).story_copy
        return StoryLore(available=self.available(card.id), can_edit=can_edit, card_id=card.id, entries=entries)

    def extras_info(self, story: Story) -> tuple[list[str], int, bool]:
        """(lore_tags, lore_count, lore_available) cho /extras. Lỗi -> rỗng."""
        try:
            entries, card = self._unlocked(story)
            assert card.id is not None
            tags = [e.title for e in entries if e.audience in ("everyone", "player")]
            return tags, len(entries), self.available(card.id)
        except Exception:
            logger.exception("Không đọc được thế giới đã mở khoá (story %s)", story.id)
            return [], 0, False

    def summary(self, card_id: int, *, account_id: AccountScope) -> LoreSummary:
        """Teaser trên hồ sơ nhân vật: card của người gọi (cả bản sao), hoặc card công khai của người khác
        (docs/auth.md §4.1, §4.5: chỉ tên người và nơi chốn ai cũng biết)."""
        try:
            card = self._repo.get_card(card_id, account_id=account_id)
        except NotFound:
            card = self._repo.get_public_card(card_id)
        enabled = [e for e in self._repo.list_lore(card_id) if e.enabled]
        public = [e for e in enabled if audience_of(e.known_by, card.name) == "everyone"]
        people = [e.title for e in public if e.category == "character"]
        places = [e.title for e in public if e.category == "place"]
        return LoreSummary(
            total=len(enabled),
            people=people[:SUMMARY_NAMES],
            places=places[:SUMMARY_NAMES],
            people_more=max(0, len(people) - SUMMARY_NAMES),
            places_more=max(0, len(places) - SUMMARY_NAMES),
        )


__all__ = [
    "LoreInputError",
    "LoreLimitError",
    "LoreService",
    "NO_BOOK_DETAIL",
    "NO_ENTRIES_DETAIL",
    "entry_warnings",
    "has_meta_terms",
]
