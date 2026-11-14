import { useCallback, useEffect, useMemo, useState } from "react";
import { api, errorMessage } from "../../api/client";
import { CharacterPicture } from "../../components/CharacterPicture";
import { SHELL_CONTAINER } from "../../components/shell/layout";
import { Button, Chip, EmptyState, Skeleton } from "../../components/ui";
import { cx } from "../../components/ui/logic";
import { useAuthAccount } from "../../hooks/useAuth";
import { clearPendingDraft } from "../../lib/draftStore";
import { navigate, routeHref } from "../../lib/router";
import type { CardSummary, PublicCardSummary, TemplateInfo } from "../../types";
import {
  buildItems,
  buildVibes,
  featuredTemplate,
  fillForReader,
  filterByVibe,
  itemRoute,
  sharedItems,
  shortText,
  templateEntryRoute,
  heroImageUrl,
  withoutHero,
  vibeLabel,
} from "./logic";
import type { ExploreItem } from "./logic";

function Hero({ template, imageUrl }: { template: TemplateInfo; imageUrl: string | null }) {
  const card = template.card;
  const url = imageUrl;
  const lang = card.language === "en" ? "en" : "vi";
  const text = shortText(fillForReader(card.scenario.trim() || card.description, card.name, lang), 180);
  const role = (card.role ?? "").trim();

  return (
    <section
      aria-labelledby="explore-featured"
      className="relative overflow-hidden rounded-card transition-colors duration-150 hover:bg-surface-2 border border-edge bg-surface sm:grid sm:grid-cols-[minmax(0,240px)_minmax(0,1fr)]"
    >
      <CharacterPicture url={url} name={card.name} className="aspect-[3/1] sm:aspect-auto sm:h-full sm:min-h-[200px]" />
      <div className="flex flex-col gap-2.5 p-4 sm:justify-center sm:gap-3 sm:px-6 sm:py-5">
        <div className="flex flex-col gap-0.5">
          <h2 id="explore-featured" className="text-[20px] leading-tight font-semibold text-fg sm:text-[22px]">
            {/* The whole card opens the profile; the button below opens it with the start sheet. */}
            <a
              href={routeHref(templateEntryRoute(template))}
              className="outline-none after:absolute after:inset-0 after:rounded-card focus-visible:after:outline-2 focus-visible:after:outline-offset-2 focus-visible:after:outline-accent"
            >
              {card.name}
            </a>
          </h2>
          {role && <p className="text-[14px] leading-snug text-accent-2">{role}</p>}
        </div>
        {text && (
          <p lang={lang} className="line-clamp-2 font-story text-[15px] text-prose sm:line-clamp-3">
            {text}
          </p>
        )}
        <div className="flex flex-wrap items-center gap-x-4 gap-y-3">
          <a
            href={routeHref(templateEntryRoute(template, true))}
            className="relative z-10 inline-flex h-11 items-center justify-center rounded-full bg-accent px-5 text-[15px] font-semibold text-on-accent transition-colors duration-150 hover:bg-accent-strong focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            Bước vào câu chuyện
          </a>
          {template.vibes.length > 0 && (
            <p className="text-[14px] text-muted">{template.vibes.map(vibeLabel).join(", ")}</p>
          )}
        </div>
      </div>
    </section>
  );
}

function HeroSkeleton() {
  return (
    <div
      aria-hidden="true"
      className="overflow-hidden rounded-card border border-edge bg-surface sm:grid sm:grid-cols-[minmax(0,240px)_minmax(0,1fr)]"
    >
      <Skeleton className="aspect-[3/1] rounded-none sm:aspect-auto sm:h-full sm:min-h-[200px]" height="auto" />
      <div className="flex flex-col gap-3 p-4 sm:justify-center sm:px-6 sm:py-5">
        <Skeleton shape="text" width="40%" height={22} />
        <Skeleton shape="text" width="55%" height={14} />
        <Skeleton shape="text" lines={3} height={13} />
        <Skeleton shape="pill" width={190} height={44} />
      </div>
    </div>
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
 * Khám phá (DESIGN.md page 2, docs/design-impl.md §6.4): the featured template with its scene
 * picture, vibe filters, and a compact 4:3 grid of the user's characters plus templates not installed yet.
 * Tapping a character (or the featured card) opens its profile ("#/character/..."); the featured
 * card's "Bước vào câu chuyện" opens the profile with the persona sheet already open.
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

  const items = useMemo(() => (cards && templates ? buildItems(cards, templates) : []), [cards, templates]);
  const vibes = useMemo(() => (templates ? buildVibes(items, templates) : []), [items, templates]);
  const shown = useMemo(() => filterByVibe(items, vibe), [items, vibe]);
  const featured = useMemo(() => (templates ? featuredTemplate(templates) : null), [templates]);
  // The hero's character is not listed again in the grid (unless a vibe filter is on).
  const grid = useMemo(() => withoutHero(shown, featured, vibe), [shown, featured, vibe]);
  const sharedAll = useMemo(() => sharedItems(shared, me?.handle ?? null), [shared, me?.handle]);
  const sharedShown = useMemo(() => filterByVibe(sharedAll, vibe), [sharedAll, vibe]);

  const ready = cards !== null && templates !== null;

  return (
    <div className={cx(SHELL_CONTAINER, "flex flex-col gap-5 pt-5 sm:gap-7 sm:pt-8")}>
      <div className="flex flex-col gap-1">
        <h1 className="text-[24px] leading-tight font-semibold text-fg">Khám phá</h1>
        <p className="text-[15px] leading-snug text-muted">Chạm một nhân vật để xem hồ sơ của họ.</p>
      </div>

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
          <HeroSkeleton />
          <GridSkeleton />
        </div>
      ) : (
        <>
          {featured && <Hero template={featured} imageUrl={heroImageUrl(featured, cards ?? [])} />}

          <section aria-labelledby="explore-all" className="flex flex-col gap-4">
            <div className="flex items-baseline justify-between gap-3">
              <h2 id="explore-all" className="text-[18px] leading-tight font-semibold text-fg">
                Nhân vật
              </h2>
              <span className="text-[14px] text-muted tabular-nums">
                {vibe === null ? items.length : `${shown.length} / ${items.length}`}
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
                {vibes.map((v) => (
                  <Chip key={v} selected={vibe === v} onClick={() => setVibe(vibe === v ? null : v)}>
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
            ) : shown.length === 0 ? (
              <EmptyState
                text={`Chưa có nhân vật nào mang nét “${vibeLabel(vibe ?? "")}”.`}
                action={
                  <Button size="sm" onClick={() => setVibe(null)}>
                    Xem tất cả
                  </Button>
                }
              />
            ) : grid.length > 0 ? (
              <ul className={GRID}>
                {grid.map((item) => (
                  <ItemCard key={item.key} item={item} />
                ))}
              </ul>
            ) : null}
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
                    {vibe === null ? sharedAll.length : `${sharedShown.length} / ${sharedAll.length}`}
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
