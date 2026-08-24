"""T6 -- the north-star composition test (docs/vision-v2.2.md §2).

The player assassinates Jarl Balgruuf. No new mechanism
(docs/scenario-ladder.md, Tier 6 intro): every beat below is Tiers 0-5
composing, not a new rule. Fixture: chronicle/fixtures/north_star.py
(design doc docs/design/north-star-fixture.md, lane 45/49). If any of
Tiers 0-5's mechanisms don't compose, this test is where it shows.

Four beats, one cast, one run:

  1. Succession -- the Jarl's role resolves from the court's real
     relationship state (rule 19, Tier 5); the sitting Steward is
     untouched (a second role, same institution, no interference).
  2. Grief and grudge -- the household (kin) mourn on their own
     calendars (rule 17, Tier 4a) and hold a grudge with the killing
     as evidence (rule 8/12, Tier 3).
  3. The rumor -- propagates city-wide with a mutation (rule 7, Tier 2)
     that survives to Markarth via the caravaneer (T2.6, Tier 2) --
     the believer's evidence chain passes through the carrier and
     carries the mutated slot.
  4. The ripple -- a read-only aggregate over reputation records
     (rule 16, Tier 3), computed here as a plain test-side function,
     never fed into any rule (docs/scenario-ladder.md's aggregate
     discipline: derived on read, never a behavior input).
"""

from chronicle.claims import EventKey
from chronicle.events import NPCDied, ScheduleRewrite
from chronicle.fixtures.carrier_schedule import (
    CARAVANEER,
    END_TICK,
    MARKARTH_RESIDENTS,
    WHITERUN_CAST,
)
from chronicle.fixtures.north_star import (
    DEATH_CLAIM_ID,
    DEATH_CLAIM_KIND,
    DECEASED,
    FROTHAR,
    GUARD,
    HOUSECARL,
    JARL_ROLE,
    KILLER,
    NELKIR,
    STEWARD,
    STEWARD_ROLE,
    build_driver,
)
from chronicle.framelog import FrameLogReader

_SEED = "north-star-2"  # worker-chosen: verified to satisfy the mutation-reaches-Markarth smoke fact
_SAVE = "whiterun-save-1"
_HOUSEHOLD = (FROTHAR, NELKIR)


def _driver(run_id: str):
    return build_driver(run_id, _SEED)


def _the_assassination(driver) -> None:
    driver.inject_event(
        NPCDied(
            tick=0, save_uuid=_SAVE, generation=0, seq=1,
            gamets=0.0, wall_ts=0.0, npc_id=DECEASED,
            cause="assassination", killer_id=KILLER, location_id="dragonsreach",
        ),
        origin={"kind": "scenario", "detail": "test_north_star"},
    )
    for witness_id in (*_HOUSEHOLD, HOUSECARL, STEWARD, GUARD):
        driver.witness(
            claim_id=DEATH_CLAIM_ID,
            belief_id=f"belief-{witness_id}-death",
            evidence_id=f"evidence-{witness_id}-death",
            kind=DEATH_CLAIM_KIND,
            slots={
                "deceased": DECEASED, "cause": "assassination", "location": "dragonsreach",
                "weapon": "a dagger", "killer": KILLER,
            },
            canonical_event_key=EventKey(_SAVE, 0, 1),
            witness_id=witness_id,
            gamets=0.0,
        )
    # The household's grudge, evidenced by the killing (vision beat 2).
    for kin_id in _HOUSEHOLD:
        belief = driver.belief_of(kin_id, DEATH_CLAIM_ID)
        relationship = driver.social.any_relationship(kin_id, DECEASED)
        driver.form_grudge(
            id=f"grudge-{kin_id}-killer", holder_id=kin_id, victim_id=DECEASED, target_id=KILLER,
            grievance_type="murder", source_belief_id=belief.id, evidentiary_strength=belief.confidence,
            relationship_to_victim=relationship, gamets=0.0,
        )


def _records(driver, stream: str) -> list[dict]:
    try:
        driver.writer.flush()
    except ValueError:  # flush of closed file -- close() already flushed
        pass
    reader = FrameLogReader(driver.writer.run_dir)
    return [record["payload"] for record in reader.records(stream)]


def _negative_sentiment(driver, observer_ids, *, subject_id=KILLER, context="security") -> float | None:
    """A read-only aggregate over reputation records -- guard cohesion / market
    confidence, computed here at read time, never stored, never a rule input
    (docs/scenario-ladder.md's Tier 6 aggregate discipline). Higher = more distrust."""
    reputations = [driver.social.reputation(observer_id, subject_id, context) for observer_id in observer_ids]
    reputations = [r for r in reputations if r is not None]
    if not reputations:
        return None
    return sum(1.0 - r.mean for r in reputations) / len(reputations)


def test_north_star_composition():
    driver = _driver("north-star-composition")
    _the_assassination(driver)

    # Beat 1a: succession. The Jarl's role is vacant the instant he
    # dies (rule 19 resolves immediately, no tick loop needed) and
    # installs whoever the court's actual relationship graph ranks
    # highest -- irileth's 0.95 shared_employer edge outranks
    # proventus's 0.85 (whiterun_relationships.py, unedited).
    assert driver.roles.holder_of(JARL_ROLE) == HOUSECARL
    jarl_role = driver.roles.role(JARL_ROLE)
    assert jarl_role.vacated_at is None  # succeeded, not left vacant

    # Beat 1b: no interference. The Steward (a second role, same
    # institution) is untouched -- proventus never died, so his role
    # was never even evaluated for vacancy.
    assert driver.roles.holder_of(STEWARD_ROLE) == STEWARD

    driver.run(0, END_TICK)
    driver.close()

    events = _records(driver, "events")
    trace = _records(driver, "trace")

    # Beat 1c: the duty lapse + role-appointed events, field-for-field
    # (schema §3:97), naming the right people.
    status_events = [p for p in events if p.get("event_type") == "status_changed"]
    lapse = next(p for p in status_events if p["status_kind"] == "duty_lapsed")
    assert lapse["npc_id"] == DECEASED
    appointed = next(p for p in status_events if p["status_kind"] == "role_appointed")
    assert appointed["npc_id"] == HOUSECARL
    assert appointed["detail"] == JARL_ROLE

    # Beat 2a: the household mourns on ITS OWN calendar -- one
    # schedule_rewrite overlay per kin, each independently triggered
    # (design doc N2/vision-v2.2.md:21, "his household mourns on
    # their calendars, not in a bark" -- plural events, not one).
    rewrites = [e for e in driver.event_log.lineage(_SAVE, 0) if isinstance(e, ScheduleRewrite)]
    assert {r.npc_id for r in rewrites} == set(_HOUSEHOLD)
    for rewrite in rewrites:
        assert rewrite.location_id == "temple_of_kynareth"
        assert rewrite.start_tick == 0

    # Beat 2b: the household holds a grudge with the killing as its
    # own evidence -- the exact belief the household witnessed.
    for kin_id in _HOUSEHOLD:
        grudges = driver.social.grudges_of(kin_id)
        assert len(grudges) == 1
        grudge = grudges[0]
        assert grudge.target_id == KILLER
        assert grudge.source_belief_id == driver.belief_of(kin_id, DEATH_CLAIM_ID).id

    # Beat 3: the rumor reaches Markarth, mutated, through the carrier
    # -- at least one Markarth resident's evidence chain names the
    # caravaneer AND carries a weapon slot different from the original.
    markarth_mutated = []
    for resident_id in MARKARTH_RESIDENTS:
        belief = driver.belief_of(resident_id, DEATH_CLAIM_ID)
        if belief is None:
            continue
        chain = driver.chain_for(belief.id)
        chain_holders = {b.holder_id for b, _ in chain}
        variant = driver.claims.variant(belief.variant_id) if belief.variant_id else None
        if CARAVANEER in chain_holders and variant is not None and variant.slots["weapon"] != "a dagger":
            markarth_mutated.append((resident_id, variant.slots["weapon"]))
    assert markarth_mutated, "no Markarth believer's chain both passed through the carrier and carried a mutated weapon slot"

    # Beat 4: the aggregate substrate exists and is computable, for
    # BOTH populations the vision names -- and it's demonstrably
    # read-only: nothing in rules.py's source even mentions it.
    guard_cohesion = _negative_sentiment(driver, [GUARD])
    market_confidence = _negative_sentiment(driver, WHITERUN_CAST)
    assert guard_cohesion is not None
    assert market_confidence is not None
    reputation_rows = [p for p in trace if p.get("record_type") == "reputation_updated"]
    assert reputation_rows  # the substrate the aggregate reads is real, not hypothetical

    import inspect

    import chronicle.rules as rules_module
    assert "aggregate" not in inspect.getsource(rules_module).lower()


def test_north_star_is_deterministic():
    """Two independent regenerations, byte-identical modulo wall_ts."""
    a = _driver("north-star-det-a")
    _the_assassination(a)
    a.run(0, END_TICK)
    a.close()

    b = _driver("north-star-det-b")
    _the_assassination(b)
    b.run(0, END_TICK)
    b.close()

    for stream in ("events", "trace"):
        records_a = [{k: v for k, v in payload.items() if k != "wall_ts"} for payload in _records(a, stream)]
        records_b = [{k: v for k, v in payload.items() if k != "wall_ts"} for payload in _records(b, stream)]
        assert records_a == records_b
