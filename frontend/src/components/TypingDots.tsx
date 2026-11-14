import { cx } from "./ui";

/**
 * Three bouncing dots: someone is writing (Phase 3b; replaces "{Tên} đang ngập ngừng tìm lời hồi
 * đáp..."). Purely visual (aria-hidden): the words for screen readers ("{Tên} đang trả lời") go in a
 * LiveStatus region that stays mounted, because a live region announces reliably only when its text
 * changes, not when it appears together with its text. The dots hold still under
 * prefers-reduced-motion (index.css).
 */
export function TypingDots({ className }: { className?: string }) {
  return (
    <span aria-hidden="true" className={cx("inline-flex items-center", className)}>
      <span className="typing-bounce" />
      <span className="typing-bounce" />
      <span className="typing-bounce" />
    </span>
  );
}
