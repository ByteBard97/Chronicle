# Lane 24 — Tier 3 L-C: accumulation-threshold escalation (Track A, sim substrate)

**Status:** Ready to start **after lane 23 lands** (both touch
`driver.py` — serial per the design doc). Everything else is unblocked:
L-A landed (`8a83e41`), design decisions R4–R6 are ruled, and the
`escalation_warning` event's fields are now defined (schema §3:95,
coordinator-filled 2026-08-23).

**Effort:** medium (rule + event + rung test).

## Context

T3.1 (frozen, `docs/scenario-ladder.md:72`): four thefts, same merchant.
Assert: below threshold, annoyance only; at threshold, **exactly one**
escalation — materialized **as an event in the log first** (the warning
claim hangs off that event's canonical key; no orphan beliefs, no
broadcast — it propagates to peer merchants only through Tier-1/2
encounters); **no double-fire** on theft five.

## Read first (in order)

1. `docs/design/tier-3-rule-registry-and-tell-decision.md` §2 (R4–R6)
   — the ruled design: derived accumulator, latch, escalation-as-event.
2. `docs/scenario-ladder.md:72` — the frozen rung text.
3. `docs/frame-log-schema.md` — §3:95 (`escalation_warning`, fields now
   defined: `holder_id`, `grievance_kind`, `count`, `threshold`) and
   §4:123 (`threshold_crossed`: `rule`, `accumulator`, `threshold`,
   `produced` — refs incl. the escalation event key).
4. `chronicle/rules.py` + `chronicle/driver.py` — the lane-19 machinery
   and (once lane 23 lands) the gate idiom. `driver.py`'s witness path
   (`:197`) and `_propagating_claims` (:208-209 — propagation for free).
5. `chronicle/events.py` — the event dataclass idiom (NPCDied etc.);
   your new event follows it. Note `origin` handling and the envelope
   fields.
6. `docs/work-packets/reviews/README.md` — governance.

## Pinned implementation decisions (coordinator-set, 2026-08-23)

- **Derived accumulator (R4, ruled):** key `(holder_id, grievance_kind)`;
  value = count of the holder's beliefs whose claim kind matches and
  whose slots name the holder as victim — a pure `ClaimStore` read, no
  stored counters. Registering which claim kinds accumulate (and the
  victim slot) is caller-supplied context in the `mutation_candidates`
  idiom.
- **Latch (R5, ruled):** fire once at count ≥ threshold; the latch is
  the existence of a `threshold_crossed` record for the key — derived
  from the log, so reconstruction can't double-fire. Monotonic
  accumulator → hysteresis reduces to the latch (doctrine 3 satisfied).
- **Evaluate on change only (R5):** the rule evaluates exactly where a
  matching belief forms (witness/retell paths), never per-tick.
- **Escalation (R6, ruled):** on firing, the driver (1) injects the
  `escalation_warning` event into the events stream (fields per §3:95
  as filled), then (2) calls the ordinary `witness()` path with
  `canonical_event_key` = that event's key — the escalating NPC witnesses
  their own escalation. Propagation is encounters-only for free.
- **`threshold_crossed` emission** (§4:123): `rule` = the rule name,
  `accumulator` = the key + count + contributing belief ids, `threshold`,
  `produced` = refs to the escalation event key + the new claim id.
- **Rule 11 registers** replacing the stub; default enabled. With no
  accumulating kinds registered, behavior is identical to today.

## Task

1. `chronicle/events.py`: the `escalation_warning` event dataclass (per
   §3:95 fields; follow the module's idiom).
2. The accumulation rule in `chronicle/rules.py` (replacing the rule-11
   stub): derived count, latch check, fire → the R6 cascade.
3. Driver wiring: evaluation hooks on belief-forming paths; the event
   injection; the witness-off-the-event call; `threshold_crossed`
   emission (scripted-wrapper idiom).
4. `scenarios/test_tier3_accumulation.py` — the T3.1 rung: four thefts
   against the same merchant (scripted witnesses per the fixture).
   Assert: no escalation at 3; exactly one `escalation_warning` event +
   one `threshold_crossed` at 4; the warning claim hangs off the
   event's canonical key (no orphan); the claim propagates
   encounters-only (transmitted records exist only via encounters);
   theft five fires nothing (latch). Plus a reconstruction-parity
   assert (state_at over the firing tick — no double-fire on replay).
   **Authoring notes (from delivery):** engine-internal events (the
   escalation) consume branch seqs — hand-numbered fixture seqs must
   skip past them; and scripted pre-run writes aren't visible to
   `FrameLogReader` until a flush (the writer flushes per tick).
5. Determinism + no behavior change at defaults (suite unedited).

## Acceptance

- `uv run pytest -q` green (lane 23's count + your new tests), ruff
  clean.
- `escalation_warning` and `threshold_crossed` records match §3:95/
  §4:123 field-for-field.
- The rung asserts pass as written above, incl. no-double-fire and
  replay parity.
- No new RNG purposes; no other schema/frozen-doc edits (§3:95 is
  already filled).

## File boundaries

**Create:** `scenarios/test_tier3_accumulation.py`

**Edit:** `chronicle/rules.py`, `chronicle/driver.py`,
`chronicle/events.py`, `chronicle/framelog.py` (event serialization
branch — omitted from the original packet's list in error; the writer
raises on unknown event types, so the new event needs its mechanical
branch. Confirmed retroactively 2026-08-23)

**Do not touch:** frozen/coordinator docs (§3:95 is done), `rng.py`,
`social.py`, `claims.py`, other `scenarios/` files, `dashboard/`, `runs/`

## Conventions

- Match the driver/events idiom; named constants (`ACCUMULATION_THRESHOLD`
  is caller-supplied per kind, not a global) with rule citations.
- **Local commits OK** (path-scoped, explicit adds); never push.
- Existing test assertions immutable; conflicts are findings.
- Report format: delivered, acceptance per criterion with command
  tails, findings list.
