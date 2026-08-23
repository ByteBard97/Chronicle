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
  };
}

/** Read the whole stream from byte 0 to current EOF. */
export async function readEntireStream(url: string): Promise<ByteRangeReadResult> {
  return readByteRange(url, 0);
}

export type LiveTailListener = (records: FrameRecord[], consumedThrough: number) => void;

/**
 * Polls `url` from the last consumed byte offset to current EOF on a fixed
 * interval (ui-spec §1.3's "~1 s cadence" default; the work packet asks
 * for the same). One poller per stream per run; `stop()` clears the timer.
 */
export class LiveTailPoller {
  private consumedThrough: number;
  private timer: ReturnType<typeof setInterval> | undefined;
  private polling = false;

  constructor(
    private readonly url: string,
    startByteOffset = 0,
    private readonly intervalMs = 1000,
  ) {
    this.consumedThrough = startByteOffset;
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
      this.consumedThrough = result.consumedThrough;
      return result.records;
    } finally {
      this.polling = false;
    }
  }

  start(onRecords: LiveTailListener): () => void {
    this.timer = setInterval(() => {
      void this.pollOnce().then((records) => {
        if (records.length > 0) onRecords(records, this.consumedThrough);
      });
    }, this.intervalMs);
    return () => this.stop();
  }

  stop(): void {
    if (this.timer !== undefined) {
      clearInterval(this.timer);
      this.timer = undefined;
    }
  }
}
