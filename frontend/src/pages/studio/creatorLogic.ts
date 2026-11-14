// F44 làm lại (docs/coins.md §5.7, wiki/screens/card-editor.md): the players and ranking block under the "Công khai"
// switch of the Studio editor, for a character saved as public. Pure, tested in creatorLogic.test.ts.
//   "12 người chơi · Hạng 7 Nhân vật hot"
//   "Bậc thưởng tiếp theo: top 50 (+200 coin)" / "Đã nhận đủ thưởng xếp hạng"
//   "Thưởng đang chờ: +300 coin (tối đa 600 coin mỗi 7 ngày)"
//   "Thưởng top 10 chỉ có khi bảng có nhân vật của ít nhất 10 người tạo khác nhau (hiện có 1)."
// The managing account and coins turned off get no coins: the server sends `next_reward: null` and the block
// promises nothing ("Bậc tiếp theo: top 50").
import { COIN_COPY } from "../../lib/coinCopy.ts";
import { formatCoinNumber } from "../../lib/coins.ts";

/** `creator` of GET/PUT /api/cards/{id}: only for the creator of a saved public character. */
export interface CreatorProgress {
  players: number;
  /** Rank on the latest "Nhân vật hot" board; null when not on it. */
  rank: number | null;
  /** Smallest tier not reached yet (100 → 50 → 10); null when all three are reached. */
  next_tier: number | null;
  /** null: no reward (the managing account, coins off) or all reached. */
  next_reward: number | null;
  /** Rewards reached but waiting (600 coins per 7 days at most). */
  waiting_coins: number;
  /** How many different creators have a ranked character: a top N tier pays only when this is at least N. */
  board_creators: number;
}

export interface CreatorBlock {
  head: string;
  reward: string | null;
  /** Why the next tier cannot pay yet (the board has characters of fewer than N creators); null otherwise. */
  rule: string | null;
  waiting: string | null;
}

/** The block, or null when there is nothing to show (private, unsaved, someone else's character). */
export function creatorBlock(
  progress: CreatorProgress | null | undefined,
  opts: { rewards?: boolean } = {},
): CreatorBlock | null {
  if (!progress) return null;
  const players = COIN_COPY.creatorPlayers(formatCoinNumber(progress.players));
  const place = progress.rank === null ? COIN_COPY.creatorUnranked : COIN_COPY.creatorRank(formatCoinNumber(progress.rank));
  const coins = opts.rewards !== false;
  let reward: string | null;
  if (progress.next_tier === null) reward = coins ? COIN_COPY.creatorDone : null;
  else if (progress.next_reward !== null && coins) {
    reward = COIN_COPY.creatorNextReward(String(progress.next_tier), formatCoinNumber(progress.next_reward));
  } else reward = COIN_COPY.creatorNextTier(String(progress.next_tier));
  const waiting = coins && progress.waiting_coins > 0 ? COIN_COPY.creatorWaiting(formatCoinNumber(progress.waiting_coins)) : null;
  const tier = progress.next_tier;
  const rule =
    coins && tier !== null && progress.next_reward !== null && progress.board_creators < tier
      ? COIN_COPY.creatorTierRule(String(tier), formatCoinNumber(progress.board_creators))
      : null;
  return { head: `${players} · ${place}`, reward, rule, waiting };
}
