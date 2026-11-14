import { test } from "node:test";
import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = fileURLToPath(new URL(".", import.meta.url));

function tsxFiles(dir: string): string[] {
  const out: string[] = [];
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) out.push(...tsxFiles(path));
    else if (name.endsWith(".tsx")) out.push(path);
  }
  return out;
}

test('UI copy says "story"; "câu chuyện" only in the CTA "Bước vào câu chuyện"', () => {
  const offenders: string[] = [];
  for (const file of tsxFiles(ROOT)) {
    readFileSync(file, "utf8")
      .split("\n")
      .forEach((line, i) => {
        const code = line.trim();
        if (code.startsWith("//") || code.startsWith("*") || code.startsWith("/*")) return;
        if (/câu chuyện/i.test(code.replaceAll("Bước vào câu chuyện", ""))) offenders.push(`${file.slice(ROOT.length)}:${i + 1}`);
      });
  }
  assert.deepEqual(offenders, []);
});
