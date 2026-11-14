"""Văn bản prompt theo ngôn ngữ: khối A (luật), B (nhân vật), C (bối cảnh), F (ghi chú cuối).

Mỗi ngôn ngữ là một module (vi.py, en.py) cung cấp một đối tượng `TEMPLATE` thoả `Template`.
Mọi hàm ở đây là hàm thuần của (card, persona, story, style): cùng đầu vào thì cùng chuỗi,
để system message giữ nguyên từng byte giữa các lượt (Ollama tái dùng prompt cache).
"""
from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Protocol

from lyris.models import CharacterCard, Language, Persona, SceneState, Story


@dataclass(frozen=True)
class PromptContext:
    card: CharacterCard
    persona: Persona
    story: Story
    style: str  # nội dung style profile đã chọn theo ngôn ngữ

    @property
    def char(self) -> str:
        return self.card.name.strip()

    @property
    def player(self) -> str:
        return self.persona.name.strip()

    def fill(self, text: str) -> str:
        """Thay `{{char}}` / `{{user}}` (chuẩn Character Card V2) bằng tên thật, bỏ khoảng trắng thừa."""
        text = _CHAR_PLACEHOLDER.sub(lambda _m: self.char, text)
        text = _USER_PLACEHOLDER.sub(lambda _m: self.player, text)
        return text.strip()


class Template(Protocol):
    story_start: str  # user giả chèn trước lời mở đầu của nhân vật
    story_continues: str  # user giả khi lượt cũ (kể cả lời mở đầu) đã bị cắt bớt
    empty_user_turn: str  # thay cho lượt cũ của người chơi chỉ có chỉ đạo, không có chữ
    dm_label: str  # nhãn đặt trước lượt DM khi story đang ở Story Mode (lịch sử chung hai mode)

    def rules(self, ctx: PromptContext) -> str:
        """Khối A theo `story.mode`."""
        ...

    def character(self, ctx: PromptContext) -> str:
        """Khối B: card + persona + xưng hô + style profile."""
        ...

    def dm_note(self, ctx: PromptContext) -> str:
        """Dòng khối F ở Story Mode khi cửa sổ lịch sử có lượt DM (mang `dm_label`): đó là tin nhắn thật đã
        gửi, nhân vật nhớ nội dung. Đặt ở F (không ở khối A) để story không có DM giữ nguyên từng byte."""
        ...

    def context(self, ctx: PromptContext, *, summary: str | None = None) -> str:
        """Khối C: bối cảnh + tóm tắt cảnh người dùng viết + tóm tắt tự động `summary` (Phase 3);
        chuỗi rỗng nếu không có gì."""
        ...

    def state_lines(
        self,
        ctx: PromptContext,
        *,
        scene: SceneState | None,
        directive: str | None,
        memories: Sequence[str],
        facts: Sequence[str],
    ) -> list[str]:
        """Các dòng state của khối F (Phase 3): cảnh, thái độ, chuyện cũ còn nhớ, điều đã biết.

        Rỗng nếu không có gì. Builder đã chọn và cắt `memories`/`facts`; ở đây chỉ viết thành chữ.
        """
        ...

    def final_note(
        self,
        ctx: PromptContext,
        *,
        directive: str | None,
        player_wrote: bool,
        avoid: Sequence[str] = (),
        state: Sequence[str] = (),
    ) -> str:
        """Khối F, nối vào cuối message user cuối. `avoid`: câu model đã dùng gần đây (xem `repetition.py`).

        `state`: các dòng từ `state_lines`, đặt ngay sau dòng tiêu đề, trước luật của lượt. Rỗng thì
        ghi chú giống hệt trước Phase 3.
        """
        ...

    def lore_header(self, ctx: PromptContext) -> str:
        """Phase 4, khối D: dòng mở của thông tin thế giới (đầu message user cuối, docs/phase4.md §6.3)."""
        ...

    def lore_item(self, ctx: PromptContext, title: str, text: str, private: bool) -> str:
        """Một dòng mục thế giới; `private`: chỉ nhân vật biết, dặn không tự kể ra."""
        ...

    def lore_footer(self, ctx: PromptContext) -> str:
        """Dòng đóng của khối D."""
        ...


_CHAR_PLACEHOLDER = re.compile(r"\{\{\s*char\s*\}\}", re.IGNORECASE)
_USER_PLACEHOLDER = re.compile(r"\{\{\s*user\s*\}\}", re.IGNORECASE)


def get_template(language: Language) -> Template:
    if language == "vi":
        from lyris.prompt.templates import vi

        return vi.TEMPLATE
    if language == "en":
        from lyris.prompt.templates import en

        return en.TEMPLATE
    raise ValueError(f"Ngôn ngữ chưa được hỗ trợ: {language!r}")


def unique(words: Iterable[str], *, exclude: Iterable[str] = ()) -> list[str]:
    """Bỏ từ rỗng, trùng (không phân biệt hoa thường) và các từ trong `exclude`, giữ thứ tự."""
    seen = {w.strip().casefold() for w in exclude if w.strip()}
    out: list[str] = []
    for word in words:
        w = word.strip()
        if w and w.casefold() not in seen:
            seen.add(w.casefold())
            out.append(w)
    return out


def quoted(words: list[str], conjunction: str) -> str:
    """`"a"`, `"a" hoặc "b"`, `"a", "b" hoặc "c"`."""
    q = [f'"{w}"' for w in words]
    if len(q) <= 1:
        return "".join(q)
    return f"{', '.join(q[:-1])} {conjunction} {q[-1]}"


def sentence(text: str) -> str:
    """Thêm dấu chấm nếu câu chưa kết thúc bằng dấu câu."""
    text = text.strip()
    core = text.rstrip("\"'”’)»")
    if core and core[-1] not in ".!?…":
        text += "."
    return text


def scene_text(scene: SceneState | None) -> str:
    """`"Thư viện, chiều tối"` từ cảnh hiện tại; rỗng nếu chưa biết gì."""
    if scene is None:
        return ""
    return ", ".join(p.strip() for p in (scene.location, scene.time) if p and p.strip())


def lead_in(head: str, rest: str) -> str:
    """Nối `"Lạc Dương, nam"` với mô tả: `", 20 tuổi..."` hoặc `". Sinh viên..."` nếu mô tả viết hoa đầu câu."""
    rest = rest.strip()
    if not rest:
        return sentence(head)
    sep = ". " if rest[0].isupper() else ", "
    return sentence(head + sep + rest)
