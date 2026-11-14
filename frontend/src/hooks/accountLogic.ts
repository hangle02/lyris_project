// Pure rules of the shared account store (useAccount.ts); tested in accountLogic.test.ts. No React.

/** The parts of the account store the load rules look at. */
export interface AccountLoadState {
  account: unknown;
  error: string | null;
  loading: boolean;
}

/**
 * Whether a newly mounted account user (hub header, invite, profile) should start a load: whenever
 * nothing is loaded and no load is running, also after a failed load. Otherwise one failed first
 * request (backend still starting, a restart) would leave the "?" avatar and no invite for the whole
 * session. Concurrent mounts share one request (refreshAccount dedupes).
 */
export function needsAccountLoad(s: AccountLoadState): boolean {
  return s.account === null && !s.loading;
}

/**
 * Whether a health change should reload the account: the backend just answered well ("ok" or "warn",
 * after a different level such as "checking" or "down") and no account is loaded yet. `previous` is
 * null on the first health render (the mount load covers that one).
 */
export function reloadAccountOnRecovery(previous: string | null, level: string, s: AccountLoadState): boolean {
  if (previous === null || previous === level) return false;
  return (level === "ok" || level === "warn") && needsAccountLoad(s);
}
