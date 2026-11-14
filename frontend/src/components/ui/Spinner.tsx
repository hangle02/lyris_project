import { cx } from "./logic";

interface SpinnerProps {
  /** Diameter in px (default 16). */
  size?: number;
  /** Screen-reader text; without it the spinner is decorative. */
  label?: string;
  className?: string;
}

/** Small ring that turns while something loads. Holds still under prefers-reduced-motion. */
export function Spinner({ size = 16, label, className }: SpinnerProps) {
  return (
    <span
      role={label ? "status" : undefined}
      aria-hidden={label ? undefined : true}
      className={cx("inline-flex shrink-0", className)}
    >
      <svg
        viewBox="0 0 24 24"
        width={size}
        height={size}
        className="animate-spin motion-reduce:animate-none"
        style={{ animationDuration: "900ms" }}
        focusable="false"
        aria-hidden="true"
      >
        <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeOpacity="0.25" strokeWidth="2.5" />
        <path d="M21 12a9 9 0 0 0-9-9" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
      </svg>
      {label && <span className="sr-only">{label}</span>}
    </span>
  );
}
