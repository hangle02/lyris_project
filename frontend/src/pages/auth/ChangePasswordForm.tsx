import { useEffect, useRef, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { api, errorMessage, errorTechnical } from "../../api/client";
import { Button, InlineAlert } from "../../components/ui";
import { passwordChanged } from "../../hooks/useAuth";
import { confirmError, newPasswordErrors, PASSWORD_HINT, passwordError } from "../../lib/passwordRules";
import type { AuthState } from "../../types";
import { PasswordField } from "./AuthLayout";
import { authFieldOf } from "./logic";

interface Props {
  /** "Mật khẩu tạm" on the forced change, "Mật khẩu hiện tại" in the account sheet. */
  currentLabel: string;
  submitLabel: string;
  /** The account's handle (a password equal to it is refused). */
  handle: string | null;
  /** Called after the server accepted (the new sign-in state is already applied). */
  onDone?: (state: AuthState) => void;
  /** Buttons beside submit (ghost "Đăng xuất", "Huỷ"); rendered before it. */
  secondary?: ReactNode;
  autoFocus?: boolean;
}

type Errors = { current?: string; password?: string; confirm?: string };

/**
 * Current (or temporary) password, new password, repeat (docs/auth.md §7.3). Rules are checked as
 * you type once a field was left; the server's sentence lands under its field when it names one.
 * Success signs the other devices out and gives this one a fresh sign-in.
 */
export function ChangePasswordForm({ currentLabel, submitLabel, handle, onDone, secondary, autoFocus = true }: Props) {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [touched, setTouched] = useState<{ next?: boolean; confirm?: boolean }>({});
  const [errors, setErrors] = useState<Errors>({});
  const [general, setGeneral] = useState<{ text: string; technical: string | null } | null>(null);
  const [sending, setSending] = useState(false);
  const currentRef = useRef<HTMLInputElement>(null);
  const nextRef = useRef<HTMLInputElement>(null);
  const confirmRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (autoFocus) currentRef.current?.focus();
  }, [autoFocus]);

  const live: Errors = {
    password: touched.next && next ? (passwordError(next, handle) ?? undefined) : undefined,
    confirm: touched.confirm ? (confirmError(next, confirm) ?? undefined) : undefined,
  };
  const shown = (k: keyof Errors) => errors[k] ?? live[k];

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (sending) return;
    const found: Errors = { ...newPasswordErrors(next, confirm, { handle, current }) };
    if (!current) found.current = `Hãy nhập ${currentLabel.toLowerCase()}.`;
    setErrors(found);
    setTouched({ next: true, confirm: true });
    if (found.current) return currentRef.current?.focus();
    if (found.password) return nextRef.current?.focus();
    if (found.confirm) return confirmRef.current?.focus();
    setSending(true);
    setGeneral(null);
    try {
      const state = await api.changePassword({ current_password: current, new_password: next });
      passwordChanged(state);
      setCurrent("");
      setNext("");
      setConfirm("");
      setTouched({});
      setSending(false);
      onDone?.(state);
    } catch (err) {
      const text = errorMessage(err);
      const field = authFieldOf(text);
      if (field === "current") {
        setErrors({ current: text });
        currentRef.current?.focus();
      } else if (field === "password") {
        setErrors({ password: text });
        nextRef.current?.focus();
      } else {
        setGeneral({ text, technical: errorTechnical(err) });
      }
      setSending(false);
    }
  };

  const clear = (k: keyof Errors) => errors[k] && setErrors((x) => ({ ...x, [k]: undefined }));

  return (
    <form noValidate onSubmit={(e) => void submit(e)} className="flex flex-col gap-5">
      {/* Lets the browser's password manager save the new password under the right account. */}
      {handle && <input type="text" name="username" autoComplete="username" value={handle} readOnly hidden />}
      <PasswordField
        ref={currentRef}
        label={currentLabel}
        value={current}
        onChange={(v) => {
          setCurrent(v);
          clear("current");
        }}
        autoComplete="current-password"
        error={shown("current")}
        disabled={sending}
      />
      <PasswordField
        ref={nextRef}
        label="Mật khẩu mới"
        value={next}
        onChange={(v) => {
          setNext(v);
          clear("password");
        }}
        onBlur={() => setTouched((t) => ({ ...t, next: true }))}
        autoComplete="new-password"
        hint={PASSWORD_HINT}
        error={shown("password")}
        disabled={sending}
      />
      <PasswordField
        ref={confirmRef}
        label="Nhập lại mật khẩu"
        value={confirm}
        onChange={(v) => {
          setConfirm(v);
          clear("confirm");
        }}
        onBlur={() => setTouched((t) => ({ ...t, confirm: true }))}
        autoComplete="new-password"
        error={shown("confirm")}
        disabled={sending}
      />
      {general && <InlineAlert tone="error" text={general.text} technical={general.technical} />}
      <div className="flex flex-col-reverse gap-2 pt-1 sm:flex-row sm:justify-end">
        {secondary}
        <Button type="submit" variant="primary" loading={sending} className="max-sm:w-full">
          {submitLabel}
        </Button>
      </div>
    </form>
  );
}
