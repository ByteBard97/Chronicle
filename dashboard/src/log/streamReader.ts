/**
 * Stream reader: Range-fetches a run's `events.jsonl` / `trace.jsonl` over
 * HTTP and parses it with the torn-tail guard (jsonl.ts). Two entry points:
 *
 *  - `readByteRange` — one-shot read of [start, end) (end omitted = to EOF),
 *    used for "load everything" and for "replay from this keyframe's
 *    offset to T".
 *  - `LiveTailPoller` — repeatedly reads from the last consumed byte to
 *    current EOF on a timer, for LIVE tailing (ui-spec §1.3: "polling with
 *    a byte offset to tail a growing log").
 */
import type { FrameRecord } from "./types";
import { rangeFetch } from "./rangeFetch";
import { JsonlTailReader, type ParsedRecord } from "./jsonl";

export function runStreamUrl(runId: string, filename: string): string {
  return `/runs/${encodeURIComponent(runId)}/${filename}`;
}

export interface ByteRangeReadResult {
  records: FrameRecord[];
  /** Byte offset one past the last complete record consumed — feed this back in as the next `start`. */
  consumedThrough: number;
  /** True if the underlying transport confirmed partial-content (206) semantics. */
  partial: boolean;
  /**
   * The transport's raw HTTP status (additive field, lane 15 Task 3):
   * `LiveTailPoller` needs to distinguish a 416 (range beyond current EOF
   * — the static-run case, back off) from a normal 200/206 read, which
   * `partial` alone can't do (a 200-with-full-body server would leave
   * `partial: false` for both a real read and a would-be-416 case).
   */
  status: number;
}

/**
 * Read and parse every complete record in [start, end) of `url`. A
 * non-terminated tail within the fetched bytes (whether because `end` cut
 * a record in half, or because it's the true not-yet-written end of a
 * growing file) is left unparsed and simply not included — that is the
 * torn-tail guard; the caller's next read naturally starts from
 * `consumedThrough`, before the torn remainder, so nothing is lost, only
 * deferred.
 */
export async function readByteRange(
  url: string,
  start: number,
  end?: number,
): Promise<ByteRangeReadResult> {
  const res = await rangeFetch(url, start, end);
  const reader = new JsonlTailReader<FrameRecord>(start);
  const parsed: ParsedRecord<FrameRecord>[] = reader.feed(res.text);
  return {
    records: parsed.map((p) => p.record),
    consumedThrough: reader.consumedBytes,
    partial: res.partial,
    status: res.status,
  };
}

/** Read the whole stream from byte 0 to current EOF. */
export async function readEntireStream(url: string): Promise<ByteRangeReadResult> {
  return readByteRange(url, 0);
}

export type LiveTailListener = (records: FrameRecord[], consumedThrough: number) => void;

/**
 * Backoff cap (lane 15 Task 3): a static (non-growing) run polled while
 * LIVE-docked hits a 416 (requested range beyond current EOF) on every
 * poll, forever — harmless individually, but sustained ~1/s polling
 * against a run that will never grow is pure waste (and log noise).
 * Doubling from the base interval on each 416, capped here, keeps
 * liveness bounded (a growing run is picked up again within this window)
 * while letting a static run's polling rate decay to a low steady state.
 */
const MAX_BACKOFF_MS = 10_000;

/**
 * Polls `url` from the last consumed byte offset to current EOF, normally
 * on a fixed interval (ui-spec §1.3's "~1 s cadence" default). One poller
 * per stream per run; `stop()` clears the timer.
 *
 * Lane 15 Task 3: the interval is no longer fixed — a 416 doubles the
 * delay before the next poll (capped at `MAX_BACKOFF_MS`); any
 * successful read (200/206) that actually advances `consumedThrough`
 * resets the delay to the base `intervalMs` immediately, so a run that
 * starts growing again is caught within one poll, not one backoff cycle.
 * Public interface unchanged (constructor, `pollOnce()`, `start()`,
 * `stop()`, `position`) — backoff is purely internal bookkeeping.
 */
export class LiveTailPoller {
  private consumedThrough: number;
  private timer: ReturnType<typeof setTimeout> | undefined;
  private polling = false;
  private stopped = false;
  /** The delay before the *next* poll — grows on 416, resets to `intervalMs` on progress. */
  private currentDelayMs: number;

  constructor(
    private readonly url: string,
    startByteOffset = 0,
    private readonly intervalMs = 1000,
  ) {
    this.consumedThrough = startByteOffset;
    this.currentDelayMs = intervalMs;
  }

  get position(): number {
    return this.consumedThrough;
  }

  /** Fetch once, immediately (used both by `start()`'s first tick and by tests). */
  async pollOnce(): Promise<FrameRecord[]> {
    if (this.polling) return [];
    this.polling = true;
    try {
      const result = await readByteRange(this.url, this.consumedThrough);
      const madeProgress = result.consumedThrough > this.consumedThrough;
      this.consumedThrough = result.consumedThrough;

      if (result.status === 416) {
        this.currentDelayMs = Math.min(this.currentDelayMs * 2, MAX_BACKOFF_MS);
      } else if ((result.status === 200 || result.status === 206) && madeProgress) {
        this.currentDelayMs = this.intervalMs;
      }

      return result.records;
    } finally {
      this.polling = false;
    }
  }

  start(onRecords: LiveTailListener): () => void {
    this.stopped = false;
    const scheduleNext = () => {
      if (this.stopped) return;
      this.timer = setTimeout(() => {
        void this.pollOnce().then((records) => {
          if (records.length > 0) onRecords(records, this.consumedThrough);
          scheduleNext();
        });
      }, this.currentDelayMs);
    };
    scheduleNext();
    return () => this.stop();
  }

  stop(): void {
    this.stopped = true;
    if (this.timer !== undefined) {
      clearTimeout(this.timer);
      this.timer = undefined;
    }
  }
}
