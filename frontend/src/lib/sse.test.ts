import { test } from "node:test";
import assert from "node:assert/strict";
import { SSEParser } from "./sse.ts";
import type { SSEMessage } from "./sse.ts";

function feedAll(chunks: string[]): SSEMessage[] {
  const p = new SSEParser();
  const out: SSEMessage[] = [];
  for (const c of chunks) out.push(...p.feed(c));
  out.push(...p.flush());
  return out;
}

const STREAM =
  'event: user_message\ndata: {"message":{"id":1}}\n\n' +
  'event: start\ndata: {"turn_index":2,"variant_index":0}\n\n' +
  ': keep-alive\n\n' +
  'event: delta\ndata: {"kind":"text","text":"Anh “cười” nhẹ."}\n\n' +
  'event: delta\ndata: {"kind":"thought","text":"Vãn Vãn…"}\n\n' +
  'event: done\ndata: {"message":{"id":2}}\n\n';

const EXPECTED = [
  { event: "user_message", data: '{"message":{"id":1}}' },
  { event: "start", data: '{"turn_index":2,"variant_index":0}' },
  { event: "delta", data: '{"kind":"text","text":"Anh “cười” nhẹ."}' },
  { event: "delta", data: '{"kind":"thought","text":"Vãn Vãn…"}' },
  { event: "done", data: '{"message":{"id":2}}' },
];

const strip = (ms: SSEMessage[]) => ms.map(({ event, data }) => ({ event, data }));

test("parses a whole stream in one chunk", () => {
  assert.deepEqual(strip(feedAll([STREAM])), EXPECTED);
});

test("handles every possible split point", () => {
  for (let i = 0; i <= STREAM.length; i++) {
    assert.deepEqual(strip(feedAll([STREAM.slice(0, i), STREAM.slice(i)])), EXPECTED, `split at ${i}`);
  }
});

test("handles one character per chunk", () => {
  assert.deepEqual(strip(feedAll([...STREAM])), EXPECTED);
});

test("handles CRLF and lone CR line endings, split between CR and LF", () => {
  const crlf = STREAM.replace(/\n/g, "\r\n");
  for (let i = 0; i <= crlf.length; i++) {
    assert.deepEqual(strip(feedAll([crlf.slice(0, i), crlf.slice(i)])), EXPECTED, `crlf split at ${i}`);
  }
  const cr = STREAM.replace(/\n/g, "\r");
  assert.deepEqual(strip(feedAll([...cr])), EXPECTED);
});

test("joins multiple data lines and strips only one leading space", () => {
  const out = feedAll(["event: x\ndata:  a\ndata:b\ndata\n\n"]);
  assert.deepEqual(strip(out), [{ event: "x", data: " a\nb\n" }]);
});

test("defaults event name to message, ignores events without data", () => {
  const out = feedAll(["data: 1\n\nevent: lonely\n\nid: 7\ndata: 2\n\n"]);
  assert.deepEqual(out, [
    { event: "message", data: "1", id: null },
    { event: "message", data: "2", id: "7" },
  ]);
});

test("event name does not leak into the next event", () => {
  const out = feedAll(["event: delta\ndata: a\n\ndata: b\n\n"]);
  assert.deepEqual(strip(out), [
    { event: "delta", data: "a" },
    { event: "message", data: "b" },
  ]);
});

test("flush dispatches a final event missing its blank line", () => {
  assert.deepEqual(strip(feedAll(['event: done\ndata: {"ok":true}'])), [{ event: "done", data: '{"ok":true}' }]);
  assert.deepEqual(strip(feedAll(['event: done\ndata: {"ok":true}\n'])), [{ event: "done", data: '{"ok":true}' }]);
});

test("works with TextDecoder streaming across split UTF-8 bytes", () => {
  const bytes = new TextEncoder().encode(STREAM);
  for (const step of [1, 2, 3, 5, 7]) {
    const dec = new TextDecoder("utf-8");
    const p = new SSEParser();
    const out: SSEMessage[] = [];
    for (let i = 0; i < bytes.length; i += step) {
      out.push(...p.feed(dec.decode(bytes.subarray(i, i + step), { stream: true })));
    }
    out.push(...p.feed(dec.decode()));
    out.push(...p.flush());
    assert.deepEqual(strip(out), EXPECTED, `step ${step}`);
  }
});
