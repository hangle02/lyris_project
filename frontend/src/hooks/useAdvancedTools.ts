import { useSyncExternalStore } from "react";
import { ADVANCED_STORAGE_KEY, readAdvanced, writeAdvanced } from "../lib/advancedTools";

// One module-level value for every screen (the switch lives in the Tài khoản sheet, the Studio
// reads it): changing it updates every reader at once, and other tabs follow through "storage".

function storage(): Storage | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null;
  }
}

let current = readAdvanced(storage());
const listeners = new Set<() => void>();

function emit() {
  for (const l of listeners) l();
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  const onStorage = (e: StorageEvent) => {
    if (e.key !== null && e.key !== ADVANCED_STORAGE_KEY) return;
    const next = readAdvanced(storage());
    if (next !== current) {
      current = next;
      emit();
    }
  };
  window.addEventListener("storage", onStorage);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", onStorage);
  };
}

/** Turns the advanced tools on or off (kept in memory even when storage refuses). */
export function setAdvancedTools(on: boolean): void {
  writeAdvanced(storage(), on);
  if (on === current) return;
  current = on;
  emit();
}

/** Whether the advanced tools (prompt preview, token estimates, generation stats) are shown. */
export function useAdvancedTools(): [boolean, (on: boolean) => void] {
  const on = useSyncExternalStore(subscribe, () => current, () => false);
  return [on, setAdvancedTools];
}
