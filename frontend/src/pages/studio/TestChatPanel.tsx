import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import { friendlyOf, isAbortError, streamTestChat } from "../../api/client";
import { useAdvancedTools } from "../../hooks/useAdvancedTools";
import { friendlyError } from "../../lib/friendlyError";
import type { FriendlyError } from "../../lib/friendlyError";
import { AutoTextarea } from "../../components/AutoTextarea";
import { Avatar } from "../../components/Avatar";
import { LiveStatus } from "../../components/LiveStatus";
import { InlineText, StoryReply } from "../../components/Prose";
import { TypingDots } from "../../components/TypingDots";
import { IconRefreshCw, IconSend, IconStop, IconTrash } from "../../components/icons";
import { Button, CONTROL_CLASS, IconButton, cx } from "../../components/ui";
import { fillPlaceholders } from "../../lib/cardForm";
import { MAX_CONTENT_CHARS, appendSegment, extractDirectives, joinSegments, splitSegments } from "../../lib/text";
import type { ReplySegment } from "../../lib/text";
import type { CharacterCard, GenStats, Mode, Persona, StorySettings, TestChatTurn } from "../../types";
import { waitingLine } from "../chat/chatLogic";
import { Notice } from "./ui";

interface Streaming {
  segments: ReplySegment[];
  startedAt: number;
  /** Phase 4b: every generation slot is busy (SSE `waiting`) until the reply starts. */
  waiting?: boolean;
}

function lines(text: string): string[] {
  return text
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean);
}

function PlayerTurn({ content, mode }: { content: string; mode: Mode }) {
  const { visible, directive } = extractDirectives(content);
  return (
    <div className="flex flex-col items-end gap-1.5">
      {visible && (
        <div
          className={cx(
            "max-w-[85%] border border-user-border bg-user-gradient px-4 py-2.5 text-[15px] leading-relaxed whitespace-pre-wrap text-user-fg [overflow-wrap:anywhere]",
            mode === "dm" ? "rounded-[20px]" : "rounded-card rounded-br-md",
          )}
        >
          {visible}
        </div>
      )}
      {directive && (
        <span className="inline-flex max-w-[85%] items-start gap-1 rounded-full bg-surface-2 px-3 py-1 text-[13px] leading-snug text-muted">
          <span className="sr-only">Chỉ đạo: </span>
          <span className="italic [overflow-wrap:anywhere]">(({directive}))</span>
        </span>
      )}
    </div>
  );
}

/** Before the first word: three bouncing dots, as in the chat (Phase 3b); the busy line when queued (4b). */
function Waiting({ queuedFor = null }: { queuedFor?: string | null }) {
  return (
    <span className="flex flex-col items-start gap-2">
      <span className="inline-flex h-10 items-center rounded-full bg-surface-2 px-4 text-[13px] text-muted">
        <TypingDots />
      </span>
      {queuedFor !== null && <span className="text-[13px] leading-snug text-muted">{waitingLine(queuedFor)}</span>}
    </span>
  );
}

function CharacterTurn({
  segments,
  mode,
  name,
  avatarUrl,
  streaming = null,
  waiting = false,
}: {
  segments: ReplySegment[];
  mode: Mode;
  name: string;
  avatarUrl: string | null;
  /** When this is the reply being written: when it started. */
  streaming?: number | null;
  waiting?: boolean;
}) {
  const live = streaming !== null;
  const queuedFor = waiting ? name : null;
  if (segments.length === 0 && live) return <Waiting queuedFor={queuedFor} />;
  if (mode === "story") return <StoryReply segments={segments} streaming={live} />;
  const text = segments
    .filter((s) => s.kind === "text")
    .map((s) => s.text)
    .join("\n");
  const bubbles = lines(text);
  if (bubbles.length === 0 && live) return <Waiting queuedFor={queuedFor} />;
  return (
    <div className="flex items-end gap-2">
      <Avatar name={name || "?"} url={avatarUrl} size={28} />
      <div className="flex max-w-[80%] min-w-0 flex-col items-start gap-1">
        {bubbles.map((b, i) => (
          <div
            key={i}
            className={cx(
              "w-fit max-w-full rounded-[20px] bg-surface-2 px-4 py-2 text-[15px] leading-snug text-fg [overflow-wrap:anywhere]",
              live && i === bubbles.length - 1 && "caret",
            )}
          >
            <InlineText text={b} />
          </div>
        ))}
      </div>
    </div>
  );
}

function statsLine(s: GenStats | null): string | null {
  if (!s) return null;
  const parts: string[] = [];
  if (s.ttft_ms != null) parts.push(`chữ đầu ${(s.ttft_ms / 1000).toFixed(1)} giây`);
  if (s.total_ms != null) parts.push(`tổng ${(s.total_ms / 1000).toFixed(1)} giây`);
  if (s.tok_per_s != null) parts.push(`${s.tok_per_s.toFixed(1)} token/giây`);
  if (s.done_reason === "length") parts.push("bị cắt vì quá dài");
  return parts.length ? parts.join(" · ") : null;
}

/**
 * "Chat thử": a throwaway conversation with the card being edited (saved or not). Starts from the
 * greeting, streams like the real chat (Thought shown in place), nothing is stored on the server.
 */
export function TestChatPanel({
  card,
  avatarUrl,
  persona,
  settings,
  blockers,
}: {
  card: CharacterCard;
  avatarUrl: string | null;
  persona: Persona | null;
  settings: StorySettings | null;
  blockers: string[];
}) {
  /** null = fresh: the conversation is just the (current) greeting. */
  const [turns, setTurns] = useState<TestChatTurn[] | null>(null);
  const [streaming, setStreaming] = useState<Streaming | null>(null);
  const [error, setError] = useState<FriendlyError | null>(null);
  const [stats, setStats] = useState<GenStats | null>(null);
  const [text, setText] = useState("");
  const abortRef = useRef<AbortController | null>(null);
  const segRef = useRef<ReplySegment[]>([]);
  const scroller = useRef<HTMLDivElement>(null);
  const stick = useRef(true);

  const mode: Mode = settings?.mode ?? "story";
  const charName = card.name.trim();
  const playerName = persona?.name ?? "";

  const greetingTurns = useMemo<TestChatTurn[]>(() => {
    const g = fillPlaceholders(card.greeting, charName, playerName);
    return g ? [{ role: "assistant", content: g }] : [];
  }, [card.greeting, charName, playerName]);

  const shown = turns ?? greetingTurns;
  const ready = !!persona && persona.id !== null && !!settings && blockers.length === 0;
  const busy = streaming !== null;

  useEffect(() => () => abortRef.current?.abort(), []);

  // Keep the view pinned to the bottom while the user has not scrolled up.
  const onScroll = () => {
    const el = scroller.current;
    if (!el) return;
    stick.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
  };
  useLayoutEffect(() => {
    const el = scroller.current;
    if (el && stick.current) el.scrollTop = el.scrollHeight;
  }, [shown, streaming, error]);

  const run = useCallback(
    async (history: TestChatTurn[]) => {
      if (!persona || persona.id === null || !settings) return;
      abortRef.current?.abort();
      const ctrl = new AbortController();
      abortRef.current = ctrl;
      segRef.current = [];
      stick.current = true;
      setError(null);
      setStats(null);
      setStreaming({ segments: [], startedAt: Date.now() });
      let finished = false;
      try {
        await streamTestChat(
          { card, persona_id: persona.id, settings, messages: history },
          (ev) => {
            if (ctrl.signal.aborted) return;
            if (ev.name === "waiting") {
              setStreaming((s) => (s ? { ...s, waiting: true } : s));
            } else if (ev.name === "start") {
              setStreaming((s) => (s ? { ...s, waiting: false } : s));
            } else if (ev.name === "delta") {
              segRef.current = appendSegment(segRef.current, ev.data.kind, ev.data.text);
              setStreaming((s) => (s ? { ...s, segments: segRef.current } : s));
            } else if (ev.name === "done") {
              finished = true;
              const raw = ev.data.raw.trim() || joinSegments(segRef.current);
              if (raw) setTurns([...history, { role: "assistant", content: raw }]);
              setStats(ev.data.stats);
            } else if (ev.name === "error") {
              finished = true;
              setError(friendlyError(ev.data.detail || "Có lỗi khi viết câu trả lời.", ev.data.technical));
            }
          },
          ctrl.signal,
        );
        if (!finished && !ctrl.signal.aborted) setError({ text: "Luồng trả lời kết thúc giữa chừng. Hãy thử lại.", technical: null });
      } catch (e) {
        if (isAbortError(e) || ctrl.signal.aborted) {
          // Stopped by the user: keep what was written so far, like the real chat.
          const partial = joinSegments(segRef.current);
          if (partial && abortRef.current === ctrl) setTurns([...history, { role: "assistant", content: partial }]);
        } else {
          setError(friendlyOf(e));
        }
      } finally {
        if (abortRef.current === ctrl) {
          abortRef.current = null;
          setStreaming(null);
        }
      }
    },
    [card, persona, settings],
  );

  const send = () => {
    const content = text.trim();
    if (!content || busy || !ready) return;
    if (content.length > MAX_CONTENT_CHARS) {
      setError({ text: "Tin nhắn quá dài (tối đa 20.000 ký tự).", technical: null });
      return;
    }
    const history: TestChatTurn[] = [...shown, { role: "user", content }];
    setTurns(history);
    setText("");
    void run(history);
  };

  const stop = () => {
    // Leave abortRef set so the catch branch keeps the partial reply.
    abortRef.current?.abort();
  };

  const last = shown[shown.length - 1];
  const hasUserTurn = shown.some((t) => t.role === "user");
  const canRegenerate = !busy && ready && hasUserTurn && last?.role === "assistant";
  const canRetry = !busy && ready && last?.role === "user";

  const regenerate = () => {
    if (!canRegenerate) return;
    const history = shown.slice(0, -1);
    setTurns(history);
    void run(history);
  };

  const reset = () => {
    abortRef.current?.abort();
    abortRef.current = null;
    setStreaming(null);
    setTurns(null);
    setError(null);
    setStats(null);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing && e.keyCode !== 229) {
      e.preventDefault();
      send();
    }
  };

  // Generation stats (seconds, tokens per second) only with the advanced tools on (Phase 3b).
  const [advanced] = useAdvancedTools();
  const stat = advanced ? statsLine(stats) : null;
  // Nothing written yet (the dots show): said to screen readers from a region that stays mounted.
  const typing =
    streaming !== null &&
    (mode === "story"
      ? streaming.segments.length === 0
      : lines(
          streaming.segments
            .filter((s) => s.kind === "text")
            .map((s) => s.text)
            .join("\n"),
        ).length === 0);

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div ref={scroller} onScroll={onScroll} className="scroll-thin min-h-0 flex-1 overflow-y-auto px-1 pb-4">
        <LiveStatus text={typing ? `${charName || "Nhân vật"} đang trả lời` : ""} />
        {blockers.length > 0 && (
          <div className="mb-4">
            <Notice tone="warn" title="Sửa form trước khi chat thử:" lines={blockers} />
          </div>
        )}
        {shown.length === 0 && !busy && (
          <p className="py-6 text-[15px] leading-relaxed text-muted">
            Card chưa có lời mở đầu. Gửi tin đầu tiên để bắt đầu cuộc thử.
          </p>
        )}
        <div className="flex flex-col gap-6 pt-1">
          {shown.map((t, i) =>
            t.role === "user" ? (
              <PlayerTurn key={i} content={t.content} mode={mode} />
            ) : (
              <CharacterTurn key={i} segments={splitSegments(t.content)} mode={mode} name={charName} avatarUrl={avatarUrl} />
            ),
          )}
          {streaming && (
            <CharacterTurn
              segments={streaming.segments}
              mode={mode}
              name={charName}
              avatarUrl={avatarUrl}
              streaming={streaming.startedAt}
              waiting={streaming.waiting}
            />
          )}
        </div>
        {error && (
          <div className="mt-5">
            <Notice
              tone="error"
              lines={[error.text]}
              technical={error.technical}
              onDismiss={() => setError(null)}
              action={
                canRetry ? (
                  <Button size="sm" onClick={() => void run(shown)}>
                    Thử lại
                  </Button>
                ) : undefined
              }
            />
          </div>
        )}
        {stat && !busy && <p className="mt-4 text-[12px] text-muted tabular-nums">{stat}</p>}
      </div>

      <div className="shrink-0 border-t border-line pt-2">
        <div className="mb-2 flex items-center gap-1">
          <Button variant="ghost" size="sm" icon={<IconRefreshCw />} onClick={regenerate} disabled={!canRegenerate} className="-ml-2">
            Làm lại
          </Button>
          <Button variant="ghost" size="sm" icon={<IconTrash />} onClick={reset} disabled={turns === null && !busy && !error}>
            Xoá cuộc thử
          </Button>
          <span className="ml-auto text-[12px] text-muted">Không lưu gì</span>
        </div>
        <div className="flex items-end gap-2">
          <AutoTextarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={onKeyDown}
            maxHeight={180}
            disabled={!ready}
            aria-label="Tin nhắn chat thử"
            placeholder={
              !persona
                ? "Chọn persona để chat thử…"
                : mode === "dm"
                  ? `Nhắn tin cho ${charName || "nhân vật"}…`
                  : 'Nhập lời thoại vào "…", *hành động*, ((chỉ đạo))'
            }
            className={cx(CONTROL_CLASS, "flex-1")}
          />
          {busy ? (
            <IconButton label="Dừng" icon={<IconStop />} variant="secondary" onClick={stop} />
          ) : (
            <IconButton label="Gửi (Enter)" icon={<IconSend />} variant="orb" onClick={send} disabled={!ready || !text.trim()} />
          )}
        </div>
      </div>
    </div>
  );
}
