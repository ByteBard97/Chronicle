# Tier 4a design prep — schedule write-back

Status: design proposal for owner review (lane 33 deliverable). No code.
Every code/schema claim carries a file:line citation verified against
`f41c058`. Structured so each **Decision** section lifts into an ADR, same
shape as the Tier-3 design doc; open points for the owner are collected in
§8.

Sources: `docs/scenario-ladder.md` Tier 4a intro + T4a.1–T4a.2 (lines
80–84), Tier 4b intro + T4b.1 (lines 86–89), §4/§8 (lines 129, 143–153);
`docs/frame-log-schema.md` §3 (line 96, the `schedule_rewrite` reserved
row); `chronicle/schedule.py`; `chronicle/driver.py`; `chronicle/rng.py`;
`chronicle/social.py`; `chronicle/framelog.py`; `chronicle/rules.py`;
`docs/design/tier-3-rule-registry-and-tell-decision.md` (the model this
doc follows) and its overseer review (`reviews/2026-08-23-lane-18/`,
`reviews/2026-08-23-lane-19/`); `docs/decisions/0009`; `docs/vision-v2.2.md`
§2; `docs/ui-spec.md` §3.8/§3.9.

---

## 0. What Tier 4a actually asks for

The tier intro (`docs/scenario-ladder.md:80-81`) names one mechanism:
**schedule block insertion/restoration driven by social state** — the
vision's "grief reroutes a mourner's days" (`docs/vision-v2.2.md:12,21`).
Two rungs:

- **T4a.1 Mourning.** Kin dies. Mourning block inserted (temple, N days);
  original schedule restored after; the rewrite is itself an event
  causally linked to the death.
- **T4a.2 Second-order counterfactual.** Run A (with reroute) vs. Run B
  (fixture-frozen, no reroute), same seed, keyed randomness. The rumor
  reaches the priest before the market in A and the reverse in B — and
  **every roll outside the mourner's changed sites is identical across
  runs** (`docs/scenario-ladder.md:84`), the keyed-randomness guarantee
  asserted directly.

This is the first tier where **state writes back into behavior** — every
prior tier's rules only ever produced beliefs/social records; nothing
before this changed what an NPC *does*. The design risk this doc has to
retire is narrower than it sounds: prove that inserting a schedule block
for one NPC cannot perturb any roll that doesn't involve that NPC, because
if it can, T4a.2 is unimplementable and every future tier that touches
schedules inherits the same doubt.

Tooling forced (`docs/scenario-ladder.md:91`, `docs/ui-spec.md:113-120`):
schedule diff (§3.8: before/after lanes per NPC, causing rule and event
linked) and run comparison (§3.9: aligned scrubbers, ranked divergence
list, **a linear merge-scan of the two trace streams for the earliest
keyed roll whose value differs** — T4a.2's assertion, tooled). Both are
informational; this design must not close their doors.

---

## 1. The write-back mechanism (question 1)

### Decision T1 — overlay, not mutation; the base schedule stays immutable

`Driver.__init__` sets `self.schedule = tuple(schedule)` once
(`driver.py:171`) and nothing else in the module ever reassigns it —
today's schedule is genuinely static for a run's lifetime. `_run_tick`
reads it fresh every tick (`driver.py:739`
`npcs_present_at(self.schedule, tick)`), so a mid-run change is visible
the moment it happens — no cache to invalidate.

Two ways to make it mid-run-writable:

- **(a) Mutate `self.schedule` in place**: splice out the mourner's
  overlapping base block(s), splice in the mourning block, and (for
  restoration) splice back a continuation block for whatever remains of
  the original block's tail past the mourning window. Every rewrite
  permanently edits the ground truth.
- **(b) Overlay**: keep `self.schedule` exactly as constructed; keep a
  separate, growing list of time-bounded overrides (`self._schedule_overlays`)
  that `_run_tick` consults before falling back to the base schedule.

**Recommendation: overlay (b).** The deciding factor is reconstruction,
not runtime cost (both are O(overlays) per tick, negligible at this
scale):

- `serialize_state`'s `"schedules"` key already only captures blocks
  **covering the exact keyframe tick** (`framelog.py:268`
  `[_schedule_json(b) for b in schedule if b.covers(tick)]`), and
  `state_at` never replays anything to keep `ReconstructedState.schedule`
  current between keyframes — it is loaded once from the nearest keyframe
  and left alone (`framelog.py:648,654,785`). This is already a known
  soft spot: `cli.py`'s `_npc_known` docstring explicitly carves out "an
  NPC ... known only from schedule blocks that fell between keyframes"
  as a case its raw-stream fallback exists to catch. Today it doesn't
  matter because the base schedule never changes — a block covering tick
  50 also covered the keyframe tick if the block spans both, which every
  v0.1 fixture's wide blocks do (`schedule.py:37-51`).
  - Under **mutation (a)**, this stops being a harmless gap. A mourning
    block that starts and ends entirely inside one keyframe interval may
    **never be captured by any keyframe** (it doesn't cover either
    keyframe's tick), so a dashboard or CLI query at a tick inside the
    mourning window would reconstruct the *pre-mourning* schedule and
    get the NPC's location wrong — silently, with no error, because
    schedule isn't trace-replayed at all today.
  - Under **overlay (b)**, the base schedule is genuinely never touched,
    so the existing `covers(keyframe_tick)` filter keeps working for the
    base layer *and* can be trivially strengthened (§1, Decision T3
    below) — while the overlay layer is reconstructed the same way every
    other Tier-3 record is: **replay the `schedule_rewrite` events up to
    T** (log-derived, arbitrary-T-exact by construction, the same
    argument Tier-3 design doc R4 made for the accumulation counter).
- **Restoration is structural under (b), not an action.** The overlay
  carries its own `end_tick`; once a queried tick is past it, the base
  schedule simply applies again — nothing to "restore," nothing to
  forget to re-splice. Under (a), restoration is an explicit second edit
  the mutator must get right (recompute the tail of the truncated block,
  or insert a fresh one) — one more place to introduce an off-by-one that
  a scenario-ladder rung wouldn't catch unless it specifically probed a
  tick after the window closed.
- **Rejected: mutation (a).** It buys nothing overlay doesn't already
  give, and it turns a currently-latent reconstruction gap into an
  active one for exactly the ticks the rung's own assertions probe (mid-
  mourning-window state).

### Decision T2 — one `schedule_rewrite` event per rewrite; no separate restoration event

`docs/frame-log-schema.md:96` reserves `schedule_rewrite` (tier 4a) with
"the rewrite as an event with a causal link to its trigger" and fields
"defined with schedule write-back" — this doc is that definition,
proposed for owner amendment (same F2-pattern as the Tier-3 doc's
escalation-event proposal):

| Field | Type | Meaning |
|---|---|---|
| `npc_id` | string | the mourner (or, generically, the NPC whose schedule is rewritten) |
| `location_id` | string | the destination for the overlay's duration (T4a.1: the temple) |
| `start_tick` / `end_tick` | int | the overlay's half-open window — `ScheduleBlock`'s own convention (`schedule.py:39,50-51`); restoration is `end_tick` reached, not a separate record |
| `cause` | string | a short tag (`"mourning"`), room for future write-back causes without a new event type |
| `trigger_event_key` | `{save_uuid, generation, seq}` | the canonical event this rewrite is causally linked to — the death, per the ladder's own wording. Same shape as `escalation_warning`'s `canonical_event_key` pattern (Tier-3 doc R6), not reused verbatim because this is the *cause*, not the anchor a claim is witnessed off — no belief is formed about a schedule rewrite itself |
| `rule` | string | the firing rule's name (`"schedule-write-back"`) — lets the schedule-diff view (§3.8: "causing rule and event linked") join directly without a `rule_evaluated` lookup |

One record captures the whole rewrite because `end_tick` is already in
it — a second "restored" event would be a derivable fact (has this
record's `end_tick` passed?), and the schema avoids that dual-role
elsewhere (Tier-3 doc §2's rejected stored-counter argument makes the
identical point about `threshold_crossed`).

**Why an event, not a trace record:** events are canonical
(`docs/frame-log-schema.md` §3 vs §4) — the schedule rewrite is a fact
about the world, not a derivation from prior facts, the same status as
`npc_died`/`escalation_warning`. It also has to be **injectable/probeable
by the fork milestone's future replay** the same way any canonical event
is, which trace records aren't designed for.

### Decision T3 — `state_at` gains a schedule-replay branch; keyframes capture the full (unfiltered) base schedule

Two small, additive changes to `framelog.py`:

1. `serialize_state`'s `"schedules"` key drops the `if b.covers(tick)`
   filter (`framelog.py:268`) — the base schedule is immutable under T1,
   so capturing it in full costs nothing extra per keyframe (a run's
   schedule is O(cast size), not O(ticks)) and removes the pre-existing
   between-keyframes gap for the base layer as a side effect.
2. `state_at` (`framelog.py:638-785`) gains one more `elif record_type
   == "schedule_rewrite":` branch reading from `EVENTS_STREAM` (parallel
   to how it already scans `EVENTS_STREAM` for `event_gamets`,
   `framelog.py:658-664`) that accumulates active overlays whose
   `[start_tick, end_tick)` covers `tick`. `ReconstructedState.schedule`
   becomes "base blocks, with any NPC under an active overlay having
   their base presence overridden for that window" — computed the same
   way §1's live-driver effective-schedule helper does (Decision T1
   asks for one function; both the live driver and replay call it, so
   there is exactly one place this logic can drift).

This is the one place this design touches code outside `driver.py`/
`schedule.py`/`events.py` — flagged for the owner because it's a real
(if small) `framelog.py` edit, not a new module.

**Restoration semantics answered:** restore the *original* schedule —
under the overlay model this is automatic (T1), and it is *resume from
where the base schedule says they'd be*, not "resume from the insertion
point." If the mourner's original block spanned past `end_tick`, they
return to it mid-block; if it didn't, whatever base block covers the
next tick applies, exactly as if the overlay had never existed. One
scenario-authoring consequence flagged in §7 Findings: the base fixture
must actually have coverage past the mourning window for "restored"
to mean anything observable.

---

## 2. The roll-identity guarantee (question 2)

### Decision T4 — automatic by construction; the assertion's exact meaning is per-pair, not per-site

`rng.roll()`'s value is a pure function of six inputs:
`(seed_id, purpose, tick, site, sorted(participants), draw)`
(`rng.py:85-103`) — nothing about who *else* is present, nothing about
iteration order, nothing about how many pairs exist at that site this
tick. `sample_encounters` (`schedule.py:89-144`) generates exactly one
`EncounterRoll` per co-present ordered pair at each location
(`schedule.py:114-125`); a pair's roll never reads the rest of
`present_by_location`.

Walking through what a mourning overlay actually changes:

- At the mourner's **original** site, for the overlay's window, the
  mourner is absent from that location's presence list — pairs
  `(mourner, X)` simply don't appear in `sample_encounters`' output
  there (no roll happens, and per T2.6's "negative results are
  first-class" discipline, note there is also no `encountered: false`
  row for them — the pair was never rolled, which is a different,
  weaker kind of absence than a rolled-and-declined one). Pairs *not*
  involving the mourner at that same site, same tick, are computed
  identically in both runs — `sample_encounters` never looks at who is
  absent, only at who is present, and their roll only names the two of
  them.
- At the **temple** (the overlay's destination), new pairs
  `(mourner, priest)` etc. appear only in Run A — genuinely new rolls at
  a site/participant combination that doesn't exist in Run B at all.
  This is not a violation of the guarantee; it's the entire point of
  T4a — different co-presence graph, different information flow.
- Every other site, every other tick, every pair not involving the
  mourner: untouched. `_run_tick` iterates ticks sequentially in both
  runs regardless (`driver.py:727`); nothing about the overlay changes
  tick order or any other NPC's blocks (T1 guarantees the overlay never
  touches non-mourner blocks).

**So the guarantee is automatic from `roll_key` mechanics alone — no new
design is needed to make it hold; the work is making sure the write-back
mechanism doesn't accidentally violate the "never touches another NPC's
presence" precondition it depends on** (which T1's overlay design
satisfies by construction: an overlay is keyed to one `npc_id` and
overrides only that NPC's own presence computation).

**The design risk named in the packet — "what breaks if a block
insertion changes pairings at *unchanged* sites" — does not materialize**
under this design, precisely because `sample_encounters` computes each
pair's roll independently of the full occupancy list. It *would*
materialize if presence were computed some other way (e.g., a
site-level "roll once for who talks to whom" scheme) — worth stating
explicitly since it's the kind of assumption a future refactor could
break silently; recommend a code comment at the `sample_encounters` call
site (or the function itself) noting that T4a.2's guarantee depends on
per-pair independence, not just per-site keying.

**The assertion's exact meaning, precisely stated for the T4a.2 rung:**
for every `encounter_rolled` record whose `{npc_a, npc_b}` does not
include the mourner's id, the record in Run A and the corresponding
record in Run B (same `tick`, same `location_id`, same participants) are
**byte-identical** (`value`, `threshold`, `encountered` all equal) — this
is a strictly stronger, fully mechanical check, and it is exactly what
`docs/ui-spec.md:120`'s forced tooling already commits to building
("first-divergent-roll finder: a linear merge-scan of the two trace
streams for the earliest keyed roll whose value differs"). The
narrative assertion (priest hears before market in A, reverse in B) is
the human-legible companion, not a substitute — recommend the rung
assert both, with the roll-identity check first (it is what actually
proves the mechanism; the narrative check proves the narrative
following from it).

---

## 3. Mourning rule — rule 17 (question 3)

### Decision T5 — trigger is belief acquisition + kinship, at the same call sites as rule 16

T3.5's precedent (Tier-3 doc R11): reputation evidence is driven by
*belief acquisition*, evaluated at the driver's existing witness/retell
(new-belief-only)/corroborate wrappers
(`driver.py:295-350` `witness`, `:352-448` `retell`, `:450-...`
`corroborate`), never a per-tick sweep, because that's exactly when the
accumulator (there: reputation; here: "does this NPC now know their kin
died") can change. Rule 17 reuses the identical shape:

- **Trigger condition** (assembled by the driver, never inside a rule —
  the T2.3 lesson, restated in Tier-3 doc R3.3): a belief just formed
  (or, for `retell`, formed for the *first* time — `hearer_already_held`
  is already computed at `driver.py:376` and gates rule 16 the same way,
  `driver.py:430`) for a claim whose kind is registered as
  mourning-eligible, **and** the newly-informed holder has a `"kinship"`
  relationship edge to the deceased (`self.social.relationship(holder_id,
  deceased_id, "kinship")`, the exact lookup already used for the
  tell-decision gate's motive check at `driver.py:1039`).
- **Naming the deceased is a real gap, flagged as a finding.** Unlike
  the accumulation rule's victim slot (`accumulation_thresholds`'
  `(victim_slot, threshold)`, Tier-3 doc R4) or reputation's subject slot
  (`reputation_relevance`'s `(subject_slot, ...)`, Tier-3 doc R11), an
  `npc_death` claim's slots today carry `perpetrator`/`cause`/`location`
  (see any Tier-0/1 fixture, e.g. `chronicle/tests/test_agent_debug_cli.py:61`)
  — **not** the deceased's own id; that only exists implicitly via the
  claim's `canonical_event_key` pointing at the `NPCDied` event. Proposed
  fix, same caller-supplies-context idiom as every other Tier-3 mapping:
  a construction-time `mourning_triggers: Mapping[str, str]` (claim kind
  → the slot naming the deceased), and scenario/fixture authors add that
  slot explicitly when witnessing a death claim meant to be
  mourning-eligible (e.g. `slots={..., "deceased": "jarl_balgruuf"}`) —
  zero schema change (claim slots are already free-form per witness()
  caller), pure fixture-authoring discipline. This is the one place
  T4a.1 needs a fixture change beyond "add a kinship edge," and it
  should be called out to whoever builds the north-star fixture (T6
  needs exactly this: "his children hold grudges... the mourners'
  rerouted days," `docs/vision-v2.2.md:21`).
- **Rule shape**: a real `Rule`, not an always-fires wrapper — mirrors
  `TellDecisionRule`/`AccumulationThresholdRule` (`rules.py:182-207,
  210-240`), not `RecordedRule`. `evaluate()` receives caller-assembled
  booleans only (`kin: bool`, `already_mourning: bool` — the latch,
  below) and computes `fired = kin and not already_mourning`; it never
  queries `self.social` itself. `fired` means the rewrite is inserted —
  same "fired = the rule's effect, not its evaluation" convention as
  rule 15 (`rules.py:224-226`).
- **Real toggle, not instrumentation-only.** Lane 19's accepted judgment
  call (`docs/work-packets/reviews/README.md:85`) draws the line at
  "real toggles only for driver-owned rules 6/7" (rules that decide
  whether something happens, vs. wrapper rules that only log an
  already-decided outcome). Rule 17 is driver-owned in exactly that
  sense — disabling it must suppress the schedule rewrite itself, not
  just its `rule_evaluated` row, because **this is the mechanism T4a.2's
  Run B needs** (see Decision T7 below: B is A with rule 17 disabled,
  not a hand-authored second fixture).

### Decision T6 — hysteresis is a log-derived latch; duration/location are placeholder tunables

Doctrine 3 ("no behavior threshold without hysteresis and an attached
reason, ever," `docs/vision-v2.2.md:67`, cited identically in the Tier-3
doc §0). Rule 17's "threshold" is a one-shot trigger, not a numeric
accumulator, so hysteresis reduces to: **never re-insert a mourning
overlay for the same (mourner, death) pair.** Same pattern as rule 11's
latch (Tier-3 doc R5, as amended by its lane-24 implementation note): the
latch is **store/log-derived** — the existence of a `schedule_rewrite`
event already naming this `npc_id` + `trigger_event_key` — so a
corroboration of the same death heard again later (or a keyframe-resume
replay) cannot double-insert. The "attached reason" doctrine 3 also wants
is the `rule_evaluated` row's `inputs`/`result` plus the emitted event's
own `trigger_event_key`/`rule` fields — the same reason is visible from
either side (trace or event), which is what the schedule-diff view
(§3.8) needs to link "causing rule and event."

Proposed placeholder tunables (new constants block in `driver.py` or
`schedule.py`, same placeholder-comment discipline as
`schedule.py:31-34`'s `ENCOUNTER_PROBABILITY` and the Tier-3 doc's
grudge half-life table):

| Constant | Proposed | Rationale |
|---|---|---|
| `MOURNING_DURATION_TICKS` | 72 (3 game-days) | Placeholder magnitude; the ladder names "N days" without pinning N. Long enough to be observable in a rung with a handful of encounter ticks, short enough not to dominate a demo-scale run. |
| `mourning_location` | construction-time param, no numeric default | Where the household's temple is isn't derivable from anything in the engine (no location taxonomy exists — `schedule.py:42`'s `location_id` is a bare string, per T2.6's own finding). One default destination per run is enough for T4a.1's single-household rung; a `Mapping[str, str]` per-household override is a natural follow-on if the north-star fixture needs more than one mourning site, not needed yet. |

Both are owner-adjudicated (open point O2, §8) — the ordering
requirement (a fixed, observable duration; a real location the encounter
sampler can roll at) is the load-bearing part, not the numbers, exactly
as the Tier-3 doc argued for grudge half-lives.

---

## 4. Avoidance weighting preview — rule 18 (question 4, Tier 4b)

Out of this doc's implementation scope (Tier 4b, not 4a) but the packet
asks for the shape and, specifically, why it must stay out of T4a.1/
T4a.2. Sketch only:

### Decision T6b (preview, not proposed for this lane's implementation)

- **Mechanism**: a per-pair encounter-probability override, not a new
  roll. `sample_encounters`' `encounter_probability` argument
  (`schedule.py:94,140-141`) becomes pair-aware: a caller-supplied
  override (e.g. `avoidance_pairs: Mapping[frozenset[str], float]`,
  populated by the driver from active grudges) lowers the *threshold*
  `encountered = value < encounter_probability` is compared against for
  a specific pair, while `value` itself — the roll — is computed exactly
  as today, same `roll_key`, same purpose (`ENCOUNTER_CO_PRESENCE`,
  `rng.py:41`). **No new RNG purpose is needed**: the roll doesn't
  change, only what it's compared to, which is a comparison the caller
  already owns (`sample_encounters` already takes
  `encounter_probability` as a parameter, `schedule.py:94`).
- **Gate**: a grudge above `AVOIDANCE_GRUDGE_THRESHOLD` (a new tunable,
  parallel to `forgiveness_threshold`) **and** not `grudge_cooled`
  (`social.py:300-307`, already implemented as of lane 20 — decayed
  severity below `forgiveness_threshold` means the grudge no longer
  gates behavior rules, docstring at `social.py:303`). The cooled floor
  already exists exactly for this: it's the mechanism that lets an old
  grudge stop avoiding someone without deleting the record.
- **Why this must stay out of T4a.1/T4a.2, not just "different tier"
  bookkeeping**: T4a.2's proof (Decision T4) depends on every roll
  outside the mourner's changed sites being **byte-identical**, including
  `threshold`. If rule 18 were active during the T4a.2 scenario and any
  unrelated grudge happened to cross the avoidance threshold at some
  point in the run, it would change `threshold` (and therefore possibly
  `encountered`) for that pair in a way with *nothing to do with*
  the mourning reroute — polluting the exact signal T4a.2 exists to
  isolate. The ladder's own framing ("different failure signature,"
  `docs/scenario-ladder.md:86`) is the same point from the requirements
  side: 4a changes *who's at the table*, 4b changes *whether tablemates
  actually talk*, and conflating them in one rung would make a T4a.2
  failure ambiguous between "the reroute broke roll-identity" and "an
  unrelated avoidance rule did." Rule 18 stays a registered, disabled
  stub through Tier 4a (`rules.py:263`'s current `StubRule` entry is
  already correct and needs no change from this lane).

---

## 5. Migration + rule-budget plan (question 5)

### Decision T7 — no new rule names, no new RNG purposes; Run B is Run A with rule 17 disabled

- **Budget**: rules 17/18 are already counted inside the ladder's raw 19
  (`docs/scenario-ladder.md:151-152`) and inside the Tier-3 doc's R13
  consolidation math (17/20 effective, `docs/design/tier-3-rule-registry-and-tell-decision.md:371`)
  — landing them fills two of the registry's existing stub slots
  (`rules.py:262-263`), it does not grow the count. Nothing in this
  design proposes a 20th rule.
- **RNG purposes**: none new. Rule 17 introduces no roll at all
  (mourning triggers deterministically off kinship + belief acquisition
  — §3). Rule 18's preview reuses `ENCOUNTER_CO_PRESENCE`
  (§4). `rng.py:46`'s `PURPOSES` frozenset is untouched by this design;
  if a future refinement needs a genuinely new draw (e.g. a rolled
  mourning duration), that is explicitly an ADR-0009 conversation, per
  the packet's own framing — not something this doc pre-empts.
- **T4a.2's Run B, precisely**: identical construction to Run A (same
  `seed_id`, same base schedule, same fixtures) with
  `disabled_rules=(SCHEDULE_WRITE_BACK,)` (the existing R1 construction-time
  toggle mechanism, `rules.py`/`driver.py:224`). Because T1's overlay
  never runs when rule 17 doesn't fire, Run B's presence computation is
  simply "base schedule, forever" — no separate "no-reroute" fixture to
  author and keep in sync with Run A's. **Rejected alternative**: a
  hand-authored second schedule fixture with no mourning-eligible
  kinship edges. Rejected because it multiplies the moving parts T4a.2
  has to hold identical (two fixtures instead of one config flag) for no
  benefit — the whole point of the registry's construction-time toggle
  (R1) is exactly this kind of A/B, and T4a.2 is its first real customer.

---

## 6. Proposed implementation-lane split (question 6)

| Lane | Scope | Files | Depends on | Effort |
|---|---|---|---|---|
| L-G | Rule 17 core: `schedule_rewrite` event type (after owner approves the new event type, T2); `chronicle/schedule.py` effective-schedule helper (base + active overlays, shared by live driver and replay, T1); `driver.py` overlay state + trigger wiring at the witness/retell/corroborate call sites (T5) incl. the `mourning_triggers` mapping; `framelog.py`'s two small edits (unfiltered base-schedule keyframe capture + `schedule_rewrite` replay branch, T3); `rules.py`'s `ScheduleWriteBackRule`; new scenario test for T4a.1 | `chronicle/events.py`, `chronicle/schedule.py`, `chronicle/driver.py`, `chronicle/framelog.py`, `chronicle/rules.py`, new scenario test | owner ruling on the new event type (like Tier-3's F2) | medium-large |
| L-H | T4a.2 counterfactual: two-driver harness (A enabled, B with rule 17 disabled per T7), the roll-identity assertion (byte-identical `encounter_rolled` rows outside the mourner's pairs, per Decision T4's exact wording) plus the narrative assertion (priest before market in A, reverse in B) | new scenario test only | L-G | medium |

Sequencing note: L-G is one lane, not split further, because its pieces
are tightly coupled — the overlay helper (T1), its event shape (T2), and
its replay branch (T3) are one mechanism; splitting them would just
produce interface churn between sub-lanes touching the same few lines of
`driver.py`/`schedule.py`. L-H is a pure scenario-test lane once L-G
lands (no new production code). Track B's §3.8 (schedule diff) should
queue behind L-G — it needs `schedule_rewrite`'s final field shape — and
§3.9 (run comparison)'s roll-merge-scan tool is generically useful
before T4a.2 exists (it's testable against any two runs sharing a
`seed_id`), so it can start in parallel with L-G rather than waiting on
it. Rule 18 (Tier 4b) is explicitly not in this split (§4) — a future
design lane once 4a is accepted.

---

## 7. What surprised me

- **The reconstruction gap was already there, just latent.** Nobody hit
  it because the schedule has never changed mid-run before; T4a is the
  first tier that makes `framelog.py:268`'s keyframe-tick filter and
  `state_at`'s "load schedule once from the keyframe, never replay it"
  behavior (`framelog.py:648-654,785`) actually matter. Overlay (T1) is
  the design that happens to fix this as a side effect rather than make
  it worse, which is a strong argument for it independent of the
  restoration-semantics argument.
- **The roll-identity guarantee needed no new mechanism at all** — it
  falls out of `sample_encounters` computing each pair independently
  (`schedule.py:114-125`), which was presumably an accident of how it
  was written for Tier 1, not something ADR-0009 was designed with T4a.2
  specifically in mind for. The actual design work was proving it, and
  naming the one precondition (an overlay must never touch another NPC's
  presence) a future refactor could accidentally break.
- **`npc_death` claims don't name the deceased in their own slots.**
  Every other Tier-3 accumulator (theft's victim, reputation's subject)
  already had a natural slot to point a caller-supplied mapping at;
  mourning's trigger is the first one where the obvious slot doesn't
  exist yet in any fixture, because nothing before this needed to know
  "who died" from the claim's content rather than from the canonical
  event underneath it.

## 8. Open points for the owner

- **O1 — the `mourning_triggers` claim-slot convention** (§3, Decision
  T5). Confirms the caller-supplies-context idiom once more, but it's a
  fixture-authoring requirement for anyone building a mourning-eligible
  death claim from here on — worth a line in whatever scenario-authoring
  notes exist (the Tier-3 doc's lane-24 authoring-notes precedent,
  `docs/work-packets/reviews/README.md:87`, is the model: propagate the
  convention into the implementing lane's packet directly).
- **O2 — mourning duration/location tunables** (§3, Decision T6).
  Placeholders; the ordering requirement (observable, non-trivial
  duration; a real rollable location) is load-bearing, the numbers
  aren't.
- **O3 — the new `schedule_rewrite` event type** (§1, Decision T2):
  schema/ADR amendment for the owner, same status as the Tier-3 doc's
  F2 (`escalation_warning`).
- **O4 — the `framelog.py` edit** (§1, Decision T3). Small and additive,
  but it's the one place this design reaches outside
  `driver.py`/`schedule.py`/`events.py`/`rules.py` — flagging so the
  implementing lane's file boundaries include it explicitly rather than
  it surfacing as an unauthorized-touch finding the way the Tier-3
  accumulation lane's `framelog.py` branch did
  (`docs/work-packets/reviews/README.md:86`, "retroactively in-bounds").
- **O5 — per-household mourning locations.** T4a.1's rung needs exactly
  one; whether the north-star fixture (T6) needs a
  `Mapping[str, str]` of per-household destinations is a fixture-design
  question, not answered here (§3, Decision T6's table).

## 9. Findings

- **F1 — none of the packet's premises were wrong.** The roll-identity
  citation (`rng.py:85-103`), the `schedule_rewrite` reserved schema row
  (`docs/frame-log-schema.md:96`), `grudge_cooled`'s existing
  implementation (`social.py:300-307`), the kinship-lookup precedent
  (`driver.py:1039`), and the §8 rule count all check out as described.
- **F2 — the schedule-reconstruction gap (§1, §7) is the one genuine
  latent bug this design surfaces**, not created by it: `framelog.py`'s
  keyframe-tick-covers filter and `state_at`'s never-replay-schedule
  behavior have been silently relying on the schedule being static since
  M0. It costs nothing to fix now (Decision T3) and would be a much
  harder bug to diagnose later if T4a landed with mutation (T1's
  rejected alternative) instead.
- **F3 — `npc_death` claims need an explicit deceased-naming slot
  convention before any mourning-eligible fixture can be authored**
  (§3, O1) — this is new fixture-authoring surface, not an engine gap;
  flagged so the implementing lane's scenario test doesn't discover it
  mid-build the way lane 24 discovered the `framelog.py` boundary gap.
- **F4 — T4a.2's roll-identity assertion is exactly what §3.9's forced
  tooling already commits to building** (the linear merge-scan,
  `docs/ui-spec.md:120`): this design doesn't invent a new verification
  method, it names the precise thing that tool needs to scan for. Worth
  noting for whoever scopes the tooling lane — the scenario-test
  assertion and the dashboard tool should share one definition of
  "outside the mourner's changed sites," not two independently-written
  ones that could silently drift apart.
