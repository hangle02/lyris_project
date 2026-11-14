// Usage tracking on the client (docs/tracking-plan.md §7). Only what happens in the UI alone is sent
// from here (opening Khám phá, tapping a vibe chip, revealing a thought...); everything the server
// knows is recorded on the server. Pure core (createTracker), tested in track.test.ts; the browser glue
// (fetch with keepalive, pagehide, the app-wide instance) is at the end of the file.
//
// Hard rules, enforced here AND on the server:
// - Only events of the client whitelist below (a copy of the backend registry's client events, kept in
//   sync by a test that reads backend/lyris/analytics/events.py).
// - Every property is an enum string from a fixed list, a boolean or a bounded integer. Anything else
//   (free text of any kind, unknown keys, wrong types) drops the whole event: no text can ever leave.
// - Nothing is sent while the account's choice is unknown, after "Chia sẻ dữ liệu sử dụng ẩn danh" is
//   turned off, or when the browser asks not to be tracked (Global Privacy Control).
//
// Identity: the server owns it. The device id is the HttpOnly `lyris_anon` cookie and visits are split
// on the server after 30 minutes idle, so this client keeps no id of its own (the API refuses extra
// fields, and a second id in localStorage would only be one more thing to clear).

/** Property rule: enum strings, a boolean, or an integer in [lo, hi]. */
export type PropRule = { kind: "enum"; values: readonly string[] } | { kind: "bool" } | { kind: "int"; lo: number; hi: number };

export interface ClientEventSpec {
  props: Readonly<Record<string, PropRule>>;
  required?: readonly string[];
  /** Allowed before signing in (only an anonymous device id is attached). */
  preAuth?: boolean;
  /** Carries the open story's id (the server checks the story is the sender's and fills `mode`). */
  story?: boolean;
}

const e = (...values: string[]): PropRule => ({ kind: "enum", values });
const BOOL: PropRule = { kind: "bool" };
const int = (lo: number, hi: number): PropRule => ({ kind: "int", lo, hi });

export const VIBE_CODES = ["chua_lanh", "diu_dang", "bi_an_noi_tam", "tinh_dau", "other_template", "other_tag"] as const;
export type VibeCode = (typeof VIBE_CODES)[number];
export const CARD_SOURCES = ["own", "template", "public"] as const;
export type CardSource = (typeof CARD_SOURCES)[number];
export const PROFILE_FROM = ["explore", "library", "profile", "story", "link"] as const;
export type ProfileFrom = (typeof PROFILE_FROM)[number];

/** The client events of the backend registry (lyris/analytics/events.py, sources "client"). */
export const CLIENT_EVENTS = {
  app_opened: { props: { display_mode: e("standalone", "browser"), authed: BOOL }, preAuth: true },
  signup_viewed: { props: { has_invite_code: BOOL }, preAuth: true },
  explore_viewed: { props: {} },
  vibe_filter_used: { props: { vibe: e(...VIBE_CODES), position: int(1, 20) }, required: ["vibe"] },
  character_profile_viewed: { props: { source: e(...CARD_SOURCES), from: e(...PROFILE_FROM) }, required: ["source"] },
  story_start_clicked: { props: { source: e(...CARD_SOURCES) }, required: ["source"] },
  suggestion_used: { props: { position: int(1, 3) }, required: ["position"], story: true },
  thought_revealed: { props: {}, story: true },
  heart_drawer_opened: { props: {}, story: true },
  events_timeline_opened: { props: {}, story: true },
  // No content_reported: reports (of a reply or of a public character) are recorded by the server,
  // detached from the account, so nobody can tell who reported.
} as const satisfies Record<string, ClientEventSpec>;

export type ClientEventName = keyof typeof CLIENT_EVENTS;
export type PropValue = string | boolean | number;
export type Props = Readonly<Record<string, PropValue>>;

/** What goes over the wire (one item of POST /api/events `events`). */
export interface WireEvent {
  name: ClientEventName;
  props?: Record<string, PropValue>;
  story_id?: number;
}

export const MAX_BATCH = 20;
/** Events waiting while the account's choice is still unknown (oldest dropped beyond this). */
export const MAX_QUEUE = 60;
export const FLUSH_DELAY_MS = 4000;
/** The same event (name, props, story) twice within this window counts once (double mounts, double taps). */
export const DEDUPE_MS = 1000;

function checkProp(rule: PropRule, value: unknown): boolean {
  switch (rule.kind) {
    case "enum":
      return typeof value === "string" && rule.values.includes(value);
    case "bool":
      return typeof value === "boolean";
    case "int":
      return typeof value === "number" && Number.isInteger(value) && value >= rule.lo && value <= rule.hi;
  }
}

/**
 * The event as it may be sent, or null when anything about it is off (unknown name or key, a value
 * outside its rule, a missing required key, a bad story id). Never repairs: a dropped event is better
 * than a guessed one.
 */
export function buildEvent(name: string, props?: Readonly<Record<string, unknown>> | null, storyId?: number | null): WireEvent | null {
  if (!Object.prototype.hasOwnProperty.call(CLIENT_EVENTS, name)) return null;
  const spec: ClientEventSpec = CLIENT_EVENTS[name as ClientEventName];
  const clean: Record<string, PropValue> = {};
  for (const [key, value] of Object.entries(props ?? {})) {
    if (value === undefined) continue;
    const rule = Object.prototype.hasOwnProperty.call(spec.props, key) ? spec.props[key] : undefined;
    if (!rule || !checkProp(rule, value)) return null;
    clean[key] = value as PropValue;
  }
  for (const key of spec.required ?? []) if (!(key in clean)) return null;
  const out: WireEvent = { name: name as ClientEventName };
  if (Object.keys(clean).length > 0) out.props = clean;
  if (spec.story) {
    if (storyId !== undefined && storyId !== null) {
      if (!Number.isSafeInteger(storyId) || storyId <= 0) return null;
      out.story_id = storyId;
    }
  } else if (storyId !== undefined && storyId !== null) {
    return null;
  }
  return out;
}

/** Who is using the app, as far as tracking cares. `null` = not known yet (hold events). */
export interface Consent {
  /** Signed in (true), signed out (false), unknown (null). */
  signedIn: boolean | null;
  /** The account turned usage sharing off (true), on (false), unknown (null). Ignored signed out. */
  optOut: boolean | null;
}

export type ConsentDecision = "send" | "hold" | "drop";

/** What to do with an event under the current consent. */
export function decide(name: ClientEventName, consent: Consent, gpc: boolean): ConsentDecision {
  if (gpc) return "drop";
  if (consent.signedIn === null) return "hold";
  if (!consent.signedIn) return (CLIENT_EVENTS[name] as ClientEventSpec).preAuth ? "send" : "drop";
  if (consent.optOut === null) return "hold";
  return consent.optOut ? "drop" : "send";
}

export interface TrackerDeps {
  /** Sends one batch (≤ MAX_BATCH). Errors are swallowed by the tracker. */
  send: (events: WireEvent[], opts: { keepalive: boolean }) => Promise<unknown> | unknown;
  now: () => number;
  setTimer: (fn: () => void, ms: number) => unknown;
  clearTimer: (handle: unknown) => void;
  /** The browser sends Global Privacy Control (`navigator.globalPrivacyControl`). */
  gpc?: () => boolean;
}

export interface Tracker {
  track: (name: ClientEventName, props?: Props | null, storyId?: number | null) => boolean;
  setConsent: (next: Partial<Consent>) => void;
  /** Sends what is queued now. `keepalive` for a page being hidden or closed. */
  flush: (keepalive?: boolean) => void;
  /** Events waiting (tests, debugging). */
  pending: () => readonly WireEvent[];
  consent: () => Consent;
}

/**
 * Batches events: sends FLUSH_DELAY_MS after the first queued one, at once when MAX_BATCH are waiting,
 * and on flush() (page hidden). While the account's choice is unknown, events wait (up to MAX_QUEUE);
 * turning sharing off drops everything waiting.
 */
export function createTracker(deps: TrackerDeps): Tracker {
  let consent: Consent = { signedIn: null, optOut: null };
  let queue: { event: WireEvent; at: number; key: string }[] = [];
  let timer: unknown = null;
  const recent = new Map<string, number>();
  const gpc = () => {
    try {
      return deps.gpc?.() === true;
    } catch {
      return false;
    }
  };

  const cancelTimer = () => {
    if (timer !== null) deps.clearTimer(timer);
    timer = null;
  };

  /** Re-checks the queue against the consent: drops what may no longer be sent. */
  const prune = () => {
    const g = gpc();
    queue = queue.filter((q) => decide(q.event.name, consent, g) !== "drop");
  };

  const sendable = () => {
    const g = gpc();
    return queue.filter((q) => decide(q.event.name, consent, g) === "send");
  };

  const flush = (keepalive = false) => {
    cancelTimer();
    prune();
    const ready = sendable();
    if (ready.length === 0) return;
    const sent = new Set(ready);
    queue = queue.filter((q) => !sent.has(q));
    for (let i = 0; i < ready.length; i += MAX_BATCH) {
      const batch = ready.slice(i, i + MAX_BATCH).map((q) => q.event);
      try {
        const p = deps.send(batch, { keepalive });
        if (p && typeof (p as Promise<unknown>).catch === "function") (p as Promise<unknown>).catch(() => undefined);
      } catch {
        // Tracking never breaks the app.
      }
    }
  };

  const schedule = () => {
    if (sendable().length >= MAX_BATCH) {
      flush(false);
      return;
    }
    if (timer === null && sendable().length > 0) timer = deps.setTimer(() => {
      timer = null;
      flush(false);
    }, FLUSH_DELAY_MS);
  };

  const track: Tracker["track"] = (name, props, storyId) => {
    const event = buildEvent(name, props, storyId);
    if (!event) return false;
    if (decide(event.name, consent, gpc()) === "drop") return false;
    const now = deps.now();
    const key = JSON.stringify(event);
    const last = recent.get(key);
    if (last !== undefined && now - last < DEDUPE_MS) return false;
    recent.set(key, now);
    if (recent.size > 200) for (const [k, t] of recent) if (now - t >= DEDUPE_MS) recent.delete(k);
    queue.push({ event, at: now, key });
    if (queue.length > MAX_QUEUE) queue = queue.slice(queue.length - MAX_QUEUE);
    schedule();
    return true;
  };

  const setConsent: Tracker["setConsent"] = (next) => {
    consent = { ...consent, ...next };
    prune();
    if (queue.length === 0) cancelTimer();
    else schedule();
  };

  return {
    track,
    setConsent,
    flush,
    pending: () => queue.map((q) => q.event),
    consent: () => consent,
  };
}

// ---- small mappings used by the screens (pure) ----

const BASE_VIBE_CODES: Readonly<Record<string, VibeCode>> = {
  "chữa lành": "chua_lanh",
  "dịu dàng": "diu_dang",
  "bí ẩn nội tâm": "bi_an_noi_tam",
  "tình đầu": "tinh_dau",
};

/**
 * Code of a vibe chip, never its text: the four DESIGN.md vibes by name, any other vibe of a Lyris
 * template "other_template", a tag of someone's card "other_tag". `normalize` is the Explore page's
 * tag normalizer (lowercase, no emoji).
 */
export function vibeCode(tag: string, templateVibes: readonly string[], normalize: (t: string) => string): VibeCode {
  const n = normalize(tag);
  const base = BASE_VIBE_CODES[n];
  if (base) return base;
  return templateVibes.some((v) => normalize(v) === n) ? "other_template" : "other_tag";
}

/** 1-based position of a chip, capped to the registry's range (1..20). */
export function chipPosition(index: number): number {
  return Math.min(20, Math.max(1, Math.floor(index) + 1));
}

/** Where a character profile was opened from, by the screen shown before it ("link" when none). */
export function profileFrom(previousRoute: string | null): ProfileFrom {
  switch (previousRoute) {
    case "explore":
      return "explore";
    case "hub":
    case "studio":
    case "card":
      return "library";
    case "profile":
      return "profile";
    case "chat":
      return "story";
    default:
      return "link";
  }
}

/** `display_mode` of app_opened: installed PWA ("standalone") or a browser tab. */
export function displayMode(standaloneMedia: boolean, iosStandalone: boolean): "standalone" | "browser" {
  return standaloneMedia || iosStandalone ? "standalone" : "browser";
}

// ---- browser glue (the app-wide tracker) ----

const ENDPOINT = "/api/events";

function sendWithFetch(events: WireEvent[], opts: { keepalive: boolean }): Promise<unknown> {
  // fetch with keepalive, not navigator.sendBeacon: a beacon cannot carry the CSRF header (X-Lyris)
  // every write needs, and keepalive survives the page closing just the same.
  return fetch(ENDPOINT, {
    method: "POST",
    credentials: "same-origin",
    keepalive: opts.keepalive,
    headers: { "X-Lyris": "1", "Content-Type": "application/json" },
    body: JSON.stringify({ events }),
  });
}

function browserGpc(): boolean {
  if (typeof navigator === "undefined") return false;
  return (navigator as Navigator & { globalPrivacyControl?: boolean }).globalPrivacyControl === true;
}

let instance: Tracker | null = null;
let previousRoute: string | null = null;
let currentRoute: string | null = null;
let currentStory: number | null = null;

function tracker(): Tracker | null {
  if (instance) return instance;
  if (typeof window === "undefined" || typeof fetch !== "function") return null;
  instance = createTracker({
    send: sendWithFetch,
    now: () => Date.now(),
    setTimer: (fn, ms) => window.setTimeout(fn, ms),
    clearTimer: (h) => window.clearTimeout(h as number),
    gpc: browserGpc,
  });
  const hide = () => instance?.flush(true);
  window.addEventListener("pagehide", hide);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") hide();
  });
  return instance;
}

/** Records a client event (dropped silently when not allowed). Never throws. */
export function track(name: ClientEventName, props?: Props | null): void {
  try {
    tracker()?.track(name, props ?? null, null);
  } catch {
    // never in the way
  }
}

/** A story event of the open story (ChatPage sets it); outside a story nothing is recorded. */
export function trackInStory(name: "suggestion_used" | "thought_revealed" | "heart_drawer_opened" | "events_timeline_opened", props?: Props | null): void {
  if (currentStory === null) return;
  try {
    tracker()?.track(name, props ?? null, currentStory);
  } catch {
    // never in the way
  }
}

/** The story open on screen (null when it closes). */
export function setTrackedStory(storyId: number | null): void {
  currentStory = storyId;
}

/** Who is signed in and what they chose about usage sharing (App keeps it current). */
export function setTrackingConsent(next: Partial<Consent>): void {
  tracker()?.setConsent(next);
}

/** The screen now shown (App calls it on each route change), for `from` of character_profile_viewed. */
export function noteRoute(name: string): void {
  if (name === currentRoute) return;
  previousRoute = currentRoute;
  currentRoute = name;
}

/** The screen shown before the current one, or null on the first screen of this visit. */
export function previousRouteName(): string | null {
  return previousRoute;
}
