// The "Sự kiện" sheet (Phase 3b, phase3.md §10): the story timeline from GET /timeline (memory,
// facts, emotion changes and scene per turn) read defensively, and its wording. Pure, no React;
// tested in eventsLogic.test.ts.
import type { EmotionKey, Mode, TimelineEntry } from "../../types.ts";

/** DESIGN.md §3.3 order; short labels for chips (the drawer uses the long ones). */
export const EMOTION_ORDER: readonly EmotionKey[] = ["affection", "trust", "attraction", "obsession", "fear", "aversion"];

export const EMOTION_SHORT: Record<EmotionKey, string> = {
  affection: "Thương mến",
  trust: "Tin cậy",
  attraction: "Rung động",
  obsession: "Nhung nhớ",
  fear: "Lo sợ",
  aversion: "Khoảng cách",
};

/** Most entries kept (a long story still opens fast). */
export const MAX_TIMELINE = 300;

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function text(v: unknown): string | null {
  if (typeof v !== "string") return null;
  const t = v.replace(/\s+/g, " ").trim();
  return t || null;
}

function int(v: unknown): number | null {
  return typeof v === "number" && Number.isInteger(v) ? v : null;
}

function delta(v: unknown): Partial<Record<EmotionKey, number>> {
  if (!isRecord(v)) return {};
  const out: Partial<Record<EmotionKey, number>> = {};
  for (const k of EMOTION_ORDER) {
    const n = v[k];
    if (typeof n === "number" && Number.isFinite(n) && Math.round(n) !== 0) out[k] = Math.round(n);
  }
  return out;
}

function entry(v: unknown): TimelineEntry | null {
  if (!isRecord(v)) return null;
  const turn = int(v.turn_index);
  if (turn === null || turn < 0) return null;
  const scene = isRecord(v.scene) ? { location: text(v.scene.location), time: text(v.scene.time) } : null;
  return {
    turn_index: turn,
    message_id: int(v.message_id) ?? 0,
    mode: v.mode === "dm" ? "dm" : "story",
    created_at: typeof v.created_at === "string" ? v.created_at : null,
    memory: text(v.memory),
    facts: Array.isArray(v.facts) ? v.facts.map(text).filter((s): s is string => s !== null) : [],
    delta: delta(v.delta),
    scene: scene && (scene.location || scene.time) ? scene : null,
  };
}

/**
 * GET /api/stories/{id}/timeline read defensively: bad rows dropped, one entry per turn (the last
 * wins), turns in story order, at most MAX_TIMELINE (the newest).
 */
export function normalizeTimeline(raw: unknown): TimelineEntry[] {
  if (!Array.isArray(raw)) return [];
  const byTurn = new Map<number, TimelineEntry>();
  for (const r of raw) {
    const e = entry(r);
    if (e) byTurn.set(e.turn_index, e);
  }
  return [...byTurn.values()].sort((a, b) => a.turn_index - b.turn_index).slice(-MAX_TIMELINE);
}

export interface DeltaChip {
  key: EmotionKey;
  /** "+2 Thương mến", "−3 Tin cậy" (a real minus sign). */
  text: string;
  /** For screen readers: "Thương mến tăng 2". */
  label: string;
}

/** Emotion changes as chips, in DESIGN.md order. */
export function deltaChips(d: Partial<Record<EmotionKey, number>>): DeltaChip[] {
  const out: DeltaChip[] = [];
  for (const key of EMOTION_ORDER) {
    const n = d[key];
    if (typeof n !== "number" || n === 0) continue;
    const name = EMOTION_SHORT[key];
    out.push({
      key,
      text: `${n > 0 ? "+" : "−"}${Math.abs(n)} ${name}`,
      label: `${name} ${n > 0 ? "tăng" : "giảm"} ${Math.abs(n)}`,
    });
  }
  return out;
}

/** "Gác xép · Chiều tối"; "" without a scene. */
export function sceneText(scene: TimelineEntry["scene"]): string {
  if (!scene) return "";
  return [scene.location, scene.time].filter((s): s is string => !!s).join(" · ");
}

/** True when the turn left something to show (memory, fact, emotion change or scene). */
export function hasEvents(e: TimelineEntry): boolean {
  return !!e.memory || e.facts.length > 0 || Object.keys(e.delta).length > 0 || !!e.scene;
}

/** Entries to list: turns with something to show, newest first. */
export function timelineItems(entries: readonly TimelineEntry[]): TimelineEntry[] {
  return entries.filter(hasEvents).reverse();
}

/** Mode label of an entry, as on the hub badges. */
export function modeLabel(mode: Mode): string {
  return mode === "dm" ? "DM" : "Story";
}

function parseIso(iso: string): Date | null {
  // The backend writes UTC; old SQLite values may lack the zone.
  const d = new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : `${iso.replace(" ", "T")}Z`);
  return Number.isNaN(d.getTime()) ? null : d;
}

/** "23:15" today, "Hôm qua 23:15", else "12/11 23:15"; "" when unknown. */
export function entryTime(iso: string | null, now: Date = new Date()): string {
  if (!iso) return "";
  const d = parseIso(iso);
  if (!d) return "";
  const hm = `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  if (d.getTime() >= startOfToday) return hm;
  if (d.getTime() >= startOfToday - 86_400_000) return `Hôm qua ${hm}`;
  return `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")} ${hm}`;
}

/** DOM id of a rendered turn (Story and DM views); the timeline jumps to it. */
export function turnDomId(turnIndex: number): string {
  return `turn-${turnIndex}`;
}

/**
 * What a tap on a timeline entry does: scroll in this view, switch to the other mode first, or
 * (when the switch is locked because something runs) only explain, with no jump left pending that
 * would take over the scroll later.
 */
export type JumpPlan = { kind: "scroll" } | { kind: "switch"; mode: Mode } | { kind: "blocked"; notice: string };

export function jumpPlan(entryMode: Mode, view: Mode, switchLocked: boolean): JumpPlan {
  if (entryMode === view) return { kind: "scroll" };
  if (switchLocked) {
    const other = entryMode === "dm" ? "DM" : "Story";
    return { kind: "blocked", notice: `Lượt này nằm bên ${other}. Đợi xong việc đang làm rồi mở lại nhé.` };
  }
  return { kind: "switch", mode: entryMode };
}
