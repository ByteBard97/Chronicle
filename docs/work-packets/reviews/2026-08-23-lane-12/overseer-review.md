# Lane 12 — overseer review and dispositions

**Date:** 2026-08-23 · **Overseer:** planning agent (per governance
ruling) · **Re:** `delivery-report.md` (same directory)

## Verification (done independently, not from the report)

- **Battery re-run:** `uv run pytest -q` → 180 passed, 2 failed (the two
  declared conflicts), 0 xfailed; `uv run ruff check .` → clean.
  Arithmetic checks: 175 + T0.4 unmarked + 6 rung tests − 2 conflicted =
  180 + 2 failing.
- **Boundary check:** `git status` shows only the packet's Edit list
  (`claims.py`, `driver.py`, `framelog.py`, `propagate.py`,
  `test_tier0_claims_mechanics.py`) plus the new
  `scenarios/test_tier2_resolution.py`. The `docs/frame-log-schema.md`
  modification in the tree is the coordinator's own amendment, not the
  lane's. Untracked `docs/research/` additions are the owner's research
  filings — not agent work, left alone.
- **Marker-only edit confirmed:** `git diff scenarios/test_tier0_claims_mechanics.py`
  shows the xfail decorator removal and nothing else; body byte-identical.
- **Rung test inventory** (`test_tier2_resolution.py`, 6 tests) maps
  onto the frozen assert list: eyewitness-shrugs-off-gossip and
  rumor-holder-updates (the direction-flip pair), summed-strength
  tiebreak including corroboration, exact-tie standoff, raise paths,
  encounter-driven arbitrary-T reconstruction parity across a keyframe.
- **No new RNG purposes; no frozen-doc edits; no dashboard edits.**

The four expected findings confirmed with acceptable nuance; the two new
findings (resolution churn at run scale; CLI null rendering) are logged
below for the backlog.

## Disposition of Conflict 1 — `test_claim_store_rejects_the_same_claim_id_with_different_content`

**Authorized.** Update the test to assert the T0.4 path (a Variant is
produced, rooted at the claim, canonical slots unchanged) and rename it —
"rejects" no longer describes the behavior. Justification: the frozen
ladder's T0.4 mandates the variant path; this unit test pins the
pre-T0.4 mechanism the rung exists to overturn. Its *intent* (never
silently rewrite the shared canonical claim) is preserved and is what
the updated assertions must still check. This is the packet's "conflicts
are findings" rule resolving through the coordinator, not a lane editing
an accepted test on its own authority.

## Disposition of Conflict 2 — `test_distinct_source_counting_survives_a_keyframe_boundary`

**The carve-out is ruled in.** "Raises on any duplicate-creating path"
is scoped to paths that would actually create a duplicate belief. A
same-content re-tell to an already-informed hearer is a **re-hearing**:

- `retell()` in this case mints **no** variant/belief/evidence, records
  the hearing (`_record_hearing` — exposure and distinct-source counting,
  rule 7, stay alive), and returns the existing (variant, belief).
- Post-carve-out `retell()` never raises for an informed hearer:
  uninformed → transmit; differing content → resolve; same content →
  re-hear. The store-level raises that remain (and that the rung test
  asserts) are witness-after-rumor, multi-slot witness disagreement, and
  resolve-without-incumbent.
- **Consequence for the new rung test** (lane's own file, editable):
  `test_t23_store_raises_on_every_duplicate_creating_path` drops the
  same-content-retell raise case and instead asserts the re-hearing
  semantics (nothing minted, hearing recorded, counts correct).
- **Driver wrapper emission (ruling on the worker's open sub-question):**
  a scripted re-hearing emits a `transmitted` record referencing the
  **existing** variant and hearer-belief ids — no new schema, the feed
  stays honest, and replay re-executes through the same store path
  (retell → re-hearing branch), preserving reconstruction parity. The
  encounter path is unaffected: same-content both-informed encounters
  still decline as `nothing_salient` (no encounter-path re-hearing —
  that ruling stands).
- **Schema gloss amended by the coordinator** (§4:117, coordinator-owned):
  "a variant is created on every transmission" now carries the re-hearing
  nuance. See the doc's dated amendment.

The conflicted Lane-4 test then passes unchanged, which is the correct
outcome — its premise (scripted same-content retellings for distinct-
source counting) is legitimate accepted behavior.

## Backlog items from this review (not this lane)

- **Resolution churn at run scale** (finding 5): 2,880 supersessions vs.
  7 transmitted in the T2.2 run; dents compound per repeated challenge.
  Literal implementation of the pins — flagged for the owner's next
  review cycle: repeat-challenge dampening is a math-tier/dynamics
  question, and the trace-volume consequence feeds the outstanding
  ui-spec §1.1 figure (owner-applied).
- **CLI null rendering** (finding 6): `superseded by None` → suggest
  `(original telling)`; fold into a future cli.py hygiene lane (the file
  was do-not-touch here).

## Verdict

**Accepted-with-fixes.** The two conflict applications above are the
only outstanding work; both are small and ruled completely. On delivery
of the amended tests + re-run battery (target: 182 passed, 0 failed,
0 xfailed), the coordinator re-verifies and commits.
