// Pure helpers of the Khám phá page (tested in logic.test.ts). No React, no DOM.
import type { CardSummary, PublicCardSummary, TemplateInfo, Visibility } from "../../types.ts";
import { characterRoute, templateRoute } from "../../lib/router.ts";
import type { Route } from "../../lib/router.ts";

// ---- creator attribution (docs/accounts.md §5) ----

/** Credit line of the templates that ship with Lyris (installed or not). */
export const TEMPLATE_CREDIT = "Mẫu của Lyris";
/** Quiet label of a card nobody else can see (visibility "private", the default). */
export const PRIVATE_LABEL = "Riêng tư";

/** "bởi @handle"; null when the backend did not send a handle. */
export function byHandle(handle: string | null | undefined): string | null {
  const h = (handle ?? "").trim().replace(/^@+/, "");
  return h ? `bởi @${h}` : null;
}

/**
 * Credit line under a character: "Mẫu của Lyris" for a template (also once installed as a card),
 * else "bởi @handle" of the account that made it, else null.
 */
export function creatorLine(opts: { template: boolean; handle: string | null | undefined }): string | null {
  return opts.template ? TEMPLATE_CREDIT : byHandle(opts.handle);
}

/** True when a card was installed from a template (`extensions.lyris.template`, set by the backend). */
export function isTemplateCard(extensions: Record<string, unknown> | null | undefined): boolean {
  const lyris = extensions?.lyris;
  if (!lyris || typeof lyris !== "object") return false;
  const slug = (lyris as Record<string, unknown>).template;
  return typeof slug === "string" && slug.trim().length > 0;
}

/** Card ids installed from a template (GET /api/templates `installed_card_id`). */
export function installedTemplateIds(templates: readonly TemplateInfo[]): Set<number> {
  const ids = new Set<number>();
  for (const t of templates) if (t.installed_card_id !== null) ids.add(t.installed_card_id);
  return ids;
}

/**
 * Whether a card is credited "Mẫu của Lyris". One rule for every screen (Studio list, Khám phá,
 * Profile, the editor): the card is a template's installed card per GET /api/templates
 * `installed_card_id` (the backend also adopts legacy seed cards by name there). Only when the
 * templates could not be loaded (`installedIds` null) does the `extensions.lyris.template` tag decide.
 */
export function isInstalledTemplate(
  cardId: number | null,
  extensions: Record<string, unknown> | null | undefined,
  installedIds: ReadonlySet<number> | null,
): boolean {
  if (installedIds === null) return isTemplateCard(extensions);
  return cardId !== null && installedIds.has(cardId);
}

/** Missing visibility counts as private (the default of every card). */
export function isPrivate(visibility: Visibility | null | undefined): boolean {
  return (visibility ?? "private") === "private";
}

/**
 * "Riêng tư" next to a character's credit: only for the account's own private cards. A template
 * (installed or not) ships with Lyris for everyone, so it never says "Riêng tư".
 */
export function privateLabelFor(opts: { template: boolean; visibility: Visibility | null | undefined }): string | null {
  return !opts.template && isPrivate(opts.visibility) ? PRIVATE_LABEL : null;
}

/** The whole credit line: "bởi @ban · Riêng tư", "Mẫu của Lyris", or "" when there is nothing to say. */
export function creditLine(opts: {
  template: boolean;
  handle: string | null | undefined;
  visibility: Visibility | null | undefined;
}): string {
  return [creatorLine(opts), privateLabelFor(opts)].filter(Boolean).join(" · ");
}

/** Credit of a template's open-licence picture (extra field of GET /api/templates, read defensively). */
export interface ImageCredit {
  title: string;
  creator: string;
  licence: string;
  licence_url: string | null;
  source_url: string;
  changes: string | null;
}

/** The four vibes DESIGN.md names, in sentence case and without the ✨ (docs/design-impl.md §10). */
export const BASE_VIBES: readonly string[] = ["Chữa lành", "Dịu dàng", "Bí ẩn nội tâm", "Tình đầu"];

/** Most chips shown in the vibe row (base vibes and template vibes first, then shared card tags). */
export const MAX_VIBES = 10;

/**
 * Comparable form of a tag or vibe: no emoji or symbols (the ✨ of DESIGN.md), NFC, lowercase,
 * single spaces. Diacritics are kept ("tình đầu" and "tinh dau" are different words in Vietnamese).
 */
export function normalizeTag(tag: string): string {
  return tag
    .normalize("NFC")
    .replace(/[\p{Extended_Pictographic}\p{So}️‍]/gu, " ")
    .toLocaleLowerCase("vi-VN")
    .replace(/\s+/g, " ")
    .trim();
}

/** Place names that keep their capitals inside a sentence-case tag ("việt nam hiện đại" -> "Việt Nam hiện đại"). */
const PROPER_NAMES: readonly string[] = [
  "việt nam",
  "trung quốc",
  "hàn quốc",
  "nhật bản",
  "sài gòn",
  "hà nội",
  "đà lạt",
  "hội an",
  "huế",
  "cornwall",
];

function titleCase(words: string): string {
  return words
    .split(" ")
    .map((w) => {
      const first = Array.from(w)[0] ?? "";
      return first.toLocaleUpperCase("vi-VN") + w.slice(first.length);
    })
    .join(" ");
}

/** Label of a vibe chip: the normalized tag in sentence case ("chữa lành" -> "Chữa lành"), place names capitalised. */
export function vibeLabel(tag: string): string {
  let n = normalizeTag(tag);
  for (const name of PROPER_NAMES) {
    n = n.replace(new RegExp(`(^|\\s)${name}(?=\\s|$)`, "gu"), (_m, lead: string) => lead + titleCase(name));
  }
  const first = Array.from(n)[0];
  return first ? first.toLocaleUpperCase("vi-VN") + n.slice(first.length) : "";
}

function str(v: unknown): string {
  return typeof v === "string" ? v : "";
}

function strOrNull(v: unknown): string | null {
  return typeof v === "string" && v.trim() ? v : null;
}

/** `image_url` of a template, when the backend sends one. */
export function templateImageUrl(t: TemplateInfo): string | null {
  return strOrNull((t as unknown as Record<string, unknown>).image_url);
}

/** `image_credit` of a template, when the backend sends a complete one. */
export function templateImageCredit(t: TemplateInfo): ImageCredit | null {
  const raw = (t as unknown as Record<string, unknown>).image_credit;
  if (!raw || typeof raw !== "object") return null;
  const r = raw as Record<string, unknown>;
  const title = str(r.title).trim();
  const source = str(r.source_url).trim();
  if (!title || !source) return null;
  return {
    title,
    creator: str(r.creator).trim(),
    licence: str(r.licence).trim(),
    licence_url: strOrNull(r.licence_url),
    source_url: source,
    changes: strOrNull(r.changes),
  };
}

/** `role` of a card list row (an extra field of GET /api/cards, read defensively). */
export function cardRole(c: CardSummary): string {
  return str((c as unknown as Record<string, unknown>).role).trim();
}

/** One portrait in the explore grid: a card of the user, or a template not installed yet ("Mẫu"). */
export interface ExploreItem {
  key: string;
  /** "shared": another account's public character (Phase 4b), opened read only. */
  kind: "card" | "template" | "shared";
  /** Saved card (the user's, or a template's installed card); null for a template not installed yet. */
  cardId: number | null;
  slug: string | null;
  name: string;
  role: string;
  /** Picture for the 4:3 frame: the card avatar, or the template's scene picture. */
  imageUrl: string | null;
  /** Normalized tags and vibes, for the vibe filter. */
  tags: string[];
  /** "bởi @handle", "Mẫu của Lyris", or null (see creatorLine). */
  creator: string | null;
  /** One short line about the character for the compact card (may be ""). */
  teaser: string;
  /** F47: the whole description, addressed to the reader (what "Tìm nhân vật" searches besides name, role and tags). */
  about: string;
}

/** Max characters of a grid card's teaser (two lines on a phone card). */
export const TEASER_CHARS = 90;

/** The card's whole description addressed to the reader ("" when there is none): searched by "Tìm nhân vật". */
export function aboutOf(description: string | null | undefined, name: string, language: string): string {
  return fillForReader((description ?? "").trim(), name, language === "en" ? "en" : "vi");
}

/** The card's own description, addressed to the reader and cut short; "" when there is none. */
export function teaserOf(description: string | null | undefined, name: string, language: string): string {
  const text = fillForReader((description ?? "").trim(), name, language === "en" ? "en" : "vi");
  return text ? shortText(text, TEASER_CHARS) : "";
}

function uniq(list: string[]): string[] {
  return [...new Set(list.filter(Boolean))];
}

/**
 * The grid: the user's cards (in API order), then templates that are not installed. A card installed
 * from a template also answers to that template's vibes.
 */
export function buildItems(cards: CardSummary[], templates: TemplateInfo[]): ExploreItem[] {
  const vibesByCard = new Map<number, string[]>();
  for (const t of templates) {
    if (t.installed_card_id !== null) {
      vibesByCard.set(t.installed_card_id, [...(vibesByCard.get(t.installed_card_id) ?? []), ...t.vibes]);
    }
  }
  const cardIds = new Set(cards.map((c) => c.id));
  const fromTemplate = installedTemplateIds(templates);
  const items: ExploreItem[] = cards.map((c) => ({
    key: `card-${c.id}`,
    kind: "card",
    cardId: c.id,
    slug: null,
    name: c.name,
    role: cardRole(c),
    imageUrl: c.avatar_url,
    tags: uniq([...c.tags, ...(vibesByCard.get(c.id) ?? [])].map(normalizeTag)),
    creator: creatorLine({ template: fromTemplate.has(c.id), handle: c.creator_handle }),
    teaser: teaserOf(c.description, c.name, c.language),
    about: aboutOf(c.description, c.name, c.language),
  }));
  for (const t of templates) {
    if (t.installed_card_id !== null && cardIds.has(t.installed_card_id)) continue;
    items.push({
      key: `template-${t.slug}`,
      kind: "template",
      cardId: t.installed_card_id,
      slug: t.slug,
      name: t.card.name,
      role: (t.card.role ?? "").trim(),
      imageUrl: templateImageUrl(t),
      tags: uniq([...t.vibes, ...t.card.tags].map(normalizeTag)),
      creator: TEMPLATE_CREDIT,
      teaser: teaserOf(t.card.description, t.card.name, t.card.language),
      about: aboutOf(t.card.description, t.card.name, t.card.language),
    });
  }
  return items;
}

/**
 * Chips of the vibe row, as normalized tags: the four base vibes, then template vibes, then tags
 * shared by at least two items, most shared first; at most `max`.
 */
export function buildVibes(items: ExploreItem[], templates: TemplateInfo[], max = MAX_VIBES): string[] {
  const out: string[] = [];
  const add = (t: string) => {
    const n = normalizeTag(t);
    if (n && !out.includes(n) && out.length < max) out.push(n);
  };
  BASE_VIBES.forEach(add);
  templates.forEach((t) => t.vibes.forEach(add));
  const counts = new Map<string, number>();
  for (const it of items) for (const tag of it.tags) counts.set(tag, (counts.get(tag) ?? 0) + 1);
  [...counts.entries()]
    .filter(([, n]) => n >= 2)
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], "vi"))
    .forEach(([tag]) => add(tag));
  return out;
}

/** Items carrying the vibe (normalized compare); all items when `vibe` is null. */
export function filterByVibe(items: ExploreItem[], vibe: string | null): ExploreItem[] {
  if (vibe === null) return items;
  const v = normalizeTag(vibe);
  return items.filter((it) => it.tags.includes(v));
}

/**
 * Card text addressed to whoever reads the explore page: `{{char}}` becomes the character's name and
 * `{{user}}` becomes "bạn" / "you", capitalised at the start of a sentence.
 */
export function fillForReader(text: string, charName: string, language: "vi" | "en"): string {
  const you = language === "en" ? "you" : "bạn";
  const cap = language === "en" ? "You" : "Bạn";
  return text
    .replace(/\{\{\s*char\s*\}\}/gi, charName)
    .replace(/(^|[.!?…]["”»)]?\s+|\n\s*)\{\{\s*user\s*\}\}/gi, (_m, lead: string) => `${lead}${cap}`)
    .replace(/\{\{\s*user\s*\}\}/gi, you);
}

/** First paragraph of a description, cut at a word boundary to about `max` characters. */
export function shortText(text: string, max = 180): string {
  const first = (text.split(/\n\s*\n/)[0] ?? "").replace(/\s+/g, " ").trim();
  if (first.length <= max) return first;
  const cut = first.slice(0, max);
  const at = cut.lastIndexOf(" ");
  return `${(at > max * 0.6 ? cut.slice(0, at) : cut).replace(/[\s,.;:–-]+$/u, "")}…`;
}

// ---- where a tap goes (the character's profile, docs/design-impl.md §16) ----

/** Profile route of a grid item: the saved card, else the template by slug; null when it has neither. */
export function itemRoute(item: Pick<ExploreItem, "cardId" | "slug">, start = false): Route | null {
  if (item.cardId !== null) return characterRoute(item.cardId, start);
  if (item.slug) return templateRoute(item.slug, start);
  return null;
}

/** Profile route of a template: its installed card when there is one. */
export function templateEntryRoute(t: Pick<TemplateInfo, "slug" | "installed_card_id">, start = false): Route {
  return t.installed_card_id !== null ? characterRoute(t.installed_card_id, start) : templateRoute(t.slug, start);
}

// ---- Phase 4b: other accounts' public characters (docs/auth.md §7.3) ----

/**
 * The one Khám phá grid (PO 2026-11-15, wiki/decisions/kham-pha-mot-luoi.md): your cards and templates not
 * installed (`buildItems`), then other accounts' public characters. No separate section: each card's credit
 * line ("Mẫu của Lyris", "bởi @handle") already says who made it. Each character once.
 */
export function exploreGrid(items: ExploreItem[], shared: ExploreItem[]): ExploreItem[] {
  const seen = new Set(items.map((i) => i.key));
  const out = [...items];
  for (const s of shared) {
    if (seen.has(s.key)) continue;
    seen.add(s.key);
    out.push(s);
  }
  return out;
}

/**
 * Other accounts' public characters, at the end of the Khám phá grid: never your own (also when an older
 * server sent them), newest change first, each credited "bởi @handle".
 */
export function sharedItems(cards: readonly PublicCardSummary[], ownHandle: string | null): ExploreItem[] {
  const own = (ownHandle ?? "").trim().replace(/^@+/, "").toLowerCase();
  return cards
    .filter((c) => !own || c.creator_handle.toLowerCase() !== own)
    .slice()
    .sort((a, b) => (b.updated_at ?? "").localeCompare(a.updated_at ?? "") || b.id - a.id)
    .map((c) => ({
      key: `shared-${c.id}`,
      kind: "shared" as const,
      cardId: c.id,
      slug: null,
      name: c.name,
      role: (c.role ?? "").trim(),
      imageUrl: c.avatar_url,
      tags: uniq(c.tags.map(normalizeTag)),
      creator: byHandle(c.creator_handle),
      teaser: teaserOf(c.description, c.name, c.language),
      about: aboutOf(c.description, c.name, c.language),
    }));
}
