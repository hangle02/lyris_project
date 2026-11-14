import { test } from "node:test";
import assert from "node:assert/strict";
import { ADVANCED_STORAGE_KEY, parseAdvanced, readAdvanced, writeAdvanced } from "./advancedTools.ts";

function memoryStore() {
  const map = new Map<string, string>();
  return {
    map,
    getItem: (k: string) => map.get(k) ?? null,
    setItem: (k: string, v: string) => void map.set(k, v),
    removeItem: (k: string) => void map.delete(k),
  };
}

const throwing = {
  getItem: () => {
    throw new Error("SecurityError");
  },
  setItem: () => {
    throw new Error("QuotaExceededError");
  },
  removeItem: () => {
    throw new Error("SecurityError");
  },
};

test("parseAdvanced: off unless explicitly on", () => {
  assert.equal(parseAdvanced("1"), true);
  assert.equal(parseAdvanced("true"), true);
  assert.equal(parseAdvanced("0"), false);
  assert.equal(parseAdvanced(""), false);
  assert.equal(parseAdvanced(null), false);
  assert.equal(parseAdvanced(undefined), false);
});

test("read and write round-trip under lyris.advanced; off removes the key", () => {
  const s = memoryStore();
  assert.equal(readAdvanced(s), false);
  assert.equal(writeAdvanced(s, true), true);
  assert.equal(s.map.get(ADVANCED_STORAGE_KEY), "1");
  assert.equal(readAdvanced(s), true);
  writeAdvanced(s, false);
  assert.equal(s.map.has(ADVANCED_STORAGE_KEY), false);
  assert.equal(readAdvanced(s), false);
});

test("missing or throwing storage reads as off and never throws", () => {
  assert.equal(readAdvanced(null), false);
  assert.equal(readAdvanced(throwing), false);
  assert.equal(writeAdvanced(throwing, true), false);
  assert.equal(writeAdvanced(undefined, true), false);
});
