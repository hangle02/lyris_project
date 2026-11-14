// Story Mode: the player's own turn in story format (Phase 3b, phase3.md §10). Rendering only: the
// stored text never changes.
//
// The player writes like the character does: "quoted speech", *actions* and plain narration, one
// paragraph per line. The same parser as the character's turns (storyBlocks.paragraphBlocks) turns
// it into blocks: every "quote" becomes a dialogue block (even a one-word “Ừ.”), a quote inside
// asterisks (*"…"*: a citation, or someone else's words) stays inline in the narration, *actions* and narration become narration blocks without the asterisks. A turn has
// no thoughts. Pure, no React; tested in playerBlocks.test.ts.
import { paragraphBlocks } from "./storyBlocks.ts";
import type { StoryBlock } from "./storyBlocks.ts";
import { splitParagraphs } from "./text.ts";

/** Markdown bold ("**ôm chặt**") reads as an action, like "*ôm chặt*". */
function normaliseEmphasis(paragraph: string): string {
  return paragraph.replace(/\*\*([^*\n]+?)\*\*/g, "*$1*");
}

/**
 * A paragraph the parser drops (no letters or digits: "...", "😳", "?!", "*...*") still belongs to
 * the player's turn: keep it as one narration line, without wrapping asterisks.
 */
function fallbackBlock(paragraph: string): StoryBlock | null {
  const text = paragraph.trim();
  if (!text) return null;
  const inner = /^\*+([^*]+)\*+$/.exec(text)?.[1]?.trim();
  if (inner) return { kind: "narration", parts: [{ kind: "action", text: inner }] };
  return { kind: "narration", parts: [{ kind: "plain", text }] };
}

/** The visible text of a player's turn (directives already removed) as ordered story blocks. */
export function playerStoryBlocks(visible: string): StoryBlock[] {
  const out: StoryBlock[] = [];
  for (const raw of splitParagraphs(visible)) {
    const para = normaliseEmphasis(raw);
    // Everything the player puts in "…" is their speech, however short; *"…"* is a citation.
    const blocks = paragraphBlocks(para, 1);
    if (blocks.length > 0) {
      out.push(...blocks);
    } else {
      const block = fallbackBlock(para);
      if (block) out.push(block);
    }
  }
  return out;
}
