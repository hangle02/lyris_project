import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { inlineText, parseInline, parseMarkdown, safeHref, slugify } from "./markdown.ts";
import type { Block } from "./markdown.ts";

test("inline marks: bold, italic, code, links; unclosed marks stay as typed", () => {
  assert.deepEqual(parseInline("a **b** c"), [
    { kind: "text", text: "a " },
    { kind: "strong", children: [{ kind: "text", text: "b" }] },
    { kind: "text", text: " c" },
  ]);
  assert.deepEqual(parseInline("*(ghi chú)*"), [{ kind: "em", children: [{ kind: "text", text: "(ghi chú)" }] }]);
  assert.deepEqual(parseInline("cookie `lyris_anon` 1 năm"), [
    { kind: "text", text: "cookie " },
    { kind: "code", text: "lyris_anon" },
    { kind: "text", text: " 1 năm" },
  ]);
  assert.deepEqual(parseInline("2 * 3 = 6"), [{ kind: "text", text: "2 * 3 = 6" }]);
  assert.deepEqual(parseInline("**mở"), [{ kind: "text", text: "**mở" }]);
  assert.equal(inlineText(parseInline("**[ĐIỀN EMAIL LIÊN HỆ]** *(sẽ điền)*")), "[ĐIỀN EMAIL LIÊN HỆ] (sẽ điền)");
});

test("links: the other legal page stays in the app; unsafe targets become plain text", () => {
  assert.deepEqual(parseInline("[Chính sách quyền riêng tư](privacy.md)"), [
    { kind: "link", href: "#/privacy", external: false, children: [{ kind: "text", text: "Chính sách quyền riêng tư" }] },
  ]);
  assert.deepEqual(safeHref("terms.md"), { href: "#/terms", external: false });
  assert.deepEqual(safeHref("https://posthog.com/privacy"), { href: "https://posthog.com/privacy", external: true });
  assert.equal(safeHref("javascript:alert(1)"), null);
  assert.equal(safeHref("data:text/html,x"), null);
  assert.equal(safeHref("//evil.example"), null);
  assert.equal(inlineText(parseInline("[bấm](javascript:alert(1))")), "bấm)");
  assert.ok(!JSON.stringify(parseInline("[bấm](javascript:alert(1))")).includes("javascript"));
});

test("blocks: headings with ids, lists, tables, rule, paragraphs", () => {
  const md = [
    "# Tiêu đề",
    "",
    "Đoạn một",
    "vẫn đoạn một.",
    "",
    "## 1. Tóm tắt",
    "",
    "- mục **một**",
    "- mục hai",
    "  nối dòng",
    "",
    "3. ba",
    "4. bốn",
    "",
    "| Tên | Để làm gì |",
    "|---|---|",
    "| `lyris_session` | Giữ đăng nhập |",
    "| a \\| b | c |",
    "",
    "---",
    "",
    "## 1. Tóm tắt",
  ].join("\n");
  const blocks = parseMarkdown(md);
  assert.deepEqual(
    blocks.map((b) => b.kind),
    ["heading", "paragraph", "heading", "list", "list", "table", "rule", "heading"],
  );
  const h = blocks[2] as Extract<Block, { kind: "heading" }>;
  assert.equal(h.level, 2);
  assert.equal(h.id, "1-tom-tat");
  assert.equal((blocks[7] as Extract<Block, { kind: "heading" }>).id, "1-tom-tat-2", "ids stay unique");
  assert.equal(inlineText((blocks[1] as Extract<Block, { kind: "paragraph" }>).text), "Đoạn một vẫn đoạn một.");
  const ul = blocks[3] as Extract<Block, { kind: "list" }>;
  assert.equal(ul.ordered, false);
  assert.deepEqual(ul.items.map(inlineText), ["mục một", "mục hai nối dòng"]);
  const ol = blocks[4] as Extract<Block, { kind: "list" }>;
  assert.equal(ol.ordered, true);
  assert.equal(ol.start, 3);
  const table = blocks[5] as Extract<Block, { kind: "table" }>;
  assert.deepEqual(table.header.map(inlineText), ["Tên", "Để làm gì"]);
  assert.deepEqual(table.rows.map((r) => r.map(inlineText)), [
    ["lyris_session", "Giữ đăng nhập"],
    ["a | b", "c"],
  ]);
});

test("slugify keeps ASCII letters and digits only", () => {
  assert.equal(slugify("4. Dữ liệu sử dụng (số liệu ẩn danh)"), "4-du-lieu-su-dung-so-lieu-an-danh");
  assert.equal(slugify("Đường"), "duong");
});

test("the real legal files parse into headings, lists and the cookie table", () => {
  for (const doc of ["privacy", "terms"]) {
    const text = readFileSync(new URL(`../../../docs/legal/${doc}.md`, import.meta.url), "utf8");
    const blocks = parseMarkdown(text);
    const headings = blocks.filter((b) => b.kind === "heading");
    assert.ok(headings.length >= 10, doc);
    assert.equal(headings[0]?.kind === "heading" && headings[0].level, 1);
    assert.ok(blocks.some((b) => b.kind === "list"), doc);
    // No stray markdown left in plain text (unparsed ** or table bars).
    const flat = JSON.stringify(blocks);
    assert.ok(!flat.includes('"text":"|'), doc);
    if (doc === "privacy") assert.ok(blocks.some((b) => b.kind === "table"));
  }
});
