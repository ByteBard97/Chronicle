/**
 * JSONL parsing with the torn-tail guard (docs/frame-log-schema.md §1 / §7):
 * "Readers treat a non-terminated tail as not-yet-written — tailing a
 * growing log must never yield a torn record." and "Readers ignore unknown
 * record types, unknown payload fields, ... — skip-and-continue, never
 * error."
 *
 * `splitCompleteLines` is the pure primitive both the full-stream reader and
 * the LIVE tail poller build on: given a chunk of text (which may start or
 * end mid-line, since it's an arbitrary byte range), return the complete
 * newline-terminated lines plus whatever incomplete text remains at the end
 * — the caller re-prepends that remainder to the next chunk it fetches
 * (or, at true end-of-stream, simply never gets to parse it, which is
 * correct: it's not-yet-written).
 */

export interface SplitResult {
  /** Complete lines, in order, each with its trailing newline stripped. */
  lines: string[];
  /** Trailing text with no newline yet — not-yet-written or not-yet-fetched. Never parsed. */
  remainder: string;
}

export function splitCompleteLines(chunk: string): SplitResult {
  const parts = chunk.split("\n");
  // split("\n") on "a\nb\n" -> ["a", "b", ""]; on "a\nb" -> ["a", "b"].
  // The last element is the remainder in both cases (empty string when the
  // chunk was fully newline-terminated) — everything before it is complete.
  const remainder = parts.pop() ?? "";
  return { lines: parts, remainder };
}

export interface ParsedRecord<P = Record<string, unknown>> {
  record: P;
  /** Byte length of this line's UTF-8 encoding, including its trailing `\n` — for offset bookkeeping. */
  byteLength: number;
}

const encoder = new TextEncoder();

/**
 * Parse a batch of complete (newline-stripped) lines as JSON. A line that
 * fails to parse as JSON is skipped, not thrown — per §7's "never error"
 * discipline, a single corrupt or partially-written line (short of a torn
 * tail, e.g. a bit-flip) must not take down the whole reader. Returns only
 * the records that parsed.
 */
export function parseJsonlLines<P = Record<string, unknown>>(
  lines: string[],
): ParsedRecord<P>[] {
  const out: ParsedRecord<P>[] = [];
  for (const line of lines) {
    if (line.length === 0) continue; // blank line (e.g. trailing newline before EOF)
    try {
      const record = JSON.parse(line) as P;
      // +1 for the newline this line was split on.
      const byteLength = encoder.encode(line).length + 1;
      out.push({ record, byteLength });
    } catch {
      // Malformed JSON on a line that *was* newline-terminated is not a
      // torn tail (that case never reaches here — splitCompleteLines keeps
      // it in `remainder`) — it's genuine corruption. Skip and continue.
      continue;
    }
  }
  return out;
}

/**
 * Stateful incremental JSONL reader: feed it chunks (in byte-offset order,
 * e.g. from successive Range fetches) and it accumulates a torn-tail
 * remainder across calls, so a record split across two fetch boundaries is
 * reassembled correctly rather than being dropped as "torn" twice.
 */
export class JsonlTailReader<P = Record<string, unknown>> {
  private remainder = "";

  /** Byte offset of the first not-yet-consumed byte, for the next Range fetch. */
  private _consumedBytes: number;

  constructor(startByteOffset = 0) {
    this._consumedBytes = startByteOffset;
  }

  get consumedBytes(): number {
    return this._consumedBytes;
  }

  /**
   * Feed the next chunk of decoded text, starting exactly at `consumedBytes`
   * in the underlying file. Returns every complete record newly parsed.
   */
  feed(chunk: string): ParsedRecord<P>[] {
    const { lines, remainder } = splitCompleteLines(this.remainder + chunk);
    this.remainder = remainder;
    const parsed = parseJsonlLines<P>(lines);
    for (const p of parsed) {
      this._consumedBytes += p.byteLength;
    }
    return parsed;
  }
}
