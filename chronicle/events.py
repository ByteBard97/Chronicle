"""The append-only event log.

Chronicle's core is event-sourced: every fact about the simulated world
enters as an immutable Event, and all derived state (beliefs, rumors,
grudges, reputation) is computed by folding over the log, never mutated
directly. This makes the sim replayable, debuggable, and testable without
a running game.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Event:
    """Base type for everything appended to the log. Never mutated after creation."""

    tick: int


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


class EventLog:
    """An append-only sequence of events. State is derived by folding over it."""

    def __init__(self) -> None:
        self._events: list[Event] = []

    def append(self, event: Event) -> None:
        self._events.append(event)

    def all(self) -> tuple[Event, ...]:
        return tuple(self._events)

    def of_type(self, event_type: type[Event]) -> tuple[Event, ...]:
        return tuple(e for e in self._events if isinstance(e, event_type))
