import { test } from "node:test";
import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { filenameOf } from "./api/client.ts";
import { CLIENT_EVENTS } from "./lib/track.ts";

const ROOT = fileURLToPath(new URL(".", import.meta.url));

function sources(dir: string): { path: string; text: string }[] {
  const out: { path: string; text: string }[] = [];
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) out.push(...sources(path));
    else if (/\.tsx?$/.test(name) && !name.endsWith(".test.ts")) out.push({ path: path.slice(ROOT.length), text: readFileSync(path, "utf8") });
  }
  return out;
}

const ALL = sources(ROOT);
const read = (rel: string) => readFileSync(new URL(rel, import.meta.url), "utf8");

test("every client event of the tracking plan is sent from a screen (content_reported stays server-side)", () => {
  const calls = ALL.flatMap((f) => [...f.text.matchAll(/\btrack(?:InStory)?\(\s*"([a-z_]+)"/g)].map((m) => m[1]));
  for (const name of Object.keys(CLIENT_EVENTS)) {
    assert.ok(calls.includes(name), `${name} is never sent`);
  }
  assert.ok(!("content_reported" in CLIENT_EVENTS), "reports are recorded by the server only (detached from the account)");
  assert.ok(!calls.includes("content_reported"), "a report is recorded by the server; the client must not send it too");
});

test("tracking calls only pass fixed codes, booleans or numbers (no variable text)", () => {
  // Every props object literal in a track call: values are string literals, booleans, numbers, or
  // calls of the code helpers (vibeCode, chipPosition, profileFrom, displayMode) / known enum variables.
  let checked = 0;
  const allowed = /^(?:"[a-z_]+"|true|false|\d+|code !== null|fullSignIn|source|vibeCode\(.*\)|chipPosition\(.*\)|profileFrom\(.*\)|displayMode\(.*\)|Math\.min\(3, i \+ 1\))$/;
  for (const f of ALL) {
    for (const m of f.text.matchAll(/\btrack(?:InStory)?\(\s*"[a-z_]+"\s*,\s*\{([^}]*)\}/g)) {
      for (const pair of (m[1] ?? "").split(/,(?![^(]*\))/)) {
        const value = pair.split(":").slice(1).join(":").trim();
        if (!value) continue;
        assert.match(value, allowed, `${f.path}: ${pair.trim()}`);
        checked++;
      }
    }
  }
  assert.ok(checked >= 7, `checked ${checked} properties`);
});

test("legal links and data controls are where the plan puts them", () => {
  const sheet = read("./components/shell/AccountSheet.tsx");
  for (const words of ['href="#/privacy"', 'href="#/terms"', "SHARING_LABEL", "EXPORT_LABEL", "DELETE_LABEL", "DeleteView"]) {
    assert.ok(sheet.includes(words), `AccountSheet: ${words}`);
  }
  assert.ok(read("./pages/auth/LoginPage.tsx").includes("<LegalLinks />"));
  for (const page of ["./pages/auth/SignupPage.tsx", "./pages/auth/SetupPage.tsx"]) {
    const src = read(page);
    assert.ok(src.includes("<ConsentField"), page);
    assert.ok(src.includes("accept_terms: true"), page);
    // accept_terms is only ever sent after the box was ticked.
    assert.ok(src.indexOf("if (!agreed) found.consent") < src.indexOf("accept_terms: true"), page);
  }
  assert.ok(read("./pages/character/StartStorySheet.tsx").includes("{AI_DISCLAIMER}"));
});

test("report: only on a character's saved reply, the text goes along only when the box is ticked", () => {
  const row = read("./components/MessageItem.tsx");
  assert.match(row, /!isUser && onReport && message\.id !== null/);
  const sheet = read("./pages/chat/ReportSheet.tsx");
  assert.match(sheet, /useState\(false\);\s*\n\s*const \[sending/, "share box starts off");
  assert.match(sheet, /share_text: share/);
});

test("filenameOf reads the export's file name, never a path", () => {
  assert.equal(filenameOf('attachment; filename="lyris-mai-20261114.json"'), "lyris-mai-20261114.json");
  assert.equal(filenameOf("attachment; filename=lyris.json"), "lyris.json");
  assert.equal(filenameOf('attachment; filename="../../etc/passwd"'), "passwd");
  assert.equal(filenameOf("attachment"), null);
  assert.equal(filenameOf(null), null);
});
