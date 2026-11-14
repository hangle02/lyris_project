// Pure helpers of the Tương tác hub (tested in logic.test.ts). No React, no DOM.
import type { EmotionKey, RelationshipState, StoryOut } from "../../types.ts";

/**
 * Time-aware greeting (DESIGN.md §6, page 1), without the emoji of the original examples
 * (docs/design-impl.md §10). `hour` is the local hour 0-23.
 */
export function greetingFor(hour: number): string {
  const h = ((Math.floor(hour) % 24) + 24) % 24;
  if (h >= 5 && h < 11) return "Nắng lên rồi, hôm nay trò chuyện cùng ai?";
  if (h >= 11 && h < 14) return "Trưa rồi, nghỉ tay trò chuyện một chút nhé?";
  if (h >= 14 && h < 18) return "Chiều dịu dàng, ai đang chờ bạn ghé thăm?";
  if (h >= 18 && h < 22) return "Tối rồi, kể nhau nghe chuyện hôm nay?";
  return "Đêm muộn rồi, ai đang thức đợi bạn?";
}

const pad2 = (n: number) => String(n).padStart(2, "0"); // taste-skill-ignore: clock and date digits

function startOfDay(d: Date): number {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
}

/** ISO timestamp from the API ("…Z", or a naive UTC "YYYY-MM-DD HH:MM:SS") to epoch ms; NaN if unusable. */
export function parseApiTime(iso: string | null | undefined): number {
  if (!iso) return NaN;
  let s = iso.trim();
  if (/^\d{4}-\d{2}-\d{2} \d/.test(s)) s = s.replace(" ", "T");
  if (/T\d{2}:\d{2}(:\d{2}(\.\d+)?)?$/.test(s)) s += "Z";
  return Date.parse(s);
}

/**
 * Last activity of a story row: "23:15" today, "Hôm qua" yesterday, "12/11" earlier this year,
 * "12/11/2025" before that. Calendar days in local time. "" when the time is unknown.
 */
export function formatStoryTime(iso: string | null | undefined, now: Date = new Date()): string {
  const t = parseApiTime(iso);
  if (Number.isNaN(t)) return "";
  const d = new Date(t);
  const today = startOfDay(now);
  const day = startOfDay(d);
  if (day >= today) return `${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
  // DST-safe "yesterday": the start of the previous calendar day.
  const yesterday = startOfDay(new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1));
  if (day >= yesterday) return "Hôm qua";
  const dm = `${pad2(d.getDate())}/${pad2(d.getMonth() + 1)}`;
  return d.getFullYear() === now.getFullYear() ? dm : `${dm}/${d.getFullYear()}`;
}

/** Lowercase, no Vietnamese diacritics (đ -> d), single spaces: "Hạ  Vy" -> "ha vy". */
export function foldText(s: string): string {
  return s
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[đĐ]/g, "d")
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim();
}

/** Fields of a story row the hub search looks at. */
export interface StorySearchFields {
  card_name: string;
  title: string;
  card_role?: string | null;
  persona_name?: string | null;
  /** In-world location from the story extras, when a later phase fills it. */
  location?: string | null;
}

/**
 * Hub search: every word of the query must appear in the character name, story title, role,
 * persona or location, ignoring case and diacritics ("ha vy" finds "Hạ Vy"). Empty query matches all.
 */
export function matchesStory(story: StorySearchFields, query: string): boolean {
  const words = foldText(query).split(" ").filter(Boolean);
  if (words.length === 0) return true;
  const hay = foldText(
    [story.card_name, story.title, story.card_role ?? "", story.persona_name ?? "", story.location ?? ""].join(" "),
  );
  return words.every((w) => hay.includes(w));
}

export const EMOTION_KEYS: readonly EmotionKey[] = ["affection", "trust", "attraction", "obsession", "fear", "aversion"];

/** Vietnamese names of the six emotions (DESIGN.md §3.3). */
export const EMOTION_LABELS: Record<EmotionKey, string> = {
  affection: "Thương mến",
  trust: "Tin cậy",
  attraction: "Rung động",
  obsession: "Nhung nhớ",
  fear: "Lo sợ mất mát",
  aversion: "Khoảng cách",
};

/** The strongest of the six emotions (first in DESIGN.md order on a tie), or null when all are 0 or unknown. */
export function dominantEmotion(
  rel: RelationshipState | null | undefined,
): { key: EmotionKey; label: string; value: number } | null {
  if (!rel) return null;
  let best: { key: EmotionKey; value: number } | null = null;
  for (const key of EMOTION_KEYS) {
    const raw = rel[key];
    const value = typeof raw === "number" && Number.isFinite(raw) ? Math.round(Math.min(100, Math.max(0, raw))) : 0;
    if (value > 0 && (best === null || value > best.value)) best = { key, value };
  }
  return best ? { ...best, label: EMOTION_LABELS[best.key] } : null;
}

/** The italic preview line of a story row: the newest message, prefixed "Bạn: " when the player wrote it. */
export function previewOf(story: Pick<StoryOut, "last_preview" | "last_role">): string | null {
  const text = (story.last_preview ?? "").replace(/\s+/g, " ").trim();
  if (!text) return null;
  return story.last_role === "user" ? `Bạn: ${text}` : text;
}

/** Newest activity first; stories without a time keep their API order at the end. */
export function sortByActivity<T extends { updated_at: string | null; created_at: string | null }>(list: T[]): T[] {
  return list
    .map((s, i) => ({ s, i, t: parseApiTime(s.updated_at ?? s.created_at) }))
    .sort((a, b) => {
      const at = Number.isNaN(a.t) ? -Infinity : a.t;
      const bt = Number.isNaN(b.t) ? -Infinity : b.t;
      return bt - at || a.i - b.i;
    })
    .map((x) => x.s);
}

/**
 * Micro-chips of a story row (DESIGN.md page 1): the dominant emotion ("Thương mến 91%") and the
 * current place, from StoryOut.dominant_emotion / location (Phase 3). Each is null when the story
 * has no real data yet, or when an older server does not send the field.
 */
export function storyChips(story: Pick<StoryOut, "dominant_emotion" | "location">): {
  emotion: { key: EmotionKey; label: string; value: number; text: string } | null;
  location: string | null;
} {
  const d = story.dominant_emotion;
  let emotion: { key: EmotionKey; label: string; value: number; text: string } | null = null;
  if (d && typeof d === "object" && (EMOTION_KEYS as readonly string[]).includes(d.key)) {
    const raw = typeof d.value === "number" && Number.isFinite(d.value) ? d.value : NaN;
    if (!Number.isNaN(raw)) {
      const value = Math.round(Math.min(100, Math.max(0, raw)));
      const label = EMOTION_LABELS[d.key];
      emotion = { key: d.key, label, value, text: `${label} ${value}%` };
    }
  }
  const loc = typeof story.location === "string" ? story.location.replace(/\s+/g, " ").trim() : "";
  return { emotion, location: loc || null };
}
