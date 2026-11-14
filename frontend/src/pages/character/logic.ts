// Pure helpers of the character profile ("#/character/..."), tested in logic.test.ts. No React, no DOM.
import type { CharacterCard, EmotionKey, LoreSummary, PublicCardView, StoryOut, StyleProfileInfo, TemplateInfo } from "../../types.ts";
import {
  EMOTION_KEYS,
  EMOTION_LABEL,
  GENDER_LABEL,
  readInitialRelationship,
  readNarrationOverride,
  suggestNarration,
} from "../../lib/cardForm.ts";
import { fillForReader, normalizeTag, vibeLabel } from "../explore/logic.ts";

type Lang = "vi" | "en";

const LANGUAGE_NAME: Record<Lang, string> = { vi: "Tiếng Việt", en: "Tiếng Anh" };

function langOf(card: Pick<CharacterCard, "language">): Lang {
  return card.language === "en" ? "en" : "vi";
}

/**
 * Card text for whoever reads the profile: {{char}} is the name, {{user}} is "bạn" / "you"; split
 * into paragraphs (blank lines or single line breaks), each with single spaces.
 */
export function readerParagraphs(text: string, name: string, language: Lang): string[] {
  return fillForReader(text ?? "", name, language)
    .split(/\n+/)
    .map((p) => p.replace(/[ \t]+/g, " ").trim())
    .filter(Boolean);
}

export interface IntroSection {
  key: "description" | "personality" | "appearance" | "background" | "goals" | "scenario";
  title: string;
  paragraphs: string[];
}

const INTRO: readonly { key: IntroSection["key"]; title: string }[] = [
  { key: "description", title: "Đôi nét" },
  { key: "personality", title: "Tính cách" },
  { key: "appearance", title: "Ngoại hình" },
  { key: "background", title: "Hoàn cảnh" },
  { key: "goals", title: "Điều mong muốn" },
  { key: "scenario", title: "Bối cảnh" },
];

/**
 * The "Giới thiệu" tab: description, personality, appearance, background, goals and the default
 * scenario ("Bối cảnh"), written for the reader; empty fields are left out. Secrets are never
 * included: they are what the story uncovers.
 */
export function introSections(card: CharacterCard): IntroSection[] {
  const name = card.name.trim();
  const lang = langOf(card);
  return INTRO.map(({ key, title }) => ({ key, title, paragraphs: readerParagraphs(card[key], name, lang) })).filter(
    (s) => s.paragraphs.length > 0,
  );
}

export interface SettingRow {
  label: string;
  value: string;
}

export interface SettingGroup {
  title: string;
  rows: SettingRow[];
}

/**
 * The "Thiết lập" tab, read only: how the character addresses people (self term, what they call
 * the player, nicknames, with others), then style, language, gender and narration pronoun. Empty
 * address fields are left out; a group with nothing in it is dropped.
 */
export function settingGroups(card: CharacterCard, profile: StyleProfileInfo | null): SettingGroup[] {
  const name = card.name.trim();
  const lang = langOf(card);
  const t = card.address_terms;
  const address: SettingRow[] = [];
  const self = t.self_term.trim();
  const player = t.player_term.trim();
  const nicknames = t.nicknames.map((n) => n.trim()).filter(Boolean);
  const others = readerParagraphs(t.others, name, lang).join(" ");
  if (self) address.push({ label: "Tự xưng", value: self });
  if (player) address.push({ label: "Gọi bạn là", value: player });
  if (nicknames.length) address.push({ label: "Tên gọi thân mật", value: nicknames.join(", ") });
  if (others) address.push({ label: "Với người khác", value: others });

  const own = lang === "vi" ? readNarrationOverride(card).trim() : "";
  const narration = own || suggestNarration(profile, card.language, card.gender, name);
  const voice: SettingRow[] = [
    // Only the style's title: its file id (snake_case) is technical, so "Chưa rõ" until /styles answers.
    { label: "Văn phong", value: profile?.title.trim() || "Chưa rõ" },
    { label: "Ngôn ngữ", value: LANGUAGE_NAME[card.language] ?? card.language },
    { label: "Giới tính", value: GENDER_LABEL[card.gender] ?? card.gender },
    { label: "Dẫn truyện gọi nhân vật là", value: narration || name },
  ];
  const speech = readerParagraphs(card.speech_style, name, lang).join(" ");
  if (speech) voice.push({ label: "Cách nói", value: speech });

  return [
    { title: "Xưng hô", rows: address },
    { title: "Giọng kể", rows: voice },
  ].filter((g) => g.rows.length > 0);
}

/** The starting emotions when the card sets them (extensions.lyris.initial_relationship), else null. */
export function startingEmotions(card: Pick<CharacterCard, "extensions">): { key: EmotionKey; label: string; value: number }[] | null {
  const { values, stored } = readInitialRelationship(card);
  if (!stored) return null;
  return EMOTION_KEYS.map((key) => ({ key, label: EMOTION_LABEL[key], value: values[key] }));
}

/** Tags of the card plus the template's vibes, as chip labels: no repeats, sentence case. */
export function profileTags(tags: readonly string[], vibes: readonly string[] = []): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const t of [...vibes, ...tags]) {
    const key = normalizeTag(t);
    if (!key || seen.has(key)) continue;
    seen.add(key);
    out.push(vibeLabel(t));
  }
  return out;
}

function time(iso: string | null | undefined): number {
  if (!iso) return 0;
  const t = Date.parse(iso.endsWith("Z") || /[+-]\d\d:?\d\d$/.test(iso) ? iso : `${iso}Z`);
  return Number.isNaN(t) ? 0 : t;
}

/** The user's stories with this card, newest activity first (then newest created, then highest id). */
export function storiesWith(stories: readonly StoryOut[], cardId: number | null): StoryOut[] {
  if (cardId === null) return [];
  return stories
    .filter((s) => s.card_id === cardId && s.id !== null)
    .sort(
      (a, b) =>
        time(b.updated_at ?? b.created_at) - time(a.updated_at ?? a.created_at) ||
        time(b.created_at) - time(a.created_at) ||
        (b.id ?? 0) - (a.id ?? 0),
    );
}

/** The template a card was installed from (GET /api/templates `installed_card_id`), if any. */
export function templateOfCard(templates: readonly TemplateInfo[] | null, cardId: number): TemplateInfo | null {
  return templates?.find((t) => t.installed_card_id === cardId) ?? null;
}

/** "Bước vào câu chuyện" copy and limits shared by the page and the sheet. */
export const ENTER_LABEL = "Bước vào câu chuyện";

// ---- Phase 4: "Thế giới" teaser on the "Giới thiệu" tab (phase4.md §10) ----

export interface WorldTeaser {
  /** "27 điều về thế giới của Lục Bắc Uyên." */
  line: string;
  groups: { title: string; names: string[]; more: number }[];
}

function count(v: unknown): number {
  return typeof v === "number" && Number.isFinite(v) && v > 0 ? Math.floor(v) : 0;
}

function nameList(v: unknown): string[] {
  if (!Array.isArray(v)) return [];
  return v.filter((x): x is string => typeof x === "string" && x.trim() !== "").map((x) => x.trim()).slice(0, 8);
}

/**
 * Names only (people and places everyone knows, at most 8 each, then "+N"); never an entry's content,
 * never the title of a story or secret entry. null hides the section (no entries, or no summary).
 */
export function worldTeaser(summary: Partial<LoreSummary> | null | undefined, characterName: string): WorldTeaser | null {
  if (!summary || typeof summary !== "object") return null;
  const total = count(summary.total);
  if (total === 0) return null;
  const name = characterName.trim() || "nhân vật";
  const groups = [
    { title: `Người quanh ${name}`, names: nameList(summary.people), more: count(summary.people_more) },
    { title: "Nơi chốn", names: nameList(summary.places), more: count(summary.places_more) },
  ].filter((g) => g.names.length > 0);
  return { line: `${total} điều về thế giới của ${name}.`, groups };
}

// ---- Phase 4b: someone else's public character (docs/auth.md §4.4, §7.3) ----

/**
 * A PublicCardView as a CharacterCard for the read-only profile and the start sheet. What other
 * accounts never receive (personality, background, goals, secrets, example dialogues, creator notes)
 * stays empty, so those sections simply do not show.
 */
export function cardFromPublic(view: PublicCardView): CharacterCard {
  return {
    id: view.id,
    uid: view.uid ?? null,
    visibility: view.visibility,
    name: view.name,
    role: view.role ?? "",
    gender: view.gender,
    language: view.language,
    description: view.description ?? "",
    personality: "",
    appearance: view.appearance ?? "",
    background: "",
    goals: "",
    secrets: "",
    speech_style: view.speech_style ?? "",
    style_profile: view.style_profile,
    address_terms: {
      self_term: view.address_terms?.self_term ?? "",
      player_term: view.address_terms?.player_term ?? "",
      nicknames: [...(view.address_terms?.nicknames ?? [])],
      others: view.address_terms?.others ?? "",
    },
    greeting: view.greeting ?? "",
    example_dialogues: "",
    tags: [...(view.tags ?? [])],
    scenario: view.scenario ?? "",
    alternate_greetings: [...(view.alternate_greetings ?? [])],
    creator_notes: "",
    avatar: null,
    extensions: view.extensions ?? {},
  };
}

/** The 13px line of the start sheet for someone else's character: the story keeps today's version. */
export function sharedStartNote(name: string, handle: string | null): string {
  const n = name.trim() || "nhân vật này";
  const who = handle ? `@${handle.replace(/^@+/, "")}` : "Người tạo";
  return `Bạn chơi với ${n} như bây giờ. ${who} sửa nhân vật sau này thì story của bạn không đổi.`;
}
