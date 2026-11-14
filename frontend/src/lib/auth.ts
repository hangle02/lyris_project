// Sign-in gate and per-account browser data (docs/auth.md §7.1). Pure helpers, tested in auth.test.ts;
// the store that calls the API lives in hooks/useAuth.ts.
import type { AccountOut, AuthState } from "../types.ts";
import type { Route } from "./router.ts";

/** Which screen the app shows. "setup" and "forceChange" have no route: the gate shows them over any hash. */
export type Gate = "setup" | "login" | "signup" | "forceChange" | "app";

export function gateOf(state: AuthState, route: Route): Gate {
  if (state.setup_required) return "setup";
  if (!state.account) return route.name === "signup" ? "signup" : "login";
  if (state.account.must_change_password) return "forceChange";
  return "app";
}

/** The routes that only make sense signed out ("#/login", "#/signup"); signed in they go to the hub. */
export function isAuthRoute(route: Route): boolean {
  return route.name === "login" || route.name === "signup";
}

// ---- where to go back after signing in ----

/** sessionStorage: the hash that was open when the app asked to sign in. */
export const NEXT_KEY = "lyris.next";

const NEXT_MAX = 512;
/** A hash of this app only: "#/" then path and query characters (no scheme, no "//", no spaces). */
const SAFE_HASH = /^#\/(?!\/)[A-Za-z0-9\-._~%/?=&@+]*$/;

/**
 * The hash to come back to, or null when there is nothing worth keeping (the hub, the sign-in pages)
 * or it does not look like a hash of this app (it could otherwise point anywhere after "#").
 */
export function safeNext(hash: string | null | undefined): string | null {
  if (typeof hash !== "string") return null;
  const h = hash.trim();
  if (!h || h.length > NEXT_MAX || !SAFE_HASH.test(h)) return null;
  const path = h.slice(1).split("?")[0] ?? "";
  const head = path.split("/").filter(Boolean)[0];
  if (head === undefined || head === "login" || head === "signup") return null;
  return h;
}

/** Storage-like (localStorage, sessionStorage, or a Map-backed fake in tests). */
export interface KeyStore {
  readonly length: number;
  key(index: number): string | null;
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

/**
 * Remembers the open hash before showing the sign-in page. A hash that is not worth it (the hub)
 * drops what an earlier visit left there: after signing in, the person lands where they were asked
 * to sign in, never on an older page.
 */
export function rememberNext(store: KeyStore | null, hash: string): void {
  if (!store) return;
  const next = safeNext(hash);
  try {
    if (next) store.setItem(NEXT_KEY, next);
    else store.removeItem(NEXT_KEY);
  } catch {
    // storage full or blocked: the hub is fine
  }
}

/** The remembered hash (once: it is removed), or null. */
export function takeNext(store: KeyStore | null): string | null {
  if (!store) return null;
  try {
    const raw = store.getItem(NEXT_KEY);
    store.removeItem(NEXT_KEY);
    return safeNext(raw);
  } catch {
    return null;
  }
}

// ---- browser data that belongs to one account ----

/** localStorage: id of the account that last used this browser (to notice a switch). */
export const ACCOUNT_KEY = "lyris.accountId";

/**
 * Keys holding one account's data (§7.1): unsent chat text, the last story, an unsaved character
 * draft or import, the Studio notice, the hash to come back to. They are dropped when someone signs
 * out or another account signs in on this browser.
 *
 * A new key that holds an account's data MUST be added here. Browser preferences stay
 * (lyris.theme, lyris.advanced, lyris.revealThoughts).
 */
export function isAccountDataKey(key: string): boolean {
  return key.startsWith("lyris.draft.") || key === "lyris.lastStoryId" || key.startsWith("lyris.studio.") || key === NEXT_KEY;
}

/** Removes every account-data key from the given stores (missing or blocked stores are skipped). */
export function clearAccountData(...stores: (KeyStore | null)[]): void {
  for (const store of stores) {
    if (!store) continue;
    try {
      const keys: string[] = [];
      for (let i = 0; i < store.length; i++) {
        const k = store.key(i);
        if (k !== null && isAccountDataKey(k)) keys.push(k);
      }
      for (const k of keys) store.removeItem(k);
    } catch {
      // blocked storage: nothing we can clear
    }
  }
}

/**
 * Who is this compared to the account stored for this browser: the same one, the first one seen
 * (nothing stored), or another account (its data must go before anything is shown).
 */
export function accountSwitch(storedId: string | null, accountId: number): "same" | "first" | "changed" {
  if (storedId === null || storedId === "") return "first";
  return storedId === String(accountId) ? "same" : "changed";
}

/**
 * The sign-in state after the person saved their own profile (PUT /api/account, avatar): the gate's
 * copy of the handle, name and picture follows, so forms and confirmations name the new @handle at
 * once. Another account, or nothing changed: the same state object.
 */
export function withAccountProfile(
  state: AuthState,
  account: Pick<AccountOut, "id" | "handle" | "display_name" | "avatar_url" | "profile_completed">,
): AuthState {
  const current = state.account;
  if (!current || current.id !== account.id) return state;
  if (
    current.handle === account.handle &&
    current.display_name === account.display_name &&
    current.avatar_url === account.avatar_url &&
    current.profile_completed === account.profile_completed
  ) {
    return state;
  }
  return {
    ...state,
    account: {
      ...current,
      handle: account.handle,
      display_name: account.display_name,
      avatar_url: account.avatar_url,
      profile_completed: account.profile_completed,
    },
  };
}

// ---- what the API tells the gate ----

/** window event fired by api/client when the server says the sign-in state changed (§7.1). */
export const AUTH_EVENT = "lyris:auth";

/** The /auth/ endpoint that needs a session and is used from a signed-in screen (forced change, account sheet). */
const SESSION_AUTH_PATHS = new Set(["/auth/change-password"]);

/**
 * True when a failed request means the gate must ask /auth/me again: signed out (401), a temporary
 * password to change (403 password_change_required), or the owner has no password yet (409
 * setup_required). The sign-in forms answer their own errors, so their endpoints never signal; a
 * 401 from "Đổi mật khẩu" does (the session was dropped meanwhile: reset or disabled by the owner).
 */
export function signalsAuth(path: string, status: number, code: string | null): boolean {
  const bare = path.split("?")[0] ?? path;
  if (bare.startsWith("/auth/")) return SESSION_AUTH_PATHS.has(bare) && status === 401;
  if (status === 401) return true;
  if (status === 403 && code === "password_change_required") return true;
  return status === 409 && code === "setup_required";
}
