import type { ReactNode } from "react";
import { cx } from "./logic";

export interface EmptyStateProps {
  /** One sentence: what is missing and what to do. No emoji, no illustration. */
  text: string;
  /** The one next step, usually a <Button size="sm">. */
  action?: ReactNode;
  /** Dashed frame where the content would be (default true). Off when the parent already frames it. */
  framed?: boolean;
  className?: string;
}

/** An empty section that keeps its place: one sentence and one action, left-aligned. */
export function EmptyState({ text, action, framed = true, className }: EmptyStateProps) {
  return (
    <div
      className={cx(
        "flex flex-col items-start gap-3",
        framed && "rounded-card border border-dashed border-line-strong px-5 py-5",
        className,
      )}
    >
      <p className="text-[15px] leading-snug text-muted">{text}</p>
      {action}
    </div>
  );
}
