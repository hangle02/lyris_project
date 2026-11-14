// One-time move of browser storage from the app's former name ("nora.*") to "lyris.*".

export interface KeyValueStore {
  readonly length: number;
  key(index: number): string | null;
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

/** Copies every "nora.*" entry to "lyris.*" (unless already set) and removes the old one. Returns how many moved. */
export function migrateLegacyKeys(store: KeyValueStore): number {
  const old: string[] = [];
  for (let i = 0; i < store.length; i++) {
    const k = store.key(i);
    if (k && k.startsWith("nora.")) old.push(k);
  }
  let moved = 0;
  for (const k of old) {
    const value = store.getItem(k);
    const target = `lyris.${k.slice("nora.".length)}`;
    if (value !== null && store.getItem(target) === null) {
      store.setItem(target, value);
      moved++;
    }
    store.removeItem(k);
  }
  return moved;
}
