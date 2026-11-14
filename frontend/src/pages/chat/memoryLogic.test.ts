import { test } from "node:test";
import assert from "node:assert/strict";
import {
  drawerLoadState,
  focusIndexAfterForget,
  forgetPrompt,
  INVITE_LINE,
  memoryKindLabel,
  memoryStatus,
  sceneRows,
} from "./memoryLogic.ts";

test("memoryKindLabel tells events from known facts", () => {
  assert.equal(memoryKindLabel("memory"), "Sự kiện");
  assert.equal(memoryKindLabel("fact"), "Điều đã biết");
});

test("memoryStatus: quiet while remembering, dots while reading again, plain invite, no counts", () => {
  assert.equal(memoryStatus({ pending: false, unprocessed_turns: 0 }), null);
  // Right after a reply the turn is being remembered: nothing is said (Phase 3b, no job status).
  assert.equal(memoryStatus({ pending: true, unprocessed_turns: 1 }), null);
  assert.equal(memoryStatus({ pending: true, unprocessed_turns: 12 }), null);
  // The player asked to read the story again: typing dots until the jobs are done.
  assert.deepEqual(memoryStatus({ pending: true, unprocessed_turns: 12 }, { rebuilding: true }), { kind: "reading" });
  // Nothing runs but turns were never read (old story, failed jobs): invite a rebuild, no number.
  assert.deepEqual(memoryStatus({ pending: false, unprocessed_turns: 3 }), { kind: "invite", text: INVITE_LINE });
  assert.equal(INVITE_LINE, "Lyris chưa đọc hết story này.");
  assert.deepEqual(memoryStatus({ pending: false, unprocessed_turns: 3 }, { rebuilding: true }), { kind: "invite", text: INVITE_LINE });
});
test("forgetPrompt names what is forgotten and by whom", () => {
  assert.equal(forgetPrompt("memory", "Hạ Vy"), "Quên sự kiện này? Hạ Vy sẽ không nhắc lại nữa.");
  assert.equal(forgetPrompt("fact", "Hạ Vy"), "Quên điều này? Hạ Vy sẽ không còn biết nữa.");
  assert.equal(forgetPrompt("memory", " "), "Quên sự kiện này? Nhân vật sẽ không nhắc lại nữa.");
});

test("sceneRows: place and time when known", () => {
  assert.deepEqual(sceneRows({ location: " Gác xép ", in_world_time: "Chiều tối" }), [
    { label: "Nơi chốn", value: "Gác xép" },
    { label: "Thời gian", value: "Chiều tối" },
  ]);
  assert.deepEqual(sceneRows({ location: null, in_world_time: "  " }), []);
});

test("drawerLoadState: a failed first load is not 'no data'", () => {
  assert.equal(drawerLoadState(null, null), "loading");
  assert.equal(drawerLoadState(null, "Mất kết nối"), "failed");
  assert.equal(drawerLoadState({}, "Mất kết nối"), "ready");
  assert.equal(drawerLoadState({}, null), "ready");
});

test("focusIndexAfterForget: the next row, the new last row, or the section", () => {
  assert.equal(focusIndexAfterForget(0, 3), 0);
  assert.equal(focusIndexAfterForget(2, 2), 1);
  assert.equal(focusIndexAfterForget(1, 2), 1);
  assert.equal(focusIndexAfterForget(0, 0), null);
});
