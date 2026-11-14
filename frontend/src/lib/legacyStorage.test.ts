import { test } from "node:test";
import assert from "node:assert/strict";
import { migrateLegacyKeys } from "./legacyStorage.ts";

function memStore(init: Record<string, string>) {
  const m = new Map(Object.entries(init));
  return {
    get length() {
      return m.size;
    },
    key: (i: number) => Array.from(m.keys())[i] ?? null,
    getItem: (k: string) => m.get(k) ?? null,
    setItem: (k: string, v: string) => void m.set(k, v),
    removeItem: (k: string) => void m.delete(k),
    dump: () => Object.fromEntries(m),
  };
}

test("moves nora.* keys to lyris.* without overwriting newer values", () => {
  const s = memStore({ "nora.lastStoryId": "3", "nora.draft.3": "chào", "lyris.draft.3": "mới", other: "x" });
  assert.equal(migrateLegacyKeys(s), 1);
  assert.deepEqual(s.dump(), { other: "x", "lyris.draft.3": "mới", "lyris.lastStoryId": "3" });
});
