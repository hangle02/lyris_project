import { useId } from "react";
import type { ReactNode } from "react";
import { IconChevronDown } from "../icons";
import { cx } from "./logic";

export interface DisclosureProps {
  /** The always-visible row ("Nâng cao"). */
  title: string;
  /** One quiet line beside the title, shown while closed. */
  hint?: ReactNode;
  open: boolean;
  onToggle: (open: boolean) => void;
  children: ReactNode;
  className?: string;
}

/**
 * A folded section (Phase 3b "Nâng cao"): a 44px row with a chevron that opens the content below it.
 * Controlled, so the owner can start work only while open (polling the machine, loading models).
 */
export function Disclosure({ title, hint, open, onToggle, children, className }: DisclosureProps) {
  const id = useId();
  return (
    <div className={cx("flex flex-col", className)}>
      <button
        type="button"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => onToggle(!open)}
        className="-mx-2 flex min-h-11 items-center gap-3 rounded-control px-2 text-left transition-colors duration-150 hover:bg-surface-2"
      >
        <span className="min-w-0 flex-1">
          <span className="block text-[16px] leading-tight font-semibold text-fg">{title}</span>
          {hint && !open && <span className="mt-0.5 block text-[13px] leading-snug text-muted">{hint}</span>}
        </span>
        <IconChevronDown
          aria-hidden="true"
          className={cx(
            "shrink-0 text-[18px] text-muted transition-transform duration-150 motion-reduce:transition-none",
            open && "rotate-180",
          )}
        />
      </button>
      <div id={id} hidden={!open} className="pt-3">
        {open && children}
      </div>
    </div>
  );
}
