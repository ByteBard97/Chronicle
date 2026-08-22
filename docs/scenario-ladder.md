# Chronicle — Scenario Ladder & Observability Plan (v0.4 — FINAL)

**Status:** v0.4 — FINAL for the constitution commit. Supersedes v0.3. Incorporates two code-grounded reviews of v0.3: T2.6's code-verification flag closed (both reviewers verified schedule.py — carriers are pure fixtures); T2.3 amended to evidence-type ordering (the trust-source middle tier contradicted §6's own trust deferral — re-homed to a future rung alongside trust machinery); supersession recorded as a separate record (variant immutability); resolution promoted to an invariant-enforcing store write path; branch key frozen into the trace schema; seed_id naming + roll-purpose discriminator in the keyed hash; trace declared always-on; tier-0 as-of-T rendering required.
**Change summary vs. v0.2:** mobile carriers added as T2.6/T2.7 (the vision-review catch: nothing previously moved information across hold borders); variant-resolution policy decided (§3 T2.3, amended in v0.4); trace placement decided (sibling stream, shared versioned frame schema — Tier 1); rule budget counted (§8); map-scope consequence for the UI spec recorded (multi-hold from Tier 2).

**Project:** Chronicle — a headless social-simulation engine for Skyrim SE/AE. NPCs hold beliefs with provenance; beliefs propagate and mutate as rumors through schedule-driven encounters; grudges, obligations, and observer-local reputation accumulate from events; state eventually writes back into NPC behavior. Event-sourced, deterministic, inspectable: every derived state must answer "who believes this, from what evidence, through whom, since when" (ADR-0007).

---

## 1. Design principles (unchanged, plus one)

1. **One new mechanism per tier.** A failure at tier N is attributable to the thing tier N introduced. If a scenario needs two new mechanisms, it is split or moved.
2. **Tooling is forced, never speculative.** Each tier names the observability capability its assertions cannot be checked without.
3. **Lower tiers stay in the regression suite forever.**
4. **Determinism, now with keyed randomness.** Every roll is derived from a hash of (run_id, tick, site, pair/actor) — not from stream position. Unchanged parts of the world produce identical rolls across runs, enabling exact seeded assertions and clean A/B counterfactuals. *(New; see §5. Must land before any Tier 4 code.)*
5. **Headless first.** No game process anywhere in this ladder.

## 2. Corrected machinery inventory (verified against `b5bd87b`)

**Built and green:**
- Append-only, branch-aware event log (`events.py`).
- Claims / variants / subjective beliefs with typed slots and evidence chains; one claim per canonical event (enforced); one belief per (holder, claim) (enforced); verbatim/gist strength split with fuzzy-trace-style decay (`claims.py`).
- `retell()` with **flat** confidence decay (RETELL_CONFIDENCE_DECAY = 0.8) — *not* trust-weighted.
- `corroborate()`: noisy-or confidence rise, distinct-source gating, staleness checks — **built, untested by any scenario until this revision**.
- Rumor stage machine, **five states**: unheard → heard → repeated → dormant → forgotten. Only heard/repeated are stored; dormant/forgotten derive lazily via `stage_at()`. There is no checking/believing/spreading/refuting state.
- Social state: sparse relationships (colocation, kinship, faction, shared_employer — enforced); grudges with separate emotional/evidentiary strength (**no decay function**); obligations with issue/fulfill/violate paths (violation→grudge wiring not yet present); observer-local Beta-style reputation (`update_reputation()`).
- Schedule-driven encounter sampling: co-presence + **one uniform global probability** (ENCOUNTER_PROBABILITY = 0.5, sequential RNG stream). No per-pair weighting.

**Not built (each is a named mechanism with a rung below):** tell-decision policy (privacy/motive gating); conflicting-variant resolution; grudge decay; trust-discounted retelling (deferred, see T1.1 note); rule registry with toggles (today: module constants); derivation trace; schedule write-back; pairwise encounter weighting; roles; collective aggregates; economy; LLM tiers; TTS; adapter.

## 3. The ladder

### Tier 0 — Claims-layer mechanics, no propagation
*Machinery: already built. These rungs must pass today — and now they actually can.*

- **T0.1 Witness.** One theft, one witness. Assert: exactly one belief; correct slots; evidence = direct observation; confidence at the direct-observation baseline.
- **T0.2 Decay.** 30 quiet game-days. Assert: exact verbatim/gist values for the fixed inputs (deterministic curve — no tolerance band needed); stage_at() = heard throughout; not dormant yet.
- **T0.3 Corroboration** *(replaces the unimplementable contradiction rung; exercises built-but-untested `corroborate()`)*. Two independent witness reports reach one NPC as testimony. Assert: confidence rises on the exact noisy-or curve; a third report **from an already-counted source** produces no rise.
- **T0.4 Shared claim invariant.** Two witnesses to one canonical event. Assert: one Claim, two beliefs. A disagreeing second witness produces a **Variant**, never a second Claim.

**Tooling forced:** injection console; NPC inspector (belief table). Every rendered field links to its producing event — the link-everything discipline that becomes ADR-0007's drill-down.

### Tier 1 — One-hop transmission + the derivation trace
*New mechanism (sim): testimony transfer through a sampled encounter — pure transmission only; all tell-decision policy moved to Tier 3.*
*New mechanism (infrastructure): the **derivation trace** — an append-only stream of derivation records emitted by the tick loop: every roll (keyed inputs + value + threshold), every encounter (fired or not), every transmission (fired, or declined-with-reason), every rule evaluation (fired, or evaluated-with-current-accumulator). This is the substrate for "negative results are first-class," the step-file the dashboard replays, and the only thing that makes "reason recorded and queryable" assertable. Retrofitting it is misery; it lands here.*

***Placement decision (resolves former §7 Q2):*** *the trace is a **sibling stream** to the canonical event log, not entries in it — the canonical log stays lean and semantic (things that happened in the world), the trace carries derivation mechanics (why the sim did what it did). Both share one versioned keyframe+delta frame schema so the dashboard scrubs them on a single timeline; the schema is frozen and versioned before any UI work, per ui-doctrines (the log format outlives UI churn). Two schema commitments made now because retrofitting them is the same cheap-now/brutal-later trade as keyed randomness: (1) **the trace is always-on, never a debug flag** — T1.3 and T3.4 assert against trace contents and scenario failures attach the trace file, so a switchable trace breaks the test suite by configuration; (2) **trace records carry the timeline branch key (save_uuid, generation) from day one** — the canonical log already does, both scrub one timeline, and freezing the frame schema without the branch key forces a schema-v2 retrofit the moment save/reload exercising begins.*

- **T1.1 Tell.** Witness and neighbor share a location block. Assert: listener belief exists; source chain = [witness]; confidence = witness confidence × 0.8 **exactly** (flat decay — trust-discounted retelling is a deliberately deferred mechanism; when scheduled, it gets its own rung because it feeds social state back into claims).
- **T1.2 Kill the sole witness.** Player kills the witness before any encounter. Assert: zero beliefs held by anyone else **for that claim id** at any later tick (scoped so the killing itself, if witnessed, doesn't vacuously break the assertion).
- **T1.3 Non-encounter is recorded.** Co-present pair, roll fails (keyed roll pinned by fixture). Assert: the trace contains the negative record with roll value vs. threshold. *(Tests the trace itself.)*

**Tooling forced:** encounter feed rendering the trace — who/where/when, what transferred, what didn't and why, negatives with equal visual weight.

### Tier 2 — Multi-hop propagation, mutation, and variant conflict
*New mechanisms: mutation policy + variant lineage; **conflicting-variant resolution** (forced by this tier's own machinery — the first time a holder of variant A hears variant B, the one-belief-per-(holder, claim) invariant meets a contradiction, and the code currently has no answer). Resolution policy is a design decision this tier must make: candidate policies (keep-stronger / keep-newer / trust-source) produce different rumor dynamics; pick one, name it as a rule, assert it.*

- **T2.1 Spread.** Public crime, 5 witnesses, 10 game-days, cast ≈ 25. Assert: the **exact informed-set** for the seed, plus the per-tick believer-count curve (catches too-fast/too-slow, not just endpoint). Distributional tolerance is reserved for future math-tier-scale casts (~1,000), not this one.
- **T2.2 Mutate.** Same run. Assert: the **exact mutated slot and value** under the seed; predecessor chain intact; no variant without a predecessor.
- **T2.3 Conflicting variants.** Holder of variant A hears variant B. **Policy decision (resolves former §7 Q1, amended v0.4): evidence-type ordering with strength tiebreak.** The variant whose evidence chain terminates in the stronger evidence *type* wins — witnessed > reported — and when types tie, higher summed evidence strength wins. This is pure claims-layer data (Evidence.evidence_type), keeping Tier 2 free of social-state lookups: the v0.3 draft's "trusted-relationship teller" middle tier read layer-4 relationship edges inside a claims operation — exactly the social→claims feedback §6 defers for trust-discounted retelling — and is re-homed to a future rung that arrives *with* trust machinery, built on the caller-supplies-context pattern propagate.py already uses. The folk dynamics survive intact: an eyewitness shrugs off thirdhand gossip (witnessed beats reported); a rumor-holder updates when the witness herself contradicts them (the incoming chain terminates in witnessed evidence). Rejected alternatives recorded: keep-stronger ignores provenance; keep-newer makes belief a recency contest late liars always win. Mechanics: **supersession is a separate record** (store-level link naming loser and winner) — never a write onto the losing variant, which is a frozen lineage record; the winner takes a small **contested-claim confidence dent** (a challenged belief is held less certainly than an unchallenged one); and **resolution is a first-class store write path** (sibling to retell()/corroborate()) that enforces the one-belief-per-(holder, claim) invariant at the store — today that invariant survives only because the propagation driver declines when both parties hold beliefs, and T2.3 is precisely where that guard stops sufficing. Assert: the named rule fires; the invariant holds and the store *raises* on any duplicate-creating path; both encounters are in the evidence chain; the supersession record exists and names both variants; the winner shows the dent; and the resolution direction flips when the fixture swaps which side holds the eyewitness.
- **T2.4 Motivated mutation placeholder.** Faction-aligned NPC retells with allegiance-consistent slot substitution (rule-based; the LLM gossip-hub tier later slots behind this interface). Assert: substitution direction matches allegiance.
- **T2.5 Dormancy and reactivation.** After spread, 90 quiet days. Assert: stage_at() migrates states per decay (belief/rumor decay only — grudge cooling belongs to Tier 3); nothing resurrects unprompted; then a fresh retelling **reactivates** a dormant rumor (positive twin, exercising stage_at()'s documented support).

- **T2.6 The carrier.** *(New in v0.3 — the vision-review catch: co-presence encounters over single-hold schedules mean every rumor structurally dies at the hold border, so the north star's Markarth/Riften beats were previously impossible.)* Fixtures add 2-3 **mobile carriers** — a caravaneer alternating Whiterun/Markarth on a multi-day cycle, a courier on a Whiterun/Riverwood/Riften circuit — ordinary NPCs whose schedule blocks span holds, making them bridge nodes by construction. Scenario: public crime in Whiterun; carrier hears it at the market; carrier's travel block completes. Assert: the first Markarth-resident belief exists only at a tick ≥ the carrier's arrival; the carrier appears in every Markarth evidence chain; no cross-border belief exists via any non-carrier path. **Flag closed (v0.4):** both reviewers verified against schedule.py — location_id is a bare string with no hold concept, the sampler groups by string equality, and multi-day blocks are just large tick ranges; carriers are pure fixtures, zero code changes. **Road decision:** travel blocks place the carrier at explicit road locations (road_whiterun_markarth), making roads deliberate weak propagation paths where travelers can meet en route; T2.7's negative assertion is scoped accordingly (the v0.1 fixture keeps roads otherwise empty so the border-holds assertion stays exact; a later fixture adds a second traveler and asserts the road leak *as designed behavior*).
- **T2.7 Kill the carrier.** The inter-hold twin of T1.2. Same setup; the carrier dies (or is removed) before departure. Assert: zero beliefs for that claim id held by any non-Whiterun NPC at any later tick — the border holds. Then the positive control: a second carrier on the same route restores propagation on the next cycle.

**Tooling forced:** map + rumor overlay (dots colored by the real five stages) + global scrubber; variant tree with per-node slot-diffs. **Named critical-path tasks:** (1) the location→coordinate fixture mapping abstract location ids to render coordinates (extraction path already verified); (2) *consequence of T2.6 for the UI spec:* the map renders **multiple holds** from Tier 2 on — Whiterun at full fidelity plus at least destination markers for carrier routes; the UI spec must not fix the map's scope to one hold.

### Tier 3 — Social accumulation, decay, and the tell-decision gate
*New mechanisms: threshold/accumulation rules; **grudge decay** (the missing twin of belief decay); **tell-decision policy** (privacy/motive gating of transmission — absorbs old T1.2 and T3.4, introduced once); violation→grudge+reputation wiring over the existing obligation paths; **rule registry** (rules become named, toggleable, instrumented objects — forced by this tier's tooling; tiers 0–2 scenarios migrate onto it as regression cases).*

- **T3.1 Serial theft.** Four thefts, same merchant. Assert: below threshold, annoyance only; at threshold, exactly one escalation — materialized **as an event in the log first** (the warning claim hangs off that event's canonical key; no orphan beliefs, no broadcast — it propagates to peer merchants only through Tier-1/2 encounters); no double-fire on theft five.
- **T3.2 Humiliation.** Public brawl loss, 6 witnesses. Assert: grudge created, emotional > evidentiary strength; witnesses hold beliefs; **grudge decays slower than the rumor** (now assertable — grudge decay exists as of this tier).
- **T3.3 Favor ledger.** Three favors; invoke one (consumed); refuse one. Assert: refusal fires the new violation wiring — grudge + reputation evidence row for observers present.
- **T3.4 Secret with stakes.** Two NPCs learn the player's secret; one is kin-motivated to keep it. Assert: motivated holder never transmits — and the trace shows the tell-decision rule declining **by name** each opportunity; unmotivated holder transmits on normal keyed rolls.
- **T3.5 Status deference** *(re-homed from Tier 4 — it is reputation accumulation from an injected event, no behavior change involved)*. Player becomes Thane. Assert: reputation rows update for informed NPCs only; uninformed NPCs unchanged — any global jump is a bug (the observer-locality tripwire).

**Tooling forced:** diff panel (two ticks → all social-state deltas, each annotated with the firing rule, linked to the trigger); rule-firing log over the registry — including **evaluated-but-not-fired rows with current accumulator values** (a counter stuck at 3-of-4 must be visible, not silent; symmetric with Tier 1's negative records).

### Tier 4a — Schedule write-back
*New mechanism: schedule block insertion/restoration driven by social state — moving bodies.*

- **T4a.1 Mourning.** Kin dies. Assert: mourning block inserted (temple, N days); original schedule restored after; the rewrite is itself an event causally linked to the death.
- **T4a.2 Second-order counterfactual.** Run A (with reroute) vs. Run B (fixture-frozen, no reroute), same seed, keyed randomness. Assert: rumor reaches the priest before the market in A and the reverse in B — and every roll outside the mourner's changed sites is **identical** across runs (the keyed-randomness guarantee, asserted directly).

### Tier 4b — Pairwise encounter weighting
*New mechanism: social state modifies per-pair encounter probability — reweighting rolls. Different failure signature from 4a; split accordingly.*

- **T4b.1 Avoidance.** Strong grudge between a pair. Assert: pair weight drops per the named avoidance rule; encounters between them cease at the shared tavern block; the weight delta is visible in the trace, not a hidden multiplier.

**Tooling forced (4a+4b):** schedule diff view (before/after lanes, causing rule linked); **run-comparison view** — two timelines, aligned scrubbers, belief-set and trace diffs, first-divergent-roll finder (the instrument T4a.2 cannot be debugged without, and the RNG-drift detector for every future change).

### Tier 5 — Roles and vacancy
*New mechanism: roles as first-class entities (the last new sim mechanism).*

- **T5.1 Vacancy.** Steward killed. Assert: role vacant; duties lapse with defined effects; lapse effects are events propagating through Tiers 1–4 machinery.
- **T5.2 Succession.** Assert: successor resolves from relationship/faction state; **varying the prior-relationship fixture while holding the seed produces a different successor** (fixtures carry the counterfactual, not seeds — the stronger determinism claim).
- **T5.3 No orphaned references.** Everything that pointed at the holder resolves through the role.

**Tooling forced:** role inspector panel; role rows in the diff panel. Compositions only.

### Tier 6 — The north star (composition test)
*No new mechanism. The Jarl assassination asserting the full cascade: succession (T5) + grief reroutes and grudges (T3/T4a) + city-wide propagation with a surviving mutated variant (T2) + collective fear as a **read-only aggregate view** — derived on read, with drill-down to contributing beliefs, never cached, and **never an input to any behavior decision**. The moment any rule keys off the aggregate, it becomes a feedback mechanism requiring its own tier and recorded inputs; T6's acceptance test for "view is enough" is that no assertion needs the aggregate to cause anything, only to be correct.*

If Tiers 0–5 are green and T6 fails, the mechanisms don't compose — this rung exists to catch exactly that. **Tooling forced: none.** If T6 needs new UI, the tooling design failed; that is itself the acceptance test.

## 4. Cross-cutting tooling rules (unchanged, one addition)

1. Global scrubber from the first commit; every view renders as of tick T. This binds Tier 0 too: the scrubber *widget* arrives with the map at Tier 2, but the Tier-0 inspector and console render as-of-T from day one (cheap — decay is computed at read time), so no view ever exists that only shows "now".
2. Dashboard state lives in the URL; **failing assertions emit a deep link** to the pinned tick/NPC/belief. Non-transmission and non-firing assertions deep-link to their trace rows.
3. Every rendered field links to its cause.
4. Negative results are first-class — now with a substrate (the Tier-1 derivation trace) rather than an aspiration.
5. *(New)* The trace is the single schema: state deltas + derivation records + negative records = the step file the dashboard replays, the object the run-comparison view diffs, and the file a scenario failure attaches.

## 5. New decision requiring an ADR: keyed randomness

Rolls derive from hash(seed_id, purpose, tick, site, participants) rather than stream position — **seed_id, not run_id**: A/B comparison runs must *share* the hash seed or every roll differs between them and T4a.2's identical-rolls assertion is vacuous ("run_id" invites giving each run its own value, which breaks the mechanism the ADR exists for); **purpose** is a roll-kind discriminator (encounter / mutation / tell-decision / …) so adding a new roll kind at a site never collides with existing kinds. Justification: sequential streams make every A/B comparison diverge on unrelated re-rolls the moment any code path changes draw count — T4a.2 is unimplementable without this, and every seeded-exact assertion above is brittle without it. Cost: the RNG no longer models one unfolding tape; accepted. Must be implemented before Tier 4 code exists; cheap now, brutal later. Candidate ADR-0009.

## 6. Deferrals (unchanged — do not review as gaps)

Trust-discounted retelling (deliberately deferred; feeds social state into claims and deserves its own rung when wanted); economy (v0.4); LLM tiers (slot behind T2.4's interface); TTS; adapter/hydration seam; save/reload branch exercising.

## 7. Resolved questions (formerly standing)

1. **T2.3 resolution policy: trust-source with strength tiebreak** — decided in-rung (§3, T2.3) with rationale and the rejected alternatives recorded.
2. **Trace placement: sibling stream** sharing the versioned keyframe+delta frame schema — decided in the Tier-1 machinery declaration, per the UI prior-art research (replay tools that work read logs; the canonical log stays semantic).
3. **Rule budget: counted below (§8); currently at the ceiling's edge with headroom only via consolidation.**

## 8. Rule-budget accounting

Named rules the finalized ladder requires, by introducing tier:

| # | Rule | Tier |
|---|------|------|
| 1 | witness-creates-belief | 0 |
| 2 | belief-decay (verbatim/gist curves) | 0 |
| 3 | corroboration (noisy-or, distinct-source) | 0 |
| 4 | shared-claim invariant (one claim per canonical event) | 0 |
| 5 | testimony-transfer (flat retell decay) | 1 |
| 6 | encounter-sampling (co-presence + keyed roll) | 1 |
| 7 | mutation policy (slot mutations keyed to memory strength) | 2 |
| 8 | variant-resolution (trust-source w/ tiebreak) | 2 |
| 9 | rumor-stage transitions (5-state machine) | 2 |
| 10 | dormancy-reactivation | 2 |
| 11 | accumulation-threshold (with hysteresis, per doctrine 3) | 3 |
| 12 | grudge-creation (emotional/evidentiary split) | 3 |
| 13 | grudge-decay | 3 |
| 14 | obligation issue/fulfill/violate (+violation→grudge wiring) | 3 |
| 15 | tell-decision policy (privacy/motive gate) | 3 |
| 16 | reputation-evidence accumulation (observer-local Beta) | 3 |
| 17 | schedule write-back (block insertion/restoration) | 4a |
| 18 | pairwise encounter weighting (avoidance) | 4b |
| 19 | role-vacancy/succession resolution | 5 |

**Count: 19 named rules against the ~20 ceiling.** Consequences: (a) the ceiling is real — v0.3's social-actions tier cannot simply add rules; it must spend the remaining slot deliberately or consolidate (candidates: 9+10 are one state machine and could be counted as one; 4 is an invariant, arguably schema not rule); (b) every rule above must exist in the rule registry (Tier 3 machinery) as a named, toggleable, trace-instrumented object; (c) any proposed rule not on this table is a scope discussion, not a commit.

## 9. Consequences exported to other documents

- **UI spec:** map renders multiple holds from Tier 2 (T2.6); the frame/trace schema is frozen and versioned before UI work begins; the variant tree must render supersession links and the contested-claim confidence dent (T2.3).
- **Fixtures:** carrier NPCs (T2.6) and the victim's kin relationship edges (grudge rules gate on pre-existing edges — the north star's "his children hold grudges" fails for a boring reason if Balgruuf's household edges aren't seeded).
- **Vision:** the build-order outline in vision §6 matches this document's tiers as finalized; the mobile-carriers amendment it promised lives at T2.6/T2.7. On the constitution commit, vision §6's prose outline should name the 4a/4b split explicitly (v2.1 was drafted against pre-split numbering).
- **Schema/ADRs:** T2.3 adds a resolution write path to the claims store that enforces the one-belief invariant at the store level (currently driver-enforced only); ADR-0009 (keyed randomness) uses seed_id + purpose per §5; the trace schema carries the branch key and is always-on per Tier 1.
