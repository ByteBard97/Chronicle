from chronicle.events import CrimeWitnessed, EventLog, NPCDied, RumorHeard, of_type


def test_derives_trivial_state_from_appended_events():
    log = EventLog()
    log.append(NPCDied(tick=10, save_uuid="s1", generation=0, seq=1, gamets=10.0, wall_ts=1000.0, npc_id="jarl_balgruuf", cause="assassination", killer_id="unknown"))
    log.append(CrimeWitnessed(tick=10, save_uuid="s1", generation=0, seq=2, gamets=10.0, wall_ts=1001.0, witness_id="proventus", perpetrator_id="unknown", crime_type="murder"))
    log.append(RumorHeard(tick=12, save_uuid="s1", generation=0, seq=3, gamets=12.0, wall_ts=1050.0, hearer_id="hulda", source_id="proventus", rumor_id="r1", content="The Jarl is dead."))

    events = log.lineage("s1", 0)
    assert len(events) == 3

    deaths = of_type(events, NPCDied)
    assert len(deaths) == 1
    assert deaths[0].npc_id == "jarl_balgruuf"

    rumors = of_type(events, RumorHeard)
    assert len(rumors) == 1
    assert rumors[0].hearer_id == "hulda"


def test_forking_a_branch_excludes_the_abandoned_suffix():
    log = EventLog()
    log.append(NPCDied(tick=10, save_uuid="s1", generation=0, seq=1, gamets=10.0, wall_ts=1000.0, npc_id="jarl_balgruuf", cause="assassination"))
    log.append(RumorHeard(tick=12, save_uuid="s1", generation=0, seq=2, gamets=12.0, wall_ts=1050.0, hearer_id="hulda", source_id="proventus", rumor_id="r1", content="The Jarl is dead."))
    # Player reloads a save from before this point -- the third event was never seen in-game.
    log.append(RumorHeard(tick=14, save_uuid="s1", generation=0, seq=3, gamets=14.0, wall_ts=1100.0, hearer_id="ysolda", source_id="hulda", rumor_id="r1", content="The Jarl was murdered by the Thalmor."))

    # Reload after 2 events; the mutated third rumor is the abandoned suffix.
    new_generation = log.fork("s1", from_generation=0, at_event_count=2)
    assert new_generation == 1

    # New play continues down a different path.
    log.append(NPCDied(tick=20, save_uuid="s1", generation=1, seq=1, gamets=13.0, wall_ts=1200.0, npc_id="jarl_balgruuf", cause="illness"))

    original = log.lineage("s1", 0)
    forked = log.lineage("s1", 1)

    assert len(original) == 3
    assert len(forked) == 3

    # The fork inherits the first 2 events, then its own new event -- not the abandoned rumor.
    assert forked[1].content == "The Jarl is dead."
    assert forked[2].cause == "illness"
    assert not any(isinstance(e, RumorHeard) and "Thalmor" in e.content for e in forked)

    # The abandoned suffix is still recorded on the original branch, and in the full log --
    # forking never deletes it, only excludes it from the new branch's derived state.
    assert any(isinstance(e, RumorHeard) and "Thalmor" in e.content for e in original)
    assert any(isinstance(e, RumorHeard) and "Thalmor" in e.content for e in log.all())


def test_append_is_idempotent_on_branch_and_seq():
    log = EventLog()
    event = NPCDied(tick=10, save_uuid="s1", generation=0, seq=1, gamets=10.0, wall_ts=1000.0, npc_id="jarl_balgruuf", cause="assassination")

    assert log.append(event) is True
    # A retried/replayed post of the same (save_uuid, generation, seq) is a no-op.
    assert log.append(event) is False

    assert len(log.lineage("s1", 0)) == 1
