import type { ReactNode } from "react";
import { cx } from "./logic";

export interface ChipProps {
  children: ReactNode;
  /** With onClick the chip is a toggle button (aria-pressed); without it, a static tag. */
  onClick?: () => void;
  selected?: boolean;
  /** Leading icon element. */
  icon?: ReactNode;
  /** A small dot before the text in this CSS colour (e.g. "var(--color-emo-affection)"). */
  dotColor?: string;
  /** md = 36px (filters, quick replies), sm = 28px (inline micro-chips). */
  size?: "md" | "sm";
  disabled?: boolean;
  title?: string;
  className?: string;
}

const SIZE = {
  md: "min-h-9 px-3.5 text-[14px] gap-1.5 [&_svg]:text-[15px]",
  sm: "min-h-7 px-2.5 text-[13px] gap-1 [&_svg]:text-[13px]",
} as const;

/**
 * Pill for filters, quick replies and tags. Unselected: a tone step with muted text; selected: a
 * light accent tint with an accent ring. Sentence case, no emoji.
 */
export function Chip({ children, onClick, selected = false, icon, dotColor, size = "md", disabled, title, className }: ChipProps) {
  const content = (
    <>
      {dotColor && (
        <span aria-hidden="true" className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: dotColor }} />
      )}
      {icon}
      <span className="min-w-0 truncate">{children}</span>
    </>
  );
  // Icons keep their size when the text truncates.
  const shape = cx("inline-flex max-w-full shrink-0 items-center rounded-full leading-tight [&_svg]:shrink-0", SIZE[size]);

  if (!onClick) {
    return (
      <span title={title} className={cx(shape, "bg-surface-2 text-muted", className)}>
        {content}
      </span>
    );
  }
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={selected}
      disabled={disabled}
      title={title}
      className={cx(
        shape,
        "font-medium transition-colors duration-150 disabled:opacity-50",
        selected
          ? "bg-accent/15 text-fg ring-1 ring-inset ring-accent/60"
          : "bg-surface-2 text-muted hover:bg-surface-3 hover:text-fg",
        className,
      )}
    >
      {content}
    </button>
  );
}

export type BadgeTone = "neutral" | "accent" | "gold" | "ok" | "warn" | "danger";

/*
 * Badge ink is the tone with 25% fg mixed in (lighter in dark, deeper in light), so it holds 4.5:1
 * on its own 15% tint over bg, surface, surface-2 and surface-3 in both themes (lowest 4.85:1).
 */
const INK: Record<BadgeTone, string> = {
  neutral: "text-muted",
  accent: "text-[color-mix(in_oklab,var(--color-accent)_75%,var(--color-fg))]",
  gold: "text-[color-mix(in_oklab,var(--color-accent-2)_75%,var(--color-fg))]",
  ok: "text-[color-mix(in_oklab,var(--color-ok)_75%,var(--color-fg))]",
  warn: "text-[color-mix(in_oklab,var(--color-warn)_75%,var(--color-fg))]",
  danger: "text-[color-mix(in_oklab,var(--color-danger)_75%,var(--color-fg))]",
};

const TINT: Record<BadgeTone, string> = {
  neutral: "bg-surface-3",
  accent: "bg-accent/15",
  gold: "bg-accent-2/15",
  ok: "bg-ok/15",
  warn: "bg-warn/15",
  danger: "bg-danger/15",
};

/** Opaque versions (the tint mixed into surface) for a badge that sits on a photo, e.g. an avatar corner. */
const TINT_SOLID: Record<BadgeTone, string> = {
  neutral: "bg-surface-3",
  accent: "bg-[color-mix(in_oklab,var(--color-accent)_16%,var(--color-surface))]",
  gold: "bg-[color-mix(in_oklab,var(--color-accent-2)_16%,var(--color-surface))]",
  ok: "bg-[color-mix(in_oklab,var(--color-ok)_16%,var(--color-surface))]",
  warn: "bg-[color-mix(in_oklab,var(--color-warn)_16%,var(--color-surface))]",
  danger: "bg-[color-mix(in_oklab,var(--color-danger)_16%,var(--color-surface))]",
};

/**
 * Small status pill (20px, 12px semibold, sentence case, no letter-spacing): a pale tint with
 * text in the same hue. Inside rows or on an avatar corner (pass `solid` there), never above a heading.
 */
export function Badge({
  children,
  tone = "neutral",
  solid = false,
  className,
}: {
  children: ReactNode;
  tone?: BadgeTone;
  /** Opaque fill plus a 2px ring in the page colour, for badges laid over images. */
  solid?: boolean;
  className?: string;
}) {
  return (
    <span
      className={cx(
        "inline-flex h-5 shrink-0 items-center rounded-full px-2 text-[12px] leading-none font-semibold whitespace-nowrap",
        INK[tone],
        solid ? cx(TINT_SOLID[tone], "ring-2 ring-bg") : TINT[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}
