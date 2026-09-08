# Lane 61 — Social-mechanics-v3.0 foundation design prep (design doc, no code)

**Status:** Ready now. **Design-doc lane — no production code**, same shape
as lane 18 (Tier-3 rule registry) and lane 33 (Tier-4a schedule
write-back): read those two docs and their overseer reviews first, that
loop is the model. The deliverable is one markdown document for owner
review, not an implementation.

**Effort:** large (deep reading across a new vision doc, a research
reframe, and the full existing engine; one substantial document).

**This is new-track work, not a ladder tier.** `docs/scenario-ladder.md`
is FINAL/frozen (Tiers 0–6, rules 1–20, explicitly at rule-budget
ceiling per its own §8 and `chronicle/rules.py:33-34`). Nothing here
amends it, adds a rule to `chronicle/rules.py`'s registry, or touches
`chronicle/tests/`. This packet's systems are the *next* layer described
in `docs/vision-v3.0.md` §6 build order item 1 — a new, separate track.

## Context

`docs/vision-v3.0.md` (2026-09-07) reframes Chronicle's headline from
NPC-grudge-tracking to a belief-driven world-event layer, and
`docs/research/comparative-systems/social-ray-tracing-player-view-2026-09-07.md`
re-derives the same 15 candidate systems by tracing backward from what
the player actually notices. Vision §6 names 7 systems as "pure-Python,
zero-engine-risk, buildable in parallel": gossip mutation + transitive
writeback, the production-rule reaction layer, Secrets/Hooks leverage,
the Dread axis, the world-event pacing director, the STC conversational
ladder, kin-priority belief routing.

**That framing has two verified problems this packet exists to fix
before any implementation lane starts:**

1. **Vision §1 claims "Crystallization... is still built the way v2.2
   specified." It is not built.** A direct grep of `chronicle/` finds
   zero named-state/founding-memory code; "sentiment" appears only
   incidentally. Four of the seven listed systems (gossip writeback,
   the reaction layer, Dread, the STC ladder) read or write a
   sentiment/named-state concept that does not exist yet. Building them
   in parallel against an undesigned shared store is a guaranteed
   collision.
2. **Kin-priority routing is mis-listed as a parallel sibling.** The
   ray-tracing doc's own §14 says plainly: "this system produces almost
   nothing on its own... it should be treated as part of §5 rather than
   as its own feature." Treat it as a routing-weight patch inside
   gossip mutation, not a module.

This packet's job is the **foundation two items** — the sentiment/
named-state model and the reaction-context contract — designed as a
serial prologue, plus **scoped (not fully designed) lane proposals**
for the remaining five systems so a follow-up design-prep lane can pick
each one up individually once the foundation is ruled. This sequencing
(2-task serial prologue, then fan out) was checked against an
independent second opinion before this packet was written; do not
re-litigate it without a specific reason — put a specific reason in the
findings list instead.

## Read first (in order)

1. `docs/vision-v3.0.md` (full) — the new headline, the four bets, §5's
   constitution (the loyalty-cascade doctrine, the CK2 opinion-modifier-
   soup guard — this document's cap-and-itemized-cause rule is a hard
   constraint on anything this packet designs), §6's build order.
2. `docs/research/comparative-systems/social-ray-tracing-player-view-2026-09-07.md`
   — full. Systems 4 (Crystallization), 5 (gossip mutation/writeback),
   6 (the production-rule layer), 9 (Leverage), 10 (Dread), 11 (pacing
   director), 13 (the conversation ladder), 14 (kin-priority routing).
3. `docs/research/comparative-systems/worked-design-tour-2026-09-06.md`
   — the same systems' mechanism-first version (companion document,
   sections 4/5/6/9/10/11/13/14) — use both together; the ray-tracing
   doc explicitly replaces this one's *framing*, not its mechanism
   detail.
4. `chronicle/claims.py` (full) — the `Claim`/`Variant`/`Evidence`/
   `BeliefInstance` model; note confidence is a continuous decayed
   float, not a discrete tier, and evidence chains via
   `predecessor_belief_id`.
5. `chronicle/social.py` (full) — the four existing per-pair/per-
   observer record kinds, deliberately never merged (rule 18):
   `Relationship` (directed, `basis` in a closed set, single `strength`
   float, no valence axis, no founding-memory citation — used today as
   "regard" for trust-discounted retelling), `Grudge` (has
   `source_belief_id`, dual emotional/evidentiary decay, a cooled
   floor), `Obligation`, `Reputation` (Beta-distributed, keyed
   `(observer, subject, context)`). **Crystallization's Friend/Rival
   states have no positive-valence analog to `Grudge` today** — this is
   the central open question, below.
6. `chronicle/avoidance.py` (full, 63 lines) — the house precedent for
   a *derived* condition over existing stores (`is_avoiding()` re-
   derives rule 18's condition from `Grudge` state, exposed read-only to
   the adapter layer) rather than new storage. This is the template to
   accept or explicitly reject for Crystallization/Dread.
7. `chronicle/rules.py` (full) — the `Rule` protocol (`name`, `tier`,
   `evaluate(ctx) -> RuleResult`), `RuleContext`/`RuleResult`,
   `RecordedRule`/`StubRule`/computing-rule shapes, and critically: the
   registry is a **fixed tuple in `_default_rules()`**, no dynamic
   registration, and is explicitly at its 20-rule ceiling. A new
   reaction-context/reaction-rule concept must decide whether it reuses
   this exact protocol shape in a **new, separate module and registry**
   (recommended default — do not touch `rules.py`) or needs a different
   shape because reactions render *output* (bark/expression/approach/
   exit tiers) rather than firing derived-state side effects.
8. `chronicle/driver.py` — read in full, but especially: `__init__`
   (the construction-time-mapping extension idiom every subsystem
   uses), `_run_tick`/`_propagate_on_encounter`, `witness()`/`retell()`/
   `corroborate()`/`resolve()` (the **acquisition-time hook** shape —
   fires once when a belief enters a store), `_apply_reputation`
   (driver.py:1628-1669, the existing belief→disposition wire via a
   `reputation_relevance` mapping — read this closely, it is the
   closest existing precedent for "hearing something moves a number"),
   `_grudge_severities`/`_avoidance_thresholds` (the **per-tick sweep**
   hook shape, called once per tick before the encounter roll — this is
   the shape the pacing director should follow, not the acquisition
   shape), `suffer_harm()` (870-932, the self-victim grudge gate).
9. `chronicle/rng.py` (full, ~103 lines) — `roll_key()`'s six-member
   hash and the **closed `PURPOSES` frozenset** that raises `ValueError`
   on an unregistered purpose. Any new roll site in this packet's
   systems (a Dread threshold check, a pacing-director off-screen-event
   roll, a leverage-detonation roll) needs a new purpose constant
   proposed here.
10. `chronicle/events.py` + `chronicle/framelog.py` — read
    `event_payload()`/`event_from_record()`/`serialize_state()`/
    `load_state()` in full. Note `load_state`'s inconsistency: some
    record kinds round-trip through their store's constructor method on
    keyframe load (re-running invariant checks — e.g.
    `social.add_grudge`), others are inserted directly into private
    dicts (bypassing invariants). A new record kind (a "Fondness"/
    named-state row, a Dread value) must pick one deliberately and say
    so.
11. `docs/decisions/0006-data-ownership-layers.md`,
    `0009-keyed-randomness.md`, `0010-tick-quantum.md` — the layering,
    RNG, and tick-unit constraints everything above cites.
12. `docs/design/tier-3-rule-registry-and-tell-decision.md` (the
    structural model for this doc — R1-R12 lettered decisions,
    findings section, rulings appendix) and its overseer review at
    `reviews/2026-08-23-lane-18/`.
13. `docs/design/conversation-tier-design-notes-2026-08-30.md` — read in
    full, not just §1-2. Its header states "design input, not decided,"
    and it proposes narrowing ADR-0011's "3-5 candidate lines" to one
    engine-authored line per tap — a live, **unresolved contradiction**
    with an *accepted* ADR. The STC conversational ladder (system 13)
    cannot be lane-split until this is resolved; flag it as a named
    blocker, not something this packet resolves.
14. `docs/work-packets/reviews/README.md` — governance (frozen-document
    rule, commit discipline, coordinator role). Note for the doc's
    cover note: per the 2026-08-25 ruling the Kimi session lineage is
    the standing planner/coordinator; this packet was commissioned
    directly by the owner outside that loop, so say so plainly in the
    cover note rather than assuming coordinator authority.

## Questions the doc must answer

**A. The sentiment/named-state model (Crystallization, foundation).**
1. Is Friend/Rival/Sworn-Friend/Guilty a **new store** (a `Sentiment` or
   `Fondness` record mirroring `Grudge`'s shape — holder, target,
   source_belief_id, strength, decay half-life, a named-label
   threshold function) or a **derived projection** over
   `Relationship.strength` + `Grudge` (positive region) +
   `Reputation.mean`, à la `avoidance.py`'s pattern? Recommend with a
   named alternative; the deciding factor is whether a positive
   disposition needs its own founding-memory citation independent of
   an existing `Relationship` edge (the ray-tracing doc's worked
   example — Carlotta's Friend state citing "stood up to the bard for
   me" — suggests yes, which argues for a `Grudge`-shaped positive
   counterpart, not a derived label over `Relationship.strength` alone,
   since `Relationship` has no founding-memory field today).
2. Cap and itemization (vision §5's non-negotiable): how many
   simultaneous named states per pair, is switching hysteretic (does
   Rival require crossing back through neutral, or can it flip
   directly to Friend), and what's the itemized-cause list a UI/dialog
   query renders.
3. Proximity-reaction tiers (bark/expression/approach/exit) — what
   triggers each tier, rate limit (ray-tracing doc says "once per pair
   per hour" as a worked example — confirm or revise), and whether this
   belongs in Crystallization's own module or is itself the first
   consumer of question B's reaction-context contract.

**B. The reaction-context contract (foundation).**
1. Define the concrete dataclass: `(event, beliefs, sentiment,
   temperament, mood) -> reaction_class` — exact field types, not
   placeholders. Beliefs: reuse `claims.BeliefInstance`/`Claim`
   directly, or a narrower read-only view? Sentiment: whatever question
   A.1 lands on. Temperament and mood: **neither currently exists
   anywhere in the codebase** (confirmed no per-NPC trait/mood field) —
   propose where they live: static authored per-NPC data (mirroring
   `chronicle/fixtures/whiterun_relationships.py`'s existing authored-
   cast pattern) is the YAGNI-consistent default for v1; a simulated
   mood state machine is out of scope unless the doc argues otherwise.
2. Registry shape: a **separate module and registry** from
   `chronicle/rules.py` (recommended — the ladder's rule budget is
   frozen at 20, and reactions render *output* rather than deriving
   state, a different enough job to warrant its own namespace) — name
   it, and give it the same evaluate-and-trace-every-attempt discipline
   as `Driver._evaluate_rule()` (a reaction that doesn't fire still
   emits a trace row — "a stuck counter is visible, not silent" applies
   here too).
3. External data authoring: the reaction table ships as moddable
   external data (vision §3, Bet 4) — propose a concrete format (JSON?
   a Python-literal table like `_default_rules()`'s fixed tuple, loaded
   from a data file?) and where it lives.
4. Precedent check (already done, cite and move on, don't re-research):
   Comme il Faut / Prom Week's exchange-selection-by-trigger-condition
   model and RimWorld's itemized/capped mood-modifier discipline are
   the two closest priors; note them as design references in the doc,
   this is not a new research task.

**C. Dread (scoped, not fully designed).**
Per-observer fear/respect as a derived label over `Reputation` (context
e.g. `"crime"`/`"violence"`) + relevant `Grudge` state, converted to
a valence (fear vs. respect vs. neutral) by the observer's temperament
(question B.1) — confirm this framing or revise, and propose the file/
lane boundary for a follow-up implementation lane. Do not fully design
the threshold math here; that is the follow-up design-prep lane's job
once the foundation ships.

**D. Secrets/Hooks leverage (scoped, not fully designed).**
Propose the record shape only (a `Secret`/`Hook` held by the player
about an NPC, an expose/hold/release action set) and its dependency on
question A/B's sentiment model (Expose's writeback and Hold's
detonation both need a place to write disposition change). Full rule
design deferred.

**E. World-event pacing director (scoped, not fully designed).**
Confirm this follows the **per-tick sweep hook** shape
(`_grudge_severities`/`_avoidance_thresholds`'s pattern), not the
acquisition-time shape, since it must act every tick regardless of
encounters. Flag explicitly: this module must not import or depend on
the civil-war/dragon-crisis phase enum (vision §6 build-order item 3,
not yet designed) — its internal per-hold clock state (Quiet/budget
accounting) stays self-contained so it isn't blocked on that later
item.

**F. STC conversational ladder (scoped, blocked).**
Name the ADR-0011/conversation-tier-design-notes contradiction (read-
first item 13) as a named blocker the owner must resolve before this
system gets its own design-prep lane. Do not attempt to resolve it
here.

**G. Kin-priority routing.**
Confirm (not redesign) that this is a routing-weight change inside
gossip mutation/`chronicle/propagate.py` + `chronicle/social.py`'s
`Relationship` `basis="kinship"` — a same-day-transit-time,
high-reliability multiplier on an existing kin edge — not a new
module, per the ray-tracing doc's own §14 admission.

**H. New event types and RNG purposes.**
Enumerate, across A-E, every place a new `Event` subclass or a new
`rng.py` `PURPOSES` entry looks necessary (e.g.: a sentiment-formed/
dissolved event, a dread-threshold-crossed event, a leverage-exposed/
held/released event). For each: name it, don't assign it a schema
section number (the coordinator assigns per house convention — see
lane-33's identical deferral) but do specify which of `framelog.py`'s
four required touch points it needs (event class, `event_payload`
branch, `event_from_record` branch, optionally a `serialize_state`/
`load_state` keyframe key) so a future lane's acceptance criteria are
concrete.

**I. Determinism and invariant gates (apply to every question above).**
Every proposal must explicitly state: (i) which existing `PURPOSES`
rolls it must not perturb, (ii) the cap and itemized-cause list for any
new scalar (vision §5's opinion-modifier-soup guard), (iii) the
founding-memory/evidence-chain citation path for any new sentiment
write ("no belief without an evidence chain ever" — vision §6 non-
goals), and (iv) confirmation that `chronicle/tests/` and
`scenarios/test_*.py` need zero edits (this is additive, greenfield
work; if any question's answer would require editing an existing test,
that's a finding, not a design decision to make silently).

**J. Lane breakdown.** A proposed implementation-lane split (numbers
left for the coordinator to assign) covering: (1) the sentiment/
Crystallization store + Dread's derived-label layer, (2) the reaction-
context contract + registry core (mirrors lane-19's role for
`rules.py`), (3) gossip-writeback extension + kin-priority routing
(one lane, per question G), (4) Secrets/Hooks leverage, (5) the pacing
director. STC ladder excluded pending F's blocker. Mind file
contention: anything touching `driver.py` or `social.py` serially, the
same discipline lanes 19→26 already used.

## Acceptance

- One markdown deliverable:
  `docs/design/social-mechanics-v3-foundation.md`.
- file:line citations throughout (this codebase's own convention — no
  claim about existing code without one).
- Every question A-J addressed; recommendations plus named
  alternatives where a real alternative exists; open points collected
  for the owner at the end; a findings list (anything the source docs
  got wrong, contradicted each other, or left ambiguous — vision §1's
  Crystallization overclaim is one confirmed example, look for more).
- Suite stays untouched-green: `uv run pytest` and `uv run ruff check .`
  unchanged from current state (no code in this lane).

## File boundaries

**Create:** `docs/design/social-mechanics-v3-foundation.md`

**Do not touch:** `chronicle/*` (no code), `docs/scenario-ladder.md`,
`docs/ui-spec.md`, `docs/ui-doctrines.md` (frozen — propose schema/event
additions in the new doc, the coordinator amends
`docs/frame-log-schema.md` at ruling time, same as lane-33's precedent),
`chronicle/tests/`, `scenarios/`.

## Conventions

- Match the Tier-3 (`docs/design/tier-3-rule-registry-and-tell-
  decision.md`) and Tier-4a (`docs/design/tier-4a-schedule-write-
  back.md`) design docs' voice and structure: lettered decision points,
  a findings section, an open-questions-for-the-owner appendix.
- **Local commits OK** (path-scoped); never push.
- Report format: the doc + a cover note (decided / needs adjudication /
  surprises), including the coordinator-authority note from read-first
  item 14.
