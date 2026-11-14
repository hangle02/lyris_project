import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { api, errorMessage, errorTechnical } from "../../api/client";
import { Button, InlineAlert, TextField } from "../../components/ui";
import { applyAuth, takeNextHash } from "../../hooks/useAuth";
import { formatInvite, normalizeCode } from "../../lib/inviteCode";
import { confirmError, newPasswordErrors, PASSWORD_HINT, passwordError } from "../../lib/passwordRules";
import { replaceRoute, routeHref } from "../../lib/router";
import { cleanDisplayName, displayNameError, HANDLE_MAX, HANDLE_MIN, handleError, normalizeHandle } from "../profile/logic";
import { AuthLayout, AuthLink, PasswordField } from "./AuthLayout";
import { authFieldOf, SIGNUP_PRIVACY } from "./logic";
import type { AuthField } from "./logic";

const HANDLE_HINT = `${HANDLE_MIN}-${HANDLE_MAX} ký tự: chữ a-z, số, _ và dấu chấm.`;
const BAD_CODE = "Mã mời gồm 12 ký tự, ví dụ LYR-7KQ2-M9XD-4TPA.";

type Errors = Partial<Record<AuthField | "confirm", string>>;

/**
 * "#/signup?code=LYR-…" (docs/auth.md §7.3). The code from the link fills "Mã mời" and is dropped
 * from the address bar at once (no screenshot or history keeps it). The invite is checked first on
 * the server: only with a good code does it say a handle is taken.
 */
export function SignupPage({ code }: { code: string | null }) {
  const [invite, setInvite] = useState(() => (code ? formatInvite(code) : ""));
  const [name, setName] = useState("");
  const [handle, setHandle] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [touched, setTouched] = useState<Partial<Record<keyof Errors, boolean>>>({});
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
    document.title = "Tạo tài khoản · Lyris";
  }, []);

  // The link's code: into the field, out of the address bar (replaceState, no history entry).
  useEffect(() => {
    if (code === null) return;
    setInvite(formatInvite(code));
    replaceRoute({ name: "signup", code: null });
  }, [code]);

  const h = normalizeHandle(handle);
  const live: Errors = {
    code: touched.code && invite.trim() && normalizeCode(invite) === null ? BAD_CODE : undefined,
    display_name: touched.display_name ? (displayNameError(name) ?? undefined) : undefined,
    handle: touched.handle && handle.trim() ? (handleError(h) ?? undefined) : undefined,
    password: touched.password && password ? (passwordError(password, h) ?? undefined) : undefined,
    confirm: touched.confirm ? (confirmError(password, confirm) ?? undefined) : undefined,
  };
  const shown = (k: keyof Errors) => errors[k] ?? live[k];
  const clear = (k: keyof Errors) => errors[k] && setErrors((x) => ({ ...x, [k]: undefined }));
  const blur = (k: keyof Errors) => () => setTouched((t) => ({ ...t, [k]: true }));

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (sending) return;
    const found: Errors = {};
    if (normalizeCode(invite) === null) found.code = invite.trim() ? BAD_CODE : "Hãy nhập mã mời.";
    const n = displayNameError(name);
    if (n) found.display_name = n;
    const he = handleError(h);
    if (he) found.handle = he;
    const pw = newPasswordErrors(password, confirm, { handle: h });
    if (pw.password) found.password = pw.password;
    if (pw.confirm) found.confirm = pw.confirm;
    setErrors(found);
    setTouched({ code: true, display_name: true, handle: true, password: true, confirm: true });
    const first = (["code", "display_name", "handle", "password", "confirm"] as const).find((k) => found[k]);
    if (first) return refs[first].current?.focus();
    setSending(true);
    setGeneral(null);
    try {
      const state = await api.signup({ invite_code: invite.trim(), handle: h, display_name: cleanDisplayName(name), password });
      // A new member starts on the hub (its empty state points to Khám phá). The remembered page of
      // an earlier visit is dropped, so a later sign-in in this tab does not land there.
      takeNextHash();
      applyAuth(state, { next: null, navigate: true });
    } catch (err) {
      const text = errorMessage(err);
      const field = authFieldOf(text);
      if (field && field !== "current") {
        setErrors({ [field]: text });
        refs[field === "code" ? "code" : field].current?.focus();
      } else {
        setGeneral({ text, technical: errorTechnical(err) });
      }
      setSending(false);
    }
  };

  return (
    <AuthLayout title="Tạo tài khoản" intro={SIGNUP_PRIVACY}>
      <form noValidate onSubmit={(e) => void submit(e)} className="flex flex-col gap-5">
        <TextField
          ref={refs.code}
          label="Mã mời"
          value={invite}
          onChange={(v) => {
            setInvite(v);
            clear("code");
          }}
          onBlur={blur("code")}
          placeholder="LYR-XXXX-XXXX-XXXX"
          autoComplete="off"
          autoCapitalize="characters"
          autoCorrect="off"
          spellCheck={false}
          error={shown("code")}
          disabled={sending}
        />
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
          hint={HANDLE_HINT}
          error={shown("handle")}
          disabled={sending}
        />
        <PasswordField
          ref={refs.password}
          label="Mật khẩu"
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
            Tạo tài khoản
          </Button>
          {general && <InlineAlert tone="error" text={general.text} technical={general.technical} />}
        </div>
      </form>
      <AuthLink lead="Đã có tài khoản?" href={routeHref({ name: "login" })}>
        Đăng nhập
      </AuthLink>
    </AuthLayout>
  );
}
