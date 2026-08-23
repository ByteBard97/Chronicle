"""Agent-debug CLI subcommand logic for ``python -m chronicle`` (docs/dashboard-build-plan.md §2 M1).

Read-only consumers of ``chronicle/framelog.py``'s ``FrameLogReader`` --
``inspect``/``trace``/``feed`` reconstruct or scan a run's log and print
what they find; nothing here mutates ``claims.py``/``social.py``/
``schedule.py`` or writes to a run's log. ``inject`` composes and validates
canonical-event JSON (docs/frame-log-schema.md §3) but never appends it --
writing an injected event is the deferred fork milestone's job
(docs/dashboard-build-plan.md §3), not this module's.

Flag names for ``inject`` are pinned to the exact CLI invocation string
``dashboard/src/components/InjectionConsole.vue`` composes and displays
(``chronicle inject --run <runId> --at <atTick> --type <eventType>
[--actor <actor>] --payload '<json>'``) -- see the module docstring on
``inject_command`` for the verified match/mismatch findings against the
work packet's own (slightly different) flag sketch.
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
from chronicle.framelog import TRACE_STREAM, FrameLogReader, default_runs_dir

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


# ---------------------------------------------------------------------------
# inspect
# ---------------------------------------------------------------------------


def inspect_command(args: argparse.Namespace) -> int:
    """``inspect <npc_id> --run <run_id> --at <tick>``: one NPC's beliefs and social-layer standing as of a tick.

    Reconstructs derived state via ``FrameLogReader.state_at()`` (Lane 4's
    reader), then reports through ``ClaimStore``/``SocialStateStore``'s
    read-only accessors what the build plan's M1 bullet asks for: beliefs
    (claim, variant, confidence/verbatim/gist strengths -- decayed
    analytically at query time per ui-spec §1.1's no-sampled-histories
    rule -- and rumor stage via ``stage_at()``), plus any relationship,
    grudge, obligation, or reputation record naming this NPC on either
    side.
    """
    reader = _reader_for(args.run, runs_dir=args.runs_dir)
    state = reader.state_at(args.at)
    npc_id = args.npc_id
    at_gamets = float(args.at)

    print(f"=== {npc_id} @ tick {args.at} (run {args.run}) ===")

    beliefs = state.claims.beliefs_of(npc_id)
    print(f"\n-- beliefs ({len(beliefs)}) --")
    if not beliefs:
        print("  (none)")
    for belief in sorted(beliefs, key=lambda b: b.id):
        claim = state.claims.claim(belief.claim_id)
        variant = state.claims.variant(belief.variant_id) if belief.variant_id is not None else None
        decayed = decay(belief, at_gamets)
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


def trace_command(args: argparse.Namespace) -> int:
    """``trace <claim_id> --run <run_id> --at <tick>``: one claim's full evidence/variant lineage as of a tick.

    ``ClaimStore`` has no ``beliefs_by_claim`` accessor (only
    ``beliefs_of(holder_id)`` and ``belief_of(holder_id, claim_id)``, both
    keyed by holder) -- finding: reads the private ``_beliefs`` dict
    directly to find every belief about this claim, same precedent as
    ``inspect_command`` above. For each belief, walks ``chain_for()`` back
    to the witnessed root (witness -> retellings -> corroborations, per
    ADR-0007), then separately reports any ``supersession`` trace record
    naming one of the claim's variants -- the claim/variant/belief store
    doesn't materialize supersession itself (it is a Tier-2 trace record,
    docs/frame-log-schema.md §4), so that part comes from scanning
    ``trace.jsonl`` directly via ``FrameLogReader.records()``.
    """
    reader = _reader_for(args.run, runs_dir=args.runs_dir)
    state = reader.state_at(args.at)
    claim_id = args.claim_id

    try:
        claim = state.claims.claim(claim_id)
    except KeyError:
        print(f"chronicle: no claim {claim_id!r} exists as of tick {args.at}", file=sys.stderr)
        return 1

    print(f"=== claim {claim.id} ({claim.kind}) @ tick {args.at} (run {args.run}) ===")
    print(f"slots: {claim.slots}  truth_status={claim.truth_status}")

    beliefs = sorted(
        (b for b in state.claims._beliefs.values() if b.claim_id == claim_id),
        key=lambda b: b.id,
    )
    variant_ids = {b.variant_id for b in beliefs if b.variant_id is not None}

    print(f"\n-- belief chains ({len(beliefs)} holder(s)) --")
    for belief in beliefs:
        chain = state.claims.chain_for(belief.id)
        print(f"holder {belief.holder_id}:")
        for held_belief, evidence in reversed(chain):
            print(_chain_line(held_belief, evidence))

    supersessions = [
        record
        for record in reader.records(TRACE_STREAM, upto_tick=args.at)
        if record["payload"].get("record_type") == "supersession"
        and (
            record["payload"].get("loser_variant_id") in variant_ids
            or record["payload"].get("winner_variant_id") in variant_ids
        )
    ]
    print(f"\n-- supersessions involving this claim's variants ({len(supersessions)}) --")
    for record in supersessions:
        payload = record["payload"]
        print(
            f"  tick {record['tick']}: {payload['holder_id']} -- "
            f"{payload['loser_variant_id']} superseded by {payload['winner_variant_id']} "
            f"via {payload['resolution_rule']} (confidence_dent={payload['confidence_dent']})"
        )

    return 0


# ---------------------------------------------------------------------------
# feed
# ---------------------------------------------------------------------------

_NPC_FIELDS = ("npc_a", "npc_b", "holder_id", "teller_id", "hearer_id", "source_id")


def _record_matches(payload: dict[str, Any], *, location_id: str | None, npc_id: str | None) -> bool:
    if location_id is not None and payload.get("location_id") != location_id:
        return False
    return npc_id is None or any(payload.get(field) == npc_id for field in _NPC_FIELDS)


def feed_command(args: argparse.Namespace) -> int:
    """``feed --run <run_id> [--location <id>] [--npc <id>] [--from-tick <t>] [--to-tick <t>]``.

    A read-only CLI view over ``trace.jsonl`` in tick order, filtered by
    the given criteria -- not the M2 dashboard encounter feed (no
    pagination/virtualization; a scenario-scale run's trace stream reads
    fine straight off disk for a shell query).

    ``FrameLogReader.records()`` yields records in *file* order, which is
    tick order for an encounter-driven driver run but is **not**
    guaranteed for a hand-scripted scenario (e.g.
    ``scenarios/test_jarl_death_belief_cascade.py`` writes gamets
    1000/1050/1100/1000/1005 -- a later witness() call at an earlier
    gamets than the retell before it). This command materializes the
    filtered set and sorts by ``(tick, seq)`` before printing, rather than
    trusting file order, so "in tick order" holds for every run this CLI
    might be pointed at, not just the common case.
    """
    reader = _reader_for(args.run, runs_dir=args.runs_dir)
    matching = [
        record
        for record in reader.records(TRACE_STREAM, upto_tick=args.to_tick)
        if (args.from_tick is None or record["tick"] >= args.from_tick)
        and _record_matches(record["payload"], location_id=args.location, npc_id=args.npc)
    ]
    matching.sort(key=lambda record: (record["tick"], record["seq"]))
    for record in matching:
        record_type = record["payload"].get("record_type", "?")
        print(f"tick {record['tick']:>6}  seq {record['seq']:>4}  {record_type:<22} {json.dumps(record['payload'])}")
    print(f"\n({len(matching)} matching record(s))", file=sys.stderr)
    return 0


# ---------------------------------------------------------------------------
# inject
# ---------------------------------------------------------------------------

# Known canonical event kinds (chronicle/events.py, mirrored per
# docs/frame-log-schema.md §3) that inject validates --type against.
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

# The console's "actor (optional)" field is generic; canonical events name
# their primary actor differently per kind. This mapping is this lane's
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


def inject_command(args: argparse.Namespace) -> int:
    """``inject --run <run_id> --at <tick> --type <event_type> [--actor <actor>] [--payload <json>]``.

    Composes and pretty-prints the canonical-event JSON for the given
    type/payload (docs/frame-log-schema.md §3), validated against
    ``chronicle/events.py``'s known event kinds. **Does not write to the
    run's log** -- ui-spec §3.1 and the build plan's §3 place live
    fork-write injection in the deferred fork milestone; this command's
    job stops at composing and validating.

    Flag names are pinned to ``InjectionConsole.vue``'s composed
    invocation string: ``--run``, ``--at``, ``--type``, optional
    ``--actor``, and ``--payload`` (a JSON object string) -- see this
    module's docstring and this lane's report for the verified match
    against the work packet's own flag sketch (which said
    ``--payload-json``; the Vue component's ``--payload`` is what's
    actually displayed to a user for copy/paste, so it wins).
    """
    event_type = args.type
    if event_type in _RESERVED_EVENT_TYPES:
        print(
            f"chronicle: event type {event_type!r} is reserved for {_RESERVED_EVENT_TYPES[event_type]} "
            "and has no producer yet (docs/frame-log-schema.md §3) -- not injectable",
            file=sys.stderr,
        )
        return 1
    if event_type not in _EVENT_FIELDS:
        known = ", ".join(sorted(_EVENT_FIELDS))
        print(f"chronicle: unknown event type {event_type!r} -- known kinds: {known}", file=sys.stderr)
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
    print(f"# run={args.run} at={args.at} type={event_type} -- NOT written to the run's log (M1 scope)")
    print(json.dumps(composed, indent=2, sort_keys=False))
    return 0


# ---------------------------------------------------------------------------
# argparse wiring
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="chronicle", description="Agent-debug CLI over a Chronicle run's frame log.")
    parser.add_argument("--runs-dir", type=Path, default=None, help="override the runs directory (else $CHRONICLE_RUNS_DIR or ./runs)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_inspect = sub.add_parser("inspect", help="one NPC's beliefs and social standing as of a tick")
    p_inspect.add_argument("npc_id")
    p_inspect.add_argument("--run", required=True)
    p_inspect.add_argument("--at", type=int, required=True)
    p_inspect.set_defaults(func=inspect_command)

    p_trace = sub.add_parser("trace", help="one claim's evidence/variant lineage as of a tick")
    p_trace.add_argument("claim_id")
    p_trace.add_argument("--run", required=True)
    p_trace.add_argument("--at", type=int, required=True)
    p_trace.set_defaults(func=trace_command)

    p_feed = sub.add_parser("feed", help="filtered trace-stream records in tick order")
    p_feed.add_argument("--run", required=True)
    p_feed.add_argument("--location", default=None)
    p_feed.add_argument("--npc", default=None)
    p_feed.add_argument("--from-tick", type=int, default=None, dest="from_tick")
    p_feed.add_argument("--to-tick", type=int, default=None, dest="to_tick")
    p_feed.set_defaults(func=feed_command)

    p_inject = sub.add_parser("inject", help="compose/validate a canonical-event JSON payload (does not write)")
    p_inject.add_argument("--run", required=True)
    p_inject.add_argument("--at", type=int, required=True)
    p_inject.add_argument("--type", required=True)
    p_inject.add_argument("--actor", default=None)
    p_inject.add_argument("--payload", default=None)
    p_inject.set_defaults(func=inject_command)

    return parser


def run(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
