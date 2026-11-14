// Pure copy and state of the heart drawer's "Ký ức" and "Cảnh" sections (phase3.md §8, §10). No React.
import type { MemoryKind, StoryExtras } from "../../types.ts";

/** Small label that tells a memory (something that happened) from a fact (something known). */
export function memoryKindLabel(kind: MemoryKind): string {
  return kind === "fact" ? "Điều đã biết" : "Sự kiện";
}

export const INVITE_LINE = "Lyris chưa đọc hết story này.";

/**
 * What the memory section says about background work (Phase 3b: no job status, no counts):
 * - "reading": the player asked to read the story again and jobs still run; typing dots only;
 * - "invite": nothing runs but some replies were never read; offer to read the story again;
 * - null: nothing to say (also while the turn just played is being remembered: that is quiet).
 */
export type MemoryStatus = { kind: "reading" } | { kind: "invite"; text: string } | null;

export function memoryStatus(
  extras: Pick<StoryExtras, "pending" | "unprocessed_turns">,
  opts: { rebuilding?: boolean } = {},
): MemoryStatus {
  if (extras.pending) return opts.rebuilding ? { kind: "reading" } : null;
  if (Math.floor(extras.unprocessed_turns) > 0) return { kind: "invite", text: INVITE_LINE };
  return null;
}
/** "Quên" confirmation, shown right under the memory it is about (so it does not quote it again). */
export function forgetPrompt(kind: MemoryKind, characterName: string): string {
  const who = characterName.trim() || "Nhân vật";
  return kind === "fact"
    ? `Quên điều này? ${who} sẽ không còn biết nữa.`
    : `Quên sự kiện này? ${who} sẽ không nhắc lại nữa.`;
}

/** Rows of the "Cảnh" section; empty when the story has no place or time yet. */
export function sceneRows(extras: Pick<StoryExtras, "location" | "in_world_time">): { label: string; value: string }[] {
  const rows: { label: string; value: string }[] = [];
  const place = extras.location?.trim();
  const time = extras.in_world_time?.trim();
  if (place) rows.push({ label: "Nơi chốn", value: place });
  if (time) rows.push({ label: "Thời gian", value: time });
  return rows;
}

/**
 * What the drawer can show: "loading" before the first answer, "failed" when the first fetch failed
 * (nothing is known, so no section may claim "no data" or keep a busy skeleton), "ready" once some
 * data arrived (a later failure keeps showing it next to the error).
 */
export type DrawerLoad = "loading" | "failed" | "ready";

export function drawerLoadState(extras: unknown | null, error: string | null): DrawerLoad {
  if (extras !== null) return "ready";
  return error ? "failed" : "loading";
}

/**
 * Where focus goes after the memory at `removedIndex` was forgotten and `remaining` rows are left:
 * the row that took its place (or the new last one), or null when the list is empty (focus the
 * section instead).
 */
export function focusIndexAfterForget(removedIndex: number, remaining: number): number | null {
  if (remaining <= 0) return null;
  return Math.min(Math.max(0, removedIndex), remaining - 1);
}
