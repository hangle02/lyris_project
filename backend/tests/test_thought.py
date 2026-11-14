"""Test bộ tách Thought: split_thought và ThoughtStreamParser phải cho cùng kết quả với mọi cách cắt chunk."""
from __future__ import annotations

import random
import zlib

import pytest

from lyris.llm.base import ParsedDelta
from lyris.llm.thought import ThoughtStreamParser, split_thought

STORY_END = """Tiếng bóng đập xuống mặt sân vang lên đều đặn rồi đột ngột dừng lại. Giữa đám nam sinh đang thở dốc, Lạc Dương là người duy nhất quay đầu về phía khán đài.

Mấy người bạn cùng đội huýt sáo trêu chọc. Anh chẳng buồn liếc lại, chỉ đưa tay nhận lấy chai nước, tiện thể kéo cô lùi vào chỗ có bóng râm.

"Nắng thế này mà chạy ra đây làm gì? Lần sau cứ ngồi trong lớp đợi tớ."

[Thought: Cả sân chỉ có mình Vãn Vãn mang nước đến cho tớ. Cảm giác này... không tệ chút nào.]"""

STORY_START = """[Thought: Biết ngay cô ngốc này sẽ hoảng trước kỳ thi. May mà đã chuẩn bị sẵn.]

Thư viện buổi chiều yên ắng đến mức nghe rõ cả tiếng quạt trần quay chậm. Lạc Dương không ngẩng đầu, nhưng tay trái đã lặng lẽ kéo quyển giáo trình cao số trước mặt sang giữa bàn.

"Tớ soạn từ tuần trước rồi. Mỗi tối làm năm bài, chỗ nào không hiểu thì hỏi."
"""

STORY_MIDDLE = """Chiếc bút trong tay Lạc Dương khựng lại giữa chừng, để lại một vệt mực đen nhỏ trên trang vở.

"Học trưởng nào?"

[Thought: Không được nói "đừng đi". Nhưng cũng không muốn cậu ấy đi chút nào.]


Anh nói xong liền quay mặt ra cửa sổ. Chỉ có vành tai hơi đỏ lên là phản bội anh."""

STORY_LOWER_SPACED = """Một chiếc ô màu xanh đậm bất chợt mở ra ngay bên cạnh cô. Anh nghiêng hẳn chiếc ô về phía cô.

"Đi thôi. Sáng nay dự báo đã nói chiều có mưa."

[ thought :   Lần nào cũng quên mang ô. Thôi thì cứ để tớ nhớ thay cậu vậy.  ]"""

STORY_UPPER = """Anh nhận lấy hộp cơm bằng cả hai tay.
[THOUGHT: Ngón tay cô ấy có vết bỏng nhỏ.]"""

STORY_TWO_THOUGHTS = """[Thought: Sợ nhất là có một ngày cậu ấy không bám theo nữa.]

Lạc Dương đứng ở cổng trường, hai tay đút túi áo khoác.

"Đi thôi, Vãn Vãn."

[Thought:Quầng mắt thâm thế kia rồi. Lại không biết tự chăm sóc mình.]"""

STORY_UNCLOSED = """Ánh đèn vàng nhạt của dãy hành lang ký túc xá đổ dài lên khuôn mặt góc cạnh của Lạc Dương.

"Cậu nói chỉ là 'hơi thích' thôi sao?"

[Thought: Hơi thích thôi à? Vậy thì vẫn còn kịp"""

STORY_BRACKETS = """[cười] Lạc Dương nhìn tờ giấy ghi [chú thích] trong tay cô, rồi nhìn dòng chữ [Thứ Hai] bị gạch đi.

"Cậu lại viết linh tinh gì vào lịch học của tớ thế?" [Th... không, anh không nói tiếp.

[Thought: Thứ duy nhất tớ muốn nhận là thư của cậu.] [ the end ] [thoughts] [Thought]"""

STORY_NO_THOUGHT = """Trăng đêm nay rất tròn. Lạc Dương tựa vào lan can ký túc xá, điện thoại áp bên tai.

"Ừ, tớ vẫn đang nghe đây."
"""

DM_SHORT = "Có. 8 giờ tớ đến trước cửa ký túc xá. \n\nĐừng có trễ nhé."
DM_TINY = "ngủ đi"
DM_EMOJI = "  chưa ngủ. sao thế 🥺  \n"

STORY_BLANKS = "  \n\nĐoạn một.\n \n\t\n\n Đoạn hai.\n\n\n\n[Thought: a  \n b ]\n\n\n  \n"

STORY_DOUBLE_BRACKET = "Anh cười [[Thought: lại thế]] rồi quay đi. [ [ thought: x"

# gemma4:12b quên `]`: Thought hết ở dòng trống, phần sau vẫn là truyện.
GEMMA_UNCLOSED = (
    "Hắn cười.\n\n"
    '[Thought: Người đẹp nào? Tôi chỉ đang trêu cậu thôi, Đậu Đinh."\n\n'
    "Cố Hoài Dã vươn tay.\n\n"
    '"Sao?"'
)

UNCLOSED_THEN_NARRATION = "Mở đầu.\n[Thought: Cô ấy giận rồi \t\n \t\nAnh bước tới.\n\n[Thought: Lần này đóng.] Hết."
UNCLOSED_CURLY_END = "Anh im lặng. [Thought: Cô ấy bảo “đợi đã” rồi đi mất”  "
UNCLOSED_MATCHED_QUOTE = 'Anh gật đầu. [Thought: Cô ấy nói "đi thôi"\n\nAnh đi theo.'
UNCLOSED_SINGLE_NEWLINE = "Anh nhìn. [Thought: Dòng một.\nDòng hai.\n  \tDòng ba “\n\n\nCô quay lại."
CLOSED_MULTILINE = 'Anh cười. [Thought: Dòng một.\nDòng hai."] Hết.\n\nSau.'
BLANK_LINE_BEFORE_BRACKET = "Anh cười. [Thought: Đoạn một.\n\nĐoạn hai.] Hết."

FIXTURES: list[str] = [
    STORY_END,
    STORY_START,
    STORY_MIDDLE,
    STORY_LOWER_SPACED,
    STORY_UPPER,
    STORY_TWO_THOUGHTS,
    STORY_UNCLOSED,
    STORY_BRACKETS,
    STORY_NO_THOUGHT,
    DM_SHORT,
    DM_TINY,
    DM_EMOJI,
    STORY_BLANKS,
    STORY_DOUBLE_BRACKET,
    "",
    "   ",
    "[",
    "[Thought:",
    "[Thought: ]",
    "[Tho",
    "Kết thúc bằng [",
    "Kết thúc bằng [ Thoug",
    GEMMA_UNCLOSED,
    UNCLOSED_THEN_NARRATION,
    UNCLOSED_CURLY_END,
    UNCLOSED_MATCHED_QUOTE,
    UNCLOSED_SINGLE_NEWLINE,
    CLOSED_MULTILINE,
    BLANK_LINE_BEFORE_BRACKET,
    '[Thought: "',
    '[Thought: a "\n \n"b',
    '[Thought: x" "\n\ny',
    "[Thought:\n\nchữ]",
    '[Thought: a"] [Thought: b"',
]


def run_parser(chunks: list[str]) -> tuple[str, str, list[ParsedDelta]]:
    parser = ThoughtStreamParser()
    deltas: list[ParsedDelta] = []
    for chunk in chunks:
        deltas.extend(parser.feed(chunk))
    deltas.extend(parser.flush())
    text = "".join(d.text for d in deltas if d.kind == "text")
    thought = "".join(d.text for d in deltas if d.kind == "thought")
    return text, thought, deltas


def expected(raw: str) -> tuple[str, str]:
    visible, thought = split_thought(raw)
    return visible, thought or ""


# ---- split_thought: các trường hợp cụ thể -----------------------------------------------------


def test_tag_at_end() -> None:
    visible, thought = split_thought(STORY_END)
    assert thought == "Cả sân chỉ có mình Vãn Vãn mang nước đến cho tớ. Cảm giác này... không tệ chút nào."
    assert visible.endswith('"Nắng thế này mà chạy ra đây làm gì? Lần sau cứ ngồi trong lớp đợi tớ."')
    assert "Thought" not in visible


def test_tag_at_start() -> None:
    visible, thought = split_thought(STORY_START)
    assert thought == "Biết ngay cô ngốc này sẽ hoảng trước kỳ thi. May mà đã chuẩn bị sẵn."
    assert visible.startswith("Thư viện buổi chiều")
    assert visible.endswith('thì hỏi."')


def test_tag_in_middle_collapses_blank_lines() -> None:
    visible, thought = split_thought(STORY_MIDDLE)
    assert thought == 'Không được nói "đừng đi". Nhưng cũng không muốn cậu ấy đi chút nào.'
    assert '"Học trưởng nào?"\n\nAnh nói xong' in visible
    assert "\n\n\n" not in visible


def test_lowercase_and_spaced_variants() -> None:
    visible, thought = split_thought(STORY_LOWER_SPACED)
    assert thought == "Lần nào cũng quên mang ô. Thôi thì cứ để tớ nhớ thay cậu vậy."
    assert visible.endswith('chiều có mưa."')
    _, thought_upper = split_thought(STORY_UPPER)
    assert thought_upper == "Ngón tay cô ấy có vết bỏng nhỏ."


def test_two_thoughts_joined_by_newline() -> None:
    visible, thought = split_thought(STORY_TWO_THOUGHTS)
    assert thought == (
        "Sợ nhất là có một ngày cậu ấy không bám theo nữa.\n"
        "Quầng mắt thâm thế kia rồi. Lại không biết tự chăm sóc mình."
    )
    assert visible == 'Lạc Dương đứng ở cổng trường, hai tay đút túi áo khoác.\n\n"Đi thôi, Vãn Vãn."'


def test_unclosed_thought_takes_rest() -> None:
    visible, thought = split_thought(STORY_UNCLOSED)
    assert thought == "Hơi thích thôi à? Vậy thì vẫn còn kịp"
    assert visible.endswith('"Cậu nói chỉ là \'hơi thích\' thôi sao?"')


def test_brackets_in_text_are_not_thoughts() -> None:
    visible, thought = split_thought(STORY_BRACKETS)
    assert thought == "Thứ duy nhất tớ muốn nhận là thư của cậu."
    assert visible.startswith("[cười] Lạc Dương")
    assert "[chú thích]" in visible and "[Thứ Hai]" in visible and "[Th..." in visible
    assert visible.endswith("[ the end ] [thoughts] [Thought]")


def test_no_thought_and_dm() -> None:
    assert split_thought(STORY_NO_THOUGHT) == (STORY_NO_THOUGHT.strip(), None)
    assert split_thought(DM_SHORT) == ("Có. 8 giờ tớ đến trước cửa ký túc xá. \n\nĐừng có trễ nhé.", None)
    assert split_thought(DM_EMOJI) == ("chưa ngủ. sao thế 🥺", None)


def test_whitespace_normalisation() -> None:
    visible, thought = split_thought(STORY_BLANKS)
    assert visible == "Đoạn một.\n\n Đoạn hai."
    assert thought == "a  \n b"


def test_double_bracket_and_empty_thought() -> None:
    visible, thought = split_thought(STORY_DOUBLE_BRACKET)
    assert visible == "Anh cười [] rồi quay đi. ["
    assert thought == "lại thế\nx"
    assert split_thought("[Thought: ]") == ("", None)
    assert split_thought("[Thought:") == ("", None)
    assert split_thought("[Tho") == ("[Tho", None)


def test_closed_thoughts_keep_quotes_and_blank_lines_inside() -> None:
    # Có `]` trước dòng trống: Thought chạy tới `]` như cũ, giữ cả dấu ngoặc kép cuối.
    visible, thought = split_thought(CLOSED_MULTILINE)
    assert visible == "Anh cười.  Hết.\n\nSau."
    assert thought == 'Dòng một.\nDòng hai."'
    assert split_thought('[Thought: Cô ấy nói "đi".]') == ("", 'Cô ấy nói "đi".')
    assert split_thought('[Thought: a"] [Thought: b"') == ("", 'a"\nb')
    # Dòng trống tới trước `]`: Thought hết ở dòng trống, phần sau (kể cả `]`) là chữ hiển thị.
    assert split_thought(BLANK_LINE_BEFORE_BRACKET) == ("Anh cười. \n\nĐoạn hai.] Hết.", "Đoạn một.")


def test_gemma_unclosed_thought_ends_at_blank_line() -> None:
    visible, thought = split_thought(GEMMA_UNCLOSED)
    assert thought == "Người đẹp nào? Tôi chỉ đang trêu cậu thôi, Đậu Đinh."
    assert visible == 'Hắn cười.\n\nCố Hoài Dã vươn tay.\n\n"Sao?"'


def test_unclosed_then_blank_line_then_narration() -> None:
    visible, thought = split_thought(UNCLOSED_THEN_NARRATION)
    assert thought == "Cô ấy giận rồi\nLần này đóng."
    assert visible == "Mở đầu.\n\nAnh bước tới.\n\n Hết."


def test_unclosed_at_end_strips_one_unmatched_quote() -> None:
    assert split_thought('Anh cười. [Thought: Ngốc thật."  ') == ("Anh cười.", "Ngốc thật.")
    assert split_thought("[Thought: Ngốc thật ” ") == ("", "Ngốc thật")
    assert split_thought("[Thought: Ngốc thật “") == ("", "Ngốc thật")
    # Chỉ bỏ một dấu.
    assert split_thought('[Thought: a "" "\n\nb') == ("b", 'a ""')
    assert split_thought('[Thought: a ""\n\nb') == ("b", 'a ""')  # số chẵn: đã khớp, giữ
    assert split_thought('[Thought: "') == ("", None)
    # Dấu ngoặc kép đã khớp thì giữ.
    assert split_thought(UNCLOSED_MATCHED_QUOTE) == ("Anh gật đầu. \n\nAnh đi theo.", 'Cô ấy nói "đi thôi"')
    assert split_thought(UNCLOSED_CURLY_END) == ("Anh im lặng.", "Cô ấy bảo “đợi đã” rồi đi mất")
    assert split_thought("[Thought: bảo “đợi”") == ("", "bảo “đợi”")


def test_single_newline_inside_thought_is_kept() -> None:
    visible, thought = split_thought(UNCLOSED_SINGLE_NEWLINE)
    assert thought == "Dòng một.\nDòng hai.\n  \tDòng ba"
    assert visible == "Anh nhìn. \n\nCô quay lại."


def test_blank_line_right_after_tag_drops_empty_thought() -> None:
    assert split_thought("[Thought:\n\nchữ]") == ("chữ]", None)


# ---- parser stream: giữ/nhả đúng lúc ------------------------------------------------------------


def test_parser_holds_tag_prefix_and_releases_plain_bracket() -> None:
    parser = ThoughtStreamParser()
    assert parser.feed("Anh cười ") == [ParsedDelta("text", "Anh cười")]
    assert parser.feed("[") == []  # có thể là thẻ: giữ lại
    assert parser.feed("c") == [ParsedDelta("text", " [c")]  # chắc chắn không phải thẻ: nhả ngay
    assert parser.feed("ười] nhẹ. [ Tho") == [ParsedDelta("text", "ười] nhẹ.")]
    assert parser.feed("ught :  Ngốc") == [ParsedDelta("thought", "Ngốc")]
    assert parser.feed(" thật] xong") == [ParsedDelta("thought", " thật"), ParsedDelta("text", "  xong")]
    assert parser.flush() == []


def test_parser_never_emits_tag_prefix_as_text() -> None:
    raw = "Mở đầu. [Thought: bí mật] Kết."
    for i in range(1, len(raw)):
        parser = ThoughtStreamParser()
        first = parser.feed(raw[:i])
        for d in first:
            if d.kind == "text":
                assert "[" not in d.text, (i, first)
                assert "bí mật" not in d.text


def test_parser_flush_releases_incomplete_prefix_as_text() -> None:
    parser = ThoughtStreamParser()
    assert parser.feed("Kết thúc bằng [ Thoug") == [ParsedDelta("text", "Kết thúc bằng")]
    assert parser.flush() == [ParsedDelta("text", " [ Thoug")]


def test_parser_is_reusable_after_flush() -> None:
    parser = ThoughtStreamParser()
    parser.feed("[Thought: một")
    parser.flush()
    deltas = parser.feed("Mới [Thought: hai]") + parser.flush()
    assert deltas == [ParsedDelta("text", "Mới"), ParsedDelta("thought", "hai")]


def test_parser_holds_trailing_quote_and_possible_blank_line() -> None:
    parser = ThoughtStreamParser()
    assert parser.feed('[Thought: Đậu Đinh."') == [ParsedDelta("thought", "Đậu Đinh.")]
    assert parser.feed("\n ") == []
    assert parser.feed("\nAnh") == [ParsedDelta("text", "Anh")]
    assert parser.flush() == []
    # Dấu ngoặc kép giữ lại được nhả khi Thought còn tiếp hoặc đóng bằng `]`.
    parser = ThoughtStreamParser()
    assert parser.feed('[Thought: a "') == [ParsedDelta("thought", "a")]
    assert parser.feed("b") == [ParsedDelta("thought", ' "b')]
    assert parser.feed('"') == [ParsedDelta("thought", '"')]
    assert parser.feed(' c "') == [ParsedDelta("thought", " c")]
    assert parser.feed("] x") == [ParsedDelta("thought", ' "'), ParsedDelta("text", "x")]


def test_gemma_example_streams_like_split() -> None:
    want = expected(GEMMA_UNCLOSED)
    for i in range(len(GEMMA_UNCLOSED) + 1):
        for j in range(i, len(GEMMA_UNCLOSED) + 1):
            chunks = [GEMMA_UNCLOSED[:i], GEMMA_UNCLOSED[i:j], GEMMA_UNCLOSED[j:]]
            assert run_parser(chunks)[:2] == want, (i, j)


def test_streaming_thought_appears_before_close() -> None:
    parser = ThoughtStreamParser()
    deltas = parser.feed("Văn.\n\n[Thought: Cô ấy")
    assert deltas == [ParsedDelta("text", "Văn."), ParsedDelta("thought", "Cô ấy")]


# ---- tính chất: mọi cách cắt chunk cho cùng kết quả -------------------------------------------


@pytest.mark.parametrize("raw", FIXTURES, ids=range(len(FIXTURES)))
def test_whole_feed_matches_split(raw: str) -> None:
    text, thought, _ = run_parser([raw])
    assert (text, thought) == expected(raw)


@pytest.mark.parametrize("raw", FIXTURES, ids=range(len(FIXTURES)))
def test_every_two_way_split_matches(raw: str) -> None:
    want = expected(raw)
    for i in range(len(raw) + 1):
        got = run_parser([raw[:i], raw[i:]])[:2]
        assert got == want, f"cắt tại {i}: {raw[:i]!r} | {raw[i:]!r}"


@pytest.mark.parametrize("raw", FIXTURES, ids=range(len(FIXTURES)))
def test_random_chunkings_match(raw: str) -> None:
    want = expected(raw)
    rng = random.Random(zlib.crc32(raw.encode()))
    for _ in range(150):
        chunks: list[str] = []
        pos = 0
        while pos < len(raw):
            size = rng.randint(1, 12)
            chunks.append(raw[pos : pos + size])
            pos += size
        text, thought, deltas = run_parser(chunks)
        assert (text, thought) == want, chunks
        assert all(d.text for d in deltas), "không được có delta rỗng"


def test_single_char_chunks_all_fixtures() -> None:
    for raw in FIXTURES:
        assert run_parser(list(raw))[:2] == expected(raw), raw


def test_random_generated_texts() -> None:
    """Văn bản ngẫu nhiên ghép từ các mảnh dễ gây nhầm lẫn."""
    pieces = [
        "Anh", " ", "\n", "\n\n", "\n \n\n", "\t", "[", "]", "[Thought:", "[ thought :", "[THOUGHT :",
        "[Thou", "[cười]", "Vãn Vãn", '"Đi thôi."', "...", "tớ", "[[", "]]", ":", "thought",
        '"', "“", "”", '."', "\n \t\n", " \n", "\n\t",
    ]
    rng = random.Random(1234)
    for _ in range(400):
        raw = "".join(rng.choice(pieces) for _ in range(rng.randint(0, 25)))
        want = expected(raw)
        assert run_parser([raw])[:2] == want, raw
        assert run_parser(list(raw))[:2] == want, raw
        cut = rng.randint(0, len(raw))
        assert run_parser([raw[:cut], raw[cut:]])[:2] == want, (raw, cut)
