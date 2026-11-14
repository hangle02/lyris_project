// Studio-specific building blocks on top of the foundation primitives (components/ui):
// notices, form sections, the {{user}}-aware text area, the chip input,
// the two-step delete dialog and link-styled buttons. Shared with the Persona page.
import { useId, useRef, useState } from "react";
import type { AnchorHTMLAttributes, ReactNode, KeyboardEvent as ReactKeyboardEvent } from "react";
import { ApiError, errorMessage } from "../../api/client";
import { AutoTextarea } from "../../components/AutoTextarea";
import { IconX } from "../../components/icons";
import { Button, CONTROL_CLASS, ErrorDetails, Field, IconButton, Modal, Spinner, TextField as UiTextField, cx } from "../../components/ui";
import { formatRelativeTime, splitList } from "../../lib/cardForm";

export { Field, Spinner };

// ---- link that looks like a Button (navigation and downloads must stay <a>) ----

type LinkVariant = "primary" | "secondary" | "ghost";

const LINK_BASE =
  "inline-flex shrink-0 select-none items-center justify-center gap-2 rounded-full font-semibold whitespace-nowrap " +
  "transition-[background-color,color] duration-150 aria-disabled:pointer-events-none aria-disabled:opacity-60";
const LINK_VARIANT: Record<LinkVariant, string> = {
  primary: "bg-accent text-on-accent hover:bg-accent-strong",
  secondary: "bg-surface-2 text-fg hover:bg-surface-3",
  ghost: "bg-transparent text-muted hover:bg-surface-2 hover:text-fg",
};
const LINK_SIZE = {
  md: "h-11 px-5 text-[15px] [&_svg]:text-[18px]",
  sm: "h-9 px-4 text-[14px] [&_svg]:text-[16px]",
} as const;

export function LinkButton({
  variant = "secondary",
  size = "md",
  icon,
  className,
  children,
  ...rest
}: AnchorHTMLAttributes<HTMLAnchorElement> & {
  variant?: LinkVariant;
  size?: "md" | "sm";
  icon?: ReactNode;
}) {
  return (
    <a className={cx(LINK_BASE, LINK_VARIANT[variant], LINK_SIZE[size], className)} {...rest}>
      {icon}
      {children}
    </a>
  );
}

// ---- notices ----

const NOTICE_TONE = {
  error: { box: "bg-danger/10", dot: "bg-danger" },
  warn: { box: "bg-warn/10", dot: "bg-warn" },
  info: { box: "bg-surface-2", dot: null },
  ok: { box: "bg-ok/10", dot: "bg-ok" },
} as const;

/**
 * A message inside the block it concerns: a flat tint of its tone, a small dot of the tone, text
 * in ink. Never a full-screen banner.
 */
export function Notice({
  tone,
  title,
  lines,
  onDismiss,
  action,
  technical,
}: {
  tone: "error" | "warn" | "info" | "ok";
  title?: string;
  lines: string[];
  onDismiss?: () => void;
  action?: ReactNode;
  /** The raw technical text of an error, under a small "Chi tiết" disclosure (Phase 3b). */
  technical?: string | null;
}) {
  if (!title && lines.length === 0) return null;
  const t = NOTICE_TONE[tone];
  return (
    <div
      role={tone === "error" ? "alert" : "status"}
      className={cx("flex items-start gap-3 rounded-control px-4 py-3 text-[14px] leading-snug", t.box)}
    >
      {t.dot && <span aria-hidden="true" className={cx("mt-[7px] h-2 w-2 shrink-0 rounded-full", t.dot)} />}
      <div className={cx("min-w-0 flex-1 [overflow-wrap:anywhere]", tone === "info" ? "text-muted" : "text-fg")}>
        {title && <p className="font-semibold">{title}</p>}
        {lines.length === 1 && <p className={title ? "mt-1" : undefined}>{lines[0]}</p>}
        {lines.length > 1 && (
          <ul className={cx("list-disc space-y-1 pl-4", title && "mt-1")}>
            {lines.map((l, i) => (
              <li key={i}>{l}</li>
            ))}
          </ul>
        )}
        <ErrorDetails technical={technical} className="mt-1.5" />
        {action && <div className="mt-3">{action}</div>}
      </div>
      {onDismiss && (
        <IconButton label="Đóng thông báo" icon={<IconX />} size="sm" onClick={onDismiss} className="-my-1.5 -mr-2" />
      )}
    </div>
  );
}

// ---- form pieces ----

/** A form section: a card with an h2, an optional one-line hint and a right-side slot. */
export function Section({
  id,
  title,
  hint,
  children,
  aside,
}: {
  id?: string;
  title: string;
  hint?: ReactNode;
  children: ReactNode;
  aside?: ReactNode;
}) {
  const headingId = useId();
  return (
    <section
      id={id}
      aria-labelledby={headingId}
      className="scroll-mt-4 rounded-card border border-edge bg-surface p-4 sm:p-5"
    >
      <div className="mb-5 flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <h2 id={headingId} className="text-[16px] leading-tight font-semibold text-fg">
            {title}
          </h2>
          {hint && <p className="mt-1.5 text-[14px] leading-snug text-muted">{hint}</p>}
        </div>
        {aside}
      </div>
      <div className="flex flex-col gap-5">{children}</div>
    </section>
  );
}

/** The "{{user}}" token, written out where a hint explains it. */
export function UserPlaceholderBadge() {
  return (
    <span
      title="Dùng {{user}} để chỉ nhân vật của người chơi; khi tạo story nó được thay bằng tên persona."
      className="rounded-full bg-surface-2 px-2 py-0.5 text-[13px] font-medium whitespace-nowrap text-fg"
    >
      {"{{user}}"}
    </span>
  );
}

/**
 * Growing textarea with its label, an optional "+ {{user}}" button that inserts the placeholder at
 * the cursor, and a length counter once the text gets long.
 */
export function TextAreaField({
  label,
  hint,
  value,
  onChange,
  placeholder,
  userPlaceholder = false,
  minRows = 2,
  maxHeight = 360,
  maxChars,
  disabled,
}: {
  label: string;
  hint?: ReactNode;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  /** Show the insert-{{user}} button. */
  userPlaceholder?: boolean;
  minRows?: number;
  maxHeight?: number;
  maxChars?: number;
  disabled?: boolean;
}) {
  const id = useId();
  const ref = useRef<HTMLTextAreaElement>(null);
  const insertUser = () => {
    const el = ref.current;
    const token = "{{user}}";
    if (!el) {
      onChange(value + token);
      return;
    }
    const start = el.selectionStart ?? value.length;
    const end = el.selectionEnd ?? value.length;
    onChange(value.slice(0, start) + token + value.slice(end));
    requestAnimationFrame(() => {
      el.focus();
      el.setSelectionRange(start + token.length, start + token.length);
    });
  };
  const showCounter = maxChars !== undefined && value.length > maxChars * 0.8;
  const over = maxChars !== undefined && value.length > maxChars;
  return (
    <Field
      label={label}
      hint={hint}
      htmlFor={id}
      extra={
        (showCounter || userPlaceholder) && (
          <span className="flex shrink-0 items-center gap-2">
            {showCounter && (
              <span className={cx("text-[12px] tabular-nums", over ? "text-danger" : "text-muted")}>
                {value.length.toLocaleString("vi-VN")}/{maxChars?.toLocaleString("vi-VN")}
              </span>
            )}
            {userPlaceholder && (
              <button
                type="button"
                onClick={insertUser}
                disabled={disabled}
                title="Chèn {{user}} vào vị trí con trỏ"
                className="-my-1 inline-flex h-7 items-center rounded-full px-2.5 text-[13px] font-medium text-muted transition-colors hover:bg-surface-2 hover:text-fg disabled:opacity-50"
              >
                {"+ {{user}}"}
              </button>
            )}
          </span>
        )
      }
    >
      <AutoTextarea
        ref={ref}
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        maxHeight={maxHeight}
        aria-invalid={over || undefined}
        style={{ minHeight: `${minRows * 1.4 + 1.4}em` }}
        className={CONTROL_CLASS}
      />
    </Field>
  );
}

/** Single-line text field (foundation TextField) with the Studio's "required" star. */
export function TextField({
  label,
  hint,
  value,
  onChange,
  placeholder,
  maxLength,
  disabled,
  required,
  onBlur,
  autoFocus,
  error,
}: {
  label: string;
  hint?: ReactNode;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  maxLength?: number;
  disabled?: boolean;
  required?: boolean;
  onBlur?: () => void;
  autoFocus?: boolean;
  error?: ReactNode;
}) {
  return (
    <UiTextField
      label={required ? `${label} *` : label}
      hint={hint}
      error={error}
      value={value}
      onChange={onChange}
      onBlur={onBlur}
      placeholder={placeholder}
      maxLength={maxLength}
      disabled={disabled}
      aria-required={required || undefined}
      autoFocus={autoFocus}
      autoComplete="off"
    />
  );
}

/** List of short strings as removable chips plus an input (Enter or "," adds; pasting a list splits it). */
export function ChipInput({
  label,
  hint,
  values,
  onChange,
  placeholder,
  max,
  disabled,
  normalize,
}: {
  label: string;
  hint?: ReactNode;
  values: string[];
  onChange: (v: string[]) => void;
  placeholder?: string;
  max?: number;
  disabled?: boolean;
  normalize?: (s: string) => string;
}) {
  const id = useId();
  const [text, setText] = useState("");
  const add = (raw: string) => {
    const parts = splitList(raw)
      .map((p) => (normalize ? normalize(p) : p))
      .filter(Boolean);
    if (parts.length === 0) return;
    const seen = new Set(values.map((v) => v.toLocaleLowerCase("vi-VN")));
    const next = [...values];
    for (const p of parts) {
      const key = p.toLocaleLowerCase("vi-VN");
      if (seen.has(key)) continue;
      if (max !== undefined && next.length >= max) break;
      seen.add(key);
      next.push(p);
    }
    onChange(next);
    setText("");
  };
  const onKeyDown = (e: ReactKeyboardEvent<HTMLInputElement>) => {
    if (e.nativeEvent.isComposing || e.keyCode === 229) return;
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      add(text);
    } else if (e.key === "Backspace" && !text && values.length > 0) {
      onChange(values.slice(0, -1));
    }
  };
  const full = max !== undefined && values.length >= max;
  return (
    <Field label={label} hint={hint} htmlFor={id}>
      <div
        className={cx(
          "flex min-h-11 flex-wrap items-center gap-1.5 rounded-control border border-line bg-surface-2 px-2 py-1.5 transition-colors focus-within:border-accent",
          disabled && "opacity-60",
        )}
      >
        {values.map((v, i) => (
          <span
            key={`${v}-${i}`}
            className="inline-flex h-8 max-w-full items-center gap-0.5 rounded-full bg-surface-3 pr-1 pl-3 text-[14px] text-fg"
          >
            <span className="truncate">{v}</span>
            <button
              type="button"
              disabled={disabled}
              onClick={() => onChange(values.filter((_, j) => j !== i))}
              aria-label={`Bỏ “${v}”`}
              className="inline-flex h-6 w-6 items-center justify-center rounded-full text-[14px] text-muted transition-colors hover:bg-surface-2 hover:text-fg"
            >
              <IconX />
            </button>
          </span>
        ))}
        <input
          id={id}
          type="text"
          value={text}
          disabled={disabled || full}
          onChange={(e) => {
            const v = e.target.value;
            if (/[,;\n]/.test(v)) add(v);
            else setText(v);
          }}
          onKeyDown={onKeyDown}
          onBlur={() => text.trim() && add(text)}
          placeholder={full ? `Tối đa ${max}` : values.length === 0 ? placeholder : "Thêm…"}
          autoComplete="off"
          className="h-8 min-w-[8rem] flex-1 bg-transparent px-1.5 text-[16px] text-fg outline-none placeholder:text-faint"
        />
      </div>
    </Field>
  );
}

// ---- dialogs ----

/**
 * Two-step delete: confirm, then call `run(false)`. A 409 (stories still use the item) switches to a
 * second step that explains the loss and calls `run(true)`.
 */
export function DeleteDialog({
  title,
  body,
  storyCount,
  run,
  onClose,
  onDeleted,
}: {
  title: string;
  body: ReactNode;
  /** Known number of stories using the item (shown in the first step when > 0). */
  storyCount?: number;
  run: (withStories: boolean) => Promise<unknown>;
  onClose: () => void;
  onDeleted: () => void;
}) {
  const [step, setStep] = useState<"confirm" | "inUse">("confirm");
  const [inUseText, setInUseText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const go = async (withStories: boolean) => {
    setBusy(true);
    setError(null);
    try {
      await run(withStories);
      onDeleted();
    } catch (e) {
      if (!withStories && e instanceof ApiError && e.status === 409) {
        setInUseText(e.message);
        setStep("inUse");
      } else {
        setError(errorMessage(e));
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal
      open
      title={title}
      size="sm"
      onClose={() => !busy && onClose()}
      dismissible={!busy}
      footer={
        <>
          <Button variant="ghost" size="sm" onClick={onClose} disabled={busy}>
            Huỷ
          </Button>
          {step === "confirm" ? (
            <Button variant="danger" size="sm" loading={busy} onClick={() => void go(false)}>
              Xoá
            </Button>
          ) : (
            <Button variant="danger" size="sm" loading={busy} onClick={() => void go(true)}>
              Xoá luôn các story
            </Button>
          )}
        </>
      }
    >
      <div className="flex flex-col gap-3 text-[15px] leading-relaxed text-prose">
        {step === "confirm" ? (
          <>
            <div>{body}</div>
            {storyCount !== undefined && storyCount > 0 && (
              <p className="text-[14px] text-muted">
                Đang có {storyCount} story dùng mục này. Bạn sẽ được hỏi lại trước khi xoá các story đó.
              </p>
            )}
          </>
        ) : (
          <Notice
            tone="error"
            title={inUseText || "Có story đang dùng mục này."}
            lines={[
              "Xoá luôn sẽ xoá các story đó cùng toàn bộ tin nhắn, đánh giá và lịch sử sửa (mất dữ liệu dùng để train). Không hoàn tác được.",
            ]}
          />
        )}
        {error && <Notice tone="error" lines={[error]} />}
      </div>
    </Modal>
  );
}

/** "vừa xong", "3 giờ trước", "12/11/2026" (see lib/cardForm formatRelativeTime). */
export function formatDate(iso: string | null | undefined): string {
  return formatRelativeTime(iso);
}
