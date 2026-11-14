import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { allowForcedLeave, isForcedLeave } from "./leaveGuard.ts";

const read = (rel: string) => readFileSync(new URL(rel, import.meta.url), "utf8");

test("leaveGuard: off until the app's own reset turns it on", () => {
  assert.equal(isForcedLeave(), false);
  allowForcedLeave();
  assert.equal(isForcedLeave(), true);
});

test("account reset in another tab: the unsaved-changes prompt cannot keep the old account's page", () => {
  // hooks/useAuth resetBrowser() turns the flag on before reload() ...
  const auth = read("../hooks/useAuth.ts");
  const reset = auth.slice(auth.indexOf("function resetBrowser"), auth.indexOf("export function applyAuth"));
  assert.ok(reset.includes("allowForcedLeave()"), "resetBrowser must allow the leave");
  assert.ok(reset.indexOf("allowForcedLeave()") < reset.indexOf("location.reload()"));
  // ... and the Studio guard's beforeunload handler lets that reload through without asking.
  const guard = read("../pages/studio/useUnsavedGuard.ts");
  const handler = guard.slice(guard.indexOf("const onBeforeUnload"), guard.indexOf("const onNavigate"));
  assert.ok(handler.includes("isForcedLeave()"));
  assert.ok(handler.indexOf("isForcedLeave()") < handler.indexOf("preventDefault"));
});

test("profile rename reaches the sign-in store; signup drops an old remembered page", () => {
  const account = read("../hooks/useAccount.ts");
  const setAccount = account.slice(account.indexOf("export function setAccount"), account.indexOf("async function write"));
  assert.ok(setAccount.includes("syncAuthProfile(account)"));
  const signup = read("../pages/auth/SignupPage.tsx");
  assert.ok(signup.includes("takeNextHash();"));
});
