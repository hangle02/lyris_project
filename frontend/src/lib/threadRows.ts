import type { Message, Mode } from "../types.ts";

/**
 * Story and DM share one timeline (the character remembers both), but each view
 * shows only its own messages. Runs of the other mode collapse into one marker row.
 */
export type ThreadRow =
  | {
      type: "msg";
      m: Message;
      /** Last message of the whole timeline, an assistant reply. */
      isLastAssistant: boolean;
      /** Last reply right after a user turn: can be regenerated. */
      canRegenerate: boolean;
      /** Later messages of the other mode that "Xoá từ đây" also removes. */
      hiddenAfter: number;
    }
  | { type: "other"; key: string; count: number };

/**
 * `all` is the full active timeline (turn order); `shown` is the part to display
 * (the turn being regenerated and anything after it are left out while streaming).
 */
export function buildRows(all: Message[], shown: Message[], view: Mode): ThreadRow[] {
  const last = all[all.length - 1];
  const prev = all[all.length - 2];

  // Messages of the other mode after each position, counted over the whole timeline.
  const otherAfter = new Map<Message, number>();
  let count = 0;
  for (let i = all.length - 1; i >= 0; i--) {
    const m = all[i] as Message;
    otherAfter.set(m, count);
    if (m.mode !== view) count++;
  }

  const rows: ThreadRow[] = [];
  for (const m of shown) {
    if (m.mode !== view) {
      const tail = rows[rows.length - 1];
      if (tail && tail.type === "other") tail.count++;
      else rows.push({ type: "other", key: `other-${m.turn_index}`, count: 1 });
      continue;
    }
    const isLastAssistant = m === last && m.role === "assistant";
    rows.push({
      type: "msg",
      m,
      isLastAssistant,
      canRegenerate: isLastAssistant && prev !== undefined && prev.role === "user",
      hiddenAfter: otherAfter.get(m) ?? 0,
    });
  }
  return rows;
}

export type Receipt = "sending" | "sent" | "seen";

/**
 * DM delivery footer: only the player's newest message in this view carries one. "seen" once a
 * character reply follows it in the timeline (or one is being written right now), "sending" while
 * the message is not saved yet, otherwise "sent". Null when the view has no player message.
 */
export function dmReceipt(
  all: Message[],
  view: Mode,
  replying: boolean,
): { turnIndex: number; status: Receipt } | null {
  for (let i = all.length - 1; i >= 0; i--) {
    const m = all[i] as Message;
    if (m.role !== "user" || m.mode !== view) continue;
    if (m.id === null) return { turnIndex: m.turn_index, status: "sending" };
    const answered = replying || all.slice(i + 1).some((n) => n.role === "assistant");
    return { turnIndex: m.turn_index, status: answered ? "seen" : "sent" };
  }
  return null;
}

/** Footer text under the player's newest DM: "00:40 • Đã gửi" / "00:40 • Đã xem" / "Đang gửi…". */
export function receiptLabel(status: Receipt, clock: string): string {
  if (status === "sending") return "Đang gửi…";
  const word = status === "seen" ? "Đã xem" : "Đã gửi";
  return clock ? `${clock} • ${word}` : word;
}
