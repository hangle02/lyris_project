// Invite and setup codes (docs/auth.md §1.3, §2.4). Same normalisation as the backend
// (backend/lyris/auth/codes.py normalize_code); both are tested against inviteCode.cases.json.
// Pure, no React, no DOM.

/** Crockford base32 (no I, L, O, U). */
export const CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ";
export const CODE_LENGTH = 12;
export const INVITE_PREFIX = "LYR";

/** Spaces, "-" and the dashes an iPhone keyboard turns "-" into (U+2010 to U+2015, U+2212). */
const SEPARATORS = /[\s\-\u2010-\u2015\u2212]+/gu;
const CONFUSABLE: Record<string, string> = { O: "0", I: "1", L: "1" };

/**
 * The 12-character code ("7KQ2M9XD4TPA"), or null when it is not one. Accepts "LYR-7KQ2-M9XD-4TPA",
 * lowercase, spaces, missing dashes, and O/I/L typed for 0/1. The prefix is dropped before L -> 1.
 */
export function normalizeCode(raw: string | null | undefined): string | null {
  if (!raw || raw.length > 100) return null;
  let text = raw.replace(SEPARATORS, "").toUpperCase();
  if (text.startsWith(INVITE_PREFIX) && text.length === CODE_LENGTH + INVITE_PREFIX.length) {
    text = text.slice(INVITE_PREFIX.length);
  }
  text = Array.from(text, (c) => CONFUSABLE[c] ?? c).join("");
  if (text.length !== CODE_LENGTH) return null;
  for (const c of text) if (!CROCKFORD.includes(c)) return null;
  return text;
}

/** "7KQ2M9XD4TPA" -> "7KQ2-M9XD-4TPA". */
export function groupCode(code: string): string {
  return code.match(/.{1,4}/g)?.join("-") ?? code;
}

/** The form people read and type: "LYR-7KQ2-M9XD-4TPA" (input already normalised or not). */
export function formatInvite(code: string): string {
  const n = normalizeCode(code);
  return `${INVITE_PREFIX}-${groupCode(n ?? code)}`;
}

/**
 * The invite link "http://<machine>:5173/#/signup?code=LYR-...". The code sits after "#", so it never
 * reaches the server or its logs; the signup page reads it and drops it from the address bar.
 */
export function inviteLink(origin: string, code: string): string {
  return `${origin.replace(/\/+$/, "")}/#/signup?code=${encodeURIComponent(formatInvite(code))}`;
}
