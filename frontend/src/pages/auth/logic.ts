// Words and small rules of the sign-in screens (docs/auth.md §7.3, §7.4). Pure, tested in logic.test.ts.

/** DESIGN.md tagline, under the wordmark of the sign-in screens. */
export const TAGLINE = "Nơi những tâm hồn trang sách bước ra sưởi ấm thực tại";

export const LOGGED_OUT_TEXT = "Bạn đã bị đăng xuất. Hãy đăng nhập lại.";
export const FORGOT_TEXT = "Quên mật khẩu? Hãy nhờ chủ máy đặt lại.";
export const SIGNUP_PRIVACY =
  "Lyris chạy trên máy của chủ máy. Story của bạn là riêng tư: tài khoản khác, kể cả chủ máy, không xem được trong app. Nhưng dữ liệu nằm trên máy đó.";
export const SETUP_INTRO =
  "Lyris giờ có đăng nhập. Nhập mã thiết lập in trong cửa sổ Terminal đang chạy Lyris trên Mac, rồi chọn mật khẩu cho tài khoản của bạn.";
export const FORCE_INTRO = "Mật khẩu của bạn vừa được đặt lại. Hãy chọn mật khẩu mới để tiếp tục.";
export const PASSWORD_CHANGED = "Đã đổi mật khẩu. Các thiết bị khác đã được đăng xuất.";

export type AuthField = "code" | "display_name" | "handle" | "password" | "current";

/**
 * Which field a server sentence is about, so a 400/422 shows under that field instead of above the
 * form; null = a general error (wrong sign-in, locked, too many tries, server down).
 */
export function authFieldOf(message: string): AuthField | null {
  const m = message.toLowerCase();
  if (m.includes("mã mời") || m.includes("mã thiết lập")) return "code";
  if (m.includes("mật khẩu hiện tại") || m.includes("mật khẩu tạm đã")) return m.includes("hiện tại") ? "current" : null;
  if (m.includes("tên đăng nhập hoặc mật khẩu") || m.includes("thử sai")) return null;
  if (m.includes("mật khẩu")) return "password";
  if (m.includes("handle") || m.includes("tên đăng nhập")) return "handle";
  if (m.includes("tên hiển thị") || m.includes("display_name")) return "display_name";
  return null;
}

/** What the login form sends: the handle as typed, without spaces at the ends (the server drops "@"). */
export function loginHandle(input: string): string {
  return input.trim();
}

/** "Mọi điện thoại và máy tính đang đăng nhập @{handle} sẽ phải đăng nhập lại, kể cả máy này." */
export function logoutAllConfirm(handle: string): string {
  return `Mọi điện thoại và máy tính đang đăng nhập @${handle.replace(/^@+/, "")} sẽ phải đăng nhập lại, kể cả máy này.`;
}
