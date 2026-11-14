import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { api, errorMessage, errorTechnical } from "../../api/client";
import { Banner } from "../../components/Banner";
import { CharacterAvatarContext } from "../../components/characterAvatar";
import { ShowThoughtsContext } from "../../components/showThoughts";
import { Composer } from "../../components/Composer";
import { IconChevronLeft } from "../../components/icons";
import { MessageList } from "../../components/MessageList";
import { StorySettingsPanel } from "../../components/StorySettingsPanel";
import { Button, EmptyState } from "../../components/ui";
import { useChat } from "../../hooks/useChat";
import { useHealth } from "../../hooks/useHealth";
import { initialOverlayOpen } from "../../lib/overlayParam";
import { navigate } from "../../lib/router";
import { showThoughtsOf } from "../../lib/storyOptions";
import type { Mode, StoryOut, StoryPatch } from "../../types";
import { ChatHeader } from "./ChatHeader";
import { EMPTY_EXTRAS, lastReplyMode, mergeStory, rollbackPatch } from "./chatLogic";
import { EventsSheet } from "./EventsSheet";
import { jumpPlan } from "./eventsLogic";
import { loreSignature } from "./loreLogic";
import { useStoryLore } from "./useStoryLore";
import { HeartDrawer } from "./HeartDrawer";
import { PlayerAvatarContext, usePersonaFace } from "./playerAvatar";
import { composerActions, replyAnchor, suggestAvailability, suggestView, suggestionsKey } from "./suggestLogic";
import type { ComposerActionId } from "./suggestLogic";
import { useStoryExtras } from "./useStoryExtras";
import { useSuggestions } from "./useSuggestions";

const LAST_STORY_KEY = "lyris.lastStoryId";
const HUB_HASH = "#/";

function rememberStory(id: number) {
  try {
    localStorage.setItem(LAST_STORY_KEY, String(id));
  } catch {
    // convenience only
  }
}

type LoadState = { state: "loading" } | { state: "ready" } | { state: "missing" } | { state: "error"; detail: string };

/** Full-screen page for a story that cannot be opened (deleted, or the server is down). */
function Unavailable({ title, text, action }: { title: string; text: string; action?: ReactNode }) {
  return (
    <div className="flex h-dvh flex-col bg-bg">
      <div className="pt-safe">
        <div className="mx-auto flex h-14 max-w-[720px] items-center px-2 sm:px-4">
          <Button variant="ghost" icon={<IconChevronLeft />} onClick={() => navigate(HUB_HASH)} className="px-3">
            Story
          </Button>
        </div>
      </div>
      <main className="mx-auto flex w-full max-w-[720px] flex-col gap-4 px-4 pt-10">
        <h1 className="text-[24px] leading-tight font-semibold text-fg">{title}</h1>
        <EmptyState text={text} action={action} />
      </main>
    </div>
  );
}

/**
 * The roleplay workspace (DESIGN.md §6, layer 2): glass header with the Story/DM switch, the
 * thought menu, the heart drawer and the story settings; the story or DM thread; quick replies
 * and the composer. Owns all chat state through useChat.
 */
export function ChatPage({ storyId }: { storyId: number }): JSX.Element {
  const [story, setStory] = useState<StoryOut | null>(null);
  const [load, setLoad] = useState<LoadState>({ state: "loading" });
  const [storyError, setStoryError] = useState<{ text: string; technical: string | null } | null>(null);
  const [modeSaving, setModeSaving] = useState(false);
  const [showThoughtsSaving, setShowThoughtsSaving] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [heartOpen, setHeartOpen] = useState(false);
  const [eventsOpen, setEventsOpen] = useState(false);
  /** A turn picked in the timeline: the list scrolls to it once it is rendered. */
  const [jumpTo, setJumpTo] = useState<{ turn: number; nonce: number } | null>(null);
  /** A short plain notice (e.g. a timeline jump that cannot happen right now). */
  const [notice, setNotice] = useState<string | null>(null);
  const [headerHeight, setHeaderHeight] = useState(0);
  const headerRef = useRef<HTMLElement>(null);

  const health = useHealth();
  const chat = useChat(storyId, story?.mode ?? "story");
  const busyNow = chat.streaming !== null || chat.mutating;
  // Polling pauses while a reply streams: the job worker waits for the stream anyway.
  const {
    extras,
    error: extrasError,
    errorTechnical: extrasErrorTechnical,
    refresh: refreshExtras,
    dropSuggestions,
    forget: forgetMemory,
    rebuild: rebuildState,
  } = useStoryExtras(storyId, { paused: chat.streaming !== null });
  // Phase 4: unlocked world entries for the heart drawer; asked again when a turn unlocks something.
  const storyLore = useStoryLore(storyId, heartOpen, loreSignature(extras));
  // Quick replies only when the player asks ("Nhận gợi ý", Phase 3b).
  const suggest = useSuggestions(storyId);
  // The persona beside the player's own turns (docs/accounts.md §5).
  const playerFace = usePersonaFace(story?.persona_id ?? null, story?.persona_name ?? "");

  const loadStory = useCallback(async () => {
    setLoad({ state: "loading" });
    try {
      const list = await api.listStories();
      const found = list.find((s) => s.id === storyId) ?? null;
      setStory(found);
      setLoad(found ? { state: "ready" } : { state: "missing" });
      if (found) rememberStory(storyId);
    } catch (e) {
      setLoad({ state: "error", detail: errorMessage(e) });
    }
  }, [storyId]);

  useEffect(() => {
    setStory(null);
    setStoryError(null);
    // "?open=heart" / "?open=settings" mở sẵn lớp phủ (chỉ để chụp ảnh kiểm tra).
    setSettingsOpen(initialOverlayOpen("settings"));
    setHeartOpen(initialOverlayOpen("heart"));
    setEventsOpen(initialOverlayOpen("events"));
    setJumpTo(null);
    setNotice(null);
    void loadStory();
  }, [loadStory]);

  // Tab title: the character's name while the story is open.
  useEffect(() => {
    if (!story) return;
    const before = document.title;
    document.title = `${story.card_name} · Lyris`;
    return () => {
      document.title = before;
    };
  }, [story]);

  // The header floats over the list (glass): the list starts below its real height.
  useLayoutEffect(() => {
    const el = headerRef.current;
    if (!el) return;
    const measure = () => setHeaderHeight(el.offsetHeight);
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, [load.state]);

  // Extras change with every reply (scores, quick replies, scene, memories): fetch again when a
  // stream (done or stopped) or a message action (regenerate, variant, edit, delete) ends. The
  // quick replies belong to the previous reply: drop them as soon as a new turn starts.
  const wasBusy = useRef(false);
  useEffect(() => {
    if (wasBusy.current && !busyNow) void refreshExtras();
    wasBusy.current = busyNow;
  }, [busyNow, refreshExtras]);
  const streamingNow = chat.streaming !== null;
  const resetSuggestions = suggest.reset;
  useEffect(() => {
    if (!streamingNow) return;
    dropSuggestions();
    resetSuggestions();
  }, [streamingNow, dropSuggestions, resetSuggestions]);

  // Suggestions answer one reply: once the newest reply changes (deleted with "Xoá từ đây", edited,
  // another variant picked) the ones asked for it, and the server's copy, are dropped. suggestView
  // also hides them right away (same anchor check), before this effect runs.
  const anchor = replyAnchor(chat.messages);
  const anchorKey = anchor?.key ?? null;
  const prevAnchor = useRef<{ story: number; key: string | null } | null>(null);
  const noMessages = chat.messages.length === 0;
  useEffect(() => {
    const prev = prevAnchor.current;
    prevAnchor.current = { story: storyId, key: anchorKey };
    // Another story opened, the list (re)loading, or the first load: nothing of this story to drop.
    if (prev === null || prev.story !== storyId || noMessages) return;
    if (prev.key === null || prev.key === anchorKey) return;
    resetSuggestions();
    dropSuggestions();
  }, [storyId, anchorKey, noMessages, resetSuggestions, dropSuggestions]);

  /** Story keys a header PATCH is still saving (count per key): an earlier response must not undo them. */
  const savingKeys = useRef(new Map<string, number>());
  const holdKeys = useCallback((keys: readonly string[]) => {
    for (const k of keys) savingKeys.current.set(k, (savingKeys.current.get(k) ?? 0) + 1);
  }, []);
  const releaseKeys = useCallback((keys: readonly string[]) => {
    for (const k of keys) {
      const n = (savingKeys.current.get(k) ?? 1) - 1;
      if (n > 0) savingKeys.current.set(k, n);
      else savingKeys.current.delete(k);
    }
  }, []);

  /** Optimistic story setting change (mode, thought style); rolled back if the server refuses.
   *  Only the patched keys roll back: "Đọc suy nghĩ" saved meanwhile stays as the player set it.
   *  Resolves to whether the server took it. */
  const patchStory = useCallback(
    async (patch: StoryPatch): Promise<boolean> => {
      if (!story) return false;
      const before = story;
      const keys = Object.keys(patch);
      holdKeys(keys);
      setModeSaving(true);
      setStoryError(null);
      setStory((cur) => (cur ? { ...cur, ...patch } : cur));
      try {
        const updated = await api.patchStory(storyId, patch);
        releaseKeys(keys);
        setStory((cur) => (cur ? mergeStory(cur, updated, savingKeys.current.keys()) : cur));
        return true;
      } catch (e) {
        releaseKeys(keys);
        setStory((cur) => (cur ? rollbackPatch(cur, before, patch) : cur));
        setStoryError({ text: errorMessage(e), technical: errorTechnical(e) });
        return false;
      } finally {
        setModeSaving(false);
      }
    },
    [story, storyId, holdKeys, releaseKeys],
  );

  /**
   * Phase 4 (B): "Đọc suy nghĩ của nhân vật" from the header menu. Optimistic like the thought style,
   * but display only: it does not lock the mode switch and works while a reply streams.
   */
  const setShowThoughts = useCallback(
    async (show: boolean) => {
      const patch = { show_thoughts: show };
      const keys = Object.keys(patch);
      holdKeys(keys);
      setShowThoughtsSaving(true);
      setStoryError(null);
      setStory((cur) => (cur ? { ...cur, ...patch } : cur));
      try {
        const updated = await api.patchStory(storyId, patch);
        releaseKeys(keys);
        setStory((cur) => (cur ? mergeStory(cur, updated, savingKeys.current.keys()) : cur));
      } catch (e) {
        releaseKeys(keys);
        setStory((cur) => (cur ? rollbackPatch(cur, { ...cur, show_thoughts: !show }, patch) : cur));
        setStoryError({ text: errorMessage(e), technical: errorTechnical(e) });
      } finally {
        setShowThoughtsSaving(false);
      }
    },
    [storyId, holdKeys, releaseKeys],
  );

  /** Settings panel save: not optimistic; errors go back to the panel. */
  const saveSettings = useCallback(
    async (patch: StoryPatch) => {
      const updated = await api.patchStory(storyId, patch);
      setStory((cur) => (cur ? { ...cur, ...updated } : cur));
    },
    [storyId],
  );

  const deleteStory = useCallback(async () => {
    await api.deleteStory(storyId);
    setSettingsOpen(false);
    try {
      localStorage.removeItem(LAST_STORY_KEY);
    } catch {
      // ignore
    }
    navigate(HUB_HASH);
  }, [storyId]);

  if (load.state === "missing") {
    return (
      <Unavailable
        title="Không tìm thấy story"
        text={`Story #${storyId} không còn (có thể đã bị xoá). Hãy chọn một story khác.`}
        action={
          <Button size="sm" variant="primary" onClick={() => navigate(HUB_HASH)}>
            Về danh sách
          </Button>
        }
      />
    );
  }
  if (load.state === "error" && !story) {
    return (
      <Unavailable
        title="Chưa mở được story"
        text={load.detail}
        action={
          <Button size="sm" variant="secondary" onClick={() => void loadStory()}>
            Thử lại
          </Button>
        }
      />
    );
  }

  const streaming = chat.streaming !== null;
  const busy = streaming || chat.mutating;
  // While suggestions are being written the server holds the story (it would answer 409): sending,
  // switching mode and message actions wait, or the player closes the suggestion area ("Huỷ gợi ý").
  // A cancelled request still holds the story on the server for a moment (`releasing`).
  const suggesting = suggest.state.status === "loading" || suggest.releasing;
  const name = story?.card_name ?? "Nhân vật";
  const view = story?.mode ?? "story";

  const last = chat.messages[chat.messages.length - 1];
  const awaitingReply = !busy && !chat.loading && last !== undefined && last.role === "user" && last.id !== null;

  let banner: ReactNode = null;
  if (chat.error) {
    banner = (
      <Banner
        tone="error"
        text={chat.error.detail}
        technical={chat.error.technical}
        onRetry={chat.error.retry}
        retryDisabled={busy}
        onDismiss={chat.dismissError}
      />
    );
  } else if (storyError) {
    banner = (
      <Banner tone="error" text={storyError.text} technical={storyError.technical} onDismiss={() => setStoryError(null)} />
    );
  } else if (notice) {
    banner = <Banner tone="info" text={notice} onDismiss={() => setNotice(null)} />;
  } else if (awaitingReply && last && story && last.mode !== story.mode) {
    // The unanswered turn is hidden in this view; answering it here would use the wrong mode.
    const other = last.mode === "dm" ? "DM" : "Story";
    banner = (
      <Banner
        tone="info"
        text={`Lượt của bạn bên ${other} chưa có câu trả lời.`}
        actionLabel={`Mở ${other}`}
        onRetry={() => changeMode(last.mode)}
        retryDisabled={busy || modeSaving}
      />
    );
  } else if (awaitingReply) {
    banner = (
      <Banner
        tone="info"
        text="Lượt của bạn chưa có câu trả lời."
        actionLabel="Trả lời"
        onRetry={chat.reply}
        retryDisabled={busy}
      />
    );
  } else if (health.level === "down" || health.level === "warn") {
    banner = <Banner tone="info" text={health.label} technical={health.technical} onRetry={health.refresh} />;
  }

  // ---- the composer's "+" (Phase 3b) ----
  const suggestNow = suggestAvailability({
    messages: chat.messages,
    busy,
    loading: chat.loading || !story,
    generating: suggesting,
    offline: health.level === "down",
    view,
  });
  const actions = composerActions({ suggest: suggestNow });
  const suggestion = suggestView(suggest.state, {
    stored: extras?.suggestions ?? [],
    storedMode: lastReplyMode(chat.messages),
    view,
    generating: streaming,
    anchor: anchorKey,
  });
  // "Gợi ý khác" / "Thử lại" follow the menu item's rule (a failed request is no longer running).
  const moreBlocked = suggestAvailability({
    messages: chat.messages,
    busy,
    loading: chat.loading || !story,
    generating: false,
    offline: health.level === "down",
    view,
  }).reason;
  // The server writes suggestions in the mode of the reply they answer (availability makes sure that
  // is the view on screen); they are tied to that reply (anchor).
  const askSuggestions = () => void suggest.request(anchor?.mode ?? view, anchorKey);
  const onAction = (id: ComposerActionId) => {
    if (id === "suggest") {
      if (suggestNow.enabled) askSuggestions();
    } else if (id === "events") {
      setEventsOpen(true);
    }
    // "image": not built yet; the menu item is disabled and says so.
  };
  const jumpToTurn = (turn: number, mode: Mode) => {
    setNotice(null);
    // A turn of the other mode only shows in that view: switch first. Not while something runs (the
    // switch is locked then): say so instead of leaving a jump pending that would fire later.
    const plan = jumpPlan(mode, view, busy || suggesting || modeSaving);
    if (plan.kind === "blocked") {
      setNotice(plan.notice);
      return;
    }
    const nonce = Date.now();
    setJumpTo({ turn, nonce });
    if (plan.kind === "scroll") return;
    void patchStory({ mode: plan.mode }).then((ok) => {
      // The switch was refused (rolled back): drop the jump, it must not fire on a later manual switch.
      if (!ok) setJumpTo((cur) => (cur?.nonce === nonce ? null : cur));
    });
  };
  // A world entry's first mention (heart drawer): the turn's mode comes from the loaded messages.
  const jumpToLore = (turn: number) => {
    setHeartOpen(false);
    const m = chat.messages.find((x) => x.turn_index === turn && x.is_active) ?? chat.messages.find((x) => x.turn_index === turn);
    if (!m) {
      setNotice("Lượt này không còn trong story.");
      return;
    }
    jumpToTurn(turn, m.mode);
  };
  const changeMode = (mode: typeof view) => {
    // A manual switch cancels a jump still waiting for its turn to render.
    setJumpTo(null);
    setNotice(null);
    void patchStory({ mode });
  };

  return (
    <div className="relative flex h-dvh flex-col overflow-hidden bg-bg">
      <ChatHeader
        ref={headerRef}
        story={story}
        extras={extras ?? EMPTY_EXTRAS}
        modeDisabled={busy || suggesting || modeSaving || !story}
        onBack={() => navigate(HUB_HASH)}
        onChangeMode={changeMode}
        onChangeThoughtStyle={(thought_style) => void patchStory({ thought_style })}
        onChangeShowThoughts={(show) => void setShowThoughts(show)}
        showThoughtsSaving={showThoughtsSaving}
        onOpenHeart={() => setHeartOpen(true)}
        onOpenSettings={() => setSettingsOpen(true)}
      />

      <CharacterAvatarContext.Provider value={story?.card_avatar_url ?? null}>
        <PlayerAvatarContext.Provider value={playerFace}>
          <ShowThoughtsContext.Provider value={showThoughtsOf(story)}>
          <MessageList
            storyId={story ? storyId : null}
            view={view}
            messages={chat.messages}
            streaming={chat.streaming}
            loading={chat.loading || !story}
            disabled={busy || suggesting}
            characterName={name}
            topInset={headerHeight}
            jumpTo={jumpTo}
            onRegenerate={chat.regenerate}
            onSelectVariant={(m, i) => void chat.selectVariant(m, i)}
            onEdit={chat.edit}
            onDelete={(m) => void chat.deleteFrom(m)}
            onFeedback={(m, r) => void chat.feedback(m, r)}
          />
          </ShowThoughtsContext.Provider>
        </PlayerAvatarContext.Provider>
      </CharacterAvatarContext.Provider>

      <div className="shrink-0">
        {banner && <div className="pt-2">{banner}</div>}
        <Composer
          key={storyId}
          storyId={storyId}
          streaming={streaming}
          mode={view}
          characterName={name}
          disabled={chat.mutating || chat.loading || suggesting || !story}
          onSend={chat.send}
          onStop={chat.stop}
          actions={story ? actions : undefined}
          onAction={onAction}
          suggestion={suggestion}
          onMoreSuggestions={askSuggestions}
          onDismissSuggestions={() => suggest.dismiss(suggestion.kind === "items" ? suggestionsKey(suggestion.items) : "")}
          moreSuggestionsBlocked={moreBlocked}
        />
      </div>

      {story && (
        <HeartDrawer
          open={heartOpen}
          onClose={() => setHeartOpen(false)}
          characterName={story.card_name}
          extras={extras}
          error={extrasError}
          errorTechnical={extrasErrorTechnical}
          onRetry={() => void refreshExtras()}
          onForget={forgetMemory}
          onRebuild={rebuildState}
          lore={storyLore.state}
          onRetryLore={() => void storyLore.reload()}
          showThoughts={showThoughtsOf(story)}
          onJumpToTurn={jumpToLore}
        />
      )}

      {story && (
        <EventsSheet
          open={eventsOpen}
          onClose={() => setEventsOpen(false)}
          storyId={storyId}
          characterName={story.card_name}
          moment={extras?.moment ?? null}
          onJump={(entry) => {
            setEventsOpen(false);
            jumpToTurn(entry.turn_index, entry.mode);
          }}
        />
      )}

      {settingsOpen && story && (
        <StorySettingsPanel
          key={storyId}
          story={story}
          busy={busy}
          onClose={() => setSettingsOpen(false)}
          onSave={saveSettings}
          onDelete={deleteStory}
        />
      )}
    </div>
  );
}
