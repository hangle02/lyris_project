import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { formatInvite, groupCode, inviteLink, normalizeCode } from "./inviteCode.ts";

interface Case {
  input: string;
  expected: string | null;
}

// The same table pytest reads (backend/tests/test_auth_units.py): both sides must agree.
const table = JSON.parse(readFileSync(new URL("./inviteCode.cases.json", import.meta.url), "utf8")) as { cases: Case[] };

test("normalizeCode follows the shared case table", () => {
  assert.ok(table.cases.length >= 10);
  for (const c of table.cases) assert.equal(normalizeCode(c.input), c.expected, JSON.stringify(c.input));
});

test("normalizeCode: iPhone dashes, nothing at all, very long input", () => {
  assert.equal(normalizeCode("LYR\u20137KQ2\u2014M9XD\u22124TPA"), "7KQ2M9XD4TPA");
  assert.equal(normalizeCode(null), null);
  assert.equal(normalizeCode(undefined), null);
  assert.equal(normalizeCode("7".repeat(101)), null);
});

test("formatInvite, groupCode and the invite link", () => {
  assert.equal(groupCode("7KQ2M9XD4TPA"), "7KQ2-M9XD-4TPA");
  assert.equal(formatInvite("7kq2m9xd4tpa"), "LYR-7KQ2-M9XD-4TPA");
  assert.equal(formatInvite("LYR-7KQ2-M9XD-4TPA"), "LYR-7KQ2-M9XD-4TPA");
  assert.equal(inviteLink("http://192.168.1.5:5173/", "LYR-7KQ2-M9XD-4TPA"), "http://192.168.1.5:5173/#/signup?code=LYR-7KQ2-M9XD-4TPA");
});
