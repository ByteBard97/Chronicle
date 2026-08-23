---
status: draft-for-review
schema_version: 1
date: 2026-08-22
---

# Frame-log schema, v1

The payload catalog for Chronicle's frame log. `docs/ui-spec.md` §1.1 froze
the *envelope* and physical layout; this document defines the *payloads*.
Written once, versioned forever: the UI iterates, the log format does not
(ui-doctrines D22). Evolution is additive-only — see §7.

Authorities this document cites but does not override: ui-spec §1.1
(envelope, physical layout, three-things rule), ADR-0009 (the `roll_key`
substructure — members and order are owned there), ADR-0010 (tick quantum),
`docs/scenario-ladder.md` §2 (which machinery produces what, at which tier).

---

## 1. Physical layout (restated from ui-spec §1.1 — verbatim contract)

One directory per run — `runs/<run_id>/` — with physically split stream
files: `events.jsonl` (small; what the world did) and `trace.jsonl`
(large; why the sim did it). Alongside them, a sidecar index (`index.json`:
per stream, tick → byte offset, plus keyframe offsets), written
incrementally by the sim and rebuildable by a scan — pure acceleration.
`runs/index.json` is the run registry (ui-spec §1.2) maintained by the
writer. `runs/` is gitignored; the path is overridable via the
`CHRONICLE_RUNS_DIR` env var, shared by pytest and the dashboard.

- **Record envelope (frozen, verbatim):** `(schema_version, seed_id,
  save_uuid, generation, tick, stream, seq, payload)`. The branch key
  `(save_uuid, generation)` is present from record one even though headless
  v0.1 runs a single branch.
- **Record framing:** newline-delimited JSON, one record per line. Readers
  treat a non-terminated tail as not-yet-written — tailing a growing log
  must never yield a torn record.
- **Three-things rule (ui-spec §1.1):** the log contains exactly (1)
  inputs — canonical events; (2) derivations with their inputs — the
  trace; (3) acceleration structures — keyframes and indexes, rebuildable
  by scanning (1)+(2). Nothing else.
- **Writer flush policy (liveness contract):** the writer flushes after
  every tick's record batch. LIVE-tailing latency is the reader's polling
  cadence, never the writer's buffer length; readers may assume a committed
  record is visible within one tick of emission.
- **Index writes** are atomic: write temp file, rename into place.

## 2. Envelope fields

| Field | Type | Unit / note |
|---|---|---|
| `schema_version` | int | unitless; `1` for this document |
| `seed_id` | string | unitless; the world's statistical identity (ADR-0009). A/B runs and forks share it |
| `save_uuid` | string | unitless; branch key part 1 (ADR-0004) |
| `generation` | int | unitless; branch key part 2 |
| `tick` | int | game-hours since run epoch (ADR-0010: 1 tick = 1 gamets = 1 game-hour) |
| `stream` | string | `"events"` \| `"trace"` |
| `seq` | int | unitless; ordering within the stream — see below |
| `payload` | object | per §3–§6 |

`seq` discipline: for canonical-event records, `seq` **is** the `Event.seq`
of the wrapped event (monotonic per branch, per `events.py` — claims
reference events by `(save_uuid, generation, seq)`, so the envelope and the
claim layer must agree). For trace records, `seq` is monotonic within the
`trace.jsonl` file, independent of event seqs.

## 3. Events stream payloads (`stream: "events"`)

Every event payload carries `event_type` plus the bitemporal coordinates
`events.py` mandates, then kind-specific fields mirroring the `Event`
dataclasses.

Common event fields:

| Field | Type | Unit / note |
|---|---|---|
| `event_type` | string | one of the kinds below |
| `gamets` | number | game-hours; valid time (bitemporal rule — mandatory, never null) |
| `wall_ts` | number | seconds since Unix epoch; transaction time (mandatory, never null) |
| `origin` | object \| null | how the event entered: `{"kind": "scenario" \| "console" \| "adapter", "detail": string}`. Null means engine-internal. This is the injection provenance the console needs — an origin field, not a separate event kind, because injected events are ordinary canonical events in every other respect |

Event kinds:

| `event_type` | Producer tier | Fields (beyond common) |
|---|---|---|
| `npc_died` | 0 | `npc_id` (string), `cause` (string), `killer_id` (string \| null), `location_id` (string \| null) |
| `crime_witnessed` | 0 | `witness_id` (string), `perpetrator_id` (string), `crime_type` (string), `location_id` (string \| null) |
| `rumor_heard` | 0 | `hearer_id` (string), `source_id` (string), `rumor_id` (string), `content` (string) |
| `escalation_warning` | 3 — **reserved** | warning escalations materialized as events before their claims propagate (ladder T3.1: no orphan beliefs). Fields defined when the threshold machinery lands |
| `schedule_rewrite` | 4a — **reserved** | the rewrite as an event with a causal link to its trigger (ladder T4a.1). Fields defined with schedule write-back |
| `role_lapse` | 5 — **reserved** | duty-lapse effects as events (ladder T5.1). Fields defined with roles |

Reserved kinds are schema commitments, not machinery: writers must not emit
them before their tier; readers must tolerate them (§7).

The keyframe record (§5) also appears on this stream.

## 4. Trace stream payloads (`stream: "trace"`)

One record type per derivation or negative result (ui-doctrines D7:
non-events are records). Common field: `record_type`. Roll-bearing records
embed `roll_key` — **members and order owned by ADR-0009**: `seed_id`,
`purpose`, `tick`, `site`, `participants`, `draw`, plus `value` (number,
[0,1)), `threshold` (number, [0,1)), and `outcome` (string, record-specific).

| `record_type` | Producer tier | Fields (beyond `record_type`) |
|---|---|---|
| `belief_formed` | 0 | `belief_id`, `claim_id`, `holder_id`, `evidence_id`, `claim_kind`, `claim_slots` (object), `canonical_event_key` (`{save_uuid, generation, seq}`) — the witness-path derivation (claim + belief + witnessed evidence from one canonical event) |
| `belief_corroborated` | 0 | `belief_id`, `source_belief_id`, `evidence_id`, `confidence_before`, `confidence_after` (numbers, [0,1]) — noisy-or rise, distinct-source gated (rule 7) |
| `encounter_rolled` | 1 | `roll_key` (purpose `encounter.co-presence`), `location_id`, `npc_a`, `npc_b`, `encountered` (boolean). `encountered: false` is the rolled-against negative row, rendered with equal weight |
| `transmitted` | 1 | `claim_id`, `teller_id`, `teller_belief_id`, `hearer_id`, `hearer_belief_id`, `evidence_id`, `variant` (`{variant_id, parent_variant_id, slots, mutated_slot: string \| null}`), `location_id`. The variant is created on every transmission (mutated or not) per `claims.retell()` |
| `nothing_salient` | 1 | `location_id`, `npc_a`, `npc_b`, `claim_id` (string \| null), `reason` (`"both-informed"` \| `"neither-informed"`) — encounter fired, `propagate.teller_and_hearer()` found nothing to propagate |
| `mutation_applied` | 2 | `claim_id`, `parent_variant_id`, `variant_id`, `slot` (string), `old_value`, `new_value`, `mutation_id` (string — the seeded mutation id the variant tree labels edges with), `roll_key` (purpose `mutation.slot` / `mutation.value`) |
| `supersession` | 2 | `holder_id`, `claim_id`, `loser_variant_id`, `winner_variant_id`, `resolution_rule` (string — the named resolution rule), `confidence_dent` (number, [0,1]). A separate record pointing at both variants — the loser is never mutated in place |
| `transmission_declined` | 3 — **reserved** | `claim_id`, `teller_id`, `hearer_id`, `location_id`, `rule` (string), `roll_key` \| null. Defined now so the encounter feed renders four outcome states from day one; produced when the tell-decision policy lands |
| `rule_evaluated` | 3 | `rule` (string), `inputs` (object — the accumulator values and entity refs the rule read), `fired` (boolean), `result` (object \| null — what firing produced: event refs, state ids). `fired: false` rows carry current accumulator values: a counter stuck at 3-of-4 is visible, not silent |
| `threshold_crossed` | 3 | `rule` (string), `accumulator` (object), `threshold` (number), `produced` (object — refs to what the escalation emitted, e.g. an `escalation_warning` event key) |

## 5. The keyframe record

A keyframe is a record on the `events` stream with `payload.record_type:
"keyframe"`, written every K ticks (K default 24 = one game-day, ADR-0010;
adaptive to cast size at the math-tier milestone). It is acceleration under
the three-things rule: rebuildable by scanning inputs + trace, carrying no
information of its own.

Payload shape — a full derived-state snapshot as of `tick`:

```json
{
  "record_type": "keyframe",
  "state": {
    "claims":        [ "Claim records: id, kind, slots, canonical_event_key, truth_status" ],
    "variants":      [ "Variant records: id, claim_id, parent_variant_id, slots, mutated_slot, gamets" ],
    "beliefs":       [ "BeliefInstance records: id, holder_id, claim_id, variant_id, confidence, verbatim_strength, gist_strength, first_learned, last_rehearsed" ],
    "evidence":      [ "Evidence records: id, belief_id, evidence_type, source_id, predecessor_belief_id, gamets, strength" ],
    "rumor_states":  [ "RumorState records: npc_id, claim_id, variant_id, stage, first_heard, last_heard, last_told, exposure_count, distinct_source_count" ],
    "relationships": [ "Relationship records: id, from_id, to_id, basis, basis_id, strength, formed_at, last_updated" ],
    "grudges":       [ "Grudge records: id, holder_id, target_id, source_belief_id, grievance_type, severity, emotional_strength, evidentiary_strength, last_rehearsed, forgiveness_threshold" ],
    "obligations":   [ "Obligation records: id, issuer_id, debtor_id, beneficiary_id, action, condition, deadline, status, witnesses, sanctions, excuse, created_at, fulfilled_at, violated_at" ],
    "reputations":   [ "Reputation records: observer_id, subject_id, context, alpha, beta, direct_count, witness_count, certified_count, uncertainty, last_updated" ],
    "schedules":     [ "ScheduleBlock records effective as of tick: npc_id, location_id, start_tick, end_tick" ]
  }
}
```

Field names and types mirror the `chronicle/claims.py`, `social.py`, and
`schedule.py` dataclasses exactly — the keyframe is a serialization of the
stores, not a remodel.

Deliberately **absent** (derived at read time, never stored — the
no-sampled-histories rule): decayed strength values, `dormant`/`forgotten`
rumor stages, reputation means, aggregate/collective views.

Additive-per-tier extensions (never breaking): rule-registry accumulator
state (Tier 3), schedule-override state (Tier 4a), pairwise encounter
weights (Tier 4b), roles (Tier 5). Each arrives as a new top-level key
under `state`.

## 6. The registry and the sidecar index

`runs/index.json` (registry — ui-spec §1.2, how the run picker enumerates
runs statically):

```json
{
  "schema_version": 1,
  "runs": [
    {
      "run_id": "string",
      "seed_id": "string",
      "created_wall_ts": "number — seconds since Unix epoch",
      "branches": [ {"save_uuid": "string", "generation": "int"} ],
      "tick_range": {"start": "int", "end": "int | null — null while running"},
      "streams": {"events": "events.jsonl", "trace": "trace.jsonl"},
      "status": "running | complete"
    }
  ]
}
```

`runs/<run_id>/index.json` (sidecar — pure acceleration, rebuildable by
scanning both streams; the M0 acceptance test proves it):

```json
{
  "schema_version": 1,
  "streams": {
    "events": {"tick_offsets": {"<tick>": "int — byte offset"}, "keyframe_offsets": [{"tick": "int", "offset": "int"}]},
    "trace":  {"tick_offsets": {"<tick>": "int — byte offset"}}
  }
}
```

`tick_offsets` points at the first record of each tick; readers binary-scan
within the tick from there. Both files are written with atomic
write-temp-rename.

## 7. Versioning and reader rules

- `schema_version` is an integer in every envelope and both JSON files.
  This document is version 1.
- Evolution is **additive-only within a major version**: new record types,
  new optional payload fields, new keyframe `state` keys. Never rename,
  retype, reorder, or remove. A breaking change is `schema_version: 2` plus
  a migration note in this document.
- **Readers ignore unknown record types, unknown payload fields, and
  unknown keyframe keys** — skip-and-continue, never error. This is what
  keeps an M3-era log readable by an M5-era reader and vice versa.
- The key encoding inside `roll_key` (component order, separators, hash)
  is part of ADR-0009's contract; changing it is a schema break.
- **Keyframe `seq` discipline:** the `events` stream's `seq` namespace is
  shared between canonical events (whose envelope `seq` IS `Event.seq`)
  and keyframes (which have no `Event.seq` of their own). Keyframes take
  `seq` values above the highest `Event.seq` seen so far in the run —
  guaranteeing no collision without needing a second counter. (Settled by
  Lane 4's implementation; formalized here per this document's own
  additive-only-evolution rule.)

## 8. Notes for the implementer (Lane 4)

- **Tick note:** payloads record bare tick integers; the quantum is
  ADR-0010's decision (1 tick = 1 gamets = 1 game-hour), cited here, not
  decided.
- **Volume sanity check:** at the ADR-0010 quantum, a 25-NPC, 10-game-day
  Tier-2 run is 240 ticks; ≤ ~300 co-present pair rolls per tick bounds
  encounter rolls near 7×10⁴, comfortably inside ui-spec §1.1's 10⁵–10⁶
  estimate once rule evaluations arrive at Tier 3. Lane 4 measures the
  exact figure and reports it for ui-spec §1.1.
- **Writer order within a tick:** events first, then trace, then keyframe
  (when due), one flush at the end of the batch — the liveness contract in
  §1.

## 9. Known gaps (routed from Lane 4's delivery, 2026-08-22)

Two gaps Lane 4 hit and worked around for M0's actual scope, not yet
reflected elsewhere in this document. Neither is a bug against anything
this document currently requires; both are here so the next tier that
touches this ground doesn't have to rediscover them.

- **No trace-stream record type yet for social-layer (`social.py`)
  mutations.** §4's record types cover claims/rumor propagation only —
  there is no `grudge_formed` / `obligation_fulfilled` /
  `relationship_formed` / `reputation_updated` trace record. This is
  consistent with scope: nothing in `chronicle/driver.py`'s tick loop
  currently drives `social.py` mutations autonomously (grudges/obligations
  are hand-authored in fixtures, not simulated per-tick yet). But it means
  that once a future tier *does* wire social mutations into the driver,
  those changes will only become visible at the next keyframe — no
  tick-accurate record of *when* a grudge formed between keyframes. Add
  record types to §4 at that point; this is an additive change, not a
  break.
- **`ClaimStore._rumor_sources` is not a keyframe key.** §5's
  `rumor_states` array captures `RumorState` but not the internal
  distinct-source exposure-counting set `_rumor_sources` uses to decide
  `is_new_source` on each hearing. Lane 4's reader reconstructs it exactly
  from each belief's grounding evidence (`_evidence_by_belief[id][0]`) —
  exact at M0 because every `(holder, claim, variant)` currently has
  exactly one grounding source. If a future tier lets a belief accumulate
  re-hearings from a second source *and* that boundary can fall between
  two keyframes, this reconstruction stops being exact and `state` needs
  an additive `rumor_sources` key.
