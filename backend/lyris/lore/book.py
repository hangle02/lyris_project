"""Character Card V2 `character_book` <-> mục thế giới (docs/phase4.md §4.6). Hàm thuần.

| Card V2 entry                                   | LoreEntry  |
| keys / content                                  | keys / content |
| name, thiếu thì comment, thiếu nữa thì khoá đầu | title      |
| enabled (mặc định true) / insertion_order / priority | enabled / position / priority |
| extensions.lyris.{known_by, category, slug}     | known_by (thiếu = ["*"]), category (thiếu = lore), slug |
| mọi trường khác (secondary_keys, constant, id...) và extensions khác | extra (export lại đúng chỗ) |

Slug: `extensions.lyris.slug`; thiếu thì `book:id-<id>` khi entry có `id`; thiếu nữa thì `book:<slug tiêu đề>`
(trùng thì thêm `-2`). Không dùng chỉ số trong mảng: book bị sắp lại thì slug theo chỉ số đổi hết.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from lyris.lore.parse import normalize_known_by, slugify
from lyris.lore.normalize import nfc
from lyris.models import MAX_LORE_CONTENT, MAX_LORE_KEYS, MAX_LORE_TITLE, LoreCategory, LoreEntry

LYRIS_KEY = "lyris"
_MAPPED = frozenset({"keys", "content", "name", "enabled", "insertion_order", "priority", "extensions"})
_CATEGORIES: tuple[LoreCategory, ...] = ("lore", "character", "place")


@dataclass
class BookEntry:
    slug: str
    title: str
    category: LoreCategory
    keys: list[str]
    known_by: list[str]
    content: str
    enabled: bool
    priority: int
    position: int
    extra: dict[str, Any] = field(default_factory=dict)


def book_of(extensions: dict[str, Any] | None) -> dict[str, Any] | None:
    """`extensions.v2.character_book` nếu là một book có entries; không thì None."""
    if not isinstance(extensions, dict):
        return None
    v2 = extensions.get("v2")
    if not isinstance(v2, dict):
        return None
    book = v2.get("character_book")
    if not isinstance(book, dict) or not isinstance(book.get("entries"), list):
        return None
    return book


def without_book(extensions: dict[str, Any]) -> dict[str, Any]:
    """Bản sao `extensions` không còn `v2.character_book` (bỏ luôn `v2` nếu rỗng)."""
    out = dict(extensions)
    v2 = out.get("v2")
    if isinstance(v2, dict) and "character_book" in v2:
        rest = {k: v for k, v in v2.items() if k != "character_book"}
        if rest:
            out["v2"] = rest
        else:
            del out["v2"]
    return out


def _str_list(value: Any) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        if isinstance(item, str):
            s = " ".join(nfc(item).split())[:80]
            if s and s not in out:
                out.append(s)
    return out[:MAX_LORE_KEYS]


def _int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return default


def book_entries(book: dict[str, Any], char_name: str | None = None) -> list[BookEntry]:
    """Các mục từ một `character_book`. Entry không phải dict hoặc không có gì (không tên, không khoá, không
    nội dung) bị bỏ."""
    entries = book.get("entries") if isinstance(book, dict) else None
    if not isinstance(entries, list):
        return []
    out: list[BookEntry] = []
    used: dict[str, int] = {}
    for index, raw in enumerate(entries):
        if not isinstance(raw, dict):
            continue
        keys = _str_list(raw.get("keys"))
        content = raw.get("content") if isinstance(raw.get("content"), str) else ""
        content = nfc(content).strip()[:MAX_LORE_CONTENT]
        name = raw.get("name") if isinstance(raw.get("name"), str) else ""
        comment = raw.get("comment") if isinstance(raw.get("comment"), str) else ""
        title = " ".join((name or comment or (keys[0] if keys else "")).split())[:MAX_LORE_TITLE]
        if not title and not content:
            continue
        if not title:
            title = f"Mục {index + 1}"
        ext = raw.get("extensions") if isinstance(raw.get("extensions"), dict) else {}
        lyris = ext.get(LYRIS_KEY) if isinstance(ext.get(LYRIS_KEY), dict) else {}
        known_raw = lyris.get("known_by")
        known_by = normalize_known_by(_str_list(known_raw), char_name) if known_raw is not None else []
        category = lyris.get("category") if lyris.get("category") in _CATEGORIES else "lore"
        slug = lyris.get("slug") if isinstance(lyris.get("slug"), str) and lyris.get("slug", "").strip() else None
        if slug is None:
            entry_id = raw.get("id")
            if isinstance(entry_id, (int, str)) and not isinstance(entry_id, bool) and str(entry_id).strip():
                slug = f"book:id-{str(entry_id).strip()}"
            else:
                slug = f"book:{slugify(title)}"
        slug = slug.strip()[:200]
        used[slug] = used.get(slug, 0) + 1
        if used[slug] > 1:
            slug = f"{slug}-{used[slug]}"
        extra = {k: v for k, v in raw.items() if k not in _MAPPED}
        other_ext = {k: v for k, v in ext.items() if k != LYRIS_KEY}
        if other_ext:
            extra["extensions"] = other_ext
        enabled = raw.get("enabled")
        out.append(
            BookEntry(
                slug=slug,
                title=title,
                category=category,
                keys=keys,
                known_by=known_by or ["*"],
                content=content,
                enabled=enabled if isinstance(enabled, bool) else True,
                priority=max(-100, min(100, _int(raw.get("priority")))),
                position=max(0, _int(raw.get("insertion_order"), index)),
                extra=extra,
            )
        )
    return out


def entries_to_book(card_name: str, entries: Sequence[LoreEntry]) -> dict[str, Any] | None:
    """`character_book` dựng từ mọi mục (mọi nguồn) của card; không có mục nào -> None."""
    items: list[dict[str, Any]] = []
    for entry in sorted(entries, key=lambda e: (e.position, e.id or 0)):
        extra = dict(entry.extra or {})
        other_ext = extra.pop("extensions", None)
        ext: dict[str, Any] = dict(other_ext) if isinstance(other_ext, dict) else {}
        ext[LYRIS_KEY] = {"known_by": list(entry.known_by), "category": entry.category, "slug": entry.slug}
        item: dict[str, Any] = {
            **extra,
            "keys": list(entry.keys),
            "content": entry.content,
            "name": entry.title,
            "enabled": entry.enabled,
            "insertion_order": entry.position,
            "priority": entry.priority,
            "extensions": ext,
        }
        item.setdefault("comment", entry.title)
        item.setdefault("case_sensitive", False)
        items.append(item)
    if not items:
        return None
    return {"name": f"{card_name.strip()} · Thế giới", "entries": items}


__all__ = ["BookEntry", "book_entries", "book_of", "entries_to_book", "without_book"]
