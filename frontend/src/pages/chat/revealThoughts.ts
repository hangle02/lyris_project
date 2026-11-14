// "Luôn hiện suy nghĩ": một công tắc dùng chung cho mọi thẻ Thought (chat, chat thử, xem trước lời mở đầu).
// Lưu ở localStorage "lyris.revealThoughts"; đồng bộ giữa các tab qua sự kiện storage.
import { useCallback, useSyncExternalStore } from "react";

export const REVEAL_THOUGHTS_KEY = "lyris.revealThoughts";

const listeners = new Set<() => void>();
let cached: boolean | null = null;

function read(): boolean {
  try {
    const v = localStorage.getItem(REVEAL_THOUGHTS_KEY);
    return v === "true" || v === "1";
  } catch {
    return false;
  }
}

function get(): boolean {
  if (cached === null) cached = read();
  return cached;
}

function emit() {
  for (const l of listeners) l();
}

function onStorage(e: StorageEvent) {
  if (e.key !== null && e.key !== REVEAL_THOUGHTS_KEY) return;
  cached = read();
  emit();
}

function subscribe(fn: () => void): () => void {
  listeners.add(fn);
  if (listeners.size === 1) window.addEventListener("storage", onStorage);
  return () => {
    listeners.delete(fn);
    if (listeners.size === 0) window.removeEventListener("storage", onStorage);
  };
}

export function setRevealThoughts(on: boolean): void {
  cached = on;
  try {
    localStorage.setItem(REVEAL_THOUGHTS_KEY, on ? "true" : "false");
  } catch {
    // storage unavailable: the switch still works for this page
  }
  emit();
}

/** [always reveal thoughts, setter]. */
export function useRevealThoughts(): [boolean, (on: boolean) => void] {
  const on = useSyncExternalStore(subscribe, get, () => false);
  const set = useCallback((v: boolean) => setRevealThoughts(v), []);
  return [on, set];
}
