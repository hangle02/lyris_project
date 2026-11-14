import { test } from "node:test";
import assert from "node:assert/strict";
import {
  ACCOUNT_KEY,
  accountSwitch,
  clearAccountData,
  gateOf,
  isAccountDataKey,
  NEXT_KEY,
  rememberNext,
  safeNext,
  signalsAuth,
  takeNext,
  withAccountProfile,
} from "./auth.ts";
import type { KeyStore } from "./auth.ts";
import { parseRoute } from "./router.ts";
import type { AuthAccount, AuthState } from "../types.ts";

function store(entries: Record<string, string> = {}): KeyStore & { map: Map<string, string> } {
  const map = new Map(Object.entries(entries));
  return {
    map,
    get length() {
      return map.size;
    },
    key: (i) => [...map.keys()][i] ?? null,
    getItem: (k) => map.get(k) ?? null,
    setItem: (k, v) => void map.set(k, v),
    removeItem: (k) => void map.delete(k),
  };
}

const ACCOUNT: AuthAccount = {
  id: 3,
  handle: "minhthu.viet",
  display_name: "Minh Thư",
  avatar_url: null,
  role: "member",
  must_change_password: false,
  profile_completed: true,
};
const OUT: AuthState = { setup_required: false, setup_needs_profile: false, account: null };
const IN: AuthState = { ...OUT, account: ACCOUNT };

test("gateOf: setup first, then sign in, then the forced password change, then the app", () => {
  const hub = parseRoute("#/");
  assert.equal(gateOf({ setup_required: true, setup_needs_profile: false, account: null }, hub), "setup");
  // Setup wins over any hash, even the signup page.
  assert.equal(gateOf({ setup_required: true, setup_needs_profile: true, account: null }, parseRoute("#/signup")), "setup");
  assert.equal(gateOf(OUT, hub), "login");
  assert.equal(gateOf(OUT, parseRoute("#/chat/4")), "login");
  assert.equal(gateOf(OUT, parseRoute("#/login")), "login");
  assert.equal(gateOf(OUT, parseRoute("#/signup?code=LYR-7KQ2-M9XD-4TPA")), "signup");
  assert.equal(gateOf({ ...IN, account: { ...ACCOUNT, must_change_password: true } }, parseRoute("#/studio")), "forceChange");
  assert.equal(gateOf(IN, parseRoute("#/studio")), "app");
  assert.equal(gateOf(IN, parseRoute("#/login")), "app");
});

test("safeNext keeps hashes of this app only", () => {
  assert.equal(safeNext("#/chat/12"), "#/chat/12");
  assert.equal(safeNext("#/studio/12?section=world"), "#/studio/12?section=world");
  assert.equal(safeNext("#/u/minhthu.viet"), "#/u/minhthu.viet");
  for (const bad of [
    null,
    undefined,
    "",
    "#/",
    "#",
    "#/login",
    "#/signup?code=LYR-7KQ2-M9XD-4TPA",
    "https://evil.example/#/chat/1",
    "#//evil.example",
    "javascript:alert(1)",
    "#/chat/1 onload",
    "#/chat/<script>",
    "/chat/1",
    `#/${"a".repeat(600)}`,
  ]) {
    assert.equal(safeNext(bad as string | null), null, String(bad));
  }
});

test("rememberNext / takeNext: once, and never the sign-in pages", () => {
  const s = store();
  rememberNext(s, "#/login");
  assert.equal(s.map.has(NEXT_KEY), false);
  rememberNext(s, "#/character/7");
  assert.equal(takeNext(s), "#/character/7");
  assert.equal(takeNext(s), null);
  s.setItem(NEXT_KEY, "https://evil.example");
  assert.equal(takeNext(s), null);
  assert.equal(takeNext(null), null);
});

test("account data keys: drafts, last story, studio, next; never the browser preferences", () => {
  for (const k of ["lyris.draft.12", "lyris.lastStoryId", "lyris.studio.pendingDraft", "lyris.studio.notice", "lyris.next"]) {
    assert.ok(isAccountDataKey(k), k);
  }
  for (const k of ["lyris.theme", "lyris.advanced", "lyris.revealThoughts", ACCOUNT_KEY, "other.app"]) {
    assert.ok(!isAccountDataKey(k), k);
  }
});

test("clearAccountData empties both stores of one account's data and keeps the rest", () => {
  const local = store({
    "lyris.draft.4": "đang gõ dở",
    "lyris.draft.9": "x",
    "lyris.lastStoryId": "4",
    "lyris.theme": "light",
    "lyris.advanced": "1",
    "lyris.revealThoughts": "1",
    [ACCOUNT_KEY]: "3",
  });
  const session = store({ "lyris.studio.pendingDraft": "{}", "lyris.studio.notice": "{}", "lyris.next": "#/chat/4", "x": "y" });
  clearAccountData(local, session, null);
  assert.deepEqual([...local.map.keys()].sort(), [ACCOUNT_KEY, "lyris.advanced", "lyris.revealThoughts", "lyris.theme"]);
  assert.deepEqual([...session.map.keys()], ["x"]);
});

test("accountSwitch tells the same account, the first one, and another one apart", () => {
  assert.equal(accountSwitch(null, 3), "first");
  assert.equal(accountSwitch("", 3), "first");
  assert.equal(accountSwitch("3", 3), "same");
  assert.equal(accountSwitch("1", 3), "changed");
});

test("signalsAuth: 401, the forced password change and setup, but not the sign-in forms", () => {
  assert.equal(signalsAuth("/stories", 401, "auth_required"), true);
  assert.equal(signalsAuth("/stories/3/messages", 401, null), true);
  assert.equal(signalsAuth("/cards", 403, "password_change_required"), true);
  assert.equal(signalsAuth("/cards", 409, "setup_required"), true);
  assert.equal(signalsAuth("/admin/accounts", 403, "owner_only"), false);
  assert.equal(signalsAuth("/cards", 403, "csrf"), false);
  assert.equal(signalsAuth("/stories/3/messages", 409, null), false);
  assert.equal(signalsAuth("/auth/login", 401, null), false);
  assert.equal(signalsAuth("/auth/change-password", 400, null), false);
});

test("rememberNext: the hub drops an older remembered page (no stale landing after a later sign-in)", () => {
  const s = store();
  rememberNext(s, "#/character/12"); // signed out on a character, then signed up (signup goes to the hub)
  assert.equal(s.map.get(NEXT_KEY), "#/character/12");
  rememberNext(s, "#/"); // later signed out by the server while on the hub
  assert.equal(s.map.has(NEXT_KEY), false);
  assert.equal(takeNext(s), null);
  rememberNext(s, "#/studio/3");
  rememberNext(s, "#/login");
  assert.equal(takeNext(s), null);
});

test("signalsAuth: a 401 from Đổi mật khẩu signals (the session was dropped meanwhile)", () => {
  assert.equal(signalsAuth("/auth/change-password", 401, "auth_required"), true);
  assert.equal(signalsAuth("/auth/change-password", 400, "bad_current_password"), false);
  assert.equal(signalsAuth("/auth/change-password", 429, "rate_limited"), false);
  assert.equal(signalsAuth("/auth/login", 401, null), false);
  assert.equal(signalsAuth("/auth/signup", 401, null), false);
  assert.equal(signalsAuth("/auth/setup-owner", 409, "setup_required"), false);
  assert.equal(signalsAuth("/auth/logout-all", 401, "auth_required"), false);
});

test("withAccountProfile: a profile rename reaches the sign-in state", () => {
  const state: AuthState = { setup_required: false, setup_needs_profile: false, account: ACCOUNT };
  const renamed = withAccountProfile(state, { id: ACCOUNT.id, handle: "moi", display_name: "Tên mới", avatar_url: "/a.png", profile_completed: true });
  assert.notEqual(renamed, state);
  assert.deepEqual(renamed.account, { ...ACCOUNT, handle: "moi", display_name: "Tên mới", avatar_url: "/a.png" });
  assert.equal(renamed.account?.role, ACCOUNT.role);
  // Nothing changed, another account, or signed out: the same object (no re-render).
  const same = withAccountProfile(state, { id: ACCOUNT.id, handle: ACCOUNT.handle, display_name: ACCOUNT.display_name, avatar_url: null, profile_completed: true });
  assert.equal(same, state);
  assert.equal(withAccountProfile(state, { id: 99, handle: "x", display_name: "X", avatar_url: null, profile_completed: true }), state);
  const out: AuthState = { setup_required: false, setup_needs_profile: false, account: null };
  assert.equal(withAccountProfile(out, { id: 3, handle: "x", display_name: "X", avatar_url: null, profile_completed: true }), out);
});
