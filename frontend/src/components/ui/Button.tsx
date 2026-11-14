import { forwardRef } from "react";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cx } from "./logic";
import { Spinner } from "./Spinner";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
/** md = 44px (touch, the default everywhere on phone); sm = 36px on tablet/desktop (dense rows,
 * toolbars) and 44px on phones (< 640px: design/README "vùng chạm tối thiểu 44px"). */
export type ButtonSize = "md" | "sm";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  /** Shows a spinner in place of the leading icon and disables the button. */
  loading?: boolean;
  /** Icon before the label (an <Icon… /> element; sized by the button). */
  icon?: ReactNode;
  /** Icon after the label. */
  iconEnd?: ReactNode;
  /** Full width of its container. */
  block?: boolean;
}

const BASE =
  "inline-flex shrink-0 select-none items-center justify-center gap-2 rounded-full font-semibold whitespace-nowrap " +
  "transition-[background-color,color,box-shadow,transform] duration-150 active:scale-[0.98] motion-reduce:active:scale-100 " +
  "disabled:pointer-events-none disabled:opacity-60";

const VARIANT: Record<ButtonVariant, string> = {
  primary: "bg-accent text-on-accent hover:bg-accent-strong",
  secondary: "bg-surface-2 text-fg hover:bg-surface-3",
  ghost: "bg-transparent text-muted hover:bg-surface-2 hover:text-fg",
  danger: "bg-transparent text-danger ring-1 ring-inset ring-danger/50 hover:bg-danger/10",
};

const SIZE: Record<ButtonSize, string> = {
  md: "h-11 px-5 text-[15px] [&_svg]:text-[18px]",
  sm: "h-9 px-4 text-[14px] [&_svg]:text-[16px] max-sm:h-11",
};

/**
 * Text button. One filled primary per screen; secondary is a tone step; ghost is text; danger is an
 * outline in the negative colour. Pill shaped. Keep one size per row.
 */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "secondary", size = "md", loading = false, icon, iconEnd, block = false, className, children, disabled, type, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type ?? "button"}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={cx(BASE, VARIANT[variant], SIZE[size], block && "w-full", className)}
      {...rest}
    >
      {loading ? <Spinner size={size === "md" ? 18 : 16} /> : icon}
      {children}
      {iconEnd}
    </button>
  );
});

export type IconButtonVariant = "ghost" | "secondary" | "primary" | "orb";

export interface IconButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children" | "aria-label"> {
  /** Accessible name, also shown as the tooltip. Required: an icon alone says nothing to a screen reader. */
  label: string;
  icon: ReactNode;
  /** ghost (default) | secondary (tone step) | primary (accent fill) | orb (brand gradient: send button only). */
  variant?: IconButtonVariant;
  /** md = 44px (default, touch), sm = 36px (44px on phones). */
  size?: ButtonSize;
  /** Toggle state: sets aria-pressed and the pressed look. */
  pressed?: boolean;
  loading?: boolean;
  /** Hide the native tooltip (e.g. when a visible label sits next to it). */
  noTooltip?: boolean;
}

const ICON_VARIANT: Record<IconButtonVariant, string> = {
  ghost: "text-muted hover:bg-surface-2 hover:text-fg",
  secondary: "bg-surface-2 text-fg hover:bg-surface-3",
  primary: "bg-accent text-on-accent hover:bg-accent-strong",
  orb: "bg-grad-orb text-on-orb shadow-orb hover:brightness-105",
};

const ICON_SIZE: Record<ButtonSize, string> = {
  md: "h-11 w-11 text-[20px]",
  sm: "h-9 w-9 text-[18px] max-sm:h-11 max-sm:w-11",
};

/** Round icon-only button with a required accessible label. */
export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(function IconButton(
  { label, icon, variant = "ghost", size = "md", pressed, loading = false, noTooltip = false, className, disabled, type, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type ?? "button"}
      aria-label={label}
      title={noTooltip ? undefined : label}
      aria-pressed={pressed}
      aria-busy={loading || undefined}
      disabled={disabled || loading}
      className={cx(
        "inline-flex shrink-0 items-center justify-center rounded-full transition-[background-color,color,transform,filter] duration-150",
        "active:scale-[0.96] motion-reduce:active:scale-100 disabled:pointer-events-none disabled:opacity-50",
        ICON_VARIANT[variant],
        ICON_SIZE[size],
        pressed && variant === "ghost" && "bg-surface-2 text-fg",
        className,
      )}
      {...rest}
    >
      {loading ? <Spinner size={size === "md" ? 18 : 16} /> : icon}
    </button>
  );
});
