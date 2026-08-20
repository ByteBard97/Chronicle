"""The append-only event log.

Chronicle's core is event-sourced: every fact about the simulated world
enters as an immutable Event, and all derived state (beliefs, rumors,
grudges, reputation) is computed by folding over the log, never mutated
directly. This makes the sim replayable, debuggable, and testable without
a running game.

Skyrim's save topology is a DAG, not a line (see
docs/decisions/0004-timeline-branching.md): every event carries a branch
key (save_uuid, generation), and state is derived by traversing root->head
along one branch's lineage, not by folding over every event ever recorded.
Reloading an earlier save forks a new generation; it never rewrites or
deletes the abandoned suffix.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Event:
    """Base type for everything appended to the log. Never mutated after creation."""

    tick: int
    save_uuid: str
    generation: int


@dataclass(frozen=True)
class NPCDied(Event):
    """An NPC's death, however it happened (combat, script, console command)."""

    npc_id: str
    cause: str
    killer_id: str | None = None
    location_id: str | None = None


@dataclass(frozen=True)
class CrimeWitnessed(Event):
    """An NPC observed another NPC (often the player) commit a crime."""

    witness_id: str
    perpetrator_id: str
    crime_type: str
    location_id: str | None = None


@dataclass(frozen=True)
class RumorHeard(Event):
    """An NPC received a rumor from a source, possibly mutated from the original."""

    hearer_id: str
    source_id: str
    rumor_id: str
    content: str


@dataclass(frozen=True)
class BranchKey:
    """Identifies one branch of a save's timeline. See ADR-0004."""

    save_uuid: str
    generation: int


class EventLog:
    """An append-only, branch-aware sequence of events.

    Events are stored per branch. State for a branch is derived by
    traversing its lineage back to the root: events inherited from the
    parent branch up to the fork point, followed by everything appended
    directly under this branch. Forking never mutates or deletes the
    branch it forked from -- the abandoned suffix stays recorded, just
    unreachable from the new branch's lineage.
    """

    def __init__(self) -> None:
        self._events: dict[BranchKey, list[Event]] = {}
        self._parent: dict[BranchKey, tuple[BranchKey, int]] = {}

    def append(self, event: Event) -> None:
        key = BranchKey(event.save_uuid, event.generation)
        self._events.setdefault(key, []).append(event)

    def fork(self, save_uuid: str, from_generation: int, at_event_count: int) -> int:
        """Fork a new branch from (save_uuid, from_generation) at at_event_count events.

        Returns the new generation number. Everything appended to the
        parent branch beyond at_event_count becomes an abandoned suffix,
        excluded from the new branch's lineage but never deleted.
        """
        parent = BranchKey(save_uuid, from_generation)
        new_generation = from_generation + 1
        child = BranchKey(save_uuid, new_generation)
        self._parent[child] = (parent, at_event_count)
        return new_generation

    def lineage(self, save_uuid: str, generation: int) -> tuple[Event, ...]:
        """Derive state: fold events from the root along this branch's lineage to its head."""
        key = BranchKey(save_uuid, generation)
        if key in self._parent:
            parent, at_event_count = self._parent[key]
            inherited = self.lineage(parent.save_uuid, parent.generation)[:at_event_count]
        else:
            inherited = ()
        return inherited + tuple(self._events.get(key, ()))

    def all(self) -> tuple[Event, ...]:
        """Every event ever recorded, across every branch. For debugging/GC, not state derivation."""
        return tuple(event for events in self._events.values() for event in events)


def of_type(events: tuple[Event, ...], event_type: type[Event]) -> tuple[Event, ...]:
    return tuple(e for e in events if isinstance(e, event_type))
