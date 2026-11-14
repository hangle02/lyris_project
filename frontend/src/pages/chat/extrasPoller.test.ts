import { test } from "node:test";
import assert from "node:assert/strict";
import { ExtrasPoller, MAX_BACKOFF_MS, POLL_MS } from "./extrasPoller.ts";

interface Answer {
  pending: boolean;
  n: number;
}

/** Hand-driven timers, a scripted server and a switchable "hidden" page. */
function harness(answers: Array<Answer | Error>) {
  const timers = new Map<number, { fn: () => void; ms: number }>();
  let nextId = 1;
  let hidden = false;
  let calls = 0;
  const data: Answer[] = [];
  const errors: unknown[] = [];
  const pendingLoads: Array<() => void> = [];
  let manual = false;

  const poller = new ExtrasPoller<Answer>({
    load: () => {
      const answer = answers[Math.min(calls, answers.length - 1)];
      calls++;
      if (manual) {
        return new Promise<Answer>((resolve, reject) => {
          pendingLoads.push(() => (answer instanceof Error ? reject(answer) : resolve(answer as Answer)));
        });
      }
      return answer instanceof Error ? Promise.reject(answer) : Promise.resolve(answer as Answer);
    },
    onData: (d) => data.push(d),
    onError: (e) => errors.push(e),
    isPending: (d) => d.pending,
    isHidden: () => hidden,
    setTimer: (fn, ms) => {
      const id = nextId++;
      timers.set(id, { fn, ms });
      return id;
    },
    clearTimer: (h) => {
      timers.delete(h as number);
    },
  });

  return {
    poller,
    data,
    errors,
    get calls() {
      return calls;
    },
    timers,
    setHidden(v: boolean) {
      hidden = v;
    },
    setManual(v: boolean) {
      manual = v;
    },
    pendingLoads,
    /** Fires every scheduled timer once and lets the fetches settle. */
    async tick() {
      const due = [...timers.entries()];
      for (const [id, t] of due) {
        timers.delete(id);
        t.fn();
      }
      await flush();
    },
  };
}

const flush = () => new Promise((r) => setTimeout(r, 0));

test("polls every 2 s while pending, stops when done", async () => {
  const h = harness([
    { pending: true, n: 1 },
    { pending: true, n: 2 },
    { pending: false, n: 3 },
  ]);
  await h.poller.refresh();
  assert.equal(h.calls, 1);
  assert.equal(h.timers.size, 1);
  assert.equal([...h.timers.values()][0]?.ms, POLL_MS);
  await h.tick();
  assert.equal(h.calls, 2);
  await h.tick();
  assert.equal(h.calls, 3);
  assert.equal(h.timers.size, 0, "no poll after pending turned false");
  assert.deepEqual(
    h.data.map((d) => d.n),
    [1, 2, 3],
  );
});

test("no polling when the answer is not pending", async () => {
  const h = harness([{ pending: false, n: 1 }]);
  await h.poller.refresh();
  assert.equal(h.poller.scheduled, false);
});

test("hidden page: no timer; visible again resumes at once", async () => {
  const h = harness([
    { pending: true, n: 1 },
    { pending: true, n: 2 },
  ]);
  await h.poller.refresh();
  assert.equal(h.poller.scheduled, true);
  h.setHidden(true);
  h.poller.visibilityChanged();
  assert.equal(h.poller.scheduled, false, "hiding cancels the scheduled poll");
  h.setHidden(false);
  h.poller.visibilityChanged();
  await flush();
  assert.equal(h.calls, 2, "coming back fetches right away");
  assert.equal(h.poller.scheduled, true);
});

test("an answer that arrives while hidden does not schedule", async () => {
  const h = harness([{ pending: true, n: 1 }]);
  h.setHidden(true);
  await h.poller.refresh();
  assert.equal(h.poller.scheduled, false);
});

test("paused (a reply is streaming): no polling until resumed", async () => {
  const h = harness([{ pending: true, n: 1 }]);
  await h.poller.refresh();
  h.poller.setPaused(true);
  assert.equal(h.poller.scheduled, false);
  h.poller.visibilityChanged();
  assert.equal(h.calls, 1, "visibility does not resume a paused poller");
  h.poller.setPaused(false);
  assert.equal(h.poller.scheduled, true);
});

test("a failed fetch while pending keeps the data, reports, and retries with backoff", async () => {
  const h = harness([
    { pending: true, n: 1 },
    new Error("down"),
    new Error("down"),
    new Error("down"),
    { pending: true, n: 2 },
    { pending: false, n: 3 },
  ]);
  await h.poller.refresh();
  await h.tick(); // fails
  assert.equal(h.errors.length, 1);
  assert.equal(h.data.length, 1, "the last good data stays");
  assert.equal(h.poller.scheduled, true, "polling goes on");
  assert.equal([...h.timers.values()][0]?.ms, POLL_MS);
  await h.tick(); // fails again: twice as long
  assert.equal([...h.timers.values()][0]?.ms, POLL_MS * 2);
  await h.tick(); // and again
  assert.equal([...h.timers.values()][0]?.ms, POLL_MS * 4);
  await h.tick(); // succeeds: back to the normal interval
  assert.deepEqual(
    h.data.map((d) => d.n),
    [1, 2],
  );
  assert.equal([...h.timers.values()][0]?.ms, POLL_MS);
  await h.tick();
  assert.equal(h.poller.scheduled, false, "stops once nothing is pending");
  assert.deepEqual(
    h.data.map((d) => d.n),
    [1, 2, 3],
  );
});

test("backoff is capped and respects hidden, paused and dispose", async () => {
  const h = harness([{ pending: true, n: 1 }, new Error("down")]);
  await h.poller.refresh();
  for (let i = 0; i < 8; i++) await h.tick();
  assert.equal([...h.timers.values()][0]?.ms, MAX_BACKOFF_MS);
  h.poller.setPaused(true);
  assert.equal(h.poller.scheduled, false);
  h.poller.setPaused(false);
  assert.equal(h.poller.scheduled, true);
  h.setHidden(true);
  h.poller.visibilityChanged();
  assert.equal(h.poller.scheduled, false);
  h.setHidden(false);
  h.poller.visibilityChanged();
  await flush();
  assert.equal(h.poller.scheduled, true, "coming back retries and keeps retrying");
  h.poller.dispose();
  assert.equal(h.poller.scheduled, false);
});

test("a failed fetch when nothing was pending stops polling", async () => {
  const h = harness([new Error("down")]);
  await h.poller.refresh();
  assert.equal(h.errors.length, 1);
  assert.equal(h.poller.scheduled, false);
  const h2 = harness([{ pending: false, n: 1 }, new Error("down")]);
  await h2.poller.refresh();
  await h2.poller.refresh();
  assert.equal(h2.errors.length, 1);
  assert.equal(h2.poller.scheduled, false);
});

test("a manual refresh cancels the scheduled poll; only the newest answer counts", async () => {
  const h = harness([
    { pending: true, n: 1 },
    { pending: true, n: 2 },
    { pending: false, n: 3 },
  ]);
  await h.poller.refresh();
  assert.equal(h.poller.scheduled, true);
  h.setManual(true);
  const first = h.poller.refresh();
  assert.equal(h.poller.scheduled, false, "refresh cancels the timer");
  const second = h.poller.refresh();
  // The older request answers last: it must be ignored.
  h.pendingLoads[1]?.();
  h.pendingLoads[0]?.();
  await Promise.all([first, second]);
  assert.deepEqual(
    h.data.map((d) => d.n),
    [1, 3],
  );
  assert.equal(h.poller.scheduled, false);
});

test("dispose stops timers and drops late answers", async () => {
  const h = harness([{ pending: true, n: 1 }]);
  await h.poller.refresh();
  h.setManual(true);
  const late = h.poller.refresh();
  h.poller.dispose();
  h.pendingLoads[0]?.();
  await late;
  assert.equal(h.data.length, 1);
  assert.equal(h.poller.scheduled, false);
  await h.poller.refresh();
  assert.equal(h.calls, 2, "no fetch after dispose");
});
