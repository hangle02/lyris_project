import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import { ApiError, api, errorMessage, errorTechnical } from "../../api/client";
import { CharacterPicture } from "../../components/CharacterPicture";
import { IconEdit, IconFlag } from "../../components/icons";
import { SubpageHeader } from "../../components/shell/SubpageHeader";
import { Button, Chip, EmptyState, InlineAlert, Meter, Skeleton, Toast } from "../../components/ui";
import { REPORT_CARD_LABEL, REPORT_DONE } from "../../lib/compliance";
import { ReportSheet } from "../chat/ReportSheet";
import { cx } from "../../components/ui/logic";
import { characterRoute, navigate, replaceRoute, routeHref, templateRoute } from "../../lib/router";
import { previousRouteName, profileFrom, track } from "../../lib/track";
import type { CardSource } from "../../lib/track";
import type { CharacterTarget } from "../../lib/router";
import { signatureLinesFor } from "../../lib/signatureLines";
import { formatActivity } from "../../lib/storyOptions";
import type { CardOut, CharacterCard, LoreSummary, StoryOut, StyleProfileInfo, TemplateInfo } from "../../types";
import {
  byHandle,
  creatorLine,
  installedTemplateIds,
  isInstalledTemplate,
  TEMPLATE_CREDIT,
  templateImageUrl,
} from "../explore/logic";
import {
  cardFromPublic,
  ENTER_LABEL,
  introSections,
  profileTags,
  settingGroups,
  sharedStartNote,
  startingEmotions,
  storiesWith,
  templateOfCard,
  worldTeaser,
} from "./logic";
import type { WorldTeaser } from "./logic";
import { StartStorySheet } from "./StartStorySheet";

interface Props {
  target: CharacterTarget;
  /** "?start=1": open the start sheet on arrival. */
  start: boolean;
}

interface Profile {
  card: CharacterCard;
  /** Saved card id; null for a template not installed yet. */
  cardId: number | null;
  /** Template slug when the profile is a template not installed yet. */
  slug: string | null;
  /** Installed from a template, or a template: "Mẫu của Lyris", never editable. */
  isTemplate: boolean;
  pictureUrl: string | null;
  creator: string | null;
  tags: string[];
  stories: StoryOut[];
  /**
   * Phase 4b: someone else's public character, or the copy behind one of your stories (read only;
   * `canStart` false for a copy). Null for your own cards and templates.
   */
  shared: { creatorHandle: string | null; canStart: boolean } | null;
}

type State =
  | { kind: "loading" }
  | { kind: "ready"; profile: Profile }
  | { kind: "missing" }
  | { kind: "error"; text: string; technical: string | null };

const BACK = { href: routeHref({ name: "explore" }), label: "Về Khám phá" };

/** The card id of a template: the installed one, or install it now (the backend returns the old card if it exists). */
async function cardIdForTemplate(slug: string, installed: number | null): Promise<number> {
  if (installed !== null) return installed;
  const card = await api.installTemplate(slug);
  if (card.id === null) throw new Error("Không mở được nhân vật này. Hãy thử lại.");
  return card.id;
}

/** Someone else's public character (or a story's copy): GET /api/cards/{id}/public. 404 when neither. */
async function loadPublicProfile(id: number, stories: Promise<StoryOut[]>): Promise<Profile> {
  const [view, list] = await Promise.all([api.getPublicCard(id), stories]);
  return {
    card: cardFromPublic(view),
    cardId: id,
    slug: null,
    isTemplate: false,
    pictureUrl: view.avatar_url,
    creator: byHandle(view.creator_handle),
    tags: profileTags(view.tags),
    stories: storiesWith(list, id),
    shared: { creatorHandle: view.creator_handle, canStart: view.can_start },
  };
}

async function loadCardProfile(id: number): Promise<Profile> {
  const storyList = api.listStories().catch(() => [] as StoryOut[]);
  let own: CardOut;
  try {
    own = await api.getCard(id);
  } catch (e) {
    // Not one of yours (or a story's copy): the read-only public profile, if there is one.
    if (e instanceof ApiError && e.status === 404) return loadPublicProfile(id, storyList);
    throw e;
  }
  const [card, templates, stories] = await Promise.all([
    Promise.resolve(own),
    // Templates only add the vibes, the scene picture and the "Mẫu của Lyris" credit.
    api.listTemplates().catch(() => null as TemplateInfo[] | null),
    storyList,
  ]);
  const template = templateOfCard(templates, id);
  const isTemplate = isInstalledTemplate(id, card.extensions, templates ? installedTemplateIds(templates) : null);
  return {
    card,
    cardId: id,
    slug: null,
    isTemplate,
    pictureUrl: (card as CardOut).avatar_url ?? (template ? templateImageUrl(template) : null),
    creator: creatorLine({ template: isTemplate, handle: card.creator_handle }),
    tags: profileTags(card.tags, template?.vibes ?? []),
    stories: storiesWith(stories, id),
    shared: null,
  };
}

function templateProfile(t: TemplateInfo): Profile {
  return {
    card: t.card,
    cardId: null,
    slug: t.slug,
    isTemplate: true,
    pictureUrl: templateImageUrl(t),
    creator: TEMPLATE_CREDIT,
    tags: profileTags(t.card.tags, t.vibes),
    stories: [],
    shared: null,
  };
}

function PageSkeleton() {
  return (
    <div aria-busy="true" className="md:grid md:grid-cols-[minmax(0,340px)_minmax(0,1fr)] md:items-start md:gap-10">
      <span className="sr-only">Đang tải nhân vật…</span>
      <Skeleton className="aspect-[4/5] w-full" height="auto" shape="card" />
      <div className="mt-5 flex flex-col gap-3 md:mt-2">
        <Skeleton shape="text" width="55%" height={34} />
        <Skeleton shape="text" width="40%" height={16} />
        <Skeleton shape="text" width="30%" height={13} />
        <div className="mt-2 flex gap-2">
          <Skeleton shape="pill" width={84} height={28} />
          <Skeleton shape="pill" width={96} height={28} />
        </div>
        <Skeleton className="mt-4" height={64} shape="card" />
        <Skeleton height={64} shape="card" />
      </div>
    </div>
  );
}

type TabKey = "intro" | "setup";
const TABS: readonly { key: TabKey; label: string }[] = [
  { key: "intro", label: "Giới thiệu" },
  { key: "setup", label: "Thiết lập" },
];

function Tabs({ value, onChange, idBase }: { value: TabKey; onChange: (t: TabKey) => void; idBase: string }) {
  const refs = useRef(new Map<TabKey, HTMLButtonElement>());
  const onKey = (e: KeyboardEvent<HTMLDivElement>) => {
    const i = TABS.findIndex((t) => t.key === value);
    let next = -1;
    if (e.key === "ArrowRight") next = (i + 1) % TABS.length;
    else if (e.key === "ArrowLeft") next = (i - 1 + TABS.length) % TABS.length;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = TABS.length - 1;
    const t = TABS[next];
    if (!t) return;
    e.preventDefault();
    onChange(t.key);
    refs.current.get(t.key)?.focus();
  };
  return (
    <div role="tablist" aria-label="Thông tin nhân vật" onKeyDown={onKey} className="flex gap-6 border-b border-line">
      {TABS.map((t) => {
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
              "-mb-px inline-flex h-11 items-center border-b-2 text-[15px] font-semibold transition-colors duration-150",
              on ? "border-accent text-fg" : "border-transparent text-muted hover:text-fg",
            )}
          >
            {t.label}
          </button>
        );
      })}
    </div>
  );
}

/**
 * "Thế giới" (Phase 4): how much of the character's world exists, and the names of people and places
 * everyone knows. Never an entry's content, a story entry's title or anything only one person knows.
 */
function WorldTeaserView({ teaser }: { teaser: WorldTeaser }) {
  return (
    <section className="flex flex-col gap-3">
      <div className="flex flex-col gap-1">
        <h4 className="text-[15px] leading-tight font-semibold text-fg">Thế giới</h4>
        <p className="text-[14px] leading-snug text-muted">{teaser.line}</p>
      </div>
      {teaser.groups.map((g) => (
        <div key={g.title} className="flex flex-col gap-2">
          <p className="text-[13px] leading-snug font-medium text-muted">{g.title}</p>
          <ul aria-label={g.title} className="flex flex-wrap gap-2">
            {g.names.map((n) => (
              <li key={n} className="max-w-full">
                <Chip size="sm">{n}</Chip>
              </li>
            ))}
            {g.more > 0 && (
              <li>
                <Chip size="sm">+{g.more}</Chip>
              </li>
            )}
          </ul>
        </div>
      ))}
    </section>
  );
}

function IntroPanel({ card, world }: { card: CharacterCard; world: WorldTeaser | null }) {
  const sections = introSections(card);
  const lang = card.language === "en" ? "en" : "vi";
  if (sections.length === 0 && !world) {
    return <p className="text-[15px] text-muted">Người tạo chưa viết giới thiệu cho nhân vật này.</p>;
  }
  return (
    <div className="flex flex-col gap-6">
      {sections.length === 0 && <p className="text-[15px] text-muted">Người tạo chưa viết giới thiệu cho nhân vật này.</p>}
      {sections.map((s) => (
        <section key={s.key} className="flex flex-col gap-2">
          <h4 className="text-[15px] leading-tight font-semibold text-fg">{s.title}</h4>
          {s.paragraphs.map((p, i) => (
            <p key={i} lang={lang} className="font-story text-[16px] text-prose [overflow-wrap:anywhere]">
              {p}
            </p>
          ))}
        </section>
      ))}
      {world && <WorldTeaserView teaser={world} />}
    </div>
  );
}

function SetupPanel({ card, profile }: { card: CharacterCard; profile: StyleProfileInfo | null }) {
  const groups = settingGroups(card, profile);
  const emotions = startingEmotions(card);
  return (
    <div className="flex flex-col gap-7">
      {groups.map((g) => (
        <section key={g.title} className="flex flex-col gap-3">
          <h4 className="text-[15px] leading-tight font-semibold text-fg">{g.title}</h4>
          <dl className="flex flex-col divide-y divide-line">
            {g.rows.map((r) => (
              <div key={r.label} className="grid grid-cols-[minmax(0,2fr)_minmax(0,3fr)] gap-4 py-2.5 first:pt-0">
                <dt className="text-[14px] leading-snug text-muted">{r.label}</dt>
                <dd className="text-[15px] leading-snug text-fg [overflow-wrap:anywhere]">{r.value}</dd>
              </div>
            ))}
          </dl>
        </section>
      ))}
      {emotions && (
        <section className="flex flex-col gap-3">
          <div className="flex flex-col gap-1">
            <h4 className="text-[15px] leading-tight font-semibold text-fg">Cảm xúc ban đầu</h4>
            <p className="text-[13px] leading-snug text-muted">
              Mỗi story mới bắt đầu từ đây, rồi đổi theo những gì hai người trải qua.
            </p>
          </div>
          <div className="grid gap-x-8 gap-y-4 sm:grid-cols-2">
            {emotions.map((e) => (
              <Meter key={e.key} label={e.label} value={e.value} color={`var(--color-emo-${e.key})`} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function StoryList({ name, stories }: { name: string; stories: StoryOut[] }) {
  return (
    <section aria-labelledby="character-stories" className="flex flex-col gap-3">
      <h3 id="character-stories" className="text-[18px] leading-tight font-semibold text-fg">
        Story của bạn với {name}
      </h3>
      <ul className="flex flex-col overflow-hidden rounded-card border border-edge bg-surface">
        {stories.map((s, i) => (
          <li key={s.id} className={cx(i > 0 && "border-t border-line")}>
            <a
              href={routeHref({ name: "chat", storyId: s.id })}
              className="flex min-h-14 flex-col gap-0.5 px-4 py-3 transition-colors duration-150 hover:bg-surface-2"
            >
              <span className="flex items-baseline gap-3">
                <span className="min-w-0 flex-1 truncate text-[15px] leading-snug font-semibold text-fg">{s.title}</span>
                <span className="shrink-0 text-[13px] text-muted tabular-nums">{formatActivity(s.updated_at ?? s.created_at)}</span>
              </span>
              <span className="truncate text-[14px] leading-snug text-muted">
                {s.persona_name}
                {s.last_preview ? ` · ${s.last_preview}` : ""}
              </span>
            </a>
          </li>
        ))}
      </ul>
    </section>
  );
}

/**
 * "#/character/<id>" and "#/character/template/<slug>": the character's profile, read only. A large
 * picture, name, role, creator, tags, signature lines, then two tabs ("Giới thiệu", "Thiết lập") and
 * the user's stories with the character. "Bước vào câu chuyện" opens the persona sheet; only the
 * user's own cards get a small "Sửa nhân vật" link to the Studio.
 */
export function CharacterPage({ target, start }: Props) {
  const [state, setState] = useState<State>({ kind: "loading" });
  const [styles, setStyles] = useState<StyleProfileInfo[]>([]);
  const [sheetOpen, setSheetOpen] = useState(start);
  // Read by the template -> installed card redirect, so an open sheet stays open on the card's profile.
  const sheetOpenRef = useRef(start);
  sheetOpenRef.current = sheetOpen;
  const [tab, setTab] = useState<TabKey>("intro");
  // "Báo cáo nhân vật" (someone else's public character, or the original of a story's copy).
  const [reporting, setReporting] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const hideToast = useCallback(() => setToast(null), []);
  const idBase = useId();
  /** Card id once a template got installed from the sheet. */
  const installedId = useRef<number | null>(null);

  // Primitive keys: dropping "?start=1" gives a new route object for the same character (no reload).
  const cardKey = target.kind === "card" ? target.id : null;
  const slugKey = target.kind === "template" ? target.slug : null;

  const load = useCallback(async () => {
    setState({ kind: "loading" });
    try {
      if (cardKey !== null) {
        setState({ kind: "ready", profile: await loadCardProfile(cardKey) });
        return;
      }
      const templates = await api.listTemplates();
      const t = templates.find((x) => x.slug === slugKey);
      if (!t) {
        setState({ kind: "missing" });
        return;
      }
      if (t.installed_card_id !== null) {
        // Already one of the user's cards: show that one (its stories, its picture).
        replaceRoute(characterRoute(t.installed_card_id, sheetOpenRef.current));
        return;
      }
      setState({ kind: "ready", profile: templateProfile(t) });
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) setState({ kind: "missing" });
      else setState({ kind: "error", text: errorMessage(e), technical: errorTechnical(e) });
    }
  }, [cardKey, slugKey]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    let alive = true;
    api
      .listStyles()
      .then((s) => alive && setStyles(s))
      .catch(() => undefined);
    return () => {
      alive = false;
    };
  }, []);

  // "?start=1": open the sheet once, then drop the flag (a reload or Back does not reopen it).
  useEffect(() => {
    if (!start) return;
    setSheetOpen(true);
    replaceRoute(cardKey !== null ? characterRoute(cardKey) : templateRoute(slugKey ?? ""));
  }, [start, cardKey, slugKey]);

  const profile = state.kind === "ready" ? state.profile : null;
  const name = profile?.card.name.trim() ?? "";

  // Phase 4: names of the world's people and places, loaded beside the card. A failure or a 404
  // (template not installed) just hides the section.
  const [summary, setSummary] = useState<LoreSummary | null>(null);
  const summaryCardId = profile?.cardId ?? null;
  useEffect(() => {
    setSummary(null);
    if (summaryCardId === null) return;
    const ctrl = new AbortController();
    api
      .getLoreSummary(summaryCardId, ctrl.signal)
      .then((s) => setSummary(s))
      .catch(() => undefined);
    return () => ctrl.abort();
  }, [summaryCardId]);
  const world = useMemo(() => worldTeaser(summary, name), [summary, name]);

  useEffect(() => {
    if (name) document.title = `${name} · Lyris`;
  }, [name]);

  // Usage: which kind of character (own, Lyris template, someone's public one) and from which screen.
  const source: CardSource | null = profile ? (profile.shared ? "public" : profile.isTemplate ? "template" : "own") : null;
  const viewed = useRef(false);
  useEffect(() => {
    if (source === null || viewed.current) return;
    viewed.current = true;
    track("character_profile_viewed", { source, from: profileFrom(previousRouteName()) });
  }, [source]);
  const openStart = () => {
    if (source !== null) track("story_start_clicked", { source });
    setSheetOpen(true);
  };

  const ensureCardId = useCallback(async () => {
    if (!profile) throw new Error("Nhân vật chưa tải xong.");
    if (profile.cardId !== null) return profile.cardId;
    if (installedId.current !== null) return installedId.current;
    const id = await cardIdForTemplate(profile.slug ?? "", null);
    installedId.current = id;
    return id;
  }, [profile]);

  const signature = useMemo(() => (profile ? signatureLinesFor(profile.card) : { lines: [], own: false }), [profile]);
  const styleProfile = useMemo(
    () => (profile ? (styles.find((s) => s.name === profile.card.style_profile) ?? null) : null),
    [styles, profile],
  );

  const latest = profile?.stories[0] ?? null;
  const editable = profile !== null && profile.cardId !== null && !profile.isTemplate && profile.shared === null;
  // A story's copy (opened from the chat) cannot start another story; everything else can.
  const canStart = profile !== null && (profile.shared?.canStart ?? true);
  const lang = profile?.card.language === "en" ? "en" : "vi";
  // User-made content shown to others can be reported from its profile (not your own, not Lyris templates).
  const reportable = profile !== null && profile.cardId !== null && profile.shared !== null;

  const openStory = (story: StoryOut) => {
    setSheetOpen(false);
    if (story.id !== null) navigate({ name: "chat", storyId: story.id });
  };

  let content;
  if (state.kind === "loading") {
    content = <PageSkeleton />;
  } else if (state.kind === "missing") {
    content = (
      <EmptyState
        text="Không tìm thấy nhân vật này. Có thể nhân vật đã bị xoá."
        action={
          <Button size="sm" variant="primary" onClick={() => navigate({ name: "explore" })}>
            Về Khám phá
          </Button>
        }
      />
    );
  } else if (state.kind === "error") {
    content = <InlineAlert tone="error" text={state.text} technical={state.technical} onRetry={() => void load()} />;
  } else {
    const p = state.profile;
    const role = (p.card.role ?? "").trim();
    content = (
      <div className="md:grid md:grid-cols-[minmax(0,340px)_minmax(0,1fr)] md:items-start md:gap-10">
        <div className="md:sticky md:top-6">
          {/* No picture: on a phone a 448px block holding one letter pushed the name below the fold,
              so the letter fallback is a short band there and keeps the portrait frame from md up. */}
          <CharacterPicture
            url={p.pictureUrl}
            name={name}
            eager
            className={cx("w-full rounded-card", p.pictureUrl ? "aspect-[4/5]" : "aspect-[2/1] md:aspect-[4/5]")}
          />
        </div>

        <div className="mt-5 flex min-w-0 flex-col gap-8 md:mt-0">
          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-1">
              <h2 className="font-brand text-[36px] leading-[1.1] font-semibold text-fg italic sm:text-[40px]">{name}</h2>
              {role && <p className="text-[16px] leading-snug font-medium text-accent-2">{role}</p>}
              {p.creator &&
                (p.shared?.creatorHandle ? (
                  <p className="text-[13px] leading-snug text-muted">
                    <a
                      href={routeHref({ name: "profile", handle: p.shared.creatorHandle })}
                      className="inline-flex min-h-11 items-center underline decoration-line-strong underline-offset-2 transition-colors duration-150 hover:text-fg hover:decoration-accent md:min-h-0"
                    >
                      {p.creator}
                    </a>
                  </p>
                ) : (
                  <p className="text-[13px] leading-snug text-muted">{p.creator}</p>
                ))}
            </div>
            {p.tags.length > 0 && (
              <ul aria-label="Tag" className="flex flex-wrap gap-2">
                {p.tags.map((t) => (
                  <li key={t}>
                    <Chip size="sm">{t}</Chip>
                  </li>
                ))}
              </ul>
            )}
            <div className="flex flex-wrap items-center gap-3 pt-1">
              <div className="hidden flex-wrap items-center gap-3 md:flex">
                {canStart && (
                  <Button variant="primary" onClick={openStart}>
                    {ENTER_LABEL}
                  </Button>
                )}
                {latest && (
                  <Button variant={canStart ? "secondary" : "primary"} onClick={() => openStory(latest)}>
                    Tiếp tục story
                  </Button>
                )}
              </div>
              {editable && (
                <a
                  href={routeHref({ name: "card", cardId: p.cardId })}
                  className="inline-flex h-11 items-center gap-1.5 rounded-full px-3 text-[14px] font-medium text-muted transition-colors duration-150 hover:bg-surface-2 hover:text-fg max-md:-ml-3 md:h-11"
                >
                  <IconEdit aria-hidden="true" className="text-[16px]" />
                  Sửa nhân vật
                </a>
              )}
              {reportable && (
                <button
                  type="button"
                  onClick={() => setReporting(true)}
                  aria-haspopup="dialog"
                  className="inline-flex h-11 items-center gap-1.5 rounded-full px-3 text-[14px] font-medium text-muted transition-colors duration-150 hover:bg-surface-2 hover:text-fg max-md:-ml-3 md:h-11"
                >
                  <IconFlag aria-hidden="true" className="text-[16px]" />
                  {REPORT_CARD_LABEL}
                </button>
              )}
            </div>
          </div>

          {signature.lines.length > 0 && (
            <section aria-labelledby="character-lines" className="flex flex-col gap-3">
              <h3 id="character-lines" className="text-[18px] leading-tight font-semibold text-fg">
                Lời nói đặc trưng
              </h3>
              {/* Full-width quote cards: sized to the text, a short line in a white hairline box read
                  as a button or a field in the light theme. */}
              <ul className="flex flex-col gap-2.5">
                {signature.lines.map((line) => (
                  <li key={line}>
                    <blockquote
                      lang={lang}
                      className="w-full rounded-card border border-edge bg-surface px-4 py-3 font-story text-[16px] font-medium text-dialogue [overflow-wrap:anywhere]"
                    >
                      “{line}”
                    </blockquote>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section aria-label="Thông tin nhân vật" className="flex flex-col gap-5">
            <Tabs value={tab} onChange={setTab} idBase={idBase} />
            <div role="tabpanel" id={`${idBase}-panel-${tab}`} aria-labelledby={`${idBase}-tab-${tab}`} tabIndex={0} className="rounded-card focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent">
              {tab === "intro" ? <IntroPanel card={p.card} world={world} /> : <SetupPanel card={p.card} profile={styleProfile} />}
            </div>
          </section>

          {p.stories.length > 0 && <StoryList name={name} stories={p.stories} />}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-dvh bg-bg">
      <SubpageHeader backHref={BACK.href} backLabel={BACK.label} title="Nhân vật" width="medium" />
      <main
        className={cx(
          "mx-auto w-full max-w-[960px] px-4 pt-4 sm:px-6 sm:pt-6",
          profile ? "pb-[calc(96px+env(safe-area-inset-bottom))] md:pb-16" : "pb-16",
        )}
      >
        {content}
      </main>

      {profile && (canStart || latest) && (
        <div className="fixed inset-x-0 bottom-0 z-20 border-t border-line bg-bg md:hidden">
          <div className="mx-auto flex w-full max-w-[720px] gap-2 px-4 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
            {latest && (
              <Button
                variant={canStart ? "secondary" : "primary"}
                block={!canStart}
                onClick={() => openStory(latest)}
                className={canStart ? "shrink-0" : "min-w-0 flex-1"}
              >
                Tiếp tục story
              </Button>
            )}
            {canStart && (
              <Button variant="primary" block onClick={openStart} className="min-w-0 flex-1">
                {ENTER_LABEL}
              </Button>
            )}
          </div>
        </div>
      )}

      {reportable && (
        <ReportSheet
          cardId={reporting ? (profile?.cardId ?? null) : null}
          characterName={name}
          onClose={() => setReporting(false)}
          onDone={() => {
            setReporting(false);
            setToast(REPORT_DONE);
          }}
        />
      )}
      <Toast text={toast} onDone={hideToast} />

      {profile && canStart && (
        <StartStorySheet
          note={profile.shared ? sharedStartNote(name, profile.shared.creatorHandle) : null}
          open={sheetOpen}
          onClose={() => setSheetOpen(false)}
          card={profile.card}
          cardId={profile.cardId}
          ensureCardId={ensureCardId}
          styles={styles}
          onCreated={openStory}
        />
      )}
    </div>
  );
}
