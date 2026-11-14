// Small text helpers for rendering prose, bubbles and directives.

/** Max length of a message body; same limit as the backend (routes.MAX_CONTENT_CHARS). */
export const MAX_CONTENT_CHARS = 20_000;

const EMOTICON_BEFORE = new Set([":", ";", "=", "x", "X", "8"]);

/** Index of the next "((" that opens a directive from `pos`, or -1. Skips emoticons like ":((". */
function nextOpener(text: string, pos: number): number {
  for (;;) {
    const i = text.indexOf("((", pos);
    if (i === -1) return -1;
    let runStart = i;
    while (runStart > pos && text[runStart - 1] === "(") runStart--;
    const before = runStart > 0 ? (text[runStart - 1] as string) : "";
    if (before && EMOTICON_BEFORE.has(before)) {
      let j = i;
      while (j < text.length && text[j] === "(") j++;
      pos = j;
      continue;
    }
    return i;
  }
}

/**
 * Client-side mirror of backend extract_directives(): removes every ((...)) (but not
 * emoticons such as ":((" or "=))") and returns the cleaned text plus the directives
 * joined with "; " (or null). An unclosed "((" at the start of a line or after a space,
 * followed by text, runs to the end. Used only for the optimistic user bubble before
 * the server echoes the message.
 */
export function extractDirectives(text: string): { visible: string; directive: string | null } {
  const found: string[] = [];
  const kept: string[] = [];
  let pos = 0;
  for (;;) {
    const i = nextOpener(text, pos);
    if (i === -1) {
      kept.push(text.slice(pos));
      break;
    }
    const j = text.indexOf("))", i + 2);
    if (j === -1) {
      const rest = text.slice(i + 2);
      const before = i > 0 ? (text[i - 1] as string) : "";
      if ((!before || /\s/.test(before)) && rest.replace(/[\s()]/g, "").length > 0) {
        kept.push(text.slice(pos, i));
        const d = rest.replace(/\s+/g, " ").trim();
        if (d) found.push(d);
      } else {
        kept.push(text.slice(pos));
      }
      break;
    }
    kept.push(text.slice(pos, i), " ");
    const d = text.slice(i + 2, j).replace(/\s+/g, " ").trim();
    if (d) found.push(d);
    pos = j + 2;
  }
  const visible = kept
    .join("")
    .split("\n")
    .map((l) => l.replace(/[ \t]{2,}/g, " ").trim())
    .join("\n")
    .replace(/\n{3,}/g, "\n\n")
    .replace(/[ \t]+([,.!?…])/g, "$1")
    .trim();
  return { visible, directive: found.length ? found.join("; ") : null };
}

/** Paragraphs for prose: every non-empty line is its own paragraph. */
export function splitParagraphs(text: string): string[] {
  return text
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter((l) => l.length > 0);
}

export type InlineSegment =
  | { kind: "plain"; text: string }
  | { kind: "quote"; text: string }
  | { kind: "action"; text: string };

const QUOTE_PAIRS: Record<string, string> = {
  "“": "”", // “ ”
  '"': '"',
  "«": "»", // « »
  "「": "」", // 「 」
};

/** True when the mark at `i` starts a word: line start or after a space/opening punctuation, and a non-space follows. */
function opensWord(line: string, i: number): boolean {
  const prev = i === 0 ? "" : (line[i - 1] as string);
  const next = line[i + 1];
  return (prev === "" || /[\s:(\[—–-]/u.test(prev)) && next !== undefined && !/\s/u.test(next);
}

/**
 * Splits a line into plain text, dialogue in quotes (kept with its quote marks) and
 * *actions* (asterisks removed). An unclosed quote runs to the end of the line, which
 * reads naturally while a reply is still streaming; an unclosed "*" stays literal.
 */
export function parseInline(line: string): InlineSegment[] {
  const out: InlineSegment[] = [];
  let plain = "";
  const pushPlain = () => {
    if (plain) out.push({ kind: "plain", text: plain });
    plain = "";
  };

  let i = 0;
  while (i < line.length) {
    const ch = line[i] as string;
    // Phone keyboards sometimes type a closing ” where an opening “ belongs (”Chào cậu”). A ” that
    // starts a word and has a partner ” later on the line opens a quote; otherwise it stays text.
    if (ch === "”" && opensWord(line, i)) {
      const end = line.indexOf("”", i + 1);
      if (end !== -1) {
        pushPlain();
        out.push({ kind: "quote", text: line.slice(i, end + 1) });
        i = end + 1;
        continue;
      }
    }
    const close = QUOTE_PAIRS[ch];
    if (close !== undefined) {
      const end = line.indexOf(close, i + 1);
      pushPlain();
      if (end === -1) {
        out.push({ kind: "quote", text: line.slice(i) });
        return out;
      }
      out.push({ kind: "quote", text: line.slice(i, end + 1) });
      i = end + 1;
      continue;
    }
    if (ch === "*") {
      const end = line.indexOf("*", i + 1);
      if (end > i + 1) {
        pushPlain();
        out.push({ kind: "action", text: line.slice(i + 1, end) });
        i = end + 1;
        continue;
      }
    }
    plain += ch;
    i++;
  }
  pushPlain();
  return out;
}

export interface ReplySegment {
  kind: "text" | "thought";
  text: string;
}

const THOUGHT_OPEN = /\[[ \t]*thought[ \t]*:/i;
/** A paragraph break: newline, optional spaces/tabs, newline (a blank line). */
const PARA_BREAK = /\n[ \t]*\n/;

/**
 * Body of a thought that ended without "]" (at a paragraph break or the end of the text): trimmed,
 * minus one trailing unmatched quote (an odd `"`, a `”` without its `“`, or a `“`) and the
 * whitespace around it. Mirrors _strip_unclosed in backend llm/thought.py.
 */
function stripUnclosed(body: string): string {
  const t = body.trim();
  const last = t.slice(-1);
  const count = (q: string) => t.split(q).length - 1;
  const unmatched =
    (last === '"' && count('"') % 2 === 1) || (last === "”" && count("”") > count("“")) || last === "“";
  return unmatched ? t.slice(0, -1).trimEnd() : t;
}

/**
 * Splits a raw assistant reply into story text and [Thought: ...] parts, in order.
 * Mirrors backend llm/thought.py: the tag is case-insensitive and may contain spaces; a thought
 * ends at the first "]", or, when no "]" comes first, at the first paragraph break (blank line)
 * or the end of the text. A single newline does not end it. Text after the paragraph break is
 * story text again, and an unclosed thought loses one trailing unmatched quote.
 * Empty parts are dropped; adjacent parts of the same kind are merged.
 */
export function splitSegments(raw: string): ReplySegment[] {
  const out: ReplySegment[] = [];
  const push = (kind: ReplySegment["kind"], text: string) => {
    const t = text.trim();
    if (!t) return;
    const prev = out[out.length - 1];
    if (prev && prev.kind === kind) prev.text = `${prev.text}\n\n${t}`;
    else out.push({ kind, text: t });
  };
  // Like split_thought, an empty thought is dropped and the text around it stays one part.
  let text = "";
  let rest = raw;
  for (;;) {
    const m = THOUGHT_OPEN.exec(rest);
    if (!m) {
      text += rest;
      break;
    }
    text += rest.slice(0, m.index);
    rest = rest.slice(m.index + m[0].length);
    const close = rest.indexOf("]");
    const brk = PARA_BREAK.exec(rest);
    const closed = close !== -1 && (!brk || close < brk.index);
    // Unclosed: ends at the paragraph break (which stays in the story text) or the end.
    const end = closed ? close : brk ? brk.index : rest.length;
    const body = closed ? rest.slice(0, end).trim() : stripUnclosed(rest.slice(0, end));
    if (body) {
      push("text", text);
      text = "";
      push("thought", body);
    }
    rest = rest.slice(closed ? end + 1 : end);
    if (!rest) break;
  }
  push("text", text);
  return out;
}

/** Appends a streamed delta to ordered segments (returns a new array). */
export function appendSegment(segments: ReplySegment[], kind: ReplySegment["kind"], text: string): ReplySegment[] {
  if (!text) return segments;
  const last = segments[segments.length - 1];
  if (last && last.kind === kind) {
    return [...segments.slice(0, -1), { kind, text: last.text + text }];
  }
  return [...segments, { kind, text }];
}

/** Rebuilds raw text (with [Thought: ...] tags) from ordered segments. */
export function joinSegments(segments: ReplySegment[]): string {
  return segments
    .map((s) => (s.kind === "thought" ? `[Thought: ${s.text.trim()}]` : s.text.trim()))
    .filter(Boolean)
    .join("\n\n");
}

/**
 * A server message made readable as UI copy: `code spans` (Markdown backticks) become “quoted”
 * words, since the app shows no monospace. Other text is left as it is.
 */
export function plainMessage(text: string): string {
  return text.replace(/`([^`\n]+)`/g, "“$1”");
}

/** ơ / ư (any tone, any case): their horn overhangs the right edge of the letter. */
const HORN_THEN_QUOTE = /([ơờớởỡợưừứửữựƠỜỚỞỠỢƯỪỨỬỮỰ])(['’"”])/g;

/**
 * Be Vietnam Pro draws the horn of ơ/ư past the letter's advance, so a closing quote or apostrophe
 * right after it ("sư'", "từ”") lands on the horn and disappears. A hair space (U+200A) between them
 * keeps both visible. Display only: never applied to text that is sent or stored.
 */
export function spaceAfterHorn(text: string): string {
  return text.replace(HORN_THEN_QUOTE, "$1 $2");
}
