import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError, errorMessage, errorTechnical } from "../../api/client";
import type { StoryExtras } from "../../types";
import { normalizeExtras, withoutMemory } from "./chatLogic";
import { ExtrasPoller } from "./extrasPoller";

/**
 * GET /api/stories/{id}/extras (relationship, quick replies, scene, memories, job state).
 * `extras` is null until the first answer; a failed refresh keeps the last good data and sets `error`.
 * While the answer says `pending`, it asks again every 2 seconds (not while the tab is hidden, not
 * while `paused`, never after unmount). The caller refreshes after every turn and message action.
 */
export function useStoryExtras(storyId: number, { paused = false }: { paused?: boolean } = {}) {
  const [extras, setExtras] = useState<StoryExtras | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorTech, setErrorTech] = useState<string | null>(null);
  const pollerRef = useRef<ExtrasPoller<StoryExtras> | null>(null);

  useEffect(() => {
    setExtras(null);
    setError(null);
    const poller = new ExtrasPoller<StoryExtras>({
      load: async () => normalizeExtras(await api.getStoryExtras(storyId)),
      onData: (data) => {
        setExtras(data);
        setError(null);
        setErrorTech(null);
      },
      onError: (e) => {
        setError(errorMessage(e));
        setErrorTech(errorTechnical(e));
      },
      isPending: (data) => data.pending,
      isHidden: () => document.visibilityState === "hidden",
      setTimer: (fn, ms) => window.setTimeout(fn, ms),
      clearTimer: (h) => window.clearTimeout(h as number),
    });
    pollerRef.current = poller;
    const onVisibility = () => poller.visibilityChanged();
    document.addEventListener("visibilitychange", onVisibility);
    void poller.refresh();
    return () => {
      document.removeEventListener("visibilitychange", onVisibility);
      poller.dispose();
      if (pollerRef.current === poller) pollerRef.current = null;
    };
  }, [storyId]);

  useEffect(() => {
    pollerRef.current?.setPaused(paused);
  }, [paused, storyId]);

  const refresh = useCallback(async () => {
    await pollerRef.current?.refresh();
  }, []);

  /** Quick replies belong to the last reply: drop them as soon as a new turn starts. */
  const dropSuggestions = useCallback(() => {
    setExtras((cur) => (cur && cur.suggestions.length > 0 ? { ...cur, suggestions: [] } : cur));
  }, []);

  /**
   * "Quên": deletes on the server, then drops the row locally and refreshes. Not optimistic, so a
   * refusal stays next to the row that caused it (the row shows a spinner meanwhile).
   */
  const forget = useCallback(
    async (memoryId: number) => {
      try {
        await api.forgetMemory(storyId, memoryId);
      } catch (e) {
        // Already gone (another tab, a regenerate): treat as forgotten.
        if (!(e instanceof ApiError && e.status === 404)) throw e;
      }
      setExtras((cur) => (cur ? withoutMemory(cur, memoryId) : cur));
      void pollerRef.current?.refresh();
    },
    [storyId],
  );

  /** "Đọc lại story": queues extraction of the unread turns; polling shows the progress. */
  const rebuild = useCallback(async () => {
    const res = await api.rebuildStoryState(storyId);
    await pollerRef.current?.refresh();
    return res;
  }, [storyId]);

  return { extras, error, errorTechnical: errorTech, refresh, dropSuggestions, forget, rebuild };
}
