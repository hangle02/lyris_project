import { useId } from "react";

interface WordmarkProps {
  /** Font size in px; the flourish and star scale with it (default 28). */
  size?: number;
  /** Gentle twinkle on the star over the "ı" (default true; stops under prefers-reduced-motion). */
  animated?: boolean;
  /** The silk-ribbon flourish under the word (default true). */
  flourish?: boolean;
  className?: string;
}

const STAR = "M12 1.5c.62 5.6 3.4 8.4 9 9-5.6.62-8.38 3.4-9 9-.62-5.6-3.4-8.38-9-9 5.6-.6 8.38-3.4 9-9Z";

/**
 * "Lyris" wordmark (DESIGN.md §2.2): Cormorant Garamond italic bold; the L in the warm wordmark
 * gradient; a dotless "ı" crowned by a small four-point star; a hand-drawn ribbon underneath.
 * Exposed to assistive tech as one image named "Lyris".
 */
export function Wordmark({ size = 28, animated = true, flourish = true, className = "" }: WordmarkProps) {
  const gid = `lyris-ribbon-${useId().replace(/[^a-zA-Z0-9_-]/g, "")}`;
  return (
    <span
      role="img"
      aria-label="Lyris"
      className={`relative inline-flex shrink-0 flex-col items-start font-brand font-bold italic leading-none select-none ${className}`}
      style={{ fontSize: size }}
    >
      <span aria-hidden="true" className="relative whitespace-nowrap pr-[0.08em] tracking-[0.005em]">
        <span className="text-grad-wordmark pr-[0.05em]">L</span>
        <span className="text-fg">yr</span>
        <span className="relative text-fg">
          {"ı"}
          <svg
            viewBox="0 0 24 24"
            className="absolute"
            style={{ width: "0.27em", height: "0.27em", left: "0.09em", top: "0.14em" }}
            focusable="false"
          >
            <path d={STAR} className={animated ? "lyris-twinkle" : undefined} style={{ fill: "var(--brand-gold)" }} />
          </svg>
        </span>
        <span className="text-fg">s</span>
      </span>
      {flourish && (
        <svg
          aria-hidden="true"
          viewBox="0 0 100 12"
          preserveAspectRatio="none"
          className="-mt-[0.1em] block"
          style={{ width: "100%", height: "0.24em" }}
          focusable="false"
        >
          <defs>
            <linearGradient id={gid} x1="0" y1="0" x2="1" y2="0">
              <stop offset="0" style={{ stopColor: "var(--brand-rose)", stopOpacity: 0.2 }} />
              <stop offset="0.35" style={{ stopColor: "var(--brand-rose)" }} />
              <stop offset="1" style={{ stopColor: "var(--brand-gold)", stopOpacity: 0.35 }} />
            </linearGradient>
          </defs>
          <path
            d="M3 7.5C16 3 28 10.5 44 7.2S74 2.4 97 5.5"
            stroke={`url(#${gid})`}
            strokeWidth={Math.max(1.2, size / 22)}
            strokeLinecap="round"
            fill="none"
            vectorEffect="non-scaling-stroke"
          />
        </svg>
      )}
    </span>
  );
}
