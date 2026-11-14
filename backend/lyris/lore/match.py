"""So khớp từ khoá của sổ thế giới trên văn bản (docs/phase4.md §5.2). Hàm thuần.

- Khoá không có chữ Hán: khớp trọn âm tiết, trọn cụm (`" " + key + " "` nằm trong `match_form(text)`).
- Khoá có chữ Hán: so chuỗi con trên dạng đã bỏ mọi khoảng trắng và dấu câu (`cjk_form`).
- Không bao giờ khớp: khoá trùng tên nhân vật / persona (`ignore`), khoá chỉ là `{{user}}`/`{{char}}`,
  khoá dưới 2 ký tự. Khoá có placeholder ở giữa phải được `fill` TRƯỚC khi đưa vào đây.
- `names_only=True` (lượt của nhân vật, kể cả lời mở đầu): chỉ khoá dạng tên riêng (`is_name_like`).

Matcher được dựng lại mỗi lượt (không cache): vài chục mục x vài khoá, quét chỉ là `in` trên chuỗi.
"""
from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from lyris.lore.normalize import cjk_form, has_cjk, is_name_like, match_form, strip_parens

PLACEHOLDER_ONLY = re.compile(r"^\s*\{\{\s*(user|char)\s*\}\}\s*$", re.IGNORECASE)
MIN_KEY_CHARS = 2


@dataclass(frozen=True)
class _Key:
    entry_id: int
    form: str  # match_form (" a b ") hoặc cjk_form
    cjk: bool
    name_like: bool


def usable_key(key: str, ignore_forms: set[str]) -> bool:
    """Khoá có dùng để so khớp được không (đã fill placeholder)."""
    k = key.strip()
    if len(k) < MIN_KEY_CHARS or PLACEHOLDER_ONLY.match(k):
        return False
    form = match_form(k)
    if not form.strip():
        return False
    return form not in ignore_forms and match_form(strip_parens(k)) not in ignore_forms


def ignore_forms(names: Iterable[str]) -> set[str]:
    """Dạng so khớp của tên nhân vật / persona (cả bản bỏ phần trong ngoặc)."""
    out: set[str] = set()
    for name in names:
        if not name or not name.strip():
            continue
        for variant in (name, strip_parens(name)):
            form = match_form(variant)
            if form.strip():
                out.add(form)
    return out


class LoreMatcher:
    """`LoreMatcher([(entry_id, keys), ...], ignore=(tên nhân vật, tên persona)).scan(text)`."""

    def __init__(self, entries: Iterable[tuple[int, Sequence[str]]], *, ignore: Iterable[str] = ()) -> None:
        skip = ignore_forms(ignore)
        self._keys: list[_Key] = []
        for entry_id, keys in entries:
            for key in keys:
                if not isinstance(key, str) or not usable_key(key, skip):
                    continue
                k = key.strip()
                if has_cjk(k):
                    self._keys.append(_Key(entry_id, cjk_form(k), True, True))
                else:
                    self._keys.append(_Key(entry_id, match_form(k), False, is_name_like(k)))

    @property
    def empty(self) -> bool:
        return not self._keys

    def scan(self, text: str, *, names_only: bool = False) -> dict[int, int]:
        """{entry_id: vị trí khớp sớm nhất} trên `text`. Vị trí chỉ dùng để xếp thứ tự, tất định."""
        if not text or not self._keys:
            return {}
        form = match_form(text)
        cjk: str | None = None
        found: dict[int, int] = {}
        for key in self._keys:
            if names_only and not key.name_like:
                continue
            if key.cjk:
                if cjk is None:
                    cjk = cjk_form(text)
                pos = cjk.find(key.form)
            else:
                pos = form.find(key.form)
            if pos < 0:
                continue
            if key.entry_id not in found or pos < found[key.entry_id]:
                found[key.entry_id] = pos
        return found


def key_matches(key: str, text: str) -> bool:
    """Một khoá có khớp `text` không (cùng luật với LoreMatcher, không có danh sách bỏ qua)."""
    return bool(LoreMatcher([(0, [key])]).scan(text))


__all__ = ["LoreMatcher", "MIN_KEY_CHARS", "PLACEHOLDER_ONLY", "ignore_forms", "key_matches", "usable_key"]
