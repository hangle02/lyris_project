// "Nạp coin" (F43, docs/coins.md §4, §10.5): the planned packs in VND, the top-up code (normalised exactly like an
// invite code, lib/inviteCode.ts), and the sentences of a redeem. Pure, tested in topupLogic.test.ts.
import { COIN_COPY } from "../../lib/coinCopy.ts";
import { formatCoinNumber, formatCoins } from "../../lib/coins.ts";
import type { Wallet } from "../../lib/coins.ts";
import { groupCode, normalizeCode } from "../../lib/inviteCode.ts";

export type PackId = "p100" | "p550" | "p1200" | "p2500";

export interface CoinPack {
  id: PackId;
  /** total, bonus included */
  coins: number;
  bonus: number;
  price_vnd: number;
}

/** GET /api/coins/packs. Test mode: nothing is sold, prices are "Giá dự kiến"; no contact channel. */
export interface PacksOut {
  test_mode: boolean;
  packs: CoinPack[];
  contact: null;
}

export interface Redeemed {
  amount: number;
  wallet: Wallet;
}

/** "50.000đ". */
export function formatVnd(n: number): string {
  return `${formatCoinNumber(n)}đ`;
}

/** The 12-character code, or null — the same rules as an invite code (lowercase, iPhone dashes, spaces). */
export function normalizeTopupCode(raw: string | null | undefined): string | null {
  return normalizeCode(raw);
}

/** "7KQ2-M9XD-4TPA" as the owner reads it out. */
export function formatTopupCode(code: string): string {
  return groupCode(normalizeCode(code) ?? code);
}

export type CodeCheck = { ok: true; code: string } | { ok: false; text: string };

/** A code that cannot be one never goes to the server (it would only use up a try); same sentence as the server. */
export function checkCodeInput(raw: string): CodeCheck {
  const code = normalizeTopupCode(raw);
  return code ? { ok: true, code } : { ok: false, text: COIN_COPY.codeInvalid };
}

const PACK_IDS: readonly PackId[] = ["p100", "p550", "p1200", "p2500"];

/** Only the four known packs are shown (an unknown id from the server is left out). */
export function knownPacks(list: readonly CoinPack[]): CoinPack[] {
  return list.filter((p) => PACK_IDS.includes(p.id));
}

/** The pack's code for `topup_pack_selected`: one of the fixed enum values (packs come through knownPacks). */
export function packCode(p: Pick<CoinPack, "id">): PackId {
  return p.id;
}

export function packTitle(p: Pick<CoinPack, "coins">): string {
  return formatCoins(p.coins);
}

export function packBonus(p: Pick<CoinPack, "bonus">): string | null {
  return p.bonus > 0 ? COIN_COPY.packBonus(formatCoinNumber(p.bonus)) : null;
}

export function packDialogTitle(p: Pick<CoinPack, "coins" | "price_vnd">): string {
  return COIN_COPY.packDialogTitle(formatCoins(p.coins), formatVnd(p.price_vnd));
}

export function redeemedText(amount: number): string {
  return COIN_COPY.redeemed(formatCoinNumber(amount));
}

/** The sentence under the code field for a failed redeem (status, server `code`, the friendly fallback). */
export function redeemErrorText(status: number, code: string | null, fallback: string): string {
  if (code === "topup_code_invalid") return COIN_COPY.codeInvalid;
  if (status === 429 || code === "rate_limited") return COIN_COPY.codeRateLimited;
  return fallback;
}

// ---------------------------------------------------------------------------- where "Nạp coin" was opened from

export type TopUpFrom = "wallet" | "composer" | "link";
let topUpFrom: TopUpFrom | null = null;

/** Called right before opening "#/coins/top-up" from a button (for the `topup_viewed` event). */
export function noteTopUpFrom(from: TopUpFrom): void {
  topUpFrom = from;
}

/** Where "#/coins/top-up" was opened from (once); a typed or pasted link is "link". */
export function takeTopUpFrom(): TopUpFrom {
  const from = topUpFrom ?? "link";
  topUpFrom = null;
  return from;
}
