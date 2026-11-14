import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import { ComposerMenu } from "../pages/chat/ComposerMenu";
import { SuggestionArea } from "../pages/chat/SuggestionArea";
import type { ComposerAction, ComposerActionId, SuggestView } from "../pages/chat/suggestLogic";
import { AutoTextarea } from "./AutoTextarea";
import { LiveStatus } from "./LiveStatus";
import { IconSend, IconStop } from "./icons";
import { IconButton } from "./ui";
import { MAX_CONTENT_CHARS } from "../lib/text";
import type { Mode } from "../types";

interface Props {
  storyId: number | null;
  streaming: boolean;
  mode: Mode;
  characterName: string;
  disabled: boolean;
  onSend: (content: string) => Promise<boolean>;
  onStop: () => void;
  /** The "+" menu (Phase 3b); no menu when absent (e.g. a composer without a story). */
  actions?: ComposerAction[];
  onAction?: (id: ComposerActionId) => void;
  /** The suggestion area (only after "Nhận gợi ý"); a tapped reply is sent at once. */
  suggestion?: SuggestView;
  onMoreSuggestions?: () => void;
  onDismissSuggestions?: () => void;
  /** Why "Gợi ý khác" cannot run now; null when it can. */
  moreSuggestionsBlocked?: string | null;
}

const DRAFT_KEY = (id: number) => `lyris.draft.${id}`;

function readDraft(id: number | null): string {
  if (id === null) return "";
  try {
    return localStorage.getItem(DRAFT_KEY(id)) ?? "";
  } catch {
    return "";
  }
}

function writeDraft(id: number | null, text: string) {
  if (id === null) return;
  try {
    if (text) localStorage.setItem(DRAFT_KEY(id), text);
    else localStorage.removeItem(DRAFT_KEY(id));
  } catch {
    // storage unavailable: drafts are a convenience only
  }
}

export function Composer({
  storyId,
  streaming,
  mode,
  characterName,
  disabled,
  onSend,
  onStop,
  actions,
  onAction,
  suggestion = { kind: "none" },
  onMoreSuggestions,
  onDismissSuggestions,
  moreSuggestionsBlocked = null,
}: Props) {
  const dm = mode === "dm";
  const [text, setText] = useState(() => readDraft(storyId));
  const ref = useRef<HTMLTextAreaElement>(null);
  const plusRef = useRef<HTMLButtonElement>(null);

  /**
   * The suggestion area's buttons go away once used (closing it, sending a reply): focus returns to
   * "+" (no phone keyboard popping up), or to the input when there is no menu or "+" is disabled.
   */
  const focusHome = () => {
    const plus = plusRef.current;
    if (plus && !plus.disabled) plus.focus();
    else ref.current?.focus();
  };

  // Per-story unsent draft. The parent remounts this component (key) when the story changes.
  useEffect(() => {
    writeDraft(storyId, text);
  }, [storyId, text]);

  const canSend = !streaming && !disabled && storyId !== null && text.trim().length > 0;

  /** One send path for the input and the quick replies. */
  const sendText = async (content: string, fromInput: boolean) => {
    if (streaming || disabled || storyId === null || !content.trim()) return;
    if (fromInput) setText("");
    const ok = await onSend(content);
    if (!ok && fromInput) {
      // Refused before streaming (busy, invalid): give the text back unless the user typed again.
      setText((cur) => (cur ? cur : content));
    }
    // A tapped quick reply leaves focus alone (no phone keyboard popping up).
    if (fromInput) ref.current?.focus();
  };

  const submit = () => (canSend ? sendText(text, true) : Promise.resolve());

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Never send while an IME (e.g. Telex/VNI) is composing a character.
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing && e.keyCode !== 229) {
      e.preventDefault();
      void submit();
    }
  };

  return (
    <div className="border-t border-line bg-bg pb-[max(0.75rem,env(safe-area-inset-bottom))]">
      <div className="mx-auto flex w-full max-w-[720px] flex-col gap-2.5 px-4 pt-3">
        {/* Always mounted, so starting and finishing a suggestion request is announced. */}
        <LiveStatus
          text={
            suggestion.kind === "loading"
              ? "Đang nghĩ gợi ý cho bạn"
              : suggestion.kind === "items"
                ? `Có ${suggestion.items.length} gợi ý trả lời.`
                : ""
          }
        />
        <SuggestionArea
          view={suggestion}
          disabled={streaming || disabled || storyId === null}
          onPick={(s) => {
            void sendText(s, false);
            focusHome();
          }}
          onMore={() => onMoreSuggestions?.()}
          onDismiss={() => {
            onDismissSuggestions?.();
            focusHome();
          }}
          moreDisabledReason={moreSuggestionsBlocked}
        />
        <div className="flex items-end gap-2">
          {actions && onAction && (
            <ComposerMenu actions={actions} onSelect={onAction} disabled={storyId === null} triggerRef={plusRef} />
          )}
          <AutoTextarea
            // Remount when the mode (and so the placeholder) changes: the height is measured on mount.
            key={mode}
            ref={ref}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={onKeyDown}
            maxHeight={220}
            placeholder={dm ? "Nhắn tin…" : 'Nhập lời thoại vào "…"'}
            aria-label={dm ? `Tin nhắn cho ${characterName}` : "Lượt của bạn: lời nói, *hành động* hoặc ((chỉ đạo cho AI))"}
            enterKeyHint="send"
            maxLength={MAX_CONTENT_CHARS}
            disabled={storyId === null}
            className="min-h-11 min-w-0 flex-1 rounded-card border border-line bg-surface-2 px-4 py-[9px] text-[16px] leading-[1.55] text-fg outline-none transition-colors duration-150 placeholder:text-faint focus:border-accent disabled:opacity-60"
          />
          {streaming ? (
            // Same 44px footprint as the send button, so the input does not reflow when a reply starts.
            <IconButton variant="secondary" label="Dừng" icon={<IconStop />} onClick={onStop} />
          ) : (
            <IconButton
              variant="orb"
              label="Gửi (Enter)"
              icon={<IconSend />}
              onClick={() => void submit()}
              disabled={!canSend}
            />
          )}
        </div>
      </div>
    </div>
  );
}
