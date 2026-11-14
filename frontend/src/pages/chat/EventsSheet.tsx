import { useCallback, useEffect, useId, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import { api, friendlyOf, isAbortError } from "../../api/client";
import { IconMapPin } from "../../components/icons";
import { Badge, Button, Chip, EmptyState, ErrorDetails, Modal, Skeleton, cx } from "../../components/ui";
import type { FriendlyError } from "../../lib/friendlyError";
import type { Moment, TimelineEntry } from "../../types";
import { momentLine } from "./chatLogic";
import { deltaChips, entryTime, modeLabel, normalizeTimeline, sceneText, timelineItems } from "./eventsLogic";

type Tab = "timeline" | "moments";

const TABS: { id: Tab; label: string }[] = [
  { id: "timeline", label: "Dòng thời gian" },
  { id: "moments", label: "Khoảnh khắc" },
];

type Load = { state: "loading" } | { state: "ready"; entries: TimelineEntry[] } | { state: "error"; error: FriendlyError };

interface Props {
  open: boolean;
  onClose: () => void;
  storyId: number;
  characterName: string;
  /** The current moment (Phase 8 fills it; shown in "Khoảnh khắc" when present). */
  moment: Moment | null;
  /** A timeline entry was picked: the sheet closes and the chat jumps to that turn. */
  onJump: (entry: TimelineEntry) => void;
}

/** One turn of the timeline: a button that jumps to the turn in the chat. */
function EntryRow({ entry, onJump }: { entry: TimelineEntry; onJump: (e: TimelineEntry) => void }) {
  const chips = deltaChips(entry.delta);
  const scene = sceneText(entry.scene);
  const time = entryTime(entry.created_at);
  return (
    <li>
      <button
        type="button"
        onClick={() => onJump(entry)}
        className="flex w-full flex-col gap-2 rounded-control px-3 py-3 text-left transition-colors duration-150 hover:bg-surface-2 focus-visible:bg-surface-2"
      >
        <span className="sr-only">Đi tới lượt này. </span>
        <span className="flex items-center gap-2 text-[13px] text-muted">
          <Badge tone={entry.mode === "dm" ? "gold" : "accent"}>{modeLabel(entry.mode)}</Badge>
          {time && <span className="tabular-nums">{time}</span>}
        </span>
        {entry.memory && <span className="font-story text-[15px] text-prose [overflow-wrap:anywhere]">{entry.memory}</span>}
        {entry.facts.length > 0 && (
          <span className="flex flex-col gap-1">
            {entry.facts.map((f) => (
              <span key={f} className="text-[14px] leading-snug text-fg [overflow-wrap:anywhere]">
                <span className="text-muted">Điều đã biết: </span>
                {f}
              </span>
            ))}
          </span>
        )}
        {(chips.length > 0 || scene) && (
          <span className="flex flex-wrap items-center gap-1.5">
            {chips.map((c) => (
              <Chip key={c.key} size="sm" dotColor={`var(--color-emo-${c.key})`} title={c.label}>
                <span aria-hidden="true">{c.text}</span>
                <span className="sr-only">{c.label}</span>
              </Chip>
            ))}
            {scene && (
              <Chip size="sm" icon={<IconMapPin />}>
                {scene}
              </Chip>
            )}
          </span>
        )}
      </button>
    </li>
  );
}

function TimelineTab({
  load,
  characterName,
  onRetry,
  onJump,
}: {
  load: Load;
  characterName: string;
  onRetry: () => void;
  onJump: (e: TimelineEntry) => void;
}) {
  if (load.state === "loading") {
    return (
      <div aria-busy="true" className="flex flex-col gap-5 px-3 py-3">
        <span className="sr-only">Đang tải sự kiện…</span>
        {[0, 1, 2].map((i) => (
          <div key={i} className="flex flex-col gap-2">
            <Skeleton shape="pill" width={64} height={20} />
            <Skeleton shape="text" lines={2} height={14} />
            <Skeleton shape="pill" width={120} height={28} />
          </div>
        ))}
      </div>
    );
  }
  if (load.state === "error") {
    return (
      <div role="alert" className="flex flex-col items-start gap-2 px-3 py-2">
        <p className="text-[14px] leading-snug text-fg">{load.error.text}</p>
        <ErrorDetails technical={load.error.technical} />
        <Button size="sm" onClick={onRetry}>
          Thử lại
        </Button>
      </div>
    );
  }
  const items = timelineItems(load.entries);
  if (items.length === 0) {
    return (
      <div className="px-3">
        <EmptyState text={`Chưa có sự kiện nào. Sau mỗi lượt ${characterName} trả lời, Lyris ghi lại điều đáng nhớ ở đây.`} />
      </div>
    );
  }
  return (
    <>
      <p className="px-3 pb-2 text-[13px] leading-snug text-muted">Mới nhất ở trên. Chạm một sự kiện để xem lại lượt đó.</p>
      <ul className="flex flex-col divide-y divide-line">
        {items.map((e) => (
          <EntryRow key={e.turn_index} entry={e} onJump={onJump} />
        ))}
      </ul>
    </>
  );
}

/**
 * The WHIF-style shell (the director fills it in Phase 8): the current moment, then missions, each
 * under its own heading so the tab shows what it will hold even while both are empty.
 */
function MomentsTab({ moment, characterName }: { moment: Moment | null; characterName: string }) {
  const line = moment ? momentLine(moment) : null;
  return (
    <div className="flex flex-col gap-6">
      <section className="flex flex-col gap-2.5">
        <h3 className="text-[15px] font-semibold text-fg">Khoảnh khắc</h3>
        {line ? (
          <div className="flex flex-col gap-2 rounded-card bg-surface-2 px-4 py-3.5">
            <p className="text-[15px] leading-snug text-fg">{line.text}</p>
            {line.effect && (
              <span>
                <Badge tone="gold">{line.effect}</Badge>
              </span>
            )}
          </div>
        ) : (
          <EmptyState
            text={`Chưa có khoảnh khắc nào. Khi story với ${characterName} rẽ sang một hướng đáng nhớ, khoảnh khắc đó hiện ở đây.`}
          />
        )}
      </section>
      <section className="flex flex-col gap-2.5">
        <h3 className="text-[15px] font-semibold text-fg">Nhiệm vụ</h3>
        <EmptyState text={`Chưa có nhiệm vụ nào. Những việc nhỏ ${characterName} nhờ bạn, hay hai người hẹn nhau làm, sẽ hiện ở đây.`} />
      </section>
    </div>
  );
}

/**
 * "Sự kiện" (Phase 3b, opened from the composer's "+"): two tabs. "Dòng thời gian" lists what each
 * turn left behind (memory, facts, emotion changes, scene), newest first; picking one closes the
 * sheet and jumps to that turn. "Khoảnh khắc" is the WHIF-style moments/missions shell (Phase 8).
 */
export function EventsSheet({ open, onClose, storyId, characterName, moment, onJump }: Props) {
  const [tab, setTab] = useState<Tab>("timeline");
  const [load, setLoad] = useState<Load>({ state: "loading" });
  const ctrlRef = useRef<AbortController | null>(null);
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const baseId = useId();

  const fetchTimeline = useCallback(async () => {
    ctrlRef.current?.abort();
    const ctrl = new AbortController();
    ctrlRef.current = ctrl;
    setLoad({ state: "loading" });
    try {
      const raw: unknown = await api.getTimeline(storyId, ctrl.signal);
      if (!ctrl.signal.aborted) setLoad({ state: "ready", entries: normalizeTimeline(raw) });
    } catch (e) {
      if (isAbortError(e) || ctrl.signal.aborted) return;
      setLoad({ state: "error", error: friendlyOf(e) });
    }
  }, [storyId]);

  // Read again every time it opens (the story moved on since).
  useEffect(() => {
    if (!open) return;
    setTab("timeline");
    void fetchTimeline();
    return () => ctrlRef.current?.abort();
  }, [open, fetchTimeline]);

  const onTabKey = (e: KeyboardEvent<HTMLButtonElement>, index: number) => {
    let next = -1;
    if (e.key === "ArrowRight" || e.key === "ArrowLeft") next = (index + (e.key === "ArrowRight" ? 1 : -1) + TABS.length) % TABS.length;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = TABS.length - 1;
    if (next === -1) return;
    e.preventDefault();
    const t = TABS[next];
    if (!t) return;
    setTab(t.id);
    tabRefs.current[next]?.focus();
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Sự kiện"
      description={`Những gì đã xảy ra giữa bạn và ${characterName}.`}
      size="md"
      // One height for both tabs: switching tabs must not resize the sheet and move the tabs away
      // from the pointer (a centred dialog re-centres when its height changes).
      className="h-[min(92dvh,40rem)] sm:h-[min(85dvh,40rem)]"
    >
      <div className="flex flex-col gap-4">
        <div role="tablist" aria-label="Loại sự kiện" className="flex border-b border-line">
          {TABS.map((t, i) => {
            const on = tab === t.id;
            return (
              <button
                key={t.id}
                ref={(el) => {
                  tabRefs.current[i] = el;
                }}
                type="button"
                role="tab"
                id={`${baseId}-tab-${t.id}`}
                aria-selected={on}
                aria-controls={`${baseId}-panel-${t.id}`}
                tabIndex={on ? 0 : -1}
                onClick={() => setTab(t.id)}
                onKeyDown={(e) => onTabKey(e, i)}
                className={cx(
                  // The ring sits inside the tab: the list scrolls under the sheet header and would clip it.
                  "relative h-11 flex-1 rounded-t-control px-2 text-[14px] font-semibold transition-colors duration-150 focus-visible:[outline-offset:-2px]",
                  on ? "text-fg" : "text-muted hover:text-fg",
                )}
              >
                {t.label}
                {on && <span aria-hidden="true" className="absolute inset-x-4 bottom-0 h-0.5 rounded-full bg-fg" />}
              </button>
            );
          })}
        </div>
        {TABS.map((t) => (
          <div
            key={t.id}
            role="tabpanel"
            id={`${baseId}-panel-${t.id}`}
            aria-labelledby={`${baseId}-tab-${t.id}`}
            hidden={tab !== t.id}
            className="-mx-3"
          >
            {tab === t.id &&
              (t.id === "timeline" ? (
                <TimelineTab load={load} characterName={characterName} onRetry={() => void fetchTimeline()} onJump={onJump} />
              ) : (
                <div className="px-3">
                  <MomentsTab moment={moment} characterName={characterName} />
                </div>
              ))}
          </div>
        ))}
      </div>
    </Modal>
  );
}
