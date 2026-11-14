// F46 (docs/coins.md §5.2, §5.7; wiki/screens/hot-ranking.md): the "Nhân vật hot" leaderboard and the strip on Khám phá.
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  HOT_COPY,
  hotFrom,
  hotStripItems,
  hotStripView,
  hotView,
  playersLabel,
  rewardNote,
  rowLabel,
  updatedLabel,
} from "./hotLogic.ts";
import type { HotBoard, HotItem } from "./hotLogic.ts";

const item = (rank: number, name: string, players: number): HotItem => ({
  rank,
  card_id: 100 + rank,
  name,
  avatar_url: null,
  creator_handle: "sangtac",
  players,
});

const board = (items: HotItem[]): HotBoard => ({ updated_at: "2026-11-14T07:05:00.000Z", ranked: items.length, items });

test("updatedLabel: 'Cập nhật lúc HH:mm' in the viewer's own time; nothing without a time", () => {
  const local = new Date(2026, 10, 14, 14, 5, 30);
  assert.equal(updatedLabel(local.toISOString()), "Cập nhật lúc 14:05");
  assert.equal(updatedLabel(new Date(2026, 10, 14, 9, 0).toISOString()), "Cập nhật lúc 09:00");
  assert.equal(updatedLabel(null), null);
  assert.equal(updatedLabel("không phải giờ"), null);
});

test("playersLabel and rowLabel: Vietnamese thousands, the row's full name for screen readers", () => {
  assert.equal(playersLabel(12), "12 người chơi");
  assert.equal(playersLabel(1200), "1.200 người chơi");
  assert.equal(playersLabel(1), "1 người chơi");
  assert.equal(rowLabel(item(1, "Hạ Vy Quán Trà", 12)), "Hạng 1: Hạ Vy Quán Trà, 12 người chơi");
  assert.equal(rowLabel(item(7, "Tần Dương", 1200)), "Hạng 7: Tần Dương, 1.200 người chơi");
});

test("hotView: an empty board says so and offers 'Mở Studio' (→ #/studio); otherwise the rows", () => {
  const empty = hotView(board([]));
  assert.equal(empty.kind, "empty");
  if (empty.kind !== "empty") throw new Error("empty");
  assert.equal(empty.title, "Chưa có nhân vật nào trên bảng xếp hạng.");
  assert.equal(empty.hint, "Công khai nhân vật của bạn trong Studio để người khác cùng chơi.");
  assert.deepEqual(empty.action, { label: "Mở Studio", href: "#/studio" });
  const full = hotView(board([item(1, "A", 9), item(2, "B", 3)]));
  assert.equal(full.kind, "list");
  if (full.kind !== "list") throw new Error("list");
  assert.deepEqual(full.rows.map((r) => [r.rank, r.name, r.players, r.label, r.href]), [
    [1, "A", "9 người chơi", "Hạng 1: A, 9 người chơi", "#/character/101"],
    [2, "B", "3 người chơi", "Hạng 2: B, 3 người chơi", "#/character/102"],
  ]);
  assert.equal(full.rows[0]?.by, "bởi @sangtac");
  assert.equal(full.rows[0]?.top, true);
  assert.equal(hotView(board([item(4, "D", 1)])).kind === "list" && (hotView(board([item(4, "D", 1)])) as { rows: { top: boolean }[] }).rows[0]?.top, false);
});

test("hotStripItems: the first 3 rows; none when the board is empty, failed to load, or a search is typed", () => {
  const b = board([item(1, "A", 9), item(2, "B", 8), item(3, "C", 7), item(4, "D", 6)]);
  assert.deepEqual(hotStripItems(b, { query: "" }).map((i) => i.rank), [1, 2, 3]);
  assert.deepEqual(hotStripItems(b, { query: "   " }).map((i) => i.rank), [1, 2, 3]);
  assert.deepEqual(hotStripItems(board([item(1, "A", 1)]), { query: "" }).map((i) => i.rank), [1]);
  assert.deepEqual(hotStripItems(board([]), { query: "" }), []);
  assert.deepEqual(hotStripItems(null, { query: "" }), [], "failed to load");
  assert.deepEqual(hotStripItems(b, { query: "ha vy" }), [], "searching hides the strip");
});

test("hotStripView: the strip keeps its title and 'Xem bảng xếp hạng' when the board is empty or not loaded; hidden only while searching", () => {
  const b = board([item(1, "A", 9), item(2, "B", 8), item(3, "C", 7), item(4, "D", 6)]);
  assert.deepEqual(hotStripView(b, { query: "" }), { rows: hotStripItems(b, { query: "" }), empty: null });
  assert.deepEqual(hotStripView(board([]), { query: "" }), { rows: [], empty: "Chưa có nhân vật nào trên bảng xếp hạng." });
  assert.deepEqual(hotStripView(null, { query: "" }), { rows: [], empty: null }, "loading or failed: title and link only");
  assert.equal(hotStripView(b, { query: "ha vy" }), null, "searching hides the strip");
  assert.equal(hotStripView(board([]), { query: "x" }), null);
  assert.equal(HOT_COPY.stripEmpty, HOT_COPY.emptyTitle);
});

test("rewardNote: only a member with coins on sees the reward line (not the managing account, not LYRIS_COINS=0)", () => {
  const note = "Nhân vật của bạn vào top 100, top 50, top 10 thì bạn được thưởng 100, 200, 300 coin.";
  const rule = "Thưởng top N chỉ có khi bảng có nhân vật của ít nhất N người tạo khác nhau.";
  assert.equal(HOT_COPY.rewardNote, note);
  assert.equal(HOT_COPY.rewardRule, rule);
  assert.equal(rewardNote({ unlimited: false, enabled: true }), `${note} ${rule}`);
  assert.equal(rewardNote({ unlimited: true, enabled: true }), null);
  assert.equal(rewardNote({ unlimited: false, enabled: false }), null);
  assert.equal(rewardNote(null), null, "wallet not known yet");
});

test("hotFrom: opened from Khám phá's button is 'explore', anything else 'link'", () => {
  assert.equal(hotFrom("explore"), "explore");
  assert.equal(hotFrom("hub"), "link");
  assert.equal(hotFrom(null), "link");
});

test("the leaderboard words: Vietnamese, no technical words", () => {
  const all = Object.values(HOT_COPY).join("\n");
  for (const bad of [/snapshot/i, /\brank\b/i, /\bapi\b/i, /token/i, /model/i, /ollama/i, /chủ máy/i]) {
    assert.doesNotMatch(all, bad);
  }
  assert.equal(HOT_COPY.title, "Nhân vật hot");
  assert.equal(HOT_COPY.subtitle, "Xếp theo tổng số người chơi. Cập nhật mỗi giờ.");
  assert.equal(HOT_COPY.seeAll, "Xem bảng xếp hạng");
  assert.equal(HOT_COPY.back, "Về Khám phá");
  assert.equal(HOT_COPY.listLabel, "Bảng xếp hạng Nhân vật hot");
  assert.equal(HOT_COPY.error, "Không tải được bảng xếp hạng.");
  assert.equal(HOT_COPY.retry, "Thử lại");
});
