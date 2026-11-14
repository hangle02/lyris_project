import { useEffect } from "react";
import { createPortal } from "react-dom";
import { IconCheck } from "../icons";

export interface ToastProps {
  /** The one sentence to show; null hides the toast. */
  text: string | null;
  onDone: () => void;
  /** How long it stays (ms). */
  duration?: number;
}

/**
 * A short confirmation ("Đã gửi báo cáo…"): a surface pill floating above the bottom edge (and the
 * composer), announced politely, gone after a few seconds. Not for errors: those stay where they
 * happened (InlineAlert).
 */
export function Toast({ text, onDone, duration = 3500 }: ToastProps) {
  useEffect(() => {
    if (text === null) return;
    const t = window.setTimeout(onDone, duration);
    return () => window.clearTimeout(t);
  }, [text, onDone, duration]);

  if (typeof document === "undefined") return null;
  return createPortal(
    <div
      role="status"
      aria-live="polite"
      className="pointer-events-none fixed inset-x-0 bottom-[calc(96px+env(safe-area-inset-bottom))] z-[60] flex justify-center px-4"
    >
      {text !== null && (
        <p className="pointer-events-auto inline-flex max-w-[420px] items-center gap-2 rounded-full border border-line bg-surface px-4 py-2.5 text-[14px] leading-snug font-medium text-fg shadow-float motion-safe:animate-[lyris-rise-in_200ms_ease-out]">
          <IconCheck aria-hidden="true" className="shrink-0 text-[16px] text-ok" />
          {text}
        </p>
      )}
    </div>,
    document.body,
  );
}
