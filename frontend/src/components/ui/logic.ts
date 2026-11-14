// Pure helpers behind the UI primitives (tested in logic.test.ts).

/** Joins class names, skipping falsy values. */
export function cx(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

/** First letter (grapheme-ish) of a name, uppercased; "?" when empty. */
export function initialOf(name: string): string {
  const first = Array.from(name.trim())[0];
  return first ? first.toLocaleUpperCase("vi-VN") : "?";
}

/**
 * Corner radius of a portrait avatar for its size: about 30% of the side, kept inside the app's
 * soft radius family (control 14px at 48px, card 20px from about 66px, never under 8px).
 */
export function portraitRadius(size: number): number {
  return Math.round(Math.min(20, Math.max(8, size * 0.3)));
}

/** Font size of an avatar's initial for its diameter. */
export function initialFontSize(size: number): number {
  return Math.max(11, Math.round(size * 0.42));
}

/**
 * Index to focus when Tab cycles inside a trapped container with `count` focusable elements.
 * `current` is the index of the focused element, or -1 when focus is outside the list.
 */
export function nextFocusIndex(current: number, count: number, backwards: boolean): number {
  if (count <= 0) return -1;
  if (current < 0) return backwards ? count - 1 : 0;
  if (backwards) return current === 0 ? count - 1 : current - 1;
  return current === count - 1 ? 0 : current + 1;
}

/** Index of the option an arrow / Home / End key moves to in a radio group, or null for other keys. */
export function radioKeyTarget(key: string, current: number, count: number): number | null {
  if (count <= 0) return null;
  const from = current < 0 ? 0 : current;
  switch (key) {
    case "ArrowRight":
    case "ArrowDown":
      return (from + 1) % count;
    case "ArrowLeft":
    case "ArrowUp":
      return (from - 1 + count) % count;
    case "Home":
      return 0;
    case "End":
      return count - 1;
    default:
      return null;
  }
}

/** Clamps a meter value into 0..max and returns its share in percent (0-100). */
export function meterPercent(value: number, max = 100): number {
  if (!Number.isFinite(value) || !Number.isFinite(max) || max <= 0) return 0;
  return Math.min(100, Math.max(0, (value / max) * 100));
}

/**
 * The stack of open overlays (Modal, Drawer). Only the top one answers Escape and traps focus;
 * the page scroll stays locked while the stack is not empty.
 */
export class OverlayStack {
  private ids: string[] = [];

  push(id: string): void {
    this.remove(id);
    this.ids.push(id);
  }

  remove(id: string): void {
    this.ids = this.ids.filter((x) => x !== id);
  }

  isTop(id: string): boolean {
    return this.ids.length > 0 && this.ids[this.ids.length - 1] === id;
  }

  get size(): number {
    return this.ids.length;
  }
}

/**
 * Attributes of a switch. `busy` (its value is being saved) keeps the button focusable: a native
 * `disabled` would blur the focused switch (focus falls to <body>, the screen reader loses its place),
 * so it is `aria-disabled` and clicks are ignored instead. `disabled` stays a real disabled button.
 */
export function switchState(disabled: boolean | undefined, busy: boolean | undefined) {
  return {
    disabled: !!disabled,
    ariaDisabled: !disabled && busy ? true : undefined,
    ariaBusy: busy ? true : undefined,
    inert: !!disabled || !!busy,
  };
}
