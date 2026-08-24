# Lane 45 — overseer review and rulings (north-star fixture design)

**Date:** 2026-08-24 · **Overseer:** planning agent · **Re:**
`docs/design/north-star-fixture.md` (`3b950a6`)

## Verdict: **accepted.** The doc's own best finding is its first
surprise — most of the north star is already built (carrier backbone,
court edges, mutation machinery), and the real gap is narrow
(household kin edges, faction data) and exactly where the ladder said
it would be.

## Rulings on the open points (coordinator authority, owner-delegated)

- **O1 — no obligation/T3.3 beat: confirmed.** None of the four vision
  beats names obligations; absence is settled, not an oversight.
- **O2 — optional T3.4 second-privacy beat: deferred, confirmed.** The
  death claim already exercises tell-decision (the assassination is
  the secret some holders keep); a second suspect-naming beat adds
  complexity without a vision mandate.
- **O3 — demo vs. test length: ruled — one fixture module, one
  run-length parameter.** The producer/test chooses the window
  (compressed for CI, full multi-day for the M7 demo); no fixture
  variants to drift apart.
- **O4 — the Jarl's role mapping: ruled.** The fixture defines
  `jarl_of_whiterun` (institution `whiterun_court`) as its own role,
  AND a sitting **steward** role held by Proventus — so Tier 5's two
  rungs exercise at two scales in one fixture: the steward's vacancy/
  succession (the small example) and the Jarl's (the vision's big
  one). Proventus is cast as *both* sitting steward and a Jarl
  succession candidate (his court edge is strong but not guaranteed
  top) — the vision's "the vacancy pulls a successor out of the web
  of relationships" flavor, not a pre-ordained answer.
- **F2 (T2.4 needs a small engine hook): accepted.** `_decide_mutation`
  has no teller-identity input; the allegiance-consistent substitution
  hook gets its own micro-lane later (lane-39-sized), not bundled
  into the fixture build.
- **F4 (the aggregate is dashboard-side): noted for the M6+ lanes;**
  the fixture guarantees the substrate.

## Dispatch note

Lane 45's doc is the input to the T6 composition lane, which the
coordinator packetizes once lanes 47/48 land (Tier 5 machinery is the
last dependency). Lanes 35 and 38 (Track B) also accepted this round —
board updated.
