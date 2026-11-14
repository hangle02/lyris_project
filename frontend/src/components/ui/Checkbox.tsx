import { forwardRef, useId } from "react";
import type { ReactNode } from "react";
import { IconCheck } from "../icons";
import { cx } from "./logic";

export interface CheckboxProps {
  /** The sentence beside the box; may hold links (a tap on a link does not tick the box). */
  label: ReactNode;
  checked: boolean;
  onChange: (checked: boolean) => void;
  hint?: ReactNode;
  error?: ReactNode;
  disabled?: boolean;
  className?: string;
}

/**
 * A real checkbox with its sentence: 44px row, a 22px box (14px radius family: 7px), ticked = ink fill
 * like Toggle. Native input under the box, so keyboard, forms and screen readers behave as usual.
 */
export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(function Checkbox(
  { label, checked, onChange, hint, error, disabled, className },
  ref,
) {
  const id = useId();
  const noteId = `${id}-note`;
  const note = error ?? hint;
  return (
    <div className={cx("flex flex-col gap-1", className)}>
      <div className="flex min-h-11 items-start gap-3">
        <span className="relative mt-[11px] inline-flex h-[22px] w-[22px] shrink-0">
          <input
            ref={ref}
            id={id}
            type="checkbox"
            checked={checked}
            disabled={disabled}
            onChange={(e) => onChange(e.target.checked)}
            aria-invalid={error ? true : undefined}
            aria-describedby={note ? noteId : undefined}
            // The hit area reaches past the box (44px) without moving the layout.
            className="peer absolute -inset-[11px] z-10 cursor-pointer opacity-0 disabled:cursor-not-allowed"
          />
          <span
            aria-hidden="true"
            className={cx(
              "pointer-events-none inline-flex h-[22px] w-[22px] items-center justify-center rounded-[7px] border text-[15px] transition-colors duration-150",
              checked ? "border-fg bg-fg text-bg" : "border-line-strong bg-surface-2 text-transparent",
              !!error && !checked && "border-danger",
              "peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-accent peer-disabled:opacity-60",
            )}
          >
            <IconCheck strokeWidth={2.5} />
          </span>
        </span>
        <label htmlFor={id} className="min-w-0 flex-1 cursor-pointer py-2.5 text-[14px] leading-snug text-fg">
          {label}
        </label>
      </div>
      {note && (
        <p id={noteId} className={cx("pl-[34px] text-[13px] leading-snug", error ? "text-danger" : "text-muted")}>
          {note}
        </p>
      )}
    </div>
  );
});
