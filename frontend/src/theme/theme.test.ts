import { test } from "node:test";
import assert from "node:assert/strict";
import { THEME_META_COLORS, oppositeTheme, parseTheme, resolveTheme, themeFromSearch } from "./theme.ts";

test("parseTheme accepts only the two themes", () => {
  assert.equal(parseTheme("dark"), "dark");
  assert.equal(parseTheme("light"), "light");
  assert.equal(parseTheme("Dark"), null);
  assert.equal(parseTheme(""), null);
  assert.equal(parseTheme(null), null);
  assert.equal(parseTheme(1), null);
});

test("resolveTheme: override, then stored choice, then system, then dark", () => {
  assert.equal(resolveTheme(null, false), "dark");
  assert.equal(resolveTheme(null, true), "light");
  assert.equal(resolveTheme("dark", true), "dark");
  assert.equal(resolveTheme("light", false), "light");
  assert.equal(resolveTheme("garbage", true), "light");
  assert.equal(resolveTheme("dark", false, "light"), "light");
  assert.equal(resolveTheme("light", true, "nonsense"), "light");
  assert.equal(resolveTheme(undefined, false, null), "dark");
});

test("oppositeTheme flips", () => {
  assert.equal(oppositeTheme("dark"), "light");
  assert.equal(oppositeTheme("light"), "dark");
});

test("themeFromSearch reads ?theme=", () => {
  assert.equal(themeFromSearch(""), null);
  assert.equal(themeFromSearch("?theme=light"), "light");
  assert.equal(themeFromSearch("?x=1&theme=dark"), "dark");
  assert.equal(themeFromSearch("?theme=blue"), null);
});

test("meta colours are the bg tokens", () => {
  assert.equal(THEME_META_COLORS.dark, "#130D14");
  assert.equal(THEME_META_COLORS.light, "#FAF5EE");
});
