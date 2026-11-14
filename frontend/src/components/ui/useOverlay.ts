import { useEffect, useId, useRef } from "react";
import type { RefObject } from "react";
import { OverlayStack, nextFocusIndex } from "./logic";

const stack = new OverlayStack();

const FOCUSABLE =
  'a[href], area[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), iframe, [tabindex]:not([tabindex="-1"]), [contenteditable="true"]';

/** Focusable, visible elements inside a container, in DOM order. */
export function focusableIn(container: HTMLElement): HTMLElement[] {
  return Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
    (el) => el.getClientRects().length > 0 && !el.closest("[inert]"),
  );
}

let savedOverflow = "";
let savedPaddingRight = "";

function lockPage() {
  const body = document.body;
  savedOverflow = body.style.overflow;
  savedPaddingRight = body.style.paddingRight;
  const scrollbar = window.innerWidth - document.documentElement.clientWidth;
  body.style.overflow = "hidden";
  if (scrollbar > 0) body.style.paddingRight = `${scrollbar}px`;
  document.getElementById("root")?.setAttribute("inert", "");
}

function unlockPage() {
  const body = document.body;
  body.style.overflow = savedOverflow;
  body.style.paddingRight = savedPaddingRight;
  document.getElementById("root")?.removeAttribute("inert");
}

interface OverlayOptions {
  open: boolean;
  onClose: () => void;
  /** The dialog panel: focus is trapped inside it. */
  panelRef: RefObject<HTMLElement | null>;
  /** Element to focus on open; default the first focusable in the panel other than its close button, else the panel. */
  initialFocusRef?: RefObject<HTMLElement | null>;
  /** Escape closes (default true). */
  closeOnEscape?: boolean;
}

/**
 * Shared behaviour of Modal and Drawer: page scroll lock and `inert` on #root while any overlay is
 * open, focus moved in on open and restored on close, Tab trapped inside the top overlay, Escape
 * closing only the top overlay.
 */
export function useOverlay({ open, onClose, panelRef, initialFocusRef, closeOnEscape = true }: OverlayOptions) {
  const id = useId();
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;
  const escRef = useRef(closeOnEscape);
  escRef.current = closeOnEscape;

  useEffect(() => {
    if (!open) return;
    const restoreTo = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    if (stack.size === 0) lockPage();
    stack.push(id);

    const focusFirst = () => {
      const panel = panelRef.current;
      if (!panel) return;
      const firstControl = focusableIn(panel).find((el) => !el.hasAttribute("data-overlay-close"));
      const target = initialFocusRef?.current ?? firstControl ?? panel;
      target.focus({ preventScroll: true });
    };
    const raf = window.requestAnimationFrame(focusFirst);

    const onKey = (e: KeyboardEvent) => {
      if (!stack.isTop(id)) return;
      if (e.key === "Escape" && escRef.current) {
        e.stopPropagation();
        onCloseRef.current();
        return;
      }
      if (e.key !== "Tab") return;
      const panel = panelRef.current;
      if (!panel) return;
      const items = focusableIn(panel);
      if (items.length === 0) {
        e.preventDefault();
        panel.focus({ preventScroll: true });
        return;
      }
      const current = items.indexOf(document.activeElement as HTMLElement);
      const atEdge =
        current === -1 || (e.shiftKey ? current === 0 : current === items.length - 1);
      if (!atEdge) return;
      e.preventDefault();
      items[nextFocusIndex(current, items.length, e.shiftKey)]?.focus();
    };
    document.addEventListener("keydown", onKey, true);

    return () => {
      window.cancelAnimationFrame(raf);
      document.removeEventListener("keydown", onKey, true);
      stack.remove(id);
      if (stack.size === 0) unlockPage();
      if (restoreTo && document.contains(restoreTo)) restoreTo.focus({ preventScroll: true });
    };
    // panelRef / initialFocusRef are stable refs; re-run only when opening or closing.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, id]);
}
