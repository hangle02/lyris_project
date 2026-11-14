import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

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

test("heart drawer: every small button is 44px tall on phones (DESIGN.md tap targets)", () => {
  const src = readFileSync(new URL("./HeartDrawer.tsx", import.meta.url), "utf8");
  const small = buttonTags(src).filter((t) => /size="sm"/.test(t));
  assert.ok(small.length >= 8, `found ${small.length}`);
  const short = small.filter((t) => !t.includes("max-sm:h-11"));
  assert.deepEqual(short, []);
});
