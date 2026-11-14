// Pure logic of the "Bước vào câu chuyện" sheet (tested in startLogic.test.ts): the optional story
// setup ("Tuỳ chỉnh story") and the POST /api/stories body. No React, no DOM.
import type { NarrationPronouns, StoryCreateRequest, StoryDefaults, StorySettings } from "../../types.ts";

/** What "Tuỳ chỉnh story" edits; null while the user has not opened it (the server's defaults apply). */
export interface StoryDraft {
  title: string;
  settings: StorySettings;
  /** 0 = greeting, 1.. = alternate greetings, -1 = none. */
  greetingIndex: number;
  /**
   * Phase 4 (B): "Đọc suy nghĩ của nhân vật". Display only, so not part of `settings` (those shape the
   * story the character writes); sent as `show_thoughts: false` only when switched off.
   */
  show_thoughts: boolean;
}

/** The setup form filled with GET /api/stories/defaults; the main greeting when the card has one. */
export function draftFromDefaults(defaults: StoryDefaults, greeting: string): StoryDraft {
  return {
    title: defaults.title,
    settings: { ...defaults.settings, narration_pronouns: { ...defaults.settings.narration_pronouns } },
    greetingIndex: greeting.trim() ? 0 : -1,
    show_thoughts: true,
  };
}

/** Problems that block starting (Vietnamese). None when the setup was never opened. */
export function draftProblems(draft: StoryDraft | null): string[] {
  if (!draft) return [];
  const problems: string[] = [];
  if (!draft.title.trim()) problems.push("Tiêu đề không được để trống.");
  const np = draft.settings.narration_pronouns;
  if (!np.character.trim() || !np.player.trim()) problems.push("Hãy điền đủ đại từ dẫn truyện.");
  return problems;
}

/**
 * Settings after a change. A language or point-of-view change carries the narration pronouns along
 * with it (the style's suggestion for the new setting), unless the user already typed their own.
 */
export function mergeSettings(
  current: StorySettings,
  next: Partial<StorySettings>,
  suggest: (s: StorySettings) => NarrationPronouns | null,
): StorySettings {
  const merged: StorySettings = { ...current, ...next };
  if ((next.language !== undefined || next.pov !== undefined) && !next.narration_pronouns) {
    const before = suggest(current);
    const after = suggest(merged);
    const np = current.narration_pronouns;
    if (before && after && before.character === np.character.trim() && before.player === np.player.trim()) {
      merged.narration_pronouns = { ...after };
    }
  }
  return merged;
}

/**
 * POST /api/stories body: just the card and persona when the setup was not opened (the server fills
 * the same defaults the form would show), else everything the form holds, trimmed.
 */
export function createRequest(cardId: number, personaId: number, draft: StoryDraft | null): StoryCreateRequest {
  if (!draft) return { card_id: cardId, persona_id: personaId };
  const s = draft.settings;
  const body: StoryCreateRequest = {
    card_id: cardId,
    persona_id: personaId,
    title: draft.title.trim(),
    greeting_index: draft.greetingIndex,
    settings: {
      ...s,
      scenario: s.scenario.trim(),
      narration_pronouns: { character: s.narration_pronouns.character.trim(), player: s.narration_pronouns.player.trim() },
    },
  };
  // The server defaults to on: the field goes only when the player switched it off.
  if (!draft.show_thoughts) body.show_thoughts = false;
  return body;
}

/** Labels of the greeting choices: "Chính", "Khác 1", …; blank greetings are not offered. */
export function greetingChoices(greeting: string, alternates: readonly string[]): { index: number; label: string }[] {
  return [greeting, ...alternates]
    .map((text, index) => ({ index, text }))
    .filter((g) => g.text.trim().length > 0)
    .map((g) => ({ index: g.index, label: g.index === 0 ? "Chính" : `Khác ${g.index}` }));
}

function samePronouns(a: NarrationPronouns, b: NarrationPronouns): boolean {
  return a.character.trim() === b.character.trim() && a.player.trim() === b.player.trim();
}

/**
 * The setup after picking another persona. `base` is the defaults the current draft started from,
 * `fresh` the defaults for the new persona. A field the user changed (differs from `base`) is kept;
 * an untouched one takes the new persona's default. The greeting choice and "Đọc suy nghĩ" are always kept. Narration
 * pronouns count as the user's own only when they differ from both the old defaults and what the old
 * persona suggests (`oldSuggestion`, for the current settings); otherwise they follow the new persona:
 * the server's defaults when the language and point of view are unchanged, else what
 * `newSuggestion` gives for the new settings.
 */
export function rebaseDraft(
  current: StoryDraft,
  base: StoryDraft,
  fresh: StoryDraft,
  oldSuggestion: NarrationPronouns | null,
  newSuggestion: (s: StorySettings) => NarrationPronouns | null,
): StoryDraft {
  const cur = current.settings;
  const was = base.settings;
  const next = fresh.settings;
  const pick = <K extends keyof StorySettings>(k: K): StorySettings[K] => (cur[k] === was[k] ? next[k] : cur[k]);
  const settings: StorySettings = {
    scenario: pick("scenario"),
    language: pick("language"),
    mode: pick("mode"),
    relationship_type: pick("relationship_type"),
    pov: pick("pov"),
    thought_style: pick("thought_style"),
    narration_pronouns: { ...cur.narration_pronouns },
  };
  const np = cur.narration_pronouns;
  const typed = !samePronouns(np, was.narration_pronouns) && !(oldSuggestion && samePronouns(np, oldSuggestion));
  if (!typed) {
    const sameSetup = settings.language === next.language && settings.pov === next.pov;
    const follow = sameSetup ? next.narration_pronouns : (newSuggestion(settings) ?? next.narration_pronouns);
    settings.narration_pronouns = { ...follow };
  }
  return {
    title: current.title === base.title ? fresh.title : current.title,
    settings,
    greetingIndex: current.greetingIndex,
    // A display choice of the player, never a persona default: always kept.
    show_thoughts: current.show_thoughts,
  };
}
