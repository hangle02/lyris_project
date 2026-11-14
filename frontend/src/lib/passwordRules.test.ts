import { test } from "node:test";
import assert from "node:assert/strict";
import {
  confirmError,
  newPasswordErrors,
  PASSWORD_MISMATCH,
  PASSWORD_SAME_AS_HANDLE,
  PASSWORD_SAME_AS_OLD,
  PASSWORD_TOO_LONG,
  PASSWORD_TOO_SHORT,
  passwordError,
  passwordLength,
} from "./passwordRules.ts";

test("the sentences are the ones of docs/auth.md §7.4", () => {
  assert.equal(PASSWORD_TOO_SHORT, "Mật khẩu cần ít nhất 8 ký tự.");
  assert.equal(PASSWORD_SAME_AS_HANDLE, "Mật khẩu không được giống tên đăng nhập.");
  assert.equal(PASSWORD_MISMATCH, "Hai mật khẩu chưa giống nhau.");
});

test("length is counted after NFC, spaces count and are kept", () => {
  const nfd = "Mật khẩu".normalize("NFD");
  assert.ok(nfd.length > 8);
  assert.equal(passwordLength(nfd), 8);
  assert.equal(passwordError(nfd), null);
  assert.equal(passwordError("1234567"), PASSWORD_TOO_SHORT);
  assert.equal(passwordError("       x"), null);
  assert.equal(passwordError("a".repeat(128)), null);
  assert.equal(passwordError("a".repeat(129)), PASSWORD_TOO_LONG);
});

test("a password equal to the handle is refused, ignoring case and @", () => {
  assert.equal(passwordError("Strawberry", "@strawberry"), PASSWORD_SAME_AS_HANDLE);
  assert.equal(passwordError("@strawberry", "strawberry"), PASSWORD_SAME_AS_HANDLE);
  assert.equal(passwordError("strawberry1", "strawberry"), null);
  assert.equal(passwordError("whatever12", ""), null);
});

test("repeat must match (NFC), empty repeat is not an error while typing", () => {
  assert.equal(confirmError("Mật khẩu", "Mật khẩu".normalize("NFD")), null);
  assert.equal(confirmError("abcdefgh", ""), null);
  assert.equal(confirmError("abcdefgh", "abcdefgx"), PASSWORD_MISMATCH);
});

test("newPasswordErrors: per field, before sending", () => {
  assert.deepEqual(newPasswordErrors("hoa mua thu", "hoa mua thu"), {});
  assert.deepEqual(newPasswordErrors("short", ""), { password: PASSWORD_TOO_SHORT, confirm: PASSWORD_MISMATCH });
  assert.deepEqual(newPasswordErrors("hoa mua thu", "hoa mua he"), { confirm: PASSWORD_MISMATCH });
  assert.deepEqual(newPasswordErrors("minhthu.viet", "minhthu.viet", { handle: "minhthu.viet" }), { password: PASSWORD_SAME_AS_HANDLE });
  assert.deepEqual(newPasswordErrors("same-old-pass", "same-old-pass", { current: "same-old-pass" }), { password: PASSWORD_SAME_AS_OLD });
});
