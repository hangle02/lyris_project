// "Lời nói đặc trưng": two or three lines a character would say, shown on the character profile.
// Stored on the card as extensions.lyris.signature_lines (optional, at most 3 lines of 140
// characters); when a card has none, picked from its example dialogues and greeting.
// Pure functions (tested in signatureLines.test.ts). No React, no DOM.

import type { CharacterCard } from "../types.ts";
import { fillForReader } from "../pages/explore/logic.ts";

export const SIGNATURE_MAX_LINES = 3;
export const SIGNATURE_MAX_CHARS = 140;
/** A picked line shorter than this says too little about the character. */
const MIN_CHARS = 12;
const MIN_WORDS = 3;
/** Picked lines closest to this length read best on the profile (one or two lines on a phone). */
const IDEAL_CHARS = 70;

function isPlainObject(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

const WRAP_QUOTES = /^[\s"“”«»「」'‘’]+|[\s"“”«»「」'‘’]+$/gu;

/** One line as stored: single spaces, no quotation marks around it. */
export function cleanSignatureLine(line: string): string {
  return line.replace(/\s+/g, " ").replace(WRAP_QUOTES, "").trim();
}

/**
 * Lines ready to store or show: cleaned, empty ones and repeats dropped, at most 3, each cut to 140
 * characters (the editor blocks longer ones before saving; this only guards old or imported data).
 */
export function cleanSignatureLines(lines: readonly unknown[]): string[] {
  const out: string[] = [];
  const seen = new Set<string>();
  for (const raw of lines) {
    if (typeof raw !== "string") continue;
    const line = Array.from(cleanSignatureLine(raw)).slice(0, SIGNATURE_MAX_CHARS).join("").trim();
    if (!line) continue;
    const key = line.toLocaleLowerCase("vi-VN");
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(line);
    if (out.length === SIGNATURE_MAX_LINES) break;
  }
  return out;
}

/** The raw stored value (strings only, as typed in the editor), or [] when the card has none. */
function storedLines(card: Pick<CharacterCard, "extensions">): string[] {
  const lyris = isPlainObject(card.extensions) ? card.extensions.lyris : undefined;
  const raw = isPlainObject(lyris) ? lyris.signature_lines : undefined;
  return Array.isArray(raw) ? raw.filter((x): x is string => typeof x === "string") : [];
}

/** The card's own signature lines, cleaned (empty when it has none). */
export function readSignatureLines(card: Pick<CharacterCard, "extensions">): string[] {
  return cleanSignatureLines(storedLines(card));
}

/** Text of the Studio field: one line per row, as the user typed it. */
export function signatureText(card: Pick<CharacterCard, "extensions">): string {
  return storedLines(card).join("\n");
}

/**
 * A copy of the card with the field's text stored as extensions.lyris.signature_lines (rows kept as
 * typed so the textarea does not jump while editing; cleaned on save), or the key removed when the
 * text is blank. Every other key of `extensions` and `extensions.lyris` is kept.
 */
export function withSignatureText<T extends Pick<CharacterCard, "extensions">>(card: T, text: string): T {
  const ext = isPlainObject(card.extensions) ? card.extensions : {};
  const lyris: Record<string, unknown> = isPlainObject(ext.lyris) ? { ...ext.lyris } : {};
  if (text.trim()) lyris.signature_lines = text.split("\n");
  else delete lyris.signature_lines;
  return { ...card, extensions: { ...ext, lyris } };
}

/** The card with its signature lines cleaned for saving (key removed when nothing is left). */
export function withCleanSignatureLines<T extends Pick<CharacterCard, "extensions">>(card: T): T {
  const ext = isPlainObject(card.extensions) ? card.extensions : {};
  if (!isPlainObject(ext.lyris) || !("signature_lines" in ext.lyris)) return card;
  const lyris: Record<string, unknown> = { ...ext.lyris };
  const clean = cleanSignatureLines(Array.isArray(lyris.signature_lines) ? lyris.signature_lines : []);
  if (clean.length) lyris.signature_lines = clean;
  else delete lyris.signature_lines;
  return { ...card, extensions: { ...ext, lyris } };
}

/** Problems that block saving (Vietnamese), empty when fine. */
export function signatureProblems(card: Pick<CharacterCard, "extensions">): string[] {
  const lines = storedLines(card).map(cleanSignatureLine).filter(Boolean);
  const errors: string[] = [];
  if (lines.length > SIGNATURE_MAX_LINES) errors.push(`Tối đa ${SIGNATURE_MAX_LINES} lời nói đặc trưng.`);
  lines.forEach((line, i) => {
    if (Array.from(line).length > SIGNATURE_MAX_CHARS) {
      errors.push(`Lời nói đặc trưng số ${i + 1} dài quá ${SIGNATURE_MAX_CHARS} ký tự.`);
    }
  });
  return errors;
}

// ---- picking lines from the card's own text ----

const THOUGHT = /\[\s*(?:thought|suy nghĩ|tiếng lòng)\s*:[^\]]*\]?/giu;
const QUOTED = /“([^”]+)”|"([^"]+)"|«([^»]+)»|「([^」]+)」/gu;
const CHAR_TAG = /^\{\{\s*char\s*\}\}$/i;
const USER_TAG = /^\{\{\s*user\s*\}\}$/i;
const USER_LABELS = new Set(["user", "you", "bạn", "người chơi", "player"]);
/** "Speaker: text" at the start of an example-dialogue line (label up to 40 characters, no quotes). */
const SPEAKER = /^\s*([^:"“«\n]{1,40}?)\s*:\s*/u;
/** A paragraph opening with a third-person pronoun continues about the person named just before. */
const PRONOUN_START = /^(?:anh|cô|nàng|hắn|chàng|gã|y|ông|bà|chị|cậu|he|she|they)(?=\s)/iu;

function quotedParts(text: string): string[] {
  const out: string[] = [];
  for (const m of text.matchAll(QUOTED)) {
    const inner = m[1] ?? m[2] ?? m[3] ?? m[4] ?? "";
    if (inner.trim()) out.push(inner);
  }
  return out;
}

function words(text: string): number {
  return text.split(/\s+/).filter(Boolean).length;
}

/** The longest run of whole sentences that fits in `max` characters, or "" when the first one is longer. */
function fitSentences(text: string, max: number): string {
  if (Array.from(text).length <= max) return text;
  const sentences = text.match(/[^.!?…]+[.!?…]+["”»]?\s*/gu) ?? [];
  let out = "";
  for (const s of sentences) {
    if (Array.from(out + s).length > max) break;
    out += s;
  }
  return out.trim();
}

interface Candidate {
  text: string;
  /** Order in the card (examples first, then greeting). */
  order: number;
  fromExamples: boolean;
}

/** Parts of a name that identify the character in narration ("Hạ Vy" -> "Hạ Vy", "Hạ", "Vy"). */
function nameParts(name: string): string[] {
  const full = name.replace(/\s+/g, " ").trim();
  if (!full) return [];
  const parts = full.split(" ").filter((w) => Array.from(w).length >= 2);
  return [full, ...parts];
}

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** True when `text` names the character (a capitalised name part as a whole word, or {{char}}). */
function mentions(text: string, parts: readonly string[]): boolean {
  if (/\{\{\s*char\s*\}\}/i.test(text)) return true;
  return parts.some((p) => new RegExp(`(^|[^\\p{L}\\p{N}])${escapeRegExp(p)}(?=$|[^\\p{L}\\p{N}])`, "u").test(text));
}

/** True when `text` has a letter or digit (a clause of only spaces and punctuation is "empty"). */
function hasWords(text: string): boolean {
  return /[\p{L}\p{N}]/u.test(text);
}

/** Opens with a third-person pronoun used as the subject ("Cô quay lưng…"), not a vocative ("Anh ơi,"). */
function startsWithPronoun(text: string): boolean {
  const t = text.trim();
  return PRONOUN_START.test(t) && !/^\S+\s*(?:,|ơi\b|à\b|này\b|nhé\b)/iu.test(t);
}

/** Words that, right after the pronoun, make "Cô khẽ nói:" a speech tag rather than a name ("Bà chủ quán:"). */
const SAY_WORDS = new Set(
  "nói đáp hỏi bảo khẽ thì thầm lẩm nhẹ cười gắt quát hét thở nhắc trả lên hạ chậm lạnh dịu nhỏ said says asked whispered replied murmured".split(" "),
);

/** A label like "Cô nói" / "Anh khẽ đáp" / "She whispered": a pronoun followed by a speech word. */
function pronounSays(label: string): boolean {
  if (!startsWithPronoun(label)) return false;
  const second = label.trim().split(/\s+/)[1]?.toLocaleLowerCase("vi-VN") ?? "";
  return SAY_WORDS.has(second);
}

/**
 * Unquoted text of a {{char}} turn that is narration about the character rather than speech: it
 * opens with a third-person pronoun or the character's name ("Cô lặng im…", "Hạ Vy cười…").
 */
function isNarration(text: string, parts: readonly string[]): boolean {
  const t = text.trim();
  if (startsWithPronoun(t)) return true;
  return parts.some((p) => t.toLocaleLowerCase("vi-VN").startsWith(`${p.toLocaleLowerCase("vi-VN")} `));
}

/**
 * Spoken lines of the character in the example dialogues (Speaker: text format, <START> blocks).
 * Unquoted speech counts only on the line that carries the character's label; later lines of the same
 * turn give their quoted parts only (unquoted ones are narration). A line led by another label
 * ("Bà chủ quán: “…”") starts someone else's turn, unless the label names the character
 * ("Hạ Vy khẽ nói: “…”") or is a pronoun clause inside the character's turn ("Cô nói: “…”").
 */
function fromExamples(text: string, name: string): string[] {
  const out: string[] = [];
  const parts = nameParts(name);
  const own = name.trim().toLocaleLowerCase("vi-VN");
  let speaker: "char" | "other" | null = null;
  for (const rawLine of text.split("\n")) {
    let line = rawLine.replace(THOUGHT, " ").trim();
    if (!line) continue;
    if (/^<\s*start\s*>$/i.test(line)) {
      speaker = null;
      continue;
    }
    let labelled = false;
    const m = SPEAKER.exec(line);
    if (m) {
      const label = (m[1] ?? "").trim();
      const lower = label.toLocaleLowerCase("vi-VN");
      if (CHAR_TAG.test(label) || (own && lower === own)) {
        speaker = "char";
        labelled = true;
      } else if (USER_TAG.test(label) || USER_LABELS.has(lower)) {
        speaker = "other";
      } else if (mentions(label, parts)) {
        speaker = "char";
      } else if (!(speaker === "char" && pronounSays(label))) {
        speaker = "other";
      }
      line = line.slice(m[0].length);
    }
    if (speaker !== "char") continue;
    const quotes = quotedParts(line);
    if (quotes.length) out.push(...quotes);
    else if (labelled) {
      // Unquoted speech: drop *actions* and (asides); keep it only when words remain and they are not
      // narration about the character.
      const plain = line.replace(/\*[^*]*\*/g, " ").replace(/\([^)]*\)/g, " ").trim();
      if (plain && !isNarration(plain, parts)) out.push(plain);
    }
  }
  return out;
}

/**
 * Quoted lines of the greeting said by the character. Each quote is judged by the narration just
 * before it (since the previous quote or the paragraph start): taken when that clause names the
 * character, or goes on about them with a pronoun ("Cô cười: “…”"), or is empty and the character was
 * the subject so far (a standalone quote right after a paragraph about them). Lines of other people
 * ("Một nữ sinh rụt rè đi tới: “…”", "Người phục vụ chen vào: “…”") are skipped.
 */
function fromGreeting(text: string, name: string): string[] {
  const parts = nameParts(name);
  const out: string[] = [];
  const paragraphs = text
    .split(/\n+/)
    .map((p) => p.replace(THOUGHT, " ").trim())
    .filter(Boolean);
  let about = false;
  const follow = (clause: string) => {
    if (hasWords(clause)) about = mentions(clause, parts) || (about && startsWithPronoun(clause));
  };
  for (const p of paragraphs) {
    let last = 0;
    for (const m of p.matchAll(QUOTED)) {
      const index = m.index ?? 0;
      follow(p.slice(last, index));
      last = index + m[0].length;
      const inner = m[1] ?? m[2] ?? m[3] ?? m[4] ?? "";
      if (about && inner.trim()) out.push(inner);
    }
    follow(p.slice(last));
  }
  return out;
}

function prepare(raw: string, name: string, language: "vi" | "en"): string {
  const filled = fillForReader(raw, name, language).replace(/\{\{\s*char\s*\}\}/gi, name);
  const line = cleanSignatureLine(filled);
  return fitSentences(line, SIGNATURE_MAX_CHARS);
}

/**
 * Two or three lines the character says, picked from the card itself: spoken lines of
 * `example_dialogues` first, then quoted lines of the greeting said by the character. Thought tags,
 * speaker labels and *actions* are removed; {{char}} becomes the name and {{user}} "bạn" / "you".
 * Distinct lines of at least three words, those closest to a medium length win, shown in the
 * card's order. Empty when the card has nothing usable.
 */
export function pickSignatureLines(
  card: Pick<CharacterCard, "name" | "language" | "example_dialogues" | "greeting">,
  max = SIGNATURE_MAX_LINES,
): string[] {
  const name = card.name.replace(/\s+/g, " ").trim();
  const lang = card.language === "en" ? "en" : "vi";
  const seen = new Set<string>();
  const candidates: Candidate[] = [];
  const add = (raw: string, fromEx: boolean) => {
    const text = prepare(raw, name, lang);
    const len = Array.from(text).length;
    if (len < MIN_CHARS || words(text) < MIN_WORDS) return;
    const key = text.toLocaleLowerCase("vi-VN").replace(/[^\p{L}\p{N}]+/gu, " ").trim();
    if (seen.has(key)) return;
    seen.add(key);
    candidates.push({ text, order: candidates.length, fromExamples: fromEx });
  };
  for (const l of fromExamples(card.example_dialogues ?? "", name)) add(l, true);
  for (const l of fromGreeting(card.greeting ?? "", name)) add(l, false);

  const score = (c: Candidate) => Math.abs(Array.from(c.text).length - IDEAL_CHARS);
  const examples = candidates.filter((c) => c.fromExamples).sort((a, b) => score(a) - score(b) || a.order - b.order);
  const greeting = candidates.filter((c) => !c.fromExamples).sort((a, b) => score(a) - score(b) || a.order - b.order);
  const chosen = [...examples, ...greeting].slice(0, Math.max(0, max));
  return chosen.sort((a, b) => a.order - b.order).map((c) => c.text);
}

/**
 * What the profile shows under "Lời nói đặc trưng": the card's own lines (placeholders filled for
 * the reader) or, when it has none, lines picked from its dialogue. `own` tells which.
 */
export function signatureLinesFor(
  card: Pick<CharacterCard, "name" | "language" | "example_dialogues" | "greeting" | "extensions">,
): { lines: string[]; own: boolean } {
  const stored = readSignatureLines(card);
  if (stored.length) {
    const name = card.name.replace(/\s+/g, " ").trim();
    const lang = card.language === "en" ? "en" : "vi";
    return { lines: stored.map((l) => cleanSignatureLine(fillForReader(l, name, lang))), own: true };
  }
  return { lines: pickSignatureLines(card), own: false };
}
