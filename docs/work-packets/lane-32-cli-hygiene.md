# Lane 32 — cli.py hygiene: Tier 2/3 record vocabulary (Track A, small)

**Status:** Ready to start immediately. Two known gaps, both flagged by
earlier lanes; the Tier-3 record vocabulary is now stable, so the CLI
can be brought current.

**Effort:** small.

## Context

1. **`_FEED_RECORD_TYPES` is behind the schema** (lane-29 backlog
   note): the `feed` subcommand's type list predates Tier 2/3 records —
   bring it current with schema §4 as of lanes 12–26 (`supersession`,
   `mutation_applied`, `transmission_declined`, `rule_evaluated`,
   `threshold_crossed`, `grudge_formed`, `reputation_updated`,
   `obligation_*`, `relationship_formed`, `escalation_warning` on the
   events side).
2. **`trace`'s supersession filter under-reports** (lane-17 finding 1):
   `cli.py:361` filters supersessions to variants held *at the
   inspection tick*, so records whose loser variant is held by nobody
   after the re-point vanish from the listing. Fix per the finding's
   suggestion: union over the claim's known variant lineage (and the
   canonical telling, null) instead of currently-held variants.

## Read first

- `chronicle/cli.py` — the `feed` type list and the `trace`
  supersession filter (:289-291, :356-370).
- `docs/frame-log-schema.md` §3/§4 — the full current vocabulary.
- `runs/tier3-demo-01/` — real records of every new type to verify
  against.
- `chronicle/tests/test_agent_debug_cli.py` — the CLI test idiom.

## Task

1. Bring `_FEED_RECORD_TYPES` (and any adjacent type lists) current
   with the schema; verify `feed` renders each type present in
   `tier3-demo-01` sensibly (no crashes, no silent drops).
2. Fix the `trace` supersession filter per the finding (union over the
   claim's variant lineage + canonical), with a regression test using
   the lane-17 case (a supersession whose loser is held by nobody after
   re-pointing — the fix makes it visible at every `--at`).
3. Battery green; no other behavior changes.

## Acceptance

- `uv run pytest -q` green (205+), ruff clean.
- `feed`/`trace` verified against `tier3-demo-01` with output tails in
  the report; the under-reported supersession case now listed, covered
  by test.
- No schema/frozen-doc edits; boundaries respected.

## File boundaries

**Edit:** `chronicle/cli.py`, `chronicle/tests/test_agent_debug_cli.py`

**Do not touch:** everything else.

## Conventions

- **Local commits OK** (path-scoped); never push.
- Report format: delivered, acceptance per criterion with command
  tails, findings list.
