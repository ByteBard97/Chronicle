# Design prep — trust-discounted retelling

**Status:** design proposal only. Implementation is blocked on two
owner decisions named in §3 — this doc scopes the mechanism precisely
enough to rule on, it does not commit to landing it.

Sources: `docs/scenario-ladder.md` §6 ("Trust-discounted retelling
(deliberately deferred; feeds social state into claims and deserves its
own rung when wanted)") and its T1.1 note; T2.3's ruling (re-homed the
v0.3 draft's "trusted-relationship teller" tier for exactly this reason,
naming `chronicle/propagate.py`'s caller-supplies-context pattern as the
model to build on); `chronicle/claims.py`'s `retell()` (the actual flat
decay this replaces) and `RETELL_CONFIDENCE_DECAY` constant;
`chronicle/social.py`'s `Relationship` (the trust proxy this reuses, no
new data model); `docs/research/comparative-systems/
ck-opinion-decay-and-threshold-tables.md` (CK2/CK3 opinion-decay prior
art, cited for the mechanism shape, not copied as-is — Chronicle's
provenance/evidence-chain model has no CK equivalent).

## 0. What this replaces, precisely

`chronicle/claims.py`'s `retell()` hardcodes:

```python
confidence=teller_belief.confidence * RETELL_CONFIDENCE_DECAY,  # 0.8, flat, everyone
```

Every retelling loses the same 20% of confidence regardless of who's
telling whom — a stranger's secondhand account and a trusted friend's
are indistinguishable. This is deliberately simple for v0.1 (ladder
T1.1: "confidence = witness confidence × 0.8 exactly (flat decay —
trust-discounted retelling is a deliberately deferred mechanism)") —
not a bug, a named placeholder.

## 1. What already exists to build on

- **The trust proxy**: `chronicle/social.py`'s `Relationship.strength`
  (already `[0,1]`, already keyed `(from_id, to_id, basis)`) — no new
  schema. A relationship's existence isn't guaranteed for every
  teller/hearer pair (only co-location/kinship/faction/shared-employer
  bases create one at all); this design must define the no-relationship
  case, not assume one always exists.
- **The caller-supplies-context pattern**: `chronicle/propagate.py`'s
  `teller_and_hearer()`/`conflicting_pair()` take a `ClaimStore` and look
  up beliefs themselves, but never look up social state — T2.3's ruling
  is explicit that this is deliberate, and the exact mistake to avoid
  (the v0.3 draft's rejected middle tier read layer-4 relationship edges
  inside a Tier-2 claims operation). The fix: the **driver** looks up the
  relevant `Relationship` (if any) and passes its `strength` into
  `retell()` as a plain float parameter — `retell()` itself gains no
  store access, exactly like `form_grudge()`'s `relationship_to_victim`
  parameter (caller already did the lookup) or `TellDecisionRule`'s
  caller-assembled `motive`/`roll_value` inputs.

## 2. The mechanism (proposed, not yet ruled)

`retell()` gains an optional `trust: float | None = None` parameter
(caller-supplied `Relationship.strength`, or `None` when no relationship
exists between teller and hearer). Migration-safe by construction, same
idiom as every other caller-supplies-context parameter in this codebase:
omitting it reproduces today's exact flat-0.8 behavior.

When `trust` is given, the confidence multiplier becomes:

```
effective_decay = RETELL_CONFIDENCE_DECAY * (TRUST_FLOOR + (1 - TRUST_FLOOR) * trust)
```

`TRUST_FLOOR` (proposed placeholder: `0.5`) is the multiplier applied at
`trust=0.0` (a hostile/unfamiliar teller) — at `trust=1.0` (maximal
existing relationship strength) `effective_decay` equals the current
flat `0.8` exactly, so a maximally-trusted retelling is unchanged from
today and every retelling gets *worse*, never better, as trust drops.
This linear form is the simplest shape that satisfies T1.1's own
constraint ("confidence = witness confidence × 0.8 **exactly**" at full
trust) while giving low trust real teeth — it is NOT drawn from the CK
research (CK's opinion decay is about modifier decay rates over time,
not per-retelling discount factors; the citation above is for the
*category* of prior art — deterministic gates plus scored multipliers —
not a borrowed formula). Both `TRUST_FLOOR` and the `None`-case default
(proposed: treat as `trust=0.5`, the interval's midpoint, since "no
tracked relationship" is not the same claim as "actively distrusted") are
placeholder tunables in the same spirit as `chronicle/social.py`'s
existing grudge half-lives — real numbers, not load-bearing precision,
named here so a reviewer rules on the *shape* rather than rediscovering
it from a diff.

**Evidence-chain consequence**: `Evidence.strength` already records "the
teller's pre-decay confidence... what an inspector re-judging the chain
needs" (claims.py's own comment) — this is unaffected, since trust
discounts the *hearer's* resulting confidence, not the *teller's*
recorded testimony strength. The trust value itself should also be
recorded somewhere on the evidence/trace record (proposed: a
`trust_applied` field alongside the existing `retell`-produced trace
row) so a provenance drill-down can show *why* a retelling landed at a
given confidence, not just that it did — matching this project's
inspectability doctrine (`docs/architecture.md`).

## 3. Why this is blocked, not just unstarted

**Correction (advisor-caught, verified against the code directly):** the
first draft of this doc said trust-discounted retelling would spend "the
ladder's last remaining slot," reading `docs/scenario-ladder.md` §8's
"Count: 19 named rules against the ~20 ceiling... must spend the
remaining slot deliberately or consolidate" at face value. That's stale.
`chronicle/rules.py`'s own module docstring records a ruling already
made: **"Budget (O4 ruling): 9+10 are one state machine and 4 is
schema-not-rule -- 17/20 against the ceiling."** Both of §8's own named
consolidation candidates were already ruled on — the effective count is
17, not 19, meaning **three slots are free**, not one. The frozen ladder
doc's §8 text was never updated to reflect O4; that's a real
inconsistency between two documents, not a re-litigation of the
consolidation question. Two owner items remain, both smaller than
originally framed:

1. **A frozen-doc update, not a scope tradeoff.** `docs/scenario-ladder.md`
   §8 needs its count/prose brought in line with O4 and a new row added
   for trust-discounted retelling if the owner wants to proceed — a doc
   amendment, not a fresh consolidation decision. Still owner-review-only
   (`AGENTS.md`'s frozen-document list), just a much lighter ask than
   originally stated here. **Kimi's independent research pass sharpened
   this further, code-verified directly (not just cited):** rules 9
   (`RumorStageRule`) and 10 (`DormancyReactivationRule`, `rules.py`
   ~line 201) both wrap the *same* `claims.stage_at()` call — rule 10's
   own docstring already concedes "the stage machine's dormancy half
   (O4: 9+10 are one machine)." Merging them is a real simplification,
   not ceiling-fudging, and drops the count to 18 on its own; landing
   trust-discounted retelling as rule 19 needs no rule-4 demotion and no
   ceiling raise. Recommended path: merge 9+10, add trust-discounted
   retelling as 19/20, leave rule 4 and the ceiling alone.
2. **The formula's floor/no-edge-default value has an unresolved
   disagreement between the two independent reviews — genuinely open,
   not something this doc should silently pick a side on.**
   - **Advisor's objection:** `TRUST_FLOOR=0.5` and the no-relationship
     default both at `0.5` collapse an *unfamiliar* teller and a
     *maximally distrusted* one to the identical `0.8 × 0.5 = 0.4`.
     Proposed fix: no-relationship passes `trust=None`, taking the flat
     `0.8` exactly (no trust data → no adjustment), and `TRUST_FLOOR`
     applies only when a real, if weak, relationship exists.
   - **Kimi's research-backed counter:** `Relationship.strength` is
     `[0,1]` — **there is no negative/distrust value anywhere in this
     schema**; active dislike is a `Grudge`, a separate mechanism. So
     "trust→0 via a weak real edge" and "no edge at all" both mean
     *weak-or-absent positive tie*, not "trusted vs. distrusted" — under
     that reading, giving them the same discount isn't a bug, it matches
     Granovetter's weak-ties literature (a message from a weak or absent
     tie lands, but at reduced confidence — informationally similar
     cases, correctly treated alike) and DeGroot/Friedkin-Johnsen's
     canonical linear trust-weighting (cited: Proskurnikov et al.,
     Ye et al. 2020). Kimi also names a concrete Chronicle-specific risk
     for advisor's fix: T2.6's cross-hold carriers are *structurally*
     strangers (no co-location/kinship/faction/employer history at all)
     — if "no edge" took the undiscounted flat `0.8`, carriers would
     propagate rumors across holds at full confidence, undermining the
     exact "weaker signal across a hold boundary" effect carriers exist
     to model.
   - **This doc does not resolve that disagreement — it's a real
     modeling-philosophy call** (does the schema's `[0,1]` strength
     range represent a trust axis with an implicit distrust floor, or a
     tie-strength-only axis with no distrust concept at all?) that
     should go back to whoever's ruling on this, not be picked by
     whichever advisor answered second.
   - **Not in dispute, independent of that question:** the linear shape
     itself (both reviews converge on it; no sigmoid/threshold
     convention was found in the literature scan), and `TRUST_FLOOR`/the
     default being placeholder tunables needing sign-off regardless of
     which side of the above they land on.
   - Separately flagged (Kimi): `Relationship`'s `co-location` basis is
     a weak-to-wrong trust proxy (two NPCs who happen to share a market
     stall aren't thereby trusting each other) — either restrict the
     trust lookup to `kinship`/`faction` bases, or treat this as its own
     open sub-question rather than silently including `co-location`.

3. **Three implementation gaps Kimi's review caught that this doc's
   first draft missed entirely — all need a ruling before code, not
   just before merge:**
   - **Directionality.** `Relationship` edges are directed
     `(from_id, to_id, basis)`. Trust here must be the *hearer's* regard
     for the *teller* — the lookup is `relationship(hearer_id,
     teller_id, ...)`, not the reverse. §2 above didn't specify this;
     it must before any code is written.
   - **Multi-edge pairs.** The same (teller, hearer) pair can hold
     several relationship bases at once (e.g. kinship *and* faction).
     Kimi's proposal: take the **max** strength across bases (any
     strong tie confers credibility) — reasonable, not yet ruled.
   - **The contested-resolution path also hardcodes the flat decay,
     undocumented by this doc's own §0 inventory.** Verified directly:
     `chronicle/claims.py`'s T2.3 resolution path (`challenger_wins`
     branch, ~line 786) computes
     `teller_belief.confidence * RETELL_CONFIDENCE_DECAY * (1 - CONTESTED_CLAIM_CONFIDENCE_DENT)`
     — a second, independent use of the exact constant `retell()` uses,
     missed in §0's "what this replaces" scan. Needs an explicit ruling:
     does contested-claim resolution also become trust-discounted (the
     "yes, consistently" answer — leaving it flat would make trust
     matter *less* exactly when two accounts collide, the moment it
     probably matters most), or is it deliberately left flat? This doc
     recommends applying the same discount there, but that's a proposal,
     not a decision made here.
   - **Named risk, not necessarily a blocker:** trust-discounting
     stacked on kinship/faction edges is the standard homophily→
     polarization mechanism in bounded-confidence trust models — without
     a scenario assertion that rumors still cross faction lines (at
     reduced confidence, not zero), this could silently partition the
     rumor graph along faction borders, the same class of failure T2.6's
     carriers were added to prevent geographically. Worth a scenario
     test if this lands, not necessarily a redesign.

## 4. Non-goals for this doc

- CK-style named-relationship crystallization (Friend/Rival/Nemesis
  labels) — a separate, larger mechanism (`docs/design/
  next-phases-2026-08.md` §3's "v0.3 headline features" note), not part
  of trust-discounting a retelling's confidence.
- Any change to `chronicle/propagate.py` itself — it stays exactly as
  thin as T2.3 already ruled; the driver does the relationship lookup,
  not `propagate.py`.
- A new `Relationship` basis for "trust" specifically — reusing the
  existing `strength` field on whatever relationship basis already
  connects teller and hearer, rather than inventing a parallel trust
  score, is this doc's own proposal (§1), open to being overruled if a
  reviewer disagrees that existing bases are a good trust proxy.
