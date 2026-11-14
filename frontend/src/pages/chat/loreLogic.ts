// "Thế giới đã mở khoá" trong ngăn "Cảm xúc & ký ức" (docs/phase4.md §11). Hàm thuần, có test.
import type { StoryExtras, StoryLore, UnlockedLore } from "../../types.ts";

/** Entries the player reads openly (everyone + "Chỉ bạn biết") and the character's own secrets. */
export interface UnlockedSplit {
  open: UnlockedLore[];
  /** "Điều {tên} giữ trong lòng": always empty when the story does not read thoughts (§11.2). */
  secret: UnlockedLore[];
}

export function splitUnlocked(entries: readonly UnlockedLore[], showThoughts: boolean): UnlockedSplit {
  return {
    open: entries.filter((e) => e.audience === "everyone" || e.audience === "player"),
    secret: showThoughts ? entries.filter((e) => e.audience === "character") : [],
  };
}

/**
 * Reload signature for the open drawer: changes when a turn unlocks something new. `lore_count` also
 * counts the character's secrets, which `lore_tags` leaves out.
 */
export function loreSignature(extras: Pick<StoryExtras, "lore_tags" | "lore_count"> | null): string {
  if (!extras) return "";
  return `${extras.lore_count ?? 0}|${extras.lore_tags.join("|")}`;
}

function nameOr(name: string): string {
  return name.trim() || "Nhân vật";
}

/** One line when there is nothing to list; null when the list has entries to show. */
export function unlockedEmptyLine(lore: Pick<StoryLore, "available">, split: UnlockedSplit, characterName: string): string | null {
  if (!lore.available && split.open.length === 0 && split.secret.length === 0) {
    return `${nameOr(characterName)} chưa có sổ thế giới.`;
  }
  if (split.open.length === 0 && split.secret.length === 0) {
    return `Chưa mở khoá điều gì. Khi story nhắc tới người, nơi chốn hay chuyện cũ trong thế giới của ${nameOr(characterName)}, chúng sẽ hiện ở đây.`;
  }
  return null;
}

/** The Studio editor of the character, scrolled to its "Thế giới" section. */
export function studioWorldHref(cardId: number): string {
  return `#/studio/${cardId}?section=world`;
}

/** Title of the secrets group. */
export function secretGroupTitle(characterName: string): string {
  return `Điều ${nameOr(characterName)} giữ trong lòng`;
}

/** Screen-reader label of a blurred secret card. */
export function secretLabel(characterName: string): string {
  return `Một điều ${nameOr(characterName)} giữ trong lòng, chạm để đọc`;
}

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function int(v: unknown): number | null {
  return typeof v === "number" && Number.isInteger(v) ? v : null;
}

const CATEGORIES = new Set(["lore", "character", "place"]);
const AUDIENCES = new Set(["everyone", "character", "player"]);

/** GET /api/stories/{id}/lore read defensively ("others" or broken rows are dropped). */
export function normalizeStoryLore(raw: unknown): StoryLore {
  if (!isRecord(raw)) return { available: false, can_edit: false, card_id: 0, entries: [] };
  const entries: UnlockedLore[] = [];
  const seen = new Set<number>();
  for (const e of Array.isArray(raw.entries) ? raw.entries : []) {
    if (!isRecord(e)) continue;
    const id = int(e.entry_id);
    const title = typeof e.title === "string" ? e.title.trim() : "";
    if (id === null || !title || seen.has(id)) continue;
    if (!AUDIENCES.has(String(e.audience))) continue;
    seen.add(id);
    entries.push({
      entry_id: id,
      title,
      category: CATEGORIES.has(String(e.category)) ? (e.category as UnlockedLore["category"]) : "lore",
      audience: e.audience as UnlockedLore["audience"],
      content: typeof e.content === "string" ? e.content.trim() : "",
      first_turn: int(e.first_turn) ?? 0,
      last_turn: int(e.last_turn) ?? 0,
      turns: int(e.turns) ?? 0,
    });
  }
  return {
    available: raw.available === true || entries.length > 0,
    can_edit: raw.can_edit === true,
    card_id: int(raw.card_id) ?? 0,
    entries,
  };
}
