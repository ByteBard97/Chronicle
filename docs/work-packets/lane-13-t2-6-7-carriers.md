# Lane 13 — T2.6/T2.7 mobile carriers (Track A, sim substrate)

**Status:** Ready to start immediately. Every prerequisite is verified
landed: death-awareness (T1.2, `3d0f573`), keyed rolls (ADR-0009), the
Tier-2 test idiom (T2.1/T2.2/T2.5), and lane 12's resolution machinery
(`6235a1a`) — whose interaction with this lane is analyzed and pinned
below. The ladder's v0.4 flag is closed: **carriers are pure fixtures,
zero code changes** — if you find a code change is needed, that's a
finding, not an action. No file overlap with lane 15 (dashboard hygiene)
or any other in-flight lane.

**Effort:** medium (fixtures + tests; no engine changes).

## Context

Tier 2's remaining executable rungs. The frozen rung texts
(`docs/scenario-ladder.md:64-65`):

> **T2.6 The carrier.** …Fixtures add 2-3 **mobile carriers** — a
> caravaneer alternating Whiterun/Markarth on a multi-day cycle, a
> courier on a Whiterun/Riverwood/Riften circuit — ordinary NPCs whose
> schedule blocks span holds, making them bridge nodes by construction.
> Scenario: public crime in Whiterun; carrier hears it at the market;
> carrier's travel block completes. Assert: the first Markarth-resident
> belief exists only at a tick ≥ the carrier's arrival; the carrier
> appears in every Markarth evidence chain; no cross-border belief
> exists via any non-carrier path. …**Road decision:** travel blocks
> place the carrier at explicit road locations
> (road_whiterun_markarth)… (the v0.1 fixture keeps roads otherwise
> empty so the border-holds assertion stays exact…).

> **T2.7 Kill the carrier.** The inter-hold twin of T1.2. Same setup;
> the carrier dies (or is removed) before departure. Assert: zero
> beliefs for that claim id held by any non-Whiterun NPC at any later
> tick — the border holds. Then the positive control: a second carrier
> on the same route restores propagation on the next cycle.

T2.4 (motivated mutation) stays parked — it needs faction allegiance
data that doesn't exist yet. These two rungs close Tier 2's executable
surface.

## Read first (in order)

1. `docs/scenario-ladder.md` lines 64–65 — the full rung texts
   (`sed -n '64,65p' docs/scenario-ladder.md | fold -s`), including the
   road decision and its v0.1 scoping parenthetical. Frozen — findings
   to the coordinator.
2. `chronicle/schedule.py` — `ScheduleBlock` (37–51: half-open
   `[start, end)`, `end > start` enforced; `location_id` is a bare
   string, multi-day blocks are just large tick ranges),
   `npcs_present_at` (54–68: groups by string equality, **drops
   singletons**), `sample_encounters` (89–144, keyed rolls).
3. `scenarios/test_tier2_spread_dormancy.py` (46–61 for the inline
   `_cast_schedule()` idiom; 96–113 for `_believer_curve`; 232–237 for
   successive `driver.run()` ranges) and
   `scenarios/test_tier1_transmission_trace.py:104-161` — the
   kill-the-witness template T2.7 mirrors, including the opportunity
   guard (assert co-presence *would* have happened on the raw schedule)
   and the injected-event seq discipline (crime seq=1, kill seq=2).
4. `chronicle/driver.py` — `_deceased` (152–156, 185–186), the
   dead-don't-roll exclusion (476–485), the scripted-wrapper TypeError
   trap (254–263: a scripted `retell` routing to resolution raises —
   pre-check hearer state or use `driver.resolve()`), and
   `mutation_candidates` defaulting to `{}` (141–145).
5. `chronicle/propagate.py` — `teller_and_hearer` (35–41) and
   `conflicting_pair` (44–65, content comparison; deterministic
   lexicographic direction, no roll).
6. `chronicle/fixtures/whiterun_schedule.py` — the fixture-module idiom
   (this lane adds a sibling).
7. `docs/work-packets/reviews/README.md` — governance. Lane agents do
   not commit.

## Pinned design decisions (coordinator-set, 2026-08-23 — deviations come back as findings)

- **No mutation candidates in the carrier fixture.** With `mutation_candidates={}`
  (the Driver default) and a single witnessed story, every belief
  carries identical slots → every both-informed encounter is
  `nothing_salient`, no supersession ever fires, and the rung's three
  T2.6 assertions stay exact. Registering candidates would let a mutated
  variant travel and resolutions re-point beliefs mid-run — the
  "carrier in every Markarth chain" assertion could then break for
  non-carrier winners. Mutation interplay is a later rung's business,
  not this lane's.
- **Roads are explicit and otherwise empty** (the rung's v0.1 scoping):
  travel blocks place carriers at `road_whiterun_markarth` /
  `road_whiterun_riverwood` / `road_riverwood_riften` style ids, and no
  other NPC ever shares a road block in this fixture. Consequence
  (verified): a lone carrier on a road is a singleton at that location,
  `npcs_present_at` drops it, and **no roll records exist en route** —
  the "no cross-border belief via any non-carrier path" assertion is
  exact by construction. The road-leak positive case (two travelers
  meeting en route) is the later fixture the rung text reserves, not
  this lane.
- **The T2.7 second carrier is in the schedule from tick 0**, with
  blocks starting only after the kill tick. `Driver.schedule` is fixed
  at construction — there is no mid-run NPC insertion; presence is
  schedule-blocks only. "Or is removed" has no mechanic: death
  (`NPCDied`) is the only removal path.
- **Deterministic encounters:** pin `encounter_probability=1.0` (the
  T2.2/T1.2 precedent) so the arrival/belief tick assertions are exact,
  not distributional.
- **No new rules.** Rule budget is 19/20 and T2.6/T2.7 add none
  (ladder §8) — keep it that way.
- **This lane is test-only.** A multi-hold *demo run* for the
  dashboard's satellite map is a separate coordinator decision (the
  ui-spec's multi-hold map export is informational here); do not
  generate runs.

## Task

1. **Fixture module** `chronicle/fixtures/carrier_schedule.py`: a
   multi-hold cast + schedule builder in the `whiterun_schedule.py`
   idiom. Contents: a Whiterun cast (market + dragonsreach locations,
   small — this is a propagation-geometry test, not a population test),
   Markarth-resident NPCs who never leave Markarth locations, and two
   carriers: the **caravaneer** (Whiterun market ↔ Markarth, multi-day
   cycle with explicit `road_whiterun_markarth` travel blocks) and, for
   T2.7's positive control, a **second carrier on the same route** whose
   blocks begin after the kill tick. (The courier's Riften circuit is
   optional color — include only if it serves an assertion.) Also
   Riverwood/Riften residents only if the courier is included.
2. **`scenarios/test_tier2_carrier.py` — T2.6 test:** public crime in
   Whiterun witnessed at the market (tick 0, canonical pattern: events
   at tick 0, then `driver.run(0, N)`); carrier hears it; travel block
   completes. Assert the rung's three, exactly:
   - the first Markarth-resident belief exists only at a tick ≥ the
     carrier's arrival tick (checkable from `transmitted` records'
     envelope ticks + `location_id`, `_believer_curve` precedent);
   - the carrier appears in **every** Markarth evidence chain
     (`driver.chain_for` walks; every Markarth believer's chain passes
     through the carrier's belief);
   - no non-Whiterun belief exists via any non-carrier path (no
     `transmitted` record with a Markarth `location_id` whose teller
     isn't the carrier or a Markarth resident informed by the carrier).
   Include the opportunity guard (T1.2 precedent): prove on the raw
   schedule that carrier/Markarth-resident co-presence exists at the
   arrival block, so a propagation bug can't masquerade as no-opportunity.
3. **Same file — T2.7 test:** same setup; the caravaneer dies
   (`inject_event(NPCDied(...))`, kill seq after the crime's seq, T1.2
   template) **before departure**. Assert zero beliefs for the claim id
   held by any non-Whiterun NPC at any later tick (scan all ticks, not
   just the endpoint). **Positive control:** the second carrier's
   post-kill blocks then restore propagation — a Markarth belief exists
   after the second carrier's arrival, with the second carrier in its
   chain.
4. **Suite hygiene:** match the T2.x idiom (seeded, deterministic, no
   wall-clock asserts; `driver.close()`; assertions via `belief_of` /
   `chain_for` / trace scans).

## Acceptance

- `uv run pytest -q` green (183 + your new tests, 0 failed, 0 xfailed);
  `uv run ruff check .` clean.
- T2.6's three assertions and T2.7's negative + positive-control
  assertions all pass as written above — exact ticks, not endpoint-only.
- Zero engine changes: `git diff chronicle/` shows only
  `fixtures/carrier_schedule.py` (new). Any other engine diff is a
  finding, not a delivery.
- No new RNG purposes; no frozen-doc edits; no dashboard edits; no
  runs generated.

## File boundaries

**Create:**
- `chronicle/fixtures/carrier_schedule.py`
- `scenarios/test_tier2_carrier.py`

**Do not touch:**
- everything else in `chronicle/` (zero-code-changes rung — engine gaps
  are findings)
- `docs/` (frozen or coordinator-owned), `dashboard/`, `runs/`,
  other `scenarios/` files

## Conventions

- Match the claims.py/driver.py + T2.x test idiom: named constants with
  rule citations, docstrings naming the rung, seeded determinism.
- **No `git commit`** — the coordinator reviews and commits (governance
  ruling, `docs/work-packets/reviews/README.md`).
- Existing test assertions are immutable; conflicts are findings.
- Report format: what you delivered, acceptance status per criterion
  with command output tails, and a findings list. (One expected finding
  to confirm, not re-derive: lane 12's encounter path never re-hears —
  a carrier re-hearing the same rumor on multiple Whiterun days produces
  only `nothing_salient` rows and no exposure-count updates. That's
  ruled behavior; just confirm your tests don't implicitly depend
  otherwise.)
