// Words and small rules of "Quản lý tài khoản" (docs/auth.md §7.3). Pure, tested in logic.test.ts.
import type { BadgeTone } from "../../components/ui/Chip.tsx";
import type { AdminAccount, InviteDays, InviteOut } from "../../types.ts";

export interface BadgeSpec {
  label: string;
  tone: BadgeTone;
}

export const EXPIRY_OPTIONS: { value: `${InviteDays}`; label: string }[] = [
  { value: "1", label: "1 ngày" },
  { value: "7", label: "7 ngày" },
  { value: "30", label: "30 ngày" },
];
export const DEFAULT_EXPIRY: `${InviteDays}` = "7";
export const NOTE_MAX = 60;

export const INVITE_ONCE = "Mã chỉ hiện một lần và dùng được một lần.";

/** Status pill of an invite: "Còn hiệu lực" (ok), "Đã dùng bởi @x", "Hết hạn", "Đã huỷ" (neutral). */
export function inviteBadge(invite: Pick<InviteOut, "status" | "used_by_handle">): BadgeSpec {
  switch (invite.status) {
    case "active":
      return { label: "Còn hiệu lực", tone: "ok" };
    case "used":
      return { label: invite.used_by_handle ? `Đã dùng bởi @${invite.used_by_handle}` : "Đã dùng", tone: "neutral" };
    case "expired":
      return { label: "Hết hạn", tone: "neutral" };
    case "revoked":
      return { label: "Đã huỷ", tone: "neutral" };
  }
}

/** The badges of an account row, in order: owner (gold), disabled (danger), waiting for a new password (warn). */
export function accountBadges(a: Pick<AdminAccount, "role" | "status" | "must_change_password">): BadgeSpec[] {
  const out: BadgeSpec[] = [];
  if (a.role === "owner") out.push({ label: "Chủ máy", tone: "gold" });
  if (a.status === "disabled") out.push({ label: "Tạm khoá", tone: "danger" });
  if (a.must_change_password) out.push({ label: "Chờ đổi mật khẩu", tone: "warn" });
  return out;
}

/** Server times are UTC ISO ("2026-11-14T10:00:00.000Z"); null when missing or unreadable. */
export function parseTime(iso: string | null | undefined): Date | null {
  if (!iso) return null;
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? null : d;
}

function pad(n: number): string {
  return String(n).padStart(2, "0");
}

/** "20/11/2026" in local time. */
export function shortDate(d: Date): string {
  return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()}`;
}

/** "vừa xong", "5 phút trước", "3 giờ trước", "hôm qua", "4 ngày trước", then the date. */
export function relativeTime(iso: string | null | undefined, now: Date): string | null {
  const d = parseTime(iso);
  if (!d) return null;
  const sec = Math.max(0, Math.round((now.getTime() - d.getTime()) / 1000));
  if (sec < 60) return "vừa xong";
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min} phút trước`;
  const hours = Math.floor(min / 60);
  if (hours < 24) return `${hours} giờ trước`;
  const days = Math.floor(hours / 24);
  if (days === 1) return "hôm qua";
  if (days < 30) return `${days} ngày trước`;
  return shortDate(d);
}

/** "Vào lần cuối 3 giờ trước", or "Chưa đăng nhập lần nào". */
export function lastSeenLine(lastLoginAt: string | null, now: Date): string {
  const rel = relativeTime(lastLoginAt, now);
  return rel ? `Vào lần cuối ${rel}` : "Chưa đăng nhập lần nào";
}

/** "2 thiết bị", or "Không có thiết bị nào đang đăng nhập". */
export function devicesLine(count: number): string {
  return count > 0 ? `${count} thiết bị` : "Không thiết bị nào đang đăng nhập";
}

/** The date line of an invite: "Hết hạn 20/11/2026" (active or expired), "Dùng 15/11/2026"... */
export function inviteDateLine(invite: Pick<InviteOut, "status" | "expires_at" | "created_at">): string {
  const exp = parseTime(invite.expires_at);
  const made = parseTime(invite.created_at);
  if (invite.status === "active" || invite.status === "expired") return exp ? `Hết hạn ${shortDate(exp)}` : "";
  return made ? `Tạo ${shortDate(made)}` : "";
}

/** "…4TPA" as the owner sees an invite (the full code is shown only once). */
export function inviteLabel(hint: string): string {
  return `…${hint}`;
}

export function revokeConfirm(hint: string): string {
  return `Huỷ mã ${inviteLabel(hint)}? Ai đang giữ mã này sẽ không dùng được nữa.`;
}

export function resetConfirm(handle: string): string {
  return `Đặt lại mật khẩu của @${handle}? @${handle} sẽ bị đăng xuất khỏi mọi thiết bị và phải đổi mật khẩu khi đăng nhập lại.`;
}

export function resetNote(handle: string): string {
  return `Gửi mật khẩu này cho @${handle}. Mật khẩu chỉ hiện một lần, dùng được 3 ngày, và @${handle} sẽ phải đổi ngay khi đăng nhập.`;
}

export function disableConfirm(handle: string): string {
  return `@${handle} sẽ bị đăng xuất khỏi mọi thiết bị. Story và nhân vật của họ vẫn còn; nhân vật công khai của họ tạm ẩn.`;
}

/** Owner first, then by creation (the server already sends them so; kept stable here). */
export function sortAccounts(list: AdminAccount[]): AdminAccount[] {
  return [...list].sort(
    (a, b) => (a.role === "owner" ? 0 : 1) - (b.role === "owner" ? 0 : 1) || a.created_at.localeCompare(b.created_at) || a.id - b.id,
  );
}

/** Newest invite first. */
export function sortInvites(list: InviteOut[]): InviteOut[] {
  return [...list].sort((a, b) => b.created_at.localeCompare(a.created_at) || b.id - a.id);
}

/** The link only works for others when the page is opened by the Mac's Wi-Fi address, not "localhost". */
export function isLocalOrigin(hostname: string): boolean {
  return hostname === "localhost" || hostname === "127.0.0.1" || hostname === "[::1]" || hostname === "::1";
}
