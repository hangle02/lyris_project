import { test } from "node:test";
import assert from "node:assert/strict";
import { needsAccountLoad, reloadAccountOnRecovery } from "./accountLogic.ts";

const account = { handle: "ban" };

test("needsAccountLoad: loads when nothing is loaded, also after a failed load", () => {
  assert.equal(needsAccountLoad({ account: null, error: null, loading: false }), true);
  // Regression: a failed first GET /api/account used to block every later auto-load.
  assert.equal(needsAccountLoad({ account: null, error: "Không kết nối được", loading: false }), true);
});

test("needsAccountLoad: no load while one runs or once an account is there", () => {
  assert.equal(needsAccountLoad({ account: null, error: null, loading: true }), false);
  assert.equal(needsAccountLoad({ account: null, error: "x", loading: true }), false);
  assert.equal(needsAccountLoad({ account, error: null, loading: false }), false);
  assert.equal(needsAccountLoad({ account, error: "x", loading: false }), false);
});

test("reloadAccountOnRecovery: only when the backend comes back and no account is loaded", () => {
  const missing = { account: null, error: "x", loading: false };
  assert.equal(reloadAccountOnRecovery("down", "ok", missing), true);
  assert.equal(reloadAccountOnRecovery("down", "warn", missing), true);
  assert.equal(reloadAccountOnRecovery("down", "down", missing), false);
  assert.equal(reloadAccountOnRecovery("checking", "ok", missing), true);
  assert.equal(reloadAccountOnRecovery("ok", "down", missing), false);
  assert.equal(reloadAccountOnRecovery("down", "checking", missing), false);
  assert.equal(reloadAccountOnRecovery("ok", "ok", missing), false);
  assert.equal(reloadAccountOnRecovery(null, "ok", missing), false);
  assert.equal(reloadAccountOnRecovery("down", "ok", { account, error: null, loading: false }), false);
  assert.equal(reloadAccountOnRecovery("down", "ok", { account: null, error: null, loading: true }), false);
});
