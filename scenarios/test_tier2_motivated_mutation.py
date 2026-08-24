"""Scenario-ladder rung T2.4 (Motivated mutation placeholder) -- rule 7's allegiance hook.

Faction-aligned NPC retells with allegiance-consistent slot
substitution (docs/scenario-ladder.md:61). Assert: substitution
direction matches allegiance. The lane-45/50 pins in force
(docs/design/north-star-fixture.md Decision N4,
docs/work-packets/lane-50-motivated-mutation.md):

  - A teller holding a "faction" relationship whose basis_id has an
    entry in the new `allegiance_candidates` mapping (claim_kind,
    slot, faction basis_id) -> value substitutes DETERMINISTICALLY --
    no mutation.value roll at all, asserted exactly (not "one of
    several candidates"), across every tick a retelling happens.
  - An unmapped teller keeps today's uniform-random substitution from
    `mutation_candidates` -- the regression proof.

Fixture: a single-slot claim (only "cause" -- no slot roll variability
to control for) with mutation_probability=1.0 (always attempted). One
teller/hearer pair per test, isolated, so each run's mutation_applied
row is unambiguous.
"""

from chronicle.claims import EventKey
from chronicle.driver import Driver
from chronicle.events import NPCDied
from chronicle.framelog import FrameLogReader
from chronicle.schedule import ScheduleBlock

_SEED = "tier2-motivated-mutation"
_SAVE = "whiterun-save-1"
_TICKS = 3

_TELLER = "ralof"
_HEARER = "hulda"

_CLAIM_ID = "claim-jarl-death"
_CLAIM_KIND = "npc_death"
_SLOT = "cause"
_STORMCLOAKS = "stormcloaks"
_MUTATION_CANDIDATES = {(_CLAIM_KIND, _SLOT): ("an accident", "a sudden illness")}
_ALLEGIANCE_CANDIDATES = {(_CLAIM_KIND, _SLOT, _STORMCLOAKS): "an Imperial plot"}

_SCHEDULE = (
    ScheduleBlock(npc_id=_TELLER, location_id="dragonsreach", start_tick=0, end_tick=100),
    ScheduleBlock(npc_id=_HEARER, location_id="dragonsreach", start_tick=0, end_tick=100),
)


def _driver(run_id: str, *, allegiance_candidates=_ALLEGIANCE_CANDIDATES) -> Driver:
    return Driver(
        run_id=run_id,
        seed_id=_SEED,
        save_uuid=_SAVE,
        generation=0,
        schedule=_SCHEDULE,
        encounter_probability=1.0,
        mutation_probability=1.0,
        mutation_candidates=_MUTATION_CANDIDATES,
        allegiance_candidates=allegiance_candidates,
    )


def _records(driver: Driver, stream: str) -> list[dict]:
    try:
        driver.writer.flush()
    except ValueError:  # flush of closed file -- close() already flushed
        pass
    reader = FrameLogReader(driver.writer.run_dir)
    return [record["payload"] for record in reader.records(stream)]


def _witness_the_death(driver: Driver, *, tick: int = 0) -> None:
    driver.inject_event(
        NPCDied(
            tick=tick, save_uuid=_SAVE, generation=0, seq=1,
            gamets=float(tick), wall_ts=0.0, npc_id="jarl_balgruuf",
            cause="unknown", killer_id=None, location_id="dragonsreach",
        ),
        origin={"kind": "scenario", "detail": "test_tier2_motivated_mutation"},
    )
    driver.witness(
        claim_id=_CLAIM_ID,
        belief_id=f"belief-{_TELLER}-death",
        evidence_id=f"evidence-{_TELLER}-death",
        kind=_CLAIM_KIND,
        slots={_SLOT: "unknown"},
        canonical_event_key=EventKey(_SAVE, 0, 1),
        witness_id=_TELLER,
        gamets=float(tick),
    )


def _the_one_mutation(driver: Driver) -> dict:
    mutations = [p for p in _records(driver, "trace") if p.get("record_type") == "mutation_applied"]
    assert len(mutations) == 1
    return mutations[0]


def test_t24_a_faction_aligned_teller_substitutes_deterministically():
    driver = _driver("tier2-motivated-mutation")
    driver.form_relationship(
        id="rel-ralof-stormcloaks", from_id=_TELLER, to_id="stormcloak_high_command",
        basis="faction", basis_id=_STORMCLOAKS, strength=0.8, gamets=0.0,
    )
    _witness_the_death(driver)
    driver.run(0, _TICKS)
    driver.close()

    mutation = _the_one_mutation(driver)
    assert mutation["new_value"] == "an Imperial plot"
    assert mutation["old_value"] == "unknown"
    # The slot roll's own evidence is still present (the slot IS randomly
    # rolled regardless of a deterministic value) -- but there is no
    # separate value-roll evidence to derive from it anymore, since no
    # mutation.value roll occurred at all (design doc N4's "no roll" hook).
    assert mutation["roll_key"] is not None
    assert mutation["roll_key"]["purpose"] == "mutation.slot"

    hearer_belief = driver.belief_of(_HEARER, _CLAIM_ID)
    assert hearer_belief is not None
    variant = driver.claims.variant(hearer_belief.variant_id)
    assert variant.slots[_SLOT] == "an Imperial plot"


def test_t24_the_same_deterministic_value_holds_across_every_retelling_tick():
    """Not "one of several candidates" -- the exact same value, every time,
    proving there is genuinely no roll deciding it (design doc N4)."""
    values = set()
    for tick_offset in range(3):
        driver = _driver(f"tier2-motivated-mutation-tick-{tick_offset}")
        driver.form_relationship(
            id="rel-ralof-stormcloaks", from_id=_TELLER, to_id="stormcloak_high_command",
            basis="faction", basis_id=_STORMCLOAKS, strength=0.8, gamets=0.0,
        )
        _witness_the_death(driver, tick=tick_offset)
        driver.run(tick_offset, tick_offset + _TICKS)
        driver.close()
        hearer_belief = driver.belief_of(_HEARER, _CLAIM_ID)
        assert hearer_belief is not None
        values.add(driver.claims.variant(hearer_belief.variant_id).slots[_SLOT])
    assert values == {"an Imperial plot"}


def test_t24_an_unaligned_teller_keeps_uniform_random_substitution():
    """The regression proof: no faction edge at all -> today's roll-based path, unchanged."""
    driver = _driver("tier2-motivated-mutation-unaligned")
    _witness_the_death(driver)
    driver.run(0, _TICKS)
    driver.close()

    mutation = _the_one_mutation(driver)
    assert mutation["new_value"] in _MUTATION_CANDIDATES[(_CLAIM_KIND, _SLOT)]
    assert mutation["new_value"] != "an Imperial plot"


def test_no_allegiance_candidates_registered_means_zero_behavior_change():
    """The pin's regression half: no mapping at all -> byte-identical to pre-lane-50, even for a faction-aligned teller."""
    with_mapping = _driver("tier2-motivated-mutation-with-mapping")
    with_mapping.form_relationship(
        id="rel-ralof-stormcloaks", from_id=_TELLER, to_id="stormcloak_high_command",
        basis="faction", basis_id=_STORMCLOAKS, strength=0.8, gamets=0.0,
    )
    _witness_the_death(with_mapping)
    with_mapping.run(0, _TICKS)
    with_mapping.close()

    without_mapping = _driver("tier2-motivated-mutation-without-mapping", allegiance_candidates=None)
    without_mapping.form_relationship(
        id="rel-ralof-stormcloaks", from_id=_TELLER, to_id="stormcloak_high_command",
        basis="faction", basis_id=_STORMCLOAKS, strength=0.8, gamets=0.0,
    )
    _witness_the_death(without_mapping)
    without_mapping.run(0, _TICKS)
    without_mapping.close()

    with_belief = with_mapping.belief_of(_HEARER, _CLAIM_ID)
    without_belief = without_mapping.belief_of(_HEARER, _CLAIM_ID)
    with_value = with_mapping.claims.variant(with_belief.variant_id).slots[_SLOT]
    without_value = without_mapping.claims.variant(without_belief.variant_id).slots[_SLOT]
    assert with_value == "an Imperial plot"
    assert without_value != "an Imperial plot"  # falls back to the uniform-random pool
