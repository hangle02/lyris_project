// Quick replies on demand and the composer's "+" menu (Phase 3b, phase3.md §10). Suggestions are
// written only when the player taps "Nhận gợi ý", never automatically. Pure, no React; tested in
// suggestLogic.test.ts.
import type { FriendlyError } from "../../lib/friendlyError.ts";
import type { Message, Mode } from "../../types.ts";

/** Most quick replies shown above the composer. */
export const MAX_SUGGESTIONS = 3;

// ---- can the player ask now? ----

export interface Availability {
  enabled: boolean;
  /** Why not, in plain words (shown under the menu item); null when enabled. */
  reason: string | null;
}

/**
 * "Nhận gợi ý" needs a character reply to answer: not while a reply streams or a message action
 * runs, not while suggestions are being written, not when the newest message is the player's (the
 * server would refuse with 409) and not before the story has any turn.
 */
export function suggestAvailability(opts: {
  messages: readonly (Pick<Message, "role" | "is_active"> & Partial<Pick<Message, "mode">>)[];
  /** A reply is streaming or a message action is running. */
  busy: boolean;
  /** The story or its turns are still loading. */
  loading: boolean;
  /** Suggestions are being written right now. */
  generating: boolean;
  /** The machine cannot answer (health "down"): asking would only fail. */
  offline?: boolean;
  /** The view on screen: the server writes suggestions in the mode of the reply they answer, so a
   *  reply of the other mode cannot be answered from here. */
  view?: Mode;
}): Availability {
  if (opts.loading) return { enabled: false, reason: "Đang tải story…" };
  if (opts.offline) return { enabled: false, reason: "Nhân vật tạm thời chưa trả lời được." };
  if (opts.generating) return { enabled: false, reason: "Đang nghĩ gợi ý…" };
  if (opts.busy) return { enabled: false, reason: "Đợi nhân vật trả lời xong đã." };
  const active = opts.messages.filter((m) => m.is_active !== false);
  const last = active[active.length - 1];
  if (!last) return { enabled: false, reason: "Story chưa có lượt nào để gợi ý." };
  if (last.role === "user") return { enabled: false, reason: "Lượt của bạn chưa có câu trả lời, nên chưa có gì để gợi ý." };
  if (opts.view && last.mode && last.mode !== opts.view) {
    const other = last.mode === "dm" ? "DM" : "Story";
    return { enabled: false, reason: `Nhân vật vừa trả lời bên ${other}. Mở ${other} để nhận gợi ý.` };
  }
  return { enabled: true, reason: null };
}

/**
 * The reply the suggestions answer: the newest active message when it is the character's, as a key
 * (id, variant, edit time) and its mode; null when the newest message is the player's or there is
 * none. Suggestions asked for one reply never show once this changes (reply deleted, edited or
 * swapped for another variant).
 */
export function replyAnchor(
  messages: readonly Pick<Message, "id" | "role" | "mode" | "is_active" | "variant_index" | "edited_at">[],
): { key: string; mode: Mode } | null {
  for (let i = messages.length - 1; i >= 0; i--) {
    const m = messages[i];
    if (!m || m.is_active === false) continue;
    if (m.role !== "assistant" || m.id === null) return null;
    return { key: `${m.id}:${m.variant_index}:${m.edited_at ?? ""}`, mode: m.mode };
  }
  return null;
}

// ---- the "+" menu ----

export type ComposerActionId = "suggest" | "image" | "events";

export interface ComposerAction {
  id: ComposerActionId;
  label: string;
  /** Small line under the label: why it is disabled, or what it does. */
  hint: string | null;
  disabled: boolean;
  /** Not built yet: shows a "Sắp có" badge. */
  soon: boolean;
}

/** The menu, in order. Data, so more actions can join later without touching the menu itself. */
export function composerActions(opts: { suggest: Availability }): ComposerAction[] {
  return [
    {
      id: "suggest",
      label: "Nhận gợi ý",
      hint: opts.suggest.enabled ? "Ba cách trả lời cho lượt tiếp theo." : opts.suggest.reason,
      disabled: !opts.suggest.enabled,
      soon: false,
    },
    {
      id: "events",
      label: "Xem sự kiện",
      hint: "Những gì đã xảy ra trong story.",
      disabled: false,
      soon: false,
    },
    {
      id: "image",
      label: "Gửi hình ảnh",
      hint: "Sắp tới bạn sẽ gửi được ảnh cho nhân vật xem.",
      disabled: true,
      soon: true,
    },
  ];
}

/** Index of the next enabled item when moving with the arrow keys (wraps); -1 when none is enabled. */
export function nextEnabledIndex(items: readonly { disabled: boolean }[], from: number, step: 1 | -1): number {
  const n = items.length;
  for (let k = 1; k <= n; k++) {
    const i = (((from + step * k) % n) + n) % n;
    if (!items[i]?.disabled) return i;
  }
  return -1;
}

// ---- the suggestion area ----

export type SuggestStatus = "idle" | "loading" | "error";

export interface SuggestState {
  status: SuggestStatus;
  /** Items from the last request (null: none asked in this turn, the server's extras apply). */
  items: string[] | null;
  /** Mode of the reply the items answer (they hide in the other view). */
  mode: Mode | null;
  /** replyAnchor key of the reply the items answer (null when unknown). */
  anchor: string | null;
  error: FriendlyError | null;
  /** The items the player closed (their key); they stay hidden until different ones arrive. */
  dismissed: string | null;
  /** Id of the newest request (from the caller): a late answer of an older one, or one that comes
   *  after a dismiss or reset (status no longer "loading"), is ignored. */
  request: number;
}

export const INITIAL_SUGGEST: SuggestState = {
  status: "idle",
  items: null,
  mode: null,
  anchor: null,
  error: null,
  dismissed: null,
  request: 0,
};

export type SuggestAction =
  | { type: "request"; mode: Mode; request: number; anchor?: string | null }
  | { type: "success"; request: number; items: readonly string[] }
  | { type: "failure"; request: number; error: FriendlyError }
  | { type: "dismiss"; key: string }
  | { type: "reset" };

/** Trimmed, de-duplicated, at most three. */
export function cleanSuggestions(items: readonly unknown[]): string[] {
  const out: string[] = [];
  for (const raw of items) {
    if (typeof raw !== "string") continue;
    const t = raw.replace(/\s+/g, " ").trim();
    if (t && !out.includes(t)) out.push(t);
    if (out.length >= MAX_SUGGESTIONS) break;
  }
  return out;
}

export function suggestionsKey(items: readonly string[]): string {
  return items.join("\n");
}

export function suggestReducer(state: SuggestState, action: SuggestAction): SuggestState {
  switch (action.type) {
    case "request":
      return {
        ...state,
        status: "loading",
        error: null,
        dismissed: null,
        mode: action.mode,
        anchor: action.anchor ?? null,
        request: action.request,
      };
    case "success":
      if (action.request !== state.request || state.status !== "loading") return state;
      return { ...state, status: "idle", items: cleanSuggestions(action.items), error: null };
    case "failure":
      if (action.request !== state.request || state.status !== "loading") return state;
      return { ...state, status: "error", error: action.error };
    case "dismiss":
      // Closing while loading cancels the request (its answer is ignored).
      return {
        ...state,
        status: "idle",
        error: null,
        dismissed: action.key,
        // Cancelled while loading: show nothing (not the replies asked for before "Gợi ý khác").
        items: state.status === "loading" ? [] : state.items,
      };
    case "reset":
      return { ...INITIAL_SUGGEST, request: state.request };
  }
}

/**
 * What the suggestion area shows: "loading" (typing dots), "error", "items", or nothing.
 * Items are the last request's answer, else the ones the server kept from an earlier request
 * (`stored`, with the mode of the reply they answer). Hidden while a reply is generated, after the
 * player closed them, and in the other view. With `anchor` (replyAnchor key of the newest reply,
 * null when the newest message is not a reply), items and errors only show for the reply they were
 * asked for, and nothing shows when there is no reply to answer.
 */
export type SuggestView =
  | { kind: "none" }
  | { kind: "loading" }
  | { kind: "error"; error: FriendlyError }
  | { kind: "items"; items: string[] };

export function suggestView(
  state: SuggestState,
  opts: { stored: readonly string[]; storedMode: Mode | null; view: Mode; generating: boolean; anchor?: string | null },
): SuggestView {
  if (opts.generating) return { kind: "none" };
  if (state.status === "loading") return { kind: "loading" };
  const checked = opts.anchor !== undefined;
  if (checked && opts.anchor === null) return { kind: "none" };
  // Asked for another reply (since deleted, edited or swapped): show nothing, not the server's copy.
  const asked = state.items !== null || state.status === "error";
  if (checked && asked && state.anchor !== opts.anchor) return { kind: "none" };
  if (state.status === "error" && state.error) return { kind: "error", error: state.error };
  const fromRequest = state.items !== null;
  const items = fromRequest ? (state.items as string[]) : cleanSuggestions(opts.stored);
  const mode = fromRequest ? state.mode : opts.storedMode;
  if (items.length === 0) return { kind: "none" };
  if (mode !== null && mode !== opts.view) return { kind: "none" };
  if (state.dismissed !== null && state.dismissed === suggestionsKey(items)) return { kind: "none" };
  return { kind: "items", items };
}
