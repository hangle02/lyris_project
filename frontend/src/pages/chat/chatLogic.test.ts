import { test } from "node:test";
import assert from "node:assert/strict";
import type { PersonaOut } from "../../types.ts";
import {
  clampScore,
  EMOTIONS,
  EMPTY_EXTRAS,
  headerSubtitle,
  headerSubtitleText,
  MAX_SUGGESTIONS,
  momentLine,
  normalizeExtras,
  personaFace,
  sceneLine,
  lastReplyMode,
  mergeStory,
  rollbackPatch,
  withoutMemory,
} from "./chatLogic.ts";

test("normalizeExtras: today's empty payload", () => {
  const empty = {
    relationship: null,
    suggestions: [],
    moment: null,
    lore_tags: [],
    location: null,
    in_world_time: null,
  };
  assert.deepEqual(normalizeExtras(empty), EMPTY_EXTRAS);
  assert.deepEqual(normalizeExtras(null), EMPTY_EXTRAS);
  assert.deepEqual(normalizeExtras("oops"), EMPTY_EXTRAS);
  assert.deepEqual(normalizeExtras({}), EMPTY_EXTRAS);
});

test("normalizeExtras: filled payload, wrong types dropped", () => {
  const got = normalizeExtras({
    relationship: { affection: 91.4, trust: "64", attraction: -3, obsession: 140, fear: null, directive: "  Dịu dàng,  ân cần. " },
    suggestions: ["  Khẽ nắm tay cô ấy ", 3, "", "Khẽ nắm tay cô ấy", "“Vì biết Vy vẫn đang thức đợi mình mà.”"],
    moment: { text: "Đón nhận sự quan tâm dịu dàng từ Hạ Vy", effect: "+Thương mến" },
    lore_tags: ["Tiệm Sách Mùa Thu", { x: 1 }],
    location: " Gác xép mùi gỗ thông ",
    in_world_time: 2315,
    extra_field: true,
  });
  assert.deepEqual(got, {
    relationship: {
      affection: 91,
      trust: 64,
      attraction: 0,
      obsession: 100,
      fear: 0,
      aversion: 0,
      directive: "Dịu dàng, ân cần.",
    },
    suggestions: ["Khẽ nắm tay cô ấy", "“Vì biết Vy vẫn đang thức đợi mình mà.”"],
    moment: { text: "Đón nhận sự quan tâm dịu dàng từ Hạ Vy", effect: "+Thương mến" },
    lore_tags: ["Tiệm Sách Mùa Thu"],
    lore_available: false,
    lore_count: 0,
    location: "Gác xép mùi gỗ thông",
    in_world_time: null,
    memories: [],
    pending: false,
    unprocessed_turns: 0,
    memory_search: "keyword",
    summary: null,
  });
});

test("normalizeExtras: Phase 4 world fields, with and without lore_available", () => {
  const got = normalizeExtras({ lore_tags: Array.from({ length: 60 }, (_, i) => `Mục ${i}`), lore_available: true, lore_count: 61 });
  assert.equal(got.lore_available, true);
  assert.equal(got.lore_count, 61);
  assert.equal(got.lore_tags.length, 50);
  const old = normalizeExtras({ lore_tags: ["Hôn ước"] });
  assert.equal(old.lore_available, false);
  assert.equal(old.lore_count, 0);
  assert.equal(normalizeExtras({ lore_available: "yes", lore_count: -3 }).lore_count, 0);
  assert.equal(normalizeExtras({ lore_available: "yes" }).lore_available, false);
});

test("normalizeExtras: a moment without text is no moment", () => {
  assert.equal(normalizeExtras({ moment: { text: "  ", effect: "+Tin cậy" } }).moment, null);
  assert.deepEqual(normalizeExtras({ moment: { text: "Lần đầu gặp lại" } }).moment, { text: "Lần đầu gặp lại", effect: null });
});

test("clampScore", () => {
  assert.equal(clampScore(0), 0);
  assert.equal(clampScore(49.5), 50);
  assert.equal(clampScore(Infinity), 0);
  assert.equal(clampScore("abc"), 0);
});

test("EMOTIONS lists the six dimensions in DESIGN.md order", () => {
  assert.deepEqual(
    EMOTIONS.map((e) => e.key),
    ["affection", "trust", "attraction", "obsession", "fear", "aversion"],
  );
});

test("headerSubtitle prefers the in-world place and time", () => {
  const story = { title: "Hạ Vy & Ngọc Anh" };
  assert.deepEqual(headerSubtitle(story, EMPTY_EXTRAS), { role: null, detail: "Hạ Vy & Ngọc Anh" });
  assert.deepEqual(headerSubtitle(story, { ...EMPTY_EXTRAS, location: "Gác xép", in_world_time: "23:15" }), {
    role: null,
    detail: "Gác xép · 23:15",
  });
  assert.equal(headerSubtitle(story, { ...EMPTY_EXTRAS, in_world_time: "Chiều thu" }).detail, "Chiều thu");
});

test("headerSubtitle leads with the character's role, never twice", () => {
  const story = { title: "Tiệm sách mùa thu", card_role: " Chủ tiệm sách mùa thu " };
  const sub = headerSubtitle(story, EMPTY_EXTRAS);
  assert.deepEqual(sub, { role: "Chủ tiệm sách mùa thu", detail: "Tiệm sách mùa thu" });
  assert.equal(headerSubtitleText(sub), "Chủ tiệm sách mùa thu · Tiệm sách mùa thu");
  assert.deepEqual(headerSubtitle({ title: "chủ tiệm sách mùa thu", card_role: "Chủ tiệm sách mùa thu" }, EMPTY_EXTRAS), {
    role: "Chủ tiệm sách mùa thu",
    detail: "",
  });
  assert.equal(headerSubtitleText(headerSubtitle({ title: "X", card_role: "" }, EMPTY_EXTRAS)), "X");
});

test("momentLine", () => {
  assert.deepEqual(momentLine({ text: "Khoảnh khắc", effect: " " }), { text: "Khoảnh khắc", effect: null });
});

test("personaFace: persona avatar of the story, fallback to the story row name", () => {
  const personas = [
    { id: 1, name: "Ngọc Anh", gender: "female", description: "", story_count: 2, avatar_url: "/api/personas/1/avatar?v=a.webp" },
    { id: 2, name: "Gia Huy", gender: "male", description: "", story_count: 0, avatar_url: null },
  ] as PersonaOut[];
  assert.deepEqual(personaFace(personas, 1, "x"), { name: "Ngọc Anh", url: "/api/personas/1/avatar?v=a.webp" });
  assert.deepEqual(personaFace(personas, 2, "x"), { name: "Gia Huy", url: null });
  assert.deepEqual(personaFace(null, 1, "Ngọc Anh"), { name: "Ngọc Anh", url: null });
  assert.deepEqual(personaFace(personas, 9, "Đã đổi"), { name: "Đã đổi", url: null });
  assert.deepEqual(personaFace([], 9, "  "), { name: "Bạn", url: null });
});

test("normalizeExtras: Phase 3 fields (memories, pending, unprocessed turns, search mode, summary)", () => {
  const got = normalizeExtras({
    suggestions: ["Một", "Hai", "Ba", "Bốn"],
    memories: [
      { id: 7, story_id: 1, message_id: 40, turn_index: 12, kind: "memory", text: " Lâm Vãn hứa  quay lại ", importance: 9, created_at: "2026-11-13T10:00:00Z" },
      { id: 5, story_id: 1, message_id: 30, turn_index: 8, kind: "fact", subject: "Lâm Vãn", text: "Lâm Vãn thích trà sữa", importance: 3 },
      { id: 7, kind: "memory", text: "trùng id" },
      { id: null, kind: "memory", text: "không có id" },
      { id: 9, kind: "rumor", text: "kind lạ" },
      { id: 10, kind: "fact", text: "   " },
      "rác",
    ],
    pending: "yes",
    unprocessed_turns: 4,
    memory_search: "hybrid",
    summary: "  Hai người đã gặp nhau ở thư viện. ",
  });
  assert.equal(got.suggestions.length, MAX_SUGGESTIONS);
  assert.deepEqual(got.suggestions, ["Một", "Hai", "Ba"]);
  assert.deepEqual(got.memories, [
    { id: 7, story_id: 1, message_id: 40, turn_index: 12, kind: "memory", text: "Lâm Vãn hứa quay lại", subject: null, importance: 5, created_at: "2026-11-13T10:00:00Z" },
    { id: 5, story_id: 1, message_id: 30, turn_index: 8, kind: "fact", text: "Lâm Vãn thích trà sữa", subject: "Lâm Vãn", importance: 3, created_at: null },
  ]);
  assert.equal(got.pending, false, "only a real true counts as pending");
  assert.equal(got.unprocessed_turns, 4);
  assert.equal(got.memory_search, "hybrid");
  assert.equal(got.summary, "Hai người đã gặp nhau ở thư viện.");

  const odd = normalizeExtras({ pending: true, unprocessed_turns: -2, memory_search: "vector", memories: "x" });
  assert.equal(odd.pending, true);
  assert.equal(odd.unprocessed_turns, 0);
  assert.equal(odd.memory_search, "keyword");
  assert.deepEqual(odd.memories, []);
  assert.equal(normalizeExtras({ unprocessed_turns: 2.5 }).unprocessed_turns, 0);
});

test("withoutMemory drops one memory and keeps the object when nothing changes", () => {
  const extras = normalizeExtras({
    memories: [
      { id: 1, kind: "memory", text: "A" },
      { id: 2, kind: "fact", text: "B" },
    ],
  });
  assert.deepEqual(withoutMemory(extras, 1).memories.map((m) => m.id), [2]);
  assert.equal(withoutMemory(extras, 99), extras);
});

test("sceneLine: place · time", () => {
  assert.equal(sceneLine({ location: "Gác xép", in_world_time: "Chiều tối" }), "Gác xép · Chiều tối");
  assert.equal(sceneLine({ location: null, in_world_time: "Chiều tối" }), "Chiều tối");
  assert.equal(sceneLine({ location: " ", in_world_time: null }), "");
});

test("headerSubtitle: the scene replaces the title and keeps the role", () => {
  const sub = headerSubtitle(
    { title: "Tiệm sách", card_role: "Chủ tiệm sách mùa thu" },
    { ...EMPTY_EXTRAS, location: "Gác xép mùi gỗ thông", in_world_time: "Chiều tối" },
  );
  assert.deepEqual(sub, { role: "Chủ tiệm sách mùa thu", detail: "Gác xép mùi gỗ thông · Chiều tối" });
  assert.equal(headerSubtitleText(sub), "Chủ tiệm sách mùa thu · Gác xép mùi gỗ thông · Chiều tối");
});

test("lastReplyMode: mode of the newest active character reply", () => {
  assert.equal(lastReplyMode([]), null);
  assert.equal(lastReplyMode([{ role: "user", mode: "dm", is_active: true }]), null);
  assert.equal(
    lastReplyMode([
      { role: "assistant", mode: "story", is_active: true },
      { role: "user", mode: "dm", is_active: true },
    ]),
    "story",
  );
  assert.equal(
    lastReplyMode([
      { role: "assistant", mode: "story", is_active: true },
      { role: "assistant", mode: "dm", is_active: false },
    ]),
    "story",
  );
});

test("rollbackPatch: a refused thought-style save keeps a show-thoughts change saved meanwhile", () => {
  type S = { thought_style: string; show_thoughts: boolean; mode: string };
  const before: S = { thought_style: "inline", show_thoughts: true, mode: "story" };
  // Optimistic style change, then the player switches thoughts off (that save succeeds).
  let cur: S = { ...before, thought_style: "end" };
  cur = { ...cur, show_thoughts: false };
  cur = rollbackPatch(cur, before, { thought_style: "end" });
  assert.deepEqual(cur, { thought_style: "inline", show_thoughts: false, mode: "story" });
  // A key changed again by someone else is not put back either.
  assert.equal(rollbackPatch({ ...before, thought_style: "inline2" }, before, { thought_style: "end" }).thought_style, "inline2");
});

test("mergeStory: an earlier response does not undo a key another save is still holding", () => {
  type S = { thought_style: string; show_thoughts: boolean; updated_at: string };
  const cur: S = { thought_style: "end", show_thoughts: false, updated_at: "1" };
  const response: Partial<S> = { thought_style: "end", show_thoughts: true, updated_at: "2" };
  assert.deepEqual(mergeStory(cur, response, ["show_thoughts"]), { thought_style: "end", show_thoughts: false, updated_at: "2" });
  assert.deepEqual(mergeStory(cur, response, []), { thought_style: "end", show_thoughts: true, updated_at: "2" });
  assert.deepEqual(mergeStory(cur, response, new Map([["show_thoughts", 1]]).keys()).show_thoughts, false);
});

test("waitingLine: the busy line of docs/auth.md §5.5, with the character's name", async () => {
  const { waitingLine } = await import("./chatLogic.ts");
  assert.equal(waitingLine("Hạ Vy"), "Có người khác đang trò chuyện. Hạ Vy sẽ trả lời ngay sau.");
  assert.equal(waitingLine("  "), "Có người khác đang trò chuyện. Nhân vật sẽ trả lời ngay sau.");
  assert.doesNotMatch(waitingLine("Hạ Vy"), /model|ollama|slot/i);
});
