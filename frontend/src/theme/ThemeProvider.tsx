import { createContext, useCallback, useContext, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { THEME_META_COLORS, THEME_STORAGE_KEY, oppositeTheme, parseTheme, resolveTheme, themeFromSearch } from "./theme";
import type { Theme } from "./theme";

/** Where the current theme comes from: the person's toggle, the system setting, or `?theme=` in the URL. */
export type ThemeSource = "stored" | "system" | "url";

export interface ThemeContextValue {
  theme: Theme;
  source: ThemeSource;
  /** Choose a theme and remember it (localStorage "lyris.theme"). */
  setTheme: (theme: Theme) => void;
  /** Switch to the other theme and remember it. */
  toggleTheme: () => void;
  /** Forget the stored choice and follow the system setting again. */
  followSystem: () => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

const LIGHT_QUERY = "(prefers-color-scheme: light)";
const SWITCH_CLASS = "theme-switching";
const SWITCH_MS = 550;

function readStored(): string | null {
  try {
    return window.localStorage.getItem(THEME_STORAGE_KEY);
  } catch {
    return null;
  }
}

function writeStored(theme: Theme | null) {
  try {
    if (theme) window.localStorage.setItem(THEME_STORAGE_KEY, theme);
    else window.localStorage.removeItem(THEME_STORAGE_KEY);
  } catch {
    // storage unavailable (private mode): the choice lasts for this visit only
  }
}

function systemPrefersLight(): boolean {
  return typeof window.matchMedia === "function" && window.matchMedia(LIGHT_QUERY).matches;
}

function reducedMotion(): boolean {
  return typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/** Sets html[data-theme] and the browser chrome colour. */
function applyTheme(theme: Theme) {
  const root = document.documentElement;
  if (root.dataset.theme !== theme) root.dataset.theme = theme;
  const meta = document.querySelector<HTMLMetaElement>('meta[name="theme-color"]');
  if (meta) meta.content = THEME_META_COLORS[theme];
}

function initialState(): { theme: Theme; source: ThemeSource } {
  const fromUrl = themeFromSearch(window.location.search);
  if (fromUrl) return { theme: fromUrl, source: "url" };
  const stored = parseTheme(readStored());
  if (stored) return { theme: stored, source: "stored" };
  // index.html's inline script already resolved it before first paint; trust it when present.
  const painted = parseTheme(document.documentElement.dataset.theme);
  return { theme: painted ?? resolveTheme(null, systemPrefersLight()), source: "system" };
}

/**
 * Owns the light/dark theme. index.html sets html[data-theme] before React loads (no flash); this
 * provider keeps it in sync, follows the system while the person has not chosen, and eases colours
 * for 500ms when the theme changes.
 */
export function ThemeProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState(initialState);
  const first = useRef(true);
  const timer = useRef<number | undefined>(undefined);

  useLayoutEffect(() => {
    const root = document.documentElement;
    if (first.current || reducedMotion()) {
      first.current = false;
      applyTheme(state.theme);
      return;
    }
    root.classList.add(SWITCH_CLASS);
    applyTheme(state.theme);
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => root.classList.remove(SWITCH_CLASS), SWITCH_MS);
  }, [state.theme]);

  useEffect(() => () => window.clearTimeout(timer.current), []);

  // Follow the system setting while the person has not picked a theme.
  useEffect(() => {
    if (state.source !== "system" || typeof window.matchMedia !== "function") return;
    const mq = window.matchMedia(LIGHT_QUERY);
    const onChange = () => setState({ theme: mq.matches ? "light" : "dark", source: "system" });
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, [state.source]);

  // Another tab changed the stored theme.
  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key !== THEME_STORAGE_KEY) return;
      const t = parseTheme(e.newValue);
      setState(t ? { theme: t, source: "stored" } : { theme: resolveTheme(null, systemPrefersLight()), source: "system" });
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const setTheme = useCallback((theme: Theme) => {
    writeStored(theme);
    setState({ theme, source: "stored" });
  }, []);

  const toggleTheme = useCallback(() => {
    setState((s) => {
      const theme = oppositeTheme(s.theme);
      writeStored(theme);
      return { theme, source: "stored" };
    });
  }, []);

  const followSystem = useCallback(() => {
    writeStored(null);
    setState({ theme: resolveTheme(null, systemPrefersLight()), source: "system" });
  }, []);

  const value = useMemo<ThemeContextValue>(
    () => ({ theme: state.theme, source: state.source, setTheme, toggleTheme, followSystem }),
    [state.theme, state.source, setTheme, toggleTheme, followSystem],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

/** Current theme and its setters. Must be used under ThemeProvider (main.tsx wraps the app). */
export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme cần nằm trong ThemeProvider");
  return ctx;
}
