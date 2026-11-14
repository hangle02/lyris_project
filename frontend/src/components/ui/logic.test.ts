import { test } from "node:test";
import assert from "node:assert/strict";
import {
  OverlayStack,
  cx,
  initialFontSize,
  initialOf,
  meterPercent,
  nextFocusIndex,
  portraitRadius,
  switchState,
  radioKeyTarget,
} from "./logic.ts";

test("cx joins truthy classes", () => {
  assert.equal(cx("a", false, null, undefined, "", "b"), "a b");
  assert.equal(cx(), "");
});

test("initialOf takes the first letter, keeps Vietnamese diacritics", () => {
  assert.equal(initialOf("hạ Vy"), "H");
  assert.equal(initialOf("  ưng"), "Ư");
  assert.equal(initialOf("ẩn"), "Ẩ");
  assert.equal(initialOf(""), "?");
  assert.equal(initialOf("   "), "?");
});

test("portraitRadius stays in the soft family", () => {
  assert.equal(portraitRadius(48), 14);
  assert.equal(portraitRadius(20), 8);
  assert.equal(portraitRadius(32), 10);
  assert.equal(portraitRadius(96), 20);
  assert.equal(portraitRadius(300), 20);
});

test("initialFontSize has a floor", () => {
  assert.equal(initialFontSize(16), 11);
  assert.equal(initialFontSize(48), 20);
});

test("nextFocusIndex wraps both ways", () => {
  assert.equal(nextFocusIndex(-1, 3, false), 0);
  assert.equal(nextFocusIndex(-1, 3, true), 2);
  assert.equal(nextFocusIndex(0, 3, false), 1);
  assert.equal(nextFocusIndex(2, 3, false), 0);
  assert.equal(nextFocusIndex(0, 3, true), 2);
  assert.equal(nextFocusIndex(1, 3, true), 0);
  assert.equal(nextFocusIndex(0, 0, false), -1);
  assert.equal(nextFocusIndex(0, 1, false), 0);
});

test("radioKeyTarget moves with arrows, Home and End", () => {
  assert.equal(radioKeyTarget("ArrowRight", 0, 2), 1);
  assert.equal(radioKeyTarget("ArrowRight", 1, 2), 0);
  assert.equal(radioKeyTarget("ArrowLeft", 0, 2), 1);
  assert.equal(radioKeyTarget("ArrowUp", 2, 3), 1);
  assert.equal(radioKeyTarget("ArrowDown", -1, 3), 1);
  assert.equal(radioKeyTarget("Home", 2, 3), 0);
  assert.equal(radioKeyTarget("End", 0, 3), 2);
  assert.equal(radioKeyTarget("Enter", 0, 3), null);
  assert.equal(radioKeyTarget("ArrowRight", 0, 0), null);
});

test("meterPercent clamps and guards", () => {
  assert.equal(meterPercent(50), 50);
  assert.equal(meterPercent(150), 100);
  assert.equal(meterPercent(-3), 0);
  assert.equal(meterPercent(9.4, 24).toFixed(2), "39.17");
  assert.equal(meterPercent(Number.NaN), 0);
  assert.equal(meterPercent(5, 0), 0);
});

test("OverlayStack: only the newest is on top", () => {
  const s = new OverlayStack();
  assert.equal(s.isTop("a"), false);
  s.push("a");
  s.push("b");
  assert.equal(s.isTop("b"), true);
  assert.equal(s.isTop("a"), false);
  assert.equal(s.size, 2);
  s.remove("b");
  assert.equal(s.isTop("a"), true);
  s.push("a");
  assert.equal(s.size, 1);
  s.remove("a");
  assert.equal(s.size, 0);
});

test("switchState: saving keeps the switch focusable (aria-disabled), disabled stays disabled", () => {
  assert.deepEqual(switchState(false, true), { disabled: false, ariaDisabled: true, ariaBusy: true, inert: true });
  assert.deepEqual(switchState(true, false), { disabled: true, ariaDisabled: undefined, ariaBusy: undefined, inert: true });
  assert.deepEqual(switchState(undefined, undefined), { disabled: false, ariaDisabled: undefined, ariaBusy: undefined, inert: false });
});
