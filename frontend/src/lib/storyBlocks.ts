// Story Mode: một lượt của nhân vật thành ba loại khối (DESIGN.md §6 lớp 2, design-impl §6.2.3).
//
// - narration: đoạn dẫn truyện / hành động (hiển thị nghiêng, màu muted, không khung). Có thể chứa
//   lời trích ngắn (dưới 3 từ, không có dấu kết câu, không đứng đầu đoạn: tên riêng, biệt danh, một
//   từ được nhắc) giữ trong dòng, hiển thị thẳng.
// - dialogue: lời thoại trong ngoặc kép từ 3 từ trở lên, hoặc câu nói ngắn ("“Được.”", "“Ừ!”", hay
//   đứng đầu đoạn), thành thẻ riêng; khi hiển thị bỏ cặp ngoặc ngoài cùng (speechText).
// - thought: [Thought: ...] giữ đúng vị trí model đặt.
//
// Hàm thuần, không phụ thuộc React; có test ở storyBlocks.test.ts.
import { parseInline, splitParagraphs } from "./text.ts";
import type { ReplySegment } from "./text.ts";

/** A piece of a narration paragraph. `quote` is a short quote kept inline (upright, marks kept). */
export type NarrationPart = { kind: "plain" | "action" | "quote"; text: string };

export type StoryBlock =
  | { kind: "narration"; parts: NarrationPart[] }
  | { kind: "dialogue"; text: string }
  | { kind: "thought"; text: string };

/** Quotes with at least this many words become a dialogue card. */
export const DIALOGUE_MIN_WORDS = 3;

// ” is here too: a phone keyboard may open a quote with it (text.ts parseInline).
const OPENERS = new Set(["“", "”", '"', "«", "「"]);
const CLOSERS = new Set(["”", '"', "»", "」"]);

/** The words inside a quote (its marks removed). An unclosed quote counts to its end. */
export function quoteWordCount(quote: string): number {
  let inner = quote.trim();
  if (inner && OPENERS.has(inner[0] as string)) inner = inner.slice(1);
  if (inner && CLOSERS.has(inner[inner.length - 1] as string)) inner = inner.slice(0, -1);
  const words = inner.trim().split(/\s+/).filter((w) => /[\p{L}\p{N}]/u.test(w));
  return words.length;
}

/**
 * Straight double quotes become curly (“...”) so every dialogue card reads the same; curly, « » and
 * 「 」 are kept as written. An unclosed straight quote (still streaming) only gets its opener.
 */
export function curlyQuote(quote: string): string {
  const t = quote.trim();
  if (!t.startsWith('"')) return t;
  const closed = t.length > 1 && t.endsWith('"');
  return `“${t.slice(1, closed ? -1 : undefined)}${closed ? "”" : ""}`;
}

/**
 * The words of a dialogue card without its outer quote marks: the card itself marks the speech, so
 * “...” around it would say it twice. Only the outermost pair goes (an unclosed quote still
 * streaming loses its opener); quotes inside the line stay.
 */
export function speechText(quote: string): string {
  let t = quote.trim();
  if (t && OPENERS.has(t[0] as string)) t = t.slice(1);
  if (t && CLOSERS.has(t[t.length - 1] as string)) t = t.slice(0, -1);
  return t.trim();
}

/** True when `text` is one quotation from its first to its last character (*"…"* citations). */
function isWholeQuote(text: string): boolean {
  const segs = parseInline(text.trim());
  return segs.length === 1 && segs[0]?.kind === "quote" && /[\p{L}\p{N}]/u.test(text);
}

/**
 * True when a short quote reads as something said, not a term or nickname being mentioned: it ends
 * with sentence punctuation inside its marks ("“Được.”", "“Ừ!”", "“Thật?”"), or it opens the
 * paragraph ("“Đi thôi”, hắn nói."). Laconic characters speak in one or two words; their lines are
 * still dialogue cards.
 */
function looksSpoken(quote: string, opensParagraph: boolean): boolean {
  if (opensParagraph) return true;
  let inner = quote.trim();
  if (inner && CLOSERS.has(inner[inner.length - 1] as string)) inner = inner.slice(0, -1);
  return /[.!?…,~]$/u.test(inner.trim());
}

/** True when a narration piece carries words (not only punctuation or spaces left between two cards). */
function hasWords(parts: NarrationPart[]): boolean {
  return parts.some((p) => /[\p{L}\p{N}]/u.test(p.text));
}

/** Trims the outer edges of a run of parts (spaces next to a card), dropping parts left empty. */
function trimParts(parts: NarrationPart[]): NarrationPart[] {
  const out = parts.map((p) => ({ ...p }));
  while (out.length && out[0] && out[0].kind !== "quote") {
    out[0].text = out[0].text.replace(/^\s+/, "");
    if (out[0].text) break;
    out.shift();
  }
  for (;;) {
    const last = out[out.length - 1];
    if (!last || last.kind === "quote") break;
    last.text = last.text.replace(/\s+$/, "");
    if (last.text) break;
    out.pop();
  }
  return out;
}

/**
 * One paragraph of story text: narration blocks split around dialogue cards. A paragraph that is
 * only speech (no narration words around it) is a card even when short ("“Ừ.”"): there is no
 * narration line for it to stay inside. `minWords`: the shortest quote inside narration that is
 * still a card (the player's turns use 1: whatever they put in "…" is their speech).
 *
 * A quote wrapped in asterisks (*"…"*) is a citation or another person's words, never a card: it
 * stays in the narration line, upright, with its marks.
 */
export function paragraphBlocks(paragraph: string, minWords: number = DIALOGUE_MIN_WORDS): StoryBlock[] {
  const segs = parseInline(paragraph);
  const speechOnly = segs.every((s) => s.kind === "quote" || !/[\p{L}\p{N}]/u.test(s.text));
  const blocks: StoryBlock[] = [];
  let run: NarrationPart[] = [];
  const flush = () => {
    // Narration right after a card drops the comma / colon the card left behind ("“Đi thôi”, hắn nói.").
    const first = run[0];
    if (first && first.kind !== "quote" && blocks[blocks.length - 1]?.kind === "dialogue") {
      first.text = first.text.replace(/^\s*[,;:]\s*/u, "");
    }
    const parts = trimParts(run);
    run = [];
    if (parts.length && hasWords(parts)) blocks.push({ kind: "narration", parts });
  };
  let wordsBefore = false;
  for (const seg of segs) {
    const opens = !wordsBefore;
    if (/[\p{L}\p{N}]/u.test(seg.text)) wordsBefore = true;
    if (
      seg.kind === "quote" &&
      (speechOnly || quoteWordCount(seg.text) >= minWords || looksSpoken(seg.text, opens))
    ) {
      flush();
      blocks.push({ kind: "dialogue", text: curlyQuote(seg.text) });
      continue;
    }
    if (seg.kind === "action" && isWholeQuote(seg.text)) {
      run.push({ kind: "quote", text: curlyQuote(seg.text.trim()) });
      continue;
    }
    const prev = run[run.length - 1];
    // Neighbouring pieces of the same kind merge (keeps the part list short and stable).
    if (prev && prev.kind === seg.kind && seg.kind !== "quote") prev.text += seg.text;
    else run.push({ kind: seg.kind, text: seg.text });
  }
  flush();
  return blocks;
}

/**
 * A Story Mode reply as ordered blocks. Text segments split into paragraphs (one per non-empty
 * line), each paragraph into narration and dialogue; each thought segment is one thought block
 * (its paragraphs joined by a blank line) at the place it was written.
 */
export function buildStoryBlocks(segments: ReplySegment[]): StoryBlock[] {
  const out: StoryBlock[] = [];
  for (const seg of segments) {
    if (seg.kind === "thought") {
      const text = splitParagraphs(seg.text).join("\n\n");
      if (text) out.push({ kind: "thought", text });
      continue;
    }
    for (const para of splitParagraphs(seg.text)) out.push(...paragraphBlocks(para));
  }
  return out;
}

/**
 * Phase 4 (B, phase4.md §12.2): the blocks the player sees. With "Đọc suy nghĩ của nhân vật" off the
 * thought blocks are left out entirely (not blurred: not in the DOM at all); the stored text is
 * unchanged. The caret goes on the last block of this list, so a hidden thought still being written
 * keeps the caret on the narration or dialogue before it.
 */
export function visibleBlocks(blocks: StoryBlock[], showThoughts: boolean): StoryBlock[] {
  return showThoughts ? blocks : blocks.filter((b) => b.kind !== "thought");
}

/** A turn that has blocks but none left once thoughts are hidden ("Lượt này chỉ có suy nghĩ của …"). */
export function onlyHiddenThoughts(blocks: StoryBlock[], showThoughts: boolean): boolean {
  return !showThoughts && blocks.length > 0 && visibleBlocks(blocks, false).length === 0;
}

/** DM: a reply with no visible text, only a thought the player chose not to read. The thread shows the
 *  note "Lượt này chỉ có suy nghĩ của {tên}." instead of an empty "…" bubble that looks stuck. */
export function dmOnlyHiddenThought(
  visibleLines: number,
  thought: string | null | undefined,
  showThoughts: boolean,
): boolean {
  return !showThoughts && visibleLines === 0 && !!thought?.trim();
}

/** Plain text of a block (tests, accessibility labels). */
export function blockText(b: StoryBlock): string {
  return b.kind === "narration" ? b.parts.map((p) => p.text).join("") : b.text;
}
