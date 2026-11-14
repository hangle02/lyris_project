import { forwardRef, useId } from "react";
import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes } from "react";
import { AutoTextarea } from "../AutoTextarea";
import { IconChevronDown } from "../icons";
import { cx, switchState } from "./logic";

/**
 * Class of every text control: 44px min height, 14px radius, pressed-linen fill (surface-2) with a
 * 1px hairline, 16px text (iOS does not zoom), faint placeholder (4.5:1), accent edge on focus.
 */
export const CONTROL_CLASS =
  "w-full min-w-0 min-h-11 rounded-control border border-line bg-surface-2 px-3.5 py-2.5 text-[16px] leading-snug text-fg " +
  "placeholder:text-faint outline-none transition-colors duration-150 focus:border-accent " +
  "focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60 aria-[invalid=true]:border-danger";

export interface FieldProps {
  label: string;
  hint?: ReactNode;
  /** Error text shown under the control in the negative colour. */
  error?: ReactNode;
  /** id of the control the label names. */
  htmlFor?: string;
  /** Keep the label for screen readers only (e.g. a search box with a visible icon). */
  hideLabel?: boolean;
  /** ids for aria-describedby (set by the controls below). */
  hintId?: string;
  errorId?: string;
  /** Right side of the label row (a counter, a small button). */
  extra?: ReactNode;
  className?: string;
  children: ReactNode;
}

/** Label above, the control, then hint or error. 8px between label and control. */
export function Field({
  label,
  hint,
  error,
  htmlFor,
  hideLabel = false,
  hintId,
  errorId,
  extra,
  className,
  children,
}: FieldProps) {
  const labelEl = (
    <label
      htmlFor={htmlFor}
      className={cx("min-w-0 text-[14px] leading-tight font-medium text-fg", extra ? "flex-1" : null, hideLabel && "sr-only")}
    >
      {label}
    </label>
  );
  return (
    <div className={cx("flex min-w-0 flex-col gap-2", className)}>
      {extra ? (
        <div className="flex min-h-5 items-center gap-2">
          {labelEl}
          {extra}
        </div>
      ) : (
        labelEl
      )}
      {children}
      {error ? (
        <p id={errorId} className="text-[13px] leading-snug text-danger">
          {error}
        </p>
      ) : (
        hint && (
          <p id={hintId} className="text-[13px] leading-snug text-muted">
            {hint}
          </p>
        )
      )}
    </div>
  );
}

function describedBy(hint: ReactNode, error: ReactNode, hintId: string, errorId: string): string | undefined {
  if (error) return errorId;
  if (hint) return hintId;
  return undefined;
}

export interface TextFieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "value" | "onChange" | "size"> {
  label: string;
  value: string;
  onChange: (value: string) => void;
  hint?: ReactNode;
  error?: ReactNode;
  /** Leading icon inside the field (e.g. <IconSearch />). */
  icon?: ReactNode;
  /** A small control at the right end inside the field (Phase 4b: "Hiện"/"Ẩn" of a password). */
  trailing?: ReactNode;
  hideLabel?: boolean;
  /** Class for the outer Field wrapper. */
  className?: string;
  /** Extra classes for the <input>. */
  inputClassName?: string;
}

/** Single-line text input with its label above. */
export const TextField = forwardRef<HTMLInputElement, TextFieldProps>(function TextField(
  { label, value, onChange, hint, error, icon, trailing, hideLabel, className, inputClassName, id, ...rest },
  ref,
) {
  const auto = useId();
  const inputId = id ?? auto;
  const hintId = `${inputId}-hint`;
  const errorId = `${inputId}-error`;
  return (
    <Field
      label={label}
      hint={hint}
      error={error}
      htmlFor={inputId}
      hideLabel={hideLabel}
      hintId={hintId}
      errorId={errorId}
      className={className}
    >
      <div className="relative min-w-0">
        {icon && (
          <span aria-hidden="true" className="pointer-events-none absolute top-1/2 left-3.5 -translate-y-1/2 text-[18px] text-muted">
            {icon}
          </span>
        )}
        <input
          ref={ref}
          id={inputId}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy(hint, error, hintId, errorId)}
          className={cx(CONTROL_CLASS, icon ? "pl-11" : null, trailing ? "pr-[4.5rem]" : null, inputClassName)}
          {...rest}
        />
        {trailing && <span className="absolute inset-y-0 right-1 flex items-center">{trailing}</span>}
      </div>
    </Field>
  );
});

export interface TextAreaProps extends Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, "value" | "onChange"> {
  label: string;
  value: string;
  onChange: (value: string) => void;
  hint?: ReactNode;
  error?: ReactNode;
  /** Grows with its content up to this height in px, then scrolls (default 260). */
  maxHeight?: number;
  hideLabel?: boolean;
  className?: string;
  inputClassName?: string;
}

/** Multi-line text that grows with its content; label above. */
export const TextArea = forwardRef<HTMLTextAreaElement, TextAreaProps>(function TextArea(
  { label, value, onChange, hint, error, maxHeight = 260, hideLabel, className, inputClassName, id, ...rest },
  ref,
) {
  const auto = useId();
  const inputId = id ?? auto;
  const hintId = `${inputId}-hint`;
  const errorId = `${inputId}-error`;
  return (
    <Field
      label={label}
      hint={hint}
      error={error}
      htmlFor={inputId}
      hideLabel={hideLabel}
      hintId={hintId}
      errorId={errorId}
      className={className}
    >
      <AutoTextarea
        ref={ref}
        id={inputId}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        maxHeight={maxHeight}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy(hint, error, hintId, errorId)}
        className={cx(CONTROL_CLASS, "min-h-[5.5rem]", inputClassName)}
        {...rest}
      />
    </Field>
  );
});

export interface SelectOption<T extends string> {
  value: T;
  label: string;
  disabled?: boolean;
}

export interface SelectProps<T extends string>
  extends Omit<SelectHTMLAttributes<HTMLSelectElement>, "value" | "onChange" | "children"> {
  label: string;
  value: T;
  onChange: (value: T) => void;
  options: ReadonlyArray<SelectOption<T>>;
  hint?: ReactNode;
  error?: ReactNode;
  /** Shown as a disabled first option when value matches none of the options (e.g. ""). */
  placeholder?: string;
  hideLabel?: boolean;
  className?: string;
}

/** Native select (system picker on iPhone) styled like the text controls, chevron on the right. */
export function Select<T extends string>({
  label,
  value,
  onChange,
  options,
  hint,
  error,
  placeholder,
  hideLabel,
  className,
  id,
  ...rest
}: SelectProps<T>) {
  const auto = useId();
  const selectId = id ?? auto;
  const hintId = `${selectId}-hint`;
  const errorId = `${selectId}-error`;
  const known = options.some((o) => o.value === value);
  return (
    <Field
      label={label}
      hint={hint}
      error={error}
      htmlFor={selectId}
      hideLabel={hideLabel}
      hintId={hintId}
      errorId={errorId}
      className={className}
    >
      <div className="relative min-w-0">
        <select
          id={selectId}
          value={value}
          onChange={(e) => onChange(e.target.value as T)}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy(hint, error, hintId, errorId)}
          className={cx(CONTROL_CLASS, "appearance-none truncate pr-10")}
          {...rest}
        >
          {!known && (
            <option value={value} disabled>
              {placeholder ?? "Chọn…"}
            </option>
          )}
          {options.map((o) => (
            <option key={o.value} value={o.value} disabled={o.disabled}>
              {o.label}
            </option>
          ))}
        </select>
        <IconChevronDown
          aria-hidden="true"
          className="pointer-events-none absolute top-1/2 right-3.5 -translate-y-1/2 text-[18px] text-muted"
        />
      </div>
    </Field>
  );
}

export interface ToggleProps {
  label: string;
  description?: ReactNode;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  /** The value is being saved: looks disabled and ignores clicks but keeps keyboard focus. */
  busy?: boolean;
  className?: string;
}

/**
 * Switch row: title (and description) on the left, the switch on the right; the whole row is the
 * hit area. On is ink-coloured (fg), not the accent; off is a tone step.
 */
export function Toggle({ label, description, checked, onChange, disabled, busy, className }: ToggleProps) {
  const titleId = useId();
  const descId = useId();
  const state = switchState(disabled, busy);
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-labelledby={titleId}
      aria-describedby={description ? descId : undefined}
      disabled={state.disabled}
      aria-disabled={state.ariaDisabled}
      aria-busy={state.ariaBusy}
      onClick={() => {
        if (!state.inert) onChange(!checked);
      }}
      className={cx(
        "flex min-h-11 w-full items-center gap-4 rounded-control py-1.5 text-left disabled:cursor-not-allowed disabled:opacity-60 aria-disabled:cursor-not-allowed aria-disabled:opacity-60",
        className,
      )}
    >
      <span className="min-w-0 flex-1">
        <span id={titleId} className="block text-[15px] leading-snug font-medium text-fg">
          {label}
        </span>
        {description && (
          <span id={descId} className="mt-0.5 block text-[13px] leading-snug text-muted">
            {description}
          </span>
        )}
      </span>
      <span
        aria-hidden="true"
        className={cx(
          "relative inline-flex h-6 w-10 shrink-0 rounded-full transition-colors duration-200",
          checked ? "bg-fg" : "bg-surface-3",
        )}
      >
        <span
          className={cx(
            "absolute top-0.5 left-0.5 h-5 w-5 rounded-full transition-transform duration-200 motion-reduce:transition-none",
            checked ? "translate-x-4 bg-bg" : "translate-x-0 bg-muted",
          )}
        />
      </span>
    </button>
  );
}
