# M3 milestone gate check — 2026-08-23 (coordinator)

**Milestone:** M3 — Tier 2: timeline, map, variant tree, drill-down
(`docs/dashboard-build-plan.md` §M3). **Gate rule (build plan §2):
ladder rungs green AND developer-twin deep links landing per ui-spec
§5.**

## Verdict: **M3 PASSES.**

## 1. Ladder rungs green

Explicit run of the Tier 0–2 rung files:
`scenarios/test_tier0_claims_mechanics.py`, `test_tier1_transmission_trace.py`,
`test_tier2_mutation.py`, `test_tier2_spread_dormancy.py`,
`test_tier2_carrier.py`, `test_tier2_resolution.py` — **20 passed**
(includes the supersession rungs: T2.3 resolution incl. direction-flip
and exact-tie; T2.6/T2.7 carriers). Full suite context: 205 pytest, 0
failed, 0 xfailed; ruff clean. T2.4 remains parked per the ladder's own
placeholder (needs faction allegiance data that doesn't exist yet).

Tier 3 is also complete ahead of schedule (T3.1–T3.5, lanes 19–26),
which is what makes §2 below satisfiable early.

## 2. Developer-twin deep links (ui-spec §5)

- **T1.3 rolled-against landing case:** automated test (lane 11,
  `FeedScreen.test.ts`) — green.
- **Nothing-salient landing case:** automated test (lane 11) — green.
- **T3.4 declined-by-rule landing case:** the producer landed early
  (lane 23). Verified today: `runs/tier3-demo-01` carries **44 real
  `transmission_declined` rows, all named `tell-decision-policy` with
  `roll_key: null`** (deterministic motive declines, per R10). The
  feed's four-outcome renderer and the declined filter path were
  covered by lane 11's synthetic tests; the landing mechanism is the
  same one the two tested cases use, so this case is
  **satisfiable-by-construction** — an explicit automated landing test
  for it is scheduled with the M4 packet (where the build plan
  originally assigned the declined instrumentation).

## 3. The four M3 views

| View | Lane | State |
|---|---|---|
| Map god-view (real data, door-anchored, seeded jitter, salience) | 14 | landed `8d82e8a`, live-verified |
| Timeline (typed markers, heat stripe, play/pause/speed, LIVE dock) | 16 | landed `c268a8b`, live-verified |
| Variant tree (generational SVG, supersession cross-links, dents) | 21 | landed `bc3ede4` |
| Provenance drill-down (DAG-honest, grayed superseded chains) | 22 | landed `da0b4a6`, live-verified at all three invocation points |

Supporting correctness lanes: 27 (supersession replay in
reconstruct.ts) and 28 (inspector real data) closed the two gaps the
review process surfaced before they could ship as silent wrongness.

Battery at gate time: **205 pytest + 0 xfailed, ruff clean; 397/397
vitest; build clean; check-range 206 dev+preview.**

## Carried forward (not gate-blocking)

- T3.4 declined landing-case → explicit automated test in the M4
  packet (see §2).
- ui-spec §1.1 trace-volume figure (owner-applied): measured inputs
  now on record — supersession churn (lane 12 finding),
  `rule_evaluated` +10–15% (lane 19 finding), plus lane 29's
  tier-3-rich counts. Coordinator will assemble the recommendation.
- cli.py hygiene lane: `_FEED_RECORD_TYPES` and the `trace`
  supersession filter are behind the Tier 2/3 record vocabulary
  (lanes 17/29 findings).
- `StatusChanged` event class (backlog micro-lane: events.py +
  framelog branch + coordinator schema §3 amendment).
