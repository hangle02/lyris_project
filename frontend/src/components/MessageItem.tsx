import { useContext, useState } from "react";
import type { KeyboardEvent, MouseEvent } from "react";
import type { Message, Rating } from "../types";
import { Avatar } from "./Avatar";
import { PlayerStoryTurn, StoryReply } from "./Prose";
import { turnDomId } from "../pages/chat/eventsLogic";
import { PlayerAvatarContext } from "../pages/chat/playerAvatar";
import { buildStoryBlocks, onlyHiddenThoughts } from "../lib/storyBlocks";
import { MAX_CONTENT_CHARS, splitSegments } from "../lib/text";
import { ShowThoughtsContext } from "./showThoughts";
import {
  IconChevronLeft,
  IconChevronRight,
  IconEdit,
  IconRefreshCw,
  IconThumbsDown,
  IconThumbsUp,
  IconTrash,
} from "./icons";
import { Button, IconButton, TextArea, cx } from "./ui";

/**
 * Older turns keep their actions out of the reading line: on a mouse they appear while the turn is
 * hovered or holds focus (the space stays reserved, so nothing shifts); on a touch screen they take
 * no room until the turn is tapped, as in DM Mode. The newest reply keeps its actions in view
 * (regenerate, versions).
 */
const QUIET_ACTIONS =
  "pointer-coarse:hidden pointer-events-none opacity-0 transition-opacity duration-150 group-hover/turn:pointer-events-auto group-hover/turn:opacity-100 group-focus-within/turn:pointer-events-auto group-focus-within/turn:opacity-100";

/** Taps on the turn itself (not on its buttons, links or fields, not ending a text selection). */
function isPlainTap(e: MouseEvent<HTMLElement>): boolean {
  const target = e.target as HTMLElement | null;
  if (target?.closest("button, a, input, textarea, select, [role=\"button\"]")) return false;
  const selection = typeof window !== "undefined" ? window.getSelection() : null;
  return !selection || selection.isCollapsed;
}

export interface MessageActions {
  onRegenerate: (m: Message) => void;
  onSelectVariant: (m: Message, variantIndex: number) => void;
  onEdit: (m: Message, content: string) => Promise<boolean>;
  onDelete: (m: Message) => void;
  onFeedback: (m: Message, rating: Rating | null) => void;
}

interface Props extends MessageActions {
  message: Message;
  characterName: string;
  /** Last message of the story, an assistant reply. */
  isLastAssistant: boolean;
  /** Last assistant reply right after a user turn: can be regenerated. */
  canRegenerate: boolean;
  /** Disable every action (a reply is streaming or a request is in flight). */
  disabled: boolean;
  /** Later turns from the other mode (hidden in this view) that "Xoá từ đây" also removes. */
  hiddenAfter: number;
}

export function EditBox({
  initial,
  onSave,
  onCancel,
  disabled,
  note,
}: {
  initial: string;
  onSave: (content: string) => Promise<boolean>;
  onCancel: () => void;
  disabled: boolean;
  /** One quiet line above the field (e.g. the raw text holds thoughts the player chose not to read). */
  note?: string | null;
}) {
  const [draft, setDraft] = useState(initial);
  const [saving, setSaving] = useState(false);
  const canSave = draft.trim().length > 0 && draft !== initial && !saving && !disabled;

  const save = async () => {
    if (!canSave) return;
    setSaving(true);
    const ok = await onSave(draft);
    setSaving(false);
    if (ok) onCancel();
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Escape") {
      e.preventDefault();
      onCancel();
    } else if (e.key === "Enter" && (e.metaKey || e.ctrlKey) && !e.nativeEvent.isComposing) {
      e.preventDefault();
      void save();
    }
  };

  return (
    <div className="w-full">
      {note && <p className="mb-2 text-[13px] leading-snug text-muted">{note}</p>}
      <TextArea
        label="Sửa tin nhắn"
        hideLabel
        value={draft}
        onChange={setDraft}
        onKeyDown={onKeyDown}
        autoFocus
        maxHeight={420}
        maxLength={MAX_CONTENT_CHARS}
        inputClassName="font-story leading-relaxed"
      />
      <div className="mt-2 flex items-center justify-end gap-2">
        <span className="mr-auto hidden text-[13px] text-muted sm:inline">⌘/Ctrl + Enter để lưu, Esc để huỷ</span>
        <Button size="sm" variant="ghost" onClick={onCancel}>
          Huỷ
        </Button>
        <Button size="sm" variant="primary" onClick={() => void save()} disabled={!canSave} loading={saving}>
          Lưu
        </Button>
      </div>
    </div>
  );
}

export function DeleteConfirm({
  onConfirm,
  onCancel,
  disabled,
  hiddenAfter = 0,
}: {
  onConfirm: () => void;
  onCancel: () => void;
  disabled: boolean;
  hiddenAfter?: number;
}) {
  return (
    <div
      role="alertdialog"
      aria-label="Xác nhận xoá"
      className="mt-2 flex w-full flex-wrap items-center gap-2 rounded-control bg-[color-mix(in_oklab,var(--color-danger)_12%,var(--color-bg))] py-2 pr-2 pl-4 text-[14px] leading-snug"
    >
      <span className="mr-auto min-w-0 py-1 text-fg">
        Xoá lượt này và mọi lượt sau?
        {hiddenAfter > 0 && <span className="text-muted"> Gồm cả {hiddenAfter} tin ở chế độ kia.</span>}
      </span>
      <Button size="sm" variant="ghost" onClick={onCancel}>
        Huỷ
      </Button>
      <Button
        size="sm"
        variant="danger"
        onClick={onConfirm}
        disabled={disabled}
        title={disabled ? "Đợi nhân vật trả lời xong hoặc bấm Dừng rồi mới xoá" : undefined}
        autoFocus
      >
        Xoá
      </Button>
    </div>
  );
}

function Tags({ message }: { message: Message }) {
  const tags: string[] = [];
  if (message.gen_stats?.aborted) tags.push("Đã dừng giữa chừng");
  if (message.edited_at) tags.push(tags.length ? "đã sửa" : "Đã sửa");
  if (tags.length === 0) return null;
  return <span className="px-1 text-[12px] text-muted">{tags.join(", ")}</span>;
}

interface ActionRowProps extends MessageActions {
  message: Message;
  isLastAssistant: boolean;
  canRegenerate: boolean;
  locked: boolean;
  onStartEdit: () => void;
  onStartDelete: () => void;
  align?: "start" | "end";
}

/** Variant switcher, regenerate, thumbs, edit, delete and tags for one message. */
export function ActionRow({
  message,
  isLastAssistant,
  canRegenerate,
  locked,
  onStartEdit,
  onStartDelete,
  onRegenerate,
  onSelectVariant,
  onFeedback,
  align = "start",
}: ActionRowProps) {
  const isUser = message.role === "user";
  return (
    <div className={cx("flex flex-wrap items-center gap-0.5", align === "end" && "justify-end")}>
      {!isUser && isLastAssistant && message.variant_count > 1 && (
        <div className="mr-1 inline-flex items-center" role="group" aria-label="Các phiên bản trả lời">
          <IconButton
            size="sm"
            label="Phiên bản trước"
            icon={<IconChevronLeft />}
            disabled={locked || message.variant_index <= 0}
            onClick={() => onSelectVariant(message, message.variant_index - 1)}
          />
          <span className="min-w-[2.6em] text-center text-[13px] text-muted tabular-nums">
            {message.variant_index + 1}/{message.variant_count}
          </span>
          <IconButton
            size="sm"
            label="Phiên bản sau"
            icon={<IconChevronRight />}
            disabled={locked || message.variant_index >= message.variant_count - 1}
            onClick={() => onSelectVariant(message, message.variant_index + 1)}
          />
        </div>
      )}
      {!isUser && canRegenerate && (
        <IconButton
          size="sm"
          label="Tạo lại câu trả lời"
          icon={<IconRefreshCw />}
          disabled={locked}
          onClick={() => onRegenerate(message)}
        />
      )}
      {!isUser && (
        <>
          <IconButton
            size="sm"
            label="Thích"
            icon={<IconThumbsUp filled={message.rating === "up"} />}
            pressed={message.rating === "up"}
            className={message.rating === "up" ? "text-accent" : undefined}
            disabled={locked}
            onClick={() => onFeedback(message, message.rating === "up" ? null : "up")}
          />
          <IconButton
            size="sm"
            label="Chê"
            icon={<IconThumbsDown filled={message.rating === "down"} />}
            pressed={message.rating === "down"}
            className={message.rating === "down" ? "text-accent" : undefined}
            disabled={locked}
            onClick={() => onFeedback(message, message.rating === "down" ? null : "down")}
          />
        </>
      )}
      <IconButton size="sm" label="Sửa" icon={<IconEdit />} disabled={locked} onClick={onStartEdit} />
      <IconButton size="sm" label="Xoá từ đây" icon={<IconTrash />} disabled={locked} onClick={onStartDelete} />
      <span className={align === "end" ? "order-first mr-1" : "ml-1"}>
        <Tags message={message} />
      </span>
    </div>
  );
}

/** The hidden ((directive)) of a player's turn, shown under the bubble. Wraps; never truncated. */
export function DirectiveChip({ directive, spaced }: { directive: string; spaced: boolean }) {
  return (
    <div
      className={cx(
        "inline-flex max-w-full items-baseline gap-1.5 rounded-control bg-surface-2 px-3 py-1.5 text-[13px] leading-snug text-muted",
        spaced && "mt-1.5",
      )}
      title="Chỉ đạo cho AI (không hiện trong truyện)"
    >
      <span className="shrink-0 font-semibold text-fg">Chỉ đạo</span>
      <span className="italic [overflow-wrap:anywhere]">{directive}</span>
    </div>
  );
}

/** One Story Mode turn: the player's turn in story format, or the character's three kinds of blocks. */
export function MessageItem({
  message,
  characterName,
  isLastAssistant,
  canRegenerate,
  disabled,
  hiddenAfter,
  ...actions
}: Props) {
  const [editing, setEditing] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const isUser = message.role === "user";
  const pending = message.id === null;
  // The story's persona beside the player's turns (null outside the chat page: no avatar).
  const player = useContext(PlayerAvatarContext);
  const [selected, setSelected] = useState(false);
  const showThoughts = useContext(ShowThoughtsContext);
  const actionsInView = isLastAssistant || selected || confirmDelete;
  const onTurnClick = (e: MouseEvent<HTMLElement>) => {
    if (isPlainTap(e)) setSelected((s) => !s);
  };

  const actionRow = (
    <ActionRow
      message={message}
      isLastAssistant={isLastAssistant}
      canRegenerate={canRegenerate}
      locked={disabled || pending}
      align={isUser ? "end" : "start"}
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
  );

  const segments = isUser ? [] : splitSegments(message.raw_content);
  const name = characterName.trim() || "nhân vật";
  // Thoughts hidden: editing still shows the raw text with [Thought: …] (an edit must keep them), so
  // say so once above the field. A deliberate exception: the player opened it to edit.
  const hiddenThoughtsInEdit = !isUser && !showThoughts && segments.some((sg) => sg.kind === "thought");
  const editBox = editing ? (
    <EditBox
      initial={message.raw_content}
      note={hiddenThoughtsInEdit ? `Bản sửa có cả suy nghĩ của ${name}.` : null}
      disabled={disabled}
      onSave={(content) => actions.onEdit(message, content)}
      onCancel={() => setEditing(false)}
    />
  ) : null;

  const deleteBox = confirmDelete ? (
    <DeleteConfirm
      disabled={disabled}
      hiddenAfter={hiddenAfter}
      onCancel={() => setConfirmDelete(false)}
      onConfirm={() => {
        if (disabled) return;
        setConfirmDelete(false);
        actions.onDelete(message);
      }}
    />
  ) : null;

  if (isUser) {
    return (
      <article
        id={turnDomId(message.turn_index)}
        tabIndex={-1}
        className="group/turn flex flex-col items-end outline-none"
        aria-label="Lượt của bạn"
        onClick={onTurnClick}
      >
        {editing ? (
          <div className="w-full">{editBox}</div>
        ) : (
          // Story format (Phase 3b): speech, actions and narration as blocks, right-aligned, with
          // the persona's avatar; the ((directive)) stays a small chip under them.
          <div className="flex max-w-[85%] items-start justify-end gap-2.5">
            <div className="flex min-w-0 flex-col items-end">
              {message.visible_content && <PlayerStoryTurn text={message.visible_content} pending={pending} />}
              {message.directive && (
                <div className="flex max-w-full justify-end">
                  <DirectiveChip directive={message.directive} spaced={!!message.visible_content} />
                </div>
              )}
            </div>
            {player && <Avatar name={player.name} url={player.url} size={28} className="mt-1 shrink-0" />}
          </div>
        )}
        {!editing && <div className={cx("mt-1", player ? "mr-[32px]" : "-mr-1.5", !actionsInView && QUIET_ACTIONS)}>{actionRow}</div>}
        {deleteBox}
      </article>
    );
  }

  return (
    <article
      id={turnDomId(message.turn_index)}
      tabIndex={-1}
      className="group/turn outline-none"
      aria-label={`Lượt của ${characterName}`}
      onClick={onTurnClick}
    >
      {editing ? (
        editBox
      ) : (
        <>
          {onlyHiddenThoughts(buildStoryBlocks(segments), showThoughts) ? (
            <p className="text-[13px] leading-snug text-muted">Lượt này chỉ có suy nghĩ của {name}.</p>
          ) : (
            <StoryReply segments={segments} showThoughts={showThoughts} />
          )}
          <div className={cx("mt-1.5 -ml-2", !actionsInView && QUIET_ACTIONS)}>{actionRow}</div>
        </>
      )}
      {deleteBox}
    </article>
  );
}
