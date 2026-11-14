import { Fragment, useContext, useState } from "react";
import type { ReactNode } from "react";
import type { StreamingState } from "../hooks/useChat";
import { dmOnlyHiddenThought } from "../lib/storyBlocks";
import { receiptLabel } from "../lib/threadRows";
import type { Receipt, ThreadRow } from "../lib/threadRows";
import { Avatar } from "./Avatar";
import { CharacterAvatarContext } from "./characterAvatar";
import { waitingLine } from "../pages/chat/chatLogic";
import { TypingDots } from "./TypingDots";
import { turnDomId } from "../pages/chat/eventsLogic";
import { IconBookOpen } from "./icons";
import { ActionRow, DeleteConfirm, DirectiveChip, EditBox } from "./MessageItem";
import type { MessageActions } from "./MessageItem";
import { InlineText } from "./Prose";
import { PlayerAvatarContext } from "../pages/chat/playerAvatar";
import { ShowThoughtsContext } from "./showThoughts";
import { ThoughtCard } from "../pages/chat/ThoughtCard";
import { Chip, cx } from "./ui";

interface Props extends MessageActions {
  rows: ThreadRow[];
  streaming: StreamingState | null;
  disabled: boolean;
  characterName: string;
  /** Character image; defaults to CharacterAvatarContext (set by the chat page). */
  avatarUrl?: string | null;
  /** Delivery footer under the player's newest message ("00:40 • Đã xem"). */
  receipt?: { turnIndex: number; status: Receipt } | null;
}

/** Messages closer than this stay in one visual group (no avatar/time between them). */
const GROUP_MS = 5 * 60 * 1000;
/** A time label appears above a message sent this long after the previous one. */
const TIME_GAP_MS = 15 * 60 * 1000;

function parseTime(iso: string | null): number {
  if (!iso) return Date.now();
  // The backend writes UTC; old SQLite values may lack the zone.
  const d = new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : `${iso.replace(" ", "T")}Z`);
  return Number.isNaN(d.getTime()) ? Date.now() : d.getTime();
}

const hm = new Intl.DateTimeFormat("vi-VN", { hour: "2-digit", minute: "2-digit", hour12: false });
const dmy = new Intl.DateTimeFormat("vi-VN", { day: "2-digit", month: "2-digit" });

function timeLabel(t: number): string {
  const d = new Date(t);
  const today = new Date();
  const startOfToday = new Date(today.getFullYear(), today.getMonth(), today.getDate()).getTime();
  if (t >= startOfToday) return hm.format(d);
  if (t >= startOfToday - 86_400_000) return `Hôm qua ${hm.format(d)}`;
  return `${dmy.format(d)} ${hm.format(d)}`;
}

/** Each non-empty line of a reply is its own text bubble, like several messages sent in a row. */
export function bubbleLines(text: string): string[] {
  return text
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean);
}

const BUBBLE = "w-fit max-w-full rounded-[20px] px-4 py-2 text-[16px] leading-snug [overflow-wrap:anywhere]";

/** Small avatar beside a bubble; `hidden` keeps its space inside a group of messages. */
function BubbleAvatar({ name, hidden = false }: { name: string; hidden?: boolean }) {
  const url = useContext(CharacterAvatarContext);
  return <Avatar name={name} url={url} size={28} className={hidden ? "invisible" : ""} />;
}

function TheirBubble({ text, caret = false }: { text: string; caret?: boolean }) {
  return (
    <div className={cx(BUBBLE, "border border-edge bg-surface text-fg", caret && "caret")}>
      <InlineText text={text} />
    </div>
  );
}

function MineBubble({ children, pending }: { children: ReactNode; pending: boolean }) {
  return (
    <div
      className={cx(
        BUBBLE,
        "border border-user-border bg-user-gradient whitespace-pre-wrap text-user-fg",
        pending && "opacity-70",
      )}
    >
      {children}
    </div>
  );
}

/** The character is writing: three bouncing dots in a bubble beside their avatar (Phase 3b). */
function TypingBubble({ name, waiting = false }: { name: string; waiting?: boolean }) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-end gap-2">
        <BubbleAvatar name={name} />
        <div className="flex h-10 w-fit items-center rounded-[20px] border border-edge bg-surface px-4 text-[13px] text-muted">
          <TypingDots />
        </div>
      </div>
      {/* Phase 4b (docs/auth.md §5.5): every generation slot is busy. */}
      {waiting && <p className="pl-9 text-[13px] leading-snug text-muted">{waitingLine(name)}</p>}
    </div>
  );
}

function DmMessage({
  row,
  characterName,
  showAvatar,
  selected,
  onToggle,
  disabled,
  footer,
  actions,
}: {
  row: Extract<ThreadRow, { type: "msg" }>;
  characterName: string;
  showAvatar: boolean;
  selected: boolean;
  onToggle: () => void;
  disabled: boolean;
  footer: string | null;
  actions: MessageActions;
}) {
  const { m } = row;
  // The story's persona beside the player's bubbles (null outside the chat page: no avatar column).
  const player = useContext(PlayerAvatarContext);
  const showThoughts = useContext(ShowThoughtsContext);
  const [editing, setEditing] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const mine = m.role === "user";
  const pending = m.id === null;
  // The newest reply keeps its actions visible (regenerate, variants); others show them on tap.
  const showActions = !editing && (selected || confirmDelete || row.isLastAssistant);

  if (editing) {
    return (
      <EditBox
        initial={m.raw_content}
        note={!mine && !showThoughts && m.thought?.trim() ? `Bản sửa có cả suy nghĩ của ${characterName.trim() || "nhân vật"}.` : null}
        disabled={disabled}
        onSave={(content) => actions.onEdit(m, content)}
        onCancel={() => setEditing(false)}
      />
    );
  }

  const actionRow = showActions ? (
    <div className={mine ? (player ? "mt-0.5 mr-7" : "mt-0.5 -mr-1.5") : "mt-0.5 ml-7"}>
      <ActionRow
        message={m}
        isLastAssistant={row.isLastAssistant}
        canRegenerate={row.canRegenerate}
        locked={disabled || pending}
        align={mine ? "end" : "start"}
        onStartEdit={() => {
          setConfirmDelete(false);
          setEditing(true);
        }}
        onStartDelete={() => {
          setEditing(false);
          setConfirmDelete(true);
        }}
        {...actions}
      />
    </div>
  ) : null;

  const deleteBox = confirmDelete ? (
    <DeleteConfirm
      disabled={disabled}
      hiddenAfter={row.hiddenAfter}
      onCancel={() => setConfirmDelete(false)}
      onConfirm={() => {
        if (disabled) return;
        setConfirmDelete(false);
        actions.onDelete(m);
      }}
    />
  ) : null;

  if (mine) {
    return (
      <article
        id={turnDomId(m.turn_index)}
        tabIndex={-1}
        aria-label="Tin nhắn của bạn"
        className="flex flex-col items-end outline-none"
      >
        <div className="flex max-w-[80%] items-end gap-2">
          <button
            type="button"
            onClick={onToggle}
            aria-expanded={selected}
            className="flex min-w-0 flex-col items-end text-left"
          >
            {m.visible_content && (
              <MineBubble pending={pending}>
                <InlineText text={m.visible_content} inheritColor />
              </MineBubble>
            )}
            {m.directive && <DirectiveChip directive={m.directive} spaced={!!m.visible_content} />}
          </button>
          {player && (
            <Avatar name={player.name} url={player.url} size={28} className={showAvatar ? "" : "invisible"} />
          )}
        </div>
        {footer && (
          <p className={cx("mt-1 text-[12px] text-muted tabular-nums", player ? "mr-10" : "mr-1")}>{footer}</p>
        )}
        {actionRow}
        {deleteBox}
      </article>
    );
  }

  const lines = bubbleLines(m.visible_content);
  return (
    <article
      id={turnDomId(m.turn_index)}
      tabIndex={-1}
      aria-label={`Tin nhắn của ${characterName}`}
      className="flex flex-col items-start outline-none"
    >
      <div className="flex max-w-[80%] items-end gap-2">
        <BubbleAvatar name={characterName} hidden={!showAvatar} />
        <button
          type="button"
          onClick={onToggle}
          aria-expanded={selected}
          className="flex min-w-0 flex-col items-start gap-1 text-left"
        >
          {lines.length > 0 ? (
            lines.map((l, i) => <TheirBubble key={i} text={l} />)
          ) : dmOnlyHiddenThought(lines.length, m.thought, showThoughts) ? (
            <span className="block py-1 text-[13px] leading-snug text-muted">
              Lượt này chỉ có suy nghĩ của {characterName}.
            </span>
          ) : (
            <TheirBubble text="…" />
          )}
        </button>
      </div>
      {showThoughts && m.thought?.trim() && (
        <div className="w-[min(80%,30rem)] pl-9">
          <ThoughtCard text={m.thought.trim()} compact className="mt-2" />
        </div>
      )}
      {actionRow}
      {deleteBox}
    </article>
  );
}

function StreamingDm({ s, characterName }: { s: StreamingState; characterName: string }) {
  const lines = bubbleLines(s.text);
  if (lines.length === 0) return <TypingBubble name={characterName} waiting={s.waiting} />;
  return (
    <div className="flex max-w-[80%] items-end gap-2" aria-live="polite" aria-busy="true">
      <BubbleAvatar name={characterName} />
      <div className="flex min-w-0 flex-col items-start gap-1">
        {lines.map((l, i) => (
          <TheirBubble key={i} text={l} caret={i === lines.length - 1} />
        ))}
      </div>
    </div>
  );
}

/** Direct messages, laid out like a phone messaging app. */
export function DmThread({
  rows,
  streaming,
  disabled,
  characterName,
  avatarUrl: avatarProp,
  receipt = null,
  ...actions
}: Props) {
  const fromContext = useContext(CharacterAvatarContext);
  const avatarUrl = avatarProp !== undefined ? avatarProp : fromContext;
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const hasMessages = rows.some((r) => r.type === "msg");

  return (
    <CharacterAvatarContext.Provider value={avatarUrl}>
      <div className="flex flex-col">
        <div className="mb-6 flex flex-col items-center gap-2 pt-2 text-center">
          <Avatar name={characterName} url={avatarUrl} size={64} />
          <span className="text-[16px] font-semibold text-fg">{characterName}</span>
          <span className="max-w-[18rem] text-[13px] leading-snug text-muted">
            {hasMessages ? "Tin nhắn riêng" : `Chưa có tin nhắn nào. Nhắn gì đó cho ${characterName} đi.`}
          </span>
        </div>

        <div className="flex flex-col">
          {rows.map((row, i) => {
            if (row.type === "other") {
              return (
                <div key={row.key} className="my-4 self-center">
                  <Chip size="sm" icon={<IconBookOpen />}>
                    {row.count} lượt trong truyện
                  </Chip>
                </div>
              );
            }
            const prev = rows[i - 1];
            const next = rows[i + 1];
            const t = parseTime(row.m.created_at);
            const prevMsg = prev?.type === "msg" ? prev.m : null;
            const nextMsg = next?.type === "msg" ? next.m : null;
            const showTime = !prevMsg || t - parseTime(prevMsg.created_at) >= TIME_GAP_MS;
            const groupedWithPrev =
              !!prevMsg && !showTime && prevMsg.role === row.m.role && t - parseTime(prevMsg.created_at) < GROUP_MS;
            const groupedWithNext =
              !!nextMsg && nextMsg.role === row.m.role && parseTime(nextMsg.created_at) - t < GROUP_MS;
            const id = row.m.id;
            const footer =
              receipt && row.m.role === "user" && receipt.turnIndex === row.m.turn_index
                ? receiptLabel(receipt.status, row.m.created_at ? hm.format(new Date(t)) : "")
                : null;
            return (
              <Fragment key={id ?? `pending-${row.m.turn_index}`}>
                {showTime && (
                  <p className="mt-4 mb-2 self-center text-[12px] text-muted tabular-nums">{timeLabel(t)}</p>
                )}
                <div className={groupedWithPrev ? "mt-1" : "mt-3"}>
                  <DmMessage
                    row={row}
                    characterName={characterName}
                    showAvatar={!groupedWithNext}
                    selected={id !== null && selectedId === id}
                    onToggle={() => setSelectedId((cur) => (id === null || cur === id ? null : id))}
                    disabled={disabled}
                    footer={footer}
                    actions={actions}
                  />
                </div>
              </Fragment>
            );
          })}
          {streaming && (
            <div className="mt-3">
              <StreamingDm s={streaming} characterName={characterName} />
            </div>
          )}
        </div>
      </div>
    </CharacterAvatarContext.Provider>
  );
}
