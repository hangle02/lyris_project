#!/usr/bin/env python
"""Chạy các kịch bản roleplay trong harness/scenarios/*.yaml qua một model Ollama và chấm điểm.

Mỗi kịch bản: dựng prompt bằng đúng `lyris.prompt.builder.build_prompt` của app (card, persona,
thiết lập story: mặc định là seed Lạc Dương, hoặc bộ card trong harness/cards/ qua khoá `card:`),
stream câu trả lời qua `lyris.llm.ollama.OllamaClient`, chạy kiểm tra máy (checks.py), rồi nhờ một model chấm (judge, mặc định gemma4:e4b) xét godmodding và việc bám
sát lượt người chơi.

Kịch bản có khoá `kind` khác `reply` (trích xuất, tóm tắt, gợi ý, viết nháp, nhiều lượt DM, TTFT qua app thật, bake-off,
chạy lồng) được chạy bằng harness/kinds.py: chỉ luật máy, không judge. Cách viết kịch bản: harness/README.md.

Kết quả ghi vào harness/results/eval-<thời gian>/:
  report.md  bảng tóm tắt + toàn bộ câu trả lời
  raw.json   dữ liệu thô (prompt, câu trả lời, số liệu, phán quyết)

Chạy từ thư mục gốc dự án, bằng Python của backend:
  backend/.venv/bin/python harness/run_eval.py --model gemma4:12b
  backend/.venv/bin/python harness/run_eval.py --model gemma4:12b --only 04-chi-dao --no-judge
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, get_args

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
BACKEND_DIR = REPO_ROOT / "backend"
for _p in (HERE, BACKEND_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import httpx  # noqa: E402
import yaml  # noqa: E402
from checks import run_checks, strip_thoughts, word_count  # noqa: E402
from kinds import KIND_KEYS, KINDS, META_KINDS, Env, Outcome, SpecError, fresh_prompt_state, parse_spec, run_kind  # noqa: E402

from lyris.config import get_settings  # noqa: E402
from lyris.llm.base import Done, LLMError, TextDelta  # noqa: E402
from lyris.llm.ollama import OllamaClient  # noqa: E402
from lyris.llm.thought import split_thought  # noqa: E402
from lyris.lore.select import lore_for_history  # noqa: E402
from lyris.models import (  # noqa: E402
    BuiltPrompt,
    CharacterCard,
    ChatTurn,
    LoreEntry,
    Message,
    Mode,
    Persona,
    Story,
    StorySettings,
)
from lyris.prompt.builder import PromptBudget, build_prompt  # noqa: E402
from lyris.prompt.directives import extract_directives  # noqa: E402
from lyris.prompt.templates import PromptContext, get_template  # noqa: E402
from lyris.seed import load_default_story_settings, load_seed_card, load_seed_persona  # noqa: E402

DEFAULT_SCENARIOS = HERE / "scenarios"
DEFAULT_CARDS = HERE / "cards"
RESULTS_DIR = HERE / "results"
DEFAULT_JUDGE_MODEL = "gemma4:e4b"
_MODES: tuple[str, ...] = get_args(Mode)
_SCENARIO_KEYS = {"id", "title", "note", "mode", "card", "history", "input", "checks", "judge", "kind", "thought_style", "lore"}
# Khoá chung của mọi loại kịch bản khác `reply` (phần riêng: kinds.KIND_KEYS).
_COMMON_KEYS = {"id", "title", "note", "mode", "card", "kind"}
_LORE_KEYS = {"title", "keys", "known_by", "content", "category"}
_CHECK_KEYS = {
    "thought_count",
    "min_thoughts",
    "max_thoughts",
    "no_adjacent_thoughts",
    "thought_at_end",
    "narration_forbidden",
    "max_words",
    "min_words",
    "forbidden_phrases",
    "directive_leak",
    "persona_line",
    "language",
    "dialogue_forbidden",
    "dialogue_required_any",
    "directive_echo",
    "say_forbidden",
    "forbidden_patterns",
    "required_any",
    "prompt_includes",
    "prompt_excludes",
}
_LIST_CHECKS = (
    "narration_forbidden",
    "forbidden_phrases",
    "dialogue_forbidden",
    "dialogue_required_any",
    "say_forbidden",
    "forbidden_patterns",
    "required_any",
    "prompt_includes",
    "prompt_excludes",
)
_LANGUAGES = ("vi", "en")
_CARD_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")

# Thứ tự thuộc tính: `reason` trước để model chấm nêu lý do rồi mới kết luận.
JUDGE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "reason": {"type": "string"},
        "godmodding": {"type": "boolean"},
        "follows_player": {"type": "boolean"},
    },
    "required": ["godmodding", "follows_player", "reason"],
}
APP_NUM_CTX = 8192  # environment/rules.md: num_ctx luôn 8192 cho mọi lời gọi
DEFAULT_DEADLINE_MIN = 50.0
JUDGE_OPTIONS: dict[str, Any] = {"temperature": 0, "num_ctx": 8192, "num_predict": 512}
_PREV_TURN_CHARS = 2000


class ScenarioError(ValueError):
    """File kịch bản sai định dạng."""


# ---- kịch bản ----------------------------------------------------------------------------------


@dataclass(frozen=True)
class HistoryItem:
    role: str
    content: str
    mode: str | None = None  # None = mode của story; "dm" trong story Story Mode = lượt nhắn tin (F12)


@dataclass(frozen=True)
class Scenario:
    id: str
    title: str
    mode: str
    input: str
    checks: dict[str, Any]
    path: Path
    history: tuple[HistoryItem, ...] | None = None  # None = dùng lời mở đầu của card
    note: str = ""
    judge: bool = True
    card: str | None = None  # tên file trong harness/cards/ (có .json); None = seed Lạc Dương
    kind: str = "reply"  # xem kinds.KINDS
    spec: dict[str, Any] = field(default_factory=dict)  # phần riêng của loại khác `reply` (kinds.parse_spec)
    thought_style: str | None = None  # ghi đè thought_style của story (CLI --thought-style vẫn thắng)
    lore: tuple[dict[str, Any], ...] = ()  # mục thế giới của card cho lượt này (F17)


def _require_str(data: dict[str, Any], key: str, where: str, *, allow_empty: bool = False) -> str:
    value = data.get(key)
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise ScenarioError(f"{where}: trường `{key}` phải là chuỗi không rỗng")
    return value


def _parse_card(data: dict[str, Any], where: str) -> str | None:
    if data.get("card") is None:
        return None
    raw_card = data["card"]
    if not isinstance(raw_card, str) or not _CARD_NAME.fullmatch(raw_card.strip()):
        raise ScenarioError(f"{where}: `card` phải là tên file trong harness/cards/, ví dụ viet_hien_dai.json")
    card = raw_card.strip()
    return card if card.endswith(".json") else card + ".json"


def _parse_head(data: dict[str, Any], where: str) -> tuple[str, str, str, str]:
    """(id, mode, title, note) chung của mọi loại kịch bản."""
    sid = _require_str(data, "id", where).strip()
    mode = data.get("mode", "story")
    if mode not in _MODES:
        raise ScenarioError(f"{where}: `mode` phải là một trong {list(_MODES)}, đang là {mode!r}")
    note = data.get("note") or ""
    if not isinstance(note, str):
        raise ScenarioError(f"{where}: `note` phải là chuỗi")
    title = data.get("title") or sid
    if not isinstance(title, str):
        raise ScenarioError(f"{where}: `title` phải là chuỗi")
    return sid, mode, title.strip(), note.strip()


def parse_checks(checks: Any, where: str) -> dict[str, Any]:
    """`checks` của lượt trả lời (dùng cho `reply` và `dm_session`)."""
    checks = checks or {}
    if not isinstance(checks, dict):
        raise ScenarioError(f"{where}: `checks` phải là mapping")
    bad_checks = set(checks) - _CHECK_KEYS
    if bad_checks:
        raise ScenarioError(f"{where}: kiểm tra không hỗ trợ {sorted(bad_checks)}; có: {sorted(_CHECK_KEYS)}")
    for key in ("thought_count", "min_thoughts", "max_thoughts", "max_words", "min_words"):
        if key in checks and (not isinstance(checks[key], int) or isinstance(checks[key], bool) or checks[key] < 0):
            raise ScenarioError(f"{where}: `checks.{key}` phải là số nguyên không âm")
    for key in _LIST_CHECKS:
        if key in checks and (
            not isinstance(checks[key], list) or not all(isinstance(w, str) and w.strip() for w in checks[key])
        ):
            raise ScenarioError(f"{where}: `checks.{key}` phải là list chuỗi không rỗng")
    for pattern in checks.get("forbidden_patterns") or []:
        try:
            re.compile(pattern)
        except re.error as exc:
            raise ScenarioError(f"{where}: `checks.forbidden_patterns` có regex hỏng {pattern!r}: {exc}") from exc
    if "language" in checks and checks["language"] not in _LANGUAGES:
        raise ScenarioError(f"{where}: `checks.language` phải là một trong {list(_LANGUAGES)}")
    return dict(checks)


def _parse_lore(value: Any, where: str) -> tuple[dict[str, Any], ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not value:
        raise ScenarioError(f"{where}: `lore` phải là list mục {{title, keys, known_by, content}}")
    out: list[dict[str, Any]] = []
    for i, item in enumerate(value):
        if not isinstance(item, dict) or set(item) - _LORE_KEYS or not {"title", "keys", "content"} <= set(item):
            raise ScenarioError(f"{where}: lore[{i}] cần title, keys, content (known_by, category tuỳ chọn)")
        for key in ("title", "content"):
            if not isinstance(item[key], str) or not item[key].strip():
                raise ScenarioError(f"{where}: lore[{i}].{key} phải là chuỗi không rỗng")
        for key in ("keys", "known_by"):
            if key in item and (
                not isinstance(item[key], list) or not all(isinstance(k, str) and k.strip() for k in item[key])
            ):
                raise ScenarioError(f"{where}: lore[{i}].{key} phải là list chuỗi không rỗng")
        out.append(dict(item))
    return tuple(out)


def parse_scenario(data: Any, path: Path) -> Scenario:
    where = path.name
    if not isinstance(data, dict):
        raise ScenarioError(f"{where}: nội dung phải là một mapping YAML")
    kind = data.get("kind", "reply")
    if kind not in KINDS:
        raise ScenarioError(f"{where}: `kind` phải là một trong {list(KINDS)}, đang là {kind!r}")
    allowed = _SCENARIO_KEYS if kind == "reply" else _COMMON_KEYS | KIND_KEYS[kind]
    unknown = set(data) - allowed
    if unknown:
        raise ScenarioError(f"{where}: trường lạ {sorted(unknown)}")
    if kind != "reply":
        sid, mode, title, note = _parse_head(data, where)
        try:
            spec = parse_spec(kind, data, where)
        except SpecError as exc:
            raise ScenarioError(str(exc)) from exc
        return Scenario(
            id=sid, title=title, mode=mode, input="", checks={}, path=path, note=note, judge=False,
            card=_parse_card(data, where), kind=kind, spec=spec,
        )

    sid = _require_str(data, "id", where).strip()
    mode = data.get("mode", "story")
    if mode not in _MODES:
        raise ScenarioError(f"{where}: `mode` phải là một trong {list(_MODES)}, đang là {mode!r}")
    text = _require_str(data, "input", where)
    checks = parse_checks(data.get("checks"), where)
    card = _parse_card(data, where)

    history: tuple[HistoryItem, ...] | None = None
    if "history" in data and data["history"] is not None:
        raw_history = data["history"]
        if not isinstance(raw_history, list):
            raise ScenarioError(f"{where}: `history` phải là list {{role, content}}")
        items: list[HistoryItem] = []
        for i, item in enumerate(raw_history):
            if not isinstance(item, dict) or set(item) - {"role", "content", "mode"}:
                raise ScenarioError(f"{where}: history[{i}] phải có đúng hai trường role, content (mode tuỳ chọn)")
            role = item.get("role")
            if role not in ("user", "assistant"):
                raise ScenarioError(f"{where}: history[{i}].role phải là user hoặc assistant")
            content = item.get("content")
            if not isinstance(content, str) or not content.strip():
                raise ScenarioError(f"{where}: history[{i}].content phải là chuỗi không rỗng")
            item_mode = item.get("mode")
            if item_mode is not None and item_mode not in _MODES:
                raise ScenarioError(f"{where}: history[{i}].mode phải là một trong {list(_MODES)}")
            items.append(HistoryItem(role=role, content=content, mode=item_mode))
        history = tuple(items)

    judge = data.get("judge", True)
    if not isinstance(judge, bool):
        raise ScenarioError(f"{where}: `judge` phải là true/false")
    thought_style = data.get("thought_style")
    if thought_style is not None and thought_style not in ("inline", "end"):
        raise ScenarioError(f"{where}: `thought_style` phải là inline hoặc end")
    _, _, title, note = _parse_head(data, where)
    return Scenario(
        id=sid,
        title=title,
        mode=mode,
        input=text,
        checks=checks,
        path=path,
        history=history,
        note=note,
        judge=judge,
        card=card,
        thought_style=thought_style,
        lore=_parse_lore(data.get("lore"), where),
    )


def load_scenarios(directory: Path, only: list[str] | None = None) -> list[Scenario]:
    """Đọc mọi *.yaml / *.yml trong `directory`, theo tên file. `only` lọc theo id."""
    if not directory.is_dir():
        raise ScenarioError(f"Không có thư mục kịch bản: {directory}")
    files = sorted([*directory.glob("*.yaml"), *directory.glob("*.yml")])
    scenarios: list[Scenario] = []
    seen: dict[str, Path] = {}
    for path in files:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise ScenarioError(f"{path.name}: YAML lỗi: {exc}") from exc
        scenario = parse_scenario(data, path)
        if scenario.id in seen:
            raise ScenarioError(f"Trùng id kịch bản {scenario.id!r}: {seen[scenario.id].name} và {path.name}")
        seen[scenario.id] = path
        scenarios.append(scenario)
    if not scenarios:
        raise ScenarioError(f"Không có file kịch bản .yaml nào trong {directory}")
    if only:
        missing = [sid for sid in only if sid not in seen]
        if missing:
            raise ScenarioError(f"Không có kịch bản id {missing}; các id hiện có: {sorted(seen)}")
        scenarios = [s for s in scenarios if s.id in only]
    return scenarios


# ---- dựng prompt -------------------------------------------------------------------------------


@dataclass(frozen=True)
class SeedSetup:
    """Card + persona + thiết lập story của một kịch bản (seed hoặc bộ card trong harness/cards/)."""

    card: CharacterCard
    persona: Persona
    story_settings: dict[str, Any]
    source: str = "seed"  # "seed" hoặc tên file bộ card

    def names(self) -> list[str]:
        """Tên riêng bỏ qua khi kiểm tra ngôn ngữ/xưng hô: nhân vật, persona, tên thân mật."""
        out: list[str] = []
        for name in (self.card.name, self.persona.name, *self.card.address_terms.nicknames):
            if name.strip() and name.strip() not in out:
                out.append(name.strip())
        return out


class CardBundleError(ValueError):
    """File bộ card trong harness/cards/ sai định dạng."""


_BUNDLE_KEYS = {"card", "persona", "story"}


def load_seed() -> SeedSetup:
    """Card, persona, thiết lập story seed (id giả = 1, không chạm DB)."""
    return SeedSetup(
        card=load_seed_card().model_copy(update={"id": 1}),
        persona=load_seed_persona().model_copy(update={"id": 1}),
        story_settings=load_default_story_settings(),
    )


def load_card_bundle(path: Path) -> SeedSetup:
    """Đọc bộ card JSON `{"card": CharacterCard, "persona": Persona, "story": StorySettings + title}`."""
    where = path.name
    if not path.is_file():
        raise CardBundleError(f"Không có file bộ card: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CardBundleError(f"{where}: không đọc được JSON: {exc}") from exc
    if not isinstance(data, dict) or set(data) != _BUNDLE_KEYS:
        raise CardBundleError(f"{where}: phải là object có đúng ba khoá card, persona, story")
    story = data["story"]
    if not isinstance(story, dict):
        raise CardBundleError(f"{where}: `story` phải là object")
    title = story.get("title")
    if not isinstance(title, str) or not title.strip():
        raise CardBundleError(f"{where}: `story.title` phải là chuỗi không rỗng")
    unknown = set(story) - set(StorySettings.model_fields) - {"title"}
    if unknown:
        raise CardBundleError(f"{where}: `story` có trường lạ {sorted(unknown)}")
    try:
        card = CharacterCard.model_validate({**data["card"], "id": 1})
        persona = Persona.model_validate({**data["persona"], "id": 1})
        settings = StorySettings.model_validate({k: v for k, v in story.items() if k != "title"})
    except (TypeError, ValueError) as exc:
        raise CardBundleError(f"{where}: dữ liệu không hợp lệ: {exc}") from exc
    return SeedSetup(
        card=card,
        persona=persona,
        story_settings={"title": title.strip(), **settings.model_dump()},
        source=where,
    )


def load_setup(scenario: Scenario, cards_dir: Path = DEFAULT_CARDS) -> SeedSetup:
    """Thiết lập cho kịch bản: bộ card nếu có khoá `card`, không thì seed."""
    if scenario.card is None:
        return load_seed()
    try:
        return load_card_bundle(cards_dir / scenario.card)
    except CardBundleError as exc:
        raise ScenarioError(f"{scenario.path.name}: {exc}") from exc


def load_setups(scenarios: list[Scenario], cards_dir: Path = DEFAULT_CARDS) -> dict[str, SeedSetup]:
    """Thiết lập theo id kịch bản; mỗi file bộ card chỉ đọc một lần."""
    cache: dict[str | None, SeedSetup] = {}
    out: dict[str, SeedSetup] = {}
    for s in scenarios:
        if s.card not in cache:
            cache[s.card] = load_setup(s, cards_dir)
        out[s.id] = cache[s.card]
    return out


def make_story(seed: SeedSetup, mode: str, model_name: str, thought_style: str | None = None) -> Story:
    data = {**seed.story_settings, "id": 1, "card_id": 1, "persona_id": 1, "mode": mode, "model_name": model_name}
    if thought_style:
        data["thought_style"] = thought_style
    return Story.model_validate(data)


def make_message(story: Story, turn_index: int, role: str, content: str, mode: str | None = None) -> Message:
    """Message như app lưu: user tách `((...))`, assistant tách `[Thought: ...]`. `mode` None = mode của story."""
    mode = mode or story.mode
    if role == "user":
        visible, directive = extract_directives(content)
        return Message(
            story_id=story.id or 1,
            turn_index=turn_index,
            role="user",
            mode=mode,
            raw_content=content,
            visible_content=visible,
            directive=directive,
        )
    visible, thought = split_thought(content)
    return Message(
        story_id=story.id or 1,
        turn_index=turn_index,
        role="assistant",
        mode=mode,
        raw_content=content,
        visible_content=visible,
        thought=thought,
        model_output=content,
    )


def scenario_history(scenario: Scenario, seed: SeedSetup, story: Story) -> list[Message]:
    """Lịch sử active: lời mở đầu (hoặc `history` của kịch bản) + lượt `input` của người chơi.

    Như khi app tạo story: `{{char}}`/`{{user}}` trong lời mở đầu và lịch sử được thay bằng tên thật.
    """
    ctx = PromptContext(card=seed.card, persona=seed.persona, story=story, style="")
    if scenario.history is None:
        items = [HistoryItem("assistant", ctx.fill(seed.card.greeting))] if seed.card.greeting.strip() else []
    else:
        items = [HistoryItem(item.role, ctx.fill(item.content), item.mode) for item in scenario.history]
    items.append(HistoryItem("user", scenario.input))
    return [make_message(story, i, item.role, item.content, item.mode) for i, item in enumerate(items)]


def checks_for_style(scenario: Scenario, thought_style: str | None) -> dict[str, Any]:
    """Với `--thought-style end`, kịch bản Story đòi đúng một Thought thay cho khoảng min/max."""
    checks = dict(scenario.checks)
    if thought_style == "end" and scenario.mode == "story" and ("min_thoughts" in checks or "max_thoughts" in checks):
        checks.pop("min_thoughts", None)
        checks.pop("max_thoughts", None)
        checks.pop("no_adjacent_thoughts", None)
        checks["thought_count"] = 1
        checks["thought_at_end"] = True
    return checks


def lore_entries(scenario: Scenario) -> list[LoreEntry]:
    """Mục thế giới của kịch bản như app lưu trong DB (id 1.., card 1, bật)."""
    return [
        LoreEntry(
            id=i,
            card_id=1,
            slug=f"muc-{i}",
            title=item["title"],
            category=item.get("category", "lore"),
            keys=list(item["keys"]),
            known_by=list(item.get("known_by", ["*"])),
            content=item["content"],
            position=i,
        )
        for i, item in enumerate(scenario.lore, 1)
    ]


def build_scenario_prompt(
    scenario: Scenario, seed: SeedSetup, model_name: str, budget: PromptBudget, thought_style: str | None = None
) -> tuple[Story, list[Message], BuiltPrompt]:
    """Prompt như ChatService dựng: `thought_style` (CLI) thắng `scenario.thought_style`; có `lore` thì chọn mục
    bằng đúng `lore_for_history` như `LoreService.prompt_lore`; khối F có chỉ dẫn diễn xuất từ 6 chỉ số ban đầu
    (`fresh_prompt_state`, như story mới trong app: chưa có tóm tắt, cảnh, ký ức)."""
    story = make_story(seed, scenario.mode, model_name, thought_style or scenario.thought_style)
    history = scenario_history(scenario, seed, story)
    lore = None
    if scenario.lore:
        ctx = PromptContext(card=seed.card, persona=seed.persona, story=story, style="")
        lore = lore_for_history(lore_entries(scenario), tpl=get_template(story.language), ctx=ctx, history=history)
    state = fresh_prompt_state(seed.card, seed.persona, story)  # như ChatService.prompt_state với story mới
    built = build_prompt(seed.card, seed.persona, story, history, budget=budget, lore=lore, state=state)
    return story, history, built


def prompt_problems(built: BuiltPrompt, checks: dict[str, Any]) -> list[str]:
    """Kiểm tra trên prompt đã dựng (tất định, trước khi gọi model): cụm phải có / không được có."""
    text = "\n".join(m.content for m in built.messages).casefold()
    problems = [f'prompt thiếu "{p}"' for p in checks.get("prompt_includes") or [] if p.casefold() not in text]
    problems += [f'prompt có "{p}" (không được gửi cho model)' for p in checks.get("prompt_excludes") or [] if p.casefold() in text]
    return problems


# ---- judge -------------------------------------------------------------------------------------


def judge_system_prompt(char: str, player: str, mode: str) -> str:
    c, p = char, player
    if mode == "dm":
        setting = (
            f"Đây là chế độ nhắn tin: câu trả lời cần chấm là tin nhắn {c} gửi cho {p}. "
            f"Người chơi điều khiển {p}; AI đóng vai {c}."
        )
    else:
        setting = (
            f"Đây là truyện tương tác: AI vừa dẫn truyện vừa đóng vai {c}; người chơi điều khiển {p}. "
            f"Dòng [Thought: ...] là suy nghĩ thầm của {c}."
        )
    return f"""Bạn là giám khảo chấm câu trả lời của một AI nhập vai. {setting}
Chấm đúng hai tiêu chí dưới đây, chỉ dựa vào văn bản được đưa, không suy diễn thêm. Hai tiêu chí độc lập với nhau. Không chấm văn phong, độ dài hay chính tả.

1. godmodding: AI có viết thay phần của người chơi hay không.
ĐƯỢC PHÉP, không phải godmodding:
- {c} phản ứng với lời nói, hành động, trạng thái mà người chơi đã viết cho {p}, kể cả tả lại chính những điều đó qua mắt {c} (người chơi viết "run rẩy" thì tả vai {p} đang run; người chơi viết "cúi đầu im lặng" thì tả {p} cúi đầu không nói).
- Nhắc lại, kể lại hay trích lại nguyên văn lời nói và hành động mà người chơi ĐÃ viết cho {p} trong lượt vừa rồi. Đây không phải lời hay hành động mới, nên không phải godmodding.
- Tả thêm trạng thái nhỏ, không chủ ý của {p} mà {c} nhìn thấy hoặc cảm nhận được, miễn hợp với điều người chơi viết: má ửng đỏ, chóp mũi đỏ vì lạnh, bàn tay lạnh, mắt còn ngái ngủ, tóc rối, hơi thở.
- {c} đoán cảm xúc của {p} trong suy nghĩ của mình (dòng [Thought: ...]) hoặc bằng lời phỏng đoán như "hình như", "có vẻ", "dường như".
- {c} làm những hành động mà người chơi đã viết cho {c}.
- {c} hỏi {p}, chạm vào {p}, hoặc dừng lại chờ {p} trả lời.
GODMODDING, chỉ cần một chỗ là tính:
- Lời thoại mới của {p}, tức câu mà người chơi không hề viết, kể cả lời gián tiếp ("cô đáp rằng...", "cô đồng ý").
- Hành động có chủ đích mới của {p} mà người chơi không viết: gật đầu, lắc đầu, đứng dậy, đi theo, cầm lấy, nắm tay, ôm, đẩy ra, cười đáp lại, quay đi, ngẩng lên nhìn...
- Khẳng định suy nghĩ, cảm xúc bên trong hay quyết định của {p} như thể người kể biết chắc ("cô thấy hạnh phúc", "trong lòng cô nghĩ...", "cô quyết định đi cùng").
- Kể tiếp quá chỗ cần {p} đáp lại, tức là tự quyết định {p} phản ứng thế nào.
Cách phân biệt: cơ thể hay nét mặt tự phản ứng (đỏ mặt, run, lạnh tay) là được phép; việc {p} chủ động nói, làm, nghĩ hay quyết định là godmodding. Trước khi kết luận có lời thoại hay hành động mới, hãy so với đúng lượt người chơi vừa viết: nếu người chơi đã viết điều đó thì không tính.

2. follows_player: câu trả lời có bám sát lượt người chơi vừa viết hay không. true khi đủ cả các điều sau, thiếu một điều là false:
- Tiếp nối trực tiếp từ đúng lời nói, hành động và hoàn cảnh người chơi vừa viết, đáp lại điều người chơi nói hoặc làm; không bỏ qua, không tự đổi cảnh, không nhảy thời gian, không lái sang chuyện khác.
- Nếu người chơi viết hành động cho {c}, câu trả lời thể hiện đúng các hành động đó.
- Nếu có chỉ đạo ẩn của người chơi: câu trả lời làm theo chỉ đạo, và không chép lại chỉ đạo (không có "((", không lặp nguyên văn hay gần nguyên văn câu chỉ đạo).

Trả về JSON gồm: reason (1-3 câu tiếng Việt; nếu có lỗi thì trích câu vi phạm trong dấu «...», không dùng dấu ngoặc kép), godmodding (true nếu có godmodding), follows_player (true nếu bám sát)."""


def judge_user_prompt(
    char: str, player: str, previous_ai: str | None, player_text: str, directive: str | None, reply: str
) -> str:
    prev = (previous_ai or "").strip()
    if len(prev) > _PREV_TURN_CHARS:
        prev = "..." + prev[-_PREV_TURN_CHARS:]
    wrote = player_text.strip() or "(người chơi không viết gì, chỉ có chỉ đạo ẩn)"
    parts = [
        f"Lượt trước của {char} (để biết bối cảnh):\n<<<\n{prev or '(không có)'}\n>>>",
        f"Lượt người chơi vừa viết cho {player} (phần trong *...* là hành động):\n<<<\n{wrote}\n>>>",
        f"Chỉ đạo ẩn của người chơi cho lượt này: {directive or 'không có'}",
        f"Câu trả lời của AI cần chấm:\n<<<\n{reply.strip()}\n>>>",
    ]
    return "\n\n".join(parts)


def judge_messages(
    seed: SeedSetup, mode: str, history: list[Message], reply: str
) -> list[dict[str, str]]:
    last_user = history[-1]
    previous_ai = next((m.raw_content for m in reversed(history[:-1]) if m.role == "assistant"), None)
    char, player = seed.card.name, seed.persona.name
    return [
        {"role": "system", "content": judge_system_prompt(char, player, mode)},
        {
            "role": "user",
            "content": judge_user_prompt(
                char, player, previous_ai, last_user.visible_content, last_user.directive, reply
            ),
        },
    ]


def parse_judge_content(content: str) -> dict[str, Any]:
    """Đọc JSON của judge; ValueError nếu sai dạng."""
    data = json.loads(content)
    if not isinstance(data, dict):
        raise ValueError("judge không trả về object JSON")
    god, follows, reason = data.get("godmodding"), data.get("follows_player"), data.get("reason")
    if not isinstance(god, bool) or not isinstance(follows, bool):
        raise ValueError(f"judge thiếu godmodding/follows_player kiểu bool: {content[:200]!r}")
    return {"godmodding": god, "follows_player": follows, "reason": reason.strip() if isinstance(reason, str) else ""}


async def call_judge(
    http: httpx.AsyncClient, model: str, messages: list[dict[str, str]]
) -> dict[str, Any]:
    """Gọi /api/chat không stream, format = JSON schema. Trả dict phán quyết hoặc {"error": ...}."""
    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
        "think": False,
        "format": JUDGE_SCHEMA,
        "keep_alive": "5m",
        "options": JUDGE_OPTIONS,
    }
    start = time.perf_counter()
    try:
        for attempt in range(2):
            resp = await http.post("/api/chat", json=body)
            if resp.status_code == 400 and attempt == 0 and "think" in resp.text.lower():
                del body["think"]
                continue
            break
    except httpx.HTTPError as exc:
        return {"error": f"Không gọi được judge qua Ollama: {exc or type(exc).__name__}"}
    if resp.status_code != 200:
        return {"error": f"Judge lỗi HTTP {resp.status_code}: {resp.text.strip()[:300]}"}
    try:
        content = resp.json()["message"]["content"]
        verdict = parse_judge_content(content)
    except (ValueError, KeyError, TypeError) as exc:
        return {"error": f"Judge trả về dữ liệu không đọc được: {exc}"}
    verdict["judge_ms"] = (time.perf_counter() - start) * 1000
    return verdict


# ---- chạy --------------------------------------------------------------------------------------


@dataclass
class ScenarioResult:
    scenario: Scenario
    built: BuiltPrompt | None  # None với loại khác `reply`
    history: list[Message]
    setup: SeedSetup
    text: str = ""
    stats: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    problems: list[str] = field(default_factory=list)
    words: int = 0
    judge: dict[str, Any] | None = None
    details: dict[str, Any] = field(default_factory=dict)  # kết quả riêng của loại khác `reply`


async def generate(client: OllamaClient, model: str, built: BuiltPrompt) -> tuple[str, dict[str, Any], str | None]:
    """Stream câu trả lời. Trả (text, stats, lỗi). Khi lỗi giữa chừng vẫn giữ phần đã sinh."""
    parts: list[str] = []
    stats: dict[str, Any] = {}
    try:
        async for event in client.chat_stream(model, built.messages, stop=built.stop, options=built.options):
            if isinstance(event, TextDelta):
                parts.append(event.text)
            elif isinstance(event, Done):
                stats = event.stats.model_dump()
    except LLMError as exc:
        return "".join(parts), stats, str(exc)
    return "".join(parts), stats, None


async def warm_up(client: OllamaClient, model: str, num_ctx: int) -> float:
    """Nạp model với cùng num_ctx (để không bị nạp lại), trả số giây. LLMError nếu lỗi."""
    start = time.perf_counter()
    async for _ in client.chat_stream(
        model,
        [ChatTurn(role="user", content="Xin chào")],
        stop=[],
        options={"num_ctx": num_ctx, "num_predict": 1},
    ):
        pass
    return time.perf_counter() - start


async def unload(http: httpx.AsyncClient, model: str) -> None:
    try:
        await http.post("/api/generate", json={"model": model, "keep_alive": 0})
    except httpx.HTTPError:
        pass


def _fmt(x: float | None, nd: int = 1) -> str:
    return "-" if x is None else f"{x:.{nd}f}"


def _secs(ms: float | None) -> float | None:
    return None if ms is None else ms / 1000


def summary_table(results: list[ScenarioResult]) -> list[str]:
    lines = [
        "| Kịch bản | Mode | TTFT (s) | tok/s | Token ra | Prompt token | Từ | Lỗi máy | Godmodding | Bám sát |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        problems = ", ".join(r.problems) if r.problems else "không"
        if r.error:
            problems = f"LỖI: {r.error}" + (f"; {problems}" if r.problems else "")
        god = "-" if r.judge is None else ("lỗi judge" if "error" in r.judge else ("CÓ" if r.judge["godmodding"] else "không"))
        follows = "-" if r.judge is None else ("lỗi judge" if "error" in r.judge else ("có" if r.judge["follows_player"] else "KHÔNG"))
        lines.append(
            f"| {r.scenario.id} | {r.scenario.mode} | {_fmt(_secs(r.stats.get('ttft_ms')), 2)} "
            f"| {_fmt(r.stats.get('tok_per_s'))} | {r.stats.get('output_tokens', '-')} "
            f"| {r.stats.get('prompt_tokens', '-')} | {r.words} | {problems} | {god} | {follows} |"
        )
    return lines


def aggregate(results: list[ScenarioResult]) -> dict[str, Any]:
    def avg(xs: list[float | None]) -> float | None:
        vals = [x for x in xs if x is not None]
        return sum(vals) / len(vals) if vals else None

    judged = [r for r in results if r.judge is not None and "error" not in r.judge]
    return {
        "scenarios": len(results),
        "generation_errors": sum(1 for r in results if r.error),
        "with_machine_problems": sum(1 for r in results if r.problems),
        "avg_ttft_s": avg([_secs(r.stats.get("ttft_ms")) for r in results]),
        "avg_tok_per_s": avg([r.stats.get("tok_per_s") for r in results]),
        "judged": len(judged),
        "godmodding": sum(1 for r in judged if r.judge and r.judge["godmodding"]),
        "not_following": sum(1 for r in judged if r.judge and not r.judge["follows_player"]),
    }


def write_report(
    out: Path, args: argparse.Namespace, results: list[ScenarioResult], meta: dict[str, Any]
) -> None:
    agg = meta["aggregate"]
    md = [
        f"# Eval {meta['started_at']}",
        "",
        f"- Model: `{args.model}`" + (f" (nạp lần đầu {_fmt(meta.get('load_s'))} s)" if meta.get("load_s") is not None else ""),
        f"- Judge: {'tắt' if args.no_judge else '`' + args.judge_model + '`'}",
        f"- num_ctx: {args.num_ctx}; kịch bản: `{args.scenarios}`",
        f"- Kiểu Thought: {args.thought_style or 'theo thiết lập story của từng kịch bản'}",
        f"- TTFT trung bình {_fmt(agg['avg_ttft_s'], 2)} s, tốc độ sinh trung bình {_fmt(agg['avg_tok_per_s'])} tok/s",
        f"- Lỗi máy: {agg['with_machine_problems']}/{agg['scenarios']} kịch bản; "
        f"lỗi sinh: {agg['generation_errors']}; godmodding (judge): {agg['godmodding']}/{agg['judged']}; "
        f"không bám sát (judge): {agg['not_following']}/{agg['judged']}",
        "",
        "TTFT đo phía client; kịch bản đầu đã được nạp model trước (warm-up) nên không tính thời gian nạp.",
        "Judge là model nhỏ, có thể chấm sai: đọc lại câu trả lời bên dưới trước khi kết luận.",
        "",
        *summary_table(results),
        "",
    ]
    for r in results:
        s = r.scenario
        md += [f"## {s.id}: {s.title}", ""]
        if s.note:
            md += [f"_{s.note}_", ""]
        st = r.setup.story_settings
        if r.built is None:
            md += [
                f"Loại `{s.kind}`. Card: {r.setup.card.name} ({r.setup.source}), persona {r.setup.persona.name}, "
                f"ngôn ngữ {st.get('language', 'vi')}.",
                "",
                "**Kết quả:**",
                "",
                "```text",
                r.text.strip() or "(trống)",
                "```",
                "",
            ]
            if r.error:
                md += [f"**Lỗi khi sinh:** {r.error}", ""]
            md += [f"- Lỗi máy: {', '.join(r.problems) if r.problems else 'không'}", ""]
            continue
        last_user = r.history[-1]
        md += [
            f"Card: {r.setup.card.name} ({r.setup.source}), persona {r.setup.persona.name}, "
            f"ngôn ngữ {st.get('language', 'vi')}, style `{r.setup.card.style_profile}`.",
            "",
            f"Mode: {s.mode}. Lịch sử: {'lời mở đầu của card' if s.history is None else f'{len(s.history)} lượt riêng của kịch bản'}."
            f" Ước lượng token prompt: {r.built.token_estimate.get('total', '-')}, bỏ {r.built.dropped_turns} lượt.",
            "",
            "**Người chơi:**",
            "",
            *[f"> {line}" if line else ">" for line in s.input.splitlines()],
            "",
        ]
        if last_user.directive:
            md += [f"Chỉ đạo ẩn (đã tách): {last_user.directive}", ""]
        md += ["**Câu trả lời:**", "", "```text", r.text.strip() or "(trống)", "```", ""]
        if r.error:
            md += [f"**Lỗi khi sinh:** {r.error}", ""]
        md += [
            f"- TTFT {_fmt(_secs(r.stats.get('ttft_ms')), 2)} s, {_fmt(r.stats.get('tok_per_s'))} tok/s, "
            f"{r.stats.get('output_tokens', '-')} token ra, {r.stats.get('prompt_tokens', '-')} token prompt, "
            f"tổng {_fmt(_secs(r.stats.get('total_ms')))} s, done_reason {r.stats.get('done_reason', '-')}",
            f"- Số từ hiển thị: {r.words}",
            f"- Lỗi máy: {', '.join(r.problems) if r.problems else 'không'}",
        ]
        if r.judge is None:
            md.append("- Judge: không chấm")
        elif "error" in r.judge:
            md.append(f"- Judge: lỗi ({r.judge['error']})")
        else:
            md.append(
                f"- Judge: godmodding {'CÓ' if r.judge['godmodding'] else 'không'}, "
                f"bám sát {'có' if r.judge['follows_player'] else 'KHÔNG'}. {r.judge['reason']}"
            )
        md.append("")
    (out / "report.md").write_text("\n".join(md), encoding="utf-8")

    raw = {
        **meta,
        "args": {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()},
        "judge_schema": JUDGE_SCHEMA,
        "results": [
            {
                "id": r.scenario.id,
                "kind": r.scenario.kind,
                "title": r.scenario.title,
                "mode": r.scenario.mode,
                "file": r.scenario.path.name,
                "card": r.setup.source,
                "language": r.setup.story_settings.get("language", "vi"),
                "input": r.scenario.input,
                "checks": checks_for_style(r.scenario, args.thought_style),
                "prompt": r.built.model_dump() if r.built is not None else None,
                "reply": r.text,
                "visible": split_thought(r.text)[0] if r.text else "",
                "thought": split_thought(r.text)[1] if r.text else None,
                "stats": r.stats,
                "error": r.error,
                "problems": r.problems,
                "words": r.words,
                "judge": r.judge,
                "details": r.details,
            }
            for r in results
        ],
    }
    (out / "raw.json").write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")


async def run(
    args: argparse.Namespace,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
    results_dir: Path = RESULTS_DIR,
    report: dict[str, Any] | None = None,
    depth: int = 0,
) -> int:
    """Chạy toàn bộ. `transport`, `results_dir` chỉ dùng cho test (Ollama giả, thư mục tạm).

    `report` (nếu có) nhận `{"out": thư mục kết quả}`. `depth` > 0: lượt chạy lồng của kịch bản `nested_eval`;
    lượt đó không in dòng "Đã ghi kết quả vào" (verify.sh đọc đúng dòng đó của lượt ngoài cùng)."""
    try:
        scenarios = load_scenarios(Path(args.scenarios), args.only)
    except ScenarioError as exc:
        print(f"Lỗi kịch bản: {exc}", file=sys.stderr)
        return 2
    if depth > 0 and any(s.kind in META_KINDS for s in scenarios):
        print(f"Lỗi kịch bản: không chạy lồng được loại {sorted(META_KINDS)}", file=sys.stderr)
        return 2
    budget = PromptBudget(num_ctx=args.num_ctx)
    # Dựng prompt trước hết: lỗi bộ card / prompt builder lộ ra ngay, chưa tốn lời gọi model nào.
    results: list[ScenarioResult] = []
    try:
        setups = load_setups(scenarios, Path(args.cards))
    except ScenarioError as exc:
        print(f"Lỗi kịch bản: {exc}", file=sys.stderr)
        return 2
    for s in scenarios:
        setup = setups[s.id]
        if s.kind != "reply":
            results.append(ScenarioResult(scenario=s, built=None, history=[], setup=setup))
            continue
        try:
            _, history, built = build_scenario_prompt(s, setup, args.model, budget, args.thought_style)
        except ValueError as exc:  # style profile không có, lịch sử sai...
            print(f"Không dựng được prompt cho kịch bản {s.id}: {exc}", file=sys.stderr)
            return 2
        results.append(ScenarioResult(scenario=s, built=built, history=history, setup=setup))
    client = OllamaClient(args.ollama_url, transport=transport)

    try:
        models = await client.list_models()
    except LLMError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if args.model not in models and f"{args.model}:latest" not in models:
        print(f"Ollama chưa có model {args.model}. Hãy chạy: ollama pull {args.model}", file=sys.stderr)
        return 1
    use_judge = not args.no_judge
    if use_judge and args.judge_model not in models and f"{args.judge_model}:latest" not in models:
        print(f"Cảnh báo: Ollama chưa có judge {args.judge_model}; bỏ qua phần chấm.", file=sys.stderr)
        use_judge = False

    started = datetime.now()

    print(f"Nạp {args.model}...", flush=True)
    load_s: float | None = None
    try:
        load_s = await warm_up(client, args.model, args.num_ctx)
    except LLMError as exc:
        print(f"Không nạp được {args.model}: {exc}", file=sys.stderr)
        return 1

    deadline = time.monotonic() + max(0.0, args.deadline_min) * 60

    def remaining() -> float:
        return deadline - time.monotonic()

    async def run_nested(ids: list[str]) -> tuple[int, Path | None]:
        sub = argparse.Namespace(
            **{**vars(args), "only": list(ids), "no_judge": True, "keep_loaded": True,
               "deadline_min": max(0.0, remaining()) / 60}
        )
        info: dict[str, Any] = {}
        code = await run(sub, transport=transport, results_dir=results_dir, report=info, depth=depth + 1)
        return code, info.get("out")

    env = Env(
        client=client,
        model=args.model,
        num_ctx=args.num_ctx,
        ollama_url=args.ollama_url,
        make_story=make_story,
        make_message=make_message,
        generate=generate,
        budget=budget,
        transport=transport,
        results_dir=results_dir,
        run_nested=run_nested,
        depth=depth,
    )

    over = f"hết giờ chung của run_eval ({args.deadline_min:g} phút, --deadline-min)"
    for i, r in enumerate(results, 1):
        if remaining() <= 0:
            r.error = f"{over}: chưa chạy"
            print(f"  [{i}/{len(results)}] {r.scenario.id}: LỖI: {r.error}", flush=True)
            continue
        if r.built is None:
            try:
                outcome = await asyncio.wait_for(
                    run_kind(r.scenario.kind, r.scenario.spec, r.setup, env, r.scenario.mode), timeout=remaining()
                )
            except TimeoutError:
                outcome = Outcome(error=f"{over}: dừng giữa chừng")
            r.text, r.problems, r.error = outcome.text, outcome.problems, outcome.error
            r.stats, r.details = outcome.stats, outcome.details
            note = f"LỖI: {r.error}" if r.error else (", ".join(r.problems) or "ok")
            print(f"  [{i}/{len(results)}] {r.scenario.id} ({r.scenario.kind}): {note}", flush=True)
            continue
        try:
            r.text, r.stats, r.error = await asyncio.wait_for(generate(client, args.model, r.built), timeout=remaining())
        except TimeoutError:
            r.error = f"{over}: dừng giữa chừng"
            print(f"  [{i}/{len(results)}] {r.scenario.id}: LỖI: {r.error}", flush=True)
            continue
        checks = checks_for_style(r.scenario, args.thought_style)
        r.problems = (
            run_checks(
                r.text,
                checks,
                persona_name=r.setup.persona.name,
                names=r.setup.names(),
                dm=r.scenario.mode == "dm",
                directive=r.history[-1].directive,
            )
            if r.text
            else []
        )
        if not r.text and not r.error:
            r.problems = ["câu trả lời rỗng"]
        r.problems += prompt_problems(r.built, checks)
        r.words = word_count(strip_thoughts(r.text))
        note = ", ".join(r.problems) or "ok"
        if r.error:
            note = f"LỖI: {r.error}"
        print(
            f"  [{i}/{len(results)}] {r.scenario.id}: TTFT {_fmt(_secs(r.stats.get('ttft_ms')), 2)}s, "
            f"{_fmt(r.stats.get('tok_per_s'))} tok/s, {r.stats.get('output_tokens', '-')} token, {note}",
            flush=True,
        )

    http_timeout = httpx.Timeout(600, connect=5)
    async with httpx.AsyncClient(base_url=args.ollama_url, timeout=http_timeout, transport=transport) as http:
        if not args.keep_loaded:
            # Máy 24GB: nhả model chat (trước khi nạp judge).
            await unload(http, args.model)
        if use_judge:
            print(f"Chấm bằng {args.judge_model}...", flush=True)
            for r in results:
                if not r.scenario.judge or not r.text.strip() or r.built is None:
                    continue
                r.judge = await call_judge(
                    http, args.judge_model, judge_messages(r.setup, r.scenario.mode, r.history, r.text)
                )
                j = r.judge
                verdict = (
                    f"lỗi: {j['error']}" if "error" in j
                    else f"godmodding={j['godmodding']}, follows_player={j['follows_player']}"
                )
                print(f"  {r.scenario.id}: {verdict}", flush=True)
            if not args.keep_loaded:
                await unload(http, args.judge_model)

    meta = {
        "started_at": started.isoformat(timespec="seconds"),
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "model": args.model,
        "num_ctx": args.num_ctx,
        "deadline_min": args.deadline_min,
        "judge_model": args.judge_model if use_judge else None,
        "load_s": load_s,
        "aggregate": aggregate(results),
    }
    stamp = started.strftime("%Y%m%d-%H%M%S")
    out = results_dir / f"eval-{stamp}"
    n = 2
    while out.exists():  # hai lần chạy trong cùng một giây
        out = results_dir / f"eval-{stamp}-{n}"
        n += 1
    out.mkdir(parents=True)
    write_report(out, args, results, meta)
    if report is not None:
        report["out"] = out

    agg = meta["aggregate"]
    print()
    print("\n".join(summary_table(results)))
    print(
        f"\nTTFT tb {_fmt(agg['avg_ttft_s'], 2)} s, tốc độ sinh tb {_fmt(agg['avg_tok_per_s'])} tok/s; "
        f"lỗi máy {agg['with_machine_problems']}/{agg['scenarios']}; "
        f"godmodding {agg['godmodding']}/{agg['judged']}; không bám sát {agg['not_following']}/{agg['judged']}"
    )
    if depth == 0:
        print(f"Đã ghi kết quả vào {out}")
    else:
        print(f"(kết quả lượt chạy lồng: {out})")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    settings = get_settings()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default=settings.chat_model, help=f"model chat (mặc định {settings.chat_model})")
    ap.add_argument("--judge-model", default=DEFAULT_JUDGE_MODEL, help=f"model chấm (mặc định {DEFAULT_JUDGE_MODEL})")
    ap.add_argument("--no-judge", action="store_true", help="không gọi judge")
    ap.add_argument("--scenarios", default=str(DEFAULT_SCENARIOS), help="thư mục chứa *.yaml")
    ap.add_argument("--cards", default=str(DEFAULT_CARDS), help="thư mục chứa bộ card *.json cho khoá `card:`")
    ap.add_argument("--only", action="append", metavar="ID", help="chỉ chạy kịch bản có id này (lặp lại được)")
    ap.add_argument(
        "--num-ctx",
        type=int,
        default=APP_NUM_CTX,
        help=f"num_ctx (mặc định {APP_NUM_CTX} như app; không lấy LYRIS_NUM_CTX: đổi là phá cache prompt)",
    )
    ap.add_argument("--ollama-url", default=settings.ollama_url)
    ap.add_argument("--keep-loaded", action="store_true", help="không nhả model khỏi RAM sau khi chạy xong")
    ap.add_argument(
        "--deadline-min",
        type=float,
        default=DEFAULT_DEADLINE_MIN,
        help=f"hạn chung (phút, mặc định {DEFAULT_DEADLINE_MIN:g}): quá hạn thì kịch bản còn lại thành lỗi của riêng nó, "
        "run_eval vẫn ghi báo cáo và thoát 0 (verify.sh cắt run_eval ở 60 phút)",
    )
    ap.add_argument(
        "--thought-style",
        choices=["inline", "end"],
        default=None,
        help="ghi đè cách đặt Thought của story (mặc định theo thiết lập story của kịch bản)",
    )
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return asyncio.run(run(args))


if __name__ == "__main__":
    raise SystemExit(main())
