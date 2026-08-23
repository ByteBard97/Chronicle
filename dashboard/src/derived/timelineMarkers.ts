/**
 * Timeline markers (lane 16, ui-spec §2:59): trace + event records ->
 * typed, positioned markers for the timeline bar, plus day-tick boundaries
 * (ADR-0010: 24 ticks = 1 game-day) and heat-stripe bucketing.
 *
 * Marker taxonomy -> record mapping (pinned by the work packet):
 *  - claim born        <- first `belief_formed` trace record per `claim_id`
 *  - mutation          <- `mutation_applied` trace records
 *  - supersession      <- `supersession` trace records
 *  - grudge formed     <- `grudge_formed` trace records
 *  - threshold crossed <- `threshold_crossed` trace records
 *  - events            <- `npc_died` / `crime_witnessed` event-stream
 *    records. ui-spec §2:59's taxonomy is trace-derivation-flavored, but
 *    per ui-doctrines ("the scrubber is an event index, not a position
 *    control") the canonical events stream gets its own marker type rather
 *    than being dropped or folded into a trace-only bucket.
 *  - role vacancy (Tier 5) and carrier arrival (no schema v1 record --
 *    deriving it from location transitions is fuzzy, per the packet) are
 *    `MARKER_TYPE_REGISTRY` entries with `hasProducer: false`. They render
 *    as active-but-empty legend entries; `deriveTimelineMarkers` never
 *    produces them. Named finding, not improvised derivation -- adding a
 *    producer later is a registry edit (new record-type branch below), not
 *    new plumbing.
 *
 * FINDING: `src/log/types.ts`'s `TraceRecordType` union omits
 * `grudge_formed`, even though docs/frame-log-schema.md §4:125 documents
 * it as a real Tier-3 trace record type -- a schema-mirror gap in that
 * file. Harmless here (`TracePayload.record_type` is typed as `string`,
 * not the union) but out of this lane's file boundary (`src/log/*` is
 * read-only per the packet) -- flagged for whichever lane next touches
 * `log/types.ts`.
 *
 * FINDING: `src/styles/tokens.css` defines `--ev-claim-born`,
 * `--ev-mutation`, `--ev-grudge`, `--ev-death`, `--ev-carrier`, and
 * `--ev-threshold`, but no token for `supersession` or `role_vacancy` (both
 * new to this lane's taxonomy vs. the old 6-entry mock legend). This
 * registry falls back to literal hex colors for those two. tokens.css is
 * outside this lane's file boundary -- a follow-up lane should add
 * `--ev-supersession` / `--ev-role-vacancy` and this registry can switch
 * to `var(--ev-...)` for them.
 */
import type { FrameRecord } from "../log/types";

export type MarkerType =
  | "claim_born"
  | "mutation"
  | "supersession"
  | "grudge_formed"
  | "threshold_crossed"
  | "role_vacancy"
  | "carrier_arrival"
  | "events";

export interface TimelineMarker {
  tick: number;
  type: MarkerType;
  label: string;
  /** Percent position along the bar, [0, 100]. */
  pos: number;
}

export interface MarkerTypeMeta {
  type: MarkerType;
  /** Legend display name (ui-spec §2:59's taxonomy wording). */
  legendName: string;
  color: string;
  /**
   * False for registry entries with no schema-v1 producer (role vacancy,
   * carrier arrival) -- these render as an active-but-empty legend entry,
   * never an error, and `deriveTimelineMarkers` never emits them.
   */
  hasProducer: boolean;
}

/**
 * The type registry (packet: "build the type registry so adding [role
 * vacancy / carrier arrival] later is config, not code"). Single source of
 * truth for legend rendering, marker coloring, and default filter state --
 * adding a ninth type is one more entry here, not new call sites.
 */
export const MARKER_TYPE_REGISTRY: MarkerTypeMeta[] = [
  { type: "claim_born", legendName: "claim born", color: "var(--ev-claim-born)", hasProducer: true },
  { type: "mutation", legendName: "mutation", color: "var(--ev-mutation)", hasProducer: true },
  { type: "supersession", legendName: "supersession", color: "#4fa8d8", hasProducer: true },
  { type: "grudge_formed", legendName: "grudge formed", color: "var(--ev-grudge)", hasProducer: true },
  { type: "threshold_crossed", legendName: "threshold crossed", color: "var(--ev-threshold)", hasProducer: true },
  { type: "role_vacancy", legendName: "role vacancy", color: "#6b7280", hasProducer: false },
  { type: "carrier_arrival", legendName: "carrier arrival", color: "var(--ev-carrier)", hasProducer: false },
  { type: "events", legendName: "events", color: "var(--ev-death)", hasProducer: true },
];

function str(v: unknown): string | undefined {
  return typeof v === "string" ? v : undefined;
}

/** Max tick observed across both streams -- the run's range for day-tick boundaries and positioning. */
export function computeMaxTick(traceRecords: FrameRecord[], eventRecords: FrameRecord[]): number {
  let max = 0;
  for (const r of traceRecords) if (r.tick > max) max = r.tick;
  for (const r of eventRecords) if (r.tick > max) max = r.tick;
  return max;
}

/** Pure: tick -> percent position along [0, maxTick], clamped to [0, 100]. */
export function tickToPercent(tick: number, maxTick: number): number {
  if (maxTick <= 0) return 0;
  return +Math.min(100, Math.max(0, (tick / maxTick) * 100)).toFixed(2);
}

/**
 * Pure: trace + event records -> typed, positioned markers, sorted by
 * tick. `maxTick` is a parameter (not recomputed here) so a caller that
 * already knows the run's range doesn't pay for a second pass; pass
 * `computeMaxTick(traceRecords, eventRecords)` when it doesn't.
 */
export function deriveTimelineMarkers(
  traceRecords: FrameRecord[],
  eventRecords: FrameRecord[],
  maxTick: number,
): TimelineMarker[] {
  const markers: TimelineMarker[] = [];
  const pos = (tick: number) => tickToPercent(tick, maxTick);

  // Claim born: first belief_formed per claim_id (the pinned recipe --
  // a claim can accumulate multiple believers over time; only the first
  // belief_formed record for a given claim marks the claim's birth).
  const firstBeliefByClaim = new Map<string, FrameRecord>();
  for (const r of traceRecords) {
    if (r.payload.record_type !== "belief_formed") continue;
    const claimId = str(r.payload.claim_id);
    if (claimId === undefined) continue;
    const existing = firstBeliefByClaim.get(claimId);
    if (existing === undefined || r.tick < existing.tick) {
      firstBeliefByClaim.set(claimId, r);
    }
  }
  for (const [claimId, r] of firstBeliefByClaim) {
    markers.push({
      tick: r.tick,
      type: "claim_born",
      label: `claim born: ${claimId}`,
      pos: pos(r.tick),
    });
  }

  for (const r of traceRecords) {
    const rt = r.payload.record_type;
    if (rt === "mutation_applied") {
      const slot = str(r.payload.slot) ?? "?";
      markers.push({
        tick: r.tick,
        type: "mutation",
        label: `mutation: ${str(r.payload.claim_id) ?? "?"} · ${slot}`,
        pos: pos(r.tick),
      });
    } else if (rt === "supersession") {
      markers.push({
        tick: r.tick,
        type: "supersession",
        label: `supersession: ${str(r.payload.claim_id) ?? "?"}`,
        pos: pos(r.tick),
      });
    } else if (rt === "grudge_formed") {
      markers.push({
        tick: r.tick,
        type: "grudge_formed",
        label: `grudge: ${str(r.payload.holder_id) ?? "?"} → ${str(r.payload.target_id) ?? "?"}`,
        pos: pos(r.tick),
      });
    } else if (rt === "threshold_crossed") {
      markers.push({
        tick: r.tick,
        type: "threshold_crossed",
        label: `threshold: ${str(r.payload.rule) ?? "?"}`,
        pos: pos(r.tick),
      });
    }
  }

  for (const r of eventRecords) {
    const eventType = str(r.payload.event_type);
    if (eventType === "npc_died") {
      markers.push({
        tick: r.tick,
        type: "events",
        label: `death: ${str(r.payload.npc_id) ?? "?"}`,
        pos: pos(r.tick),
      });
    } else if (eventType === "crime_witnessed") {
      markers.push({
        tick: r.tick,
        type: "events",
        label: `crime witnessed: ${str(r.payload.crime_type) ?? "?"} (${str(r.payload.witness_id) ?? "?"})`,
        pos: pos(r.tick),
      });
    }
  }

  markers.sort((a, b) => a.tick - b.tick);
  return markers;
}

export interface DayTick {
  pos: number;
  n: number;
}

/** Day-tick boundaries (ADR-0010: 24 ticks = 1 game-day) across [0, maxTick]. */
export function computeDayTicks(maxTick: number): DayTick[] {
  const ticks: DayTick[] = [];
  if (maxTick <= 0) return ticks;
  const dayCount = Math.floor(maxTick / 24);
  for (let n = 1; n <= dayCount; n++) {
    ticks.push({ n, pos: tickToPercent(n * 24, maxTick) });
  }
  return ticks;
}

/**
 * Post-delivery correction (found in browser verification, not by any
 * test -- jsdom's synthetic clicks can't catch this class of bug, only
 * real hit-testing can): real data produces co-tick markers by
 * construction (a death and the crime witnessing it happen in the same
 * tick), which render at the identical `pos` and fully overlap in the
 * sparse (non-heat-stripe) rendering path -- the later button in DOM
 * order silently eats every click meant for the one(s) underneath it.
 *
 * Collapses same-position markers into one, combining their labels
 * (the click's only effect is `urlState.t = marker.tick`, and coincident
 * markers already share that tick, so nothing is lost). Deliberately
 * NOT a vertical fan-out: an offset would misrepresent position for a
 * magic pixel constant; collapsing is honest, since they *are* one tick.
 * Keeps the first marker's type/color for the combined dot -- a
 * simplification, not a fabrication (the full list is always in the
 * title). Composes with `computeHeatStripe`, which should run on the
 * grouped result so bucket counts reflect distinct positions, not raw
 * per-tick event counts.
 */
export function groupCoincidentMarkers(markers: TimelineMarker[]): TimelineMarker[] {
  const byPos = new Map<number, TimelineMarker[]>();
  for (const m of markers) {
    const group = byPos.get(m.pos);
    if (group === undefined) byPos.set(m.pos, [m]);
    else group.push(m);
  }

  const grouped: TimelineMarker[] = [];
  for (const group of byPos.values()) {
    if (group.length === 1) {
      grouped.push(group[0]!);
      continue;
    }
    const first = group[0]!;
    grouped.push({
      tick: first.tick,
      type: first.type,
      pos: first.pos,
      label: group.map((m) => m.label).join(" · "),
    });
  }
  grouped.sort((a, b) => a.tick - b.tick);
  return grouped;
}

export interface HeatBucket {
  pos: number;
  count: number;
}

export type HeatStripe =
  | { dense: false; markers: TimelineMarker[] }
  | { dense: true; buckets: HeatBucket[] };

/**
 * Pure: markers + bar pixel width -> either the individual markers
 * (sparse) or density buckets (dense), when markers-per-pixel exceed 1
 * (i.e. `markers.length > barWidthPx`). Deterministic: one bucket per
 * pixel (`Math.floor(barWidthPx)`, minimum 1), so the same input always
 * produces the same buckets regardless of call order.
 */
export function computeHeatStripe(markers: TimelineMarker[], barWidthPx: number): HeatStripe {
  if (barWidthPx <= 0 || markers.length <= barWidthPx) {
    return { dense: false, markers };
  }
  const bucketCount = Math.max(1, Math.floor(barWidthPx));
  const counts = new Array<number>(bucketCount).fill(0);
  for (const m of markers) {
    const idx = Math.min(bucketCount - 1, Math.floor((m.pos / 100) * bucketCount));
    counts[idx] += 1;
  }
  const buckets: HeatBucket[] = [];
  for (let i = 0; i < bucketCount; i++) {
    if (counts[i] > 0) {
      buckets.push({ pos: +(((i + 0.5) / bucketCount) * 100).toFixed(2), count: counts[i] });
    }
  }
  return { dense: true, buckets };
}
