import { useEffect, useId, useRef, useState } from "react";
import type { ReactNode } from "react";
import { errorMessage, errorTechnical } from "../../api/client";
import { TypingDots } from "../../components/TypingDots";
import { IconChevronDown, IconClock, IconEye, IconMapPin, IconSparkles } from "../../components/icons";
import { Badge, Button, Drawer, ErrorDetails, Meter, Skeleton, cx } from "../../components/ui";
import type { MemoryItem, StoryExtras, UnlockedLore } from "../../types";
import { EMOTIONS } from "./chatLogic";
import {
  drawerLoadState,
  focusIndexAfterForget,
  forgetPrompt,
  memoryKindLabel,
  memoryStatus,
  sceneRows,
} from "./memoryLogic";
import { secretGroupTitle, secretLabel, splitUnlocked, studioWorldHref, unlockedEmptyLine } from "./loreLogic";
import { useRevealThoughts } from "./revealThoughts";
import type { StoryLoreState } from "./useStoryLore";

interface Props {
  open: boolean;
  onClose: () => void;
  characterName: string;
  /** null until the first fetch returns. */
  extras: StoryExtras | null;
  /** The last fetch failed (the drawer keeps showing the last good data, if any). */
  error: string | null;
  /** Technical text of that failure, for "Chi tiết". */
  errorTechnical?: string | null;
  onRetry: () => void;
  /** Deletes one memory or fact; rejects with the server's message. */
  onForget: (memoryId: number) => Promise<void>;
  /** Queues extraction of the turns never read. */
  onRebuild: () => Promise<unknown>;
  /** Phase 4: unlocked world entries (useStoryLore). */
  lore: StoryLoreState;
  onRetryLore: () => void;
  /** The story reads the character's thoughts; off hides the character's secrets entirely. */
  showThoughts: boolean;
  /** "Xem lúc được nhắc tới lần đầu": jump to that turn (the page closes the drawer). */
  onJumpToTurn: (turnIndex: number) => void;
}

const NO_RELATIONSHIP = "Story này chưa có dữ liệu cảm xúc.";

function Section({ title, children }: { title: string; children: ReactNode }) {
  const id = useId();
  return (
    <section aria-labelledby={id} className="flex flex-col gap-3">
      <h3 id={id} className="text-[16px] leading-tight font-semibold text-fg">
        {title}
      </h3>
      {children}
    </section>
  );
}

function SceneSection({ extras }: { extras: StoryExtras }) {
  const rows = sceneRows(extras);
  if (rows.length === 0) {
    return <p className="text-[14px] leading-snug text-muted">Chưa rõ nơi chốn và thời gian trong story.</p>;
  }
  return (
    <dl className="flex flex-col gap-2">
      {rows.map((r) => (
        <div key={r.label} className="flex items-baseline gap-2.5 text-[14px] leading-snug">
          {/* Inline icon so the label's baseline is its text, level with the value beside it. */}
          <dt className="shrink-0 text-muted [&_svg]:mr-1.5 [&_svg]:inline [&_svg]:align-[-0.15em] [&_svg]:text-[15px]">
            {r.label === "Nơi chốn" ? <IconMapPin /> : <IconClock />}
            {r.label}
          </dt>
          <dd className="min-w-0 text-fg [overflow-wrap:anywhere]">{r.value}</dd>
        </div>
      ))}
    </dl>
  );
}

function MemoryRow({
  item,
  characterName,
  onForget,
}: {
  item: MemoryItem;
  characterName: string;
  /** Resolves once forgotten (the row is then removed); rejects with the server's message. */
  onForget: (id: number) => Promise<void>;
}) {
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<{ text: string; technical: string | null } | null>(null);
  const promptId = useId();
  const keepRef = useRef<HTMLButtonElement>(null);
  const askRef = useRef<HTMLButtonElement>(null);
  // Focus follows the swap inside the drawer's focus trap: "Giữ lại" when the question opens,
  // back to "Quên" when it closes (not on first render).
  const opened = useRef(false);
  useEffect(() => {
    if (confirming) {
      opened.current = true;
      keepRef.current?.focus();
    } else if (opened.current) {
      askRef.current?.focus();
    }
  }, [confirming]);
  const id = item.id;

  const forget = async () => {
    if (id === null || busy) return;
    setBusy(true);
    setError(null);
    try {
      await onForget(id);
    } catch (e) {
      setError({ text: errorMessage(e), technical: errorTechnical(e) });
      setBusy(false);
      setConfirming(false);
    }
  };

  return (
    <li className="flex flex-col gap-2 py-3 first:pt-0 last:pb-0">
      <p className="text-[14px] leading-relaxed text-prose [overflow-wrap:anywhere]">{item.text}</p>
      {confirming ? (
        <div
          role="group"
          aria-labelledby={promptId}
          className="flex flex-col gap-2 rounded-control bg-surface-2 px-3.5 py-3"
        >
          <p id={promptId} className="text-[13px] leading-snug text-fg">
            {forgetPrompt(item.kind, characterName)}
          </p>
          <div className="flex justify-end gap-2">
            <Button
              ref={keepRef}
              size="sm"
              variant="ghost"
              onClick={() => setConfirming(false)}
              disabled={busy}
              className="max-sm:h-11"
            >
              Giữ lại
            </Button>
            <Button size="sm" variant="danger" onClick={() => void forget()} loading={busy} className="max-sm:h-11">
              Quên
            </Button>
          </div>
        </div>
      ) : (
        <div className="flex items-center gap-2">
          <Badge tone={item.kind === "fact" ? "gold" : "neutral"}>{memoryKindLabel(item.kind)}</Badge>
          {item.kind === "fact" && item.subject && (
            <span className="min-w-0 truncate text-[13px] text-muted">về {item.subject}</span>
          )}
          <Button
            ref={askRef}
            data-forget=""
            size="sm"
            variant="ghost"
            onClick={() => setConfirming(true)}
            disabled={id === null}
            aria-label={`Quên: ${item.text}`}
            // 44px touch target on phones; the negative margin keeps the row as tall as the badge, so
            // the tag line sits close to the memory it belongs to.
            className="-mr-3 ml-auto max-sm:-my-2 max-sm:h-11"
          >
            Quên
          </Button>
        </div>
      )}
      {error && (
        <div role="alert" className="flex flex-col gap-0.5">
          <p className="text-[13px] leading-snug text-danger">Chưa quên được. {error.text}</p>
          <ErrorDetails technical={error.technical} />
        </div>
      )}
    </li>
  );
}

function MemorySection({
  extras,
  characterName,
  onForget,
  onRebuild,
}: {
  extras: StoryExtras;
  characterName: string;
  onForget: (id: number) => Promise<void>;
  onRebuild: () => Promise<unknown>;
}) {
  const [rebuilding, setRebuilding] = useState(false);
  const [rebuildError, setRebuildError] = useState<{ text: string; technical: string | null } | null>(null);
  /** The player asked to read the story again; typing dots until the jobs are done. */
  const [readingAgain, setReadingAgain] = useState(false);
  const [announce, setAnnounce] = useState("");
  // Where focus goes once the control that had it is gone: a forgotten row's "Quên" or the
  // "Đọc lại story" button replaced by the typing dots. Without this it drops to <body>.
  const [refocus, setRefocus] = useState<{ kind: "forget"; index: number } | { kind: "rebuild" } | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const statusRef = useRef<HTMLDivElement>(null);
  const status = memoryStatus(extras, { rebuilding: readingAgain });
  const statusKind = status?.kind ?? null;
  const memoryCount = extras.memories.length;

  // Reading again ends when no job is left.
  useEffect(() => {
    if (readingAgain && !extras.pending) setReadingAgain(false);
  }, [readingAgain, extras.pending]);

  useEffect(() => {
    if (refocus === null) return;
    if (refocus.kind === "forget") {
      const buttons = listRef.current?.querySelectorAll<HTMLButtonElement>("button[data-forget]:not(:disabled)") ?? [];
      const index = focusIndexAfterForget(refocus.index, buttons.length);
      const target = index === null ? null : buttons[index];
      (target ?? rootRef.current)?.focus();
    } else if (statusKind === "reading") {
      statusRef.current?.focus();
    } else if (statusKind !== "invite") {
      rootRef.current?.focus();
    } // still an invite: the button stays and keeps focus
    setRefocus(null);
  }, [refocus, statusKind, memoryCount]);

  const forget = async (id: number) => {
    const index = extras.memories.findIndex((m) => m.id === id);
    await onForget(id);
    setAnnounce("Đã quên.");
    setRefocus({ kind: "forget", index: Math.max(0, index) });
  };

  const rebuild = async () => {
    setRebuilding(true);
    setRebuildError(null);
    try {
      await onRebuild();
      setReadingAgain(true);
      setRefocus({ kind: "rebuild" });
    } catch (e) {
      setRebuildError({ text: errorMessage(e), technical: errorTechnical(e) });
    } finally {
      setRebuilding(false);
    }
  };

  return (
    <div ref={rootRef} tabIndex={-1} className="flex flex-col gap-3 outline-none">
      <p className="sr-only" aria-live="polite">
        {status?.kind === "reading" ? "Lyris đang đọc lại story" : announce}
      </p>
      {status?.kind === "reading" && (
        <div ref={statusRef} tabIndex={-1} className="flex outline-none">
          <span className="inline-flex h-10 items-center rounded-full bg-surface-2 px-4 text-[13px] text-muted">
            <TypingDots />
          </span>
        </div>
      )}
      {status?.kind === "invite" && (
        <div className="flex flex-col items-start gap-3 rounded-card bg-surface-2 px-4 py-3.5">
          <p className="text-[14px] leading-snug text-fg">
            {status.text}
          </p>
          <Button size="sm" variant="secondary" onClick={() => void rebuild()} loading={rebuilding} className="max-sm:h-11">
            Đọc lại story
          </Button>
          {rebuildError && (
            <div role="alert" className="flex flex-col gap-0.5">
              <p className="text-[13px] leading-snug text-danger">{rebuildError.text}</p>
              <ErrorDetails technical={rebuildError.technical} />
            </div>
          )}
        </div>
      )}

      {extras.memories.length > 0 ? (
        <ul ref={listRef} className="flex flex-col divide-y divide-line">
          {extras.memories.map((m) => (
            <MemoryRow key={m.id ?? m.text} item={m} characterName={characterName} onForget={forget} />
          ))}
        </ul>
      ) : (
        status?.kind !== "reading" && (
          <p className="text-[14px] leading-snug text-muted">
            Chưa có ký ức nào. Nhân vật ghi nhớ sau mỗi lượt trả lời.
          </p>
        )
      )}

      {extras.summary && (
        <details className="group rounded-control bg-surface-2 px-4 py-3">
          {/* The set's chevron instead of the browser's black disclosure triangle. */}
          <summary className="flex cursor-pointer list-none items-center justify-between gap-2 text-[14px] font-medium text-fg [&::-webkit-details-marker]:hidden">
            Tóm tắt những lượt cũ
            <IconChevronDown className="shrink-0 text-[16px] text-muted transition-transform duration-150 group-open:rotate-180 motion-reduce:transition-none" />
          </summary>
          <p className="pt-2 font-story text-[14px] text-prose">{extras.summary}</p>
        </details>
      )}
    </div>
  );
}

/** One unlocked entry the player may read: a folded row (sparkle, name, "Chỉ bạn biết"), the note inside. */
function OpenEntry({ entry, onJump }: { entry: UnlockedLore; onJump: () => void }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <li className="flex flex-col">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((o) => !o)}
        className="-mx-2 flex min-h-11 items-center gap-2.5 rounded-control px-2 py-1.5 text-left transition-colors duration-150 hover:bg-surface-2"
      >
        <IconSparkles aria-hidden="true" className="shrink-0 text-[15px] text-accent-2" />
        <span className="min-w-0 flex-1 text-[15px] leading-snug font-medium text-fg [overflow-wrap:anywhere]">{entry.title}</span>
        {entry.audience === "player" && <Badge tone="gold">Chỉ bạn biết</Badge>}
        <IconChevronDown
          aria-hidden="true"
          className={cx("shrink-0 text-[16px] text-muted transition-transform duration-150 motion-reduce:transition-none", open && "rotate-180")}
        />
      </button>
      <div id={id} hidden={!open} className="pb-2 pl-[26px]">
        {open && (
          <>
            {entry.content && <p className="font-story text-[14px] text-prose [overflow-wrap:anywhere] whitespace-pre-line">{entry.content}</p>}
            <Button size="sm" variant="ghost" onClick={onJump} className="mt-1 -ml-3 max-sm:h-11">
              Xem lúc được nhắc tới lần đầu
            </Button>
          </>
        )}
      </div>
    </li>
  );
}

/** Stand-in words behind the blur: the real note is in the DOM only once opened. */
const VEILED = "Một điều được giữ kín trong lòng, chưa từng nói ra với ai, kể cả với bạn.";

/**
 * Something only the character knows: a thought-like card (3px accent edge), name and note blurred
 * until tapped. "Luôn hiện suy nghĩ" shows it plainly. Never rendered when the story does not read
 * thoughts (the caller leaves the whole group out).
 */
function SecretEntry({ entry, characterName }: { entry: UnlockedLore; characterName: string }) {
  const [always] = useRevealThoughts();
  const [open, setOpen] = useState(false);
  const revealed = always || open;
  const shell = cx(
    "relative block w-full rounded-r-control border-l-[3px] border-accent px-4 py-3 text-left",
    "bg-[color-mix(in_oklab,var(--color-accent)_8%,var(--color-surface))]",
  );
  const body = revealed ? (
    <span className="block transition-[filter,opacity] duration-300 ease-out motion-reduce:transition-none">
      <span className="block text-[14px] font-semibold text-fg [overflow-wrap:anywhere]">{entry.title}</span>
      {entry.content && (
        <span className="mt-1 block font-story text-[14px] text-thought italic [overflow-wrap:anywhere] whitespace-pre-line">{entry.content}</span>
      )}
    </span>
  ) : (
    <span aria-hidden="true" className="block blur-[3px] opacity-80 select-none">
      <span className="block text-[14px] font-semibold text-fg">Điều giữ trong lòng</span>
      <span className="mt-1 block font-story text-[14px] text-thought italic">{VEILED}</span>
    </span>
  );
  if (always) return <li className={shell}>{body}</li>;
  return (
    <li>
      <button
        type="button"
        aria-pressed={open}
        aria-label={open ? undefined : secretLabel(characterName)}
        onClick={() => setOpen((o) => !o)}
        className={cx(shell, "group cursor-pointer")}
      >
        {open && <span className="sr-only">Chạm để giấu lại. </span>}
        {body}
        {!open && (
          <span aria-hidden="true" className="absolute inset-0 flex items-center justify-center">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-line bg-surface px-3 py-1 text-[13px] font-medium text-fg transition-colors group-hover:bg-surface-2">
              <IconEye className="text-[15px] text-accent" />
              Chạm để đọc
            </span>
          </span>
        )}
      </button>
    </li>
  );
}

function WorldSection({
  lore,
  characterName,
  showThoughts,
  onRetry,
  onJumpToTurn,
}: {
  lore: StoryLoreState;
  characterName: string;
  showThoughts: boolean;
  onRetry: () => void;
  onJumpToTurn: (turnIndex: number) => void;
}) {
  const data = lore.kind === "ready" ? lore.lore : lore.kind === "error" ? lore.lore : null;
  if (!data) {
    if (lore.kind === "error") {
      return (
        <div role="alert" className="flex flex-col items-start gap-1">
          <div className="flex items-center gap-2">
            <p className="text-[14px] leading-snug text-fg">Chưa tải được thế giới.</p>
            <Button size="sm" variant="ghost" onClick={onRetry} className="max-sm:h-11">
              Thử lại
            </Button>
          </div>
          <ErrorDetails technical={[lore.text, lore.technical].filter(Boolean).join("\n") || null} />
        </div>
      );
    }
    return (
      <div aria-busy="true" className="flex flex-col gap-2">
        <Skeleton shape="pill" width={160} height={28} />
        <Skeleton shape="pill" width={160} height={28} />
      </div>
    );
  }
  const split = splitUnlocked(data.entries, showThoughts);
  const empty = unlockedEmptyLine(data, split, characterName);
  return (
    <div className="flex flex-col gap-4">
      {empty && (
        <div className="flex flex-col items-start gap-2">
          <p className="text-[14px] leading-snug text-muted">{empty}</p>
          {!data.available && data.can_edit && data.card_id > 0 && (
            <a
              href={studioWorldHref(data.card_id)}
              className="-ml-3 inline-flex h-9 items-center rounded-full px-3 text-[14px] font-semibold text-muted transition-colors duration-150 hover:bg-surface-2 hover:text-fg max-sm:h-11"
            >
              Thêm trong Studio
            </a>
          )}
        </div>
      )}
      {split.open.length > 0 && (
        <ul className="flex flex-col">
          {split.open.map((e) => (
            <OpenEntry key={e.entry_id} entry={e} onJump={() => onJumpToTurn(e.first_turn)} />
          ))}
        </ul>
      )}
      {split.secret.length > 0 && (
        <div className="flex flex-col gap-2.5">
          <h4 className="text-[14px] leading-tight font-semibold text-muted">{secretGroupTitle(characterName)}</h4>
          <ul className="flex flex-col gap-2.5">
            {split.secret.map((e) => (
              <SecretEntry key={e.entry_id} entry={e} characterName={characterName} />
            ))}
          </ul>
        </div>
      )}
      {lore.kind === "error" && (
        <div role="alert" className="flex items-center gap-2">
          <p className="text-[13px] leading-snug text-muted">Chưa tải lại được thế giới.</p>
          <Button size="sm" variant="ghost" onClick={onRetry} className="max-sm:h-11">
            Thử lại
          </Button>
        </div>
      )}
    </div>
  );
}

/**
 * The heart drawer (DESIGN.md slide-over, phase3.md §8): the acting directive, the six emotion
 * bars, the current scene, the memories (forget one, read the story again) and the world entries the
 * story has unlocked (Phase 4).
 * No job status or search mode (Phase 3b: technical things live under Tài khoản → Nâng cao).
 */
export function HeartDrawer({
  open,
  onClose,
  characterName,
  extras,
  error,
  errorTechnical: errorTech = null,
  onRetry,
  onForget,
  onRebuild,
  lore,
  onRetryLore,
  showThoughts,
  onJumpToTurn,
}: Props) {
  const rel = extras?.relationship ?? null;
  const load = drawerLoadState(extras, error);
  const loading = load === "loading";
  // Opening focuses the top of the content, not the first control (that would be a "Quên" deep in the
  // memory list): a screen reader starts at the directive, and nothing destructive sits under focus.
  const startRef = useRef<HTMLDivElement>(null);

  return (
    <Drawer
      open={open}
      onClose={onClose}
      title="Cảm xúc & ký ức"
      description={`Điều ${characterName} đang cảm thấy và còn nhớ trong story này.`}
      initialFocusRef={startRef}
    >
      <div ref={startRef} tabIndex={-1} className="flex flex-col gap-7 pt-2 outline-none">
        {error && (
          <div
            role="alert"
            className="flex items-center gap-3 rounded-control bg-[color-mix(in_oklab,var(--color-danger)_12%,var(--color-surface))] py-2 pr-2 pl-4 text-[14px] leading-snug text-fg"
          >
            <div className="min-w-0 flex-1">
              <p>Không tải được cảm xúc của story. {error}</p>
              <ErrorDetails technical={errorTech} />
            </div>
            <Button size="sm" variant="secondary" onClick={onRetry} className="max-sm:h-11">
              Thử lại
            </Button>
          </div>
        )}

        {/* A failed first load knows nothing: only the error and "Thử lại", no "no data" copy and no
            busy skeletons next to it. */}
        {load !== "failed" && (
          <>
            <Section title="Chỉ dẫn diễn xuất">
              {loading ? (
                <Skeleton shape="card" height={88} />
              ) : (
                <div className="rounded-card bg-surface-2 px-4 py-3.5">
                  {rel ? (
                    <p className="font-story text-[15px] text-prose">
                      {rel.directive ?? `Chưa có chỉ dẫn diễn xuất cho ${characterName}.`}
                    </p>
                  ) : (
                    <p className="text-[14px] leading-relaxed text-muted">{NO_RELATIONSHIP}</p>
                  )}
                </div>
              )}
            </Section>

            <Section title="Ma trận cảm xúc">
              <div className="flex flex-col gap-4" aria-busy={loading || undefined}>
                {EMOTIONS.map((e) => (
                  <Meter
                    key={e.key}
                    label={e.label}
                    value={rel ? rel[e.key] : 0}
                    empty={!rel}
                    color={`var(--color-emo-${e.key})`}
                  />
                ))}
              </div>
            </Section>

            <Section title="Cảnh">
              {loading || !extras ? <Skeleton shape="text" width="60%" height={14} /> : <SceneSection extras={extras} />}
            </Section>

            <Section title="Ký ức">
              {loading || !extras ? (
                <div aria-busy="true" className="flex flex-col gap-2">
                  <Skeleton shape="text" lines={2} />
                  <Skeleton shape="pill" width={96} height={20} />
                </div>
              ) : (
                <MemorySection extras={extras} characterName={characterName} onForget={onForget} onRebuild={onRebuild} />
              )}
            </Section>

            <Section title="Thế giới đã mở khoá">
              <WorldSection
                lore={lore}
                characterName={characterName}
                showThoughts={showThoughts}
                onRetry={onRetryLore}
                onJumpToTurn={onJumpToTurn}
              />
            </Section>
          </>
        )}

      </div>
    </Drawer>
  );
}
