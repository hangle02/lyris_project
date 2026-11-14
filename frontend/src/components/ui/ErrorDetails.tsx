import { IconChevronDown } from "../icons";
import { plainMessage } from "../../lib/text";
import { cx } from "./logic";

/**
 * "Chi tiết": the technical text behind a plain error message (Phase 3b), folded away by default.
 * Native <details>, so it opens with the keyboard and screen readers announce its state.
 */
export function ErrorDetails({ technical, className }: { technical: string | null | undefined; className?: string }) {
  if (!technical || !technical.trim()) return null;
  return (
    <details className={cx("group text-[13px] leading-snug", className)}>
      <summary className="inline-flex min-h-8 cursor-pointer list-none items-center gap-1 rounded-full text-muted hover:text-fg max-sm:min-h-11 [&::-webkit-details-marker]:hidden">
        Chi tiết
        <IconChevronDown
          aria-hidden="true"
          className="text-[14px] transition-transform duration-150 group-open:rotate-180 motion-reduce:transition-none"
        />
      </summary>
      <p className="mt-1 whitespace-pre-wrap text-muted [overflow-wrap:anywhere]">{plainMessage(technical.trim())}</p>
    </details>
  );
}
