# T6 north-star fixture design

Status: design proposal for owner review (lane 45 deliverable). No
code, no fixture code. Every code/schema claim carries a file:line
citation verified against `0261eec`. Structured so each **Decision**
section lifts into a fixture-build packet, same shape as the
Tier-3/4a/4b/5 design docs; open points for the owner are collected in
§7. Decisions here are prefixed **N** (north star).

Sources: `docs/vision-v2.2.md` §2 (verbatim), §6; `docs/scenario-ladder.md`
Tier 6 intro (line 102), §9 (line 160); `docs/ui-spec.md` §5 (the
stranger walkthrough); `chronicle/fixtures/whiterun_relationships.py`;
`chronicle/fixtures/carrier_schedule.py`; `scenarios/run_carrier_demo.py`,
`run_tier3_demo.py`, `run_mourning_demo.py`; every landed design doc
(Tier 3/4a/4b/5) for the authoring disciplines this fixture must satisfy.

---

## 0. What T6 actually asks for

Tier 6 adds **no new mechanism** (`docs/scenario-ladder.md:102-104`):
"if Tiers 0–5 are green and T6 fails, the mechanisms don't compose."
The acceptance test is the vision's own north star
(`docs/vision-v2.2.md:16-22`): the player assassinates Jarl Balgruuf.
Four beats, verbatim:

1. **Succession** — resolves through the court's actual relationship
   and faction state, not a scripted replacement; different prior
   relationships produce a different Jarl.
2. **Grief and grudge** — his household mourns on their calendars, not
   in a bark; his children hold grudges with the killing as their
   evidence; the mourners' rerouted days change who they meet and
   therefore what they hear.
3. **The rumor** — travels at the speed people move, along kin and
   trade and tavern edges, carried beyond the hold by caravaneers and
   couriers, and it mutates: a Stormcloak blacksmith retells it as an
   Imperial plot; three weeks later a Markarth merchant greets you with
   a confidently-wrong thirdhand version, every hop showable.
4. **The ripple** — guard cohesion, market confidence, and faction
   posture shift as **aggregates over what individuals actually
   believe** — never a global flag. Tier 6's own discipline
   (`docs/scenario-ladder.md:104`): "collective fear... derived on
   read, with drill-down to contributing beliefs, never cached, and
   never an input to any behavior decision. The moment any rule keys
   off the aggregate, it becomes a feedback mechanism requiring its own
   tier." This fixture must not tempt that — the aggregate is a *view*,
   and nothing in this doc proposes a rule that reads one.

§9's fixture consequences (`docs/scenario-ladder.md:160`) name the two
non-obvious requirements explicitly: carrier NPCs (T2.6, landed) and
**the victim's kin relationship edges** — "the north star's 'his
children hold grudges' fails for a boring reason if Balgruuf's
household edges aren't seeded." This doc exists to make sure nothing
else fails for an equally boring reason.

---

## 1. The cast (question 1)

### Decision N1 — six groups, ~18 NPCs, built as an EXTENSION of the existing `carrier_schedule()` fixture, not a replacement

`chronicle/fixtures/carrier_schedule.py` already seeds exactly the
cross-hold backbone T6's rumor beat needs: `WHITERUN_CAST = ("belethor",
"carlotta", "ysolda")` at the market (`:40`), `CARAVANEER`/
`RELIEF_CARAVANEER` on a Whiterun↔Markarth cycle via
`ROAD_WHITERUN_MARKARTH` (`:38,70-78`), and three `MARKARTH_RESIDENTS`
(`:41`). **Recommendation: the north-star fixture module imports and
extends this schedule** (the same "one shared edge list, multiple
seeders" pattern `whiterun_relationships.py:41-58` already uses for
relationships) rather than duplicating it — every prior demo run that
depends on `carrier_schedule()`'s exact timings
(`run_carrier_demo.py`) stays untouched, and the cross-hold plumbing
is proven machinery, not a fresh risk.

Six groups, sized against the ladder's own precedent ("18,007 trace
rows / 7.9 MB for a 25-NPC 10-game-day run," cited in the trace-volume
figure decision this series already measured):

| Group | Cast | Role in the composition |
|---|---|---|
| **Household** | jarl_balgruuf (victim), 2 kin (mourn + grudge — the T4a/T3.2 double beat) | Grief, grudge, mourning reroute |
| **Court** | 3 succession candidates with varying relationship strength to `whiterun_court` (reusing `whiterun_relationships.py:36-37`'s `proventus`/`irileth` edges plus one new candidate) | Succession (Tier 5) |
| **Market** | `carrier_schedule.py`'s existing `WHITERUN_CAST` (belethor, carlotta, ysolda) + 2 guards | Propagation density, the ripple's market-confidence aggregate |
| **Carriers** | `CARAVANEER`/`RELIEF_CARAVANEER` (existing) + 1 new courier on a *different* route (the ladder's T2.6 fixture text names "a caravaneer... a courier on a Whiterun/Riverwood/Riften circuit" as the two-carrier precedent — this fixture only strictly needs the Markarth leg for T6, but a second route costs nothing and matches the vision's "beyond the hold... caravaneers and couriers," plural) | Cross-hold spread |
| **Temple** | 1 priest (mourning destination) | Tier 4a |
| **Markarth** | `carrier_schedule.py`'s existing `MARKARTH_RESIDENTS` (3) + 1 faction-aligned NPC (the mutated variant's eventual holder — the vision's own "a Markarth merchant greets you with a confidently-wrong thirdhand version") | The mutation's landing site |

Total: 2 (household) + 3 (court, one overlapping the household's
narrative as Balgruuf's own court) + 5 (market) + 3 (carriers) + 1
(temple) + 4 (Markarth) = **~18 named NPCs**, comfortably inside the
25-NPC precedent with room for the fixture author to add flavor
without hitting a volume concern. Guards (2, market group) are the
ripple's guard-cohesion aggregate population — deliberately undifferentiated,
since the aggregate reads their *beliefs*, not any special-cased "guard"
mechanism.

---

## 2. The relationship/faction graph (question 2)

### Decision N2 — kinship for household, faction/shared_employer for court and factions, and a concrete flip that proves the fixture-carried counterfactual

**Household kin edges** (the §9 consequence, non-negotiable): both
household NPCs get `basis="kinship"` edges to `jarl_balgruuf`
(`form_relationship`, the exact `whiterun_relationships.py` idiom, no
`basis_id` needed for kinship per that fixture's own precedent). This
is what makes both the mourning trigger (design doc
`tier-4a-schedule-write-back.md` §3, Decision T5: "the newly-informed
holder has a kinship edge to the deceased") and the grudge trigger
(rule 8's gate, `social.py:216-236`) fire at all — omit either edge and
that NPC silently can't mourn or grudge, the exact "boring failure"
§9 warns about.

**Court edges, decidable from the graph (Tier 5's own requirement,
design doc `tier-5-roles-and-vacancy.md` §3, Decision S5).** Reusing
`whiterun_relationships.py:36-37`'s existing `shared_employer` edges to
`jarl_balgruuf` under `basis_id="whiterun_court"` (proventus 0.85,
irileth 0.95) plus one **new** candidate at, say, strength 0.60 gives
three ranked candidates. **The concrete flip, stated plainly so the
fixture author can just build it:**

- **Fixture A** (as `whiterun_relationships.py` stands today): irileth
  (0.95) > proventus (0.85) > new candidate (0.60) → **irileth
  succeeds**.
- **Fixture B** (one edge changed — proventus's strength raised to,
  say, 0.97): proventus (0.97) > irileth (0.95) > new candidate (0.60)
  → **proventus succeeds**.

Same `seed_id`, same everything else, one relationship `strength`
value flipped — exactly Tier 5's design doc S5's "fixtures carry the
counterfactual, not seeds," demonstrated concretely rather than left
abstract. **This doc does not decide which fixture ships as T6's
canonical one** — that's the implementing lane's call — but it commits
to both being buildable from the same base graph with a one-line diff,
which is the actual acceptance bar Tier 5's design set.

**Faction edges for T2.4** (§5 below): two opposing factions,
`"stormcloaks"` and `"empire"` — the vision's own example
(`docs/vision-v2.2.md:20`, "a Stormcloak blacksmith retells it as an
Imperial plot"). One market or carrier NPC gets `basis="faction",
basis_id="stormcloaks"`; another gets `basis_id="empire"`. No new
relationship basis needed — `"faction"` is already in
`ALLOWED_RELATIONSHIP_BASES` (`social.py:55`).

**Rivalry/obligation edges**: not required by any T6 beat this doc's
sources name. Not seeded — a north-star fixture that includes state
nothing reads is exactly the kind of accidental complexity every
"caller-supplies-context, no mapping means zero effect" design in this
series has avoided. Flagged as open point O1 in case the owner wants
an obligation-refusal beat folded in for T3.3 coverage (not asked for
by any source this doc cites).

---

## 3. The claim/event scripts (question 3)

### Decision N3 — one canonical anchor, deceased-naming slots throughout, and the privacy/reputation mappings each landed tier already defines the shape of

**The assassination.** `NPCDied(npc_id="jarl_balgruuf", cause=
"assassination", ...)`, witnessed independently by the household (kin,
mourning/grudge-eligible) and at least one court member. **T0.4's
disagreeing witness, exercised in anger** (per the packet's own
framing): a *second* independent witness at the same scene reports a
conflicting detail (e.g. the murder weapon — "dagger" vs. "poison," the
exact slot `docs/ui-spec.md:135`'s stranger-walkthrough example names:
"drill provenance from belief to dagger through the mutation"). This
gives T2.3's evidence-type-ordering resolution something real to
resolve (two witnessed-tier beliefs, strength tiebreak) right at the
source, before the story ever leaves Dragonsreach — the north star
exercising a mechanism the ladder's own T0.4/T2.3 rungs already proved
in isolation.

**Deceased-naming slot** (lane 33/36's F3/O1 convention, mandatory):
`slots={"deceased": "jarl_balgruuf", "weapon": "dagger", ...}`, with
`mourning_triggers = {"npc_death": "deceased"}` registered exactly as
`run_mourning_demo.py` already does.

**Mutation candidates** (rule 7, ordinary T2.2 machinery — zero new
code): `mutation_candidates[("npc_death", "weapon")] = ("a poisoned
blade", "a hired crossbow", "witchcraft")` — the slot the stranger
walkthrough's provenance drill-down needs to show changing hop-to-hop.
This is the SAME mechanism `run_carrier_demo.py:36-39` already
exercises; nothing new to design.

**Privacy/motive mapping** (rule 15, lane 23's shape): the assassination
itself is exactly the kind of secret a court insider might be
kin-motivated to keep quiet about a suspect's identity — if the fixture
wants a T3.4 beat woven in, `claim_privacy = {"npc_death": "deceased"}`
plus a kinship edge from one holder to a NAMED suspect (not the victim)
gates their silence about *that* detail. **Optional, not required by
any of this doc's four numbered beats** — flagged as O2, since adding
it means a second, distinct claim (accusation of a specific suspect,
separate from the death claim itself) rather than reusing the death
claim's own privacy.

**Reputation-relevance mapping** (rule 16, lane 26's shape) for the
ripple's aggregates: register `("npc_death", "deceased")`-adjacent
context so guards/market NPCs who become informed accrue
`reputation_updated` rows in a `"security"`/`"civic"` context — **this
is the derivation substrate the read-only aggregate (§0) reads**, not a
new mechanism. The aggregate itself (guard cohesion as some function
over guards' reputation/belief state) is a **dashboard-side derived
view** (M6+, out of this doc's engine scope) — this doc's job is only
to make sure the underlying `reputation_updated` rows exist for it to
read.

---

## 4. The assertion outline (question 4)

Outline only — the T6 lane (after Tier 5 lands) writes the actual test.
Per beat:

1. **Succession**: `driver.roles.holder_of("steward_of_whiterun")` (or
   whichever role the fixture casts as vacant — the vision text says
   "the Jarl," so the role model may need a `"jarl_of_whiterun"` role
   distinct from Tier 5's rung's own steward example) resolves to the
   fixture-predicted candidate; re-run with Fixture B (§2), assert the
   different candidate, same `seed_id` — Tier 5's own counterfactual,
   composed here rather than invented fresh.
2. **Mourning reroute**: both household NPCs' `schedule_rewrite` events
   exist (lane 36's mechanism, unmodified); at least one informs
   someone (the priest, or a court member) only reachable via the
   reroute — `run_mourning_demo.py`'s own verified chain
   (erik → priest) is the existing proof this composes; T6 just needs
   the SAME household also holding a grudge (next point) simultaneously,
   proving the two Tier-3/4a mechanisms don't interfere.
3. **Grudge**: `driver.social.grudges_of(kin_id)` contains a grudge
   whose `source_belief_id` traces to the assassination belief
   (rule 8/12's existing machinery, `form_grudge`) — the vision's
   "his children hold grudges with the killing as their evidence,"
   asserted by walking the exact evidence chain ADR-0007 promises.
4. **The mutated variant survives to Markarth**: `trace`'s variant
   lineage for the death claim shows the `"weapon"` slot mutated at
   some hop before the carrier's Markarth arrival tick, and the
   Markarth resident's held belief carries the mutated value, not the
   original — `run_carrier_demo.py`'s own carrier mechanism plus the
   ordinary mutation machinery, composed, not new.
5. **T2.4 (if built, §5)**: the Stormcloak-aligned teller's retelling
   substitutes the empire-blaming candidate (or vice versa),
   deterministically — "substitution direction matches allegiance,"
   the ladder's own assertion text, verbatim.
6. **The read-only aggregate**: a dashboard-side check (not an engine
   assertion) that the aggregate view is *correct* (matches a
   hand-computed function over the reconstructed beliefs at T) and
   that **nothing in the engine's rule set reads it** — an architectural
   assertion (`grep`-style: no rule's `evaluate()` inputs reference an
   aggregate) as much as a behavioral one.

---

## 5. T2.4's unpark (question 5)

### Decision N4 — the fixture provides the faction data; the rule mechanism itself needs one small, separately-designed engine hook, not bundled into this doc

T2.4 has been parked since v0.1 specifically for lack of faction
allegiance data (`claude-sessions/2026-08-23_handoff-kimi-track-a.md`'s
own framing, echoed in this packet's context section: "T2.4
motivated-mutation placeholder — needs faction allegiance data").
§2's `stormcloaks`/`empire` edges (Decision N2) remove that blocker at
the *data* level. But "substitution direction matches allegiance"
cannot be satisfied by today's `_decide_mutation`
(`driver.py:1062-1117`): `mutation_candidates` is a single
`(claim_kind, slot) -> Sequence[str]` mapping shared by every teller,
and the value roll (`MUTATION_VALUE`, `:1113-1117`) picks uniformly —
there is no teller-identity input anywhere in that function today, so
no fixture data alone can make the substitution *deterministic by
allegiance* without a code change.

**Minimal proposed hook** (named here so the fixture doc is buildable,
but explicitly NOT a full design — this deserves its own micro
design-decision before an implementing lane touches `_decide_mutation`,
the same way Tier 3/4a/4b/5 each got their own doc rather than being
folded into a fixture spec): a new caller-supplied mapping,
`allegiance_candidates: Mapping[tuple[str, str, str], str]` keyed
`(claim_kind, slot, faction_basis_id)` → the single deterministic
value. In `_decide_mutation`, after the existing slot is chosen
(`:1107`), check whether the teller holds a `"faction"` relationship
whose `basis_id` has an entry for `(claim.kind, slot)`; if so, use that
value directly (`roll_key=None` for the value roll — the same
"deterministic decline, no roll" idiom rule 15's stage 1 already
established, `TellDecisionRule`, `rules.py`) instead of drawing
`MUTATION_VALUE`. Unmapped tellers keep today's uniform-random
behavior unchanged — migration-safe by construction, the same
guarantee every caller-supplies-context mapping in this codebase makes.

**Recommendation:** route this hook through its own small design
review (not this doc, not silently folded into the fixture-build lane)
before implementation — it's a real, if small, change to a live,
tested code path (`_decide_mutation` has direct coverage in the Tier-2
suite), and deserves the same citation-and-rationale treatment this
series gives every engine change, however small (lane 39's
`StatusChanged` is the right-sized precedent: one focused micro-lane,
not a rider on a bigger doc).

---

## 6. The demo-run twin (question 6)

### Decision N5 — one fixture, two consumers: the T6 test and the M7 stranger-walkthrough demo run

The stranger walkthrough (`docs/ui-spec.md:135`) needs, present in the
data, exactly the beats §4 already outlines: the assassination
findable on the timeline; the rumor overlay's carrier hop scrubbable;
a Markarth believer with a visible variant badge; the variant tree
showing which slot changed at which hop; a provenance drill from belief
to the mutated weapon slot; a URL that reproduces the view. **Nothing
here is demo-specific** — every one of those is a direct consequence of
§3's claim scripts and §4's assertions, which is the point: the same
fixture module (§1's extension of `carrier_schedule()`) backs both
`scenarios/test_north_star.py` (T6, once Tier 5 lands) and
`scenarios/run_north_star_demo.py` (the M7 producer), the same
one-fixture-many-consumers relationship `run_tier3_demo.py` already has
with its own rung tests. The only demo-specific concern is run length:
the walkthrough needs "ten minutes, zero coaching" of *watchable*
material, which argues for the same multi-game-day `END_TICK` scale
`carrier_schedule.py:61`'s `END_TICK = 240` (10 game-days) already
uses, not a compressed unit-test-scale run — flagged as O3 since it's a
producer-authoring choice, not a fixture-design one.

---

## 7. Open points for the owner

- **O1 — no obligation/rivalry beat.** This doc doesn't seed one; T3.3
  isn't named by any of this doc's sources as a north-star requirement.
  Confirm before the fixture build lane treats its absence as
  settled rather than an oversight.
- **O2 — the optional T3.4 (tell-decision) beat** (§3): a second,
  suspect-naming claim with its own privacy mapping, distinct from the
  death claim itself. Adds real cast/script complexity for a beat none
  of the four numbered vision beats explicitly asks for — recommend
  deferring unless the owner specifically wants T3.4 represented in the
  composition.
- **O3 — demo run length vs. test run length.** The M7 producer likely
  wants the full multi-day `carrier_schedule.py` timescale; the T6 test
  itself may want a compressed version for CI speed. Whether these are
  the *same* fixture module with a run-length parameter, or two
  fixture variants, is a producer/test-authoring decision for the
  implementing lane, not resolved here.
- **O4 — which role the vision's "Jarl" maps to in Tier 5's model.**
  Tier 5's design doc (`tier-5-roles-and-vacancy.md`) illustrates its
  mechanism with a "steward" rung example; the vision's own beat is
  about the **Jarl** specifically. This doc assumes a `Role(id=
  "jarl_of_whiterun", institution_id="whiterun_court", ...)` distinct
  from any steward role, but the implementing lane should confirm the
  exact role roster (does Balgruuf's household also include an existing
  steward who *isn't* who dies? `whiterun_relationships.py` already
  has `proventus` as steward-flavored via `shared_employer` to
  `jarl_balgruuf` — worth deciding whether Proventus is cast as sitting
  steward, succession candidate, or both).

## 8. Findings

- **F1 — none of the packet's premises were wrong.** `carrier_schedule.py`
  and `whiterun_relationships.py`'s existing fixture data, the T0.4/
  T2.3 disagreeing-witness mechanism, every landed tier's
  caller-supplies-context mapping shape, and the ui-spec's exact
  stranger-walkthrough step list all check out as cited.
- **F2 — T2.4's unpark needs real (if small) engine work, not just
  fixture data**, contrary to how the packet's question 5 could be read
  ("whether this fixture's faction data finally exercises the
  placeholder" almost suggests data alone might suffice). It doesn't —
  `_decide_mutation` has no teller-identity input today. Named as a
  separate, small, explicitly-NOT-designed-here hook (§5) rather than
  either silently expanding this doc's scope to a full engine design or
  silently dropping T2.4 from the composition.
- **F3 — the existing `carrier_schedule()`/`whiterun_relationships.py`
  fixtures cover far more of the north star than a fresh build would
  suggest.** The cross-hold backbone, the court's succession-decidable
  edges, and the T2.2 mutation mechanism are all already-proven
  machinery; this doc's real contribution is the household kin edges
  (§9's named non-obvious requirement), the faction edges for T2.4, and
  assembling the pieces into one coherent cast rather than inventing
  new mechanics.
- **F4 — the read-only aggregate (§0, §4 beat 6) is the one beat this
  doc cannot fully spec**, because the aggregate itself is dashboard-
  side (M6+), not an engine concern this fixture directly produces.
  What this fixture guarantees is the *substrate* (reputation/belief
  records the aggregate would read); the aggregate's own correctness
  is a future lane's assertion, not this one's.
