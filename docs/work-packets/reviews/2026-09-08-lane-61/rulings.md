# Lane 61 rulings (2026-09-09)

Ruled directly per the owner's instruction this session ("ask kimi and
advisor what they think, then decide; run a socratic debate only if you
still can't decide"). This resolves the ruling sheet's own closing
governance question: the owner engaged directly, so this session rules
rather than routing the packet to the Kimi coordinator lineage first.
Kimi was consulted as a technical second opinion (task `kfdgwusze`,
still running at time of writing — see addendum below once it lands),
not as the standing-coordinator approval path.

Verification method: checked each recommendation's cited precedent
directly in the repo rather than taking the ruling sheet's citations on
faith.

## O1 — RULED: yes, hysteresis required

Verified: lane 43 (`docs/work-packets/reviews/2026-08-24-lane-43/delivery-report.md:99`)
has an explicit cooling band (below 0.5, above 0.2) for its 20-tick
window; `chronicle/avoidance.py` has the cooled-floor precedent the
ruling sheet cites (`grudge_cooled`, "cooled means forgiven, not a
leftover penalty"). Adopted as recommended: a pair must decay through
neutral before flipping Friend↔Rival.

**Overlap-window label ruled (Kimi flagged as underspecified):** while
grudge is above the Rival threshold but fondness hasn't yet decayed
below the Friend threshold, the pair reads as neutral/`None`, not a
stale "Friend." "Decay through neutral" means the label passes through
an actual neutral state, not that the old label persists until the new
one is earned. One-shot Sworn-Rival-magnitude events while Friend is
strong are correctly blocked for the full decay window under this rule
— that's the intended, conscious cost of hysteresis, not a bug.

## O2 — RULED: yes, flat ANDed-clause grammar

Verified: `docs/research/48-cif-ck-skyrim-social-npcs-primary-source.md`
Table 1 confirms CIF-CK's mapping onto Creation Kit Quest Start
Conditions is real, not a stretched analogy. Adopted as recommended:
flat implicitly-ANDed clauses, restricted field namespaces
(`event.*`/`sentiment_label`/`temperament.*`/`mood.*`), `eq/neq/gt/gte/
lt/lte` on numerics, equality-only on strings/enums, one non-recursive
`any_of` OR-block, required integer `priority` (validated at load, no
inferred specificity), tiebreak priority→load-order→name, loud logged
failure on any unresolvable field reference.

Flagged, not blocking: whether flat-AND stays expressive enough as the
reaction table grows. Not resolved by precedent either way — genuine
judgment call, but not one that blocks shipping v1 (the `any_of` escape
hatch covers the near-term OR cases the design doc anticipates, and the
loud-validation-failure rule means outgrowing the grammar fails loud,
not silently). Revisit if/when a real rule can't be expressed.

**Load-order determinism ruled (Kimi finding):** file enumeration order
must be explicitly sorted (alphabetical by filename) at load time, not
left to directory-listing order. Left unsorted, the tiebreak
(priority → load-order → name) becomes platform-dependent, which
collides with the project's byte-identical-logs doctrine. This is a
one-line requirement on whoever writes the loader, not a design change.

**Rate-limit state is explicitly out of the O2 grammar (resolves the
O2↔O6 inconsistency Kimi flagged):** `last_fired` is not a namespace a
rule author can reference, and "per pair per hour" is not expressed as
a predicate at all — see O6 below. The registry's field surface stays
exactly `event.*`/`sentiment_label`/`temperament.*`/`mood.*`; rate
limiting is a pre-filter the caller (`Driver`) applies before a
candidate reaction is even offered to the registry for evaluation, not
a rule condition. This keeps the moddable surface (data files) and the
engine-owned bookkeeping (timing state) on opposite sides of the same
line X2 already draws ("registry never queries stores itself").

## O3 — RULED: yes, fold Dread into crystallization.py — rationale corrected

Adopted, but not for the reason the ruling sheet gave. The build plan's
own text shows the "removes a dependency edge" justification doesn't
survive contact with the plan's own lane breakdown — Dread's valence
conversion still reads lane 2's `temperament.boldness` fixture regardless
of which file it lives in. Rule this on the actual solid ground instead:
Dread and Crystallization are both derived-label functions over the same
two stores (`Grudge`, `Fondness`), same `is_avoiding()`-style shape — one
module is the honest boundary, cheap to split later if it grows.

## O4 — NOT ruled by this session; owner-signature item

This is a formal ADR amendment (ADR-0011 §3), and the build plan says so
explicitly: "itself an owner-level decision, not a pre-lane chore this
plan can just schedule — O4 recommends the amendment, it doesn't
authorize it." A design session ruling on its own ADR amendment isn't
the same kind of decision as O1/O2/O3/O5/O6. **Owner: does the
recommended split stand — menu construction (deterministic, Phase 1) vs.
line-rendering call shape (Phase 2, deferred) — yes/no?** Lane 6 (STC
ladder) stays blocked until this is answered; everything else in this
file is unaffected by the answer.

## O5 — RULED: yes, field-shape only

Mirrors `form_grudge()`'s existing self-victim bypass (lane 25, "self-
victim emotional 1.0"). `Fondness`'s constructor allows `holder_id ==
target_id`; no `Guilty` semantics designed, deferred as scoped.

## O6 — RULED: yes, caller-assembled rate-limit state, with two additions

Verified: `chronicle/driver.py` already has this exact shape —
`_grudge_severities` (line 1753) and `_avoidance_thresholds` (line 1769)
are caller-assembled per-tick sweep state feeding into `_evaluate_rule`,
not state owned by the thing being evaluated. `last_fired: Mapping[tuple[
str,str], float]` assembled the same way, populated by `Driver`, read by
the otherwise-pure `ReactionRegistry`. Adopted as recommended, plus:

**Enforcement point (resolves the O2 inconsistency):** `last_fired` is
read by `Driver` as a pre-filter before a candidate reaction reaches the
registry at all — not passed into `ReactionContext` as an evaluable
field. It gates whether a pair is eligible for reaction evaluation this
tick, full stop.

**Persistence ruled (Kimi finding, correctly flagged as missed):**
`last_fired` must round-trip through save/load like any other
tick-scoped Driver state — `_grudge_severities`/`_avoidance_thresholds`
are safe to omit from keyframes only because they're recomputed fresh
from persisted `Grudge` rows every tick; `last_fired` has no underlying
store to recompute from, so skipping it would let rate-limit state
silently reset on reload, diverging the sim from a continuous run. Add
it to the keyframe via the same four-touch-point convention framelog
already uses for other Driver-owned state (`serialize_state`/
`load_state`).

**Key directionality ruled:** ordered `(observer_id, subject_id)` tuple,
not a `frozenset` pair. This deliberately breaks precedent with
`_grudge_severities`' frozenset keying — that's correct there because
grudge severity is symmetric enmity strength, but a reaction is a
specific NPC's response to a specific event about a specific other NPC;
A's rate limit reacting to B and B's rate limit reacting to A are
independent and must not share a key.

## O7 — RULED: the Event-subclass conclusion holds, but "nothing to build" was wrong

Confirmed independently via `grep -n "class.*Event" chronicle/events.py`:
`NPCDied`, `CrimeWitnessed`, `RumorHeard`, `EscalationWarning`,
`StatusChanged`, `RoleInstalled`, `ScheduleRewrite` — no `GrudgeFormed`
Event subclass, so no `FondnessFormed` Event subclass either. That part
of the ruling sheet's finding stands.

**Correction (Kimi caught this, verified directly):** grudge formation
*is* logged, just not as an `Event` subclass — `Driver.form_grudge()`
(`driver.py:844`) emits a `grudge_formed` trace record
(`driver.py:855`, consumed by `framelog.py:931`), matching the design
doc's own schema §4. The real precedent is "trace record, not Event
subclass," not "no record at all." Lane 1 must add the equivalent
`Driver.form_fondness()` wrapper emitting a `fondness_formed` trace
record — mirroring `form_grudge`'s wrapper exactly, including the
driver.py call site(s) that invoke it (see "lane 1 boundary" below).
Shipping Fondness formation with no trace record at all would be
silent in a way the rest of this packet's own doctrine ("visible, not
silent") forbids.

## vision-v3.0.md corrections — already applied, closed

Checked `git diff docs/vision-v3.0.md` directly: both stale claims the
ruling sheet flagged are already corrected in the current working tree
(uncommitted) — §1 now reads the honest "not yet built, ruled in lane
61" version, and the build-order item now folds kin-priority routing
into the gossip lane per §7 instead of listing it as a parallel system.
This item is done, not pending; nothing further to ask the owner here.

## Dispatch blockers surfaced while ruling (separate from O1-O7 — must be resolved before lane dispatch, not before this ruling)

1. **Lane 1 ↔ lane 2 is a mutual dependency the build plan states but
   never names as a cycle.** Lane 1's own text: "lane 1 still depends on
   lane 2 for Dread specifically." Lane 2's own text: "Depends on lane 1
   for the `sentiment_label`/`sentiment_source_belief_id` input shape."
   The plan's "any serialization order is correct" claim is scoped to
   `driver.py` contention only, not to this. Needs a concrete resolution
   (e.g., freeze lane 2's `temperament` static-fixture shape first since
   Dread only needs the fixture, not the full registry; land the rest of
   lane 2 and lane 1's Crystallization core in parallel) before either
   lane is dispatched.
2. **Lane 1's boundary is understated (Kimi finding, verified):** the
   plan scopes lane 1 to `chronicle/crystallization.py` only. But
   Fondness formation needs a `Driver.form_fondness()` wrapper and its
   driver.py call site(s), exactly mirroring the verified
   `Driver.form_grudge()` pattern (`driver.py:844`, called from
   `driver.py:922` and `driver.py:1070`). Lane 1's file boundary is
   `chronicle/crystallization.py` **plus** a `driver.py` touch — making
   this a **fourth** `driver.py` claimant, not three.
3. **`driver.py` sequencing, corrected for four claimants:** natural
   order is **lane 1's formation call site → lane 3 (gossip-writeback,
   interchangeable with lane 1) → lane 2's Driver-wiring block → lane 5
   (pacing)** — lane 1 before lane 2's wiring since lane 2 already
   depends on lane 1's `sentiment_label` output shape regardless of
   `driver.py` contention.
4. **§8's event/RNG table has more unruled leftovers than O7 alone.**
   O7 resolves only `FondnessFormed`. `HookCreated`/`HookSpent`,
   `OffScreenEventFired`/`Suppressed`, `PACING_BUDGET_SPEND`, and a
   possible `DREAD_REPORT_DECISION` remain unruled — fine to rule
   per-lane when lanes 4-6 (leverage, pacing, STC ladder) are actually
   dispatched, but flagging now so it isn't mistaken for already closed.

## Kimi cross-check — complete (task `kfdgwusze`)

Dispatched `kimi_agent` with the ruling sheet and build plan for an
independent technical opinion. It verified every factual citation
against the actual code (confirmed independently, not just trusted) and
surfaced four real gaps, all folded into the rulings above rather than
left open: the O7 trace-record correction, the O2↔O6 rate-limit
expressiveness gap, lane 1's understated `driver.py` boundary, and O6's
missing persistence/keyframe requirement. It also flagged smaller
items now resolved above: O1's overlap-window label, O2's load-order
determinism hazard, and O6's key directionality.

**No item required a socratic debate.** Every gap Kimi raised was a
concrete, verifiable engineering question (checked against repo
precedent — `framelog.py`, `driver.py`'s existing sweep-state pattern,
`social.py`'s self-victim bypass) with a decidable answer, not a values
or tradeoff disagreement between two defensible positions. The one item
advisor flagged in advance as the likeliest debate candidate (O2's
long-term grammar expressiveness) turned out, once Kimi looked closely,
to have a concrete near-term answer (rate-limiting simply isn't in the
grammar's scope) rather than an open philosophical question.

Kimi's one point of actual disagreement with the ruling sheet — O3's
stated rationale being misleading — matches this session's own
independent read before Kimi was consulted (see O3 above): both landed
on "adopt the conclusion, reject the stated reason" via the same
build-plan text, not via debate.

## Addendum (2026-09-10) — dispatch blocker #1, RULED

Resolved during the `phase1-build-plan.md` pre-dispatch review (Kimi
technical pass + advisor). Blocker #1's original framing only broke one
edge of the lane 1↔2 cycle (freezing lane 2's `temperament` fixture
resolves lane 1's dependency on lane 2, but leaves lane 2's dependency on
lane 1's `sentiment_label` shape unaddressed — Kimi caught this as an
asymmetric fix).

**Ruled:** lane 2 owns the `ReactionContext` contract, so it also owns
specifying the `sentiment_label`/`sentiment_source_belief_id` input
shape — frozen at the same time as the `temperament` fixture, before
either lane starts. Lane 1's `crystallize()` conforms to the frozen
shape. Both edges resolved the same way: lane 2 freezes both of its
input contracts up front, then lanes 1 and 2 build in parallel against
the frozen shapes. This is a technical sequencing decision within this
session's standing ruling authority (same basis as O1-O3/O5-O7), not an
owner-signature item like O4 — no ADR is implicated and nothing here is
reversible-with-difficulty if wrong.
