import type { CSSProperties } from "react";
import { cx } from "./logic";

export interface SkeletonProps {
  /** CSS width (number = px). Default 100%. */
  width?: number | string;
  /** CSS height (number = px). Default 1em for text, 48px otherwise. */
  height?: number | string;
  /** text: a line at text height; block: control radius; card: card radius; circle; pill. */
  shape?: "text" | "block" | "card" | "circle" | "pill";
  /** For shape "text": number of lines (the last one 60% wide). */
  lines?: number;
  className?: string;
}

const RADIUS = {
  text: "rounded-full",
  block: "rounded-control",
  card: "rounded-card",
  circle: "rounded-full",
  pill: "rounded-full",
} as const;

const px = (v: number | string | undefined) => (typeof v === "number" ? `${v}px` : v);

/**
 * Placeholder at the real size of what is loading: a flat tone, no shimmer, no pulse. Hidden from
 * screen readers; put aria-busy="true" on the region and a visually hidden "Đang tải…" if useful.
 */
export function Skeleton({ width, height, shape = "block", lines = 1, className }: SkeletonProps) {
  const isText = shape === "text";
  const style: CSSProperties = {
    width: px(width) ?? (shape === "circle" ? px(height) ?? "48px" : "100%"),
    height: px(height) ?? (isText ? "0.9em" : "48px"),
  };
  if (isText && lines > 1) {
    return (
      <span aria-hidden="true" className={cx("flex w-full flex-col gap-[0.55em]", className)} style={{ width: px(width) }}>
        {Array.from({ length: lines }, (_, i) => (
          <span
            key={i}
            className="block rounded-full bg-surface-3"
            style={{ height: style.height, width: i === lines - 1 ? "60%" : "100%" }}
          />
        ))}
      </span>
    );
  }
  return <span aria-hidden="true" className={cx("block shrink-0 bg-surface-3", RADIUS[shape], className)} style={style} />;
}
