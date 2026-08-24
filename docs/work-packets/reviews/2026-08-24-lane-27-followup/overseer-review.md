# Lane-27 finding follow-up — transmitted-belief decay divergence, fixed

**Delivered:** `fca6332` (worker-initiated, not a dispatched packet —
chronicle-17 went back to a finding it had left unfixed since lane 27
and actually measured the blast radius instead of continuing to
assume it was large).

## Background

`dashboard/src/log/reconstruct.ts`'s `applyTraceRecord`'s `transmitted`
case decayed the teller's belief via `decayBelief()` before deriving
the hearer's confidence/verbatim/gist and the evidence's strength.
`chronicle/claims.py`'s `retell()` (confirmed directly, `claims.py:317`)
takes `teller_belief` as-is and applies the retell decay constants to
its raw fields — no pre-decay step. This divergence was noted in this
file's own header comment as a known, documented, left-as-is item
since lane 27, on the stated assumption that fixing it "would shift
confidence values several already-landed lanes' tests assert against"
— an assumption never actually tested until tonight.

## Verified independently

- **Claim checked against the source**: `chronicle/claims.py:317-360`'s
  `retell()` signature and body confirm no decay step is applied to
  `teller_belief` before use — matches the fix's premise exactly.
- **Battery, re-run independently**: `uv run pytest -q` 249 passed
  (untouched, zero Python files in the commit); `uv run ruff check .`
  clean; `npm test` 608/608 across 87 files (same total as before —
  two existing tests' *expectations* were corrected, not added/removed,
  consistent with the commit's own claim of "exactly two failures,
  both hand-computing the buggy formula as their expected value");
  `npm run build` clean; `npm run check-range --both` 206 dev+preview.
- **Diff matches the claim exactly**: the only behavioral change is
  removing the `decayBelief(tellerBelief, tick)` call and using
  `tellerBelief` directly in the three places it previously used
  `decayedTeller` (confidence/verbatim/gist for the hearer's new
  belief, and the evidence's `strength`). The file's own header
  comment is updated in place to record the fix, matching this
  session's own convention for "FIXED (was filed as a finding...)"
  notes (see the `schedule_rewrite`/lane-41 precedent in the same
  file).
- **Direction of the real-data spot-check is the expected one**: since
  `decayBelief` only ever reduces confidence/verbatim/gist (decay is
  monotonically non-increasing), removing an erroneous extra decay
  step can only raise a downstream value, never lower it — the
  claimed 0.37→0.49 move for `north-star-01`'s `markarth_resident_3`
  is consistent with that, though not independently re-run live by
  the coordinator this pass (a reasonable, correctly-directioned claim
  given the mechanism, not independently re-verified byte-for-byte).

## Judgment on process

This was not a dispatched lane — chronicle-17 revisited a finding on
its own initiative. The right call here: it's a bug fix correcting a
documented divergence toward the engine's own real semantics (not new
scope, not a design decision), it was measured rather than assumed
(exactly the discipline this project has repeatedly rewarded tonight
— e.g. lane 24's "confirmed, not guessed" finding, lane 49/51's
seq-collision catches), and the blast radius genuinely was small
because it was checked rather than estimated. Accepted.

## Ruling

**Accepted.**
