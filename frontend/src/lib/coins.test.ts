// F42 (docs/coins.md §10): the composer lock, the "Tạo lại câu trả lời" lock reason, the shared wallet
// store (a refresh unlocks without reloading), the history grouping, Vietnamese number format and the
// words of the member's coin screens.
import { test } from "node:test";
import assert from "node:assert/strict";
import { COIN_COPY, allCoinStrings } from "./coinCopy.ts";
import {
  composerCoinLock,
  createWalletStore,
  dailyToast,
  formatCoins,
  formatDelta,
  formatCoinNumber,
  groupHistory,
  historyTime,
  takeWalletFrom,
  noteWalletFrom,
} from "./coins.ts";
import type { CoinHistoryItem, Wallet } from "./coins.ts";
import { LOCK_NO_COINS_REGEN, LOCK_REPLYING, regenerateLockReason } from "./actionLock.ts";

const member = (over: Partial<Wallet> = {}): Wallet => ({
  balance: 300,
  available: 300,
  unlimited: false,
  price_per_reply: 6,
  enabled: true,
  ...over,
});

test("composerCoinLock: under 6 usable coins locks the composer and Tạo lại says why", () => {
  const lock = composerCoinLock({ available: 4 });
  assert.equal(lock.locked, true);
  assert.equal(regenerateLockReason(null, lock), "Cần 6 coin để tạo lại.");
  assert.equal(LOCK_NO_COINS_REGEN, "Cần 6 coin để tạo lại.");
  // The page's own reason (a reply streaming) comes first: the player can stop it.
  assert.equal(regenerateLockReason(LOCK_REPLYING, lock), LOCK_REPLYING);
  assert.equal(composerCoinLock(member({ available: 6, balance: 6 })).locked, false);
  assert.equal(regenerateLockReason(null, composerCoinLock(member())), null);
  // Balance 10 with 6 held by a reply on its way: 4 usable -> locked.
  assert.equal(composerCoinLock(member({ balance: 10, available: 4 })).locked, true);
  // Not loaded yet: never lock on a guess.
  assert.equal(composerCoinLock(null).locked, false);
  assert.equal(composerCoinLock(undefined).locked, false);
});

test("composerCoinLock: the owner (unlimited) and coins turned off are never locked", () => {
  for (const available of [0, 4, 5]) {
    assert.equal(composerCoinLock({ available, balance: 0, unlimited: true }).locked, false);
    assert.equal(composerCoinLock(member({ available, balance: available, enabled: false })).locked, false);
  }
});

test("wallet store: a refresh to 6 coins unlocks without reloading the page", async () => {
  let next: Wallet = member({ balance: 4, available: 4 });
  const store = createWalletStore(async () => next);
  const seen: boolean[] = [];
  const stop = store.subscribe(() => {
    if (store.get().wallet) seen.push(composerCoinLock(store.get().wallet).locked);
  });
  await store.refresh();
  assert.equal(composerCoinLock(store.get().wallet).locked, true);
  next = member({ balance: 6, available: 6 });
  await store.refresh();
  assert.equal(composerCoinLock(store.get().wallet).locked, false);
  assert.deepEqual(seen.filter((x, i) => i === 0 || x !== seen[i - 1]), [true, false]);
  stop();
  // A failed refresh keeps the last good wallet.
  const failing = createWalletStore(async () => {
    throw new Error("mạng");
  });
  failing.set(member({ available: 6, balance: 6 }));
  await failing.refresh();
  assert.equal(failing.get().wallet?.available, 6);
  assert.equal(failing.get().error, true);
  // Concurrent refreshes share one request.
  let calls = 0;
  const shared = createWalletStore(async () => {
    calls += 1;
    return member();
  });
  await Promise.all([shared.refresh(), shared.refresh(), shared.refresh()]);
  assert.equal(calls, 1);
  shared.reset();
  assert.equal(shared.get().wallet, null);
});

test("formatCoins and deltas use Vietnamese thousands", () => {
  assert.equal(formatCoins(1200), "1.200 coin");
  assert.equal(formatCoins(6), "6 coin");
  assert.equal(formatCoins(2500000), "2.500.000 coin");
  assert.equal(formatCoinNumber(360), "360");
  assert.equal(formatDelta(300), "+300");
  assert.equal(formatDelta(-1200), "−1.200");
});

const row = (id: number, over: Partial<CoinHistoryItem>): CoinHistoryItem => ({
  id,
  delta: -6,
  kind: "chat",
  label: "Câu trả lời của Hạ Vy",
  created_at: "2026-11-14T10:00:00.000Z",
  balance_after: 0,
  coin_day: "2026-11-14",
  story_id: 1,
  name: "Hạ Vy",
  ...over,
});

test("groupHistory folds neighbouring replies of one story on one day", () => {
  const items = [
    row(9, { created_at: "2026-11-14T12:00:00.000Z" }),
    row(8, {}),
    row(7, {}),
    row(6, { story_id: 2, name: "Lạc Dương", label: "Câu trả lời của Lạc Dương" }),
    row(5, { kind: "daily_login", delta: 60, label: "Đăng nhập hôm nay", story_id: null, name: null }),
    row(4, {}),
    row(3, { coin_day: "2026-11-13" }),
    row(2, { story_id: null, name: null, label: "Chat thử ở Studio" }),
    row(1, { story_id: null, name: null, label: "Chat thử ở Studio" }),
    row(0, { kind: "signup_grant", delta: 300, label: "Quà tạo tài khoản", story_id: null, name: null }),
  ];
  const groups = groupHistory(items);
  assert.deepEqual(
    groups.map((g) => [g.label, g.delta, g.count]),
    [
      ["3 câu trả lời của Hạ Vy", -18, 3],
      ["Câu trả lời của Lạc Dương", -6, 1],
      ["Đăng nhập hôm nay", 60, 1],
      ["Câu trả lời của Hạ Vy", -6, 1],
      ["Câu trả lời của Hạ Vy", -6, 1],
      ["Chat thử ở Studio", -6, 1],
      ["Chat thử ở Studio", -6, 1],
      ["Quà tạo tài khoản", 300, 1],
    ],
  );
  // The newest time of a group is shown; keys are unique.
  assert.equal(groups[0]?.created_at, "2026-11-14T12:00:00.000Z");
  assert.equal(new Set(groups.map((g) => g.key)).size, groups.length);
  assert.equal(COIN_COPY.groupedReplies(2, "Vy"), "2 câu trả lời của Vy");
});

test("historyTime: today as hour, yesterday as Hôm qua, older as day/month", () => {
  const now = new Date(2026, 10, 14, 20, 0);
  assert.equal(historyTime(new Date(2026, 10, 14, 9, 5).toISOString(), now), "09:05");
  assert.equal(historyTime(new Date(2026, 10, 13, 23, 0).toISOString(), now), "Hôm qua");
  assert.equal(historyTime(new Date(2026, 10, 2, 8, 0).toISOString(), now), "02/11");
});

test("daily notice: shown once a day, also when sign-in already added the gift", () => {
  const w = member();
  const fresh = { granted: true, amount: 60, today: 60, coin_day: "2026-11-14", wallet: w };
  assert.equal(dailyToast(fresh, null), "+60 coin cho hôm nay");
  const signedIn = { granted: false, amount: 0, today: 60, coin_day: "2026-11-14", wallet: w };
  assert.equal(dailyToast(signedIn, null), "+60 coin cho hôm nay");
  assert.equal(dailyToast(signedIn, "2026-11-14"), null);
  assert.equal(dailyToast(signedIn, "2026-11-13"), "+60 coin cho hôm nay");
  const owner = { granted: false, amount: 0, today: 0, coin_day: "2026-11-14", wallet: member({ unlimited: true }) };
  assert.equal(dailyToast(owner, null), null);
});

test("wallet_viewed source is taken once, then defaults to link", () => {
  noteWalletFrom("header");
  assert.equal(takeWalletFrom(), "header");
  assert.equal(takeWalletFrom(), "link");
});

test("coin copy never says chủ máy, token, credits, model or Ollama", () => {
  const all = allCoinStrings();
  assert.ok(all.length >= 25);
  for (const s of all) {
    assert.doesNotMatch(s, /chủ máy|token|credits|model|ollama/i, s);
  }
  assert.equal(COIN_COPY.chipLabel("1.200"), "Coin: 1.200. Mở ví coin");
  assert.equal(COIN_COPY.ownerNote, "Tài khoản quản lý không tốn coin.");
});
