"""Agent-debug CLI subcommand logic for ``python -m chronicle`` (docs/dashboard-build-plan.md §2 M1).

``inspect``/``trace``/``feed`` are read-only consumers of
``chronicle/framelog.py``'s ``FrameLogReader`` -- they reconstruct or scan a
run's log and print what they find; nothing here mutates
``claims.py``/``social.py``/``schedule.py``. Belief strengths are printed
with read-time decay applied (claims.decay / claims.stage_at) -- never the
stored as-of-last-rehearsed values as-if-current (rule 19). Ticks are
game-hours (ADR-0010: 1 tick = 1 gamets = 1 game-hour). Output is plain
text, one record per line, kept compact and greppable -- a debugging
surface, not a table widget.

Each read subcommand accepts two invocation forms (both are tested):

  - positional: ``inspect <run_id> <npc_id> [--at <tick>]``,
    ``trace <run_id> <claim_id> [--at <tick>]``,
    ``feed <run_id> [--location <id>] [--npc <id>] [--at <tick>] [--limit <n>]``
    (``--at`` defaults to the run's current max tick);
  - flag form (pinned to the dashboard's copy/paste strings):
    ``inspect <npc_id> --run <run_id> --at <tick>``,
    ``trace <claim_id> --run <run_id> --at <tick>``,
    ``feed --run <run_id> [--location <id>] [--npc <id>] [--from-tick <t>] [--to-tick <t>]``.

``inject`` has two modes:

  - ``inject <run_id> --event '<json>'`` -- the write path: appends one
    canonical-event record to the run's ``events.jsonl`` through
    ``FrameLogWriter``'s own machinery (no hand-rolled appends), stamping
    ``origin: {"kind": "console", "detail": "chronicle inject"}``
    (docs/frame-log-schema.md §3). Injection at a tick earlier than the
    run's current max tick is refused: that is fork territory, a
    deliberately deferred milestone (docs/dashboard-build-plan.md §3).
  - ``inject --run <run_id> --at <tick> --type <event_type> [--actor <a>]
    [--payload '<json>']`` -- compose/validate only (no write). Flag names
    pinned to the exact invocation string
    ``dashboard/src/components/InjectionConsole.vue`` composes and displays;
    see ``inject_command``'s docstring for the verified match/mismatch
    findings against the original flag sketch.

``sync-check <run_id> --manifest '<json>'`` classifies a co-save manifest
(``chronicle.sync.Manifest``'s fields) against the run's on-disk state via
``chronicle.sync.resolve()`` (docs/design/chronicle-sync-cli-integration.md).
CONTINUE is fully supported (exit 0); FORK/ADOPT are computed and reported
but not applied -- no on-disk fork mechanism exists yet (exit 3);
LEGACY_IMPORT is report-only (exit 0); invalid input, a run/save_uuid
mismatch, or an unknown run all exit 1. See ``sync_check_command``'s
docstring for the full decision table.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from chronicle.claims import BeliefInstance, decay, stage_at
from chronicle.events import CrimeWitnessed, NPCDied, RumorHeard
from chronicle.fork import fork_run
from chronicle.framelog import (
    EVENTS_STREAM,
    STREAM_FILES,
    TRACE_STREAM,
    FrameLogReader,
    FrameLogWriter,
    default_runs_dir,
    event_payload,
)
from chronicle.sync import (
    SUPPORTED_FORMAT_VERSION,
    BranchState,
    Manifest,
    Resolution,
    ResolveDecision,
    legacy_import_resolution,
    resolve,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _run_dir(run_id: str, *, runs_dir: Path | None = None) -> Path:
    base = runs_dir if runs_dir is not None else default_runs_dir()
    return base / run_id


def _reader_for(run_id: str, *, runs_dir: Path | None = None) -> FrameLogReader:
    run_dir = _run_dir(run_id, runs_dir=runs_dir)
    if not run_dir.exists():
        raise SystemExit(f"chronicle: no such run {run_id!r} under {run_dir.parent} (looked for {run_dir})")
    return FrameLogReader(run_dir)


def _fmt_float(value: float) -> str:
    return f"{value:.4f}"


def _max_tick(reader: FrameLogReader) -> int | None:
    """The run's current max tick across both streams, from the sidecar index."""
    index = reader.read_index()
    ticks = [int(t) for stream in index["streams"].values() for t in stream["tick_offsets"]]
    return max(ticks) if ticks else None


def _resolve_run_and_subject(args: argparse.Namespace, *, subject_name: str) -> tuple[str, str]:
    """Both invocation forms: ``<run_id> <subject>`` positionally, or ``<subject> --run <run_id>``."""
    if args.run is not None:
        if args.pos2 is not None:
            raise SystemExit("chronicle: pass the run id either positionally or via --run, not both")
        run_id, subject = args.run, args.pos1
    else:
        run_id, subject = args.pos1, args.pos2
    if run_id is None or subject is None:
        raise SystemExit(
            f"chronicle: need a run id and a {subject_name} -- "
            f"`<run_id> <{subject_name}>` or `<{subject_name}> --run <run_id>`"
        )
    return run_id, subject


def _resolve_positional_run(args: argparse.Namespace, *, command: str) -> str:
    """The run id for subcommands that take no subject: ``<run_id>`` or ``--run <run_id>``."""
    if args.run is not None and args.pos_run is not None:
        raise SystemExit("chronicle: pass the run id either positionally or via --run, not both")
    run_id = args.run if args.run is not None else args.pos_run
    if run_id is None:
        raise SystemExit(f"chronicle: {command} needs a run id -- `{command} <run_id>` or `{command} --run <run_id>`")
    return run_id


def _resolve_at(reader: FrameLogReader, at: int | None) -> int:
    """``--at`` defaults to the run's current max tick (1 tick = 1 gamets = 1 game-hour, ADR-0010)."""
    if at is not None:
        return at
    max_tick = _max_tick(reader)
    if max_tick is None:
        raise SystemExit("chronicle: run has no records yet -- pass --at explicitly")
    return max_tick


# Payload fields that name an NPC, across both streams' record types
# (schema §3/§4) -- feed's --npc filter and inspect's unknown-NPC check.
_NPC_FIELDS = (
    "npc_a", "npc_b", "holder_id", "teller_id", "hearer_id", "source_id",
    "npc_id", "witness_id", "perpetrator_id", "killer_id",
    # Tier-3 record types (lanes 23-26): the entity slot each names, so
    # `feed --npc`/`inspect`'s participant match doesn't silently drop them.
    "target_id", "observer_id", "subject_id", "issuer_id", "debtor_id",
    "beneficiary_id", "from_id", "to_id",
)


# ---------------------------------------------------------------------------
# inspect
# ---------------------------------------------------------------------------


def _npc_known(reader: FrameLogReader, state: Any, npc_id: str) -> bool:
    """Whether anything in the run names this NPC -- derived state first, then the raw streams.

    The stream fallback keeps an NPC with no derived state at the inspected
    tick (e.g. only ever an encounter participant, or known only from
    schedule blocks that fell between keyframes) from reading as "unknown".
    """
    if state.claims.beliefs_of(npc_id):
        return True
    social = state.social
    if social.relationships_from(npc_id) or social.grudges_of(npc_id) or social.obligations_involving(npc_id):
        return True
    # No accessors exist for "records where this NPC is the target/subject"
    # -- same private-dict-read precedent as inspect_command below.
    if any(r.to_id == npc_id for r in social._relationships.values()):
        return True
    if any(g.target_id == npc_id for g in social._grudges.values()):
        return True
    if any(r.observer_id == npc_id or r.subject_id == npc_id for r in social._reputations.values()):
        return True
    if any(block.npc_id == npc_id for block in state.schedule):
        return True
    for stream in (EVENTS_STREAM, TRACE_STREAM):
        for record in reader.records(stream):
            payload = record["payload"]
            if any(payload.get(field) == npc_id for field in _NPC_FIELDS):
                return True
    return False


def inspect_command(args: argparse.Namespace) -> int:
    """``inspect <run_id> <npc_id> [--at <tick>]`` (or ``inspect <npc_id> --run <run_id> [--at <tick>]``).

    One NPC's beliefs and social-layer standing as of a tick (default: the
    run's max tick). Reconstructs derived state via
    ``FrameLogReader.state_at()``, then reports through
    ``ClaimStore``/``SocialStateStore``'s read-only accessors what the build
    plan's M1 bullet asks for: beliefs (claim, variant,
    confidence/verbatim/gist strengths -- decayed analytically at query time
    per ui-spec §1.1's no-sampled-histories rule -- and rumor stage via
    ``stage_at()``), plus relationships from them, grudges they hold,
    obligations involving them, and reputations where they are the observer
    (subject-side records are printed too, where the store can find them).
    """
    run_id, npc_id = _resolve_run_and_subject(args, subject_name="npc_id")
    reader = _reader_for(run_id, runs_dir=args.runs_dir)
    tick = _resolve_at(reader, args.at)
    state = reader.state_at(tick)
    at_gamets = float(tick)

    if not _npc_known(reader, state, npc_id):
        raise SystemExit(
            f"chronicle: unknown npc {npc_id!r} in run {run_id!r} -- "
            "no beliefs, social records, schedule blocks, or log records name them"
        )

    print(f"=== {npc_id} @ tick {tick} (run {run_id}) ===")

    beliefs = state.claims.beliefs_of(npc_id)
    print(f"\n-- beliefs ({len(beliefs)}) --")
    if not beliefs:
        print("  (none)")
    for belief in sorted(beliefs, key=lambda b: b.id):
        claim = state.claims.claim(belief.claim_id)
        variant = state.claims.variant(belief.variant_id) if belief.variant_id is not None else None
        decayed = decay(belief, at_gamets)  # read-time decay -- never print stored strengths as-if-current (rule 19)
        rumor = state.claims.rumor_state(npc_id, belief.claim_id, belief.variant_id)
        stage = stage_at(rumor, belief, at_gamets) if rumor is not None else "unheard"
        print(f"  belief {belief.id}")
        print(f"    claim       : {claim.id} ({claim.kind}) slots={claim.slots}")
        if variant is not None:
            print(f"    variant     : {variant.id} mutated_slot={variant.mutated_slot} slots={variant.slots}")
        else:
            print("    variant     : (original telling)")
        print(
            f"    confidence  : {_fmt_float(decayed.confidence)} "
            f"(stored {_fmt_float(belief.confidence)} as of last_rehearsed={belief.last_rehearsed})"
        )
        print(f"    verbatim    : {_fmt_float(decayed.verbatim_strength)}  gist: {_fmt_float(decayed.gist_strength)}")
        print(f"    rumor stage : {stage}")

    relationships_held = state.social.relationships_from(npc_id)
    # No accessor exists for "relationships where this NPC is the target"
    # (SocialStateStore indexes only by from_id) -- reading the private
    # dict directly, the same way chronicle/framelog.py's serialize_state()
    # already does. Flagged as a finding in this lane's report rather than
    # added here (file boundary: don't add store methods without calling
    # it out).
    relationships_subject = tuple(r for r in state.social._relationships.values() if r.to_id == npc_id)
    print(f"\n-- relationships held ({len(relationships_held)}) --")
    for rel in relationships_held:
        print(f"  -> {rel.to_id} basis={rel.basis} strength={_fmt_float(rel.strength)}")
    print(f"-- relationships subject to ({len(relationships_subject)}) --")
    for rel in relationships_subject:
        print(f"  <- {rel.from_id} basis={rel.basis} strength={_fmt_float(rel.strength)}")

    grudges_held = state.social.grudges_of(npc_id)
    grudges_subject = tuple(g for g in state.social._grudges.values() if g.target_id == npc_id)
    print(f"\n-- grudges held ({len(grudges_held)}) --")
    for g in grudges_held:
        print(f"  against {g.target_id}: {g.grievance_type} severity={_fmt_float(g.severity)}")
    print(f"-- grudges subject to ({len(grudges_subject)}) --")
    for g in grudges_subject:
        print(f"  held by {g.holder_id}: {g.grievance_type} severity={_fmt_float(g.severity)}")

    obligations = state.social.obligations_involving(npc_id)
    print(f"\n-- obligations involving {npc_id} ({len(obligations)}) --")
    for o in obligations:
        role = "issuer" if o.issuer_id == npc_id else "debtor" if o.debtor_id == npc_id else "beneficiary"
        print(f"  [{role}] {o.id}: {o.action} status={o.status}")

    # No accessor exists for "every Reputation naming this NPC on either
    # side" (SocialStateStore only supports the exact-key lookup rule 10
    # requires) -- same private-dict-read precedent as above.
    reps_held = [r for r in state.social._reputations.values() if r.observer_id == npc_id]
    reps_subject = [r for r in state.social._reputations.values() if r.subject_id == npc_id]
    print(f"\n-- reputations held (as observer) ({len(reps_held)}) --")
    for r in reps_held:
        print(f"  of {r.subject_id} in {r.context!r}: mean={_fmt_float(r.mean)} uncertainty={_fmt_float(r.uncertainty)}")
    print(f"-- reputations subject to (as subject) ({len(reps_subject)}) --")
    for r in reps_subject:
        print(f"  by {r.observer_id} in {r.context!r}: mean={_fmt_float(r.mean)} uncertainty={_fmt_float(r.uncertainty)}")

    return 0


# ---------------------------------------------------------------------------
# trace
# ---------------------------------------------------------------------------


def _chain_line(belief: BeliefInstance, evidence: Any) -> str:
    return f"  {belief.holder_id} (belief {belief.id}, confidence stored {_fmt_float(belief.confidence)}) <- {evidence.evidence_type} via {evidence.source_id}"


# The claim-bearing trace record types the M1 packet's provenance view lists
# (schema §4): the witness-path derivation, transmissions, corroborations,
# and the nothing-salient negative rows that name the claim.
_CLAIM_TRACE_RECORD_TYPES = ("belief_formed", "transmitted", "belief_corroborated", "nothing_salient")


def trace_command(args: argparse.Namespace) -> int:
    """``trace <run_id> <claim_id> [--at <tick>]`` (or ``trace <claim_id> --run <run_id> [--at <tick>]``).

    One claim's full provenance as of a tick (default: the run's max tick):
    every trace record touching the claim (``belief_formed``/``transmitted``/
    ``belief_corroborated``/``nothing_salient`` rows naming it, schema §4) in
    seq order, the claim's variant lineage, and -- for each holder -- the
    ``chain_for()`` evidence walk back to the witnessed root (witness ->
    retellings -> corroborations, per ADR-0007), plus any ``supersession``
    trace record naming one of the claim's variants (a Tier-2 record type the
    claim/variant/belief store doesn't materialize itself).

    ``ClaimStore`` has no ``beliefs_by_claim`` accessor (only
    ``beliefs_of(holder_id)`` and ``belief_of(holder_id, claim_id)``, both
    keyed by holder) -- finding: reads the private ``_beliefs`` dict
    directly to find every belief about this claim, same precedent as
    ``inspect_command`` above.
    """
    run_id, claim_id = _resolve_run_and_subject(args, subject_name="claim_id")
    reader = _reader_for(run_id, runs_dir=args.runs_dir)
    tick = _resolve_at(reader, args.at)
    state = reader.state_at(tick)

    try:
        claim = state.claims.claim(claim_id)
    except KeyError:
        print(f"chronicle: no claim {claim_id!r} exists as of tick {tick}", file=sys.stderr)
        return 1

    print(f"=== claim {claim.id} ({claim.kind}) @ tick {tick} (run {run_id}) ===")
    print(f"slots: {claim.slots}  truth_status={claim.truth_status}")

    beliefs = sorted(
        (b for b in state.claims._beliefs.values() if b.claim_id == claim_id),
        key=lambda b: b.id,
    )
    # belief_corroborated records name beliefs, not claims (schema §4) --
    # resolve them through the reconstructed store.
    claim_of_belief = {b.id: b.claim_id for b in state.claims._beliefs.values()}

    touching = []
    for record in reader.records(TRACE_STREAM, upto_tick=tick):
        payload = record["payload"]
        record_type = payload.get("record_type")
        if record_type not in _CLAIM_TRACE_RECORD_TYPES:
            continue
        if payload.get("claim_id") == claim_id or (
            record_type == "belief_corroborated"
            and claim_id in {claim_of_belief.get(payload["belief_id"]), claim_of_belief.get(payload["source_belief_id"])}
        ):
            touching.append(record)
    print(f"\n-- trace records touching this claim ({len(touching)}, seq order) --")
    for record in touching:
        payload = record["payload"]
        print(f"  tick {record['tick']:>6}  seq {record['seq']:>4}  {payload['record_type']:<22} {json.dumps(payload)}")

    variants = sorted(
        (v for v in state.claims._variants.values() if v.claim_id == claim_id),
        key=lambda v: (v.gamets, v.id),
    )
    print(f"\n-- variant lineage ({len(variants)}) --")
    for variant in variants:
        print(
            f"  {variant.id} parent={variant.parent_variant_id or '-'} "
            f"mutated_slot={variant.mutated_slot or '-'} gamets={variant.gamets:g} slots={dict(variant.slots)}"
        )

    print(f"\n-- belief chains ({len(beliefs)} holder(s)) --")
    for belief in beliefs:
        chain = state.claims.chain_for(belief.id)
        print(f"holder {belief.holder_id}:")
        for held_belief, evidence in reversed(chain):
            print(_chain_line(held_belief, evidence))

    # lane-17 finding 1: filter by the claim's known variant lineage (plus the
    # canonical telling, null) rather than currently-held variants -- a
    # supersession whose loser is held by nobody after re-pointing must still
    # show up here.
    variant_ids = {v.id for v in variants} | {None}
    supersessions = [
        record
        for record in reader.records(TRACE_STREAM, upto_tick=tick)
        if record["payload"].get("record_type") == "supersession"
        and record["payload"].get("claim_id") == claim_id
        and (
            record["payload"].get("loser_variant_id") in variant_ids
            or record["payload"].get("winner_variant_id") in variant_ids
        )
    ]
    print(f"\n-- supersessions involving this claim's variants ({len(supersessions)}) --")
    for record in supersessions:
        payload = record["payload"]
        # Null variant ids name the claim's original telling (the amended
        # schema §4:120 idiom) -- render that, not Python's None.
        loser = payload["loser_variant_id"] or "(original telling)"
        winner = payload["winner_variant_id"] or "(original telling)"
        print(
            f"  tick {record['tick']}: {payload['holder_id']} -- "
            f"{loser} superseded by {winner} "
            f"via {payload['resolution_rule']} (confidence_dent={payload['confidence_dent']})"
        )

    return 0


# ---------------------------------------------------------------------------
# feed
# ---------------------------------------------------------------------------


# The encounter feed's record types, brought current with schema §4 as of
# lanes 12-26 (lane-29 backlog note: this list predated Tier 2/3 records).
# Tier-1 encounter outcomes, Tier-2 mutation/resolution, and Tier-3 social
# mechanics -- all trace-stream `record_type` values, except
# `escalation_warning`, which is an *event* (`event_type`, schema §3:95):
# it is reserved-tier there but already has a lane-24 producer, and the
# packet calls it out by name so the feed shows the escalation it triggers,
# not just the `threshold_crossed` trace row that names it.
_FEED_RECORD_TYPES = (
    "encounter_rolled", "transmitted", "nothing_salient",
    "supersession", "mutation_applied",
    "transmission_declined", "rule_evaluated", "threshold_crossed",
    "grudge_formed", "reputation_updated",
    "obligation_issued", "obligation_resolved", "relationship_formed",
    "escalation_warning",
)


def _record_matches(payload: dict[str, Any], *, location_id: str | None, npc_id: str | None) -> bool:
    if location_id is not None and payload.get("location_id") != location_id:
        return False
    return npc_id is None or any(payload.get(field) == npc_id for field in _NPC_FIELDS)


def _feed_type(payload: dict[str, Any]) -> str | None:
    """A record's type name, whichever stream it came from.

    Trace records key it as ``record_type``; events key it as
    ``event_type`` (schema §3 vs §4) -- ``feed`` reads both streams so
    ``escalation_warning`` (an event) shows up alongside the trace rows.
    """
    return payload.get("record_type") or payload.get("event_type")


def feed_command(args: argparse.Namespace) -> int:
    """``feed <run_id> [--location <id>] [--npc <id>] [--at <tick>] [--limit <n>]`` (flag form: ``--run``/``--from-tick``/``--to-tick``).

    The encounter feed in text form: the Tier-1/2/3 record types in
    ``_FEED_RECORD_TYPES`` from the trace stream, plus ``escalation_warning``
    events, filtered by location and/or participant NPC, up to tick
    ``--at``/``--to-tick`` (default: all). Not the M2 dashboard feed -- no
    virtualization; ``--limit`` (50 by default, <=0 for all) keeps it a
    debugging surface, not a table widget.

    ``FrameLogReader.records()`` yields records in *file* order, which is
    tick order for an encounter-driven driver run but is **not**
    guaranteed for a hand-scripted scenario (e.g.
    ``scenarios/test_jarl_death_belief_cascade.py`` writes gamets
    1000/1050/1100/1000/1005 -- a later witness() call at an earlier
    gamets than the retell before it). This command materializes the
    filtered set and sorts by ``(tick, seq)`` before printing, rather than
    trusting file order, so "in tick order" holds for every run this CLI
    might be pointed at, not just the common case. Events and trace
    records keep independent ``seq`` counters (framelog.py), so at a tick
    where both streams produced records, the merged order between them is
    best-effort, not a causal guarantee -- ties are broken by stream
    (events before trace) for determinism, nothing stronger.
    """
    run_id = _resolve_positional_run(args, command="feed")
    reader = _reader_for(run_id, runs_dir=args.runs_dir)
    upto_tick = args.to_tick if args.to_tick is not None else args.at
    matching = [
        (stream_index, record)
        for stream_index, stream in enumerate((EVENTS_STREAM, TRACE_STREAM))
        for record in reader.records(stream, upto_tick=upto_tick)
        if _feed_type(record["payload"]) in _FEED_RECORD_TYPES
        and (args.from_tick is None or record["tick"] >= args.from_tick)
        and _record_matches(record["payload"], location_id=args.location, npc_id=args.npc)
    ]
    matching.sort(key=lambda entry: (entry[1]["tick"], entry[0], entry[1]["seq"]))
    shown = matching if args.limit <= 0 else matching[: args.limit]
    for _, record in shown:
        record_type = _feed_type(record["payload"]) or "?"
        print(f"tick {record['tick']:>6}  seq {record['seq']:>4}  {record_type:<22} {json.dumps(record['payload'])}")
    print(f"\n({len(shown)} of {len(matching)} matching record(s))", file=sys.stderr)
    return 0


# ---------------------------------------------------------------------------
# inject
# ---------------------------------------------------------------------------

# Known canonical event kinds (chronicle/events.py, mirrored per
# docs/frame-log-schema.md §3) that inject validates against.
# Reserved kinds (escalation_warning/schedule_rewrite/role_lapse) are
# schema commitments without a producer yet (§3: "writers must not emit
# them before their tier") -- inject rejects them the same as any unknown
# type, naming the tier that owns them.
_EVENT_FIELDS: dict[str, dict[str, bool]] = {
    # field_name -> required?
    "npc_died": {"npc_id": True, "cause": True, "killer_id": False, "location_id": False},
    "crime_witnessed": {"witness_id": True, "perpetrator_id": True, "crime_type": True, "location_id": False},
    "rumor_heard": {"hearer_id": True, "source_id": True, "rumor_id": True, "content": True},
}

_EVENT_CLASSES = {
    "npc_died": NPCDied,
    "crime_witnessed": CrimeWitnessed,
    "rumor_heard": RumorHeard,
}

# The console's "actor (optional)" field is generic; canonical events name
# their primary actor differently per kind. This mapping is lane 9's
# interpretation of what "actor" means per type -- flagged as a finding,
# since InjectionConsole.vue itself doesn't disambiguate.
_ACTOR_FIELD: dict[str, str] = {
    "npc_died": "npc_id",
    "crime_witnessed": "witness_id",
    "rumor_heard": "hearer_id",
}

_RESERVED_EVENT_TYPES = {
    "escalation_warning": "Tier 3 (tell-decision/threshold machinery)",
    "schedule_rewrite": "Tier 4a (schedule write-back)",
    "role_lapse": "Tier 5 (roles)",
}

# Fields --event may carry beyond the kind-specific ones: envelope/bitemporal
# coordinates the write path fills in when absent.
_EVENT_ENVELOPE_FIELDS = {"event_type", "tick", "gamets", "wall_ts", "seq", "origin"}

# The origin stamp for the write path (schema §3: injected events are
# ordinary canonical events in every other respect). Default matches the
# console's own usage; --origin-kind/--origin-detail let a non-console
# caller (e.g. a future Skyrim-adapter listener shelling out to this same
# tested write path, per docs/design/chronicle-bridge-death-extraction.md)
# stamp itself correctly instead of being mislabeled "console".
_INJECT_WRITE_ORIGIN = {"kind": "console", "detail": "chronicle inject"}
_VALID_ORIGIN_KINDS = {"scenario", "console", "adapter"}


def _check_event_type(event_type: Any) -> str | None:
    """An error message if event_type is reserved/unknown, else None."""
    if event_type in _RESERVED_EVENT_TYPES:
        return (
            f"chronicle: event type {event_type!r} is reserved for {_RESERVED_EVENT_TYPES[event_type]} "
            "and has no producer yet (docs/frame-log-schema.md §3) -- not injectable"
        )
    if event_type not in _EVENT_FIELDS:
        known = ", ".join(sorted(_EVENT_FIELDS))
        return f"chronicle: unknown event type {event_type!r} -- known kinds: {known}"
    return None


def _branch_identity(reader: FrameLogReader, runs_dir: Path, run_id: str) -> tuple[str, str, int]:
    """The run's (seed_id, save_uuid, generation), from the run registry or (fallback) any record envelope.

    Registry-first, not record-first: chronicle/fork.py's copy-forward
    fork support (docs/design/fork-on-disk-support.md) stamps a forked
    run's copied-prefix records with the PARENT's generation (they really
    happened under that branch) and only its own new records with the
    fork's own generation -- so a forked run's FIRST record no longer
    reliably names that run's own current generation the way it did
    before forking existed. The registry entry is written from the
    Driver's own generation at construction (chronicle/framelog.py's
    FrameLogWriter._register) and stays correct regardless of what
    generation its earliest copied records carry, so it's the
    authoritative source; falling back to a record envelope only covers
    a run with no registry entry at all (e.g. a hand-built fixture in a
    test that never went through the normal writer lifecycle).
    """
    registry_path = runs_dir / "index.json"
    if registry_path.exists():
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        for entry in registry.get("runs", []):
            if entry.get("run_id") == run_id:
                branch = entry["branches"][0]
                return entry["seed_id"], branch["save_uuid"], branch["generation"]
    for stream in (EVENTS_STREAM, TRACE_STREAM):
        first = next(reader.records(stream), None)
        if first is not None:
            return first["seed_id"], first["save_uuid"], first["generation"]
    raise SystemExit(f"chronicle: run {run_id!r} has no records and no registry entry -- cannot determine its branch identity")


def _open_appending_writer(run_dir: Path, *, seed_id: str, save_uuid: str, generation: int) -> FrameLogWriter:
    """Reattach a FrameLogWriter to an existing run for one append.

    ``FrameLogWriter.__init__`` is create-only by design (append-only logs;
    a new run means a new run_id), so the inject write path rebuilds the
    writer's in-memory position from the on-disk sidecar index and stream
    file sizes, then reuses the writer's own write_event/flush machinery --
    envelope, offset accounting, atomic index rewrite -- rather than
    hand-rolling an append.
    """
    reader = FrameLogReader(run_dir)
    index = reader.read_index()
    writer = FrameLogWriter.__new__(FrameLogWriter)
    writer.run_id = run_dir.name
    writer.seed_id = seed_id
    writer.save_uuid = save_uuid
    writer.generation = generation
    writer.runs_dir = run_dir.parent
    writer.run_dir = run_dir
    writer._files = {stream: open(run_dir / STREAM_FILES[stream], "ab") for stream in STREAM_FILES}  # noqa: SIM115 -- closed by the caller
    writer._offsets = {stream: (run_dir / STREAM_FILES[stream]).stat().st_size for stream in STREAM_FILES}
    writer._seqs = {EVENTS_STREAM: 0, TRACE_STREAM: sum(1 for _ in reader.records(TRACE_STREAM))}
    # Keyframes carry the high water without consuming a seq (schema §7's
    # keyframe seq discipline), so the high water is over canonical events
    # only; -1 until the first one.
    writer._event_seq_high_water = max(
        (r["seq"] for r in reader.records(EVENTS_STREAM) if "event_type" in r["payload"]),
        default=-1,
    )
    writer._tick_offsets = {stream: dict(index["streams"][stream]["tick_offsets"]) for stream in STREAM_FILES}
    writer._keyframe_offsets = list(index["streams"][EVENTS_STREAM]["keyframe_offsets"])
    ticks = [int(t) for stream in STREAM_FILES for t in index["streams"][stream]["tick_offsets"]]
    writer._tick_min = min(ticks) if ticks else None
    writer._tick_max = max(ticks) if ticks else None
    writer._created_wall_ts = time.time()
    writer._closed = False
    return writer


def _inject_write(args: argparse.Namespace) -> int:
    """``inject <run_id> --event '<json>'``: append one canonical event to the run's events.jsonl.

    The write path the dashboard's injection console composes. The JSON is
    an events-stream payload per schema §3 (``event_type`` plus the
    kind-specific fields, and ``tick`` or ``gamets``); the CLI fills in the
    branch identity from the run, a fresh seq, and wall_ts when absent, and
    stamps ``origin: {"kind": "console", "detail": "chronicle inject"}"`` by
    default -- pass ``--origin-kind``/``--origin-detail`` to stamp
    differently (e.g. ``adapter`` for a Skyrim-adapter caller), per schema
    §3's ``origin.kind`` enum (``scenario`` | ``console`` | ``adapter``).
    Injection at a tick earlier than the run's current max tick is refused
    -- that is fork territory, a deliberately deferred milestone
    (docs/dashboard-build-plan.md §3).
    """
    if args.origin_kind is not None and args.origin_kind not in _VALID_ORIGIN_KINDS:
        known = ", ".join(sorted(_VALID_ORIGIN_KINDS))
        print(f"chronicle: --origin-kind {args.origin_kind!r} is not one of {known} (docs/frame-log-schema.md §3)", file=sys.stderr)
        return 1

    run_id = _resolve_positional_run(args, command="inject")
    run_dir = _run_dir(run_id, runs_dir=args.runs_dir)
    reader = _reader_for(run_id, runs_dir=args.runs_dir)

    try:
        data = json.loads(args.event)
    except json.JSONDecodeError as exc:
        print(f"chronicle: --event is not valid JSON: {exc}", file=sys.stderr)
        return 1
    if not isinstance(data, dict):
        print("chronicle: --event must be a JSON object (an events-stream payload per docs/frame-log-schema.md §3)", file=sys.stderr)
        return 1

    event_type_error = _check_event_type(data.get("event_type"))
    if event_type_error is not None:
        print(event_type_error, file=sys.stderr)
        return 1
    event_type = data["event_type"]

    if "tick" not in data and "gamets" not in data:
        print("chronicle: --event must carry a tick or gamets (1 tick = 1 gamets = 1 game-hour, ADR-0010)", file=sys.stderr)
        return 1
    tick = int(data["tick"]) if "tick" in data else int(data["gamets"])
    gamets = float(data["gamets"]) if "gamets" in data else float(tick)

    max_tick = _max_tick(reader)
    if max_tick is not None and tick < max_tick:
        print(
            f"chronicle: refusing to inject at tick {tick} -- run {run_id!r} has already reached tick {max_tick}: "
            "injection at a historical tick is fork territory, a deliberately deferred milestone "
            "(docs/dashboard-build-plan.md §3)",
            file=sys.stderr,
        )
        return 1

    fields = _EVENT_FIELDS[event_type]
    missing = [name for name, required in fields.items() if required and name not in data]
    if missing:
        print(f"chronicle: missing required field(s) for {event_type!r}: {', '.join(missing)}", file=sys.stderr)
        return 1
    unknown = [name for name in data if name not in fields and name not in _EVENT_ENVELOPE_FIELDS]
    if unknown:
        allowed = ", ".join([*fields, *sorted(_EVENT_ENVELOPE_FIELDS)])
        print(f"chronicle: unknown field(s) for {event_type!r}: {', '.join(unknown)} (allowed: {allowed})", file=sys.stderr)
        return 1

    event_seqs = {r["seq"] for r in reader.records(EVENTS_STREAM) if "event_type" in r["payload"]}
    if "seq" in data:
        seq = int(data["seq"])
        if seq in event_seqs:
            print(
                f"chronicle: seq {seq} is already used by an event in run {run_id!r} -- "
                "(save_uuid, generation, seq) is the idempotency key; pick a fresh seq",
                file=sys.stderr,
            )
            return 1
    else:
        seq = max(event_seqs, default=-1) + 1

    seed_id, save_uuid, generation = _branch_identity(reader, run_dir.parent, run_id)
    kwargs = {name: data[name] for name in fields if name in data}
    event = _EVENT_CLASSES[event_type](
        tick=tick,
        save_uuid=save_uuid,
        generation=generation,
        seq=seq,
        gamets=gamets,
        wall_ts=float(data.get("wall_ts", time.time())),
        **kwargs,
    )
    origin = _INJECT_WRITE_ORIGIN
    if args.origin_kind is not None or args.origin_detail is not None:
        origin = {
            "kind": args.origin_kind if args.origin_kind is not None else _INJECT_WRITE_ORIGIN["kind"],
            "detail": args.origin_detail if args.origin_detail is not None else _INJECT_WRITE_ORIGIN["detail"],
        }
    payload = event_payload(event, origin=origin)

    writer = _open_appending_writer(run_dir, seed_id=seed_id, save_uuid=save_uuid, generation=generation)
    try:
        writer.write_event(tick=tick, seq=seq, payload=payload)
        writer.flush()  # the liveness contract (schema §1): a tailing reader sees it immediately
    finally:
        # Not writer.close(): that would re-register the run as "complete"
        # and rewrite its registry entry. flush() has already committed the
        # record and the sidecar index; just release the file handles.
        for f in writer._files.values():
            f.close()
        writer._closed = True
    print(f"injected {event_type} seq={seq} tick={tick} into run {run_id} (origin {origin['kind']}: {origin['detail']})")
    return 0


def inject_command(args: argparse.Namespace) -> int:
    """``inject`` in two modes: ``--event '<json>'`` writes; ``--type``/``--payload`` composes.

    The compose path pretty-prints the canonical-event JSON for the given
    type/payload (docs/frame-log-schema.md §3), validated against
    ``chronicle/events.py``'s known event kinds, and **does not write to
    the run's log** -- its flag names are pinned to
    ``InjectionConsole.vue``'s composed invocation string: ``--run``,
    ``--at``, ``--type``, optional ``--actor``, and ``--payload`` (a JSON
    object string; the original flag sketch said ``--payload-json``, but
    the Vue component's ``--payload`` is what's actually displayed to a
    user for copy/paste, so it wins). The ``--event`` write path is
    ``_inject_write`` above.
    """
    if args.event is not None:
        return _inject_write(args)
    missing_flags = [
        flag for flag, value in (("--run", args.run), ("--at", args.at), ("--type", args.type)) if value is None
    ]
    if missing_flags:
        raise SystemExit(
            f"chronicle: inject needs either --event '<json>' (write path) or "
            f"{' '.join(missing_flags)} (compose path): missing {', '.join(missing_flags)}"
        )

    event_type = args.type
    event_type_error = _check_event_type(event_type)
    if event_type_error is not None:
        print(event_type_error, file=sys.stderr)
        return 1

    try:
        payload: dict[str, Any] = json.loads(args.payload) if args.payload else {}
    except json.JSONDecodeError as exc:
        print(f"chronicle: --payload is not valid JSON: {exc}", file=sys.stderr)
        return 1
    if not isinstance(payload, dict):
        print("chronicle: --payload must be a JSON object", file=sys.stderr)
        return 1

    if args.actor is not None:
        actor_field = _ACTOR_FIELD[event_type]
        if actor_field in payload and payload[actor_field] != args.actor:
            print(
                f"chronicle: --actor {args.actor!r} conflicts with payload[{actor_field!r}] = {payload[actor_field]!r}",
                file=sys.stderr,
            )
            return 1
        payload[actor_field] = args.actor

    fields = _EVENT_FIELDS[event_type]
    missing = [name for name, required in fields.items() if required and name not in payload]
    if missing:
        print(f"chronicle: missing required field(s) for {event_type!r}: {', '.join(missing)}", file=sys.stderr)
        return 1
    unknown = [name for name in payload if name not in fields]
    if unknown:
        print(f"chronicle: unknown field(s) for {event_type!r}: {', '.join(unknown)} (allowed: {', '.join(fields)})", file=sys.stderr)
        return 1

    for name in fields:
        payload.setdefault(name, None)

    composed = {
        "event_type": event_type,
        "tick": args.at,
        "gamets": float(args.at),
        "wall_ts": time.time(),
        "origin": {"kind": "console", "detail": "chronicle inject CLI"},
        **payload,
    }
    print(f"# run={args.run} at={args.at} type={event_type} -- NOT written to the run's log (compose mode; use --event to write)")
    print(json.dumps(composed, indent=2, sort_keys=False))
    return 0


# ---------------------------------------------------------------------------
# fork
# ---------------------------------------------------------------------------


def fork_command(args: argparse.Namespace) -> int:
    """``chronicle fork <run_id> --at-tick T [--new-run-id ID]`` (docs/design/fork-on-disk-support.md).

    A thin wrapper over ``chronicle.fork.fork_run`` -- the file-level fork
    and ``Driver`` construction both live there, matching how
    ``_inject_write`` above is a thin CLI wrapper over the lower-level
    write path. ``--new-run-id`` defaults to ``"<run_id>-fork-<at_tick>"``
    when omitted (no existing run-id generator to reuse in this codebase).

    A bare ``chronicle fork`` invocation has nothing further to inject, so
    this command closes the new ``Driver`` immediately -- marking its
    registry entry complete, matching the normal run lifecycle. A caller
    that wants to inject a diverging event and keep running (a scenario, or
    eventually the dashboard's injection console) should call
    ``fork_run()`` directly instead of shelling out to this command.
    """
    run_id = _resolve_positional_run(args, command="fork")
    new_run_id = args.new_run_id if args.new_run_id is not None else f"{run_id}-fork-{args.at_tick}"
    try:
        driver = fork_run(run_id, at_tick=args.at_tick, new_run_id=new_run_id, runs_dir=args.runs_dir)
    except (FileNotFoundError, FileExistsError, ValueError) as exc:
        print(f"chronicle: {exc}", file=sys.stderr)
        return 1
    new_run_dir = (args.runs_dir if args.runs_dir is not None else default_runs_dir()) / new_run_id
    driver.close()
    print(f"forked {run_id!r} at tick {args.at_tick} -> new run {new_run_id!r} (generation {driver.generation}) at {new_run_dir}")
    return 0


# ---------------------------------------------------------------------------
# sync-check
# ---------------------------------------------------------------------------

# chronicle.sync.Manifest's field set, verbatim (docs/decisions/0005-sync-handshake.md's
# schema table). `parent_generation` is the only nullable field (a root
# generation legitimately carries `null`, per chronicle.sync.resolve()'s ADOPT
# comment); everything else is mandatory, matching Manifest's own dataclass
# (no field has a default).
_SYNC_MANIFEST_FIELD_TYPES: dict[str, type | tuple[type, ...]] = {
    "format_version": int,
    "save_uuid": str,
    "generation": int,
    "parent_generation": (int, type(None)),
    "head_seq": int,
    "gamets": (int, float),
    "wall_ts": (int, float),
}


def _parse_manifest_json(raw: str) -> dict[str, Any] | str:
    """Parse ``--manifest``'s raw text into a JSON object, or return an error message string.

    Deliberately split from ``_validate_sync_manifest_fields`` below: the
    format_version gate (ADR-0005's tolerant-read rule -- see
    ``sync_check_command``'s docstring) must run on the raw dict BEFORE any
    field-shape validation, so a manifest from a newer shim with fields
    this build doesn't recognize yet still reaches LEGACY_IMPORT instead
    of being rejected as "unknown field(s)".
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return f"chronicle: --manifest is not valid JSON: {exc}"
    if not isinstance(data, dict):
        return "chronicle: --manifest must be a JSON object (chronicle.sync.Manifest's fields)"
    return data


def _validate_sync_manifest_fields(data: dict[str, Any]) -> Manifest | str:
    """Validate an already-parsed manifest dict into a ``chronicle.sync.Manifest``, or an error message string.

    Only called once the format_version gate (see ``_parse_manifest_json``'s
    docstring and ``sync_check_command``) has already confirmed this
    manifest's format_version is one this build understands. Mirrors
    ``_inject_write``'s ``--event`` validation style: missing/unknown
    fields and wrong field types all produce a single clear message rather
    than a traceback.
    """
    missing = [name for name in _SYNC_MANIFEST_FIELD_TYPES if name not in data]
    if missing:
        return f"chronicle: missing required field(s) in --manifest: {', '.join(missing)}"
    unknown = [name for name in data if name not in _SYNC_MANIFEST_FIELD_TYPES]
    if unknown:
        allowed = ", ".join(_SYNC_MANIFEST_FIELD_TYPES)
        return f"chronicle: unknown field(s) in --manifest: {', '.join(unknown)} (allowed: {allowed})"

    for name, expected in _SYNC_MANIFEST_FIELD_TYPES.items():
        value = data[name]
        if isinstance(value, bool) or not isinstance(value, expected):
            want = expected.__name__ if isinstance(expected, type) else " or ".join(t.__name__ for t in expected)
            return f"chronicle: --manifest field {name!r} must be {want}, got {value!r}"

    try:
        return Manifest(
            format_version=data["format_version"],
            save_uuid=data["save_uuid"],
            generation=data["generation"],
            parent_generation=data["parent_generation"],
            head_seq=data["head_seq"],
            gamets=float(data["gamets"]),
            wall_ts=float(data["wall_ts"]),
        )
    except ValueError as exc:
        return f"chronicle: --manifest is invalid: {exc}"


def sync_check_command(args: argparse.Namespace) -> int:
    """``sync-check <run_id> --manifest '<json>'``: classify a co-save manifest against a run's on-disk state.

    Wires ``chronicle.sync.resolve()`` (docs/design/chronicle-sync-cli-
    integration.md §1) to a real run, read the same way ``_inject_write``
    already reads one: ``_branch_identity`` for the run's baked-in
    ``(save_uuid, generation)``, the events-stream seq set for ``head_seq``
    (same source ``_inject_write`` uses for its own next-seq computation),
    and ``_max_tick`` for ``head_gamets`` (ADR-0010: 1 tick = 1 gamets = 1
    game-hour, so a run's max tick doubles as its max gamets).

    A run directory on disk today bakes in exactly one ``(save_uuid,
    generation)`` pair (docs/design/chronicle-sync-cli-integration.md §0:
    ``chronicle/framelog.py``'s on-disk format stores a single-element
    ``"branches"`` list, and ``chronicle/events.py``'s ``EventLog.fork()``
    has no on-disk counterpart at all) -- so the ``BranchState`` built here
    always has a single-element ``known_generations``, and this command can
    only fully *act on* one of ``resolve()``'s six decisions:

      - ``CONTINUE``: the manifest matches this run -- fully supported.
        Prints the ``Resolution`` as JSON to stdout, exit 0.
      - ``FORK``/``ADOPT``: ``resolve()`` can still correctly *decide*
        these (the manifest's gamets is behind this run's head, or it
        names a generation this run has never recorded), but nothing here
        can *act* on them -- no on-disk fork mechanism exists yet. Prints
        the raw decision JSON (nothing is hidden) plus a stderr message
        naming the limitation, exit 3 -- a distinct code so a caller can
        tell "computed but unsupported" apart from "invalid input" (exit
        1) or an argparse usage error (argparse's own exit 2).
      - ``LEGACY_IMPORT``: the manifest's format_version is newer than
        this build understands (``chronicle.sync.SUPPORTED_FORMAT_VERSION``)
        -- the only way this command can reach it, since ``known=True`` is
        always true for a run that exists on disk by definition
        (``NEW_TIMELINE``, which needs ``known=False``, is therefore
        structurally unreachable here -- named below rather than silently
        dropped). Checked BEFORE field validation or the save_uuid check
        below (ADR-0005's tolerant-read rule, mirrored by
        ``chronicle.sync.resolve()`` itself: a manifest stamped with a
        newer format_version must not have any other field interpreted --
        not validated, not compared -- since those may be exactly the
        additions a newer shim introduced). Report-only for this lane (per
        the design doc's §1 lean) -- prints the decision and a stderr note
        that no new run was created, exit 0.
      - ``DEGRADED`` is not reachable from ``resolve()`` for any real
        manifest -- only ``chronicle.sync.degraded_resolution()``, which
        nothing in this CLI path calls, produces it (that decision
        describes the *shim* being unable to reach the service at all,
        which is a fact this command's own successful execution disproves)
        -- so it is not handled as a real branch below.

    The ``BranchState`` assembled here is scoped to the named run: before
    classifying, this command checks that ``manifest.save_uuid`` actually
    matches the run's own save_uuid (from ``_branch_identity``) and refuses
    (exit 1) on a mismatch -- ``resolve()`` has no save_uuid field on
    ``BranchState`` to cross-check itself, so a caller handing it state for
    the wrong save would otherwise get a confident but meaningless
    CONTINUE, exactly the wrong-branch outcome ``chronicle.sync`` exists to
    prevent.
    """
    run_id = _resolve_positional_run(args, command="sync-check")
    run_dir = _run_dir(run_id, runs_dir=args.runs_dir)
    reader = _reader_for(run_id, runs_dir=args.runs_dir)

    data_or_error = _parse_manifest_json(args.manifest)
    if isinstance(data_or_error, str):
        print(data_or_error, file=sys.stderr)
        return 1
    data = data_or_error

    # The format_version gate runs on the raw dict, before any field
    # validation or the save_uuid check below -- see this function's
    # docstring and _parse_manifest_json's. A missing/non-int
    # format_version falls through to normal validation, which will
    # report it as a missing/wrong-type field.
    format_version = data.get("format_version")
    if isinstance(format_version, int) and not isinstance(format_version, bool) and format_version > SUPPORTED_FORMAT_VERSION:
        hint = data.get("save_uuid") if isinstance(data.get("save_uuid"), str) else None
        resolution = legacy_import_resolution(save_uuid_hint=hint)
        print(json.dumps(_sync_resolution_payload(resolution), indent=2, sort_keys=False))
        print(
            f"chronicle: sync-check computed LEGACY_IMPORT -- the manifest's format_version ({format_version}) is "
            f"newer than this build supports (chronicle.sync.SUPPORTED_FORMAT_VERSION={SUPPORTED_FORMAT_VERSION}); "
            "report-only for this lane, no new run was created, and no other manifest field was interpreted "
            "(docs/design/chronicle-sync-cli-integration.md §1).",
            file=sys.stderr,
        )
        return 0

    manifest_or_error = _validate_sync_manifest_fields(data)
    if isinstance(manifest_or_error, str):
        print(manifest_or_error, file=sys.stderr)
        return 1
    manifest = manifest_or_error

    _seed_id, run_save_uuid, generation = _branch_identity(reader, run_dir.parent, run_id)
    if manifest.save_uuid != run_save_uuid:
        print(
            f"chronicle: --manifest save_uuid {manifest.save_uuid!r} does not match run {run_id!r}'s own "
            f"save_uuid {run_save_uuid!r} -- refusing to classify a manifest against the wrong run's state",
            file=sys.stderr,
        )
        return 1

    event_seqs = {r["seq"] for r in reader.records(EVENTS_STREAM) if "event_type" in r["payload"]}
    head_seq = max(event_seqs, default=-1)
    max_tick = _max_tick(reader)
    head_gamets = float(max_tick) if max_tick is not None else 0.0

    branch_state = BranchState(
        known=True,
        head_generation=generation,
        head_seq=head_seq,
        head_gamets=head_gamets,
        known_generations=frozenset({generation}),
    )
    resolution = resolve(manifest, branch_state)
    payload = json.dumps(_sync_resolution_payload(resolution), indent=2, sort_keys=False)

    if resolution.decision is ResolveDecision.CONTINUE:
        print(payload)
        return 0

    if resolution.decision in (ResolveDecision.FORK, ResolveDecision.ADOPT):
        print(payload)
        print(
            f"chronicle: sync-check computed {resolution.decision.value} for run {run_id!r}, but no fork-on-disk "
            "mechanism exists yet to act on it -- chronicle/framelog.py's on-disk format bakes in exactly one "
            "(save_uuid, generation) pair per run, and EventLog.fork() (chronicle/events.py) has no on-disk "
            "counterpart (docs/design/chronicle-sync-cli-integration.md §0). The decision above is real -- only "
            "the write side is unbuilt.",
            file=sys.stderr,
        )
        return 3

    # Unreachable in practice: NEW_TIMELINE needs known=False (never true
    # here -- the run exists on disk by definition), LEGACY_IMPORT is
    # already handled above, pre-resolve(), on the raw format_version
    # (manifest.format_version is <= SUPPORTED_FORMAT_VERSION by the time
    # resolve() sees it), and DEGRADED is never produced by resolve() at
    # all (see its docstring). A defensive fallback, not a real branch --
    # if this ever fires it means resolve()'s contract changed underneath
    # this command.
    raise AssertionError(f"chronicle: sync-check: resolve() returned an unexpected decision {resolution.decision!r}")


def _sync_resolution_payload(resolution: Resolution) -> dict[str, Any]:
    """The JSON-serializable form of a ``chronicle.sync.Resolution`` printed to stdout."""
    return {
        "decision": resolution.decision.value,
        "branch_generation": resolution.branch_generation,
        "fork_parent_generation": resolution.fork_parent_generation,
        "fork_at_gamets": resolution.fork_at_gamets,
        "replay_from_seq": resolution.replay_from_seq,
        "save_uuid_hint": resolution.save_uuid_hint,
    }


# ---------------------------------------------------------------------------
# argparse wiring
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="chronicle", description="Agent-debug CLI over a Chronicle run's frame log.")
    parser.add_argument("--runs-dir", type=Path, default=None, help="override the runs directory (else $CHRONICLE_RUNS_DIR or ./runs)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_inspect = sub.add_parser("inspect", help="one NPC's beliefs and social standing as of a tick")
    p_inspect.add_argument("pos1", nargs="?", metavar="run_id", help="the run id (positional form) or the npc id (with --run)")
    p_inspect.add_argument("pos2", nargs="?", metavar="npc_id", help="the npc id (positional form)")
    p_inspect.add_argument("--run", default=None, help="the run id (flag form)")
    p_inspect.add_argument("--at", type=int, default=None, help="tick to inspect (default: the run's max tick)")
    p_inspect.set_defaults(func=inspect_command)

    p_trace = sub.add_parser("trace", help="one claim's provenance chain and variant lineage as of a tick")
    p_trace.add_argument("pos1", nargs="?", metavar="run_id", help="the run id (positional form) or the claim id (with --run)")
    p_trace.add_argument("pos2", nargs="?", metavar="claim_id", help="the claim id (positional form)")
    p_trace.add_argument("--run", default=None, help="the run id (flag form)")
    p_trace.add_argument("--at", type=int, default=None, help="tick to trace as of (default: the run's max tick)")
    p_trace.set_defaults(func=trace_command)

    p_feed = sub.add_parser("feed", help="the encounter feed in text form, filtered, in tick order")
    p_feed.add_argument("pos_run", nargs="?", metavar="run_id", help="the run id (positional form)")
    p_feed.add_argument("--run", default=None, help="the run id (flag form)")
    p_feed.add_argument("--location", default=None, help="only records at this location_id")
    p_feed.add_argument("--npc", default=None, help="only records naming this npc_id")
    p_feed.add_argument("--at", type=int, default=None, help="only records up to this tick (default: all)")
    p_feed.add_argument("--from-tick", type=int, default=None, dest="from_tick")
    p_feed.add_argument("--to-tick", type=int, default=None, dest="to_tick", help="same as --at")
    p_feed.add_argument("--limit", type=int, default=50, help="max records to print (default 50; <=0 means all)")
    p_feed.set_defaults(func=feed_command)

    p_inject = sub.add_parser("inject", help="append a canonical event (--event) or compose/validate its JSON (--type; no write)")
    p_inject.add_argument("pos_run", nargs="?", metavar="run_id", help="the run id (positional form, with --event)")
    p_inject.add_argument("--run", default=None)
    p_inject.add_argument("--at", type=int, default=None)
    p_inject.add_argument("--type", default=None)
    p_inject.add_argument("--actor", default=None)
    p_inject.add_argument("--payload", default=None)
    p_inject.add_argument("--event", default=None, help="a full events-stream payload as JSON (schema §3); appends it to the run's events.jsonl")
    p_inject.add_argument(
        "--origin-kind",
        default=None,
        dest="origin_kind",
        help="override the injected event's origin.kind (schema §3: scenario|console|adapter); defaults to 'console'",
    )
    p_inject.add_argument(
        "--origin-detail",
        default=None,
        dest="origin_detail",
        help="override the injected event's origin.detail; defaults to 'chronicle inject'",
    )
    p_inject.set_defaults(func=inject_command)

    p_fork = sub.add_parser(
        "fork",
        help="fork a run at a historical tick into a new run, generation+1 (docs/design/fork-on-disk-support.md)",
    )
    p_fork.add_argument("pos_run", nargs="?", metavar="run_id", help="the parent run id (positional form)")
    p_fork.add_argument("--run", default=None, help="the parent run id (flag form)")
    p_fork.add_argument("--at-tick", type=int, required=True, dest="at_tick", help="the tick to fork at (inclusive)")
    p_fork.add_argument(
        "--new-run-id",
        default=None,
        dest="new_run_id",
        help="id for the new run (default: '<run_id>-fork-<at_tick>')",
    )
    p_fork.set_defaults(func=fork_command)

    p_sync_check = sub.add_parser(
        "sync-check",
        help=(
            "classify a co-save manifest against a run's state (chronicle.sync.resolve); CONTINUE is the only "
            "decision this can act on today -- FORK/ADOPT are computed and reported but not applied (no on-disk "
            "fork mechanism exists yet, docs/design/chronicle-sync-cli-integration.md); NEW_TIMELINE/LEGACY_IMPORT "
            "are report-only"
        ),
    )
    p_sync_check.add_argument("pos_run", nargs="?", metavar="run_id", help="the run id (positional form)")
    p_sync_check.add_argument("--run", default=None, help="the run id (flag form)")
    p_sync_check.add_argument(
        "--manifest",
        required=True,
        help=(
            "the co-save manifest as JSON (chronicle.sync.Manifest's fields: format_version, save_uuid, "
            "generation, parent_generation, head_seq, gamets, wall_ts)"
        ),
    )
    p_sync_check.set_defaults(func=sync_check_command)

    return parser


def run(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point returning an exit code: wraps run(), turning SystemExit into (printed message, code)."""
    try:
        return run(argv)
    except SystemExit as exc:
        if exc.code is None or isinstance(exc.code, int):
            return exc.code or 0
        print(exc.code, file=sys.stderr)
        return 1
