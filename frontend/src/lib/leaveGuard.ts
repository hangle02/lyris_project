// One flag shared by the unsaved-changes guards (pages/studio/useUnsavedGuard) and the sign-in store
// (hooks/useAuth). When the account changes under a tab (signed out, or another account signed in in
// another tab), the tab clears its data and reloads; the browser's "Leave site?" prompt must not let
// the person stay on the previous account's page.

let forced = false;

/** The next unload is the app's own reset: guards let it through without asking. */
export function allowForcedLeave(): void {
  forced = true;
}

/** True after allowForcedLeave() (the page is about to reload). */
export function isForcedLeave(): boolean {
  return forced;
}
