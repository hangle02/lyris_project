import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  LOCK_GENERIC,
  LOCK_PENDING,
  LOCK_REPLYING,
  LOCK_SAVING,
  LOCK_SUGGESTING,
  actionLockReason,
  messageLockReason,
} from "./actionLock.ts";

test("actionLockReason: no lock, no reason", () => {
  assert.equal(actionLockReason({ streaming: false, suggesting: false, saving: false }), null);
});

test("actionLockReason: a streaming reply says to wait or press Dừng", () => {
  const r = actionLockReason({ streaming: true, suggesting: false, saving: false });
  assert.equal(r, LOCK_REPLYING);
  assert.match(r ?? "", /trả lời xong/);
  assert.match(r ?? "", /Dừng/);
  // Streaming wins over the other causes: it is what the player sees and can stop.
  assert.equal(actionLockReason({ streaming: true, suggesting: true, saving: true }), LOCK_REPLYING);
});

test("actionLockReason: suggestions being written, then a save in flight", () => {
  assert.equal(actionLockReason({ streaming: false, suggesting: true, saving: false }), LOCK_SUGGESTING);
  assert.match(LOCK_SUGGESTING, /Huỷ gợi ý/);
  assert.equal(actionLockReason({ streaming: false, suggesting: false, saving: true }), LOCK_SAVING);
  assert.equal(actionLockReason({ streaming: false, suggesting: true, saving: true }), LOCK_SUGGESTING);
});

test("messageLockReason: the page's reason while locked, a pending turn says it is being saved", () => {
  assert.equal(messageLockReason({ disabled: false, pending: false, reason: null }), null);
  assert.equal(messageLockReason({ disabled: true, pending: false, reason: LOCK_SAVING }), LOCK_SAVING);
  assert.equal(messageLockReason({ disabled: true, pending: true, reason: LOCK_REPLYING }), LOCK_REPLYING);
  assert.equal(messageLockReason({ disabled: false, pending: true, reason: null }), LOCK_PENDING);
  // Locked without a reason from the page (e.g. Studio): still never a bare disabled button, and the
  // fallback does not claim a reply is streaming (no "bấm Dừng" when there is nothing to stop).
  assert.equal(messageLockReason({ disabled: true, pending: false, reason: null }), LOCK_GENERIC);
  assert.doesNotMatch(LOCK_GENERIC, /Dừng|trả lời/);
});

test("every reason is a plain sentence, no technical words", () => {
  for (const r of [LOCK_REPLYING, LOCK_SUGGESTING, LOCK_SAVING, LOCK_PENDING, LOCK_GENERIC]) {
    assert.ok(r.length > 10, r);
    assert.match(r, /[.!]$/, r);
    assert.doesNotMatch(r, /\b(model|token|ollama|request|stream|409)\b/i, r);
  }
});

test("ActionRow: locked buttons carry the reason as their title, the row too", () => {
  const src = readFileSync(new URL("../components/MessageItem.tsx", import.meta.url), "utf8");
  const row = src.slice(src.indexOf("export function ActionRow"), src.indexOf("export function DirectiveChip"));
  for (const label of ["Sửa", "Xoá từ đây"]) {
    const at = row.indexOf(`label="${label}"`);
    assert.ok(at > 0, label);
    const tag = row.slice(row.lastIndexOf("<IconButton", at), row.indexOf("/>", at));
    assert.match(tag, /title=\{tip\(/, `${label}: ${tag}`);
  }
  assert.match(row, /title=\{lockReason \?\? undefined\}/);
});
