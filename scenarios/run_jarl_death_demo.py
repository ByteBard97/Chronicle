"""Generate a real demo run into runs/: the Jarl's death over 10 game-days.

Not a test — a runnable demo producer (pytest ignores it: no test_ prefix).
The output is a frame log per docs/frame-log-schema.md v1 that the dashboard
(RunPicker) and the agent-debug CLI (python -m chronicle inspect/trace/feed)
both read. Deterministic: same seed, same log (chronicle/tests/
test_determinism.py proves the property this script relies on).

    uv run python scenarios/run_jarl_death_demo.py
"""

from chronicle.claims import EventKey
from chronicle.driver import Driver
from chronicle.events import CrimeWitnessed, NPCDied
from chronicle.fixtures.whiterun_relationships import seed_whiterun_via_driver
from chronicle.fixtures.whiterun_schedule import whiterun_schedule

RUN_ID = "whiterun-jarl-01"
SEED = "jarl-death-demo"
TICKS = 240  # 10 game-days at ADR-0010's hour quantum


def main() -> None:
    driver = Driver(
        run_id=RUN_ID,
        seed_id=SEED,
        save_uuid="whiterun-save-1",
        generation=0,
        schedule=whiterun_schedule(),
        encounter_probability=0.35,
    )
    seed_whiterun_via_driver(driver, gamets=0.0)
    driver.inject_event(
        NPCDied(
            tick=0, save_uuid="whiterun-save-1", generation=0, seq=1,
            gamets=0.0, wall_ts=0.0, npc_id="jarl_balgruuf",
            cause="assassination", killer_id=None, location_id="dragonsreach",
        ),
        origin={"kind": "scenario", "detail": "run_jarl_death_demo"},
    )
    driver.inject_event(
        CrimeWitnessed(
            tick=0, save_uuid="whiterun-save-1", generation=0, seq=2,
            gamets=0.0, wall_ts=1.0, witness_id="proventus",
            perpetrator_id="unknown", crime_type="murder",
            location_id="dragonsreach",
        ),
        origin={"kind": "scenario", "detail": "run_jarl_death_demo"},
    )
    driver.witness(
        claim_id="claim-jarl-death",
        belief_id="belief-irileth-death",
        evidence_id="evidence-irileth-death",
        kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "dragonsreach"},
        canonical_event_key=EventKey("whiterun-save-1", 0, 1),
        witness_id="irileth",
        gamets=0.0,
    )
    driver.run(0, TICKS)
    driver.close()

    from chronicle.framelog import default_runs_dir

    run_dir = default_runs_dir() / RUN_ID
    for stream in ("events.jsonl", "trace.jsonl"):
        path = run_dir / stream
        n = sum(1 for _ in path.open())
        print(f"{stream}: {n} records")
    print(f"run written: {run_dir}")


if __name__ == "__main__":
    main()
