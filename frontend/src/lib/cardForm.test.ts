import { test } from "node:test";
import assert from "node:assert/strict";
import {
  readNarrationOverride,
  withNarrationOverride,
  DEFAULT_INITIAL_RELATIONSHIP,
  EMOTION_HINT,
  EMOTION_KEYS,
  EMOTION_LABEL,
  applyOverrides,
  cardHints,
  clampEmotion,
  cleanList,
  containsWord,
  defaultTestSettings,
  emptyCard,
  fillPlaceholders,
  filterCards,
  formatRelativeTime,
  isDefaultRelationship,
  isDirty,
  readInitialRelationship,
  summaryRole,
  withInitialRelationship,
  narrationOnly,
  normalizeTerm,
  prepareForSave,
  relationshipFor,
  splitList,
  suggestNarration,
  toCard,
  validateCard,
} from "./cardForm.ts";
import type { CardOut, CharacterCard, Persona, StyleProfileInfo } from "../types.ts";

const CO_DAI: StyleProfileInfo = {
  name: "trung_co_dai",
  title: "Cổ trang",
  description: "",
  narration: { vi: { male: "hắn", female: "nàng", other: "" }, en: { male: "he", female: "she", other: "they" } },
  address_examples: [{ self: "ta", player: "ngươi" }],
};

function card(over: Partial<CharacterCard> = {}): CharacterCard {
  return { ...emptyCard("trung_hien_dai"), name: "Lạc Dương", ...over };
}

const LAM_VAN: Persona = { id: 1, name: "Lâm Vãn", gender: "female", description: "" };

test("emptyCard has every field with safe defaults", () => {
  const c = emptyCard();
  assert.equal(c.id, null);
  assert.equal(c.style_profile, "chung");
  assert.deepEqual(c.address_terms, { self_term: "", player_term: "", nicknames: [], others: "" });
  assert.deepEqual(c.alternate_greetings, []);
  assert.deepEqual(c.extensions, {});
  assert.equal(c.avatar, null);
  // Fresh objects every call.
  c.tags.push("x");
  assert.deepEqual(emptyCard().tags, []);
});

test("normalizeTerm keeps the first option, lower-cases, keeps English I", () => {
  assert.equal(normalizeTerm("Tớ", "vi"), "tớ");
  assert.equal(normalizeTerm("anh/em", "vi"), "anh");
  assert.equal(normalizeTerm("ta, bổn tọa", "vi"), "ta");
  assert.equal(normalizeTerm("ngươi hoặc nàng", "vi"), "ngươi");
  assert.equal(normalizeTerm("Sư Tỷ", "vi"), "sư tỷ");
  assert.equal(normalizeTerm("Sư tỷ (khi thân)", "vi"), "sư tỷ");
  assert.equal(normalizeTerm('  "cậu"  ', "vi"), "cậu");
  assert.equal(normalizeTerm("I", "en"), "I");
  assert.equal(normalizeTerm("You or babe", "en"), "you");
  assert.equal(normalizeTerm("   ", "vi"), "");
});

test("validateCard reports blocking problems in Vietnamese", () => {
  assert.deepEqual(validateCard(card()), []);
  assert.deepEqual(validateCard(card({ name: "  " })), ["Tên nhân vật không được để trống."]);
  assert.match(validateCard(card({ name: "x".repeat(81) }))[0] ?? "", /80 ký tự/);
  assert.deepEqual(validateCard(card({ style_profile: "" })), ["Hãy chọn một style profile."]);
  assert.match(validateCard(card({ style_profile: "khong_co" }), ["chung", "trung_hien_dai"])[0] ?? "", /không có/);
  assert.deepEqual(validateCard(card(), ["trung_hien_dai"]), []);
  assert.match(validateCard(card({ greeting: "a".repeat(20_001) }))[0] ?? "", /lời mở đầu/);
  assert.match(
    validateCard(card({ tags: Array.from({ length: 21 }, (_, i) => `t${i}`) }))[0] ?? "",
    /Tối đa 20 tag/,
  );
  // Duplicate tags are not counted twice.
  assert.deepEqual(validateCard(card({ tags: [...Array(20).fill("a"), "A"] })), []);
  assert.match(
    validateCard(card({ address_terms: { self_term: "t".repeat(201), player_term: "", nicknames: [], others: "" } }))[0] ??
      "",
    /tự xưng/,
  );
});

test("prepareForSave trims and de-duplicates", () => {
  const out = prepareForSave(
    card({
      name: "  Lạc   Dương ",
      tags: [" học đường", "Học đường", "", "ngọt"],
      alternate_greetings: ["Xin chào", "   ", ""],
      address_terms: { self_term: " tớ ", player_term: "cậu ", nicknames: ["Vãn Vãn", "vãn vãn", " "], others: " " },
    }),
  );
  assert.equal(out.name, "Lạc Dương");
  assert.deepEqual(out.tags, ["học đường", "ngọt"]);
  assert.deepEqual(out.alternate_greetings, ["Xin chào"]);
  assert.deepEqual(out.address_terms, { self_term: "tớ", player_term: "cậu", nicknames: ["Vãn Vãn"], others: "" });
});

test("cleanList and splitList", () => {
  assert.deepEqual(cleanList(["a", " A ", "b  c", ""]), ["a", "b c"]);
  assert.deepEqual(splitList("Vãn Vãn, A Vãn; vãn vãn\nTiểu Vãn"), ["Vãn Vãn", "A Vãn", "Tiểu Vãn"]);
});

test("suggestNarration uses the profile, then the fallback, then the name", () => {
  assert.equal(suggestNarration(CO_DAI, "vi", "male"), "hắn");
  assert.equal(suggestNarration(CO_DAI, "vi", "female"), "nàng");
  assert.equal(suggestNarration(null, "vi", "male"), "anh");
  assert.equal(suggestNarration(undefined, "en", "female"), "she");
  assert.equal(suggestNarration(CO_DAI, "vi", "other", "Tiểu Bạch"), "Tiểu Bạch");
  assert.equal(suggestNarration(CO_DAI, "en", "other", "X"), "they");
});

test("relationshipFor mirrors the backend", () => {
  assert.equal(relationshipFor("male", "female"), "het");
  assert.equal(relationshipFor("female", "male"), "het");
  assert.equal(relationshipFor("male", "male"), "bl");
  assert.equal(relationshipFor("female", "female"), "gl");
  assert.equal(relationshipFor("other", "female"), "none");
});

test("fillPlaceholders replaces {{char}} and {{user}} in any case", () => {
  assert.equal(fillPlaceholders(" {{char}} nhìn {{ User }}. {{USER}}! ", "Lạc Dương", "Lâm Vãn"), "Lạc Dương nhìn Lâm Vãn. Lâm Vãn!");
  assert.equal(fillPlaceholders("$& {{user}}", "A", "$1"), "$& $1");
});

test("defaultTestSettings and applyOverrides", () => {
  const c = card({ style_profile: "trung_co_dai", scenario: "{{char}} đợi {{user}} ở sơn môn." });
  const d = defaultTestSettings(c, LAM_VAN, CO_DAI);
  assert.deepEqual(d, {
    scenario: "Lạc Dương đợi Lâm Vãn ở sơn môn.",
    language: "vi",
    mode: "story",
    relationship_type: "het",
    pov: "third",
    thought_style: "inline",
    narration_pronouns: { character: "hắn", player: "nàng" },
  });
  const en = defaultTestSettings(c, LAM_VAN, CO_DAI, "en");
  assert.deepEqual(en.narration_pronouns, { character: "he", player: "she" });

  const o = applyOverrides(d, { mode: "dm", narration_player: "cô" });
  assert.equal(o.mode, "dm");
  assert.deepEqual(o.narration_pronouns, { character: "hắn", player: "cô" });
  assert.equal(o.language, "vi");
  assert.deepEqual(applyOverrides(d, {}), d);
});

test("isDirty ignores id, avatar and CardOut extras", () => {
  const a = card({ id: 3, tags: ["x"], extensions: { v2: { creator: "me" } } });
  const out: CardOut = { ...a, avatar: "card-3-ab.png", avatar_url: "/api/cards/3/avatar", story_count: 2, updated_at: "now", creator_handle: "ban", creator_name: "Bạn" };
  assert.equal(isDirty(a, out), false);
  assert.equal(isDirty(a, toCard(out)), false);
  assert.equal(isDirty(a, { ...a, id: null }), false);
  assert.equal(isDirty(a, { ...a, name: "Khác" }), true);
  assert.equal(isDirty(a, { ...a, tags: ["x", "y"] }), true);
  assert.equal(isDirty(a, { ...a, address_terms: { ...a.address_terms, nicknames: ["A"] } }), true);
  assert.equal(isDirty(a, { ...a, extensions: { v2: { creator: "you" } } }), true);
  // Phase 4b: the "Công khai" switch is saved with the card; missing means private.
  assert.equal(isDirty(a, { ...a, visibility: "public" }), true);
  assert.equal(isDirty({ ...a, visibility: "private" }, { ...a, visibility: undefined }), false);
});

test("toCard copies deeply and drops CardOut fields", () => {
  const src: CardOut = {
    ...card({ id: 9, tags: ["a"] }),
    creator_handle: null,
    creator_name: null,
    avatar_url: "/x",
    story_count: 1,
    updated_at: null,
  };
  const c = toCard(src);
  assert.equal("avatar_url" in c, false);
  c.tags.push("b");
  c.address_terms.nicknames.push("n");
  assert.deepEqual(src.tags, ["a"]);
  assert.deepEqual(src.address_terms.nicknames, []);
});

test("toCard keeps uid and visibility so a save never resets them", () => {
  const src: CardOut = {
    ...card({ id: 9 }),
    uid: "a".repeat(32),
    visibility: "unlisted",
    creator_handle: "ban",
    creator_name: "Bạn",
    avatar_url: null,
    story_count: 0,
    updated_at: null,
  };
  const c = toCard(src);
  assert.equal(c.uid, "a".repeat(32));
  assert.equal(c.visibility, "unlisted");
  const bare = toCard(card({ id: 1 }));
  assert.equal("uid" in bare, false);
  assert.equal("visibility" in bare, false);
});

test("narrationOnly and containsWord", () => {
  const g = 'Cậu ấy cười. "Tớ đợi cậu mãi." [Thought: Cậu ấy thật đáng yêu.] Anh quay đi.';
  const n = narrationOnly(g);
  assert.equal(containsWord(n, "tớ"), false);
  assert.equal(containsWord(n, "cậu"), true); // "Cậu ấy" in narration
  assert.equal(containsWord("Anh quay đi.", "an"), false);
  assert.equal(containsWord("sư tỷ đến", "Sư tỷ"), true);
});

test("cardHints flags missing terms, missing Thought and terms in narration", () => {
  const ok = card({
    address_terms: { self_term: "tớ", player_term: "cậu", nicknames: [], others: "" },
    greeting: 'Anh mỉm cười. "Tớ đợi cậu lâu rồi."\n\n[Thought: Cậu ấy đến rồi.]',
  });
  assert.deepEqual(cardHints(ok), []);

  const missing = card({ greeting: "Anh mỉm cười." });
  const fields = cardHints(missing).map((h) => h.field);
  assert.deepEqual(fields, ["address", "greeting"]);

  const inNarration = card({
    address_terms: { self_term: "ta", player_term: "ngươi", nicknames: [], others: "" },
    greeting: 'Ta đặt chén trà xuống. "Ngươi đến rồi." [Thought: Ngươi cuối cùng cũng tới.]',
  });
  const hints = cardHints(inNarration, CO_DAI);
  assert.equal(hints.length, 1);
  assert.match(hints[0]?.text ?? "", /"ta"/);
  assert.doesNotMatch(hints[0]?.text ?? "", /ngươi/);

  // A term that is also the narration pronoun ("anh") is not flagged.
  const anhEm = card({
    address_terms: { self_term: "anh", player_term: "em", nicknames: [], others: "" },
    greeting: 'Anh nhìn {{user}}. "Em đến rồi." [Thought: Em ấy gầy đi.]',
  });
  assert.deepEqual(cardHints(anhEm), []);

  // English cards do not need Vietnamese address terms; non-normalized terms get a hint.
  assert.deepEqual(cardHints(card({ language: "en" })), []);
  const upper = cardHints(card({ address_terms: { self_term: "Tớ", player_term: "cậu/bạn", nicknames: [], others: "" } }));
  assert.equal(upper.length, 2);
  assert.match(upper[1]?.text ?? "", /"cậu"/);
});

// ---- Lyris design: role, starting emotions, list search ----

test("role is trimmed on save, limited to 80 chars and counts as a change", () => {
  assert.equal(prepareForSave(card({ role: "  Chủ tiệm   sách mùa thu " })).role, "Chủ tiệm sách mùa thu");
  assert.deepEqual(validateCard(card({ role: "x".repeat(80) })), []);
  assert.match(validateCard(card({ role: "x".repeat(81) }))[0] ?? "", /Vai trò dài quá 80/);
  const a = card({ role: "Lớp trưởng" });
  assert.equal(isDirty(a, { ...a, role: "Bí thư" }), true);
  assert.equal(toCard({ ...a, role: undefined } as unknown as CharacterCard).role, "");
});

test("readInitialRelationship falls back to the defaults and clamps values", () => {
  assert.deepEqual(readInitialRelationship(card()), { values: { ...DEFAULT_INITIAL_RELATIONSHIP }, stored: false });
  assert.deepEqual(DEFAULT_INITIAL_RELATIONSHIP, { affection: 30, trust: 30, attraction: 10, obsession: 0, fear: 0, aversion: 20 });
  const c = card({
    extensions: { lyris: { initial_relationship: { affection: 120, trust: -4, attraction: 44.6, obsession: "9", fear: null } } },
  });
  const r = readInitialRelationship(c);
  assert.equal(r.stored, true);
  assert.deepEqual(r.values, { affection: 100, trust: 0, attraction: 45, obsession: 0, fear: 0, aversion: 20 });
  // A broken lyris block is read as "not stored".
  assert.equal(readInitialRelationship(card({ extensions: { lyris: "x" } })).stored, false);
  assert.equal(readInitialRelationship(card({ extensions: { lyris: { initial_relationship: [1, 2] } } })).stored, false);
  assert.equal(clampEmotion(Number.NaN, 7), 7);
});

test("withInitialRelationship merges and keeps every other extensions key", () => {
  const c = card({
    extensions: {
      character_book: { entries: [{ keys: ["a"] }] },
      lyris: { template: "ha-vy", role: "Chủ tiệm sách", initial_relationship: { affection: 70 } },
    },
  });
  const out = withInitialRelationship(c, { fear: 40 });
  assert.deepEqual(out.extensions.character_book, { entries: [{ keys: ["a"] }] });
  const lyris = out.extensions.lyris as Record<string, unknown>;
  assert.equal(lyris.template, "ha-vy");
  assert.equal(lyris.role, "Chủ tiệm sách");
  assert.deepEqual(lyris.initial_relationship, { affection: 70, trust: 30, attraction: 10, obsession: 0, fear: 40, aversion: 20 });
  // The input is not mutated.
  assert.deepEqual((c.extensions.lyris as Record<string, unknown>).initial_relationship, { affection: 70 });
  assert.equal(isDirty(c, out), true);
  assert.equal(isDefaultRelationship(readInitialRelationship(card()).values), true);
  assert.equal(isDefaultRelationship(readInitialRelationship(out).values), false);
});

test("prepareForSave always stores the starting emotions", () => {
  const out = prepareForSave(card({ extensions: { v2: { creator: "me" } } }));
  assert.deepEqual(out.extensions.v2, { creator: "me" });
  assert.deepEqual((out.extensions.lyris as Record<string, unknown>).initial_relationship, DEFAULT_INITIAL_RELATIONSHIP);
  assert.equal(EMOTION_KEYS.length, 6);
  for (const k of EMOTION_KEYS) assert.ok(EMOTION_LABEL[k] && EMOTION_HINT[k]);
});

test("filterCards searches name, role, tags and description; summaryRole reads defensively", () => {
  const rows = [
    { name: "Hạ Vy", description: "", tags: ["chữa lành"], role: "Chủ tiệm sách mùa thu" },
    { name: "Lạc Dương", description: "Lớp trưởng lạnh lùng", tags: [] },
    { name: "Tạ Vân Lan", description: "", tags: ["Cổ trang"] },
  ];
  assert.deepEqual(filterCards(rows, "").length, 3);
  assert.deepEqual(filterCards(rows, "  TIỆM sách ").map((r) => r.name), ["Hạ Vy"]);
  assert.deepEqual(filterCards(rows, "cổ trang").map((r) => r.name), ["Tạ Vân Lan"]);
  assert.deepEqual(filterCards(rows, "lớp trưởng").map((r) => r.name), ["Lạc Dương"]);
  assert.equal(summaryRole(rows[1]), "");
  assert.equal(summaryRole({ role: 3 }), "");
  assert.equal(summaryRole(null), "");
});

test("formatRelativeTime", () => {
  const now = Date.parse("2026-11-12T10:00:00Z");
  assert.equal(formatRelativeTime(null, now), "");
  assert.equal(formatRelativeTime("không phải ngày", now), "");
  assert.equal(formatRelativeTime("2026-11-12T09:59:30Z", now), "vừa xong");
  assert.equal(formatRelativeTime("2026-11-12T09:55:00", now), "5 phút trước"); // no zone = UTC
  assert.equal(formatRelativeTime("2026-11-12T07:00:00Z", now), "3 giờ trước");
  assert.equal(formatRelativeTime("2026-11-10T10:00:00Z", now), "2 ngày trước");
  assert.match(formatRelativeTime("2026-10-01T10:00:00Z", now), /1\/10\/2026/);
});

test("narration override is stored in extensions.lyris and keeps other keys", () => {
  const base = { ...emptyCard(), extensions: { lyris: { initial_relationship: { affection: 40 } }, other: 1 } };
  const set = withNarrationOverride(base, "  hắn ");
  assert.equal(readNarrationOverride(set), "hắn");
  assert.deepEqual((set.extensions.lyris as Record<string, unknown>).initial_relationship, { affection: 40 });
  assert.equal(set.extensions.other, 1);
  const cleared = withNarrationOverride(set, "");
  assert.equal(readNarrationOverride(cleared), "");
  assert.equal("narration_character" in (cleared.extensions.lyris as Record<string, unknown>), false);
  const both = withNarrationOverride({ ...base, extensions: { lyris: { narration_character: { vi: "y", en: "he" } } } }, "");
  assert.deepEqual((both.extensions.lyris as Record<string, unknown>).narration_character, { en: "he" });
});

test("prepareForSave cleans signature lines; validateCard blocks too many or too long", () => {
  const card = { ...emptyCard(), name: "Hạ Vy", extensions: { lyris: { signature_lines: ["“Trà gừng nè.”", "", "  "] } } };
  const saved = prepareForSave(card);
  assert.deepEqual((saved.extensions.lyris as Record<string, unknown>).signature_lines, ["Trà gừng nè."]);
  assert.deepEqual(validateCard(card), []);
  const many = { ...card, extensions: { lyris: { signature_lines: ["a", "b", "c", "d"] } } };
  assert.ok(validateCard(many).includes("Tối đa 3 lời nói đặc trưng."));
  const blank = prepareForSave({ ...card, extensions: { lyris: { signature_lines: [" "] } } });
  assert.equal("signature_lines" in (blank.extensions.lyris as Record<string, unknown>), false);
});
