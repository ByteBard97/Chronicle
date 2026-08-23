"""Scenario-ladder Tier 2, spread and dormancy rungs (docs/scenario-ladder.md §3 Tier 2).

  - T2.1 Spread -- a public crime with 5 witnesses and a ~25-NPC cast runs
    10 game-days (240 ticks, ADR-0010: 1 tick = 1 gamets = 1 game-hour)
    through the driver's tick loop at the real ENCOUNTER_PROBABILITY.
    Asserted: the EXACT informed-set for the pinned seed and the per-tick
    believer-count curve, as golden regression values -- their role is
    catching too-fast/too-slow drift, per the rung.
  - T2.5 Dormancy and reactivation -- after a small spread, 90 quiet
    game-days (2160 ticks) with nobody co-present. Asserted: stage_at()
    migrates unheard -> heard -> repeated -> dormant exactly as
    claims.py's decay constants dictate (RUMOR_DORMANT_AFTER = 1080 ticks
    sits dormant well before day 90 -- the T2.5 anchor the ADR-0010
    rebaseline used); nothing resurrects unprompted; then a fresh scripted
    retelling (driver.retell) reactivates a dormant rumor -- the positive
    twin, exercising stage_at()'s documented reactivation support.
"""

from chronicle.claims import RUMOR_DORMANT_AFTER
from chronicle.driver import Driver
from chronicle.events import CrimeWitnessed
from chronicle.framelog import FrameLogReader
from chronicle.schedule import ScheduleBlock

ORIGIN = {"kind": "scenario", "detail": "test_tier2_spread_dormancy"}
SAVE_UUID = "whiterun-save-t2"
CLAIM_ID = "claim-market-theft"
CLAIM_SLOTS = {"perpetrator": "unknown", "crime_type": "theft", "location": "whiterun_market"}

# -- T2.1 fixture: a 25-NPC Whiterun cast -----------------------------------
# 5 witnesses to the market theft plus 20 citizens. The day runs in three
# 80-tick phases; every NPC rotates one location per phase, so information
# moves between locations only via NPCs who physically move -- the same
# co-presence-only discipline schedule.py enforces everywhere (rules 2/15).
CAST = tuple(f"citizen_{i:02d}" for i in range(1, 26))
WITNESSES = CAST[:5]
LOCATIONS = ("whiterun_market", "bannered_mare", "dragonsreach_court", "whiterun_plains")
PHASES = ((0, 80), (80, 160), (160, 240))
SPREAD_TICKS = 240  # 10 game-days (ADR-0010).

# Pinned run identity: keyed rolls (ADR-0009) make every run of this seed
# byte-deterministic, which is what licenses the exact golden assertions below.
SPREAD_SEED_ID = "tier2-spread-v1"


def _cast_schedule() -> tuple[ScheduleBlock, ...]:
    blocks = []
    for index, npc_id in enumerate(CAST):
        # The 5 witnesses all stand at the market for phase 0 (the public
        # crime); everyone rotates one location per phase thereafter.
        base = 0 if index < len(WITNESSES) else (index - len(WITNESSES)) % len(LOCATIONS)
        for phase, (start, end) in enumerate(PHASES):
            blocks.append(
                ScheduleBlock(
                    npc_id=npc_id,
                    location_id=LOCATIONS[(base + phase) % len(LOCATIONS)],
                    start_tick=start,
                    end_tick=end,
                )
            )
    return tuple(blocks)


def _witness_the_market_theft(driver: Driver, witness_ids: tuple[str, ...] = WITNESSES):
    """Seed the canonical theft and the witnesses' first-hand beliefs, through the driver.

    All witnesses attach to the same canonical event and the same claim id
    with identical slots -- the shared-claim invariant (rule 21): one Claim,
    five BeliefInstances.
    """
    driver.inject_event(
        CrimeWitnessed(
            tick=0, save_uuid=SAVE_UUID, generation=0, seq=1,
            gamets=0.0, wall_ts=0.0, witness_id=witness_ids[0],
            perpetrator_id="unknown", crime_type="theft", location_id="whiterun_market",
        ),
        origin=ORIGIN,
    )
    theft_event = driver.event_log.lineage(SAVE_UUID, 0)[0]
    theft_key = (theft_event.save_uuid, theft_event.generation, theft_event.seq)
    claim = None
    for npc_id in witness_ids:
        claim, _, _ = driver.witness(
            claim_id=CLAIM_ID,
            belief_id=f"belief-{npc_id}-theft",
            evidence_id=f"evidence-{npc_id}-theft",
            kind="crime_witnessed",
            slots=dict(CLAIM_SLOTS),
            canonical_event_key=theft_key,
            witness_id=npc_id,
            gamets=0.0,
        )
    return claim


def _believer_curve(driver: Driver, claim_id: str, ticks: int) -> tuple[int, ...]:
    """Believer count after each tick in [0, ticks), rebuilt from the trace alone.

    curve[t] = the 5 first-hand witnesses plus one believer per transmitted
    record with tick <= t -- one belief per (holder, claim) is enforced by
    the store, so each transmission is exactly one new believer.
    """
    reader = FrameLogReader(driver.writer.run_dir)
    transmission_ticks = [
        record["tick"]
        for record in reader.records("trace")
        if record["payload"].get("record_type") == "transmitted"
        and record["payload"]["claim_id"] == claim_id
    ]
    return tuple(
        len(WITNESSES) + sum(1 for tick in transmission_ticks if tick <= t)
        for t in range(ticks)
    )


def test_t21_spread_informed_set_and_believer_curve_are_exact_for_the_seed():
    """Ladder T2.1 (Spread): public crime, 5 witnesses, cast of 25, 10 game-days.

    Asserts the EXACT informed-set and the per-tick believer-count curve for
    the pinned seed -- golden regression values whose role is catching
    too-fast/too-slow propagation drift (the rung reserves distributional
    tolerance for math-tier-scale casts, not this one). The mechanism under
    test is encounter-sampling (co-presence + keyed roll, rules 2/15) feeding
    testimony-transfer (flat retell decay, rule 14); nobody here decides who
    talks to whom -- the schedule and the run's keyed rolls do.
    """
    driver = Driver(
        run_id="scenario-t21-spread",
        seed_id=SPREAD_SEED_ID,
        save_uuid=SAVE_UUID,
        generation=0,
        schedule=_cast_schedule(),
        # The real tunable (schedule.py's ENCOUNTER_PROBABILITY = 0.5), not a
        # pinned 1.0: the curve's shape under the actual sampling probability
        # is exactly what the rung wants pinned.
    )
    claim = _witness_the_market_theft(driver)
    driver.run(0, SPREAD_TICKS)
    driver.close()

    informed = frozenset(npc_id for npc_id in CAST if driver.belief_of(npc_id, claim.id) is not None)
    curve = _believer_curve(driver, claim.id, SPREAD_TICKS)
    transitions = tuple((t, count) for t, count in enumerate(curve) if t == 0 or count != curve[t - 1])

    # GOLDEN VALUES for seed "tier2-spread-v1" under ADR-0009 keying (rolls
    # are a pure function of seed_id/purpose/tick/site/participants, so these
    # are byte-deterministic). Pinned from a recorded run of this fixture;
    # any change here means propagation got faster or slower -- the drift
    # tripwire this rung exists to be.
    #
    # All growth lands at tick 0: the 5 witnesses share their phase-0 market
    # location with exactly 5 other citizens (those whose rotation base
    # also lands on the market at phase 0 -- citizens 06/10/14/18/22), so
    # tick 0 alone rolls all 5 witness x 5 target teller/hearer pairs
    # simultaneously; each target's odds of at least one hit among its up-
    # to-5 candidate tellers at p=0.5 already exceeds 96% in that first
    # tick. After phase 0 the informed group's rotation base (0) never
    # revisits another base's location (bases differ by a constant offset
    # every phase), so nobody outside this group is ever reachable again --
    # ADR-0009 keying plus the fixture's own rotation geometry, not a
    # propagation-rate bug.
    golden_informed = frozenset(
        {"citizen_01", "citizen_02", "citizen_03", "citizen_04", "citizen_05",
         "citizen_06", "citizen_10", "citizen_14", "citizen_18", "citizen_22"}
    )
    golden_curve_transitions: tuple[tuple[int, int], ...] = ((0, 10),)
    assert informed == golden_informed
    assert transitions == golden_curve_transitions

    # Fixture-level sanity, independent of the goldens: the witnesses are the
    # story's only seeds, the curve starts at 5 and is monotone, and the
    # endpoint agrees with the store.
    assert set(WITNESSES) <= informed
    assert curve[0] >= len(WITNESSES)
    assert all(curve[t] <= curve[t + 1] for t in range(len(curve) - 1))
    assert curve[-1] == len(informed)


# -- T2.5 fixture: a four-NPC spread, then silence ---------------------------
# ysolda witnesses the theft at the Bannered Mare; at tick 0 she tells hulda
# and saadia (encounter_probability=1.0 pins every co-present roll to fire,
# same pinning as the Tier-1 scenarios); at tick 5 hulda retells to carlotta
# at the market. After tick 10 nobody is co-present with anyone ever again:
# the quiet window is 2160 ticks = 90 quiet game-days (ADR-0010), the rung's
# window. idril never meets a soul -- the rung's "unheard" control.
DORMANCY_QUIET_TICKS = 2160  # 90 quiet game-days (ADR-0010).
DORMANCY_END_TICK = 10 + DORMANCY_QUIET_TICKS

DORMANCY_SCHEDULE = (
    ScheduleBlock(npc_id="ysolda", location_id="bannered_mare", start_tick=0, end_tick=5),
    ScheduleBlock(npc_id="hulda", location_id="bannered_mare", start_tick=0, end_tick=5),
    ScheduleBlock(npc_id="saadia", location_id="bannered_mare", start_tick=0, end_tick=5),
    ScheduleBlock(npc_id="hulda", location_id="whiterun_market", start_tick=5, end_tick=10),
    ScheduleBlock(npc_id="carlotta", location_id="whiterun_market", start_tick=5, end_tick=10),
    ScheduleBlock(npc_id="idril", location_id="whiterun_plains", start_tick=0, end_tick=DORMANCY_END_TICK),
)


def _dormancy_driver() -> Driver:
    driver = Driver(
        run_id="scenario-t25-dormancy",
        seed_id="tier2-dormancy",
        save_uuid=SAVE_UUID,
        generation=0,
        schedule=DORMANCY_SCHEDULE,
        encounter_probability=1.0,
    )
    _witness_the_market_theft(driver, witness_ids=("ysolda",))
    return driver


def _rumor_stage(driver: Driver, npc_id: str, at_gamets: float) -> str:
    belief = driver.belief_of(npc_id, CLAIM_ID)
    assert belief is not None
    return driver.claims.rumor_stage_now(npc_id, CLAIM_ID, belief.variant_id, at_gamets)


def test_t25_dormancy_migration_then_scripted_retelling_reactivates():
    """Ladder T2.5 (Dormancy and reactivation): after spread, 90 quiet days.

    Asserts stage_at() migrates stages per decay (claims.py's rumor-stage
    machine, rule 16): unheard -> heard -> repeated -> dormant as
    RUMOR_DORMANT_AFTER dictates, dormant well before day 90 (the anchor
    ADR-0010's rebaseline was calibrated against); nothing resurrects
    unprompted -- no stage leaves dormant/forgotten without a new hearing;
    then a fresh scripted retelling reactivates a dormant rumor (the positive
    twin, exercising stage_at()'s documented lazy-reactivation support).
    """
    driver = _dormancy_driver()

    # The spread: 10 ticks of co-presence, then the quiet window.
    driver.run(0, 10)
    rumor_states_after_spread = {
        npc_id: driver.claims.rumor_state(npc_id, CLAIM_ID, driver.belief_of(npc_id, CLAIM_ID).variant_id)
        for npc_id in ("ysolda", "hulda", "saadia", "carlotta")
    }
    driver.run(10, DORMANCY_END_TICK)

    # The spread did what the fixture says: ysolda told at tick 0 (repeated),
    # hulda heard at 0 and told at 5 (repeated), saadia heard at 0, carlotta
    # heard at 5. Last-activity ticks: ysolda 0, hulda 5, saadia 0, carlotta 5.
    assert rumor_states_after_spread["ysolda"].stage == "repeated"
    assert rumor_states_after_spread["ysolda"].last_told == 0
    assert rumor_states_after_spread["hulda"].stage == "repeated"
    assert rumor_states_after_spread["hulda"].last_told == 5
    assert rumor_states_after_spread["saadia"].stage == "heard"
    assert rumor_states_after_spread["carlotta"].stage == "heard"

    # "unheard" is the absence of a RumorState (claims.py's RumorState
    # docstring): idril was never co-present with an informed NPC.
    assert driver.belief_of("idril", CLAIM_ID) is None
    assert driver.claims.rumor_state("idril", CLAIM_ID, None) is None

    # heard/repeated -> dormant exactly at RUMOR_DORMANT_AFTER = 1080 ticks of
    # inactivity (rule 16): at last_activity + 1080 the stored stage still
    # reads; one tick later the rumor is dormant. Dormancy onset lands at
    # ~45 quiet game-days -- well before the 90-day window closes, the T2.5
    # anchor ADR-0010's rebaseline pinned RUMOR_DORMANT_AFTER against.
    quiet = RUMOR_DORMANT_AFTER  # 1080 ticks: ~45 quiet game-days.
    assert _rumor_stage(driver, "saadia", quiet) == "heard"
    assert _rumor_stage(driver, "saadia", quiet + 1) == "dormant"
    assert _rumor_stage(driver, "ysolda", quiet) == "repeated"
    assert _rumor_stage(driver, "ysolda", quiet + 1) == "dormant"
    assert _rumor_stage(driver, "carlotta", 5 + quiet) == "heard"
    assert _rumor_stage(driver, "carlotta", 5 + quiet + 1) == "dormant"
    assert _rumor_stage(driver, "hulda", 5 + quiet) == "repeated"
    assert _rumor_stage(driver, "hulda", 5 + quiet + 1) == "dormant"

    # At the end of the 90-day window every informed holder is dormant --
    # and dormant, not forgotten: gist decay (GIST_DECAY_HALF_LIFE = 1440
    # ticks) has not eroded gist_strength below RUMOR_FORGOTTEN_GIST_THRESHOLD
    # yet, so stage_at() never reaches its "forgotten" branch inside the window.
    for npc_id in ("ysolda", "hulda", "saadia", "carlotta"):
        for at in (1200, 1600, DORMANCY_END_TICK - 1):
            assert _rumor_stage(driver, npc_id, at) == "dormant"

    # "forgotten" is real, just later: queried lazily (rule 19 -- no ticks
    # need to run) far enough out, carlotta's twice-retold gist decays under
    # the threshold and stage_at() answers "forgotten". Wide margins around
    # the ~6016-tick crossing so the assertion keys on the constants, not on
    # floating-point boundary luck.
    assert _rumor_stage(driver, "carlotta", 6000) == "dormant"
    assert _rumor_stage(driver, "carlotta", 6100) == "forgotten"

    # Nothing resurrects unprompted: the quiet window contains no hearing or
    # telling at all -- the trace holds no transmitted/belief_formed record
    # past tick 10, and every RumorState is byte-identical to its post-spread
    # snapshot, so no stage could have left dormant/forgotten without a new
    # hearing (there was none).
    reader = FrameLogReader(driver.writer.run_dir)
    quiet_activity = [
        record
        for record in reader.records("trace")
        if record["tick"] >= 10
        and record["payload"].get("record_type") in ("transmitted", "belief_formed")
    ]
    assert quiet_activity == []
    for npc_id, snapshot in rumor_states_after_spread.items():
        belief = driver.belief_of(npc_id, CLAIM_ID)
        assert driver.claims.rumor_state(npc_id, CLAIM_ID, belief.variant_id) == snapshot

    # The positive twin: a fresh scripted retelling reactivates a dormant
    # rumor. saadia is dormant at the window's close; she retells the story
    # to idril at gamets 2170, and stage_at() reads her as "repeated" again
    # immediately -- the lazy-derivation discipline means no record had to
    # predict the reactivation in advance (claims.py's RumorState docstring).
    saadia_belief = driver.belief_of("saadia", CLAIM_ID)
    assert _rumor_stage(driver, "saadia", DORMANCY_END_TICK - 1) == "dormant"
    driver.retell(
        claim=driver.claim(CLAIM_ID),
        parent_variant=driver.variant(saadia_belief.variant_id),
        variant_id="variant-reactivation",
        belief_id="belief-idril-theft",
        evidence_id="evidence-idril-theft",
        teller_id="saadia",
        teller_belief=saadia_belief,
        hearer_id="idril",
        gamets=float(DORMANCY_END_TICK),
    )

    # saadia reactivates: dormant -> repeated on the strength of the retelling
    # alone, with her dormancy clock restarted (last_told = 2170).
    assert _rumor_stage(driver, "saadia", DORMANCY_END_TICK) == "repeated"
    assert _rumor_stage(driver, "saadia", DORMANCY_END_TICK + quiet) == "repeated"
    assert _rumor_stage(driver, "saadia", DORMANCY_END_TICK + quiet + 1) == "dormant"

    # idril leaves "unheard" for the first time -- a new hearing, the only
    # thing allowed to move a stage out of dormant/forgotten territory.
    idril_belief = driver.belief_of("idril", CLAIM_ID)
    assert idril_belief is not None
    assert _rumor_stage(driver, "idril", DORMANCY_END_TICK) == "heard"

    # The reactivated chain walks back through saadia to ysolda's witnessed
    # observation (ADR-0007): the dormant holder's memory, not a new event,
    # grounds the retelling.
    chain = driver.chain_for(idril_belief.id)
    assert [belief.holder_id for belief, _ in chain] == ["idril", "saadia", "ysolda"]
    assert chain[0][1].evidence_type == "reported"
    assert chain[-1][1].evidence_type == "witnessed"
    driver.close()
