import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const src = readFileSync(new URL("./AdminPage.tsx", import.meta.url), "utf8");

/** The `<Modal …>` opening tag that contains `marker`. */
function modalWith(marker: string): string {
  const at = src.indexOf(marker);
  assert.ok(at >= 0, marker);
  const start = src.lastIndexOf("<Modal", at);
  return src.slice(start, src.indexOf("footer=", start));
}

test("temporary password: shown once, so the scrim and Escape cannot close it", () => {
  assert.match(modalWith('title="Mật khẩu tạm"'), /dismissible=\{false\}/);
});

test("new invite code: shown once, so the scrim and Escape cannot close it once created", () => {
  assert.match(modalWith('title={created ? "Mã mời mới" : "Tạo mã mời"}'), /dismissible=\{!sending && !created\}/);
});

test("invite link: when copying fails, the link itself is on screen to select by hand", () => {
  assert.match(src, /label="Sao chép liên kết"[^>]*onFailed=\{\(\) => setShowLink\(true\)\}/);
  const shown = src.slice(src.indexOf("{showLink && ("));
  assert.ok(shown.startsWith("{showLink && ("));
  assert.match(shown.slice(0, 300), /select-all[\s\S]*\{link\}/);
});
