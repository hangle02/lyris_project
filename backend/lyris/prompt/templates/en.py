"""English prompt text.

Block A follows `systems.en_story` in `harness/prompts.json` verbatim, parameterized by names,
genders, relationship type, point of view and narration pronouns. The DM template mirrors
`systems.vi_dm`. As in vi.py, the player's directions are never called "((...))": the builder
moves them into the closing note, so the prompt never contains "((".

The Thought and length rules intentionally differ from prompts.json (the Phase 0 baseline with
"exactly one Thought"): they follow `story.thought_style` now (inline: 2-3 Thoughts spread through
the reply; end: one at the end), plus a plain-prose rule.
"""
from __future__ import annotations

from collections.abc import Sequence

from lyris.models import Gender, RelationshipType, SceneState
from lyris.prompt.templates import PromptContext, lead_in, quoted, scene_text, sentence, unique

GENDER: dict[Gender, str] = {"male": "male", "female": "female", "other": "non-binary"}

RELATIONSHIP: dict[RelationshipType, str] = {
    "het": "male - female romance",
    "bl": "male - male romance (danmei)",
    "gl": "female - female romance (baihe)",
    "none": "platonic, no romance",
}

# Narration pronouns are stored per story; a story switched from Vietnamese may still hold
# "anh"/"cô". Only accept values that are English pronouns, otherwise derive from gender.
_ENGLISH_PRONOUNS = {"he", "she", "they", "i", "it", "xe", "ze", "we"}
_DEFAULT_PRONOUN: dict[Gender, str] = {"male": "he", "female": "she", "other": "they"}


def _third_person(value: str, gender: Gender) -> str:
    v = value.strip()
    if v.casefold() in _ENGLISH_PRONOUNS and v.casefold() not in {"i", "we"}:
        return v.lower()
    return _DEFAULT_PRONOUN[gender]


def _first_person(value: str) -> str:
    return "we" if value.strip().casefold() == "we" else "I"



def _thought_rule(ctx: PromptContext) -> str:
    """Where the inner monologue goes, by `story.thought_style` (block A)."""
    c = ctx.char
    if ctx.story.thought_style == "end":
        return (
            f"- End the turn with exactly one line of {c}'s inner monologue in the form [Thought: ...], "
            f"2-4 sentences: what {c} really feels, fears or intends but does not say."
        )
    return (
        f"- Write {c}'s inner monologue as [Thought: ...] lines woven into the story: 2-3 Thought lines per turn, "
        "each on its own paragraph, placed right after the action or words that trigger it. "
        "Spread them through the turn (beginning, middle, end); never put two Thought lines in a row. "
        f"Each Thought is 2-3 sentences of what {c} really feels or intends but does not say, "
        "without repeating what was just described."
    )


def _thought_reminder(ctx: PromptContext) -> str:
    c = ctx.char
    if ctx.story.thought_style == "end":
        return f"End with exactly one [Thought: ...] line for {c}, 2-4 sentences."
    return (
        f"2-3 [Thought: ...] lines for {c} spread through the story, never two in a row, "
        "2-3 sentences each, each on its own paragraph."
    )


NATURAL_ENGLISH = (
    "- Write plain, natural prose. Describe concrete things that can be seen, heard or touched (expression, "
    "gaze, voice, gestures, objects); no overblown similes or metaphors, no purple prose. Describe people, "
    "not \"the atmosphere\" (no thickening, freezing or heavy air)."
)


class EnTemplate:
    story_start = "(The story begins.)"
    story_continues = "(The story continues.)"
    empty_user_turn = "(The player wrote nothing this turn.)"
    dm_label = "[Text message]"

    # ---- Block A ------------------------------------------------------------------------

    def rules(self, ctx: PromptContext) -> str:
        return self._story_rules(ctx) if ctx.story.mode == "story" else self._dm_rules(ctx)

    def _common_setup(self, ctx: PromptContext) -> list[str]:
        c, p = ctx.char, ctx.player
        return [
            f"- Genders: {c} is {GENDER[ctx.card.gender]}, {p} is {GENDER[ctx.persona.gender]}.",
            f"- Relationship type: {RELATIONSHIP[ctx.story.relationship_type]}.",
        ]

    def _pov_line(self, ctx: PromptContext) -> str:
        c, p = ctx.char, ctx.player
        np_ = ctx.story.narration_pronouns
        her = _third_person(np_.player, ctx.persona.gender)
        if ctx.story.pov == "first":
            me = _first_person(np_.character)
            return (
                f'- Point of view: first person. {c} narrates the story as "{me}". '
                f'Refer to {p} as "{her}" or by name in narration.'
            )
        him = _third_person(np_.character, ctx.card.gender)
        return (
            f'- Point of view: third person. Refer to {c} as "{him}" and {p} as "{her}" in narration. '
            'The narrator never refers to itself as "I".'
        )

    def _story_rules(self, ctx: PromptContext) -> str:
        c, p = ctx.char, ctx.player
        intro = f"You are the narrator and play the character {c} in an interactive story in English."
        if ctx.story.pov == "first":
            intro = f"You play the character {c} and tell an interactive story in English in the first person, as {c}."
        setup = [
            "Story setup:",
            *self._common_setup(ctx),
            self._pov_line(ctx),
            "- Setting, style and forms of address: follow the sections below.",
        ]
        rules = [
            "Rules:",
            f"- Write in novel style: {c}'s actions, the setting and {c}'s dialogue.",
            "- The player's turn is canon: continue directly from exactly what the player just wrote. "
            "Do not ignore it, change the scene or drift to another topic.",
            f"- The player is the author: if the player writes actions for {c}, or gives directions in the note "
            f"at the end of their turn, follow them while keeping {c}'s voice. Never repeat the directions in the story.",
            _thought_rule(ctx),
            NATURAL_ENGLISH,
            f"- {p} is controlled by the player. You may react to the words, actions and states the player wrote, "
            f"and describe them through {c}'s eyes.",
            f"- Reacting is not retelling: never copy {p}'s dialogue or restate the actions {p} just wrote; "
            f"open the turn with {c}'s reaction.",
            f"- You may add small physical details of {p} that {c} can see or feel, as long as they fit what the "
            "player wrote (a blush, a nose red from the cold, cold hands).",
            f"- Never write new dialogue, deliberate actions, thoughts or decisions for {p}. "
            f"End the turn where {p} needs to respond.",
            "- English only. Narration and dialogue about 120-200 words, not counting Thought lines.",
        ]
        return "\n\n".join([intro, "\n".join(setup), "\n".join(rules)])

    def _dm_rules(self, ctx: PromptContext) -> str:
        c, p = ctx.char, ctx.player
        intro = f"You play {c}, texting {p} in English."
        setup = [
            "Story setup:",
            *self._common_setup(ctx),
            "- Setting, style and forms of address: follow the sections below.",
        ]
        rules = [
            "Rules:",
            "- Reply like a real text message: 1-3 short sentences, optionally split into 2-3 texts, one per line. "
            "No action descriptions, no narration, no [Thought: ...] line.",
            "- Reply directly to the message the player just sent. If the player gives directions in the note at "
            "the end of their turn, follow them but never repeat that part.",
            f"- Pick up a concrete detail from what {p} just sent: tease back, ask back, share something of "
            f"{c}'s own, so every turn adds something new. Vary the length; sometimes a single text is enough.",
            "- Do not end with advice or well-wishes (sleep early, get some rest, eat properly...) unless "
            f"{p} just said goodnight or goodbye. Never repeat a line or idea from earlier texts.",
            f"- Never write messages for {p}.",
            "- English only.",
        ]
        return "\n\n".join([intro, "\n".join(setup), "\n".join(rules)])

    # ---- Block B ------------------------------------------------------------------------

    def character(self, ctx: PromptContext) -> str:
        card, c, p = ctx.card, ctx.char, ctx.player
        char_lines = [lead_in(f"Character: {c}, {GENDER[card.gender]}", ctx.fill(card.description))]
        labelled = [
            ("Personality", card.personality),
            ("Appearance", card.appearance),
            ("Background", card.background),
            ("Goals", card.goals),
            (f"Secrets ({p} does not know; reveal only gradually through actions and thoughts)", card.secrets),
            ("Way of speaking", card.speech_style),
        ]
        char_lines += [f"{label}: {sentence(ctx.fill(value))}" for label, value in labelled if value.strip()]
        persona_line = lead_in(f"Player: {p}, {GENDER[ctx.persona.gender]}", ctx.fill(ctx.persona.description))
        parts = ["\n".join(char_lines) + "\n" + persona_line]

        # Vietnamese self/player terms (tớ/cậu...) have no English equivalent beyond I/you, and a
        # Vietnamese card's free-text `others` would leak Vietnamese into the prompt: those only carry
        # over from an English card. Nicknames always carry over.
        at = card.address_terms
        nicknames = unique(at.nicknames)
        if nicknames:
            parts.append(f"Nicknames: {c} sometimes calls {p} {quoted(nicknames, 'or')} when being gentle.")
        address: list[str] = []
        if card.language == "en":
            self_term, player_term = at.self_term.strip(), at.player_term.strip()
            if self_term and self_term.casefold() not in {"i", "me"}:
                address.append(f'- {c} refers to themself as "{self_term}".')
            if player_term and player_term.casefold() != "you":
                address.append(f'- {c} calls {p} "{player_term}".')
            if at.others.strip():
                address.append(f"- With others: {sentence(ctx.fill(at.others))}")
        if address:
            parts.append("Forms of address (dialogue and Thoughts only):\n" + "\n".join(address))

        if ctx.style.strip():
            parts.append(ctx.style.strip())
        if card.example_dialogues.strip():
            parts.append("Example dialogue (for voice only, do not copy):\n" + ctx.fill(card.example_dialogues))
        return "\n\n".join(parts)

    # ---- Block C ------------------------------------------------------------------------

    def context(self, ctx: PromptContext, *, summary: str | None = None) -> str:
        lines: list[str] = []
        if ctx.story.scenario.strip():
            lines.append(f"Scenario: {ctx.fill(ctx.story.scenario)}")
        if ctx.story.scene_summary.strip():
            lines.append(f"Story so far: {ctx.fill(ctx.story.scene_summary)}")
        if summary and summary.strip():
            lines.append(f"Earlier in the story: {summary.strip()}")
        return "\n\n".join(lines)

    # ---- Block F ------------------------------------------------------------------------

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
            lines.append(f"- Current scene: {sentence(where)}")
        if directive and directive.strip():
            lines.append(f"- {c}'s attitude right now: {sentence(directive)}")
        if memories:
            lines.append(
                f"- Things {c} remembers from earlier (bring them up only when they fit the scene; "
                "never retell them word for word):"
            )
            lines.extend(f"  + {sentence(m)}" for m in memories)
        if facts:
            lines.append(f"- What {c} knows:")
            lines.extend(f"  + {sentence(f)}" for f in facts)
        return lines

    def dm_note(self, ctx: PromptContext) -> str:
        c, p = ctx.char, ctx.player
        return (
            f"- A turn labelled {self.dm_label} is a text message {c} and {p} sent each other by phone: it really "
            f"happened, and {c} remembers and knows everything in it (names, plans, what was told). This turn is "
            "still narration and does not start with that label."
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
            lines = [f"[Note for the writer, not a message from {p}]", *state]
            if player_wrote:
                lines.append(
                    f"- Reply directly to the message {p} just sent: 1-3 short sentences, message text only, "
                    "no action descriptions, no [Thought: ...]."
                )
            else:
                lines.append(
                    f"- {p} sent nothing new this turn; {c} texts again: 1-3 short sentences, message text only, "
                    "no action descriptions, no [Thought: ...]."
                )
            if directive:
                lines.append(
                    f"- The player's direction for this turn: {sentence(directive)} "
                    "Follow it, but never repeat it in the message."
                )
            if avoid:
                listed = "; ".join(f'"{a}"' for a in avoid)
                lines.append(
                    f"- {c}'s recent texts ended with: {listed}. Do not repeat those lines or ideas, "
                    "and do not end with advice."
                )
            return "\n".join(lines)

        lines = [f"[Note to the narrator, not {p}'s words]", *state]
        if player_wrote:
            lines.append(
                f"- Continue directly from exactly what {p} just said and did above; do not skip it or change "
                f"the scene. Do not copy or restate {p}'s words and actions; open with {c}'s reaction. "
                f"End where {p} needs to respond."
            )
        else:
            lines.append(
                f"- {p} did nothing new this turn; continue from the current scene. End where {p} needs to respond."
            )
        if directive:
            lines.append(
                f"- The player's direction for this turn: {sentence(directive)} "
                "Follow it, but never repeat it in the story."
            )
        if avoid:
            listed = "; ".join(f'"{a}"' for a in avoid)
            lines.append(
                f"- Recent turns opened with: {listed}. Open this turn differently (with speech, a sound or a "
                "detail of the scene) and do not repeat lines or details already written."
            )
        her = _third_person(np_.player, ctx.persona.gender)
        if ctx.story.pov == "first":
            pron = f'{c} narrates as "{_first_person(np_.character)}"; {p} is "{her}".'
        else:
            pron = f'In narration, {c} is "{_third_person(np_.character, ctx.card.gender)}" and {p} is "{her}".'
        lines.append(f"- {_thought_reminder(ctx)} {pron} Plain, concrete prose.")
        return "\n".join(lines)

    # ---- Block D (Phase 4): world notes at the head of the last user message ----------------

    def lore_header(self, ctx: PromptContext) -> str:
        c, p = ctx.char, ctx.player
        who = f"the writer, not a message from {p}" if ctx.story.mode == "dm" else f"the narrator, not {p}'s words"
        return f"[World notes for {who}. {c} knows these; use them only when they fit the scene, never recite them.]"

    def lore_item(self, ctx: PromptContext, title: str, text: str, private: bool) -> str:
        if private:
            note = f" (only {ctx.char} knows this and has told no one; do not bring it up without a reason)"
            return f"- {title}{note}: {text}"
        return f"- {title}: {text}"

    def lore_footer(self, ctx: PromptContext) -> str:
        return "[End of world notes.]"


TEMPLATE = EnTemplate()
