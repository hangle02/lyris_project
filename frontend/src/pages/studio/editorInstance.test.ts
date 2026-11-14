import { test } from "node:test";
import assert from "node:assert/strict";
import { nextEditorInstance } from "./editorInstance.ts";
import type { AdoptedId, EditorInstance } from "./editorInstance.ts";

test("same address keeps the same instance", () => {
  const inst: EditorInstance = { key: 3, cardId: 12 };
  assert.equal(nextEditorInstance(inst, 12, null), inst);
});

test("first save of a new card keeps the editor (new -> its own id)", () => {
  const inst: EditorInstance = { key: 0, cardId: null };
  const adopted: AdoptedId = { key: 0, id: 12 };
  assert.deepEqual(nextEditorInstance(inst, 12, adopted), { key: 0, cardId: 12 });
});

test("Nhân bản then Back remounts instead of reusing the copy's editor", () => {
  // new -> saved as 12 (kept), duplicate -> 13 (remount), Back -> 12 must remount again.
  let inst: EditorInstance = { key: 0, cardId: null };
  const adopted: AdoptedId = { key: 0, id: 12 };
  inst = nextEditorInstance(inst, 12, adopted);
  assert.deepEqual(inst, { key: 0, cardId: 12 });
  inst = nextEditorInstance(inst, 13, adopted);
  assert.deepEqual(inst, { key: 1, cardId: 13 });
  inst = nextEditorInstance(inst, 12, adopted);
  assert.deepEqual(inst, { key: 2, cardId: 12 });
});

test("a later new editor does not adopt an id another editor created", () => {
  // Editor 0 saved card 12; the user opens "new" (editor 1), then presses Back to #/studio/12.
  const adopted: AdoptedId = { key: 0, id: 12 };
  let inst: EditorInstance = { key: 0, cardId: 12 };
  inst = nextEditorInstance(inst, null, adopted);
  assert.deepEqual(inst, { key: 1, cardId: null });
  inst = nextEditorInstance(inst, 12, adopted);
  assert.deepEqual(inst, { key: 2, cardId: 12 });
});

test("an unrelated id from a new editor remounts", () => {
  const inst: EditorInstance = { key: 4, cardId: null };
  assert.deepEqual(nextEditorInstance(inst, 7, { key: 4, id: 12 }), { key: 5, cardId: 7 });
  assert.deepEqual(nextEditorInstance(inst, 7, null), { key: 5, cardId: 7 });
});
