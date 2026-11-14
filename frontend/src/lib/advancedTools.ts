// The "Công cụ nâng cao" switch (Tài khoản → Nâng cao, Phase 3b): shows the Studio prompt preview,
// token estimates and generation stats. Off by default; stored per browser in localStorage
// ("lyris.advanced"). Storage may be missing or throw (private mode): every access is guarded and
// the app works with the switch off. Pure, no React; the hook is hooks/useAdvancedTools.ts.
import type { KeyValueStore } from "./legacyStorage.ts";

export const ADVANCED_STORAGE_KEY = "lyris.advanced";

/** "1" (or "true") is on; anything else, including nothing, is off. */
export function parseAdvanced(value: string | null | undefined): boolean {
  return value === "1" || value === "true";
}

/** Reads the switch; false when storage is unavailable or throws. */
export function readAdvanced(store: Pick<KeyValueStore, "getItem"> | null | undefined): boolean {
  if (!store) return false;
  try {
    return parseAdvanced(store.getItem(ADVANCED_STORAGE_KEY));
  } catch {
    return false;
  }
}

/** Writes the switch (off removes the key); returns false when storage refused. */
export function writeAdvanced(store: Pick<KeyValueStore, "setItem" | "removeItem"> | null | undefined, on: boolean): boolean {
  if (!store) return false;
  try {
    if (on) store.setItem(ADVANCED_STORAGE_KEY, "1");
    else store.removeItem(ADVANCED_STORAGE_KEY);
    return true;
  } catch {
    return false;
  }
}
