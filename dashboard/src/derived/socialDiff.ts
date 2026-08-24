/**
 * Two-tick social-state diff (lane 30, ui-spec §3.7 first half): every
 * social-state delta between T2 (earlier) and T1 (later/playhead) across
 * beliefs, grudges, obligations, and reputations -- each row carrying a
 * signed Δ, the NPC(s) involved, a best-effort firing-rule chip, and the
 * triggering-event's (tick, seq) for a feed deep link.
 *
 * State reconstruction (packet-pinned, see lane-30 packet's "The two-tick
 * state problem"): `stores/mapData.ts` has no way to hold two `SocialState`s
 * at once (its `setTick` mutates one shared ref), so this module
 * reconstructs both states itself, directly from `reconstruct.ts`'s
 * exported primitives, given the run's full `eventRecords`/`traceRecords`
 * (keyframes excluded, per that store's contract). Of the two documented-
 * equivalent approaches (replay-from-scratch twice, or replay T2 then
 * replay forward through the (T2, T1] window), this module takes the
 * latter: `state2 = replayTo(empty, records<=t2, t2)`, then
 * `state1 = replayTo(state2, window, t1)` -- one fewer full replay, and it
 * naturally produces the `window` (T2, T1] slice this module needs anyway
 * for rule/event matching. No keyframe fast-path is used for either replay
 * (`eventRecords`/`traceRecords` don't carry keyframes) -- a deliberate,
 * documented choice, not something to "optimize" later: correct at this
 * data scale (small demo runs), not a general-purpose reader.
 *
 * Derived-at-T semantics (the panel's actual point, ui-spec §3.7): a
 * quiet day with zero trace records in the window can still show real
 * movement, because belief confidence and grudge severity/emotional/
 * evidentiary strength are time-decayed, read-time derivations
 * (`decayBelief`, and this module's own `grudgeAt` -- see below), not
 * stored values. Obligations and reputations have no analogous decay-at-
 * read in `chronicle/social.py` (obligation status is a discrete state
 * machine; `Reputation`'s alpha/beta are Bayesian counts with no time
 * term) -- their deltas compare raw stored values directly, which is
 * correct, not an oversight.
 *
 * FINDING (grudge decay not yet ported to the dashboard): lane 34 landed
 * `KeyframeGrudge` storage/replay in `reconstruct.ts` but not `social.py`'s
 * `grudge_at()`/`grudge_cooled()` read-time derivation (rule 13, ruled
 * 2026-08-23 under lane 18's R7) -- no `derived/*.ts` module has it yet.
 * This lane needs it for the "grudge formed/decayed-crossing" delta type,
 * so `grudgeAt`/`grudgeCooled` are ported here (verbatim formula/constants
 * from `chronicle/social.py:72-79,281-299`) rather than added to
 * `derived/decay.ts` or `derived/constants.ts`, which are outside this
 * lane's file boundary (edit list is `router/index.ts` and
 * `ViewSwitcher.vue` only). Filed for the coordinator: a future lane
 * touching grudges elsewhere should hoist this into a shared module
 * instead of a second independent port.
 *
 * Role rows (lane 52, additive, ui-spec §3.10: "role rows join the diff
 * panel"): `"role"` added to `DiffRowType` -- a vacancy/succession row per
 * role whose roster-level state (`SocialState.roles`, folded by
 * `reconstruct.ts`'s `applyRoleEvent` as part of this module's existing
 * full, unwindowed `replayTo` calls -- no keyframe-window hazard here,
 * unlike `RunReader`) differs between T2 and T1, plus one row per
 * `status_changed(duty_lapsed)` event firing inside the (T2, T1] window
 * (duty lapse has no roster-level representation to diff -- see
 * `derived/roles.ts`'s header -- so it's read directly off `window`
 * instead). `toEventLink` (below) can't be reused for either: role events
 * are EVENTS-stream payloads keyed by `event_type`, not `record_type`, so
 * routing them through it would produce `recordType: "unknown"` on every
 * row -- `toRoleEventLink` builds the link off `event_type` instead.
 * `DiffRow.vue`'s `TYPE_LABEL` and `DiffFilterBar.vue`'s `TYPE_OPTIONS` are
 * both exhaustive over `DiffRowType` and needed a one-key additive edit
 * each to keep `vue-tsc`/the filter list correct -- filed as an in-bounds
 * finding (same "verify and note" precedent as this lane's `reconstruct.ts`/
 * `runReader.ts` extension), not a restructure of either file.
 *
 * Rule-chip matching (packet: "the exact matching heuristic is left to
 * your judgment... not hardcoded to specific rule name strings"): a
 * delta's underlying trace record (e.g. `grudge_formed`) and the
 * `rule_evaluated` record that produced it share identifying id values
 * (confirmed against `runs/tier3-demo-01`: a `grudge_formed` at tick 2 is
 * immediately followed, same tick, by a `rule_evaluated` whose `result`
 * contains that exact grudge id). `matchRuleForEvent` below is generic:
 * it scans every string value nested in a same-tick, `fired: true`
 * `rule_evaluated` record's `inputs`/`result` for overlap with a
 * caller-supplied set of ids (the delta's own subject/object ids) --
 * no rule name is ever hardcoded into the matching logic itself.
 */
import type { FrameRecord, KeyframeGrudge, KeyframeRole } from "../log/types";
import { emptySocialState, grudgeKey, replayTo, reputationKey, rumorKey, type SocialState } from "../log/reconstruct";
import { decayBelief, decayValue } from "./decay";
import { rumorStageAt } from "./rumorStage";

// ---------------------------------------------------------------------------
// Grudge decay-at-read (chronicle/social.py:72-79,281-299 -- see header finding)

const GRUDGE_EMOTIONAL_WEIGHT = 0.5;
const GRUDGE_EVIDENTIARY_WEIGHT = 0.5;
const GRUDGE_EMOTIONAL_HALF_LIFE = 672.0;
const GRUDGE_EVIDENTIARY_HALF_LIFE = 336.0;

/** `chronicle/social.py`'s `grudge_at()`, ported verbatim: decay from `last_rehearsed`, severity recomputed from the decayed strengths. */
export function grudgeAt(grudge: KeyframeGrudge, atTick: number): KeyframeGrudge {
  const elapsed = Math.max(0, atTick - grudge.last_rehearsed);
  const emotional = decayValue(grudge.emotional_strength, elapsed, GRUDGE_EMOTIONAL_HALF_LIFE);
  const evidentiary = decayValue(grudge.evidentiary_strength, elapsed, GRUDGE_EVIDENTIARY_HALF_LIFE);
  return {
    ...grudge,
    emotional_strength: emotional,
    evidentiary_strength: evidentiary,
    severity: Math.min(1, GRUDGE_EMOTIONAL_WEIGHT * emotional + GRUDGE_EVIDENTIARY_WEIGHT * evidentiary),
  };
}

/** `chronicle/social.py`'s `grudge_cooled()`: decayed severity below the grudge's own forgiveness threshold. */
export function grudgeCooled(grudge: KeyframeGrudge, atTick: number): boolean {
  return grudgeAt(grudge, atTick).severity < grudge.forgiveness_threshold;
}

// ---------------------------------------------------------------------------
// Row shape

export type DiffRowType = "belief" | "grudge" | "obligation" | "reputation" | "role";

/** The `rule_evaluated` record best-effort matched as this delta's cause. */
export interface DiffRuleChip {
  rule: string;
  tick: number;
  seq: number;
}

/** The trace/event record identified as this delta's direct trigger, or `null` for a pure-decay row. */
export interface DiffEventLink {
  tick: number;
  seq: number;
  recordType: string;
}

export interface DiffRow {
  key: string;
  type: DiffRowType;
  /** Every NPC id involved, for the NPC filter (mirrors feedReader's `participants` idiom). */
  npcs: string[];
  claimId: string | null;
  /** Short one-line subject label, e.g. "grudge adrianne -> ulfberth (obligation_violated)". */
  label: string;
  /** T2's (earlier) derived-at-T value. 0 (belief/grudge) or a documented neutral baseline (reputation) when the subject didn't exist yet. */
  before: number;
  /** T1's (later/playhead) derived-at-T value. */
  after: number;
  /** after - before -- positive means "increased from T2 to T1". */
  delta: number;
  /** One-line human detail, e.g. a stage or status transition, or a formatted before/after pair. */
  detail: string;
  rule: DiffRuleChip | null;
  event: DiffEventLink | null;
}

// ---------------------------------------------------------------------------
// Generic rule-chip matching (see header)

function collectStrings(value: unknown, out: Set<string>): void {
  if (typeof value === "string") {
    out.add(value);
  } else if (Array.isArray(value)) {
    for (const v of value) collectStrings(v, out);
  } else if (value !== null && typeof value === "object") {
    for (const v of Object.values(value)) collectStrings(v, out);
  }
}

/**
 * Best-effort: the `fired: true` `rule_evaluated` record at exactly `tick`
 * whose `inputs`/`result` share a string value with `ids` -- the closest
 * (highest `seq`) match wins when more than one qualifies. `null` if no
 * `rule_evaluated` record at that tick mentions any of `ids` (a pure-decay
 * row, or a record type this heuristic doesn't recognize).
 */
export function matchRuleForEvent(records: FrameRecord[], tick: number, ids: string[]): DiffRuleChip | null {
  const idSet = new Set(ids.filter((id) => id.length > 0));
  if (idSet.size === 0) return null;
  let best: FrameRecord | null = null;
  for (const record of records) {
    if (record.tick !== tick) continue;
    if (record.payload.record_type !== "rule_evaluated") continue;
    if (record.payload.fired !== true) continue;
    const values = new Set<string>();
    collectStrings(record.payload.inputs, values);
    collectStrings(record.payload.result, values);
    const overlaps = [...idSet].some((id) => values.has(id));
    if (!overlaps) continue;
    if (best === null || record.seq > best.seq) best = record;
  }
  if (best === null) return null;
  const rule = best.payload.rule;
  return typeof rule === "string" ? { rule, tick: best.tick, seq: best.seq } : null;
}

/** The last (highest tick, then seq) record in `records` for which `matches` is true, or `null`. */
function lastMatch(records: FrameRecord[], matches: (r: FrameRecord) => boolean): FrameRecord | null {
  let best: FrameRecord | null = null;
  for (const record of records) {
    if (!matches(record)) continue;
    if (best === null || record.tick > best.tick || (record.tick === best.tick && record.seq > best.seq)) {
      best = record;
    }
  }
  return best;
}

function toEventLink(record: FrameRecord | null): DiffEventLink | null {
  if (record === null) return null;
  const recordType = record.payload.record_type;
  return { tick: record.tick, seq: record.seq, recordType: typeof recordType === "string" ? recordType : "unknown" };
}

const EPSILON = 1e-9;

// ---------------------------------------------------------------------------
// Belief rows

function beliefRows(state1: SocialState, state2: SocialState, window: FrameRecord[]): DiffRow[] {
  const rows: DiffRow[] = [];
  const ids = new Set([...state1.beliefs.keys(), ...state2.beliefs.keys()]);
  for (const id of ids) {
    const b1 = state1.beliefs.get(id) ?? null;
    const b2 = state2.beliefs.get(id) ?? null;
    const base = b1 ?? b2;
    if (base === null) continue; // unreachable (id came from one of the two maps), narrows for TS.

    const decayed1 = b1 !== null ? decayBelief(b1, state1.tick) : null;
    const decayed2 = b2 !== null ? decayBelief(b2, state2.tick) : null;
    const before = decayed2?.confidence ?? 0;
    const after = decayed1?.confidence ?? 0;

    const rumor1 = b1 !== null ? (state1.rumors.get(rumorKey(b1.holder_id, b1.claim_id, b1.variant_id)) ?? null) : null;
    const rumor2 = b2 !== null ? (state2.rumors.get(rumorKey(b2.holder_id, b2.claim_id, b2.variant_id)) ?? null) : null;
    const stage1 = rumorStageAt(rumor1, b1, state1.tick);
    const stage2 = rumorStageAt(rumor2, b2, state2.tick);

    const isNew = b2 === null;
    const stageChanged = stage1 !== stage2;
    const confidenceChanged = Math.abs(after - before) > EPSILON;
    if (!isNew && !stageChanged && !confidenceChanged) continue;

    const event = toEventLink(
      lastMatch(
        window,
        (r) =>
          (r.payload.record_type === "belief_formed" && r.payload.belief_id === id) ||
          (r.payload.record_type === "belief_corroborated" && r.payload.belief_id === id) ||
          (r.payload.record_type === "transmitted" && r.payload.hearer_belief_id === id) ||
          (r.payload.record_type === "supersession" && r.payload.winner_belief_id === id),
      ),
    );
    const rule = event !== null ? matchRuleForEvent(window, event.tick, [id, base.claim_id, base.holder_id]) : null;

    rows.push({
      key: `belief:${id}`,
      type: "belief",
      npcs: [base.holder_id],
      claimId: base.claim_id,
      label: `belief ${id} (${base.claim_id})`,
      before,
      after,
      delta: after - before,
      detail: stageChanged
        ? `${stage2} → ${stage1}`
        : `confidence ${before.toFixed(3)} → ${after.toFixed(3)}`,
      rule,
      event,
    });
  }
  return rows;
}

// ---------------------------------------------------------------------------
// Grudge rows

function grudgeRows(state1: SocialState, state2: SocialState, window: FrameRecord[]): DiffRow[] {
  const rows: DiffRow[] = [];
  const keys = new Set([...state1.grudges.keys(), ...state2.grudges.keys()]);
  for (const key of keys) {
    const g1 = state1.grudges.get(key) ?? null;
    const g2 = state2.grudges.get(key) ?? null;
    const base = g1 ?? g2;
    if (base === null) continue;

    const before = g2 !== null ? grudgeAt(g2, state2.tick).severity : 0;
    const after = g1 !== null ? grudgeAt(g1, state1.tick).severity : 0;
    const threshold = base.forgiveness_threshold;
    const wasActive = g2 !== null ? !grudgeCooled(g2, state2.tick) : false;
    const isActive = g1 !== null ? !grudgeCooled(g1, state1.tick) : false;

    const isNew = g2 === null;
    const crossed = g2 !== null && g1 !== null && wasActive !== isActive;
    const changed = Math.abs(after - before) > EPSILON;
    if (!isNew && !crossed && !changed) continue;

    const event = toEventLink(
      lastMatch(window, (r) => r.payload.record_type === "grudge_formed" && grudgeKey(String(r.payload.holder_id), String(r.payload.target_id)) === key),
    );
    const rule = event !== null ? matchRuleForEvent(window, event.tick, [base.id, base.holder_id, base.target_id, base.source_belief_id]) : null;

    rows.push({
      key: `grudge:${key}`,
      type: "grudge",
      npcs: [base.holder_id, base.target_id],
      claimId: null,
      label: `grudge ${base.holder_id} → ${base.target_id} (${base.grievance_type})`,
      before,
      after,
      delta: after - before,
      detail: crossed
        ? `forgiveness threshold ${threshold.toFixed(2)}: ${wasActive ? "active" : "cooled"} → ${isActive ? "active" : "cooled"}`
        : `severity ${before.toFixed(3)} → ${after.toFixed(3)}`,
      rule,
      event,
    });
  }
  return rows;
}

// ---------------------------------------------------------------------------
// Obligation rows

/**
 * A synthetic signed value for an obligation's status, so a discrete state
 * machine still produces the panel's "every delta has a signed Δ" contract:
 * a favorable resolution (fulfilled) is positive, an adverse one
 * (violated) is negative, `active`/never-existed is the 0 baseline, and
 * excused/expired sit between (excused closer to neutral than violated,
 * per `chronicle/social.py`'s doc that `excuse` mitigates the sanction).
 * A documented design choice, not a value chronicle/social.py itself
 * defines.
 */
const OBLIGATION_STATUS_VALUE: Record<string, number> = {
  active: 0,
  fulfilled: 1,
  excused: 0.5,
  expired: -0.5,
  violated: -1,
};

function obligationValue(status: string): number {
  return OBLIGATION_STATUS_VALUE[status] ?? 0;
}

function obligationRows(state1: SocialState, state2: SocialState, window: FrameRecord[]): DiffRow[] {
  const rows: DiffRow[] = [];
  const ids = new Set([...state1.obligations.keys(), ...state2.obligations.keys()]);
  for (const id of ids) {
    const o1 = state1.obligations.get(id) ?? null;
    const o2 = state2.obligations.get(id) ?? null;
    const base = o1 ?? o2;
    if (base === null) continue;

    const isNew = o2 === null;
    const statusChanged = o1 !== null && o2 !== null && o1.status !== o2.status;
    if (!isNew && !statusChanged) continue;

    const before = o2 !== null ? obligationValue(o2.status) : 0;
    const after = o1 !== null ? obligationValue(o1.status) : 0;

    const event = toEventLink(
      lastMatch(
        window,
        (r) =>
          (r.payload.record_type === "obligation_issued" && r.payload.id === id) ||
          (r.payload.record_type === "obligation_resolved" && r.payload.obligation_id === id),
      ),
    );
    const rule = event !== null ? matchRuleForEvent(window, event.tick, [id, base.issuer_id, base.debtor_id]) : null;

    rows.push({
      key: `obligation:${id}`,
      type: "obligation",
      npcs: [base.issuer_id, base.debtor_id],
      claimId: null,
      label: `obligation ${id} (${base.action})`,
      before,
      after,
      delta: after - before,
      detail: `${o2?.status ?? "(none)"} → ${o1?.status ?? "(none)"}`,
      rule,
      event,
    });
  }
  return rows;
}

// ---------------------------------------------------------------------------
// Reputation rows

/** `alpha / (alpha + beta)` -- the Beta distribution's mean, the natural single-number summary of a Reputation. */
function reputationMean(r: { alpha: number; beta: number }): number {
  return r.alpha / (r.alpha + r.beta);
}

/** `chronicle/social.py`'s `REPUTATION_PRIOR_ALPHA`/`REPUTATION_PRIOR_BETA` (both 1.0) -- the neutral prior mean for a reputation that doesn't exist yet. */
const REPUTATION_PRIOR_MEAN = 0.5;

function reputationRows(state1: SocialState, state2: SocialState, window: FrameRecord[]): DiffRow[] {
  const rows: DiffRow[] = [];
  const keys = new Set([...state1.reputations.keys(), ...state2.reputations.keys()]);
  for (const key of keys) {
    const r1 = state1.reputations.get(key) ?? null;
    const r2 = state2.reputations.get(key) ?? null;
    const base = r1 ?? r2;
    if (base === null) continue;

    const before = r2 !== null ? reputationMean(r2) : REPUTATION_PRIOR_MEAN;
    const after = r1 !== null ? reputationMean(r1) : REPUTATION_PRIOR_MEAN;
    const isNew = r2 === null;
    const changed = Math.abs(after - before) > EPSILON;
    if (!isNew && !changed) continue;

    const event = toEventLink(
      lastMatch(
        window,
        (r) =>
          r.payload.record_type === "reputation_updated" &&
          reputationKey(String(r.payload.observer_id), String(r.payload.subject_id), String(r.payload.context)) === key,
      ),
    );
    const rule = event !== null ? matchRuleForEvent(window, event.tick, [base.observer_id, base.subject_id, base.context]) : null;

    rows.push({
      key: `reputation:${key}`,
      type: "reputation",
      npcs: [base.observer_id, base.subject_id],
      claimId: null,
      label: `reputation ${base.observer_id} → ${base.subject_id} (${base.context})`,
      before,
      after,
      delta: after - before,
      detail: `mean ${before.toFixed(3)} → ${after.toFixed(3)}`,
      rule,
      event,
    });
  }
  return rows;
}

// ---------------------------------------------------------------------------
// Role rows (lane 52 -- see header)

/** `record.payload.event_type`-keyed event link -- role events carry no `record_type` (see header). */
function toRoleEventLink(record: FrameRecord | null): DiffEventLink | null {
  if (record === null) return null;
  const eventType = record.payload.event_type;
  return { tick: record.tick, seq: record.seq, recordType: typeof eventType === "string" ? eventType : "unknown" };
}

function roleHolderLabel(holderId: string | null | undefined): string {
  return holderId ?? "(vacant)";
}

function rosterRows(state1: SocialState, state2: SocialState, window: FrameRecord[]): DiffRow[] {
  const rows: DiffRow[] = [];
  const ids = new Set([...state1.roles.keys(), ...state2.roles.keys()]);
  for (const id of ids) {
    const r1: KeyframeRole | null = state1.roles.get(id) ?? null;
    const r2: KeyframeRole | null = state2.roles.get(id) ?? null;
    const base = r1 ?? r2;
    if (base === null) continue;

    const isNew = r2 === null;
    const holderChanged = (r1?.holder_id ?? null) !== (r2?.holder_id ?? null);
    if (!isNew && !holderChanged) continue;

    const before = r2 !== null ? (r2.holder_id !== null ? 1 : -1) : 0;
    const after = r1 !== null ? (r1.holder_id !== null ? 1 : -1) : 0;

    const kind: "installed" | "vacancy" | "succession" = isNew ? "installed" : r1?.holder_id === null ? "vacancy" : "succession";

    const event = toRoleEventLink(
      lastMatch(window, (r) => {
        const eventType = r.payload.event_type;
        if (eventType === "role_installed") return r.payload.role_id === id;
        if (eventType === "npc_died") return kind === "vacancy" && r.payload.npc_id === r2?.holder_id;
        if (eventType === "status_changed") return r.payload.status_kind === "role_appointed" && r.payload.detail === id;
        return false;
      }),
    );
    const rule =
      event !== null
        ? matchRuleForEvent(window, event.tick, [id, r1?.holder_id, r2?.holder_id].filter((s): s is string => typeof s === "string"))
        : null;

    rows.push({
      key: `role:${id}`,
      type: "role",
      npcs: [r1?.holder_id, r2?.holder_id].filter((s): s is string => typeof s === "string"),
      claimId: null,
      label: `role ${base.title} (${id})`,
      before,
      after,
      delta: after - before,
      detail:
        kind === "installed"
          ? `installed, holder ${roleHolderLabel(r1?.holder_id)}`
          : `${roleHolderLabel(r2?.holder_id)} → ${roleHolderLabel(r1?.holder_id)}`,
      rule,
      event,
    });
  }
  return rows;
}

/**
 * One row per `status_changed(duty_lapsed)` event firing inside `window` --
 * duty lapse has no roster-level state to diff (see `derived/roles.ts`'s
 * header on why `Role` carries no lapse field), so this reads the raw
 * event directly and best-effort-correlates it to whichever known role
 * (from either snapshot) currently lists a duty by that name.
 */
function dutyLapseRows(state1: SocialState, state2: SocialState, window: FrameRecord[]): DiffRow[] {
  const rows: DiffRow[] = [];
  const knownRoles = [...state1.roles.values(), ...state2.roles.values()];
  for (const record of window) {
    if (record.payload.event_type !== "status_changed") continue;
    if (record.payload.status_kind !== "duty_lapsed") continue;
    const dutyName = record.payload.detail;
    const npcId = record.payload.npc_id;
    if (typeof dutyName !== "string" || typeof npcId !== "string") continue;
    const role = knownRoles.find((r) => r.duties.some((d) => d.name === dutyName));
    const roleLabel = role !== undefined ? `${role.title} (${role.role_id})` : "(unknown role)";

    rows.push({
      key: `role-duty-lapse:${role?.role_id ?? "unknown"}:${dutyName}:${record.tick}:${record.seq}`,
      type: "role",
      npcs: [npcId],
      claimId: null,
      label: `duty lapsed: ${dutyName} (${roleLabel})`,
      before: 0,
      after: -1,
      delta: -1,
      detail: `${npcId}'s ${dutyName} lapsed`,
      rule: matchRuleForEvent(window, record.tick, [role?.role_id, npcId].filter((s): s is string => typeof s === "string")),
      event: { tick: record.tick, seq: record.seq, recordType: "status_changed" },
    });
  }
  return rows;
}

function roleRows(state1: SocialState, state2: SocialState, window: FrameRecord[]): DiffRow[] {
  return [...rosterRows(state1, state2, window), ...dutyLapseRows(state1, state2, window)];
}

// ---------------------------------------------------------------------------
// Public API

export interface SocialDiffFilters {
  npc?: string;
  rule?: string;
  type?: string;
}

export function filterDiffRows(rows: DiffRow[], filters: SocialDiffFilters): DiffRow[] {
  return rows.filter((row) => {
    if (filters.npc && !row.npcs.includes(filters.npc)) return false;
    if (filters.rule && row.rule?.rule !== filters.rule) return false;
    if (filters.type && row.type !== filters.type) return false;
    return true;
  });
}

function sortRows(rows: DiffRow[]): DiffRow[] {
  return [...rows].sort((a, b) => {
    const ta = a.event?.tick ?? Infinity;
    const tb = b.event?.tick ?? Infinity;
    if (ta !== tb) return ta - tb;
    const sa = a.event?.seq ?? Infinity;
    const sb = b.event?.seq ?? Infinity;
    if (sa !== sb) return sa - sb;
    if (a.type !== b.type) return a.type.localeCompare(b.type);
    return a.key.localeCompare(b.key);
  });
}

/**
 * The full two-tick diff: reconstructs state at `t2` and `t1` from
 * `allRecords` (a run's full `eventRecords` + `traceRecords`, keyframes
 * excluded -- see `stores/mapData.ts`), then compares beliefs, grudges,
 * obligations, and reputations across them. `t2` should be earlier than
 * `t1` (the panel's convention: T1 is the playhead, T2 is one game-day
 * earlier per ADR-0010); if `t2 >= t1` the (T2, T1] window is empty and
 * every row falls back to a same-tick comparison of decayed values (still
 * well-defined, just not the panel's intended reading).
 */
export function computeSocialDiff(allRecords: FrameRecord[], t1: number, t2: number): DiffRow[] {
  const upToT2 = allRecords.filter((r) => r.tick <= t2);
  const state2 = replayTo(emptySocialState(-1), upToT2, t2);
  const window = allRecords.filter((r) => r.tick > t2 && r.tick <= t1);
  const state1 = replayTo(state2, window, t1);

  return sortRows([
    ...beliefRows(state1, state2, window),
    ...grudgeRows(state1, state2, window),
    ...obligationRows(state1, state2, window),
    ...reputationRows(state1, state2, window),
    ...roleRows(state1, state2, window),
  ]);
}
