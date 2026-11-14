import { useId } from "react";

interface LogoMarkProps {
  /** Rendered width and height in px (default 32). */
  size?: number;
  /** Accessible name. Without it the mark is decorative (aria-hidden). */
  title?: string;
  /** Slow twinkle on the star (off by default; stops under prefers-reduced-motion). */
  animated?: boolean;
  className?: string;
}

/**
 * Book pages: each half of the heart is a page curving from the spine (bottom point) over the top
 * into the gutter. The spine runs down the middle, interrupted by the star.
 */
const LOGO_PAGES = [
  "M24 41C15 34.5 5.5 27 5.5 17.5 5.5 11.2 10 7 15.3 7c3.9 0 7.1 2.3 8.7 5.6",
  "M24 41c9-6.5 18.5-14 18.5-23.5C42.5 11.2 38 7 32.7 7c-3.9 0-7.1 2.3-8.7 5.6",
] as const;

/** The gutter between the pages, above and below the star. */
const LOGO_SPINE = ["M24 12.6v3.4", "M24 35.4V41"] as const;

/** The four-point star cradled between the pages. */
const LOGO_STAR = "M24 19c.5 4.5 2.3 6.3 6.8 6.8-4.5.5-6.3 2.3-6.8 6.8-.5-4.5-2.3-6.3-6.8-6.8 4.5-.5 6.3-2.3 6.8-6.8Z";

/**
 * Lyris app mark (DESIGN.md §2.1): two open book pages curving into a heart, cradling a four-point
 * star. Rounded 1.8px stroke in a warm two-stop gradient; the star is filled gold. Colours follow
 * the theme through --brand-rose and --brand-gold.
 */
export function LogoMark({ size = 32, title, animated = false, className = "" }: LogoMarkProps) {
  const gid = `lyris-mark-${useId().replace(/[^a-zA-Z0-9_-]/g, "")}`;
  const stroke = Math.min(4, Math.max(1.8, size / 26));
  const a11y = title ? { role: "img" as const, "aria-label": title } : { "aria-hidden": true as const };
  return (
    <svg
      viewBox="0 0 48 48"
      width={size}
      height={size}
      fill="none"
      className={`shrink-0 ${className}`}
      focusable="false"
      {...a11y}
    >
      <defs>
        <linearGradient id={gid} gradientUnits="userSpaceOnUse" x1="8" y1="40" x2="40" y2="8">
          <stop offset="0" style={{ stopColor: "var(--brand-rose)" }} />
          <stop offset="1" style={{ stopColor: "var(--brand-gold)" }} />
        </linearGradient>
      </defs>
      <g
        stroke={`url(#${gid})`}
        strokeWidth={stroke}
        strokeLinecap="round"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
      >
        {LOGO_PAGES.map((d) => (
          <path key={d} d={d} vectorEffect="non-scaling-stroke" />
        ))}
        {LOGO_SPINE.map((d) => (
          <path key={d} d={d} vectorEffect="non-scaling-stroke" />
        ))}
      </g>
      <path d={LOGO_STAR} className={animated ? "lyris-twinkle" : undefined} style={{ fill: "var(--brand-gold)" }} />
    </svg>
  );
}
