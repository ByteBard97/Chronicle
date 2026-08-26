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
   §8 needs its count/prose brought in line with O4 (17/20, three free
   slots) and a new row added for trust-discounted retelling if the
   owner wants to proceed — a doc amendment recording a fact and a new
   rule, not a fresh consolidation decision. Still owner-review-only
   (`AGENTS.md`'s frozen-document list), just a much lighter ask than
   originally stated here.
2. **The formula/constants in §2 have a real defect** (advisor-caught):
   `TRUST_FLOOR=0.5` and the no-relationship default both being `0.5`
   means an *unfamiliar* teller and a *maximally distrusted* one produce
   the identical `0.8 × 0.5 = 0.4` — collapsing two semantically
   different states into one. **Revised proposal:** the no-relationship
   case passes `trust=None` and takes the current flat `0.8` exactly,
   full stop — "no tracked relationship" means "no trust information to
   apply," not "assume mistrust." This also keeps T1.1's own assertion
   ("confidence = witness confidence × 0.8 **exactly**") literally true
   for every pair with no relationship edge, rather than only for pairs
   with a maximal one. `TRUST_FLOOR` itself (proposed: lower to `0.4`,
   now that it only ever applies when a real, if weak, relationship
   exists) is still a placeholder needing sign-off, not a settled number.
   Separately flagged: `Relationship`'s `co-location` basis is a weak-to-
   wrong trust proxy (two NPCs who happen to share a market stall aren't
   thereby trusting each other) — either restrict the trust lookup to
   `kinship`/`faction` bases, or treat this as its own open sub-question
   for the owner rather than silently including `co-location`.

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
