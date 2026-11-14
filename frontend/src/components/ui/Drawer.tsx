import { useId, useRef } from "react";
import { createPortal } from "react-dom";
import { cx } from "./logic";
import { OverlayHeader } from "./Modal";
import type { OverlayBaseProps } from "./Modal";
import { useOverlay } from "./useOverlay";

export interface DrawerProps extends OverlayBaseProps {
  /** Edge it slides from (default right). Left/right drawers take the full width under 640px. */
  side?: "right" | "left" | "bottom";
  /** Width in px for left/right drawers from 640px (default 400). */
  width?: number;
}

const ENTER = {
  right: "lyris-drawer-right-in",
  left: "lyris-drawer-left-in",
  bottom: "lyris-drawer-bottom-in",
} as const;

/**
 * Slide-over panel (e.g. the heart drawer). Solid surface, floating shadow, focus trapped, Escape
 * closes, page scroll locked, safe areas respected. Rendered in a portal on document.body.
 */
export function Drawer({
  open,
  onClose,
  title,
  description,
  children,
  footer,
  hideTitle,
  dismissible = true,
  initialFocusRef,
  className,
  side = "right",
  width = 400,
}: DrawerProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const titleId = useId();
  const descId = useId();
  useOverlay({ open, onClose, panelRef, initialFocusRef, closeOnEscape: dismissible });
  if (!open) return null;

  const placement =
    side === "bottom"
      ? "inset-x-0 bottom-0 max-h-[90dvh] rounded-t-[20px] pb-[env(safe-area-inset-bottom)] sm:mx-auto sm:max-w-[640px]"
      : cx(
          "inset-y-0 w-full pt-[env(safe-area-inset-top)] pb-[env(safe-area-inset-bottom)] sm:w-[var(--drawer-w)]",
          side === "right" ? "right-0 sm:rounded-l-card" : "left-0 sm:rounded-r-card",
        );

  return createPortal(
    <div className="fixed inset-0 z-50">
      <div
        aria-hidden="true"
        className="lyris-scrim-in absolute inset-0 bg-scrim"
        onClick={dismissible ? onClose : undefined}
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={description ? descId : undefined}
        tabIndex={-1}
        style={{ ["--drawer-w" as string]: `${width}px` }}
        className={cx(
          "absolute flex flex-col overflow-hidden bg-surface text-fg outline-none",
          side === "right" ? "shadow-drawer" : "shadow-float",
          ENTER[side],
          placement,
          className,
        )}
      >
        <OverlayHeader
          title={title}
          description={description}
          titleId={titleId}
          descId={descId}
          hideTitle={hideTitle}
          onClose={onClose}
        />
        <div className="scroll-thin min-h-0 flex-1 overflow-y-auto overscroll-contain px-5 pb-5">{children}</div>
        {footer && (
          <div className="flex shrink-0 flex-wrap items-center justify-end gap-2 border-t border-line px-5 py-3">
            {footer}
          </div>
        )}
      </div>
    </div>,
    document.body,
  );
}
