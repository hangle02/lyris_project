// The owner's coin tools in "Quản lý tài khoản" (F43, docs/coins.md §4.3–§4.5): top-up codes, "Cộng/trừ coin"
// with a reason, and the coin log. What is typed is checked here BEFORE sending. Pure, tested in
// adminCoinLogic.test.ts. Owner-only words: they are not in lib/coinCopy.ts (the member's screens).
import { formatCoins } from "../../lib/coins.ts";
import type { PackId } from "../coins/topupLogic.ts";
import type { BadgeSpec } from "./logic.ts";

export const CODE_AMOUNT_MIN = 1;
export const CODE_AMOUNT_MAX = 10_000;
export const ADJUST_MAX = 10_000;
export const REASON_MIN = 3;
export const REASON_MAX = 120;
export const CODE_NOTE_MAX = 60;

export const AMOUNT_PROBLEM = "Số coin từ 1 đến 10.000.";
export const DELTA_PROBLEM = "Nhập số coin khác 0, từ −10.000 đến 10.000.";
export const REASON_PROBLEM = "Lý do cần từ 3 đến 120 ký tự.";

export type CodeChoice = PackId | "custom";
export const PACK_CHOICES: { value: CodeChoice; label: string }[] = [
  { value: "p100", label: "100 coin" },
  { value: "p550", label: "550 coin" },
  { value: "p1200", label: "1.200 coin" },
  { value: "p2500", label: "2.500 coin" },
  { value: "custom", label: "Tự nhập" },
];

export type TopupCodeStatus = "active" | "used" | "expired" | "revoked";

export interface TopupCodeItem {
  id: number;
  hint: string;
  amount: number;
  pack_id: PackId | null;
  note: string;
  created_at: string;
  expires_at: string;
  status: TopupCodeStatus;
  used_by_handle: string | null;
}

export interface TopupCodeCreated {
  /** the full code, shown once */
  code: string;
  item: TopupCodeItem;
}

export interface CoinLogItem {
  id: number;
  created_at: string;
  kind: "topup_code" | "admin_adjust" | "creator_milestone";
  handle: string | null;
  delta: number;
  reason: string | null;
  note: string | null;
  milestone: number | null;
  /** Creator rewards (F44): "Thưởng xếp hạng top 10", "Thưởng công khai lần đầu", old "Thưởng mốc 10 người chơi". */
  label?: string | null;
}

export interface CoinLog {
  items: CoinLogItem[];
  totals: { days: number; granted: number; topped_up: number; spent: number };
}

export interface AdjustBody {
  delta: number;
  reason: string;
  request_id: string;
}

export interface CodeBody {
  pack_id?: PackId;
  amount?: number;
  note: string;
  expires_days: 1 | 7 | 30;
}

/** "20", "1.200", "-5", "−5", "+20" → the number; anything else (decimals, "1.20", letters) → null. */
export function parseWholeNumber(text: string): number | null {
  const t = text.trim().replace(/−/g, "-").replace(/\s+/g, "");
  const m = /^([+-]?)(\d{1,3}(?:\.\d{3})+|\d+)$/.exec(t);
  if (!m) return null;
  const n = Number((m[2] ?? "").replace(/\./g, ""));
  if (!Number.isSafeInteger(n)) return null;
  return m[1] === "-" ? -n : n;
}

export function codeAmountProblem(text: string): string | null {
  const n = parseWholeNumber(text);
  return n !== null && n >= CODE_AMOUNT_MIN && n <= CODE_AMOUNT_MAX ? null : AMOUNT_PROBLEM;
}

export function cleanReason(text: string): string {
  return text.split(/\s+/).filter(Boolean).join(" ");
}

export function reasonProblem(text: string): string | null {
  const n = cleanReason(text).length;
  return n >= REASON_MIN && n <= REASON_MAX ? null : REASON_PROBLEM;
}

export function deltaProblem(text: string): string | null {
  const n = parseWholeNumber(text);
  return n !== null && n !== 0 && Math.abs(n) <= ADJUST_MAX ? null : DELTA_PROBLEM;
}

export type AdjustCheck =
  | { ok: true; body: AdjustBody }
  | { ok: false; problems: { delta?: string; reason?: string } };

/** "Cộng/trừ coin": the request to send, or what is wrong with each field. */
export function adjustRequest(deltaText: string, reasonText: string, requestId: string): AdjustCheck {
  const delta = deltaProblem(deltaText);
  const reason = reasonProblem(reasonText);
  if (delta || reason) {
    const problems: { delta?: string; reason?: string } = {};
    if (delta) problems.delta = delta;
    if (reason) problems.reason = reason;
    return { ok: false, problems };
  }
  return { ok: true, body: { delta: parseWholeNumber(deltaText) as number, reason: cleanReason(reasonText), request_id: requestId } };
}

export type CodeCheck = { ok: true; body: CodeBody } | { ok: false; problem: string };

/** "Tạo mã nạp": a pack sends only `pack_id`; "Tự nhập" sends only `amount` (1–10.000). */
export function codeRequest(choice: CodeChoice, amountText: string, note: string, days: `${1 | 7 | 30}`): CodeCheck {
  const expires_days = Number(days) as 1 | 7 | 30;
  const cleanNote = cleanReason(note);
  if (choice !== "custom") return { ok: true, body: { pack_id: choice, note: cleanNote, expires_days } };
  const problem = codeAmountProblem(amountText);
  if (problem) return { ok: false, problem };
  return { ok: true, body: { amount: parseWholeNumber(amountText) as number, note: cleanNote, expires_days } };
}

/** A fresh id for one opening of "Cộng/trừ coin": sent again on a retry so the change is written once. */
export function newRequestId(): string {
  const c = globalThis.crypto as Crypto | undefined;
  if (c && typeof c.randomUUID === "function") return c.randomUUID();
  return `r${Date.now().toString(36)}${Math.random().toString(36).slice(2, 12)}`;
}

/** Status pill of a top-up code (same words as an invite). */
export function topupCodeBadge(item: Pick<TopupCodeItem, "status" | "used_by_handle">): BadgeSpec {
  switch (item.status) {
    case "active":
      return { label: "Còn hiệu lực", tone: "ok" };
    case "used":
      return { label: item.used_by_handle ? `Đã dùng bởi @${item.used_by_handle}` : "Đã dùng", tone: "neutral" };
    case "expired":
      return { label: "Hết hạn", tone: "neutral" };
    case "revoked":
      return { label: "Đã huỷ", tone: "neutral" };
  }
}

/** "1.200 coin" on a member's row; null for the owner (never charged). */
export function memberCoinLine(balance: number | null | undefined): string | null {
  return typeof balance === "number" ? formatCoins(balance) : null;
}

/** The main words of a coin log row: the code's note, the adjustment's reason, or the creator reward. */
export function coinLogTitle(item: Pick<CoinLogItem, "kind" | "note" | "reason" | "milestone" | "label">): string {
  if (item.kind === "topup_code") return item.note ? `Nạp bằng mã · ${item.note}` : "Nạp bằng mã";
  if (item.kind === "creator_milestone") return item.label || `Thưởng mốc ${item.milestone ?? 0} người chơi`;
  return item.reason ?? "Điều chỉnh";
}
