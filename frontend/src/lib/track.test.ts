import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  buildEvent,
  chipPosition,
  CLIENT_EVENTS,
  createTracker,
  decide,
  DEDUPE_MS,
  displayMode,
  FLUSH_DELAY_MS,
  MAX_BATCH,
  MAX_QUEUE,
  profileFrom,
  vibeCode,
} from "./track.ts";
import type { TrackerDeps, WireEvent } from "./track.ts";

/** A fake clock, timers and transport. */
function harness(opts: { gpc?: boolean } = {}) {
  let now = 1_000_000;
  const timers: { fn: () => void; at: number; id: number }[] = [];
  let nextId = 1;
  const sent: { events: WireEvent[]; keepalive: boolean }[] = [];
  const deps: TrackerDeps = {
    send: (events, o) => {
      sent.push({ events, keepalive: o.keepalive });
      return Promise.resolve();
    },
    now: () => now,
    setTimer: (fn, ms) => {
      const id = nextId++;
      timers.push({ fn, at: now + ms, id });
      return id;
    },
    clearTimer: (h) => {
      const i = timers.findIndex((t) => t.id === h);
      if (i >= 0) timers.splice(i, 1);
    },
    gpc: () => opts.gpc === true,
  };
  const advance = (ms: number) => {
    now += ms;
    for (const t of [...timers].sort((a, b) => a.at - b.at)) {
      if (t.at <= now) {
        timers.splice(timers.indexOf(t), 1);
        t.fn();
      }
    }
  };
  return { deps, sent, advance, timers };
}

const signedIn = { signedIn: true, optOut: false } as const;

test("buildEvent: only whitelisted names, keys and values", () => {
  assert.deepEqual(buildEvent("explore_viewed"), { name: "explore_viewed" });
  assert.deepEqual(buildEvent("vibe_filter_used", { vibe: "tinh_dau", position: 4 }), {
    name: "vibe_filter_used",
    props: { vibe: "tinh_dau", position: 4 },
  });
  assert.equal(buildEvent("message_sent", { mode: "story" }), null, "server-only event");
  assert.equal(buildEvent("made_up"), null);
  assert.equal(buildEvent("__proto__"), null);
  assert.equal(buildEvent("toString"), null);
  assert.equal(buildEvent("vibe_filter_used", { vibe: "tinh_dau", position: 0 }), null, "below range");
  assert.equal(buildEvent("vibe_filter_used", { vibe: "tinh_dau", position: 2.5 }), null, "not an integer");
  assert.equal(buildEvent("vibe_filter_used", { position: 2 }), null, "required key missing");
  assert.equal(buildEvent("app_opened", { display_mode: "browser", authed: "yes" }), null, "bool as text");
  assert.equal(buildEvent("explore_viewed", { extra: true }), null, "unknown key");
  assert.equal(buildEvent("explore_viewed", undefined, 4), null, "story id on a non-story event");
  assert.equal(buildEvent("thought_revealed", undefined, -1), null);
  assert.deepEqual(buildEvent("thought_revealed", null, 12), { name: "thought_revealed", story_id: 12 });
});

test("no text can leave: any free text in a property drops the whole event", () => {
  const secrets = [
    "Anh nhớ em nhiều lắm",
    "Hạ Vy",
    "@mai",
    "mai@example.com",
    "LYR-7KQ2-M9XD-4TPA",
    "tình đầu", // a vibe's text, not its code
    "Chữa lành",
  ];
  const t = harness();
  const tracker = createTracker(t.deps);
  tracker.setConsent(signedIn);
  for (const s of secrets) {
    for (const [name, spec] of Object.entries(CLIENT_EVENTS)) {
      const keys = Object.keys(spec.props);
      for (const key of [...keys, "text", "content", "title", "name", "handle"]) {
        assert.equal(tracker.track(name as keyof typeof CLIENT_EVENTS, { [key]: s }), false, `${name}.${key}`);
      }
    }
  }
  tracker.flush();
  const wire = JSON.stringify(t.sent);
  for (const s of secrets) assert.ok(!wire.includes(s), s);
  assert.equal(tracker.pending().length, 0);
});

test("every enum value is a fixed code (snake_case ASCII), never words", () => {
  for (const spec of Object.values(CLIENT_EVENTS)) {
    for (const rule of Object.values(spec.props) as { kind: string; values?: readonly string[] }[]) {
      for (const v of rule.values ?? []) assert.match(v, /^[a-z0-9_]+$/);
    }
  }
});

test("client whitelist matches the backend registry's client events", () => {
  const py = readFileSync(new URL("../../../backend/lyris/analytics/events.py", import.meta.url), "utf8");
  const names = [...py.matchAll(/_spec\(\s*"([a-z_]+)",\s*(C|frozenset\(\{"server", "client"\}\))/g)].map((m) => m[1]).sort();
  assert.ok(names.length >= 10, "found the client events in events.py");
  assert.deepEqual(Object.keys(CLIENT_EVENTS).sort(), names);
  const preAuth = [...py.matchAll(/_spec\("([a-z_]+)"[^\n]*pre_auth=True/g)].map((m) => m[1]).sort();
  assert.deepEqual(
    Object.entries(CLIENT_EVENTS)
      .filter(([, s]) => (s as { preAuth?: boolean }).preAuth)
      .map(([n]) => n)
      .sort(),
    preAuth,
  );
  const storyScoped = [...py.matchAll(/_spec\(\s*"([a-z_]+)"[\s\S]*?\)\s*,\n/g)]
    .filter((m) => m[0].includes("story_scoped=True"))
    .map((m) => m[1])
    .sort();
  assert.deepEqual(
    Object.entries(CLIENT_EVENTS)
      .filter(([, s]) => (s as { story?: boolean }).story)
      .map(([n]) => n)
      .sort(),
    storyScoped,
  );
});

test("consent: hold while unknown, pre-sign-in events only, opt-out and GPC drop", () => {
  const signedOut = { signedIn: false, optOut: null };
  assert.equal(decide("explore_viewed", { signedIn: null, optOut: null }, false), "hold");
  assert.equal(decide("app_opened", signedOut, false), "send");
  assert.equal(decide("signup_viewed", signedOut, false), "send");
  assert.equal(decide("explore_viewed", signedOut, false), "drop");
  assert.equal(decide("explore_viewed", { signedIn: true, optOut: null }, false), "hold");
  assert.equal(decide("explore_viewed", { signedIn: true, optOut: true }, false), "drop");
  assert.equal(decide("explore_viewed", { signedIn: true, optOut: false }, false), "send");
  assert.equal(decide("app_opened", { signedIn: true, optOut: false }, true), "drop", "GPC");
});

test("opt-out: nothing is sent, and what was waiting is dropped", () => {
  const t = harness();
  const tracker = createTracker(t.deps);
  assert.equal(tracker.track("explore_viewed"), true, "held while unknown");
  tracker.track("heart_drawer_opened", null, 3);
  assert.equal(tracker.pending().length, 2);
  t.advance(FLUSH_DELAY_MS * 3);
  assert.equal(t.sent.length, 0, "unknown consent never sends");
  tracker.setConsent({ signedIn: true, optOut: true });
  assert.equal(tracker.pending().length, 0);
  assert.equal(tracker.track("explore_viewed"), false);
  tracker.flush(true);
  t.advance(FLUSH_DELAY_MS * 3);
  assert.equal(t.sent.length, 0);
  // Turned back on: new events go out again.
  tracker.setConsent({ optOut: false });
  tracker.track("explore_viewed");
  t.advance(FLUSH_DELAY_MS);
  assert.equal(t.sent.length, 1);
});

test("opt-out while events wait for the timer: they never leave", () => {
  const t = harness();
  const tracker = createTracker(t.deps);
  tracker.setConsent(signedIn);
  tracker.track("explore_viewed");
  tracker.setConsent({ optOut: true });
  t.advance(FLUSH_DELAY_MS * 2);
  tracker.flush(true);
  assert.equal(t.sent.length, 0);
});

test("GPC: the tracker never sends", () => {
  const t = harness({ gpc: true });
  const tracker = createTracker(t.deps);
  tracker.setConsent(signedIn);
  assert.equal(tracker.track("app_opened", { display_mode: "browser", authed: true }), false);
  tracker.flush(true);
  assert.equal(t.sent.length, 0);
});

test("signed out: only app_opened / signup_viewed wait for sending; signing in releases held ones", () => {
  const t = harness();
  const tracker = createTracker(t.deps);
  tracker.track("app_opened", { display_mode: "browser", authed: false });
  tracker.setConsent({ signedIn: false });
  assert.equal(tracker.track("explore_viewed"), false);
  tracker.flush();
  assert.deepEqual(t.sent[0]?.events, [{ name: "app_opened", props: { display_mode: "browser", authed: false } }]);
  // Signed in, choice not read yet: held; then read as "on": sent.
  tracker.setConsent({ signedIn: true, optOut: null });
  tracker.track("explore_viewed");
  t.advance(FLUSH_DELAY_MS * 2);
  assert.equal(t.sent.length, 1);
  tracker.setConsent({ optOut: false });
  t.advance(FLUSH_DELAY_MS);
  assert.deepEqual(t.sent[1]?.events, [{ name: "explore_viewed" }]);
});

test("batching: one request after the delay, at once at MAX_BATCH, chunks of MAX_BATCH on flush", () => {
  const t = harness();
  const tracker = createTracker(t.deps);
  tracker.setConsent(signedIn);
  tracker.track("explore_viewed");
  tracker.track("vibe_filter_used", { vibe: "chua_lanh", position: 2 });
  assert.equal(t.sent.length, 0, "not sent before the delay");
  t.advance(FLUSH_DELAY_MS - 1);
  assert.equal(t.sent.length, 0);
  t.advance(1);
  assert.equal(t.sent.length, 1);
  assert.equal(t.sent[0]?.events.length, 2);
  assert.equal(t.sent[0]?.keepalive, false);

  // MAX_BATCH distinct events: sent at once, no timer needed.
  for (let i = 0; i < MAX_BATCH; i++) tracker.track("vibe_filter_used", { vibe: "other_tag", position: i + 1 });
  assert.equal(t.sent.length, 2);
  assert.equal(t.sent[1]?.events.length, MAX_BATCH);

  // Held while unknown, then released together: split into batches of MAX_BATCH.
  const t2 = harness();
  const held = createTracker(t2.deps);
  for (let i = 0; i < 45; i++) held.track("suggestion_used", { position: (i % 3) + 1 }, i + 1);
  held.setConsent(signedIn);
  held.flush(true);
  assert.deepEqual(
    t2.sent.map((b) => b.events.length),
    [20, 20, 5],
  );
  // Page hidden: what waits goes out at once, with keepalive.
  held.track("explore_viewed");
  held.flush(true);
  assert.deepEqual(t2.sent.at(-1), { events: [{ name: "explore_viewed" }], keepalive: true });
});

test("queue is bounded while consent is unknown", () => {
  const t = harness();
  const tracker = createTracker(t.deps);
  for (let i = 0; i < MAX_QUEUE + 30; i++) tracker.track("suggestion_used", { position: 1 }, i + 1);
  assert.equal(tracker.pending().length, MAX_QUEUE);
  assert.equal(tracker.pending()[0]?.story_id, 31, "oldest dropped");
});

test("the same event twice within DEDUPE_MS counts once", () => {
  const t = harness();
  const tracker = createTracker(t.deps);
  tracker.setConsent(signedIn);
  assert.equal(tracker.track("explore_viewed"), true);
  assert.equal(tracker.track("explore_viewed"), false);
  t.advance(DEDUPE_MS);
  assert.equal(tracker.track("explore_viewed"), true);
  assert.equal(tracker.track("thought_revealed", null, 1), true, "other event");
  assert.equal(tracker.track("thought_revealed", null, 2), true, "other story");
});

test("a failing transport never throws into the app", () => {
  const t = harness();
  const tracker = createTracker({
    ...t.deps,
    send: () => {
      throw new Error("offline");
    },
  });
  tracker.setConsent(signedIn);
  tracker.track("explore_viewed");
  assert.doesNotThrow(() => tracker.flush(true));
  const rejecting = createTracker({ ...t.deps, send: () => Promise.reject(new Error("429")) });
  rejecting.setConsent(signedIn);
  rejecting.track("explore_viewed");
  assert.doesNotThrow(() => rejecting.flush());
});

test("vibe codes, chip positions, profile origin, display mode", () => {
  const norm = (s: string) => s.replace(/✨/g, "").trim().toLowerCase();
  assert.equal(vibeCode("✨ Chữa lành", [], norm), "chua_lanh");
  assert.equal(vibeCode("Tình đầu", [], norm), "tinh_dau");
  assert.equal(vibeCode("Bí ẩn nội tâm", [], norm), "bi_an_noi_tam");
  assert.equal(vibeCode("Dịu dàng", [], norm), "diu_dang");
  assert.equal(vibeCode("Cornwall", ["cornwall"], norm), "other_template");
  assert.equal(vibeCode("Tag riêng của ai đó", ["cornwall"], norm), "other_tag");
  assert.equal(chipPosition(0), 1);
  assert.equal(chipPosition(40), 20);
  assert.equal(profileFrom("explore"), "explore");
  assert.equal(profileFrom("hub"), "library");
  assert.equal(profileFrom("studio"), "library");
  assert.equal(profileFrom("profile"), "profile");
  assert.equal(profileFrom("chat"), "story");
  assert.equal(profileFrom(null), "link");
  assert.equal(profileFrom("character"), "link");
  assert.equal(displayMode(true, false), "standalone");
  assert.equal(displayMode(false, true), "standalone");
  assert.equal(displayMode(false, false), "browser");
});

test("F47 explore_searched: only has_results (a bool), never the typed words; F46 hot_board_viewed: from explore/link", () => {
  assert.deepEqual(buildEvent("explore_searched", { has_results: true }), { name: "explore_searched", props: { has_results: true } });
  assert.deepEqual(buildEvent("explore_searched", { has_results: false }), { name: "explore_searched", props: { has_results: false } });
  assert.equal(buildEvent("explore_searched"), null, "has_results is required");
  assert.equal(buildEvent("explore_searched", { has_results: true, query: "ha vy" }), null, "no typed words");
  assert.equal(buildEvent("explore_searched", { has_results: "ha vy" }), null);
  assert.deepEqual(Object.keys(CLIENT_EVENTS.explore_searched.props), ["has_results"]);
  assert.deepEqual(buildEvent("hot_board_viewed", { from: "explore" }), { name: "hot_board_viewed", props: { from: "explore" } });
  assert.deepEqual(buildEvent("hot_board_viewed", { from: "link" }), { name: "hot_board_viewed", props: { from: "link" } });
  assert.equal(buildEvent("hot_board_viewed", { from: "studio" }), null);
  const plan = readFileSync(new URL("../../../docs/tracking-plan.md", import.meta.url), "utf8");
  assert.match(plan, /^\| `explore_searched` \| C \|.*`has_results: bool`/m);
  assert.match(plan, /^\| `hot_board_viewed` \| C \|.*`from: enum\(explore\\\|link\)`/m);
});
