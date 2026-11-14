import { test } from "node:test";
import assert from "node:assert/strict";
import type { NarrationPronouns, StorySettings } from "../../types.ts";
import { createRequest, draftFromDefaults, draftProblems, greetingChoices, mergeSettings, rebaseDraft } from "./startLogic.ts";

const SETTINGS: StorySettings = {
  scenario: "  Chiều mưa ở tiệm sách.  ",
  language: "vi",
  mode: "story",
  relationship_type: "het",
  pov: "third",
  thought_style: "inline",
  narration_pronouns: { character: "cô", player: "anh" },
};

test("draftFromDefaults: copies the defaults, greeting 0 when there is one", () => {
  const d = draftFromDefaults({ title: "Hạ Vy và Gia Huy", settings: SETTINGS }, "Bốn giờ chiều…");
  assert.equal(d.greetingIndex, 0);
  d.settings.narration_pronouns.character = "nàng";
  assert.equal(SETTINGS.narration_pronouns.character, "cô");
  assert.equal(draftFromDefaults({ title: "x", settings: SETTINGS }, "  ").greetingIndex, -1);
});

test("draftProblems: blank title or pronouns block; no draft is fine", () => {
  assert.deepEqual(draftProblems(null), []);
  const d = draftFromDefaults({ title: " ", settings: SETTINGS }, "");
  d.settings.narration_pronouns.player = " ";
  assert.deepEqual(draftProblems(d), ["Tiêu đề không được để trống.", "Hãy điền đủ đại từ dẫn truyện."]);
});

test("createRequest: only card and persona without a draft, trimmed fields with one", () => {
  assert.deepEqual(createRequest(4, 2, null), { card_id: 4, persona_id: 2 });
  const d = draftFromDefaults({ title: "  Mưa  ", settings: { ...SETTINGS, narration_pronouns: { character: " cô ", player: "anh " } } }, "x");
  assert.deepEqual(createRequest(4, 2, d), {
    card_id: 4,
    persona_id: 2,
    title: "Mưa",
    greeting_index: 0,
    settings: { ...SETTINGS, scenario: "Chiều mưa ở tiệm sách.", narration_pronouns: { character: "cô", player: "anh" } },
  });
});

test("mergeSettings: language/POV carry suggested pronouns unless the user typed their own", () => {
  const suggest = (s: StorySettings): NarrationPronouns =>
    s.pov === "first" ? { character: "tôi", player: "anh" } : s.language === "en" ? { character: "she", player: "he" } : { character: "cô", player: "anh" };
  assert.deepEqual(mergeSettings(SETTINGS, { language: "en" }, suggest).narration_pronouns, { character: "she", player: "he" });
  assert.deepEqual(mergeSettings(SETTINGS, { pov: "first" }, suggest).narration_pronouns, { character: "tôi", player: "anh" });
  const typed = { ...SETTINGS, narration_pronouns: { character: "nàng", player: "chàng" } };
  assert.deepEqual(mergeSettings(typed, { language: "en" }, suggest).narration_pronouns, { character: "nàng", player: "chàng" });
  assert.equal(mergeSettings(SETTINGS, { mode: "dm" }, suggest).mode, "dm");
  assert.deepEqual(mergeSettings(SETTINGS, { language: "en" }, () => null).narration_pronouns, SETTINGS.narration_pronouns);
});

test("greetingChoices: main and alternates, blanks skipped", () => {
  assert.deepEqual(greetingChoices("Chào", ["", "Khác"]), [
    { index: 0, label: "Chính" },
    { index: 2, label: "Khác 2" },
  ]);
  assert.deepEqual(greetingChoices(" ", []), []);
});

test("rebaseDraft: another persona keeps the user's edits and refreshes the untouched fields", () => {
  const base = draftFromDefaults({ title: "Hạ Vy và Gia Huy", settings: SETTINGS }, "Chào");
  const fresh = draftFromDefaults(
    { title: "Hạ Vy và Minh Thư", settings: { ...SETTINGS, relationship_type: "gl", narration_pronouns: { character: "cô", player: "cô ấy" } } },
    "Chào",
  );
  const noSuggest = () => null;

  // Nothing edited: the new persona's defaults (except the greeting choice, which is the user's).
  const untouched = rebaseDraft({ ...base, greetingIndex: 0 }, base, fresh, null, noSuggest);
  assert.deepEqual(untouched, fresh);

  // Title, scenario, greeting and mode edited: kept; relationship and pronouns follow the new persona.
  const edited = {
    title: "Chiều mưa",
    greetingIndex: -1,
    show_thoughts: true,
    settings: { ...base.settings, scenario: "Tiệm đóng cửa sớm.", mode: "dm" as const, narration_pronouns: { ...base.settings.narration_pronouns } },
  };
  const r = rebaseDraft(edited, base, fresh, null, noSuggest);
  assert.equal(r.title, "Chiều mưa");
  assert.equal(r.greetingIndex, -1);
  assert.equal(r.settings.scenario, "Tiệm đóng cửa sớm.");
  assert.equal(r.settings.mode, "dm");
  assert.equal(r.settings.relationship_type, "gl");
  assert.deepEqual(r.settings.narration_pronouns, { character: "cô", player: "cô ấy" });

  // Pronouns the user typed stay.
  const typed = { ...edited, settings: { ...edited.settings, narration_pronouns: { character: "nàng", player: "chàng" } } };
  assert.deepEqual(rebaseDraft(typed, base, fresh, null, noSuggest).settings.narration_pronouns, { character: "nàng", player: "chàng" });

  // POV changed by the user (pronouns were the old persona's suggestion): the new persona's suggestion.
  const firstPerson = {
    ...edited,
    settings: { ...edited.settings, pov: "first" as const, narration_pronouns: { character: "tôi", player: "anh" } },
  };
  const r2 = rebaseDraft(firstPerson, base, fresh, { character: "tôi", player: "anh" }, (s) =>
    s.pov === "first" ? { character: "tôi", player: "cậu" } : null,
  );
  assert.equal(r2.settings.pov, "first");
  assert.deepEqual(r2.settings.narration_pronouns, { character: "tôi", player: "cậu" });
});

// ---- Phase 4 (B): "Đọc suy nghĩ của nhân vật" ----

test("draftFromDefaults reads thoughts by default; createRequest sends show_thoughts only when off", () => {
  const d = draftFromDefaults({ title: "Mưa", settings: SETTINGS }, "x");
  assert.equal(d.show_thoughts, true);
  assert.equal("show_thoughts" in createRequest(4, 2, d), false);
  assert.equal(createRequest(4, 2, { ...d, show_thoughts: false }).show_thoughts, false);
  // Not customised: nothing but the card and persona (the server's default is on).
  assert.deepEqual(createRequest(4, 2, null), { card_id: 4, persona_id: 2 });
});

test("rebaseDraft keeps the player's thought choice when the persona changes", () => {
  const base = draftFromDefaults({ title: "A", settings: SETTINGS }, "Chào");
  const fresh = draftFromDefaults({ title: "B", settings: SETTINGS }, "Chào");
  const off = { ...base, show_thoughts: false };
  assert.equal(rebaseDraft(off, base, fresh, null, () => null).show_thoughts, false);
  assert.equal(rebaseDraft(base, base, fresh, null, () => null).show_thoughts, true);
});
