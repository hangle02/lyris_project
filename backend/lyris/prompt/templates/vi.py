"""Văn bản prompt tiếng Việt.

Khối A bám sát nguyên văn `systems.vi_story` / `systems.vi_dm` trong `harness/prompts.json`
(bản `vi_story` đạt 0/15 lỗi với gemma4:12b), chỉ thay tên, giới tính, kiểu quan hệ, ngôi kể,
đại từ dẫn truyện và xưng hô bằng tham số. Khác biệt có chủ ý: chỉ đạo của người chơi không
còn được gọi là "((...))" (builder đã tách chúng ra và đưa vào ghi chú cuối lượt, nên prompt
không bao giờ chứa "((" và model không có mẫu nào để in lại).

Luật Thought và độ dài đã đổi có chủ ý so với prompts.json (bản Phase 0 chỉ có "đúng một Thought"):
giờ theo `story.thought_style` (inline: 2-3 Thought rải giữa truyện; end: một Thought ở cuối), và có
thêm luật viết tiếng Việt tự nhiên. prompts.json giữ nguyên làm mốc của bake-off Phase 0.
"""
from __future__ import annotations

from collections.abc import Sequence

from lyris.models import Gender, RelationshipType, SceneState
from lyris.prompt.templates import PromptContext, lead_in, quoted, scene_text, sentence, unique

GENDER: dict[Gender, str] = {
    "male": "nam",
    "female": "nữ",
    "other": "người phi nhị nguyên giới",
}

RELATIONSHIP: dict[RelationshipType, str] = {
    "het": "nam - nữ (ngôn tình)",
    "bl": "nam - nam (đam mỹ)",
    "gl": "nữ - nữ (bách hợp)",
    "none": "không lãng mạn (không phát triển thành tình cảm yêu đương)",
}


def _pronoun_or_name(pronoun: str, name: str) -> str:
    pronoun = pronoun.strip()
    if not pronoun or pronoun.casefold() == name.casefold():
        return f'"{name}"'
    return f'"{pronoun}" hoặc "{name}"'


def _thought_rule(ctx: PromptContext) -> str:
    """Luật đặt suy nghĩ thầm theo `story.thought_style` (khối A)."""
    c = ctx.char
    if ctx.story.thought_style == "end":
        return (
            f"- Kết thúc lượt bằng đúng một dòng suy nghĩ thầm của {c} theo dạng [Thought: ...], dài 2-4 câu: "
            f"điều {c} thật sự cảm thấy, lo lắng hay định làm nhưng không nói ra."
        )
    return (
        f"- Suy nghĩ thầm của {c} viết theo dạng [Thought: ...], lồng vào giữa truyện: 2-3 dòng Thought mỗi lượt, "
        "mỗi dòng đứng riêng thành một đoạn, đặt ngay sau hành động hoặc lời nói khơi ra suy nghĩ đó. "
        "Rải các Thought ở những chỗ khác nhau trong lượt (đầu, giữa, cuối), không đặt hai Thought liền nhau. "
        f"Mỗi Thought 2-3 câu, là điều {c} thật sự cảm thấy hay định làm nhưng không nói ra, "
        "không lặp lại điều vừa tả."
    )


def _thought_reminder(ctx: PromptContext) -> str:
    """Nhắc lại luật Thought ở ghi chú cuối lượt (khối F)."""
    c = ctx.char
    if ctx.story.thought_style == "end":
        return f"Kết thúc bằng đúng một dòng [Thought: ...] của {c}, 2-4 câu."
    return (
        f"2-3 dòng [Thought: ...] của {c} rải ở các chỗ khác nhau trong truyện, không đặt hai Thought liền nhau, "
        "mỗi dòng 2-3 câu, đứng riêng một đoạn."
    )


NATURAL_VIETNAMESE = (
    "- Viết tiếng Việt tự nhiên, câu rõ nghĩa như người Việt viết truyện. Tả bằng chi tiết cụ thể nhìn, nghe, "
    "chạm được (sắc mặt, ánh mắt, giọng nói, động tác, đồ vật); không so sánh hay ẩn dụ khoa trương, không ghép "
    'chữ gượng hay dịch sát từng chữ. Tả con người, không tả "bầu không khí" (không viết bầu không khí '
    'đặc quánh, hạ xuống, đông cứng...). Ví dụ viết "Anh không nói gì, sắc mặt lạnh đi." thay vì so sánh '
    "không khí quanh anh với băng giá."
)


def _dialogue_only_words(ctx: PromptContext) -> str:
    """Câu cấm dùng từ xưng hô của lời thoại trong phần dẫn truyện (rỗng nếu không có từ nào cần cấm)."""
    np_ = ctx.story.narration_pronouns
    at = ctx.card.address_terms
    words = unique([at.self_term, at.player_term], exclude=[np_.character, np_.player])
    if not words:
        return ""
    this = {1: "từ này", 2: "hai từ này"}.get(len(words), "các từ này")
    listed = ", ".join(f'"{w}"' for w in words)
    return f" Không dùng {listed} trong phần dẫn truyện; {this} chỉ xuất hiện trong lời thoại và Thought."


class ViTemplate:
    story_start = "(Câu chuyện bắt đầu.)"
    story_continues = "(Câu chuyện tiếp tục.)"
    empty_user_turn = "(Lượt này người chơi không viết gì.)"
    dm_label = "[Tin nhắn điện thoại]"

    # ---- Khối A -------------------------------------------------------------------------

    def rules(self, ctx: PromptContext) -> str:
        return self._story_rules(ctx) if ctx.story.mode == "story" else self._dm_rules(ctx)

    def _common_setup(self, ctx: PromptContext) -> list[str]:
        c, p = ctx.char, ctx.player
        return [
            f"- Giới tính: {c} là {GENDER[ctx.card.gender]}, {p} là {GENDER[ctx.persona.gender]}.",
            f"- Kiểu quan hệ: {RELATIONSHIP[ctx.story.relationship_type]}.",
        ]

    def _story_rules(self, ctx: PromptContext) -> str:
        c, p = ctx.char, ctx.player
        np_ = ctx.story.narration_pronouns
        forbidden = _dialogue_only_words(ctx)
        if ctx.story.pov == "first":
            intro = (
                f"Bạn đóng vai nhân vật {c} và kể một câu chuyện tương tác bằng tiếng Việt "
                f"ở ngôi thứ nhất, qua lời của {c}."
            )
            pov_lines = [
                f"- Ngôi kể: ngôi thứ nhất. {c} là người kể chuyện, không có người dẫn truyện đứng ngoài.",
                f'- Đại từ khi dẫn truyện: {c} tự gọi mình là "{np_.character.strip()}", '
                f"gọi {p} là {_pronoun_or_name(np_.player, p)}.{forbidden}",
            ]
        else:
            intro = f"Bạn là người dẫn truyện và đóng vai nhân vật {c} trong một câu chuyện tương tác bằng tiếng Việt."
            narrator_self = unique(
                ["tôi", ctx.card.address_terms.self_term], exclude=[np_.character, np_.player]
            )
            no_self = ", ".join(f'không xưng "{w}"' for w in narrator_self)
            pov_lines = [
                "- Ngôi kể: ngôi thứ ba. Người dẫn truyện đứng ngoài"
                + (f", {no_self}." if no_self else "."),
                f"- Đại từ khi dẫn truyện: gọi {c} là {_pronoun_or_name(np_.character, c)}, "
                f"gọi {p} là {_pronoun_or_name(np_.player, p)}.{forbidden}",
            ]
        player_pronoun = np_.player.strip() or p
        setup = [
            "Thiết lập câu chuyện:",
            *self._common_setup(ctx),
            *pov_lines,
            "- Văn phong, xưng hô và bối cảnh: theo các phần bên dưới.",
        ]
        rules = [
            "Luật:",
            f"- Viết kiểu tiểu thuyết: mô tả hành động, bối cảnh và lời thoại của {c}.",
            "- Lượt của người chơi là sự thật của câu chuyện: tiếp nối trực tiếp từ đúng hành động, "
            "lời nói và hoàn cảnh người chơi vừa viết, không bỏ qua, không tự đổi cảnh hay lái sang chuyện khác.",
            f"- Người chơi là tác giả: nếu người chơi viết hành động cho {c}, hoặc đưa chỉ đạo trong ghi chú "
            f"cuối lượt, hãy làm theo, nhưng giữ giọng và tính cách {c}. Không nhắc lại chỉ đạo trong truyện.",
            _thought_rule(ctx),
            NATURAL_VIETNAMESE,
            f"- {p} do người chơi điều khiển. Được phép: phản ứng với lời nói, hành động, trạng thái mà "
            f"người chơi đã viết, và mô tả lại chúng qua mắt {c} (ví dụ người chơi viết \"run rẩy\" thì "
            f"{c} nhận ra vai {player_pronoun} đang run).",
            f"- Mô tả lại không có nghĩa là kể lại: không chép lại lời thoại của {p}, không kể lại từng hành động "
            f"{p} vừa viết; mở đầu lượt bằng phản ứng của {c}.",
            f"- Được tả thêm trạng thái nhỏ của {p} mà {c} nhìn thấy hoặc cảm nhận được, miễn hợp với những "
            "gì người chơi viết (ví dụ má ửng đỏ, chóp mũi đỏ vì lạnh, bàn tay lạnh ngắt).",
            f"- Không được: viết lời thoại, hành động có chủ đích, suy nghĩ hay quyết định mới cho {p}. "
            f"Dừng lượt ở chỗ cần {p} đáp lại.",
            "- Chỉ dùng tiếng Việt. Phần dẫn truyện và lời thoại dài khoảng 120-200 từ, không tính Thought.",
        ]
        return "\n\n".join([intro, "\n".join(setup), "\n".join(rules)])

    def _dm_rules(self, ctx: PromptContext) -> str:
        c, p = ctx.char, ctx.player
        intro = f"Bạn đóng vai {c} đang nhắn tin với {p} bằng tiếng Việt."
        setup = [
            "Thiết lập câu chuyện:",
            *self._common_setup(ctx),
            "- Văn phong, xưng hô và bối cảnh: theo các phần bên dưới.",
        ]
        rules = [
            "Luật:",
            "- Trả lời như tin nhắn thật: 1-3 câu ngắn, có thể tách thành 2-3 tin, mỗi tin một dòng. "
            "Không mô tả hành động, không dẫn truyện, không có dòng [Thought: ...].",
            "- Trả lời đúng vào tin nhắn người chơi vừa gửi. Nếu người chơi đưa chỉ đạo trong ghi chú cuối "
            "lượt, làm theo nhưng không nhắc lại phần đó.",
            f"- Bám vào chi tiết cụ thể trong tin {p} vừa gửi: trêu lại, hỏi lại, kể chuyện của {c}, "
            "để mỗi lượt là một ý mới. Độ dài thay đổi theo tin của người chơi, có lúc chỉ một tin.",
            "- Không kết tin bằng lời dặn dò hay chúc (ngủ sớm, nghỉ ngơi, đừng thức khuya, ăn uống đầy đủ...) "
            f"trừ khi {p} vừa nói sắp đi ngủ hoặc chào tạm biệt. Không lặp lại câu hay ý đã nhắn ở các tin trước.",
            f"- Không viết tin nhắn thay {p}.",
            "- Chỉ dùng tiếng Việt.",
        ]
        return "\n\n".join([intro, "\n".join(setup), "\n".join(rules)])

    # ---- Khối B -------------------------------------------------------------------------

    def character(self, ctx: PromptContext) -> str:
        card, c, p = ctx.card, ctx.char, ctx.player
        char_lines = [lead_in(f"Nhân vật: {c}, {GENDER[card.gender]}", ctx.fill(card.description))]
        labelled = [
            ("Tính cách", card.personality),
            ("Ngoại hình", card.appearance),
            ("Hoàn cảnh", card.background),
            ("Mục tiêu", card.goals),
            (f"Bí mật ({p} chưa biết; chỉ hé lộ dần qua hành động và Thought, không nói thẳng ra)", card.secrets),
            ("Cách nói", card.speech_style),
        ]
        char_lines += [f"{label}: {sentence(ctx.fill(value))}" for label, value in labelled if value.strip()]
        persona_line = lead_in(f"Người chơi: {p}, {GENDER[ctx.persona.gender]}", ctx.fill(ctx.persona.description))

        parts = ["\n".join(char_lines) + "\n" + persona_line]

        at = card.address_terms
        address: list[str] = []
        if at.self_term.strip() or at.player_term.strip():
            pieces: list[str] = []
            if at.self_term.strip():
                pieces.append(f'{c} tự xưng "{at.self_term.strip()}"')
            if at.player_term.strip():
                pieces.append(f'gọi {p} là "{at.player_term.strip()}"')
            line = "- " + ", ".join(pieces)
            nicknames = unique(at.nicknames)
            if nicknames:
                line += f"; lúc thân mật hoặc dỗ dành có thể gọi {quoted(nicknames, 'hoặc')}"
            address.append(sentence(line))
        elif unique(at.nicknames):
            address.append(f"- Lúc thân mật hoặc dỗ dành, {c} có thể gọi {p} là {quoted(unique(at.nicknames), 'hoặc')}.")
        if at.others.strip():
            address.append(f"- Với người khác: {sentence(ctx.fill(at.others))}")
        if address:
            parts.append("Xưng hô (chỉ dùng trong lời thoại và Thought):\n" + "\n".join(address))

        if ctx.style.strip():
            parts.append(ctx.style.strip())
        if card.example_dialogues.strip():
            parts.append(
                "Ví dụ lời thoại (chỉ để tham khảo giọng nói, không chép lại):\n" + ctx.fill(card.example_dialogues)
            )
        return "\n\n".join(parts)

    # ---- Khối C -------------------------------------------------------------------------

    def context(self, ctx: PromptContext, *, summary: str | None = None) -> str:
        lines: list[str] = []
        if ctx.story.scenario.strip():
            lines.append(f"Bối cảnh: {ctx.fill(ctx.story.scenario)}")
        if ctx.story.scene_summary.strip():
            lines.append(f"Tóm tắt những gì đã xảy ra: {ctx.fill(ctx.story.scene_summary)}")
        if summary and summary.strip():
            lines.append(f"Những gì đã xảy ra trước đó: {summary.strip()}")
        return "\n\n".join(lines)

    # ---- Khối F -------------------------------------------------------------------------

    def state_lines(
        self,
        ctx: PromptContext,
        *,
        scene: SceneState | None,
        directive: str | None,
        memories: Sequence[str],
        facts: Sequence[str],
    ) -> list[str]:
        c = ctx.char
        lines: list[str] = []
        where = scene_text(scene)
        if where:
            lines.append(f"- Cảnh hiện tại: {sentence(where)}")
        if directive and directive.strip():
            lines.append(f"- Thái độ của {c} lúc này: {sentence(directive)}")
        if memories:
            lines.append(f"- Chuyện cũ {c} còn nhớ (chỉ nhắc khi hợp cảnh, không kể lại nguyên văn):")
            lines.extend(f"  + {sentence(m)}" for m in memories)
        if facts:
            lines.append(f"- Điều {c} biết:")
            lines.extend(f"  + {sentence(f)}" for f in facts)
        return lines

    def dm_note(self, ctx: PromptContext) -> str:
        c, p = ctx.char, ctx.player
        return (
            f"- Lượt có nhãn {self.dm_label} là tin nhắn {c} và {p} đã gửi nhau qua điện thoại: chuyện đã xảy ra, "
            f"{c} nhớ và biết mọi điều trong đó (tên, lời hẹn, chuyện đã kể). Lượt này vẫn là dẫn truyện, "
            "không mở đầu bằng nhãn ấy."
        )

    def final_note(
        self,
        ctx: PromptContext,
        *,
        directive: str | None,
        player_wrote: bool,
        avoid: Sequence[str] = (),
        state: Sequence[str] = (),
    ) -> str:
        c, p = ctx.char, ctx.player
        np_ = ctx.story.narration_pronouns
        if ctx.story.mode == "dm":
            lines = [f"[Ghi chú cho người viết, không phải tin nhắn của {p}]", *state]
            if player_wrote:
                lines.append(
                    f"- Trả lời đúng vào tin nhắn {p} vừa gửi: 1-3 câu ngắn (có thể tách thành vài tin, mỗi tin một dòng), chỉ có nội dung tin nhắn, "
                    "không mô tả hành động, không [Thought: ...]."
                )
            else:
                lines.append(
                    f"- Lượt này {p} không nhắn gì thêm; {c} nhắn tiếp: 1-3 câu ngắn (có thể tách thành vài tin, mỗi tin một dòng), chỉ có nội dung tin nhắn, "
                    "không mô tả hành động, không [Thought: ...]."
                )
            if directive:
                lines.append(
                    f"- Chỉ đạo của người chơi cho lượt này: {sentence(directive)} "
                    "Làm theo nhưng không nhắc lại chỉ đạo này trong tin nhắn."
                )
            if avoid:
                listed = "; ".join(f"«{a}»" for a in avoid)
                lines.append(
                    f"- Các tin gần đây {c} đã kết bằng: {listed}. Lần này không lặp lại những câu hay ý đó, "
                    "không kết bằng lời dặn dò."
                )
            return "\n".join(lines)

        lines = [f"[Ghi chú cho người dẫn truyện, không phải lời của {p}]", *state]
        if player_wrote:
            lines.append(
                f"- Tiếp nối trực tiếp từ đúng lời nói, hành động của {p} vừa viết ở trên; không bỏ qua, "
                f"không đổi cảnh. Không chép lại lời {p} vừa nói; không thêm lời thoại, hành động có chủ đích, "
                f"suy nghĩ hay cảm xúc mới cho {p}. Dừng ở chỗ cần {p} đáp lại."
            )
        else:
            lines.append(
                f"- Lượt này {p} không nói hay làm gì thêm; tiếp nối từ cảnh hiện tại. Dừng ở chỗ cần {p} đáp lại."
            )
        if directive:
            lines.append(
                f"- Chỉ đạo của người chơi cho lượt này: {sentence(directive)} "
                "Làm theo nhưng không in lại chỉ đạo này trong truyện."
            )
        if avoid:
            listed = "; ".join(f"«{a}»" for a in avoid)
            lines.append(
                f"- Các lượt gần đây mở đầu bằng: {listed}. Lượt này mở đầu theo cách khác "
                "(ví dụ bằng lời nói, một âm thanh hay một chi tiết của cảnh), không lặp lại câu hay chi tiết đã tả."
            )
        if ctx.story.pov == "first":
            pron = (
                f'{c} kể ở ngôi thứ nhất, tự gọi mình là "{np_.character.strip()}", '
                f"gọi {p} là {_pronoun_or_name(np_.player, p)}."
            )
        else:
            pron = (
                f"Dẫn truyện gọi {c} là {_pronoun_or_name(np_.character, c)}, "
                f"{p} là {_pronoun_or_name(np_.player, p)}."
            )
        lines.append(
            f"- {_thought_reminder(ctx)} {pron} Câu văn tự nhiên, tả cụ thể. "
            "Dẫn truyện và lời thoại khoảng 120-200 từ, không quá 200 từ."
        )
        return "\n".join(lines)

    # ---- Khối D (Phase 4): thông tin thế giới, đầu message user cuối ------------------------

    def lore_header(self, ctx: PromptContext) -> str:
        c, p = ctx.char, ctx.player
        who = f"người viết, không phải tin nhắn của {p}" if ctx.story.mode == "dm" else (
            f"người dẫn truyện, không phải lời của {p}"
        )
        return (
            f"[Thông tin thế giới cho {who}. {c} biết những điều này; chỉ dùng khi hợp cảnh, "
            "không kể lại nguyên văn.]"
        )

    def lore_item(self, ctx: PromptContext, title: str, text: str, private: bool) -> str:
        if private:
            note = f" (chuyện riêng của {ctx.char}, chưa kể với ai; không tự nói ra nếu không có lý do)"
            return f"- {title}{note}: {text}"
        return f"- {title}: {text}"

    def lore_footer(self, ctx: PromptContext) -> str:
        return "[Hết thông tin thế giới.]"


TEMPLATE = ViTemplate()
