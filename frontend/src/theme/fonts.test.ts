import { test } from "node:test";
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

// F26: the three self-hosted fonts must carry the Vietnamese glyphs (Ặ ặ Ỡ ỡ Ừ ừ đ Đ…), from local files.
const SRC = fileURLToPath(new URL("..", import.meta.url));
const FRONTEND = dirname(SRC);
const FAMILIES = {
  "plus-jakarta-sans": { family: "Plus Jakarta Sans", token: "--font-sans" },
  "be-vietnam-pro": { family: "Be Vietnam Pro", token: "--font-story" },
  "cormorant-garamond": { family: "Cormorant Garamond", token: "--font-brand" },
} as const;
type Pkg = keyof typeof FAMILIES;

/** Each `import "@fontsource/<pkg>/<file>.css"` in main.tsx. */
function fontImports(): { pkg: Pkg; file: string }[] {
  const main = readFileSync(join(SRC, "main.tsx"), "utf8");
  return [...main.matchAll(/import\s+"@fontsource\/([a-z-]+)\/([\w-]+\.css)";/g)].map((m) => ({ pkg: m[1] as Pkg, file: m[2] ?? "" }));
}

/** The `@font-face` blocks of one fontsource CSS file. */
function faces(css: string): string[] {
  return [...css.matchAll(/@font-face\s*{([^}]*)}/g)].map((m) => m[1] ?? "");
}

/** U+XXXX or U+XXXX-YYYY pieces of a unicode-range, as [from, to]. */
function ranges(block: string): [number, number][] {
  const value = block.match(/unicode-range:\s*([^;]+);/)?.[1] ?? "";
  return value.split(",").map((part) => {
    const [a = "", b = a] = part.trim().replace(/^U\+/i, "").split("-");
    return [parseInt(a, 16), parseInt(b, 16)] as [number, number];
  });
}

const VIETNAMESE = [..."ẶặỠỡỪừĐđƠơƯưẤấỘộ"].map((c) => c.codePointAt(0)!);

test("main.tsx imports all three fonts (UI, story text, wordmark)", () => {
  const pkgs = new Set(fontImports().map((i) => i.pkg));
  assert.deepEqual([...pkgs].sort(), Object.keys(FAMILIES).sort());
});

test("every imported font file has a Vietnamese @font-face (U+1EA0-1EF9, đ, ơ, ư) served from a local file", () => {
  const problems: string[] = [];
  for (const { pkg, file } of fontImports()) {
    const cssPath = join(FRONTEND, "node_modules", "@fontsource", pkg, file);
    const css = readFileSync(cssPath, "utf8");
    const family = FAMILIES[pkg].family;
    const covered = (cp: number) =>
      faces(css).some(
        (b) => b.includes(`font-family: '${family}'`) && ranges(b).some(([lo, hi]) => cp >= lo && cp <= hi),
      );
    const missing = VIETNAMESE.filter((cp) => !covered(cp)).map((cp) => String.fromCodePoint(cp));
    if (missing.length) problems.push(`${pkg}/${file}: không có ${missing.join(" ")}`);
    const viet = faces(css).find((b) => ranges(b).some(([lo, hi]) => lo <= 0x1ea0 && hi >= 0x1ef9));
    const url = viet?.match(/url\((\.\/files\/[^)]+\.woff2)\)/)?.[1];
    if (!url) problems.push(`${pkg}/${file}: khối tiếng Việt không có file .woff2 cục bộ`);
    else if (!existsSync(join(dirname(cssPath), url))) problems.push(`${pkg}/${file}: thiếu ${url}`);
    else if (!/vietnamese/.test(url)) problems.push(`${pkg}/${file}: ${url} không phải bộ chữ tiếng Việt`);
  }
  assert.deepEqual(problems, []);
});

test("the font tokens put each self-hosted family first", () => {
  const css = readFileSync(join(SRC, "index.css"), "utf8");
  for (const { family, token } of Object.values(FAMILIES)) {
    const value = css.match(new RegExp(`${token}:\\s*([^;]+);`))?.[1] ?? "";
    assert.ok(value.trim().startsWith(`"${family}"`), `${token}: ${value}`);
  }
});
