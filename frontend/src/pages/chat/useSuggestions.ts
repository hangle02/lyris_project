import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { api, friendlyOf, isAbortError } from "../../api/client";
import type { Mode } from "../../types";
import { INITIAL_SUGGEST, cleanSuggestions, suggestReducer } from "./suggestLogic";

/**
 * Quick replies on demand (Phase 3b): POST /api/stories/{id}/suggestions when the player taps
 * "Nhận gợi ý" or "Gợi ý khác". Closing the area or starting a new turn (`reset`) cancels a request
 * still running; a late answer is ignored. The state is read through suggestLogic.suggestView.
 *
 * `releasing`: a request was just cancelled. The server notices the dropped connection a moment
 * later (it polls every few hundred ms) and holds the story until then, so a send in that moment
 * would get 409; the page keeps sending locked for RELEASE_MS.
 */
export const RELEASE_MS = 800;

export function useSuggestions(storyId: number) {
  const [state, dispatch] = useReducer(suggestReducer, INITIAL_SUGGEST);
  const [releasing, setReleasing] = useState(false);
  const counter = useRef(0);
  const ctrlRef = useRef<AbortController | null>(null);
  const releaseTimer = useRef<number | null>(null);

  const cancel = useCallback(() => {
    const ctrl = ctrlRef.current;
    ctrlRef.current = null;
    if (!ctrl) return;
    ctrl.abort();
    setReleasing(true);
    if (releaseTimer.current !== null) window.clearTimeout(releaseTimer.current);
    releaseTimer.current = window.setTimeout(() => {
      releaseTimer.current = null;
      setReleasing(false);
    }, RELEASE_MS);
  }, []);

  useEffect(() => {
    dispatch({ type: "reset" });
    return cancel;
  }, [storyId, cancel]);

  useEffect(
    () => () => {
      if (releaseTimer.current !== null) window.clearTimeout(releaseTimer.current);
    },
    [],
  );

  const request = useCallback(
    async (mode: Mode, anchor: string | null = null) => {
      cancel();
      const ctrl = new AbortController();
      ctrlRef.current = ctrl;
      const id = ++counter.current;
      dispatch({ type: "request", mode, request: id, anchor });
      try {
        const res = await api.requestSuggestions(storyId, ctrl.signal);
        const items = cleanSuggestions(Array.isArray(res?.items) ? res.items : []);
        if (items.length === 0) {
          dispatch({
            type: "failure",
            request: id,
            error: { text: "Chưa nghĩ ra gợi ý nào. Hãy thử lại.", technical: null },
          });
        } else {
          dispatch({ type: "success", request: id, items });
        }
      } catch (e) {
        if (isAbortError(e) || ctrl.signal.aborted) return;
        dispatch({ type: "failure", request: id, error: friendlyOf(e) });
      } finally {
        if (ctrlRef.current === ctrl) ctrlRef.current = null;
      }
    },
    [storyId, cancel],
  );

  /** Closes the area; `key` names the replies on screen (suggestionsKey), "" when none are. */
  const dismiss = useCallback(
    (key: string) => {
      cancel();
      dispatch({ type: "dismiss", key });
    },
    [cancel],
  );

  /** A new turn starts: whatever was asked for belongs to the previous reply. */
  const reset = useCallback(() => {
    cancel();
    dispatch({ type: "reset" });
  }, [cancel]);

  return { state, releasing, request, dismiss, reset };
}
