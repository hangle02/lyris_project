import { useCallback, useEffect, useRef } from "react";
import { isForcedLeave } from "../../lib/leaveGuard";
import { addNavigationGuard, parseRoute, routeHref } from "../../lib/router";

const LEAVE_MESSAGE = "Bạn có thay đổi chưa lưu. Rời trang và bỏ các thay đổi này?";

function currentHref(): string {
  return routeHref(parseRoute(window.location.hash));
}

/** Rewrites the hash without a history entry and without notifying anyone (used to undo a navigation). */
function restoreHash(hash: string): void {
  const url = `${window.location.pathname}${window.location.search}${hash}`;
  window.history.replaceState(window.history.state, "", url);
}

/**
 * Warns before losing unsaved changes: the browser's own prompt on reload/close, and a confirm()
 * on in-app navigation (any hash change away from `ownHref`: a link, the Back button, navigate()).
 * The confirm runs as a router navigation guard, i.e. before any useRoute subscriber re-renders (a
 * plain window listener ran too late on a real link click: the router re-rendered first and the
 * page was gone). Cancelling puts the old hash back and the router is not notified.
 *
 * Returns `allowLeave()` to call right before a navigation that must not ask (after delete), and
 * `moveTo(href)` when the page itself changes its address (first save of a new card).
 */
export function useUnsavedGuard(
  dirty: boolean,
  ownHref: string,
): { allowLeave: () => void; moveTo: (href: string) => void } {
  // ownHref is read once; later moves go through moveTo() (state updates may render after the hash changes).
  const state = useRef({ dirty, ownHref, bypass: false });
  state.current.dirty = dirty;

  useEffect(() => {
    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      const s = state.current;
      // The account changed under this tab (hooks/useAuth reloads it): never offer to stay.
      if (!s.dirty || s.bypass || isForcedLeave()) return;
      e.preventDefault();
      // Older browsers need returnValue set.
      e.returnValue = "";
    };
    /** Router guard: true lets the navigation through, false cancelled it (old hash put back). */
    const onNavigate = (): boolean => {
      const s = state.current;
      if (!s.dirty || s.bypass) return true;
      if (currentHref() === s.ownHref) return true;
      if (window.confirm(LEAVE_MESSAGE)) {
        s.bypass = true;
        return true;
      }
      restoreHash(s.ownHref);
      return false;
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    const removeGuard = addNavigationGuard(onNavigate);
    return () => {
      window.removeEventListener("beforeunload", onBeforeUnload);
      removeGuard();
    };
  }, []);

  const allowLeave = useCallback(() => {
    state.current.bypass = true;
  }, []);
  /** The page now lives at `href` (e.g. "#/studio/new" -> "#/studio/12" after the first save). */
  const moveTo = useCallback((href: string) => {
    state.current.ownHref = href;
    replaceHash(href);
  }, []);
  return { allowLeave, moveTo };
}

/** Replaces the current hash (no history entry) and lets the router know. */
function replaceHash(href: string): void {
  if (window.location.hash === href) return;
  restoreHash(href);
  window.dispatchEvent(new HashChangeEvent("hashchange"));
}
