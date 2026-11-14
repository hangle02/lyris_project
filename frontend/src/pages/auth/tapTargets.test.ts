import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const read = (rel: string) => readFileSync(new URL(rel, import.meta.url), "utf8");

/** Opening `<Button …>` tags of a TSX source (brace-aware, so `=>` inside props does not end a tag). */
function buttonTags(source: string): string[] {
  const tags: string[] = [];
  let from = 0;
  for (;;) {
    const start = source.indexOf("<Button", from);
    if (start < 0) return tags;
    let depth = 0;
    let i = start;
    for (; i < source.length; i++) {
      const ch = source[i];
      if (ch === "{") depth++;
      else if (ch === "}") depth--;
      else if (ch === ">" && depth === 0) break;
    }
    tags.push(source.slice(start, i + 1));
    from = i + 1;
  }
}

test("PasswordField: the Hiện/Ẩn toggle is 44px tall on phones (every sign-in and password form)", () => {
  const src = read("./AuthLayout.tsx");
  const field = src.slice(src.indexOf("export const PasswordField"), src.indexOf("export function AuthLink"));
  const tags = buttonTags(field);
  assert.equal(tags.length, 1);
  assert.match(tags[0] ?? "", /max-sm:h-11/);
});

test("Đăng xuất mọi thiết bị: both confirm buttons are 44px tall on phones", () => {
  const src = read("../../components/shell/AccountSheet.tsx");
  const start = src.indexOf('aria-label="Đăng xuất mọi thiết bị"');
  const group = src.slice(start, src.indexOf(") : (", start));
  const tags = buttonTags(group);
  assert.equal(tags.length, 2);
  for (const t of tags) assert.match(t, /max-sm:h-11/, t);
});
