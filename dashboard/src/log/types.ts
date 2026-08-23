/**
 * Frame-log types (docs/frame-log-schema.md v1). This module is the
 * TypeScript mirror of that document's envelope, payload catalog, keyframe
 * shape, and the two JSON files (run registry + per-run sidecar index).
 *
 * Reader discipline (schema §7): "Readers ignore unknown record types,
 * unknown payload fields, and unknown keyframe keys — skip-and-continue,
 * never error." That is why every payload type below is typed loosely
 * (known fields plus an index signature) rather than as a closed/exact
 * type — an exact type would make TypeScript itself reject a future
 * `schema_version: 2` field the runtime is supposed to tolerate. The
 * *runtime* tolerance (skip-and-continue) lives in reconstruct.ts and
 * jsonl.ts, not here; these types just avoid fighting it.
 */

// ---------------------------------------------------------------------------
// Envelope (schema §2)

export type StreamName = "events" | "trace";

/** A payload object: known fields vary by record type; unknown fields pass through untyped. */
export type Payload = Record<string, unknown>;

export interface FrameRecord<P extends Payload = Payload> {
  schema_version: number;
  seed_id: string;
  save_uuid: string;
  generation: number;
  tick: number;
  stream: StreamName;
  seq: number;
  payload: P;
}

// ---------------------------------------------------------------------------
// roll_key (ADR-0009 — members and order owned there, cited here)

export interface RollKey {
  seed_id: string;
  purpose: string;
  tick: number;
  site: string;
  participants: string[];
  draw: number;
}

/** Fields common to every roll-bearing trace record (schema §4). */
export interface RollBearing {
  roll_key: RollKey;
  value: number; // [0, 1)
  threshold: number; // [0, 1)
  outcome: string;
}

// ---------------------------------------------------------------------------
// Events stream payloads (schema §3)

export type EventKind =
  | "npc_died"
  | "crime_witnessed"
  | "rumor_heard"
  | "escalation_warning" // reserved (Tier 3)
  | "schedule_rewrite" // reserved (Tier 4a)
  | "role_lapse"; // reserved (Tier 5)

export interface EventOrigin {
  kind: "scenario" | "console" | "adapter";
  detail: string;
}

export interface EventPayload extends Payload {
  event_type: string;
  gamets: number;
  wall_ts: number;
  origin: EventOrigin | null;
}

/** The keyframe record: `payload.record_type === "keyframe"`, on the events stream (schema §5). */
export interface KeyframePayload extends Payload {
  record_type: "keyframe";
  state: KeyframeState;
}

/**
 * The keyframe's `state` object, per schema §5. Every key is optional at the
 * type level — additive-per-tier extension (schema §5's closing paragraph)
 * means an M1-era reader will see keyframes without `reputations`/`schedules`
 * populated yet, and an M3-era log may carry keys this type doesn't name at
 * all; the index signature is what lets those pass through unrejected.
 *
 * Field names inside each record mirror chronicle/claims.py, social.py, and
 * schedule.py "exactly" per the schema doc — but that document deliberately
 * doesn't reproduce every dataclass field, so these are typed as loose
 * records (unknown-keyframe-key tolerance, schema §7) rather than exact
 * mirrors of the Python dataclasses.
 */
export interface KeyframeState {
  claims?: KeyframeClaim[];
  variants?: KeyframeVariant[];
  beliefs?: KeyframeBelief[];
  evidence?: KeyframeEvidence[];
  rumor_states?: KeyframeRumorState[];
  relationships?: Record<string, unknown>[];
  grudges?: Record<string, unknown>[];
  obligations?: Record<string, unknown>[];
  reputations?: Record<string, unknown>[];
  schedules?: Record<string, unknown>[];
  // Additive-per-tier keys (rule-registry accumulators, schedule overrides,
  // encounter weights, roles) land here as further optional properties as
  // their tiers arrive — the index signature covers them meanwhile.
  [extra: string]: unknown;
}

export interface KeyframeClaim {
  id: string;
  kind: string;
  slots: Record<string, string | null>;
  canonical_event_key: { save_uuid: string; generation: number; seq: number };
  truth_status: string;
  [extra: string]: unknown;
}

export interface KeyframeVariant {
  id: string;
  claim_id: string;
  parent_variant_id: string | null;
  slots: Record<string, string | null>;
  mutated_slot: string | null;
  gamets: number;
  [extra: string]: unknown;
}

export interface KeyframeBelief {
  id: string;
  holder_id: string;
  claim_id: string;
  variant_id: string | null;
  confidence: number;
  verbatim_strength: number;
  gist_strength: number;
  first_learned: number;
  last_rehearsed: number;
  [extra: string]: unknown;
}

export interface KeyframeEvidence {
  id: string;
  belief_id: string;
  evidence_type: string;
  source_id: string;
  predecessor_belief_id: string | null;
  gamets: number;
  strength: number;
  [extra: string]: unknown;
}

export interface KeyframeRumorState {
  npc_id: string;
  claim_id: string;
  variant_id: string | null;
  stage: "heard" | "repeated" | string;
  first_heard: number;
  last_heard: number;
  last_told: number | null;
  exposure_count: number;
  distinct_source_count: number;
  [extra: string]: unknown;
}

// ---------------------------------------------------------------------------
// Trace stream payloads (schema §4)

export type TraceRecordType =
  | "belief_formed"
  | "belief_corroborated"
  | "encounter_rolled"
  | "transmitted"
  | "nothing_salient"
  | "mutation_applied"
  | "supersession"
  | "transmission_declined" // reserved (Tier 3)
  | "rule_evaluated"
  | "threshold_crossed";

export interface TracePayload extends Payload {
  record_type: string;
}

// ---------------------------------------------------------------------------
// The run registry (schema §6, `runs/index.json`)

export interface RunRegistryBranch {
  save_uuid: string;
  generation: number;
}

export interface RunRegistryTickRange {
  start: number;
  end: number | null;
}

export interface RunRegistryStreams {
  events: string;
  trace: string;
}

export interface RunRegistryEntry {
  run_id: string;
  seed_id: string;
  created_wall_ts: number;
  branches: RunRegistryBranch[];
  tick_range: RunRegistryTickRange;
  streams: RunRegistryStreams;
  status: "running" | "complete" | string;
}

export interface RunRegistryFile {
  schema_version: number;
  runs: RunRegistryEntry[];
}

// ---------------------------------------------------------------------------
// The per-run sidecar index (schema §6, `runs/<run_id>/index.json`)

export interface SidecarKeyframeOffset {
  tick: number;
  offset: number;
}

export interface SidecarStreamIndex {
  tick_offsets: Record<string, number>;
  keyframe_offsets?: SidecarKeyframeOffset[];
}

export interface SidecarIndexFile {
  schema_version: number;
  streams: {
    events: SidecarStreamIndex;
    trace: SidecarStreamIndex;
  };
}
