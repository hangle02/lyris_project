// Password rules checked in the browser before sending (docs/auth.md §3.1, §7.4). The server checks
// them again (plus the short list of common passwords) and its sentence wins. Pure, no React.

export const PASSWORD_MIN = 8;
export const PASSWORD_MAX = 128;

export const PASSWORD_TOO_SHORT = "Mật khẩu cần ít nhất 8 ký tự.";
export const PASSWORD_TOO_LONG = "Mật khẩu dài tối đa 128 ký tự.";
export const PASSWORD_SAME_AS_HANDLE = "Mật khẩu không được giống tên đăng nhập.";
export const PASSWORD_MISMATCH = "Hai mật khẩu chưa giống nhau.";
export const PASSWORD_SAME_AS_OLD = "Mật khẩu mới phải khác mật khẩu cũ.";
export const PASSWORD_HINT = "Ít nhất 8 ký tự.";

/** Characters as the server counts them: code points after Unicode NFC (iPhone and Mac may differ). */
export function passwordLength(password: string): number {
  return Array.from(password.normalize("NFC")).length;
}

/**
 * The first rule a new password breaks, or null. Spaces are kept (never trimmed); `handle` may carry
 * a leading "@". Case is ignored when comparing with the handle, like the server.
 */
export function passwordError(password: string, handle?: string | null): string | null {
  const n = passwordLength(password);
  if (n < PASSWORD_MIN) return PASSWORD_TOO_SHORT;
  if (n > PASSWORD_MAX) return PASSWORD_TOO_LONG;
  const h = (handle ?? "").trim().replace(/^@+/, "").toLowerCase();
  if (h) {
    const p = password.normalize("NFC").toLowerCase();
    if (p === h || p === `@${h}`) return PASSWORD_SAME_AS_HANDLE;
  }
  return null;
}

/** "Nhập lại mật khẩu": null when both are the same after NFC (or nothing typed yet). */
export function confirmError(password: string, confirm: string): string | null {
  if (confirm === "") return null;
  return password.normalize("NFC") === confirm.normalize("NFC") ? null : PASSWORD_MISMATCH;
}

/** Problems of a "new password + repeat" pair, per field, for a form about to be sent. */
export function newPasswordErrors(
  password: string,
  confirm: string,
  opts: { handle?: string | null; current?: string | null } = {},
): { password?: string; confirm?: string } {
  const out: { password?: string; confirm?: string } = {};
  const p = passwordError(password, opts.handle);
  if (p) out.password = p;
  else if (opts.current && opts.current.normalize("NFC") === password.normalize("NFC")) out.password = PASSWORD_SAME_AS_OLD;
  if (confirm === "") out.confirm = PASSWORD_MISMATCH;
  else {
    const c = confirmError(password, confirm);
    if (c) out.confirm = c;
  }
  return out;
}
