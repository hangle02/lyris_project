import { useEffect, useId, useRef, useState } from "react";
import type { KeyboardEvent, ReactNode, RefObject } from "react";
import { IconClock, IconImage, IconMessageCircle, IconPlus } from "../../components/icons";
import { Badge, cx } from "../../components/ui";
import { nextEnabledIndex } from "./suggestLogic";
import type { ComposerAction, ComposerActionId } from "./suggestLogic";

const ICONS: Record<ComposerActionId, ReactNode> = {
  suggest: <IconMessageCircle />,
  events: <IconClock />,
  image: <IconImage />,
};

interface Props {
  actions: ComposerAction[];
  onSelect: (id: ComposerActionId) => void;
  disabled?: boolean;
  /** The "+" button, for a parent that moves focus back to it (e.g. after closing the suggestions). */
  triggerRef?: RefObject<HTMLButtonElement>;
}

/**
 * The composer's "+" (Phase 3b): a 44px button left of the input that opens a small menu of extra
 * actions (data from suggestLogic.composerActions). From 640px the menu is a popover above the
 * button; on phones a sheet from the bottom over a scrim. Arrow keys / Home / End move between
 * items (disabled ones too, so their reason is read), Enter or Space picks, Escape and a click
 * outside close it, and focus returns to "+".
 */
export function ComposerMenu({ actions, onSelect, disabled = false, triggerRef }: Props) {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const rootRef = useRef<HTMLDivElement>(null);
  const ownButtonRef = useRef<HTMLButtonElement>(null);
  const buttonRef = triggerRef ?? ownButtonRef;
  const itemRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const menuId = useId();

  const close = (refocus: boolean) => {
    setOpen(false);
    if (refocus) buttonRef.current?.focus();
  };

  // Opening focuses the first action that can run (else the first item).
  useEffect(() => {
    if (!open) return;
    const first = nextEnabledIndex(actions, -1, 1);
    const index = first === -1 ? 0 : first;
    setActive(index);
    const raf = window.requestAnimationFrame(() => itemRefs.current[index]?.focus());
    return () => window.cancelAnimationFrame(raf);
    // Only when it opens: the list may change while open (a reply finishing) without moving focus.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  // A press outside closes it (focus goes where the press went).
  useEffect(() => {
    if (!open) return;
    const onDown = (e: PointerEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", onDown, true);
    return () => document.removeEventListener("pointerdown", onDown, true);
  }, [open]);

  useEffect(() => {
    if (disabled) setOpen(false);
  }, [disabled]);

  const move = (to: number) => {
    const n = actions.length;
    if (n === 0) return;
    const i = ((to % n) + n) % n;
    setActive(i);
    itemRefs.current[i]?.focus();
  };

  const onMenuKey = (e: KeyboardEvent<HTMLDivElement>) => {
    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        move(active + 1);
        break;
      case "ArrowUp":
        e.preventDefault();
        move(active - 1);
        break;
      case "Home":
        e.preventDefault();
        move(0);
        break;
      case "End":
        e.preventDefault();
        move(actions.length - 1);
        break;
      case "Escape":
        e.preventDefault();
        e.stopPropagation();
        close(true);
        break;
      case "Tab":
        // Leaving the menu with Tab closes it; focus moves on as usual.
        setOpen(false);
        break;
    }
  };

  const pick = (a: ComposerAction) => {
    if (a.disabled) return;
    close(true);
    onSelect(a.id);
  };

  return (
    <div ref={rootRef} className="relative shrink-0">
      <button
        ref={buttonRef}
        type="button"
        aria-label="Thêm"
        title="Thêm: gợi ý, sự kiện…"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        disabled={disabled}
        onClick={() => setOpen((o) => !o)}
        onKeyDown={(e) => {
          if (e.key === "ArrowUp" || e.key === "ArrowDown") {
            e.preventDefault();
            setOpen(true);
          }
        }}
        className={cx(
          "inline-flex h-11 w-11 items-center justify-center rounded-full text-[22px] text-muted transition-colors duration-150",
          "hover:bg-surface-2 hover:text-fg disabled:opacity-50",
          open && "bg-surface-2 text-fg",
        )}
      >
        <IconPlus className={cx("transition-transform duration-150 motion-reduce:transition-none", open && "rotate-45")} />
      </button>

      {open && (
        <>
          {/* Phones: the menu is a bottom sheet over a scrim (a tap on it closes). */}
          <div aria-hidden="true" className="fixed inset-0 z-40 bg-scrim sm:hidden" onClick={() => setOpen(false)} />
          <div
            id={menuId}
            role="menu"
            aria-label="Thêm"
            onKeyDown={onMenuKey}
            className={cx(
              "z-50 flex flex-col border border-line bg-surface p-2 shadow-float",
              "max-sm:fixed max-sm:inset-x-0 max-sm:bottom-0 max-sm:rounded-t-card max-sm:border-b-0 max-sm:pb-[max(0.75rem,env(safe-area-inset-bottom))]",
              "sm:absolute sm:bottom-full sm:left-0 sm:mb-2 sm:w-[300px] sm:rounded-card",
            )}
          >
            <div aria-hidden="true" className="mx-auto mt-1 mb-2 h-1 w-10 rounded-full bg-line-strong sm:hidden" />
            {actions.map((a, i) => {
              const hintId = `${menuId}-${a.id}-hint`;
              return (
                <button
                  key={a.id}
                  ref={(el) => {
                    itemRefs.current[i] = el;
                  }}
                  type="button"
                  role="menuitem"
                  tabIndex={i === active ? 0 : -1}
                  aria-disabled={a.disabled || undefined}
                  aria-describedby={a.hint ? hintId : undefined}
                  onClick={() => pick(a)}
                  onFocus={() => setActive(i)}
                  className={cx(
                    "flex min-h-14 w-full items-center gap-3.5 rounded-control px-3 py-2 text-left outline-none transition-colors duration-150",
                    "focus-visible:bg-surface-2 focus-visible:ring-2 focus-visible:ring-accent/60",
                    a.disabled ? "cursor-default" : "hover:bg-surface-2",
                  )}
                >
                  <span aria-hidden="true" className={cx("shrink-0 text-[20px]", a.disabled ? "text-faint" : "text-muted")}>
                    {ICONS[a.id]}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="flex items-center gap-2">
                      <span className={cx("text-[15px] leading-tight font-medium", a.disabled ? "text-muted" : "text-fg")}>
                        {a.label}
                      </span>
                      {a.soon && <Badge>Sắp có</Badge>}
                    </span>
                    {a.hint && (
                      <span id={hintId} className="mt-0.5 block text-[13px] leading-snug text-muted">
                        {a.hint}
                      </span>
                    )}
                  </span>
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
