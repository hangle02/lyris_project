import { useCallback, useEffect, useRef, useState } from "react";
import { api, errorMessage, errorTechnical, isAbortError } from "../../api/client";
import type { StoryLore } from "../../types";
import { normalizeStoryLore } from "./loreLogic";

export type StoryLoreState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "ready"; lore: StoryLore }
  | { kind: "error"; text: string; technical: string | null; lore: StoryLore | null };

/**
 * Unlocked world entries of a story for the heart drawer (phase4.md §11.1). Fetched when the drawer
 * opens, and again while it is open whenever `signature` changes (a turn unlocked something, a reply
 * was regenerated, a version flipped, turns deleted). A closed drawer keeps the last data and asks
 * nothing. Only the newest answer is used.
 */
export function useStoryLore(storyId: number, open: boolean, signature: string) {
  const [state, setState] = useState<StoryLoreState>({ kind: "idle" });
  const req = useRef(0);
  const ctrl = useRef<AbortController | null>(null);

  const load = useCallback(async () => {
    const id = ++req.current;
    ctrl.current?.abort();
    const c = new AbortController();
    ctrl.current = c;
    // Keep what is on screen while asking again; only the first load shows skeletons.
    setState((cur) => (cur.kind === "ready" || cur.kind === "error" ? cur : { kind: "loading" }));
    try {
      const lore = normalizeStoryLore(await api.getStoryLore(storyId, c.signal));
      if (id === req.current) setState({ kind: "ready", lore });
    } catch (e) {
      if (isAbortError(e) || id !== req.current) return;
      setState((cur) => ({
        kind: "error",
        text: errorMessage(e),
        technical: errorTechnical(e),
        lore: cur.kind === "ready" ? cur.lore : cur.kind === "error" ? cur.lore : null,
      }));
    }
  }, [storyId]);

  // A new story starts empty.
  useEffect(() => {
    setState({ kind: "idle" });
    return () => {
      req.current++;
      ctrl.current?.abort();
    };
  }, [storyId]);

  useEffect(() => {
    if (open) void load();
  }, [open, signature, load]);

  return { state, reload: load };
}
