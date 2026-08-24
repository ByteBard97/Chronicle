# Lane 29 — Tier-3-rich demo run (Track A, producer)

**Status:** Ready to start immediately. Tier 3 is complete (`fa553c7`).
This lane produces the run the M4 dashboard lanes (diff panel +
rule-firing log, ui-spec §3.7) will be built against — every demo run
today predates the registry, so none contains `rule_evaluated`,
`threshold_crossed`, `transmission_declined`, or `reputation_updated`
rows.

**Effort:** small-medium (producer script + verification; no engine
changes).

## Context

Same shape as lane 17 (`scenarios/run_carrier_demo.py`) but with the
Tier-3 opt-ins exercised: the registry's rules firing (and visibly
*not* firing — the "counter stuck at 3-of-4" rows), the tell-decision
gate declining, accumulation escalating, reputation accumulating. The
goal is a run where every Tier-3 record type the dashboard renders
appears in realistic volume.

## Read first (in order)

1. `scenarios/run_carrier_demo.py` — the producer idiom (lane 17).
2. The Tier-3 opt-in seams (all construction-time, the
   `mutation_candidates` idiom): `claim_privacy` (lane 23),
   accumulating-kind registration (lane 24), `violation_evidentiary_strength`
   (lane 25), `reputation_relevance` (lane 26). Read the driver ctor.
3. `docs/frame-log-schema.md` §3:95, §4:121-128 — the record types the
   run must contain.
4. `chronicle/fixtures/` — reuse or extend a fixture; a new fixture
   module is in-bounds if composition demands it.
5. `docs/work-packets/reviews/README.md` — governance.

## Pinned design decisions (coordinator-set, 2026-08-23)

- **One run, id `tier3-demo-01`,** deterministic (`seed_id` a named
  constant), fresh dir (writer refuses existing).
- **The scenario exercises all five Tier-3 rungs in one cast:** a
  private secret with a kin-motivated holder (declines), a merchant
  suffering serial theft (escalation at 4), obligations with a refusal
  (cascade), a status proclamation (reputation), plus ordinary
  rumor/mutation traffic underneath (supersessions welcome — they're
  free at this scale).
- **Negative rows required:** the run must contain `rule_evaluated`
  rows with `fired: false` (accumulator below threshold — the diff
  panel's stuck-counter case) and `transmission_declined` rows (the
  feed's fourth outcome).
- **No engine changes** — the producer composes existing opt-ins. If
  something can't be expressed, that's a finding.
- **The `RumorHeard` anchor** (lane 23/26 precedent) for the
  proclamation; no new event types in this lane.

## Task

1. `scenarios/run_tier3_demo.py` (producer, not a test): Driver with
  the Tier-3 opt-ins registered; the scenario above; `driver.run`;
  printed record counts.
2. Generate `runs/tier3-demo-01/`; verify the smoke facts (record
  counts per type — all five Tier-3 types present, plus
  `fired: false` rule rows) via the CLI; report output tails.
3. Determinism: regenerate twice into temp `CHRONICLE_RUNS_DIR`s, diff
  modulo `wall_ts`; report.
4. Suite green (producer adds no tests; if you add a determinism
  guard test, keep it in the existing harness's idiom).

## Acceptance

- `runs/tier3-demo-01/` exists with all five Tier-3 record types +
  negative `rule_evaluated` rows, verified via CLI with output tails.
- Determinism verified modulo `wall_ts`.
- `uv run pytest -q` green (205+), `uv run ruff check .` clean.
- No engine/fixture-test edits; no schema edits.

## File boundaries

**Create:** `scenarios/run_tier3_demo.py`, `runs/tier3-demo-01/`
(generated), optionally `chronicle/fixtures/tier3_demo.py`

**Do not touch:** everything else — engine files are complete for this
lane's purposes; gaps are findings.

## Conventions

- Match the producer idiom; named constants.
- **Local commits OK** (path-scoped); never push.
- Report format: delivered, acceptance per criterion with command
  tails, findings list.
