"""The frame log: writer and reader for Chronicle's run logs (docs/frame-log-schema.md v1).

Physical layout (ui-spec §1.1, frozen): one directory per run --
``runs/<run_id>/`` -- with physically split stream files ``events.jsonl``
(what the world did) and ``trace.jsonl`` (why the sim did it), a sidecar
``index.json`` (per-stream tick -> byte offset, plus keyframe offsets), and
a run registry ``runs/index.json``. The log contains exactly three things
(ui-spec §1.1's three-things rule): inputs (canonical events), derivations
with their inputs (the trace), and acceleration structures (keyframes and
indexes, rebuildable by scanning the first two).

Writer discipline, per the schema doc:

  - newline-delimited JSON, one record per line; readers treat a
    non-terminated tail as not-yet-written (never a torn record);
  - flush after every tick's record batch (the liveness contract: LIVE-tail
    latency is the reader's polling cadence, never the writer's buffer);
  - index and registry writes are atomic write-temp-rename;
  - ``runs/`` is overridable via the ``CHRONICLE_RUNS_DIR`` env var, shared
    by pytest and the dashboard (ui-spec §1.2).

Reader discipline: derived state at any tick T is reconstructed from the log
alone -- nearest keyframe at or before T, then trace records after the
keyframe replayed through the same claims.py/social.py constructors that
produced them live, with decay applied analytically at read time
(claims.py:decay -- never sampled into the log).
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self

from chronicle.claims import (
    BeliefInstance,
    Claim,
    ClaimStore,
    EventKey,
    Evidence,
    RumorState,
    Variant,
)
from chronicle.events import CrimeWitnessed, Event, NPCDied, RumorHeard
from chronicle.schedule import ScheduleBlock
from chronicle.social import (
    Grudge,
    Obligation,
    Relationship,
    Reputation,
    SocialStateStore,
)

SCHEMA_VERSION = 1
DEFAULT_KEYFRAME_INTERVAL = 24  # ticks -- one game-day (ADR-0010, schema §5)

EVENTS_STREAM = "events"
TRACE_STREAM = "trace"
STREAM_FILES = {EVENTS_STREAM: "events.jsonl", TRACE_STREAM: "trace.jsonl"}


def default_runs_dir() -> Path:
    """Where run logs live: ``$CHRONICLE_RUNS_DIR`` if set, else ``<repo>/runs/`` (ui-spec §1.2)."""
    override = os.environ.get("CHRONICLE_RUNS_DIR")
    if override:
        return Path(override)
    return Path(__file__).resolve().parent.parent / "runs"


# ---------------------------------------------------------------------------
# Payload serialization: store records <-> keyframe state (schema §5).
# Field names and types mirror the claims.py/social.py/schedule.py
# dataclasses exactly -- the keyframe is a serialization of the stores, not
# a remodel. Decayed strengths, dormant/forgotten stages, and reputation
# means are deliberately absent (derived analytically at read time).
# ---------------------------------------------------------------------------


def _event_key_json(key: EventKey) -> dict[str, object]:
    # Tolerate plain-tuple keys from pre-ADR-0009 call sites (claims.py only
    # ever used the key as a dict key, so both forms exist in stores).
    key = EventKey(*key)
    return {"save_uuid": key.save_uuid, "generation": key.generation, "seq": key.seq}


def _claim_json(claim: Claim) -> dict[str, object]:
    return {
        "id": claim.id,
        "kind": claim.kind,
        "slots": dict(claim.slots),
        "canonical_event_key": _event_key_json(claim.canonical_event_key),
        "truth_status": claim.truth_status,
    }


def _variant_json(variant: Variant) -> dict[str, object]:
    return {
        "id": variant.id,
        "claim_id": variant.claim_id,
        "parent_variant_id": variant.parent_variant_id,
        "slots": dict(variant.slots),
        "mutated_slot": variant.mutated_slot,
        "gamets": variant.gamets,
    }


def _belief_json(belief: BeliefInstance) -> dict[str, object]:
    return {
        "id": belief.id,
        "holder_id": belief.holder_id,
        "claim_id": belief.claim_id,
        "variant_id": belief.variant_id,
        "confidence": belief.confidence,
        "verbatim_strength": belief.verbatim_strength,
        "gist_strength": belief.gist_strength,
        "first_learned": belief.first_learned,
        "last_rehearsed": belief.last_rehearsed,
    }


def _evidence_json(evidence: Evidence) -> dict[str, object]:
    return {
        "id": evidence.id,
        "belief_id": evidence.belief_id,
        "evidence_type": evidence.evidence_type,
        "source_id": evidence.source_id,
        "predecessor_belief_id": evidence.predecessor_belief_id,
        "gamets": evidence.gamets,
        "strength": evidence.strength,
    }


def _rumor_json(rumor: RumorState) -> dict[str, object]:
    return {
        "npc_id": rumor.npc_id,
        "claim_id": rumor.claim_id,
        "variant_id": rumor.variant_id,
        "stage": rumor.stage,
        "first_heard": rumor.first_heard,
        "last_heard": rumor.last_heard,
        "last_told": rumor.last_told,
        "exposure_count": rumor.exposure_count,
        "distinct_source_count": rumor.distinct_source_count,
    }


def _relationship_json(rel: Relationship) -> dict[str, object]:
    return {
        "id": rel.id,
        "from_id": rel.from_id,
        "to_id": rel.to_id,
        "basis": rel.basis,
        "basis_id": rel.basis_id,
        "strength": rel.strength,
        "formed_at": rel.formed_at,
        "last_updated": rel.last_updated,
    }


def _grudge_json(grudge: Grudge) -> dict[str, object]:
    return {
        "id": grudge.id,
        "holder_id": grudge.holder_id,
        "target_id": grudge.target_id,
        "source_belief_id": grudge.source_belief_id,
        "grievance_type": grudge.grievance_type,
        "severity": grudge.severity,
        "emotional_strength": grudge.emotional_strength,
        "evidentiary_strength": grudge.evidentiary_strength,
        "last_rehearsed": grudge.last_rehearsed,
        "forgiveness_threshold": grudge.forgiveness_threshold,
    }


def _obligation_json(obligation: Obligation) -> dict[str, object]:
    return {
        "id": obligation.id,
        "issuer_id": obligation.issuer_id,
        "debtor_id": obligation.debtor_id,
        "beneficiary_id": obligation.beneficiary_id,
        "action": obligation.action,
        "condition": obligation.condition,
        "deadline": obligation.deadline,
        "status": obligation.status,
        "witnesses": list(obligation.witnesses),
        "sanctions": obligation.sanctions,
        "excuse": obligation.excuse,
        "created_at": obligation.created_at,
        "fulfilled_at": obligation.fulfilled_at,
        "violated_at": obligation.violated_at,
    }


def _reputation_json(rep: Reputation) -> dict[str, object]:
    return {
        "observer_id": rep.observer_id,
        "subject_id": rep.subject_id,
        "context": rep.context,
        "alpha": rep.alpha,
        "beta": rep.beta,
        "direct_count": rep.direct_count,
        "witness_count": rep.witness_count,
        "certified_count": rep.certified_count,
        "uncertainty": rep.uncertainty,
        "last_updated": rep.last_updated,
    }


def _schedule_json(block: ScheduleBlock) -> dict[str, object]:
    return {
        "npc_id": block.npc_id,
        "location_id": block.location_id,
        "start_tick": block.start_tick,
        "end_tick": block.end_tick,
    }


def serialize_state(
    claims: ClaimStore,
    social: SocialStateStore,
    schedule: Sequence[ScheduleBlock],
    *,
    tick: int,
) -> dict[str, object]:
    """The keyframe ``state`` payload (schema §5): a full derived-state snapshot as of ``tick``.

    Lists are sorted by id so two independently-built snapshots of equal
    state compare equal regardless of insertion order. Schedule blocks are
    those effective (covering) as of ``tick``.
    """
    beliefs = sorted(claims._beliefs.values(), key=lambda b: b.id)
    return {
        "claims": [_claim_json(c) for c in sorted(claims._claims.values(), key=lambda c: c.id)],
        "variants": [_variant_json(v) for v in sorted(claims._variants.values(), key=lambda v: v.id)],
        "beliefs": [_belief_json(b) for b in beliefs],
        "evidence": [
            _evidence_json(e)
            for belief in beliefs
            for e in claims._evidence_by_belief[belief.id]
        ],
        "rumor_states": [_rumor_json(r) for r in sorted(claims._rumors.values(), key=lambda r: (r.npc_id, r.claim_id, r.variant_id or ""))],
        # The distinct-source exposure sets behind rumor_states' counts
        # (schema §5's rumor_sources key): serialized directly so rule 7's
        # distinct-source counting survives a keyframe boundary exactly.
        "rumor_sources": [
            {"npc_id": npc_id, "claim_id": claim_id, "variant_id": variant_id, "source_ids": sorted(source_ids)}
            for (npc_id, claim_id, variant_id), source_ids in sorted(
                claims._rumor_sources.items(), key=lambda item: (item[0][0], item[0][1], item[0][2] or "")
            )
        ],
        "relationships": [_relationship_json(r) for r in sorted(social._relationships.values(), key=lambda r: r.id)],
        "grudges": [_grudge_json(g) for g in sorted(social._grudges.values(), key=lambda g: g.id)],
        "obligations": [_obligation_json(o) for o in sorted(social._obligations.values(), key=lambda o: o.id)],
        "reputations": [
            _reputation_json(r) for r in sorted(social._reputations.values(), key=lambda r: (r.observer_id, r.subject_id, r.context))
        ],
        "schedules": [_schedule_json(b) for b in schedule if b.covers(tick)],
    }


def load_state(claims: ClaimStore, social: SocialStateStore, state: Mapping[str, Any]) -> tuple[ScheduleBlock, ...]:
    """Load a keyframe ``state`` payload into (initially empty) stores. Returns the schedule blocks.

    Readers ignore unknown keyframe keys (schema §7: skip-and-continue), so
    per-tier additive state keys from newer logs don't break this reader.
    """
    for record in state.get("claims", ()):
        claim = Claim(
            id=record["id"],
            kind=record["kind"],
            slots=record["slots"],
            canonical_event_key=EventKey(**record["canonical_event_key"]),
            truth_status=record["truth_status"],
        )
        claims._claims[claim.id] = claim
        claims._claim_id_by_event[claim.canonical_event_key] = claim.id
    for record in state.get("variants", ()):
        variant = Variant(
            id=record["id"],
            claim_id=record["claim_id"],
            parent_variant_id=record["parent_variant_id"],
            slots=record["slots"],
            mutated_slot=record["mutated_slot"],
            gamets=record["gamets"],
        )
        claims._variants[variant.id] = variant
    for record in state.get("beliefs", ()):
        belief = BeliefInstance(**record)
        claims._beliefs[belief.id] = belief
    for record in state.get("evidence", ()):
        evidence = Evidence(**record)
        claims._evidence_by_belief.setdefault(evidence.belief_id, []).append(evidence)
    for record in state.get("rumor_states", ()):
        rumor = RumorState(**record)
        claims._rumors[(rumor.npc_id, rumor.claim_id, rumor.variant_id)] = rumor
    # _rumor_sources rides in the keyframe as "rumor_sources" (schema §5's
    # v1 completeness addition). When absent (pre-amendment v1 logs, §7's
    # skip-and-continue rule in reverse), fall back to rebuilding it from
    # each belief's original grounding evidence (index 0, the same record
    # chain_for() walks): witnessed beliefs are self-sourced, reported
    # beliefs carry their teller. Exact for any state the current claims.py
    # can produce -- every hearing creates a belief grounded in that
    # hearing's source -- but the keyframe key makes that exactness
    # structural rather than a derivation coincidence.
    rumor_sources = state.get("rumor_sources")
    if rumor_sources is not None:
        for record in rumor_sources:
            key = (record["npc_id"], record["claim_id"], record["variant_id"])
            claims._rumor_sources[key] = set(record["source_ids"])
    else:
        for belief in claims._beliefs.values():
            grounding = claims._evidence_by_belief[belief.id][0]
            claims._rumor_sources.setdefault((belief.holder_id, belief.claim_id, belief.variant_id), set()).add(grounding.source_id)
    for record in state.get("relationships", ()):
        social.add_relationship(Relationship(**record))
    for record in state.get("grudges", ()):
        social.add_grudge(Grudge(**record))
    for record in state.get("obligations", ()):
        social.add_obligation(Obligation(**{**record, "witnesses": tuple(record["witnesses"])}))
    for record in state.get("reputations", ()):
        rep = Reputation(**record)
        social._reputations[(rep.observer_id, rep.subject_id, rep.context)] = rep
    return tuple(ScheduleBlock(**record) for record in state.get("schedules", ()))


def event_payload(event: Event, *, origin: Mapping[str, str] | None) -> dict[str, object]:
    """The events-stream payload for one canonical event (schema §3)."""
    payload: dict[str, object] = {
        "gamets": event.gamets,
        "wall_ts": event.wall_ts,
        "origin": dict(origin) if origin is not None else None,
    }
    if isinstance(event, NPCDied):
        payload["event_type"] = "npc_died"
        payload.update(npc_id=event.npc_id, cause=event.cause, killer_id=event.killer_id, location_id=event.location_id)
    elif isinstance(event, CrimeWitnessed):
        payload["event_type"] = "crime_witnessed"
        payload.update(
            witness_id=event.witness_id,
            perpetrator_id=event.perpetrator_id,
            crime_type=event.crime_type,
            location_id=event.location_id,
        )
    elif isinstance(event, RumorHeard):
        payload["event_type"] = "rumor_heard"
        payload.update(hearer_id=event.hearer_id, source_id=event.source_id, rumor_id=event.rumor_id, content=event.content)
    else:
        raise TypeError(f"no events-stream payload mapping for {type(event).__name__} -- extend chronicle/framelog.py (schema §3)")
    return payload


# ---------------------------------------------------------------------------
# Writer
# ---------------------------------------------------------------------------


def _atomic_write_json(path: Path, data: Mapping[str, Any]) -> None:
    """Write-temp-rename (schema §1: index writes are atomic)."""
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp:
            json.dump(data, tmp, indent=2)
            tmp.write("\n")
        os.replace(tmp_name, path)
    except BaseException:
        os.unlink(tmp_name)
        raise


class FrameLogWriter:
    """Writes one run's frame log under ``runs/<run_id>/`` (schema §1, §6).

    One instance per run. Call ``flush()`` after every tick's record batch
    (the driver does) -- the liveness contract. ``close()`` writes the final
    index and marks the registry entry complete.
    """

    def __init__(
        self,
        *,
        run_id: str,
        seed_id: str,
        save_uuid: str,
        generation: int,
        runs_dir: Path | None = None,
    ) -> None:
        self.run_id = run_id
        self.seed_id = seed_id
        self.save_uuid = save_uuid
        self.generation = generation
        self.runs_dir = runs_dir if runs_dir is not None else default_runs_dir()
        self.run_dir = self.runs_dir / run_id
        if self.run_dir.exists():
            raise FileExistsError(f"run directory {self.run_dir} already exists -- frame logs are append-only; pick a new run_id")
        self.run_dir.mkdir(parents=True)

        self._files: dict[str, Any] = {}
        self._offsets: dict[str, int] = {}
        self._seqs: dict[str, int] = {}
        # The events-stream seq namespace is shared between canonical events
        # (whose envelope seq IS Event.seq, schema §2) and keyframes (which
        # have no Event.seq of their own): a keyframe carries the highest
        # canonical-event seq written so far and does NOT consume a seq
        # number, so a canonical event appended after a keyframe never
        # collides with it. -1 until the first canonical event.
        self._event_seq_high_water = -1
        self._tick_offsets: dict[str, dict[str, int]] = {EVENTS_STREAM: {}, TRACE_STREAM: {}}
        self._keyframe_offsets: list[dict[str, int]] = []
        self._tick_min: int | None = None
        self._tick_max: int | None = None
        self._created_wall_ts = time.time()
        self._closed = False

        for stream, filename in STREAM_FILES.items():
            self._files[stream] = open(self.run_dir / filename, "wb")  # noqa: SIM115 -- closed in close()
            self._offsets[stream] = 0
            self._seqs[stream] = 0
        self._write_index()
        self._register(status="running")

    def _envelope(self, *, stream: str, tick: int, seq: int, payload: Mapping[str, Any]) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "seed_id": self.seed_id,
            "save_uuid": self.save_uuid,
            "generation": self.generation,
            "tick": tick,
            "stream": stream,
            "seq": seq,
            "payload": payload,
        }

    def _append(self, stream: str, *, tick: int, seq: int, payload: Mapping[str, Any]) -> None:
        if self._closed:
            raise ValueError("writer is closed")
        record = self._envelope(stream=stream, tick=tick, seq=seq, payload=payload)
        line = (json.dumps(record) + "\n").encode("utf-8")
        offset = self._offsets[stream]
        self._files[stream].write(line)
        self._offsets[stream] += len(line)
        self._tick_offsets[stream].setdefault(str(tick), offset)
        self._tick_min = tick if self._tick_min is None else min(self._tick_min, tick)
        self._tick_max = tick if self._tick_max is None else max(self._tick_max, tick)

    def write_event(self, *, tick: int, seq: int, payload: Mapping[str, Any]) -> None:
        """Append one canonical-event record; its envelope seq IS the Event.seq (schema §2)."""
        self._event_seq_high_water = max(self._event_seq_high_water, seq)
        self._append(EVENTS_STREAM, tick=tick, seq=seq, payload=payload)

    def write_trace(self, *, tick: int, payload: Mapping[str, Any]) -> None:
        """Append one trace record; seq is monotonic within trace.jsonl, independent of event seqs (schema §2)."""
        seq = self._seqs[TRACE_STREAM]
        self._seqs[TRACE_STREAM] += 1
        self._append(TRACE_STREAM, tick=tick, seq=seq, payload=payload)

    def write_keyframe(self, *, tick: int, state: Mapping[str, Any]) -> None:
        """Append a keyframe record to the events stream (schema §5) and record its offset in the index.

        The keyframe's seq is the highest canonical-event seq written so
        far (-1 if none yet) -- it does not consume a seq number, so a
        canonical event appended after this keyframe never collides with
        it; the stream's seq is monotonic non-decreasing, file order the
        true order (schema §2).
        """
        self._keyframe_offsets.append({"tick": tick, "offset": self._offsets[EVENTS_STREAM]})
        self._append(
            EVENTS_STREAM,
            tick=tick,
            seq=self._event_seq_high_water,
            payload={"record_type": "keyframe", "state": state},
        )

    def flush(self) -> None:
        """Commit the current tick's record batch, then atomically refresh the sidecar index.

        The liveness contract (schema §1): LIVE-tailing latency is the
        reader's polling cadence, never this writer's buffer length.
        """
        for f in self._files.values():
            f.flush()
        self._write_index()

    def _write_index(self) -> None:
        _atomic_write_json(self.run_dir / "index.json", self._index_data())

    def _index_data(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "streams": {
                EVENTS_STREAM: {
                    "tick_offsets": self._tick_offsets[EVENTS_STREAM],
                    "keyframe_offsets": self._keyframe_offsets,
                },
                TRACE_STREAM: {"tick_offsets": self._tick_offsets[TRACE_STREAM]},
            },
        }

    def _register(self, *, status: str) -> None:
        """Upsert this run into the runs registry ``runs/index.json`` (schema §6), preserving entries owned by others."""
        registry_path = self.runs_dir / "index.json"
        registry: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "runs": []}
        if registry_path.exists():
            try:
                existing = json.loads(registry_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                existing = None
            if isinstance(existing, dict) and isinstance(existing.get("runs"), list):
                registry["runs"] = [r for r in existing["runs"] if not (isinstance(r, dict) and r.get("run_id") == self.run_id)]
        registry["runs"].append(
            {
                "run_id": self.run_id,
                "seed_id": self.seed_id,
                "created_wall_ts": self._created_wall_ts,
                "branches": [{"save_uuid": self.save_uuid, "generation": self.generation}],
                "tick_range": {"start": self._tick_min, "end": self._tick_max if status == "complete" else None},
                "streams": dict(STREAM_FILES),
                "status": status,
            }
        )
        _atomic_write_json(registry_path, registry)

    def close(self) -> None:
        """Final flush; mark the registry entry complete. Idempotent."""
        if self._closed:
            return
        self.flush()
        for f in self._files.values():
            f.close()
        self._closed = True
        self._register(status="complete")

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


# ---------------------------------------------------------------------------
# Reader
# ---------------------------------------------------------------------------


@dataclass
class ReconstructedState:
    """Derived state at one tick, rebuilt from the log alone (keyframe + replayed deltas).

    Decay is analytic at read time (claims.decay / claims.stage_at) -- the
    stored beliefs carry as-of-last-rehearsed strengths, exactly like the
    live stores; nothing decayed is ever read from or written to the log.
    """

    tick: int
    claims: ClaimStore
    social: SocialStateStore
    schedule: tuple[ScheduleBlock, ...]


def _iter_records(path: Path) -> Iterator[tuple[int, dict[str, Any]]]:
    """Yield (byte offset, record) per complete line. A non-terminated tail is treated as not-yet-written (schema §1)."""
    data = path.read_bytes()
    if not data:
        return
    lines = data.split(b"\n")
    if not data.endswith(b"\n"):
        lines = lines[:-1]  # torn tail -- a reader must never yield a partial record
    offset = 0
    for line in lines:
        if line:
            yield offset, json.loads(line)
        offset += len(line) + 1


class FrameLogReader:
    """Random access to one run's derived state at any tick, from the log alone."""

    def __init__(self, run_dir: Path | str) -> None:
        self.run_dir = Path(run_dir)

    def read_index(self) -> dict[str, Any]:
        """The writer-maintained sidecar index."""
        return json.loads((self.run_dir / "index.json").read_text(encoding="utf-8"))

    def rebuild_index(self) -> dict[str, Any]:
        """Rebuild the sidecar index by scanning both streams -- the proof that the index is pure acceleration (schema §6)."""
        tick_offsets: dict[str, dict[str, int]] = {EVENTS_STREAM: {}, TRACE_STREAM: {}}
        keyframe_offsets: list[dict[str, int]] = []
        for stream, filename in STREAM_FILES.items():
            for offset, record in _iter_records(self.run_dir / filename):
                tick_offsets[stream].setdefault(str(record["tick"]), offset)
                if stream == EVENTS_STREAM and record["payload"].get("record_type") == "keyframe":
                    keyframe_offsets.append({"tick": record["tick"], "offset": offset})
        return {
            "schema_version": SCHEMA_VERSION,
            "streams": {
                EVENTS_STREAM: {"tick_offsets": tick_offsets[EVENTS_STREAM], "keyframe_offsets": keyframe_offsets},
                TRACE_STREAM: {"tick_offsets": tick_offsets[TRACE_STREAM]},
            },
        }

    def records(self, stream: str, *, upto_tick: int | None = None) -> Iterator[dict[str, Any]]:
        """All records of one stream in file order (unknown record types tolerated, schema §7)."""
        for _, record in _iter_records(self.run_dir / STREAM_FILES[stream]):
            if upto_tick is not None and record["tick"] > upto_tick:
                continue
            yield record

    def _keyframe_at_or_before(self, tick: int) -> dict[str, Any] | None:
        index = self.read_index()
        keyframes = [k for k in index["streams"][EVENTS_STREAM]["keyframe_offsets"] if k["tick"] <= tick]
        if not keyframes:
            return None
        latest = keyframes[-1]
        with open(self.run_dir / STREAM_FILES[EVENTS_STREAM], "rb") as f:
            f.seek(latest["offset"])
            line = f.readline()
        return json.loads(line)

    def state_at(self, tick: int) -> ReconstructedState:
        """Derived state as of ``tick``: nearest keyframe + replayed trace deltas, from the log alone.

        Replay re-executes each derivation through the same claims.py
        constructors the live run used (witness/retell/corroborate), so the
        reconstructed stores -- including rumor-stage bookkeeping that has
        no trace record of its own -- match the in-memory run exactly.
        """
        claims = ClaimStore()
        social = SocialStateStore()
        schedule: tuple[ScheduleBlock, ...] = ()

        keyframe = self._keyframe_at_or_before(tick)
        replay_after = -1
        if keyframe is not None:
            replay_after = keyframe["tick"]
            schedule = load_state(claims, social, keyframe["payload"]["state"])

        # Canonical events up to T: replayed belief_formed records recover
        # their gamets from the canonical event they derive from.
        event_gamets: dict[tuple[str, int, int], float] = {}
        for record in self.records(EVENTS_STREAM, upto_tick=tick):
            payload = record["payload"]
            if payload.get("record_type") == "keyframe" or "event_type" not in payload:
                continue
            key = (record["save_uuid"], record["generation"], record["seq"])
            event_gamets[key] = payload["gamets"]

        for record in self.records(TRACE_STREAM, upto_tick=tick):
            if record["tick"] <= replay_after:
                continue
            payload = record["payload"]
            record_type = payload.get("record_type")
            if record_type == "belief_formed":
                event_key = payload["canonical_event_key"]
                gamets = event_gamets[(event_key["save_uuid"], event_key["generation"], event_key["seq"])]
                claims.witness(
                    claim_id=payload["claim_id"],
                    belief_id=payload["belief_id"],
                    evidence_id=payload["evidence_id"],
                    kind=payload["claim_kind"],
                    slots=payload["claim_slots"],
                    canonical_event_key=EventKey(event_key["save_uuid"], event_key["generation"], event_key["seq"]),
                    witness_id=payload["holder_id"],
                    gamets=gamets,
                )
            elif record_type == "transmitted":
                variant = payload["variant"]
                parent_variant_id = variant["parent_variant_id"]
                mutate_slot = variant["mutated_slot"]
                claims.retell(
                    claim=claims.claim(payload["claim_id"]),
                    parent_variant=claims.variant(parent_variant_id) if parent_variant_id is not None else None,
                    variant_id=variant["variant_id"],
                    belief_id=payload["hearer_belief_id"],
                    evidence_id=payload["evidence_id"],
                    teller_id=payload["teller_id"],
                    teller_belief=claims.chain_for(payload["teller_belief_id"])[0][0],
                    hearer_id=payload["hearer_id"],
                    gamets=float(record["tick"]),
                    mutate_slot=mutate_slot,
                    mutated_value=variant["slots"][mutate_slot] if mutate_slot is not None else None,
                )
            elif record_type == "belief_corroborated":
                claims.corroborate(
                    belief_id=payload["belief_id"],
                    source_belief=claims.chain_for(payload["source_belief_id"])[0][0],
                    evidence_id=payload["evidence_id"],
                    gamets=float(record["tick"]),
                )
            elif record_type == "supersession":
                # Re-executed through the store's resolution write path (ladder
                # T2.3), not applied as a delta: the amended payload (schema
                # §4, 2026-08-23) carries the teller/evidence ids replay needs
                # to rebuild the appended Evidence and the belief re-point +
                # dent exactly, so post-keyframe reconstruction matches the
                # live run. The recorded loser/winner/rule/dent fields let a
                # reader cross-check the re-execution; they are not inputs.
                claims.resolve(
                    claim=claims.claim(payload["claim_id"]),
                    holder_id=payload["holder_id"],
                    teller_id=payload["teller_id"],
                    teller_belief=claims.chain_for(payload["teller_belief_id"])[0][0],
                    evidence_id=payload["evidence_id"],
                    gamets=float(record["tick"]),
                )
            elif record_type == "relationship_formed":
                # The payload carries the full Relationship fields except
                # last_updated, which equals formed_at at formation (schema
                # §4) -- form_relationship() sets both to the same gamets.
                social.add_relationship(
                    Relationship(
                        id=payload["id"],
                        from_id=payload["from_id"],
                        to_id=payload["to_id"],
                        basis=payload["basis"],
                        basis_id=payload["basis_id"],
                        strength=payload["strength"],
                        formed_at=payload["formed_at"],
                        last_updated=payload["formed_at"],
                    )
                )
            elif record_type == "grudge_formed":
                # The payload carries the full Grudge fields (schema §4) --
                # the severity/emotional-strength derivation already ran
                # live inside social.form_grudge(), and the record is its
                # output, not its inputs (there is no victim_id to re-run
                # the rule-8 lookup against).
                social.add_grudge(
                    Grudge(
                        id=payload["id"],
                        holder_id=payload["holder_id"],
                        target_id=payload["target_id"],
                        source_belief_id=payload["source_belief_id"],
                        grievance_type=payload["grievance_type"],
                        severity=payload["severity"],
                        emotional_strength=payload["emotional_strength"],
                        evidentiary_strength=payload["evidentiary_strength"],
                        last_rehearsed=payload["last_rehearsed"],
                        forgiveness_threshold=payload["forgiveness_threshold"],
                    )
                )
            elif record_type == "obligation_issued":
                fields = {k: v for k, v in payload.items() if k != "record_type"}
                social.add_obligation(Obligation(**{**fields, "witnesses": tuple(payload["witnesses"])}))
            elif record_type == "obligation_resolved":
                # Re-executed through the store's resolve paths, so replay
                # enforces the same resolve-once discipline as the live run.
                if payload["status"] == "fulfilled":
                    social.fulfill_obligation(payload["obligation_id"], gamets=payload["gamets"])
                else:
                    social.violate_obligation(payload["obligation_id"], gamets=payload["gamets"], excuse=payload["excuse"])
            elif record_type == "reputation_updated":
                # Re-executed from the recorded inputs (schema §4); the
                # payload's resulting alpha/beta/counts let a reader
                # cross-check the reconstruction without re-deriving it.
                social.update_reputation(
                    observer_id=payload["observer_id"],
                    subject_id=payload["subject_id"],
                    context=payload["context"],
                    kind=payload["kind"],
                    positive=payload["positive"],
                    gamets=payload["last_updated"],
                )
            # encounter_rolled / nothing_salient carry no store mutation;
            # unknown record types are skipped (schema §7).

        return ReconstructedState(tick=tick, claims=claims, social=social, schedule=schedule)
