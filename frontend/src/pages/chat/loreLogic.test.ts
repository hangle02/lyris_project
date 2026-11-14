import { test } from "node:test";
import assert from "node:assert/strict";
import type { UnlockedLore } from "../../types.ts";
import {
  loreSignature,
  normalizeStoryLore,
  secretGroupTitle,
  secretLabel,
  splitUnlocked,
  studioWorldHref,
  unlockedEmptyLine,
} from "./loreLogic.ts";

function u(id: number, audience: UnlockedLore["audience"]): UnlockedLore {
  return { entry_id: id, title: `Mục ${id}`, category: "lore", audience, content: "x", first_turn: 3, last_turn: 7, turns: 2 };
}

test("splitUnlocked: open = everyone + player, secret = character; no secrets when thoughts are not read", () => {
  const list = [u(1, "everyone"), u(2, "character"), u(3, "player")];
  const on = splitUnlocked(list, true);
  assert.deepEqual(on.open.map((e) => e.entry_id), [1, 3]);
  assert.deepEqual(on.secret.map((e) => e.entry_id), [2]);
  const off = splitUnlocked(list, false);
  assert.deepEqual(off.open.map((e) => e.entry_id), [1, 3]);
  assert.deepEqual(off.secret, []);
});

test("unlockedEmptyLine: no world book, nothing unlocked yet, or a list", () => {
  const none = splitUnlocked([], true);
  assert.equal(unlockedEmptyLine({ available: false }, none, "Lục Bắc Uyên"), "Lục Bắc Uyên chưa có sổ thế giới.");
  assert.equal(
    unlockedEmptyLine({ available: true }, none, "Lục Bắc Uyên"),
    "Chưa mở khoá điều gì. Khi story nhắc tới người, nơi chốn hay chuyện cũ trong thế giới của Lục Bắc Uyên, chúng sẽ hiện ở đây.",
  );
  // Only a secret, thoughts hidden: nothing to show, not even a count.
  assert.match(unlockedEmptyLine({ available: true }, splitUnlocked([u(2, "character")], false), "A") ?? "", /^Chưa mở khoá/);
  assert.equal(unlockedEmptyLine({ available: true }, splitUnlocked([u(1, "everyone")], false), "A"), null);
});

test("loreSignature changes with the count (secrets) and the titles", () => {
  assert.equal(loreSignature(null), "");
  assert.equal(loreSignature({ lore_tags: ["Hôn ước"], lore_count: 2 }), "2|Hôn ước");
  assert.notEqual(loreSignature({ lore_tags: ["Hôn ước"], lore_count: 3 }), loreSignature({ lore_tags: ["Hôn ước"], lore_count: 2 }));
  assert.equal(loreSignature({ lore_tags: [] }), "0|");
});

test("normalizeStoryLore drops broken rows and 'others'", () => {
  const got = normalizeStoryLore({
    available: true,
    can_edit: true,
    card_id: 4,
    entries: [
      { entry_id: 31, title: " Hôn ước ", category: "lore", audience: "everyone", content: "Năm 1979", first_turn: 3, last_turn: 7, turns: 3 },
      { entry_id: 32, title: "X", audience: "others" },
      { entry_id: 31, title: "Trùng", audience: "player" },
      { title: "Không id", audience: "player" },
      "rác",
      { entry_id: 26, title: "Hứa Tri Ý", category: "weird", audience: "player" },
    ],
  });
  assert.equal(got.card_id, 4);
  assert.equal(got.can_edit, true);
  assert.deepEqual(got.entries.map((e) => [e.entry_id, e.title, e.category, e.audience]), [
    [31, "Hôn ước", "lore", "everyone"],
    [26, "Hứa Tri Ý", "lore", "player"],
  ]);
  assert.deepEqual(normalizeStoryLore(null), { available: false, can_edit: false, card_id: 0, entries: [] });
});

test("copy helpers", () => {
  assert.equal(studioWorldHref(4), "#/studio/4?section=world");
  assert.equal(secretGroupTitle("Lục Bắc Uyên"), "Điều Lục Bắc Uyên giữ trong lòng");
  assert.equal(secretLabel(" "), "Một điều Nhân vật giữ trong lòng, chạm để đọc");
});
