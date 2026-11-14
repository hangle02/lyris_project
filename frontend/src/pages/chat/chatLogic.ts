// Pure logic of the chat screen (no React): defensive extras reading, emotion bars, header subtitle.
import type {
  EmotionKey,
  MemoryItem,
  Message,
  Mode,
  Moment,
  PersonaOut,
  RelationshipState,
  StoryExtras,
  StoryOut,
} from "../../types.ts";

/** Most quick replies shown above the composer (phase3.md §8). */
export const MAX_SUGGESTIONS = 3;
/** Most memories the drawer lists (the API sends at most 50). */
export const MAX_MEMORIES = 50;

export interface EmotionRow {
  key: EmotionKey;
  label: string;
}

/** DESIGN.md §3.3, in the drawer's order. Colours: var(--color-emo-<key>). */
export const EMOTIONS: readonly EmotionRow[] = [
  { key: "affection", label: "Thương mến" },
  { key: "trust", label: "Tin cậy" },
  { key: "attraction", label: "Rung động" },
  { key: "obsession", label: "Nhung nhớ / Chiếm hữu" },
  { key: "fear", label: "Lo sợ mất mát" },
  { key: "aversion", label: "Khoảng cách" },
];

export const EMPTY_EXTRAS: StoryExtras = {
  relationship: null,
  suggestions: [],
  moment: null,
  lore_tags: [],
  lore_available: false,
  lore_count: 0,
  location: null,
  in_world_time: null,
  memories: [],
  pending: false,
  unprocessed_turns: 0,
  memory_search: "keyword",
  summary: null,
};

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function text(v: unknown): string | null {
  if (typeof v !== "string") return null;
  const t = v.replace(/\s+/g, " ").trim();
  return t ? t : null;
}

function texts(v: unknown, max: number): string[] {
  if (!Array.isArray(v)) return [];
  const seen = new Set<string>();
  const out: string[] = [];
  for (const item of v) {
    const t = text(item);
    if (t && !seen.has(t)) {
      seen.add(t);
      out.push(t);
    }
    if (out.length >= max) break;
  }
  return out;
}

/** 0-100, rounded; anything that is not a finite number reads as 0. */
export function clampScore(v: unknown): number {
  const n = typeof v === "number" ? v : typeof v === "string" ? Number(v) : NaN;
  if (!Number.isFinite(n)) return 0;
  return Math.round(Math.min(100, Math.max(0, n)));
}

function relationship(v: unknown): RelationshipState | null {
  if (!isRecord(v)) return null;
  const r: RelationshipState = {
    affection: clampScore(v.affection),
    trust: clampScore(v.trust),
    attraction: clampScore(v.attraction),
    obsession: clampScore(v.obsession),
    fear: clampScore(v.fear),
    aversion: clampScore(v.aversion),
    directive: text(v.directive),
  };
  return r;
}

function moment(v: unknown): Moment | null {
  if (!isRecord(v)) return null;
  const t = text(v.text);
  if (!t) return null;
  return { text: t, effect: text(v.effect) };
}

function int(v: unknown): number | null {
  return typeof v === "number" && Number.isInteger(v) ? v : null;
}

function memoryItem(v: unknown): MemoryItem | null {
  if (!isRecord(v)) return null;
  const id = int(v.id);
  const t = text(v.text);
  const kind = v.kind === "fact" ? "fact" : v.kind === "memory" ? "memory" : null;
  // Without an id the item cannot be forgotten; without text there is nothing to show.
  if (id === null || !t || !kind) return null;
  const importance = int(v.importance);
  return {
    id,
    story_id: int(v.story_id) ?? 0,
    message_id: int(v.message_id) ?? 0,
    turn_index: int(v.turn_index) ?? 0,
    kind,
    text: t,
    subject: text(v.subject),
    importance: importance === null ? 3 : Math.min(5, Math.max(1, importance)),
    created_at: typeof v.created_at === "string" ? v.created_at : null,
  };
}

function memories(v: unknown): MemoryItem[] {
  if (!Array.isArray(v)) return [];
  const seen = new Set<number>();
  const out: MemoryItem[] = [];
  for (const raw of v) {
    const m = memoryItem(raw);
    if (m && m.id !== null && !seen.has(m.id)) {
      seen.add(m.id);
      out.push(m);
    }
    if (out.length >= MAX_MEMORIES) break;
  }
  return out;
}

/**
 * GET /api/stories/{id}/extras read defensively: older servers miss the Phase 3 fields and any
 * field may be of the wrong type. Strings are trimmed, lists de-duplicated and capped.
 */
export function normalizeExtras(raw: unknown): StoryExtras {
  if (!isRecord(raw)) return EMPTY_EXTRAS;
  const unprocessed = int(raw.unprocessed_turns);
  return {
    relationship: relationship(raw.relationship),
    suggestions: texts(raw.suggestions, MAX_SUGGESTIONS),
    moment: moment(raw.moment),
    lore_tags: texts(raw.lore_tags, 50),
    // Phase 4: older servers send neither (no world book: nothing unlocked).
    lore_available: raw.lore_available === true,
    lore_count: Math.max(0, int(raw.lore_count) ?? 0),
    location: text(raw.location),
    in_world_time: text(raw.in_world_time),
    memories: memories(raw.memories),
    pending: raw.pending === true,
    unprocessed_turns: unprocessed !== null && unprocessed > 0 ? unprocessed : 0,
    memory_search: raw.memory_search === "hybrid" ? "hybrid" : "keyword",
    summary: text(raw.summary),
  };
}

/** The extras without one memory (optimistic "Quên"). */
export function withoutMemory(extras: StoryExtras, memoryId: number): StoryExtras {
  const next = extras.memories.filter((m) => m.id !== memoryId);
  return next.length === extras.memories.length ? extras : { ...extras, memories: next };
}

/** In-world place and time, "Gác xép · Chiều tối"; "" when the story has neither. */
export function sceneLine(extras: Pick<StoryExtras, "location" | "in_world_time">): string {
  return [extras.location, extras.in_world_time].filter((s): s is string => !!s && !!s.trim()).map((s) => s.trim()).join(" · ");
}

/** Header subtitle: in-world place and time when the story tracks them, else the story title. */
export function headerSubtitle(
  story: Pick<StoryOut, "title"> & { card_role?: string | null },
  extras: StoryExtras,
): { role: string | null; detail: string } {
  const scene = sceneLine(extras);
  const role = (story.card_role ?? "").trim() || null;
  const detail = scene || story.title.trim();
  // A story often carries the role as its title: never say it twice.
  if (role && detail.toLocaleLowerCase("vi-VN") === role.toLocaleLowerCase("vi-VN")) return { role, detail: "" };
  return { role, detail };
}

/** The subtitle as one line of text (tooltip, screen readers). */
export function headerSubtitleText(sub: { role: string | null; detail: string }): string {
  return [sub.role, sub.detail].filter(Boolean).join(" · ");
}

/** The moment banner's effect, e.g. "+Thương mến"; nothing when the effect is empty. */
export function momentLine(m: Moment): { text: string; effect: string | null } {
  return { text: m.text, effect: m.effect && m.effect.trim() ? m.effect.trim() : null };
}

/** Who the player is in a story, for the small avatar beside their own DM bubbles. */
export interface PlayerFace {
  name: string;
  url: string | null;
}

/**
 * The story's persona from GET /api/personas: its name and avatar. Until the list arrives (or when
 * the persona is missing), the name from the story row and no picture (initial letter).
 */
export function personaFace(
  personas: readonly PersonaOut[] | null,
  personaId: number,
  fallbackName: string,
): PlayerFace {
  const p = personas?.find((x) => x.id === personaId) ?? null;
  const name = (p?.name ?? fallbackName).trim() || "Bạn";
  return { name, url: p?.avatar_url ?? null };
}

/** Mode of the newest character reply (the one quick replies belong to); null when there is none. */
export function lastReplyMode(messages: readonly Pick<Message, "role" | "mode" | "is_active">[]): Mode | null {
  for (let i = messages.length - 1; i >= 0; i--) {
    const m = messages[i];
    if (m && m.role === "assistant" && m.is_active) return m.mode;
  }
  return null;
}

// ---- story settings patched from the header (optimistic, several requests may overlap) ----

/**
 * The server's copy of the story after one PATCH, merged into what is on screen. `keep` = keys another
 * PATCH is still saving: the screen already shows their new value, while this response may still carry the
 * old one (the server handled this request first).
 */
export function mergeStory<T extends object>(cur: T, updated: Partial<T>, keep: Iterable<string>): T {
  const out = { ...cur, ...updated } as T;
  for (const key of keep) {
    if (key in cur) (out as Record<string, unknown>)[key] = (cur as Record<string, unknown>)[key];
  }
  return out;
}

/**
 * A refused PATCH: put back only its own keys, and only those still showing the value it set. A setting
 * changed (and saved) meanwhile by another request stays as it is.
 */
export function rollbackPatch<T extends object>(cur: T, before: T, patch: Partial<T>): T {
  const out = { ...cur } as Record<string, unknown>;
  for (const [key, value] of Object.entries(patch)) {
    if (Object.is(out[key], value)) out[key] = (before as Record<string, unknown>)[key];
  }
  return out as T;
}

/**
 * Phase 4b (docs/auth.md §5.5): the line under the typing dots while every generation slot of the
 * machine is busy (SSE `waiting`). Never says model, slot or Ollama.
 */
export function waitingLine(characterName: string): string {
  const name = characterName.trim() || "Nhân vật";
  return `Có người khác đang trò chuyện. ${name} sẽ trả lời ngay sau.`;
}
