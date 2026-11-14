import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { api, errorMessage, errorTechnical } from "../../api/client";
import { Button, InlineAlert, TextField } from "../../components/ui";
import { applyAuth, takeNextHash, useAuth } from "../../hooks/useAuth";
import { routeHref } from "../../lib/router";
import { AuthLayout, AuthLink, PasswordField } from "./AuthLayout";
import { FORGOT_TEXT, LOGGED_OUT_TEXT, loginHandle } from "./logic";

/**
 * "#/login" (docs/auth.md §7.3). Signed out on any other hash, the gate shows this page and keeps that
 * hash; signing in goes back there. The server's sentence is shown as it is (wrong sign-in, locked,
 * too many tries), under the button.
 */
export function LoginPage() {
  const { loggedOut } = useAuth();
  const [handle, setHandle] = useState("");
  const [password, setPassword] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<{ text: string; technical: string | null } | null>(null);
  const [missing, setMissing] = useState<{ handle?: string; password?: string }>({});
  const handleRef = useRef<HTMLInputElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    document.title = "Đăng nhập · Lyris";
    handleRef.current?.focus();
  }, []);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (sending) return;
    const h = loginHandle(handle);
    const gaps = { handle: h ? undefined : "Hãy nhập tên đăng nhập.", password: password ? undefined : "Hãy nhập mật khẩu." };
    setMissing(gaps);
    if (gaps.handle) return handleRef.current?.focus();
    if (gaps.password) return passwordRef.current?.focus();
    setSending(true);
    setError(null);
    try {
      const state = await api.login({ handle: h, password });
      applyAuth(state, { next: takeNextHash(), navigate: true });
    } catch (err) {
      setError({ text: errorMessage(err), technical: errorTechnical(err) });
      setSending(false);
    }
  };

  return (
    <AuthLayout title="Đăng nhập">
      {loggedOut && <InlineAlert tone="info" text={LOGGED_OUT_TEXT} />}
      <form noValidate onSubmit={(e) => void submit(e)} className="flex flex-col gap-5">
        <TextField
          ref={handleRef}
          label="Tên đăng nhập"
          value={handle}
          onChange={(v) => {
            setHandle(v);
            if (missing.handle) setMissing((m) => ({ ...m, handle: undefined }));
          }}
          placeholder="@handle"
          autoComplete="username"
          autoCapitalize="none"
          autoCorrect="off"
          spellCheck={false}
          name="username"
          error={missing.handle}
          disabled={sending}
        />
        <PasswordField
          ref={passwordRef}
          label="Mật khẩu"
          value={password}
          onChange={(v) => {
            setPassword(v);
            if (missing.password) setMissing((m) => ({ ...m, password: undefined }));
          }}
          autoComplete="current-password"
          name="password"
          error={missing.password}
          disabled={sending}
        />
        <div className="flex flex-col gap-3 pt-1">
          <Button type="submit" variant="primary" block loading={sending}>
            Đăng nhập
          </Button>
          {error && <InlineAlert tone="error" text={error.text} technical={error.technical} />}
        </div>
      </form>
      <div className="flex flex-col gap-1">
        <AuthLink lead="Có mã mời?" href={routeHref({ name: "signup", code: null })}>
          Tạo tài khoản
        </AuthLink>
        <p className="text-[14px] leading-snug text-muted">{FORGOT_TEXT}</p>
      </div>
    </AuthLayout>
  );
}
