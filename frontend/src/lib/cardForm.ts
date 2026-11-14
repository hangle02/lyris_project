// Pure logic of the Character Studio form (no React, no DOM): defaults, validation,
// normalization and the default "test" settings for prompt preview / test chat.
// Limits mirror backend/lyris/api/routes_studio.py validate_card().

import type {
  AddressTerms,
  CardOut,
  CharacterCard,
  EmotionKey,
  Gender,
  Language,
  Persona,
  RelationshipType,
  StorySettings,
  StyleProfileInfo,
} from "../types.ts";
import { signatureProblems, withCleanSignatureLines } from "./signatureLines.ts";

export const MAX_NAME_CHARS = 80;
/** Role line under the name ("Chủ tiệm sách mùa thu"); same limit as the backend. */
export const MAX_ROLE_CHARS = 80;
export const MAX_TEXT_CHARS = 20_000;
export const MAX_TAGS = 20;
export const MAX_TAG_CHARS = 60;
export const MAX_TERM_CHARS = 200;
export const MAX_ALT_GREETINGS = 50;
/** Block B (character + persona + style) above this many tokens deserves a warning. */
export const TOKEN_B_WARN = 1200;
/** Default style profile for a new card when nothing else is known. */
export const DEFAULT_STYLE = "chung";

export const GENDER_LABEL: Record<Gender, string> = { male: "Nam", female: "Nữ", other: "Khác" };
export const LANGUAGE_LABEL: Record<Language, string> = { vi: "Tiếng Việt", en: "English" };

/** Text fields of a card, with the Vietnamese label used in messages. */
export const CARD_TEXT_FIELDS = {
  description: "mô tả",
  personality: "tính cách",
  appearance: "ngoại hình",
  background: "hoàn cảnh",
  goals: "mục tiêu",
  secrets: "bí mật",
  speech_style: "cách nói",
  greeting: "lời mở đầu",
  example_dialogues: "ví dụ thoại",
  scenario: "bối cảnh",
  creator_notes: "ghi chú của người tạo",
} as const satisfies Partial<Record<keyof CharacterCard, string>>;

export type CardTextField = keyof typeof CARD_TEXT_FIELDS;

export function emptyCard(styleProfile: string = DEFAULT_STYLE): CharacterCard {
  return {
    id: null,
    name: "",
    role: "",
    gender: "male",
    language: "vi",
    description: "",
    personality: "",
    appearance: "",
    background: "",
    goals: "",
    secrets: "",
    speech_style: "",
    style_profile: styleProfile,
    address_terms: { self_term: "", player_term: "", nicknames: [], others: "" },
    greeting: "",
    example_dialogues: "",
    tags: [],
    scenario: "",
    alternate_greetings: [],
    creator_notes: "",
    avatar: null,
    extensions: {},
  };
}

function deepCopy<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

/** Only the CharacterCard fields of a CardOut (or any superset), deep-copied; missing fields get defaults. */
export function toCard(src: CharacterCard | CardOut): CharacterCard {
  const base = emptyCard(src.style_profile || DEFAULT_STYLE);
  const terms: Partial<AddressTerms> = src.address_terms ?? {};
  return {
    id: src.id ?? null,
    name: src.name ?? "",
    role: src.role ?? "",
    gender: src.gender ?? base.gender,
    language: src.language ?? base.language,
    description: src.description ?? "",
    personality: src.personality ?? "",
    appearance: src.appearance ?? "",
    background: src.background ?? "",
    goals: src.goals ?? "",
    secrets: src.secrets ?? "",
    speech_style: src.speech_style ?? "",
    style_profile: src.style_profile || base.style_profile,
    address_terms: {
      self_term: terms.self_term ?? "",
      player_term: terms.player_term ?? "",
      nicknames: [...(terms.nicknames ?? [])],
      others: terms.others ?? "",
    },
    greeting: src.greeting ?? "",
    example_dialogues: src.example_dialogues ?? "",
    tags: [...(src.tags ?? [])],
    scenario: src.scenario ?? "",
    alternate_greetings: [...(src.alternate_greetings ?? [])],
    creator_notes: src.creator_notes ?? "",
    avatar: src.avatar ?? null,
    extensions: deepCopy(src.extensions ?? {}),
    // Backend-managed (Phase 2c): sent back unchanged so a save never resets the card's visibility.
    ...(src.uid != null ? { uid: src.uid } : {}),
    ...(src.visibility ? { visibility: src.visibility } : {}),
  };
}

// ---- normalization ----

const TERM_CUT = /\/|,|;|\(|\s+hoặc\s+|\s+or\s+/i;
const STRIP_CHARS = " \t\n\"'“”‘’«».,:;!?-–—[]";

function stripChars(text: string): string {
  let start = 0;
  let end = text.length;
  while (start < end && STRIP_CHARS.includes(text[start] as string)) start++;
  while (end > start && STRIP_CHARS.includes(text[end - 1] as string)) end--;
  return text.slice(start, end);
}

function isTitleCase(text: string): boolean {
  const words = text.split(/\s+/).filter(Boolean);
  return words.length > 1 && words.every((w) => {
    const first = Array.from(w)[0] ?? "";
    return first !== first.toLocaleLowerCase("vi-VN");
  });
}

/**
 * An address term as the prompt wants it (same as the AI-draft post-processing):
 * the first option only (cut at "/", ",", ";", "(", " hoặc ", " or "), quotes stripped,
 * first letter lower-cased (the whole phrase if every word is capitalized, e.g. "Sư Tỷ"),
 * English "I" kept.
 */
export function normalizeTerm(raw: string, language: Language): string {
  const first = raw.trim().split(TERM_CUT)[0] ?? "";
  const text = stripChars(first.trim()).split(/\s+/).filter(Boolean).join(" ");
  if (!text) return "";
  if (language === "en" && (text === "I" || text.startsWith("I "))) return text;
  if (isTitleCase(text)) return text.toLocaleLowerCase("vi-VN");
  const chars = Array.from(text);
  return (chars[0] as string).toLocaleLowerCase("vi-VN") + chars.slice(1).join("");
}

/** Trims items, drops empty ones and case-insensitive duplicates (first spelling wins). */
export function cleanList(items: readonly string[]): string[] {
  const out: string[] = [];
  const seen = new Set<string>();
  for (const item of items) {
    const t = item.replace(/\s+/g, " ").trim();
    if (!t) continue;
    const key = t.toLocaleLowerCase("vi-VN");
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(t);
  }
  return out;
}

/** "a, b , c" -> ["a", "b", "c"] (cleaned). Used by chip inputs when pasting a list. */
export function splitList(text: string): string[] {
  return cleanList(text.split(/[,;\n]/));
}

/** What gets sent on save: trimmed name, cleaned tags/nicknames/terms, blank alternate greetings dropped. */
export function prepareForSave(card: CharacterCard): CharacterCard {
  const c = toCard(card);
  c.name = c.name.replace(/\s+/g, " ").trim();
  c.role = c.role.replace(/\s+/g, " ").trim();
  c.tags = cleanList(c.tags);
  c.address_terms = {
    self_term: c.address_terms.self_term.trim(),
    player_term: c.address_terms.player_term.trim(),
    nicknames: cleanList(c.address_terms.nicknames),
    others: c.address_terms.others.trim(),
  };
  c.alternate_greetings = c.alternate_greetings.filter((g) => g.trim().length > 0);
  // The starting emotions are always stored explicitly (defaults if the user never moved a slider).
  return withCleanSignatureLines(withInitialRelationship(c, readInitialRelationship(c).values));
}

// ---- validation ----

/** Blocking problems (Vietnamese), same limits as the backend. Empty array = OK to save. */
export function validateCard(card: CharacterCard, styleNames?: readonly string[]): string[] {
  const errors: string[] = [];
  const name = card.name.trim();
  if (!name) errors.push("Tên nhân vật không được để trống.");
  else if (Array.from(name).length > MAX_NAME_CHARS) errors.push(`Tên nhân vật dài quá ${MAX_NAME_CHARS} ký tự.`);
  if (card.role.replace(/\s+/g, " ").trim().length > MAX_ROLE_CHARS) {
    errors.push(`Vai trò dài quá ${MAX_ROLE_CHARS} ký tự.`);
  }

  if (!card.style_profile.trim()) errors.push("Hãy chọn một style profile.");
  else if (styleNames && styleNames.length > 0 && !styleNames.includes(card.style_profile)) {
    errors.push(`Bộ văn phong "${card.style_profile}" không có; hãy chọn lại.`);
  }

  for (const [field, label] of Object.entries(CARD_TEXT_FIELDS) as [CardTextField, string][]) {
    if (card[field].length > MAX_TEXT_CHARS) errors.push(`Phần ${label} dài quá 20.000 ký tự.`);
  }

  const alts = card.alternate_greetings.filter((g) => g.trim());
  if (alts.length > MAX_ALT_GREETINGS) errors.push(`Tối đa ${MAX_ALT_GREETINGS} lời mở đầu khác.`);
  card.alternate_greetings.forEach((g, i) => {
    if (g.length > MAX_TEXT_CHARS) errors.push(`Lời mở đầu khác số ${i + 1} dài quá 20.000 ký tự.`);
  });

  const tags = cleanList(card.tags);
  if (tags.length > MAX_TAGS) errors.push(`Tối đa ${MAX_TAGS} tag.`);
  const longTag = tags.find((t) => t.length > MAX_TAG_CHARS);
  if (longTag) errors.push(`Tag "${longTag.slice(0, 20)}…" dài quá ${MAX_TAG_CHARS} ký tự.`);

  const t = card.address_terms;
  if (t.self_term.length > MAX_TERM_CHARS) errors.push(`Xưng hô (tự xưng) dài quá ${MAX_TERM_CHARS} ký tự.`);
  if (t.player_term.length > MAX_TERM_CHARS) errors.push(`Xưng hô (gọi người chơi) dài quá ${MAX_TERM_CHARS} ký tự.`);
  if (t.nicknames.some((n) => n.trim().length > MAX_TERM_CHARS)) {
    errors.push(`Tên gọi thân mật dài quá ${MAX_TERM_CHARS} ký tự.`);
  }
  if (t.others.length > MAX_TEXT_CHARS) errors.push("Xưng hô với người khác dài quá 20.000 ký tự.");
  errors.push(...signatureProblems(card));
  return errors;
}

/**
 * What blocks "Lưu" in the editor: the card as it will be saved (prepareForSave), plus the signature
 * lines AS TYPED. prepareForSave keeps at most 3 signature lines, so validating only the prepared card
 * let a 4th typed line be dropped silently instead of being reported.
 */
export function saveProblems(card: CharacterCard, styleNames?: readonly string[]): string[] {
  const errors = validateCard(prepareForSave(card), styleNames);
  for (const p of signatureProblems(card)) if (!errors.includes(p)) errors.push(p);
  return errors;
}

// ---- soft hints (do not block saving) ----

export type HintField = "address" | "greeting";

export interface CardHint {
  field: HintField;
  text: string;
}

const THOUGHT_OPEN = /\[[ \t]*thought[ \t]*:/i;
const THOUGHT_BLOCK = /\[[ \t]*thought[ \t]*:[^\]]*(\]|$)/gi;
const QUOTED = /"[^"\n]*"|“[^”\n]*”|«[^»\n]*»|「[^」\n]*」/g;

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** Narration text only: dialogue in quotes and [Thought: ...] removed. */
export function narrationOnly(text: string): string {
  return text.replace(THOUGHT_BLOCK, " ").replace(QUOTED, " ");
}

/** True when `term` appears as a whole word (Unicode-aware, case-insensitive) in `text`. */
export function containsWord(text: string, term: string): boolean {
  const t = term.trim();
  if (!t) return false;
  const re = new RegExp(`(?<![\\p{L}\\p{N}_])${escapeRegExp(t)}(?![\\p{L}\\p{N}_])`, "iu");
  return re.test(text);
}

/** Every narration pronoun the profile (or the built-in fallback) may use: not suspicious in narration. */
function narrationWords(profile: StyleProfileInfo | null | undefined, language: Language): Set<string> {
  const out = new Set<string>();
  for (const v of Object.values(FALLBACK_NARRATION[language])) if (v) out.add(v.toLocaleLowerCase("vi-VN"));
  const fromProfile = profile?.narration?.[language];
  if (fromProfile) for (const v of Object.values(fromProfile)) if (v?.trim()) out.add(v.trim().toLocaleLowerCase("vi-VN"));
  return out;
}

/**
 * Things worth checking before saving (never blocking): missing address terms for a Vietnamese card,
 * a greeting without any Thought, address terms used in the greeting's narration.
 */
export function cardHints(card: CharacterCard, profile?: StyleProfileInfo | null): CardHint[] {
  const hints: CardHint[] = [];
  const t = card.address_terms;
  if (card.language === "vi" && (!t.self_term.trim() || !t.player_term.trim())) {
    hints.push({
      field: "address",
      text: "Chưa điền đủ xưng hô (tự xưng và gọi người chơi). Tiếng Việt cần cặp xưng hô rõ ràng, ví dụ tớ/cậu.",
    });
  }
  for (const [label, value] of [
    ["tự xưng", t.self_term],
    ["gọi người chơi", t.player_term],
  ] as const) {
    if (value.trim() && normalizeTerm(value, card.language) !== value.trim()) {
      hints.push({
        field: "address",
        text: `Xưng hô (${label}) nên là một từ viết thường, ví dụ "${normalizeTerm(value, card.language)}".`,
      });
    }
  }

  const greeting = card.greeting.trim();
  if (greeting) {
    if (!THOUGHT_OPEN.test(greeting)) {
      hints.push({
        field: "greeting",
        text: "Lời mở đầu chưa có dòng [Thought: ...]. Nhân vật hay bắt chước lượt đầu, nên có 1-2 dòng suy nghĩ.",
      });
    }
    const narration = narrationOnly(greeting);
    const allowed = narrationWords(profile, card.language);
    const used = cleanList([t.self_term, t.player_term]).filter(
      (term) => !allowed.has(term.toLocaleLowerCase("vi-VN")) && containsWord(narration, term),
    );
    if (used.length > 0) {
      hints.push({
        field: "greeting",
        text: `Lời mở đầu dùng xưng hô trong dẫn truyện (${used
          .map((u) => `"${u}"`)
          .join(", ")}). Xưng hô chỉ nên nằm trong lời thoại và Thought; dẫn truyện dùng tên hoặc đại từ.`,
      });
    }
  }
  return hints;
}

// ---- story/test settings ----

export const FALLBACK_NARRATION: Record<Language, Record<Gender, string>> = {
  vi: { male: "anh", female: "cô", other: "" },
  en: { male: "he", female: "she", other: "they" },
};

/**
 * Third-person narration pronoun for a character of `gender` (same rule as the backend's default_settings):
 * the style profile's narration[language][gender], else the built-in fallback, else the name.
 */
export function suggestNarration(
  profile: StyleProfileInfo | null | undefined,
  language: Language,
  gender: Gender,
  name = "",
): string {
  const fromProfile = profile?.narration?.[language]?.[gender]?.trim();
  return fromProfile || FALLBACK_NARRATION[language][gender] || name.trim();
}

export function relationshipFor(a: Gender, b: Gender): RelationshipType {
  if (a === "other" || b === "other") return "none";
  if (a !== b) return "het";
  return a === "male" ? "bl" : "gl";
}

/** Replaces {{char}} / {{user}} (any case, inner spaces allowed) like the backend's PromptContext.fill. */
export function fillPlaceholders(text: string, charName: string, userName: string): string {
  return text
    .replace(/\{\{\s*char\s*\}\}/gi, () => charName)
    .replace(/\{\{\s*user\s*\}\}/gi, () => userName)
    .trim();
}

/** What a new story of this card + persona would start with (mirror of backend default_settings). */
export function defaultTestSettings(
  card: CharacterCard,
  persona: Persona,
  profile: StyleProfileInfo | null | undefined,
  language: Language = card.language,
): StorySettings {
  return {
    scenario: fillPlaceholders(card.scenario, card.name.trim(), persona.name.trim()),
    language,
    mode: "story",
    relationship_type: relationshipFor(card.gender, persona.gender),
    pov: "third",
    thought_style: "inline",
    narration_pronouns: {
      character: suggestNarration(profile, language, card.gender, card.name),
      player: suggestNarration(profile, language, persona.gender, persona.name),
    },
  };
}

/** User overrides on top of the defaults (only the fields the user touched). */
export type SettingsOverrides = Partial<Omit<StorySettings, "narration_pronouns">> & {
  narration_character?: string;
  narration_player?: string;
};

export function applyOverrides(defaults: StorySettings, o: SettingsOverrides): StorySettings {
  const language = o.language ?? defaults.language;
  return {
    scenario: o.scenario ?? defaults.scenario,
    language,
    mode: o.mode ?? defaults.mode,
    relationship_type: o.relationship_type ?? defaults.relationship_type,
    pov: o.pov ?? defaults.pov,
    thought_style: o.thought_style ?? defaults.thought_style,
    narration_pronouns: {
      character: o.narration_character ?? defaults.narration_pronouns.character,
      player: o.narration_player ?? defaults.narration_pronouns.player,
    },
  };
}

// ---- dirty check ----

function sameValue(a: unknown, b: unknown): boolean {
  if (a === b) return true;
  if (Array.isArray(a) || Array.isArray(b)) {
    if (!Array.isArray(a) || !Array.isArray(b) || a.length !== b.length) return false;
    return a.every((v, i) => sameValue(v, b[i]));
  }
  if (a && b && typeof a === "object" && typeof b === "object") {
    const ka = Object.keys(a as object).filter((k) => (a as Record<string, unknown>)[k] !== undefined);
    const kb = Object.keys(b as object).filter((k) => (b as Record<string, unknown>)[k] !== undefined);
    if (ka.length !== kb.length) return false;
    return ka.every((k) => sameValue((a as Record<string, unknown>)[k], (b as Record<string, unknown>)[k]));
  }
  return false;
}

/** Fields compared by isDirty: everything the user edits (not `id`, not the server-managed `avatar`). */
const DIRTY_KEYS: (keyof CharacterCard)[] = [
  "name",
  "role",
  "gender",
  "language",
  "description",
  "personality",
  "appearance",
  "background",
  "goals",
  "secrets",
  "speech_style",
  "style_profile",
  "address_terms",
  "greeting",
  "example_dialogues",
  "tags",
  "scenario",
  "alternate_greetings",
  "creator_notes",
  "extensions",
];

/** True when `b` differs from `a` in any user-editable field. Extra keys (CardOut) are ignored. */
export function isDirty(a: CharacterCard, b: CharacterCard): boolean {
  // Phase 4b: the "Công khai" switch is saved with the card (missing = private, the default).
  if ((a.visibility ?? "private") !== (b.visibility ?? "private")) return true;
  return DIRTY_KEYS.some((k) => !sameValue(a[k], b[k]));
}

// ---- starting emotions (extensions.lyris.initial_relationship) ----

/** The six emotions in DESIGN.md order. */
export const EMOTION_KEYS: readonly EmotionKey[] = ["affection", "trust", "attraction", "obsession", "fear", "aversion"];

export const EMOTION_LABEL: Record<EmotionKey, string> = {
  affection: "Thương mến",
  trust: "Tin cậy",
  attraction: "Rung động",
  obsession: "Nhung nhớ / Chiếm hữu",
  fear: "Lo sợ mất mát",
  aversion: "Khoảng cách",
};

/** One line per emotion for the Studio sliders: what a high value means at the first scene. */
export const EMOTION_HINT: Record<EmotionKey, string> = {
  affection: "Quý mến, muốn quan tâm người chơi.",
  trust: "Tin lời, dám mở lòng.",
  attraction: "Để ý, tim đập nhanh khi ở gần.",
  obsession: "Nhớ nhung, muốn giữ người chơi cho riêng mình.",
  fear: "Sợ mất người chơi hoặc mối quan hệ này.",
  aversion: "Dè chừng, giữ khoảng cách.",
};

export type InitialRelationship = Record<EmotionKey, number>;

/** Where a new story's emotion matrix starts when the card says nothing else (0-100). */
export const DEFAULT_INITIAL_RELATIONSHIP: Readonly<InitialRelationship> = Object.freeze({
  affection: 30,
  trust: 30,
  attraction: 10,
  obsession: 0,
  fear: 0,
  aversion: 20,
});

function isPlainObject(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

/** A whole number 0-100; anything that is not a finite number gives `fallback`. */
export function clampEmotion(value: unknown, fallback: number): number {
  if (typeof value !== "number" || !Number.isFinite(value)) return fallback;
  return Math.min(100, Math.max(0, Math.round(value)));
}

/**
 * The card's starting emotions from extensions.lyris.initial_relationship, each value checked;
 * missing or broken values fall back to the defaults. `stored` = the card had the object at all.
 */
export function readInitialRelationship(card: Pick<CharacterCard, "extensions">): {
  values: InitialRelationship;
  stored: boolean;
} {
  const lyris = isPlainObject(card.extensions) ? card.extensions.lyris : undefined;
  const raw = isPlainObject(lyris) ? lyris.initial_relationship : undefined;
  const src = isPlainObject(raw) ? raw : {};
  const values = {} as InitialRelationship;
  for (const k of EMOTION_KEYS) values[k] = clampEmotion(src[k], DEFAULT_INITIAL_RELATIONSHIP[k]);
  return { values, stored: isPlainObject(raw) };
}

/**
 * A copy of the card with extensions.lyris.initial_relationship set (the patch merged over the
 * current values). Every other key of `extensions` and of `extensions.lyris` is kept.
 */
export function withInitialRelationship(card: CharacterCard, patch: Partial<InitialRelationship>): CharacterCard {
  const current = readInitialRelationship(card).values;
  const next = {} as InitialRelationship;
  for (const k of EMOTION_KEYS) next[k] = clampEmotion(patch[k], current[k]);
  const ext = isPlainObject(card.extensions) ? card.extensions : {};
  const lyris = isPlainObject(ext.lyris) ? ext.lyris : {};
  return { ...card, extensions: { ...ext, lyris: { ...lyris, initial_relationship: next } } };
}

/** True when every value equals the default. */
export function isDefaultRelationship(values: InitialRelationship): boolean {
  return EMOTION_KEYS.every((k) => values[k] === DEFAULT_INITIAL_RELATIONSHIP[k]);
}

// ---- Studio list ----

/** The role of a card list row; the list endpoint may or may not send it (read defensively). */
export function summaryRole(row: unknown): string {
  if (!isPlainObject(row)) return "";
  const role = row.role;
  return typeof role === "string" ? role.replace(/\s+/g, " ").trim() : "";
}

interface SearchableCard {
  name: string;
  description: string;
  tags: string[];
}

/** Cards whose name, role, tag or description contains the query (case-insensitive, Vietnamese). */
export function filterCards<T extends SearchableCard>(cards: readonly T[], query: string): T[] {
  const q = query.replace(/\s+/g, " ").trim().toLocaleLowerCase("vi-VN");
  if (!q) return [...cards];
  const has = (s: string) => s.toLocaleLowerCase("vi-VN").includes(q);
  return cards.filter((c) => has(c.name) || has(summaryRole(c)) || c.tags.some(has) || has(c.description));
}

// ---- time ----

function parseIso(iso: string): Date | null {
  const d = new Date(iso.endsWith("Z") || /[+-]\d\d:?\d\d$/.test(iso) ? iso : `${iso}Z`);
  return Number.isNaN(d.getTime()) ? null : d;
}

/** "vừa xong", "5 phút trước", "3 giờ trước", "2 ngày trước", then "12/11/2026". Server times are UTC. */
export function formatRelativeTime(iso: string | null | undefined, now: number = Date.now()): string {
  if (!iso) return "";
  const d = parseIso(iso);
  if (!d) return "";
  const diff = (now - d.getTime()) / 1000;
  if (diff < 60) return "vừa xong";
  if (diff < 3600) return `${Math.floor(diff / 60)} phút trước`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} giờ trước`;
  if (diff < 86400 * 7) return `${Math.floor(diff / 86400)} ngày trước`;
  return d.toLocaleDateString("vi-VN", { day: "numeric", month: "numeric", year: "numeric" });
}

// ---- narration pronoun override (extensions.lyris.narration_character) ----

/** The card's own Vietnamese narration pronoun for the character ("" when it follows the style). */
export function readNarrationOverride(card: Pick<CharacterCard, "extensions">): string {
  const ext = isPlainObject(card.extensions) ? card.extensions : {};
  const lyris = isPlainObject(ext.lyris) ? ext.lyris : {};
  const v = lyris.narration_character;
  if (typeof v === "string") return v;
  if (isPlainObject(v) && typeof v.vi === "string") return v.vi;
  return "";
}

/**
 * A copy of the card with extensions.lyris.narration_character set to `value` (trimmed, at most
 * 20 characters), or removed when empty. Every other extensions key is kept; an {vi, en} object
 * keeps its "en" value.
 */
export function withNarrationOverride(card: CharacterCard, value: string): CharacterCard {
  const ext = isPlainObject(card.extensions) ? card.extensions : {};
  const lyris: Record<string, unknown> = isPlainObject(ext.lyris) ? { ...ext.lyris } : {};
  const clean = value.replace(/\s+/g, " ").trim().slice(0, 20);
  const prev = lyris.narration_character;
  if (isPlainObject(prev)) {
    const next: Record<string, unknown> = { ...prev };
    if (clean) next.vi = clean;
    else delete next.vi;
    if (Object.keys(next).length) lyris.narration_character = next;
    else delete lyris.narration_character;
  } else if (clean) {
    lyris.narration_character = clean;
  } else {
    delete lyris.narration_character;
  }
  return { ...card, extensions: { ...ext, lyris } };
}
