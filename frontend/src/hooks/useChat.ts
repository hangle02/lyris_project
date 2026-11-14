import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError, errorMessage, errorTechnical, isAbortError, streams } from "../api/client";
import { refreshWallet } from "./useWallet";
import { friendlyError } from "../lib/friendlyError";
import { appendSegment, extractDirectives, joinSegments } from "../lib/text";
import type { ReplySegment } from "../lib/text";
import type { ChatStreamEvent, DeltaKind, Message, Mode, Rating } from "../types";

export type StreamKind = "send" | "reply" | "regenerate";

export interface StreamingState {
  kind: StreamKind;
  /** Turn being generated (from `start`, or the regenerated turn up front). */
  turnIndex: number | null;
  variantIndex: number | null;
  /** Mode of the story when the stream started (decides the rendering). */
  mode: Mode;
  text: string;
  thought: string;
  /** Story text and thoughts in the order they were streamed. */
  segments: ReplySegment[];
  lastKind: DeltaKind | null;
  /** Date.now() when the request was sent (for the elapsed-time hint while waiting). */
  startedAt: number;
  /** Phase 4b: every generation slot of the machine is busy (SSE `waiting`), until `start`. */
  waiting: boolean;
}

export interface ChatError {
  /** Plain words (Phase 3b: no "Ollama", no model names). */
  detail: string;
  /** What actually went wrong, for "Chi tiết". */
  technical?: string | null;
  retry: (() => void) | null;
}

type Starter = (onEvent: (ev: ChatStreamEvent) => void, signal: AbortSignal) => Promise<void>;

function byTurn(a: Message, b: Message): number {
  return a.turn_index - b.turn_index;
}

/** Replace the active message of the same turn (or append), keeping turn order. */
function upsertTurn(list: Message[], msg: Message): Message[] {
  const rest = list.filter((m) => m.turn_index !== msg.turn_index && m.id !== null);
  return [...rest, msg].sort(byTurn);
}

/** Resync delays after a Stop: the backend saves the partial reply as soon as it sees the disconnect. */
const ABORT_RESYNC_MS = [150, 800, 2000];

/** Local stand-in for the partial reply the backend saves on Stop, shown until the resync returns. */
function abortedPlaceholder(
  storyId: number,
  mode: Mode,
  turnIndex: number,
  variantIndex: number,
  text: string,
  thought: string,
  segments: ReplySegment[],
): Message {
  return {
    id: null,
    story_id: storyId,
    turn_index: turnIndex,
    variant_index: variantIndex,
    is_active: true,
    role: "assistant",
    mode,
    raw_content: joinSegments(segments),
    visible_content: text.trim(),
    thought: thought.trim() ? thought.trim() : null,
    directive: null,
    model_output: null,
    model_name: null,
    gen_stats: {
      ttft_ms: null,
      total_ms: null,
      prompt_tokens: null,
      output_tokens: null,
      tok_per_s: null,
      done_reason: null,
      aborted: true,
    },
    rating: null,
    variant_count: 1,
    created_at: null,
    edited_at: null,
  };
}

export function useChat(storyId: number | null, storyMode: Mode) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState<StreamingState | null>(null);
  const [error, setError] = useState<ChatError | null>(null);
  const [mutating, setMutating] = useState(false);

  const abortRef = useRef<AbortController | null>(null);
  const storyRef = useRef<number | null>(storyId);
  const modeRef = useRef<Mode>(storyMode);
  modeRef.current = storyMode;

  const reload = useCallback(async (id: number) => {
    const list = await api.listMessages(id);
    if (storyRef.current === id) setMessages([...list].sort(byTurn));
  }, []);

  // Load messages whenever the story changes; abort anything in flight for the old one.
  useEffect(() => {
    storyRef.current = storyId;
    abortRef.current?.abort();
    abortRef.current = null;
    setStreaming(null);
    setError(null);
    setMessages([]);
    if (storyId === null) return;
    let cancelled = false;
    setLoading(true);
    api
      .listMessages(storyId)
      .then((list) => {
        if (!cancelled) setMessages([...list].sort(byTurn));
      })
      .catch((e: unknown) => {
        if (!cancelled) setError({ detail: errorMessage(e), technical: errorTechnical(e), retry: () => void reload(storyId).then(() => setError(null)) });
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [storyId, reload]);

  // Abort the stream if the component unmounts.
  useEffect(() => () => abortRef.current?.abort(), []);

  /**
   * Runs one SSE generation. Returns true when the server accepted the request
   * (stream started), false when it was refused before streaming.
   */
  const runStream = useCallback(
    async (
      kind: StreamKind,
      starter: Starter,
      opts: { regenTurn?: number; retry: () => void; onRefused?: () => void },
    ): Promise<boolean> => {
      const id = storyRef.current;
      if (id === null || abortRef.current) return false;
      const ctrl = new AbortController();
      abortRef.current = ctrl;
      setError(null);
      const mode = modeRef.current;
      setStreaming({
        kind,
        turnIndex: opts.regenTurn ?? null,
        variantIndex: null,
        mode,
        text: "",
        thought: "",
        segments: [],
        lastKind: null,
        startedAt: Date.now(),
        waiting: false,
      });

      let accepted = false;
      let finished = false;
      // Local copy of what was streamed, to keep it on screen after a Stop.
      let turnIndex: number | null = opts.regenTurn ?? null;
      let variantIndex = 0;
      let streamedText = "";
      let streamedThought = "";
      let streamedSegments: ReplySegment[] = [];
      const isCurrent = () => storyRef.current === id && abortRef.current === ctrl;

      const onEvent = (ev: ChatStreamEvent) => {
        if (!isCurrent()) return;
        accepted = true;
        switch (ev.name) {
          case "user_message":
            setMessages((ms) => upsertTurn(ms, ev.data.message));
            break;
          case "waiting":
            setStreaming((s) => (s ? { ...s, waiting: true } : s));
            break;
          case "start":
            turnIndex = ev.data.turn_index;
            variantIndex = ev.data.variant_index;
            setStreaming((s) =>
              s ? { ...s, turnIndex: ev.data.turn_index, variantIndex: ev.data.variant_index, waiting: false } : s,
            );
            break;
          case "delta": {
            const { kind: dk, text } = ev.data;
            if (dk === "thought") streamedThought += text;
            else streamedText += text;
            streamedSegments = appendSegment(streamedSegments, dk, text);
            const segments = streamedSegments;
            setStreaming((s) =>
              s
                ? dk === "thought"
                  ? { ...s, thought: s.thought + text, segments, lastKind: "thought" }
                  : { ...s, text: s.text + text, segments, lastKind: "text" }
                : s,
            );
            break;
          }
          case "done":
            finished = true;
            setMessages((ms) => upsertTurn(ms, ev.data.message));
            setStreaming(null);
            break;
          case "error":
            finished = true;
            setStreaming(null);
            {
              const f = friendlyError(ev.data.detail || "Có lỗi khi sinh câu trả lời.", ev.data.technical);
              setError({ detail: f.text, technical: f.technical, retry: opts.retry });
            }
            break;
        }
      };

      try {
        await starter(onEvent, ctrl.signal);
        if (isCurrent() && !finished) {
          setStreaming(null);
          setError({ detail: "Luồng trả lời kết thúc bất ngờ.", retry: opts.retry });
          void reload(id).catch(() => undefined);
        }
      } catch (e) {
        if (storyRef.current !== id) return accepted;
        setStreaming(null);
        if (isAbortError(e) || ctrl.signal.aborted) {
          // Stopped by the user: the backend keeps the partial reply (gen_stats.aborted).
          // Keep the streamed text on screen (as a pending local message, so the
          // "awaiting reply" banner does not flash) until the server copy arrives.
          const hasPartial = turnIndex !== null && (streamedText.trim() !== "" || streamedThought.trim() !== "");
          setMessages((ms) => {
            const saved = ms.filter((m) => m.id !== null);
            if (!hasPartial || turnIndex === null) return saved;
            const placeholder = abortedPlaceholder(
              id,
              mode,
              turnIndex,
              variantIndex,
              streamedText,
              streamedThought,
              streamedSegments,
            );
            return [...saved.filter((m) => m.turn_index !== turnIndex), placeholder].sort(byTurn);
          });
          const expectTurn = hasPartial ? turnIndex : null;
          // On a regenerate the turn already holds the old variant: wait for the new one.
          const expectVariant = variantIndex;
          const resync = async (attempt: number): Promise<void> => {
            if (storyRef.current !== id) return;
            let list: Message[];
            try {
              list = await api.listMessages(id);
            } catch {
              list = [];
            }
            if (storyRef.current !== id) return;
            const savedPartial =
              expectTurn === null ||
              list.some(
                (m) => m.role === "assistant" && m.turn_index === expectTurn && m.variant_index === expectVariant,
              );
            if (!savedPartial && attempt + 1 < ABORT_RESYNC_MS.length) {
              window.setTimeout(() => void resync(attempt + 1), ABORT_RESYNC_MS[attempt + 1]);
              return;
            }
            if (list.length > 0 || savedPartial) setMessages([...list].sort(byTurn));
            else void reload(id).catch(() => undefined);
          };
          window.setTimeout(() => void resync(0), ABORT_RESYNC_MS[0]);
        } else if (!accepted && e instanceof ApiError && e.status !== 0) {
          // Refused before streaming (404/409/422, or 402 out of coins): nothing was saved.
          // F42: 402 `coins_required` (another tab spent the last coins): the shared wallet locks the composer.
          if (e.status === 402) refreshWallet();
          setMessages((ms) => ms.filter((m) => m.id !== null));
          opts.onRefused?.();
          setError({ detail: errorMessage(e), technical: errorTechnical(e), retry: kind === "send" ? null : opts.retry });
        } else {
          setError({ detail: errorMessage(e), technical: errorTechnical(e), retry: opts.retry });
          void reload(id).catch(() => undefined);
        }
      } finally {
        if (abortRef.current === ctrl) abortRef.current = null;
      }
      return accepted;
    },
    [reload],
  );

  const reply = useCallback((): void => {
    const id = storyRef.current;
    if (id === null) return;
    void runStream("reply", (onEvent, signal) => streams.reply(id, onEvent, signal), { retry: () => reply() });
  }, [runStream]);

  const regenerate = useCallback(
    (msg: Message): void => {
      if (msg.id === null) return;
      const mid = msg.id;
      void runStream("regenerate", (onEvent, signal) => streams.regenerate(mid, onEvent, signal), {
        regenTurn: msg.turn_index,
        retry: () => regenerate(msg),
      });
    },
    [runStream],
  );

  /** Sends a user turn. Resolves false if the server refused it (so the composer keeps the text). */
  const send = useCallback(
    async (content: string): Promise<boolean> => {
      const id = storyRef.current;
      if (id === null || abortRef.current) return false;
      const { visible, directive } = extractDirectives(content);
      let refused = false;
      setMessages((ms) => {
        const last = ms[ms.length - 1];
        const optimistic: Message = {
          id: null,
          story_id: id,
          turn_index: last ? last.turn_index + 1 : 0,
          variant_index: 0,
          is_active: true,
          role: "user",
          mode: modeRef.current,
          raw_content: content,
          visible_content: visible,
          thought: null,
          directive,
          model_output: null,
          model_name: null,
          gen_stats: null,
          rating: null,
          variant_count: 1,
          created_at: null,
          edited_at: null,
        };
        return [...ms, optimistic];
      });
      await runStream("send", (onEvent, signal) => streams.send(id, content, onEvent, signal), {
        retry: () => reply(),
        onRefused: () => {
          refused = true;
        },
      });
      return !refused;
    },
    [runStream, reply],
  );

  const stop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const mutate = useCallback(async <T,>(fn: () => Promise<T>): Promise<T | null> => {
    setMutating(true);
    setError(null);
    try {
      return await fn();
    } catch (e) {
      setError({ detail: errorMessage(e), technical: errorTechnical(e), retry: null });
      return null;
    } finally {
      setMutating(false);
    }
  }, []);

  const selectVariant = useCallback(
    async (msg: Message, variantIndex: number) => {
      if (msg.id === null) return;
      const mid = msg.id;
      const updated = await mutate(() => api.selectVariant(mid, variantIndex));
      if (updated && storyRef.current === msg.story_id) setMessages((ms) => upsertTurn(ms, updated));
    },
    [mutate],
  );

  const edit = useCallback(
    async (msg: Message, content: string): Promise<boolean> => {
      if (msg.id === null) return false;
      const mid = msg.id;
      const updated = await mutate(() => api.editMessage(mid, content));
      if (!updated) return false;
      if (storyRef.current === msg.story_id) setMessages((ms) => upsertTurn(ms, updated));
      return true;
    },
    [mutate],
  );

  const deleteFrom = useCallback(
    async (msg: Message) => {
      if (msg.id === null) return;
      const mid = msg.id;
      const res = await mutate(() => api.deleteFrom(mid));
      if (res && storyRef.current === msg.story_id) setMessages([...res.messages].sort(byTurn));
    },
    [mutate],
  );

  const feedback = useCallback(
    async (msg: Message, rating: Rating | null) => {
      if (msg.id === null) return;
      const mid = msg.id;
      // Optimistic toggle; the server copy wins.
      setMessages((ms) => ms.map((m) => (m.id === mid ? { ...m, rating } : m)));
      const updated = await mutate(() => api.setFeedback(mid, rating));
      if (storyRef.current !== msg.story_id) return;
      if (updated) setMessages((ms) => ms.map((m) => (m.id === mid ? updated : m)));
      else setMessages((ms) => ms.map((m) => (m.id === mid ? { ...m, rating: msg.rating } : m)));
    },
    [mutate],
  );

  const dismissError = useCallback(() => setError(null), []);

  return {
    messages,
    loading,
    streaming,
    error,
    mutating,
    send,
    reply,
    regenerate,
    stop,
    selectVariant,
    edit,
    deleteFrom,
    feedback,
    dismissError,
  };
}

export type ChatController = ReturnType<typeof useChat>;
