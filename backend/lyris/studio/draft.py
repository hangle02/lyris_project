"""AI viết nháp: một dòng ý tưởng -> CharacterCard đầy đủ (chưa lưu) bằng structured output của Ollama.

Model (`gemma4:12b`) tôn trọng `format` = JSON schema (khoá, enum) nhưng các trường văn bản tự do đôi khi
viết lan man, xưng hô hay bị viết hoa ("Sư tỷ") hoặc kèm nhiều lựa chọn ("Đệ tử/Đệ muội"). Vì vậy: prompt
ghi rõ độ dài từng trường và hậu xử lý chặt (cắt trường quá dài, chuẩn hoá xưng hô, cắt danh sách, sửa thẻ
Thought, cảnh báo).

Schema KHÔNG dùng `maxLength` cho chuỗi (đã thử với Ollama + gemma4:12b): grammar sinh ra cho chuỗi có
giới hạn độ dài không cho phép ký tự escape, nên model không viết được "\n" (lời mở đầu dính thành một
đoạn, model đóng chuỗi sớm, ví dụ thoại thành "  n  "); còn khi chạm giới hạn thì model kẹt, sinh khoảng
trắng tới hết `num_predict` và request hỏng ("length"). Giới hạn độ dài vì vậy chỉ áp ở hậu xử lý.
"""
from __future__ import annotations

import copy
import re
from typing import Any

from lyris.llm.base import LLMClient
from lyris.models import AddressTerms, CharacterCard, ChatTurn, Gender, Language, StyleProfileInfo

MAX_IDEA_CHARS = 2000
FALLBACK_STYLE = "chung"
MAX_NICKNAMES = 4
MAX_TAGS = 6
MAX_NAME_CHARS = 80
MAX_TAG_CHARS = 40
MAX_ROLE_CHARS = 60

DRAFT_OPTIONS: dict[str, Any] = {"temperature": 0.8, "num_predict": 2048, "num_ctx": 8192}

_GENDERS: tuple[Gender, ...] = ("male", "female", "other")

# Giới hạn ký tự cho từng trường văn bản, áp ở hậu xử lý (rộng gấp 2-3 lần độ dài mong muốn trong prompt);
# vượt giới hạn nghĩa là model viết lan man -> cắt về hết câu cuối trong giới hạn + cảnh báo.
FIELD_MAX_CHARS: dict[str, int] = {
    "name": 60,
    "description": 500,
    "personality": 500,
    "appearance": 450,
    "background": 600,
    "goals": 350,
    "secrets": 350,
    "speech_style": 450,
    "self_term": 30,
    "player_term": 30,
    "others": 250,
    "scenario": 500,
    "greeting": 2200,
    "example_dialogues": 700,
}

FIELD_LABELS: dict[str, str] = {
    "name": "Tên",
    "role": "Vai trò",
    "description": "Mô tả",
    "personality": "Tính cách",
    "appearance": "Ngoại hình",
    "background": "Hoàn cảnh",
    "goals": "Mục tiêu",
    "secrets": "Bí mật",
    "speech_style": "Cách nói",
    "self_term": "Tự xưng",
    "player_term": "Gọi người chơi",
    "others": "Xưng hô với người khác",
    "scenario": "Bối cảnh",
    "greeting": "Lời mở đầu",
    "example_dialogues": "Ví dụ thoại",
}

_TEXT_FIELDS = (
    "description",
    "personality",
    "appearance",
    "background",
    "goals",
    "secrets",
    "speech_style",
    "others",
    "scenario",
    "greeting",
    "example_dialogues",
)


def _string() -> dict[str, Any]:
    # Không có maxLength: xem docstring đầu module.
    return {"type": "string"}


def _string_list(max_items: int) -> dict[str, Any]:
    return {"type": "array", "items": _string(), "maxItems": max_items}


# Thứ tự khoá là thứ tự model viết: tên, giới tính, văn phong trước; xưng hô trước lời mở đầu
# (để lời mở đầu dùng đúng xưng hô vừa chọn).
DRAFT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "name": _string(),
        "gender": {"type": "string", "enum": list(_GENDERS)},
        "style_profile": {"type": "string"},
        "role": _string(),
        "description": _string(),
        "personality": _string(),
        "appearance": _string(),
        "background": _string(),
        "goals": _string(),
        "secrets": _string(),
        "speech_style": _string(),
        "self_term": _string(),
        "player_term": _string(),
        "nicknames": _string_list(3),
        "others": _string(),
        "scenario": _string(),
        "greeting": _string(),
        "example_dialogues": _string(),
        "tags": _string_list(MAX_TAGS),
    },
    "required": [
        "name",
        "gender",
        "style_profile",
        "role",
        "description",
        "personality",
        "appearance",
        "background",
        "goals",
        "secrets",
        "speech_style",
        "self_term",
        "player_term",
        "nicknames",
        "others",
        "scenario",
        "greeting",
        "example_dialogues",
        "tags",
    ],
    "additionalProperties": False,
}


class DraftError(ValueError):
    """Đầu vào của AI viết nháp không hợp lệ (thông điệp tiếng Việt, API trả 422)."""


# ---- schema ---------------------------------------------------------------------------------------


def draft_schema(style_names: list[str], *, gender: Gender | None = None, style_profile: str | None = None) -> dict[str, Any]:
    """DRAFT_SCHEMA với enum cụ thể: style_profile theo danh sách profile (hoặc đúng một giá trị khi người dùng
    đã chọn), gender ép một giá trị khi người dùng đã chọn."""
    schema = copy.deepcopy(DRAFT_SCHEMA)
    props = schema["properties"]
    if style_profile is not None:
        props["style_profile"]["enum"] = [style_profile]
    else:
        props["style_profile"]["enum"] = list(style_names) or [FALLBACK_STYLE]
    if gender is not None:
        props["gender"]["enum"] = [gender]
    return schema


# ---- prompt ---------------------------------------------------------------------------------------

_VI_SYSTEM = """\
Bạn là biên tập viên giúp người dùng viết thẻ nhân vật (character card) cho một ứng dụng nhập vai bằng chữ. Từ một dòng ý tưởng, hãy tạo một nhân vật có chiều sâu, nhất quán, đủ chất liệu để nhập vai lâu dài, rồi trả về đúng một object JSON theo schema.

Quy ước chung:
- Viết mọi trường bằng tiếng Việt tự nhiên, có dấu đầy đủ, kể cả khi ý tưởng viết bằng ngôn ngữ khác.
- Người chơi luôn được gọi là {{user}} (viết đúng như vậy, có hai cặp ngoặc nhọn). Không tự đặt tên cho người chơi. Nếu ý tưởng không nói rõ giới tính người chơi thì viết sao cho hợp với người chơi nam hay nữ đều được, và không dùng đại từ có giới tính (anh, cô, hắn, nàng, y) để chỉ {{user}}.
- Nhân vật thì viết thẳng tên, không viết {{char}} (trừ trong example_dialogues). Ở mọi trường, khi cần đại từ cho nhân vật thì dùng đúng đại từ dẫn truyện của style profile đã chọn (ví dụ cổ trang: "hắn" cho nam, "nàng" cho nữ), không dùng "anh"/"cô" cho nhân vật cổ trang.
- Tên người, địa danh, đồ vật, món ăn theo đúng văn hoá của bối cảnh: bối cảnh Trung Quốc dùng tên Hán Việt (ví dụ Tạ Vân Lan, Lục Trần, Thanh Vân Tông), bối cảnh Việt Nam dùng tên người Việt (ví dụ Trần Minh Khang), bối cảnh phương Tây dùng tên phương Tây.
- Ngắn gọn là bắt buộc. Mỗi trường chỉ viết đúng độ dài ghi dưới đây rồi đóng chuỗi ngay. Các trường ngắn viết liền một đoạn, không xuống dòng, không gạch đầu dòng. Không lặp ý giữa các trường.
- An toàn: không có nội dung tình dục hay gợi dục lộ liễu, không máu me tàn bạo, không cổ vũ tự làm hại bản thân; tuyệt đối không có gì tình dục liên quan tới người dưới 18 tuổi. Tình cảm, ghen tuông, chiếm hữu được phép nhưng kín đáo. Nếu ý tưởng đòi những điều bị cấm thì viết phiên bản an toàn của ý tưởng.

Các trường:
- name: họ tên đầy đủ của nhân vật, không kèm chức danh hay chú thích.
- gender: "male" (nam), "female" (nữ) hoặc "other".
- style_profile: chọn MỘT tên trong danh sách văn phong ở cuối, hợp nhất với bối cảnh của ý tưởng.
- role: vai trò hoặc thân phận ngắn hiện ngay dưới tên, 2-6 chữ, viết hoa chữ cái đầu, không có dấu chấm, không nhắc {{user}}, ví dụ "Chủ tiệm sách mùa thu", "Đại sư tỷ Thanh Vân Tông", "Kiến trúc sư ở Sài Gòn".
- description: 1-2 câu: tuổi, thân phận hoặc nghề, quan hệ với {{user}}.
- personality: 2-3 câu: tính cách chính, mâu thuẫn bên trong, đối xử với {{user}} khác với người ngoài thế nào.
- appearance: 1-2 câu: vài nét ngoại hình và cách ăn mặc dễ nhớ.
- background: 2-3 câu: quá khứ và hoàn cảnh hiện tại có liên quan đến câu chuyện.
- goals: 1 câu: điều nhân vật muốn.
- secrets: 1-2 câu: điều nhân vật giấu kín, có thể tạo kịch tính về sau.
- speech_style: 1-2 câu: giọng nói, cách dùng từ; nói với {{user}} khác gì so với nói với người khác.
- self_term: từ nhân vật tự xưng khi nói với {{user}}. Chỉ MỘT từ hoặc cụm, viết thường, ví dụ "ta", "tớ", "anh", "tôi". Không đưa nhiều lựa chọn, không dùng dấu "/".
- player_term: từ nhân vật gọi {{user}} khi nói chuyện. Chỉ MỘT từ hoặc cụm, viết thường, ví dụ "ngươi", "cậu", "em", "sư đệ". Không đưa nhiều lựa chọn, không dùng dấu "/".
- nicknames: 0-3 tên gọi thân mật mà nhân vật dùng để GỌI {{user}} (không phải danh xưng hay nghề của nhân vật), không dựa vào tên thật của người chơi (vì chưa biết tên), ví dụ "nhóc con", "tiểu sư muội". Không có thì để mảng rỗng.
- others: 1 câu: cách nhân vật xưng hô với người khác (người lạ, bề trên, bề dưới).
- scenario: 1-2 câu: bối cảnh lúc câu chuyện bắt đầu (nơi chốn, thời điểm, tình huống giữa nhân vật và {{user}}).
- greeting: lời mở đầu, theo luật riêng bên dưới.
- example_dialogues: đúng 3 dòng thoại mẫu thể hiện giọng nhân vật trong ba tình huống khác nhau, mỗi dòng dạng {{char}}: "..." (mở và đóng ngoặc kép), các dòng cách nhau bằng \\n. Chỉ có lời của nhân vật, không có lời của {{user}}. Dùng đúng self_term/player_term đã chọn.
- tags: 3-6 thẻ ngắn viết thường (thể loại, bối cảnh, kiểu nhân vật).

Luật cho greeting (quan trọng nhất):
- Là cảnh mở đầu câu chuyện, kể ở ngôi thứ ba, đúng văn phong của style profile đã chọn. Dài 120-180 từ, không tính Thought. Chia 5-8 đoạn ngắn, các đoạn cách nhau bằng một dòng trống (\\n\\n).
- Có đúng 2 dòng suy nghĩ thầm của nhân vật dạng [Thought: ...]. Mỗi dòng đứng riêng thành một đoạn, dài 2-3 câu, là điều nhân vật thật sự cảm thấy hoặc định làm nhưng không nói ra, không lặp lại điều vừa tả. Dòng thứ nhất đặt sau một hai đoạn đầu, dòng thứ hai ở khoảng giữa hoặc gần cuối; giữa hai Thought phải có ít nhất một đoạn dẫn truyện hoặc lời thoại. Không mở đầu và không kết thúc lời mở đầu bằng Thought. Luôn đóng ngoặc "]" ở cuối mỗi Thought.
- Xưng hô (self_term, player_term, nicknames) chỉ xuất hiện trong lời thoại (đặt trong ngoặc kép "...") và trong Thought. Phần dẫn truyện gọi nhân vật bằng tên hoặc bằng đại từ dẫn truyện của style profile (ghi trong danh sách ở cuối), gọi người chơi bằng {{user}}. Ví dụ đúng: {{user}} ngẩng lên. Hắn đặt chén trà xuống. Ví dụ sai: Sư đệ ngẩng lên. Ta đặt chén trà xuống.
- Người dẫn truyện không xưng "tôi", "ta", "tớ".
- Không viết lời thoại, hành động có chủ đích, suy nghĩ hay quyết định của {{user}}. Chỉ được tả {{user}} ở trạng thái nhìn thấy được lúc cảnh bắt đầu (đang ngồi, đang ngủ, vừa bước vào).
- Kết thúc ở chỗ {{user}} cần đáp lại: một câu hỏi, lời mời hay hành động của nhân vật hướng về {{user}}. Không kể tiếp phản ứng của {{user}}, không thêm câu tả nhân vật "chờ đợi câu trả lời".
- Viết tiếng Việt tự nhiên, câu rõ nghĩa như người Việt viết truyện. Tả bằng chi tiết cụ thể nhìn, nghe, chạm được (ánh mắt, giọng nói, động tác, đồ vật, ánh sáng, mùi); không so sánh hay ẩn dụ khoa trương. Không dùng các cụm sáo rỗng kiểu văn dịch: "bầu không khí", "không gian" (theo nghĩa bầu không khí), "sự im lặng kéo dài", "một sự ... bao trùm"; muốn tả im lặng thì tả việc nhân vật làm trong lúc đó.

Danh sách style profile:
"""

_EN_SYSTEM = """\
You are an editor helping the user write a character card for a text roleplay app. From a one-line idea, create a character with depth and consistency, with enough material for a long roleplay, then return exactly one JSON object that follows the schema.

General rules:
- Write every field in natural English, even if the idea is written in another language.
- The player is always called {{user}} (written exactly like that, with double curly braces). Never invent a name for the player. If the idea does not state the player's gender, write so that it works for a male or female player, and never use gendered pronouns (he, she, him, her) for {{user}}.
- Write the character's name directly; do not write {{char}} (except in example_dialogues). In every field, refer to the character with the chosen style profile's narration pronoun.
- Names of people, places, objects and food follow the culture of the setting: for a Chinese setting use Sino-Vietnamese readings with diacritics, exactly as the chosen style profile describes (e.g. Tạ Vân Lan, Lục Trần); for a Vietnamese setting use Vietnamese names; for a Western setting use Western names.
- Brevity is mandatory. Write each field at exactly the length given below, then close the string. Short fields are a single paragraph: no line breaks, no bullet points. Do not repeat information across fields.
- Safety: no sexual or explicitly suggestive content, no graphic gore, nothing that encourages self-harm; never anything sexual involving anyone under 18. Romance, jealousy and possessiveness are fine but non-explicit. If the idea asks for something prohibited, write a safe version of it.

Fields:
- name: the character's full name, without titles or notes.
- gender: "male", "female" or "other".
- style_profile: choose ONE name from the style profile list at the end that best fits the setting of the idea.
- role: a short title shown right under the name, 2-6 words, first letter capitalised, no full stop, never mentioning {{user}}, e.g. "Lighthouse keeper on the Cornish coast", "Night-shift nurse".
- description: 1-2 sentences: age, status or job, relationship with {{user}}.
- personality: 2-3 sentences: core traits, an inner conflict, how they treat {{user}} differently from others.
- appearance: 1-2 sentences: a few memorable features and how they dress.
- background: 2-3 sentences: the past and the present situation that matter to the story.
- goals: 1 sentence: what the character wants.
- secrets: 1-2 sentences: what the character hides, something that can create drama later.
- speech_style: 1-2 sentences: voice and word choice; how they talk to {{user}} versus others.
- self_term: how the character refers to themself when talking to {{user}}; normally "I". ONE word or phrase only, no alternatives, no "/".
- player_term: how the character addresses {{user}} in speech; normally "you". ONE word or phrase only, no alternatives, no "/".
- nicknames: 0-3 affectionate names the character uses to ADDRESS {{user}} (not the character's own titles or job), not based on the player's real name (it is unknown), e.g. "kid", "little junior sister". Use an empty array if none.
- others: 1 sentence: how the character addresses other people (strangers, superiors, subordinates).
- scenario: 1-2 sentences: the situation when the story begins (place, time, what is happening between the character and {{user}}).
- greeting: the opening scene, following the rules below.
- example_dialogues: exactly 3 sample lines showing the character's voice in three different situations, each line written as {{char}}: "..." (opening and closing quotes), separated by \\n. Only the character speaks; never write lines for {{user}}.
- tags: 3-6 short lowercase tags (genre, setting, character type).

Rules for greeting (most important):
- The opening scene of the story, told in the third person, in the voice of the chosen style profile. 120-180 words, not counting Thoughts. Split into 5-8 short paragraphs separated by a blank line (\\n\\n).
- Exactly 2 lines of the character's inner thoughts in the form [Thought: ...]. Each one is its own paragraph, 2-3 sentences long: what the character truly feels or plans but does not say aloud, not a repeat of what was just described. Put the first after the first one or two paragraphs and the second around the middle or near the end; at least one paragraph of narration or dialogue must separate them. Do not open or close the greeting with a Thought. Always close each Thought with "]".
- The narration refers to the character by name or by the style profile's narration pronoun (listed below) and to the player as {{user}}. "I" and "you" appear only inside quoted dialogue ("...") and inside Thoughts; the narrator never says "I".
- Never write {{user}}'s dialogue, deliberate actions, thoughts or decisions. Only describe {{user}} as visible at the start of the scene (sitting, asleep, just walking in).
- End where {{user}} has to respond: a question, an invitation or an action of the character directed at {{user}}. Do not narrate {{user}}'s reaction, and do not add a closing line about the character waiting for an answer.
- Write natural, clear prose. Use concrete details that can be seen, heard or touched (glances, voice, gestures, objects, light, smells); no overblown comparisons or metaphors, never describe "the atmosphere".

Style profiles:
"""


def _profile_line(p: StyleProfileInfo, language: Language) -> str:
    head = f"- {p.name}: {p.title.strip() or p.name}"
    if p.description.strip():
        head += f". {p.description.strip().rstrip('.')}."
    narration = p.narration.get(language, {})
    male, female = narration.get("male", "").strip(), narration.get("female", "").strip()
    parts = [head]
    if language == "vi":
        if male or female:
            parts.append(f'Dẫn truyện: nam "{male or "tên"}", nữ "{female or "tên"}".')
        pairs = [
            f'{ex.get("self", "").strip()}/{ex.get("player", "").strip()}'
            + (f' ({ex.get("note", "").strip()})' if ex.get("note", "").strip() else "")
            for ex in p.address_examples[:4]
            if ex.get("self", "").strip() and ex.get("player", "").strip()
        ]
        if pairs:
            parts.append("Xưng hô gợi ý: " + "; ".join(pairs) + ".")
    elif male or female:
        parts.append(f'Narration pronouns: male "{male or "name"}", female "{female or "name"}".')
    return " ".join(parts)


def build_draft_messages(
    *,
    idea: str,
    language: Language,
    gender: Gender | None,
    style_profile: str | None,
    styles: list[StyleProfileInfo],
) -> list[ChatTurn]:
    """Dựng [system, user] cho AI viết nháp. Khi người dùng đã chọn style thì chỉ liệt kê profile đó."""
    shown = [s for s in styles if s.name == style_profile] if style_profile else list(styles)
    profiles = "\n".join(_profile_line(p, language) for p in shown)
    if not profiles:
        profiles = (
            f'- {FALLBACK_STYLE}: trung tính, theo bối cảnh của ý tưởng.'
            if language == "vi"
            else f"- {FALLBACK_STYLE}: neutral, follows the setting of the idea."
        )

    if language == "vi":
        system = _VI_SYSTEM + profiles
        gender_vi = {"male": "nam", "female": "nữ", "other": "khác (phi nhị nguyên giới)"}
        lines = [f"Ý tưởng nhân vật: {idea}", "", "Yêu cầu bắt buộc:", "- Viết thẻ nhân vật bằng tiếng Việt."]
        if gender is not None:
            lines.append(f'- Giới tính nhân vật: {gender_vi[gender]} (gender = "{gender}").')
        if style_profile is not None:
            lines.append(f'- Style profile: {style_profile} (style_profile = "{style_profile}").')
        lines.append("- Lời mở đầu 120-180 từ, có đúng 2 dòng [Thought: ...] rải ở hai chỗ khác nhau.")
        lines.append("Trả về đúng một object JSON theo schema.")
    else:
        system = _EN_SYSTEM + profiles
        gender_en = {"male": "male", "female": "female", "other": "other (non-binary)"}
        lines = [f"Character idea: {idea}", "", "Requirements:", "- Write the card in English."]
        if gender is not None:
            lines.append(f'- Character gender: {gender_en[gender]} (gender = "{gender}").')
        if style_profile is not None:
            lines.append(f'- Style profile: {style_profile} (style_profile = "{style_profile}").')
        lines.append("- Greeting of 120-180 words with exactly 2 [Thought: ...] lines in two different places.")
        lines.append("Return exactly one JSON object that follows the schema.")
    return [ChatTurn(role="system", content=system), ChatTurn(role="user", content="\n".join(lines))]


# ---- hậu xử lý ------------------------------------------------------------------------------------

_USER_PLACEHOLDER = re.compile(r"\{\{\s*user\s*\}\}|\{\s*user\s*\}|<\s*user\s*>", re.I)
_CHAR_PLACEHOLDER = re.compile(r"\{\{\s*char\s*\}\}|\{\s*char\s*\}|<\s*char\s*>", re.I)
_THOUGHT_OPEN = re.compile(r"\[\s*(?:thought|suy\s+nghĩ)\s*:\s*", re.I)
_THOUGHT_BLOCK = re.compile(r"\[Thought:.*?\]", re.S)
_QUOTED = re.compile(r'"[^"\n]*"|“[^”\n]*”|«[^»\n]*»')
_TERM_CUT = re.compile(r"/|,|;|\(|\s+hoặc\s+|\s+or\s+", re.I)
_LIST_SPLIT = re.compile(r"/|,|;|\s+hoặc\s+|\s+or\s+", re.I)
_SENTENCE_END = re.compile(r"[.!?…][\"”’»)\]]*")
_STRIP_CHARS = " \t\n\"'“”‘’«».,:;!?-–—[]"


def _clean_text(value: str) -> str:
    """Trim, chuẩn hoá xuống dòng, placeholder; gộp >= 3 dòng trống thành 2."""
    text = value.replace("\r\n", "\n").replace("\r", "\n")
    if "\n" not in text and "\\n" in text:
        # Model escape hai lần: "\\n" thay vì xuống dòng thật.
        text = text.replace("\\n", "\n")
    text = _USER_PLACEHOLDER.sub("{{user}}", text)
    text = _CHAR_PLACEHOLDER.sub("{{char}}", text)
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _cut_to_sentence(text: str) -> str:
    """Cắt chuỗi bị đứt giữa chừng về hết câu cuối cùng (nếu còn đủ dài), không thì thêm dấu "…"."""
    last_end = None
    for m in _SENTENCE_END.finditer(text):
        last_end = m.end()
    if last_end is not None and last_end >= len(text) // 2:
        return text[:last_end].rstrip()
    return text.rstrip(" ,;:-–—") + "…"


def normalize_role(raw: str) -> tuple[str, bool]:
    """Vai trò ngắn: một dòng, bỏ ngoặc kép/dấu chấm cuối, viết hoa chữ đầu, tối đa MAX_ROLE_CHARS ký tự
    (cắt ở ranh giới từ). Trả (vai trò, đã phải cắt bớt hay không)."""
    text = _USER_PLACEHOLDER.sub("{{user}}", raw.replace("\\n", "\n"))
    lines = [line for line in text.split("\n") if line.strip()]
    text = lines[0] if lines else ""
    # Vai trò hiện nguyên văn trên thẻ, không thay placeholder: bỏ "{{user}}" (kèm "của"/"of" đứng trước).
    text = re.sub(r"\s*(?:\b(?:của|với|of|to|for)\s+)?\{\{user\}\}", "", text, flags=re.I)
    text = " ".join(text.split()).strip(" \t\"'“”‘’«».,:;!-–—")
    if not text:
        return "", False
    text = text[0].upper() + text[1:]
    if len(text) <= MAX_ROLE_CHARS:
        return text, False
    cut = text[:MAX_ROLE_CHARS]
    space = cut.rfind(" ")
    if space >= MAX_ROLE_CHARS // 2:
        cut = cut[:space]
    return cut.rstrip(" ,;:-–—"), True


def _is_title_case(text: str) -> bool:
    words = text.split()
    return len(words) > 1 and all(w[:1].isupper() for w in words)


def normalize_term(raw: str, language: Language) -> str:
    """Xưng hô: lấy lựa chọn đầu tiên (cắt ở "/", ",", " hoặc ", " or ", "("), bỏ ngoặc kép, viết thường chữ đầu
    (cả cụm nếu mọi chữ đều viết hoa đầu, ví dụ "Sư Tỷ"); giữ "I" của tiếng Anh."""
    text = _TERM_CUT.split(raw.strip(), maxsplit=1)[0]
    text = " ".join(text.strip(_STRIP_CHARS).split())
    if not text:
        return ""
    if language == "en" and (text == "I" or text.startswith("I ")):
        return text
    if _is_title_case(text):
        return text.lower()
    return text[0].lower() + text[1:]


def _normalize_list_item(raw: str) -> str:
    text = raw.split("(", 1)[0]
    return " ".join(text.strip(_STRIP_CHARS).split())


def _normalize_nicknames(raw: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        for part in _LIST_SPLIT.split(item):
            name = _USER_PLACEHOLDER.sub("{{user}}", _normalize_list_item(part))
            key = name.casefold()
            if name and key not in seen:
                seen.add(key)
                out.append(name)
    return out[:MAX_NICKNAMES]


def _normalize_tags(raw: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        for part in item.split(","):
            tag = " ".join(part.strip().lstrip("#").strip(_STRIP_CHARS).split()).lower()
            if tag and len(tag) <= MAX_TAG_CHARS and tag not in seen:
                seen.add(tag)
                out.append(tag)
    return out[:MAX_TAGS]


def fix_thoughts(greeting: str) -> tuple[str, int]:
    """Chuẩn hoá thẻ mở thành "[Thought: " và đóng ngoặc cho Thought thiếu "]".

    Thought thiếu "]" được đóng ở cuối đoạn của nó (trước dòng trống, hoặc trước thẻ Thought kế tiếp).
    Trả (văn bản đã sửa, số Thought đã phải đóng ngoặc).
    """
    text = _THOUGHT_OPEN.sub("[Thought: ", greeting)
    fixed = 0
    paragraphs = re.split(r"\n\s*\n", text)
    out: list[str] = []
    for para in paragraphs:
        starts = [m.start() for m in re.finditer(r"\[Thought: ", para)]
        if not starts:
            out.append(para)
            continue
        pieces = [para[: starts[0]]]
        bounds = starts + [len(para)]
        for i, start in enumerate(starts):
            seg = para[start : bounds[i + 1]]
            body = seg[len("[Thought: ") :]
            if "]" not in body:
                trailing = seg[len(seg.rstrip()) :]
                seg = seg.rstrip() + "]" + trailing
                fixed += 1
            pieces.append(seg)
        out.append("".join(pieces))
    return "\n\n".join(out), fixed


def _narration_only(greeting: str) -> str:
    """Phần dẫn truyện: bỏ Thought và lời thoại trong ngoặc kép."""
    text = _THOUGHT_BLOCK.sub(" ", greeting)
    return _QUOTED.sub(" ", text)


def _word_count(text: str) -> int:
    return len(re.findall(r"\w+(?:[-'’]\w+)*", text))


def _terms_in_narration(greeting: str, terms: list[str], allowed: set[str]) -> list[str]:
    narration = _narration_only(greeting)
    found: list[str] = []
    for term in terms:
        t = term.strip()
        if not t or t.casefold() in allowed or t.casefold() in {f.casefold() for f in found}:
            continue
        if re.search(rf"(?<!\w){re.escape(t)}(?!\w)", narration, flags=re.I):
            found.append(t)
    return found


_QUOTE_PAIRS = (('"', '"'), ("“", "”"))


def normalize_examples(text: str, name: str) -> str:
    """Ví dụ thoại: dòng mở bằng tên nhân vật -> "{{char}}:"; dòng thiếu ngoặc kép đóng thì thêm vào;
    bỏ dòng trống thừa giữa các dòng thoại."""
    lines: list[str] = []
    name_prefix = re.compile(rf"^\s*{re.escape(name)}\s*:", re.I) if name else None
    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            continue
        if name_prefix is not None:
            line = name_prefix.sub("{{char}}:", line, count=1)
        for open_q, close_q in _QUOTE_PAIRS:
            if open_q == close_q:
                if line.count(open_q) % 2 == 1:
                    line = line.rstrip() + close_q
            elif line.count(open_q) > line.count(close_q):
                line = line.rstrip() + close_q
        lines.append(line)
    return "\n".join(lines)


def _as_str(data: dict[str, Any], key: str, warnings: list[str]) -> str:
    value = data.get(key, "")
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, int | float):
        return str(value)
    warnings.append(f'Trường "{FIELD_LABELS.get(key, key)}" sai kiểu dữ liệu nên đã bỏ trống.')
    return ""


def _as_str_list(data: dict[str, Any], key: str) -> list[str]:
    value = data.get(key)
    if isinstance(value, str):
        return [value]
    if not isinstance(value, list):
        return []
    return [v for v in value if isinstance(v, str)]


def postprocess_draft(
    data: dict[str, Any],
    *,
    language: Language,
    gender: Gender | None,
    style_profile: str | None,
    styles: list[StyleProfileInfo],
    idea: str = "",
) -> tuple[CharacterCard, list[str]]:
    """Chuyển JSON model trả về thành CharacterCard chưa lưu + cảnh báo tiếng Việt."""
    warnings: list[str] = []
    style_names = [s.name for s in styles]

    # Các trường văn bản: trim, chuẩn hoá; chạm giới hạn ký tự -> cắt về hết câu + cảnh báo.
    texts: dict[str, str] = {}
    for key in ("name", *_TEXT_FIELDS):
        raw = _as_str(data, key, warnings)
        limit = FIELD_MAX_CHARS[key]
        value = _clean_text(raw)
        if len(value) >= limit:
            value = _cut_to_sentence(value[:limit]) if key != "name" else value
            warnings.append(f'Trường "{FIELD_LABELS[key]}" quá dài nên đã bị cắt bớt; hãy đọc lại.')
        texts[key] = value

    # Tên
    name = texts["name"].split("(", 1)[0]
    name = " ".join(name.strip(_STRIP_CHARS).split())[:MAX_NAME_CHARS].strip()
    if not name:
        warnings.append("Model không đặt tên cho nhân vật; hãy điền tên.")

    # Vai trò (thiếu thì để trống, người dùng tự điền)
    role, role_cut = normalize_role(_as_str(data, "role", warnings))
    if role_cut:
        warnings.append(f'Trường "{FIELD_LABELS["role"]}" quá dài nên đã bị cắt bớt; hãy đọc lại.')

    # Giới tính
    raw_gender = data.get("gender")
    if gender is not None:
        final_gender: Gender = gender
    elif isinstance(raw_gender, str) and raw_gender.strip().lower() in _GENDERS:
        final_gender = raw_gender.strip().lower()  # type: ignore[assignment]
    else:
        final_gender = "other"
        warnings.append('Model không chọn được giới tính hợp lệ; đã đặt "khác", hãy chọn lại.')

    # Style profile
    raw_style = data.get("style_profile")
    raw_style = raw_style.strip() if isinstance(raw_style, str) else ""
    if style_profile is not None:
        final_style = style_profile
    elif raw_style in style_names:
        final_style = raw_style
    else:
        final_style = FALLBACK_STYLE if (FALLBACK_STYLE in style_names or not style_names) else style_names[0]
        warnings.append(
            f'Model chọn style profile không có sẵn ("{raw_style or "trống"}"); đã đặt "{final_style}", hãy chọn lại.'
        )

    # Xưng hô
    terms: dict[str, str] = {}
    for key in ("self_term", "player_term"):
        raw = _as_str(data, key, warnings).strip()
        term = normalize_term(raw, language)
        if term and _TERM_CUT.search(raw.strip(_STRIP_CHARS)):
            warnings.append(
                f'Model đưa nhiều lựa chọn cho "{FIELD_LABELS[key]}" ("{raw}"); đã chọn "{term}", '
                "hãy kiểm tra cho hợp với giới tính người chơi."
            )
        if not term:
            if language == "en":
                term = "I" if key == "self_term" else "you"
            else:
                warnings.append(f'Chưa có "{FIELD_LABELS[key]}"; hãy điền xưng hô.')
        terms[key] = term
    nicknames = [
        n
        for n in _normalize_nicknames(_as_str_list(data, "nicknames"))
        if n != "{{user}}" and n.casefold() != terms["player_term"].casefold()
    ]
    tags = _normalize_tags(_as_str_list(data, "tags"))

    # Lời mở đầu
    greeting, fixed = fix_thoughts(texts["greeting"])
    if fixed:
        warnings.append("Đã tự thêm dấu \"]\" cho dòng Thought bị thiếu trong lời mở đầu; hãy kiểm tra.")
    if not greeting:
        warnings.append("Model không viết lời mở đầu; hãy tự viết thêm.")
    else:
        n_thoughts = len(_THOUGHT_BLOCK.findall(greeting))
        if n_thoughts == 0:
            warnings.append("Lời mở đầu không có dòng [Thought: ...] nào; nên thêm 2 dòng suy nghĩ thầm.")
        elif n_thoughts != 2:
            warnings.append(f"Lời mở đầu có {n_thoughts} dòng Thought (nên có 2).")
        words = _word_count(_THOUGHT_BLOCK.sub(" ", greeting))
        if words < 80 or words > 260:
            warnings.append(f"Lời mở đầu dài {words} từ (nên khoảng 120-180 từ, không tính Thought).")
        if "{{user}}" not in greeting:
            warnings.append("Lời mở đầu không nhắc tới {{user}} (người chơi); hãy kiểm tra.")
        if re.search(r"bầu\s+không\s+khí|the\s+atmosphere", greeting, flags=re.I):
            warnings.append('Lời mở đầu có tả "bầu không khí"; nên thay bằng chi tiết cụ thể.')
        profile = next((s for s in styles if s.name == final_style), None)
        allowed = {
            v.strip().casefold()
            for v in (profile.narration.get(language, {}).values() if profile else [])
            if isinstance(v, str) and v.strip()
        }
        leaked = _terms_in_narration(greeting, [terms["self_term"], terms["player_term"]], allowed)
        if leaked:
            listed = ", ".join(f'"{t}"' for t in leaked)
            warnings.append(
                f"Lời mở đầu dùng xưng hô trong dẫn truyện ({listed}); xưng hô chỉ nên nằm trong lời thoại "
                "và Thought, hãy sửa lại."
            )

    card = CharacterCard(
        id=None,
        name=name,
        role=role,
        gender=final_gender,
        language=language,
        description=texts["description"],
        personality=texts["personality"],
        appearance=texts["appearance"],
        background=texts["background"],
        goals=texts["goals"],
        secrets=texts["secrets"],
        speech_style=texts["speech_style"],
        style_profile=final_style,
        address_terms=AddressTerms(
            self_term=terms["self_term"],
            player_term=terms["player_term"],
            nicknames=nicknames,
            others=texts["others"],
        ),
        greeting=greeting,
        example_dialogues=normalize_examples(texts["example_dialogues"], name),
        tags=tags,
        scenario=texts["scenario"],
        creator_notes=f"AI viết nháp từ ý tưởng: {idea}" if idea else "",
    )
    return card, warnings


# ---- điểm vào -------------------------------------------------------------------------------------


async def draft_card(
    llm: LLMClient,
    model: str,
    *,
    idea: str,
    language: Language,
    gender: Gender | None,
    style_profile: str | None,
    styles: list[StyleProfileInfo],
) -> tuple[CharacterCard, list[str]]:
    """Gọi model viết nháp card từ ý tưởng. DraftError khi đầu vào sai; LLMError lan ra từ client."""
    idea = (idea or "").strip()
    if not idea:
        raise DraftError("Hãy nhập ý tưởng cho nhân vật.")
    if len(idea) > MAX_IDEA_CHARS:
        raise DraftError(f"Ý tưởng quá dài ({len(idea)} ký tự); tối đa {MAX_IDEA_CHARS} ký tự.")
    if language not in ("vi", "en"):
        raise DraftError("Ngôn ngữ không hợp lệ (chỉ hỗ trợ tiếng Việt hoặc tiếng Anh).")
    if gender is not None and gender not in _GENDERS:
        raise DraftError("Giới tính không hợp lệ.")
    style_names = [s.name for s in styles]
    if style_profile is not None:
        style_profile = style_profile.strip() or None
    if style_profile is not None and style_profile not in style_names:
        raise DraftError(f'Không có style profile "{style_profile}".')

    messages = build_draft_messages(
        idea=idea, language=language, gender=gender, style_profile=style_profile, styles=styles
    )
    schema = draft_schema(style_names, gender=gender, style_profile=style_profile)
    data = await llm.chat_json(model, messages, schema=schema, options=dict(DRAFT_OPTIONS))
    return postprocess_draft(
        data, language=language, gender=gender, style_profile=style_profile, styles=styles, idea=idea
    )
