import { InlineText } from "../../components/Prose";
import { trackInStory } from "../../lib/track";
import { cx } from "../../components/ui";

interface Props {
  /** The replies the player asked for ("Nhận gợi ý"), at most three (suggestLogic.suggestView). */
  suggestions: string[];
  disabled: boolean;
  onPick: (text: string) => void;
}

/**
 * Suggested replies above the composer (DESIGN.md §6), shown only after the player asked for them
 * (Phase 3b, SuggestionArea); a tap sends the reply at once, so each one must be readable before it
 * is tapped.
 *
 * - Phones: one row that swipes sideways. Each reply is a card almost as wide as the screen and up to
 *   two lines tall (about 80 characters, a whole suggestion). The next card peeks 14px at the right
 *   edge, which shows only its padding: no word is ever cut by the screen edge.
 * - From 640px: the replies wrap onto as many lines as they need inside the composer column, one line
 *   each, so a mouse user never has to scroll sideways to find the third one.
 */
export function QuickReplies({ suggestions, disabled, onPick }: Props) {
  if (suggestions.length === 0) return null;
  return (
    <div
      role="group"
      aria-label="Gợi ý trả lời nhanh"
      className={cx(
        "scroll-thin -mx-4 snap-x snap-mandatory scroll-px-4 overflow-x-auto overscroll-x-contain px-4 pb-1 motion-safe:scroll-smooth",
        "sm:mx-0 sm:snap-none sm:overflow-visible sm:px-0 sm:pb-0",
      )}
    >
      <ul className="flex w-max gap-2 sm:w-auto sm:flex-wrap">
        {suggestions.map((s, i) => (
          <li
            key={s}
            // 100vw minus the 16px margin, the 8px gap and a 14px peek of the next card; a lone card
            // takes the full row between the margins.
            className="w-[calc(100vw-38px)] shrink-0 snap-start only:w-[calc(100vw-32px)] sm:w-auto sm:max-w-full sm:shrink"
          >
            <button
              type="button"
              disabled={disabled}
              title={s}
              aria-label={`Gửi: ${s}`}
              onClick={() => {
                // Usage: which of the suggestions was taken (its place, never its text).
                trackInStory("suggestion_used", { position: Math.min(3, i + 1) });
                onPick(s);
              }}
              className={cx(
                // 44px+ on phones (touch), 36px from 640px; the pressed-input tone of DESIGN.md.
                "flex min-h-11 w-full items-center rounded-control bg-surface-2 px-4 py-2 text-left text-[14px] leading-snug font-medium text-fg",
                "transition-colors duration-150 hover:bg-surface-3 disabled:opacity-50 sm:min-h-9 sm:rounded-full sm:py-1.5",
              )}
            >
              <span className="line-clamp-2 min-w-0 sm:line-clamp-1">
                {/* Shown formatted (*actions* in italics, no asterisks); sent exactly as written. */}
                <InlineText text={s} />
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
