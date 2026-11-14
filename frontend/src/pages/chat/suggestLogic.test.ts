import { test } from "node:test";
import assert from "node:assert/strict";
import {
  INITIAL_SUGGEST,
  cleanSuggestions,
  composerActions,
  nextEnabledIndex,
  replyAnchor,
  suggestAvailability,
  suggestReducer,
  suggestView,
  suggestionsKey,
} from "./suggestLogic.ts";
import type { SuggestState } from "./suggestLogic.ts";

const reply = { role: "assistant" as const, is_active: true };
const mine = { role: "user" as const, is_active: true };
const base = { busy: false, loading: false, generating: false };

test("suggestAvailability: only when the newest message is the character's and nothing runs", () => {
  assert.deepEqual(suggestAvailability({ ...base, messages: [reply] }), { enabled: true, reason: null });
  assert.deepEqual(suggestAvailability({ ...base, messages: [reply, mine, reply] }).enabled, true);
  const waiting = suggestAvailability({ ...base, messages: [reply, mine] });
  assert.equal(waiting.enabled, false);
  assert.match(waiting.reason ?? "", /chưa có câu trả lời/);
  assert.equal(suggestAvailability({ ...base, messages: [] }).reason, "Story chưa có lượt nào để gợi ý.");
  assert.equal(suggestAvailability({ ...base, busy: true, messages: [reply] }).reason, "Đợi nhân vật trả lời xong đã.");
  assert.equal(suggestAvailability({ ...base, generating: true, messages: [reply] }).reason, "Đang nghĩ gợi ý…");
  assert.equal(suggestAvailability({ ...base, loading: true, messages: [reply] }).enabled, false);
  assert.equal(suggestAvailability({ ...base, offline: true, messages: [reply] }).reason, "Nhân vật tạm thời chưa trả lời được.");
  // Inactive variants do not count as the newest message.
  assert.equal(suggestAvailability({ ...base, messages: [reply, { role: "user", is_active: false }] }).enabled, true);
});

test("composerActions: data-driven list; image is a disabled 'Sắp có' shell", () => {
  const on = composerActions({ suggest: { enabled: true, reason: null } });
  assert.deepEqual(
    on.map((a) => [a.id, a.disabled, a.soon]),
    [
      ["suggest", false, false],
      ["events", false, false],
      ["image", true, true],
    ],
  );
  const off = composerActions({ suggest: { enabled: false, reason: "Đợi nhân vật trả lời xong đã." } });
  assert.equal(off[0]?.disabled, true);
  assert.equal(off[0]?.hint, "Đợi nhân vật trả lời xong đã.");
  // No technical words in the menu.
  for (const a of on) assert.doesNotMatch(`${a.label} ${a.hint}`, /model|ollama|prompt|token/i);
});

test("nextEnabledIndex skips disabled items and wraps", () => {
  const items = [{ disabled: false }, { disabled: false }, { disabled: true }];
  assert.equal(nextEnabledIndex(items, 0, 1), 1);
  assert.equal(nextEnabledIndex(items, 1, 1), 0);
  assert.equal(nextEnabledIndex(items, 0, -1), 1);
  assert.equal(nextEnabledIndex(items, -1, 1), 0);
  assert.equal(nextEnabledIndex([{ disabled: true }], 0, 1), -1);
});

test("cleanSuggestions trims, drops empties and duplicates, keeps three", () => {
  assert.deepEqual(cleanSuggestions([" Một ", "", "Một", 3, "Hai", "Ba", "Bốn"]), ["Một", "Hai", "Ba"]);
});

const err = { text: "Có lỗi xảy ra. Hãy thử lại.", technical: "HTTP 500" };

test("reducer: request, answer, error; late answers ignored", () => {
  let s: SuggestState = suggestReducer(INITIAL_SUGGEST, { type: "request", mode: "story", request: 1 });
  assert.equal(s.status, "loading");
  s = suggestReducer(s, { type: "success", request: 0, items: ["cũ"] });
  assert.equal(s.status, "loading");
  s = suggestReducer(s, { type: "success", request: 1, items: ["A", "B"] });
  assert.deepEqual([s.status, s.items], ["idle", ["A", "B"]]);
  s = suggestReducer(s, { type: "request", mode: "story", request: 2 });
  s = suggestReducer(s, { type: "failure", request: 2, error: err });
  assert.deepEqual([s.status, s.error], ["error", err]);
  // A reset (a new turn starts) ignores whatever was in flight.
  s = suggestReducer(s, { type: "request", mode: "story", request: 3 });
  s = suggestReducer(s, { type: "reset" });
  s = suggestReducer(s, { type: "success", request: 3, items: ["muộn"] });
  assert.deepEqual([s.status, s.items], ["idle", null]);
});

const opts = { stored: [] as string[], storedMode: null, view: "story" as const, generating: false };

test("suggestView: loading dots, error, items, or nothing", () => {
  assert.deepEqual(suggestView(INITIAL_SUGGEST, opts), { kind: "none" });
  const loading = suggestReducer(INITIAL_SUGGEST, { type: "request", mode: "story", request: 1 });
  assert.deepEqual(suggestView(loading, opts), { kind: "loading" });
  const done = suggestReducer(loading, { type: "success", request: 1, items: ["A"] });
  assert.deepEqual(suggestView(done, opts), { kind: "items", items: ["A"] });
  // Hidden while a reply is generated and in the other view.
  assert.deepEqual(suggestView(done, { ...opts, generating: true }), { kind: "none" });
  assert.deepEqual(suggestView(done, { ...opts, view: "dm" }), { kind: "none" });
  const failed = suggestReducer(loading, { type: "failure", request: 1, error: err });
  assert.deepEqual(suggestView(failed, opts), { kind: "error", error: err });
});

test("suggestView: the server's stored suggestions show until dismissed", () => {
  const stored = { ...opts, stored: ["Ừ", "Không"], storedMode: "story" as const };
  assert.deepEqual(suggestView(INITIAL_SUGGEST, stored), { kind: "items", items: ["Ừ", "Không"] });
  assert.deepEqual(suggestView(INITIAL_SUGGEST, { ...stored, view: "dm" }), { kind: "none" });
  const closed = suggestReducer(INITIAL_SUGGEST, { type: "dismiss", key: suggestionsKey(["Ừ", "Không"]) });
  assert.deepEqual(suggestView(closed, stored), { kind: "none" });
  // Different ones (a later request) show again.
  const again = suggestReducer(suggestReducer(closed, { type: "request", mode: "story", request: 1 }), {
    type: "success",
    request: 1,
    items: ["Mới"],
  });
  assert.deepEqual(suggestView(again, stored), { kind: "items", items: ["Mới"] });
});

test("dismiss while loading cancels: nothing shows, the answer is ignored", () => {
  let s = suggestReducer(INITIAL_SUGGEST, { type: "request", mode: "story", request: 1 });
  s = suggestReducer(s, { type: "success", request: 1, items: ["A"] });
  s = suggestReducer(s, { type: "request", mode: "story", request: 2 });
  s = suggestReducer(s, { type: "dismiss", key: "" });
  s = suggestReducer(s, { type: "success", request: 2, items: ["B"] });
  assert.deepEqual(suggestView(s, opts), { kind: "none" });
});

test("replyAnchor: the newest active message when it is the character's reply", () => {
  const msg = (id: number | null, role: "user" | "assistant", extra: Record<string, unknown> = {}) => ({
    id,
    role,
    mode: "story" as const,
    is_active: true,
    variant_index: 0,
    edited_at: null,
    ...extra,
  });
  assert.deepEqual(replyAnchor([msg(1, "assistant")]), { key: "1:0:", mode: "story" });
  assert.equal(replyAnchor([msg(1, "assistant"), msg(2, "user")]), null);
  assert.equal(replyAnchor([]), null);
  assert.deepEqual(replyAnchor([msg(1, "assistant", { mode: "dm", variant_index: 2 }), msg(2, "user", { is_active: false })]), {
    key: "1:2:",
    mode: "dm",
  });
  assert.notEqual(replyAnchor([msg(1, "assistant", { edited_at: "t" })])?.key, replyAnchor([msg(1, "assistant")])?.key);
});

test("suggestView: suggestions asked for a reply vanish once that reply is deleted, edited or swapped", () => {
  const anchored = { ...opts, anchor: "5:0:" };
  let s = suggestReducer(INITIAL_SUGGEST, { type: "request", mode: "story", request: 1, anchor: "5:0:" });
  assert.deepEqual(suggestView(s, anchored), { kind: "loading" });
  s = suggestReducer(s, { type: "success", request: 1, items: ["A", "B"] });
  assert.deepEqual(suggestView(s, anchored), { kind: "items", items: ["A", "B"] });
  // Another variant / an edit of the reply: the old items (and the server's copy of them) are hidden.
  assert.deepEqual(suggestView(s, { ...anchored, anchor: "5:1:", stored: ["A", "B"], storedMode: "story" }), { kind: "none" });
  // "Xoá từ đây": the newest message is the player's, nothing to answer.
  assert.deepEqual(suggestView(s, { ...anchored, anchor: null, stored: ["A"], storedMode: "story" }), { kind: "none" });
  // Errors too.
  const failed = suggestReducer(suggestReducer(INITIAL_SUGGEST, { type: "request", mode: "story", request: 2, anchor: "5:0:" }), {
    type: "failure",
    request: 2,
    error: err,
  });
  assert.deepEqual(suggestView(failed, { ...anchored, anchor: "6:0:" }), { kind: "none" });
  // After a reset the server's stored ones (for the current reply) still show.
  const reset = suggestReducer(s, { type: "reset" });
  assert.deepEqual(suggestView(reset, { ...anchored, anchor: "6:0:", stored: ["C"], storedMode: "story" }), {
    kind: "items",
    items: ["C"],
  });
});

test("suggestAvailability: a reply of the other mode cannot be answered from this view", () => {
  const storyReply = { role: "assistant" as const, is_active: true, mode: "story" as const };
  const res = suggestAvailability({ ...base, messages: [storyReply], view: "dm" });
  assert.equal(res.enabled, false);
  assert.equal(res.reason, "Nhân vật vừa trả lời bên Story. Mở Story để nhận gợi ý.");
  assert.equal(suggestAvailability({ ...base, messages: [storyReply], view: "story" }).enabled, true);
});
