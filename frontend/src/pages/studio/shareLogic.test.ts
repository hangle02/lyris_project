import { test } from "node:test";
import assert from "node:assert/strict";
import { canShare, isPublic, shareDescription, unshareNote, visibilityBadge } from "./shareLogic.ts";

test("the switch is hidden for templates", () => {
  assert.equal(canShare({ template: true }), false);
  assert.equal(canShare({ template: false }), true);
});

test("the description names the character and never promises the secrets stay hidden", () => {
  const d = shareDescription("Hạ Vy");
  assert.match(d, /^Người khác trên Lyris này thấy Hạ Vy ở Khám phá/);
  assert.match(d, /không xem được bí mật, mục tiêu hay sổ thế giới trong hồ sơ/);
  assert.match(d, /Hạ Vy vẫn có thể tự kể ra điều mình biết/);
  assert.match(d, /Story của bạn luôn riêng tư\.$/);
  assert.doesNotMatch(d, /không thấy bí mật/);
  assert.doesNotMatch(d, /câu chuyện/);
  assert.match(shareDescription("  "), /thấy nhân vật này ở Khám phá/);
});

test("turning a shared character off reminds that started stories go on", () => {
  assert.equal(
    unshareNote("Hạ Vy", { checked: false, savedPublic: true }),
    "Story mà người khác đã bắt đầu vẫn tiếp tục với Hạ Vy như lúc họ bắt đầu.",
  );
  assert.equal(unshareNote("Hạ Vy", { checked: true, savedPublic: true }), null);
  assert.equal(unshareNote("Hạ Vy", { checked: false, savedPublic: false }), null);
  assert.equal(unshareNote("Hạ Vy", { checked: true, savedPublic: false }), null);
});

test("Studio list badge: Công khai replaces Riêng tư; templates have none", () => {
  assert.deepEqual(visibilityBadge({ template: false, visibility: "public" }), { label: "Công khai", tone: "accent" });
  assert.deepEqual(visibilityBadge({ template: false, visibility: "private" }), { label: "Riêng tư", tone: "neutral" });
  assert.deepEqual(visibilityBadge({ template: false, visibility: undefined }), { label: "Riêng tư", tone: "neutral" });
  assert.equal(visibilityBadge({ template: true, visibility: "public" }), null);
  assert.equal(isPublic("public"), true);
  assert.equal(isPublic("unlisted"), false);
});
