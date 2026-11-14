import { useId, useRef } from "react";
import type { ReactNode, RefObject } from "react";
import { createPortal } from "react-dom";
import { IconX } from "../icons";
import { IconButton } from "./Button";
import { cx } from "./logic";
import { useOverlay } from "./useOverlay";

export interface OverlayBaseProps {
  open: boolean;
  onClose: () => void;
  /** Dialog title (20px). Always the accessible name, even when hidden. */
  title: string;
  /** One line under the title. */
  description?: ReactNode;
  children: ReactNode;
  /** Sticky action row at the bottom (buttons right-aligned on wide screens). */
  footer?: ReactNode;
  /** Visually hide the title row (keep it for screen readers); the close button stays. */
  hideTitle?: boolean;
  /** Escape and a tap on the scrim close it (default true). Turn off while saving. */
  dismissible?: boolean;
  /** Element to focus on open; default the first focusable control. */
  initialFocusRef?: RefObject<HTMLElement | null>;
  /** Extra classes for the panel. */
  className?: string;
}

export interface ModalProps extends OverlayBaseProps {
  /** Width on screens ≥ 640px: sm 400, md 520 (default), lg 680. */
  size?: "sm" | "md" | "lg";
}

const WIDTH = { sm: "sm:max-w-[400px]", md: "sm:max-w-[520px]", lg: "sm:max-w-[680px]" } as const;

export function OverlayHeader({
  title,
  description,
  titleId,
  descId,
  hideTitle,
  onClose,
}: {
  title: string;
  description?: ReactNode;
  titleId: string;
  descId: string;
  hideTitle?: boolean;
  onClose: () => void;
}) {
  return (
    <div className={cx("flex shrink-0 items-start gap-3 px-5", hideTitle ? "pt-3" : "pt-5 pb-3")}>
      <div className={cx("min-w-0 flex-1", hideTitle && "sr-only")}>
        <h2 id={titleId} className="text-[20px] leading-tight font-semibold text-fg">
          {title}
        </h2>
        {description && (
          <p id={descId} className="mt-1.5 text-[14px] leading-snug text-pretty text-muted">
            {description}
          </p>
        )}
      </div>
      <IconButton
        label="Đóng"
        icon={<IconX />}
        size="sm"
        onClick={onClose}
        data-overlay-close=""
        className="-mt-1 -mr-2 ml-auto"
      />
    </div>
  );
}

/**
 * Dialog: a bottom sheet on phones, centred card from 640px. Solid surface with a floating shadow,
 * focus trapped, Escape closes, page scroll locked. Rendered in a portal on document.body.
 */
export function Modal({
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
  size = "md",
}: ModalProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const titleId = useId();
  const descId = useId();
  useOverlay({ open, onClose, panelRef, initialFocusRef, closeOnEscape: dismissible });
  if (!open) return null;

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center sm:p-6">
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
        className={cx(
          "lyris-sheet-in relative flex max-h-[92dvh] w-full flex-col overflow-hidden bg-surface text-fg shadow-float outline-none",
          "rounded-t-[20px] pb-[env(safe-area-inset-bottom)] sm:max-h-[85dvh] sm:rounded-card sm:pb-0",
          WIDTH[size],
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
