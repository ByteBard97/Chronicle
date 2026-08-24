"""Generate the north-star demo run into runs/: the Jarl assassination, full cast.

Not a test — a runnable demo producer (pytest ignores it: no test_
prefix). Same idiom as scenarios/run_tier3_demo.py and
run_mourning_demo.py, over the composed fixture
chronicle/fixtures/north_star.py (design doc N5's one-fixture-many-
consumers precedent — the same fixture module `scenarios/
test_north_star.py`'s T6 rung is built on). This is the M7 stranger-
walkthrough's data (docs/ui-spec.md §5): the assassination findable on
the timeline, the rumor overlay's carrier hop scrubbable, a Markarth
believer with a visible variant badge, the variant tree showing the
mutated slot, a provenance drill from belief to the mutated weapon
through the mutation, and (via `CHRONICLE_RUNS_DIR`/URL state) a
reproducible view. Deterministic: fixed seed, same log
(chronicle/tests/test_determinism.py proves the property this script
relies on).

    uv run python scenarios/run_north_star_demo.py
"""

import json
from collections import Counter

from chronicle.claims import EventKey
from chronicle.events import NPCDied
from chronicle.fixtures.carrier_schedule import CARAVANEER, END_TICK, MARKARTH_RESIDENTS
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
    PRIEST,
    STEWARD,
    STEWARD_ROLE,
    build_driver,
)
from chronicle.framelog import default_runs_dir

RUN_ID = "north-star-01"
# Worker-chosen (same seed test_north_star.py verified): satisfies the
# mutation-reaches-Markarth-via-the-caravaneer smoke fact.
SEED = "north-star-2"
SAVE_UUID = "whiterun-save-1"
HOUSEHOLD = (FROTHAR, NELKIR)


def _scripted_setup(driver) -> None:
    """All pre-run scripted writes; the tick loop then carries the rumor city-wide and beyond."""
    # build_driver() installs two roles via driver.install_role() (lane 51),
    # each an engine-internal event that consumes a branch seq -- the
    # assassination's own seq must skip past them, not assume seq=1.
    death_seq = max((event.seq for event in driver.event_log.lineage(SAVE_UUID, 0)), default=0) + 1
    driver.inject_event(
        NPCDied(
            tick=0, save_uuid=SAVE_UUID, generation=0, seq=death_seq,
            gamets=0.0, wall_ts=0.0, npc_id=DECEASED,
            cause="assassination", killer_id=KILLER, location_id="dragonsreach",
        ),
        origin={"kind": "scenario", "detail": "run_north_star_demo"},
    )
    for witness_id in (*HOUSEHOLD, HOUSECARL, STEWARD, GUARD):
        driver.witness(
            claim_id=DEATH_CLAIM_ID,
            belief_id=f"belief-{witness_id}-death",
            evidence_id=f"evidence-{witness_id}-death",
            kind=DEATH_CLAIM_KIND,
            slots={
                "deceased": DECEASED, "cause": "assassination", "location": "dragonsreach",
                "weapon": "a dagger", "killer": KILLER,
            },
            canonical_event_key=EventKey(SAVE_UUID, 0, death_seq),
            witness_id=witness_id,
            gamets=0.0,
        )
    for kin_id in HOUSEHOLD:
        belief = driver.belief_of(kin_id, DEATH_CLAIM_ID)
        relationship = driver.social.any_relationship(kin_id, DECEASED)
        driver.form_grudge(
            id=f"grudge-{kin_id}-killer", holder_id=kin_id, victim_id=DECEASED, target_id=KILLER,
            grievance_type="murder", source_belief_id=belief.id, evidentiary_strength=belief.confidence,
            relationship_to_victim=relationship, gamets=0.0,
        )


def main() -> None:
    driver = build_driver(RUN_ID, SEED)
    _scripted_setup(driver)
    driver.run(0, END_TICK)
    driver.close()

    run_dir = default_runs_dir() / RUN_ID
    counts: Counter[str] = Counter()
    for stream, type_field in (("events.jsonl", "event_type"), ("trace.jsonl", "record_type")):
        for line in (run_dir / stream).open():
            payload = json.loads(line)["payload"]
            record_type = payload.get(type_field) or payload.get("record_type", "?")
            counts[f"{stream}:{record_type}"] += 1
    for key, count in sorted(counts.items()):
        print(f"{key}: {count}")

    # The four vision beats, smoke-checked.
    missing = []
    if driver.roles.holder_of(JARL_ROLE) is None:
        missing.append("jarl role stayed vacant")
    if driver.roles.holder_of(STEWARD_ROLE) != STEWARD:
        missing.append("steward role disturbed")
    if counts["events.jsonl:schedule_rewrite"] != len(HOUSEHOLD):
        missing.append(f"schedule_rewrite (expected {len(HOUSEHOLD)}, one per household member)")
    for kin_id in HOUSEHOLD:
        if not driver.social.grudges_of(kin_id):
            missing.append(f"{kin_id} holds no grudge")

    markarth_mutated = []
    for resident_id in MARKARTH_RESIDENTS:
        belief = driver.belief_of(resident_id, DEATH_CLAIM_ID)
        if belief is None:
            continue
        chain_holders = {b.holder_id for b, _ in driver.chain_for(belief.id)}
        variant = driver.claims.variant(belief.variant_id) if belief.variant_id else None
        if CARAVANEER in chain_holders and variant is not None and variant.slots["weapon"] != "a dagger":
            markarth_mutated.append((resident_id, variant.slots["weapon"]))
    if not markarth_mutated:
        missing.append("no mutated variant reached Markarth via the carrier")
    else:
        print(f"Markarth's mutated belief(s): {markarth_mutated}")

    reputation_rows = 0
    for line in (run_dir / "trace.jsonl").open():
        if json.loads(line)["payload"].get("record_type") == "reputation_updated":
            reputation_rows += 1
    if reputation_rows == 0:
        missing.append("no reputation substrate for the ripple aggregate")
    else:
        print(f"reputation_updated rows (the ripple's substrate): {reputation_rows}")

    print(f"jarl succeeded by: {driver.roles.holder_of(JARL_ROLE)}")
    print(f"priest ever informed: {driver.belief_of(PRIEST, DEATH_CLAIM_ID) is not None}")
    print(f"smoke: {'OK' if not missing else f'MISSING {missing}'}")
    print(f"run written: {run_dir}")


if __name__ == "__main__":
    main()
