import { useEffect, useId, useRef, useState } from "react";
import { IconCheck, IconChevronDown, IconEye, IconEyeOff } from "../../components/icons";
import { Button, Toggle, cx } from "../../components/ui";
import { SHOW_THOUGHTS_LABEL, showThoughtsHint, THOUGHT_STYLE_OPTIONS } from "../../lib/storyOptions";
import type { ThoughtStyle } from "../../types";
import { useRevealThoughts } from "./revealThoughts";

interface Props {
  value: ThoughtStyle;
  /** The style cannot change right now (a reply is streaming, a save is running). */
  disabled: boolean;
  onChange: (style: ThoughtStyle) => void;
  /** Phase 4 (B): the story shows thought cards (saved on the story, so every device agrees). */
  showThoughts: boolean;
  /** Saves "Đọc suy nghĩ của nhân vật" at once (optimistic; the page rolls back if refused). */
  onChangeShowThoughts: (show: boolean) => void;
  /** That switch is being saved. It stays usable while a reply streams (display only). */
  showThoughtsSaving?: boolean;
  characterName: string;
}

/**
 * "Suy nghĩ" menu in the chat header: "Đọc suy nghĩ của nhân vật" (saved on the story, Phase 4), the
 * "Luôn hiện suy nghĩ" switch (this device; hidden while thoughts are not read, nothing left to blur)
 * and where the character's thoughts go in Story Mode (inline or one at the end; saved on the story).
 * With thoughts off the button shows an eye-off icon and says so to screen readers.
 */
export function ThoughtMenu({
  value,
  disabled,
  onChange,
  showThoughts,
  onChangeShowThoughts,
  showThoughtsSaving = false,
  characterName,
}: Props) {
  const [open, setOpen] = useState(false);
  const [always, setAlways] = useRevealThoughts();
  const root = useRef<HTMLDivElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const panelId = useId();
  const groupId = useId();

  useEffect(() => {
    if (!open) return;
    panel.current?.querySelector<HTMLElement>("button")?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        setOpen(false);
        trigger.current?.focus();
      }
    };
    const onDown = (e: PointerEvent) => {
      if (root.current && !root.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onDown);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onDown);
    };
  }, [open]);

  return (
    <div ref={root} className="relative">
      <Button
        ref={trigger}
        size="sm"
        variant="ghost"
        icon={showThoughts ? <IconEye /> : <IconEyeOff />}
        aria-label={showThoughts ? undefined : "Suy nghĩ (đang ẩn)"}
        iconEnd={<IconChevronDown className={cx("transition-transform duration-150", open && "rotate-180")} />}
        aria-expanded={open}
        aria-controls={open ? panelId : undefined}
        aria-haspopup="dialog"
        onClick={() => setOpen((o) => !o)}
        className={cx("px-3", open && "bg-surface-2 text-fg")}
      >
        Suy nghĩ
      </Button>
      {open && (
        <div
          ref={panel}
          id={panelId}
          role="dialog"
          aria-label="Suy nghĩ của nhân vật"
          className="absolute top-full right-0 z-30 mt-2 w-[min(20rem,calc(100vw-2rem))] rounded-card bg-surface p-2 shadow-float"
        >
          <div className="flex flex-col gap-1 px-3">
            <Toggle
              label={SHOW_THOUGHTS_LABEL}
              description={showThoughtsHint(characterName)}
              checked={showThoughts}
              onChange={onChangeShowThoughts}
              busy={showThoughtsSaving}
            />
            {showThoughts && (
              <Toggle
                label="Luôn hiện suy nghĩ"
                description="Không làm mờ thẻ suy nghĩ, khỏi phải chạm để đọc."
                checked={always}
                onChange={setAlways}
              />
            )}
          </div>
          <p id={groupId} className="mt-3 px-3 pb-1.5 text-[13px] font-medium text-muted">
            Ở Story, suy nghĩ nằm
          </p>
          <div role="radiogroup" aria-labelledby={groupId} className="flex flex-col gap-1">
            {THOUGHT_STYLE_OPTIONS.map((o) => {
              const active = o.value === value;
              return (
                <button
                  key={o.value}
                  type="button"
                  role="radio"
                  aria-checked={active}
                  disabled={disabled}
                  onClick={() => {
                    if (!active) onChange(o.value);
                  }}
                  className={cx(
                    "rounded-control px-3 py-2.5 text-left transition-colors duration-150 disabled:opacity-60",
                    active ? "bg-surface-2" : "hover:bg-surface-2",
                  )}
                >
                  <span className="flex items-center justify-between gap-2 text-[15px] font-medium text-fg">
                    {o.label}
                    {active && <IconCheck aria-hidden="true" className="shrink-0 text-[16px] text-accent" />}
                  </span>
                  <span className="mt-0.5 block text-[13px] leading-snug text-muted">{o.hint}</span>
                </button>
              );
            })}
          </div>
          {!showThoughts && (
            <p className="px-3 pt-2 text-[13px] leading-snug text-muted">
              Nhân vật vẫn nghĩ trong lòng theo kiểu này, chỉ là bạn không đọc thấy.
            </p>
          )}
          <p className="px-3 pt-2 pb-1 text-[12px] leading-snug text-muted">Kiểu suy nghĩ áp dụng từ lượt trả lời tiếp theo.</p>
        </div>
      )}
    </div>
  );
}
