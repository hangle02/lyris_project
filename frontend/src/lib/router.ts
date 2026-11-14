// Hash router nhỏ cho Lyris: "#/" (Tương tác), "#/explore", "#/chat/12", "#/studio", "#/studio/new",
// "#/studio/12", "#/personas", "#/character/12", "#/character/template/<slug>", "#/me", "#/u/<handle>",
// "#/login", "#/signup?code=LYR-…", "#/admin" (Phase 4b), "#/privacy", "#/terms" (ra mắt) và "#/new-story?card=12" cũ (chuyển sang profile nhân vật). Không cần thư viện; mọi đường dẫn lạ
// đưa về hub.
import { useSyncExternalStore } from "react";
import { formatInvite, normalizeCode } from "./inviteCode.ts";

export type Route =
  /** "#/": Tương tác, lớp 1 (danh sách story). Also "#/chat" without an id. */
  | { name: "hub" }
  /** "#/explore": Khám phá. */
  | { name: "explore" }
  /**
   * "#/chat/12": the roleplay workspace. parseRoute only ever returns a number here; `null` is kept in
   * the type for older callers and links to the hub ("#/").
   */
  | { name: "chat"; storyId: number | null }
  | { name: "studio" }
  /** null = new card (editor), "#/studio/new" */
  | { name: "card"; cardId: number | null }
  | { name: "personas" }
  /**
   * "#/new-story?card=12": old links only. App redirects it to the character's profile with the
   * start sheet open ("#/character/12?start=1"); without a card, to Khám phá.
   */
  | { name: "newStory"; cardId: number | null }
  /**
   * Read-only character profile: "#/character/12" (a card of the user, installed templates included)
   * or "#/character/template/ha-vy" (a template not installed yet). `start` ("?start=1") opens the
   * "Bước vào câu chuyện" sheet on arrival.
   */
  | { name: "character"; target: CharacterTarget; start: boolean }
  /**
   * Account profile (docs/accounts.md §5): "#/me" is the current account (`handle: null`);
   * "#/u/<handle>" is someone's public profile (handle lowercased, without "@").
   */
  | { name: "profile"; handle: string | null }
  /** Phase 4b (docs/auth.md §7.2): "#/login". Signed in, the app sends it to the hub. */
  | { name: "login" }
  /**
   * "#/signup?code=LYR-...": create an account with an invite. `code` is normalised (lib/inviteCode),
   * null when missing or not a code. The page drops it from the address bar once read.
   */
  | { name: "signup"; code: string | null }
  /** "#/admin": "Quản lý tài khoản", owner only (a member is sent to the hub). */
  | { name: "admin" }
  /**
   * "#/privacy" and "#/terms" (docs/compliance.md §3): the Privacy Policy and the Terms. Open to
   * everyone, signed in or not, also before the owner setup.
   */
  | { name: "legal"; doc: LegalDocName };

/** The two legal pages. */
export type LegalDocName = "terms" | "privacy";

/** Whose profile "#/character/..." shows: a saved card, or a template by slug. */
export type CharacterTarget = { kind: "card"; id: number } | { kind: "template"; slug: string };

export type RouteName = Route["name"];

const DEFAULT_ROUTE: Route = { name: "hub" };

/** Positive integer id, or null (rejects "1.5", "-3", "0x1", "1e3", ""). */
function parseId(text: string | null | undefined): number | null {
  if (!text || !/^\d{1,15}$/.test(text)) return null;
  const n = Number(text);
  return Number.isSafeInteger(n) && n > 0 ? n : null;
}

/**
 * Handle in a "#/u/<handle>" path: "@" prefix dropped, lowercased (handles ignore case). Only the
 * characters a handle can hold (a-z 0-9 _ .) and at most 30 of them; anything else -> null. The full
 * rules (length 3+, no dot at either end) are checked by the profile page and the backend.
 */
function parseHandle(text: string | undefined): string | null {
  if (text === undefined) return null;
  const h = text.trim().replace(/^@/, "").toLowerCase();
  return /^[a-z0-9_.]{1,30}$/.test(h) ? h : null;
}

/** Template slug ("ha-vy", "morwenna-penrose"): lowercase letters, digits, "-" and "_", at most 64. */
function parseSlug(text: string | undefined): string | null {
  if (text === undefined) return null;
  const s = text.trim().toLowerCase();
  return /^[a-z0-9][a-z0-9_-]{0,63}$/.test(s) ? s : null;
}

/** "?start=1" (also "true"/"yes"): open the start sheet on arrival. */
function parseFlag(value: string | null): boolean {
  return value !== null && /^(1|true|yes)$/i.test(value.trim());
}

function safeDecode(s: string): string {
  try {
    return decodeURIComponent(s);
  } catch {
    return s;
  }
}

/** Parses a location hash ("#/studio/12", "/studio/12" or "studio/12"). Unknown -> hub. */
export function parseRoute(hash: string): Route {
  let h = (hash ?? "").trim();
  if (h.startsWith("#")) h = h.slice(1);
  const qAt = h.indexOf("?");
  const path = qAt >= 0 ? h.slice(0, qAt) : h;
  const params = new URLSearchParams(qAt >= 0 ? h.slice(qAt + 1) : "");
  const parts = path
    .split("/")
    .filter((p) => p.length > 0)
    .map(safeDecode);

  const [head, second, ...rest] = parts;
  if (head === "character") {
    const start = parseFlag(params.get("start"));
    if (second === "template" && rest.length === 1) {
      const slug = parseSlug(rest[0]);
      return slug === null ? DEFAULT_ROUTE : { name: "character", target: { kind: "template", slug }, start };
    }
    const id = rest.length === 0 ? parseId(second) : null;
    return id === null ? DEFAULT_ROUTE : { name: "character", target: { kind: "card", id }, start };
  }
  if (rest.length > 0) return DEFAULT_ROUTE;

  switch (head) {
    case undefined:
      return DEFAULT_ROUTE;
    case "explore":
      return second === undefined ? { name: "explore" } : DEFAULT_ROUTE;
    case "chat": {
      const id = parseId(second);
      return id === null ? DEFAULT_ROUTE : { name: "chat", storyId: id };
    }
    case "studio": {
      if (second === undefined) return { name: "studio" };
      if (second === "new") return { name: "card", cardId: null };
      const id = parseId(second);
      return id === null ? { name: "studio" } : { name: "card", cardId: id };
    }
    case "personas":
      return second === undefined ? { name: "personas" } : DEFAULT_ROUTE;
    case "new-story":
      return second === undefined ? { name: "newStory", cardId: parseId(params.get("card")) } : DEFAULT_ROUTE;
    case "me":
      return second === undefined ? { name: "profile", handle: null } : DEFAULT_ROUTE;
    case "login":
      return second === undefined ? { name: "login" } : DEFAULT_ROUTE;
    case "signup":
      return second === undefined ? { name: "signup", code: normalizeCode(params.get("code")) } : DEFAULT_ROUTE;
    case "admin":
      return second === undefined ? { name: "admin" } : DEFAULT_ROUTE;
    case "privacy":
    case "terms":
      return second === undefined ? { name: "legal", doc: head } : DEFAULT_ROUTE;
    case "u": {
      const handle = parseHandle(second);
      return handle === null ? DEFAULT_ROUTE : { name: "profile", handle };
    }
    default:
      return DEFAULT_ROUTE;
  }
}

/** Hash for a route, e.g. "#/studio/12". parseRoute(routeHref(r)) gives r back (a chat without id gives the hub). */
export function routeHref(r: Route): string {
  switch (r.name) {
    case "hub":
      return "#/";
    case "explore":
      return "#/explore";
    case "chat":
      return r.storyId === null ? "#/" : `#/chat/${r.storyId}`;
    case "studio":
      return "#/studio";
    case "card":
      return r.cardId === null ? "#/studio/new" : `#/studio/${r.cardId}`;
    case "personas":
      return "#/personas";
    case "newStory":
      return r.cardId === null ? "#/new-story" : `#/new-story?card=${r.cardId}`;
    case "profile":
      return r.handle === null ? "#/me" : `#/u/${encodeURIComponent(r.handle)}`;
    case "login":
      return "#/login";
    case "signup":
      return r.code === null ? "#/signup" : `#/signup?code=${formatInvite(r.code)}`;
    case "admin":
      return "#/admin";
    case "legal":
      return r.doc === "privacy" ? "#/privacy" : "#/terms";
    case "character": {
      const path =
        r.target.kind === "card" ? `#/character/${r.target.id}` : `#/character/template/${encodeURIComponent(r.target.slug)}`;
      return r.start ? `${path}?start=1` : path;
    }
  }
}

/** The profile route of a card ("#/character/12"), optionally with the start sheet open. */
export function characterRoute(cardId: number, start = false): Route {
  return { name: "character", target: { kind: "card", id: cardId }, start };
}

/** The profile route of a template not installed yet ("#/character/template/ha-vy"). */
export function templateRoute(slug: string, start = false): Route {
  return { name: "character", target: { kind: "template", slug }, start };
}

/**
 * Where an old "#/new-story" link goes now: with a card, that character's profile with the start
 * sheet open; without one, Khám phá (pick a character there). Null for any other route.
 */
export function legacyRedirect(r: Route): Route | null {
  if (r.name !== "newStory") return null;
  return r.cardId === null ? { name: "explore" } : characterRoute(r.cardId, true);
}

/** The three tabs of the floating bar, or null on screens that hide it (chat, editor, personas, new story). */
export type TabName = "explore" | "hub" | "studio";

export function tabOf(r: Route): TabName | null {
  switch (r.name) {
    case "hub":
    case "explore":
    case "studio":
      return r.name;
    default:
      return null;
  }
}

/** Normalizes "#/x", "/x" or "x" to "#/x". */
export function toHash(target: Route | string): string {
  if (typeof target !== "string") return routeHref(target);
  let h = target.trim();
  if (h.startsWith("#")) h = h.slice(1);
  if (!h.startsWith("/")) h = `/${h}`;
  return `#${h}`;
}

/** Goes to a route (adds a history entry). Same hash -> no-op. */
export function navigate(r: Route | string): void {
  const hash = toHash(r);
  if (window.location.hash === hash) return;
  window.location.hash = hash;
}

/**
 * Rewrites the current hash without a history entry (e.g. "#/new-story" -> "#/chat/12" after the
 * story is created), so Back does not bounce. Notifies useRoute subscribers.
 */
export function replaceRoute(r: Route | string): void {
  const hash = toHash(r);
  if (window.location.hash === hash) return;
  const url = `${window.location.pathname}${window.location.search}${hash}`;
  window.history.replaceState(window.history.state, "", url);
  // replaceState does not fire hashchange.
  window.dispatchEvent(new HashChangeEvent("hashchange"));
}

/**
 * Navigation guards (the Studio editor's "unsaved changes" prompt) run BEFORE any useRoute subscriber
 * hears about a hash change. They must: when a subscriber re-renders first, React can unmount the
 * guarded page (and remove its own window listeners) before the browser calls them — a real link click
 * or the Back button then left the page without asking. A guard returns false when it cancelled the
 * navigation (it has put the old hash back); subscribers are then not notified.
 */
type NavigationGuard = () => boolean;
const guards = new Set<NavigationGuard>();
const subscribers = new Set<() => void>();

/** Registers a guard; returns the function that removes it. */
export function addNavigationGuard(guard: NavigationGuard): () => void {
  guards.add(guard);
  return () => {
    guards.delete(guard);
  };
}

/** One hash change: guards first (any false cancels), then every subscriber. Exported for tests. */
export function runNavigation(): void {
  for (const guard of [...guards]) if (!guard()) return;
  for (const onChange of [...subscribers]) onChange();
}

/** useRoute's subscription (useSyncExternalStore). Exported for tests. */
export function subscribeRoute(onChange: () => void): () => void {
  if (subscribers.size === 0) {
    window.addEventListener("hashchange", runNavigation);
    window.addEventListener("popstate", runNavigation);
  }
  subscribers.add(onChange);
  return () => {
    subscribers.delete(onChange);
    if (subscribers.size === 0) {
      window.removeEventListener("hashchange", runNavigation);
      window.removeEventListener("popstate", runNavigation);
    }
  };
}

function getHash(): string {
  return window.location.hash;
}

function getServerHash(): string {
  return "";
}

// Cache so the same hash gives the same Route object (stable for effects/memo).
let cachedHash: string | null = null;
let cachedRoute: Route = DEFAULT_ROUTE;

function routeFor(hash: string): Route {
  if (hash !== cachedHash) {
    cachedHash = hash;
    cachedRoute = parseRoute(hash);
  }
  return cachedRoute;
}

/** Current route; re-renders on hashchange. */
export function useRoute(): Route {
  const hash = useSyncExternalStore(subscribeRoute, getHash, getServerHash);
  return routeFor(hash);
}

/** True when two routes point at the same screen. */
export function sameRoute(a: Route, b: Route): boolean {
  return routeHref(a) === routeHref(b);
}
