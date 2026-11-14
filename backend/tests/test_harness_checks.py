"""Test cho harness/: checks.py (kiểm tra máy), bakeoff.py import lại từ checks, run_eval.py (không cần Ollama)."""
from __future__ import annotations

import ast
import importlib
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

import httpx
import pytest

HARNESS_DIR = Path(__file__).resolve().parents[2] / "harness"
if str(HARNESS_DIR) not in sys.path:
    sys.path.insert(0, str(HARNESS_DIR))

checks = importlib.import_module("checks")
run_eval = importlib.import_module("run_eval")


# ---- checks.py ---------------------------------------------------------------------------------


def test_checks_is_stdlib_only() -> None:
    tree = ast.parse((HARNESS_DIR / "checks.py").read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.add(node.module.split(".")[0])
    assert modules, "checks.py phải import re"
    assert modules <= set(sys.stdlib_module_names), modules - set(sys.stdlib_module_names)


def test_bakeoff_reuses_checks() -> None:
    bakeoff = importlib.import_module("bakeoff")
    assert bakeoff.auto_check is checks.auto_check
    assert bakeoff.narration_only is checks.narration_only
    assert bakeoff.HAN is checks.HAN
    source = (HARNESS_DIR / "bakeoff.py").read_text(encoding="utf-8")
    assert "def auto_check" not in source and "def narration_only" not in source


def test_narration_only_drops_thought_and_dialogue() -> None:
    text = 'Anh nhìn cô. "Tớ ở đây, cậu đừng sợ." [Thought: tớ lo cho cậu] Cô run lên.'
    narration = checks.narration_only(text)
    assert "Tớ ở đây" not in narration and "lo cho" not in narration
    assert "Anh nhìn cô." in narration and "Cô run lên." in narration


def test_auto_check_behaviour_unchanged() -> None:
    rules = {"thought_count": 1, "narration_forbidden": ["tớ", "cậu", "tôi"]}
    good = 'Anh khẽ cười. "Tớ đưa cậu về." [Thought: Cô ngốc này.]'
    assert checks.auto_check(good, rules) == []
    bad = "Tớ nhìn cậu ấy. Anh không nói gì. 好"
    assert checks.auto_check(bad, rules) == ["chữ Hán", "0 Thought", "xưng hô trong dẫn truyện x2"]
    two = "[Thought: a] x [Thought: b]"
    assert checks.auto_check(two, {"thought_count": 1}) == ["2 Thought"]
    assert checks.auto_check("Hello", {}) == []


def test_directive_leak() -> None:
    assert checks.directive_leak("Anh gật đầu. ((ghen))")
    assert checks.directive_leak("((")
    assert not checks.directive_leak("Anh (khẽ) cười.")


@pytest.mark.parametrize(
    "text",
    [
        "Lâm Vãn: Tớ đi đây.",
        "Anh cười.\nLâm Vãn: Ừ.",
        "**Lâm Vãn:** Ừ.",
        "  - Lâm Vãn : được",
        "lâm vãn: ừ",
        "Lâm Vãn：ừ",
    ],
)
def test_persona_line_detects(text: str) -> None:
    assert checks.persona_line(text, "Lâm Vãn")


@pytest.mark.parametrize(
    "text",
    [
        "Anh nhìn Lâm Vãn: cô đang ngủ.",
        'Anh nói: "Lâm Vãn, dậy thôi."',
        "Lâm Vãn khẽ run.",
        "",
    ],
)
def test_persona_line_ignores(text: str) -> None:
    assert not checks.persona_line(text, "Lâm Vãn")


def test_persona_line_empty_name() -> None:
    assert not checks.persona_line(": abc", "  ")


def test_word_count_and_strip_thoughts() -> None:
    assert checks.word_count("") == 0
    assert checks.word_count("Vãn Vãn, dậy thôi... 🥺 !") == 4
    assert checks.word_count("tớ không ngủ được, cậu còn thức không") == 8
    text = "Anh cười. [Thought: rất nhiều chữ ở đây] Đi thôi. [ thought : chưa đóng"
    assert checks.strip_thoughts(text) == "Anh cười.  Đi thôi. "
    assert checks.word_count(checks.strip_thoughts(text)) == 4


def test_thought_unclosed() -> None:
    assert checks.thought_unclosed("Anh cười. [Thought: chưa xong")
    assert checks.thought_unclosed("[Thought: a] rồi [THOUGHT: b")
    assert not checks.thought_unclosed("[Thought: xong] Anh đi.")
    assert not checks.thought_unclosed("Không có thought")


def test_run_checks_clean_story_reply() -> None:
    rules = {"thought_count": 1, "narration_forbidden": ["tớ", "cậu", "tôi"], "min_words": 5, "max_words": 50}
    reply = 'Lạc Dương khẽ cười, đưa tay vuốt tóc cô. "Ngủ đủ chưa?"\n\n[Thought: Ngốc thật.]'
    assert checks.run_checks(reply, rules, persona_name="Lâm Vãn") == []


def test_run_checks_reports_everything() -> None:
    rules = {
        "thought_count": 0,
        "max_words": 3,
        "forbidden_phrases": ["ghen nhưng không nói ra"],
    }
    reply = "Anh GHEN NHƯNG KHÔNG NÓI RA. ((ghen))\nLâm Vãn: Ừ. [Thought: x"
    problems = checks.run_checks(reply, rules, persona_name="Lâm Vãn")
    assert "1 Thought" in problems
    assert "Thought chưa đóng" in problems
    assert any(p.startswith("dài ") and "(tối đa 3)" in p for p in problems)
    assert 'có cụm cấm "ghen nhưng không nói ra"' in problems
    assert "lọt chỉ đạo (( ))" in problems
    assert 'có dòng "Lâm Vãn:"' in problems


def test_run_checks_min_words_and_toggles() -> None:
    assert checks.run_checks("Ừ.", {"min_words": 5}) == ["ngắn 1 từ (tối thiểu 5)"]
    rules = {"directive_leak": False, "persona_line": False}
    assert checks.run_checks("((x))\nLâm Vãn: ừ", rules, persona_name="Lâm Vãn") == []
    assert checks.run_checks("   ", {}) == ["câu trả lời rỗng"]
    # Không có persona_name thì không kiểm tra dòng persona.
    assert checks.run_checks("Lâm Vãn: ừ", {}) == []


def test_run_checks_dm_actions() -> None:
    rules = {"thought_count": 0, "max_words": 60, "forbidden_phrases": ["*"]}
    assert checks.run_checks("Còn. Ngủ không được thì gọi cho tớ.", rules, persona_name="Lâm Vãn") == []
    assert checks.run_checks("*cầm điện thoại* Còn.", rules) == ['có cụm cấm "*"']


# ---- run_eval.py: kịch bản và prompt -----------------------------------------------------------


# Bộ 8 kịch bản trả lời gốc (01-08). Các kịch bản model thật của từng tính năng (f05-…, f36-…, nhiều loại khác
# `reply`) có test riêng ở test_run_eval_kinds.py.
CORE_IDS = [
    "01-mo-dau",
    "02-bay-im-lang",
    "03-hanh-dong-cho-ai",
    "04-chi-dao",
    "05-dm",
    "06-viet-hien-dai",
    "07-co-trang",
    "08-tieng-anh",
]


@pytest.fixture(scope="module")
def scenarios() -> list[Any]:
    return run_eval.load_scenarios(run_eval.DEFAULT_SCENARIOS, CORE_IDS)


@pytest.fixture(scope="module")
def seed() -> Any:
    return run_eval.load_seed()


def test_five_seed_scenarios(scenarios: list[Any]) -> None:
    seed_scenarios = [s for s in scenarios if s.card is None]
    ids = [s.id for s in seed_scenarios]
    assert len(ids) == 5 and len(set(ids)) == 5
    assert {s.mode for s in seed_scenarios} == {"story", "dm"}
    for s in seed_scenarios:
        assert s.title and s.note and s.input.strip()
        if s.mode == "story":
            assert s.checks["min_thoughts"] == 2 and s.checks["max_thoughts"] == 4
            assert {"tớ", "cậu", "tôi"} <= set(s.checks["narration_forbidden"])
        else:
            assert s.checks["thought_count"] == 0
    assert any("((" in s.input for s in seed_scenarios), "cần một kịch bản chỉ đạo (( ))"
    assert any("Lạc Dương" in s.input for s in seed_scenarios), "cần một kịch bản người chơi viết hành động cho Lạc Dương"


def test_only_filter(scenarios: list[Any]) -> None:
    picked = run_eval.load_scenarios(run_eval.DEFAULT_SCENARIOS, [scenarios[1].id])
    assert [s.id for s in picked] == [scenarios[1].id]
    with pytest.raises(run_eval.ScenarioError, match="Không có kịch bản"):
        run_eval.load_scenarios(run_eval.DEFAULT_SCENARIOS, ["khong-ton-tai"])


def test_every_scenario_builds_a_prompt(scenarios: list[Any]) -> None:
    for s in scenarios:
        setup = run_eval.load_setup(s)
        story, history, built = run_eval.build_scenario_prompt(s, setup, "gemma4:12b", run_eval.PromptBudget())
        assert story.mode == s.mode
        assert history[-1].role == "user" and history[-1].raw_content == s.input
        assert built.messages[0].role == "system"
        assert built.messages[-1].role == "user"
        assert built.options["num_predict"] == (900 if s.mode == "story" else 200)
        assert built.dropped_turns == 0
        assert all("((" not in m.content for m in built.messages)
        assert story.language == setup.story_settings["language"]
        if s.history is None:
            assert history[0].role == "assistant"
            assert history[0].raw_content == setup.card.greeting.replace("{{user}}", setup.persona.name)
            assert history[0].thought is not None
        else:
            assert len(history) == len(s.history) + 1


def test_directive_scenario_splits_directive(scenarios: list[Any], seed: Any) -> None:
    s = next(s for s in scenarios if "((" in s.input)
    _, history, built = run_eval.build_scenario_prompt(s, seed, "gemma4:12b", run_eval.PromptBudget())
    last = history[-1]
    assert last.directive and "ghen" in last.directive
    assert "((" not in last.visible_content and "ghen" not in last.visible_content
    assert last.directive in built.messages[-1].content


def _write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("body", "match"),
    [
        ("id: a\ninput: x\nmode: voice\n", "mode"),
        ("id: a\nmode: story\n", "input"),
        ("input: x\n", "id"),
        ("id: a\ninput: x\nchecks: {max_word: 3}\n", "không hỗ trợ"),
        ("id: a\ninput: x\nchecks: {max_words: -1}\n", "max_words"),
        ("id: a\ninput: x\nchecks: {narration_forbidden: tớ}\n", "narration_forbidden"),
        ("id: a\ninput: x\nhistory: [{role: system, content: hi}]\n", "role"),
        ("id: a\ninput: x\nhistory: [{role: user, content: ''}]\n", "content"),
        ("id: a\ninput: x\nextra: 1\n", "trường lạ"),
        ("- 1\n- 2\n", "mapping"),
    ],
)
def test_bad_scenario_rejected(tmp_path: Path, body: str, match: str) -> None:
    _write(tmp_path, "bad.yaml", body)
    with pytest.raises(run_eval.ScenarioError, match=match):
        run_eval.load_scenarios(tmp_path)


def test_duplicate_and_empty_dirs(tmp_path: Path) -> None:
    with pytest.raises(run_eval.ScenarioError, match="Không có file"):
        run_eval.load_scenarios(tmp_path)
    _write(tmp_path, "a.yaml", "id: same\ninput: x\n")
    _write(tmp_path, "b.yml", "id: same\ninput: y\n")
    with pytest.raises(run_eval.ScenarioError, match="Trùng id"):
        run_eval.load_scenarios(tmp_path)


def test_empty_history_override(tmp_path: Path, seed: Any) -> None:
    _write(tmp_path, "a.yaml", "id: a\nmode: dm\nhistory: []\ninput: chào\n")
    (s,) = run_eval.load_scenarios(tmp_path)
    _, history, built = run_eval.build_scenario_prompt(s, seed, "m", run_eval.PromptBudget())
    assert [m.role for m in history] == ["user"]
    assert [m.role for m in built.messages] == ["system", "user"]


# ---- run_eval.py: judge -------------------------------------------------------------------------


def test_judge_prompt_encodes_rules(seed: Any, scenarios: list[Any]) -> None:
    system = run_eval.judge_system_prompt("Lạc Dương", "Lâm Vãn", "story")
    for phrase in ("má ửng đỏ", "bàn tay lạnh", "Lời thoại mới của Lâm Vãn", "Hành động có chủ đích mới",
                   "quyết định", "chỉ đạo", "không chép lại", "follows_player", "godmodding",
                   "trích lại nguyên văn", "«...»"):
        assert phrase in system, phrase
    dm = run_eval.judge_system_prompt("Lạc Dương", "Lâm Vãn", "dm")
    assert "nhắn tin" in dm

    s = next(s for s in scenarios if "((" in s.input)
    _, history, _ = run_eval.build_scenario_prompt(s, seed, "m", run_eval.PromptBudget())
    messages = run_eval.judge_messages(seed, s.mode, history, "Anh im lặng. [Thought: hừ]")
    user = messages[1]["content"]
    assert "Thư viện sắp đóng cửa" in user  # lượt trước của Lạc Dương
    assert history[-1].visible_content in user
    assert f"Chỉ đạo ẩn của người chơi cho lượt này: {history[-1].directive}" in user
    assert "Anh im lặng. [Thought: hừ]" in user


def test_parse_judge_content() -> None:
    got = run_eval.parse_judge_content('{"reason": " ok ", "godmodding": false, "follows_player": true}')
    assert got == {"godmodding": False, "follows_player": True, "reason": "ok"}
    with pytest.raises(ValueError):
        run_eval.parse_judge_content('{"godmodding": "no", "follows_player": true}')
    with pytest.raises(ValueError):
        run_eval.parse_judge_content("[]")
    with pytest.raises(ValueError):
        run_eval.parse_judge_content("không phải json")


async def test_call_judge_request_and_think_retry() -> None:
    bodies: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        bodies.append(body)
        if "think" in body:
            return httpx.Response(400, json={"error": "model does not support thinking"})
        content = json.dumps({"reason": "Tốt.", "godmodding": False, "follows_player": True})
        return httpx.Response(200, json={"message": {"role": "assistant", "content": content}, "done": True})

    async with httpx.AsyncClient(base_url="http://ollama", transport=httpx.MockTransport(handler)) as http:
        verdict = await run_eval.call_judge(http, "gemma4:e4b", [{"role": "user", "content": "x"}])
    assert verdict["godmodding"] is False and verdict["follows_player"] is True and verdict["reason"] == "Tốt."
    assert bodies[0]["think"] is False and bodies[0]["stream"] is False
    assert bodies[0]["format"] == run_eval.JUDGE_SCHEMA
    assert set(run_eval.JUDGE_SCHEMA["properties"]) == {"godmodding", "follows_player", "reason"}
    assert "think" not in bodies[1]


async def test_call_judge_errors() -> None:
    def bad_json(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": {"content": "{}"}})

    def server_error(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    for handler, match in ((bad_json, "không đọc được"), (server_error, "HTTP 500")):
        async with httpx.AsyncClient(base_url="http://o", transport=httpx.MockTransport(handler)) as http:
            verdict = await run_eval.call_judge(http, "j", [])
        assert match in verdict["error"]


# Câu trả lời mẫu đúng luật cho ba kịch bản bộ card (06, 07, 08).
GOOD_VIET = (
    "Khang nghe xong thì bật cười, tiếng cười lẫn vào tiếng mưa rào rào trên mái tôn bên kia đường.\n\n"
    "[Thought: Lo bị đồn mà không lo ướt hết người. Đúng là nhóc con mới đi làm.]\n\n"
    '"Đồn gì mà đồn. Giờ này mấy anh chị về hết rồi, còn ai đâu mà thấy." Anh gỡ túi nilon, giũ bộ áo mưa '
    'ra rồi choàng lên vai cô. "Mà có ai thấy thì anh nói anh tiện đường. Em mặc vô đi, anh xuống hầm lấy xe."\n\n'
    "Anh kéo mũ áo mưa trùm lên mái tóc còn lấm tấm nước của cô, ngón tay dừng lại một chút ở mép vải rồi rút về.\n\n"
    "[Thought: Nói tiện đường cho nhẹ nhàng vậy thôi. Thật ra nhà mình ở bên kia cầu, chở cô ấy về xong "
    "chắc phải vòng thêm cả chục phút.]\n\n"
    '"Đứng yên đây nha, đừng chạy ra mưa." Anh quay lưng đi về phía cầu thang xuống hầm xe, được vài bước '
    "lại ngoái đầu nhìn cô."
)
GOOD_CO_TRANG = (
    "Tạ Vân Lan không đáp ngay. Nàng nhìn bàn tay đang run nhẹ của hắn, rồi nhìn vệt máu mờ nơi khóe miệng "
    "mà hắn chưa kịp lau.\n\n"
    "[Thought: Còn biết sợ làm ta mất mặt, sao không biết sợ chết? Ba năm rồi, cái tính cứng đầu này vẫn "
    "chẳng đổi.]\n\n"
    '"Từ lúc sư đệ bắt đầu luyện thức thứ năm." Giọng nàng vẫn lạnh. "Thiếu một chút? Chân khí của đệ sắp '
    'đâm thủng kinh mạch rồi, một chút đó phải đổi bằng nửa cái mạng."\n\n'
    "Nàng đặt bình sứ vào lòng bàn tay hắn, đầu ngón tay lạnh như ngọc chạm qua rồi rời đi.\n\n"
    '"Thắng hay thua là chuyện của ngày mai. Đêm nay đệ uống đan, điều tức, rồi về nghỉ." Nàng xoay người, '
    'tà áo trắng lướt qua đám cỏ ướt sương. "Thể diện của ta, không đến lượt đệ lo."\n\n'
    "[Thought: Nếu ngày mai hắn thật sự thua, ta sẽ tự mình đi xin sư tôn cho hắn thêm một năm. Nhưng "
    "chuyện này tuyệt đối không thể để hắn biết.]\n\n"
    "Nàng dừng bước ở mép rừng trúc, không quay đầu lại, chờ xem hắn có chịu nghe lời hay không."
)
GOOD_EN = (
    "Lạc Dương caught the jacket before it slid to the floor and settled it back over her shoulders.\n\n"
    "[Thought: She wakes up and the first thing she asks about is some stranger. At least she noticed.]\n\n"
    '"Most of it," he said. "You missed the sunset."\n\n'
    "He followed her glance toward the stairwell, where the freshman had already disappeared, and his "
    "expression didn't change.\n\n"
    '"No one. Someone who wanted my WeChat." He slid the milk tea closer to her hand. "I told her it '
    "wasn't convenient.\"\n\n"
    "[Thought: I could have just said I don't know her. Why did I want her to hear that I said no?]\n\n"
    "He tidied the loose pages of her notes into a neat stack, the way she always forgot to. "
    '"Drink that before it gets cold. Hotpot or noodles, Vãn Vãn? You pick."\n\n'
    "He set the stack beside her bag and waited, one hand resting on the back of her chair."
)


# ---- run_eval.py: chạy trọn với Ollama giả ------------------------------------------------------


class FakeOllama:
    """Ollama giả cho run(): /api/tags, /api/chat (stream hoặc judge), /api/generate (unload)."""

    def __init__(self, replies: dict[str, str]) -> None:
        self.replies = replies
        self.chat_bodies: list[dict[str, Any]] = []
        self.judge_bodies: list[dict[str, Any]] = []
        self.unloaded: list[str] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "gemma4:12b"}, {"name": "gemma4:e4b"}]})
        body = json.loads(request.content)
        if path == "/api/generate":
            self.unloaded.append(body["model"])
            return httpx.Response(200, json={"done": True})
        assert path == "/api/chat"
        if body["stream"] is False:
            self.judge_bodies.append(body)
            god = "Lâm Vãn: " in body["messages"][1]["content"]
            content = json.dumps({"reason": "Lý do.", "godmodding": god, "follows_player": not god})
            return httpx.Response(200, json={"message": {"content": content}, "done": True})
        self.chat_bodies.append(body)
        text = "Chào"  # warm-up
        last = body["messages"][-1]["content"]
        for key, reply in self.replies.items():
            if key in last:
                text = reply
        chunks = [text[i : i + 9] for i in range(0, len(text), 9)]
        lines = [json.dumps({"message": {"content": c}, "done": False}) for c in chunks]
        lines.append(
            json.dumps(
                {
                    "message": {"content": ""},
                    "done": True,
                    "done_reason": "stop",
                    "eval_count": 40,
                    "eval_duration": 2_000_000_000,
                    "prompt_eval_count": 1500,
                }
            )
        )
        return httpx.Response(200, content=("\n".join(lines) + "\n").encode())


async def test_run_end_to_end_with_fake_ollama(tmp_path: Path, scenarios: list[Any]) -> None:
    good = 'Lạc Dương khẽ cười, nhìn cô.\n\n[Thought: Ngốc thật.]\n\n"Ngủ đủ chưa?"\n\n[Thought: Lại thức khuya rồi.]'
    replies = {
        "sớm hơn": good,  # 01
        "im lặng": 'Anh im lặng chờ.\nLâm Vãn: Tớ không sao.\n[Thought: hừ]',  # 02: godmodding + dòng persona
        "không ngủ được": "Còn. Ngủ không được thì gọi cho tớ.",  # 05 dm
        "đồn bậy": GOOD_VIET,  # 06
        "mất mặt sao": GOOD_CO_TRANG,  # 07
        "who was that": GOOD_EN,  # 08
    }
    fake = FakeOllama(replies)
    only = [arg for sid in CORE_IDS for arg in ("--only", sid)]
    args = run_eval.parse_args(["--model", "gemma4:12b", "--ollama-url", "http://ollama", *only])
    code = await run_eval.run(args, transport=httpx.MockTransport(fake), results_dir=tmp_path)
    assert code == 0

    (out,) = tmp_path.iterdir()
    assert out.name.startswith("eval-")
    raw = json.loads((out / "raw.json").read_text(encoding="utf-8"))
    report = (out / "report.md").read_text(encoding="utf-8")
    assert [r["id"] for r in raw["results"]] == [s.id for s in scenarios]
    by_id = {r["id"]: r for r in raw["results"]}

    first = by_id[scenarios[0].id]
    assert first["reply"] == good and first["stats"]["tok_per_s"] == 20.0
    assert [p.split(" ")[0] for p in first["problems"]] == ["ngắn"]  # câu mẫu ngắn hơn min_words
    assert first["judge"]["godmodding"] is False and first["judge"]["follows_player"] is True

    silent = by_id["02-bay-im-lang"]
    assert 'có dòng "Lâm Vãn:"' in silent["problems"]
    assert silent["judge"]["godmodding"] is True

    dm = by_id["05-dm"]
    assert dm["problems"] == [] and dm["thought"] is None

    # Kịch bản dùng bộ card: câu trả lời mẫu đúng luật thì không có lỗi máy nào.
    for sid, reply in (("06-viet-hien-dai", GOOD_VIET), ("07-co-trang", GOOD_CO_TRANG), ("08-tieng-anh", GOOD_EN)):
        assert by_id[sid]["reply"] == reply
        assert by_id[sid]["problems"] == [], (sid, by_id[sid]["problems"])
        assert by_id[sid]["judge"]["godmodding"] is False
    assert by_id["06-viet-hien-dai"]["card"] == "viet_hien_dai.json" and by_id["01-mo-dau"]["card"] == "seed"
    assert by_id["08-tieng-anh"]["language"] == "en"
    en_system = by_id["08-tieng-anh"]["prompt"]["messages"][0]["content"]
    assert "Lạc Dương" in en_system and "English" in en_system and "{{user}}" not in en_system
    # Judge của kịch bản bộ card dùng đúng tên nhân vật/persona của bộ card.
    judge_users = [b["messages"][1]["content"] for b in fake.judge_bodies]
    assert any("Lượt người chơi vừa viết cho Lục Trần" in u for u in judge_users)
    assert any("Lượt trước của Trần Minh Khang" in u for u in judge_users)

    # warm-up + 8 kịch bản stream; judge 8 lần; nhả cả model chat lẫn judge.
    assert len(fake.chat_bodies) == 1 + len(scenarios) == 9
    assert fake.chat_bodies[0]["options"]["num_ctx"] == fake.chat_bodies[1]["options"]["num_ctx"]
    assert len(fake.judge_bodies) == 8
    assert fake.unloaded == ["gemma4:12b", "gemma4:e4b"]

    assert "| Kịch bản |" in report and "Ngốc thật." in report and "Lâm Vãn: Tớ không sao." in report
    assert "Card: Tạ Vân Lan (trung_co_dai.json), persona Lục Trần" in report
    assert raw["aggregate"]["godmodding"] == 1 and raw["aggregate"]["judged"] == 8


async def test_run_no_judge_only_and_missing_model(tmp_path: Path) -> None:
    fake = FakeOllama({})
    transport = httpx.MockTransport(fake)
    args = run_eval.parse_args(["--model", "gemma4:12b", "--no-judge", "--only", "05-dm", "--keep-loaded",
                                "--ollama-url", "http://ollama"])
    assert await run_eval.run(args, transport=transport, results_dir=tmp_path) == 0
    raw = json.loads(next(tmp_path.iterdir()).joinpath("raw.json").read_text(encoding="utf-8"))
    assert [r["id"] for r in raw["results"]] == ["05-dm"]
    assert raw["results"][0]["judge"] is None and fake.judge_bodies == [] and fake.unloaded == []

    missing = run_eval.parse_args(["--model", "khong-co:1b", "--ollama-url", "http://ollama"])
    assert await run_eval.run(missing, transport=transport, results_dir=tmp_path / "x") == 1
    assert not (tmp_path / "x").exists()


def test_thought_range_checks() -> None:
    one = 'Anh nhìn cô. "Ừ."\n[Thought: Ngốc.]'
    assert checks.run_checks(one, {"min_thoughts": 2, "max_thoughts": 4}) == ["1 Thought (tối thiểu 2)"]
    five = "\n".join(f"Câu {i}.\n[Thought: nghĩ {i}]" for i in range(5))
    assert checks.run_checks(five, {"min_thoughts": 2, "max_thoughts": 4}) == ["5 Thought (tối đa 4)"]


def test_thought_style_end_switches_scenario_checks(scenarios: list[Any]) -> None:
    story = next(s for s in scenarios if s.mode == "story")
    assert run_eval.checks_for_style(story, "end")["thought_count"] == 1
    assert run_eval.checks_for_style(story, "end")["thought_at_end"] is True
    assert "min_thoughts" not in run_eval.checks_for_style(story, "end")
    assert run_eval.checks_for_style(story, None) == story.checks
    dm = next(s for s in scenarios if s.mode == "dm")
    assert run_eval.checks_for_style(dm, "end") == dm.checks


def test_adjacent_thoughts_check() -> None:
    together = 'Anh nhìn cô.\n\n[Thought: Một.]\n\n[ thought: Hai.]\n\n"Ừ."'
    spread = 'Anh nhìn cô.\n\n[Thought: Một.]\n\n"Ừ."\n\n[Thought: Hai.]'
    assert checks.run_checks(together, {"no_adjacent_thoughts": True}) == ["Thought liền nhau"]
    assert checks.run_checks(spread, {"no_adjacent_thoughts": True}) == []
    assert checks.run_checks(together, {}) == []


def test_unclosed_inline_thought_is_caught() -> None:
    # Thought đầu quên `]`: app nuốt cả đoạn truyện sau vào Thought, harness phải báo lỗi.
    text = ('Anh nhìn cô. [Thought: Cô ấy mệt thật rồi.\n\nAnh đứng dậy. "Đi thôi, tớ đưa cậu về."\n\n'
            '[Thought: Phải đưa cô ấy về.]\n\nAnh chờ cô trả lời.')
    problems = checks.run_checks(text, {"min_thoughts": 2, "max_thoughts": 4})
    # Như app: Thought đầu hết ở dòng trống, phần sau vẫn là truyện, nên có đủ 2 Thought.
    assert problems == ["Thought chưa đóng"]
    assert checks.count_thoughts(text) == 2


GEMMA_UNCLOSED = (
    "Hắn cười.\n\n"
    '[Thought: Người đẹp nào? Tôi chỉ đang trêu cậu thôi, Đậu Đinh."\n\n'
    "Cố Hoài Dã vươn tay.\n\n"
    '"Sao?"'
)


def test_closed_thoughts_unchanged() -> None:
    text = 'Anh cười. [Thought: Dòng một.\nDòng hai."] Hết.\n\n[Thought: Ba.]'
    assert checks.count_thoughts(text) == 2
    assert checks.thought_bodies(text) == ['Dòng một.\nDòng hai."', "Ba."]
    assert checks.strip_thoughts(text) == "Anh cười.  Hết.\n\n"
    assert not checks.thought_unclosed(text)


def test_unclosed_thought_ends_at_blank_line_like_the_app() -> None:
    assert checks.thought_unclosed(GEMMA_UNCLOSED)
    assert checks.count_thoughts(GEMMA_UNCLOSED) == 1
    assert checks.thought_bodies(GEMMA_UNCLOSED) == ["Người đẹp nào? Tôi chỉ đang trêu cậu thôi, Đậu Đinh."]
    assert checks.strip_thoughts(GEMMA_UNCLOSED) == 'Hắn cười.\n\n\n\nCố Hoài Dã vươn tay.\n\n"Sao?"'
    # Phần sau dòng trống được kiểm tra như dẫn truyện.
    assert "Cố Hoài Dã vươn tay." in checks.narration_only(GEMMA_UNCLOSED)
    assert '"Sao?"' not in checks.narration_only(GEMMA_UNCLOSED)
    assert checks.dialogue_parts(GEMMA_UNCLOSED) == ["Sao?"]
    problems = checks.run_checks(GEMMA_UNCLOSED, {"thought_count": 1, "thought_at_end": True})
    assert problems == ["Thought chưa đóng", "Thought không ở cuối"]
    # Dòng trống có space/tab cũng là ngắt đoạn; `\n` đơn thì không.
    text = "Mở. [Thought: giận rồi \t\n \t\nAnh tớ bước tới."
    assert checks.find_words(checks.narration_only(text), ["tớ"]) == ["tớ"]
    assert checks.thought_bodies("[Thought: Dòng một.\nDòng hai") == ["Dòng một.\nDòng hai"]
    assert checks.strip_thoughts("A [Thought: Dòng một.\nDòng hai") == "A "


def test_unclosed_thought_body_drops_one_unmatched_quote() -> None:
    assert checks.thought_bodies('[Thought: Ngốc thật."  ') == ["Ngốc thật."]
    assert checks.thought_bodies("[Thought: đi mất ” ") == ["đi mất"]
    assert checks.thought_bodies("[Thought: đi mất “") == ["đi mất"]
    assert checks.thought_bodies('[Thought: a "" "\n\nb') == ['a ""']
    assert checks.thought_bodies('[Thought: Cô ấy nói "đi thôi"\n\nb') == ['Cô ấy nói "đi thôi"']
    assert checks.thought_bodies("[Thought: bảo “đợi”") == ["bảo “đợi”"]
    # Có `]` thì giữ nguyên dấu ngoặc kép.
    assert checks.thought_bodies('[Thought: Đậu Đinh."]') == ['Đậu Đinh."']


def test_adjacent_thoughts_include_unclosed_ones() -> None:
    text = "Anh nhìn cô.\n\n[Thought: Một.\n\n[ thought: Hai.]\n\nAnh đi."
    assert checks.run_checks(text, {"no_adjacent_thoughts": True}) == ["Thought chưa đóng", "Thought liền nhau"]


def test_thought_tag_is_case_and_space_tolerant_like_the_app() -> None:
    text = "Cô ấy cười. [thought: Cậu ngốc thật, tớ thích cậu.]"
    assert checks.run_checks(text, {"thought_count": 1, "narration_forbidden": ["tớ", "cậu", "tôi"]}) == []
    assert checks.run_checks("Nhắn. [ Thought : hmm]", {"thought_count": 0}) == ["1 Thought"]


def test_thought_at_end_check() -> None:
    assert checks.run_checks("Anh cười.\n\n[Thought: Vui.]", {"thought_at_end": True}) == []
    assert checks.run_checks("[Thought: Vui.]\n\nAnh cười.", {"thought_at_end": True}) == ["Thought không ở cuối"]


# ---- Phase 2: kiểm tra ngôn ngữ và xưng hô trong lời thoại -------------------------------------


def test_find_words_is_whole_word_unicode_and_skips_compounds() -> None:
    assert checks.find_words("Anh đi. Thanh anh tuấn.", ["anh"]) == ["anh"]
    assert checks.find_words("ANH ơi, Anh à", ["anh"]) == ["anh", "anh"]
    assert checks.find_words("Đệ tử Thanh Vân, người ta nói", ["đệ", "ta"]) == []
    assert checks.find_words("Sư  đệ, đệ đi đâu?", ["sư đệ", "đệ"]) == ["sư đệ", "đệ"]
    # Từ ghép được tìm đích danh thì không bị che.
    assert checks.find_words("Hắn là đệ tử.", ["đệ tử"]) == ["đệ tử"]
    # NFD (dấu tách rời) vẫn khớp như NFC.
    assert checks.find_words(unicodedata.normalize("NFD", "Tớ đây"), ["tớ"]) == ["tớ"]
    assert checks.find_words("abc", []) == []


def test_narration_forbidden_ignores_compounds() -> None:
    text = 'Người ta đồn hắn là bậc anh hùng, kiếm pháp tôi luyện mười năm. "Ta không tin."'
    assert checks.auto_check(text, {"narration_forbidden": ["ta", "anh", "tôi"]}) == []
    assert checks.auto_check("Anh nói với em.", {"narration_forbidden": ["em"]}) == ["xưng hô trong dẫn truyện x1"]


def test_language_vi_flags_english_and_missing_diacritics() -> None:
    good = 'Khang bật cười. "Đồn gì mà đồn, em mặc áo mưa vô đi." [Thought: Ngốc thật.]'
    assert checks.language_problems(good, "vi") == []
    mixed = 'Anh cười. "Em à, what are you doing? Đi thôi." [Thought: Cô ấy thật là...]'
    (problem,) = checks.language_problems(mixed, "vi")
    assert problem.startswith("lẫn tiếng Anh x3") and "what" in problem
    # Hai từ tiếng Anh thì chưa tính.
    assert checks.language_problems('Anh cười. "Sorry em, please đợi anh chút."', "vi") == []
    no_marks = "Anh nhin co, khong noi gi, chi im lang dung do mot luc lau roi moi di."
    assert checks.language_problems(no_marks, "vi") == ["ít dấu tiếng Việt (0% số từ)"]
    # Câu quá ngắn không xét tỉ lệ dấu.
    assert checks.language_problems("Ok anh.", "vi") == []
    # Tên riêng không dấu (bỏ đi) không kéo tỉ lệ xuống.
    names_heavy = "Minh Khang " * 25 + "gật đầu rồi đi về nhà."
    assert checks.language_problems(names_heavy, "vi")[0].startswith("ít dấu tiếng Việt")
    assert checks.language_problems(names_heavy, "vi", ["Minh Khang"]) == []


def test_language_en_flags_vietnamese_outside_names() -> None:
    names = ["Lạc Dương", "Lâm Vãn", "Vãn Vãn", "A Vãn"]
    good = (
        'Lạc Dương smiled at Lâm Vãn. "Vãn Vãn, wake up." [Thought: She never listens.] '
        "Dương sighed and ordered a café latte; A Vãn would want one too."
    )
    assert checks.language_problems(good, "en", names) == []
    drift = 'He looked at her. "Vãn Vãn, dậy thôi, tớ đưa cậu đi ăn." [Thought: Cô ấy mệt rồi.]'
    (problem,) = checks.language_problems(drift, "en", names)
    assert problem.startswith("lẫn tiếng Việt x") and "dậy" in problem and "tớ" in problem
    # Không truyền tên thì tên có dấu cũng bị tính.
    assert checks.language_problems("Lạc Dương smiled.", "en") == ["lẫn tiếng Việt x2 (Lạc, Dương)"]
    with pytest.raises(ValueError):
        checks.language_problems("x", "fr")


def test_dialogue_parts_and_thought_bodies() -> None:
    text = 'Nàng nói: "Ta đi đây." Rồi “đệ ở lại” [Thought: Hắn sẽ ổn.] Hết.'
    assert checks.dialogue_parts(text) == ["Ta đi đây.", "đệ ở lại"]
    assert checks.thought_bodies(text) == ["Hắn sẽ ổn."]
    assert checks.dialogue_parts("Ngủ sớm đi. [Thought: lo]", dm=True) == ["Ngủ sớm đi."]
    assert checks.dialogue_parts("Không có lời thoại.") == []


def test_dialogue_forbidden_checks_dialogue_and_thought_only() -> None:
    rules = {"dialogue_forbidden": ["anh", "em", "tớ", "cậu"]}
    ok = 'Hắn khẽ nói: "Ta biết rồi, sư tỷ." [Thought: Nàng lạnh lùng thật.] Anh hùng khó qua ải mỹ nhân.'
    assert checks.run_checks(ok, rules) == []
    bad = 'Nàng nhìn hắn. "Anh đi đi, em mệt rồi." [Thought: Tớ không muốn gặp cậu ấy.]'
    (problem,) = checks.run_checks(bad, rules)
    assert problem == "xưng hô sai trong lời thoại x4 (anh, em, tớ, cậu)"
    # DM: cả tin nhắn là lời thoại.
    assert checks.run_checks("Em ngủ chưa?", rules, dm=True) == ["xưng hô sai trong lời thoại x1 (em)"]


def test_dialogue_required_any() -> None:
    rules = {"dialogue_required_any": ["anh", "em"]}
    assert checks.run_checks('Anh cười. "Về thôi em."', rules) == []
    # Có lời thoại nhưng không có xưng hô nào (tên "Ngọc Anh" không tính là "anh").
    problems = checks.run_checks('Anh cười. "Ngọc Anh, về thôi."', rules, names=["Ngọc Anh"])
    assert problems == ["lời thoại không có xưng hô nào trong [anh, em]"]
    # Xưng hô chỉ nằm trong Thought vẫn được tính.
    assert checks.run_checks('Anh cười. "Về thôi." [Thought: Em ấy mệt rồi.]', rules) == []
    # Không có lời thoại thì không đòi.
    assert checks.run_checks("Anh im lặng nhìn mưa.", rules) == []
    # persona_name cũng được coi là tên riêng.
    assert checks.run_checks('"Ngọc Anh ơi."', rules, persona_name="Ngọc Anh") == [
        "lời thoại không có xưng hô nào trong [anh, em]"
    ]


def test_run_checks_old_signature_still_works() -> None:
    # bakeoff.py gọi auto_check/run_checks với tham số cũ: vẫn chạy như trước.
    assert checks.run_checks('Anh cười. "Ừ."\n[Thought: Vui.]', {"thought_count": 1}) == []


# ---- Phase 2: bộ card và kịch bản dùng bộ card --------------------------------------------------

CARD_SCENARIOS = {
    "06-viet-hien-dai": ("viet_hien_dai.json", "vi"),
    "07-co-trang": ("trung_co_dai.json", "vi"),
    "08-tieng-anh": ("lac_duong_en.json", "en"),
}


def test_card_scenarios_present(scenarios: list[Any]) -> None:
    by_id = {s.id: s for s in scenarios}
    assert len(scenarios) == 8
    for sid, (card, language) in CARD_SCENARIOS.items():
        s = by_id[sid]
        assert s.card == card and s.mode == "story" and s.title and s.note
        assert s.checks["language"] == language
        assert s.checks["min_thoughts"] == 2 and s.checks["max_thoughts"] == 4 and s.checks["no_adjacent_thoughts"]
        assert s.checks["narration_forbidden"] and s.checks["dialogue_required_any"] and s.checks["dialogue_forbidden"]
        assert "bầu không khí" in s.checks["forbidden_phrases"]
    assert {"anh", "em", "tớ", "cậu"} <= set(by_id["07-co-trang"].checks["dialogue_forbidden"])
    assert {"I", "you"} <= set(by_id["08-tieng-anh"].checks["narration_forbidden"])


@pytest.mark.parametrize("sid", sorted(CARD_SCENARIOS))
def test_card_bundle_greeting_follows_its_own_rules(scenarios: list[Any], sid: str) -> None:
    s = next(s for s in scenarios if s.id == sid)
    setup = run_eval.load_setup(s)
    card, persona, settings = setup.card, setup.persona, setup.story_settings
    assert setup.source == CARD_SCENARIOS[sid][0]
    assert card.language == settings["language"] == CARD_SCENARIOS[sid][1]
    assert settings["thought_style"] == "inline" and settings["pov"] == "third" and settings["title"]
    assert "{{user}}" in card.greeting and "{{" not in settings["scenario"]
    np_ = settings["narration_pronouns"]
    if card.language == "en":
        assert (card.address_terms.self_term, card.address_terms.player_term) == ("I", "you")
        assert np_ == {"character": "he", "player": "she"}
    _, history, _ = run_eval.build_scenario_prompt(s, setup, "m", run_eval.PromptBudget())
    greeting = history[0].raw_content
    assert persona.name in greeting and "{{" not in greeting
    # Lời mở đầu: 2 Thought, mỗi Thought 2-3 câu, không liền nhau, không ở cuối; qua mọi kiểm tra của kịch bản.
    bodies = checks.thought_bodies(greeting)
    assert len(bodies) == 2
    for body in bodies:
        assert 2 <= len(re.findall(r"[.!?]+(?:\s|$)", body)) <= 3, body
    assert checks.thought_not_at_end(greeting)  # còn chữ sau Thought cuối
    rules = {k: v for k, v in s.checks.items() if k not in ("min_words", "max_words")}
    assert checks.run_checks(greeting, rules, persona_name=persona.name, names=setup.names()) == []
    # Không dùng từ xưng hô trong dẫn truyện (kể cả từ của chính card).
    terms = [card.address_terms.self_term, card.address_terms.player_term]
    assert checks.find_words(checks.narration_only(greeting), [t for t in terms if t not in np_.values()]) == []


def test_bad_replies_for_card_scenarios_are_caught(scenarios: list[Any]) -> None:
    by_id = {s.id: s for s in scenarios}

    def problems(sid: str, text: str) -> list[str]:
        s = by_id[sid]
        setup = run_eval.load_setup(s)
        return checks.run_checks(text, s.checks, persona_name=setup.persona.name, names=setup.names())

    modern = GOOD_CO_TRANG.replace('"Thể diện của ta', '"Thể diện của anh').replace("sư đệ bắt đầu", "em bắt đầu")
    got = problems("07-co-trang", modern)
    assert any(p.startswith("xưng hô sai trong lời thoại") for p in got), got

    viet_em = GOOD_VIET.replace("rồi choàng lên vai cô", "rồi choàng lên vai em")
    assert "xưng hô trong dẫn truyện x1" in problems("06-viet-hien-dai", viet_em)

    drift = GOOD_EN.replace('"Most of it," he said.', '"Ừ, ngủ cả buổi chiều luôn," he said.')
    got = problems("08-tieng-anh", drift)
    assert any(p.startswith("lẫn tiếng Việt") for p in got), got

    first_person = GOOD_EN.replace("He set the stack", "I set the stack")
    assert "xưng hô trong dẫn truyện x1" in problems("08-tieng-anh", first_person)


def test_load_card_bundle_errors(tmp_path: Path) -> None:
    good = json.loads((run_eval.DEFAULT_CARDS / "viet_hien_dai.json").read_text(encoding="utf-8"))

    def write(name: str, data: Any) -> Path:
        path = tmp_path / name
        path.write_text(data if isinstance(data, str) else json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return path

    assert run_eval.load_card_bundle(write("ok.json", good)).card.name == "Trần Minh Khang"
    cases = [
        ("not-json.json", "{", "JSON"),
        ("missing.json", {"card": good["card"], "persona": good["persona"]}, "ba khoá"),
        ("no-title.json", {**good, "story": {k: v for k, v in good["story"].items() if k != "title"}}, "title"),
        ("extra.json", {**good, "story": {**good["story"], "mood": "vui"}}, "trường lạ"),
        ("bad-card.json", {**good, "card": {"name": "X"}}, "không hợp lệ"),
        ("bad-lang.json", {**good, "story": {**good["story"], "language": "fr"}}, "không hợp lệ"),
    ]
    for name, data, match in cases:
        with pytest.raises(run_eval.CardBundleError, match=match):
            run_eval.load_card_bundle(write(name, data))
    with pytest.raises(run_eval.CardBundleError, match="Không có file"):
        run_eval.load_card_bundle(tmp_path / "khong-co.json")


@pytest.mark.parametrize(
    ("body", "match"),
    [
        ("id: a\ninput: x\nchecks: {language: fr}\n", "language"),
        ("id: a\ninput: x\nchecks: {dialogue_forbidden: anh}\n", "dialogue_forbidden"),
        ("id: a\ninput: x\nchecks: {dialogue_required_any: ['']}\n", "dialogue_required_any"),
        ("id: a\ninput: x\ncard: ../seed.json\n", "card"),
        ("id: a\ninput: x\ncard: 3\n", "card"),
    ],
)
def test_bad_phase2_scenario_rejected(tmp_path: Path, body: str, match: str) -> None:
    _write(tmp_path, "bad.yaml", body)
    with pytest.raises(run_eval.ScenarioError, match=match):
        run_eval.load_scenarios(tmp_path)


def test_card_key_without_extension_and_seed_names(tmp_path: Path) -> None:
    _write(tmp_path, "a.yaml", "id: a\ninput: x\ncard: viet_hien_dai\n")
    (s,) = run_eval.load_scenarios(tmp_path)
    assert s.card == "viet_hien_dai.json"
    assert run_eval.load_setup(s).names() == ["Trần Minh Khang", "Ngọc Anh", "nhóc"]
    assert run_eval.load_seed().names() == ["Lạc Dương", "Lâm Vãn", "Vãn Vãn", "A Vãn"]


async def test_run_with_custom_cards_dir_and_missing_card(tmp_path: Path) -> None:
    scen = tmp_path / "scen"
    cards = tmp_path / "cards"
    scen.mkdir()
    cards.mkdir()
    bundle = json.loads((run_eval.DEFAULT_CARDS / "lac_duong_en.json").read_text(encoding="utf-8"))
    bundle["persona"]["name"] = "Mia"
    (cards / "mia.json").write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
    _write(
        scen,
        "a.yaml",
        "id: en-dm\nmode: dm\ncard: mia.json\nhistory: []\ninput: you up?\n"
        "checks: {language: en, thought_count: 0, dialogue_required_any: [I, you]}\n",
    )
    fake = FakeOllama({"you up?": "Yeah, I'm up. Can't sleep either?"})
    out_dir = tmp_path / "out"
    args = run_eval.parse_args(["--model", "gemma4:12b", "--no-judge", "--scenarios", str(scen),
                                "--cards", str(cards), "--ollama-url", "http://ollama"])
    assert await run_eval.run(args, transport=httpx.MockTransport(fake), results_dir=out_dir) == 0
    raw = json.loads(next(out_dir.iterdir()).joinpath("raw.json").read_text(encoding="utf-8"))
    (result,) = raw["results"]
    assert result["card"] == "mia.json" and result["language"] == "en" and result["problems"] == []
    system = result["prompt"]["messages"][0]["content"]
    assert "Lạc Dương is male, Mia is female" in system and "texting Mia in English" in system

    # Bộ card không tồn tại: báo lỗi kịch bản (mã 2) trước khi gọi Ollama.
    (cards / "mia.json").unlink()
    fake2 = FakeOllama({})
    assert await run_eval.run(args, transport=httpx.MockTransport(fake2), results_dir=tmp_path / "out2") == 2
    assert fake2.chat_bodies == [] and not (tmp_path / "out2").exists()
