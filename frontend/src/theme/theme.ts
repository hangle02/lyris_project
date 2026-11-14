// Pure theme logic shared by ThemeProvider (and mirrored by the inline script in index.html).

export type Theme = "dark" | "light";

/** localStorage key holding the theme the person chose with the toggle. Absent = follow the system. */
export const THEME_STORAGE_KEY = "lyris.theme";

/** `<meta name="theme-color">` per theme: the app ground (`bg` token). */
export const THEME_META_COLORS: Readonly<Record<Theme, string>> = {
  dark: "#130D14",
  light: "#FAF5EE",
};

/** A stored or URL value as a Theme, or null when it is anything else. */
export function parseTheme(value: unknown): Theme | null {
  return value === "dark" || value === "light" ? value : null;
}

/**
 * The theme to show: an explicit override (e.g. `?theme=light` for screenshots) first, then the
 * person's stored choice, then the system preference. With no preference at all, dark.
 */
export function resolveTheme(
  stored: string | null | undefined,
  systemPrefersLight: boolean,
  override?: string | null,
): Theme {
  return parseTheme(override) ?? parseTheme(stored) ?? (systemPrefersLight ? "light" : "dark");
}

export function oppositeTheme(theme: Theme): Theme {
  return theme === "dark" ? "light" : "dark";
}

/** Reads `?theme=` from a location search string ("" or "?a=b&theme=light"). */
export function themeFromSearch(search: string): Theme | null {
  try {
    return parseTheme(new URLSearchParams(search).get("theme"));
  } catch {
    return null;
  }
}
