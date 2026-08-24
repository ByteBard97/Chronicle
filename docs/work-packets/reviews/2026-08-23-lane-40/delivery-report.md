# Lane 40 delivery report — Tier 4b design prep (avoidance)

**Delivered:** `docs/design/tier-4b-avoidance.md` (content verified
byte-identical to what's on disk; see the housekeeping note below about
the commit it landed in). No code. Suite unchanged: 218 passed, ruff
clean.

## Cover note

**Decided** (this doc's own recommendations, ready to build against):

- A per-pair threshold **replacement** (`frozenset`-keyed), not a
  multiplier, computed by the driver fresh each tick from active
  grudges — the exact same per-tick-consultation shape lane 36
  established for schedule overlays. `AVOIDANCE_PROBABILITY = 0.0` is
  proposed deliberately as a hard zero, not a small placeholder, so
  T4b.1's "encounters... cease" reads as an exact, assertable guarantee
  rather than a probabilistic approximation that could flake under a
  different seed or run length.
- **No new record type.** The existing `encounter_rolled.threshold`
  field already carries the weight delta; a paired `rule_evaluated` row
  (rule 18, once per avoiding pair per tick — not a global sweep) is
  what makes the *reason* visible without a schema change, matching how
  every other Tier-3/4a rule reuses that same shape.
- Cooling/reheating needs no special-case machinery at all — it falls
  straight out of `grudge_at`'s continuous decay, the same
  derived-not-destroyed discipline as the rest of the tier. A genuine
  three-stage severity progression (avoiding / cooling / forgiven) falls
  out for free once `AVOIDANCE_GRUDGE_THRESHOLD` sits above
  `forgiveness_threshold`'s default.
- Rule 18 registers exactly like rule 17: real (driver-owned) toggle,
  no rule-budget change (already counted in the raw 19), no new RNG
  purpose (same roll, different comparison threshold).

**Needs adjudication** (owner-visible, §6 in the doc):

- **O1 — `AVOIDANCE_PROBABILITY = 0.0`.** Recommend zero over a small
  nonzero placeholder, for the reason above.
- **O2 — `AVOIDANCE_GRUDGE_THRESHOLD = 0.5`.** Placeholder; the
  ordering requirement (above `forgiveness_threshold`'s 0.2 default) is
  load-bearing, the number isn't.
- **O3 — no bulk `grudges()` accessor on `SocialStateStore`.** The
  driver reading `self.social._grudges.values()` directly follows an
  existing precedent but is a private-attribute reach from outside
  `social.py`; flagged so the implementing lane's packet makes an
  explicit call rather than silently reaching for `_grudges` again.
- **O4 — mutual-grudge collapse.** A two-directional grudge folds into
  one avoidance key with no special handling; a real modeling
  simplification worth the owner's eyes, though no rung needs the
  distinction.

**Surprises:**

1. The preview (Tier-4a doc's T6b) turned out to need almost no
   correction against the landed code — `sample_encounters`'s signature
   and the roll-vs-threshold split are exactly as sketched. Most of this
   lane's actual work was precision: naming the exact rung assertion
   (§2), the exact distinguishing test (`threshold` value + a same-tick
   rule-18 row), and confirming (not just assuming) that lane 37's
   fixture forms zero grudges (`grep form_grudge
   scenarios/test_tier4a_counterfactual.py` — no matches), so the
   roll-identity/avoidance interaction question (§5) resolved to "no
   current conflict" rather than needing a design change.
2. Two separate thresholds already exist on `Grudge`
   (`forgiveness_threshold`) and needed to be joined by a *third*
   concept (`AVOIDANCE_GRUDGE_THRESHOLD`) rather than reusing
   `forgiveness_threshold` itself — a grudge that's "not yet forgiven"
   and a grudge that's "actively causing avoidance" are different
   claims, and collapsing them would mean every unforgiven grudge
   (however faint) causes avoidance forever, which doesn't match "a
   strong grudge" in the rung text.

## Housekeeping note (process, not content)

The design doc's own commit (`0740c1b`) unexpectedly bundled several
Track B dashboard files (`dashboard/src/derived/socialDiff*`,
`dashboard/src/views/DiffScreen.vue`, etc.) that were staged by a
concurrent session between my `git add
docs/design/tier-4b-avoidance.md` and `git commit` — a shared-working-
directory race, not anything wrong with either side's content. Verified
directly: `docs/design/tier-4b-avoidance.md`'s content in that commit
is byte-identical to what's on disk (no corruption), and the dashboard
files are otherwise untouched by anything in this lane (`git diff
chronicle/` for this lane is empty as required). Flagging so the
coordinator's review of that commit isn't confused by the unrelated
diff, and so any correction (if wanted) is a deliberate call rather
than something I did unilaterally — I did not rewrite history to split
it apart.
