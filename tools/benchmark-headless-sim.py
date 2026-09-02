"""Per-tick latency benchmark for the headless Chronicle sim (infra-only, no design decisions).

Loads the real Whiterun fixture set (chronicle/fixtures/whiterun_schedule.py +
whiterun_relationships.py, ~19 NPCs) through the same Driver/run() path
scenarios/run_jarl_death_demo.py uses, and times it tick-by-tick via the
public Driver.run(start, end) API called one tick at a time -- this measures
exactly what a real run pays per tick, including the writer's per-tick flush
(the writer discipline documented in chronicle/framelog.py), not a stripped-down
timing of internal state transitions alone.

For the 150-NPC scale, the fixture set is cloned N times with every npc_id
and location_id suffixed "__gK" per clone group -- schedule.py's
sample_encounters() groups strictly by location_id (npcs_present_at()), so
distinct suffixes make each clone group an independent, non-interacting
population rather than 8 copies colliding into one another's encounters.
This scales total present-NPC and total relationship-edge count linearly
without inventing new fixture data.

Usage:
    uv run python tools/benchmark-headless-sim.py
    uv run python tools/benchmark-headless-sim.py --ticks 500 --clones 1 4 8
"""

from __future__ import annotations

import argparse
import statistics
import tempfile
import time
from pathlib import Path

from chronicle.driver import Driver
from chronicle.fixtures.whiterun_relationships import _EDGE_SPECS
from chronicle.fixtures.whiterun_schedule import whiterun_schedule
from chronicle.schedule import ScheduleBlock


def _cloned_schedule(n_clones: int) -> tuple[ScheduleBlock, ...]:
    base = whiterun_schedule()
    return tuple(
        ScheduleBlock(
            npc_id=f"{block.npc_id}__g{group}",
            location_id=f"{block.location_id}__g{group}",
            start_tick=block.start_tick,
            end_tick=block.end_tick,
        )
        for group in range(n_clones)
        for block in base
    )


def _cloned_edge_specs(n_clones: int) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for group in range(n_clones):
        for spec in _EDGE_SPECS:
            clone = dict(spec)
            clone["id"] = f"{spec['id']}__g{group}"
            clone["from_id"] = f"{spec['from_id']}__g{group}"
            clone["to_id"] = f"{spec['to_id']}__g{group}"
            out.append(clone)
    return out


def run_benchmark(n_clones: int, ticks: int, runs_dir: Path) -> dict[str, float]:
    schedule = _cloned_schedule(n_clones)
    edge_specs = _cloned_edge_specs(n_clones)
    n_npcs = len({block.npc_id for block in schedule})

    driver = Driver(
        run_id=f"benchmark-{n_clones}x-{ticks}t",
        seed_id=f"benchmark-seed-{n_clones}x",
        save_uuid=f"benchmark-save-{n_clones}x",
        generation=0,
        schedule=schedule,
        encounter_probability=0.35,
        runs_dir=runs_dir,
    )
    for spec in edge_specs:
        driver.form_relationship(**spec, gamets=0.0)

    latencies_s: list[float] = []
    for tick in range(ticks):
        start = time.perf_counter()
        driver.run(tick, tick + 1)
        latencies_s.append(time.perf_counter() - start)
    driver.close()

    latencies_ms = sorted(latency * 1000 for latency in latencies_s)
    return {
        "n_npcs": n_npcs,
        "n_edges": len(edge_specs),
        "ticks": ticks,
        "mean_ms": statistics.fmean(latencies_ms),
        "p50_ms": latencies_ms[len(latencies_ms) // 2],
        "p99_ms": latencies_ms[min(len(latencies_ms) - 1, int(len(latencies_ms) * 0.99))],
        "max_ms": latencies_ms[-1],
        "total_s": sum(latencies_s),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ticks", type=int, default=1000)
    parser.add_argument(
        "--clones",
        type=int,
        nargs="+",
        default=[1, 8],
        help="Fixture-set clone counts to benchmark (1 = ~19 NPCs, 8 = ~150 NPCs).",
    )
    args = parser.parse_args()

    print(f"{'clones':>6} {'npcs':>5} {'edges':>6} {'ticks':>6} {'mean_ms':>9} {'p50_ms':>9} {'p99_ms':>9} {'max_ms':>9}")
    with tempfile.TemporaryDirectory(prefix="chronicle-benchmark-") as tmp:
        runs_dir = Path(tmp)
        for n_clones in args.clones:
            result = run_benchmark(n_clones, args.ticks, runs_dir)
            print(
                f"{n_clones:>6} {result['n_npcs']:>5} {result['n_edges']:>6} {result['ticks']:>6} "
                f"{result['mean_ms']:>9.3f} {result['p50_ms']:>9.3f} {result['p99_ms']:>9.3f} {result['max_ms']:>9.3f}"
            )


if __name__ == "__main__":
    main()
