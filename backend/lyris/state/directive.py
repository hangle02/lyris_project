"""Chỉ dẫn diễn xuất: đổi 6 chỉ số cảm xúc thành 1-2 câu nói thái độ của nhân vật (docs/phase3.md §3).

Hàm thuần, bảng luật cố định: cùng đầu vào thì cùng câu. Không bao giờ in số, vì model nhỏ sẽ chép số
vào truyện ("độ thương mến 70"). Câu này vào khối F của prompt và hiện ở thẻ "Chỉ dẫn diễn xuất".

Cách ghép:
  - Câu 1: tình cảm nền theo thương mến x tin cậy (bảng 3x3), chỉnh theo khoảng cách khi khoảng cách cao.
  - Phần sau: tối đa hai "nỗi lòng" từ rung động, nhung nhớ, lo sợ mất mát (kèm các tổ hợp đáng chú ý:
    rung động cao + khoảng cách cao, lo sợ cao + nhung nhớ cao, tin cậy thấp + thương mến cao).

Tên người chơi chỉ xuất hiện MỘT lần trong cả chỉ dẫn (Phase 3b): lần sau dùng đại từ (đại từ dẫn truyện
của người chơi nếu có, không thì "người ấy" / "them"), tránh "... Lâm Vãn; muốn lại gần Lâm Vãn ...".
Tên nhân vật cũng chỉ một lần: câu thứ hai bắt đầu bằng đại từ dẫn truyện của nhân vật ("Anh còn ...");
không có đại từ dùng được thì gộp vào câu đầu (", và còn ..."), không lặp "Lạc Dương còn ...".
"""
from __future__ import annotations

from typing import Literal

from lyris.models import Language, RelationshipValues

Level = Literal["low", "mid", "high"]

LOW_BELOW = 30  # < 30: thấp
HIGH_FROM = 70  # >= 70: cao; còn lại: vừa


def level(value: int) -> Level:
    if value >= HIGH_FROM:
        return "high"
    if value >= LOW_BELOW:
        return "mid"
    return "low"


# ---- tiếng Việt ----------------------------------------------------------------------------------

# Tình cảm nền: (thương mến, tin cậy) -> vị ngữ. {p} = tên người chơi.
_BOND_VI: dict[tuple[Level, Level], str] = {
    ("high", "high"): "rất thương mến và tin cậy {p}",
    ("high", "mid"): "rất thương mến {p} và ngày càng tin tưởng hơn",
    ("high", "low"): "thương {p} thật lòng, quan tâm nhưng chưa dám mở lòng",
    ("mid", "high"): "quý mến và tin cậy {p}",
    ("mid", "mid"): "có thiện cảm và bắt đầu tin tưởng {p}",
    ("mid", "low"): "có thiện cảm với {p} nhưng vẫn còn dè chừng",
    ("low", "high"): "tin {p} nhưng chưa thấy gần gũi",
    ("low", "mid"): "đối xử với {p} bình thường, chưa thân thiết",
    ("low", "low"): "chưa tin {p} và còn xa cách",
}

# Khoảng cách cao (khi không đi kèm rung động cao) và thương mến thấp: lạnh nhạt hẳn; theo mức tin cậy.
_COLD_VI: dict[Level, str] = {
    "high": "lạnh nhạt và giữ khoảng cách rõ rệt với {p}, dù vẫn tin tưởng",
    "mid": "lạnh nhạt, giữ khoảng cách rõ rệt với {p}",
    "low": "lạnh nhạt, dè chừng và giữ khoảng cách rõ rệt với {p}",
}
# Khoảng cách cao, thương mến vừa/cao: thay hẳn câu nền (không nối thêm, tránh hai chữ "nhưng").
_GUARDED_VI: dict[tuple[Level, Level], str] = {
    ("high", "high"): "rất thương mến và tin cậy {p}, nhưng vẫn cố giữ khoảng cách",
    ("high", "mid"): "rất thương mến {p} nhưng vẫn cố giữ khoảng cách",
    ("high", "low"): "thương {p} thật lòng nhưng chưa dám mở lòng, vẫn cố giữ khoảng cách",
    ("mid", "high"): "quý mến và tin cậy {p}, nhưng vẫn cố giữ khoảng cách",
    ("mid", "mid"): "có thiện cảm với {p} nhưng vẫn cố giữ khoảng cách",
    ("mid", "low"): "có thiện cảm với {p} nhưng vẫn dè chừng, giữ khoảng cách",
}

# Rung động theo mức khoảng cách (khi rung động cao).
_ATTRACTION_HIGH_VI: dict[Level, str] = {
    "high": "trong lòng muốn lại gần {p} nhưng vẫn còn giữ ý, chưa để lộ ra",
    "mid": "đang rung động nhưng vẫn giữ trong lòng, chưa nói ra",
    "low": "đang rung động rõ rệt, khó giấu được cảm xúc",
}
_ATTRACTION_MID_VI = "đôi lúc thấy lòng xao động vì {p}"

_JEALOUS_VI = "dễ ghen, chỉ muốn giữ chặt {p} bên mình"
_OBSESSION_HIGH_VI = "lúc nào cũng nghĩ về {p}, chỉ muốn mình là người duy nhất được để ý"
_FEAR_HIGH_VI = "rất sợ mất {p}, chỉ cần xa nhau một chút là bất an"
_LONGING_MID_VI = "hay nhớ đến {p}, thấp thỏm sợ bị bỏ lại"
_FEAR_MID_VI = "thỉnh thoảng lo {p} sẽ rời đi"
_OBSESSION_MID_VI = "hay nghĩ về {p}"

# ---- tiếng Anh -----------------------------------------------------------------------------------

_BOND_EN: dict[tuple[Level, Level], str] = {
    ("high", "high"): "deeply cares for and trusts {p}",
    ("high", "mid"): "deeply cares for {p} and trusts them more each day",
    ("high", "low"): "truly cares for {p} but is not ready to open up yet",
    ("mid", "high"): "is fond of {p} and trusts them",
    ("mid", "mid"): "is warming to {p} and starting to trust them",
    ("mid", "low"): "is fond of {p} but still wary",
    ("low", "high"): "trusts {p} but does not feel close to them yet",
    ("low", "mid"): "treats {p} politely, without any special closeness",
    ("low", "low"): "does not trust {p} and keeps them at a distance",
}
_COLD_EN: dict[Level, str] = {
    "high": "trusts {p} yet stays cold and clearly distant",
    "mid": "is cold toward {p} and clearly keeps their distance",
    "low": "is cold and guarded toward {p}, clearly keeping their distance",
}
_GUARDED_EN: dict[tuple[Level, Level], str] = {
    ("high", "high"): "deeply cares for and trusts {p}, yet still keeps some distance",
    ("high", "mid"): "deeply cares for {p} yet still keeps some distance",
    ("high", "low"): "truly cares for {p} but stays guarded, keeping some distance",
    ("mid", "high"): "is fond of {p} and trusts them, yet still keeps some distance",
    ("mid", "mid"): "is fond of {p} yet still keeps some distance",
    ("mid", "low"): "is fond of {p} but wary, keeping their distance",
}

_ATTRACTION_HIGH_EN: dict[Level, str] = {
    "high": "wants to get closer to {p} but still holds back, not letting it show",
    "mid": "is falling for {p} but keeps it unspoken",
    "low": "is openly smitten with {p} and can hardly hide it",
}
_ATTRACTION_MID_EN = "sometimes feels a flutter around {p}"

_JEALOUS_EN = "gets jealous easily, wanting to hold on to {p} tightly"
_OBSESSION_HIGH_EN = "thinks about {p} constantly, wanting all of their attention"
_FEAR_HIGH_EN = "is afraid of losing {p}, uneasy whenever they seem distant"
_LONGING_MID_EN = "often thinks about {p}, quietly worried they might leave"
_FEAR_MID_EN = "now and then worries about {p} leaving"
_OBSESSION_MID_EN = "often thinks about {p}"


def _phrases(values: RelationshipValues, language: Language) -> tuple[str, list[str]]:
    """(tình cảm nền, các nỗi lòng theo thứ tự ưu tiên, tối đa 2), còn chứa chỗ trống {p}."""
    en = language == "en"
    aff, tru, att = level(values.affection), level(values.trust), level(values.attraction)
    obs, fea, ave = level(values.obsession), level(values.fear), level(values.aversion)

    bond = (_BOND_EN if en else _BOND_VI)[(aff, tru)]
    if ave == "high" and att != "high":
        if aff == "low":
            bond = (_COLD_EN if en else _COLD_VI)[tru]
        else:
            bond = (_GUARDED_EN if en else _GUARDED_VI)[(aff, tru)]

    inner: list[str] = []
    if att == "high":
        inner.append((_ATTRACTION_HIGH_EN if en else _ATTRACTION_HIGH_VI)[ave])
    if fea == "high" and obs == "high":
        inner.append(_JEALOUS_EN if en else _JEALOUS_VI)
    elif obs == "high":
        inner.append(_OBSESSION_HIGH_EN if en else _OBSESSION_HIGH_VI)
    elif fea == "high":
        inner.append(_FEAR_HIGH_EN if en else _FEAR_HIGH_VI)
    elif obs == "mid" and fea == "mid":
        inner.append(_LONGING_MID_EN if en else _LONGING_MID_VI)
    elif fea == "mid":
        inner.append(_FEAR_MID_EN if en else _FEAR_MID_VI)
    elif obs == "mid":
        inner.append(_OBSESSION_MID_EN if en else _OBSESSION_MID_VI)
    if att == "mid" and len(inner) < 2:
        inner.append(_ATTRACTION_MID_EN if en else _ATTRACTION_MID_VI)
    return bond, inner[:2]


# Đại từ dẫn truyện không dùng được thay tên trong chỉ dẫn (ngôi thứ nhất/hai, sẽ làm model nhầm vai).
_NOT_THIRD_PERSON = frozenset({"tôi", "tớ", "mình", "ta", "tao", "bạn", "cậu", "mày", "i", "you", "me"})


# Đại từ tiếng Anh làm chủ ngữ được cho câu thứ hai (động từ trong bảng luật chia ngôi thứ ba số ít).
_EN_SUBJECT = {"he": "He", "she": "She"}


def _vi_pronoun(pronoun: str | None, names: tuple[str, ...]) -> str | None:
    """Đại từ dẫn truyện tiếng Việt dùng được thay tên, viết thường ("Cô" -> "cô"); None = không dùng được.

    Không dùng được: rỗng, ngôi thứ nhất/hai, hoặc thật ra là tên (nhân vật/người chơi giới tính "khác" thì
    hồ sơ văn phong để trống đại từ, story lưu tên vào chỗ đại từ), vì dùng nó là lặp lại tên."""
    word = " ".join((pronoun or "").split())
    if not word or word.casefold() in _NOT_THIRD_PERSON:
        return None
    if any(word.casefold() == " ".join(n.split()).casefold() for n in names if n.strip()):
        return None
    if " " not in word and word[1:] == word[1:].lower():
        word = word.lower()  # đại từ một chữ viết hoa ("Cô") sẽ nằm giữa câu
    return word


def _char_subject(
    language: Language, pronoun: str | None, player_pronoun: str | None, names: tuple[str, ...] = ()
) -> str | None:
    """Chủ ngữ cho câu thứ hai thay cho tên nhân vật; None = không dùng được (gộp vào câu đầu)."""
    if language == "en":
        return _EN_SUBJECT.get((pronoun or "").strip().casefold())
    word = _vi_pronoun(pronoun, names)
    if word is None:
        return None
    if word.casefold() == (player_pronoun or "").strip().casefold():
        return None  # hai bên cùng đại từ ("anh" ... "anh"): dễ nhầm người, gộp câu
    return word[:1].upper() + word[1:]


def _later_reference(language: Language, pronoun: str | None, names: tuple[str, ...] = ()) -> str:
    if language == "en":
        return "them"
    return _vi_pronoun(pronoun, names) or "người ấy"


def _name_once(text: str, name: str, later: str) -> str:
    """Thay chỗ trống {p} đầu tiên bằng tên, các chỗ sau bằng đại từ."""
    head, sep, rest = text.partition("{p}")
    if not sep:
        return text
    return head + name + rest.replace("{p}", later)


def acting_directive(
    values: RelationshipValues,
    *,
    char: str,
    player: str,
    language: Language,
    player_pronoun: str | None = None,
    char_pronoun: str | None = None,
) -> str:
    """1-2 câu nói thái độ hiện tại của `char` với `player`, không có số.

    Ví dụ: "Lạc Dương rất thương mến và tin cậy Lâm Vãn; đang rung động nhưng vẫn giữ trong lòng, chưa nói ra."
    Tên người chơi chỉ viết một lần; các lần sau là `player_pronoun` (đại từ dẫn truyện, vd "cô").
    Tên nhân vật cũng một lần; câu thứ hai dùng `char_pronoun` (đại từ dẫn truyện của nhân vật, vd "anh").
    """
    c = char.strip()
    p = player.strip()
    bond, inner = _phrases(values, language)
    subject = _char_subject(language, char_pronoun, player_pronoun, (c, p))
    if language == "en":
        out = f"{c} {bond}"
        if inner and subject:
            out += f". {subject} {', and '.join(inner)}"
        elif len(inner) > 1:
            # Không có he/she: liệt kê một lần "A, B, and C", tránh ", and ..., and ..." nối đuôi.
            out += f", {inner[0]}, and {inner[1]}"
        elif inner:
            out += f", and {inner[0]}"
        out += "."
    else:
        out = f"{c} {bond}"
        if inner:
            out += f"; {inner[0]}"
        if len(inner) > 1:
            out += f". {subject} còn {inner[1]}" if subject else f", và còn {inner[1]}"
        out += "."
    return _name_once(out, p, _later_reference(language, player_pronoun, (c, p)))
