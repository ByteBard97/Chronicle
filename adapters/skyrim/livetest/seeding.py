"""Seed Chronicle state into the live run -- wraps the verified two-step recipe.

Nothing here reimplements the recipe: ``tools/chronicle-devbench-runbook.py``'s
``seed_crime_witnessed_grudge`` (inject a real ``crime_witnessed`` event,
then derive grudge/belief through ``Driver.crime_witnessed``) is imported
and called. See ``docs/design/chronicle-bridge-verification-runbook.md``
correction #11 for why that recipe is real rather than a workaround.
"""

from __future__ import annotations

import importlib.util
import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from types import ModuleType

from .harness import GLOBALS_JSON, REPO_ROOT

RUNBOOK_TOOL = REPO_ROOT / "tools" / "chronicle-devbench-runbook.py"
PLAYER_ID = "the_player"


@cache
def runbook_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("chronicle_devbench_runbook", RUNBOOK_TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _seed(*, run_id: str, runs_dir: Path, witness: str, perpetrator: str, self_victim: bool, gamets: float, crime_type: str, location_id: str) -> str:
    ok, message = runbook_module().seed_crime_witnessed_grudge(
        run_id=run_id,
        runs_dir=str(runs_dir),
        witness_id=witness,
        perpetrator_id=perpetrator,
        crime_type=crime_type,
        self_victim=self_victim,
        location_id=location_id,
        gamets=gamets,
    )
    if not ok:
        raise RuntimeError(f"seeding failed: {message}")
    return message


def seed_grudge(*, run_id: str, runs_dir: Path, holder: str, target: str, gamets: float, crime_type: str = "assault") -> str:
    """NPC->NPC (or NPC->the_player) grudge at severity 1.0, plus the witness belief."""
    return _seed(run_id=run_id, runs_dir=runs_dir, witness=holder, perpetrator=target, self_victim=True, gamets=gamets, crime_type=crime_type, location_id="whiterun")


def seed_belief(*, run_id: str, runs_dir: Path, holder: str, gamets: float) -> str:
    """Bystander belief only (confidence 0.95), no grudge -- the diegetic-evidence precondition."""
    return _seed(run_id=run_id, runs_dir=runs_dir, witness=holder, perpetrator="unknown", self_victim=False, gamets=gamets, crime_type="theft", location_id="whiterun")


@dataclass(frozen=True)
class AvoidanceGlobal:
    npc_a: str
    npc_b: str
    editor_id: str
    local_form_id: int
    plugin: str


@cache
def _avoidance_table() -> dict[tuple[str, str], AvoidanceGlobal]:
    rows = json.loads(GLOBALS_JSON.read_text())
    table: dict[tuple[str, str], AvoidanceGlobal] = {}
    for row in rows:
        entry = AvoidanceGlobal(row["npcA"], row["npcB"], row["globalEditorId"], int(row["globalLocalFormId"], 16), row["plugin"])
        table[(entry.npc_a, entry.npc_b)] = entry
    return table


def avoidance_global(npc_a: str, npc_b: str) -> AvoidanceGlobal:
    """The patcher-authored gating global for a pair (order-insensitive)."""
    key = tuple(sorted((npc_a, npc_b)))
    try:
        return _avoidance_table()[key]  # type: ignore[index]
    except KeyError:
        raise KeyError(f"no avoidance global for pair {key}; is {GLOBALS_JSON} current?") from None
