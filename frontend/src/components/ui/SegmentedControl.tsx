import { useRef } from "react";
import type { KeyboardEvent, ReactNode } from "react";
import { cx, radioKeyTarget } from "./logic";

export interface SegmentOption<T extends string> {
  value: T;
  label: string;
  icon?: ReactNode;
  disabled?: boolean;
}

export interface SegmentedControlProps<T extends string> {
  options: ReadonlyArray<SegmentOption<T>>;
  value: T;
  onChange: (value: T) => void;
  /** Accessible name of the group (e.g. "Kiểu hiển thị"). */
  label: string;
  /** md = 36px segments (default), sm = 28px (inside a 56px header). */
  size?: "md" | "sm";
  disabled?: boolean;
  className?: string;
}

const SEG = {
  md: "h-9 px-3.5 text-[14px] [&_svg]:text-[16px]",
  sm: "h-7 px-3 text-[13px] [&_svg]:text-[14px]",
} as const;

/**
 * Pill switch between two or three modes (Story / DM). A radio group with roving focus: arrows,
 * Home and End move and select. The chosen segment is filled with the accent.
 */
export function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
  label,
  size = "md",
  disabled = false,
  className,
}: SegmentedControlProps<T>) {
  const refs = useRef<Array<HTMLButtonElement | null>>([]);
  const current = options.findIndex((o) => o.value === value);

  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    let target = radioKeyTarget(e.key, current, options.length);
    if (target === null) return;
    e.preventDefault();
    // Skip disabled options in the direction of travel.
    const step = e.key === "ArrowLeft" || e.key === "ArrowUp" || e.key === "End" ? -1 : 1;
    for (let i = 0; i < options.length && options[target]?.disabled; i++) {
      target = (target + step + options.length) % options.length;
    }
    const opt = options[target];
    if (!opt || opt.disabled) return;
    refs.current[target]?.focus();
    if (opt.value !== value) onChange(opt.value);
  };

  return (
    <div
      role="radiogroup"
      aria-label={label}
      aria-disabled={disabled || undefined}
      onKeyDown={disabled ? undefined : onKeyDown}
      className={cx("inline-flex w-fit shrink-0 items-center gap-0.5 rounded-full bg-surface-2 p-1", className)}
    >
      {options.map((o, i) => {
        const on = o.value === value;
        return (
          <button
            key={o.value}
            ref={(el) => {
              refs.current[i] = el;
            }}
            type="button"
            role="radio"
            aria-checked={on}
            tabIndex={on || (current === -1 && i === 0) ? 0 : -1}
            disabled={disabled || o.disabled}
            onClick={() => !on && onChange(o.value)}
            className={cx(
              "inline-flex items-center justify-center gap-1.5 rounded-full font-semibold whitespace-nowrap transition-colors duration-150",
              "disabled:cursor-not-allowed disabled:opacity-50",
              SEG[size],
              on ? "bg-accent text-on-accent" : "text-muted hover:text-fg",
            )}
          >
            {o.icon}
            {o.label}
          </button>
        );
      })}
    </div>
  );
}
