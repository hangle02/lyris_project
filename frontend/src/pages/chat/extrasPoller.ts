// Refresh and polling of a story's extras (phase3.md §8), without React or the DOM so it can be
// tested with fake timers. useStoryExtras wires it to fetch, setTimeout and document.hidden.

/** Ask again every 2 seconds while the server says background jobs are pending. */
export const POLL_MS = 2000;

/** Longest wait between retries after failed fetches while jobs were pending. */
export const MAX_BACKOFF_MS = 30000;

export interface PollerDeps<T> {
  /** One fetch; rejects on failure. */
  load: () => Promise<T>;
  onData: (data: T) => void;
  onError: (error: unknown) => void;
  /** Whether the answer says jobs are still pending (keep polling). */
  isPending: (data: T) => boolean;
  /** True while the page is hidden (another tab, app in the background): no polling then. */
  isHidden: () => boolean;
  setTimer: (fn: () => void, ms: number) => unknown;
  clearTimer: (handle: unknown) => void;
  intervalMs?: number;
  maxBackoffMs?: number;
}

/**
 * - `refresh()` fetches now (cancelling a scheduled poll); only the newest fetch's answer counts.
 * - After an answer with pending = true, the next fetch is scheduled `intervalMs` later, unless the
 *   page is hidden or polling is paused (a reply is streaming: the worker waits anyway, and the end
 *   of the stream refreshes).
 * - `visibilityChanged()` resumes at once when the page comes back while the last answer was pending.
 * - A failed fetch keeps the last good data. If that data was pending, polling goes on with backoff
 *   (`intervalMs`, then twice as long each time, up to `maxBackoffMs`) so a backend restart or one 5xx
 *   during a long extraction does not leave the drawer stuck on "pending"; a good answer resets it.
 *   If nothing was pending, polling stays stopped until the next refresh.
 * - `dispose()` stops everything; late answers are dropped.
 */
export class ExtrasPoller<T> {
  private readonly deps: PollerDeps<T>;
  private readonly interval: number;
  private readonly maxBackoff: number;
  private failures = 0;
  private seq = 0;
  private timer: unknown = null;
  private lastPending = false;
  private paused = false;
  private disposed = false;

  constructor(deps: PollerDeps<T>) {
    this.deps = deps;
    this.interval = deps.intervalMs ?? POLL_MS;
    this.maxBackoff = Math.max(this.interval, deps.maxBackoffMs ?? MAX_BACKOFF_MS);
  }

  /** Whether a poll is scheduled (for tests and debugging). */
  get scheduled(): boolean {
    return this.timer !== null;
  }

  async refresh(): Promise<void> {
    if (this.disposed) return;
    this.cancelTimer();
    const mine = ++this.seq;
    try {
      const data = await this.deps.load();
      if (this.disposed || mine !== this.seq) return;
      this.failures = 0;
      this.lastPending = this.deps.isPending(data);
      this.deps.onData(data);
      this.schedule();
    } catch (e) {
      if (this.disposed || mine !== this.seq) return;
      // lastPending stays what the last good answer said: retry only if jobs were pending then.
      this.failures++;
      this.deps.onError(e);
      this.schedule();
    }
  }

  setPaused(paused: boolean): void {
    if (this.paused === paused) return;
    this.paused = paused;
    if (paused) this.cancelTimer();
    else this.schedule();
  }

  visibilityChanged(): void {
    if (this.disposed) return;
    if (this.deps.isHidden()) {
      this.cancelTimer();
    } else if (this.lastPending && !this.paused && this.timer === null) {
      void this.refresh();
    }
  }

  dispose(): void {
    this.disposed = true;
    this.seq++;
    this.cancelTimer();
  }

  private schedule(): void {
    if (this.disposed || this.paused || !this.lastPending || this.deps.isHidden() || this.timer !== null) return;
    this.timer = this.deps.setTimer(() => {
      this.timer = null;
      void this.refresh();
    }, this.delay());
  }

  /** Normal interval, or the backoff after `failures` failed fetches in a row (2 s, 4 s, 8 s … 30 s). */
  private delay(): number {
    if (this.failures === 0) return this.interval;
    return Math.min(this.maxBackoff, this.interval * 2 ** (this.failures - 1));
  }

  private cancelTimer(): void {
    if (this.timer !== null) {
      this.deps.clearTimer(this.timer);
      this.timer = null;
    }
  }
}
