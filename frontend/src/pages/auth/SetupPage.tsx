import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { api, errorMessage, errorTechnical } from "../../api/client";
import { Button, InlineAlert, TextField } from "../../components/ui";
import { applyAuth, refreshAuth, takeNextHash } from "../../hooks/useAuth";
import { normalizeCode } from "../../lib/inviteCode";
import { confirmError, newPasswordErrors, PASSWORD_HINT, passwordError } from "../../lib/passwordRules";
import { cleanDisplayName, displayNameError, HANDLE_MAX, HANDLE_MIN, handleError, normalizeHandle } from "../profile/logic";
import { AuthLayout, PasswordField } from "./AuthLayout";
import { authFieldOf, SETUP_INTRO } from "./logic";

type Key = "code" | "display_name" | "handle" | "password" | "confirm";
type Errors = Partial<Record<Key, string>>;

const BAD_CODE = "Mã thiết lập gồm 12 ký tự, ví dụ 7KQ2-M9XD-4TPA.";

/**
 * First run after the upgrade (docs/auth.md §2.4, §7.3): the owner has no password yet. The setup
 * code printed in the Mac's Terminal proves the person sits at the Mac; nobody on the Wi-Fi can take
 * the owner's account by opening the page first. The owner's handle is never shown here; a brand-new
 * machine (`needsProfile`) also asks for a name and a handle.
 */
export function SetupPage({ needsProfile }: { needsProfile: boolean }) {
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [handle, setHandle] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [touched, setTouched] = useState<Partial<Record<Key, boolean>>>({});
  const [errors, setErrors] = useState<Errors>({});
  const [general, setGeneral] = useState<{ text: string; technical: string | null } | null>(null);
  const [sending, setSending] = useState(false);
  const refs = {
    code: useRef<HTMLInputElement>(null),
    display_name: useRef<HTMLInputElement>(null),
    handle: useRef<HTMLInputElement>(null),
    password: useRef<HTMLInputElement>(null),
    confirm: useRef<HTMLInputElement>(null),
  };

  useEffect(() => {
    document.title = "Đặt mật khẩu cho chủ máy · Lyris";
    refs.code.current?.focus();
    // Only on mount (refs are stable).
  }, []);

  const h = normalizeHandle(handle);
  const ownHandle = needsProfile ? h : null;
  const live: Errors = {
    code: touched.code && code.trim() && normalizeCode(code) === null ? BAD_CODE : undefined,
    display_name: needsProfile && touched.display_name ? (displayNameError(name) ?? undefined) : undefined,
    handle: needsProfile && touched.handle && handle.trim() ? (handleError(h) ?? undefined) : undefined,
    password: touched.password && password ? (passwordError(password, ownHandle) ?? undefined) : undefined,
    confirm: touched.confirm ? (confirmError(password, confirm) ?? undefined) : undefined,
  };
  const shown = (k: Key) => errors[k] ?? live[k];
  const clear = (k: Key) => errors[k] && setErrors((x) => ({ ...x, [k]: undefined }));
  const blur = (k: Key) => () => setTouched((t) => ({ ...t, [k]: true }));

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (sending) return;
    const found: Errors = {};
    if (normalizeCode(code) === null) found.code = code.trim() ? BAD_CODE : "Hãy nhập mã thiết lập.";
    if (needsProfile) {
      const n = displayNameError(name);
      if (n) found.display_name = n;
      const he = handleError(h);
      if (he) found.handle = he;
    }
    const pw = newPasswordErrors(password, confirm, { handle: ownHandle });
    if (pw.password) found.password = pw.password;
    if (pw.confirm) found.confirm = pw.confirm;
    setErrors(found);
    setTouched({ code: true, display_name: true, handle: true, password: true, confirm: true });
    const first = (["code", "display_name", "handle", "password", "confirm"] as const).find((k) => found[k]);
    if (first) return refs[first].current?.focus();
    setSending(true);
    setGeneral(null);
    try {
      const state = await api.setupOwner({
        setup_code: code.trim(),
        password,
        ...(needsProfile ? { display_name: cleanDisplayName(name), handle: h } : {}),
      });
      applyAuth(state, { next: takeNextHash(), navigate: true });
    } catch (err) {
      const status = (err as { status?: number }).status;
      // 409: set up meanwhile (another tab, the Mac's command): the gate moves on to the login page.
      if (status === 409) {
        void refreshAuth();
        setSending(false);
        return;
      }
      const text = errorMessage(err);
      const field = authFieldOf(text);
      if (field === "code" || field === "password" || (needsProfile && (field === "handle" || field === "display_name"))) {
        setErrors({ [field]: text });
        refs[field].current?.focus();
      } else {
        setGeneral({ text, technical: errorTechnical(err) });
      }
      setSending(false);
    }
  };

  return (
    <AuthLayout title="Đặt mật khẩu cho chủ máy" intro={SETUP_INTRO}>
      <form noValidate onSubmit={(e) => void submit(e)} className="flex flex-col gap-5">
        <TextField
          ref={refs.code}
          label="Mã thiết lập"
          value={code}
          onChange={(v) => {
            setCode(v);
            clear("code");
          }}
          onBlur={blur("code")}
          placeholder="XXXX-XXXX-XXXX"
          autoComplete="one-time-code"
          autoCapitalize="characters"
          autoCorrect="off"
          spellCheck={false}
          hint="12 ký tự, ví dụ 7KQ2-M9XD-4TPA."
          error={shown("code")}
          disabled={sending}
        />
        {needsProfile && (
          <>
            <TextField
              ref={refs.display_name}
              label="Tên hiển thị"
              value={name}
              onChange={(v) => {
                setName(v);
                clear("display_name");
              }}
              onBlur={blur("display_name")}
              placeholder="Ví dụ: Mai"
              autoComplete="nickname"
              maxLength={80}
              error={shown("display_name")}
              disabled={sending}
            />
            <TextField
              ref={refs.handle}
              label="Tên đăng nhập"
              value={handle}
              onChange={(v) => {
                setHandle(v.replace(/^@+/, "").toLowerCase());
                clear("handle");
              }}
              onBlur={blur("handle")}
              placeholder="@handle"
              autoComplete="username"
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck={false}
              maxLength={HANDLE_MAX + 10}
              hint={`${HANDLE_MIN}-${HANDLE_MAX} ký tự: chữ a-z, số, _ và dấu chấm.`}
              error={shown("handle")}
              disabled={sending}
            />
          </>
        )}
        <PasswordField
          ref={refs.password}
          label="Mật khẩu mới"
          value={password}
          onChange={(v) => {
            setPassword(v);
            clear("password");
          }}
          onBlur={blur("password")}
          autoComplete="new-password"
          hint={PASSWORD_HINT}
          error={shown("password")}
          disabled={sending}
        />
        <PasswordField
          ref={refs.confirm}
          label="Nhập lại mật khẩu"
          value={confirm}
          onChange={(v) => {
            setConfirm(v);
            clear("confirm");
          }}
          onBlur={blur("confirm")}
          autoComplete="new-password"
          error={shown("confirm")}
          disabled={sending}
        />
        <div className="flex flex-col gap-3 pt-1">
          <Button type="submit" variant="primary" block loading={sending}>
            Lưu và vào Lyris
          </Button>
          {general && <InlineAlert tone="error" text={general.text} technical={general.technical} />}
        </div>
      </form>
    </AuthLayout>
  );
}
