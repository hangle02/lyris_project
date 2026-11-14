import { test } from "node:test";
import assert from "node:assert/strict";
import {
  dominantEmotion,
  foldText,
  formatStoryTime,
  greetingFor,
  matchesStory,
  parseApiTime,
  previewOf,
  sortByActivity,
  storyChips,
} from "./logic.ts";

test("greetingFor: five parts of the day, no emoji", () => {
  assert.equal(greetingFor(5), "Nắng lên rồi, hôm nay trò chuyện cùng ai?");
  assert.equal(greetingFor(10), "Nắng lên rồi, hôm nay trò chuyện cùng ai?");
  assert.equal(greetingFor(11), "Trưa rồi, nghỉ tay trò chuyện một chút nhé?");
  assert.equal(greetingFor(14), "Chiều dịu dàng, ai đang chờ bạn ghé thăm?");
  assert.equal(greetingFor(18), "Tối rồi, kể nhau nghe chuyện hôm nay?");
  assert.equal(greetingFor(22), "Đêm muộn rồi, ai đang thức đợi bạn?");
  assert.equal(greetingFor(0), "Đêm muộn rồi, ai đang thức đợi bạn?");
  assert.equal(greetingFor(4), "Đêm muộn rồi, ai đang thức đợi bạn?");
  assert.equal(greetingFor(24 + 6), greetingFor(6));
  for (let h = 0; h < 24; h++) assert.doesNotMatch(greetingFor(h), /\p{Extended_Pictographic}/u);
});

test("parseApiTime: Z, offset and naive UTC strings", () => {
  assert.equal(parseApiTime("2026-11-12T10:00:00Z"), Date.UTC(2026, 10, 12, 10));
  assert.equal(parseApiTime("2026-11-12T10:00:00.250Z"), Date.UTC(2026, 10, 12, 10, 0, 0, 250));
  assert.equal(parseApiTime("2026-11-12 10:00:00"), Date.UTC(2026, 10, 12, 10));
  assert.equal(parseApiTime("2026-11-12T10:00:00"), Date.UTC(2026, 10, 12, 10));
  assert.equal(parseApiTime("2026-11-12T17:00:00+07:00"), Date.UTC(2026, 10, 12, 10));
  assert.ok(Number.isNaN(parseApiTime(null)));
  assert.ok(Number.isNaN(parseApiTime("")));
  assert.ok(Number.isNaN(parseApiTime("không phải ngày")));
});

test("formatStoryTime: today, yesterday, this year, older", () => {
  const now = new Date(2026, 10, 12, 23, 40); // local time
  const iso = (d: Date) => d.toISOString();
  assert.equal(formatStoryTime(iso(new Date(2026, 10, 12, 23, 15)), now), "23:15");
  assert.equal(formatStoryTime(iso(new Date(2026, 10, 12, 0, 5)), now), "00:05");
  assert.equal(formatStoryTime(iso(new Date(2026, 10, 11, 23, 59)), now), "Hôm qua");
  assert.equal(formatStoryTime(iso(new Date(2026, 10, 11, 0, 0)), now), "Hôm qua");
  assert.equal(formatStoryTime(iso(new Date(2026, 10, 10, 23, 59)), now), "10/11");
  assert.equal(formatStoryTime(iso(new Date(2026, 0, 3, 8, 0)), now), "03/01");
  assert.equal(formatStoryTime(iso(new Date(2025, 11, 31, 8, 0)), now), "31/12/2025");
  assert.equal(formatStoryTime(null, now), "");
  // A clock slightly ahead of ours still reads as today.
  assert.equal(formatStoryTime(iso(new Date(2026, 10, 12, 23, 41)), now), "23:41");
});

test("formatStoryTime: yesterday across a month boundary", () => {
  const now = new Date(2026, 11, 1, 9, 0);
  assert.equal(formatStoryTime(new Date(2026, 10, 30, 22, 0).toISOString(), now), "Hôm qua");
  assert.equal(formatStoryTime(new Date(2026, 10, 29, 22, 0).toISOString(), now), "29/11");
});

test("foldText: diacritics, đ, case and spaces", () => {
  assert.equal(foldText("  Hạ  Vy "), "ha vy");
  assert.equal(foldText("Đà Lạt"), "da lat");
  assert.equal(foldText("Tạ Vân Lan"), "ta van lan");
  assert.equal(foldText("Ngữ Yên"), "ngu yen");
});

test("matchesStory: every word, any field, no diacritics needed", () => {
  const s = {
    card_name: "Hạ Vy",
    title: "Gác xép mùi gỗ thông",
    card_role: "Chủ tiệm sách mùa thu",
    persona_name: "Lâm",
    location: null,
  };
  assert.ok(matchesStory(s, ""));
  assert.ok(matchesStory(s, "   "));
  assert.ok(matchesStory(s, "ha vy"));
  assert.ok(matchesStory(s, "Hạ"));
  assert.ok(matchesStory(s, "tiem sach"));
  assert.ok(matchesStory(s, "vy gac"));
  assert.ok(matchesStory(s, "lâm"));
  assert.ok(!matchesStory(s, "khang"));
  assert.ok(!matchesStory(s, "vy khang"));
  assert.ok(matchesStory({ ...s, location: "Đà Lạt" }, "da lat"));
  assert.ok(matchesStory({ card_name: "A", title: "B" }, "a b"));
});

test("dominantEmotion: strongest non-zero, first on a tie", () => {
  assert.equal(dominantEmotion(null), null);
  const zero = { affection: 0, trust: 0, attraction: 0, obsession: 0, fear: 0, aversion: 0, directive: null };
  assert.equal(dominantEmotion(zero), null);
  assert.deepEqual(dominantEmotion({ ...zero, affection: 91, trust: 40 }), {
    key: "affection",
    label: "Thương mến",
    value: 91,
  });
  assert.deepEqual(dominantEmotion({ ...zero, trust: 50, fear: 50 }), { key: "trust", label: "Tin cậy", value: 50 });
  assert.deepEqual(dominantEmotion({ ...zero, aversion: 130 }), { key: "aversion", label: "Khoảng cách", value: 100 });
});

test("previewOf: player turns are prefixed, blank is null", () => {
  assert.equal(previewOf({ last_preview: "Cô khẽ cười.", last_role: "assistant" }), "Cô khẽ cười.");
  assert.equal(previewOf({ last_preview: "Chào  em\n nhé", last_role: "user" }), "Bạn: Chào em nhé");
  assert.equal(previewOf({ last_preview: "   ", last_role: "assistant" }), null);
  assert.equal(previewOf({ last_preview: null, last_role: null }), null);
});

test("sortByActivity: newest first, unknown times last in API order", () => {
  const list = [
    { id: 1, updated_at: "2026-11-10T10:00:00Z", created_at: null },
    { id: 2, updated_at: null, created_at: null },
    { id: 3, updated_at: "2026-11-12T10:00:00Z", created_at: null },
    { id: 4, updated_at: null, created_at: "2026-11-11T10:00:00Z" },
    { id: 5, updated_at: null, created_at: null },
  ];
  assert.deepEqual(
    sortByActivity(list).map((s) => s.id),
    [3, 4, 1, 2, 5],
  );
});

test("storyChips: dominant emotion and place from the story row (Phase 3)", () => {
  assert.deepEqual(storyChips({ dominant_emotion: { key: "affection", value: 91 }, location: " Gác xép  mùi gỗ thông " }), {
    emotion: { key: "affection", label: "Thương mến", value: 91, text: "Thương mến 91%" },
    location: "Gác xép mùi gỗ thông",
  });
  assert.equal(storyChips({ dominant_emotion: { key: "obsession", value: 140.4 } }).emotion?.text, "Nhung nhớ 100%");
  // No real data yet, or an older server: no chips.
  assert.deepEqual(storyChips({ dominant_emotion: null, location: null }), { emotion: null, location: null });
  assert.deepEqual(storyChips({}), { emotion: null, location: null });
  assert.equal(storyChips({ location: "   " }).location, null);
  // Defensive: unknown key or a non-number value.
  assert.equal(storyChips({ dominant_emotion: { key: "joy", value: 50 } as never }).emotion, null);
  assert.equal(storyChips({ dominant_emotion: { key: "trust", value: "50" } as never }).emotion, null);
});
