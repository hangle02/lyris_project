// Hands an unsaved card (AI draft or import) from the Studio list to the editor ("#/studio/new"),
// plus a one-shot notice for the next Studio screen. Kept in memory and mirrored in sessionStorage
// so a reload of "#/studio/new" does not lose a draft that took a minute to write.

import type { CharacterCard } from "../types.ts";

export interface PendingDraft {
  source: "draft" | "import";
  card: CharacterCard;
  warnings: string[];
  /** Import from PNG: image held by the server, attached on save. */
  avatar_token: string | null;
  /** Import: the file name, for the notice at the top of the editor. */
  file_name?: string | null;
}

const DRAFT_KEY = "lyris.studio.pendingDraft";
const NOTICE_KEY = "lyris.studio.notice";

let memoryDraft: PendingDraft | null = null;
let memoryNotice: StoredNotice | null = null;

function storage(): Storage | null {
  try {
    return typeof window !== "undefined" && window.sessionStorage ? window.sessionStorage : null;
  } catch {
    return null;
  }
}

function isDraft(v: unknown): v is PendingDraft {
  if (!v || typeof v !== "object") return false;
  const d = v as Record<string, unknown>;
  const card = d.card as Record<string, unknown> | undefined;
  return (
    (d.source === "draft" || d.source === "import") &&
    !!card &&
    typeof card === "object" &&
    typeof card.name === "string" &&
    Array.isArray(d.warnings) &&
    (d.avatar_token === null || typeof d.avatar_token === "string")
  );
}

export function setPendingDraft(d: PendingDraft): void {
  memoryDraft = d;
  try {
    storage()?.setItem(DRAFT_KEY, JSON.stringify(d));
  } catch {
    // quota or privacy mode: memory copy is enough within this tab
  }
}

/** The pending draft without consuming it (safe to call during render). */
export function peekPendingDraft(): PendingDraft | null {
  if (memoryDraft) return memoryDraft;
  try {
    const raw = storage()?.getItem(DRAFT_KEY);
    if (!raw) return null;
    const parsed: unknown = JSON.parse(raw);
    if (isDraft(parsed)) {
      memoryDraft = parsed;
      return parsed;
    }
  } catch {
    // corrupted: ignore
  }
  return null;
}

export function clearPendingDraft(): void {
  memoryDraft = null;
  try {
    storage()?.removeItem(DRAFT_KEY);
  } catch {
    // ignore
  }
}

interface StoredNotice {
  text: string;
  /** Route href of the screen that should show it ("#/studio", "#/studio/12"). */
  target: string;
}

function isNotice(v: unknown): v is StoredNotice {
  return !!v && typeof v === "object" && typeof (v as StoredNotice).text === "string" && typeof (v as StoredNotice).target === "string";
}

/** A short message for the next screen at `target` (e.g. "Đã xoá ..." for "#/studio"). */
export function setNotice(text: string, target: string): void {
  memoryNotice = { text, target };
  try {
    storage()?.setItem(NOTICE_KEY, JSON.stringify(memoryNotice));
  } catch {
    // ignore
  }
}

/** The notice meant for `target`, without consuming it (safe during render). */
export function peekNotice(target: string): string | null {
  let n = memoryNotice;
  if (!n) {
    try {
      const raw = storage()?.getItem(NOTICE_KEY);
      const parsed: unknown = raw ? JSON.parse(raw) : null;
      n = isNotice(parsed) ? parsed : null;
    } catch {
      n = null;
    }
  }
  return n && n.target === target ? n.text : null;
}

/** Drops the notice once a screen has shown it (or it is stale). */
export function clearNotice(): void {
  memoryNotice = null;
  try {
    storage()?.removeItem(NOTICE_KEY);
  } catch {
    // ignore
  }
}
