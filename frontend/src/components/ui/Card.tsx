import type { HTMLAttributes, ReactNode } from "react";
import { cx } from "./logic";

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  /** Inner padding: md 20px (default), sm 16px, none. */
  padding?: "md" | "sm" | "none";
}

/**
 * Resting surface: `surface` on the page ground, 20px radius, no shadow. Separated by the tone step
 * in dark and by a 1px `edge` hairline in light (where the step alone is too faint).
 */
export function Card({ children, padding = "md", className, ...rest }: CardProps) {
  return (
    <div
      className={cx(
        "rounded-card border border-edge bg-surface",
        padding === "md" && "p-5",
        padding === "sm" && "p-4",
        className,
      )}
      {...rest}
    >
      {children}
    </div>
  );
}
