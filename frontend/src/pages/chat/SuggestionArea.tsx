import { useLayoutEffect, useRef } from "react";
import { TypingDots } from "../../components/TypingDots";
import { IconRefreshCw, IconX } from "../../components/icons";
import { Button, IconButton, InlineAlert } from "../../components/ui";
import { QuickReplies } from "./QuickReplies";
import type { SuggestView } from "./suggestLogic";

interface Props {
  view: SuggestView;
  /** Sends one reply at once (the composer's send path). */
  onPick: (text: string) => void;
  /** "Gợi ý khác" / "Thử lại": asks again. */
  onMore: () => void;
  /** Closes the area (cancels a request still running). */
  onDismiss: () => void;
  /** Sending is not possible right now (a reply streams, the story is loading). */
  disabled: boolean;
  /** Asking again is not possible right now (with the reason as tooltip). */
  moreDisabledReason: string | null;
}

/** Focus is nowhere (the focused button was just removed): document.body or nothing. */
function focusLost(): boolean {
  const active = document.activeElement;
  return active === null || active === document.body;
}

/**
 * The suggestion area above the composer (Phase 3b): only after the player tapped "Nhận gợi ý".
 * Typing dots while the replies are written, then the replies as cards (tap sends at once) with
 * "Gợi ý khác" and a close button; an error in plain words with "Chi tiết" and "Thử lại".
 *
 * Focus never drops to the page: "Gợi ý khác" / "Thử lại" move it to "Huỷ gợi ý" in the loading
 * row, and when the replies (or an error) replace that row while it had focus, focus moves to the
 * area. Closing the area or sending a reply is handled by the composer (focus goes back to "+").
 * Screen readers hear "Đang nghĩ gợi ý…" / "Có N gợi ý" from the composer's LiveStatus.
 */
export function SuggestionArea({ view, onPick, onMore, onDismiss, disabled, moreDisabledReason }: Props) {
  const areaRef = useRef<HTMLDivElement>(null);
  const cancelRef = useRef<HTMLButtonElement>(null);
  /** "Gợi ý khác" / "Thử lại" was used: focus "Huỷ gợi ý" once the loading row is there. */
  const focusCancel = useRef(false);
  /** "Huỷ gợi ý" had focus (it has no blur when it is removed). */
  const cancelFocused = useRef(false);

  const more = () => {
    focusCancel.current = true;
    onMore();
  };

  useLayoutEffect(() => {
    if (view.kind === "loading") {
      if (focusCancel.current) {
        focusCancel.current = false;
        cancelRef.current?.focus();
      }
      return;
    }
    focusCancel.current = false;
    if (cancelFocused.current) {
      cancelFocused.current = false;
      if (view.kind !== "none" && focusLost()) areaRef.current?.focus();
    }
  }, [view.kind]);

  if (view.kind === "none") return null;

  if (view.kind === "loading") {
    // Same header row as the ready state, so the area reads as one thing filling in (and the close
    // button does not jump); the dots sit where the replies will land.
    return (
      <div className="flex flex-col gap-1.5">
        <div className="flex min-h-9 items-center gap-1">
          <p className="mr-auto text-[13px] font-medium text-muted">Gợi ý cho bạn</p>
          <IconButton
            ref={cancelRef}
            size="sm"
            label="Huỷ gợi ý"
            icon={<IconX />}
            onClick={onDismiss}
            onFocus={() => {
              cancelFocused.current = true;
            }}
            onBlur={() => {
              cancelFocused.current = false;
            }}
            className="max-sm:h-11 max-sm:w-11"
          />
        </div>
        <span className="inline-flex min-h-11 w-fit items-center rounded-control bg-surface-2 px-4 text-[13px] text-muted sm:min-h-9 sm:rounded-full">
          <TypingDots />
        </span>
      </div>
    );
  }

  if (view.kind === "error") {
    return (
      <div ref={areaRef} tabIndex={-1} role="group" aria-label="Gợi ý cho bạn" className="outline-none">
        <InlineAlert
          tone="error"
          text={view.error.text}
          technical={view.error.technical}
          onRetry={more}
          retryDisabled={moreDisabledReason !== null}
          onDismiss={onDismiss}
        />
      </div>
    );
  }

  return (
    <div ref={areaRef} tabIndex={-1} role="group" aria-label="Gợi ý cho bạn" className="flex flex-col gap-1.5 outline-none">
      <div className="flex min-h-9 items-center gap-1">
        <p className="mr-auto text-[13px] font-medium text-muted">Gợi ý cho bạn</p>
        <Button
          size="sm"
          variant="ghost"
          icon={<IconRefreshCw />}
          onClick={more}
          disabled={moreDisabledReason !== null}
          title={moreDisabledReason ?? "Viết ba gợi ý khác"}
          className="max-sm:h-11"
        >
          Gợi ý khác
        </Button>
        <IconButton size="sm" label="Ẩn gợi ý" icon={<IconX />} onClick={onDismiss} className="max-sm:h-11 max-sm:w-11" />
      </div>
      <QuickReplies suggestions={view.items} disabled={disabled} onPick={onPick} />
    </div>
  );
}
