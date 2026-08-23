# Lane 17 — carrier+mutation demo run + CLI supersession polish (Track A)

**Status:** Ready to start immediately. The carrier fixture landed
(`c17b326`); the demo-run producer idiom exists
(`scenarios/run_jarl_death_demo.py`); lane 12's mutation/resolution
machinery is committed. Lane 14/15/16 (dashboard) are disjoint — this
lane produces the *data* those lanes will render.

**Effort:** small-medium (producer script + tiny CLI fix + tests).

## Context

Today's only real run, `runs/whiterun-jarl-01`, has **zero mutations and
zero supersessions** (verified in the lane-12 review) — by design. The
dashboard's next lanes need a run that exercises what they render:
lane 16's timeline wants `mutation_applied`/`supersession` markers, the
variant tree (lane 18) wants lineage + supersession cross-links, and the
map's satellite/carrier UI wants real carrier traffic. This lane
generates that run, and picks up the lane-12 backlog's one-line CLI
polish while it's in the neighborhood.

## Read first (in order)

1. `scenarios/run_jarl_death_demo.py` (74 lines) — the producer idiom:
   Driver construction, tick-0 events, `driver.run(0, N)`, printed
   record counts. Note it is **not** a test (no `test_` prefix).
2. `chronicle/fixtures/carrier_schedule.py` — the landed fixture:
   `carrier_schedule()` blocks, named tick constants
   (`CARAVANEER_*`, `RELIEF_*`, `END_TICK`), location ids.
3. `scenarios/test_tier2_mutation.py` — how `mutation_candidates` are
   registered (the caller-supplies-context mapping shape) and the
   `mutation_id`/goldens discipline.
4. `chronicle/cli.py` — the supersession print site (the `None`
   rendering), plus `chronicle/tests/` cli coverage (`cc9f2ab`) for the
   test idiom.
5. `chronicle/tests/test_determinism.py` — the same-seed-identical
   harness (mask `wall_ts`, the one legitimately nondeterministic
   field).
6. `docs/work-packets/reviews/README.md` — governance. Lane agents do
   not commit.

## Pinned design decisions (coordinator-set, 2026-08-23)

- **The demo keeps both carriers alive** — it's the T2.6 shape (the
  full carrier loop), not T2.7. No kill events. One public crime,
  witnessed at the market at tick 0 (the jarl-demo's canonical pattern:
  events at tick 0, then `driver.run(0, N)`).
- **`encounter_probability=0.35`** (the jarl-demo value) — the fixture's
  1.0 pinning is for exact-tick tests only; the fixture supplies blocks,
  the producer picks probabilities.
- **Mutation candidates registered** with lore-flavored slot values
  (perpetrator/cause/location — the T2.2 mapping shape), so variants
  emerge en route and resolutions fire. **Expect heavy supersession
  churn** (the T2.2 precedent: 2,880 on a 25-NPC cast) — that is the
  ruled behavior, not a bug; report the counts, don't tune dynamics
  (that's the owner-review backlog item).
- **Deterministic:** fixed `seed_id`; regenerating to a fresh
  `CHRONICLE_RUNS_DIR` twice must produce byte-identical logs modulo
  `wall_ts` (the determinism harness's masking rule).
- **Do not regenerate `runs/whiterun-jarl-01`** — the writer refuses
  existing run dirs and that run stays as-is. Fresh run id:
  `carrier-mutation-01`.

## Task

1. **`scenarios/run_carrier_demo.py`** (producer, not a test): Driver
   over `carrier_schedule()` with the pinned parameters; tick-0 crime +
   witness; `driver.run(0, END_TICK)`; print record counts by type
   (events + trace). Follow the jarl-demo's structure and output style.
2. **Generate the run** into `runs/carrier-mutation-01/`
   (`rm -rf` first if it exists — append-only writer). Verify the smoke
   facts and put them in your report: Markarth-resident beliefs exist;
   `mutation_applied` > 0; `supersession` > 0; the caravaneer appears
   in Markarth chains.
3. **Determinism check:** regenerate twice into temp dirs
   (`CHRONICLE_RUNS_DIR`) and diff modulo `wall_ts`; report the result.
   (This is a manual verification, not a new test file — the
   determinism harness already covers the machinery.)
4. **CLI polish:** `chronicle/cli.py`'s supersession line renders a
   null variant id as `(original telling)` instead of `None` (lane-12
   finding 6). Extend the nearest existing CLI test to cover it.

## Acceptance

- `runs/carrier-mutation-01/` exists with the smoke facts above,
  verified via the CLI (`inspect`/`trace`/`feed` forms from the jarl
  demo's dogfooding) and reported with output tails.
- Determinism verified (byte-identical modulo `wall_ts`); method and
  diff result in the report.
- `uv run pytest -q` green (185 + your CLI test delta); `uv run ruff
  check .` clean.
- No engine changes beyond `cli.py`'s rendering fix; no fixture edits;
  no scenario-test edits.

## File boundaries

**Create:**
- `scenarios/run_carrier_demo.py`
- `runs/carrier-mutation-01/` (generated — the coordinator commits it
  at integration)

**Edit:**
- `chronicle/cli.py` (the null-variant rendering only)
- the nearest CLI test file in `chronicle/tests/` (add the
  `(original telling)` case)

**Do not touch:**
- `chronicle/` engine files other than `cli.py`, fixtures, scenario
  tests, `runs/whiterun-jarl-01`, `docs/`, `dashboard/`

## Conventions

- Match the jarl-demo producer's style; named constants, no ad-hoc
  literals.
- **No `git commit`** — the coordinator reviews and commits.
- Report format: what you delivered, acceptance status per criterion
  with command output tails (incl. record counts + determinism diff),
  and a findings list.
