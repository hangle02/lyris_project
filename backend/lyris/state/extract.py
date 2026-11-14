"""Trích xuất state của một lượt bằng model chat (docs/phase3.md §5).

Một lời gọi structured output (`chat_json`) đọc lượt vừa xong (tin của người chơi + câu trả lời của
nhân vật, có Thought) và trả: một câu `reason` (model tự nghĩ trước khi chấm điểm, bị bỏ khi kiểm tra),
thay đổi 6 chỉ số cảm xúc, cảnh, một ký ức, các fact mới.
Kết quả luôn được kiểm tra lại ở đây (kẹp số, giới hạn số chỉ số đổi theo `pick_changes`, bỏ trùng...) trước
khi tới job worker.

Cảm xúc tăng giảm theo tình huống (docs/phase3.md §10.5): prompt nói rõ điều gì làm từng chỉ số tăng và
giảm, kèm ví dụ tương phản (ghen, nói dối, bị đẩy ra, xin lỗi, chuyện thường ngày = 0), và dặn chấm theo
tính cách + Thought của nhân vật.

Phase 3b: gợi ý trả lời không còn nằm ở đây (chỉ sinh khi người chơi bấm "Nhận gợi ý", xem
`lyris/state/suggest.py`). Lời mở đầu (lượt 0) cũng được trích xuất, nhưng chỉ cảnh và ký ức
(`OPENING_SCHEMA`): chưa có tương tác nên không có thay đổi cảm xúc hay fact.

Schema không dùng `maxLength`: grammar của Ollama làm hỏng escape và xuống dòng khi có nó.
"""
from __future__ import annotations

import math
import re
import unicodedata
from collections.abc import Sequence
from typing import Any

from lyris.models import (
    EMOTION_KEYS,
    MAX_DELTA,
    CharacterCard,
    ChatTurn,
    ExtractionResult,
    FactDraft,
    Gender,
    Message,
    Mode,
    Persona,
    RelationshipDelta,
    RelationshipValues,
    SceneState,
    Story,
)

# JSON gọn một dòng + reason một câu: đo 124-167 token output (JSON thụt lề cũ: ~235). 500 vẫn dư gấp 2-3 lần, kể cả
# khi model lỡ thụt lề hay ghi đủ 3 fact; chỉ chặn sớm lúc model viết lan man (docs/phase3.md §10.7).
NUM_PREDICT = 500
TEMPERATURE = 0.3
MAX_FACTS = 3
MAX_CHANGED_EMOTIONS = 2  # lượt ấm lòng: giữ tối đa 2 chỉ số thay đổi (lớn nhất theo trị tuyệt đối)
MAX_CHANGED_EMOTIONS_MIXED = 3  # lượt tổn thương hoặc lẫn lộn (ghen: chiếm hữu tăng, lo sợ tăng, tin cậy giảm)
_MAX_PERSONALITY_CHARS = 400
_MAX_SECRET_CHARS = 200
MAX_KNOWN_FACTS_IN_PROMPT = 12
_MAX_REPLY_CHARS = 6000
_MAX_USER_CHARS = 3000
_MAX_SUMMARY_CHARS = 1500

_DELTA_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {k: {"type": "integer", "minimum": -MAX_DELTA, "maximum": MAX_DELTA} for k in EMOTION_KEYS},
    "required": list(EMOTION_KEYS),
}

_MEMORY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "text": {"type": "string"},
        "importance": {"type": "integer", "minimum": 1, "maximum": 5},
    },
    "required": ["text", "importance"],
}

# Lượt này với nhân vật là gì (docs/phase3.md §10.5): chọn một nhãn trước khi chấm số. "everyday" = mọi chỉ số 0
# (chống trôi dần lên); "warm"/"hurt" chỉ giữ thay đổi đúng chiều đó (bỏ nhiễu ngược chiều); "mixed" có cả hai.
TONES: tuple[str, ...] = ("everyday", "warm", "hurt", "mixed")

# `reason` đứng đầu: model viết ra điều vừa xảy ra và nhân vật cảm thấy gì TRƯỚC khi chấm số (chain-of-thought
# trong JSON; grammar của Ollama giữ đúng thứ tự thuộc tính), rồi `tone`, rồi mới tới số. `validate` bỏ `reason`.
SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "reason": {"type": "string"},
        "tone": {"type": "string", "enum": list(TONES)},
        "relationship_delta": _DELTA_SCHEMA,
        "location": {"type": "string"},
        "time": {"type": "string"},
        "memory": _MEMORY_SCHEMA,
        # maxItems: lượt dày fact (người chơi kể cả tiểu sử) làm model ghi 10+ fact, vượt NUM_PREDICT (đo: 14 fact,
        # done_reason "length" ở 500 token -> mất cả lượt trích xuất). `validate` cũng chỉ giữ MAX_FACTS.
        "facts": {
            "type": "array",
            "maxItems": MAX_FACTS,
            "items": {
                "type": "object",
                "properties": {"subject": {"type": "string"}, "text": {"type": "string"}},
                "required": ["subject", "text"],
            },
        },
    },
    "required": ["reason", "tone", "relationship_delta", "location", "time", "memory", "facts"],
}

# Lời mở đầu (lượt 0): chỉ cảnh và ký ức.
OPENING_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "location": {"type": "string"},
        "time": {"type": "string"},
        "memory": _MEMORY_SCHEMA,
    },
    "required": ["location", "time", "memory"],
}

EMOTION_LABEL_VI: dict[str, str] = {
    "affection": "thương mến",
    "trust": "tin cậy",
    "attraction": "rung động",
    "obsession": "nhung nhớ",
    "fear": "lo sợ mất mát",
    "aversion": "khoảng cách",
}
EMOTION_LABEL_EN: dict[str, str] = {
    "affection": "affection",
    "trust": "trust",
    "attraction": "attraction",
    "obsession": "longing",
    "fear": "fear of loss",
    "aversion": "distance",
}
GENDER_VI: dict[Gender, str] = {"male": "nam", "female": "nữ", "other": "phi nhị nguyên giới"}
GENDER_EN: dict[Gender, str] = {"male": "male", "female": "female", "other": "non-binary"}

# ---- xưng hô của người chơi với nhân vật ----------------------------------------------------------

# Cặp ngang hàng: người chơi dùng lại đúng cặp của nhân vật (nhân vật "tớ"/"cậu" -> người chơi cũng "tớ"/"cậu").
_PEER_SELF = frozenset({"tớ", "mình", "tao", "tui"})
_PEER_WITH_TOI = frozenset({"bạn", "cậu"})
# Từ thân tộc: hai bên đổi vai (nhân vật "anh"/"em" -> người chơi "em"/"anh").
_KIN = frozenset(
    {"anh", "chị", "em", "cô", "chú", "bác", "dì", "ông", "bà", "con", "cháu", "thầy", "mẹ", "bố", "ba", "má"}
)


def player_address(card: CharacterCard) -> tuple[str | None, str]:
    """(người chơi tự xưng, người chơi gọi nhân vật) suy ra từ `card.address_terms`.

    - Cặp ngang hàng (tớ/cậu, mình/cậu, tao/mày, tôi/bạn, ta/ngươi): người chơi dùng lại đúng cặp đó,
      tức gọi nhân vật bằng từ nhân vật gọi mình ("tớ" -> người chơi gọi nhân vật là "cậu").
    - Thân tộc (anh/em, chị/em, chú/cháu...): đổi vai, người chơi xưng `player_term`, gọi nhân vật `self_term`.
    - Nhân vật xưng "tôi" gọi người chơi "em": người chơi xưng "em", gọi "anh"/"chị" theo giới tính nhân vật.
    - Không suy ra được thì người chơi gọi nhân vật bằng tên, không rõ tự xưng (None).
    """
    at = card.address_terms
    self_t = at.self_term.strip().lower()
    player_t = at.player_term.strip().lower()
    name = card.name.strip()
    elder = {"male": "anh", "female": "chị"}.get(card.gender)
    if not self_t or not player_t:
        return None, name
    if self_t in _PEER_SELF or (self_t == "tôi" and player_t in _PEER_WITH_TOI) or (self_t, player_t) == ("ta", "ngươi"):
        return self_t, player_t
    if self_t in _KIN:
        return player_t, self_t
    if self_t == "tôi":
        if player_t == "em":
            return "em", elder or name
        return "tôi", elder or name
    return None, name


# ---- prompt ----------------------------------------------------------------------------------------

# Ví dụ trong prompt (ký ức, rồi hai fact). Model nhỏ đôi khi chép nguyên ví dụ, nên `validate` bỏ chúng.
_EXAMPLES_VI = ("{p} hứa cuối tuần sẽ cùng {c} về quê", "{c} không ăn được cay", "{p} học năm hai ngành kiến trúc")
_EXAMPLES_EN = (
    "{p} promised to visit {c}'s hometown this weekend",
    "{c} cannot eat spicy food",
    "{p} is a second-year architecture student",
)


def example_texts(card: CharacterCard, persona: Persona, language: str) -> list[str]:
    """Câu ví dụ (ký ức, fact, fact) đã điền tên, đúng như trong prompt."""
    c, p = card.name.strip(), persona.name.strip()
    return [e.replace("{c}", c).replace("{p}", p) for e in (_EXAMPLES_EN if language == "en" else _EXAMPLES_VI)]


def _clip(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + " …"


def is_opening(turn: Sequence[Message]) -> bool:
    """Lượt cần đọc là lời mở đầu của story (message assistant lượt 0)."""
    return any(m.role == "assistant" and m.turn_index == 0 for m in turn)


def _turn_mode(story: Story, turn: Sequence[Message]) -> Mode:
    for msg in reversed(turn):
        if msg.role == "assistant":
            return msg.mode
    return story.mode


def _scene_text(scene: SceneState, unknown: str) -> str:
    parts = [p.strip() for p in (scene.location, scene.time) if p and p.strip()]
    return ", ".join(parts) if parts else unknown


def _turn_lines(card: CharacterCard, persona: Persona, turn: Sequence[Message], nothing: str) -> list[str]:
    c, p = card.name.strip(), persona.name.strip()
    lines: list[str] = []
    for msg in turn:
        if msg.role == "user":
            text = _clip(msg.visible_content, _MAX_USER_CHARS) or nothing
            lines.append(f"{p}: {text}")
        else:
            lines.append(f"{c}: {_clip(msg.raw_content, _MAX_REPLY_CHARS)}")
    return lines


def _character_lines(card: CharacterCard, *, personality: str, secret: str) -> list[str]:
    """Tính cách (và bí mật) của nhân vật: model chấm cảm xúc theo đúng con người này."""
    lines: list[str] = []
    if card.personality.strip():
        lines.append(f"{personality}: {_clip(card.personality, _MAX_PERSONALITY_CHARS)}")
    if card.secrets.strip():
        lines.append(f"{secret}: {_clip(card.secrets, _MAX_SECRET_CHARS)}")
    return lines


def _delta_rules_vi(c: str, p: str) -> list[str]:
    """Luật chấm relationship_delta: mỗi chỉ số tăng khi nào, giảm khi nào, kèm ví dụ tương phản."""
    return [
        f"- reason: viết TRƯỚC, đúng một câu ngắn (dưới 25 từ) để tự nghĩ (không ai đọc): {p} vừa làm gì với {c} (quan tâm, bênh "
        f"vực, thân mật, hay thờ ơ, quên, lỡ hẹn, nói dối, thân thiết với người khác...), và theo tính cách cùng "
        f"[Thought] của {c} thì {c} thật sự thấy thế nào (vui, ghen, tổn thương, hụt hẫng, nghi ngờ, yên lòng...) "
        "hay chẳng có gì khác mọi ngày.",
        f'- tone: lượt này với {c} là gì. "everyday": chuyện thường ngày như mọi khi (chào hỏi, hỏi han, nhờ '
        f"giảng bài, trêu đùa, đi cùng nhau), kể cả khi {c} vẫn thấy vui, ấm lòng hay muốn che chở như mọi ngày. "
        f'"warm": điều đặc biệt làm {c} ấm lòng hay rung động (được bênh vực, được tâm sự, khoảnh khắc thân mật '
        f'hiếm có, lời xin lỗi thật lòng). "hurt": {p} làm điều sai với {c} hay làm {c} đau, nghi ngờ, xa cách '
        f"(quên điều quan trọng với {c}, lỡ hẹn, huỷ hẹn, thờ ơ, nói dối, đẩy {c} ra, thân thiết với người khác), "
        f'kể cả khi {c} ngoài mặt bỏ qua. "mixed": có cả hai. everyday thì mọi chỉ số đều 0. Chọn tone theo điều '
        f"{p} làm ở lượt này, không theo việc {c} vui hay rung động đến đâu: {c} tự sáp lại gần, tự thấy {p} đáng "
        f"yêu trong một buổi như mọi ngày thì vẫn là everyday.",
        f"- relationship_delta: cảm xúc của {c} với {p} thay đổi thế nào sau lượt này. Mỗi chỉ số là số nguyên "
        "từ -5 đến 5, dấu theo đúng điều đã xảy ra: chuyện làm ấm lòng thì affection, trust, attraction tăng còn "
        "obsession, fear, aversion giảm; chuyện làm đau, làm nghi ngờ hay làm xa cách thì ngược lại: affection, "
        "trust, attraction giảm còn obsession, fear, aversion tăng. Chấm theo điều "
        f'{p} đã làm: {c} ngoài mặt cười bảo "không sao", vẫn dịu dàng hay dung túng thì trong lòng vẫn hụt '
        "hẫng, vẫn chấm như chuyện làm đau. Ý nghĩa:",
        f"  - affection (thương mến): tăng khi {p} quan tâm, dịu dàng, ở bên {c}; giảm khi {p} lạnh nhạt, thờ ơ, "
        f"quên điều quan trọng với {c}, nói lời làm đau hay coi thường {c}.",
        f"  - trust (tin cậy): tăng khi {p} thành thật, giữ lời, tâm sự chuyện riêng, xin lỗi thật lòng; giảm khi "
        f"{p} nói dối, giấu giếm, thất hứa, lỡ hẹn hay huỷ hẹn không báo trước, hoặc vô tư thân thiết với người "
        f"khác khiến {c} bất an (kể cả khi {c} ngoài mặt vẫn dịu dàng bỏ qua, lòng tin vẫn sứt mẻ).",
        f"  - attraction (rung động): tăng khi có khoảnh khắc thân mật hiếm có làm tim {c} rung lên (đụng chạm, "
        f"ánh mắt, lời bày tỏ), không tăng vì những lần ngồi gần, giúp đỡ như mọi ngày; giảm khi {c} bị cự tuyệt "
        f"hay vỡ mộng về {p}.",
        f"  - obsession (nhung nhớ/chiếm hữu): tăng khi {p} xa cách hoặc gần gũi người khác khiến {c} muốn giữ chặt "
        f"{p}; giảm khi {c} thấy yên lòng, không còn phải giữ.",
        f"  - fear (lo sợ mất mát): tăng khi {c} sợ {p} rời xa hay thuộc về người khác (có người theo đuổi {p}, "
        f"{p} đẩy {c} ra); giảm khi {p} trấn an, làm lành, hứa ở lại.",
        f"  - aversion (khoảng cách/dè chừng): tăng khi {c} bị tổn thương, bị lừa, bị bỏ quên, bị đẩy ra nên thu "
        f"mình lại; giảm khi {p} xin lỗi, làm lành, mở lòng.",
        f"  Ví dụ cho một nhân vật thầm thương {p}, hay ghen (nhân vật khác thì chấm theo tính cách riêng):",
        f"  - {p} vui vẻ kể chuyện thân thiết với một người khác giới đang để ý mình: hurt; obsession 2, fear 2, "
        "trust -1 (không tăng affection).",
        f"  - {p} nói dối và bị {c} phát hiện: hurt; trust -3, aversion 2.",
        f"  - {p} quên mất ngày quan trọng của {c}, hoặc huỷ hẹn vào phút chót: hurt; affection -1, trust -1, "
        f'aversion 1 (kể cả khi {c} cười bảo "không sao").',
        f"  - {p} gắt gỏng, lạnh lùng đẩy {c} ra: hurt; affection -1, fear 2, aversion 2.",
        f"  - {p} xin lỗi thật lòng sau khi làm {c} buồn: warm; trust 1, aversion -2.",
        f"  - {p} chủ động tựa vào {c}, nói lời từ đáy lòng rằng {c} rất quan trọng với mình: warm; attraction 2, "
        "affection 1.",
        f"  - Chuyện trò thường ngày, hỏi han, trêu đùa như mọi khi: everyday; tất cả 0, kể cả khi {c} vẫn thấy vui, "
        "ấm lòng như mọi ngày.",
        "  Phần lớn các lượt là chuyện thường ngày: để tất cả 0; một câu ngọt hay cử chỉ quen thuộc không đủ để "
        "tăng. Chỉ khác 0 khi lượt này thật sự chạm vào đúng cảm xúc đó, thường 1-3 chỉ số. Mức: 1-2 là bình "
        f"thường, 3 là chuyện lớn với {c} (bị lừa dối, bị phản bội là chuyện lớn với tin cậy), 4-5 chỉ dành cho "
        "bước ngoặt. Nhân vật chiếm hữu, nhạy cảm hay đa nghi "
        "phản ứng mạnh hơn khi bị ghen, bị lừa, bị đẩy ra; nhân vật điềm tĩnh, rộng lượng thì nhẹ hơn.",
    ]


def _delta_rules_en(c: str, p: str) -> list[str]:
    return [
        f"- reason: write this FIRST, one short sentence (under 25 words) to think (nobody reads it): what {p} "
        f"just did to {c} "
        "(caring, standing up for them, an intimate moment, or neglect, forgetting, a broken plan, a lie, getting "
        f"close to someone else...), and, given {c}'s personality and [Thought], how {c} really feels about it "
        "(glad, jealous, hurt, let down, suspicious, reassured...) or that it is just like any other day.",
        f'- tone: what this turn is for {c}. "everyday": ordinary as usual (greetings, checking in, asking for '
        f"help with homework, teasing, hanging out), even if {c} still feels the usual warmth or protectiveness. "
        f'"warm": something special that warms {c} or makes their heart race (being stood up for, being confided '
        f'in, a rare intimate moment, a sincere apology). "hurt": {p} wrongs {c} or makes {c} hurt, doubtful or '
        f"distant (forgetting something important to {c}, missing or cancelling plans, neglect, lies, pushing {c} "
        f'away, getting close to someone else), even if {c} outwardly lets it go. "mixed": both. everyday means '
        f"every value is 0. Pick the tone by what {p} did this turn, not by how happy or flustered {c} feels: if "
        f"{c} leans in or finds {p} cute on an ordinary day, it is still everyday.",
        f"- relationship_delta: how {c}'s feelings toward {p} changed after this turn. Each value is an integer "
        "from -5 to 5 and its sign follows what happened: what warms the heart raises affection, trust and "
        "attraction and lowers obsession, fear and aversion; what hurts, breeds doubt or pushes away does the "
        "opposite: affection, trust and attraction drop, obsession, fear and aversion rise. Judge what "
        f"{p} did: if {c} smiles and says \"it's fine\", stays gentle or indulgent, they are still let down inside "
        "and it still counts as hurtful. Meaning:",
        f"  - affection: up when {p} is caring, gentle, stays with {c}; down when {p} is cold, neglectful, "
        f"forgets something important to {c}, says hurtful things or belittles {c}.",
        f"  - trust: up when {p} is honest, keeps promises, confides, apologizes sincerely; down when {p} lies, "
        f"hides things, breaks promises, misses or cancels plans without warning, or carelessly gets close to "
        f"someone else so that {c} feels insecure (even if {c} outwardly lets it go, the trust is still dented).",
        f"  - attraction: up on a rare intimate moment that makes {c}'s heart race (touch, a look, a confession), "
        f"not for sitting close or helping out as on any other day; down when {c} is rebuffed or disillusioned "
        f"with {p}.",
        f"  - obsession (longing/possessiveness): up when {p} grows distant or close to someone else and {c} wants "
        f"to hold on to {p}; down when {c} feels secure and no longer needs to hold on.",
        f"  - fear (fear of loss): up when {c} fears {p} will leave or belong to someone else (someone pursues {p}, "
        f"{p} pushes {c} away); down when {p} reassures, makes up, promises to stay.",
        f"  - aversion (distance/wariness): up when {c} is hurt, deceived, forgotten or pushed away and withdraws; "
        f"down when {p} apologizes, makes up, opens up.",
        f"  Examples for a character secretly in love with {p} and easily jealous (judge other characters by their "
        "own personality):",
        f"  - {p} happily talks about getting close to an admirer: hurt; obsession 2, fear 2, trust -1 (no "
        "affection gain).",
        f"  - {p} lied and {c} finds out: hurt; trust -3, aversion 2.",
        f"  - {p} forgets a day that matters to {c}, or cancels plans at the last minute: hurt; affection -1, "
        f'trust -1, aversion 1 (even if {c} smiles and says "it\'s fine").',
        f"  - {p} snaps at {c} and coldly pushes them away: hurt; affection -1, fear 2, aversion 2.",
        f"  - {p} sincerely apologizes after hurting {c}: warm; trust 1, aversion -2.",
        f"  - {p} leans on {c} and says from the heart how much {c} means to them: warm; attraction 2, affection 1.",
        f"  - Everyday small talk, checking in, the usual teasing: everyday; all 0, even if {c} still feels the "
        "usual warmth.",
        "  Most turns are everyday: leave everything at 0; a sweet line or a familiar gesture is not enough to "
        "raise anything. Only change a value when this turn really touches that exact feeling, usually 1-3 values. "
        f"Size: 1-2 is normal, 3 is a big deal for {c} (being lied to or betrayed is a big deal for trust), 4-5 is "
        "for turning points. Possessive, sensitive or "
        "suspicious characters react more strongly to jealousy, lies and rejection; calm, easygoing ones less.",
    ]


# Nhắc lại mức mẫu SAU lượt cần đọc (docs/phase3.md §10.7). Luật đầy đủ nằm ở system (đầu prompt, để cache); khi
# luật ở xa lượt cần đọc, model chấm nhẹ tay hơn: lời xin lỗi chỉ ra toàn ±1 (còn mỗi khoảng cách -1 sau kiểm tra)
# thay vì tin cậy +, khoảng cách -2; được bênh vực chỉ ra toàn ±1. Một dòng này (~150 token, không cache được) đưa
# lại đúng mức như khi luật đứng sau. Mẫu "được bênh vực" là nhãn warm đã nêu trong luật tone, thêm số cho nó; câu
# cuối nhắc lại hai luật tin cậy / khoảng cách đã có (đo: xin lỗi 4/4 ra trust 1, aversion -2; thiếu câu này 2/4).
_RECAP_VI = (
    "Mức mẫu (nhân vật thầm thương, hay ghen): ghen: hurt, obsession 2, fear 2, trust -1; bị nói dối: hurt, trust -3, "
    "aversion 2; bị quên, bị huỷ hẹn: hurt, affection -1, trust -1, aversion 1; bị đẩy ra: hurt, affection -1, fear 2, "
    "aversion 2; xin lỗi thật lòng: warm, trust 1, aversion -2; được bênh vực trước mọi người: warm, affection 2, "
    "attraction 2; thân mật thật sự: warm, attraction 2, affection 1; chuyện thường ngày: everyday, tất cả 0. Thất "
    "hứa, lỡ hẹn, huỷ hẹn thì trust giảm (kể cả khi có ghen); xin lỗi thật lòng thì aversion giảm 2, trust tăng."
)
_RECAP_EN = (
    "Reference sizes (a character secretly in love and easily jealous): jealousy: hurt, obsession 2, fear 2, trust -1; "
    "lied to: hurt, trust -3, aversion 2; forgotten, plans cancelled: hurt, affection -1, trust -1, aversion 1; pushed "
    "away: hurt, affection -1, fear 2, aversion 2; sincere apology: warm, trust 1, aversion -2; stood up for in front of "
    "others: warm, affection 2, attraction 2; a real intimate moment: warm, attraction 2, affection 1; everyday small "
    "talk: everyday, all 0. Broken promises, missed or cancelled plans lower trust (even when jealousy is involved); a "
    "sincere apology lowers aversion by 2 and raises trust."
)


def _split_prompt(
    intro: str,
    head: list[str],
    tasks: list[str],
    kind: str,
    state: list[str],
    turn_block: list[str],
    recap: str | None = None,
) -> list[ChatTurn]:
    """Phần cố định trước, phần đổi theo lượt sau (docs/phase3.md §10.7).

    System = vai trò + nhân vật (tên, xưng hô, tính cách, bí mật) + toàn bộ luật ghi: giống hệt nhau giữa mọi lượt
    của một story, Story lẫn DM (khoảng 2070 token với gemma4:12b). User = kiểu lượt (`kind`) + trạng thái trước
    lượt (chỉ số, cảnh, tóm tắt, fact) + lượt cần đọc + `recap` (mức mẫu, chỉ khi có chấm cảm xúc). Ollama dùng lại
    cache phần system kể cả khi có lời gọi chat chen giữa, nên lời gọi trích xuất kế tiếp chỉ phải đọc vài trăm
    token (~4-5 giây) thay vì ~2500 (~23 giây). Trước đây luật nằm SAU lượt cần đọc nên không bao giờ dùng lại được.
    """
    system = "\n\n".join([intro, "\n".join(head), "\n".join(tasks)])
    user = "\n\n".join([kind, "\n".join(state), "\n\n".join(turn_block), *([recap] if recap else [])])
    return [ChatTurn(role="system", content=system), ChatTurn(role="user", content=user)]


def _prompt_vi(
    card: CharacterCard,
    persona: Persona,
    story: Story,
    before: RelationshipValues,
    scene: SceneState,
    summary: str | None,
    turn: Sequence[Message],
    known_facts: Sequence[str],
) -> list[ChatTurn]:
    c, p = card.name.strip(), persona.name.strip()
    ex_memory, *ex_facts = example_texts(card, persona, "vi")
    mode = _turn_mode(story, turn)
    role = f", {card.role.strip()}" if card.role.strip() else ""
    head = [
        f"Nhân vật AI: {c} ({GENDER_VI[card.gender]}{role}). Người chơi: {p} ({GENDER_VI[persona.gender]}).",
    ]
    kind = "Kiểu lượt: " + (
        "Story (có dẫn truyện, hành động và lời thoại)." if mode == "story" else "Nhắn tin (DM), chỉ có tin nhắn."
    )
    at = card.address_terms
    player_self, player_calls = player_address(card)
    if at.self_term.strip() and at.player_term.strip():
        line = f'Xưng hô: {c} tự xưng "{at.self_term.strip()}", gọi {p} là "{at.player_term.strip()}".'
        if player_self:
            line += f' Khi {p} nói với {c}: {p} xưng "{player_self}", gọi {c} là "{player_calls}".'
        else:
            line += f" Khi {p} nói với {c}: gọi {c} là {player_calls}."
        head.append(line)
    head.extend(_character_lines(card, personality=f"Tính cách {c}", secret=f"Bí mật của {c}"))

    values = ", ".join(f"{EMOTION_LABEL_VI[k]} {getattr(before, k)}" for k in EMOTION_KEYS)
    state = [
        "Trạng thái trước lượt này:",
        f"- Cảm xúc của {c} với {p} (0-100): {values}.",
        f"- Cảnh hiện tại: {_scene_text(scene, 'chưa rõ')}.",
    ]
    if summary and summary.strip():
        state.append(f"- Chuyện trước đó: {_clip(summary, _MAX_SUMMARY_CHARS)}")
    facts = [f.strip() for f in known_facts if f.strip()][-MAX_KNOWN_FACTS_IN_PROMPT:]
    if facts:
        state.append("- Điều đã biết (không ghi lại):")
        state.extend(f"  - {f}" for f in facts)

    turn_block = [
        f"Lượt cần đọc ([Thought: ...] là suy nghĩ thầm của {c}, cho biết cảm xúc thật):",
        *_turn_lines(card, persona, turn, "(không viết gì)"),
    ]

    opening = is_opening(turn)
    if opening:
        turn_block[0] = f"Lời mở đầu của story (chưa có tương tác; [Thought: ...] là suy nghĩ thầm của {c}):"
    tasks = [
        "Ghi lại:",
        "\n".join(_delta_rules_vi(c, p)),
        '- location, time: nơi và thời điểm của cảnh sau lượt này, thật ngắn (ví dụ "Thư viện tầng ba", '
        '"Chiều tối"). Khi các nhân vật đã sang chỗ khác (đi ăn, về nhà, ra phố...) hoặc đã sang buổi khác, '
        'phải ghi nơi hay lúc mới. time là buổi hay mốc thời gian, suy ra từ dấu hiệu trong lượt (nắng chiều, ăn '
        'tối, thức khuya, "sáng hôm sau"...). Cảnh hiện tại "chưa rõ" thì ghi theo những gì lượt này cho thấy. '
        + f"Lượt nhắn tin (DM): location là nơi {p} đang ở, chỉ khi tin nhắn nói rõ {p} đang ở đâu lúc này; "
        "nơi hẹn gặp sau này không phải cảnh hiện tại; không đoán nơi. "
        'Chỉ để "" khi không đổi so với cảnh hiện tại hoặc lượt này không cho biết.',
        f"- memory: một câu kể sự việc đáng nhớ nhất của lượt này: ai làm gì, nói gì (ví dụ \"{ex_memory}\"). "
        "importance từ 1 đến 5: 1 là chuyện thường ngày, 5 là bước ngoặt của quan hệ. "
        'text là "" nếu lượt này không có gì đáng nhớ.',
        f"- facts: điều cụ thể, bền vững được nói ra hoặc xảy ra rõ ràng trong lượt này về {c}, {p}, người khác "
        "hoặc thế giới: sở thích, thói quen, quan hệ với người khác, lời hứa, sự kiện đã xảy ra, thông tin nhân thân "
        "(tuổi, nghề, quê, gia đình). Không ghi nhận xét về tính cách, cảm xúc hay điều đoán ra từ thái độ "
        f'(sai: "{c} rất dịu dàng", "{c} có tính chiếm hữu cao", "{p} có vẻ bối rối"; '
        f'đúng: "{ex_facts[0]}", "{ex_facts[1]}"). subject là tên người hoặc vật được nói tới. '
        "Không lặp lại điều đã biết. Phần lớn các lượt không có fact mới; khi đó trả mảng rỗng [].",
    ]
    if opening:
        # Lời mở đầu: chỉ cảnh và ký ức (không delta, không fact).
        tasks = ["Ghi lại:", tasks[2], tasks[3].replace("của lượt này", "của lời mở đầu")]
    intro = (
        "Bạn là người ghi chép cho một story roleplay tương tác. Đọc một lượt rồi ghi lại trạng thái bằng "
        "tiếng Việt. Chỉ trả JSON gọn trên một dòng (không xuống dòng, không thụt lề)."
    )
    return _split_prompt(intro, head, tasks, kind, state, turn_block, None if opening else _RECAP_VI)


def _prompt_en(
    card: CharacterCard,
    persona: Persona,
    story: Story,
    before: RelationshipValues,
    scene: SceneState,
    summary: str | None,
    turn: Sequence[Message],
    known_facts: Sequence[str],
) -> list[ChatTurn]:
    c, p = card.name.strip(), persona.name.strip()
    ex_memory, *ex_facts = example_texts(card, persona, "en")
    mode = _turn_mode(story, turn)
    role = f", {card.role.strip()}" if card.role.strip() else ""
    head = [
        f"AI character: {c} ({GENDER_EN[card.gender]}{role}). Player: {p} ({GENDER_EN[persona.gender]}).",
    ]
    kind = "Turn type: " + ("Story (narration, actions and dialogue)." if mode == "story" else "Text messages (DM) only.")
    head.extend(_character_lines(card, personality=f"{c}'s personality", secret=f"{c}'s secret"))
    values = ", ".join(f"{EMOTION_LABEL_EN[k]} {getattr(before, k)}" for k in EMOTION_KEYS)
    state = [
        "State before this turn:",
        f"- {c}'s feelings toward {p} (0-100): {values}.",
        f"- Current scene: {_scene_text(scene, 'unknown')}.",
    ]
    if summary and summary.strip():
        state.append(f"- Earlier in the story: {_clip(summary, _MAX_SUMMARY_CHARS)}")
    facts = [f.strip() for f in known_facts if f.strip()][-MAX_KNOWN_FACTS_IN_PROMPT:]
    if facts:
        state.append("- Already known (do not record again):")
        state.extend(f"  - {f}" for f in facts)
    turn_block = [
        f"Turn to read ([Thought: ...] is {c}'s private thought and shows the real feelings):",
        *_turn_lines(card, persona, turn, "(wrote nothing)"),
    ]
    opening = is_opening(turn)
    if opening:
        turn_block[0] = f"Opening of the story (no interaction yet; [Thought: ...] is {c}'s private thought):"
    tasks = [
        "Record:",
        "\n".join(_delta_rules_en(c, p)),
        '- location, time: where and when the scene is after this turn, very short (e.g. "Third-floor library", '
        '"Early evening"). Use "" if unchanged from the current scene or unclear.',
        f"- memory: one sentence about the most memorable thing in this turn: who did or said what "
        f"(e.g. \"{ex_memory}\"). importance 1-5: 1 is everyday, 5 is a turning point "
        'in the relationship. Use "" for text if nothing in this turn is worth remembering.',
        f"- facts: concrete, lasting facts clearly stated or shown in this turn about {c}, {p}, other people or "
        "the world: likes and dislikes, habits, relationships with others, promises, events that happened, personal "
        "details (age, job, hometown, family). No judgments about personality or mood, nothing guessed from "
        f'behavior (wrong: "{c} is gentle", "{c} is very possessive", "{p} seems flustered"; '
        f'right: "{ex_facts[0]}", "{ex_facts[1]}"). subject is the person or thing the fact is about. '
        "Do not repeat what is already known. Most turns reveal no new fact; then return [].",
    ]
    if opening:
        tasks = ["Record:", tasks[2], tasks[3].replace("in this turn", "in the opening")]
    intro = (
        "You take notes for an interactive roleplay story. Read one turn and record the state in English. "
        "Reply with compact JSON on a single line only (no line breaks, no indentation)."
    )
    return _split_prompt(intro, head, tasks, kind, state, turn_block, None if opening else _RECAP_EN)


def build_messages(
    *,
    card: CharacterCard,
    persona: Persona,
    story: Story,
    before: RelationshipValues,
    scene: SceneState,
    summary: str | None,
    turn: Sequence[Message],
    known_facts: Sequence[str] = (),
) -> list[ChatTurn]:
    """System + user message cho lời gọi trích xuất, theo `story.language`."""
    build = _prompt_en if story.language == "en" else _prompt_vi
    return build(card, persona, story, before, scene, summary, turn, known_facts)


# ---- kiểm tra kết quả ------------------------------------------------------------------------------

_PUNCT = re.compile(r"[^\w\s]|_")
_WS = re.compile(r"\s+")
_NONE_VALUES = frozenset(
    {"", "không rõ", "chưa rõ", "không đổi", "không có", "unknown", "unchanged", "none", "null", "n/a", "na", "-"}
)
# Dấu hiệu "fact" thật ra là nhận xét tính cách/cảm xúc (model nhỏ vẫn hay ghi dù prompt đã dặn).
_JUDGMENT = re.compile(
    r"\b(tính cách|có tính|có vẻ|dường như|hình như|tỏ ra|cảm thấy|"
    r"personality|seems?|appears? to|tends? to be|feels?)\b",
    re.IGNORECASE,
)


def normalize(text: str) -> str:
    """Khoá so trùng: NFC, chữ thường, bỏ dấu câu, gộp khoảng trắng."""
    text = unicodedata.normalize("NFC", text).casefold()
    return _WS.sub(" ", _PUNCT.sub(" ", text)).strip()


def _as_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            value = float(value.strip())
        except ValueError:
            return default
    if isinstance(value, float) and math.isfinite(value):  # bỏ NaN, ±inf (json.loads nhận Infinity, 1e999)
        return round(value)
    return default


def _text(value: Any) -> str:
    return _WS.sub(" ", value).strip() if isinstance(value, str) else ""


def _scene_value(value: Any, current: str | None) -> str | None:
    text = _text(value).strip(" .")
    if normalize(text) in _NONE_VALUES:
        return None
    if current and normalize(text) == normalize(current):
        return None
    return text


def _by_size(raw: dict[str, int]) -> list[str]:
    """Các chỉ số khác 0, lớn trước theo trị tuyệt đối; bằng nhau thì theo thứ tự EMOTION_KEYS."""
    return sorted((k for k in EMOTION_KEYS if raw.get(k)), key=lambda k: (-abs(raw[k]), EMOTION_KEYS.index(k)))


# Chiều "ấm lòng" của từng chỉ số: thương mến, tin cậy, rung động tăng là ấm; nhung nhớ/chiếm hữu, lo sợ,
# khoảng cách thì GIẢM mới là ấm (tăng là ghen, bất an, thu mình). Dấu số học không nói lên chuyện tốt hay xấu.
WARM_SIGN: dict[str, int] = {"affection": 1, "trust": 1, "attraction": 1, "obsession": -1, "fear": -1, "aversion": -1}


# Lượt ấm lòng toàn ±1 chỉ giữ một thay đổi: ưu tiên dấu hiệu làm lành (khoảng cách, lo sợ, nhung nhớ giảm)
# trước thương mến / tin cậy / rung động tăng.
_REPAIR_ORDER: dict[str, int] = {"aversion": 0, "fear": 1, "obsession": 2}

# Lượt tổn thương, các thay đổi cùng cỡ: tin cậy giảm đứng trước. Thương mến -1 là con số model rắc vào gần như mọi lượt
# tổn thương; tin cậy giảm mới nói chuyện gì đã xảy ra (ghen, huỷ hẹn, nói dối) và là điều các ví dụ trong prompt yêu
# cầu ("ghen: obsession 2, fear 2, trust -1"). Còn lại theo thứ tự EMOTION_KEYS.
_HURT_ORDER: dict[str, int] = {"trust": 0}


def is_warm(key: str, value: int) -> bool:
    """Thay đổi này làm quan hệ ấm lên (True) hay tổn thương (False)."""
    return value * WARM_SIGN[key] > 0


def _guess_tone(raw: dict[str, int], warm: list[str], hurt: list[str]) -> str:
    """Không có `tone` hợp lệ (dữ liệu cũ, demo DB): đoán theo các con số."""
    if not hurt:
        return "warm"
    if not warm:
        return "hurt"
    if abs(raw[warm[0]]) >= 2 and abs(raw[hurt[0]]) >= 2:
        return "mixed"
    weight_warm, weight_hurt = sum(abs(raw[k]) for k in warm), sum(abs(raw[k]) for k in hurt)
    return "warm" if weight_warm > weight_hurt else "hurt"  # bằng nhau: nghiêng về tổn thương


def pick_changes(raw: dict[str, int], tone: str | None = None) -> list[str]:
    """Chọn các chỉ số được giữ (docs/phase3.md §10.5), theo chiều ấm/tổn thương chứ không theo dấu số học.

    - `tone` "everyday": không giữ gì (chuyện thường ngày không làm cảm xúc nhích lên).
    - "warm": chỉ giữ thay đổi ấm lòng, tối đa 2; nếu đều ±1 thì chỉ giữ 1 (kiểu "affection +1, attraction +1"
      mỗi lượt làm cảm xúc trôi dần lên), ưu tiên dấu hiệu làm lành (`_REPAIR_ORDER`: aversion, fear, obsession
      giảm) rồi mới tới thứ tự EMOTION_KEYS. Thay đổi tổn thương lẻ (obsession +1, fear +1 khi được ôm) là nhiễu.
    - "hurt": chỉ giữ thay đổi tổn thương, tối đa 3, kể cả ±1 (ghen: obsession 2, fear 2, trust -1 giữ cả ba).
      Cùng cỡ thì tin cậy giảm đứng trước (`_HURT_ORDER`): "affection -1, trust -1, obsession 2, fear 2" giữ trust,
      không giữ affection. Thay đổi ấm lòng lẻ (attraction +1 lúc đang ghen) là nhiễu.
    - "mixed": giữ thay đổi lớn nhất của mỗi chiều, thêm cái thứ ba khi nó đổi từ 2 trở lên.
    - Không có `tone` (hoặc sai): đoán theo các con số (`_guess_tone`).
    Bằng cỡ thì theo thứ tự EMOTION_KEYS.
    """
    order = _by_size(raw)
    if tone == "everyday" or not order:
        return []
    warm = [k for k in order if is_warm(k, raw[k])]
    hurt = sorted(
        (k for k in order if not is_warm(k, raw[k])),
        key=lambda k: (-abs(raw[k]), _HURT_ORDER.get(k, len(_HURT_ORDER)), EMOTION_KEYS.index(k)),
    )
    if tone not in ("warm", "hurt", "mixed"):
        tone = _guess_tone(raw, warm, hurt)
    if tone == "mixed" and not (warm and hurt):
        tone = "warm" if warm else "hurt"
    if tone == "warm":
        if all(abs(raw[k]) == 1 for k in warm):
            # Đều ±1: giữ một, chọn theo nghĩa chứ không theo thứ tự khoá. Khoảng cách / lo sợ / nhung nhớ giảm
            # chỉ xuất hiện khi có chuyện làm lành (xin lỗi, trấn an) nên nói nhiều hơn thương mến +1, con số
            # model hay rắc vào mọi lượt.
            return sorted(warm, key=lambda k: (_REPAIR_ORDER.get(k, len(_REPAIR_ORDER)), EMOTION_KEYS.index(k)))[:1]
        return warm[:MAX_CHANGED_EMOTIONS]
    if tone == "hurt":
        return hurt[:MAX_CHANGED_EMOTIONS_MIXED]
    kept = [warm[0], hurt[0]]
    kept.extend(k for k in order if k not in kept and abs(raw[k]) >= 2)
    return sorted(kept[:MAX_CHANGED_EMOTIONS_MIXED], key=order.index)


def top_delta(raw: dict[str, int], keep: int | None = None, tone: str | None = None) -> dict[str, int]:
    """Chỉ giữ một vài thay đổi khác 0, các chỉ số khác về 0. Model nhỏ hay cho 3-6 chỉ số cùng nhích lên mỗi
    lượt, làm cảm xúc trôi dần lên.
    `keep` None = theo `pick_changes(raw, tone)`; có `keep` thì giữ đúng `keep` thay đổi lớn nhất."""
    kept = set(pick_changes(raw, tone) if keep is None else _by_size(raw)[:keep])
    return {k: (raw.get(k, 0) if k in kept else 0) for k in EMOTION_KEYS}


def validate(
    data: Any,
    *,
    scene: SceneState,
    known_facts: Sequence[str] = (),
    player_texts: Sequence[str] = (),
    examples: Sequence[str] = (),
    opening: bool = False,
) -> ExtractionResult:
    """Đổi JSON thô của model thành ExtractionResult hợp lệ; không bao giờ raise vì dữ liệu xấu.

    Kẹp delta về ±MAX_DELTA rồi chỉ giữ 0-3 thay đổi theo `tone` (`pick_changes`); `reason`, `tone` bị bỏ;
    cắt khoảng trắng; cảnh trùng
    cảnh hiện tại hoặc rỗng = không đổi (None); tối đa 3 fact; bỏ fact trùng nhau, trùng câu ký ức của lượt,
    hoặc trùng `known_facts` (so sau khi `normalize`). Ký ức/fact trùng câu ví dụ của prompt (`examples`)
    bị bỏ. `opening` (lời mở đầu): delta luôn 0, không fact. Kết quả không có gợi ý (Phase 3b).
    `player_texts` giữ lại cho tương thích, không còn dùng.
    """
    del player_texts
    copied = {normalize(e) for e in examples if e.strip()}
    if not isinstance(data, dict):
        data = {}

    raw_delta = data.get("relationship_delta")
    raw_delta = raw_delta if isinstance(raw_delta, dict) else {}
    clamped = {k: max(-MAX_DELTA, min(MAX_DELTA, _as_int(raw_delta.get(k)))) for k in EMOTION_KEYS}
    tone = data.get("tone")
    tone = tone.strip().casefold() if isinstance(tone, str) else None
    delta = RelationshipDelta() if opening else RelationshipDelta(**top_delta(clamped, tone=tone))

    new_scene = SceneState(
        location=_scene_value(data.get("location"), scene.location),
        time=_scene_value(data.get("time"), scene.time),
    )

    memory: str | None = None
    importance = 3
    raw_memory = data.get("memory")
    if isinstance(raw_memory, dict):
        text = _text(raw_memory.get("text"))
        if normalize(text) not in _NONE_VALUES and normalize(text) not in copied:
            memory = text
        importance = max(1, min(5, _as_int(raw_memory.get("importance"), 3)))
    elif isinstance(raw_memory, str) and normalize(raw_memory) not in _NONE_VALUES | copied:
        memory = _text(raw_memory)

    facts: list[FactDraft] = []
    seen = {normalize(f) for f in known_facts if f.strip()} | copied
    if memory:
        seen.add(normalize(memory))  # model hay chép nguyên câu ký ức sang fact: trùng thì bỏ fact
    raw_facts = data.get("facts") if not opening else None
    for item in raw_facts if isinstance(raw_facts, list) else []:
        if len(facts) >= MAX_FACTS:
            break
        if isinstance(item, dict):
            subject, text = _text(item.get("subject")), _text(item.get("text"))
        elif isinstance(item, str):
            subject, text = "", _text(item)
        else:
            continue
        key = normalize(text)
        if not key or key in _NONE_VALUES or key in seen or _JUDGMENT.search(text):
            continue
        seen.add(key)
        facts.append(FactDraft(subject=subject, text=text))

    return ExtractionResult(
        relationship_delta=delta,
        scene=new_scene,
        memory=memory,
        memory_importance=importance,
        facts=facts,
    )


# ---- lời gọi ---------------------------------------------------------------------------------------


async def extract_turn(
    llm,  # noqa: ANN001 - LLMClient
    *,
    model: str,
    num_ctx: int,
    card: CharacterCard,
    persona: Persona,
    story: Story,
    before: RelationshipValues,
    scene: SceneState,
    summary: str | None,
    turn: list[Message],
    known_facts: Sequence[str] = (),
) -> ExtractionResult:
    """Trích xuất state của một lượt.

    `turn`: các message user của lượt (có thể không có) rồi message assistant (dùng `raw_content`, có Thought).
    Lời mở đầu (assistant lượt 0, không có message user) chỉ ghi cảnh và ký ức.
    `before`/`scene`/`summary`: state ngay trước lượt này. `known_facts`: text các fact đã có của story
    (để model không ghi lại và để bỏ trùng). Raise LLMError khi gọi model lỗi (LLMOutputError khi JSON hỏng).
    """
    if not any(m.role == "assistant" for m in turn):
        raise ValueError("Lượt cần trích xuất phải có message của nhân vật (role 'assistant').")
    messages = build_messages(
        card=card,
        persona=persona,
        story=story,
        before=before,
        scene=scene,
        summary=summary,
        turn=turn,
        known_facts=known_facts,
    )
    opening = is_opening(turn)
    data = await llm.chat_json(
        model,
        messages,
        schema=OPENING_SCHEMA if opening else SCHEMA,
        options={"num_ctx": num_ctx, "num_predict": NUM_PREDICT, "temperature": TEMPERATURE},
    )
    return validate(
        data,
        scene=scene,
        known_facts=known_facts,
        examples=example_texts(card, persona, story.language),
        opening=opening,
    )
