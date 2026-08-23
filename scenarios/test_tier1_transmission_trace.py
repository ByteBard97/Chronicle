"""Scenario-ladder Tier 1: one-hop transmission + the derivation trace (docs/scenario-ladder.md §3 Tier 1).

The new sim mechanism at this tier is testimony transfer through a sampled
encounter -- pure transmission only (tell-decision policy is Tier 3); the new
infrastructure mechanism is the derivation trace, asserted against directly
in T1.3. All three rungs run through the driver's tick loop over an inline
schedule fixture: nobody in these tests decides who talks to whom -- the
schedule and the run's keyed rolls (ADR-0009) do.

  - T1.1 Tell -- witness and neighbor share a location block; the listener's
    belief exists, its source chain is [witness], and its confidence is the
    witness's confidence x the flat retell constant, exactly.
  - T1.2 Kill the sole witness -- the witness dies before any encounter;
    zero beliefs for that claim id held by anyone else at any later tick.
  - T1.3 Non-encounter is recorded -- a co-present pair whose roll fails
    leaves a negative encounter_rolled record in the trace, with roll value
    vs. threshold, read back via FrameLogReader.
"""

from chronicle.claims import RETELL_CONFIDENCE_DECAY, WITNESS_CONFIDENCE
from chronicle.driver import Driver
from chronicle.events import CrimeWitnessed, NPCDied
from chronicle.framelog import FrameLogReader
from chronicle.schedule import ScheduleBlock, npcs_present_at

ORIGIN = {"kind": "scenario", "detail": "test_tier1_transmission_trace"}

# The shared location block for this tier's two-NPC fixtures: witness and
# neighbor are co-present at the Bannered Mare, so the tick loop's encounter
# sampling (schedule.py, rules 2/15) is the only thing that can move the story.
WITNESS_BLOCK = ScheduleBlock(npc_id="irileth", location_id="bannered_mare", start_tick=0, end_tick=48)
NEIGHBOR_BLOCK = ScheduleBlock(npc_id="hulda", location_id="bannered_mare", start_tick=0, end_tick=48)


def _witness_the_theft(driver: Driver):
    """Seed the canonical theft and irileth's witnessed belief about it, through the driver."""
    driver.inject_event(
        CrimeWitnessed(
            tick=0, save_uuid="whiterun-save-1", generation=0, seq=1,
            gamets=0.0, wall_ts=0.0, witness_id="irileth",
            perpetrator_id="unknown", crime_type="theft", location_id="bannered_mare",
        ),
        origin=ORIGIN,
    )
    theft_event = driver.event_log.lineage("whiterun-save-1", 0)[0]
    theft_key = (theft_event.save_uuid, theft_event.generation, theft_event.seq)
    claim, _, _ = driver.witness(
        claim_id="claim-theft",
        belief_id="belief-irileth-theft",
        evidence_id="evidence-irileth-theft",
        kind="crime_witnessed",
        slots={"perpetrator": "unknown", "crime_type": "theft", "location": "bannered_mare"},
        canonical_event_key=theft_key,
        witness_id="irileth",
        gamets=0.0,
    )
    return claim


def test_t11_tell_transmits_the_story_one_hop_through_a_sampled_encounter():
    """Ladder T1.1 (Tell): witness and neighbor share a location block -- the listener's
    belief exists, its source chain is [witness], and its confidence is the witness's
    confidence x 0.8 exactly (testimony-transfer rule: flat retell decay,
    claims.py's RETELL_CONFIDENCE_DECAY; trust-discounted retelling is deliberately
    deferred per the ladder's T1.1 note).
    """
    driver = Driver(
        run_id="scenario-t11-tell",
        seed_id="tier1-tell",
        save_uuid="whiterun-save-1",
        generation=0,
        schedule=(WITNESS_BLOCK, NEIGHBOR_BLOCK),
        # Every co-present qualifying pair encounters, so the outcome is
        # deterministic and assertable (same pinning as
        # test_jarl_death_encounter_driven_propagation.py).
        encounter_probability=1.0,
    )
    claim = _witness_the_theft(driver)

    driver.run(0, 24)

    # The listener's belief exists -- formed by nobody's hand but the
    # schedule's and the tick loop's.
    hulda_belief = driver.belief_of("hulda", claim.id)
    assert hulda_belief is not None

    # Source chain = [witness]: one hop -- hulda heard it from irileth, who
    # witnessed it. No intermediaries.
    chain = driver.chain_for(hulda_belief.id)
    assert len(chain) == 2
    assert chain[0][1].evidence_type == "reported"
    assert chain[0][1].source_id == "irileth"
    assert chain[1][0].holder_id == "irileth"
    assert chain[1][1].evidence_type == "witnessed"

    # Confidence = witness confidence x the retell constant, exactly: the
    # teller's stored confidence is the direct-observation baseline (decay is
    # read-time, so nothing eroded before the tick-0 retelling), and the flat
    # 0.8 applies with no trust weighting.
    assert hulda_belief.confidence == WITNESS_CONFIDENCE * RETELL_CONFIDENCE_DECAY
    driver.close()


def test_t12_killing_the_sole_witness_before_any_encounter_stops_the_story():
    """Ladder T1.2 (Kill the sole witness): the player kills the witness before any
    encounter -- zero beliefs for that claim id held by anyone else at any later tick
    (scoped to the theft claim, so the killing itself, if witnessed, doesn't vacuously
    break the assertion). A dead NPC must not testify.
    """
    driver = Driver(
        run_id="scenario-t12-kill-the-witness",
        seed_id="tier1-kill-the-witness",
        save_uuid="whiterun-save-1",
        generation=0,
        # Irileth is alone in Dragonsreach while the crime happens; the player
        # kills her before her tavern block with hulda begins -- before any
        # encounter the story could travel through.
        schedule=(
            ScheduleBlock(npc_id="irileth", location_id="dragonsreach", start_tick=0, end_tick=10),
            ScheduleBlock(npc_id="irileth", location_id="bannered_mare", start_tick=10, end_tick=58),
            ScheduleBlock(npc_id="hulda", location_id="bannered_mare", start_tick=0, end_tick=58),
        ),
        encounter_probability=1.0,
    )
    claim = _witness_the_theft(driver)
    driver.inject_event(
        NPCDied(
            tick=5, save_uuid="whiterun-save-1", generation=0, seq=2,
            gamets=5.0, wall_ts=5.0, npc_id="irileth",
            cause="killed by the player", killer_id="player", location_id="dragonsreach",
        ),
        origin=ORIGIN,
    )

    driver.run(0, 58)

    reader = FrameLogReader(driver.writer.run_dir)
    trace = list(reader.records("trace"))

    # The schedule co-presence was real: irileth's tavern block overlaps
    # hulda's for ticks 10..58, so the story had every mechanical opportunity
    # to travel had she lived -- the rung's zero-beliefs assertion below is
    # not an artifact of a fixture where the pair never met. (The guard
    # asserts opportunity, not fired encounters: the dead are excluded before
    # any roll, so no encounter_rolled record ever names her -- that exclusion
    # is the mechanism under test.)
    for tick in (10, 30, 57):
        present = npcs_present_at(driver.schedule, tick)
        assert set(present["bannered_mare"]) == {"irileth", "hulda"}

    # The rung: zero beliefs for that claim id held by anyone else at any
    # later tick -- no transmission of the theft story ever fired, and hulda
    # never holds it.
    transmissions = [
        record for record in trace
        if record["payload"].get("record_type") == "transmitted"
        and record["payload"]["claim_id"] == claim.id
    ]
    assert transmissions == []
    assert driver.belief_of("hulda", claim.id) is None
    driver.close()


def test_t13_a_failed_encounter_roll_is_recorded_in_the_trace():
    """Ladder T1.3 (Non-encounter is recorded): a co-present pair whose roll fails --
    every roll here is a rolled-against negative (encounter_probability=0.0) -- leaves
    a negative encounter_rolled record in the derivation trace with encountered: false
    and roll value vs. threshold, keyed per ADR-0009; read back via FrameLogReader
    (encounter-sampling rule + the trace's negative-results-are-first-class contract,
    frame-log schema §4).
    """
    driver = Driver(
        run_id="scenario-t13-non-encounter",
        seed_id="tier1-non-encounter",
        save_uuid="whiterun-save-1",
        generation=0,
        schedule=(WITNESS_BLOCK, NEIGHBOR_BLOCK),
        # 0.0: every keyed roll is a rolled-against negative -- the pair is
        # co-present for 24 ticks and never once encounters.
        encounter_probability=0.0,
    )
    claim = _witness_the_theft(driver)
    driver.run(0, 24)
    driver.close()

    # The trace is read back from the log alone, through FrameLogReader -- the
    # same path the dashboard's encounter feed will take.
    reader = FrameLogReader(driver.writer.run_dir)
    rolls = [
        record
        for record in reader.records("trace")
        if record["payload"].get("record_type") == "encounter_rolled"
    ]

    # One negative record per co-present pair per tick: 24 ticks, one pair.
    assert len(rolls) == 24
    for record in rolls:
        payload = record["payload"]
        # The negative record itself: encountered: false, value vs. threshold.
        assert payload["encountered"] is False
        assert payload["outcome"] == "no_encounter"
        assert payload["threshold"] == 0.0
        assert 0.0 <= payload["value"] < 1.0
        assert payload["value"] >= payload["threshold"]
        assert payload["encountered"] == (payload["value"] < payload["threshold"])
        # Keyed per ADR-0009: seed_id, purpose, tick, site, participants, draw.
        roll_key = payload["roll_key"]
        assert roll_key["seed_id"] == "tier1-non-encounter"
        assert roll_key["purpose"] == "encounter.co-presence"
        assert roll_key["tick"] == record["tick"]
        assert roll_key["site"] == "bannered_mare"
        assert roll_key["participants"] == ["hulda", "irileth"]  # sorted
        assert roll_key["draw"] == 0

    # The negative's consequence: with every roll failing, the story never
    # moved -- hulda holds no belief about the theft.
    assert driver.belief_of("hulda", claim.id) is None
