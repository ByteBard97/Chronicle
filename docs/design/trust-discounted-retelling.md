# Design prep — trust-discounted retelling

**Status:** ruled and ready to implement. Every open question in this
doc's earlier drafts (§3) has been resolved via two rounds of independent
review (advisor, Kimi with a sourced research pass) plus direct
verification against the code — the owner has no domain opinion on
tuning questions like these and has delegated them to that process
(session policy, `docs/loop-playbook.md`). The one remaining action
before code is a small, mechanical amendment to `docs/scenario-ladder.md`
§8 (§3.1 below) — not a design decision, a doc catching up to a ruling
that already happened.

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

`retell()` gains an optional `trust: float | None = None` parameter.
Migration-safe by construction, same idiom as every other
caller-supplies-context parameter in this codebase: omitting it
reproduces today's exact flat-0.8 behavior on every axis.

**Confidence only — ruled (Kimi, verified against `claims.py`'s
docstrings).** Trust discounts `confidence` alone.
`verbatim_strength`/`gist_strength` (`RETELL_VERBATIM_DECAY`/
`RETELL_GIST_DECAY`) stay exactly as they are regardless of trust. The
two axes are deliberately orthogonal in this fuzzy-trace-theory model:
verbatim/gist are *how precisely the content is retained*, confidence is
*whether the hearer believes it's true* — a source-credibility judgment
has no plausible mechanism for changing memory precision, and this
schema can already express "I don't believe a word Belethor says, but I
remember exactly what he claimed." `stage_at()` keys "forgotten" off
decayed `gist_strength` (`claims.py:274`); discounting gist by trust
would make low-trust rumors both less-believed *and* erased sooner —
double-counting distrust in a way nothing has modeled. `corroborate()`
already draws exactly this line (boosts confidence from testimony,
leaves verbatim/gist untouched) — this follows the codebase's own
established pattern.

When `trust` is given, the confidence multiplier is:

```
effective_decay = RETELL_CONFIDENCE_DECAY * (TRUST_FLOOR + (1 - TRUST_FLOOR) * trust)
```

`TRUST_FLOOR = 0.5` at `trust=0.0`; at `trust=1.0`, `effective_decay`
equals the current flat `0.8` exactly (T1.1's "× 0.8 **exactly**"
assertion holds unchanged at maximal trust). Linear, not sigmoid or
threshold-gated — both independent reviews converged on this; it matches
the canonical trust-weighting literature (DeGroot 1974; Friedkin–Johnsen)
and composes correctly across multi-hop retellings the way trust-path
literature expects. **Not drawn from the CK research** cited above (that
citation is for the *category* of prior art — deterministic gates plus
scored multipliers over time — not a borrowed per-retelling formula).

**No-relationship default: `trust=0.5`, the interval's midpoint — ruled
(Kimi's research, verified against the schema).** `Relationship.strength`
is hard-gated to `[0,1]` by `_require_unit_interval` (`social.py`); no
code anywhere constructs a negative or "hostile" value — active distrust
lives only in `Grudge`, a separate mechanism. So "a weak real edge" and
"no edge at all" are the *same kind* of signal (weak-or-absent positive
tie), not "neutral vs. distrusted," and treating them alike is correct,
not a collapse — matching Granovetter's weak-ties result that a message
from a weak or absent tie lands, just at reduced confidence. Concretely
load-bearing for this project: T2.6's cross-hold carriers are
*structurally* strangers (no co-location/kinship/faction/employer
history at all); giving strangers the full undiscounted `0.8` would let
carrier-borne rumors cross hold boundaries at full confidence, undoing
the exact "weaker signal across a hold boundary" effect carriers exist
to model. `TRUST_FLOOR`/the default remain placeholder tunables in the
spirit of `social.py`'s existing grudge half-lives — real numbers, not
load-bearing precision — but the *shape and default* are settled.

**Relationship lookup — ruled.** Direction: `relationship(hearer_id,
teller_id, ...)` — trust is the *hearer's* regard for the *teller*,
never the reverse (`Relationship` edges are directed). Basis filter:
**exclude `colocation`, use max strength over `{kinship, faction,
shared_employer}` only** — ruled (Kimi, verified against
`chronicle/social.py`/`chronicle/fixtures/whiterun_relationships.py`).
`colocation` edges are hand-seeded fixture constants (`strength` is a
caller-supplied literal at construction, e.g. `0.5` for hulda→ysolda);
nothing in the codebase ever updates a `Relationship`'s `strength` after
formation, so a colocation edge tracks no real signal (not encounter
count, not familiarity, not time) — including it would inject
meaningless trust boosts and, once the encounter-sampling seam
`social.py`'s own docstring reserves `colocation` for eventually lands,
would silently turn every co-present pair into a trust floor that erases
the no-relationship case above as a side effect. Kinship/faction/employer
strengths were hand-set with real intent (the fixtures use 0.85–0.95 for
employer, 0.9 for kinship) — those are the bases that actually encode
regard.

**The contested-resolution path inherits the same discount — ruled.**
`chronicle/claims.py`'s T2.3 resolution path (`challenger_wins` branch,
~line 786) has its own independent hardcoded use of
`RETELL_CONFIDENCE_DECAY` — missed in this doc's original §0 inventory,
caught in review. It takes the same `trust` parameter and the same
formula; leaving it flat would make trust matter *least* exactly when
two accounts collide, which is the moment source credibility should
matter *most*.

**Evidence-chain consequence**: `Evidence.strength` already records "the
teller's pre-decay confidence... what an inspector re-judging the chain
needs" (claims.py's own comment) — unaffected, since trust discounts the
*hearer's* resulting confidence, not the teller's recorded testimony
strength. The trust value used is recorded on the trace record (a
`trust_applied` field alongside the existing `retell`-produced row) so a
provenance drill-down can show *why* a retelling landed at a given
confidence — matching this project's inspectability doctrine
(`docs/architecture.md`).

**Named risk to cover in tests, not a blocker:** trust-discounting
stacked on kinship/faction edges is the standard homophily→polarization
mechanism in bounded-confidence trust models. A scenario test should
assert rumors still cross faction lines at reduced (not zero) confidence
— otherwise this could silently partition the rumor graph along faction
borders, the class of failure T2.6's carriers exist to prevent
geographically.

## 3. The one remaining action: a frozen-doc catch-up, not a decision

`docs/scenario-ladder.md` §8 currently reads "Count: 19 named rules
against the ~20 ceiling... must spend the remaining slot deliberately or
consolidate." That's stale: `chronicle/rules.py`'s own module docstring
records a ruling already made — **"Budget (O4 ruling): 9+10 are one
state machine and 4 is schema-not-rule -- 17/20 against the ceiling."**
Verified directly: rules 9 (`RumorStageRule`) and 10
(`DormancyReactivationRule`, `rules.py` ~line 201) both wrap the *same*
`claims.stage_at()` call — rule 10's own docstring already concedes "the
stage machine's dormancy half (O4: 9+10 are one machine)." The ladder
doc's §8 prose just never absorbed that ruling.

**Action for whoever lands this code:** amend `docs/scenario-ladder.md`
§8 to (a) merge the 9/10 table rows into one, bringing the count to
18/20, matching the ruling `rules.py` already records, and (b) add a new
row for trust-discounted retelling, landing at 19/20. No rule-4 demotion,
no ceiling raise — this is recording a fact and adding one row, not
opening the consolidation question. This is still a frozen,
owner-review-only document (`AGENTS.md`) in the sense that it shouldn't
be edited carelessly — but a design doc that has been through two
independent reviews and rules cleanly on its own open questions is
exactly the case that document's freeze is meant to allow through, not
block.

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
