// "Nhiệm vụ hôm nay" (F45, docs/coins.md §6, wiki/screens/missions.md): the three mission rows and the "Quảng cáo
// mẫu" dialog. The server owns the clock (a claim before 15 server seconds is refused); the dialog only counts down so
// the button unlocks at the right moment. Pure, tested in missionsLogic.test.ts.
import { COIN_COPY } from "../../lib/coinCopy.ts";
import type { Wallet } from "../../lib/coins.ts";

export type MissionId = "ad" | "characters" | "turns";

export interface Mission {
  id: MissionId;
  progress: number;
  target: number;
  reward: number;
  claimed: boolean;
  claimable: boolean;
  remaining: number;
}

/** GET /api/coins/missions. The owner (and coins turned off): `missions: []`. */
export interface MissionsOut {
  coin_day: string;
  earned_today: number;
  cap: number;
  missions: Mission[];
  unlimited: boolean;
  enabled: boolean;
}

export interface AdStartOut {
  ad_id: number;
  seconds: number;
}

export interface ClaimOut {
  amount: number;
  wallet: Wallet;
}

// ---------------------------------------------------------------------------- the mission rows

export type RowAction =
  | { kind: "watch"; label: string; disabled: boolean }
  | { kind: "claim"; label: string; disabled: boolean }
  | { kind: "done"; label: string };

export interface MissionRow {
  id: MissionId;
  title: string;
  reward: string;
  progress: string;
  note: string | null;
  /** null: not done yet, only the progress shows. */
  action: RowAction | null;
}

const TITLES: Record<MissionId, string> = {
  ad: COIN_COPY.missionAd,
  characters: COIN_COPY.missionCharacters,
  turns: COIN_COPY.missionTurns,
};

export function capReached(data: Pick<MissionsOut, "earned_today" | "cap">): boolean {
  return data.earned_today >= data.cap;
}

export function missionRow(m: Mission, data: Pick<MissionsOut, "earned_today" | "cap">): MissionRow {
  const progress = `${Math.min(m.progress, m.target)}/${m.target}`;
  if (m.id === "ad") {
    const action: RowAction =
      m.remaining <= 0
        ? { kind: "done", label: COIN_COPY.adsDone }
        : { kind: "watch", label: COIN_COPY.watch, disabled: capReached(data) || data.earned_today + m.reward > data.cap };
    return { id: m.id, title: TITLES.ad, reward: COIN_COPY.rewardEach(m.reward), progress, note: null, action };
  }
  let action: RowAction | null = null;
  if (m.claimed) action = { kind: "done", label: COIN_COPY.claimed };
  else if (m.claimable) action = { kind: "claim", label: COIN_COPY.claim, disabled: false };
  return {
    id: m.id,
    title: TITLES[m.id],
    reward: COIN_COPY.reward(m.reward),
    progress,
    note: m.id === "turns" ? COIN_COPY.turnsNote : null,
    action,
  };
}

/** "Đã nhận 5/30 coin hôm nay", or the full-day sentence at 30. */
export function earnedText(data: Pick<MissionsOut, "earned_today" | "cap">): string {
  return capReached(data) ? COIN_COPY.missionsFull : COIN_COPY.missionsEarned(data.earned_today);
}

/** Only the three known missions, in the screen's order. */
export function knownMissions(list: readonly Mission[]): Mission[] {
  const order: MissionId[] = ["ad", "characters", "turns"];
  return order.map((id) => list.find((m) => m.id === id)).filter((m): m is Mission => m !== undefined);
}

// ---------------------------------------------------------------------------- the sample-ad dialog

/** A few more seconds when the server clock says "not yet" (the device clock runs a little fast). */
export const EXTRA_MS = 3_000;

export type AdState =
  | { phase: "starting" }
  | { phase: "counting"; adId: number; endsAt: number; note: string | null }
  | { phase: "ready"; adId: number }
  | { phase: "claiming"; adId: number }
  | { phase: "claimed"; adId: number; amount: number }
  | { phase: "expired"; adId: number | null; text: string }
  | { phase: "error"; adId: number | null; text: string; technical: string | null };

export type AdEvent =
  | { type: "reset" }
  | { type: "started"; adId: number; seconds: number; now: number }
  | { type: "tick"; now: number }
  | { type: "claim" }
  | { type: "claimed"; amount: number }
  | { type: "notFinished"; now: number }
  | { type: "expired" }
  | { type: "failed"; text: string; technical: string | null };

export const AD_START: AdState = { phase: "starting" };

function adIdOf(s: AdState): number | null {
  return "adId" in s ? s.adId : null;
}

/** The dialog's steps: starting → counting → ready → claiming → claimed. Events out of order leave it as it is. */
export function adReducer(s: AdState, e: AdEvent): AdState {
  switch (e.type) {
    case "reset":
      return AD_START;
    case "started":
      if (s.phase !== "starting") return s;
      return { phase: "counting", adId: e.adId, endsAt: e.now + Math.max(0, e.seconds) * 1000, note: null };
    case "tick":
      if (s.phase !== "counting" || e.now < s.endsAt) return s;
      return { phase: "ready", adId: s.adId };
    case "claim":
      if (s.phase !== "ready") return s;
      return { phase: "claiming", adId: s.adId };
    case "claimed":
      if (s.phase !== "claiming") return s;
      return { phase: "claimed", adId: s.adId, amount: e.amount };
    case "notFinished":
      if (s.phase !== "claiming") return s;
      return { phase: "counting", adId: s.adId, endsAt: e.now + EXTRA_MS, note: COIN_COPY.adNotFinished };
    case "expired":
      if (s.phase === "claimed") return s;
      return { phase: "expired", adId: adIdOf(s), text: COIN_COPY.adExpired };
    case "failed":
      if (s.phase === "claimed") return s;
      return { phase: "error", adId: adIdOf(s), text: e.text, technical: e.technical };
  }
}

/** Whole seconds left, rounded up (never "0" while time is left). */
export function secondsLeft(s: AdState, now: number): number {
  if (s.phase !== "counting") return 0;
  return Math.max(0, Math.ceil((s.endsAt - now) / 1000));
}

/** "Nhận 5 coin" is pressable only once the countdown is over (and not while sending or after the claim). */
export function claimLocked(s: AdState, now: number): boolean {
  if (s.phase === "ready") return false;
  if (s.phase === "counting") return secondsLeft(s, now) > 0;
  return true;
}

export type CloseAction = { kind: "cancel"; adId: number } | { kind: "close" };

/** "Đóng" (or Escape, or a tap outside) before the claim: the server cancels that view (it can never be claimed). */
export function closeAction(s: AdState): CloseAction {
  if (s.phase === "counting" || s.phase === "ready" || s.phase === "claiming") return { kind: "cancel", adId: s.adId };
  if (s.phase === "error" && s.adId !== null) return { kind: "cancel", adId: s.adId };
  return { kind: "close" };
}

/** The sentence for a refused start / claim (server `code`, the friendly fallback). */
export function adErrorText(code: string | null, fallback: string): string {
  switch (code) {
    case "ad_not_finished":
      return COIN_COPY.adNotFinished;
    case "ad_expired":
      return COIN_COPY.adExpired;
    case "ad_limit":
      return COIN_COPY.adLimit;
    case "mission_cap":
      return COIN_COPY.missionsFull;
    default:
      return fallback;
  }
}

/** The polite live region reads the countdown every 5 seconds (not every second). */
export function countdownLive(seconds: number): string | null {
  return seconds > 0 && seconds % 5 === 0 ? COIN_COPY.adLeft(seconds) : null;
}

// ---------------------------------------------------------------------------- where "Nhiệm vụ" was opened from

export type MissionsFrom = "wallet" | "composer" | "link";
let missionsFrom: MissionsFrom | null = null;

/** Called right before opening "#/missions" from a button (for the `missions_viewed` event). */
export function noteMissionsFrom(from: MissionsFrom): void {
  missionsFrom = from;
}

/** Where "#/missions" was opened from (once); a typed or pasted link is "link". */
export function takeMissionsFrom(): MissionsFrom {
  const from = missionsFrom ?? "link";
  missionsFrom = null;
  return from;
}
