// Pure helpers of the account profile (docs/accounts.md §2, §5); tested in logic.test.ts.
// No React, no DOM. The handle rules mirror the backend (AccountUpdate + the repo check):
// 3-30 characters a-z 0-9 _ . , no dot at either end, case-insensitive, unique.
import type { AccountOut, CardSummary, TemplateInfo, Visibility } from "../../types.ts";

export const HANDLE_MIN = 3;
export const HANDLE_MAX = 30;
export const DISPLAY_NAME_MAX = 60;
export const BIO_MAX = 500;

/** Characters, as the backend counts them (Python str length = code points). */
export function charCount(text: string): number {
  return Array.from(text).length;
}

/** What a typed handle becomes: spaces at the ends and a leading "@" dropped, lowercased. */
export function normalizeHandle(input: string): string {
  return input.trim().replace(/^@+/, "").toLowerCase();
}

/** Vietnamese reason why a (normalized) handle is not allowed, or null when it follows the rules. */
export function handleError(handle: string): string | null {
  const h = handle;
  if (h.length === 0) return "Hãy đặt một handle.";
  if (/\s/.test(h)) return "Handle không có khoảng trắng.";
  if (/[^\x00-\x7f]/.test(h)) return "Handle không dùng chữ có dấu. Ví dụ: “ngọc” viết thành “ngoc”.";
  if (/[^a-z0-9_.]/.test(h)) return "Handle chỉ gồm chữ a-z, số 0-9, dấu gạch dưới _ và dấu chấm.";
  if (h.length < HANDLE_MIN) return `Handle cần ít nhất ${HANDLE_MIN} ký tự.`;
  if (h.length > HANDLE_MAX) return `Handle dài tối đa ${HANDLE_MAX} ký tự.`;
  if (h.startsWith(".") || h.endsWith(".")) return "Handle không bắt đầu hay kết thúc bằng dấu chấm.";
  return null;
}

/** True when `handle` follows every rule (after normalizeHandle). */
export function isValidHandle(handle: string): boolean {
  return handleError(handle) === null;
}

/** Display name as it will be saved: spaces collapsed and trimmed. */
export function cleanDisplayName(name: string): string {
  return name.replace(/\s+/g, " ").trim();
}

export function displayNameError(name: string): string | null {
  const n = cleanDisplayName(name);
  if (n.length === 0) return "Hãy nhập tên hiển thị.";
  if (charCount(n) > DISPLAY_NAME_MAX) return `Tên hiển thị dài tối đa ${DISPLAY_NAME_MAX} ký tự.`;
  return null;
}

/** Bio as it will be saved: trailing spaces and blank lines at the ends dropped (inner lines kept). */
export function cleanBio(bio: string): string {
  return bio.replace(/[ \t]+$/gm, "").trim();
}

export function bioError(bio: string): string | null {
  const n = charCount(cleanBio(bio));
  return n > BIO_MAX ? `Giới thiệu dài tối đa ${BIO_MAX} ký tự (đang có ${n}).` : null;
}

/**
 * A handle suggested from a display name ("Ngọc Anh" -> "ngoc_anh"), used while the account has
 * not been set up yet. Null when nothing usable is left (fewer than 3 characters).
 */
export function handleFromName(name: string): string | null {
  const base = name
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[đĐ]/g, "d")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, HANDLE_MAX)
    .replace(/_+$/g, "");
  return isValidHandle(base) ? base : null;
}

export type ProfileField = "display_name" | "handle" | "bio";

/**
 * Which field a server error message is about, so a 422 from PUT /api/account is shown under that
 * field ("Handle @x đã có người dùng." -> "handle"); null = show it above the form.
 */
export function serverErrorField(message: string): ProfileField | null {
  const m = message.toLowerCase();
  if (m.includes("handle")) return "handle";
  if (m.includes("display_name") || m.includes("tên hiển thị")) return "display_name";
  if (m.includes("bio") || m.includes("giới thiệu")) return "bio";
  return null;
}

/** First client-side error of the edit form, per field (only fields that have one). */
export function validateProfile(v: { display_name: string; handle: string; bio: string }): Partial<Record<ProfileField, string>> {
  const out: Partial<Record<ProfileField, string>> = {};
  const name = displayNameError(v.display_name);
  const handle = handleError(normalizeHandle(v.handle));
  const bio = bioError(v.bio);
  if (name) out.display_name = name;
  if (handle) out.handle = handle;
  if (bio) out.bio = bio;
  return out;
}

/** Same handle, ignoring case and a leading "@". */
export function sameHandle(a: string | null | undefined, b: string | null | undefined): boolean {
  if (!a || !b) return false;
  return normalizeHandle(a) === normalizeHandle(b);
}

/** Whose profile a profile route shows, and where the route should move. */
export interface ProfileOwnership {
  /** True when the page shows the current account (with "Sửa profile" and the private tabs). */
  own: boolean;
  /**
   * Set when the account was renamed while "#/u/<old handle>" was open: the route should move to
   * "#/u/<follow>". Until it does, the page keeps showing the own profile (the old handle no longer
   * exists, so the public view would only say "not found").
   */
  follow: string | null;
}

/**
 * Ownership of "#/me" (`routeHandle` null) and "#/u/<routeHandle>". `lastOwnHandle` is the handle
 * this route last matched as the account's own (null when it never did).
 */
export function profileOwnership(
  routeHandle: string | null,
  accountHandle: string | null,
  lastOwnHandle: string | null,
): ProfileOwnership {
  if (routeHandle === null) return { own: true, follow: null };
  if (accountHandle === null) return { own: false, follow: null };
  if (sameHandle(routeHandle, accountHandle)) return { own: true, follow: null };
  if (sameHandle(routeHandle, lastOwnHandle)) return { own: true, follow: normalizeHandle(accountHandle) };
  return { own: false, follow: null };
}

/** Label of a card's visibility on your own grid: "Riêng tư", or "Công khai" once shared (Phase 4b). */
export function visibilityLabel(v: Visibility | null | undefined): string | null {
  switch (v ?? "private") {
    case "private":
      return "Riêng tư";
    case "unlisted":
      return "Không công khai";
    case "public":
      return "Công khai";
    default:
      return null;
  }
}

/**
 * Characters the account created, newest first: its own cards, without installed templates (those
 * are "Mẫu của Lyris") and without cards another account made.
 */
export function createdCards(cards: CardSummary[], templates: TemplateInfo[], handle: string | null): CardSummary[] {
  const templateIds = new Set(templates.map((t) => t.installed_card_id).filter((id): id is number => id !== null));
  return cards
    .filter((c) => !templateIds.has(c.id))
    .filter((c) => c.creator_handle === null || handle === null || sameHandle(c.creator_handle, handle))
    .slice()
    .sort((a, b) => (b.updated_at ?? "").localeCompare(a.updated_at ?? "") || b.id - a.id);
}

export interface ProfileStat {
  key: "cards" | "stories" | "personas";
  value: number;
  label: string;
}

/** The three counts under the bio. `cardCount` overrides the account's when the grid is loaded. */
export function profileStats(account: Pick<AccountOut, "card_count" | "story_count" | "persona_count">, cardCount?: number): ProfileStat[] {
  return [
    { key: "cards", value: cardCount ?? account.card_count, label: "nhân vật" },
    { key: "stories", value: account.story_count, label: "story" },
    { key: "personas", value: account.persona_count, label: "persona" },
  ];
}

/** "@ban" from "ban". */
export function atHandle(handle: string): string {
  return `@${handle}`;
}
