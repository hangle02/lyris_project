// Coins on the client (F42, docs/coins.md §8, §10). Pure and tested in coins.test.ts:
// - `composerCoinLock(wallet)`: the composers (Story, DM, Studio test chat) lock when a member has fewer
//   than 6 usable coins (balance minus the coins held by a reply on its way). The owner (`unlimited`) and
//   coins turned off (`enabled: false`) never lock; an unknown wallet never locks on a guess.
// - `createWalletStore(fetcher)`: the one shared wallet (header chip, account sheet, wallet page, chat).
//   Refreshed on app open, tab return, after each reply and after a 402; a refresh to 6 coins opens the
//   composers at once (no reload).
// - `groupHistory`, `formatCoins`, `historyTime`, `dailyToast`: the wallet page and the daily notice.
import { COIN_COPY, PRICE_PER_REPLY } from "./coinCopy.ts";

export interface Wallet {
  balance: number;
  /** balance minus the coins held for a reply being written */
  available: number;
  /** the owner: never charged */
  unlimited: boolean;
  price_per_reply: number;
  /** false when the server runs with LYRIS_COINS=0 */
  enabled: boolean;
}

export interface Checkin {
  granted: boolean;
  amount: number;
  /** today's daily gift (60), already added or not; 0 for the owner or coins off */
  today: number;
  coin_day: string;
  wallet: Wallet;
}

export interface CoinHistoryItem {
  id: number;
  delta: number;
  kind: string;
  label: string;
  created_at: string;
  balance_after: number;
  coin_day: string;
  story_id: number | null;
  name?: string | null;
}

export interface CoinHistory {
  items: CoinHistoryItem[];
  next: number | null;
}

export interface CoinLock {
  locked: boolean;
}

/** Locked when a member's usable coins are under the price of one reply. */
export function composerCoinLock(wallet: Partial<Wallet> | null | undefined): CoinLock {
  if (!wallet) return { locked: false };
  if (wallet.enabled === false || wallet.unlimited === true) return { locked: false };
  const price = wallet.price_per_reply ?? PRICE_PER_REPLY;
  const usable = wallet.available ?? wallet.balance;
  if (typeof usable !== "number") return { locked: false };
  return { locked: usable < price };
}

/** Header chip, account row and wallet page show coins only to members while coins are on. */
export function showsCoins(wallet: Wallet | null | undefined): boolean {
  return !!wallet && wallet.enabled && !wallet.unlimited;
}

// ---------------------------------------------------------------------------- numbers and time

/** "1.200" (Vietnamese thousands). */
export function formatCoinNumber(n: number): string {
  const sign = n < 0 ? "-" : "";
  const digits = String(Math.trunc(Math.abs(n)));
  return sign + digits.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

/** "1.200 coin". */
export function formatCoins(n: number): string {
  return `${formatCoinNumber(n)} ${COIN_COPY.unit}`;
}

/** "+300" / "−18" (a real minus sign). */
export function formatDelta(n: number): string {
  return n > 0 ? `+${formatCoinNumber(n)}` : `−${formatCoinNumber(Math.abs(n))}`;
}

const pad = (n: number) => String(n).padStart(2, "0");

/** "23:15" today, "Hôm qua", else "02/11" (the device's local time). */
export function historyTime(iso: string, now: Date = new Date()): string {
  const t = new Date(iso);
  if (Number.isNaN(t.getTime())) return "";
  const day = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const diff = Math.round((day(now) - day(t)) / 86_400_000);
  if (diff <= 0) return `${pad(t.getHours())}:${pad(t.getMinutes())}`;
  if (diff === 1) return COIN_COPY.yesterday;
  return `${pad(t.getDate())}/${pad(t.getMonth() + 1)}`;
}

// ---------------------------------------------------------------------------- history

export interface HistoryGroup {
  key: string;
  label: string;
  delta: number;
  count: number;
  created_at: string;
  kind: string;
}

/**
 * The wallet history as shown: neighbouring replies of the same story on the same Vietnam day become one
 * row "{k} câu trả lời của {tên}" with the summed coins; everything else stays one row each.
 */
export function groupHistory(items: readonly CoinHistoryItem[]): HistoryGroup[] {
  const out: HistoryGroup[] = [];
  let open: { group: HistoryGroup; story: number; day: string; name: string } | null = null;
  for (const item of items) {
    const isReply = item.kind === "chat" && item.story_id !== null;
    if (isReply && open && open.story === item.story_id && open.day === item.coin_day) {
      open.group.count += 1;
      open.group.delta += item.delta;
      open.group.label = COIN_COPY.groupedReplies(open.group.count, open.name);
      continue;
    }
    const group: HistoryGroup = {
      key: `c${item.id}`,
      label: item.label,
      delta: item.delta,
      count: 1,
      created_at: item.created_at,
      kind: item.kind,
    };
    out.push(group);
    open = isReply
      ? { group, story: item.story_id as number, day: item.coin_day, name: item.name || COIN_COPY.someone }
      : null;
  }
  return out;
}

// ---------------------------------------------------------------------------- daily notice

/** "+60 coin cho hôm nay" once per Vietnam day (also when the password sign-in already added it), else null. */
export function dailyToast(res: Checkin, seenDay: string | null): string | null {
  if (res.wallet.unlimited || !res.wallet.enabled) return null;
  if (res.granted) return COIN_COPY.dailyGift(res.amount || res.today);
  if (res.today > 0 && seenDay !== res.coin_day) return COIN_COPY.dailyGift(res.today);
  return null;
}

// ---------------------------------------------------------------------------- where the wallet was opened from

export type WalletFrom = "header" | "account" | "composer" | "link";
let walletFrom: WalletFrom | null = null;

/** Called right before opening "#/coins" from a button (for the `wallet_viewed` event). */
export function noteWalletFrom(from: WalletFrom): void {
  walletFrom = from;
}

/** Where "#/coins" was opened from (once); a typed or pasted link is "link". */
export function takeWalletFrom(): WalletFrom {
  const from = walletFrom ?? "link";
  walletFrom = null;
  return from;
}

// ---------------------------------------------------------------------------- shared wallet store

export interface WalletSnapshot {
  /** null until the first load succeeds (or after a sign-out). */
  wallet: Wallet | null;
  /** the last refresh failed (the last good wallet is kept) */
  error: boolean;
  loading: boolean;
}

export interface WalletStore {
  get(): WalletSnapshot;
  subscribe(listener: () => void): () => void;
  /** Re-reads the wallet; concurrent calls share one request. */
  refresh(): Promise<Wallet | null>;
  set(wallet: Wallet): void;
  reset(): void;
}

export function createWalletStore(fetcher: () => Promise<Wallet>): WalletStore {
  let snapshot: WalletSnapshot = { wallet: null, error: false, loading: false };
  let inflight: Promise<Wallet | null> | null = null;
  let version = 0;
  const listeners = new Set<() => void>();
  const update = (patch: Partial<WalletSnapshot>) => {
    snapshot = { ...snapshot, ...patch };
    for (const l of listeners) l();
  };
  return {
    get: () => snapshot,
    subscribe(listener) {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
    refresh() {
      if (inflight) return inflight;
      const started = version;
      update({ loading: true });
      inflight = fetcher()
        .then(
          (wallet) => {
            if (version === started) update({ wallet, error: false, loading: false });
            else update({ loading: false });
            return snapshot.wallet;
          },
          () => {
            update({ error: true, loading: false });
            return snapshot.wallet;
          },
        )
        .finally(() => {
          inflight = null;
        });
      return inflight;
    },
    set(wallet) {
      version += 1;
      update({ wallet, error: false });
    },
    reset() {
      version += 1;
      update({ wallet: null, error: false, loading: false });
    },
  };
}
