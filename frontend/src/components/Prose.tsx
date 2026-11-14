import { Fragment } from "react";
import type { ReactNode } from "react";
import { playerStoryBlocks } from "../lib/playerBlocks";
import { buildStoryBlocks, speechText, visibleBlocks } from "../lib/storyBlocks";
import type { NarrationPart, StoryBlock } from "../lib/storyBlocks";
import { parseInline, spaceAfterHorn } from "../lib/text";
import type { ReplySegment } from "../lib/text";
import { ThoughtCard } from "../pages/chat/ThoughtCard";
import { cx } from "./ui";

/**
 * One line of text with dialogue in ink and *actions* in italics (DM bubbles, previews).
 * `inheritColor` keeps quotes in the surrounding colour (the player's gradient bubble).
 */
export function InlineText({ text, inheritColor = false }: { text: string; inheritColor?: boolean }) {
  return (
    <>
      {parseInline(spaceAfterHorn(text)).map((seg, i) => {
        if (seg.kind === "quote") {
          if (inheritColor) return <Fragment key={i}>{seg.text}</Fragment>;
          return (
            <span key={i} className="text-dialogue">
              {seg.text}
            </span>
          );
        }
        if (seg.kind === "action") {
          return (
            <em key={i} className="italic">
              {seg.text}
            </em>
          );
        }
        return <Fragment key={i}>{seg.text}</Fragment>;
      })}
    </>
  );
}

/** Text inside a chat bubble: keeps line breaks, highlights *actions* and dialogue. */
export function BubbleText({
  text,
  streaming = false,
  inheritColor = false,
}: {
  text: string;
  streaming?: boolean;
  inheritColor?: boolean;
}) {
  const lines = text.split(/\r?\n/);
  return (
    <div className={cx("whitespace-pre-wrap [overflow-wrap:anywhere]", streaming && "caret")}>
      {lines.map((l, i) => (
        <Fragment key={i}>
          {i > 0 && "\n"}
          <InlineText text={l} inheritColor={inheritColor} />
        </Fragment>
      ))}
    </div>
  );
}

/** *action* inside a spoken line stays italic; the asterisks go. */
function SpokenText({ text: raw }: { text: string }) {
  const text = spaceAfterHorn(raw);
  const out: ReactNode[] = [];
  const re = /\*([^*\n]+)\*/g;
  let last = 0;
  for (let m = re.exec(text); m; m = re.exec(text)) {
    if (m.index > last) out.push(text.slice(last, m.index));
    out.push(
      <em key={m.index} className="italic">
        {m[1]}
      </em>,
    );
    last = m.index + m[0].length;
  }
  if (last < text.length) out.push(text.slice(last));
  return <>{out}</>;
}

function NarrationText({ parts }: { parts: NarrationPart[] }) {
  return (
    <>
      {parts.map((p, i) =>
        p.kind === "quote" ? (
          <span key={i} className="not-italic text-dialogue">
            {spaceAfterHorn(p.text)}
          </span>
        ) : (
          <Fragment key={i}>{spaceAfterHorn(p.text)}</Fragment>
        ),
      )}
    </>
  );
}

/** One block of a Story Mode reply. */
export function StoryBlockView({ block, caret = false, streaming = false }: { block: StoryBlock; caret?: boolean; streaming?: boolean }) {
  if (block.kind === "thought") return <ThoughtCard text={block.text} streaming={streaming && caret} />;
  if (block.kind === "dialogue") {
    return (
      <p className="w-fit max-w-full rounded-card border border-edge bg-surface px-4 py-3 font-story text-[16px] font-medium text-dialogue [overflow-wrap:anywhere]">
        <span className={caret ? "caret" : undefined}>
          <SpokenText text={speechText(block.text)} />
        </span>
      </p>
    );
  }
  return (
    <p className={cx("font-story text-[16px] italic text-muted [overflow-wrap:anywhere]", caret && "caret")}>
      <NarrationText parts={block.parts} />
    </p>
  );
}

/**
 * A Story Mode reply in three kinds of blocks (DESIGN.md §6, layer 2): narration in muted italics
 * without a box, spoken lines of three words or more as cards, and the character's thoughts as
 * blurred cards where the model placed them. `streaming` puts the caret on the last block.
 *
 * `showThoughts` false (Phase 4, "Đọc suy nghĩ của nhân vật" off): thought cards are not rendered at
 * all, and the caret sits on the last block still shown.
 */
export function StoryReply({
  segments,
  streaming = false,
  showThoughts = true,
}: {
  segments: ReplySegment[];
  streaming?: boolean;
  showThoughts?: boolean;
}) {
  const blocks = visibleBlocks(buildStoryBlocks(segments), showThoughts);
  if (blocks.length === 0) return null;
  return (
    <div className="flex flex-col items-start gap-3">
      {blocks.map((b, i) => (
        <div key={i} className={b.kind === "narration" || b.kind === "thought" ? "w-full" : "max-w-full"}>
          <StoryBlockView block={b} caret={streaming && i === blocks.length - 1} streaming={streaming} />
        </div>
      ))}
    </div>
  );
}

/**
 * The player's own turn in Story Mode (Phase 3b): parsed like the character's turns, so quoted
 * speech reads as dialogue and *actions* / narration as italic narration (asterisks gone), one block
 * per paragraph. Marked as the player's: right-aligned, speech in the player's rose bubble. Rendering
 * only; the stored text is untouched.
 */
export function PlayerStoryTurn({ text, pending = false }: { text: string; pending?: boolean }) {
  const blocks = playerStoryBlocks(text);
  if (blocks.length === 0) return null;
  return (
    <div className={cx("flex min-w-0 flex-col items-end gap-2", pending && "opacity-70")}>
      {blocks.map((b, i) =>
        b.kind === "dialogue" ? (
          <p
            key={i}
            className="w-fit max-w-full rounded-card border border-user-border bg-user-gradient px-4 py-2.5 font-story text-[16px] font-medium text-user-fg [overflow-wrap:anywhere]"
          >
            <SpokenText text={speechText(b.text)} />
          </p>
        ) : b.kind === "narration" ? (
          // text-right: a paragraph that wraps keeps the turn's right edge, like its one-line neighbours.
          <p key={i} className="w-fit max-w-full text-right font-story text-[16px] italic text-muted [overflow-wrap:anywhere]">
            <NarrationText parts={b.parts} />
          </p>
        ) : null,
      )}
    </div>
  );
}
