import { cx, meterPercent } from "./logic";

export interface MeterProps {
  /** What is measured ("Thương mến", "Bộ nhớ hợp nhất"). */
  label: string;
  value: number;
  /** Default 100. */
  max?: number;
  /** Fill colour as CSS (e.g. "var(--color-emo-trust)"). Default the accent. */
  color?: string;
  /** Text on the right of the label ("91%", "9.4 GB / 24 GB"). Default the rounded percent. */
  valueText?: string;
  /** No data yet: the track stays, the fill and the value fade ("—"). */
  empty?: boolean;
  /** Label for screen readers only. */
  hideLabel?: boolean;
  className?: string;
}

/**
 * Labelled bar at its true ratio, both ends readable: label left, value right in tabular figures,
 * an 8px track below. The width eases over 500ms (DESIGN.md: emotion bars).
 */
export function Meter({ label, value, max = 100, color, valueText, empty = false, hideLabel = false, className }: MeterProps) {
  const pct = empty ? 0 : meterPercent(value, max);
  const shown = empty ? "—" : (valueText ?? `${Math.round(pct)}%`);
  return (
    <div
      role="meter"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={max}
      aria-valuenow={empty ? undefined : Math.min(max, Math.max(0, value))}
      aria-valuetext={empty ? "Chưa có dữ liệu" : shown}
      className={cx("flex min-w-0 flex-col gap-1.5", className)}
    >
      <div className={cx("flex items-baseline justify-between gap-3 text-[14px] leading-tight", hideLabel && "sr-only")}>
        <span className="min-w-0 truncate text-fg">{label}</span>
        <span className={cx("shrink-0 tabular-nums", empty ? "text-faint" : "text-muted")}>{shown}</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-surface-3">
        <div
          className="h-full rounded-full transition-[width] duration-500 ease-out motion-reduce:transition-none"
          style={{ width: `${pct}%`, backgroundColor: color ?? "var(--color-accent)" }}
        />
      </div>
    </div>
  );
}
