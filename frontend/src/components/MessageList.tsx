import { useContext, useEffect, useLayoutEffect, useMemo, useRef } from "react";
import type { StreamingState } from "../hooks/useChat";
import { buildStoryBlocks, visibleBlocks } from "../lib/storyBlocks";
import type { ReplySegment } from "../lib/text";
import { buildRows, dmReceipt } from "../lib/threadRows";
import { waitingLine } from "../pages/chat/chatLogic";
import { turnDomId } from "../pages/chat/eventsLogic";
import type { Message, Mode } from "../types";
import { DmThread, bubbleLines } from "./DmThread";
import { IconMessageCircle } from "./icons";
import { LiveStatus } from "./LiveStatus";
import { MessageItem } from "./MessageItem";
import type { MessageActions } from "./MessageItem";
import { StoryReply } from "./Prose";
import { ShowThoughtsContext } from "./showThoughts";
import { TypingDots } from "./TypingDots";
import { Chip, EmptyState, Skeleton } from "./ui";

interface Props extends MessageActions {
  storyId: number | null;
  /** Which view to show: the story as prose, or the DM thread. */
  view: Mode;
  messages: Message[];
  streaming: StreamingState | null;
  loading: boolean;
  disabled: boolean;
  characterName: string;
  /** Space above the first message for a header that floats over the list (px). */
  topInset?: number;
  /**
   * Scroll to this turn, highlight it briefly and move focus to it (the "Sự kiện" timeline). A new
   * `nonce` asks again for the same turn. Waits until the turn is rendered (e.g. after a mode switch).
   */
  jumpTo?: { turn: number; nonce: number } | null;
}

/**
 * Before the first word: three bouncing dots in the character's column (Phase 3b; no "đang ngập
 * ngừng..." line, no timer). Screen readers hear "{Tên} đang trả lời" through the list's LiveStatus.
 */
function StoryWaiting({ queuedFor }: { queuedFor: string | null }) {
  return (
    <div className="flex flex-col items-start gap-2">
      <span className="inline-flex h-10 items-center rounded-full border border-edge bg-surface px-4 text-[13px] text-muted">
        <TypingDots />
      </span>
      {/* Phase 4b: someone else holds the machine; a small line under the dots (docs/auth.md §5.5). */}
      {queuedFor !== null && <p className="text-[13px] leading-snug text-muted">{waitingLine(queuedFor)}</p>}
    </div>
  );
}

/** Nothing the player can see yet: no text, or (thoughts hidden) only a thought so far. */
function nothingShown(segments: ReplySegment[], showThoughts: boolean): boolean {
  return segments.length === 0 || visibleBlocks(buildStoryBlocks(segments), showThoughts).length === 0;
}

function StreamingStory({ s, characterName }: { s: StreamingState; characterName: string }) {
  const showThoughts = useContext(ShowThoughtsContext);
  // A reply that opens with a hidden thought keeps the three dots until narration or speech arrives.
  if (nothingShown(s.segments, showThoughts)) return <StoryWaiting queuedFor={s.waiting ? characterName : null} />;
  return (
    <div aria-live="polite" aria-busy="true">
      <StoryReply segments={s.segments} streaming showThoughts={showThoughts} />
    </div>
  );
}

/** The story while its turns load: the real layout with flat bars, no shimmer. */
function StorySkeleton() {
  return (
    <div className="flex flex-col gap-7" aria-busy="true">
      <span className="sr-only">Đang tải story…</span>
      <div className="flex flex-col gap-3">
        <Skeleton shape="text" lines={3} height={14} />
        <Skeleton shape="card" width="72%" height={52} />
        <Skeleton shape="text" lines={2} height={14} />
      </div>
      <Skeleton shape="card" width="56%" height={48} className="self-end" />
      <div className="flex flex-col gap-3">
        <Skeleton shape="text" lines={2} height={14} />
        <Skeleton shape="card" width="64%" height={52} />
      </div>
    </div>
  );
}

function DmSkeleton() {
  return (
    <div className="flex flex-col gap-3 pt-24" aria-busy="true">
      <span className="sr-only">Đang tải tin nhắn…</span>
      <Skeleton shape="pill" width="58%" height={40} />
      <Skeleton shape="pill" width="44%" height={40} className="self-end" />
      <Skeleton shape="pill" width="66%" height={40} />
      <Skeleton shape="pill" width="38%" height={40} className="self-end" />
    </div>
  );
}

const STICK_THRESHOLD = 96;
/** A timeline jump waits this long for its turn to render (a mode switch, the list loading). */
const JUMP_WAIT_MS = 4000;

export function MessageList({
  storyId,
  view,
  messages,
  streaming,
  loading,
  disabled,
  characterName,
  topInset = 0,
  jumpTo = null,
  ...actions
}: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const stick = useRef(true);
  const showThoughts = useContext(ShowThoughtsContext);

  const onScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    stick.current = el.scrollHeight - el.scrollTop - el.clientHeight < STICK_THRESHOLD;
  };

  // New story or switched view: jump to the bottom. A layout effect declared before the
  // follow effect, so the reset happens in the same pass as the scroll.
  useLayoutEffect(() => {
    stick.current = true;
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [storyId, view]);

  // Follow new content while the reader is at the bottom (also when the header above changes height).
  useLayoutEffect(() => {
    const el = scrollRef.current;
    if (el && stick.current) el.scrollTop = el.scrollHeight;
  }, [messages, streaming, loading, view, topInset]);

  // The list's own box shrinks when something appears below it (a notice above the composer, the
  // quick replies, the phone keyboard): keep the newest turn in view if the reader was at the bottom.
  useLayoutEffect(() => {
    const el = scrollRef.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(() => {
      if (stick.current) el.scrollTop = el.scrollHeight;
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // When a new stream starts, always bring it into view.
  const streamActive = streaming !== null;
  useLayoutEffect(() => {
    if (!streamActive) return;
    stick.current = true;
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [streamActive]);

  // While a turn is being (re)generated, hide its old content and anything after it.
  const hideFrom = streaming?.turnIndex ?? null;
  const rows = useMemo(() => {
    const shown = hideFrom === null ? messages : messages.filter((m) => m.turn_index < hideFrom);
    return buildRows(messages, shown, view);
  }, [messages, hideFrom, view]);
  // Jump to a turn from the timeline: once it is rendered, scroll it to the middle, outline it for a
  // moment and give it focus (after the closing sheet has returned focus to its opener).
  const handledJump = useRef<number | null>(null);
  const jumpTimers = useRef<number[]>([]);
  /** When the pending jump was first seen: one that waits too long is given up. */
  const jumpSeen = useRef<{ nonce: number; at: number } | null>(null);
  // Runs after every render until the asked turn exists; timers live in a ref so later renders
  // (streaming, polling) do not cut the highlight short.
  useLayoutEffect(() => {
    if (!jumpTo || handledJump.current === jumpTo.nonce) return;
    const now = Date.now();
    if (jumpSeen.current?.nonce !== jumpTo.nonce) jumpSeen.current = { nonce: jumpTo.nonce, at: now };
    else if (now - jumpSeen.current.at > JUMP_WAIT_MS) {
      // Never rendered in time (e.g. the mode switch did not happen): drop it, so it cannot take over
      // the scroll and focus much later.
      handledJump.current = jumpTo.nonce;
      return;
    }
    const root = scrollRef.current;
    const el = root?.querySelector<HTMLElement>(`#${turnDomId(jumpTo.turn)}`) ?? null;
    if (!root || !el) return; // not rendered yet (other view, still loading): try again on the next render
    handledJump.current = jumpTo.nonce;
    stick.current = false;
    for (const t of jumpTimers.current) window.clearTimeout(t);
    root.querySelectorAll(".turn-highlight").forEach((n) => n.classList.remove("turn-highlight"));
    const reduce = typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    // A turn taller than the visible area starts at its top (below the glass header, through
    // scroll-padding-top); centring it would hide its first lines.
    const room = root.clientHeight - topInset;
    const block = el.offsetHeight > room * 0.9 ? "start" : "center";
    el.scrollIntoView({ block, behavior: reduce ? "auto" : "smooth" });
    el.classList.add("turn-highlight");
    jumpTimers.current = [
      window.setTimeout(() => el.focus({ preventScroll: true }), 80),
      window.setTimeout(() => el.classList.remove("turn-highlight"), 2400),
    ];
  });
  useEffect(
    () => () => {
      for (const t of jumpTimers.current) window.clearTimeout(t);
    },
    [],
  );

  // A stream started in the other view (should not happen: the mode toggle is locked while busy).
  const viewStreaming = streaming && streaming.mode === view ? streaming : null;
  const receipt = useMemo(
    () => (view === "dm" ? dmReceipt(messages, view, viewStreaming !== null) : null),
    [messages, view, viewStreaming],
  );
  const firstLoad = loading && messages.length === 0;
  // Nothing written yet (the dots show): said once to screen readers, from a region that stays mounted.
  const typing =
    viewStreaming !== null &&
    (view === "dm" ? bubbleLines(viewStreaming.text).length === 0 : nothingShown(viewStreaming.segments, showThoughts));

  return (
    <div
      ref={scrollRef}
      onScroll={onScroll}
      style={{ paddingTop: topInset, scrollPaddingTop: topInset }}
      className="scroll-thin min-h-0 flex-1 overflow-y-auto overscroll-contain"
    >
      <LiveStatus
        text={
          typing
            ? viewStreaming?.waiting
              ? waitingLine(characterName)
              : `${characterName.trim() || "Nhân vật"} đang trả lời`
            : ""
        }
      />
      {view === "dm" ? (
        <div className="mx-auto w-full max-w-[720px] px-4 pt-6 pb-6">
          {firstLoad ? (
            <DmSkeleton />
          ) : (
            <DmThread
              rows={rows}
              streaming={viewStreaming}
              disabled={disabled}
              characterName={characterName}
              receipt={receipt}
              {...actions}
            />
          )}
        </div>
      ) : (
        <div className="mx-auto flex w-full max-w-[720px] flex-col gap-7 px-4 pt-6 pb-8">
          {firstLoad && <StorySkeleton />}
          {!loading && !rows.some((r) => r.type === "msg") && !viewStreaming && storyId !== null && (
            <EmptyState text={`Chưa có lượt nào. Hãy viết lượt đầu tiên cho story với ${characterName}.`} />
          )}
          {rows.map((row) =>
            row.type === "other" ? (
              <div key={row.key} className="self-center">
                <Chip size="sm" icon={<IconMessageCircle />}>
                  {row.count} tin nhắn riêng
                </Chip>
              </div>
            ) : (
              <MessageItem
                key={row.m.id ?? `pending-${row.m.turn_index}`}
                message={row.m}
                characterName={characterName}
                isLastAssistant={row.isLastAssistant}
                canRegenerate={row.canRegenerate}
                hiddenAfter={row.hiddenAfter}
                disabled={disabled}
                {...actions}
              />
            ),
          )}
          {viewStreaming && <StreamingStory s={viewStreaming} characterName={characterName} />}
        </div>
      )}
    </div>
  );
}
