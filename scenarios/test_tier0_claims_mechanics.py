"""Scenario-ladder Tier 0: claims-layer mechanics, no propagation (docs/scenario-ladder.md §3 Tier 0).

The ladder's Tier-0 header: "Machinery: already built. These rungs must
pass today." Each test below is one rung's own words made executable,
run through the driver (chronicle/driver.py) so the frame log records
every derivation, and queried through the store the way the dashboard
will (ADR-0007), not by holding onto return values:

  - T0.1 Witness -- one theft, one witness: exactly one belief, correct
    slots, witnessed evidence, confidence at the direct-observation
    baseline.
  - T0.2 Decay -- 30 quiet game-days (720 ticks/gamets, ADR-0010): exact
    closed-form verbatim/gist/confidence values, stage_at() = heard, not
    dormant (the RUMOR_DORMANT_AFTER anchor is ~45 days).
  - T0.3 Corroboration -- two independent witness reports reach one NPC:
    confidence rises on the exact noisy-or curve; a third report from an
    already-counted source produces no rise (rule 7).
  - T0.4 Shared-claim invariant -- two witnesses to one canonical event:
    one Claim, two beliefs; a disagreeing second witness produces a
    Variant, never a second Claim.
"""

import pytest

from chronicle.claims import RUMOR_DORMANT_AFTER, WITNESS_CONFIDENCE, decay, stage_at
from chronicle.driver import Driver
from chronicle.events import CrimeWitnessed, NPCDied

# ADR-0010: 1 tick = 1 gamets = 1 game-hour, 24 per game-day.
TICKS_PER_GAME_DAY = 24

ORIGIN = {"kind": "scenario", "detail": "test_tier0_claims_mechanics"}


def test_t01_witness_forms_exactly_one_direct_observation_belief():
    """Ladder T0.1 (Witness): one theft, one witness -- exactly one belief, correct slots,
    evidence = direct observation, confidence at the direct-observation baseline
    (witness-creates-belief, claims.py's WITNESS_CONFIDENCE).
    """
    driver = Driver(
        run_id="scenario-t01-witness",
        seed_id="tier0-witness",
        save_uuid="whiterun-save-1",
        generation=0,
    )
    driver.inject_event(
        CrimeWitnessed(
            tick=0, save_uuid="whiterun-save-1", generation=0, seq=1,
            gamets=0.0, wall_ts=0.0, witness_id="proventus",
            perpetrator_id="unknown", crime_type="theft", location_id="bannered_mare",
        ),
        origin=ORIGIN,
    )
    theft_event = driver.event_log.lineage("whiterun-save-1", 0)[0]
    theft_key = (theft_event.save_uuid, theft_event.generation, theft_event.seq)

    slots = {"perpetrator": "unknown", "crime_type": "theft", "location": "bannered_mare"}
    claim, _, _ = driver.witness(
        claim_id="claim-theft",
        belief_id="belief-proventus-theft",
        evidence_id="evidence-proventus-theft",
        kind="crime_witnessed",
        slots=slots,
        canonical_event_key=theft_key,
        witness_id="proventus",
        gamets=0.0,
    )

    # Exactly one belief, queried back out of the store (not the return value).
    beliefs = driver.beliefs_of("proventus")
    assert len(beliefs) == 1
    belief = beliefs[0]

    # Correct slots, on the claim the belief points at.
    assert belief.claim_id == claim.id
    assert dict(claim.slots) == slots
    assert tuple(claim.canonical_event_key) == theft_key

    # Evidence = direct observation: one witnessed Evidence record, sourced
    # from the witness himself, grounded in the canonical event (no
    # predecessor belief -- nothing was reported to him).
    evidence = driver.claims.evidence_for(belief.id)
    assert len(evidence) == 1
    assert evidence[0].evidence_type == "witnessed"
    assert evidence[0].source_id == "proventus"
    assert evidence[0].predecessor_belief_id is None

    # Confidence at the direct-observation baseline.
    assert belief.confidence == WITNESS_CONFIDENCE
    driver.close()


def test_t02_thirty_quiet_game_days_decay_on_the_exact_closed_form_curve():
    """Ladder T0.2 (Decay): 30 quiet game-days (720 ticks, ADR-0010) -- exact closed-form
    verbatim/gist values for the fixed inputs (deterministic curve, no tolerance band);
    stage_at() = heard throughout, not dormant yet (belief-decay rule + rumor-stage
    machine; RUMOR_DORMANT_AFTER anchors dormancy at ~45 quiet days).
    """
    driver = Driver(
        run_id="scenario-t02-decay",
        seed_id="tier0-decay",
        save_uuid="whiterun-save-1",
        generation=0,
    )
    driver.inject_event(
        CrimeWitnessed(
            tick=0, save_uuid="whiterun-save-1", generation=0, seq=1,
            gamets=0.0, wall_ts=0.0, witness_id="proventus",
            perpetrator_id="unknown", crime_type="theft", location_id="bannered_mare",
        ),
        origin=ORIGIN,
    )
    theft_event = driver.event_log.lineage("whiterun-save-1", 0)[0]
    theft_key = (theft_event.save_uuid, theft_event.generation, theft_event.seq)
    claim, _, _ = driver.witness(
        claim_id="claim-theft",
        belief_id="belief-proventus-theft",
        evidence_id="evidence-proventus-theft",
        kind="crime_witnessed",
        slots={"perpetrator": "unknown", "crime_type": "theft", "location": "bannered_mare"},
        canonical_event_key=theft_key,
        witness_id="proventus",
        gamets=0.0,
    )

    # 30 quiet game-days actually pass in the sim: no schedule, no encounters,
    # no rehearsal -- the tick loop has nothing to derive.
    quiet_days = 30
    driver.run(0, quiet_days * TICKS_PER_GAME_DAY)
    elapsed = float(quiet_days * TICKS_PER_GAME_DAY)  # 720.0 gamets

    # Exact closed-form decay (claims.py's halving curve, stated independently
    # here): value * 0.5 ** (elapsed / half-life), elapsed measured from the
    # belief's last rehearsal at gamets 0. Witness formation values:
    # confidence 0.95, verbatim 1.0, gist 1.0.
    belief = driver.beliefs_of("proventus")[0]
    decayed = decay(belief, at_gamets=elapsed)
    assert decayed.confidence == 0.95 * 0.5 ** (elapsed / 168.0)  # ~7-day confidence half-life
    assert decayed.verbatim_strength == 1.0 * 0.5 ** (elapsed / 72.0)  # ~3-day verbatim half-life
    assert decayed.gist_strength == 1.0 * 0.5 ** (elapsed / 1440.0)  # ~60-day gist half-life

    # stage_at() = heard throughout the 30 quiet days -- never dormant: the
    # dormancy anchor (RUMOR_DORMANT_AFTER, ~45 quiet days) has not passed.
    assert elapsed < RUMOR_DORMANT_AFTER
    rumor = driver.claims.rumor_state("proventus", claim.id, None)
    assert rumor is not None
    for day in range(1, quiet_days + 1):
        at = float(day * TICKS_PER_GAME_DAY)
        assert stage_at(rumor, belief, at) == "heard"
    driver.close()


def test_t03_corroboration_rises_on_the_exact_noisy_or_curve():
    """Ladder T0.3 (Corroboration): two independent witness reports reach one NPC as
    testimony -- confidence rises on the exact noisy-or curve (1 - product of
    disbelief); a third report from an already-counted source produces no rise
    (corroboration rule: noisy-or, distinct-source gating; claims.py:corroborate).
    """
    driver = Driver(
        run_id="scenario-t03-corroboration",
        seed_id="tier0-corroboration",
        save_uuid="whiterun-save-1",
        generation=0,
    )
    driver.inject_event(
        CrimeWitnessed(
            tick=0, save_uuid="whiterun-save-1", generation=0, seq=1,
            gamets=0.0, wall_ts=0.0, witness_id="proventus",
            perpetrator_id="unknown", crime_type="theft", location_id="bannered_mare",
        ),
        origin=ORIGIN,
    )
    theft_event = driver.event_log.lineage("whiterun-save-1", 0)[0]
    theft_key = (theft_event.save_uuid, theft_event.generation, theft_event.seq)

    # Three independent witnesses to the same canonical theft: proventus
    # (whose belief gets corroborated), irileth, and a guard. Same claim_id,
    # same slots -- the same canonical event, so the same Claim record.
    slots = {"perpetrator": "unknown", "crime_type": "theft", "location": "bannered_mare"}
    for npc in ("proventus", "irileth", "whiterun_guard_1"):
        driver.witness(
            claim_id="claim-theft",
            belief_id=f"belief-{npc}-theft",
            evidence_id=f"evidence-{npc}-theft",
            kind="crime_witnessed",
            slots=slots,
            canonical_event_key=theft_key,
            witness_id=npc,
            gamets=0.0,
        )

    # First independent report: noisy-or over two direct-observation beliefs,
    # no decay (corroboration at the witnesses' own gamets, elapsed = 0).
    after_first, _ = driver.corroborate(
        belief_id="belief-proventus-theft",
        source_belief=driver.belief_of("irileth", "claim-theft"),
        evidence_id="evidence-irileth-corroborates-proventus",
        gamets=0.0,
    )
    expected_first = 1 - (1 - 0.95) * (1 - 0.95)
    assert after_first.confidence == expected_first

    # Second independent report, from a distinct source: the curve again over
    # the already-corroborated belief and the guard's direct observation.
    after_second, _ = driver.corroborate(
        belief_id="belief-proventus-theft",
        source_belief=driver.belief_of("whiterun_guard_1", "claim-theft"),
        evidence_id="evidence-guard-corroborates-proventus",
        gamets=0.0,
    )
    expected_second = 1 - (1 - expected_first) * (1 - 0.95)
    assert after_second.confidence == expected_second

    # A third report from an already-counted source produces no rise: the
    # store refuses distinct-source-violating repetition (rule 7), and
    # proventus's confidence is exactly where the second report left it.
    with pytest.raises(ValueError):
        driver.corroborate(
            belief_id="belief-proventus-theft",
            source_belief=driver.belief_of("irileth", "claim-theft"),
            evidence_id="evidence-irileth-corroborates-proventus-again",
            gamets=0.0,
        )
    assert driver.belief_of("proventus", "claim-theft").confidence == expected_second
    driver.close()


def test_t04_two_witnesses_one_canonical_event_one_claim_two_beliefs():
    """Ladder T0.4, first half (shared-claim invariant): two witnesses to one canonical
    event -- one Claim, two beliefs (shared-claim invariant: one claim per canonical
    event, enforced at the store write path).
    """
    driver = Driver(
        run_id="scenario-t04-shared-claim",
        seed_id="tier0-shared-claim",
        save_uuid="whiterun-save-1",
        generation=0,
    )
    driver.inject_event(
        NPCDied(
            tick=0, save_uuid="whiterun-save-1", generation=0, seq=1,
            gamets=0.0, wall_ts=0.0, npc_id="jarl_balgruuf",
            cause="assassination", killer_id=None, location_id="dragonsreach",
        ),
        origin=ORIGIN,
    )
    death_event = driver.event_log.lineage("whiterun-save-1", 0)[0]
    death_key = (death_event.save_uuid, death_event.generation, death_event.seq)

    slots = {"perpetrator": "unknown", "cause": "assassination", "location": "dragonsreach"}
    claim, _, _ = driver.witness(
        claim_id="claim-jarl-death",
        belief_id="belief-proventus-death",
        evidence_id="evidence-proventus-death",
        kind="npc_death",
        slots=slots,
        canonical_event_key=death_key,
        witness_id="proventus",
        gamets=0.0,
    )
    # Second witness, same canonical event: reuses the same claim_id -- it is
    # the same Claim record, not a second independent one.
    driver.witness(
        claim_id="claim-jarl-death",
        belief_id="belief-irileth-death",
        evidence_id="evidence-irileth-death",
        kind="npc_death",
        slots=slots,
        canonical_event_key=death_key,
        witness_id="irileth",
        gamets=0.0,
    )

    # One Claim, two beliefs: both witnesses hold a belief pointing at the
    # single shared Claim for the event.
    proventus_belief = driver.belief_of("proventus", claim.id)
    irileth_belief = driver.belief_of("irileth", claim.id)
    assert proventus_belief is not None and irileth_belief is not None
    assert proventus_belief.id != irileth_belief.id
    assert proventus_belief.claim_id == irileth_belief.claim_id == claim.id

    # The invariant is enforced, not conventional: a second claim id for the
    # same canonical event is rejected at the store write path.
    with pytest.raises(ValueError):
        driver.witness(
            claim_id="claim-jarl-death-again",
            belief_id="belief-carlotta-death",
            evidence_id="evidence-carlotta-death",
            kind="npc_death",
            slots=slots,
            canonical_event_key=death_key,
            witness_id="carlotta",
            gamets=0.0,
        )
    driver.close()


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Machinery gap: a disagreeing second witness does not produce a Variant. "
        "ClaimStore.witness (chronicle/claims.py:459-463) raises ValueError "
        "('claim ... already exists with different content') instead -- the "
        "disagreeing-witness-produces-variant path the ladder's T0.4 names does "
        "not exist in claims.witness()."
    ),
)
def test_t04_disagreeing_second_witness_produces_a_variant_never_a_second_claim():
    """Ladder T0.4, second half (shared-claim invariant): a disagreeing second witness
    (different slot values for the same canonical event) produces a Variant, never a
    second Claim -- claims never mutate in place, so disagreement must live on a
    Variant hanging off the one shared Claim.
    """
    driver = Driver(
        run_id="scenario-t04-disagreeing-witness",
        seed_id="tier0-disagreeing-witness",
        save_uuid="whiterun-save-1",
        generation=0,
    )
    driver.inject_event(
        NPCDied(
            tick=0, save_uuid="whiterun-save-1", generation=0, seq=1,
            gamets=0.0, wall_ts=0.0, npc_id="jarl_balgruuf",
            cause="assassination", killer_id=None, location_id="dragonsreach",
        ),
        origin=ORIGIN,
    )
    death_event = driver.event_log.lineage("whiterun-save-1", 0)[0]
    death_key = (death_event.save_uuid, death_event.generation, death_event.seq)

    claim, _, _ = driver.witness(
        claim_id="claim-jarl-death",
        belief_id="belief-proventus-death",
        evidence_id="evidence-proventus-death",
        kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "dragonsreach"},
        canonical_event_key=death_key,
        witness_id="proventus",
        gamets=0.0,
    )

    # Irileth disagrees about the perpetrator slot. Per the rung this is a
    # Variant of the one shared Claim -- not a second Claim, and not an
    # in-place edit of the canonical claim's slots.
    _, irileth_belief, _ = driver.witness(
        claim_id="claim-jarl-death",
        belief_id="belief-irileth-death",
        evidence_id="evidence-irileth-death",
        kind="npc_death",
        slots={"perpetrator": "a thalmor justiciar", "cause": "assassination", "location": "dragonsreach"},
        canonical_event_key=death_key,
        witness_id="irileth",
        gamets=0.0,
    )
    assert irileth_belief.claim_id == claim.id  # never a second Claim
    assert irileth_belief.variant_id is not None  # her disagreement is a Variant
    variant = driver.variant(irileth_belief.variant_id)
    assert variant.claim_id == claim.id
    assert variant.slots["perpetrator"] == "a thalmor justiciar"
    # The canonical claim never mutates in place: proventus's telling stands.
    assert claim.slots["perpetrator"] == "unknown"
    assert driver.claim(claim.id).slots["perpetrator"] == "unknown"
    driver.close()
