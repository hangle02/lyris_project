// F47 (wiki/features/F47-tim-nhan-vat.md): "Tìm nhân vật" on Khám phá. Pure helpers (tested in search.test.ts) plus the
// small `useDebounced` hook built on the pure `createDebounced`.
//
// - Compare without diacritics and case ("ha vy" finds "Hạ Vy"; "đ" → "d"), spaces collapsed.
// - Several words: a character must match every word, in its name, role, tags or description. A word matches the START
//   of a word there ("ha" finds "Hạ", "Hải" but not the middle of "thành" or "nhà"); punctuation splits words.
// - Together with a vibe chip: both must match. Results keep the grid order. A blank box filters nothing.
// - The typed words never leave the device: `explore_searched` only says whether something was found.
import { useEffect, useRef, useState } from "react";
import { filterByVibe } from "./logic.ts";
import type { ExploreItem } from "./logic.ts";

/** Filter 250 ms after the last key. */
export const DEBOUNCE_MS = 250;

export const SEARCH_COPY = {
  placeholder: "Tìm nhân vật",
  label: "Tìm nhân vật theo tên, tag hoặc giới thiệu",
  clear: "Xoá tìm kiếm",
} as const;

/** "Không tìm thấy nhân vật nào cho “ha vy”." */
export function noResultsText(query: string): string {
  return `Không tìm thấy nhân vật nào cho “${query.trim().replace(/\s+/g, " ")}”.`;
}

/** Lowercase, no Vietnamese diacritics ("đ" → "d"), single spaces: "Hạ Vy ĐÀ LẠT" → "ha vy da lat". */
export function foldVietnamese(text: string): string {
  return text
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[đĐ]/g, "d")
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim();
}

const folded = new WeakMap<ExploreItem, string>();
const NOT_WORD = /[^\p{L}\p{N}]+/u;

/** Folded words of a text: letters and digits only (punctuation and spaces split words). */
function words(text: string): string[] {
  return foldVietnamese(text).split(NOT_WORD).filter(Boolean);
}

/**
 * Everything a search looks at: the folded words of the name, role, tags and the whole description, each preceded by
 * one space (" ha vy chu tiem sach …"), so " " + word finds a word start.
 */
export function searchText(item: ExploreItem): string {
  let text = folded.get(item);
  if (text === undefined) {
    text = " " + words([item.name, item.role, ...item.tags, item.about].join(" ")).join(" ");
    folded.set(item, text);
  }
  return text;
}

/** The words of a search (folded, punctuation dropped); [] for a blank box. */
export function queryWords(query: string): string[] {
  return words(query);
}

function matchesWords(item: ExploreItem, list: string[]): boolean {
  const text = searchText(item);
  return list.every((w) => text.includes(` ${w}`));
}

/** True when every word of `query` starts a word of the item (a blank query matches everything). */
export function matchesQuery(item: ExploreItem, query: string): boolean {
  const list = queryWords(query);
  return list.length === 0 || matchesWords(item, list);
}

/** Items matching both the search and the vibe chip, in grid order. Blank search, no vibe: the same list. */
export function filterItems(items: ExploreItem[], opts: { query: string; vibe: string | null }): ExploreItem[] {
  const byVibe = filterByVibe(items, opts.vibe);
  const list = queryWords(opts.query);
  if (list.length === 0) return byVibe;
  return byVibe.filter((it) => matchesWords(it, list));
}

export interface Debounced<T> {
  get(): T;
  /** New raw value; the settled value follows `ms` after the last call (`now`: at once, e.g. clearing the box). */
  set(value: T, opts?: { now?: boolean }): void;
  cancel(): void;
}

/** Pure core of `useDebounced`: `onSettle` runs `ms` after the last `set` (timers from the global scope). */
export function createDebounced<T>(initial: T, ms: number, onSettle: (value: T) => void): Debounced<T> {
  let settled = initial;
  let timer: ReturnType<typeof setTimeout> | null = null;
  const cancel = () => {
    if (timer !== null) clearTimeout(timer);
    timer = null;
  };
  return {
    get: () => settled,
    set(value, opts) {
      cancel();
      const settle = () => {
        timer = null;
        settled = value;
        onSettle(value);
      };
      if (opts?.now) settle();
      else timer = setTimeout(settle, ms);
    },
    cancel,
  };
}

/** `value`, 250 ms (or `ms`) after it last changed. An empty string settles at once (the box was cleared). */
export function useDebounced(value: string, ms: number = DEBOUNCE_MS): string {
  const [settled, setSettled] = useState(value);
  const ref = useRef<Debounced<string> | null>(null);
  if (ref.current === null) ref.current = createDebounced(value, ms, setSettled);
  useEffect(() => {
    ref.current?.set(value, { now: value.trim() === "" });
  }, [value]);
  useEffect(() => () => ref.current?.cancel(), []);
  return settled;
}

/** `explore_searched {has_results}` at most once per distinct settled search (folded); never for a blank box. */
export function createSearchTracker(send: (props: { has_results: boolean }) => void): {
  settled(query: string, hasResults: boolean): void;
} {
  let last = "";
  return {
    settled(query, hasResults) {
      const key = foldVietnamese(query);
      if (!key || key === last) return;
      last = key;
      send({ has_results: hasResults });
    },
  };
}
