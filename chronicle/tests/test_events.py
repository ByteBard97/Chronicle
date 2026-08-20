from chronicle.events import CrimeWitnessed, EventLog, NPCDied, RumorHeard


def test_derives_trivial_state_from_appended_events():
    log = EventLog()
    log.append(NPCDied(tick=10, npc_id="jarl_balgruuf", cause="assassination", killer_id="unknown"))
    log.append(CrimeWitnessed(tick=10, witness_id="proventus", perpetrator_id="unknown", crime_type="murder"))
    log.append(RumorHeard(tick=12, hearer_id="hulda", source_id="proventus", rumor_id="r1", content="The Jarl is dead."))

    assert len(log.all()) == 3

    deaths = log.of_type(NPCDied)
    assert len(deaths) == 1
    assert deaths[0].npc_id == "jarl_balgruuf"

    rumors = log.of_type(RumorHeard)
    assert len(rumors) == 1
    assert rumors[0].hearer_id == "hulda"
