import { useCallback, useEffect, useId, useRef, useState } from "react";
import type { KeyboardEvent, ReactNode } from "react";
import { ApiError, api, errorMessage } from "../../api/client";
import { Avatar } from "../../components/Avatar";
import { IconEdit, IconPlus } from "../../components/icons";
import { SubpageHeader } from "../../components/shell/SubpageHeader";
import { Badge, Button, Card, EmptyState, InlineAlert, Skeleton } from "../../components/ui";
import { cx } from "../../components/ui/logic";
import { useAccount } from "../../hooks/useAccount";
import { clearPendingDraft } from "../../lib/draftStore";
import { initialOverlayOpen, initialTab } from "../../lib/overlayParam";
import { characterRoute, navigate, replaceRoute, routeHref } from "../../lib/router";
import { GENDER_LABELS } from "../../lib/storyOptions";
import type { AccountOut, CardSummary, PersonaOut, PublicProfile, TemplateInfo } from "../../types";
import { cardRole } from "../explore/logic";
import { defaultPersonaId } from "../personaLogic";
import { EditProfileSheet } from "./EditProfileSheet";
import { atHandle, createdCards, profileOwnership, profileStats, sameHandle, visibilityLabel } from "./logic";
import { ProfileBanner } from "./ProfileBanner";

const BACK = { href: routeHref({ name: "hub" }), label: "Về Tương tác" };

/** What the head shows: the account's own data, or the public part of someone's profile. */
interface HeadData {
  display_name: string;
  handle: string;
  bio: string;
  avatar_url: string | null;
  banner_url: string | null;
}

/** Banner, the large avatar over its lower edge, name, @handle, bio, and (owner) counts + "Sửa profile". */
function ProfileHead({ data, own, stats, onEdit }: { data: HeadData; own: boolean; stats: ReactNode; onEdit?: () => void }) {
  const bio = data.bio.trim();
  return (
    <section aria-label="Thông tin tài khoản">
      <ProfileBanner url={data.banner_url} collapseEmpty className="sm:rounded-card" />
      <div className="px-4 sm:px-5">
        <div className="flex items-end justify-between gap-3">
          <span className="relative z-10 -mt-12 flex shrink-0 rounded-full bg-bg p-1">
            <Avatar name={data.display_name} url={data.avatar_url} size={88} />
          </span>
          {own && onEdit && (
            <Button size="sm" variant="secondary" icon={<IconEdit />} onClick={onEdit} className="mb-1">
              Sửa profile
            </Button>
          )}
        </div>
        <h2 className="mt-3 text-[24px] leading-tight font-semibold text-fg [overflow-wrap:anywhere]">{data.display_name}</h2>
        <p className="mt-0.5 text-[15px] leading-snug text-muted">{atHandle(data.handle)}</p>
        {bio ? (
          <p className="mt-3 max-w-[60ch] text-[15px] leading-relaxed whitespace-pre-line text-prose [overflow-wrap:anywhere]">
            {bio}
          </p>
        ) : (
          own && <p className="mt-3 text-[15px] leading-snug text-muted">Chưa có lời giới thiệu.</p>
        )}
        {stats}
      </div>
    </section>
  );
}

function HeadSkeleton() {
  return (
    <div aria-hidden="true">
      <Skeleton className="aspect-[3/1] rounded-none sm:rounded-card" height="auto" />
      <div className="px-4 sm:px-5">
        <span className="relative z-10 -mt-12 flex w-fit rounded-full bg-bg p-1">
          <Skeleton shape="circle" width={88} height={88} />
        </span>
        <div className="mt-3 flex flex-col gap-2.5">
          <Skeleton shape="text" width="45%" height={22} />
          <Skeleton shape="text" width="25%" height={14} />
          <Skeleton shape="text" width="80%" height={14} className="mt-2" />
        </div>
      </div>
    </div>
  );
}

/**
 * `cardCount`: the length of the "Nhân vật" grid once it is loaded (it leaves out installed templates,
 * which the account's card_count includes), null while it loads (a skeleton, so the number never
 * jumps), undefined when it failed (the account's own count).
 */
function Stats({ account, cardCount }: { account: AccountOut; cardCount: number | null | undefined }) {
  return (
    <ul aria-label="Số liệu" className="mt-4 flex flex-wrap gap-x-5 gap-y-1 text-[15px]">
      {profileStats(account, cardCount ?? undefined).map((s) => (
        <li key={s.key} className="flex items-baseline gap-1">
          {s.key === "cards" && cardCount === null ? (
            <Skeleton shape="text" width={16} height={14} className="self-center" />
          ) : (
            <span className="font-semibold text-fg tabular-nums">{s.value}</span>
          )}
          <span className="text-muted">{s.label}</span>
        </li>
      ))}
    </ul>
  );
}

function Picture({ url, name }: { url: string | null; name: string }) {
  const [broken, setBroken] = useState(false);
  useEffect(() => setBroken(false), [url]);
  return (
    <span className="relative block aspect-[3/4] overflow-hidden bg-surface-3">
      {url && !broken ? (
        <img
          src={url}
          alt=""
          loading="lazy"
          decoding="async"
          draggable={false}
          onError={() => setBroken(true)}
          className="absolute inset-0 h-full w-full object-cover"
        />
      ) : (
        <span className="absolute inset-0 flex">
          <Avatar name={name} fill />
        </span>
      )}
    </span>
  );
}

/** A portrait like Khám phá: picture 3:4 with the visibility label, name, role. Links to the character's profile when given. */
function CharacterTile({ card, href, showLabel = true }: { card: CardSummary; href: string | null; showLabel?: boolean }) {
  const role = cardRole(card);
  const label = showLabel ? visibilityLabel(card.visibility) : null;
  const inner = (
    <>
      <span className="relative block">
        <Picture url={card.avatar_url} name={card.name} />
        {label && (
          <span className="absolute top-2.5 left-2.5">
            <Badge solid tone="neutral">
              {label}
            </Badge>
          </span>
        )}
      </span>
      <span className="flex min-w-0 flex-col gap-0.5 px-3.5 pt-3 pb-3.5">
        <span className="truncate text-[15px] leading-snug font-semibold text-fg">{card.name}</span>
        <span className={cx("truncate text-[13px] leading-snug", role ? "text-accent-2" : "text-muted")}>
          {role || "Chưa có vai trò"}
        </span>
      </span>
    </>
  );
  const frame = "flex w-full flex-col overflow-hidden rounded-card border border-edge bg-surface text-left";
  return (
    <li>
      {href ? (
        <a href={href} className={cx(frame, "transition-colors duration-150 hover:bg-surface-2")} aria-label={`Xem nhân vật ${card.name}`}>
          {inner}
        </a>
      ) : (
        <div className={frame}>{inner}</div>
      )}
    </li>
  );
}

const GRID = "grid grid-cols-2 gap-3 sm:grid-cols-3 sm:gap-4";

function GridSkeleton() {
  return (
    <ul aria-hidden="true" className={GRID}>
      {Array.from({ length: 4 }, (_, i) => (
        <li key={i} className="overflow-hidden rounded-card border border-edge bg-surface">
          <Skeleton className="aspect-[3/4] rounded-none" height="auto" />
          <span className="flex flex-col gap-2 px-3.5 pt-3 pb-3.5">
            <Skeleton shape="text" width="60%" height={14} />
            <Skeleton shape="text" width="80%" height={12} />
          </span>
        </li>
      ))}
    </ul>
  );
}

function LoadError({ what, error, onRetry }: { what: string; error: string; onRetry: () => void }) {
  return (
    <Card padding="md" role="alert" className="flex flex-col items-start gap-3">
      <p className="text-[15px] leading-snug text-fg">Không tải được {what}.</p>
      <p className="text-[14px] leading-snug text-muted [overflow-wrap:anywhere]">{error}</p>
      <Button size="sm" onClick={onRetry}>
        Thử lại
      </Button>
    </Card>
  );
}

function newCard() {
  // A blank new card: never revive a draft the user left behind earlier.
  clearPendingDraft();
  navigate({ name: "card", cardId: null });
}

function CharactersPanel({ cards, error, onRetry }: { cards: CardSummary[] | null; error: string | null; onRetry: () => void }) {
  if (cards === null && error) return <LoadError what="nhân vật" error={error} onRetry={onRetry} />;
  if (cards === null) {
    return (
      <div aria-busy="true">
        <span className="sr-only">Đang tải nhân vật…</span>
        <GridSkeleton />
      </div>
    );
  }
  if (cards.length === 0) {
    return (
      <EmptyState
        text="Bạn chưa tạo nhân vật nào. Nhân vật bạn tạo sẽ hiện ở đây."
        action={
          <Button size="sm" variant="primary" onClick={newCard}>
            Tạo nhân vật
          </Button>
        }
      />
    );
  }
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3">
        {/* Each tile already says "Riêng tư"; this line says where the cards live, not that again. */}
        <p className="text-[14px] leading-snug text-muted">Nhân vật bạn tạo, lưu trong tài khoản của bạn.</p>
        <Button size="sm" variant="ghost" icon={<IconPlus />} onClick={newCard} className="-mr-3 shrink-0">
          Tạo mới
        </Button>
      </div>
      <ul className={GRID}>
        {cards.map((c) => (
          <CharacterTile key={c.id} card={c} href={routeHref(characterRoute(c.id))} />
        ))}
      </ul>
    </div>
  );
}

function PersonasPanel({
  personas,
  defaultId,
  error,
  onRetry,
}: {
  personas: PersonaOut[] | null;
  /** Saved default persona (settings), null when unset or unknown. */
  defaultId: number | null;
  error: string | null;
  onRetry: () => void;
}) {
  const manage = routeHref({ name: "personas" });
  // The persona a new story starts with, as the backend picks it (saved default, else the first).
  const defaultPid = personas ? defaultPersonaId(personas, defaultId) : null;
  if (personas === null && error) return <LoadError what="persona" error={error} onRetry={onRetry} />;
  if (personas === null) {
    return (
      <div aria-busy="true" className="flex flex-col gap-2">
        <span className="sr-only">Đang tải persona…</span>
        <Skeleton shape="card" height={84} />
        <Skeleton shape="card" height={84} />
      </div>
    );
  }
  if (personas.length === 0) {
    return (
      <EmptyState
        text="Chưa có persona nào. Persona là vai bạn đóng khi trò chuyện trong story."
        action={
          <Button size="sm" variant="primary" onClick={() => navigate(manage)}>
            Tạo persona
          </Button>
        }
      />
    );
  }
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-[14px] leading-snug text-muted">Chỉ bạn thấy. Story mới dùng persona mặc định.</p>
        <Button size="sm" variant="ghost" onClick={() => navigate(manage)} className="-mr-3 shrink-0">
          Quản lý persona
        </Button>
      </div>
      <Card padding="none" className="overflow-hidden">
        <ul className="divide-y divide-line">
          {personas.map((p) => (
            <li key={p.id ?? p.name}>
              <a href={manage} className="flex gap-3.5 px-4 py-3.5 transition-colors duration-150 hover:bg-surface-2 sm:px-5">
                <Avatar name={p.name} url={p.avatar_url} size={48} />
                <span className="flex min-w-0 flex-1 flex-col gap-0.5">
                  <span className="flex min-w-0 items-center gap-2">
                    <span className="truncate text-[16px] leading-snug font-semibold text-fg">{p.name}</span>
                    {p.id !== null && p.id === defaultPid && <Badge tone="accent">Mặc định</Badge>}
                  </span>
                  <span className="text-[13px] leading-snug text-muted tabular-nums">
                    {GENDER_LABELS[p.gender]} · {p.story_count} story
                  </span>
                  {p.description.trim() && (
                    <span className="line-clamp-2 pt-0.5 text-[14px] leading-snug text-muted">{p.description.trim()}</span>
                  )}
                </span>
              </a>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}

const TAB_KEYS = ["characters", "personas"] as const;
type TabKey = (typeof TAB_KEYS)[number];

/** Underlined tabs (tablist + arrow keys); the panel below belongs to the selected one. */
function Tabs({
  tabs,
  value,
  onChange,
  idBase,
}: {
  tabs: { key: TabKey; label: string; count: number | null }[];
  value: TabKey;
  onChange: (k: TabKey) => void;
  idBase: string;
}) {
  const refs = useRef<Map<TabKey, HTMLButtonElement>>(new Map());
  const onKey = (e: KeyboardEvent<HTMLDivElement>) => {
    const i = tabs.findIndex((t) => t.key === value);
    let next = -1;
    if (e.key === "ArrowRight") next = (i + 1) % tabs.length;
    else if (e.key === "ArrowLeft") next = (i - 1 + tabs.length) % tabs.length;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = tabs.length - 1;
    const t = tabs[next];
    if (!t) return;
    e.preventDefault();
    onChange(t.key);
    refs.current.get(t.key)?.focus();
  };
  return (
    <div role="tablist" aria-label="Nội dung profile" onKeyDown={onKey} className="flex gap-6 border-b border-line">
      {tabs.map((t) => {
        const on = t.key === value;
        return (
          <button
            key={t.key}
            ref={(el) => {
              if (el) refs.current.set(t.key, el);
              else refs.current.delete(t.key);
            }}
            type="button"
            role="tab"
            id={`${idBase}-tab-${t.key}`}
            aria-selected={on}
            aria-controls={`${idBase}-panel-${t.key}`}
            tabIndex={on ? 0 : -1}
            onClick={() => onChange(t.key)}
            className={cx(
              "-mb-px inline-flex h-11 items-center gap-1.5 border-b-2 text-[15px] font-semibold transition-colors duration-150",
              on ? "border-accent text-fg" : "border-transparent text-muted hover:text-fg",
            )}
          >
            {t.label}
            {t.count !== null && <span className="font-medium text-muted tabular-nums">{t.count}</span>}
          </button>
        );
      })}
    </div>
  );
}

/** The owner's profile ("#/me", or "#/u/<own handle>"). */
function OwnProfile({ account }: { account: AccountOut }) {
  const idBase = useId();
  // "?tab=personas" / "?open=profile" open that tab / the edit sheet on load (screenshots only).
  const [tab, setTab] = useState<TabKey>(() => initialTab(TAB_KEYS, "characters"));
  const [editing, setEditing] = useState(() => initialOverlayOpen("profile"));
  const [cards, setCards] = useState<CardSummary[] | null>(null);
  const [cardsError, setCardsError] = useState<string | null>(null);
  const [personas, setPersonas] = useState<PersonaOut[] | null>(null);
  const [personasError, setPersonasError] = useState<string | null>(null);
  const [defaultPersona, setDefaultPersona] = useState<number | null>(null);
  const handle = account.handle;

  const loadCards = useCallback(async () => {
    setCardsError(null);
    try {
      const [list, templates] = await Promise.all([
        api.listCards(),
        // Templates only tell which cards are installed samples ("Mẫu của Lyris"), not the account's own.
        api.listTemplates().catch(() => [] as TemplateInfo[]),
      ]);
      setCards(createdCards(list, templates, handle));
    } catch (e) {
      setCardsError(errorMessage(e));
    }
  }, [handle]);

  const loadPersonas = useCallback(async () => {
    setPersonasError(null);
    try {
      const [list, settings] = await Promise.all([
        api.listPersonas(),
        // Only marks "Mặc định"; without settings the first persona is the default, as on the server.
        api.getSettings().catch(() => null),
      ]);
      setPersonas(list);
      setDefaultPersona(settings?.default_persona_id ?? null);
    } catch (e) {
      setPersonasError(errorMessage(e));
    }
  }, []);

  useEffect(() => {
    void loadCards();
    void loadPersonas();
  }, [loadCards, loadPersonas]);

  return (
    <>
      <ProfileHead
        data={account}
        own
        onEdit={() => setEditing(true)}
        stats={<Stats account={account} cardCount={cards ? cards.length : cardsError ? undefined : null} />}
      />
      <div className="mt-6 px-4 sm:px-5">
        <Tabs
          idBase={idBase}
          value={tab}
          onChange={setTab}
          tabs={[
            { key: "characters", label: "Nhân vật", count: cards?.length ?? null },
            { key: "personas", label: "Persona", count: personas?.length ?? null },
          ]}
        />
        <div
          role="tabpanel"
          id={`${idBase}-panel-${tab}`}
          aria-labelledby={`${idBase}-tab-${tab}`}
          tabIndex={0}
          className="rounded-card pt-4 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent"
        >
          {tab === "characters" ? (
            <CharactersPanel cards={cards} error={cardsError} onRetry={() => void loadCards()} />
          ) : (
            <PersonasPanel personas={personas} defaultId={defaultPersona} error={personasError} onRetry={() => void loadPersonas()} />
          )}
        </div>
      </div>
      <EditProfileSheet open={editing} onClose={() => setEditing(false)} />
    </>
  );
}

/** Someone else's public profile ("#/u/<handle>"): only what they made public. */
function PublicProfileView({ handle }: { handle: string }) {
  const [profile, setProfile] = useState<PublicProfile | null>(null);
  const [error, setError] = useState<{ text: string; notFound: boolean } | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let alive = true;
    setError(null);
    api
      .getProfile(handle)
      .then((p) => alive && setProfile(p))
      .catch((e: unknown) => {
        if (alive) setError({ text: errorMessage(e), notFound: e instanceof ApiError && e.status === 404 });
      });
    return () => {
      alive = false;
    };
  }, [handle, tick]);

  if (!profile && error?.notFound) {
    return (
      <div className="px-4 pt-6 sm:px-0">
        <EmptyState
          text={`Không có tài khoản ${atHandle(handle)} trên Lyris.`}
          action={
            <Button size="sm" onClick={() => navigate({ name: "hub" })}>
              Về Tương tác
            </Button>
          }
        />
      </div>
    );
  }
  if (!profile && error) {
    return (
      <div className="px-4 pt-6 sm:px-0">
        <LoadError what={`profile ${atHandle(handle)}`} error={error.text} onRetry={() => setTick((n) => n + 1)} />
      </div>
    );
  }
  if (!profile) {
    return (
      <div aria-busy="true">
        <span className="sr-only">Đang tải profile…</span>
        <HeadSkeleton />
      </div>
    );
  }
  return (
    <>
      <ProfileHead data={profile} own={false} stats={null} />
      <section aria-labelledby="profile-public-cards" className="mt-6 flex flex-col gap-4 px-4 sm:px-5">
        <div className="flex items-baseline justify-between gap-3 border-b border-line pb-3">
          <h3 id="profile-public-cards" className="text-[18px] leading-tight font-semibold text-fg">
            Nhân vật
          </h3>
          <span className="text-[14px] text-muted tabular-nums">{profile.cards.length}</span>
        </div>
        {profile.cards.length === 0 ? (
          <EmptyState text={`${profile.display_name} chưa chia sẻ nhân vật nào.`} />
        ) : (
          <ul className={GRID}>
            {profile.cards.map((c) => (
              // Phase 4b: someone's public character opens its read-only profile (no label: all are public here).
              <CharacterTile key={c.uid ?? c.id} card={c} href={routeHref(characterRoute(c.id))} showLabel={false} />
            ))}
          </ul>
        )}
      </section>
    </>
  );
}

/**
 * Account profile (docs/accounts.md §5): "#/me" is yours (counts, "Sửa profile", tabs Nhân vật and
 * Persona); "#/u/<handle>" shows someone's public profile, or yours when the handle is your own.
 * Full screen without the tab bar, like the other subpages.
 */
export function ProfilePage({ handle }: { handle: string | null }) {
  const { account, error, loading, refresh } = useAccount();

  // Counts change when cards, stories or personas are made elsewhere: re-read on every visit.
  useEffect(() => {
    void refresh();
  }, [refresh]);

  // The handle this "#/u/<handle>" route last matched as the account's own. A rename saved here
  // ("Sửa profile") changes the account's handle before the route: the page stays the owner's and the
  // route follows to the new handle, instead of asking the server for the old handle (404).
  const lastOwnHandle = useRef<string | null>(null);
  const { own, follow } = profileOwnership(handle, account?.handle ?? null, lastOwnHandle.current);
  useEffect(() => {
    if (handle !== null && account !== null && sameHandle(handle, account.handle)) lastOwnHandle.current = account.handle;
  }, [handle, account]);
  useEffect(() => {
    if (follow !== null) replaceRoute({ name: "profile", handle: follow });
  }, [follow]);
  // "#/u/<handle>" waits for the account to know whether it is yours (unless the account cannot load).
  const deciding = handle !== null && account === null && error === null;

  let content: ReactNode;
  if (own && account) {
    content = <OwnProfile account={account} />;
  } else if (own && handle === null) {
    content = error ? (
      <div className="px-4 pt-6 sm:px-0">
        <InlineAlert tone="error" text={`Không tải được tài khoản. ${error}`} onRetry={() => void refresh()} retryDisabled={loading} />
      </div>
    ) : (
      <div aria-busy="true">
        <span className="sr-only">Đang tải profile…</span>
        <HeadSkeleton />
      </div>
    );
  } else if (deciding) {
    content = (
      <div aria-busy="true">
        <span className="sr-only">Đang tải profile…</span>
        <HeadSkeleton />
      </div>
    );
  } else {
    content = <PublicProfileView handle={handle ?? ""} />;
  }

  return (
    <div className="min-h-dvh bg-bg">
      <SubpageHeader backHref={BACK.href} backLabel={BACK.label} title="Profile" subtitle={own ? "Tài khoản của bạn" : undefined} />
      <main className="mx-auto w-full max-w-[720px] pb-[calc(48px+env(safe-area-inset-bottom))] sm:px-6 sm:pt-6">{content}</main>
    </div>
  );
}
