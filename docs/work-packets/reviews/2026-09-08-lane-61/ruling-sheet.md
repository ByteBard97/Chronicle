# Lane 61 ruling sheet — social-mechanics-v3-foundation design doc

**Rulings proposed 2026-09-08 (not yet owner-confirmed).** A build plan
was drafted against these seven recommendations at the owner's request
("make a plan to begin work") — see `phase1-build-plan.md` in this
directory. The plan is written on the assumption O1-O7 are adopted as
recommended; it will need revision on any item the owner rules
otherwise. The governance note at the bottom (rule-directly vs.
route-to-Kimi-first) is still open and addressed to the owner, not
resolved by this session.

Status: recommendations for owner ruling. Written directly at the owner's
request (context-clear + resume session), same as the design doc itself —
outside the standing Kimi-coordinator loop per the handoff's open question.
Nothing here is self-ruled; every item below is a recommendation awaiting
the owner's yes/no.

Source: `docs/design/social-mechanics-v3-foundation.md` §12 (O1-O5), plus
two contract gaps found while preparing this sheet (O6-O7, not in the
original doc).

---

## O1 — Crystallization hysteresis rule

**Recommend:** yes — a pair must decay through neutral before flipping
sign. Concretely: the new label can only apply once the *opposing* row's
decayed value falls below its own threshold (the design doc's own proposed
mechanism, §1 S2).

**Why:** Doctrine 3 ("no threshold without hysteresis and a reason")
requires *some* rule; this one is consistent with `avoidance.py`'s
cooled-floor precedent and lane 43's already-ruled cooling-band behavior.
The alternative (one severe event flips Friend directly to Rival) reads
as more dramatic in the moment but has no precedent elsewhere in the
codebase and would need its own separate justification for why this state
gets to skip the general hysteresis doctrine.

**Cost if ruled the other way:** a discontinuous-feeling flip (Friend one
tick, Rival the next) with no cooling period — cheaper to implement, but
inconsistent with every other threshold in the codebase.

## O2 — reaction table predicate grammar / file format

**Recommend:** flat, implicitly-ANDed clause list, restricted to the
field namespaces `ReactionContext` actually exposes (`event.*`,
`sentiment_label`, `temperament.*`, `mood.*`), comparison operators
(`eq`/`neq`/`gt`/`gte`/`lt`/`lte`) on numeric fields, equality-only on
strings/enums, plus one non-recursive `any_of: [...]` OR-block per rule.
No nesting, no arbitrary boolean trees. Ranking is an explicit required
integer `priority` field (validated at load), not inferred specificity —
tiebreak: priority desc, then file load order, then rule name.

Worked example:
```json
{
  "name": "bold_approach_on_rival_insult",
  "priority": 80,
  "when": {
    "event.type": "insult",
    "sentiment_label": "Rival",
    "temperament.boldness": {"gte": 0.5}
  },
  "reaction_class": "approach"
}
```

**Why:** the strongest precedent is CIF-CK ("Prom Week meets Skyrim"),
which maps Comme il Faut's own preconditions directly onto **Creation
Kit Quest Start Conditions** (`docs/research/48-cif-ck-skyrim-social-npcs-
primary-source.md` Table 1) — the closest published academic social-rule
system, when forced to ship inside this exact engine, converged on CK's
grammar. `beliefs` (the context's raw tuple field) is deliberately kept
out of the v1 predicate surface — it's already reduced to
`sentiment_label`/`sentiment_source_belief_id` by crystallization before
reaching the reaction layer, so no existential-over-a-collection operator
is needed yet. No nesting because an arbitrary boolean tree can't be
specificity-ranked or priority-audited, which directly conflicts with
"most-specific-wins."

**Gotcha flagged by the research:** CK's own real footgun is that
ordering is manual list-order, not auto-ranked ("first Info whose
conditions are satisfied wins") — a general entry placed above a specific
one silently shadows it with no engine warning. The required `priority`
field with load-time validation exists specifically to make this an
authoring convention instead of a silent trap. Separately: RimWorld's
`ThoughtDef` XML looks fully declarative but any non-trivial condition
escapes to a compiled C# `workerClass` — recommend an explicit, loud,
logged validation failure at load for any rule referencing an
unresolvable field (e.g. a `mood.*` reference, since mood ships
always-empty in v1), never a silent fallback or an `eval()` escape
hatch.

**Cost if ruled the other way** (e.g. arbitrary boolean expressions or
inferred specificity): loses moddability safety and audit-ability; the
whole point of a ranked table is that a modder or the dashboard can look
at two rules and know which wins without executing them.

## O3 — Dread: own module or fold into crystallization.py

**Recommend:** fold into `crystallization.py`.

**Why:** both Dread and Crystallization are derived-label functions over
the same two underlying stores (`Grudge`, `Reputation`/`Fondness`), same
`is_avoiding()`-style shape. One module is the more honest boundary and
it removes lane 4's dependency edge on lane 2 (Dread no longer needs to
wait on the reaction-context contract just to get a home). Cheap to split
into its own file later if it grows; expensive to merge two already-
diverged modules back together.

**Cost if ruled the other way:** cleaner separation of concerns on paper,
but two files reading the same two stores with the same derivation shape,
and one more inter-lane dependency to sequence.

## O4 — STC ladder blocker (ADR-0011 vs. conversation-tier-design-notes)

**Recommend:** rule in the conversation-tier-design-notes' favor —
formally amend ADR-0011 §3 to adopt the deterministic parameterized-intent
menu model, and use that to unblock the STC ladder as Phase 1 work.

**Why:** the actual contradiction is narrower than it looks. ADR-0011 §3
has the LLM generate 3-5 candidate *lines* from a bare intent taxonomy in
one call. The conversation-tier-notes' amendment splits this into two
separable pieces: (1) **menu construction** — which options the player
sees — becomes a deterministic engine query over parameterized intents
(`confront, rumor_id=X`, `boast, quest_id=Y`), pure Python, no LLM, fully
testable and explainable (the dashboard can trace exactly why an option
appeared); (2) **line rendering** — how many candidate lines the LLM
produces per tap (one vs. three-to-five) — is a Phase 2 question about
LLM call shape, not a Phase 1 question at all.

The STC conversational ladder *is* piece (1) — deterministic menu/option
construction. It doesn't need piece (2) resolved to proceed. Ruling this
way converts a blocker into a scoped, buildable Phase 1 lane, and defers
the actual Phase-2-relevant open questions (confirm-vs-autoplay, free-form
input) to when Phase 2 design starts, which is where they belong per the
phase-discipline doctrine.

**Cost if ruled the other way:** the STC ladder stays blocked until
someone resolves a question (LLM call shape) that Phase 1 doesn't
actually need answered, delaying one of the seven parallel-buildable
Phase 1 systems for no mechanical reason.

## O5 — Fondness self-directed variant (Guilty)

**Recommend:** pull the self-case into scope now, but only as a field-
shape decision, not a semantics design. Concretely: confirm `Fondness`'s
constructor allows `holder_id == target_id` the same way `form_grudge()`
already has a documented self-subject bypass (lane 25 ruled "self-victim
emotional 1.0" for the grudge side). Do not design what `Guilty` actually
triggers or how it's consumed — that stays deferred.

**Why:** the design doc's own reasoning is decisive here — it's
categorically cheaper to leave a field/constructor path open now, while
`Fondness`'s shape is still being decided, than to retrofit a self-case
onto an already-shipped record later. This mirrors what the project
already did for `Grudge`.

**Cost if ruled the other way:** if `Guilty` turns out to need a
self-directed `Fondness` row later, whichever lane adds it has to touch
an already-shipped, already-tested record shape instead of a not-yet-built
one — a strictly worse position than deciding it now.

## O6 — new: reaction-rate-limit state has no home in the contract (not in the original §12 list)

**Finding:** §1 S3 says the reaction layer must rate-limit bark/expression
output "per pair per hour," but §2 X2's `ReactionContext` is a frozen
dataclass with no field for "when did this pair last fire a reaction" —
and nothing in the registry's `Reaction.evaluate(ctx)` signature has
anywhere to read or write that state either.

**Recommend:** the caller assembles rate-limit state into `ReactionContext`
the same way it assembles `beliefs` (caller-assembled discipline, X2's own
stated pattern) — e.g. a `last_fired: Mapping[tuple[str,str], float]`
slot, populated by whatever owns the per-tick sweep (likely `Driver`,
alongside the existing `_grudge_severities`/`_avoidance_thresholds` sweep
hooks). The registry itself stays pure and stateless, consistent with
X1's "reactions are a categorically different job" framing and X2's
"never queries stores itself" rule.

**Why this needs ruling now, not at lane-2 dispatch time:** it's a
contract shape decision in the single highest-risk item in the whole
packet (§2's own words) — deciding it after lane 2 is dispatched risks
exactly the kind of rework the packet was written to avoid.

**Cost if ruled the other way** (state lives inside the registry): breaks
the frozen-dataclass purity of the contract and gives the registry
mutable state to manage across ticks, which is a bigger design surface
than "one more caller-assembled field."

## O7 — new: `FondnessFormed` event — resolved, not open

§8's table flagged this as needing verification: "if grudges don't
currently emit their own event type, `Fondness` shouldn't invent an
asymmetry, flag as a finding." Checked directly:
`grep -n "class.*Event" chronicle/events.py` — the existing subclasses are
`NPCDied`, `CrimeWitnessed`, `RumorHeard`, `EscalationWarning`,
`StatusChanged`, `RoleInstalled`, `ScheduleRewrite`. **No
`GrudgeFormed`/equivalent exists.** Grudge formation is not itself logged
as a distinct `Event` subclass.

**Resolved, no owner ruling needed:** `Fondness` formation should *not*
get a dedicated `FondnessFormed` event either, matching the existing
(lack of) precedent. This dissolves the §8 flag rather than becoming a
new open point.

---

## Riding along, not part of O1-O7: two vision-v3.0 factual corrections still outstanding

The design doc's own §13 findings flagged two things it explicitly
declined to fix because they're out of its file boundary
(`vision-v3.0.md` isn't lane 61's file):

1. §1's claim that Crystallization "is still built the way v2.2
   specified" is false — confirmed by grep, nothing exists yet.
2. §6's build-order item 1 lists kin-priority routing as a
   parallel-buildable sibling system; the ray-tracing doc (written one
   day later) already contradicts this in its own §14, and §7 of the
   design doc resolves it (folds into gossip, no separate lane).

Nobody has fixed vision-v3.0.md since these were flagged. Recommend
folding a two-sentence correction into vision-v3.0.md as part of ruling
this sheet, so the next person to read it doesn't re-derive the same
false premises. Small, mechanical, low-risk — flagging for an explicit
yes/no rather than just doing it, since vision-v3.0.md is a frozen-status
document by convention.

---

## One governance note

These five-to-seven-item rulings have historically come from the
standing coordinator (the Kimi session lineage, per
`docs/work-packets/reviews/README.md`'s 2026-08-25 governance entry) —
see lanes 18, 33, 40, 44, 45 for the pattern. Lane 61 was written outside
that loop at your direct request. Want me to rule-and-proceed directly
from your answers here, or route this sheet to Kimi first?
