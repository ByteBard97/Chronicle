# Lane 49 — T6: the north-star composition test (Track A)

**Status:** Ready to start immediately. Every mechanism the north star
needs is landed (Tiers 0–5, rules 1–19 live); the fixture design is
accepted and ruled (`docs/design/north-star-fixture.md` — your spec;
overseer review in `docs/work-packets/reviews/2026-08-24-lane-45/`).

**Effort:** large (fixture build + composition test + demo producer —
the capstone lane).

## Context

Tier 6 (frozen, `docs/scenario-ladder.md` Tier 6 intro): **no new
mechanism.** The Jarl assassination asserting the full cascade:
succession (T5) + grief reroutes and grudges (T3/T4a) + city-wide
propagation with a surviving mutated variant (T2) + collective fear as
a **read-only aggregate view** — derived on read, with drill-down,
never cached, never an input to any behavior decision. "If Tiers 0–5
are green and T6 fails, the mechanisms don't compose."

The vision's north star (`docs/vision-v2.2.md` §2) is the acceptance
test for the whole architecture. This lane builds it.

## Read first (in order)

1. `docs/design/north-star-fixture.md` — the ruled fixture spec (cast
   groups, relationship/faction graph, claim/event scripts, assertion
   outline per beat). Deviations come back as findings.
2. `docs/vision-v2.2.md` §2 — the four beats, verbatim.
3. `docs/scenario-ladder.md` Tier 6 intro — esp. the aggregate
   discipline (read-only view, never a behavior input).
4. The fixture modules you're extending:
   `chronicle/fixtures/carrier_schedule.py` (lane 13),
   `chronicle/fixtures/whiterun_relationships.py`.
5. The mechanism surfaces each beat uses: `chronicle/roles.py` (T5),
   mourning overlays (lane 36), grudges (lanes 20/25/43),
   mutation/resolution (lanes 12), carriers (lane 13).
6. `scenarios/run_tier3_demo.py` — the producer idiom (Decision N5's
   one-fixture-two-consumers precedent).
7. `docs/work-packets/reviews/README.md` — governance.

## Pinned decisions (ruled — see the design doc + review)

- **O1/O2 (ruled):** no obligation beat; no second T3.4 privacy beat.
- **O3 (ruled):** one fixture module with a run-length parameter —
  compressed for the test, full multi-day for the demo.
- **O4 (ruled):** the role roster casts BOTH `jarl_of_whiterun` AND a
  sitting steward (Proventus — dual-cast as sitting steward and Jarl
  succession candidate).
- **F2 (ruled):** T2.4's engine hook is NOT this lane (a later
  micro-lane); the composition exercises faction data where it's
  consumable today (succession, reputation), not motivated mutation.
- **The aggregate is a test-side read** (F4): the T6 assertions
  compute the aggregate from reputation/belief records at assert time
  (a test helper, not engine machinery); the dashboard aggregate view
  is a later M6+ lane.

## Task

1. **The fixture** (`chronicle/fixtures/north_star.py`): extend the
   carrier backbone per the design doc — household kin edges, faction
   edges, the O4 role roster, temple/priest, the Markarth side.
2. **`scenarios/test_north_star.py`** — the composition test, asserting
   per the design doc's outline:
   - **Succession:** Balgruuf dies → `jarl_of_whiterun` vacant → the
     successor resolves from the fixture's relationship state (and the
     steward succession runs independently).
   - **Grief/grudge:** household kin mourn (mourning overlay inserted,
     rerouted days) and hold grudges with the killing as evidence.
   - **The rumor:** propagates city-wide with at least one mutation;
     the mutated variant **survives to Markarth** via the carrier —
     assert the Markarth believer's chain passes through the carrier
     AND carries the mutated slot.
   - **The aggregate substrate:** the test-side aggregate helper
     computes guard-cohesion/market-confidence from the records and
     is correct against them (and is demonstrably read-only — no rule
     reads it).
3. **`scenarios/run_north_star_demo.py`** — the M7 demo producer
   (`runs/north-star-01`, full multi-day window): the stranger
   walkthrough's data (Decision N5's beat list).
4. Determinism: the composition test is seeded and exact (or names its
   tolerance per the rung); the demo regenerates identically modulo
   `wall_ts`.

## Acceptance

- `uv run pytest -q` green (240 + your new tests), ruff clean.
- The four beats pass as automated assertions per the design doc's
  outline; the composition test fails loudly if any mechanism doesn't
  compose (that's its purpose).
- `runs/north-star-01` exists with the walkthrough beats present
  (CLI-verified, output tails in the report).
- No new RNG purposes; no schema edits; no new rules (rule budget is
  full at 19 — Tier 6 adds none).

## File boundaries

**Create:** `chronicle/fixtures/north_star.py`,
`scenarios/test_north_star.py`, `scenarios/run_north_star_demo.py`,
`runs/north-star-01/` (generated)

**Edit:** `chronicle/fixtures/carrier_schedule.py`,
`chronicle/fixtures/whiterun_relationships.py` (extension only — the
lane-13 rungs must stay green; changes are additive)

**Do not touch:** engine files (any gap is a finding — Tier 6 adds no
mechanism), frozen/coordinator docs, other `scenarios/` files,
`dashboard/`

## Conventions

- Match the fixture/test idiom; named constants; seeded determinism.
- **Local commits OK** (path-scoped, atomic `add && commit`); never push.
- File a delivery report on disk: delivered, acceptance per criterion
  with command tails, findings list.
