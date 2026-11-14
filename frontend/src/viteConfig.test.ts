// Phase 4b (docs/auth.md §3.3, §3.7, §3.8): guard rails on the Vite dev server, read as text so the test does
// not start Vite. A live check (curl through a running Vite) is in the manual checklist (auth.md §8.3).
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const config = readFileSync(new URL("../vite.config.ts", import.meta.url), "utf8");
const code = config
  .split("\n")
  .filter((line) => !line.trim().startsWith("//"))
  .join("\n");

test("vite: /api proxy forwards the real client address (xfwd) and keeps the original Host", () => {
  assert.match(code, /"\/api":\s*\{\s*target:\s*apiTarget,\s*xfwd:\s*true\s*\}/);
  assert.doesNotMatch(code, /changeOrigin/);
  // the same proxy object is used by `vite` and `vite preview`
  assert.equal(code.match(/proxy:\s*apiProxy/g)?.length, 2);
});

test("vite: never allow every Host (DNS rebinding)", () => {
  assert.doesNotMatch(code, /allowedHosts\s*:\s*true/);
});

test("vite: only frontend/ is served; the database and data/ are denied", () => {
  assert.match(code, /allow:\s*\[frontendDir\]/);
  assert.match(code, /strict:\s*true/);
  for (const pattern of ['"**/*.db"', '"**/*.db-wal"', '"**/data/**"', '".env"', '"**/.git/**"']) {
    assert.ok(code.includes(pattern), pattern);
  }
});
