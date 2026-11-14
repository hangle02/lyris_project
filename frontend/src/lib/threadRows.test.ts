import { test } from "node:test";
import assert from "node:assert/strict";
import { buildRows, dmReceipt, receiptLabel } from "./threadRows.ts";
import type { Message, Mode, Role } from "../types.ts";

function msg(turn: number, role: Role, mode: Mode): Message {
  return {
    id: turn + 1,
    story_id: 1,
    turn_index: turn,
    variant_index: 0,
    is_active: true,
    role,
    mode,
    raw_content: `m${turn}`,
    visible_content: `m${turn}`,
    thought: null,
    directive: null,
    model_output: null,
    model_name: null,
    gen_stats: null,
    rating: null,
    variant_count: 1,
    created_at: null,
    edited_at: null,
  };
}

const timeline = [
  msg(0, "assistant", "story"),
  msg(1, "user", "story"),
  msg(2, "assistant", "story"),
  msg(3, "user", "dm"),
  msg(4, "assistant", "dm"),
  msg(5, "user", "story"),
  msg(6, "assistant", "story"),
];

test("story view collapses DM runs and counts hidden later messages", () => {
  const rows = buildRows(timeline, timeline, "story");
  assert.deepEqual(
    rows.map((r) => (r.type === "msg" ? `${r.m.turn_index}` : `other:${r.count}`)),
    ["0", "1", "2", "other:2", "5", "6"],
  );
  const first = rows[0];
  assert.ok(first && first.type === "msg" && first.hiddenAfter === 2);
  const last = rows[rows.length - 1];
  assert.ok(last && last.type === "msg" && last.isLastAssistant && last.canRegenerate && last.hiddenAfter === 0);
});

test("dm view: the last DM reply is not regenerable when story turns follow it", () => {
  const rows = buildRows(timeline, timeline, "dm");
  assert.deepEqual(
    rows.map((r) => (r.type === "msg" ? `${r.m.turn_index}` : `other:${r.count}`)),
    ["other:3", "3", "4", "other:2"],
  );
  const reply = rows[2];
  assert.ok(reply && reply.type === "msg" && !reply.isLastAssistant && !reply.canRegenerate && reply.hiddenAfter === 2);
});

test("dmReceipt: newest player DM is sent, then seen once a reply follows", () => {
  const dm = [msg(0, "assistant", "dm"), msg(1, "user", "dm")];
  assert.deepEqual(dmReceipt(dm, "dm", false), { turnIndex: 1, status: "sent" });
  assert.deepEqual(dmReceipt(dm, "dm", true), { turnIndex: 1, status: "seen" });
  assert.deepEqual(dmReceipt([...dm, msg(2, "assistant", "dm")], "dm", false), { turnIndex: 1, status: "seen" });
  // The newest player message of this view, even when story turns come after it.
  assert.deepEqual(dmReceipt(timeline, "dm", false), { turnIndex: 3, status: "seen" });
  assert.equal(dmReceipt([msg(0, "assistant", "dm")], "dm", false), null);
  const pending = { ...msg(2, "user", "dm"), id: null };
  assert.deepEqual(dmReceipt([...dm, pending], "dm", false), { turnIndex: 2, status: "sending" });
});

test("receiptLabel", () => {
  assert.equal(receiptLabel("sent", "00:40"), "00:40 • Đã gửi");
  assert.equal(receiptLabel("seen", "23:15"), "23:15 • Đã xem");
  assert.equal(receiptLabel("sending", "23:15"), "Đang gửi…");
  assert.equal(receiptLabel("seen", ""), "Đã xem");
});
