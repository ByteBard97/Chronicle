/**
 * Encounter-feed reader (lane 11, ui-spec §3.3 / frame-log-schema.md §4):
 * pages the trace stream by tick using the sidecar index's
 * `tick_offsets` + Range reads (`streamReader.ts`'s `readByteRange`), and
 * maps the raw trace records that matter to the feed into a small,
 * render-ready `FeedRow` shape.
 *
 * Deliberately does NOT touch `reconstruct.ts` (lane 6, do-not-touch):
 * `encounter_rolled`/`nothing_salient` are no-ops there by design (no
 * derived-state effect) — the feed reads the trace stream itself.
 *
 * Design call (documented per the packet): only the four record types the
 * feed actually renders as outcome rows are mapped — `transmitted`,
 * `encounter_rolled`, `nothing_salient`, `transmission_declined`. Every
 * other trace record type (`belief_formed`, `mutation_applied`,
 * `supersession`, `relationship_formed`, `rule_evaluated`,
 * `threshold_crossed`, ...) is not part of the encounter feed's four
 * outcome states and is skipped (`mapTraceRecordToFeedRow` returns
 * `null`) rather than surfaced as a fifth kind of row.
 */
import type { FrameRecord } from "./types";
import { readByteRange } from "./streamReader";

// ---------------------------------------------------------------------------
// Row shape

export type FeedOutcome = "transmitted" | "rolled_against" | "declined" | "nothing_salient";

export type FeedRowDetail =
  | { kind: "transmitted"; variantId: string | null; mutatedSlot: string | null }
  | { kind: "rolled_against"; value: number; threshold: number }
  | { kind: "declined"; rule: string }
  | { kind: "nothing_salient"; reason: string };

export interface FeedRow {
  tick: number;
  seq: number;
  location: string | null;
  /** Exactly two participant ids, in the order the record carried them. */
  participants: string[];
  outcome: FeedOutcome;
  claimId: string | null;
  detail: FeedRowDetail;
}

/**
 * Map one raw trace `FrameRecord` to a `FeedRow`, or `null` if this record
 * isn't one of the feed's four outcome states.
 *
 * `encounter_rolled` with `encountered: true` is deliberately elided (not
 * its own outcome row, packet's "Key design facts"): a positive co-presence
 * roll is not itself transmitted/rolled-against/declined/nothing-salient —
 * it's the encounter that then produced one of those trace-native
 * follow-up records at the same tick, which is/are mapped on their own.
 */
export function mapTraceRecordToFeedRow(record: FrameRecord): FeedRow | null {
  const p = record.payload;
  const recordType = p.record_type;

  if (recordType === "transmitted") {
    const variant = p.variant as { variant_id?: string; mutated_slot?: string | null } | undefined;
    return {
      tick: record.tick,
      seq: record.seq,
      location: typeof p.location_id === "string" ? p.location_id : null,
      participants: [String(p.teller_id), String(p.hearer_id)],
      outcome: "transmitted",
      claimId: typeof p.claim_id === "string" ? p.claim_id : null,
      detail: {
        kind: "transmitted",
        variantId: typeof variant?.variant_id === "string" ? variant.variant_id : null,
        mutatedSlot: typeof variant?.mutated_slot === "string" ? variant.mutated_slot : null,
      },
    };
  }

  if (recordType === "encounter_rolled") {
    if (p.encountered === true) return null; // see module doc: not its own outcome row
    return {
      tick: record.tick,
      seq: record.seq,
      location: typeof p.location_id === "string" ? p.location_id : null,
      participants: [String(p.npc_a), String(p.npc_b)],
      outcome: "rolled_against",
      // encounter_rolled carries no claim_id (schema §4:116) — pinned,
      // not a bug: an active claim filter structurally excludes these rows.
      claimId: null,
      detail: {
        kind: "rolled_against",
        value: typeof p.value === "number" ? p.value : 0,
        threshold: typeof p.threshold === "number" ? p.threshold : 0,
      },
    };
  }

  if (recordType === "nothing_salient") {
    return {
      tick: record.tick,
      seq: record.seq,
      location: typeof p.location_id === "string" ? p.location_id : null,
      participants: [String(p.npc_a), String(p.npc_b)],
      outcome: "nothing_salient",
      claimId: typeof p.claim_id === "string" ? p.claim_id : null,
      detail: {
        kind: "nothing_salient",
        reason: typeof p.reason === "string" ? p.reason : "",
      },
    };
  }

  if (recordType === "transmission_declined") {
    return {
      tick: record.tick,
      seq: record.seq,
      location: typeof p.location_id === "string" ? p.location_id : null,
      participants: [String(p.teller_id), String(p.hearer_id)],
      outcome: "declined",
      claimId: typeof p.claim_id === "string" ? p.claim_id : null,
      detail: {
        kind: "declined",
        rule: typeof p.rule === "string" ? p.rule : "",
      },
    };
  }

  return null;
}

// ---------------------------------------------------------------------------
// Tick-offset pagination

/** The known ticks in a sidecar stream index, ascending. */
export function sortedTicks(tickOffsets: Record<string, number>): number[] {
  return Object.keys(tickOffsets)
    .map(Number)
    .filter((n) => Number.isFinite(n))
    .sort((a, b) => a - b);
}

export interface TickReadResult {
  records: FrameRecord[];
  /** Byte offset one past the last complete record consumed (feed into a LiveTailPoller). */
  consumedThrough: number;
}

/**
 * Read every trace record for ticks in `[fromTick, toTick]` (inclusive),
 * using the sidecar's `tick_offsets` to compute the byte range: start at
 * the first known tick's offset, end at the offset of the tick
 * immediately after `toTick` in the *full* known tick set.
 *
 * Edge case (dedicated test): if the highest known tick overall is within
 * `[fromTick, toTick]` — i.e. this read reaches the end of what the
 * sidecar knows about — there is no "next tick" to bound the slice, so
 * `end` is omitted and `readByteRange` reads to EOF (RFC 7233 open-ended
 * range). Computing a synthetic end offset here would silently drop
 * whatever trace rows exist for that last tick.
 */
export async function readTicksInRange(
  url: string,
  tickOffsets: Record<string, number>,
  fromTick: number,
  toTick: number,
): Promise<TickReadResult> {
  const allTicks = sortedTicks(tickOffsets);
  const inRange = allTicks.filter((t) => t >= fromTick && t <= toTick);
  if (inRange.length === 0) return { records: [], consumedThrough: 0 };

  const start = tickOffsets[String(inRange[0])];
  const lastIndex = allTicks.indexOf(inRange[inRange.length - 1]);
  const isLastKnownTick = lastIndex === allTicks.length - 1;
  const end = isLastKnownTick ? undefined : tickOffsets[String(allTicks[lastIndex + 1])];

  const result = await readByteRange(url, start, end);
  return { records: result.records, consumedThrough: result.consumedThrough };
}

// ---------------------------------------------------------------------------
// Filters (urlState.filters — NPC / location / outcome / claim)

export interface FeedFilters {
  npc?: string;
  location?: string;
  outcome?: string;
  claim?: string;
}

export function filterFeedRows(rows: FeedRow[], filters: FeedFilters): FeedRow[] {
  return rows.filter((row) => {
    if (filters.npc && !row.participants.includes(filters.npc)) return false;
    if (filters.location && row.location !== filters.location) return false;
    if (filters.outcome && row.outcome !== filters.outcome) return false;
    // encounter_rolled (rolled_against) carries no claim_id: an active
    // claim filter structurally excludes those rows. Correct, per the
    // packet's pinned note — not "fixed" here.
    if (filters.claim && row.claimId !== filters.claim) return false;
    return true;
  });
}
