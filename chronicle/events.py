"""The append-only event log -- layer 1 of Chronicle's data-ownership model.

Chronicle's core is event-sourced: every fact about the simulated world
enters as an immutable Event, and all derived state (beliefs, rumors,
grudges, reputation) is computed by folding over the log, never mutated
directly. This makes the sim replayable, debuggable, and testable without
a running game.

This module owns only the canonical event log -- what objectively
happened (docs/decisions/0006-data-ownership-layers.md, layer 1). It is
the only objective layer; everything built on top of it is observer-
relative and lives elsewhere:

  - layer 2, claim/variant store: typed claims derived from events, plus
    mutated variants (a rumor's retelling), each linked to its predecessor.
  - layer 3, subjective belief store: per-NPC BeliefInstance records --
    what a given NPC believes, with confidence, evidence, and provenance,
    which may diverge from what this log says actually happened.
  - layer 4, social state store: sparse relationships, grudges,
    obligations, and observer-local reputation.
  - layer 5, narrative/query layer: story sifters, quest hooks, the
    dashboard's causality-timeline drill-down
    (docs/decisions/0007-inspectability.md).

Canonical events in this log never mutate once appended -- a claim built
from an event can be superseded by a new variant, but the originating
event itself is permanent. This is what lets every derived belief, rumor,
or grudge answer "since when, from what evidence" (ADR-0007) by walking
back through claims/variants to the event(s) that grounded them.

Skyrim's save topology is a DAG, not a line (see
docs/decisions/0004-timeline-branching.md): every event carries a branch
key (save_uuid, generation), and state is derived by traversing root->head
along one branch's lineage, not by folding over every event ever recorded.
Reloading an earlier save forks a new generation; it never rewrites or
deletes the abandoned suffix.

Every event also carries an idempotency key -- (save_uuid, generation,
seq), seq monotonic per branch -- and both bitemporal time coordinates:
gamets (Skyrim's in-game clock -- valid time, when the fact is true in
the modeled reality) and wall_ts (real time the event was durably
appended -- transaction time). Both are mandatory, never None: a write
missing either is rejected outright, because a nullable/optional time
field is exactly what broke two other Skyrim external-state mods in
production (see docs/decisions/0004-timeline-branching.md's bitemporal
rule, and docs/research/09-save-sync-forensics.md for the incidents that
motivate it). (save_uuid, generation, seq) lets EventLog.append() be
idempotent -- replays, retried network posts, and double-fired Papyrus
events become no-ops on a duplicate key rather than double-counted state.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Event:
    """Base type for everything appended to the log. Never mutated after creation."""

    tick: int
    save_uuid: str
    generation: int
    seq: int
    gamets: float
    wall_ts: float


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
class EscalationWarning(Event):
    """A threshold rule's escalation, materialized as an event BEFORE its claim propagates (ladder T3.1).

    Engine-internal (origin None): the accumulation-threshold rule (11)
    injects this when a holder's grievance accumulator crosses its
    threshold; the warning claim is then witnessed off this event's
    canonical key, so no belief is ever orphaned from the log.
    """

    holder_id: str
    grievance_kind: str
    count: int
    threshold: int


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

    append() is idempotent on (save_uuid, generation, seq): appending an
    event whose key was already seen is a no-op. This is what makes
    reconnect replays, retried network posts, and double-fired Papyrus
    events safe by construction (docs/decisions/0005-sync-handshake.md).
    """

    def __init__(self) -> None:
        self._events: dict[BranchKey, list[Event]] = {}
        self._parent: dict[BranchKey, tuple[BranchKey, int]] = {}
        self._seen_seqs: dict[BranchKey, set[int]] = {}

    def append(self, event: Event) -> bool:
        """Append event; returns False (no-op) if its (branch, seq) was already appended."""
        key = BranchKey(event.save_uuid, event.generation)
        seen = self._seen_seqs.setdefault(key, set())
        if event.seq in seen:
            return False
        seen.add(event.seq)
        self._events.setdefault(key, []).append(event)
        return True

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
