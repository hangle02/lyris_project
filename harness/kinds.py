"""Các loại kịch bản ngoài `reply` cho run_eval.py: chứng minh dòng "Model thật:" của wiki bằng luật máy.

Mỗi loại gọi ĐÚNG code app dùng (import `lyris.*`), num_ctx như app (8192), model chat của run_eval
(mặc định gemma4:12b). Không loại nào cần judge: mọi kiểm tra ở đây là luật máy.

  extract      `lyris.state.extract.extract_turn` trên từng lượt (`cases`): chiều thay đổi cảm xúc sau khi app
               kiểm tra (`validate`), ký ức / điều đã biết có đúng chi tiết của lượt.            (F09, F10)
  summarize    `lyris.memory.summarize.summarize` trên một đoạn story: tóm tắt giữ đủ chi tiết bắt buộc.  (F10)
  suggest      `lyris.state.suggest.suggest_replies` hai lần (lần hai = "Gợi ý khác", avoid = lần một).  (F15)
  draft        `lyris.studio.draft.draft_card` từ một dòng ý tưởng.                                       (F19)
  dm_session   nhiều lượt DM liên tiếp qua `build_prompt` + model chat: câu kết không lặp.               (F13)
  app_ttft     app THẬT trong tiến trình (`create_app`, worker, prefill, DB tạm): TTFT từng lượt.        (F14)
  bakeoff      `harness/bakeoff.py` (`run_bakeoff`) in bảng so sánh model.                                (F36)
  nested_eval  chạy lồng `run_eval` trên vài kịch bản, kiểm báo cáo được lưu.                             (F36)

Mỗi hàm `*_problems` là hàm thuần (không gọi model) để test được bằng dữ liệu giả.
"""
from __future__ import annotations

import asyncio
import contextlib
import io
import json
import re
import secrets
import shutil
import statistics
import tempfile
import time
import unicodedata
from collections import Counter
from collections.abc import Awaitable, Callable, Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from checks import language_problems, phrase_in, run_checks, strip_thoughts

from lyris.llm.base import LLMError
from lyris.models import (
    EMOTION_KEYS,
    CharacterCard,
    Message,
    Persona,
    RelationshipValues,
    SceneState,
    Story,
)

KINDS: tuple[str, ...] = (
    "reply",
    "extract",
    "summarize",
    "suggest",
    "draft",
    "dm_session",
    "app_ttft",
    "bakeoff",
    "nested_eval",
)
# Loại không được chạy lồng trong nested_eval (tránh đệ quy, tránh nhả model giữa chừng).
META_KINDS = frozenset({"bakeoff", "nested_eval"})

# Khoá riêng của từng loại (ngoài id, title, note, kind, card, mode).
KIND_KEYS: dict[str, frozenset[str]] = {
    "extract": frozenset({"cases"}),
    "summarize": frozenset({"previous", "messages", "required_all", "forbidden", "language"}),
    "suggest": frozenset({"history", "language", "max_overlap"}),
    "draft": frozenset({"idea", "language", "gender", "style_profile", "required_fields", "forbidden_warnings"}),
    "dm_session": frozenset(
        {"history", "turns", "checks", "max_same_ending", "ending_words", "max_same_tail", "reminders", "max_same_reminder"}
    ),
    "app_ttft": frozenset(
        {
            "preload", "turns", "max_ttft_s", "max_median_ttft_s", "after_shift", "max_turns", "probe_chars",
            "settle_timeout_s", "max_total_s",
        }
    ),
    "bakeoff": frozenset({"limit"}),
    "nested_eval": frozenset({"ids"}),
}

DELTA_EXPECT = ("up", "down", "zero", "nonzero")
DRAFT_FIELDS = ("name", "role", "personality", "greeting", "description", "scenario", "speech_style")


class SpecError(ValueError):
    """Phần riêng của một loại kịch bản sai định dạng."""


# ---- đọc kịch bản ------------------------------------------------------------------------------------


def _str(value: Any, where: str, *, empty: bool = False) -> str:
    if not isinstance(value, str) or (not empty and not value.strip()):
        raise SpecError(f"{where} phải là chuỗi không rỗng")
    return value


def _str_list(value: Any, where: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value):
        raise SpecError(f"{where} phải là list chuỗi không rỗng")
    return list(value)


def _int(value: Any, where: str, *, minimum: int = 0) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise SpecError(f"{where} phải là số nguyên >= {minimum}")
    return value


def _num(value: Any, where: str) -> float:
    if not isinstance(value, int | float) or isinstance(value, bool) or value <= 0:
        raise SpecError(f"{where} phải là số dương")
    return float(value)


def parse_turns(value: Any, where: str, *, need_last: str | None = None) -> list[dict[str, str]]:
    """List `{role, content, mode?}`; `need_last` = role bắt buộc của phần tử cuối."""
    if not isinstance(value, list) or not value:
        raise SpecError(f"{where} phải là list {{role, content}} không rỗng")
    out: list[dict[str, str]] = []
    for i, item in enumerate(value):
        if not isinstance(item, dict) or set(item) - {"role", "content", "mode"} or not {"role", "content"} <= set(item):
            raise SpecError(f"{where}[{i}] phải có role, content (và mode tuỳ chọn)")
        if item["role"] not in ("user", "assistant"):
            raise SpecError(f"{where}[{i}].role phải là user hoặc assistant")
        _str(item["content"], f"{where}[{i}].content")
        if "mode" in item and item["mode"] not in ("story", "dm"):
            raise SpecError(f"{where}[{i}].mode phải là story hoặc dm")
        out.append(dict(item))
    if need_last and out[-1]["role"] != need_last:
        raise SpecError(f"{where}: phần tử cuối phải là role {need_last}")
    return out


def _required_groups(value: Any, where: str) -> list[list[str]]:
    """List mà mỗi phần tử là một chuỗi hoặc list chuỗi (một trong các cách viết)."""
    if not isinstance(value, list) or not value:
        raise SpecError(f"{where} phải là list không rỗng")
    groups: list[list[str]] = []
    for i, item in enumerate(value):
        if isinstance(item, str) and item.strip():
            groups.append([item])
        else:
            groups.append(_str_list(item, f"{where}[{i}]"))
    return groups


def _expect(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not value:
        raise SpecError(f"{where} phải là mapping không rỗng")
    allowed = {"delta", "all_zero", "memory_any", "facts_any", "facts_owner"}
    if set(value) - allowed:
        raise SpecError(f"{where}: khoá lạ {sorted(set(value) - allowed)}; có: {sorted(allowed)}")
    out: dict[str, Any] = {}
    if "delta" in value:
        delta = value["delta"]
        if not isinstance(delta, dict) or not delta:
            raise SpecError(f"{where}.delta phải là mapping chỉ số -> up/down/zero/nonzero")
        for k, v in delta.items():
            if k not in EMOTION_KEYS or v not in DELTA_EXPECT:
                raise SpecError(f"{where}.delta.{k}: chỉ số phải thuộc {list(EMOTION_KEYS)}, giá trị thuộc {list(DELTA_EXPECT)}")
        out["delta"] = dict(delta)
    if "all_zero" in value:
        if value["all_zero"] is not True:
            raise SpecError(f"{where}.all_zero chỉ nhận true")
        out["all_zero"] = True
    for key in ("memory_any", "facts_any"):
        if key in value:
            out[key] = _str_list(value[key], f"{where}.{key}")
    if "facts_owner" in value:
        if value["facts_owner"] not in ("persona", "character") or "facts_any" not in value:
            raise SpecError(f"{where}.facts_owner phải là persona hoặc character (và cần facts_any)")
        out["facts_owner"] = value["facts_owner"]
    return out


def _relationship(value: Any, where: str) -> dict[str, int]:
    if not isinstance(value, dict) or set(value) - set(EMOTION_KEYS):
        raise SpecError(f"{where} phải là mapping chỉ số cảm xúc -> 0..100")
    for k, v in value.items():
        if not isinstance(v, int) or isinstance(v, bool) or not 0 <= v <= 100:
            raise SpecError(f"{where}.{k} phải là số nguyên 0..100")
    return dict(value)


def parse_spec(kind: str, data: dict[str, Any], where: str) -> dict[str, Any]:
    """Phần riêng của kịch bản loại `kind` (đã biết mọi khoá thuộc KIND_KEYS[kind])."""
    spec: dict[str, Any] = {}
    if kind == "extract":
        cases = data.get("cases")
        if not isinstance(cases, list) or not cases:
            raise SpecError(f"{where}: `cases` phải là list không rỗng")
        parsed = []
        names: set[str] = set()
        for i, case in enumerate(cases):
            cw = f"{where}: cases[{i}]"
            if not isinstance(case, dict) or set(case) - {"name", "turn", "expect", "before"}:
                raise SpecError(f"{cw} chỉ có name, turn, expect, before")
            name = _str(case.get("name"), f"{cw}.name").strip()
            if name in names:
                raise SpecError(f"{cw}: trùng name {name!r}")
            names.add(name)
            turn = parse_turns(case.get("turn"), f"{cw}.turn", need_last="assistant")
            parsed.append(
                {
                    "name": name,
                    "turn": turn,
                    "expect": _expect(case.get("expect"), f"{cw}.expect"),
                    "before": _relationship(case["before"], f"{cw}.before") if "before" in case else None,
                }
            )
        spec["cases"] = parsed
    elif kind == "summarize":
        spec["messages"] = parse_turns(data.get("messages"), f"{where}: `messages`")
        spec["previous"] = _str(data["previous"], f"{where}: `previous`") if data.get("previous") else None
        spec["required_all"] = _required_groups(data.get("required_all"), f"{where}: `required_all`")
        spec["forbidden"] = _str_list(data["forbidden"], f"{where}: `forbidden`") if "forbidden" in data else []
        spec["language"] = data.get("language", "vi")
    elif kind == "suggest":
        spec["history"] = (
            parse_turns(data["history"], f"{where}: `history`", need_last="assistant") if data.get("history") else None
        )
        spec["language"] = data.get("language", "vi")
        spec["max_overlap"] = float(data.get("max_overlap", 0.6))
        if not 0 < spec["max_overlap"] <= 1:
            raise SpecError(f"{where}: `max_overlap` phải trong (0, 1]")
    elif kind == "draft":
        spec["idea"] = _str(data.get("idea"), f"{where}: `idea`")
        spec["language"] = data.get("language", "vi")
        spec["gender"] = data.get("gender")
        if spec["gender"] not in (None, "male", "female", "other"):
            raise SpecError(f"{where}: `gender` phải là male, female, other hoặc bỏ trống")
        spec["style_profile"] = data.get("style_profile")
        fields = _str_list(data.get("required_fields", ["name", "role", "personality", "greeting"]), f"{where}: `required_fields`")
        bad = [f for f in fields if f not in DRAFT_FIELDS]
        if bad:
            raise SpecError(f"{where}: `required_fields` lạ {bad}; có: {list(DRAFT_FIELDS)}")
        spec["required_fields"] = fields
        spec["forbidden_warnings"] = (
            _str_list(data["forbidden_warnings"], f"{where}: `forbidden_warnings`") if "forbidden_warnings" in data else []
        )
    elif kind == "dm_session":
        spec["history"] = parse_turns(data["history"], f"{where}: `history`") if data.get("history") else []
        spec["turns"] = _str_list(data.get("turns"), f"{where}: `turns`")
        checks = data.get("checks") or {}
        if not isinstance(checks, dict):
            raise SpecError(f"{where}: `checks` phải là mapping")
        spec["checks"] = dict(checks)
        spec["max_same_ending"] = _int(data.get("max_same_ending", 2), f"{where}: `max_same_ending`", minimum=1)
        spec["ending_words"] = _int(data.get("ending_words", 3), f"{where}: `ending_words`", minimum=1)
        spec["max_same_tail"] = _int(data.get("max_same_tail", 3), f"{where}: `max_same_tail`", minimum=1)
        spec["reminders"] = _required_groups(data["reminders"], f"{where}: `reminders`") if "reminders" in data else []
        spec["max_same_reminder"] = _int(data.get("max_same_reminder", 2), f"{where}: `max_same_reminder`", minimum=1)
    elif kind == "app_ttft":
        spec["preload"] = parse_turns(data["preload"], f"{where}: `preload`") if data.get("preload") else []
        if spec["preload"] and (len(spec["preload"]) % 2 or spec["preload"][0]["role"] != "user"):
            raise SpecError(f"{where}: `preload` phải là các cặp user, assistant")
        spec["turns"] = _str_list(data.get("turns"), f"{where}: `turns`")
        spec["max_ttft_s"] = _num(data.get("max_ttft_s"), f"{where}: `max_ttft_s`")
        spec["max_median_ttft_s"] = (
            _num(data["max_median_ttft_s"], f"{where}: `max_median_ttft_s`") if "max_median_ttft_s" in data else None
        )
        spec["after_shift"] = _int(data.get("after_shift", 1), f"{where}: `after_shift`")
        spec["max_turns"] = _int(data.get("max_turns", 8), f"{where}: `max_turns`", minimum=2)
        spec["probe_chars"] = _int(data.get("probe_chars", 2500), f"{where}: `probe_chars`", minimum=1)
        spec["settle_timeout_s"] = _num(data.get("settle_timeout_s", 180), f"{where}: `settle_timeout_s`")
        spec["max_total_s"] = _num(data.get("max_total_s", 900), f"{where}: `max_total_s`")
    elif kind == "bakeoff":
        spec["limit"] = _int(data.get("limit", 2), f"{where}: `limit`", minimum=1)
    elif kind == "nested_eval":
        spec["ids"] = _str_list(data.get("ids"), f"{where}: `ids`")
    for key in ("language",):
        if key in spec and spec[key] not in ("vi", "en"):
            raise SpecError(f"{where}: `{key}` phải là vi hoặc en")
    return spec


# ---- môi trường chạy -----------------------------------------------------------------------------------


@dataclass
class Env:
    """Những gì một loại kịch bản cần từ run_eval (truyền vào để tránh import vòng)."""

    client: Any  # OllamaClient
    model: str
    num_ctx: int
    ollama_url: str
    make_story: Callable[..., Story]
    make_message: Callable[..., Message]
    generate: Callable[..., Awaitable[tuple[str, dict[str, Any], str | None]]]
    budget: Any  # PromptBudget
    transport: Any = None
    results_dir: Path | None = None
    run_nested: Callable[..., Awaitable[tuple[int, Path | None]]] | None = None
    depth: int = 0


@dataclass
class Outcome:
    text: str = ""
    problems: list[str] = field(default_factory=list)
    error: str | None = None
    stats: dict[str, Any] = field(default_factory=dict)
    details: dict[str, Any] = field(default_factory=dict)


def _messages(env: Env, story: Story, turns: Sequence[dict[str, str]], *, start: int = 0, fill: Callable[[str], str]) -> list[Message]:
    return [
        env.make_message(story, start + i, t["role"], fill(t["content"]), mode=t.get("mode"))
        for i, t in enumerate(turns)
    ]


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", text).casefold()).strip()


# ---- extract (F09, F10) -----------------------------------------------------------------------------


def delta_problems(delta: dict[str, int], expect: dict[str, Any]) -> list[str]:
    """Chiều thay đổi (sau khi app kiểm tra) có đúng mong đợi không."""
    problems: list[str] = []
    if expect.get("all_zero") and any(delta.get(k, 0) for k in EMOTION_KEYS):
        changed = ", ".join(f"{k} {delta[k]:+d}" for k in EMOTION_KEYS if delta.get(k))
        problems.append(f"chuyện thường ngày mà chỉ số vẫn đổi ({changed})")
    for key, want in (expect.get("delta") or {}).items():
        got = delta.get(key, 0)
        ok = {"up": got > 0, "down": got < 0, "zero": got == 0, "nonzero": got != 0}[want]
        if not ok:
            problems.append(f"{key} {got:+d} (cần {want})")
    return problems


def _name_forms(name: str, *extra: str) -> list[str]:
    """Tên đầy đủ, từng phần của tên (>= 2 chữ cái) và các cách gọi thêm."""
    name = name.strip()
    return [n for n in (name, *name.split(), *extra) if len(n) >= 2]


def _names_in(text: str, forms: Sequence[str]) -> bool:
    return any(phrase_in(text, f) for f in forms)


def memory_problems(
    memory: str | None,
    facts: Sequence[tuple[str, str]],
    expect: dict[str, Any],
    owners: dict[str, str] | None = None,
) -> list[str]:
    """Ký ức / điều đã biết có chứa ít nhất một chi tiết mong đợi không (nguyên từ, xem `phrase_in`).

    `facts`: (subject, text) như app lưu. `expect["facts_owner"]` (persona | character): điều đã biết có chi tiết
    đó phải nói về ĐÚNG người (subject, hoặc text khi subject trống, có tên người đó và không có tên người kia);
    "Lạc Dương dị ứng tôm" khi người dị ứng là người chơi thì là gán nhầm. `owners`: {"persona": tên, "character": tên}.
    """
    problems: list[str] = []
    want_memory = expect.get("memory_any") or []
    if want_memory and not (memory and any(phrase_in(memory, p) for p in want_memory)):
        problems.append(f"ký ức «{memory or ''}» không có chi tiết nào trong [{', '.join(want_memory)}]")
    want_facts = expect.get("facts_any") or []
    if not want_facts:
        return problems
    matching = [(subj, text) for subj, text in facts if any(phrase_in(text, p) for p in want_facts)]
    if not matching:
        shown = "; ".join(text for _, text in facts) or "không có"
        problems.append(f"điều đã biết ({shown}) không có chi tiết nào trong [{', '.join(want_facts)}]")
        return problems
    owner = expect.get("facts_owner")
    if owner and owners:
        other = "character" if owner == "persona" else "persona"
        mine = _name_forms(owners[owner], *(["{{user}}"] if owner == "persona" else []))
        theirs = _name_forms(owners[other])

        def about_owner(subj: str, text: str) -> bool:
            who = subj if subj.strip() else text
            return _names_in(who, mine) and not _names_in(who, theirs)

        if not any(about_owner(subj, text) for subj, text in matching):
            shown = "; ".join(f"{subj or '-'}: {text}" for subj, text in matching)
            problems.append(f"điều đã biết có chi tiết nhưng gán nhầm người (cần nói về {owners[owner]}): {shown}")
    return problems


async def run_extract(spec: dict[str, Any], setup: Any, env: Env, mode: str) -> Outcome:
    from lyris.prompt.templates import PromptContext
    from lyris.state.extract import extract_turn
    from lyris.state.fold import initial_relationship

    out = Outcome()
    lines: list[str] = []
    cases: list[dict[str, Any]] = []
    for case in spec["cases"]:
        story = env.make_story(setup, mode, env.model)
        ctx = PromptContext(card=setup.card, persona=setup.persona, story=story, style="")
        turn = _messages(env, story, case["turn"], start=1, fill=ctx.fill)  # lượt 1+ (lượt 0 là lời mở đầu)
        base = initial_relationship(None, setup.card.extensions)
        before = RelationshipValues(**{**base.model_dump(), **(case["before"] or {})})
        start = time.perf_counter()
        try:
            result = await extract_turn(
                env.client,
                model=env.model,
                num_ctx=env.num_ctx,
                card=setup.card,
                persona=setup.persona,
                story=story,
                before=before,
                scene=SceneState(),
                summary=None,
                turn=turn,
            )
        except LLMError as exc:
            out.error = f"{case['name']}: {exc}"
            break
        delta = result.relationship_delta.model_dump()
        facts = [f.text for f in result.facts]
        owners = {"persona": setup.persona.name, "character": setup.card.name}
        found = [
            *delta_problems(delta, case["expect"]),
            *memory_problems(result.memory, [(f.subject, f.text) for f in result.facts], case["expect"], owners),
        ]
        out.problems.extend(f"{case['name']}: {p}" for p in found)
        changed = ", ".join(f"{k} {delta[k]:+d}" for k in EMOTION_KEYS if delta[k]) or "không đổi"
        lines.append(
            f"[{case['name']}] {('LỖI: ' + '; '.join(found)) if found else 'ok'}\n"
            f"  cảm xúc: {changed}\n  ký ức: {result.memory or '-'}\n  điều đã biết: {'; '.join(facts) or '-'}"
        )
        cases.append(
            {
                "name": case["name"],
                "delta": delta,
                "memory": result.memory,
                "facts": facts,
                "fact_subjects": [f.subject for f in result.facts],
                "scene": result.scene.model_dump(),
                "problems": found,
                "seconds": round(time.perf_counter() - start, 2),
            }
        )
    out.text = "\n".join(lines)
    out.details = {"cases": cases}
    return out


# ---- summarize (F10) ----------------------------------------------------------------------------------


def summary_problems(text: str, required_all: Sequence[Sequence[str]], forbidden: Sequence[str]) -> list[str]:
    problems: list[str] = []
    for group in required_all:
        if not any(phrase_in(text, p) for p in group):
            problems.append(f"tóm tắt thiếu «{' / '.join(group)}»")
    for phrase in forbidden:
        if phrase_in(text, phrase):
            problems.append(f"tóm tắt có «{phrase}» (không có trong story)")
    return problems


async def run_summarize(spec: dict[str, Any], setup: Any, env: Env, mode: str) -> Outcome:
    from lyris.memory.summarize import summarize
    from lyris.prompt.templates import PromptContext

    story = env.make_story(setup, mode, env.model)
    ctx = PromptContext(card=setup.card, persona=setup.persona, story=story, style="")
    messages = _messages(env, story, spec["messages"], start=1, fill=ctx.fill)
    out = Outcome()
    try:
        text = await summarize(
            env.client,
            model=env.model,
            num_ctx=env.num_ctx,
            card=setup.card,
            persona=setup.persona,
            story=story,
            previous=spec["previous"],
            messages=messages,
        )
    except LLMError as exc:
        out.error = str(exc)
        return out
    out.text = text
    out.problems = [
        *summary_problems(text, spec["required_all"], spec["forbidden"]),
        *language_problems(text, spec["language"], setup.names()),
    ]
    out.details = {"summary": text, "words": len(text.split())}
    return out


# ---- suggest (F15) ------------------------------------------------------------------------------------


def _word_set(text: str) -> set[str]:
    return set(re.findall(r"\w+", unicodedata.normalize("NFC", text).casefold()))


def overlap(a: str, b: str) -> float:
    """Độ trùng từ giữa hai gợi ý: số từ chung / số từ của gợi ý NGẮN hơn (một gợi ý ngắn nằm trọn trong gợi ý dài
    là trùng 100%; Jaccard thì lỏng khi hai gợi ý dài khác nhau)."""
    wa, wb = _word_set(a), _word_set(b)
    if not wa or not wb:
        return 1.0 if wa == wb else 0.0
    return len(wa & wb) / min(len(wa), len(wb))


def verbatim_problem(suggestion: str, last_user_content: str) -> str | None:
    """Gửi gợi ý làm lượt người chơi: phải giữ nguyên chữ (không bị tách chỉ đạo, không đổi chữ) và nằm
    nguyên văn trong message cuối gửi model. `last_user_content` = message user cuối của prompt đã dựng."""
    from lyris.prompt.directives import extract_directives

    visible, directive = extract_directives(suggestion)
    if directive or visible.strip() != suggestion.strip():
        return f"gợi ý «{suggestion}» không gửi được nguyên văn (bị tách thành chỉ đạo)"
    if suggestion.strip() not in last_user_content:
        return f"gợi ý «{suggestion}» không nằm nguyên văn trong lượt gửi model"
    return None


def suggestion_problems(
    first: Sequence[str], second: Sequence[str], *, max_overlap: float, language: str, names: Iterable[str]
) -> list[str]:
    """Hai lần gợi ý: mỗi lần đúng 3 gợi ý, đúng ngôn ngữ; lần 2 ("Gợi ý khác") không trùng / gần giống lần 1."""
    problems: list[str] = []
    names = list(names)
    for label, items in (("lần 1", first), ("Gợi ý khác", second)):
        if len(items) != 3:
            problems.append(f"{label}: {len(items)} gợi ý (cần 3)")
        for s in items:
            problems.extend(f"{label}: {p} trong «{s}»" for p in language_problems(s, language, names))
    for b in second:
        for a in first:
            score = overlap(a, b)
            if _norm(a) == _norm(b) or score >= max_overlap:
                problems.append(f"Gợi ý khác «{b}» gần giống lần trước «{a}» (trùng {round(score * 100)}% từ)")
    return problems


async def run_suggest(spec: dict[str, Any], setup: Any, env: Env, mode: str) -> Outcome:
    from lyris.prompt.builder import build_prompt
    from lyris.prompt.templates import PromptContext
    from lyris.state.suggest import suggest_replies

    story = env.make_story(setup, mode, env.model)
    ctx = PromptContext(card=setup.card, persona=setup.persona, story=story, style="")
    turns = spec["history"] or [{"role": "assistant", "content": setup.card.greeting}]
    history = _messages(env, story, turns, fill=ctx.fill)
    out = Outcome()
    try:
        first = await suggest_replies(
            env.client, model=env.model, num_ctx=env.num_ctx, card=setup.card, persona=setup.persona, story=story,
            history=history,
        )
        second = await suggest_replies(
            env.client, model=env.model, num_ctx=env.num_ctx, card=setup.card, persona=setup.persona, story=story,
            history=history, avoid=first,
        )
    except LLMError as exc:
        out.error = str(exc)
        return out
    problems = suggestion_problems(first, second, max_overlap=spec["max_overlap"], language=spec["language"], names=setup.names())
    for s in [*first, *second]:
        sent = env.make_message(story, len(history), "user", s)
        built = build_prompt(setup.card, setup.persona, story, [*history, sent], budget=env.budget)
        why = verbatim_problem(s, built.messages[-1].content)
        if why:
            problems.append(why)
    out.problems = problems
    out.text = "Lần 1:\n" + "\n".join(f"- {s}" for s in first) + "\nGợi ý khác:\n" + "\n".join(f"- {s}" for s in second)
    out.details = {"first": list(first), "second": list(second)}
    return out


# ---- draft (F19) --------------------------------------------------------------------------------------


def draft_problems(
    card: CharacterCard, warnings: Sequence[str], *, required: Sequence[str], forbidden_warnings: Sequence[str], language: str
) -> list[str]:
    problems: list[str] = []
    if card.id is not None:
        problems.append("card nháp đã có id (bị lưu)")
    for name in required:
        if not str(getattr(card, name, "") or "").strip():
            problems.append(f"card nháp thiếu {name}")
    for w in warnings:
        if any(w.startswith(prefix) for prefix in forbidden_warnings):
            problems.append(f"cảnh báo: {w}")
    names = [card.name, *card.address_terms.nicknames]
    for label, body in (("tính cách", card.personality), ("lời mở đầu", card.greeting.replace("{{user}}", " "))):
        if body.strip():
            problems.extend(f"{label} của card nháp {p}" for p in language_problems(body, language, names))
    return problems


async def run_draft(spec: dict[str, Any], setup: Any, env: Env, mode: str) -> Outcome:
    from lyris.prompt.builder import list_style_profiles
    from lyris.studio.draft import draft_card

    out = Outcome()
    try:
        card, warnings = await draft_card(
            env.client,
            env.model,
            idea=spec["idea"],
            language=spec["language"],
            gender=spec["gender"],
            style_profile=spec["style_profile"],
            styles=list_style_profiles(),
        )
    except LLMError as exc:
        out.error = str(exc)
        return out
    out.problems = draft_problems(
        card, warnings, required=spec["required_fields"], forbidden_warnings=spec["forbidden_warnings"], language=spec["language"]
    )
    out.text = (
        f"Tên: {card.name}\nVai trò: {card.role}\nGiới tính: {card.gender}\nVăn phong: {card.style_profile}\n"
        f"Tính cách: {card.personality}\nXưng hô: {card.address_terms.self_term}/{card.address_terms.player_term}\n"
        f"Lời mở đầu:\n{card.greeting}\nCảnh báo: {'; '.join(warnings) or 'không'}"
    )
    out.details = {"card": card.model_dump(mode="json"), "warnings": list(warnings)}
    return out


# ---- dm_session (F13) ---------------------------------------------------------------------------------

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?…])\s+|\n+")


def closing_sentence(text: str) -> str:
    """Câu cuối (chuẩn hoá: chữ thường, bỏ dấu câu và emoji) của phần hiển thị."""
    visible = strip_thoughts(text).strip()
    parts = [p for p in _SENTENCE_SPLIT.split(visible) if re.search(r"\w", p)]
    if not parts:
        return ""
    return " ".join(re.findall(r"\w+", unicodedata.normalize("NFC", parts[-1]).casefold()))


def closing_tail(text: str, words: int) -> str:
    tokens = re.findall(r"\w+", unicodedata.normalize("NFC", strip_thoughts(text)).casefold())
    return " ".join(tokens[-words:])


def repetition_problems(
    replies: Sequence[str],
    *,
    max_same_ending: int,
    ending_words: int,
    max_same_tail: int,
    reminders: Sequence[Sequence[str]] = (),
    max_same_reminder: int = 2,
) -> list[str]:
    """Câu kết lặp: cùng một câu cuối ở quá `max_same_ending` lượt, cùng `ending_words` chữ cuối ở quá
    `max_same_tail` lượt, hoặc câu cuối chứa cùng một lời dặn (một nhóm cụm trong `reminders`, vd "ngủ sớm" /
    "thức khuya": viết lại kiểu khác vẫn là một lời dặn) ở quá `max_same_reminder` lượt."""
    problems: list[str] = []
    closings = [closing_sentence(r) for r in replies]
    for group in reminders:
        n = sum(1 for c in closings if c and any(phrase_in(c, p) for p in group))
        if n > max_same_reminder:
            problems.append(
                f"{n}/{len(replies)} lượt kết bằng cùng một lời dặn «{' / '.join(group)}» (tối đa {max_same_reminder})"
            )
    endings = Counter(e for e in closings if e)
    for ending, n in endings.most_common():
        if n > max_same_ending:
            problems.append(f"{n}/{len(replies)} lượt kết bằng cùng một câu «{ending}» (tối đa {max_same_ending})")
    tails = Counter(t for t in (closing_tail(r, ending_words) for r in replies) if t)
    for tail, n in tails.most_common():
        if n > max_same_tail:
            problems.append(f"{n}/{len(replies)} lượt kết bằng cùng «… {tail}» (tối đa {max_same_tail})")
    return problems


def dm_turn_problems(reply: str, checks: dict[str, Any], *, persona_name: str, names: Iterable[str]) -> list[str]:
    """Luật mỗi lượt của dm_session: mặc định chỉ "câu trả lời rỗng" (F13 chỉ chấm câu kết lặp, luật khác như
    `((` hay dòng "<persona>:" thuộc tính năng khác); `checks` của kịch bản thì chạy đúng các luật đó."""
    if not reply.strip():
        return ["câu trả lời rỗng"]
    if not checks:
        return []
    return run_checks(reply, {"directive_leak": False, "persona_line": False, **checks}, persona_name=persona_name, names=names, dm=True)


def fresh_prompt_state(card: CharacterCard, persona: Persona, story: Story) -> Any:
    """PromptState như ChatService dựng cho một story mới (chưa có event): chỉ dẫn diễn xuất từ 6 chỉ số ban đầu
    của card; chưa có tóm tắt, cảnh, ký ức."""
    from lyris.models import PromptState
    from lyris.state.fold import initial_relationship
    from lyris.state.service import _relationship_directive

    values = initial_relationship(None, card.extensions)
    return PromptState(directive=_relationship_directive(values, card, persona, story))


async def run_dm_session(spec: dict[str, Any], setup: Any, env: Env, mode: str) -> Outcome:
    from lyris.prompt.builder import build_prompt
    from lyris.prompt.templates import PromptContext

    story = env.make_story(setup, "dm", env.model)
    ctx = PromptContext(card=setup.card, persona=setup.persona, story=story, style="")
    history = _messages(env, story, spec["history"], fill=ctx.fill)
    out = Outcome()
    replies: list[str] = []
    ttfts: list[float] = []
    lines: list[str] = []
    state = fresh_prompt_state(setup.card, setup.persona, story)
    for i, text in enumerate(spec["turns"], 1):
        history.append(env.make_message(story, len(history), "user", text))
        built = build_prompt(setup.card, setup.persona, story, history, budget=env.budget, state=state)
        reply, stats, error = await env.generate(env.client, env.model, built)
        if error:
            out.error = f"lượt {i}: {error}"
            break
        replies.append(reply)
        if stats.get("ttft_ms") is not None:
            ttfts.append(stats["ttft_ms"])
        found = dm_turn_problems(reply, spec["checks"], persona_name=setup.persona.name, names=setup.names())
        out.problems.extend(f"lượt {i}: {p}" for p in found)
        lines.append(f"[{i}] {setup.persona.name}: {text}\n    {setup.card.name}: {reply.strip()}")
        history.append(env.make_message(story, len(history), "assistant", reply))
    if not out.error:
        out.problems.extend(
            repetition_problems(
                replies,
                max_same_ending=spec["max_same_ending"],
                ending_words=spec["ending_words"],
                max_same_tail=spec["max_same_tail"],
                reminders=spec["reminders"],
                max_same_reminder=spec["max_same_reminder"],
            )
        )
    out.text = "\n".join(lines)
    out.stats = {"ttft_ms": statistics.mean(ttfts) if ttfts else None}
    out.details = {"replies": replies, "endings": [closing_sentence(r) for r in replies]}
    return out


# ---- app_ttft (F14) -----------------------------------------------------------------------------------


@dataclass
class TurnTiming:
    turn: int  # lượt sống thứ mấy (1 = lượt đầu, không tính)
    ttft_s: float | None  # phía người chơi: gửi POST tới sự kiện `delta` đầu tiên
    window_start: int | None
    shifted: bool
    prompt_tokens: int | None = None
    ollama_ttft_s: float | None = None  # OllamaClient tự đo (chỉ để đối chiếu)


def ttft_problems(
    timings: Sequence[TurnTiming], *, max_ttft_s: float, after_shift: int, max_median_s: float | None = None
) -> list[str]:
    """Mọi lượt sau lượt đầu có TTFT <= max_ttft_s, trung vị các lượt đó <= max_median_s ("khoảng 4-5 giây");
    phải có một lượt cửa sổ dịch (sau lượt đầu) và đủ `after_shift` lượt đo sau nó."""
    problems: list[str] = []
    measured = [t for t in timings if t.turn > 1]
    if not measured:
        return ["không có lượt nào sau lượt đầu để đo"]
    for t in measured:
        tag = " (cửa sổ dịch)" if t.shifted else ""
        if t.ttft_s is None:
            problems.append(f"lượt {t.turn}{tag}: không đo được TTFT")
        elif t.ttft_s > max_ttft_s:
            problems.append(f"lượt {t.turn}{tag}: TTFT {t.ttft_s:.2f}s > {max_ttft_s:g}s")
    values = [t.ttft_s for t in measured if t.ttft_s is not None]
    if max_median_s is not None and values and statistics.median(values) > max_median_s:
        problems.append(f"trung vị TTFT các lượt sau lượt đầu {statistics.median(values):.2f}s > {max_median_s:g}s")
    shifts = [t.turn for t in measured if t.shifted]
    if not shifts:
        problems.append("không gặp lượt cửa sổ dịch nào sau lượt đầu (kịch bản chưa đo được lượt dịch)")
    elif sum(1 for t in measured if t.turn > shifts[0]) < after_shift:
        problems.append(f"chưa đo đủ {after_shift} lượt sau lượt cửa sổ dịch")
    return problems


class SettleTimeout(Exception):
    """Việc nền (trích xuất, tóm tắt, prefill) chưa xong sau `settle_timeout_s`."""


async def _wait_idle(app: Any, story_id: int, timeout: float) -> None:
    """Chờ worker xong mọi job và prefill (như người chơi đọc xong mới gõ lượt sau)."""
    worker = app.state.worker
    repo = app.state.repo
    deadline = time.monotonic() + timeout
    calm = 0
    while calm < 3:
        if time.monotonic() > deadline:
            raise SettleTimeout(f"việc nền chưa xong sau {timeout:g} giây")
        busy = (
            worker.current_job is not None
            or getattr(worker, "_prefill_due", None) is not None
            or getattr(worker, "_prefill_task", None) is not None
            or repo.has_pending_jobs(story_id)
        )
        calm = 0 if busy else calm + 1
        await asyncio.sleep(0.2)


def _prepare_db(db_path: Path, model: str, setup_preload: Callable[[Any], None]) -> None:
    """DB tạm: chủ máy có mật khẩu ngẫu nhiên + đã đồng ý điều khoản, story seed dùng `model`, nạp sẵn lịch sử."""
    from lyris.auth import clock, passwords
    from lyris.auth import store as auth_store
    from lyris.compliance import legal
    from lyris.db.connection import connect, migrate
    from lyris.db.repo import ANY_ACCOUNT, Repo
    from lyris.seed import ensure_seed

    conn = connect(db_path)
    try:
        migrate(conn)
        repo = Repo(conn)
        owner = repo.owner_account()
        assert owner.id is not None
        now = clock.now()
        with repo.transaction():
            auth_store.write_password(conn, owner.id, passwords.hash_password_sync(secrets.token_hex(16)), now, temporary=False)
            auth_store.delete_setup(conn)
            legal.accept(conn, owner.id, now)
        sid = ensure_seed(repo)
        assert sid is not None
        repo.update_story(sid, account_id=ANY_ACCOUNT, model_name=model)
        setup_preload(repo)
    finally:
        conn.close()


def preload_history(repo: Any, story_id: int, pairs: Sequence[dict[str, str]], *, probe_chars: int, budget: Any) -> int:
    """Nạp các cặp (user, assistant) xoay vòng vào story tới khi một lượt kế tiếp dài `probe_chars` ký tự sẽ
    làm cửa sổ dịch (`next_window_start`), để lượt dịch rơi vào vài lượt sống đầu. Trả số message đã nạp."""
    from lyris.db.repo import ANY_ACCOUNT
    from lyris.llm.thought import split_thought
    from lyris.prompt.builder import next_window_start
    from lyris.prompt.directives import extract_directives
    from lyris.prompt.templates import PromptContext

    if not pairs:
        return 0
    story = repo.get_story(story_id, account_id=ANY_ACCOUNT)
    card = repo.get_card(story.card_id, account_id=ANY_ACCOUNT)
    persona = repo.get_persona(story.persona_id, account_id=ANY_ACCOUNT)
    ctx = PromptContext(card=card, persona=persona, story=story, style="")
    added = 0
    for cycle in range(200):
        history = repo.active_messages(story_id)
        if next_window_start(card, persona, story, history, next_user_chars=probe_chars, budget=budget) > 0:
            break
        item = pairs[(cycle * 2) % len(pairs)]
        reply = pairs[(cycle * 2 + 1) % len(pairs)]
        turn = repo.next_turn_index(story_id)
        visible, directive = extract_directives(ctx.fill(item["content"]))
        repo.insert_message(
            Message(story_id=story_id, turn_index=turn, role="user", mode=story.mode,
                    raw_content=ctx.fill(item["content"]), visible_content=visible, directive=directive)
        )
        raw = ctx.fill(reply["content"])
        shown, thought = split_thought(raw)
        repo.insert_message(
            Message(story_id=story_id, turn_index=turn + 1, role="assistant", mode=story.mode,
                    raw_content=raw, visible_content=shown, thought=thought, model_output=raw)
        )
        added += 2
    return added


TTFT_PORTS = (8068, 8069)  # cổng server test (environment/rules.md: 8066-8069; 8066/8067 là của bot)


def _bind_test_port(ports: Sequence[int]) -> tuple[Any, int]:
    """Giữ sẵn một socket 127.0.0.1 ở cổng trống đầu tiên (uvicorn bind lỗi thì gọi sys.exit: tránh)."""
    import socket

    last: OSError | None = None
    for port in ports:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError as exc:
            sock.close()
            last = exc
            continue
        return sock, port
    raise OSError(f"cổng {', '.join(map(str, ports))} đều bận ({last})")


async def _send_turn(http: Any, url: str, text: str) -> tuple[float | None, str | None, str]:
    """Gửi một lượt như giao diện (POST, đọc SSE). Trả (giây tới `delta` đầu tiên có chữ, lỗi, tên sự kiện cuối)."""
    start = time.perf_counter()
    first: float | None = None
    event = ""
    last_event = ""
    async with http.stream("POST", url, json={"content": text}) as resp:
        if resp.status_code != 200:
            body = (await resp.aread()).decode("utf-8", "replace")
            return None, f"app trả {resp.status_code}: {body.strip()[-300:]}", ""
        async for line in resp.aiter_lines():
            if line.startswith("event:"):
                event = line[6:].strip()
                last_event = event
            elif line.startswith("data:") and event == "delta" and first is None:
                try:
                    data = json.loads(line[5:])
                except ValueError:
                    data = {}
                if str(data.get("text") or "").strip():
                    first = time.perf_counter() - start
            elif line.startswith("data:") and event == "error":
                return first, f"app báo lỗi: {line[5:].strip()[:300]}", event
    if last_event != "done":
        return first, f"stream kết thúc ở sự kiện {last_event or 'không có'} (chưa có done)", last_event
    return first, None, last_event


async def _app_ttft_body(spec: dict[str, Any], env: Env, tmp: Path, out: Outcome, timings: list[TurnTiming],
                         lines: list[str], info: dict[str, Any]) -> None:
    import httpx
    import uvicorn

    from lyris.api.app import create_app
    from lyris.auth import clock
    from lyris.auth import store as auth_store
    from lyris.auth.net import SESSION_COOKIE
    from lyris.config import Settings
    from lyris.db.repo import ANY_ACCOUNT

    db_path = tmp / "lyris.db"

    def preload(repo: Any) -> None:
        sid = repo.list_stories(account_id=ANY_ACCOUNT)[0].id
        info["story_id"] = sid
        info["preloaded"] = preload_history(repo, sid, spec["preload"], probe_chars=spec["probe_chars"], budget=env.budget)

    _prepare_db(db_path, env.model, preload)
    settings = Settings(
        db_path=db_path,
        ollama_url=env.ollama_url,
        chat_model=env.model,
        num_ctx=env.num_ctx,
        avatars_dir=tmp / "avatars",
        draft_model=env.model,
    )
    app = create_app(settings, start_forwarder=False)  # llm=None: OllamaClient thật, worker + prefill bật
    sid = info["story_id"]
    sock, port = _bind_test_port(TTFT_PORTS)
    info["port"] = port
    async with app.router.lifespan_context(app):
        repo = app.state.repo
        owner = repo.owner_account()
        with repo.transaction():
            token, _ = auth_store.insert_session(repo.conn, owner.id, now=clock.now(), label="harness", ip="127.0.0.1")
        server = uvicorn.Server(
            uvicorn.Config(app, lifespan="off", log_level="warning", access_log=False, proxy_headers=False)
        )
        serving = asyncio.create_task(server.serve(sockets=[sock]))
        try:
            while not server.started:
                if serving.done():
                    raise OSError(f"không bật được server test ở cổng {port}")
                await asyncio.sleep(0.02)
            async with httpx.AsyncClient(
                base_url=f"http://127.0.0.1:{port}",
                cookies={SESSION_COOKIE: token},
                headers={"X-Lyris": "1"},
                timeout=httpx.Timeout(600, connect=5),
                trust_env=False,  # không đi qua proxy của máy
            ) as http:
                await _wait_idle(app, sid, spec["settle_timeout_s"])
                prev_start: int | None = None
                shift_at: int | None = None
                for n in range(1, spec["max_turns"] + 1):
                    text = spec["turns"][(n - 1) % len(spec["turns"])]
                    ttft, error, _ = await _send_turn(http, f"/api/stories/{sid}/messages", text)
                    if error:
                        out.error = f"lượt {n}: {error}"
                        break
                    msg = repo.active_messages(sid)[-1]
                    stats = msg.gen_stats
                    snap = msg.prompt_snapshot or {}
                    start = snap.get("window_start_turn") if isinstance(snap.get("window_start_turn"), int) else None
                    shifted = n > 1 and prev_start is not None and start is not None and start != prev_start
                    model_ttft = stats.ttft_ms / 1000 if stats and stats.ttft_ms is not None else None
                    tokens = stats.prompt_tokens if stats else None
                    timings.append(TurnTiming(n, ttft, start, shifted, tokens, model_ttft))
                    lines.append(
                        f"lượt {n}: TTFT {'-' if ttft is None else f'{ttft:.2f}s'}"
                        f" (Ollama {'-' if model_ttft is None else f'{model_ttft:.2f}s'}), cửa sổ từ lượt {start}"
                        f"{' (DỊCH)' if shifted else ''}, đọc prompt {tokens if tokens is not None else '-'} token"
                    )
                    prev_start = start
                    if shifted and shift_at is None:
                        shift_at = n
                    if shift_at is not None and n - shift_at >= spec["after_shift"]:
                        break
                    await _wait_idle(app, sid, spec["settle_timeout_s"])
        finally:
            server.should_exit = True
            with contextlib.suppress(Exception):
                await asyncio.wait_for(asyncio.shield(serving), timeout=10)
            if not serving.done():
                serving.cancel()
            sock.close()


async def run_app_ttft(spec: dict[str, Any], setup: Any, env: Env, mode: str) -> Outcome:
    """App thật trong tiến trình: create_app với Ollama thật (worker + prefill bật như khi chạy app), DB tạm, phục
    vụ qua uvicorn ở cổng test 8068 (8069 nếu bận). Gửi lượt qua HTTP như giao diện và đo TTFT phía người chơi: từ
    lúc gửi POST tới sự kiện `delta` đầu tiên (gồm dựng prompt, tìm ký ức, chọn mục thế giới, chờ khoá). Chờ việc
    nền + prefill xong rồi mới gửi lượt sau (§10.6). Cả kịch bản có hạn `max_total_s`: quá hạn là lỗi của riêng
    kịch bản này."""
    out = Outcome()
    tmp = Path(tempfile.mkdtemp(prefix="lyris-ttft-"))
    timings: list[TurnTiming] = []
    lines: list[str] = []
    info: dict[str, Any] = {}
    try:
        await asyncio.wait_for(_app_ttft_body(spec, env, tmp, out, timings, lines, info), timeout=spec["max_total_s"])
    except TimeoutError:
        out.error = out.error or f"kịch bản quá {spec['max_total_s']:g} giây (giới hạn tổng max_total_s), dừng"
    except (LLMError, SettleTimeout, OSError) as exc:
        out.error = out.error or f"{type(exc).__name__}: {exc}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if not out.error:
        out.problems = ttft_problems(
            timings, max_ttft_s=spec["max_ttft_s"], after_shift=spec["after_shift"], max_median_s=spec["max_median_ttft_s"]
        )
    measured = [t.ttft_s for t in timings if t.turn > 1 and t.ttft_s is not None]
    out.stats = {"ttft_ms": statistics.mean(measured) * 1000 if measured else None}
    out.text = f"Nạp sẵn {info.get('preloaded', 0)} message.\n" + "\n".join(lines)
    out.details = {
        "timings": [t.__dict__ for t in timings],
        "max_ttft_s": spec["max_ttft_s"],
        "max_median_ttft_s": spec["max_median_ttft_s"],
        "median_ttft_s": statistics.median(measured) if measured else None,
        "measured": "client: POST tới event delta đầu tiên",
        "port": info.get("port"),
    }
    return out


# ---- bakeoff (F36) ------------------------------------------------------------------------------------


def bakeoff_problems(code: int, out_dir: Path | None, model: str, *, printed: str | None = None) -> list[str]:
    """bakeoff chạy xong (mã 0), ghi speed.md có bảng với dòng của model và số TTFT, tok/s; mọi câu của model chạy
    được (raw.json không có câu `[LỖI: …]`, câu nào cũng có TTFT). `printed`: đầu ra của lệnh, phải in bảng đó."""
    if code != 0:
        return [f"bakeoff thoát mã {code}"]
    if out_dir is None or not (out_dir / "speed.md").is_file():
        return ["bakeoff không ghi speed.md"]
    table = (out_dir / "speed.md").read_text(encoding="utf-8")
    if "| Model |" not in table:
        return ["speed.md không có bảng so sánh model"]
    row = next((line for line in table.splitlines() if line.startswith(f"| {model} |")), None)
    if row is None:
        return [f"bảng không có dòng cho {model}"]
    cells = [c.strip() for c in row.strip("|").split("|")]
    if len(cells) < 5 or "lỗi" in cells[1]:
        return [f"dòng của {model} báo lỗi: {row}"]
    try:
        float(cells[3]), float(cells[4])
    except ValueError:
        return [f"dòng của {model} thiếu TTFT hoặc tok/s: {row}"]
    problems: list[str] = []
    try:
        runs = json.loads((out_dir / "raw.json").read_text(encoding="utf-8"))["models"][model]["runs"]
    except (OSError, ValueError, KeyError, TypeError):
        return ["bakeoff không ghi raw.json có các câu của model"]
    for r in runs:
        text = str(r.get("text") or "")
        if text.startswith("[LỖI:") or r.get("ttft_s") is None:
            problems.append(f"bakeoff: câu {r.get('case')} của {model} lỗi ({text[:80] or 'không có TTFT'})")
    if printed is not None:
        shown = printed.splitlines()
        if not any(line.startswith("| Model |") for line in shown) or not any(line.startswith(f"| {model} |") for line in shown):
            problems.append("bakeoff.py không in bảng so sánh model")
    return problems


async def run_bakeoff_kind(spec: dict[str, Any], setup: Any, env: Env, mode: str) -> Outcome:
    """Chạy đúng lệnh `harness/bakeoff.py` (hàm `main` với tham số dòng lệnh) và giữ lại đầu ra của nó: dòng
    "Đã ghi kết quả vào" của bakeoff không lọt ra đầu ra của run_eval (verify.sh đọc dòng đó của run_eval)."""
    import bakeoff

    out_root = env.results_dir or bakeoff.HERE / "results"
    argv = ["--models", env.model, "--host", env.ollama_url, "--limit", str(spec["limit"]),
            "--num-ctx", str(env.num_ctx), "--out-root", str(out_root)]
    out = Outcome()
    buf = io.StringIO()

    def call() -> int:
        with contextlib.redirect_stdout(buf):
            return bakeoff.main(argv)

    try:
        code = await asyncio.to_thread(call)
    except SystemExit as exc:  # argparse
        code = exc.code if isinstance(exc.code, int) else 2
    except Exception as exc:  # noqa: BLE001 - urllib, OSError...
        out.error = f"bakeoff lỗi: {exc}"
        return out
    printed = buf.getvalue()
    found = re.search(r"Đã ghi kết quả vào (.+)$", printed, re.M)
    out_dir = Path(found.group(1).strip()) if found else None
    out.problems = bakeoff_problems(code, out_dir, env.model, printed=printed)
    out.text = "\n".join(line for line in printed.splitlines() if line.startswith("|"))
    out.details = {"out_dir": str(out_dir) if out_dir else None, "exit_code": code, "argv": argv}
    return out


# ---- nested_eval (F36) --------------------------------------------------------------------------------


def nested_problems(code: int, out_dir: Path | None, ids: Sequence[str]) -> list[str]:
    """run_eval lồng thoát 0, ghi report.md + raw.json, có đúng các kịch bản yêu cầu và không lỗi sinh.
    (Lỗi máy của từng kịch bản là việc của tính năng sở hữu kịch bản đó, không tính ở đây.)"""
    if code != 0:
        return [f"run_eval lồng thoát mã {code}"]
    if out_dir is None or not (out_dir / "report.md").is_file() or not (out_dir / "raw.json").is_file():
        return ["run_eval lồng không ghi report.md / raw.json"]
    try:
        raw = json.loads((out_dir / "raw.json").read_text(encoding="utf-8"))
    except ValueError as exc:
        return [f"raw.json hỏng: {exc}"]
    results = {r.get("id"): r for r in raw.get("results", []) if isinstance(r, dict)}
    problems = [f"báo cáo thiếu kịch bản {sid}" for sid in ids if sid not in results]
    problems.extend(f"{sid}: lỗi sinh ({results[sid]['error']})" for sid in ids if sid in results and results[sid].get("error"))
    return problems


async def run_nested_eval(spec: dict[str, Any], setup: Any, env: Env, mode: str) -> Outcome:
    out = Outcome()
    if env.run_nested is None or env.depth > 0:
        out.error = "nested_eval không chạy lồng được ở đây"
        return out
    code, out_dir = await env.run_nested(spec["ids"])
    out.problems = nested_problems(code, out_dir, spec["ids"])
    out.text = f"run_eval lồng: mã {code}, kết quả ở {out_dir}"
    out.details = {"exit_code": code, "out_dir": str(out_dir) if out_dir else None, "ids": spec["ids"]}
    return out


RUNNERS: dict[str, Callable[[dict[str, Any], Any, Env, str], Awaitable[Outcome]]] = {
    "extract": run_extract,
    "summarize": run_summarize,
    "suggest": run_suggest,
    "draft": run_draft,
    "dm_session": run_dm_session,
    "app_ttft": run_app_ttft,
    "bakeoff": run_bakeoff_kind,
    "nested_eval": run_nested_eval,
}


async def run_kind(kind: str, spec: dict[str, Any], setup: Any, env: Env, mode: str) -> Outcome:
    """Một lỗi bất ngờ trong một kịch bản thành `error` của đúng kịch bản đó: không làm cả lượt run_eval chết
    (verify.sh sẽ coi mọi kịch bản là đỏ nếu run_eval thoát khác 0)."""
    try:
        return await RUNNERS[kind](spec, setup, env, mode)
    except LLMError as exc:
        return Outcome(error=str(exc))
    except Exception as exc:  # noqa: BLE001
        return Outcome(error=f"{type(exc).__name__}: {exc}")


__all__ = [
    "KINDS",
    "KIND_KEYS",
    "META_KINDS",
    "Env",
    "Outcome",
    "SpecError",
    "TurnTiming",
    "bakeoff_problems",
    "closing_sentence",
    "delta_problems",
    "dm_turn_problems",
    "draft_problems",
    "fresh_prompt_state",
    "memory_problems",
    "nested_problems",
    "overlap",
    "parse_spec",
    "parse_turns",
    "repetition_problems",
    "run_kind",
    "suggestion_problems",
    "summary_problems",
    "ttft_problems",
    "verbatim_problem",
]

