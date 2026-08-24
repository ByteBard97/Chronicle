/**
 * Rule-firing log (lane 31, ui-spec §3.7 second half): every
 * `rule_evaluated` trace record -- fired *and* evaluated-but-not-fired --
 * mapped to a render-ready row, plus a per-rule fire-frequency histogram
 * (the "fires-too-often detector"). The companion to lane 30's
 * `derived/socialDiff.ts` (which answers "what changed"); this module
 * answers "what did the rules *do*", including the negative rows the
 * panel's doctrine treats as first-class (a counter stuck at 3-of-4 is
 * visible, not silent).
 *
 * Pure, no Vue/store deps (the established idiom -- see socialDiff.ts):
 * takes `FrameRecord[]` in, returns rows/buckets out. Trace paging (the
 * feed.ts idiom -- sidecar `tick_offsets` + Range reads) lives in the
 * view layer, exactly like DiffScreen.vue reuses `stores/mapData.ts`
 * rather than duplicating a loader here.
 *
 * Real-shape note (`docs/frame-log-schema.md` §4, confirmed against
 * `runs/tier3-demo-01/trace.jsonl`): `rule_evaluated` is
 * `{ rule: string, inputs: object, fired: boolean, result: object | null }`
 * -- `result` is `null` whenever `fired` is `false`. A not-fired row's
 * `inputs` still carries the rule's current accumulator values (e.g.
 * `{ count: 1, threshold: 4, ... }`) -- `summarizeFields` below special-
 * cases a `count`/`threshold` pair into a "1/4" prefix so that value reads
 * as a ratio at a glance, per the panel's "3/4 thefts" pinned example,
 * instead of two separate `key: value` pairs.
 */
import type { FrameRecord } from "../log/types";

// ---------------------------------------------------------------------------
// Field summarization (shared by inputs/result display)

function formatFieldValue(value: unknown): string {
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(3);
  if (typeof value === "boolean") return value ? "true" : "false";
  if (value === null || value === undefined) return "—";
  if (Array.isArray(value)) return `[${value.length}]`;
  if (typeof value === "object") return "{…}";
  return String(value);
}

/**
 * One-line summary of an `inputs`/`result` object: `count`/`threshold`
 * (when both are numbers) collapse to a leading "N/M" ratio -- the
 * accumulator-value display the not-fired rows need -- followed by every
 * other field as `key: value`, comma-joined. `"—"` for an empty/absent
 * object (e.g. `result: null` on a not-fired row is handled by the
 * caller, not here).
 */
export function summarizeFields(obj: Record<string, unknown> | null | undefined): string {
  if (obj === null || obj === undefined) return "—";
  const keys = Object.keys(obj);
  if (keys.length === 0) return "—";

  const hasRatio = typeof obj.count === "number" && typeof obj.threshold === "number";
  const parts: string[] = [];
  if (hasRatio) parts.push(`${obj.count as number}/${obj.threshold as number}`);
  for (const key of keys) {
    if (hasRatio && (key === "count" || key === "threshold")) continue;
    parts.push(`${key}: ${formatFieldValue(obj[key])}`);
  }
  return parts.join(", ");
}

// ---------------------------------------------------------------------------
// Row shape

export interface RuleLogRow {
  key: string;
  tick: number;
  seq: number;
  rule: string;
  fired: boolean;
  inputs: Record<string, unknown>;
  result: Record<string, unknown> | null;
  /** Accumulator/inputs display -- always populated, fired or not. */
  inputsSummary: string;
  /** "not fired" for a negative row (result is always null there, per schema); the fired row's result summary otherwise. */
  resultSummary: string;
}

function asObject(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : null;
}

/**
 * Map one raw trace `FrameRecord` to a `RuleLogRow`, or `null` if it isn't
 * a `rule_evaluated` record. Mirrors `feedReader.ts`'s
 * `mapTraceRecordToFeedRow` skip-and-continue idiom for every other trace
 * record type.
 */
export function mapTraceRecordToRuleLogRow(record: FrameRecord): RuleLogRow | null {
  const p = record.payload;
  if (p.record_type !== "rule_evaluated") return null;

  const rule = typeof p.rule === "string" ? p.rule : "(unknown rule)";
  const fired = p.fired === true;
  const inputs = asObject(p.inputs) ?? {};
  const result = fired ? asObject(p.result) : null;

  return {
    key: `${record.tick}:${record.seq}`,
    tick: record.tick,
    seq: record.seq,
    rule,
    fired,
    inputs,
    result,
    inputsSummary: summarizeFields(inputs),
    resultSummary: fired ? summarizeFields(result) : "not fired",
  };
}

/** Map every `rule_evaluated` record in `records` to a row, in stream order. */
export function mapTraceRecordsToRuleLogRows(records: FrameRecord[]): RuleLogRow[] {
  const rows: RuleLogRow[] = [];
  for (const record of records) {
    const row = mapTraceRecordToRuleLogRow(record);
    if (row !== null) rows.push(row);
  }
  return rows;
}

// ---------------------------------------------------------------------------
// Filters (urlState.filters -- rule)

export interface RuleLogFilters {
  rule?: string;
}

export function filterRuleLogRows(rows: RuleLogRow[], filters: RuleLogFilters): RuleLogRow[] {
  return rows.filter((row) => {
    if (filters.rule && row.rule !== filters.rule) return false;
    return true;
  });
}

// ---------------------------------------------------------------------------
// Fire-frequency histogram (the fires-too-often detector)

export interface RuleHistogramBucket {
  rule: string;
  fired: number;
  notFired: number;
  total: number;
}

/**
 * Per-rule fired/evaluated-not-fired counts over `rows`, sorted by total
 * evaluations descending (busiest rule first -- the point of a
 * fires-too-often detector), then alphabetically for ties.
 */
export function computeRuleHistogram(rows: RuleLogRow[]): RuleHistogramBucket[] {
  const counts = new Map<string, { fired: number; notFired: number }>();
  for (const row of rows) {
    const entry = counts.get(row.rule) ?? { fired: 0, notFired: 0 };
    if (row.fired) {
      entry.fired += 1;
    } else {
      entry.notFired += 1;
    }
    counts.set(row.rule, entry);
  }
  return [...counts.entries()]
    .map(([rule, { fired, notFired }]) => ({ rule, fired, notFired, total: fired + notFired }))
    .sort((a, b) => b.total - a.total || a.rule.localeCompare(b.rule));
}
