import { test } from "node:test";
import assert from "node:assert/strict";
import {
  affectsNextTurn,
  defaultRelationship,
  fillPlaceholders,
  formatActivity,
  formFromStory,
  greetingAt,
  narrationFor,
  settingsPatch,
  showThoughtsHint,
  showThoughtsOf,
  suggestPronouns,
  validateSettingsForm,
} from "./storyOptions.ts";
import type { Story, StyleProfileInfo } from "../types.ts";

const coDai: StyleProfileInfo = {
  name: "trung_co_dai",
  title: "Cổ trang",
  description: "",
  narration: { vi: { male: "hắn", female: "nàng", other: "" }, en: { male: "he", female: "she", other: "they" } },
  address_examples: [],
};

const story: Story = {
  id: 1,
  card_id: 1,
  persona_id: 1,
  title: "Lạc Dương & Lâm Vãn",
  scenario: "Thư viện",
  language: "vi",
  mode: "story",
  relationship_type: "het",
  pov: "third",
  thought_style: "inline",
  narration_pronouns: { character: "anh", player: "cô" },
  model_name: "gemma4:12b",
  scene_summary: "",
  created_at: null,
};

test("narrationFor uses the profile, then falls back, then the name", () => {
  assert.equal(narrationFor(coDai, "vi", "male", "Tạ Vân"), "hắn");
  assert.equal(narrationFor(coDai, "vi", "other", "Tạ Vân"), "Tạ Vân");
  assert.equal(narrationFor(null, "vi", "female", "Lâm Vãn"), "cô");
  assert.equal(narrationFor(null, "vi", "other", "Tiểu Bạch"), "Tiểu Bạch");
  assert.equal(narrationFor(undefined, "en", "other", "X"), "they");
});

test("suggestPronouns: third and first person", () => {
  const ctx = {
    profile: coDai,
    language: "vi" as const,
    pov: "third" as const,
    cardGender: "female" as const,
    cardName: "Tạ Vân Lan",
    personaGender: "male" as const,
    personaName: "Lục Trần",
  };
  assert.deepEqual(suggestPronouns(ctx), { character: "nàng", player: "hắn" });
  assert.deepEqual(suggestPronouns({ ...ctx, pov: "first" }), { character: "tôi", player: "hắn" });
  assert.deepEqual(suggestPronouns({ ...ctx, pov: "first", language: "en" }), { character: "I", player: "he" });
});

test("defaultRelationship mirrors the backend", () => {
  assert.equal(defaultRelationship("male", "female"), "het");
  assert.equal(defaultRelationship("female", "male"), "het");
  assert.equal(defaultRelationship("male", "male"), "bl");
  assert.equal(defaultRelationship("female", "female"), "gl");
  assert.equal(defaultRelationship("other", "female"), "none");
});

test("settingsPatch sends only what changed", () => {
  const form = formFromStory(story);
  assert.deepEqual(settingsPatch(story, form), {});
  assert.deepEqual(settingsPatch(story, { ...form, title: "  Mới  ", pov: "first" }), { title: "Mới", pov: "first" });
  // Empty title is never sent (the form validation blocks it).
  assert.deepEqual(settingsPatch(story, { ...form, title: "   " }), {});
  assert.deepEqual(settingsPatch(story, { ...form, narration_pronouns: { character: " hắn ", player: "cô" } }), {
    narration_pronouns: { character: "hắn", player: "cô" },
  });
  assert.deepEqual(settingsPatch(story, { ...form, scenario: "Thư viện  " }), {});
  assert.deepEqual(settingsPatch(story, { ...form, scenario: "" }), { scenario: "" });
  // formFromStory copies the pronouns (editing the form never mutates the story).
  form.narration_pronouns.character = "y";
  assert.equal(story.narration_pronouns.character, "anh");
});

test("affectsNextTurn and validation", () => {
  assert.equal(affectsNextTurn({ title: "x" }), false);
  assert.equal(affectsNextTurn({ language: "en" }), true);
  assert.deepEqual(validateSettingsForm(formFromStory(story)), []);
  assert.equal(validateSettingsForm({ ...formFromStory(story), title: " " }).length, 1);
  assert.equal(
    validateSettingsForm({ ...formFromStory(story), narration_pronouns: { character: "", player: "cô" } }).length,
    1,
  );
});

test("greetingAt and fillPlaceholders", () => {
  assert.equal(greetingAt("A", ["B", "C"], 0), "A");
  assert.equal(greetingAt("A", ["B", "C"], 2), "C");
  assert.equal(greetingAt("A", ["B"], 5), "");
  assert.equal(greetingAt("A", ["B"], -1), "");
  assert.equal(fillPlaceholders("{{char}} nhìn {{ USER }}.", "Lạc Dương", "Lâm Vãn"), "Lạc Dương nhìn Lâm Vãn.");
});

test("formatActivity", () => {
  const now = Date.parse("2026-11-12T12:00:00Z");
  assert.equal(formatActivity(null, now), "");
  assert.equal(formatActivity("garbage", now), "");
  assert.equal(formatActivity("2026-11-12T11:59:40Z", now), "vừa xong");
  assert.equal(formatActivity("2026-11-12 11:55:00", now), "5 phút trước");
  assert.equal(formatActivity("2026-11-12T09:00:00+00:00", now), "3 giờ trước");
  assert.equal(formatActivity("2026-11-11T08:00:00Z", now), "hôm qua");
  assert.equal(formatActivity("2026-11-08T12:00:00Z", now), "4 ngày trước");
  assert.match(formatActivity("2026-10-01T12:00:00Z", now), /^\d\d\/10\/2026$/);
});

// ---- Phase 4 (B) ----

test("showThoughtsOf / formFromStory: a missing field (older server) reads as on", () => {
  assert.equal(showThoughtsOf(story), true);
  assert.equal(showThoughtsOf(null), true);
  assert.equal(showThoughtsOf({ ...story, show_thoughts: true }), true);
  assert.equal(showThoughtsOf({ ...story, show_thoughts: false }), false);
  assert.equal(formFromStory(story).show_thoughts, true);
  assert.equal(formFromStory({ ...story, show_thoughts: false }).show_thoughts, false);
});

test("settingsPatch sends show_thoughts only when it changed; it does not count as a next-turn change", () => {
  const form = formFromStory(story);
  assert.deepEqual(settingsPatch(story, { ...form, show_thoughts: false }), { show_thoughts: false });
  const off = { ...story, show_thoughts: false };
  assert.deepEqual(settingsPatch(off, formFromStory(off)), {});
  assert.deepEqual(settingsPatch(off, { ...formFromStory(off), show_thoughts: true }), { show_thoughts: true });
  assert.equal(affectsNextTurn({ show_thoughts: false }), false);
});

test("showThoughtsHint names the character, or says Nhân vật", () => {
  assert.equal(
    showThoughtsHint("Lâm Vãn"),
    "Tắt thì thẻ suy nghĩ không hiện trong story. Lâm Vãn vẫn nghĩ như thường, chỉ là bạn không đọc thấy.",
  );
  assert.match(showThoughtsHint("  "), /^Tắt thì .* Nhân vật vẫn nghĩ/);
});
