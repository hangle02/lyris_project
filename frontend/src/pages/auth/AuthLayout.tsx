import type { ReactNode } from "react";
import { forwardRef, useState } from "react";
import { Wordmark } from "../../components/brand";
import { Button, TextField } from "../../components/ui";
import type { TextFieldProps } from "../../components/ui";
import { ThemeToggle } from "../../theme";
import { TAGLINE } from "./logic";

/**
 * Frame of the sign-in screens (docs/auth.md §7.3): centred column, at most 400px wide, 20px side
 * margins; the wordmark and the DESIGN.md tagline on top, the screen's h1, then the form. The theme
 * switch sits in the corner like on the hub.
 */
export function AuthLayout({ title, intro, children }: { title: string; intro?: ReactNode; children: ReactNode }) {
  return (
    <div className="relative flex min-h-dvh flex-col bg-bg">
      <div className="absolute top-0 right-0 pt-safe">
        <div className="p-2">
          <ThemeToggle />
        </div>
      </div>
      <main className="mx-auto flex w-full max-w-[400px] flex-1 flex-col justify-center gap-7 px-5 pt-[max(4rem,env(safe-area-inset-top))] pb-[max(2.5rem,env(safe-area-inset-bottom))]">
        <div className="flex flex-col items-start gap-2">
          <Wordmark size={34} />
          <p className="text-[14px] leading-snug text-muted">{TAGLINE}</p>
        </div>
        <div className="flex flex-col gap-2">
          <h1 className="text-[24px] leading-tight font-semibold text-fg">{title}</h1>
          {intro && <p className="text-[14px] leading-relaxed text-muted">{intro}</p>}
        </div>
        {children}
      </main>
    </div>
  );
}

/** Password input with a ghost "Hiện" / "Ẩn" at the right end. Never trims what is typed. */
export const PasswordField = forwardRef<HTMLInputElement, Omit<TextFieldProps, "type" | "trailing">>(function PasswordField(
  props,
  ref,
) {
  const [shown, setShown] = useState(false);
  return (
    <TextField
      ref={ref}
      {...props}
      type={shown ? "text" : "password"}
      autoCapitalize="none"
      autoCorrect="off"
      spellCheck={false}
      trailing={
        <Button
          size="sm"
          variant="ghost"
          onClick={() => setShown((s) => !s)}
          aria-label={shown ? `Ẩn ${props.label.toLowerCase()}` : `Hiện ${props.label.toLowerCase()}`}
          aria-pressed={shown}
          className="px-3 max-sm:h-11"
        >
          {shown ? "Ẩn" : "Hiện"}
        </Button>
      }
    />
  );
});

/** Small link line under a form ("Có mã mời? Tạo tài khoản"). */
export function AuthLink({ lead, href, children }: { lead: string; href: string; children: ReactNode }) {
  return (
    <p className="text-[14px] leading-snug text-muted">
      {lead}{" "}
      <a
        href={href}
        className="inline-flex min-h-11 items-center font-semibold text-fg underline decoration-line-strong underline-offset-4 transition-colors duration-150 hover:decoration-accent"
      >
        {children}
      </a>
    </p>
  );
}
