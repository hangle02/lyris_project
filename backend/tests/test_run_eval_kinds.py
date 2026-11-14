"""Test cho các loại kịch bản model thật mới của harness (harness/kinds.py, run_eval.py) — không cần Ollama.

Mỗi luật máy được thử hai chiều: câu trả lời / kết quả xấu phải ra lỗi, kết quả tốt thì không. Cuối file chạy
trọn run_eval với Ollama giả (httpx.MockTransport) trên mọi kịch bản mới, cả app thật trong tiến trình (F14).
"""
from __future__ import annotations

import importlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import httpx
import pytest

HARNESS_DIR = Path(__file__).resolve().parents[2] / "harness"
if str(HARNESS_DIR) not in sys.path:
    sys.path.insert(0, str(HARNESS_DIR))

checks = importlib.import_module("checks")
kinds = importlib.import_module("kinds")
run_eval = importlib.import_module("run_eval")
bakeoff = importlib.import_module("bakeoff")

NEW_IDS = [
    "f05-chi-dao",
    "f07-thought-long",
    "f07-thought-cuoi",
    "f09-cam-xuc",
    "f10-ky-uc",
    "f10-tom-tat",
    "f12-dm-xung-ten",
    "f13-dm-10-luot",
    "f14-ttft",
    "f15-goi-y",
    "f17-the-gioi",
    "f19-viet-nhap",
    "f36-bakeoff",
    "f36-chay-long",
]


# ---- luật máy mới trong checks.py (kịch bản reply) -------------------------------------------------------


def test_directive_echo_catches_copied_directive() -> None:
    directive = "Lạc Dương ghen nhưng không nói ra, chỉ thể hiện qua hành động và giọng điệu"
    bad = 'Anh im lặng. [Thought: Phải thể hiện qua hành động và giọng điệu thôi.]\n\n"Ừ."'
    good = 'Anh đặt cốc trà xuống hơi mạnh tay. [Thought: Học trưởng Chu à.]\n\n"Tuỳ cậu."'
    rules = {"directive_echo": True}
    assert checks.run_checks(bad, rules, directive=directive) == ["chép lại chỉ đạo «thể hiện qua hành động»"]
    assert checks.run_checks(good, rules, directive=directive) == []
    assert checks.run_checks(bad, rules, directive=None) == []  # không có chỉ đạo thì không có gì để chép


def test_say_forbidden_only_checks_spoken_dialogue() -> None:
    rules = {"say_forbidden": ["ghen"]}
    said = 'Anh quay đi. "Tớ ghen đấy, được chưa?"'
    thought = 'Anh quay đi.\n\n[Thought: Mình ghen thật rồi.]\n\n"Tuỳ cậu."'
    assert checks.run_checks(said, rules) == ["nói thẳng trong lời thoại x1 (ghen)"]
    assert checks.run_checks(thought, rules) == []
    assert checks.run_checks("Tớ ghen đấy.", rules, dm=True) == ["nói thẳng trong lời thoại x1 (ghen)"]


def test_forbidden_patterns_and_required_any() -> None:
    pattern = "chưa (hề |từng |bao giờ |có )?(nói|cho|tiết lộ|giới thiệu|xưng)[^.!?\\]]{0,30}tên"
    bad = "Anh khựng lại.\n\n[Thought: Mình chưa hề nói tên với ai ở đây cả.]"
    good = "Anh khựng lại.\n\n[Thought: Cô ấy còn nhớ tên mình từ tin nhắn tối qua.]"
    assert checks.run_checks(bad, {"forbidden_patterns": [pattern]}) == ["có câu bị cấm «chưa hề nói tên»"]
    assert checks.run_checks(good, {"forbidden_patterns": [pattern]}) == []
    rules = {"required_any": ["chè bưởi", "nước cốt dừa"]}
    assert checks.run_checks('"Vẫn chè bưởi như mọi khi."', rules) == []
    assert checks.run_checks('"Món gì cũng được."', rules) == ["không có chi tiết nào trong [chè bưởi, nước cốt dừa]"]


def test_prompt_includes_and_excludes() -> None:
    scenarios = {s.id: s for s in run_eval.load_scenarios(run_eval.DEFAULT_SCENARIOS, ["f17-the-gioi"])}
    s = scenarios["f17-the-gioi"]
    setup = run_eval.load_setup(s)
    _, _, built = run_eval.build_scenario_prompt(s, setup, "gemma4:12b", run_eval.PromptBudget())
    assert run_eval.prompt_problems(built, s.checks) == []
    assert [u.title for u in built.lore_used] == ["Quán chè bà Tư"]  # mục {{user}} khớp từ khoá nhưng không gửi
    leaked = built.model_copy(update={"messages": [*built.messages[:-1], built.messages[-1].model_copy(update={"content": "lá thư"})]})
    assert 'prompt có "lá thư" (không được gửi cho model)' in run_eval.prompt_problems(leaked, s.checks)


# ---- extract (F09, F10) -------------------------------------------------------------------------------


def test_delta_problems() -> None:
    zero = {k: 0 for k in kinds.EMOTION_KEYS}
    assert kinds.delta_problems({**zero, "trust": -1, "obsession": 2}, {"delta": {"trust": "down"}}) == []
    assert kinds.delta_problems({**zero, "trust": 1}, {"delta": {"trust": "down"}}) == ["trust +1 (cần down)"]
    assert kinds.delta_problems({**zero, "aversion": -2, "trust": 1}, {"delta": {"aversion": "down", "trust": "up"}}) == []
    assert kinds.delta_problems({**zero, "aversion": -1}, {"delta": {"aversion": "down", "trust": "up"}}) == ["trust +0 (cần up)"]
    assert kinds.delta_problems(zero, {"all_zero": True}) == []
    assert kinds.delta_problems({**zero, "affection": 1}, {"all_zero": True}) == [
        "chuyện thường ngày mà chỉ số vẫn đổi (affection +1)"
    ]


def test_memory_problems() -> None:
    expect = {"memory_any": ["Tô Châu", "giỗ"], "facts_any": ["dị ứng tôm"]}
    assert kinds.memory_problems("Lâm Vãn sắp về Tô Châu ăn giỗ", [("Lâm Vãn", "Lâm Vãn dị ứng tôm từ bé")], expect) == []
    bad = kinds.memory_problems(None, [], expect)
    assert len(bad) == 2 and "ký ức «»" in bad[0] and "điều đã biết (không có)" in bad[1]
    assert len(kinds.memory_problems("Hai người ăn tối", [("Lâm Vãn", "Lâm Vãn thích trà sữa")], expect)) == 2


# ---- summarize (F10) ------------------------------------------------------------------------------------


def test_summary_problems() -> None:
    groups = [["Tây Hồ"], ["vòng tay", "chiếc vòng"]]
    assert kinds.summary_problems("Họ hẹn xem pháo hoa ở Tây Hồ; anh mua chiếc vòng bạc.", groups, []) == []
    assert kinds.summary_problems("Họ hẹn đi chơi.", groups, ["Thượng Hải"]) == [
        "tóm tắt thiếu «Tây Hồ»",
        "tóm tắt thiếu «vòng tay / chiếc vòng»",
    ]
    assert kinds.summary_problems("Tây Hồ, vòng tay, Thượng Hải.", groups, ["Thượng Hải"]) == [
        "tóm tắt có «Thượng Hải» (không có trong story)"
    ]


# ---- suggest (F15) --------------------------------------------------------------------------------------

FIRST = [
    'Tôi khẽ kéo tay áo cậu ấy. "Tớ ngủ quên lâu lắm hả?"',
    'Tôi dụi mắt, cười trừ. "Sao cậu không gọi tớ dậy?"',
    'Tôi đứng dậy vươn vai. "Đi ăn lẩu cay đi, tớ đói rồi."',
]
SECOND = [
    'Tôi kéo chiếc áo khoác chặt hơn. "Áo của cậu ấm thật đấy."',
    'Tôi nhìn ra cửa sổ. "Trời tối rồi, mình về ký túc xá thôi."',
    'Tôi chống cằm nhìn cậu ấy. "Cậu đọc tới chương mấy rồi?"',
]


def test_suggestion_problems() -> None:
    kw = {"max_overlap": 0.6, "language": "vi", "names": ["Lạc Dương", "Lâm Vãn"]}
    assert kinds.suggestion_problems(FIRST, SECOND, **kw) == []
    same = kinds.suggestion_problems(FIRST, FIRST, **kw)
    assert len(same) >= 3 and all("gần giống lần trước" in p for p in same)
    two = kinds.suggestion_problems(FIRST[:2], SECOND, **kw)
    assert two == ["lần 1: 2 gợi ý (cần 3)"]
    english = kinds.suggestion_problems(FIRST, [*SECOND[:2], "I tug at your sleeve and ask what you are reading there."], **kw)
    assert any("Gợi ý khác:" in p and "ít dấu tiếng Việt" in p for p in english)


def test_verbatim_problem() -> None:
    assert kinds.verbatim_problem('"Đi thôi."', 'mở đầu\n\n"Đi thôi."\n\n(ghi chú)') is None
    assert "chỉ đạo" in (kinds.verbatim_problem("Đi thôi ((cười))", "Đi thôi") or "")
    assert "không nằm nguyên văn" in (kinds.verbatim_problem("Đi thôi.", "Đi thôi nào.") or "")


# ---- draft (F19) ----------------------------------------------------------------------------------------


def _card(**over: Any) -> Any:
    base = {
        "name": "Mai Chi",
        "role": "Thủ thư thư viện cũ",
        "gender": "female",
        "personality": "Trầm tính, tỉ mỉ, hay để ý những điều nhỏ nhặt của người khác.",
        "style_profile": "viet_hien_dai",
        "address_terms": {"self_term": "chị", "player_term": "em"},
        "greeting": "Chiều thứ bảy, nắng nghiêng qua ô cửa thư viện. [Thought: Lại là người đó.] Cô đặt cuốn thơ lên quầy, chờ {{user}} lên tiếng.",
    }
    return kinds.CharacterCard.model_validate({**base, **over})


def test_draft_problems() -> None:
    kw = {"required": ["name", "role", "personality", "greeting"], "forbidden_warnings": ["Model không đặt tên", "Chưa có"], "language": "vi"}
    assert kinds.draft_problems(_card(), ["Lời mở đầu có 1 dòng Thought (nên có 2)."], **kw) == []
    bad = kinds.draft_problems(_card(role="", id=7), ['Chưa có "Tự xưng"; hãy điền xưng hô.'], **kw)
    assert "card nháp đã có id (bị lưu)" in bad and "card nháp thiếu role" in bad
    assert any(p.startswith("cảnh báo: Chưa có") for p in bad)
    english = kinds.draft_problems(
        _card(greeting="The afternoon sun falls across the library desk where she waits for you, as she always does."), [], **kw
    )
    assert any("ít dấu tiếng Việt" in p for p in english)


# ---- dm_session (F13) -----------------------------------------------------------------------------------


def test_closing_sentence_and_repetition() -> None:
    assert kinds.closing_sentence("Ừ, tớ biết rồi. Đi ngủ sớm đi nhé 😴") == "đi ngủ sớm đi nhé"
    assert kinds.closing_sentence("[Thought: buồn ngủ] Mai gặp.") == "mai gặp"
    kw = {"max_same_ending": 2, "ending_words": 3, "max_same_tail": 3}
    same = [f"Câu {i} khác nhau. Đi ngủ sớm đi." for i in range(10)]
    problems = kinds.repetition_problems(same, **kw)
    assert problems == [
        "10/10 lượt kết bằng cùng một câu «đi ngủ sớm đi» (tối đa 2)",
        "10/10 lượt kết bằng cùng «… ngủ sớm đi» (tối đa 3)",
    ]
    tails = [f"Lượt {i}. Nhớ uống nước rồi ngủ sớm đi" + ("" if i % 2 else " nha") for i in range(8)]
    assert any("cùng «… ngủ sớm đi»" in p for p in kinds.repetition_problems(tails, **kw))
    varied = [
        "Ừ, tớ ăn rồi.", "Đừng run, cậu ôn kỹ rồi mà.", "Chương bốn.", "Học trưởng Chu à.", "Tuỳ cậu thôi.",
        "Rảnh. Mấy giờ?", "Cuốn nào, tớ mua cho.", "Có đèn pin không?", "Đang đọc sách.", "Hồi nhỏ cậu ngã xuống ao, nhớ không?",
    ]
    assert kinds.repetition_problems(varied, **kw) == []


# ---- app_ttft (F14) -------------------------------------------------------------------------------------


def test_ttft_problems() -> None:
    T = kinds.TurnTiming
    good = [T(1, 40.0, 0, False), T(2, 4.8, 0, False), T(3, 5.1, 6, True), T(4, 4.4, 6, False)]
    assert kinds.ttft_problems(good, max_ttft_s=6.0, after_shift=1) == []
    slow = [T(1, 40.0, 0, False), T(2, 4.8, 0, False), T(3, 31.0, 6, True), T(4, 4.4, 6, False)]
    assert kinds.ttft_problems(slow, max_ttft_s=6.0, after_shift=1) == ["lượt 3 (cửa sổ dịch): TTFT 31.00s > 6s"]
    no_shift = [T(1, 40.0, 0, False), T(2, 4.8, 0, False)]
    assert kinds.ttft_problems(no_shift, max_ttft_s=6.0, after_shift=1) == [
        "không gặp lượt cửa sổ dịch nào sau lượt đầu (kịch bản chưa đo được lượt dịch)"
    ]
    assert kinds.ttft_problems(good[:3], max_ttft_s=6.0, after_shift=1) == ["chưa đo đủ 1 lượt sau lượt cửa sổ dịch"]
    assert kinds.ttft_problems([T(1, 1.0, 0, False)], max_ttft_s=6.0, after_shift=0) == ["không có lượt nào sau lượt đầu để đo"]
    assert kinds.ttft_problems([T(1, 1.0, 0, False), T(2, None, 3, True)], max_ttft_s=6.0, after_shift=0) == [
        "lượt 2 (cửa sổ dịch): không đo được TTFT"
    ]


# ---- bakeoff, nested_eval (F36) ------------------------------------------------------------------------


def test_bakeoff_problems(tmp_path: Path) -> None:
    assert kinds.bakeoff_problems(1, None, "gemma4:12b") == ["bakeoff thoát mã 1"]
    assert kinds.bakeoff_problems(0, tmp_path, "gemma4:12b") == ["bakeoff không ghi speed.md"]
    head = "| Model | RAM nạp (GB) | Nạp lần đầu (s) | TTFT tb (s) | Tốc độ sinh tb (tok/s) | x | y |\n|---|---|---|---|---|---|---|\n"
    (tmp_path / "speed.md").write_text(head + "| gemma4:12b | 9.1 | 4.0 | 1.25 | 11.3 | 300.0 | 0/2 |\n", encoding="utf-8")
    assert kinds.bakeoff_problems(0, tmp_path, "gemma4:12b") == ["bakeoff không ghi raw.json có các câu của model"]
    runs = [{"case": "a", "text": "ok", "ttft_s": 1.2}, {"case": "b", "text": "ok", "ttft_s": 1.3}]
    (tmp_path / "raw.json").write_text(json.dumps({"models": {"gemma4:12b": {"runs": runs}}}), encoding="utf-8")
    assert kinds.bakeoff_problems(0, tmp_path, "gemma4:12b") == []
    assert kinds.bakeoff_problems(0, tmp_path, "qwen3:8b") == ["bảng không có dòng cho qwen3:8b"]
    (tmp_path / "speed.md").write_text(head + "| gemma4:12b | lỗi: hết RAM | | | | | |\n", encoding="utf-8")
    assert "báo lỗi" in kinds.bakeoff_problems(0, tmp_path, "gemma4:12b")[0]
    (tmp_path / "speed.md").write_text(head + "| gemma4:12b | 9.1 | 4.0 | - | - | - | 2/2 |\n", encoding="utf-8")
    assert "thiếu TTFT" in kinds.bakeoff_problems(0, tmp_path, "gemma4:12b")[0]


def _fake_bakeoff(monkeypatch: pytest.MonkeyPatch, *, fail_model: bool = False) -> None:
    class _Resp:
        def read(self) -> bytes:
            return b"{}"

    monkeypatch.setattr(bakeoff.urllib.request, "urlopen", lambda *a, **k: _Resp())

    def chat_safe(model: str, messages: list[dict[str, Any]], options: dict[str, Any]) -> dict[str, Any]:
        if fail_model:
            raise RuntimeError("model not found")
        return {"text": "Lạc Dương nhìn cô. [Thought: ngốc]", "ttft_s": 1.2, "total_s": 3.0, "out_tokens": 30,
                "tok_per_s": 11.0, "prompt_tokens": 300, "prompt_tok_per_s": 250.0}

    monkeypatch.setattr(bakeoff, "chat_safe", chat_safe)
    monkeypatch.setattr(bakeoff, "loaded_size_gb", lambda model: 9.1)
    monkeypatch.setattr(bakeoff, "unload", lambda model: None)


def test_run_bakeoff_writes_table(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _fake_bakeoff(monkeypatch)
    code, out, table = bakeoff.run_bakeoff(["gemma4:12b"], host="http://ollama", out_root=tmp_path, limit=2)
    assert code == 0 and out is not None and table[0].startswith("| Model |")
    assert kinds.bakeoff_problems(code, out, "gemma4:12b") == []
    assert len(json.loads((out / "raw.json").read_text(encoding="utf-8"))["models"]["gemma4:12b"]["runs"]) == 2
    assert "Đã ghi kết quả vào" not in capsys.readouterr().out  # chỉ main() in dòng này (verify.sh đọc dòng của run_eval)
    _fake_bakeoff(monkeypatch, fail_model=True)
    code, out, _ = bakeoff.run_bakeoff(["gemma4:12b"], host="http://ollama", out_root=tmp_path, limit=1)
    assert kinds.bakeoff_problems(code, out, "gemma4:12b") != []


def test_nested_problems(tmp_path: Path) -> None:
    assert kinds.nested_problems(2, None, ["a"]) == ["run_eval lồng thoát mã 2"]
    assert kinds.nested_problems(0, tmp_path, ["a"]) == ["run_eval lồng không ghi report.md / raw.json"]
    (tmp_path / "report.md").write_text("# Eval", encoding="utf-8")
    (tmp_path / "raw.json").write_text(json.dumps({"results": [{"id": "a", "error": None, "problems": ["x"]}]}), encoding="utf-8")
    assert kinds.nested_problems(0, tmp_path, ["a"]) == []  # lỗi máy của kịch bản con không tính
    assert kinds.nested_problems(0, tmp_path, ["a", "b"]) == ["báo cáo thiếu kịch bản b"]
    (tmp_path / "raw.json").write_text(json.dumps({"results": [{"id": "a", "error": "mất kết nối"}]}), encoding="utf-8")
    assert kinds.nested_problems(0, tmp_path, ["a"]) == ["a: lỗi sinh (mất kết nối)"]


# ---- đọc kịch bản ---------------------------------------------------------------------------------------


def test_new_scenarios_load_with_kinds() -> None:
    by_id = {s.id: s for s in run_eval.load_scenarios(run_eval.DEFAULT_SCENARIOS)}
    assert set(NEW_IDS) <= set(by_id)
    assert by_id["f09-cam-xuc"].kind == "extract" and len(by_id["f09-cam-xuc"].spec["cases"]) == 6
    assert by_id["f14-ttft"].spec["max_ttft_s"] == 6.0
    assert by_id["f07-thought-cuoi"].thought_style == "end"
    assert by_id["f36-chay-long"].spec["ids"] and not {by_id[i].kind for i in by_id["f36-chay-long"].spec["ids"]} & kinds.META_KINDS


def test_thought_style_and_dm_history_reach_the_prompt() -> None:
    by_id = {s.id: s for s in run_eval.load_scenarios(run_eval.DEFAULT_SCENARIOS, ["f07-thought-cuoi", "f12-dm-xung-ten"])}
    s = by_id["f07-thought-cuoi"]
    story, _, built = run_eval.build_scenario_prompt(s, run_eval.load_setup(s), "m", run_eval.PromptBudget())
    assert story.thought_style == "end" and "Kết thúc bằng đúng một dòng [Thought" in built.messages[-1].content
    s = by_id["f12-dm-xung-ten"]
    _, history, built = run_eval.build_scenario_prompt(s, run_eval.load_setup(s), "m", run_eval.PromptBudget())
    assert [m.mode for m in history].count("dm") == 4 and history[-1].mode == "story"
    body = "\n".join(m.content for m in built.messages)
    assert body.count("[Tin nhắn điện thoại]") == 4 + 1 and "Tần Dương. Ô của em" in body  # 4 lượt DM + dòng nhắc ở khối F


@pytest.mark.parametrize(
    ("body", "match"),
    [
        ("id: a\nkind: voice\n", "kind"),
        ("id: a\nkind: extract\ncases: []\n", "cases"),
        ("id: a\nkind: extract\ninput: x\ncases: []\n", "trường lạ"),
        (
            "id: a\nkind: extract\ncases:\n  - name: x\n    turn: [{role: user, content: hi}, {role: assistant, content: ok}]\n"
            "    expect: {delta: {trust: sideways}}\n",
            "giá trị thuộc",
        ),
        ("id: a\nkind: extract\ncases:\n  - name: x\n    turn: [{role: user, content: hi}]\n    expect: {all_zero: true}\n", "assistant"),
        ("id: a\nkind: summarize\nmessages: [{role: user, content: hi}]\n", "required_all"),
        ("id: a\nkind: app_ttft\nturns: [hi]\n", "max_ttft_s"),
        ("id: a\nkind: draft\nidea: x\nrequired_fields: [tuoi]\n", "required_fields"),
        ("id: a\ninput: x\nchecks: {forbidden_patterns: ['(']}\n", "regex"),
        ("id: a\ninput: x\nthought_style: giua\n", "thought_style"),
        ("id: a\ninput: x\nlore: [{title: t, content: c}]\n", "lore"),
    ],
)
def test_bad_new_scenarios_rejected(tmp_path: Path, body: str, match: str) -> None:
    (tmp_path / "bad.yaml").write_text(body, encoding="utf-8")
    with pytest.raises(run_eval.ScenarioError, match=match):
        run_eval.load_scenarios(tmp_path)


# ---- chạy trọn với Ollama giả ---------------------------------------------------------------------------

GOOD_STORY = (
    "Lạc Dương đặt cốc trà xuống, ngón tay gõ nhẹ lên mép bàn.\n\n"
    "[Thought: Cô ấy lại thức khuya rồi.]\n\n"
    '"Ừ." Anh kéo quyển vở lại gần. "Chỗ này làm lại từ dòng ba."\n\n'
    "[Thought: Giảng bao nhiêu lần cũng được.]\n\nAnh đợi cô viết tiếp."
)
GOOD_END = 'Lạc Dương kéo quyển vở lại gần. "Chỗ này làm lại từ dòng ba."\n\n[Thought: Giảng bao nhiêu lần cũng được. Miễn cô ấy ngồi đây.]'
LONG_APP = (
    "Lạc Dương gấp sách lại, nhìn ra sân trường đã lên đèn. " * 12
    + "\n\n[Thought: Cô ấy lại quên mang khăn.]\n\n"
    + '"Về thôi." Anh cầm túi sách của cô khoác lên vai. ' * 6
    + "\n\n[Thought: Mai lại gặp.]"
)
DM_GOOD = [
    "Ăn rồi. Mì tôm không no đâu.", "Cậu ôn kỹ rồi mà, đừng run.", "Chương năm.", "Học trưởng Chu à.",
    "Thích thì vào.", "Rảnh. Mấy giờ?", "Tên gì, tớ tìm trước.", "Có đèn pin không?", "Đang đọc sách.",
    "Hồi nhỏ cậu ngã xuống ao vịt, nhớ không?",
]


def _draft_json(good: bool) -> dict[str, Any]:
    greeting = (
        "Chiều thứ bảy, nắng nghiêng qua những giá sách gỗ cũ của thư viện phố Hàng Bài. Mai Chi ngồi sau quầy, "
        "lật từng trang sổ mượn đã ngả vàng.\n\n[Thought: Ba giờ rồi. Người đó sắp tới.]\n\n"
        "Chuông cửa khẽ reo. {{user}} bước vào, mái tóc còn vương mấy giọt mưa phùn. Cô đẩy cuốn thơ đã gói sẵn "
        "trong giấy báo sang phía trước, giọng nhỏ như sợ làm phiền cả căn phòng.\n\n"
        "\"Cuốn em hỏi tuần trước, chị để dành rồi. Bìa hơi cũ, em đọc nhẹ tay nhé.\"\n\n"
        "[Thought: Mong là cuốn này em thích. Mình đã đọc lại nó ba lần chỉ để chắc như vậy.]\n\n"
        "Cô cúi xuống ghi tên vào sổ, đầu bút dừng lại một nhịp trước khi viết."
    )
    if not good:
        greeting = "The afternoon sun falls across the old library. She waits for {{user}} to say something, as always."
    return {
        "name": "Mai Chi", "gender": "female", "style_profile": "viet_hien_dai",
        "role": "Thủ thư thư viện cũ" if good else "",
        "description": "Thủ thư ở thư viện cũ phố Hàng Bài.", "personality": "Trầm tính, tỉ mỉ, hay để ý người khác.",
        "appearance": "Tóc búi thấp, đeo kính.", "background": "Làm thủ thư năm năm.", "goals": "Giữ thư viện.",
        "secrets": "Thầm để ý {{user}}.", "speech_style": "Nói nhỏ, chậm.", "self_term": "chị", "player_term": "em",
        "nicknames": [], "others": "Với người lạ xưng tôi.", "scenario": "Thư viện cũ phố Hàng Bài.",
        "greeting": greeting, "example_dialogues": '{{char}}: "Em đọc nhẹ tay nhé."', "tags": ["hiện đại"],
    }


EXTRACT = {
    # dấu hiệu trong lượt -> (tone, delta tốt, delta xấu)
    "Học trưởng Chu nhắn rủ tớ cuối tuần": ("hurt", {"obsession": 2, "fear": 2, "trust": -1}, {"affection": 1}),
    "karaoke": ("hurt", {"trust": -3, "aversion": 2}, {"trust": 1}),
    "quên béng": ("hurt", {"affection": -1, "trust": -1, "aversion": 1}, {"affection": -1}),
    "thật lòng xin lỗi": ("warm", {"trust": 1, "aversion": -2}, {"affection": 2}),
    "Chào buổi sáng": ("everyday", {}, {"affection": 1}),
    "tích phân": ("everyday", {}, {"trust": 1}),
}


class FakeOllama:
    """Ollama giả cho mọi loại kịch bản: stream chat, chat_json (trích xuất, tóm tắt, gợi ý, viết nháp),
    /api/show + /api/generate (prefill raw, unload), /api/tags. `good=False` trả kết quả sai luật."""

    def __init__(self, good: bool = True) -> None:
        self.good = good
        self.paths: list[str] = []
        self.prefills = 0

    def _stream(self, text: str) -> httpx.Response:
        chunks = [text[i : i + 40] for i in range(0, len(text), 40)] or [""]
        lines = [json.dumps({"message": {"content": c}, "done": False}) for c in chunks]
        lines.append(json.dumps({"message": {"content": ""}, "done": True, "done_reason": "stop", "eval_count": 40,
                                 "eval_duration": 2_000_000_000, "prompt_eval_count": 400}))
        return httpx.Response(200, content=("\n".join(lines) + "\n").encode())

    def _json(self, data: dict[str, Any]) -> httpx.Response:
        return httpx.Response(200, json={"message": {"content": json.dumps(data, ensure_ascii=False)}, "done": True, "done_reason": "stop"})

    def _reply(self, last: str) -> str:
        g = self.good
        if "Xin chào" == last.strip():
            return "Chào"
        if "học trưởng Chu nhắn rủ tớ tối nay" in last:
            return GOOD_STORY if g else '"Tớ ghen đấy." ((Lạc Dương ghen nhưng không nói ra'
        if "đạo hàm riêng" in last:
            if "Kết thúc bằng đúng một dòng [Thought" in last:
                return GOOD_END if g else GOOD_STORY
            return GOOD_STORY if g else "[Thought: Một.]\n\n[Thought: Hai.]\n\nAnh im lặng."
        if "Anh Dương ơi" in last:
            return (
                'Tần Dương ngẩng lên. [Thought: Cô ấy nhớ tên mình từ tin nhắn tối qua.]\n\n"Ô của em đây."'
                if g else 'Tần Dương khựng lại. [Thought: Mình chưa hề nói tên với ai, sao cô ấy biết?]\n\n"Ô của em đây."'
            )
        if "quán chè bà Tư không" in last:
            return (
                'Lạc Dương gật đầu. [Thought: Cô ấy lại quên.]\n\n"Chè bưởi. Bà Tư hay cho thêm nước cốt dừa."'
                if g else '"Món gì cũng được." [Thought: Cô ấy còn giữ lá thư trong hộp bút.]'
            )
        for i, turn in enumerate(_dm_turns()):
            if turn in last:
                return DM_GOOD[i] if g else f"{DM_GOOD[i]} Đi ngủ sớm đi."
        if "không ngủ được" in last:  # 05-dm
            return "Còn. Sao thế?"
        return LONG_APP

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        self.paths.append(path)
        if path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "gemma4:12b"}, {"name": "gemma4:e4b"}]})
        body = json.loads(request.content) if request.content else {}
        if path == "/api/show":
            return httpx.Response(200, json={"renderer": "gemma4-large"})
        if path == "/api/generate":
            if body.get("raw"):
                self.prefills += 1
                return self._stream("x")
            return httpx.Response(200, json={"done": True})
        assert path == "/api/chat", path
        last = body["messages"][-1]["content"]
        if body.get("stream") is not False:
            return self._stream(self._reply(last))
        props = set((body.get("format") or {}).get("properties", {}))
        g = self.good
        if "relationship_delta" in props:
            tone, delta = "everyday", {}
            for key, (t, good_d, bad_d) in EXTRACT.items():
                if key in last:
                    tone, delta = (t, good_d) if g else ("warm" if t != "warm" else "hurt", bad_d)
            memory, facts = "", []
            if "Tô Châu" in last:
                memory = "Lâm Vãn sắp về Tô Châu ăn giỗ ông nội" if g else "Hai người nói chuyện"
                facts = [{"subject": "Lâm Vãn", "text": "Lâm Vãn dị ứng tôm từ bé"}] if g else []
            if "piano" in last:
                memory = "Lạc Dương kể học piano từ năm sáu tuổi" if g else ""
                facts = [{"subject": "Lạc Dương", "text": "Mẹ Lạc Dương dạy đàn ở Cung thiếu nhi"}] if g else []
            full = {k: delta.get(k, 0) for k in kinds.EMOTION_KEYS}
            return self._json({"reason": "r", "tone": tone, "relationship_delta": full, "location": "", "time": "",
                               "memory": {"text": memory, "importance": 3}, "facts": facts})
        if "relationship_delta" not in props and "location" in props:
            return self._json({"location": "", "time": "", "memory": {"text": "", "importance": 1}})
        if props == {"summary"}:
            text = ("Lâm Vãn rủ Lạc Dương xem pháo hoa ở Tây Hồ đêm giao thừa và anh hứa đi. Cô từ chối học trưởng Chu. "
                    "Lạc Dương lén mua chiếc vòng tay bạc khắc mặt trăng.") if g else "Hai người đi ăn mì bò ở căn tin."
            return self._json({"summary": text})
        if props == {"suggestions"}:
            second = "Các gợi ý đã đưa trước đó" in last
            if g:
                return self._json({"suggestions": SECOND if second else FIRST})
            # Xấu: lần 1 chỉ 2 gợi ý; "Gợi ý khác" gần như chép lại lần trước.
            return self._json({"suggestions": [f.replace("cậu", "cậu ấy") for f in FIRST] if second else FIRST[:2]})
        if "greeting" in props:
            return self._json(_draft_json(g))
        raise AssertionError(f"lời gọi JSON lạ: {props}")


def _dm_turns() -> list[str]:
    (s,) = run_eval.load_scenarios(run_eval.DEFAULT_SCENARIOS, ["f13-dm-10-luot"])
    return s.spec["turns"]


def _patch_app_client(monkeypatch: pytest.MonkeyPatch, transport: httpx.MockTransport) -> None:
    app_module = importlib.import_module("lyris.api.app")
    real = app_module.OllamaClient
    monkeypatch.setattr(app_module, "OllamaClient", lambda url, **kw: real(url, transport=transport))


async def _run(tmp_path: Path, fake: FakeOllama, ids: list[str], scenarios: Path | None = None) -> tuple[int, dict[str, Any]]:
    argv = ["--model", "gemma4:12b", "--no-judge", "--keep-loaded", "--ollama-url", "http://ollama"]
    if scenarios is not None:
        argv += ["--scenarios", str(scenarios)]
    for sid in ids:
        argv += ["--only", sid]
    info: dict[str, Any] = {}
    code = await run_eval.run(run_eval.parse_args(argv), transport=httpx.MockTransport(fake), results_dir=tmp_path, report=info)
    raw = json.loads((info["out"] / "raw.json").read_text(encoding="utf-8")) if "out" in info else {}
    return code, {r["id"]: r for r in raw.get("results", [])}


async def test_all_new_scenarios_pass_with_good_fake(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = FakeOllama(good=True)
    _patch_app_client(monkeypatch, httpx.MockTransport(fake))
    _fake_bakeoff(monkeypatch)
    code, results = await _run(tmp_path, fake, NEW_IDS)
    assert code == 0
    for sid in NEW_IDS:
        assert results[sid]["error"] is None, (sid, results[sid]["error"])
        assert results[sid]["problems"] == [], (sid, results[sid]["problems"], results[sid]["reply"][:500])
    out = capsys.readouterr().out
    # verify.sh đọc dòng "Đã ghi kết quả vào" đầu tiên: lượt lồng (f36-chay-long) và bakeoff không được in dòng đó.
    assert out.count("Đã ghi kết quả vào") == 1
    ttft = results["f14-ttft"]["details"]["timings"]
    assert ttft[0]["turn"] == 1 and any(t["shifted"] for t in ttft[1:]), ttft
    assert fake.prefills >= 2  # worker của app thật prefill raw giữa các lượt
    assert results["f36-chay-long"]["details"]["exit_code"] == 0
    assert results["f09-cam-xuc"]["kind"] == "extract" and len(results["f09-cam-xuc"]["details"]["cases"]) == 6


async def test_new_scenarios_catch_bad_answers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeOllama(good=False)
    _fake_bakeoff(monkeypatch, fail_model=True)
    ids = [i for i in NEW_IDS if i not in ("f14-ttft", "f36-chay-long")]
    code, results = await _run(tmp_path, fake, ids)
    assert code == 0
    for sid in ids:
        assert results[sid]["problems"], sid
    p = {sid: " | ".join(results[sid]["problems"]) for sid in ids}
    assert "lọt chỉ đạo" in p["f05-chi-dao"] and "nói thẳng trong lời thoại" in p["f05-chi-dao"]
    assert "Thought liền nhau" in p["f07-thought-long"] and "Thought không ở cuối" in p["f07-thought-cuoi"]
    for case in ("ghen", "noi-doi", "quen-hen", "xin-loi", "chao-buoi-sang", "nho-giang-bai"):
        assert f"{case}:" in p["f09-cam-xuc"], case
    assert "ký ức" in p["f10-ky-uc"] and "điều đã biết" in p["f10-ky-uc"]
    assert "tóm tắt thiếu «Tây Hồ»" in p["f10-tom-tat"]
    assert "có câu bị cấm" in p["f12-dm-xung-ten"]
    assert "lượt kết bằng cùng một câu" in p["f13-dm-10-luot"]
    assert "2 gợi ý (cần 3)" in p["f15-goi-y"] and "gần giống lần trước" in p["f15-goi-y"]
    assert "không có chi tiết nào" in p["f17-the-gioi"] and 'có cụm cấm "lá thư"' in p["f17-the-gioi"]
    assert "card nháp thiếu role" in p["f19-viet-nhap"] and "ít dấu tiếng Việt" in p["f19-viet-nhap"]
    assert p["f36-bakeoff"]


async def test_app_ttft_flags_slow_turns(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeOllama(good=True)
    _patch_app_client(monkeypatch, httpx.MockTransport(fake))
    scen = tmp_path / "scen"
    scen.mkdir()
    text = (run_eval.DEFAULT_SCENARIOS / "17-f14-ttft.yaml").read_text(encoding="utf-8")
    (scen / "a.yaml").write_text(text.replace("max_ttft_s: 6.0", "max_ttft_s: 0.000001"), encoding="utf-8")
    code, results = await _run(tmp_path / "out", fake, ["f14-ttft"], scenarios=scen)
    assert code == 0
    problems = results["f14-ttft"]["problems"]
    assert problems and all("TTFT" in p and "> 1e-06s" in p for p in problems), problems


async def test_nested_eval_refuses_meta_kinds(tmp_path: Path) -> None:
    scen = tmp_path / "scen"
    scen.mkdir()
    shutil.copy(run_eval.DEFAULT_SCENARIOS / "05-dm.yaml", scen / "05-dm.yaml")
    (scen / "n.yaml").write_text("id: n\nkind: nested_eval\nids: [n]\n", encoding="utf-8")
    code, results = await _run(tmp_path / "out", FakeOllama(), ["n"], scenarios=scen)
    assert code == 0
    assert "mã 2" in results["n"]["problems"][0]  # lượt lồng từ chối chạy lại nested_eval (không đệ quy)


async def test_run_eval_deadline_turns_remaining_scenarios_into_errors(tmp_path: Path) -> None:
    """Hết giờ chung (`--deadline-min`): kịch bản còn lại thành `error` của riêng nó, run_eval vẫn thoát 0 và ghi
    báo cáo (verify.sh coi rc != 0 là đỏ cho MỌI kịch bản)."""
    argv = ["--model", "gemma4:12b", "--no-judge", "--keep-loaded", "--ollama-url", "http://ollama", "--deadline-min", "0"]
    for sid in ("05-dm", "f10-tom-tat"):
        argv += ["--only", sid]
    info: dict[str, Any] = {}
    code = await run_eval.run(run_eval.parse_args(argv), transport=httpx.MockTransport(FakeOllama()), results_dir=tmp_path, report=info)
    assert code == 0
    raw = json.loads((info["out"] / "raw.json").read_text(encoding="utf-8"))
    errors = {r["id"]: r["error"] for r in raw["results"]}
    assert set(errors) == {"05-dm", "f10-tom-tat"} and all(e and "hết giờ" in e for e in errors.values()), errors


async def test_app_ttft_total_cap_is_an_error_of_that_scenario_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeOllama(good=True)
    _patch_app_client(monkeypatch, httpx.MockTransport(fake))
    scen = tmp_path / "scen"
    scen.mkdir()
    text = (run_eval.DEFAULT_SCENARIOS / "17-f14-ttft.yaml").read_text(encoding="utf-8")
    assert "max_total_s: 900" in text
    (scen / "a.yaml").write_text(text.replace("max_total_s: 900", "max_total_s: 0.05"), encoding="utf-8")
    shutil.copy(run_eval.DEFAULT_SCENARIOS / "05-dm.yaml", scen / "05-dm.yaml")
    code, results = await _run(tmp_path / "out", fake, ["f14-ttft", "05-dm"], scenarios=scen)
    assert code == 0
    assert "quá" in (results["f14-ttft"]["error"] or ""), results["f14-ttft"]
    assert results["05-dm"]["error"] is None


def test_f14_scenario_is_time_capped_and_checks_median() -> None:
    (s,) = run_eval.load_scenarios(run_eval.DEFAULT_SCENARIOS, ["f14-ttft"])
    assert s.spec["settle_timeout_s"] <= 180 and s.spec["max_total_s"] <= 900
    assert s.spec["max_median_ttft_s"] == 5.0 and s.spec["max_ttft_s"] == 6.0


def test_ttft_problems_median_matches_about_4_to_5_seconds() -> None:
    """Done when F14: "khoảng 4-5 giây, không lượt nào quá 6 giây": mọi lượt 5,9 giây phải đỏ."""
    T = kinds.TurnTiming
    slowish = [T(1, 40.0, 0, False), T(2, 5.9, 0, False), T(3, 5.8, 6, True), T(4, 5.7, 6, False)]
    assert kinds.ttft_problems(slowish, max_ttft_s=6.0, max_median_s=5.0, after_shift=1) == [
        "trung vị TTFT các lượt sau lượt đầu 5.80s > 5s"
    ]
    good = [T(1, 40.0, 0, False), T(2, 4.8, 0, False), T(3, 5.6, 6, True), T(4, 4.4, 6, False)]
    assert kinds.ttft_problems(good, max_ttft_s=6.0, max_median_s=5.0, after_shift=1) == []


async def test_app_ttft_is_measured_from_the_client_side(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """TTFT của F14 là từ lúc gửi POST tới sự kiện `delta` đầu tiên qua HTTP thật (uvicorn 8068/8069), không phải
    số OllamaClient tự đo (bỏ qua dựng prompt, tìm ký ức, chờ khoá)."""
    fake = FakeOllama(good=True)
    _patch_app_client(monkeypatch, httpx.MockTransport(fake))
    code, results = await _run(tmp_path, fake, ["f14-ttft"])
    assert code == 0 and results["f14-ttft"]["error"] is None, results["f14-ttft"]
    details = results["f14-ttft"]["details"]
    assert details["measured"] == "client: POST tới event delta đầu tiên"
    assert details["port"] in (8068, 8069)
    for t in details["timings"]:
        assert t["ttft_s"] is not None and t["ollama_ttft_s"] is not None
        assert t["ttft_s"] >= t["ollama_ttft_s"], t


def test_phrase_in_matches_whole_words_and_case_of_names() -> None:
    assert not checks.phrase_in("Hai người kể chuyện cho nhau nghe", "Chu")
    assert not checks.phrase_in("Anh chu đáo mua sẵn vé.", "Chu")
    assert checks.phrase_in("Cô từ chối học trưởng Chu.", "Chu")
    assert not checks.phrase_in("Cậu đi đàng hoàng vào.", "đàn")
    assert checks.phrase_in("Mẹ anh Dạy đàn ở Cung thiếu nhi", "dạy đàn")
    assert checks.phrase_in("Hẹn xem pháo\nhoa", "pháo hoa")
    assert kinds.summary_problems("Họ kể chuyện cho nhau nghe ở Tây Hồ.", [["Chu"], ["Tây Hồ"]], []) == ["tóm tắt thiếu «Chu»"]


def test_memory_problems_checks_who_the_fact_is_about() -> None:
    owners = {"persona": "Lâm Vãn", "character": "Lạc Dương"}
    expect = {"facts_any": ["dị ứng tôm"], "facts_owner": "persona"}
    assert kinds.memory_problems(None, [("Lâm Vãn", "Lâm Vãn dị ứng tôm từ bé")], expect, owners) == []
    assert kinds.memory_problems(None, [("", "Vãn dị ứng tôm từ nhỏ")], expect, owners) == []
    wrong = kinds.memory_problems(None, [("Lạc Dương", "Lạc Dương dị ứng tôm")], expect, owners)
    assert len(wrong) == 1 and "gán nhầm" in wrong[0], wrong
    (s,) = run_eval.load_scenarios(run_eval.DEFAULT_SCENARIOS, ["f10-ky-uc"])
    first, second = s.spec["cases"]
    assert not {"Tô Châu", "giỗ"} & set(first["expect"]["facts_any"]) and first["expect"]["facts_owner"] == "persona"
    assert second["expect"]["facts_owner"] == "character" and "đàn" not in second["expect"]["memory_any"]


F12_LEAKS = [
    "Sao cô ấy biết mình tên Dương nhỉ?",
    "Cô ấy biết tên mình từ lúc nào vậy?",
    "Mình đâu có nói tên cho cô ấy.",
    "Mình đã bao giờ nói tên với cô ấy đâu.",
    "Chưa ai ở đây biết tên mình cả.",
    "Ai đã nói tên mình cho cô ấy?",
    "Mình chưa hề nói tên với ai ở đây cả.",
    "Không ai biết tên mình ở phố này.",
]
F12_OK = [
    "Cô ấy nhớ tên mình từ tin nhắn tối qua.",
    "Hạ Vy. Tên đẹp thật.",
    "Tối qua cô ấy hỏi tên, mình đã nói rồi.",
    "Cô ấy biết tên mình rồi, gọi tự nhiên như người quen.",
    "Ai lại để quên ô giữa trời mưa thế này.",
    "Mai là thứ hai, tiệm mở sớm.",
]


def test_f12_patterns_catch_every_way_of_saying_the_name_was_never_given() -> None:
    (s,) = run_eval.load_scenarios(run_eval.DEFAULT_SCENARIOS, ["f12-dm-xung-ten"])
    patterns = s.checks["forbidden_patterns"]
    for line in F12_LEAKS:
        text = f'Tần Dương khựng lại.\n\n[Thought: {line}]\n\n"Ô của em đây."'
        assert checks.pattern_problems(text, patterns), line
    for line in F12_OK:
        text = f'Tần Dương ngẩng lên.\n\n[Thought: {line}]\n\n"Ô của em đây."'
        assert checks.pattern_problems(text, patterns) == [], line


def test_reworded_reminders_count_as_the_same_closing() -> None:
    kw = {"max_same_ending": 2, "ending_words": 3, "max_same_tail": 3, "max_same_reminder": 2,
          "reminders": [["ngủ sớm", "thức khuya", "đi ngủ"], ["giữ ấm", "mặc ấm"]]}
    replies = ["Ừ. Ngủ sớm đi nhé.", "Chương năm. Nhớ ngủ sớm nha.", "Mai thi rồi. Đừng thức khuya đấy.",
               "Đang đọc sách.", "Rảnh. Mấy giờ?"]
    problems = kinds.repetition_problems(replies, **kw)
    assert problems == ["3/5 lượt kết bằng cùng một lời dặn «ngủ sớm / thức khuya / đi ngủ» (tối đa 2)"], problems
    assert kinds.repetition_problems([*replies[:2], *replies[3:]], **kw) == []
    (s,) = run_eval.load_scenarios(run_eval.DEFAULT_SCENARIOS, ["f13-dm-10-luot"])
    assert s.spec["max_same_reminder"] == 2 and any("ngủ sớm" in g for g in s.spec["reminders"])


def test_dm_session_turns_only_check_empty_replies_by_default() -> None:
    """F13 chỉ chấm câu kết lặp: luật mặc định khác (`((`, dòng "<persona>:") không làm F13 đỏ."""
    assert kinds.dm_turn_problems("", {}, persona_name="Lâm Vãn", names=[]) == ["câu trả lời rỗng"]
    assert kinds.dm_turn_problems("Ừ ((cười)).\nLâm Vãn: ...", {}, persona_name="Lâm Vãn", names=[]) == []
    assert kinds.dm_turn_problems("Ừ ((cười)).", {"directive_leak": True}, persona_name="Lâm Vãn", names=[]) == [
        "lọt chỉ đạo (( ))"
    ]


def test_suggestion_overlap_uses_the_shorter_suggestion() -> None:
    short, long = "Đi ăn lẩu đi", "Đi ăn lẩu đi, tớ đói lắm rồi, mình đi luôn bây giờ nhé cậu"
    assert kinds.overlap(short, long) == 1.0  # gợi ý ngắn nằm trọn trong gợi ý dài
    kw = {"max_overlap": 0.6, "language": "vi", "names": ["Lạc Dương", "Lâm Vãn"]}
    first = [FIRST[0], FIRST[1], 'Tôi đứng dậy. "Đi ăn lẩu đi."']
    second = [SECOND[0], SECOND[1], 'Tôi đứng dậy. "Đi ăn lẩu đi, tớ đói lắm rồi, mình đi luôn bây giờ nhé cậu."']
    assert any("gần giống lần trước" in p for p in kinds.suggestion_problems(first, second, **kw))


def test_bakeoff_problems_reject_failed_runs_and_need_the_printed_table(tmp_path: Path) -> None:
    head = "| Model | RAM nạp (GB) | Nạp lần đầu (s) | TTFT tb (s) | Tốc độ sinh tb (tok/s) | x | y |\n|---|---|---|---|---|---|---|\n"
    row = "| gemma4:12b | 9.1 | 4.0 | 1.25 | 11.3 | 300.0 | 0/2 |\n"
    (tmp_path / "speed.md").write_text(head + row, encoding="utf-8")
    runs = [{"case": "a", "text": "ok", "ttft_s": 1.2}, {"case": "b", "text": "[LỖI: timed out]", "ttft_s": None}]
    (tmp_path / "raw.json").write_text(json.dumps({"models": {"gemma4:12b": {"runs": runs}}}), encoding="utf-8")
    printed = head + row
    problems = kinds.bakeoff_problems(0, tmp_path, "gemma4:12b", printed=printed)
    assert problems == ["bakeoff: câu b của gemma4:12b lỗi ([LỖI: timed out])"], problems
    runs[1] = {"case": "b", "text": "ok", "ttft_s": 1.0}
    (tmp_path / "raw.json").write_text(json.dumps({"models": {"gemma4:12b": {"runs": runs}}}), encoding="utf-8")
    assert kinds.bakeoff_problems(0, tmp_path, "gemma4:12b", printed=printed) == []
    assert kinds.bakeoff_problems(0, tmp_path, "gemma4:12b", printed="") == ["bakeoff.py không in bảng so sánh model"]


async def test_bakeoff_kind_runs_the_cli_entry_point(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Kịch bản f36-bakeoff gọi đúng `bakeoff.main()` (lệnh `harness/bakeoff.py`), không gọi tắt run_bakeoff."""
    _fake_bakeoff(monkeypatch)
    seen: list[list[str]] = []
    real_main = bakeoff.main

    def spy(argv: list[str] | None = None) -> int:
        seen.append(list(argv or []))
        return real_main(argv)

    monkeypatch.setattr(bakeoff, "main", spy)
    code, results = await _run(tmp_path, FakeOllama(), ["f36-bakeoff"])
    assert code == 0 and results["f36-bakeoff"]["problems"] == [] and results["f36-bakeoff"]["error"] is None
    assert seen and seen[0][:2] == ["--models", "gemma4:12b"] and "--limit" in seen[0]


def test_reply_prompt_has_the_acting_directive_like_chat_service() -> None:
    """Prompt của kịch bản giống ChatService với story mới: khối F có chỉ dẫn diễn xuất từ 6 chỉ số ban đầu."""
    from lyris.state.fold import initial_relationship
    from lyris.state.service import _relationship_directive

    (s,) = run_eval.load_scenarios(run_eval.DEFAULT_SCENARIOS, ["01-mo-dau"])
    setup = run_eval.load_setup(s)
    story, _, built = run_eval.build_scenario_prompt(s, setup, "m", run_eval.PromptBudget())
    want = _relationship_directive(initial_relationship(None, setup.card.extensions), setup.card, setup.persona, story)
    assert want and want in built.messages[-1].content


def test_num_ctx_is_pinned_to_8192(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LYRIS_NUM_CTX", "4096")
    assert run_eval.parse_args([]).num_ctx == 8192


def test_co_trang_narration_forbids_anh() -> None:
    (s,) = run_eval.load_scenarios(run_eval.DEFAULT_SCENARIOS, ["07-co-trang"])
    assert "anh" in s.checks["narration_forbidden"]
    assert "xưng hô trong dẫn truyện" in " ".join(checks.run_checks("Anh khẽ cười, thu kiếm.", {"narration_forbidden": s.checks["narration_forbidden"]}))


async def test_unexpected_error_in_a_kind_stays_in_that_scenario(monkeypatch: pytest.MonkeyPatch) -> None:
    async def boom(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("hỏng bất ngờ")

    monkeypatch.setitem(kinds.RUNNERS, "summarize", boom)
    out = await kinds.run_kind("summarize", {}, None, None, "story")  # type: ignore[arg-type]
    assert out.error == "RuntimeError: hỏng bất ngờ" and out.problems == []
