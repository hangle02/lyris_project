import { test } from "node:test";
import assert from "node:assert/strict";
import type { LoreEntry, LoreImportResult } from "../../types.ts";
import {
  audienceBadge,
  audienceOf,
  activeQuery,
  bookConvertedOnSave,
  bookEntryCount,
  canonTone,
  cleanInput,
  contentWarnings,
  deletePrompt,
  filterEntries,
  groupEntries,
  importFileError,
  importItemGroups,
  importNotes,
  importSummaryLines,
  isNameLike,
  keysLine,
  keyWarnings,
  knowOptions,
  knownByFor,
  missingToggleLabel,
  nothingNew,
  playerOnlyLine,
  sameName,
  searchShown,
  validateEntry,
  withoutBook,
} from "./loreLogic.ts";

const CHAR = "Lục Bắc Uyên";

function entry(over: Partial<LoreEntry>): LoreEntry {
  return {
    id: 1,
    card_id: 4,
    slug: "manual:abc",
    title: "Mục",
    category: "lore",
    keys: [],
    known_by: ["*"],
    content: "",
    source: "manual",
    edited: false,
    enabled: true,
    priority: 0,
    position: 0,
    extra: {},
    created_at: null,
    updated_at: null,
    audience: "everyone",
    warnings: [],
    ...over,
  };
}

function result(over: Partial<LoreImportResult>): LoreImportResult {
  return {
    dry_run: true,
    created: 0,
    updated: 0,
    unchanged: 0,
    kept_edited: 0,
    deleted: 0,
    missing: 0,
    skipped_removed: 0,
    player_only: [],
    dropped_sentences: [],
    items: [],
    notes: [],
    warnings: [],
    ...over,
  };
}

test("canonTone / sameName: tone placement and NFD do not matter, diacritics do", () => {
  assert.equal(canonTone("hoà"), "hòa");
  assert.equal(canonTone("thuý"), "thúy");
  assert.equal(canonTone("quý"), "quý");
  assert.equal(canonTone("hoàng"), "hoàng");
  assert.equal(sameName("Nhân Hoà", "Nhân Hòa"), true);
  assert.equal(sameName("Lục".normalize("NFD"), "Lục"), true);
  assert.equal(sameName("Lục Bắc Uyên (陆北渊)", "lục bắc uyên"), true);
  assert.equal(sameName("Lúc", "Lục"), false);
  assert.equal(sameName("", ""), false);
});

test("audienceOf mirrors the backend order: everyone > character > player > others", () => {
  assert.equal(audienceOf(["*"], CHAR), "everyone");
  assert.equal(audienceOf(["{{char}}"], CHAR), "character");
  assert.equal(audienceOf(["Lục Bắc Uyên"], CHAR), "character");
  assert.equal(audienceOf(["{{user}}", "Lục Bắc Uyên"], CHAR), "character");
  assert.equal(audienceOf(["{{user}}"], CHAR), "player");
  assert.equal(audienceOf(["{{user}}", "Hạ Trì"], CHAR), "player");
  assert.equal(audienceOf(["Hạ Trì"], CHAR), "others");
  assert.equal(audienceOf([], CHAR), "others");
});

test("knowOptions / knownByFor: a fourth read-only choice keeps another person's name", () => {
  assert.deepEqual(
    knowOptions(CHAR, ["*"]).map((o) => o.label),
    ["Mọi người", "Chỉ Lục Bắc Uyên", "Chỉ bạn"],
  );
  const others = knowOptions(CHAR, ["Hạ Trì"]);
  assert.equal(others.length, 4);
  assert.equal(others[3]?.label, "Chỉ Hạ Trì biết");
  assert.equal(others[3]?.hint, "Lục Bắc Uyên không biết điều này.");
  assert.deepEqual(knownByFor("everyone", ["Hạ Trì"]), ["*"]);
  assert.deepEqual(knownByFor("character", ["*"]), ["{{char}}"]);
  assert.deepEqual(knownByFor("player", ["*"]), ["{{user}}"]);
  assert.deepEqual(knownByFor("others", ["Hạ Trì"]), ["Hạ Trì"]);
  assert.equal(knowOptions(" ", ["*"])[1]?.label, "Chỉ nhân vật");
});

test("audienceBadge: labels and tones of the row badge", () => {
  assert.deepEqual(audienceBadge("everyone", CHAR), { label: "Mọi người", tone: "neutral" });
  assert.deepEqual(audienceBadge("character", CHAR), { label: "Chỉ Lục Bắc Uyên", tone: "accent" });
  assert.deepEqual(audienceBadge("player", CHAR), { label: "Chỉ bạn", tone: "gold" });
  assert.deepEqual(audienceBadge("others", CHAR), { label: "Người khác", tone: "neutral" });
});

test("keyWarnings: one-syllable common words, the character's name, names left alone", () => {
  assert.deepEqual(keyWarnings(["mẹ"], CHAR), ["Từ khoá “mẹ” chỉ có một chữ nên sẽ gợi rất thường xuyên."]);
  assert.deepEqual(keyWarnings(["nhẫn"], CHAR), ["Từ khoá “nhẫn” chỉ có một chữ, cũng khớp trong những từ như “kiên nhẫn”."]);
  assert.deepEqual(keyWarnings(["lục bắc uyên"], CHAR), ["Từ khoá “lục bắc uyên” là tên nhân vật nên không dùng để gợi nhớ."]);
  // Diacritics matter: "luc bac uyen" is not the name.
  assert.deepEqual(keyWarnings(["luc bac uyen"], CHAR), []);
  assert.deepEqual(keyWarnings(["hôn ước", "Hạ Trì", "London", "GHOST", "夏驰", "  "], CHAR), []);
  assert.equal(isNameLike("phòng 402"), true);
  assert.equal(isNameLike("căn hộ"), false);
});

test("contentWarnings: spoiler words only for entries the character reads; long content", () => {
  const text = "Theo nguyên tác, cô là nữ chính.";
  assert.deepEqual(contentWarnings(text, "everyone", CHAR), [
    "Có chữ “nguyên tác”, “nữ chính”. Nếu đây là điều Lục Bắc Uyên không được biết, hãy chọn “Chỉ bạn”.",
  ]);
  assert.equal(contentWarnings(text, "character", CHAR).length, 1);
  assert.deepEqual(contentWarnings(text, "player", CHAR), []);
  assert.deepEqual(contentWarnings("Năm 1979, con tàu.", "everyone", CHAR), []);
  assert.deepEqual(contentWarnings("a".repeat(451), "player", CHAR), ["Dài quá thì Lục Bắc Uyên chỉ đọc phần đầu."]);
});

test("validateEntry: name, key count, who knows, content length", () => {
  const ok = { title: "Hôn ước", keys: ["hôn ước"], known_by: ["*"], content: "x" };
  assert.deepEqual(validateEntry(ok), []);
  assert.deepEqual(validateEntry({ ...ok, title: "  " }), ["Mục thế giới cần có tên."]);
  assert.deepEqual(validateEntry({ ...ok, keys: Array.from({ length: 33 }, (_, i) => `k${i}`) }), ["Mỗi mục có tối đa 32 từ khoá."]);
  assert.deepEqual(validateEntry({ ...ok, known_by: [] }), ["Cần chọn ai biết điều này."]);
  assert.deepEqual(validateEntry({ ...ok, content: "x".repeat(4001) }), ["Nội dung dài tối đa 4000 ký tự."]);
});

test("cleanInput trims and clamps", () => {
  const c = cleanInput({ title: " A ", category: "place", keys: [" x ", " "], known_by: [" * "], content: " c ", enabled: true, priority: 500 });
  assert.deepEqual(c, { title: "A", category: "place", keys: ["x"], known_by: ["*"], content: "c", enabled: true, priority: 100 });
});

test("groupEntries: fixed order, empty groups hidden, order kept", () => {
  const list = [
    entry({ id: 1, title: "Lục trạch", category: "place" }),
    entry({ id: 2, title: "Hôn ước", category: "lore" }),
    entry({ id: 3, title: "Vân Lộc", category: "place" }),
  ];
  const groups = groupEntries(list);
  assert.deepEqual(groups.map((g) => g.title), ["Chuyện và bí mật", "Nơi chốn"]);
  assert.deepEqual(groups[1]?.entries.map((e) => e.id), [1, 3]);
  assert.deepEqual(groupEntries([]), []);
});

test("filterEntries: case-insensitive, diacritics kept, searches keys and content", () => {
  const list = [
    entry({ id: 1, title: "Hôn ước Lục - Ôn", keys: ["đính hôn"] }),
    entry({ id: 2, title: "Chuyện lúc nhỏ", content: "Mùa hè năm ấy" }),
  ];
  assert.deepEqual(filterEntries(list, "LỤC").map((e) => e.id), [1]);
  assert.deepEqual(filterEntries(list, "lúc").map((e) => e.id), [2]);
  assert.deepEqual(filterEntries(list, "ĐÍNH").map((e) => e.id), [1]);
  assert.deepEqual(filterEntries(list, "mùa hè").map((e) => e.id), [2]);
  assert.equal(filterEntries(list, "  ").length, 2);
});

test("keysLine: three keys then …; null without keys", () => {
  assert.equal(keysLine(["hôn ước", "đính hôn", "Lục Ôn", "1979"]), "Gợi nhớ khi nhắc: hôn ước, đính hôn, Lục Ôn…");
  assert.equal(keysLine(["a"]), "Gợi nhớ khi nhắc: a");
  assert.equal(keysLine([" "]), null);
});

test("importSummaryLines: counts, zero lines dropped, nothing new", () => {
  const r = result({ created: 27, updated: 3, kept_edited: 2, skipped_removed: 2, unchanged: 20 });
  assert.deepEqual(importSummaryLines(r), [
    "Thêm 27 mục mới.",
    "Cập nhật 3 mục.",
    "Giữ nguyên 2 mục bạn đã sửa.",
    "Bỏ qua 2 mục bạn đã xoá.",
    "Không đổi 20 mục.",
  ]);
  const same = result({ unchanged: 27, skipped_removed: 1 });
  assert.equal(nothingNew(same), true);
  assert.deepEqual(importSummaryLines(same), ["File này đã được nhập, không có gì mới.", "Bỏ qua 1 mục bạn đã xoá."]);
  assert.deepEqual(importSummaryLines(result({ deleted: 3, missing: 3 })), ["Xoá 3 mục không còn trong file."]);
  // The server's own "Bỏ qua…" note is not repeated.
  assert.deepEqual(importNotes({ ...same, notes: ["Bỏ qua 1 mục bạn đã xoá.", "Không nhập phần Bí mật."] }), ["Không nhập phần Bí mật."]);
  // The server's "Chỉ bạn" note is already shown in its own box.
  const withPlayer = result({
    created: 2,
    player_only: ["Hứa Tri Ý", "Phó Cảnh Hành"],
    notes: ["Bỏ 4 câu nhắc tới điều chỉ bạn biết.", "Hứa Tri Ý, Phó Cảnh Hành: chỉ bạn biết, vì thế giới có điều chỉ bạn biết về họ."],
  });
  assert.deepEqual(importNotes(withPlayer), ["Bỏ 4 câu nhắc tới điều chỉ bạn biết."]);
});

test("missingToggleLabel only when the file lacks entries imported before", () => {
  assert.equal(missingToggleLabel(result({ missing: 0 })), null);
  assert.equal(missingToggleLabel(result({ missing: 3 })), "Xoá 3 mục không còn trong file");
});

test("playerOnlyLine, importItemGroups, deletePrompt", () => {
  assert.equal(playerOnlyLine([], CHAR), null);
  assert.equal(
    playerOnlyLine(["Hứa Tri Ý", "Phó Cảnh Hành"], CHAR),
    "Chỉ bạn biết: Hứa Tri Ý, Phó Cảnh Hành, vì thế giới có điều chỉ bạn biết về họ. Đổi trong danh sách sau khi nhập nếu Lục Bắc Uyên cũng biết họ.",
  );
  const groups = importItemGroups([
    { slug: "a", title: "Hạ Trì", category: "character", action: "create" },
    { slug: "b", title: "Hôn ước", category: "lore", action: "unchanged" },
  ]);
  assert.deepEqual(groups.map((g) => g.title), ["Chuyện và bí mật", "Người xung quanh"]);
  assert.deepEqual(groups[0]?.entries, [{ title: "Hôn ước", tag: null }]);
  assert.deepEqual(groups[1]?.entries, [{ title: "Hạ Trì", tag: "mới" }]);
  assert.equal(deletePrompt({ title: "A", source: "manual" }), "Xoá “A”? Story đã mở mục này sẽ không còn thấy nó.");
  assert.match(deletePrompt({ title: "A", source: "world_md" }), /Nhập lại file sẽ không thêm lại mục này\.$/);
});

test("importFileError: size limit and empty file", () => {
  assert.equal(importFileError({ name: "world.md", size: 600_000 }), "File quá lớn (tối đa 500 KB).");
  assert.equal(importFileError({ name: "world.md", size: 0 }), "File này trống.");
  assert.equal(importFileError({ name: "world.md", size: 12_000 }), null);
});

test("bookEntryCount / withoutBook read the card's leftover character_book defensively", () => {
  const ext = { v2: { character_book: { entries: [{}, {}] }, creator: "x" }, lyris: { a: 1 } };
  assert.equal(bookEntryCount(ext), 2);
  assert.equal(bookEntryCount({}), 0);
  assert.equal(bookEntryCount(null), 0);
  assert.equal(bookEntryCount({ v2: { character_book: { entries: "no" } } }), 0);
  assert.deepEqual(withoutBook(ext), { v2: { creator: "x" }, lyris: { a: 1 } });
  assert.deepEqual(withoutBook({ v2: { character_book: {} } }), {});
  assert.deepEqual(withoutBook({ lyris: {} }), { lyris: {} });
});

test("search: the query stops filtering once the field hides (list back to ≤ 12 entries)", () => {
  const mk = (i: number) => ({ title: i === 0 ? "Lục Chấn Đình" : `Mục ${i}`, keys: [], content: "" });
  const thirteen = Array.from({ length: 13 }, (_, i) => mk(i));
  assert.equal(searchShown(13), true);
  assert.equal(filterEntries(thirteen, activeQuery(13, "Lục")).length, 1);
  const twelve = thirteen.slice(1);
  assert.equal(searchShown(12), false);
  assert.equal(activeQuery(12, "Lục"), "");
  assert.equal(filterEntries(twelve, activeQuery(12, "Lục")).length, 12);
});

test("bookConvertedOnSave: only when a saved card loses the book it sent", () => {
  const book = { v2: { character_book: { entries: [{}, {}] } } };
  assert.equal(bookConvertedOnSave(book, {}), true);
  assert.equal(bookConvertedOnSave(book, { v2: {} }), true);
  assert.equal(bookConvertedOnSave(book, book), false);
  assert.equal(bookConvertedOnSave({}, {}), false);
  assert.equal(bookConvertedOnSave(null, undefined), false);
});
