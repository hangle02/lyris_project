import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, errorMessage } from "../../api/client";
import { CharacterPicture } from "../../components/CharacterPicture";
import { IconSearch, IconX } from "../../components/icons";
import { SHELL_CONTAINER } from "../../components/shell/layout";
import { Button, Chip, EmptyState, IconButton, Skeleton, TextField } from "../../components/ui";
import { cx } from "../../components/ui/logic";
import { useAuthAccount } from "../../hooks/useAuth";
import { clearPendingDraft } from "../../lib/draftStore";
import { navigate, routeHref } from "../../lib/router";
import { chipPosition, track, vibeCode } from "../../lib/track";
import type { CardSummary, PublicCardSummary, TemplateInfo } from "../../types";
import { HotRowLink } from "./HotRows";
import { HOT_COPY, hotRow, hotStripView } from "./hotLogic";
import type { HotBoard } from "./hotLogic";
import { buildItems, buildVibes, itemRoute, normalizeTag, sharedItems, vibeLabel } from "./logic";
import type { ExploreItem } from "./logic";
import { SEARCH_COPY, createSearchTracker, filterItems, noResultsText, queryWords, useDebounced } from "./search";

/**
 * F47: "Tìm nhân vật". A short placeholder that fits one line at 390px; the full name for screen readers in
 * aria-label. The × inside clears the box at once.
 */
function SearchBox({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const input = useRef<HTMLInputElement>(null);
  return (
    <TextField
      ref={input}
      label={SEARCH_COPY.label}
      aria-label={SEARCH_COPY.label}
      hideLabel
      type="search"
      icon={<IconSearch />}
      value={value}
      onChange={onChange}
      placeholder={SEARCH_COPY.placeholder}
      enterKeyHint="search"
      autoComplete="off"
      spellCheck={false}
      className="w-full sm:max-w-[560px]"
      inputClassName="rounded-full bg-surface-2 pr-12 [&::-webkit-search-cancel-button]:appearance-none"
      trailing={
        value ? (
          <IconButton
            label={SEARCH_COPY.clear}
            icon={<IconX />}
            noTooltip
            onClick={() => {
              onChange("");
              input.current?.focus();
            }}
          />
        ) : undefined
      }
    />
  );
}

/**
 * F46: "Nhân vật hot" on top of Khám phá (where the big featured card used to be): the first three of the
 * leaderboard and "Xem bảng xếp hạng". A ranked list, not a grid: its characters still have their cell below.
 * It is the way to #/explore/hot, so it stays with an empty or unloaded board; hidden only while searching.
 */
function HotStrip({ board, query }: { board: HotBoard | null; query: string }) {
  const view = hotStripView(board, { query });
  if (view === null) return null;
  const rows = view.rows.map(hotRow);
  return (
    <section aria-labelledby="explore-hot" className="flex flex-col gap-2 sm:max-w-[720px]">
      <div className="flex items-center justify-between gap-3">
        <h2 id="explore-hot" className="text-[18px] leading-tight font-semibold text-fg">
          {HOT_COPY.title}
        </h2>
        <a
          href={routeHref({ name: "hot" })}
          className="-mr-2 inline-flex min-h-11 items-center rounded-full px-2 text-[14px] font-semibold text-accent transition-colors duration-150 hover:text-accent-strong focus-visible:outline-2 focus-visible:outline-accent"
        >
          {HOT_COPY.seeAll}
        </a>
      </div>
      {rows.length > 0 && (
        <ol aria-label={HOT_COPY.title} className="divide-y divide-line overflow-hidden rounded-card bg-surface">
          {rows.map((row) => (
            <HotRowLink key={row.key} row={row} compact />
          ))}
        </ol>
      )}
      {view.empty && (
        <p data-hot-strip-empty className="rounded-card bg-surface px-4 py-3 text-[14px] leading-snug text-muted">
          {view.empty}
        </p>
      )}
    </section>
  );
}

// Fixed columns at every width: every card the same size in every section; a short last row stays short.
const GRID = "grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5";

/**
 * One character in the grid. Every card has the same size: a short last row keeps empty cells
 * instead of stretching its cards (user's rule, 2026-11-14); cards in a row share one height.
 */
function ItemCard({ item }: { item: ExploreItem }) {
  const route = itemRoute(item);
  return (
    <li className="flex">
      <a
        href={route ? routeHref(route) : undefined}
        aria-label={`Xem nhân vật ${item.name}${item.kind === "template" ? " (mẫu)" : item.kind === "shared" && item.creator ? `, ${item.creator}` : ""}`}
        className="group flex w-full flex-col overflow-hidden rounded-card border border-edge bg-surface text-left transition-colors duration-150 hover:bg-surface-2"
      >
        <span className="relative block">
          <CharacterPicture url={item.imageUrl} name={item.name} className="aspect-[4/3]" />
        </span>
        <span className="flex min-w-0 flex-col gap-0.5 px-3 pt-2.5 pb-3">
          <span className="truncate text-[15px] leading-snug font-semibold text-fg">{item.name}</span>
          <span className={cx("truncate text-[13px] leading-snug", item.role ? "text-accent-2" : "text-muted")}>
            {item.role || "Chưa có vai trò"}
          </span>
          {item.teaser && (
            <span className="mt-1 line-clamp-2 text-[13px] leading-snug text-prose">{item.teaser}</span>
          )}
          <span className="mt-1 truncate text-[12px] leading-snug text-muted">
            {item.creator}
          </span>
        </span>
      </a>
    </li>
  );
}

function StripSkeleton() {
  return (
    <ul aria-hidden="true" className="divide-y divide-line overflow-hidden rounded-card bg-surface sm:max-w-[720px]">
      {Array.from({ length: 3 }, (_, i) => (
        <li key={i} className="flex min-h-14 items-center gap-3 px-3 py-1.5 sm:px-4">
          <Skeleton shape="text" width={24} height={14} />
          <Skeleton shape="circle" width={44} height={44} />
          <span className="flex flex-1 flex-col gap-2">
            <Skeleton shape="text" width="50%" height={14} />
            <Skeleton shape="text" width="30%" height={12} />
          </span>
        </li>
      ))}
    </ul>
  );
}

function GridSkeleton() {
  return (
    <ul aria-hidden="true" className={GRID}>
      {Array.from({ length: 4 }, (_, i) => (
        <li key={i} className="overflow-hidden rounded-card border border-edge bg-surface">
          <Skeleton className="aspect-[4/3] rounded-none" height="auto" />
          <span className="flex flex-col gap-2 px-3 pt-2.5 pb-3">
            <Skeleton shape="text" width="60%" height={14} />
            <Skeleton shape="text" width="80%" height={12} />
            <Skeleton shape="text" lines={2} height={11} />
          </span>
        </li>
      ))}
    </ul>
  );
}

/**
 * Khám phá (DESIGN.md page 2, docs/design-impl.md §6.4, wiki/screens/explore.md): "Tìm nhân vật" (F47), the
 * "Nhân vật hot" strip (F46, in place of the old featured card), vibe filters, and a compact 4:3 grid of the user's
 * characters plus templates not installed yet, then other accounts' public characters. Every character has
 * exactly one cell. Tapping a character opens its profile ("#/character/...").
 */
export function ExplorePage() {
  const [cards, setCards] = useState<CardSummary[] | null>(null);
  const [templates, setTemplates] = useState<TemplateInfo[] | null>(null);
  /** Phase 4b: other accounts' public characters; [] when none or when they could not be read. */
  const [shared, setShared] = useState<PublicCardSummary[]>([]);
  const me = useAuthAccount();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [vibe, setVibe] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const settledQuery = useDebounced(query);
  /** F46: the first rows of the leaderboard; null when it could not be read (no strip then). */
  const [hot, setHot] = useState<HotBoard | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [c, t, p] = await Promise.all([
        api.listCards(),
        // Templates are a bonus: without them the grid still shows the user's characters.
        api.listTemplates().catch(() => [] as TemplateInfo[]),
        // Shared characters too: without them the section is simply not there.
        api.listPublicCards().catch(() => [] as PublicCardSummary[]),
      ]);
      setCards(c);
      setTemplates(t);
      setShared(p);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    let alive = true;
    api
      .getHotBoard(3)
      .then((b) => alive && setHot(b))
      .catch(() => alive && setHot(null));
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    track("explore_viewed");
  }, []);

  const items = useMemo(() => (cards && templates ? buildItems(cards, templates) : []), [cards, templates]);
  const vibes = useMemo(() => (templates ? buildVibes(items, templates) : []), [items, templates]);
  const shown = useMemo(() => filterItems(items, { query: settledQuery, vibe }), [items, settledQuery, vibe]);
  const sharedAll = useMemo(() => sharedItems(shared, me?.handle ?? null), [shared, me?.handle]);
  const sharedShown = useMemo(
    () => filterItems(sharedAll, { query: settledQuery, vibe }),
    [sharedAll, settledQuery, vibe],
  );
  const searching = queryWords(settledQuery).length > 0;
  const filtered = searching || vibe !== null;
  const nothingFound = searching && shown.length === 0 && sharedShown.length === 0;

  const ready = cards !== null && templates !== null;

  // F47: explore_searched {has_results} once per distinct settled search (never the typed words).
  const searchTracker = useRef(createSearchTracker((props) => track("explore_searched", props)));
  useEffect(() => {
    if (ready) searchTracker.current.settled(settledQuery, !nothingFound);
  }, [ready, settledQuery, nothingFound]);

  return (
    <div className={cx(SHELL_CONTAINER, "flex flex-col gap-5 pt-5 sm:gap-7 sm:pt-8")}>
      <div className="flex flex-col gap-1">
        <h1 className="text-[24px] leading-tight font-semibold text-fg">Khám phá</h1>
        <p className="text-[15px] leading-snug text-muted">Chạm một nhân vật để xem hồ sơ của họ.</p>
      </div>

      <SearchBox value={query} onChange={setQuery} />

      {error && !ready ? (
        <div role="alert" className="flex flex-col items-start gap-3 rounded-card border border-edge bg-surface p-5">
          <p className="text-[15px] text-fg">Không tải được danh sách nhân vật.</p>
          <p className="text-[14px] text-muted [overflow-wrap:anywhere]">{error}</p>
          <Button size="sm" loading={loading} onClick={() => void load()}>
            Thử lại
          </Button>
        </div>
      ) : !ready ? (
        <div aria-busy="true" className="flex flex-col gap-6 sm:gap-8">
          <span className="sr-only">Đang tải nhân vật…</span>
          <StripSkeleton />
          <GridSkeleton />
        </div>
      ) : (
        <>
          <HotStrip board={hot} query={query} />

          <section aria-labelledby="explore-all" className="flex flex-col gap-4">
            <div className="flex items-baseline justify-between gap-3">
              <h2 id="explore-all" className="text-[18px] leading-tight font-semibold text-fg">
                Nhân vật
              </h2>
              <span className="text-[14px] text-muted tabular-nums">
                {filtered ? `${shown.length} / ${items.length}` : items.length}
              </span>
            </div>

            {vibes.length > 0 && items.length > 0 && (
              <div
                role="group"
                aria-label="Lọc theo cảm xúc"
                className="flex flex-wrap gap-2"
              >
                <Chip selected={vibe === null} onClick={() => setVibe(null)}>
                  Tất cả
                </Chip>
                {vibes.map((v, i) => (
                  <Chip
                    key={v}
                    selected={vibe === v}
                    onClick={() => {
                      if (vibe !== v) {
                        // The vibe's code and the chip's place, never the tag's words.
                        const templateVibes = (templates ?? []).flatMap((t) => t.vibes);
                        track("vibe_filter_used", { vibe: vibeCode(v, templateVibes, normalizeTag), position: chipPosition(i) });
                      }
                      setVibe(vibe === v ? null : v);
                    }}
                  >
                    {vibeLabel(v)}
                  </Chip>
                ))}
              </div>
            )}

            {items.length === 0 ? (
              <EmptyState
                text="Chưa có nhân vật nào. Tạo nhân vật đầu tiên trong Studio."
                action={
                  <Button
                    size="sm"
                    variant="primary"
                    onClick={() => {
                      // A blank new card: never revive a draft the user left behind earlier.
                      clearPendingDraft();
                      navigate({ name: "card", cardId: null });
                    }}
                  >
                    Tạo nhân vật
                  </Button>
                }
              />
            ) : nothingFound ? (
              <EmptyState
                text={noResultsText(settledQuery)}
                action={
                  <Button size="sm" onClick={() => setQuery("")}>
                    {SEARCH_COPY.clear}
                  </Button>
                }
              />
            ) : shown.length === 0 && searching ? null : shown.length === 0 ? (
              <EmptyState
                text={`Chưa có nhân vật nào mang nét “${vibeLabel(vibe ?? "")}”.`}
                action={
                  <Button size="sm" onClick={() => setVibe(null)}>
                    Xem tất cả
                  </Button>
                }
              />
            ) : (
              <ul className={GRID}>
                {shown.map((item) => (
                  <ItemCard key={item.key} item={item} />
                ))}
              </ul>
            )}
          </section>

          {/* Phase 4b: other accounts' public characters. No section at all when there are none. */}
          {sharedShown.length > 0 && (
            <section aria-labelledby="explore-shared" className="flex flex-col gap-4">
              <div className="flex flex-col gap-1">
                <div className="flex items-baseline justify-between gap-3">
                  <h2 id="explore-shared" className="text-[18px] leading-tight font-semibold text-fg">
                    Nhân vật được chia sẻ
                  </h2>
                  <span className="text-[14px] text-muted tabular-nums">
                    {filtered ? `${sharedShown.length} / ${sharedAll.length}` : sharedAll.length}
                  </span>
                </div>
                <p className="text-[14px] leading-snug text-muted">Người khác trên Lyris này chia sẻ. Story bạn bắt đầu là của riêng bạn.</p>
              </div>
              <ul className={GRID}>
                {sharedShown.map((item) => (
                  <ItemCard key={item.key} item={item} />
                ))}
              </ul>
            </section>
          )}
        </>
      )}
    </div>
  );
}
