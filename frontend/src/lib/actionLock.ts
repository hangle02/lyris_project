// Why the actions under a turn (Sửa, Xoá từ đây, Thích, Tạo lại…) are locked right now (F06).
// A locked button says why in its tooltip (`title`): never a bare disabled button. Pure, tested in
// actionLock.test.ts.

/** A reply is streaming: wait for it, or stop it. */
export const LOCK_REPLYING = "Đợi nhân vật trả lời xong (hoặc bấm Dừng) rồi mới làm được.";
/** Suggestions are being written (the server holds the story meanwhile). */
export const LOCK_SUGGESTING = "Đợi gợi ý hiện xong (hoặc bấm Huỷ gợi ý) rồi mới làm được.";
/** An edit, delete or version switch is being saved. */
export const LOCK_SAVING = "Đang lưu thay đổi, đợi một chút.";
/** Locked, but the page gave no reason (e.g. a caller outside the chat page): a plain "wait". */
export const LOCK_GENERIC = "Đợi một chút rồi mới làm được.";
/** This turn has no id yet: it is still being saved. */
export const LOCK_PENDING = "Lượt này đang được lưu, đợi một chút.";

/** The chat page's lock reason, or null when actions are open. Streaming first: the player can stop it. */
export function actionLockReason(s: { streaming: boolean; suggesting: boolean; saving: boolean }): string | null {
  if (s.streaming) return LOCK_REPLYING;
  if (s.suggesting) return LOCK_SUGGESTING;
  if (s.saving) return LOCK_SAVING;
  return null;
}

/**
 * Reason for one turn's actions: the page's reason while the page locks them (LOCK_GENERIC when the
 * page gave none: never "bấm Dừng" when nothing streams), else "being saved" for a turn without an id;
 * null when nothing is locked.
 */
export function messageLockReason(s: { disabled: boolean; pending: boolean; reason: string | null }): string | null {
  if (s.disabled) return s.reason ?? LOCK_GENERIC;
  if (s.pending) return LOCK_PENDING;
  return null;
}

/** F42 (docs/coins.md §10.3): a member under 6 usable coins cannot ask for another version. */
export const LOCK_NO_COINS_REGEN = "Cần 6 coin để tạo lại.";

/**
 * Reason "Tạo lại câu trả lời" is locked: the page's reason first (a reply streaming can be stopped),
 * then the coin lock; null when it can run.
 */
export function regenerateLockReason(pageReason: string | null, coin: { locked: boolean }): string | null {
  if (pageReason) return pageReason;
  return coin.locked ? LOCK_NO_COINS_REGEN : null;
}
