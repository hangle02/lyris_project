// F46 (docs/coins.md §5.2, §5.7; wiki/screens/hot-ranking.md): pure helpers of the "Nhân vật hot" leaderboard
// (#/explore/hot) and of the strip at the top of Khám phá. Tested in hotLogic.test.ts. No React, no DOM.
import { formatCoinNumber } from "../../lib/coins.ts";
import { characterRoute, routeHref } from "../../lib/router.ts";
import { byHandle } from "./logic.ts";

/** One row of GET /api/explore/hot (public fields only). */
export interface HotItem {
  rank: number;
  card_id: number;
  name: string;
  avatar_url: string | null;
  creator_handle: string;
  players: number;
}

/** GET /api/explore/hot: the latest computed board (computed at most once an hour). */
export interface HotBoard {
  /** When the board was computed (ISO, UTC); null before the first computation. */
  updated_at: string | null;
  /** How many characters are ranked in all (the list keeps the first 100). */
  ranked: number;
  items: HotItem[];
}

export const HOT_COPY = {
  title: "Nhân vật hot",
  subtitle: "Xếp theo tổng số người chơi. Cập nhật mỗi giờ.",
  seeAll: "Xem bảng xếp hạng",
  back: "Về Khám phá",
  listLabel: "Bảng xếp hạng Nhân vật hot",
  rewardNote: "Nhân vật của bạn vào top 100, top 50, top 10 thì bạn được thưởng 100, 200, 300 coin.",
  rewardRule: "Thưởng top N chỉ có khi bảng có nhân vật của ít nhất N người tạo khác nhau.",
  emptyTitle: "Chưa có nhân vật nào trên bảng xếp hạng.",
  stripEmpty: "Chưa có nhân vật nào trên bảng xếp hạng.",
  emptyHint: "Công khai nhân vật của bạn trong Studio để người khác cùng chơi.",
  openStudio: "Mở Studio",
  error: "Không tải được bảng xếp hạng.",
  retry: "Thử lại",
  loading: "Đang tải bảng xếp hạng…",
} as const;

/** How many rows the strip on Khám phá shows. */
export const STRIP_ROWS = 3;

function pad(n: number): string {
  return String(n).padStart(2, "0");
}

/** "Cập nhật lúc 14:05" in the viewer's own clock; null without a (valid) time. */
export function updatedLabel(updatedAt: string | null | undefined): string | null {
  if (!updatedAt) return null;
  const d = new Date(updatedAt);
  if (Number.isNaN(d.getTime())) return null;
  return `Cập nhật lúc ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** "12 người chơi", "1.200 người chơi". */
export function playersLabel(n: number): string {
  return `${formatCoinNumber(n)} người chơi`;
}

/** aria-label of a row: "Hạng 1: Hạ Vy, 12 người chơi". */
export function rowLabel(item: Pick<HotItem, "rank" | "name" | "players">): string {
  return `Hạng ${item.rank}: ${item.name}, ${playersLabel(item.players)}`;
}

export interface HotRow {
  key: string;
  rank: number;
  cardId: number;
  name: string;
  by: string | null;
  players: string;
  label: string;
  href: string;
  imageUrl: string | null;
  /** Ranks 1–3 are drawn in the accent colour. */
  top: boolean;
}

export function hotRow(item: HotItem): HotRow {
  return {
    key: `hot-${item.card_id}`,
    rank: item.rank,
    cardId: item.card_id,
    name: item.name,
    by: byHandle(item.creator_handle),
    players: playersLabel(item.players),
    label: rowLabel(item),
    href: routeHref(characterRoute(item.card_id)),
    imageUrl: item.avatar_url,
    top: item.rank <= 3,
  };
}

export type HotView =
  | { kind: "empty"; title: string; hint: string; action: { label: string; href: string } }
  | { kind: "list"; rows: HotRow[] };

/** What #/explore/hot shows for a loaded board. */
export function hotView(board: Pick<HotBoard, "items">): HotView {
  if (board.items.length === 0) {
    return {
      kind: "empty",
      title: HOT_COPY.emptyTitle,
      hint: HOT_COPY.emptyHint,
      action: { label: HOT_COPY.openStudio, href: routeHref({ name: "studio" }) },
    };
  }
  return { kind: "list", rows: board.items.map(hotRow) };
}

/**
 * Rows of the "Nhân vật hot" strip on Khám phá: the first three. None (no strip at all) when the board is
 * empty, could not be loaded (`board` null), or a search is typed.
 */
export function hotStripItems(board: Pick<HotBoard, "items"> | null, opts: { query: string }): HotItem[] {
  if (!board || opts.query.trim() !== "") return [];
  return board.items.slice(0, STRIP_ROWS);
}

/**
 * The strip on Khám phá. It is the way to #/explore/hot, so it stays (title and "Xem bảng xếp hạng") when the board is
 * empty (one line saying so) or not loaded yet / failed (no rows); hidden (null) only while a search is typed.
 */
export function hotStripView(
  board: Pick<HotBoard, "items"> | null,
  opts: { query: string },
): { rows: HotItem[]; empty: string | null } | null {
  if (opts.query.trim() !== "") return null;
  const rows = hotStripItems(board, opts);
  return { rows, empty: board && board.items.length === 0 ? HOT_COPY.stripEmpty : null };
}

/**
 * The reward lines: only for a member while coins are on (the managing account and LYRIS_COINS=0 get none). The rule
 * says why a small board pays nothing yet.
 */
export function rewardNote(wallet: { unlimited: boolean; enabled: boolean } | null | undefined): string | null {
  if (!wallet || wallet.unlimited || !wallet.enabled) return null;
  return `${HOT_COPY.rewardNote} ${HOT_COPY.rewardRule}`;
}

/** `from` of hot_board_viewed: the "Xem bảng xếp hạng" button of Khám phá, or any other way in. */
export function hotFrom(previousRoute: string | null): "explore" | "link" {
  return previousRoute === "explore" ? "explore" : "link";
}
