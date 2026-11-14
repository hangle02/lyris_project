import { useId } from "react";
import type { ReactNode } from "react";
import { cx } from "./logic";

export interface ChoiceOption<T extends string> {
  value: T;
  label: string;
  /** One line shown under the group while this option is chosen. */
  hint?: string;
}

export interface ChoiceGroupProps<T extends string> {
  label: string;
  options: ReadonlyArray<ChoiceOption<T>>;
  value: T;
  onChange: (value: T) => void;
  /** Fixed hint; otherwise the chosen option's own hint. */
  hint?: ReactNode;
  disabled?: boolean;
}

/**
 * A labelled set of form choices as pills that wrap (gender, language, style...); the chosen one
 * gets the accent tint and ring. For the two-way mode switch in a header use SegmentedControl.
 */
export function ChoiceGroup<T extends string>({ label, options, value, onChange, hint, disabled }: ChoiceGroupProps<T>) {
  const labelId = useId();
  const active = options.find((o) => o.value === value);
  const shownHint = hint ?? active?.hint;
  return (
    <div className="flex min-w-0 flex-col gap-2">
      <span id={labelId} className="text-[14px] leading-tight font-medium text-fg">
        {label}
      </span>
      <div role="radiogroup" aria-labelledby={labelId} className="flex flex-wrap gap-2">
        {options.map((o) => {
          const on = o.value === value;
          return (
            <button
              key={o.value}
              type="button"
              role="radio"
              aria-checked={on}
              disabled={disabled}
              onClick={() => !on && onChange(o.value)}
              className={cx(
                "min-h-9 rounded-full px-3.5 text-[14px] font-medium transition-colors duration-150 disabled:opacity-50",
                on
                  ? "bg-accent/15 text-fg ring-1 ring-inset ring-accent/60"
                  : "bg-surface-2 text-muted hover:bg-surface-3 hover:text-fg",
              )}
            >
              {o.label}
            </button>
          );
        })}
      </div>
      {shownHint && <p className="text-[13px] leading-snug text-muted">{shownHint}</p>}
    </div>
  );
}
