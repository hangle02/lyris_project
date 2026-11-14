import { useEffect, useSyncExternalStore } from "react";
import { api, errorMessage } from "../api/client";
import type { AccountOut, AccountUpdate } from "../types";
import { needsAccountLoad } from "./accountLogic";
import { syncAuthProfile } from "./useAuth";

/**
 * The current account (docs/accounts.md), shared by the hub header, the "Tài khoản" sheet, the
 * profile page and the hub invite: one module-level store, so a save in one place shows everywhere
 * at once. Loaded on first use; `refresh()` re-reads it (counts change when cards, stories or
 * personas are created elsewhere).
 */
export interface AccountSnapshot {
  /** null until the first load succeeds. */
  account: AccountOut | null;
  /** Error of the last load (the last good account is kept). */
  error: string | null;
  loading: boolean;
}

let snapshot: AccountSnapshot = { account: null, error: null, loading: false };
let inflight: Promise<AccountOut | null> | null = null;
/** Bumped by every write, so a load that started before it cannot overwrite the newer account. */
let version = 0;
const listeners = new Set<() => void>();

function setSnapshot(patch: Partial<AccountSnapshot>): void {
  snapshot = { ...snapshot, ...patch };
  for (const l of listeners) l();
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function getSnapshot(): AccountSnapshot {
  return snapshot;
}

/** The store as it is right now (for effects that must not wait for a re-render). */
export const getAccountSnapshot = getSnapshot;

/** GET /api/account; concurrent calls share one request. Resolves to the account, or null on error. */
export function refreshAccount(): Promise<AccountOut | null> {
  if (inflight) return inflight;
  const started = version;
  setSnapshot({ loading: true });
  inflight = api
    .getAccount()
    .then(
      (account) => {
        if (version === started) setSnapshot({ account, error: null, loading: false });
        else setSnapshot({ loading: false });
        return snapshot.account;
      },
      (e: unknown) => {
        setSnapshot({ error: errorMessage(e), loading: false });
        return null;
      },
    )
    .finally(() => {
      inflight = null;
    });
  return inflight;
}

/** Puts a fresh account from any endpoint that returns one (PUT, avatar, banner) into the store. */
export function setAccount(account: AccountOut): void {
  version += 1;
  setSnapshot({ account, error: null });
  // A new @handle (or name, picture) must reach the sign-in store too: password forms, "Đăng xuất mọi
  // thiết bị" and Khám phá read it from there.
  syncAuthProfile(account);
}

async function write(call: () => Promise<AccountOut>): Promise<AccountOut> {
  // Errors (ApiError with the server's Vietnamese message, e.g. 422 for a taken handle) go to the caller.
  const account = await call();
  setAccount(account);
  return account;
}

export const accountActions = {
  refresh: refreshAccount,
  /** PUT /api/account; marks the profile completed on the server. */
  update: (body: AccountUpdate) => write(() => api.updateAccount(body)),
  uploadAvatar: (file: Blob) => write(() => api.uploadAccountAvatar(file)),
  removeAvatar: () => write(() => api.deleteAccountAvatar()),
  uploadBanner: (file: Blob) => write(() => api.uploadAccountBanner(file)),
  removeBanner: () => write(() => api.deleteAccountBanner()),
};

export type AccountState = AccountSnapshot & typeof accountActions;

/** Current account and the actions that change it. Starts the first load when nothing is loaded yet. */
export function useAccount(): AccountState {
  const snap = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
  useEffect(() => {
    // Also after a failed load: one failed first request must not hide the account all session.
    if (needsAccountLoad(snapshot)) void refreshAccount();
  }, []);
  return { ...snap, ...accountActions };
}
