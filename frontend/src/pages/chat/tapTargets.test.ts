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

test("chat header: 'Suy nghĩ' and the Story/DM segments are 44px tall on phones (F26, #/chat at 390px)", () => {
  const menu = readFileSync(new URL("./ThoughtMenu.tsx", import.meta.url), "utf8");
  const trigger = buttonTags(menu).filter((t) => /ref=\{trigger\}/.test(t));
  assert.equal(trigger.length, 1);
  assert.match(trigger[0] ?? "", /max-sm:h-11/);

  // The header's Story/DM switch is a SegmentedControl: on phones every size gives 44px segments.
  const header = readFileSync(new URL("./ChatHeader.tsx", import.meta.url), "utf8");
  assert.match(header, /<SegmentedControl/);
  const seg = readFileSync(new URL("../../components/ui/SegmentedControl.tsx", import.meta.url), "utf8");
  const sizes = seg.slice(seg.indexOf("const SEG = {"), seg.indexOf("} as const;"));
  for (const size of ["md", "sm"]) {
    const line = sizes.split("\n").find((l) => l.trim().startsWith(`${size}:`)) ?? "";
    assert.match(line, /max-sm:h-11/, `${size}: ${line}`);
    assert.match(line, /max-sm:min-w-11/, `${size}: ${line}`);
  }
  // Header icon buttons stay the 44px default (no size="sm").
  const icons = header.match(/<IconButton[\s\S]*?\/>/g) ?? [];
  assert.ok(icons.length >= 3, `found ${icons.length}`);
  for (const t of icons) assert.doesNotMatch(t, /size="sm"/, t);
});

test("heart drawer: every small button is 44px tall on phones (DESIGN.md tap targets)", () => {
  const src = readFileSync(new URL("./HeartDrawer.tsx", import.meta.url), "utf8");
  const small = buttonTags(src).filter((t) => /size="sm"/.test(t));
  assert.ok(small.length >= 8, `found ${small.length}`);
  const short = small.filter((t) => !t.includes("max-sm:h-11"));
  assert.deepEqual(short, []);
});

test("Button and IconButton size sm are 44px on phones (design/README: vùng chạm tối thiểu 44px)", () => {
  // Message actions (Tạo lại, Thích, Chê, Sửa, Xoá từ đây, Báo cáo) and the Huỷ/Xoá of 'Xác nhận xoá' are size="sm".
  const src = readFileSync(new URL("../../components/ui/Button.tsx", import.meta.url), "utf8");
  const block = (name: string) => src.slice(src.indexOf(`const ${name}`), src.indexOf("};", src.indexOf(`const ${name}`)));
  const sm = (name: string) => block(name).split("\n").find((l) => l.trim().startsWith("sm:")) ?? "";
  assert.match(sm("SIZE"), /max-sm:h-11/, sm("SIZE"));
  assert.match(sm("ICON_SIZE"), /max-sm:h-11/, sm("ICON_SIZE"));
  assert.match(sm("ICON_SIZE"), /max-sm:w-11/, sm("ICON_SIZE"));
  // Desktop keeps the dense 36px row.
  assert.match(sm("SIZE"), /\bh-9\b/);
  assert.match(sm("ICON_SIZE"), /\bh-9 w-9\b/);
});

test("hub header: the Lyris wordmark link (home) is a 44px tap target (bot measures `header a[href]` at 390px)", () => {
  const src = readFileSync(new URL("../../components/shell/HubHeader.tsx", import.meta.url), "utf8");
  const at = src.indexOf('<a href={routeHref({ name: "hub" })}');
  assert.ok(at > 0);
  const tag = src.slice(at, src.indexOf(">", at) + 1);
  assert.match(tag, /\bmin-h-11\b/, tag);
  assert.match(tag, /\bmin-w-11\b/, tag);
});
