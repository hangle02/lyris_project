import { test } from "node:test";
import assert from "node:assert/strict";
import {
  deltaChips,
  entryTime,
  hasEvents,
  jumpPlan,
  modeLabel,
  normalizeTimeline,
  sceneText,
  timelineItems,
  turnDomId,
} from "./eventsLogic.ts";

const row = (over: Record<string, unknown>) => ({
  turn_index: 2,
  message_id: 10,
  mode: "story",
  created_at: "2026-11-13T15:20:00Z",
  memory: null,
  facts: [],
  delta: {},
  scene: null,
  ...over,
});

test("normalizeTimeline: defensive read, one entry per turn, story order", () => {
  const out = normalizeTimeline([
    row({ turn_index: 4, memory: "  Hạ Vy kể về   bức thư. ", delta: { affection: 2, trust: 0, fear: "x", bogus: 3 } }),
    row({ turn_index: 0, scene: { location: "Tiệm sách", time: null } }),
    { turn_index: -1 },
    { memory: "không có lượt" },
    "rác",
    row({ turn_index: 4, memory: "Bản sau thắng" }),
    row({ turn_index: 6, mode: "dm", facts: ["Thích trà gừng", "", 5], scene: { location: " ", time: "" } }),
  ]);
  assert.deepEqual(
    out.map((e) => e.turn_index),
    [0, 4, 6],
  );
  assert.equal(out[1]?.memory, "Bản sau thắng");
  assert.equal(out[2]?.mode, "dm");
  assert.deepEqual(out[2]?.facts, ["Thích trà gừng"]);
  assert.equal(out[2]?.scene, null);
  assert.deepEqual(normalizeTimeline(row({ delta: { affection: 2, trust: 0, fear: "x" } }) as unknown), []);
  assert.deepEqual(normalizeTimeline([row({ delta: { affection: 2.4, trust: 0, fear: "x" } })])[0]?.delta, { affection: 2 });
  assert.deepEqual(normalizeTimeline(null), []);
});

test("deltaChips: signed text with a real minus, DESIGN.md order, zeros skipped", () => {
  assert.deepEqual(deltaChips({ trust: -3, affection: 2, fear: 0 }), [
    { key: "affection", text: "+2 Thương mến", label: "Thương mến tăng 2" },
    { key: "trust", text: "−3 Tin cậy", label: "Tin cậy giảm 3" },
  ]);
  assert.deepEqual(deltaChips({}), []);
});

test("sceneText, hasEvents, timelineItems (newest first, empty turns left out)", () => {
  assert.equal(sceneText({ location: "Gác xép", time: "Chiều tối" }), "Gác xép · Chiều tối");
  assert.equal(sceneText({ location: null, time: "Đêm" }), "Đêm");
  assert.equal(sceneText(null), "");
  const entries = normalizeTimeline([
    row({ turn_index: 0, scene: { location: "Tiệm sách", time: null } }),
    row({ turn_index: 2 }),
    row({ turn_index: 4, memory: "Hứa đi xem đèn lồng." }),
  ]);
  assert.equal(hasEvents(entries[1]!), false);
  assert.deepEqual(
    timelineItems(entries).map((e) => e.turn_index),
    [4, 0],
  );
});

test("entryTime: today, yesterday, older; unknown is empty", () => {
  const now = new Date(2026, 10, 13, 20, 0);
  const at = (d: Date) => d.toISOString();
  assert.equal(entryTime(at(new Date(2026, 10, 13, 9, 5)), now), "09:05");
  assert.equal(entryTime(at(new Date(2026, 10, 12, 23, 15)), now), "Hôm qua 23:15");
  assert.equal(entryTime(at(new Date(2026, 10, 2, 7, 0)), now), "02/11 07:00");
  assert.equal(entryTime(null, now), "");
  assert.equal(entryTime("không phải ngày", now), "");
});

test("modeLabel and turnDomId", () => {
  assert.equal(modeLabel("dm"), "DM");
  assert.equal(modeLabel("story"), "Story");
  assert.equal(turnDomId(12), "turn-12");
});

test("jumpPlan: scroll here, switch first, or explain when the switch is locked", () => {
  assert.deepEqual(jumpPlan("story", "story", true), { kind: "scroll" });
  assert.deepEqual(jumpPlan("dm", "story", false), { kind: "switch", mode: "dm" });
  const blocked = jumpPlan("dm", "story", true);
  assert.equal(blocked.kind, "blocked");
  assert.match(blocked.kind === "blocked" ? blocked.notice : "", /bên DM/);
});
