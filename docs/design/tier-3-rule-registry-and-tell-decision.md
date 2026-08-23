# Tier 3 design prep — rule registry + tell-decision

Status: design proposal for owner review (lane 18 deliverable). No code.
Every code/schema claim carries a file:line citation verified against
`e558dfc`. Structured so each **Decision** section lifts into an ADR; open
points for the owner are collected in §10.

Sources: `docs/scenario-ladder.md` Tier 3 intro + T3.1–T3.5 (lines 69–76)
and §8 rule table (lines 129–155); `docs/frame-log-schema.md` §4 (lines
104–133); `chronicle/social.py`; `chronicle/claims.py`; `chronicle/rng.py`;
`chronicle/driver.py`; `chronicle/propagate.py`; `chronicle/framelog.py`;
`docs/decisions/0009`/`0010`; `docs/vision-v2.2.md` §6.

---

## 0. What Tier 3 actually asks for

The tier intro (`docs/scenario-ladder.md:69-70`) names five mechanisms:
threshold/accumulation rules, grudge decay, the tell-decision gate,
violation→grudge+reputation wiring, and the **rule registry** — the last
"forced by this tier's tooling," with tiers 0–2 migrating onto it as
regression cases. §8 (`docs/scenario-ladder.md:133-155`) counts **19 named
rules against a ~20 ceiling** and states as consequence (b): *every* rule —
including the ten already implemented — must exist in the registry as a
named, toggleable, trace-instrumented object.

Two external consumers shape the design:

- The tier's own tooling (`docs/scenario-ladder.md:78`): a rule-firing
  log over the registry including **evaluated-but-not-fired rows with
  current accumulator values** — "a counter stuck at 3-of-4 must be
  visible, not silent."
- The GM/director layer (`docs/vision-v2.2.md:59`, §6): sifts exactly this
  surface — provenance-anchored intervention reads named, instrumented
  rules. Cheap to design for now, expensive to retrofit.

Doctrine 3 — "No behavior threshold without hysteresis and an attached
reason, ever" (`docs/vision-v2.2.md:67`) — constrains every threshold rule
below.

---

## 1. Rule registry shape (question 1)

### Decision R1 — a rule is a small object; the registry is per-run, Driver-owned

Proposed shape (new module `chronicle/rules.py`):

```
class Rule(Protocol):
    name: str          # the §8 table string, e.g. "tell-decision"
    tier: int          # introducing tier, per §8
    def evaluate(self, ctx: RuleContext) -> RuleResult | None: ...
```

- **Instances live on the Driver**, constructed in `Driver.__init__`
  alongside the stores. Rationale: a rule evaluation *emits to the run's
  writer* and *reads the run's stores* — both are per-run objects
  (`driver.py:120-172`). A module-level singleton registry would either
  hold run state (leak across runs — the determinism harness runs two
  drivers per test, `chronicle/tests/test_determinism.py:68-74`) or be
  re-bound per run anyway. Per-run is the only honest scope.
- **"Toggleable" = construction-time config.** `Driver.__init__` takes an
  optional `disabled_rules: Collection[str] = ()` (or the positive form,
  `enabled_rules=None` meaning all). No mid-run toggling: mid-run state
  would have to be event-sourced to survive arbitrary-T reconstruction
  (`framelog.py:223` `serialize_state`), and no rung asks for it.
  **Rejected alternative:** mid-run toggle records in the trace — pure
  scope creep against the ladder text, and a reconstruction hazard.
- **Default is all-enabled.** The 186-test battery defines current
  behavior; any registry default that isn't "everything on" breaks tiers
  0–2. Toggleability exists for scenario authors and the GM layer's
  what-if probes, not to change shipped defaults.

### Decision R2 — retro-registration is by wrapper, not refactor

The ten implemented rules (§8 #1–10) keep their current internals. Each
gets a thin `Rule` object whose `evaluate()` is invoked **at the existing
call site** — which for rules 1–5, 7, 8 is already a Driver wrapper
(`driver.py:197` `witness`, `:232` `retell`, `:295` `corroborate`, `:314`
`resolve`; mutation at `:563` `_decide_mutation`), for rule 6 the
encounter sampler (`driver.py:486-511`), and for rules 9–10 the stage
machine (`claims.py` `stage_at`, thresholds at `claims.py:73-74`).

**Rejected alternative:** refactoring `claims.py`/`social.py` internals
into rule objects. It buys aesthetic purity at the price of rewriting
green, frozen-test-covered code — exactly the intrusion the lane
boundaries on every prior tier have been shaped to avoid. The registry
needs rules to be *named, toggleable, instrumented* — none of those words
says "rewritten."

### Decision R3 — the `rule_evaluated` emission contract

Every rule evaluation emits a `rule_evaluated` record — fired or not —
with the schema's existing fields (`docs/frame-log-schema.md:122`):
`rule`, `inputs` (accumulator values + entity refs), `fired` (bool),
`result` (object | null). No schema change needed.

Three contract pins:

1. **Emission happens even when `fired: false`**, with current accumulator
   values in `inputs` — the ladder's "3-of-4 visible, not silent"
   requirement, symmetric with Tier 1's negative records (ui-doctrines D7,
   cited at `driver.py:516`).
2. **A disabled rule emits nothing.** It is absent, not silent-negative:
   D7 covers evaluations that *happen*; a disabled rule isn't evaluated.
   Which rules were enabled is run configuration (see open point O1).
3. **`inputs` is caller-assembled context** — the rule receives
   already-looked-up data (the caller-supplies-context discipline of
   `social.py:203-254` `form_grudge` and `propagate.py`), it never queries
   stores itself. This is what keeps rules unit-testable and keeps the
   social→claims leak T2.3 rejected from re-entering through the registry
   (`docs/scenario-ladder.md:60`).

---

## 2. Accumulation-threshold with hysteresis — rule 11 (question 2)

T3.1 (`docs/scenario-ladder.md:72`): four thefts, same merchant; below
threshold annoyance only; at threshold **exactly one** escalation,
materialized **as an event in the log first**; the warning claim hangs off
that event's canonical key; propagation is encounters-only; no double-fire
on theft five.

### Decision R4 — the accumulator is derived, not stored

Accumulator key: `(holder_id, grievance_kind)` where `grievance_kind` is a
claim kind naming the holder as victim (T3.1: kind `"theft"`, slot
`victim = merchant`). The accumulator **value** is derived on evaluation:
count the holder's beliefs whose claim kind matches and whose slots name
the holder as victim — a pure `ClaimStore` read.

Rationale: event-sourcing discipline. A stored counter would need keyframe
serialization and replay handling (`framelog.py:223-268`) to survive
arbitrary-T reconstruction; a derived count is reconstruction-safe for
free, because beliefs already reconstruct exactly. **Rejected
alternative:** a stored per-key counter with `threshold_crossed` as its
persistence — that makes the record both evidence *and* state, the
dual-role the schema avoids elsewhere (supersession is a link, not a
write, `docs/frame-log-schema.md:120`).

### Decision R5 — hysteresis = fire threshold + latched fired-flag, both log-derived

Doctrine 3 wants no oscillation and an attached reason. For a monotonic
accumulator (beliefs are never un-learned — records are never destroyed,
`claims.py:66-68`), oscillation is impossible by construction, so
hysteresis reduces to the **latch**: fire once at count ≥
`ACCUMULATION_THRESHOLD` (T3.1: 4), never again. The latch is the
existence of a `threshold_crossed` record
(`docs/frame-log-schema.md:123`) for the key — again log-derived, so
reconstruction can't double-fire. The "attached reason" is the
`rule_evaluated`/`threshold_crossed` `inputs`/`accumulator` payload:
rule name, count, threshold, the contributing belief ids.

Evaluation site: the driver's scripted and encounter witness/retell paths,
after a belief forms for a claim whose kind is registered as accumulating
(caller-supplied, like `mutation_candidates`, `driver.py:130`). **Not** a
per-tick sweep — evaluation happens exactly when the accumulator can
change, which also bounds `rule_evaluated` volume (one row per
belief-forming event, not one per tick per NPC).

**Implementation amendment (2026-08-23, lane 24, coordinator-confirmed):**
the latch as implemented is **store-derived** — the escalation belief's
existence — not trace-record-derived. Two practical failures of the
letter of this pin surfaced in delivery: writer buffering misses
unflushed same-phase records (theft 5 scripted immediately after theft 4
would double-fire), and a start-from-keyframe driver's *new* run dir has
no old trace to scan, while the store (which `state_at` reconstructs
exactly) carries over. The escalation belief is itself log-derived state
(rebuilt from `belief_formed` at replay), so it serves the pin's stated
purpose — "reconstruction can't double-fire" — strictly better. Replay
parity proven in the rung test.

### Decision R6 — escalation is a real event; the claim is witnessed off it

On firing, the driver (1) injects an `escalation_warning` event into the
**events stream** (layer 1) with the accumulator key in its payload —
this is the "materialized as an event in the log first" requirement; (2)
calls the existing `witness()` path with
`canonical_event_key = that event's key`, the merchant as witness of their
own escalation; (3) the claim then propagates encounters-only for free,
because `_propagating_claims` is exactly the witness-path registry
(`driver.py:208-209`).

`escalation_warning` is a **new event type → schema/ADR decision for the
owner** (frame-log-schema §3's reserved-type rule; see finding F2).

---

## 3. Grudge machinery — rules 12–13 (question 3)

Substrate: `Grudge` (`social.py:100-118`) already carries
`emotional_strength`/`evidentiary_strength`/`last_rehearsed`/
`forgiveness_threshold`; `form_grudge` (`social.py:203-254`) enforces
rule 8's relationship-edge gate via caller-looked-up `Relationship`;
`grudge_formed` (`docs/frame-log-schema.md:125`) carries the full fields.

### Decision R7 — grudge decay is decay-at-read, mirroring belief decay

No new records, no mutation: a pure `grudge_at(grudge, gamets)` sibling to
`stage_at()`, applying `claims._decay` (`claims.py:94-95`) from
`last_rehearsed`. Event-sourcing discipline: state is derived, not
destroyed (`claims.py:66-68`).

Proposed constants (new tunables block in `social.py`, same
placeholder-status comment discipline as `claims.py:43-58`):

| Constant | Proposed | Rationale |
|---|---|---|
| `GRUDGE_EMOTIONAL_HALF_LIFE` | 672.0 ticks (~28 game-days) | Slower than belief confidence (168) by a wide margin — T3.2's assertable "grudge decays slower than the rumor"; anger outlives the story. |
| `GRUDGE_EVIDENTIARY_HALF_LIFE` | 336.0 ticks (~14 game-days) | Between confidence (168) and gist (1440): the *facts* of the grievance fade faster than the *feeling* — the emotional/evidentiary split the schema already models. |

Both are placeholder magnitudes, tunable-not-derived, owner-adjudicated
(open point O2). T3.2's assertion becomes mechanical: at equal elapsed
time and comparable starting strengths, `grudge_at(...).emotional_strength
> decay(belief, ...).confidence` — a constants-ordering assert plus one
scenario assert, exactly how ADR-0010's sanity checks argued
(`docs/decisions/0010:105-126`).

`forgiveness_threshold` becomes the "cooled" floor: a grudge decayed below
it no longer gates behavior rules (T4b avoidance) but is never deleted.

---

## 4. Obligation violation wiring — rule 14 (question 4)

Substrate: `issue/fulfill/violate_obligation` wrappers
(`driver.py:381-434`) already emit `obligation_issued`/
`obligation_resolved` (`docs/frame-log-schema.md:126-127`).

### Decision R8 — violation cascades inside the existing `violate_obligation` wrapper

T3.3 (`docs/scenario-ladder.md:74`): refusal fires grudge + reputation
evidence for present observers. Proposed cascade, after the
`obligation_resolved` write:

1. **Grudge:** issuer against debtor, `grievance_type =
   "obligation_violated"`, evidentiary strength from the obligation's
   sanctions/severity (caller-supplied). **Wrinkle:** `form_grudge`'s
   rule-8 gate requires a holder→*victim* relationship edge
   (`social.py:225-235`), but here the victim *is* the holder (the issuer
   is the wronged party). Rule 8's text gates grudges about harm to
   someone the holder *cares about* — harm-to-self is the base case, not
   an exception. Recommendation: the violation path passes an explicit
   self-edge convention (or a documented `victim_id == holder_id` bypass
   in `form_grudge`), stated as open point O3 — it touches a
   validation-enforced rule, so the owner should see it.
2. **Reputation evidence:** one `update_reputation` per **present
   observer** — `obligation.witnesses` ∩ co-located NPCs at the refusal
   tick (caller-supplied presence from `npcs_present_at`) — `subject_id =
   debtor`, `kind = "witnessed"`, `positive = False`, context from the
   obligation's action. Observers who merely *hear about* the refusal
   later get `kind = "reported"` rows driven by belief propagation — the
   same evidence-tiering as `REPUTATION_WEIGHT_BY_KIND`
   (`social.py:64-68`).

The whole cascade is one rule-14 evaluation: one `rule_evaluated` row
naming the obligation, listing the grudge id and reputation rows in
`result`.

---

## 5. Tell-decision policy — rule 15 (question 5)

T3.4 (`docs/scenario-ladder.md:75`): motivated holder **never**
transmits, and the trace shows the rule declining **by name** each
opportunity; unmotivated holder transmits on normal keyed rolls. The
schema row is already reserved (`docs/frame-log-schema.md:121`):
`transmission_declined` with `rule` (string) and `roll_key | null`. The
RNG purpose is already registered (`rng.py:44` `TELL_DECISION =
"tell.decision"`); **no new purpose may be added without an ADR-0009
change** — and none is needed.

### Decision R9 — the gate sits after `teller_and_hearer`, before mutation

In `_propagate_on_encounter` (`driver.py:513-552`), today the flow is:
resolve (teller, hearer) → mutation decision → retell. The gate inserts
between the first and second steps: only when an actual transmission is
otherwise about to happen does the tell-decision rule evaluate. Every
other encounter outcome (neither/both-informed, conflict) is untouched —
including T2.3's resolution path, which must not be gated (a contested
hearing is not a telling).

Placement rejected alternative: *before* `teller_and_hearer` — would emit
decline rows for pairs with nothing to tell, multiplying noise without
information.

### Decision R10 — two-stage gate: deterministic motive check, then keyed roll

- **Stage 1 — motive/privacy (deterministic).** Inputs are
  caller-supplied context assembled by the driver: the claim's
  privacy classification (fixture-supplied, like `mutation_candidates`),
  and the teller's already-looked-up social state relevant to motive
  (kinship edges to the subject, grudges). Motive met → decline,
  **always**, no roll: `transmission_declined` with `rule =
  "tell-decision"` (or a sub-reason string — the rung asserts declining
  *by name*; the `rule` field is that name) and `roll_key = null` — the
  schema's `roll_key | null` (`docs/frame-log-schema.md:121`) exists for
  exactly this deterministic-decline case. The T2.3 lesson holds: the
  *rule* reads context the *driver* assembled; no social-state lookup
  leaks into `claims.py` operations.
- **Stage 2 — unmotivated (keyed roll).** Roll purpose `tell.decision`;
  roll_key members per ADR-0009: `site = location_id`, `participants =
  [teller_id, hearer_id]`, `draw =` the claim's ordinal in the
  `_propagating_claims` loop (`driver.py:519`) — that ordinal is the
  discriminator that keeps two claims told in the same
  tick/site/pair distinct. Threshold `TELL_PROBABILITY = 1.0` as the
  migration default (today every resolved transmission happens; anything
  below 1.0 changes tiers 0–2 behavior). Scenario fixtures that want
  refusals-by-roll lower it per-run, construction-time.

Both outcomes emit `rule_evaluated` (rule 15) in addition to any
`transmission_declined`: opportunities are visible even when the tell
proceeds — T3.4's "each opportunity" wording, and M4's fourth
outcome-state producer.

---

## 6. Observer-local reputation — rule 16 (question 6)

Substrate: the Beta accumulator exists — `update_reputation`
(`social.py:298-353`), priors (`social.py:62-63`), kind weights
(`social.py:64-68`), the observer-local key `(observer, subject,
context)` enforced by there being *no* global query
(`social.py:16-19`, `:490-491`), and the `reputation_updated` record
carrying inputs-plus-result (`docs/frame-log-schema.md:128`).

### Decision R11 — reputation evidence is driven by belief acquisition, nothing else

An NPC's reputation rows update exactly when they **gain or corroborate a
belief** whose claim has reputation relevance (caller-supplied per claim
kind — same seam as `mutation_candidates`): the kind maps to the belief's
evidence type — witness path → `"witnessed"`, encounter retell →
`"reported"`, corroboration → `"corroborated"`. `subject_id` and
`positive` come from the claim's slots via the caller-supplied mapping.

T3.5's tripwire (`docs/scenario-ladder.md:76`: uninformed NPCs
unchanged — any global jump is a bug) is then assertable *by
construction*: reconstruct at tick t, diff reputation stores, assert every
changed row's observer holds a belief about the triggering claim. The
injected Thane event propagates through the ordinary witness/encounter
path, so "informed" is a belief-store query, not a flag.

---

## 7. Migration + rule-budget plan (question 7)

### Decision R12 — migration is default-on, then per-scenario declaration

1. Registry lands with all 19 rules registered; rules 1–10 as wrappers
   (R2), rules 11–19 as their tiers implement them — registered early as
   disabled stubs so §8 consequence (b) ("every rule must exist in the
   registry") holds from day one.
2. Tiers 0–2 scenarios keep passing untouched (default-on).
3. Then, one scenario file at a time, tests declare the rules they
   exercise — `driver.rules.get("mutation-policy")` is present, enabled,
   and emitted `rule_evaluated` rows — turning the existing suite into the
   §8 regression cases without a big-bang rewrite.

### Decision R13 (recommendation; owner decides) — budget accounting

19/20 with §8's own consolidation candidates applied:

- **9+10 count as one.** `stage_at` *is* one state machine;
  dormancy-reactivation is a transition in it, not a separate rule.
- **4 is schema, not rule.** The shared-claim invariant is enforced by
  store construction raising (`claims.py` `resolve()`'s duplicate-belief
  raise), like the sparse-graph rule in `social.py:14-17` — an invariant
  the data model upholds, not a policy that evaluates.

Effective count: **17/20**, headroom 3. The registry still lists all 19
names (the table is the vocabulary); consolidation changes the *budget
accounting*, not the registry contents.

---

## 8. Proposed implementation-lane split (question 8)

| Lane | Scope | Files | Depends on | Effort |
|---|---|---|---|---|
| L-A | Registry core: `Rule` protocol, per-Driver registry, `disabled_rules` construction arg, `rule_evaluated` emission, wrapper retro-registration of rules 1–10 | **new** `chronicle/rules.py`; `chronicle/driver.py` (hooks) | — | medium |
| L-B | T3.2 grudge decay: `grudge_at()` + constants block | `chronicle/social.py`, `chronicle/tests/test_social.py` | — (instrumentation optional) | small |
| L-C | T3.1 accumulation-threshold: rule 11 + escalation event (after owner approves the new event type) | `chronicle/rules.py`, `chronicle/driver.py`, `chronicle/events.py`, new scenario test | L-A, owner ruling on F2 | medium |
| L-D | T3.4 tell-decision gate: rule 15, gate wiring, `transmission_declined` | `chronicle/rules.py`, `chronicle/driver.py`, `chronicle/propagate.py` (context assembly only), new scenario test | L-A | medium |
| L-E | T3.3 violation cascade: rule 14 in `violate_obligation` | `chronicle/driver.py`, `chronicle/social.py` (if O3's self-edge lands there), new scenario test | L-A, O3 ruling | small-medium |
| L-F | T3.5 reputation wiring: rule 16, belief-acquisition hooks | `chronicle/rules.py`, `chronicle/driver.py`, new scenario test | L-A | medium |

Sequencing note: L-A and L-B are parallelizable immediately (disjoint
files). L-C through L-F all touch `driver.py` — run them serially or
accept rebase churn. Track B (dashboard) consumes `rule_evaluated` /
`transmission_declined` rows; its diff-panel/rule-log lanes should queue
behind L-A + at least one firing rule.

---

## 9. What surprised me

- **The schema is further ahead of the code than expected.** Every
  Tier-3 record this design emits already exists field-for-field
  (`docs/frame-log-schema.md:121-128`), including `roll_key | null` on
  `transmission_declined` — which turns out to be exactly the
  deterministic-decline case (R10). The only genuine schema gap is the
  escalation *event* type (F2).
- **The accumulator wants no state.** My first sketch stored counters;
  the event-sourcing discipline already in the codebase
  (`claims.py:66-68`) makes log-derived accumulation strictly better, and
  the latch falls out of `threshold_crossed` existence for free (R5).
- **Rule 8's gate has a hole exactly where T3.3 walks.** `form_grudge`
  requires a holder→victim edge; violation grudges are holder-as-victim.
  Nobody hit it because no engine path calls `form_grudge` yet — the
  social-cascade scenario is scripted.

## 10. Open points for the owner

- **O1 — run-config record.** Should the set of enabled rules be recorded
  (a) as a new trace record type (schema amendment), (b) in `runs/
  index.json` metadata, or (c) nowhere (registry is always default-on in
  practice)? I recommend (b): configuration, not derivation — but it's a
  schema-adjacent call.
- **O2 — grudge decay magnitudes** (R7's table). Placeholders; the
  ordering (emotional > evidentiary > belief-confidence half-lives) is the
  load-bearing part, not the numbers.
- **O3 — rule-8 self-victim convention** for violation grudges (R8.1).
  Self-edge vs. documented bypass in `form_grudge`. Touches an enforced
  validation rule, so it's owner-visible.
- **O4 — budget consolidation** (R13): 9+10 as one, 4 as schema-not-rule.
  Registry lists all 19 either way; the question is the counted total.
- **O5 — T3.4's `rule` field granularity.** Rule name only
  ("tell-decision"), or name + sub-reason ("tell-decision:kin-motive")?
  The schema allows any string; the rung asserts "by name." I recommend
  name in `rule`, sub-reason inside `inputs` of the paired
  `rule_evaluated` row — keeps the reserved record's vocabulary tight.

## 11. Findings

- **F1 — none of the packet's premises were wrong.** All citations
  checked: schema rows, `tell.decision` registration (`rng.py:44`),
  `form_grudge`'s caller-supplies-context discipline, the demo run's
  `relationship_formed` emission, §8's 19/20 count.
- **F2 — the escalation event type is the only schema change this tier
  needs.** `escalation_warning` (name TBD) must be added to
  frame-log-schema §3's event vocabulary and `chronicle/events.py`. The
  packet's "gaps are findings" applies: this doc proposes; the owner
  amends.
- **F3 — `rule_evaluated` volume needs a sizing pass before the dashboard
  consumes it.** R5's evaluate-on-change-only bounds accumulation rules,
  but R10's per-opportunity tell-decision rows add one row per
  transmitting encounter — on the T2.1-scale estimate (10⁵–10⁶ trace
  rows/10 days, `docs/decisions/0010:140-144`) that's a meaningful
  increment against ui-spec §1.1's trace-volume figure (already flagged in
  the lane-12 backlog for supersession churn). Worth one line in the
  owner-review cycle, not a blocker.
