# Lane 2 — Frame-log schema catalog

**Status:** Ready to start. No dependencies (coordinate with Lane 3 on the
tick-quantum note, below). Deliverable is one new file.
**Effort:** medium. This is the build's first real design artifact.

## Context

Chronicle's dashboard reads a **frame log** per sim run. `docs/ui-spec.md`
§1.1 froze the record *envelope* and physical layout but deliberately left
the *payloads* undefined. This lane defines them. The catalog is written
once and versioned forever — the UI iterates, the log format does not
(ui-doctrines D22).

## Read first (in order)

1. `docs/ui-spec.md` §1.1 (the frozen envelope, physical layout, three-things
   rule — restate the envelope **verbatim**, do not redesign it) and §1.2.
2. `docs/scenario-ladder.md` §2 (the machinery inventory — one record type
   per rung that produces something) and §3 (tiers, for which tier each
   record type arrives).
3. `chronicle/claims.py`, `chronicle/social.py`, `chronicle/events.py`,
   `chronicle/schedule.py` — the actual state shapes the keyframe must
   serialize and the trace must reference.
4. `docs/ui-doctrines.md` D7 (negative results are first-class — trace
   record types must include non-events).

## Task

Write `docs/frame-log-schema.md` (schema_version: 1):

- **Envelope:** restate ui-spec §1.1's frozen envelope verbatim:
  `(schema_version, seed_id, save_uuid, generation, tick, stream, seq,
  payload)`; JSONL framing; torn-tail rule; `runs/<run_id>/` layout with
  `events.jsonl` / `trace.jsonl` / `index.json` (tick → byte offset per
  stream + keyframe offsets, atomic write-temp-rename) and `runs/index.json`.
- **Writer flush policy (liveness contract):** the writer flushes after
  every tick's record batch. LIVE tailing latency must be the reader's
  polling cadence, not the writer's buffer length — without this, the LIVE
  dock (ui-spec §1.3) silently lags. Readers may assume a committed record
  is visible within one tick of emission.
- **Events stream payloads:** one record type per canonical event kind in
  `chronicle/events.py` + the ladder (death, crime-witnessed, testimony,
  injection, …). Field-level: names, types, units, optionality.
- **Trace stream payloads:** one record type per derivation/negative result:
  encounter-rolled (roll value vs. threshold, plus a `roll_key` substructure
  whose members and order are owned by ADR-0009 — cite it, don't redefine
  it), transmitted,
  nothing-salient, and the **reserved** declined-with-rule type (defined now,
  produced at Tier 3 — the schema reserves it so the feed renders four
  outcome states from day one), rule-evaluated / evaluated-but-not-fired
  (with accumulator values), mutation-applied (slot, old→new, mutation id),
  supersession, threshold-crossed.
- **The keyframe record:** full derived-state snapshot shape, defined as
  **versioned-and-extensible**: additive fields per tier (grudges at Tier 3,
  schedule overrides at Tier 4a, roles at Tier 5), never breaking — an
  M3-era log must stay readable by an M5-era reader. Specify the reader
  rule for unknown fields (ignore-and-continue).
- **Tick note:** payloads record bare tick integers; the quantum is Lane 3's
  decision — reference it, don't decide it.

## Acceptance

- Field-complete enough that Lane 4 implements `chronicle/framelog.py`
  against this document alone.
- Every record type names the ladder tier that introduces its producer.
- Every payload field has a type and a unit or "unitless" note.

## File boundaries

- **Create:** `docs/frame-log-schema.md` only.
- **Do not touch:** code, frozen docs (`ui-spec.md`, `scenario-ladder.md`,
  `ui-doctrines.md`), `docs/decisions/` (Lane 1's).

## Conventions

- Do **not** `git commit` — leave the file for the coordinator.
- If a needed record type has no producer in the machinery inventory, mark
  it "reserved" rather than inventing machinery — that's the ladder's job.
