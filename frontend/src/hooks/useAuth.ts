import { useSyncExternalStore } from "react";
import { api, errorMessage } from "../api/client";
import { ACCOUNT_KEY, AUTH_EVENT, accountSwitch, clearAccountData, takeNext, withAccountProfile } from "../lib/auth";
import { allowForcedLeave } from "../lib/leaveGuard";
import type { KeyStore } from "../lib/auth";
import { replaceRoute } from "../lib/router";
import type { AccountOut, AuthAccount, AuthState } from "../types";

/**
 * Who is signed in (docs/auth.md §7.1): one module-level store read by the gate in App, the sign-in
 * pages, the "Tài khoản" sheet and every owner-only control. Loaded once at start (GET /api/auth/me);
 * asked again whenever api/client reports a 401, a forced password change or setup (event
 * `lyris:auth`).
 */
export interface AuthSnapshot {
  status: "loading" | "ready" | "error";
  state: AuthState | null;
  /** Plain sentence when /auth/me could not be read (the server is not running). */
  error: string | null;
  /** The server signed this browser out while the app was open: the login page says so. */
  loggedOut: boolean;
}

let snapshot: AuthSnapshot = { status: "loading", state: null, error: null, loggedOut: false };
let inflight: Promise<void> | null = null;
let started = false;
const listeners = new Set<() => void>();

function set(patch: Partial<AuthSnapshot>): void {
  snapshot = { ...snapshot, ...patch };
  for (const l of listeners) l();
}

function subscribe(l: () => void): () => void {
  listeners.add(l);
  return () => {
    listeners.delete(l);
  };
}

function getSnapshot(): AuthSnapshot {
  return snapshot;
}

function local(): KeyStore | null {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

function session(): KeyStore | null {
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

/**
 * Drops this browser's data of the previous account and reloads at `hash` (no React state, module
 * cache or history entry of the other person survives; Back then asks the server again and gets 401).
 */
function resetBrowser(hash: string, forgetAccount: boolean): void {
  // Unsaved-changes guards must not offer "Stay": the cookie already belongs to someone else (or no one).
  allowForcedLeave();
  clearAccountData(local(), session());
  if (forgetAccount) {
    try {
      window.localStorage.removeItem(ACCOUNT_KEY);
    } catch {
      // nothing stored
    }
  }
  window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}${hash}`);
  window.location.reload();
}

/**
 * Takes a new sign-in state (from /auth/me or a sign-in form). Another account than the one this
 * browser last saw: clear its data and reload on the hub. Otherwise, with `next`, go there first
 * (the page that was open before signing in), then show the app. Returns false when reloading.
 */
export function applyAuth(state: AuthState, opts: { next?: string | null; navigate?: boolean } = {}): boolean {
  const account = state.account;
  if (account) {
    let stored: string | null = null;
    try {
      stored = window.localStorage.getItem(ACCOUNT_KEY);
    } catch {
      stored = null;
    }
    const kind = accountSwitch(stored, account.id);
    if (kind === "changed") {
      try {
        window.localStorage.setItem(ACCOUNT_KEY, String(account.id));
      } catch {
        // blocked storage: the reload still clears what it can
      }
      set({ status: "loading" });
      resetBrowser("#/", false);
      return false;
    }
    if (kind === "first") {
      try {
        window.localStorage.setItem(ACCOUNT_KEY, String(account.id));
      } catch {
        // private mode: nothing to remember
      }
    }
    if (opts.navigate) replaceRoute(opts.next ?? "#/");
  }
  set({ status: "ready", state, error: null, loggedOut: account ? false : snapshot.loggedOut });
  return true;
}

/** GET /api/auth/me; concurrent calls share one request. */
export function refreshAuth(): Promise<void> {
  if (inflight) return inflight;
  inflight = api
    .authMe()
    .then(
      (state) => {
        applyAuth(state);
      },
      (e: unknown) => {
        // Keep a known state (a passing network hiccup); only the first load shows the error screen.
        set(snapshot.state ? { error: errorMessage(e) } : { status: "error", error: errorMessage(e) });
      },
    )
    .finally(() => {
      inflight = null;
    });
  return inflight;
}

function onAuthEvent(e: Event): void {
  const status = (e as CustomEvent<{ status?: number }>).detail?.status;
  // A 401 while signed in: the login page opens with "Bạn đã bị đăng xuất".
  if (status === 401 && snapshot.state?.account) set({ loggedOut: true });
  void refreshAuth();
}

/** Starts the store once (first render of the gate). */
export function startAuth(): void {
  if (started) return;
  started = true;
  window.addEventListener(AUTH_EVENT, onAuthEvent);
  // Another tab signed out or signed in as someone else: the cookie is shared, so this tab must not
  // keep showing the old account (its unsent drafts in sessionStorage included).
  window.addEventListener("storage", (e) => {
    if (e.key !== ACCOUNT_KEY && e.key !== null) return;
    const shown = snapshot.state?.account?.id ?? null;
    if (shown === null || e.newValue === String(shown)) return;
    resetBrowser("#/", false);
  });
  void refreshAuth();
}

/**
 * "Đăng xuất" / "Đăng xuất mọi thiết bị": tells the server, then clears this browser's data of the
 * account and reloads on the login page. A server that already forgot the sign-in (401) is fine.
 */
export async function signOut(everywhere = false): Promise<void> {
  try {
    await (everywhere ? api.logoutAll() : api.logout());
  } catch (e) {
    const status = (e as { status?: number }).status;
    if (status !== 401) throw e;
  }
  set({ status: "loading" });
  resetBrowser("#/login", true);
}

/**
 * The account was deleted (DELETE /api/account): this browser forgets it and reloads, on the login
 * page, or on the first-run setup when the owner deleted the last account (the gate shows it on "#/").
 */
export function accountDeleted(setupRequired: boolean): void {
  set({ status: "loading" });
  resetBrowser(setupRequired ? "#/" : "#/login", true);
}

/** After a successful password change (new sign-in for this device). */
export function passwordChanged(state: AuthState): void {
  applyAuth(state);
}

/** The person saved their own profile: the gate's handle, name and picture follow (no reload needed). */
export function syncAuthProfile(account: AccountOut): void {
  const state = snapshot.state;
  if (!state) return;
  const next = withAccountProfile(state, account);
  if (next !== state) set({ state: next });
}

/** The hash to return to after signing in (sessionStorage "lyris.next"), read once. */
export function takeNextHash(): string | null {
  return takeNext(session());
}

export function useAuth(): AuthSnapshot {
  return useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
}

/** The signed-in account (null while loading or signed out). */
export function useAuthAccount(): AuthAccount | null {
  return useAuth().state?.account ?? null;
}

/** True only for the owner of the machine (models, machine info, "Quản lý tài khoản"). */
export function useIsOwner(): boolean {
  return useAuthAccount()?.role === "owner";
}

/** Snapshot outside React (effects that must not wait for a render). */
export const getAuthSnapshot = getSnapshot;
