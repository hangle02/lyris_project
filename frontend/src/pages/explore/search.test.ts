// F47 (wiki/features/F47-tim-nhan-vat.md): the "Tìm nhân vật" box of Khám phá.
import { mock, test } from "node:test";
import assert from "node:assert/strict";
import { buildItems, sharedItems } from "./logic.ts";
import type { ExploreItem } from "./logic.ts";
import {
  DEBOUNCE_MS,
  SEARCH_COPY,
  createDebounced,
  createSearchTracker,
  filterItems,
  foldVietnamese,
  matchesQuery,
  noResultsText,
} from "./search.ts";
import type { CardSummary, PublicCardSummary, TemplateInfo } from "../../types.ts";

function template(slug: string, name: string, extra: Partial<TemplateInfo["card"]> = {}, vibes: string[] = []): TemplateInfo {
  return {
    slug,
    featured: false,
    vibes,
    installed_card_id: null,
    card: {
      name,
      role: "",
      description: "",
      tags: [],
      language: "vi",
      scenario: "",
      ...extra,
    },
  } as unknown as TemplateInfo;
}

function card(id: number, name: string, extra: Record<string, unknown> = {}): CardSummary {
  return {
    id,
    name,
    tags: [],
    description: "",
    language: "vi",
    avatar_url: null,
    creator_handle: "ban",
    visibility: "private",
    ...extra,
  } as unknown as CardSummary;
}

function shared(id: number, name: string, extra: Record<string, unknown> = {}): PublicCardSummary {
  return {
    id,
    name,
    role: "",
    tags: [],
    description: "",
    language: "vi",
    avatar_url: null,
    creator_handle: "khach",
    updated_at: "2026-11-14T00:00:00Z",
    ...extra,
  } as unknown as PublicCardSummary;
}

const HA_VY = template("ha-vy", "Hạ Vy", {
  role: "Chủ tiệm sách mùa thu",
  description:
    '26 tuổi, chủ tiệm sách cũ "Mùa Thu" nằm lưng chừng một con dốc gần hồ Xuân Hương, Đà Lạt. {{user}} là vị khách lạ ghé tiệm vào một chiều mưa.',
  tags: ["chữa lành", "đà lạt", "tiệm sách"],
}, ["Chữa lành", "Dịu dàng"]);
const KHANG = template("tran-minh-khang", "Trần Minh Khang", {
  role: "Kiến trúc sư hướng dẫn thực tập",
  description: "27 tuổi, kiến trúc sư ở Sài Gòn.",
  tags: ["sài gòn", "công sở"],
}, ["Dịu dàng"]);
const MORWENNA = template("morwenna-penrose", "Morwenna Penrose", {
  role: "Lighthouse keeper on the Cornish coast",
  description: "34, caretaker of the old lighthouse.",
  tags: ["cornwall", "lighthouse"],
  language: "en",
}, ["Bí ẩn nội tâm"]);

function items(): ExploreItem[] {
  return buildItems([card(5, "Lạc Dương", { role: "Thanh mai trúc mã", tags: ["vườn trường"] })], [HA_VY, KHANG, MORWENNA]);
}

const names = (list: ExploreItem[]) => list.map((i) => i.name);

test("foldVietnamese: no diacritics, đ→d, lowercase, single spaces", () => {
  assert.equal(foldVietnamese("Hạ Vy ĐÀ LẠT  ở  Huế"), "ha vy da lat o hue");
  assert.equal(foldVietnamese("  Tạ Vân Lan\n"), "ta van lan");
  assert.equal(foldVietnamese("Đường đến tiệm sách"), "duong den tiem sach");
  assert.equal(foldVietnamese(""), "");
});

test("matchesQuery: Hạ Vy by name, case, part of a name, the about text; every word must match", () => {
  const hv = items().find((i) => i.name === "Hạ Vy");
  assert.ok(hv);
  for (const q of ["ha vy", "HẠ VY", "vy", "tiem sach", "da lat", "vy da lat", "  ha   vy  "]) assert.equal(matchesQuery(hv, q), true, q);
  for (const q of ["vy khang", "vy morwenna", "zzqxy"]) assert.equal(matchesQuery(hv, q), false, q);
  assert.deepEqual(names(filterItems(items(), { query: "vy morwenna", vibe: null })), []);
  assert.deepEqual(names(filterItems(items(), { query: "ha vy", vibe: null })), ["Hạ Vy"]);
});

test("matchesQuery: every word matches the START of a word (not the middle of one); punctuation splits words", () => {
  const list = sharedItems(
    [
      shared(11, "Lão Thành", { role: "Thợ rèn", description: "Ở nhà một mình, ba con mèo.", tags: [] }),
      shared(12, "Hải Đăng", { role: "Người gác hải đăng", description: "Trầm tính.", tags: ["biển"] }),
    ],
    "ban",
  );
  const thanh = list.find((i) => i.name === "Lão Thành");
  const haiDang = list.find((i) => i.name === "Hải Đăng");
  assert.ok(thanh && haiDang);
  // "ha" starts "Hải" but only sits inside "thành", "nhà": not a match for Lão Thành.
  assert.equal(matchesQuery(haiDang, "ha"), true);
  assert.equal(matchesQuery(thanh, "ha"), false, "'ha' inside 'thành'/'nhà' is not a match");
  assert.deepEqual(names(filterItems(list, { query: "ha", vibe: null })), ["Hải Đăng"]);
  for (const q of ["thanh", "nha", "nh", "lao th", "meo", "tho ren"]) assert.equal(matchesQuery(thanh, q), true, q);
  for (const q of ["anh", "ren tho x", "eo"]) assert.equal(matchesQuery(thanh, q), false, q);
  // Punctuation in the text or in the box splits words: "mình," and "da-lat".
  assert.equal(matchesQuery(thanh, "minh"), true);
  const hv = items().find((i) => i.name === "Hạ Vy");
  assert.ok(hv);
  assert.equal(matchesQuery(hv, "da-lat"), true);
  assert.equal(matchesQuery(hv, "vy,"), true);
  assert.equal(matchesQuery(hv, "a"), false, "no word of Hạ Vy starts with 'a'");
});

test("filterItems: name, role, tags and about text of all three kinds of cells; AND with the vibe; empty query keeps the list", () => {
  const all = items();
  // card (own), template, shared
  assert.deepEqual(names(filterItems(all, { query: "truc ma", vibe: null })), ["Lạc Dương"], "role of an own card");
  assert.deepEqual(names(filterItems(all, { query: "vuon truong", vibe: null })), ["Lạc Dương"], "tag of an own card");
  assert.deepEqual(names(filterItems(all, { query: "kien truc su", vibe: null })), ["Trần Minh Khang"], "role of a template");
  assert.deepEqual(names(filterItems(all, { query: "caretaker", vibe: null })), ["Morwenna Penrose"], "about text");
  const others = sharedItems(
    [shared(9, "Hải Đăng", { role: "Người gác hải đăng", description: "Trầm tính, ở đảo xa.", tags: ["biển"] })],
    "ban",
  );
  assert.deepEqual(names(filterItems(others, { query: "bien", vibe: null })), ["Hải Đăng"], "tag of a shared card");
  assert.deepEqual(names(filterItems(others, { query: "dao xa", vibe: null })), ["Hải Đăng"], "about text of a shared card");
  assert.deepEqual(names(filterItems(others, { query: "nguoi gac", vibe: null })), ["Hải Đăng"], "role of a shared card");
  // AND with the vibe chip.
  assert.deepEqual(names(filterItems(all, { query: "", vibe: "dịu dàng" })), ["Hạ Vy", "Trần Minh Khang"]);
  assert.deepEqual(names(filterItems(all, { query: "khang", vibe: "dịu dàng" })), ["Trần Minh Khang"]);
  assert.deepEqual(names(filterItems(all, { query: "ha vy", vibe: "bí ẩn nội tâm" })), [], "Hạ Vy has no such vibe");
  // Empty or blank: the same list, same order (the very same items).
  for (const q of ["", "   ", "\n"]) assert.deepEqual(filterItems(all, { query: q, vibe: null }), all, JSON.stringify(q));
  // Results keep the grid order.
  assert.deepEqual(names(all), ["Lạc Dương", "Hạ Vy", "Trần Minh Khang", "Morwenna Penrose"]);
  assert.deepEqual(names(filterItems(all, { query: "tuoi", vibe: null })), ["Hạ Vy", "Trần Minh Khang"]);
  assert.deepEqual(names(filterItems([...all].reverse(), { query: "tuoi", vibe: null })), ["Trần Minh Khang", "Hạ Vy"]);
});

test("useDebounced core: the value changes only 250 ms after the last change (5 keys 100 ms apart: one filter)", () => {
  mock.timers.enable({ apis: ["setTimeout"] });
  try {
    const seen: string[] = [];
    const d = createDebounced("", DEBOUNCE_MS, (v) => seen.push(v));
    assert.equal(DEBOUNCE_MS, 250);
    for (const ch of ["h", "ha", "ha ", "ha v", "ha vy"]) {
      d.set(ch);
      mock.timers.tick(100);
    }
    assert.deepEqual(seen, [], "still typing");
    assert.equal(d.get(), "");
    mock.timers.tick(149);
    assert.deepEqual(seen, []);
    mock.timers.tick(1);
    assert.deepEqual(seen, ["ha vy"]);
    assert.equal(d.get(), "ha vy");
    // Clearing the box ("Xoá tìm kiếm") is at once.
    d.set("", { now: true });
    assert.deepEqual(seen, ["ha vy", ""]);
    d.set("x");
    d.cancel();
    mock.timers.tick(1000);
    assert.deepEqual(seen, ["ha vy", ""], "cancelled on unmount");
  } finally {
    mock.timers.reset();
  }
});

test("explore_searched: only has_results, at most once per distinct search after the debounce; never for an empty box", () => {
  const sent: Record<string, unknown>[] = [];
  const t = createSearchTracker((props) => sent.push(props));
  t.settled("ha vy", true);
  t.settled("ha vy", true);
  t.settled("  HA  vy ", true); // the same search
  t.settled("", false);
  t.settled("zzqxy", false);
  t.settled("ha vy", true); // again after another search: a new search
  assert.deepEqual(sent, [{ has_results: true }, { has_results: false }, { has_results: true }]);
  for (const p of sent) assert.deepEqual(Object.keys(p), ["has_results"]);
  assert.ok(!JSON.stringify(sent).includes("vy"));
});

test("the search words", () => {
  assert.equal(SEARCH_COPY.placeholder, "Tìm nhân vật");
  assert.equal(SEARCH_COPY.label, "Tìm nhân vật theo tên, tag hoặc giới thiệu");
  assert.equal(SEARCH_COPY.clear, "Xoá tìm kiếm");
  assert.equal(noResultsText("zzqxy"), "Không tìm thấy nhân vật nào cho “zzqxy”.");
  assert.equal(noResultsText("  ha vy "), "Không tìm thấy nhân vật nào cho “ha vy”.");
});
