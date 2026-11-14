import { test } from "node:test";
import assert from "node:assert/strict";
import { hasWorldBlock, roleLabel, sampleTurnNote } from "./previewLogic.ts";

test("roleLabel: the last user message names block D when the preview has one", () => {
  assert.equal(roleLabel(0, 4, "system"), "System · khối A + B + C");
  assert.equal(roleLabel(3, 4, "user"), "Lượt người chơi + khối F");
  assert.equal(roleLabel(3, 4, "user", true), "Khối D + lượt người chơi + khối F");
  assert.equal(roleLabel(1, 4, "user", true), "Người chơi");
  assert.equal(roleLabel(2, 4, "assistant", true), "Nhân vật");
});

test("hasWorldBlock / sampleTurnNote", () => {
  assert.equal(hasWorldBlock({ A: 900, D: 91, total: 2000 }), true);
  assert.equal(hasWorldBlock({ A: 900, D: 0 }), false);
  assert.equal(hasWorldBlock({ A: 900 }), false);
  assert.equal(hasWorldBlock(null), false);
  assert.match(sampleTurnNote(true), /khối D và khối F/);
  assert.doesNotMatch(sampleTurnNote(false), /khối D/);
});
