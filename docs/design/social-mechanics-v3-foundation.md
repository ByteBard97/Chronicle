# Social-mechanics-v3.0 foundation design prep

Status: design proposal for owner review (lane 61 deliverable). No code.
Every code claim below carries a file:line citation, verified against
this session's direct reading of `chronicle/claims.py`, `social.py`,
`rules.py`, `driver.py`, `rng.py`, `events.py`, `framelog.py`,
`avoidance.py`, `roles.py`, `schedule.py` and their tests. Structured so
each **Decision** section lifts into a follow-up implementation-lane
packet; open points for the owner are collected in §12.

**This is new-track work, not a ladder amendment.** `docs/scenario-
ladder.md` is FINAL (Tiers 0–6, rules 1–20, at its own stated rule-
budget ceiling — `chronicle/rules.py:33-34`). Nothing proposed here
edits it, adds to `chronicle/rules.py`'s fixed registry, or touches
`chronicle/tests/`/`scenarios/`.

Sources: `docs/vision-v3.0.md` (full); `docs/research/comparative-
systems/social-ray-tracing-player-view-2026-09-07.md` (full);
`docs/research/comparative-systems/worked-design-tour-2026-09-06.md`
(companion mechanism detail); `chronicle/claims.py`; `chronicle/
social.py`; `chronicle/rules.py`; `chronicle/driver.py`; `chronicle/
rng.py`; `chronicle/events.py`; `chronicle/framelog.py`; `chronicle/
avoidance.py`; `docs/decisions/0006`/`0009`/`0010`; `docs/design/
tier-3-rule-registry-and-tell-decision.md` (structural model); `docs/
design/conversation-tier-design-notes-2026-08-30.md`.

---

## 0. What this packet actually asks for

Vision §6 names seven systems as "pure-Python, zero-engine-risk,
buildable in parallel": gossip mutation + transitive writeback, the
production-rule reaction layer, Secrets/Hooks leverage, the Dread axis,
the world-event pacing director, the STC conversational ladder,
kin-priority belief routing.

Two corrections precede any design work:

1. **Vision §1's claim that Crystallization "is still built the way
   v2.2 specified" is false.** `grep -rn "Friend\|Rival\|Sworn.Friend\|
   crystalliz" chronicle/` returns nothing but incidental English-word
   hits. No named-relationship-state code exists. Four of the seven
   systems (writeback, the reaction layer, Dread, the STC ladder) read
   or write a sentiment/named-state concept that isn't there yet —
   building all seven in parallel means four of them design the same
   missing store four different ways.
2. **Kin-priority routing is not a parallel sibling.** The ray-tracing
   doc's own §14 says it "produces almost nothing on its own... should
   be treated as part of §5." §7 here confirms that reading rather than
   re-arguing it.

This document designs the two blocking foundation pieces in full
(§1 sentiment/Crystallization, §2 the reaction-context contract),
scopes three more at file/lane-boundary depth without finishing their
internal mechanism design (§3 Dread, §4 Leverage, §5 the pacing
director), names one as blocked on an unrelated open contradiction
(§6 the STC ladder), confirms kin-routing folds into gossip (§7), and
proposes the new event/RNG surface (§8) and lane split (§10) the
foundation unlocks.

---

## 1. The sentiment/named-state model (Crystallization)

### What's already there

`chronicle/social.py` has four per-pair/per-observer record kinds,
deliberately kept separate (rule 18's docstring: "never merged"):

- `Relationship` (`social.py:85-109`): directed, `basis` restricted to
  `ALLOWED_RELATIONSHIP_BASES = {"colocation","kinship","faction",
  "shared_employer"}`, single `strength: float [0,1]`. **No valence
  axis** (nothing distinguishes "close because kin" from "close because
  the same feud"), **no founding-memory citation** (no
  `source_belief_id` field). Already consumed as "regard" by
  `Driver._trust_for_retelling` (`driver.py:403+`).
- `Grudge` (`social.py:112-131`): `holder_id`, `target_id`,
  `source_belief_id`, `severity`, dual-decay (`emotional_strength` at
  a 672-tick half-life, `evidentiary_strength` at 336), a
  `forgiveness_threshold` cooled-floor via `grudge_cooled()`.
- `Obligation`, `Reputation` (Beta-distributed, `(observer, subject,
  context)`-keyed, `.mean`/`.uncertainty`).

`chronicle/avoidance.py` (63 lines total) is the house precedent for
**not** adding new storage: `is_avoiding()` re-derives rule 18's
condition purely from existing `Grudge` state, exposed read-only to the
adapter layer.

### Decision S1 — Friend/Rival needs a new record, not a derived label

The ray-tracing doc's own worked example (§4: Carlotta's Friend state
citing "stood up to the bard for me — three separate occasions") makes
a founding-memory citation the whole point of the mechanic: it's what
the "have I done something for you?" dialogue query renders. `Grudge`
already has exactly this shape on the negative side
(`source_belief_id`, decay, a cooled floor). `Relationship` doesn't —
it's basis-typed regard, not a citation of a specific act.

**Proposed:** a new record, `Fondness` (mirrors `Grudge`'s shape
exactly, same module): `holder_id`, `target_id`, `source_belief_id`,
`warmth: float`, `emotional_strength`/`evidentiary_strength` twin decay
(reuse `Grudge`'s half-lives as the default, tunable separately per
vision §5's "every scalar needs a cap and a reason" — do not silently
share `GRUDGE_EMOTIONAL_HALF_LIFE`, declare `FONDNESS_EMOTIONAL_HALF_
LIFE` explicitly even if initially set to the same value). A `form_
fondness()` constructor mirrors `form_grudge()`'s gate shape
(`social.py:203-254`) including its O3 self-subject bypass equivalent
(does a self-directed positive state — e.g. pride — exist? **out of
scope for v1**, `Guilty` from the ray-tracing doc's own vocabulary list
is explicitly self-directed and is deferred to a follow-up lane, not
designed here).

**Rejected alternative:** deriving Friend/Rival purely from
`Relationship.strength` sign or magnitude. Rejected because
`Relationship` is basis-typed (kinship/faction/colocation/shared-
employer) and a Friend state must be able to exist between two NPCs
with *no* qualifying basis edge at all (a market vendor and a passing
adventurer) — exactly the ray-tracing doc's Grelka example. Forcing
Crystallization through `Relationship` would require loosening its
`ALLOWED_RELATIONSHIP_BASES` gate, a change to already-shipped, tested
code (rejected on the same grounds R2 rejected refactoring `claims.py`/
`social.py` internals).

### Decision S2 — named-state labels are a derived projection over `{Grudge, Fondness}`, not a third store

The state itself (Friend/Rival/Sworn Friend/Grateful/Beholden) is a
**pure function** of a pair's live `Grudge`/`Fondness` rows at a given
`gamets` — `crystallize(holder_id, target_id, at_gamets) -> str | None`
— following `avoidance.is_avoiding()`'s exact template: no new
persisted "current state" field, because a persisted label would be a
second source of truth that can desync from the decaying rows it's
supposed to summarize (the same reasoning `avoidance.py`'s docstring
gives for re-deriving rather than caching).

Threshold table (cap-and-itemized, vision §5): a small ordered list of
`(predicate_on_decayed_grudge_and_fondness, label)` pairs, most-severe-
wins, e.g. `severity_at(...) > SWORN_RIVAL_THRESHOLD -> "Sworn Rival"`,
else `> RIVAL_THRESHOLD -> "Rival"`, mirrored on the positive side. At
most one label per pair at a time (no simultaneous Friend+Rival) —
**hysteresis question left open for the owner** (O1, §12): does a pair
have to decay through neutral before flipping sign, or can a single
severe enough event flip Friend directly to Rival? Doctrine 3 (no
threshold without hysteresis and a reason) applies; propose hysteresis
via requiring the *opposing* row's decayed value to fall below its own
threshold before the new label can apply, but this needs an owner
ruling before implementation, not a lane-level judgment call.

### Decision S3 — proximity reactions consume the reaction-context contract (§2), Crystallization does not render bark/expression/approach/exit itself

`crystallize()` produces a label + its founding `source_belief_id`.
Rendering that as a bark/expression/approach/exit tier, rate-limited
per pair per hour, is the reaction layer's job (§2) — Crystallization
is one *input* to it (the `sentiment` slot in `(event, beliefs,
sentiment, temperament, mood) -> reaction_class`), not a parallel
rendering path. This avoids two independent reaction-selection
mechanisms existing side by side.

---

## 2. The reaction-context contract (production-rule reaction layer)

The ray-tracing doc (§6) names this "the shading model — not a light
source, everything visible passes through it." It is the fan-in point
for Crystallization (§1), Dread (§3), gossip writeback, and later the
LLM conversation tier. Getting its input contract wrong forces rework
in every producer built against it — this is the single highest-risk
item in the whole packet (independently confirmed by two reviewers
before this doc was written).

### Decision X1 — a new module and registry, not an extension of `chronicle/rules.py`

`chronicle/rules.py`'s registry is a **fixed tuple** returned by
`_default_rules()` (`rules.py:454-477`), stated to be at its 20-rule
ceiling (`rules.py:33-34`, `docs/scenario-ladder.md` §8). Its rules
derive/mutate simulation state (grudges, reputations, obligations).
Reactions do a categorically different job: given already-settled
state, select a *rendering* — a reaction class consumed downstream by
barks/expressions/dialogue, never fed back into `claims.py`/
`social.py` as a new fact. Reusing `rules.py`'s registry would either
blow its frozen budget or blur "derives state" with "renders output."

**Proposed:** `chronicle/reactions.py`, same `Protocol` shape as
`Rule` for consistency (`name: str`, `evaluate(ctx) -> ReactionResult`)
but its own class names (`Reaction`, `ReactionContext`,
`ReactionResult`, `ReactionRegistry`) and its own numbering namespace,
starting at 1, independent of rules 1–20. Never imports from
`chronicle/rules.py`; may import read-only from `social.py`/
`claims.py` the same way rules do.

### Decision X2 — the context dataclass, concretely

```python
@dataclass(frozen=True)
class ReactionContext:
    event: Event                        # chronicle.events.Event subclass, the triggering occurrence
    observer_id: str                    # the NPC reacting
    subject_id: str | None              # who/what the reaction is about, if any
    beliefs: tuple[BeliefInstance, ...]  # caller-assembled, already-looked-up (never queried by the reaction)
    sentiment_label: str | None         # from crystallize() (§1), e.g. "Friend", "Rival", or None
    sentiment_source_belief_id: str | None  # the founding-memory citation, carried through so a reaction can render "why"
    temperament: Mapping[str, float]    # static per-NPC traits (see X3), e.g. {"boldness": 0.8}
    mood: Mapping[str, float]           # itemized, capped modifiers (see X3) — never a bare scalar
    tick: int
    gamets: float

@dataclass(frozen=True)
class ReactionResult:
    fired: bool
    reaction_class: str | None          # e.g. "bark", "expression", "approach", "exit" — the ray-tracing doc's own tier vocabulary
    result: Mapping[str, object] | None  # itemized cause list for the UI/dialogue query, mirroring RuleResult.result
```

Caller-assembled inputs (the `RuleContext` discipline, `rules.py:95-
105`, restated at `rules.py:19,59`): a `Reaction.evaluate()` never
queries `ClaimStore`/`social.py` stores itself, it only reads
`ctx`. This is what kept T2.3's social→claims leak out of the rule
registry and must hold here too.

Every evaluated reaction — fired or not — emits a `reaction_evaluated`
trace record (mirrors `rule_evaluated`, `Driver._evaluate_rule()`,
`driver.py:366-401`): "a stuck counter is visible, not silent" applies
to reactions exactly as it does to rules. A pair that *should* have
reacted but didn't (rate-limited, or no rule matched) is a visible,
inspectable non-event, not a silent absence — this is also what makes
the ray-tracing doc's "under-sampling reads as noise" warning
checkable in the test suite (a scenario can assert "reaction evaluated,
did not fire, because rate-limit" rather than just "nothing happened").

### Decision X3 — temperament and mood are static authored data for v1, not a simulated state machine

Neither field exists anywhere in the codebase today (confirmed: no
`temperament`, `boldness`, or `mood` hits in `chronicle/`). Per YAGNI
and the project's existing authored-cast pattern (`chronicle/fixtures/
whiterun_relationships.py` already hand-authors per-NPC relationship
seed data), **temperament is a small, static, per-NPC dict authored
alongside the existing cast fixtures** — e.g. `{"boldness": 0.8,
"volatility": 0.3}` — not derived or simulated. **Mood is out of scope
for this lane entirely**; the `ReactionContext.mood` field is reserved
in the contract (so later work doesn't have to change every reaction's
signature) but ships as an always-empty mapping until a future lane
designs it, itemized and capped, exactly the way `Grudge`/`Fondness`
are. Building a mood state machine now would be exactly the kind of
speculative generality the project's own conventions reject.

### Decision X4 — the reaction table ships as external, moddable data

Vision §3 (Bet 4) requires this. `rules.py`'s `_default_rules()` is a
fixed Python tuple, which is *not* externally moddable — appropriate
for a frozen, budget-capped, 20-item registry, wrong for a table meant
to grow and be authored by modders. **Proposed:** a data file (JSON,
consistent with the dashboard/frame-log ecosystem's existing JSON
usage — e.g. `docs/frame-log-schema.md`'s own envelope is JSON records)
under a new `chronicle/data/reactions/` directory, loaded at `Driver`
construction into `ReactionRegistry` instances. Each entry: a name, a
tier, a match predicate expressed as simple field comparisons (not
arbitrary code, to stay moddable and safe), a `reaction_class` output,
most-specific-match-wins ordering. Exact predicate-language grammar is
a follow-up lane's design question, not resolved here — flagged as O2
in §12.

**Precedent, cited not re-researched:** Comme il Faut / Prom Week
(McCoy/Treanor/Mateas) — social exchanges selected by rule-trigger
conditions over social state + character traits, most-salient-wins,
is the closest published analogue to this exact contract. RimWorld's
itemized/capped mood-modifier discipline is the model for X3's "mood
must be itemized" constraint whenever mood is actually designed. Both
are design references; no further research is needed before
implementation.

---

## 3. Dread (scoped)

**Framing (confirmed, not fully designed):** per-observer fear/respect
is a derived label, same shape as §1's Crystallization, over
`Reputation` (keyed `(observer_id, subject_id, context)`, likely
`context="violence"` or `context="crime"` — an existing, already-wired
mechanism via `Driver._apply_reputation`, `driver.py:1628-1669`) plus
relevant `Grudge` rows, converted to a valence (Terrified vs. Bold-
respect vs. neutral) by the observer's `temperament.boldness` (§2 X3).
This directly matches the ray-tracing doc's Belethor-vs-Uthgerd worked
example: same belief, same reputation evidence, opposite output because
of a per-NPC trait — which is exactly what `ReactionContext.temperament`
exists to carry.

**Not designed here:** the exact threshold table, the "terrified NPCs
comply and then report" downstream behavior (ray-tracing §10's named
built-in price — this likely needs its own new event type, see §8),
and whether Dread needs its own decay half-lives distinct from
`Reputation`'s existing evidence-accumulation decay. **Proposed lane
boundary:** one implementation lane, `chronicle/dread.py` (or folded
into a `crystallization.py` module alongside §1's `Fondness`/
`crystallize()` if the owner prefers fewer new files — a genuine
open point, O3 in §12), consuming `Reputation` and `Grudge` read-only,
producing a `dread_label()` derived function with the same shape as
`is_avoiding()`.

## 4. Secrets/Hooks leverage (scoped)

**Framing (confirmed, not fully designed):** a `Secret` the player
holds about an NPC (source: some existing belief the player themself
holds — reuse `claims.py`'s existing belief model rather than invent a
parallel "known fact" type), with three player actions: Expose (writes
the belief into the rumor graph at the player's own reliability tier —
this is an ordinary `witness()`/`retell()` call from the player's
`holder_id`, not new mechanism), Hold (creates a spendable hook —
genuinely new state, needs a `Hook` record: `holder_id` (player),
`subject_id`, `source_belief_id`, `spent: bool`), Release (converts a
held hook into an `Obligation` — reuses the existing `Obligation`
record verbatim, no new type needed).

**Not designed here:** the exact detonation mechanics of Expose on a
third party's disposition (this is a consumer of §1/§2's Crystallization
and reaction contract, not a new disposition-writing path), and whether
`Hook` needs its own event type or can piggyback on existing
`Obligation`-issuance events. **Proposed lane boundary:** one
implementation lane, `chronicle/leverage.py`, new `Hook` record only
(smallest possible addition — Expose and Release both reuse existing
mechanism).

## 5. World-event pacing director (scoped)

**Framing (confirmed, not fully designed):** this must follow the
**per-tick sweep hook** shape (`Driver._grudge_severities`/
`_avoidance_thresholds`, `driver.py:1753-1775`, called once per tick
before the encounter roll), not the acquisition-time hook shape
(`witness`/`retell`/etc.) — it has to act every tick regardless of
whether an encounter happens, to decide whether *this* tick is the one
where a queued off-screen event fires, gets suppressed, or gets
telegraphed.

**Explicit constraint carried over from the packet:** this module's
internal per-hold clock state (Quiet/Agitation-style budget accounting)
must not import or depend on the civil-war/dragon-crisis phase enum —
that system is vision §6 build-order item 3, unstarted, and this
module must not block on it or be blocked by it. The pacing director
is generic scheduling infrastructure; the civil-war phase system is one
future *consumer* of it, not a dependency.

**Not designed here:** the belief-citation-required-or-rejected rule
the ray-tracing doc names (§11: "every off-screen event must cite a
motivating belief or it's rejected") in full, or the exact suppression
logic for Aftermath-style states. **Proposed lane boundary:** one
implementation lane, `chronicle/pacing.py`, likely needs a new roll
purpose in `rng.py` (§8) for "does this tick's budget get spent."

## 6. STC conversational ladder (blocked, not scoped)

`docs/design/conversation-tier-design-notes-2026-08-30.md` (read in
full per this packet's instructions) states its own status as "design
input, not decided," and its §2 proposes narrowing ADR-0011's accepted
"3-5 candidate lines" surface down to one engine-authored line per
conversational tap. That is a live, unresolved contradiction with an
*already-accepted* ADR — not something this design-prep lane can or
should resolve. **This system gets no lane-boundary proposal in §10
until the owner rules on that contradiction directly.** Flagged as O4
in §12.

## 7. Kin-priority routing (confirmed, not redesigned)

Confirmed reading, not redesigned: this is a routing-weight change
inside gossip mutation, using the existing `Relationship` record's
`basis="kinship"` edges (`social.py:85-109`, already in
`ALLOWED_RELATIONSHIP_BASES`) — a same-tick-or-near-same-tick transit
time and a high-reliability multiplier applied wherever
`chronicle/propagate.py`'s `teller_and_hearer()`/`conflicting_pair()`
or `Driver.retell()`'s trust-discount math (`driver.py:403+`,
`TRUST_RELATIONSHIP_BASES` already includes `"kinship"`) currently
treats all relationship bases uniformly. **No new module.** Folds into
whichever lane extends gossip mutation/writeback generally — do not
give this its own lane row in §10.

---

## 8. New event types and RNG purposes

Per-system enumeration, `framelog.py`'s four-touch-point convention
(`event_payload` branch, `event_from_record` branch, optionally a
`serialize_state`/`load_state` keyframe key, a schema §3 doc entry —
section numbers assigned by the coordinator at ruling time, same
deferral as lane-33's precedent):

| System | New `Event` subclass? | New `rng.py` `PURPOSES` entry? |
|---|---|---|
| §1 Crystallization | `FondnessFormed` (mirrors an eventual `GrudgeFormed`-equivalent if one exists — verify against `events.py` before naming; if grudges don't currently emit their own event type, `Fondness` shouldn't invent an asymmetry, flag as a finding) | None — formation is deterministic from existing belief acquisition, no new dice roll |
| §2 reaction layer | `ReactionFired` (or reuse the trace-only `reaction_evaluated` record and skip a dedicated Event subclass entirely, if reactions are pure rendering with no derived-state consequence — **recommended**, avoids event-stream bloat for something that doesn't change simulation state) | None expected |
| §3 Dread | `DreadThresholdCrossed`, if downstream systems (e.g. §11's "terrified NPCs comply and report") need to key off a discrete crossing rather than re-deriving continuously | Possibly — if "does a terrified NPC report" is itself a roll, needs a new purpose, e.g. `DREAD_REPORT_DECISION` |
| §4 Leverage | `HookCreated`, `HookSpent` | Possibly — if Expose's detonation has a probabilistic element |
| §5 Pacing director | `OffScreenEventFired`, `OffScreenEventSuppressed` (both — the ray-tracing doc's suppression case is explicitly as important as the firing case) | Yes — a per-tick "does this tick's budget get spent" roll, new purpose e.g. `PACING_BUDGET_SPEND` |

All proposed, none assigned a schema section number — the coordinator
amends `docs/frame-log-schema.md` §3 at ruling time, per house
convention.

## 9. Determinism and invariant gates (cross-cutting — apply to every decision above)

- **No existing `PURPOSES` roll is perturbed.** Every new roll site
  above gets its own new `rng.py` purpose constant; none reuse or
  reinterpret `ENCOUNTER_CO_PRESENCE`, `MUTATION_SLOT`, `MUTATION_
  VALUE`, or `TELL_DECISION`.
- **Every new scalar (`Fondness.warmth`, Dread's valence, mood
  modifiers whenever designed) ships capped and itemized from its
  first implementation lane**, per vision §5's CK2 opinion-modifier-
  soup guard — not precision-tuned later.
- **Every sentiment write cites a founding belief.** `Fondness.
  source_belief_id`, `Hook.source_belief_id`, Dread's underlying
  `Reputation`/`Grudge` evidence — nothing in this packet introduces a
  disposition number with no evidence chain behind it.
- **Zero edits to `chronicle/tests/` or `scenarios/test_*.py`.** Every
  decision above is additive: new modules, new optional constructor-
  time mappings on `Driver.__init__` (the existing extension idiom —
  `driver.py:209-362`), never a change to an existing test's
  assertions. If a follow-up lane finds this isn't true for some
  reason, that's a finding to report, not a silent scope change.

---

## 10. Proposed implementation-lane split

Lane numbers left for the coordinator to assign; dependencies are on
this design doc's ruling, not on each other except where noted.

1. **Sentiment/Crystallization core** — `chronicle/crystallization.py`:
   `Fondness` record + constructor (§1 S1), `crystallize()` derived
   labeling (§1 S2). No reaction rendering yet.
2. **Reaction-context contract + registry core** — `chronicle/
   reactions.py`: `ReactionContext`/`ReactionResult`/`Reaction`
   protocol/`ReactionRegistry` (§2 X1-X2), temperament as static
   fixture data (§2 X3), external data-file loading (§2 X4). Depends on
   lane 1 for the `sentiment_label`/`sentiment_source_belief_id` input
   shape.
3. **Gossip-writeback extension + kin-priority routing** — one lane,
   `chronicle/propagate.py` + `driver.py`'s trust-discount path (§7).
   Independent of lanes 1-2.
4. **Dread** — `chronicle/dread.py` (or folded into lane 1's module,
   owner's call per O3) (§3). Depends on lane 2 for temperament input.
5. **Secrets/Hooks leverage** — `chronicle/leverage.py`, `Hook` record
   only (§4). Depends on lanes 1-2 for detonation effects, but the
   record itself can start independently.
6. **World-event pacing director** — `chronicle/pacing.py` (§5).
   Independent of lanes 1-4; needs its own `rng.py` purpose (§8) and a
   new per-tick sweep hook wired into `Driver.__init__`/`_run_tick`
   (mind `driver.py` contention with lane 3 if both land in the same
   window — serialize them the way lanes 19→26 did on `driver.py`).

STC conversational ladder excluded pending §6's blocker.

---

## 11. What surprised me

- Vision-v3.0 §1's flat claim that Crystallization is already built is
  the single highest-value correction in this packet — it would have
  cost real rework if four parallel lanes had each assumed a different
  sentiment store existed.
- `Relationship` (the record that most looks like "disposition" at a
  glance) turns out to be the wrong home for Crystallization precisely
  *because* it's basis-typed — a structural constraint from Tier 2/3
  work that predates vision-v3.0 by weeks and wasn't designed with
  Crystallization in mind at all, but happens to rule it out cleanly.
- `chronicle/rules.py`'s stated 20-rule ceiling is a stronger
  constraint than the vision doc seems to assume — it isn't just a
  progress marker, it's a closed, owner-ruled budget (`docs/scenario-
  ladder.md` §8), which is the real reason the reaction layer needs its
  own module rather than "rule 21."
- Neither temperament nor mood exists anywhere yet, despite being
  load-bearing inputs in nearly every ray-tracing-doc worked example
  (Belethor/Uthgerd, the four-reaction Bannered Mare scene). This
  packet resolves temperament (static authored data) but deliberately
  punts mood — that's a real, not cosmetic, scope cut and the owner
  should know it's been made.

## 12. Open points for the owner

- **O1.** Crystallization hysteresis rule (§1 S2): must a pair decay
  through neutral before flipping Friend↔Rival, or can one severe event
  flip it directly? Doctrine 3 requires *a* hysteresis rule; it doesn't
  pick which.
- **O2.** The reaction table's predicate grammar (§2 X4) — how
  expressive should modder-authored match conditions be, and in what
  file format. Not resolved here.
- **O3.** Should Dread live in its own module or fold into
  `crystallization.py` (§3)? Both are derived-label modules over the
  same two underlying stores; a combined module might be the more
  honest boundary, but §1/§3 are conceptually distinct enough that
  separate modules also has a case.
- **O4.** The STC conversational ladder is blocked on an unresolved
  contradiction between `docs/design/conversation-tier-design-notes-
  2026-08-30.md` and the accepted ADR-0011. This needs a direct owner
  ruling before any lane touches it; it is out of scope for this
  packet to adjudicate.
- **O5.** Whether `Fondness` needs a self-directed variant (a `Guilty`
  state per the ray-tracing doc's own named vocabulary) is deferred
  entirely (§1 S1) — confirm this deferral is acceptable for v1, or
  pull it back in scope now while `Fondness`'s shape is still being
  decided (cheaper to add the self-case now than retrofit later).

## 13. Findings

- Vision-v3.0 §1's "Crystallization... still built the way v2.2
  specified" does not match the repository state — corrected throughout
  this doc, most explicitly in §0 and §11.
- Vision §6's build-order item 1 lists kin-priority routing as a
  parallel-buildable sibling system; the project's own newer research
  document (the ray-tracing reframe, written one day later) already
  contradicts this in its own §14 text. §7 here resolves the
  contradiction in the newer document's favor and recommends vision-
  v3.0 be corrected to match on its next revision (not done in this
  packet — vision-v3.0.md is out of this lane's file boundary).
