"""Các kiểm tra máy cho câu trả lời roleplay (dùng chung cho bakeoff.py và run_eval.py).

Chỉ dùng thư viện chuẩn: bakeoff.py chạy bằng python3 hệ thống, không có package nào cài thêm.
"""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from typing import Any

HAN = re.compile(r"[一-鿿]")

# Thẻ Thought như parser của app (backend/lyris/llm/thought.py) chấp nhận: không phân biệt hoa thường, cho phép dấu cách/tab.
_THOUGHT_OPEN = re.compile(r"\[[ \t]*thought[ \t]*:", re.I)
# Mỗi khối kết thúc ở `]` đầu tiên; chưa gặp `]` thì ở chỗ ngắt đoạn đầu tiên (dòng trống: `\n`,
# space/tab tuỳ ý, `\n`; không ăn chỗ ngắt đoạn, phần sau là truyện) hoặc hết văn bản, giống
# split_thought. Một `\n` đơn không kết thúc Thought.
_THOUGHT_BLOCK = re.compile(r"\[[ \t]*thought[ \t]*:.*?(?:\]|(?=\n[ \t]*\n)|\Z)", re.I | re.S)
_QUOTE_CHARS = '"“”'
_QUOTED = re.compile(r"[\"“][^\"”]*[\"”]")

# ---- so khớp theo từ (Unicode) -----------------------------------------------------------------

# Từ ghép tiếng Việt chứa một âm tiết trùng với từ xưng hô nhưng không phải xưng hô
# ("anh hùng", "tôi luyện", "người ta", "đệ tử"...). Khi đếm một từ xưng hô, các cụm này được
# che đi trước, trừ khi chính cụm đó nằm trong danh sách đang tìm.
VI_COMPOUNDS: tuple[str, ...] = (
    "anh hùng", "anh tuấn", "anh minh", "anh dũng", "anh hào", "anh linh", "anh khí", "anh tài",
    "anh thư", "anh đào", "anh vũ", "tinh anh",
    "tôi luyện", "tôi rèn", "tôi tớ", "đầy tớ",
    "người ta",
    "đệ tử", "đệ nhất", "đệ nhị", "đệ tam", "đệ trình", "huynh đệ",
)


def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def _phrase_pattern(phrases: Iterable[str]) -> re.Pattern[str] | None:
    """Regex khớp nguyên từ/cụm từ (biên `\\b` Unicode, không phân biệt hoa thường); cụm dài trước."""
    items = sorted({_nfc(p).strip() for p in phrases if p and p.strip()}, key=len, reverse=True)
    if not items:
        return None
    alts = "|".join(r"\s+".join(map(re.escape, p.split())) for p in items)
    return re.compile(r"(?<!\w)(?:" + alts + r")(?!\w)", re.I)


def _blank(match: re.Match[str]) -> str:
    return " " * len(match.group(0))


def remove_phrases(text: str, phrases: Iterable[str]) -> str:
    """Thay các từ/cụm (ví dụ tên riêng) bằng khoảng trắng, theo nguyên từ, không phân biệt hoa thường."""
    pat = _phrase_pattern(phrases)
    text = _nfc(text)
    return pat.sub(_blank, text) if pat else text


def find_words(text: str, words: Iterable[str]) -> list[str]:
    """Các lần xuất hiện (viết thường) của `words` trong `text`, theo nguyên từ.

    Bỏ qua các từ ghép trong VI_COMPOUNDS (trừ khi chính từ ghép đó được tìm).
    """
    wanted = [w for w in words if w and w.strip()]
    pat = _phrase_pattern(wanted)
    if pat is None:
        return []
    searched = {_nfc(w).strip().lower() for w in wanted}
    masked = remove_phrases(text, [c for c in VI_COMPOUNDS if c not in searched])
    return [re.sub(r"\s+", " ", m.group(0).lower()) for m in pat.finditer(masked)]


def narration_only(text: str) -> str:
    """Bỏ Thought và lời thoại trong ngoặc kép, chỉ giữ phần dẫn truyện."""
    text = _THOUGHT_BLOCK.sub("", text)
    return _QUOTED.sub("", text)


def auto_check(text: str, rules: dict) -> list[str]:
    """Các lỗi máy phát hiện được, theo luật của system prompt trong prompts.json."""
    problems = []
    if HAN.search(text):
        problems.append("chữ Hán")
    want = rules.get("thought_count")
    n_thoughts = count_thoughts(text)
    if want is not None and n_thoughts != want:
        problems.append(f"{n_thoughts} Thought")
    words = rules.get("narration_forbidden", [])
    if words:
        n = len(find_words(narration_only(text), words))
        if n:
            problems.append(f"xưng hô trong dẫn truyện x{n}")
    return problems


# ---- kiểm tra thêm cho run_eval.py -------------------------------------------------------------

_WORD = re.compile(r"\w+")


def _has_adjacent_thoughts(text: str) -> bool:
    """Một Thought kết thúc rồi ngay sau đó (chỉ cách khoảng trắng) là Thought khác."""
    blocks = list(_THOUGHT_BLOCK.finditer(text))
    return any(not text[a.end() : b.start()].strip() for a, b in zip(blocks, blocks[1:]))


def directive_leak(text: str) -> bool:
    """Câu trả lời có lọt `((` (chỉ đạo ẩn của người chơi bị in lại) hay không."""
    return "((" in text


def persona_line(text: str, persona_name: str) -> bool:
    """Có dòng nào bắt đầu bằng tên persona + `:` (model viết lời thay người chơi kiểu kịch bản).

    Bỏ qua khoảng trắng, dấu gạch đầu dòng và dấu nhấn Markdown (`**Lâm Vãn:**`, `- Lâm Vãn :`).
    """
    name = persona_name.strip()
    if not name:
        return False
    pat = re.compile(r"^[ \t>*_\-–—•]*" + re.escape(name) + r"[ \t*_]*[:：]", re.I | re.M)
    return pat.search(text) is not None


def strip_thoughts(text: str) -> str:
    """Bỏ mọi khối `[Thought: ...]` (kể cả khối chưa đóng, tới dòng trống hoặc hết văn bản), giữ phần hiển thị."""
    return _THOUGHT_BLOCK.sub("", text)


def word_count(text: str) -> int:
    """Số từ (âm tiết với tiếng Việt): các cụm chữ/số, không tính dấu câu và emoji."""
    return len(_WORD.findall(text))


def count_thoughts(text: str) -> int:
    """Số khối Thought theo đúng cách app tách (khối kết thúc ở `]` đầu tiên, dòng trống hoặc hết văn bản)."""
    return len(_THOUGHT_BLOCK.findall(text))


def thought_unclosed(text: str) -> bool:
    """Có Thought không đóng (lỗi của model): khối hết ở dòng trống hoặc hết văn bản mà không có `]`,
    hoặc bên trong lại có thẻ `[Thought:` khác (thẻ trước quên `]`, nên app nuốt phần truyện sau đó
    vào Thought)."""
    for match in _THOUGHT_BLOCK.finditer(text):
        body = match.group(0)
        if not body.endswith("]") or _THOUGHT_OPEN.search(body, 1):
            return True
    return False


def thought_not_at_end(text: str) -> bool:
    """Sau Thought cuối cùng vẫn còn chữ (kiểu "một đoạn ở cuối" đòi Thought đứng cuối lượt)."""
    blocks = list(_THOUGHT_BLOCK.finditer(text))
    return bool(blocks) and bool(text[blocks[-1].end():].strip())


def _thought_body(block: str) -> str:
    """Nội dung một khối Thought như split_thought: bỏ thẻ và `]`; khối không có `]` thì bỏ thêm một
    dấu ngoặc kép lẻ ở cuối (`"` lẻ số lần, `”` nhiều hơn `“`, hoặc `“`) cùng khoảng trắng quanh nó."""
    body = _THOUGHT_OPEN.sub("", block, count=1)
    if body.endswith("]"):
        return body[:-1].strip()
    body = body.strip()
    last = body[-1:]
    if last and last in _QUOTE_CHARS and (
        (last == '"' and body.count('"') % 2 == 1)
        or (last == "”" and body.count("”") > body.count("“"))
        or last == "“"
    ):
        body = body[:-1].rstrip()
    return body


def thought_bodies(text: str) -> list[str]:
    """Nội dung các khối Thought (đã bỏ thẻ `[Thought:` và `]`)."""
    return [_thought_body(m.group(0)) for m in _THOUGHT_BLOCK.finditer(text)]


def dialogue_parts(text: str, *, dm: bool = False) -> list[str]:
    """Lời thoại của nhân vật: các đoạn trong ngoặc kép ngoài Thought.

    Ở DM Mode cả tin nhắn là lời nhân vật nói, nên trả phần hiển thị (đã bỏ Thought) nếu không rỗng.
    """
    visible = strip_thoughts(text)
    if dm:
        return [visible.strip()] if visible.strip() else []
    return [m.group(0)[1:-1] for m in _QUOTED.finditer(visible) if m.group(0)[1:-1].strip()]


# ---- kiểm tra ngôn ngữ -------------------------------------------------------------------------

# Mọi chữ cái tiếng Việt có dấu (thường và hoa).
VI_DIACRITIC_CHARS = frozenset(
    "àáảãạăằắẳẵặâầấẩẫậđèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ"
    "ÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬĐÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴ"
)
# Chữ có dấu cũng gặp trong từ mượn tiếng Anh (café, rôle...): chỉ tính là tiếng Việt khi từ có
# chữ riêng của tiếng Việt, hoặc không nằm trong danh sách từ mượn.
_LATIN1_ACCENTS = frozenset("àáâãèéêìíòóôõùúýÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝ")
EN_LOANWORDS = frozenset({
    "café", "cafés", "fiancé", "fiancée", "cliché", "clichés", "déjà", "résumé", "rôle", "crêpe",
    "crêpes", "entrée", "protégé", "touché", "soirée", "décor", "naïve", "façade", "über", "à",
    "attaché", "sauté", "purée", "rosé", "risqué", "passé", "exposé", "doppelgänger", "jalapeño",
})
# Từ tiếng Anh rất thông dụng, không trùng với âm tiết tiếng Việt không dấu (bỏ "to", "do", "can",
# "me", "an", "in"... vì tiếng Việt cũng có).
EN_COMMON_WORDS = frozenset({
    "the", "and", "you", "your", "you're", "is", "are", "was", "were", "what", "this", "that",
    "with", "for", "of", "have", "has", "i'm", "i've", "i'll", "i'd", "don't", "doesn't", "didn't",
    "can't", "won't", "it's", "that's", "she", "they", "their", "but", "not", "just", "would",
    "could", "should", "there", "where", "why", "how", "when", "who", "about", "from", "will",
    "yes", "please", "thank", "thanks", "sorry", "really", "because",
})
_LETTER_WORD = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)*")
VI_MIN_DIACRITIC_RATIO = 0.15
_VI_RATIO_MIN_WORDS = 5  # câu quá ngắn ("Ừ.", "Ok") thì không xét tỉ lệ dấu
_EN_WORD_LIMIT = 3


def _expand_names(names: Iterable[str] | None) -> list[str]:
    """Tên đầy đủ kèm từng phần của tên (model hay gọi tắt "Dương", "Vãn")."""
    out: list[str] = []
    for name in names or []:
        name = _nfc(name).strip()
        if not name:
            continue
        out.append(name)
        out.extend(part for part in name.split() if len(part) >= 2)
    return out


def _language_words(text: str, names: Iterable[str] | None) -> list[str]:
    """Các từ (chỉ chữ cái) để xét ngôn ngữ: bỏ thẻ Thought, bỏ tên riêng."""
    text = _THOUGHT_OPEN.sub("[", _nfc(text))
    text = remove_phrases(text, _expand_names(names))
    return [w.replace("’", "'") for w in _LETTER_WORD.findall(text)]


def _is_vietnamese_word(word: str) -> bool:
    chars = set(word)
    if not chars & VI_DIACRITIC_CHARS:
        return False
    if chars & (VI_DIACRITIC_CHARS - _LATIN1_ACCENTS):
        return True
    return word.lower() not in EN_LOANWORDS


def _examples(words: list[str], limit: int = 5) -> str:
    seen: list[str] = []
    for w in words:
        if w not in seen:
            seen.append(w)
    return ", ".join(seen[:limit])


def language_problems(text: str, language: str, names: Iterable[str] | None = None) -> list[str]:
    """Lỗi ngôn ngữ của câu trả lời.

    vi: lẫn >= 3 từ tiếng Anh thông dụng, hoặc tỉ lệ từ có dấu tiếng Việt < 15% (câu >= 5 từ).
    en: còn từ có dấu tiếng Việt.
    Tên riêng trong `names` (và từng phần của tên) được bỏ trước khi xét.
    """
    words = _language_words(text, names)
    problems: list[str] = []
    if language == "vi":
        english = [w.lower() for w in words if w.lower() in EN_COMMON_WORDS]
        if len(english) >= _EN_WORD_LIMIT:
            problems.append(f"lẫn tiếng Anh x{len(english)} ({_examples(english)})")
        if len(words) >= _VI_RATIO_MIN_WORDS:
            marked = sum(1 for w in words if set(w) & VI_DIACRITIC_CHARS)
            ratio = marked / len(words)
            if ratio < VI_MIN_DIACRITIC_RATIO:
                problems.append(f"ít dấu tiếng Việt ({round(ratio * 100)}% số từ)")
    elif language == "en":
        vietnamese = [w for w in words if _is_vietnamese_word(w)]
        if vietnamese:
            problems.append(f"lẫn tiếng Việt x{len(vietnamese)} ({_examples(vietnamese)})")
    else:
        raise ValueError(f"Ngôn ngữ không hỗ trợ: {language!r} (chỉ có vi, en)")
    return problems


def dialogue_problems(
    text: str,
    *,
    forbidden: Iterable[str] = (),
    required_any: Iterable[str] = (),
    names: Iterable[str] | None = None,
    dm: bool = False,
) -> list[str]:
    """Kiểm tra xưng hô trong lời thoại và Thought.

    forbidden: không từ nào được xuất hiện trong lời thoại (trong ngoặc kép) và Thought.
    required_any: nếu có lời thoại thì lời thoại + Thought phải có ít nhất một từ trong danh sách.
    Tên riêng đầy đủ trong `names` được bỏ trước (ví dụ "Ngọc Anh" không tính là "anh").
    """
    full_names = [n for n in (names or []) if n and n.strip()]
    dialogue = [remove_phrases(d, full_names) for d in dialogue_parts(text, dm=dm)]
    thoughts = [remove_phrases(t, full_names) for t in thought_bodies(text)]
    spoken = "\n".join([*dialogue, *thoughts])
    problems: list[str] = []
    forbidden = [w for w in forbidden if w and w.strip()]
    if forbidden:
        hits = find_words(spoken, forbidden)
        if hits:
            problems.append(f"xưng hô sai trong lời thoại x{len(hits)} ({_examples(hits)})")
    required = [w for w in required_any if w and w.strip()]
    if required and dialogue and not find_words(spoken, required):
        problems.append(f"lời thoại không có xưng hô nào trong [{', '.join(required)}]")
    return problems


def run_checks(
    text: str,
    rules: dict[str, Any],
    *,
    persona_name: str | None = None,
    names: Iterable[str] | None = None,
    dm: bool = False,
) -> list[str]:
    """Mọi lỗi máy của một câu trả lời theo `checks` của kịch bản (rỗng = không lỗi).

    `rules` hỗ trợ:
      thought_count, narration_forbidden  như auto_check
      min_thoughts, max_thoughts          số dòng Thought cho phép (kiểu "lồng giữa truyện")
      no_adjacent_thoughts                báo lỗi khi hai Thought đứng liền nhau
      thought_at_end                      báo lỗi khi còn chữ sau Thought cuối (kiểu "một đoạn ở cuối")
      max_words, min_words                đếm trên phần hiển thị (đã bỏ Thought)
      forbidden_phrases                   list chuỗi không được xuất hiện (không phân biệt hoa thường)
      directive_leak                      mặc định true: báo lỗi nếu có `((`
      persona_line                        mặc định true: báo lỗi nếu có dòng "<persona>:"
      language                            "vi" | "en": xem language_problems (bỏ tên trong `names`)
      dialogue_forbidden                  list từ không được có trong lời thoại và Thought
      dialogue_required_any               list từ; có lời thoại thì phải dùng ít nhất một từ
    `names`: tên riêng (nhân vật, persona, tên thân mật) bỏ qua khi xét ngôn ngữ và xưng hô.
    `dm`: DM Mode, cả tin nhắn được coi là lời thoại.
    Luôn kiểm tra thêm câu trả lời rỗng và Thought chưa đóng.
    """
    if not text.strip():
        return ["câu trả lời rỗng"]
    names = [n for n in (names or []) if n and n.strip()]
    if persona_name and persona_name.strip() and persona_name not in names:
        names.append(persona_name)
    problems = auto_check(text, rules)
    if thought_unclosed(text):
        problems.append("Thought chưa đóng")
    n_thoughts = count_thoughts(text)
    min_thoughts = rules.get("min_thoughts")
    if min_thoughts is not None and n_thoughts < min_thoughts:
        problems.append(f"{n_thoughts} Thought (tối thiểu {min_thoughts})")
    max_thoughts = rules.get("max_thoughts")
    if max_thoughts is not None and n_thoughts > max_thoughts:
        problems.append(f"{n_thoughts} Thought (tối đa {max_thoughts})")
    if rules.get("no_adjacent_thoughts") and _has_adjacent_thoughts(text):
        problems.append("Thought liền nhau")
    if rules.get("thought_at_end") and thought_not_at_end(text):
        problems.append("Thought không ở cuối")
    visible_words = word_count(strip_thoughts(text))
    max_words = rules.get("max_words")
    if max_words is not None and visible_words > max_words:
        problems.append(f"dài {visible_words} từ (tối đa {max_words})")
    min_words = rules.get("min_words")
    if min_words is not None and visible_words < min_words:
        problems.append(f"ngắn {visible_words} từ (tối thiểu {min_words})")
    lowered = text.lower()
    for phrase in rules.get("forbidden_phrases", []) or []:
        if phrase and phrase.lower() in lowered:
            problems.append(f'có cụm cấm "{phrase}"')
    if rules.get("directive_leak", True) and directive_leak(text):
        problems.append("lọt chỉ đạo (( ))")
    if persona_name and rules.get("persona_line", True) and persona_line(text, persona_name):
        problems.append(f'có dòng "{persona_name}:"')
    language = rules.get("language")
    if language:
        problems.extend(language_problems(text, language, names))
    problems.extend(
        dialogue_problems(
            text,
            forbidden=rules.get("dialogue_forbidden") or [],
            required_any=rules.get("dialogue_required_any") or [],
            names=names,
            dm=dm,
        )
    )
    return problems
