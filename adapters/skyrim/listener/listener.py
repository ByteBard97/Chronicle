"""ChronicleBridge listener -- receives ChronicleBridge's outbound POSTs
(adapters/skyrim/contracts/chronicle-bridge.openapi.yaml) and either
writes a rolling JSON snapshot file (/whiterun/positions) or appends a
canonical event to a live run (/whiterun/events,
docs/design/chronicle-bridge-death-extraction.md). Stdlib-only (matches
the throwaway probe's own "http.server is enough" choice) plus pydantic
for schema validation against the generated models.py -- never hand-parse
the body, the whole point of the shared contract is that a malformed
payload is rejected here, not silently misinterpreted.

Not part of chronicle/ -- see this directory's README.md for why, and for
how to regenerate models.py when the contract changes. /whiterun/events
does not import chronicle/ either; it shells out to the same
`python -m chronicle inject` CLI write path a human uses at the console
(chronicle/cli.py), the documented seam boundary, stamped
`--origin-kind adapter` so it's never mislabeled as a console injection.

    uv run --with pydantic python adapters/skyrim/listener/listener.py --shared-secret <token>
    uv run --with pydantic python adapters/skyrim/listener/listener.py --shared-secret <token> --live-run <run_id>

/whiterun/events is unavailable (503) unless --live-run is given -- there
is deliberately no default and no auto-selection of an existing run. Never
point --live-run at a fixture/demo run the M7 release gate or the ladder's
scenario tests depend on (e.g. runs/north-star-01); always a dedicated
live-play run, since injected events are ordinary appends with no undo.

Trust model: this binds 0.0.0.0 because the real topology is a separate
Windows machine on the LAN POSTing in -- it can't be restricted to
loopback. There is no real authentication scheme here (no TLS, no user
accounts) -- `--shared-secret` is a lightweight bearer-token check meant
to stop an accidental/opportunistic LAN neighbor from writing garbage into
the snapshot file, not to withstand a targeted attacker. Do not expose
this port beyond a trusted home LAN.

GET /whiterun/hydration and POST /whiterun/hydration/ack (docs/design/
chronicle-bridge-hydration-out.md §3b, and the ack protocol added to close
the "delivered before confirmed" gap named in fad0d79's commit message):
a pair served by the GET is tracked as "offered-awaiting-ack", not
"delivered", until the C++ poller's ack tells the listener what actually
happened -- see `_HydrationPairState`'s docstring for the full state
machine. The ack endpoint is a plain hand-rolled JSON array (no pydantic
model, matching the GET response's own ad hoc shape below -- neither is
part of the OpenAPI contract; both are this listener's own read/ack
protocol layered on top of it), gated the same way as every other
--live-run-only route. Its in-memory state still does NOT persist across
listener restarts -- same limitation as before, just carried in a richer
per-pair state machine now instead of a single "last pushed rank" int.

GET /whiterun/avoidance and POST /whiterun/avoidance/ack (docs/design/
chronicle-bridge-avoidance-out.md): the same poll/ack protocol shape as
hydration, applied to rule 18's already-computed avoidance-pair state
(`chronicle.avoidance.is_avoiding`, reusing `chronicle.driver`'s own
`_avoidance_thresholds` condition, never a second copy of it) instead of
the relationship-rank bucketing. Two structural differences from
hydration, both because avoidance is a different shape of fact:
symmetric, not directed (a grudge is holder->target, but rule 18's own
`frozenset((npc_a, npc_b))` treats a grudge PAIR as mutual for avoidance
purposes) -- so the response's `npc_a`/`npc_b` are canonicalized
lexicographically (`sorted((a, b))`) rather than preserving
holder/target, and the same canonicalization is applied to an incoming
ack's pair before looking up its state, so a caller that echoes the pair
in either order still resolves to the same entry; and a two-outcome ack
(`applied`/`retry`), not hydration's three, because avoidance has no
`no_relationship`-equivalent permanent-failure case -- it depends only on
whether both NPCs are named-cast (already filtered) and whether a live
game/actor reference is available (`retry`, temporary), never on an
authored vanilla record that may not exist. See `_AvoidancePairState`'s
docstring for the state machine (same shape as `_HydrationPairState`'s,
minus the third outcome and its per-rank scoping -- here there is only
ever one tracked fact per pair, "is it avoiding").

GET /whiterun/vendor-markup and POST /whiterun/vendor-markup/ack
(docs/design/chronicle-bridge-vendor-markup-out.md): the same poll/ack
protocol shape as hydration, applied to `chronicle.vendor_markup.
markup_multiplier_for`'s continuous grudge-severity-to-price-multiplier
curve instead of the relationship-rank bucketing. Directed, like
hydration (a grudge holder marks up prices toward its target -- a
one-directional fact), NOT symmetric like avoidance -- the response's
`holder_id`/`target_id` are never canonicalized/sorted, the pair is
served exactly as the underlying `Grudge` names it. Two-outcome ack
(`applied`/`retry`), same as avoidance and NOT hydration's three: a
vendor-markup write has no `no_relationship`-equivalent permanent-failure
case the way hydration's `BGSRelationship::GetRelationship()` lookup
does -- it never depends on an authored vanilla record that might not
exist. The eventual game-side consumer (writing a price multiplier at
barter-menu open, per the design doc's §0) only ever fails because no
game is active or an NPC reference doesn't resolve -- both temporary,
retry-worthy conditions, never a permanent "no such record" case. See
`_VendorMarkupPairState`'s docstring for the state machine (same shape as
`_AvoidancePairState`'s: two outcomes, no per-rank scoping, since there
is only ever one tracked fact per pair -- its current multiplier).

GET /whiterun/evidence and POST /whiterun/evidence/ack (docs/design/
chronicle-bridge-diegetic-evidence-out.md): the same poll/ack protocol
shape as the other three, applied to `chronicle.diegetic_evidence.
should_reveal_evidence`'s decayed-belief-confidence threshold gate
instead of a `Grudge` read -- this is the first of the four "Out" slices
to read `chronicle.claims.ClaimStore` rather than `chronicle.social.
SocialStateStore`. Structurally different from all three prior slices in
two ways, both because "an NPC's belief crossed a confidence threshold"
is a different shape of fact than any of theirs: **single-key, not a
pair** -- there is no second party, so the tracked key is
`(holder_id, belief_id)`, not a directed or symmetric pair of NPC ids
(design doc §2's own framing: "near the NPC who now believes it," not
"near the claim's subject" -- `Claim.slots` has no standardized subject
field to resolve one from generically); and **one-shot, with no re-offer
on decay**, unlike hydration's re-offered-on-any-rank-change or
avoidance's re-evaluated-every-poll booleans -- a `PlaceObjectAtMe` spawn
has no retraction mechanism in this cut, so once an entry reaches
`applied` it is a true terminal state, never re-offered again even if the
belief's confidence later decays back below threshold or rises again
(design doc §3, a named limitation, not a bug). Two-outcome ack
(`applied`/`retry`), same as avoidance/vendor-markup and unlike
hydration's three: a `PlaceObjectAtMe` call has no `no_relationship`-
equivalent permanent-failure mode. Gated identically to the other three
(503 without `--live-run`, same auth, restricted to `NAMED_CAST_NPC_IDS`
-- only named-cast NPCs have a resolvable `Actor*` for a C++ consumer to
spawn evidence at; vendor-markup is the one exception to that parity,
accepting `PLAYER_ID` on its target side, see `_vendor_markup_pairs`). See `_EvidenceEntryState`'s docstring for the state
machine.

Like the other three slices, evidence's in-memory state does not survive
a listener restart -- same named gap, same "identical to a `retry` ack"
restart behavior EXCEPT for an already-`applied` entry, which a restart
forgets entirely (there is no persistence across restarts for any of
these state machines) even though this cut's own within-process contract
says `applied` is otherwise permanent -- a real, named limitation of the
in-memory-only state, not a new one specific to evidence.

POST /whiterun/sync/hello and POST /whiterun/sync/mutation (docs/design/
chronicle-bridge-sync-handshake-out.md): the save/reload sync handshake's
service half. Calls straight into `chronicle.sync.resolve()`/
`mutation_admissible()` (never re-implements the six-way RESOLVE decision
table) and `chronicle.framelog.event_from_record()` (never re-implements
per-event-type reconstruction) -- see `_process_hello`/`_process_mutation`.
Unlike every write path above, these two import `chronicle.events`/
`chronicle.sync` directly rather than shelling out to `python -m chronicle
inject`: the design doc's §4.4 explains why -- `EventLog.append()` IS the
mutation endpoint's commit point, so it must happen synchronously,
in-process, in the same request that replies to the shim, and there is no
run/framelog concept involved at all (sync state is a durable per-
save_uuid sidecar, not a run directory). Bearer-token auth only, NOT
gated behind `--live-run` (design doc §8b item 3 -- sync state is keyed
by `save_uuid`, orthogonal to demo runs). Unlike every per-slice state
dict above (`hydration_pair_states` and friends), the sync handshake's
own session state (active epoch, hello_seq, the single tracked
generation/head_seq/head_gamets triple) is durable -- one JSON file per
save_uuid under `--sync-state-dir`, written synchronously on every change
-- because, per the design doc's §4.3, this is the one slice where a
listener restart would be silent timeline corruption if left in-memory
like everything else here. The mutation endpoint's own `EventLog`
instance (`mutation_event_log`, used only for its `.append()` idempotency)
is, deliberately, NOT part of that durability story and does not survive
a restart -- see `_SyncSessionState`'s docstring.

Read-only exception, /whiterun/hydration (docs/design/chronicle-bridge-
hydration-out.md §3b): this one route DOES import chronicle/ directly
(`chronicle.framelog.FrameLogReader`/`state_at`, `chronicle.social`,
`chronicle.hydration.relationship_rank_for`, `chronicle.avoidance.
is_avoiding`, `chronicle.vendor_markup.markup_multiplier_for`,
`chronicle.diegetic_evidence.should_reveal_evidence`), unlike every write
path in this file. The house rule above -- "shell out to `python -m chronicle`,
never import chronicle/ directly" -- exists to keep *writes* going
through the CLI's own validation/refusal logic (fork-territory checks,
origin stamping) so this listener can never silently corrupt a run. This
endpoint has no write path at all: it only reconstructs a run's existing
on-disk state (the same `FrameLogReader.state_at()` read `chronicle
sync-check`/`chronicle inspect` already do from inside the CLI process)
and computes a pure function over it. There is nothing for the CLI
boundary to protect here -- a direct import can't corrupt a run it never
writes to -- and shelling out to a fresh `python -m chronicle` subprocess
would still have to pay interpreter startup on top of the same
`state_at()` log replay the direct import already does, buying no safety
in exchange. Write access to a run still goes through the CLI
exclusively -- this exception is scoped to this one GET handler and must
not be used as precedent for adding new write paths that skip the CLI.
"""

import argparse
import dataclasses
import json
import re
import secrets
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).parent))
from models import EventType, GameEvent, PositionSnapshot

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
from chronicle.avoidance import is_avoiding
from chronicle.diegetic_evidence import should_reveal_evidence
from chronicle.events import EventLog
from chronicle.framelog import FrameLogReader, default_runs_dir, event_from_record
from chronicle.hydration import RANK_NO_GRUDGE, relationship_rank_for
from chronicle.sync import (
    BranchState,
    Manifest,
    ResolveDecision,
    legacy_import_resolution,
    mutation_admissible,
    resolve,
)
from chronicle.vendor_markup import MARKUP_NO_MARKUP, markup_multiplier_for

# Mirrors adapters/skyrim/ChronicleBridge/src/IdentityMap.cpp's kNamedCast
# table exactly (chronicleNpcId column) -- the same 19-entry set
# chronicle/tests/test_fixtures.py's NAMED_CAST_NPC_IDS already hardcodes
# for its own sync check. Only NPCs in this set have a resolvable in-game
# actor reference `SetRelationshipRank` could ever be called on (design
# doc §3), so /whiterun/hydration filters grudges down to pairs entirely
# within this set. Keep this in sync with IdentityMap.cpp by hand -- there
# is no shared source of truth between C++ and Python for this table.
NAMED_CAST_NPC_IDS = frozenset(
    {
        "ysolda",
        "idolaf_battle_born",
        "saffir",
        "carlotta_valentia",
        "amren",
        "adrianne_avenicci",
        "lars_battle_born",
        "braith",
        "fralia_gray_mane",
        "nazeem",
        "lillith_maiden_loom",
        "brenuin",
        "anoriath",
        "lucia",
        "heimskr",
        "sigurd",
        "olava_the_feeble",
        "danica_pure_spring",
        "olfina_gray_mane",
    }
)

# The player-as-an-actor identity, this project's established convention
# (chronicle/fixtures/north_star.py's KILLER = "the_player"). Deliberately
# NOT a member of NAMED_CAST_NPC_IDS -- the player is not an NPC and has no
# IdentityMap.cpp row -- but it IS a legitimate `target_id` on the
# /whiterun/vendor-markup route specifically: adapters/skyrim/
# ChronicleBridge/src/VendorMarkupCache.cpp (kPlayerTargetId, line 24)
# keeps ONLY pairs with target_id == "the_player" out of that endpoint's
# response, since a vendor's markup toward some other NPC has no
# barter-menu meaning. See _vendor_markup_pairs.
PLAYER_ID = "the_player"

_write_lock = threading.Lock()

# adapters/skyrim/listener/listener.py -> repo root, three parents up.
# `python -m chronicle` needs cwd here to import the chronicle/ package
# (not installed; a plain top-level package, same as every test/CLI
# invocation in this repo already assumes).
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# A snapshot with hundreds of NPCs at ~40 bytes/entry is still well under
# 100KB -- 1MiB is generous headroom, not a real limit on legitimate
# traffic. Anything bigger is either a bug or someone probing the port,
# and must be rejected before `rfile.read()`, not after: reading an
# attacker-declared Content-Length unconditionally is an unbounded
# memory-allocation footgun regardless of how small real payloads are.
_MAX_BODY_BYTES = 1 * 1024 * 1024


def _inject_death_event(event: GameEvent, *, live_run: str) -> tuple[bool, str]:
    """Shell out to ``python -m chronicle inject`` (never import chronicle/ --
    the documented seam boundary, this directory's README.md). Returns
    (ok, message) -- message is stdout on success, stderr on failure, so
    the caller can log/relay chronicle's own reason for a rejection (e.g.
    a historical-tick refusal) rather than swallowing it.
    """
    payload = {
        "event_type": event.event_type.value,
        "gamets": event.gamets,
        "npc_id": event.npc_id,
        "cause": event.cause if event.cause is not None else "unknown",
    }
    if event.killer_id is not None:
        payload["killer_id"] = event.killer_id
    if event.location_id is not None:
        payload["location_id"] = event.location_id

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "chronicle",
            "inject",
            live_run,
            "--event",
            json.dumps(payload),
            "--origin-kind",
            "adapter",
            "--origin-detail",
            "chronicle-bridge death event",
        ],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return False, result.stderr.strip()
    return True, result.stdout.strip()


def _inject_crime_witnessed_event(event: GameEvent, *, live_run: str) -> tuple[bool, str]:
    """Sibling of ``_inject_death_event`` for the crime-witness slice
    (docs/design/chronicle-bridge-crime-witness-out.md §4): same shell-out-
    to-``python -m chronicle inject`` discipline, ``--origin-kind adapter``,
    never imports ``chronicle/`` directly.
    """
    payload = {
        "event_type": event.event_type.value,
        "gamets": event.gamets,
        "witness_id": event.witness_id,
        "perpetrator_id": event.perpetrator_id,
        "crime_type": event.crime_type,
    }
    if event.victim_id is not None:
        payload["victim_id"] = event.victim_id
    if event.location_id is not None:
        payload["location_id"] = event.location_id

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "chronicle",
            "inject",
            live_run,
            "--event",
            json.dumps(payload),
            "--origin-kind",
            "adapter",
            "--origin-detail",
            "chronicle-bridge crime_witnessed event",
        ],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return False, result.stderr.strip()
    return True, result.stdout.strip()


def _max_tick(reader: FrameLogReader) -> int | None:
    """The run's current max tick across both streams -- mirrors chronicle/cli.py's own helper of the same name."""
    index = reader.read_index()
    ticks = [int(t) for stream in index["streams"].values() for t in stream["tick_offsets"]]
    return max(ticks) if ticks else None


@dataclasses.dataclass
class _HydrationPairState:
    """One entry in the per-(holder_id, target_id) hydration state machine.

    Closes the gap named in fad0d79's commit message: the old code marked
    a pair "delivered" (updated its dedupe cache) the instant it was
    served by GET /whiterun/hydration, before the C++ poller ever
    confirmed the write succeeded. Now a pair moves through explicit
    states, and only an ack (or a rank change) advances it:

        (absent from the dict)          -- "not-yet-offered": baseline,
                                            equivalent to a settled rank of
                                            RANK_NO_GRUDGE (0). Every pair
                                            starts here, and a `retry` ack
                                            (or a listener restart -- the
                                            in-memory state is wiped either
                                            way) sends it back here too.
        status="awaiting_ack"           -- offered in a GET response, no
                                            ack received yet for this exact
                                            `rank`. A poll while
                                            awaiting-ack at the SAME rank is
                                            a no-op: this is what makes two
                                            back-to-back polls with no ack
                                            in between return the pair only
                                            once (in-flight, not a
                                            duplicate offer).
        status="applied"                -- the C++ poller confirmed it
                                            wrote `rank` in-game. A poll at
                                            the same rank is a no-op (the
                                            old cache's whole idempotency
                                            purpose, preserved).
        status="permanently_skipped"    -- the C++ poller confirmed
                                            `BGSRelationship::
                                            GetRelationship()` returned
                                            null for this exact `rank` --
                                            no authored vanilla
                                            relationship exists, so
                                            retrying the SAME rank forever
                                            would never succeed. A poll at
                                            the same rank is a no-op.

    The key insight tying rank changes to permanent-skip tracking: a
    "permanently_skipped" status is scoped to the *specific rank* it was
    recorded against, not to the pair as a whole. `_hydration_pairs`
    below only ever compares the freshly computed rank against
    `entry.rank` -- if they differ (the grudge decayed back to 0, got
    worse, or anything else), the pair is offered again regardless of
    what its previous status was. A rank that was once permanently
    skipped can still be offered again under a *different* rank; only the
    exact rank that produced a `no_relationship` ack is ever suppressed.

    `retry` carries no information worth remembering (unlike
    applied/permanently_skipped, which are meaningful outcomes tied to a
    specific rank) -- it is handled by simply deleting the dict entry,
    which is indistinguishable, at this data-structure level, from what a
    listener restart already does to every pair. Both simply forget the
    pair and re-evaluate it fresh on the next poll.

    A real gap this closes, found in review of the first version of this
    state machine: an explicit `retry` ack and a listener restart both
    self-correct, but a silently DROPPED ack (the C++ poller's
    PostHydrationAck POST fails or times out -- a real, expected
    possibility, since it's deliberately fire-and-forget, same as every
    other outbound call in ChronicleBridge) does not produce either of
    those. Without a timeout, a pair whose ack never arrives at all would
    stay "awaiting_ack" forever at that exact rank -- `_hydration_pairs`'s
    same-rank comparison would treat it as already-offered indefinitely,
    even though nothing was ever actually confirmed. `awaiting_since`
    exists to close exactly this: an "awaiting_ack" entry older than
    `_AWAITING_ACK_TIMEOUT_SECONDS` is treated as expired and re-offered
    on the next poll regardless of whether its rank changed, restoring
    the "a dropped ack is safe, not silently stuck" property the ack
    protocol is supposed to have.
    """

    rank: int
    status: str  # "awaiting_ack" | "applied" | "permanently_skipped"
    awaiting_since: float | None = None  # time.monotonic() when status became "awaiting_ack"; None otherwise.


# Comfortably longer than HydrationPoller.cpp's ~8s poll interval (a few
# poll cycles' worth of slack for an ack that's merely slow, not lost) but
# short enough that a genuinely dropped ack doesn't leave a pair stuck for
# an entire play session. A first-cut placeholder, not a measured constant
# -- same discipline as every other interval/threshold in this codebase.
_AWAITING_ACK_TIMEOUT_SECONDS = 60.0


_ACK_OUTCOMES = frozenset({"applied", "no_relationship", "retry"})


def _hydration_pairs(live_run: str, pair_states: dict[tuple[str, str], _HydrationPairState]) -> list[dict[str, object]]:
    """Compute changed (holder, target, rank) pairs for the live run's named-cast grudges.

    Reads the run's current on-disk state at its max tick (the same
    FrameLogReader/state_at pattern `chronicle sync-check`/`chronicle
    inspect` use), buckets every grudge whose holder and target are both
    in the named cast via relationship_rank_for(), and returns only the
    pairs whose bucketed rank differs from the pair's currently tracked
    rank in `pair_states` -- moving that pair to "awaiting_ack" at the new
    rank as it goes. See `_HydrationPairState`'s docstring for the full
    state machine this now drives (design doc §3b + the ack protocol that
    closes fad0d79's "delivered before confirmed" gap).
    """
    reader = FrameLogReader(default_runs_dir() / live_run)
    max_tick = _max_tick(reader)
    if max_tick is None:
        return []
    state = reader.state_at(max_tick)
    at_gamets = float(max_tick)

    changed: list[dict[str, object]] = []
    for grudge in state.social.grudges():
        if grudge.holder_id not in NAMED_CAST_NPC_IDS or grudge.target_id not in NAMED_CAST_NPC_IDS:
            continue
        rank = relationship_rank_for(grudge, at_gamets=at_gamets)
        key = (grudge.holder_id, grudge.target_id)
        entry = pair_states.get(key)

        # A stale "awaiting_ack" entry (its ack was silently dropped, not
        # explicitly retried) forces a re-offer even if the computed rank
        # hasn't changed, per _HydrationPairState's "awaiting_since"
        # doctrine -- without this, a dropped ack (a real, expected
        # possibility, since PostHydrationAck is fire-and-forget) would
        # leave the pair stuck forever at the same rank. This is a
        # DIFFERENT case from "no entry at all" (the genuine first-poll
        # case, handled below by the ordinary default-to-0 comparison) --
        # conflating the two here previously broke the first-poll case for
        # a sub-threshold (rank 0) grudge, caught by this file's own test
        # suite before it shipped.
        expired = (
            entry is not None
            and entry.status == "awaiting_ack"
            and entry.awaiting_since is not None
            and time.monotonic() - entry.awaiting_since > _AWAITING_ACK_TIMEOUT_SECONDS
        )

        # A pair absent from the state machine defaults to a settled rank
        # of 0 (no discount), not "unknown" -- 0 is the game's own default
        # relationship rank, so a pair that has always bucketed to 0 must
        # never be reported as a spurious "changed to 0" push on its very
        # first poll. This same comparison also implements every other
        # no-op case regardless of status (awaiting_ack/applied/
        # permanently_skipped): if the computed rank matches whatever rank
        # this pair is currently tracked at, there is nothing new to offer
        # -- UNLESS its awaiting_ack entry just expired, in which case it's
        # re-offered regardless of whether the rank matches.
        last_rank = entry.rank if entry is not None else RANK_NO_GRUDGE
        if not expired and rank == last_rank:
            continue
        pair_states[key] = _HydrationPairState(rank=rank, status="awaiting_ack", awaiting_since=time.monotonic())
        changed.append({"holder_id": grudge.holder_id, "target_id": grudge.target_id, "relationship_rank": rank})
    return changed


def _apply_hydration_ack(
    pair_states: dict[tuple[str, str], _HydrationPairState], holder_id: str, target_id: str, outcome: str
) -> None:
    """Advance one pair's state machine entry per an ack's outcome.

    Silently ignores an ack for a pair with no current entry (e.g. a
    stale ack that arrives after the pair's rank already changed and was
    re-offered under a new entry, or after a listener restart wiped
    state) -- there is nothing to update, and this must never crash the
    ack endpoint over a race that resolves itself on the next poll
    anyway.
    """
    entry = pair_states.get((holder_id, target_id))
    if entry is None:
        return
    if outcome == "applied":
        pair_states[(holder_id, target_id)] = _HydrationPairState(rank=entry.rank, status="applied")
    elif outcome == "no_relationship":
        pair_states[(holder_id, target_id)] = _HydrationPairState(rank=entry.rank, status="permanently_skipped")
    elif outcome == "retry":
        del pair_states[(holder_id, target_id)]


@dataclasses.dataclass
class _AvoidancePairState:
    """One entry in the per-(npc_a, npc_b) avoidance state machine -- the
    same protocol shape as `_HydrationPairState`, applied to a symmetric,
    two-outcome fact instead of a directed, per-rank one.

    `(npc_a, npc_b)` is always the canonical, lexicographically sorted
    ordering (`tuple(sorted((a, b)))`) -- the pair is looked up and stored
    under that key regardless of which order a grudge's holder/target (or
    an incoming ack) happened to name them in, since avoidance itself is
    mutual once it applies (design doc, and rule 18's own
    `frozenset((npc_a, npc_b))`).

        (absent from the dict)  -- "not-yet-offered": baseline, equivalent
                                    to a settled `avoiding=False`. Every
                                    pair starts here, and a `retry` ack (or
                                    a listener restart) sends it back here.
        status="awaiting_ack"   -- offered in a GET response, no ack
                                    received yet for this exact `avoiding`
                                    value. A poll while awaiting-ack at the
                                    SAME value is a no-op.
        status="applied"        -- the C++ poller confirmed it expressed
                                    this `avoiding` value in-game. A poll
                                    at the same value is a no-op.

    Unlike hydration's `permanently_skipped`, there is no third status
    here: avoidance has no `no_relationship`-equivalent permanent-failure
    case (see the module docstring's comparison), so an ack only ever
    settles a pair (`applied`) or forgets it for re-evaluation (`retry`,
    handled by deleting the entry -- indistinguishable from what a
    listener restart already does, same precedent as hydration's `retry`).

    `awaiting_since` closes the identical dropped-ack gap
    `_HydrationPairState` documents: an "awaiting_ack" entry older than
    `_AWAITING_ACK_TIMEOUT_SECONDS` is treated as expired and re-offered on
    the next poll regardless of whether its `avoiding` value changed.
    """

    avoiding: bool
    status: str  # "awaiting_ack" | "applied"
    awaiting_since: float | None = None  # time.monotonic() when status became "awaiting_ack"; None otherwise.


_AVOIDANCE_ACK_OUTCOMES = frozenset({"applied", "retry"})


def _avoidance_pairs(live_run: str, pair_states: dict[tuple[str, str], _AvoidancePairState]) -> list[dict[str, object]]:
    """Compute changed (npc_a, npc_b, avoiding) pairs for the live run's named-cast grudges.

    Groups every named-cast grudge by its unordered pair
    (`frozenset((holder_id, target_id))`) -- a mutual pair (both sides
    holding a grudge against the other) collapses to one group, the same
    "avoidance is about the pair, not the direction" rule
    `Driver._grudge_severities` already applies. `avoiding` for a group is
    true if ANY grudge in it currently satisfies `is_avoiding` (either
    direction can put the pair into avoidance) -- a stricter union than
    strictly necessary to replicate `Driver`'s own single-dict-entry
    internals, but the correct symmetric semantics for a read-only export
    that isn't required to reproduce that internal's incidental
    iteration-order behavior.

    Only pairs whose `avoiding` value differs from what's currently
    tracked in `pair_states` (or whose `awaiting_ack` entry has expired,
    per `_AvoidancePairState`'s docstring) are returned -- same dedupe/ack
    discipline as `_hydration_pairs`.
    """
    reader = FrameLogReader(default_runs_dir() / live_run)
    max_tick = _max_tick(reader)
    if max_tick is None:
        return []
    state = reader.state_at(max_tick)
    at_gamets = float(max_tick)

    grudges_by_pair: dict[frozenset[str], list] = {}
    for grudge in state.social.grudges():
        if grudge.holder_id not in NAMED_CAST_NPC_IDS or grudge.target_id not in NAMED_CAST_NPC_IDS:
            continue
        grudges_by_pair.setdefault(frozenset((grudge.holder_id, grudge.target_id)), []).append(grudge)

    changed: list[dict[str, object]] = []
    for pair, grudges in grudges_by_pair.items():
        avoiding = any(is_avoiding(g, at_gamets=at_gamets) for g in grudges)
        npc_a, npc_b = sorted(pair)
        key = (npc_a, npc_b)
        entry = pair_states.get(key)

        expired = (
            entry is not None
            and entry.status == "awaiting_ack"
            and entry.awaiting_since is not None
            and time.monotonic() - entry.awaiting_since > _AWAITING_ACK_TIMEOUT_SECONDS
        )

        last_avoiding = entry.avoiding if entry is not None else False
        if not expired and avoiding == last_avoiding:
            continue
        pair_states[key] = _AvoidancePairState(avoiding=avoiding, status="awaiting_ack", awaiting_since=time.monotonic())
        changed.append({"npc_a": npc_a, "npc_b": npc_b, "avoiding": avoiding})
    return changed


def _apply_avoidance_ack(
    pair_states: dict[tuple[str, str], _AvoidancePairState], npc_a: str, npc_b: str, outcome: str
) -> None:
    """Advance one pair's state machine entry per an ack's outcome.

    Canonicalizes `(npc_a, npc_b)` the same way `_avoidance_pairs` does
    before lookup, so an ack that echoes the pair in either order still
    resolves to the same tracked entry. Silently ignores an ack for a pair
    with no current entry -- same reasoning as `_apply_hydration_ack`:
    nothing to update, and a stale/racing ack must never crash this
    endpoint.
    """
    key = tuple(sorted((npc_a, npc_b)))
    entry = pair_states.get(key)
    if entry is None:
        return
    if outcome == "applied":
        pair_states[key] = _AvoidancePairState(avoiding=entry.avoiding, status="applied")
    elif outcome == "retry":
        del pair_states[key]


@dataclasses.dataclass
class _VendorMarkupPairState:
    """One entry in the per-(holder_id, target_id) vendor-markup state
    machine -- the same protocol shape as `_HydrationPairState`, applied
    to a directed pair (like hydration) but a two-outcome ack (like
    avoidance).

    `(holder_id, target_id)` is never canonicalized/sorted -- unlike
    `_AvoidancePairState`, this pair is directed (a grudge holder marks up
    prices toward its target; the reverse direction is a different,
    independently tracked fact, exactly like `_HydrationPairState`'s own
    holder/target shape), per docs/design/chronicle-bridge-vendor-markup-
    out.md's own ruling that this slice mirrors hydration's directed
    shape, not avoidance's symmetric one.

        (absent from the dict)  -- "not-yet-offered": baseline, equivalent
                                    to a settled multiplier of
                                    MARKUP_NO_MARKUP (1.0, no markup).
                                    Every pair starts here, and a `retry`
                                    ack (or a listener restart) sends it
                                    back here.
        status="awaiting_ack"   -- offered in a GET response, no ack
                                    received yet for this exact
                                    `multiplier` value. A poll while
                                    awaiting-ack at the SAME value is a
                                    no-op.
        status="applied"        -- the C++ poller confirmed it wrote this
                                    `multiplier` in-game. A poll at the
                                    same value is a no-op.

    No third status, same reasoning `_AvoidancePairState`'s docstring
    gives for its own two-outcome shape: a vendor-markup write has no
    `no_relationship`-equivalent permanent-failure case (see this file's
    module docstring) -- it depends only on whether both NPCs are
    named-cast (already filtered) and whether a live game/actor reference
    is available (`retry`, temporary), never on an authored vanilla
    record that may or may not exist. An ack only ever settles a pair
    (`applied`) or forgets it for re-evaluation (`retry`, handled by
    deleting the entry -- indistinguishable from what a listener restart
    already does, same precedent as hydration's and avoidance's `retry`).

    `awaiting_since` closes the identical dropped-ack gap
    `_HydrationPairState`/`_AvoidancePairState` document: an
    "awaiting_ack" entry older than `_AWAITING_ACK_TIMEOUT_SECONDS` is
    treated as expired and re-offered on the next poll regardless of
    whether its `multiplier` value changed.
    """

    multiplier: float
    status: str  # "awaiting_ack" | "applied"
    awaiting_since: float | None = None  # time.monotonic() when status became "awaiting_ack"; None otherwise.


_VENDOR_MARKUP_ACK_OUTCOMES = frozenset({"applied", "retry"})


def _vendor_markup_pairs(
    live_run: str, pair_states: dict[tuple[str, str], _VendorMarkupPairState]
) -> list[dict[str, object]]:
    """Compute changed (holder, target, markup_multiplier) pairs for the
    live run's grudges held BY a named-cast NPC (the vendor), against
    either another named-cast NPC or the player (`PLAYER_ID`).

    Directed, mirroring `_hydration_pairs` exactly (one entry per grudge,
    keyed on (holder_id, target_id), never canonicalized) rather than
    `_avoidance_pairs`'s symmetric grouping-by-unordered-pair. Only pairs
    whose computed multiplier differs from what's currently tracked in
    `pair_states` (or whose `awaiting_ack` entry has expired, per
    `_VendorMarkupPairState`'s docstring) are returned -- same dedupe/ack
    discipline as `_hydration_pairs`/`_avoidance_pairs`.
    """
    reader = FrameLogReader(default_runs_dir() / live_run)
    max_tick = _max_tick(reader)
    if max_tick is None:
        return []
    state = reader.state_at(max_tick)
    at_gamets = float(max_tick)

    changed: list[dict[str, object]] = []
    for grudge in state.social.grudges():
        # This route's filter is deliberately wider on the target side than
        # hydration's/avoidance's: `PLAYER_ID` is an accepted `target_id`
        # here and nowhere else. VendorMarkupCache.cpp keeps only
        # target_id == "the_player" rows, so a named-cast-on-both-sides
        # filter would leave the game side permanently unservable -- every
        # pair it can act on would be dropped here first. The holder must
        # still be named-cast: it is the vendor whose in-game actor
        # reference the price write has to resolve.
        if grudge.holder_id not in NAMED_CAST_NPC_IDS:
            continue
        if grudge.target_id not in NAMED_CAST_NPC_IDS and grudge.target_id != PLAYER_ID:
            continue
        multiplier = markup_multiplier_for(grudge, at_gamets=at_gamets)
        key = (grudge.holder_id, grudge.target_id)
        entry = pair_states.get(key)

        # Same "stale awaiting_ack entry forces a re-offer" doctrine as
        # _hydration_pairs/_avoidance_pairs -- a silently dropped ack
        # (PostVendorMarkupAck, fire-and-forget like every other outbound
        # call in ChronicleBridge) must not leave a pair stuck forever at
        # the same multiplier.
        expired = (
            entry is not None
            and entry.status == "awaiting_ack"
            and entry.awaiting_since is not None
            and time.monotonic() - entry.awaiting_since > _AWAITING_ACK_TIMEOUT_SECONDS
        )

        # A pair absent from the state machine defaults to a settled
        # multiplier of MARKUP_NO_MARKUP (1.0) -- the game's own default,
        # no-discount price -- not "unknown", so a pair that has always
        # computed to 1.0 is never reported as a spurious "changed to
        # 1.0" push on its very first poll. Same "no change to offer" vs.
        # "explicitly reset to 1.0" distinction RANK_NO_GRUDGE gets in
        # _hydration_pairs: a grudge that cools back down to 1.0 from a
        # nonzero markup IS a real change (entry.multiplier was != 1.0,
        # so the comparison below fires and the pair is re-offered at
        # 1.0) -- it is only the never-tracked-at-all case that is
        # silently treated as already-1.0.
        last_multiplier = entry.multiplier if entry is not None else MARKUP_NO_MARKUP
        if not expired and multiplier == last_multiplier:
            continue
        pair_states[key] = _VendorMarkupPairState(multiplier=multiplier, status="awaiting_ack", awaiting_since=time.monotonic())
        changed.append({"holder_id": grudge.holder_id, "target_id": grudge.target_id, "markup_multiplier": multiplier})
    return changed


def _apply_vendor_markup_ack(
    pair_states: dict[tuple[str, str], _VendorMarkupPairState], holder_id: str, target_id: str, outcome: str
) -> None:
    """Advance one pair's state machine entry per an ack's outcome.

    Silently ignores an ack for a pair with no current entry -- same
    reasoning as `_apply_hydration_ack`/`_apply_avoidance_ack`: nothing to
    update, and a stale/racing ack must never crash this endpoint.
    """
    entry = pair_states.get((holder_id, target_id))
    if entry is None:
        return
    if outcome == "applied":
        pair_states[(holder_id, target_id)] = _VendorMarkupPairState(multiplier=entry.multiplier, status="applied")
    elif outcome == "retry":
        del pair_states[(holder_id, target_id)]


@dataclasses.dataclass
class _EvidenceEntryState:
    """One entry in the per-(holder_id, belief_id) diegetic-evidence state
    machine -- the same protocol shape as `_HydrationPairState`'s/
    `_AvoidancePairState`'s/`_VendorMarkupPairState`'s, applied to a
    single-key fact (one NPC's one belief, not a pair) with no tracked
    value: unlike the other three, whose entries carry a rank/avoiding/
    multiplier VALUE to compare a freshly computed one against, evidence
    is a one-shot reveal with no re-offer on decay (design doc §2/§3) --
    there is nothing to compare a later poll's computed boolean against,
    only whether this entry has ALREADY been offered or applied. A
    `should_reveal_evidence() is False` poll therefore never touches this
    state machine at all (see `_evidence_entries`): the absence of a value
    field here is deliberate, not an oversight -- adding one back would
    invite exactly the bug this shape avoids, re-deriving a "revealed"
    boolean to diff against and accidentally re-offering (or worse,
    forgetting) an already-`applied` entry once confidence later drops
    back below threshold.

        (absent from the dict)  -- "not-yet-offered": baseline. Every
                                    entry starts here, and a `retry` ack
                                    (or a listener restart) sends it back
                                    here.
        status="awaiting_ack"   -- offered in a GET response, no ack
                                    received yet. A poll while awaiting-ack
                                    is a no-op.
        status="applied"        -- the C++ poller confirmed the spawn was
                                    attempted. TERMINAL -- unlike every
                                    other state machine in this file, there
                                    is no condition under which an
                                    "applied" entry is ever re-offered
                                    again, not even if the belief's
                                    confidence later decays below threshold
                                    and rises back above it (design doc
                                    §3's own named, deliberate limitation:
                                    "one object per belief, ever").

    No third status, same reasoning `_AvoidancePairState`'s/
    `_VendorMarkupPairState`'s docstrings give for their own two-outcome
    shape: a `PlaceObjectAtMe` call has no `no_relationship`-equivalent
    permanent-failure case (design doc §2's own F1/F2 citation) -- it
    depends only on whether the NPC is named-cast (already filtered) and
    whether a live game/actor reference is available (`retry`, temporary).

    `awaiting_since` closes the identical dropped-ack gap
    `_HydrationPairState`/`_AvoidancePairState`/`_VendorMarkupPairState`
    document: an "awaiting_ack" entry older than
    `_AWAITING_ACK_TIMEOUT_SECONDS` is treated as expired and re-offered on
    the next poll.
    """

    status: str  # "awaiting_ack" | "applied"
    awaiting_since: float | None = None  # time.monotonic() when status became "awaiting_ack"; None otherwise.


_EVIDENCE_ACK_OUTCOMES = frozenset({"applied", "retry"})


def _evidence_entries(live_run: str, entry_states: dict[tuple[str, str], _EvidenceEntryState]) -> list[dict[str, object]]:
    """Compute newly-revealable (holder_id, belief_id, claim_id) entries for
    the live run's named-cast NPCs' beliefs.

    Loops `NAMED_CAST_NPC_IDS` and calls `ClaimStore.beliefs_of(holder_id)`
    per NPC (at most 19 calls, design doc §2's own bound) rather than
    adding a store-wide `beliefs()` enumerator `ClaimStore` doesn't have
    and nothing else needs yet -- deliberately not the `for grudge in
    state.social.grudges()` scan-and-filter the other three slices use,
    since there is no equivalent store-wide enumerator here to scan.

    Unlike `_hydration_pairs`/`_avoidance_pairs`/`_vendor_markup_pairs`,
    there is no "computed value differs from tracked value" comparison --
    evidence has no tracked value (see `_EvidenceEntryState`'s docstring).
    An entry already `applied` is a permanent no-op regardless of what
    `should_reveal_evidence` computes on this or any future poll; an entry
    that has never been offered (or whose `awaiting_ack` has expired) is
    offered if-and-only-if `should_reveal_evidence` is currently True.
    `should_reveal_evidence() is False` for an entry with no current
    tracked state is simply skipped -- there is nothing to revert to
    "not revealed," since it was never offered in the first place.
    """
    reader = FrameLogReader(default_runs_dir() / live_run)
    max_tick = _max_tick(reader)
    if max_tick is None:
        return []
    state = reader.state_at(max_tick)
    at_gamets = float(max_tick)

    changed: list[dict[str, object]] = []
    for holder_id in NAMED_CAST_NPC_IDS:
        for belief in state.claims.beliefs_of(holder_id):
            key = (holder_id, belief.id)
            entry = entry_states.get(key)

            if entry is not None and entry.status == "applied":
                continue  # terminal -- never re-offered, per design doc §3.

            expired = (
                entry is not None
                and entry.status == "awaiting_ack"
                and entry.awaiting_since is not None
                and time.monotonic() - entry.awaiting_since > _AWAITING_ACK_TIMEOUT_SECONDS
            )
            if entry is not None and not expired:
                continue  # already offered, awaiting_ack, not yet expired -- no-op.

            if not should_reveal_evidence(belief, at_gamets=at_gamets):
                continue  # not (yet) well-evidenced enough -- nothing to offer.

            entry_states[key] = _EvidenceEntryState(status="awaiting_ack", awaiting_since=time.monotonic())
            changed.append({"holder_id": holder_id, "belief_id": belief.id, "claim_id": belief.claim_id})
    return changed


def _apply_evidence_ack(entry_states: dict[tuple[str, str], _EvidenceEntryState], holder_id: str, belief_id: str, outcome: str) -> None:
    """Advance one entry's state machine per an ack's outcome.

    Silently ignores an ack for an entry with no current state -- same
    reasoning as `_apply_hydration_ack`/`_apply_avoidance_ack`/
    `_apply_vendor_markup_ack`: nothing to update, and a stale/racing ack
    must never crash this endpoint.
    """
    entry = entry_states.get((holder_id, belief_id))
    if entry is None:
        return
    if outcome == "applied":
        entry_states[(holder_id, belief_id)] = _EvidenceEntryState(status="applied")
    elif outcome == "retry":
        del entry_states[(holder_id, belief_id)]


# --- Save/reload sync handshake (docs/design/chronicle-bridge-sync-handshake-out.md) ---

# save_uuid arrives as attacker/game-controlled JSON and is used as a
# sync-state filename component -- reject anything outside a safe
# filesystem charset before it ever reaches a path, rather than trying to
# escape/sanitize it. The co-save's own save_uuid is 32 lowercase hex
# chars (spec §3); existing chronicle runs use human-readable ids like
# "save-listener-1" (spec §8b item 4) -- both fit this charset.
_SYNC_SAVE_UUID_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")

# spec §8b item 1: the confirm_required "large jump" threshold. Both legs
# are named constants specifically so they're easy to tune later against
# real play data, per the spec's own framing -- the *shape* of the rule
# (an OR of a gamets leg and a seq leg) is decided, these two numbers are
# not. gamets is in game-hours (ADR-0010: 1 tick = 1 gamets = 1
# game-hour, chronicle/cli.py), so the gamets leg is compared directly
# against branch_state.head_gamets - manifest.gamets with no unit
# conversion.
_CONFIRM_REQUIRED_GAMETS_HOURS = 24.0
_CONFIRM_REQUIRED_SEQ_DELTA = 50

# Where the durable per-save_uuid sync sidecar lives by default -- a
# sibling of this listener script, following the same "listener-owned
# artifact lives next to listener.py, not under chronicle/runs/"
# convention --snapshot-path's own default already establishes (this
# directory is deliberately not part of chronicle/, see module docstring).
_DEFAULT_SYNC_STATE_DIR = Path(__file__).parent / "sync-state"

# Guards both the durable sidecar (read-modify-write) and the in-memory
# mutation_event_log for the sync routes -- one lock, not a per-save_uuid
# lock table, the same "one lock is enough for v1" simplification
# _write_lock already makes for /whiterun/positions.
_sync_lock = threading.Lock()


@dataclasses.dataclass
class _SyncSessionState:
    """Durable per-save_uuid sync session state (spec §4.3).

    Unlike every other per-slice state in this file (`_HydrationPairState`
    and its siblings, all safe to lose on restart because their state is
    recomputable from a run's frame log), this MUST survive a listener
    restart: branch/epoch/commit state is not recomputable from anything
    else the listener reads, so losing it silently resets head_seq to 0
    while the co-save manifest still says N, producing spurious
    ADOPT/amnesia on the very next HELLO -- timeline corruption, not a
    soft retry (spec §4.3). One JSON file per save_uuid under
    --sync-state-dir, written synchronously (atomic temp-file + rename,
    the same discipline `_handle_positions` already uses for the
    positions snapshot) on every change -- see `_save_sync_state`.

    `active_epoch`/`hello_seq` bump together, once per genuinely NEW load
    -- see `_process_hello`. `hello_seq` is tracked specifically so a
    RETRIED, identical HELLO (the same load, resent because its first
    response never arrived -- a real possibility given ChronicleBridge's
    fire-and-forget-by-default HTTP client, spec §2) is recognized and
    does NOT mint a second epoch for what is, from the game's own
    perspective, still the same load: `chronicle.sync`'s own caller-
    discipline comment describes "a new epoch per load/new-game", and
    hello_seq (incremented on every kPostLoadGame, spec §4.2) is exactly
    that granularity.

    `generation`/`head_seq`/`head_gamets` are the v1 single-generation
    `BranchState` simplification the spec's §4.1 names explicitly: since
    FORK/ADOPT aren't actionable yet (no fork-on-disk support exists),
    this service never creates a second generation, so there is only ever
    one generation to track per save_uuid. `generation is None` means "no
    branch known yet for this save_uuid" -- `BranchState(known=False)`,
    the NEW_TIMELINE/LEGACY_IMPORT territory.
    """

    active_epoch: int
    hello_seq: int
    generation: int | None
    head_seq: int
    head_gamets: float


def _sync_state_path(sync_state_dir: Path, save_uuid: str) -> Path:
    return sync_state_dir / f"{save_uuid}.json"


def _load_sync_state(sync_state_dir: Path, save_uuid: str) -> _SyncSessionState | None:
    """None means this save_uuid has never had a durable sidecar entry written -- the caller
    treats that the same way chronicle.sync.BranchState(known=False) does."""
    path = _sync_state_path(sync_state_dir, save_uuid)
    if not path.exists():
        return None
    return _SyncSessionState(**json.loads(path.read_text()))


def _save_sync_state(sync_state_dir: Path, save_uuid: str, state: _SyncSessionState) -> None:
    """Synchronous atomic write (temp file + rename) -- spec §4.3 requires every state change
    that must survive a restart to be durable before the caller replies to the shim."""
    sync_state_dir.mkdir(parents=True, exist_ok=True)
    path = _sync_state_path(sync_state_dir, save_uuid)
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(dataclasses.asdict(state)))
    tmp_path.replace(path)


def _manifest_from_hello_body(body: dict) -> Manifest:
    """The HTTP-boundary conversions spec §3/§4.1 require, done here, once: `parent_generation`'s
    `0` co-save sentinel -> Python `None` (chronicle.sync.Manifest treats `None` as the meaningful
    "no ancestor" value, not `0`), and `wall_ts`'s Unix milliseconds (the co-save's `int64_t`) ->
    Unix seconds (chronicle.events.Event.wall_ts's float unit). Split out from `_process_hello` so
    it can be exercised directly by the golden-fixture round-trip test (spec §3) without a live
    HTTP round trip.
    """
    parent_generation_raw = int(body["parent_generation"])
    return Manifest(
        format_version=int(body["format_version"]),
        save_uuid=body["save_uuid"],
        generation=int(body["generation"]),
        parent_generation=None if parent_generation_raw == 0 else parent_generation_raw,
        head_seq=int(body["head_seq"]),
        gamets=float(body["gamets"]),
        wall_ts=float(body["wall_ts"]) / 1000.0,
    )


def _process_hello(sync_state_dir: Path, body: dict) -> dict[str, object]:
    """The core of POST /whiterun/sync/hello (spec §4.1/§4.2/§4.3/§4.6), split out from the HTTP
    handler for testability. Caller holds `_sync_lock` and has already validated `body`'s shape.

    Loads (or initializes) this save_uuid's durable session state, builds the v1 single-generation
    `chronicle.sync.BranchState` (spec §4.1) from it, calls `chronicle.sync.resolve()` (or
    `legacy_import_resolution()` directly when `manifest_present` is False, matching resolve()'s
    own docstring: a missing manifest is decided by the caller before resolve() is ever invoked),
    computes `actionable`/`confirm_required`, persists any session-state change durably, and
    returns the JSON-serializable response body (spec §4.1's exact shape, `hello_seq` echoed).
    """
    save_uuid = body["save_uuid"]
    hello_seq = int(body["hello_seq"])
    manifest_present = bool(body["manifest_present"])

    state = _load_sync_state(sync_state_dir, save_uuid)

    # hello_seq lives in SyncHandshake's in-memory C++ state (spec §5),
    # NOT in the co-save manifest (§3's field table has seven fields, none
    # of them hello_seq) -- so it resets to 1 whenever the GAME PROCESS
    # restarts, even though this service's own durable sidecar does not.
    # A monotonicity check (hello_seq > state.hello_seq) would treat that
    # entirely legitimate reset as "stale" and wedge the session with no
    # self-correction path (every subsequent hello would keep losing to a
    # stored value that can never come back down). Equality is therefore
    # the ONLY signal this service can safely use for "same load, retried
    # response" (spec §4.2/§2) -- anything else, lower or higher, is
    # treated as a new load and bumps the epoch. A spuriously-bumped epoch
    # self-heals via the shim's own 409-threshold-triggers-re-HELLO loop
    # (spec §4.1's "Shim-side 409 handling"); a wedged session would not.
    is_new_load = state is None or hello_seq != state.hello_seq

    confirm_required = False
    if not manifest_present:
        # No manifest to interpret at all -- resolve() is never called
        # (its own docstring: this is decided by the caller beforehand).
        resolution = legacy_import_resolution(save_uuid_hint=save_uuid)
    else:
        manifest = _manifest_from_hello_body(body)
        if state is None or state.generation is None:
            branch_state = BranchState(known=False)
        else:
            branch_state = BranchState(
                known=True,
                head_generation=state.generation,
                head_seq=state.head_seq,
                head_gamets=state.head_gamets,
                known_generations=frozenset({state.generation}),
            )
        resolution = resolve(manifest, branch_state)
        # confirm_required (spec §4.6/§8b item 1) is a pure threshold on
        # the service's tracked branch head vs. the manifest -- computed
        # whenever there IS a known branch to compare against, not just on
        # FORK specifically (§8b item 1 states it with no decision
        # predicate; scoping it to FORK-only would silently drop the audit
        # record §4.6 wants for e.g. ADOPT's own head_seq-ahead row).
        if branch_state.known:
            confirm_required = (
                branch_state.head_gamets - manifest.gamets > _CONFIRM_REQUIRED_GAMETS_HOURS
                or branch_state.head_seq - manifest.head_seq > _CONFIRM_REQUIRED_SEQ_DELTA
            )

    new_epoch = (0 if state is None else state.active_epoch + 1) if is_new_load else state.active_epoch

    # Default: leave the tracked branch exactly as it was (or "unknown" if
    # there was never one) -- CONTINUE needs no change (resolve()'s own
    # precondition means the service's tracked head_seq/head_gamets are
    # already >= the manifest's), and FORK/ADOPT/LEGACY_IMPORT must never
    # silently adopt unverified history this service can't act on yet
    # (spec §4).
    new_generation = state.generation if state is not None else None
    new_head_seq = state.head_seq if state is not None else 0
    new_head_gamets = state.head_gamets if state is not None else 0.0
    if manifest_present and resolution.decision is ResolveDecision.NEW_TIMELINE:
        # A genuinely new (or amnesia'd-back-to-new) branch: start tracking
        # it at the manifest's own gamets (a legitimate clock reading, not
        # unverified committed history) but head_seq=0 -- nothing has
        # actually been committed via EventLog.append() yet for this
        # now-known branch (spec §4.4: head_seq means exactly what the
        # service has durably appended, never an un-ACKed claim).
        new_generation = resolution.branch_generation
        new_head_seq = 0
        new_head_gamets = manifest.gamets

    _save_sync_state(
        sync_state_dir,
        save_uuid,
        _SyncSessionState(
            active_epoch=new_epoch,
            hello_seq=hello_seq,
            generation=new_generation,
            head_seq=new_head_seq,
            head_gamets=new_head_gamets,
        ),
    )

    actionable = resolution.decision in (ResolveDecision.CONTINUE, ResolveDecision.NEW_TIMELINE, ResolveDecision.DEGRADED)
    return {
        "decision": resolution.decision.value,
        "actionable": actionable,
        "epoch_id": new_epoch,
        "replay_from_seq": resolution.replay_from_seq,
        "confirm_required": confirm_required,
        "hello_seq": hello_seq,  # echoes the request's own value (spec §4.1/§4.2).
    }


def _process_mutation(sync_state_dir: Path, event_log: EventLog, body: dict) -> tuple[int, str | None]:
    """The core of POST /whiterun/sync/mutation (spec §4.1/§4.4), split out from the HTTP handler
    for testability. Caller holds `_sync_lock` and has already validated `body`'s shape. Returns
    (http_status, error_message_or_None) -- the caller logs the message (if any) and replies with
    the status, never a 500 for a stale epoch (spec §4.4: 409).

    Epoch-fencing via `chronicle.sync.mutation_admissible()`. On acceptance: `EventLog.append()`
    is the commit point (spec §4.4) -- it happens synchronously here, and the durable session
    state's `head_seq`/`head_gamets` only advance, durably, AFTER a successful append, all before
    this function returns and the caller replies 2xx. There is no gap in which a mutation can be
    "ACKed but not really there."
    """
    save_uuid = body["save_uuid"]
    generation = int(body["generation"])
    seq = int(body["seq"])
    epoch_id = int(body["epoch_id"])
    event_json = body["event"]
    if not isinstance(event_json, dict):
        return 400, "event must be a JSON object"

    state = _load_sync_state(sync_state_dir, save_uuid)
    if state is None:
        # No session for this save_uuid at all -- no HELLO ever
        # established an epoch, so no epoch_id the shim could carry here
        # was ever legitimately issued. Treat exactly like a stale epoch.
        return 409, f"no active sync session for save_uuid {save_uuid!r} -- mutation before hello"
    if not mutation_admissible(epoch_id, state.active_epoch):
        return 409, f"stale epoch: mutation epoch {epoch_id} not admissible against current epoch {state.active_epoch}"

    # tick/gamets/wall_ts defaulting mirrors chronicle/cli.py's own
    # _inject_write discipline exactly (ADR-0010: 1 tick = 1 gamets = 1
    # game-hour; wall_ts, transaction time, defaults to now if the caller
    # doesn't supply one) -- not re-derived independently here.
    if "tick" not in event_json and "gamets" not in event_json:
        return 400, "event must carry a tick or gamets (1 tick = 1 gamets = 1 game-hour, ADR-0010)"
    tick = int(event_json["tick"]) if "tick" in event_json else int(event_json["gamets"])
    gamets = float(event_json["gamets"]) if "gamets" in event_json else float(tick)
    wall_ts = float(event_json.get("wall_ts", time.time()))
    payload = {**event_json, "gamets": gamets, "wall_ts": wall_ts}
    record = {"tick": tick, "save_uuid": save_uuid, "generation": generation, "seq": seq, "payload": payload}
    try:
        # chronicle.framelog.event_from_record() is the existing "rebuild
        # the typed Event from a JSON payload" dispatcher -- reused here
        # rather than re-implementing per-event-type construction.
        event = event_from_record(record)
    except (KeyError, TypeError) as exc:
        return 400, f"malformed event: {exc}"

    # EventLog.append()'s own (save_uuid, generation, seq) dedup is the
    # only dedup mechanism here (chronicle/events.py:206) -- a replayed
    # mutation is a safe no-op, its head_seq/head_gamets already reflect
    # the first, successful append.
    if event_log.append(event):
        _save_sync_state(
            sync_state_dir,
            save_uuid,
            dataclasses.replace(state, head_seq=max(state.head_seq, seq), head_gamets=max(state.head_gamets, gamets)),
        )
    return 204, None


def _make_handler(snapshot_path: Path, shared_secret: str | None, live_run: str | None, sync_state_dir: Path | None = None) -> type[BaseHTTPRequestHandler]:
    # Per-pair hydration state machine (design doc §3b + the ack protocol
    # that closes fad0d79's "delivered before confirmed" gap) -- see
    # _HydrationPairState's docstring for the full state machine. In-memory
    # only, scoped to this one handler-class closure -- it does NOT persist
    # across listener restarts. That is a real, named gap (design doc §3's
    # "Idempotency/staleness" open question): a restarted listener
    # re-announces every currently-nonzero rank (a missing entry defaults to
    # comparing against rank 0, see _hydration_pairs) on its first poll
    # after restart, since it has no memory of what the C++ poller
    # previously received or acked. Not solved here -- and, per the ack
    # protocol's own design, a listener restart is handled identically to a
    # `retry` ack (both just forget the pair), so this is not a new gap.
    hydration_pair_states: dict[tuple[str, str], _HydrationPairState] = {}

    # Per-(npc_a, npc_b) avoidance state machine (design doc
    # chronicle-bridge-avoidance-out.md), same closure-scoped,
    # in-memory-only, does-not-survive-a-restart shape as
    # hydration_pair_states above -- see _AvoidancePairState's docstring.
    avoidance_pair_states: dict[tuple[str, str], _AvoidancePairState] = {}

    # Per-(holder_id, target_id) vendor-markup state machine (design doc
    # chronicle-bridge-vendor-markup-out.md), same closure-scoped,
    # in-memory-only, does-not-survive-a-restart shape as
    # hydration_pair_states/avoidance_pair_states above -- see
    # _VendorMarkupPairState's docstring.
    vendor_markup_pair_states: dict[tuple[str, str], _VendorMarkupPairState] = {}

    # Per-(holder_id, belief_id) diegetic-evidence state machine (design
    # doc chronicle-bridge-diegetic-evidence-out.md), same closure-scoped,
    # in-memory-only, does-not-survive-a-restart shape as the three state
    # dicts above -- see _EvidenceEntryState's docstring.
    evidence_entry_states: dict[tuple[str, str], _EvidenceEntryState] = {}

    # Where the sync handshake's durable per-save_uuid sidecar lives
    # (_SyncSessionState's docstring) -- unlike every dict above, this
    # state is NOT closure-scoped/in-memory-only; it's read from and
    # written back to disk on every hello/mutation.
    resolved_sync_state_dir = sync_state_dir if sync_state_dir is not None else _DEFAULT_SYNC_STATE_DIR

    # The mutation endpoint's own EventLog, used only for its
    # (save_uuid, generation, seq) append() dedup (chronicle/events.py:206)
    # -- deliberately in-memory-only/closure-scoped like the pair-state
    # dicts above, NOT part of the sync durability story (module docstring
    # explains why: only the session bookkeeping needs to survive a
    # restart in this v1, not the mutation events' own content).
    mutation_event_log: EventLog = EventLog()

    class Handler(BaseHTTPRequestHandler):
        def _check_auth(self) -> bool:
            if shared_secret is None:
                return True
            token = self.headers.get("X-Chronicle-Bridge-Token")
            if token is None or not secrets.compare_digest(token, shared_secret):
                self.send_response(401)
                self.end_headers()
                return False
            return True

        def _read_body(self) -> bytes | None:
            """None means a response was already sent (bad/oversized length)."""
            try:
                length = int(self.headers.get("Content-Length", 0))
            except ValueError:
                self.send_response(400)
                self.end_headers()
                return None
            if length <= 0 or length > _MAX_BODY_BYTES:
                self.send_response(413)
                self.end_headers()
                return None
            return self.rfile.read(length)

        def do_POST(self) -> None:
            if self.path == "/whiterun/positions":
                self._handle_positions()
            elif self.path == "/whiterun/events":
                self._handle_events()
            elif self.path == "/whiterun/hydration/ack":
                self._handle_hydration_ack()
            elif self.path == "/whiterun/avoidance/ack":
                self._handle_avoidance_ack()
            elif self.path == "/whiterun/vendor-markup/ack":
                self._handle_vendor_markup_ack()
            elif self.path == "/whiterun/evidence/ack":
                self._handle_evidence_ack()
            elif self.path == "/whiterun/sync/hello":
                self._handle_sync_hello()
            elif self.path == "/whiterun/sync/mutation":
                self._handle_sync_mutation()
            else:
                self.send_response(404)
                self.end_headers()

        def _handle_positions(self) -> None:
            if not self._check_auth():
                return
            raw = self._read_body()
            if raw is None:
                return

            try:
                snapshot = PositionSnapshot.model_validate_json(raw)
            except ValidationError as exc:
                print(f"rejected malformed snapshot: {exc}", file=sys.stderr)
                self.send_response(400)
                self.end_headers()
                return

            # Atomic-ish write (temp file + rename) so the dashboard's poller
            # never reads a half-written file -- the same torn-record concern
            # docs/frame-log-schema.md's own reader discipline names, applied
            # here even though this file isn't part of the frame log itself.
            with _write_lock:
                tmp_path = snapshot_path.with_suffix(".tmp")
                tmp_path.write_text(json.dumps(snapshot.model_dump(), indent=None))
                tmp_path.replace(snapshot_path)

            self.send_response(204)
            self.end_headers()

        def _handle_events(self) -> None:
            if live_run is None:
                self.send_response(503)
                self.end_headers()
                return
            if not self._check_auth():
                return
            raw = self._read_body()
            if raw is None:
                return

            try:
                event = GameEvent.model_validate_json(raw)
            except ValidationError as exc:
                print(f"rejected malformed event: {exc}", file=sys.stderr)
                self.send_response(400)
                self.end_headers()
                return

            # GameEvent is one flat schema across event kinds (JSON Schema
            # can't express per-variant `required` on it -- contract's own
            # note); this is where per-kind shape is actually enforced
            # (docs/design/chronicle-bridge-crime-witness-out.md §4).
            if event.event_type is EventType.crime_witnessed:
                if event.witness_id is None or event.perpetrator_id is None or event.crime_type is None:
                    print("rejected malformed event: crime_witnessed missing witness_id/perpetrator_id/crime_type", file=sys.stderr)
                    self.send_response(400)
                    self.end_headers()
                    return
                ok, message = _inject_crime_witnessed_event(event, live_run=live_run)
            else:
                if event.npc_id is None:
                    print("rejected malformed event: npc_died missing npc_id", file=sys.stderr)
                    self.send_response(400)
                    self.end_headers()
                    return
                ok, message = _inject_death_event(event, live_run=live_run)
            if not ok:
                print(f"chronicle inject rejected event: {message}", file=sys.stderr)
                self.send_response(400)
                self.end_headers()
                return

            print(f"[listener] {message}", file=sys.stderr)
            self.send_response(204)
            self.end_headers()

        def do_GET(self) -> None:
            if self.path == "/whiterun/hydration":
                self._handle_hydration()
            elif self.path == "/whiterun/avoidance":
                self._handle_avoidance()
            elif self.path == "/whiterun/vendor-markup":
                self._handle_vendor_markup()
            elif self.path == "/whiterun/evidence":
                self._handle_evidence()
            else:
                self.send_response(404)
                self.end_headers()

        def _handle_hydration(self) -> None:
            # Same gating convention as /whiterun/events: 503 if no
            # --live-run was given at startup, never a default/auto-selected
            # run (design doc §3b).
            if live_run is None:
                self.send_response(503)
                self.end_headers()
                return
            if not self._check_auth():
                return

            pairs = _hydration_pairs(live_run, hydration_pair_states)
            body = json.dumps(pairs).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _handle_hydration_ack(self) -> None:
            """POST /whiterun/hydration/ack -- the C++ poller reports what
            actually happened to each pair GET /whiterun/hydration served it,
            closing fad0d79's "delivered before confirmed" gap. Gated
            identically to GET /whiterun/hydration (503 without --live-run,
            same auth check).

            Body: a JSON array of {"holder_id": str, "target_id": str,
            "outcome": "applied" | "no_relationship" | "retry"} objects. Not
            part of the OpenAPI contract or validated via a pydantic model --
            same ad hoc hand-rolled-JSON precedent as the GET response this
            acks (see this file's module docstring on that read-only
            exception). Any malformed body is rejected wholesale with a 400,
            matching /whiterun/events' and /whiterun/positions' own
            reject-the-whole-request-on-bad-input style -- there is no
            partial application of a batch with one bad entry.
            """
            if live_run is None:
                self.send_response(503)
                self.end_headers()
                return
            if not self._check_auth():
                return
            raw = self._read_body()
            if raw is None:
                return

            try:
                payload = json.loads(raw)
                if not isinstance(payload, list):
                    raise TypeError("expected a JSON array")
                parsed: list[tuple[str, str, str]] = []
                for item in payload:
                    if not isinstance(item, dict):
                        raise TypeError("expected an array of objects")
                    holder_id = item["holder_id"]
                    target_id = item["target_id"]
                    outcome = item["outcome"]
                    if not isinstance(holder_id, str) or not isinstance(target_id, str):
                        raise TypeError("holder_id/target_id must be strings")
                    if outcome not in _ACK_OUTCOMES:
                        raise ValueError(f"unknown outcome: {outcome!r}")
                    parsed.append((holder_id, target_id, outcome))
            except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                print(f"rejected malformed hydration ack: {exc}", file=sys.stderr)
                self.send_response(400)
                self.end_headers()
                return

            for holder_id, target_id, outcome in parsed:
                _apply_hydration_ack(hydration_pair_states, holder_id, target_id, outcome)

            self.send_response(204)
            self.end_headers()

        def _handle_avoidance(self) -> None:
            """GET /whiterun/avoidance -- same gating as /whiterun/hydration
            (503 without --live-run, same auth), symmetric response shape
            (docs/design/chronicle-bridge-avoidance-out.md)."""
            if live_run is None:
                self.send_response(503)
                self.end_headers()
                return
            if not self._check_auth():
                return

            pairs = _avoidance_pairs(live_run, avoidance_pair_states)
            body = json.dumps(pairs).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _handle_avoidance_ack(self) -> None:
            """POST /whiterun/avoidance/ack -- the same ack protocol as
            /whiterun/hydration/ack, applied to a symmetric pair and a
            two-outcome ("applied" | "retry") shape (see module docstring
            for why avoidance has no third, permanent-failure outcome).

            Body: a JSON array of {"npc_a": str, "npc_b": str, "outcome":
            "applied" | "retry"} objects -- npc_a/npc_b may be given in
            either order (canonicalized before lookup, see
            `_apply_avoidance_ack`). Not part of the OpenAPI contract, same
            hand-rolled-JSON precedent as every other ack/GET pair in this
            file. A malformed body is rejected wholesale with a 400, same
            reject-the-whole-batch style as /whiterun/hydration/ack.
            """
            if live_run is None:
                self.send_response(503)
                self.end_headers()
                return
            if not self._check_auth():
                return
            raw = self._read_body()
            if raw is None:
                return

            try:
                payload = json.loads(raw)
                if not isinstance(payload, list):
                    raise TypeError("expected a JSON array")
                parsed: list[tuple[str, str, str]] = []
                for item in payload:
                    if not isinstance(item, dict):
                        raise TypeError("expected an array of objects")
                    npc_a = item["npc_a"]
                    npc_b = item["npc_b"]
                    outcome = item["outcome"]
                    if not isinstance(npc_a, str) or not isinstance(npc_b, str):
                        raise TypeError("npc_a/npc_b must be strings")
                    if outcome not in _AVOIDANCE_ACK_OUTCOMES:
                        raise ValueError(f"unknown outcome: {outcome!r}")
                    parsed.append((npc_a, npc_b, outcome))
            except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                print(f"rejected malformed avoidance ack: {exc}", file=sys.stderr)
                self.send_response(400)
                self.end_headers()
                return

            for npc_a, npc_b, outcome in parsed:
                _apply_avoidance_ack(avoidance_pair_states, npc_a, npc_b, outcome)

            self.send_response(204)
            self.end_headers()

        def _handle_vendor_markup(self) -> None:
            """GET /whiterun/vendor-markup -- same gating as
            /whiterun/hydration (503 without --live-run, same auth),
            directed response shape (docs/design/chronicle-bridge-vendor-
            markup-out.md)."""
            if live_run is None:
                self.send_response(503)
                self.end_headers()
                return
            if not self._check_auth():
                return

            pairs = _vendor_markup_pairs(live_run, vendor_markup_pair_states)
            body = json.dumps(pairs).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _handle_vendor_markup_ack(self) -> None:
            """POST /whiterun/vendor-markup/ack -- the same ack protocol as
            /whiterun/hydration/ack and /whiterun/avoidance/ack, applied to
            a directed pair and a two-outcome ("applied" | "retry") shape
            (see module docstring for why vendor-markup has no third,
            permanent-failure outcome, unlike hydration).

            Body: a JSON array of {"holder_id": str, "target_id": str,
            "outcome": "applied" | "retry"} objects -- not part of the
            OpenAPI contract, same hand-rolled-JSON precedent as every
            other ack/GET pair in this file. A malformed body is rejected
            wholesale with a 400, same reject-the-whole-batch style as the
            other two ack endpoints.
            """
            if live_run is None:
                self.send_response(503)
                self.end_headers()
                return
            if not self._check_auth():
                return
            raw = self._read_body()
            if raw is None:
                return

            try:
                payload = json.loads(raw)
                if not isinstance(payload, list):
                    raise TypeError("expected a JSON array")
                parsed: list[tuple[str, str, str]] = []
                for item in payload:
                    if not isinstance(item, dict):
                        raise TypeError("expected an array of objects")
                    holder_id = item["holder_id"]
                    target_id = item["target_id"]
                    outcome = item["outcome"]
                    if not isinstance(holder_id, str) or not isinstance(target_id, str):
                        raise TypeError("holder_id/target_id must be strings")
                    if outcome not in _VENDOR_MARKUP_ACK_OUTCOMES:
                        raise ValueError(f"unknown outcome: {outcome!r}")
                    parsed.append((holder_id, target_id, outcome))
            except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                print(f"rejected malformed vendor-markup ack: {exc}", file=sys.stderr)
                self.send_response(400)
                self.end_headers()
                return

            for holder_id, target_id, outcome in parsed:
                _apply_vendor_markup_ack(vendor_markup_pair_states, holder_id, target_id, outcome)

            self.send_response(204)
            self.end_headers()

        def _handle_evidence(self) -> None:
            """GET /whiterun/evidence -- same gating as /whiterun/hydration
            (503 without --live-run, same auth), single-key response shape
            (docs/design/chronicle-bridge-diegetic-evidence-out.md)."""
            if live_run is None:
                self.send_response(503)
                self.end_headers()
                return
            if not self._check_auth():
                return

            entries = _evidence_entries(live_run, evidence_entry_states)
            body = json.dumps(entries).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _handle_evidence_ack(self) -> None:
            """POST /whiterun/evidence/ack -- the same ack protocol as the
            other three ack routes, applied to evidence's single-key shape
            and a two-outcome ("applied" | "retry") shape (see module
            docstring for why evidence has no third, permanent-failure
            outcome). `applied` is terminal here, unlike the other three's
            `applied` (see `_EvidenceEntryState`'s docstring).

            Body: a JSON array of {"holder_id": str, "belief_id": str,
            "outcome": "applied" | "retry"} objects -- not part of the
            OpenAPI contract, same hand-rolled-JSON precedent as every
            other ack/GET pair in this file. A malformed body is rejected
            wholesale with a 400, same reject-the-whole-batch style as the
            other three ack endpoints.
            """
            if live_run is None:
                self.send_response(503)
                self.end_headers()
                return
            if not self._check_auth():
                return
            raw = self._read_body()
            if raw is None:
                return

            try:
                payload = json.loads(raw)
                if not isinstance(payload, list):
                    raise TypeError("expected a JSON array")
                parsed: list[tuple[str, str, str]] = []
                for item in payload:
                    if not isinstance(item, dict):
                        raise TypeError("expected an array of objects")
                    holder_id = item["holder_id"]
                    belief_id = item["belief_id"]
                    outcome = item["outcome"]
                    if not isinstance(holder_id, str) or not isinstance(belief_id, str):
                        raise TypeError("holder_id/belief_id must be strings")
                    if outcome not in _EVIDENCE_ACK_OUTCOMES:
                        raise ValueError(f"unknown outcome: {outcome!r}")
                    parsed.append((holder_id, belief_id, outcome))
            except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                print(f"rejected malformed evidence ack: {exc}", file=sys.stderr)
                self.send_response(400)
                self.end_headers()
                return

            for holder_id, belief_id, outcome in parsed:
                _apply_evidence_ack(evidence_entry_states, holder_id, belief_id, outcome)

            self.send_response(204)
            self.end_headers()

        def _handle_sync_hello(self) -> None:
            """POST /whiterun/sync/hello (design doc §4.1/§4.2/§4.3/§4.6). Bearer-token auth
            only -- deliberately NOT gated behind --live-run (design doc §8b item 3: sync state is
            keyed by save_uuid, orthogonal to demo runs). Not part of the OpenAPI contract, same
            hand-rolled-JSON precedent as every ack/GET pair in this file (no pydantic model).

            Body: the manifest fields as JSON (format_version, save_uuid, generation,
            parent_generation, head_seq, gamets, wall_ts, char_name_hash -- char_name_hash is
            display/debug only, ignored here, same as chronicle.sync.Manifest's own omission of
            it) plus manifest_present: bool and hello_seq: uint64. Any malformed/missing field
            rejects the whole request with 400, same reject-the-whole-request style as every other
            POST route in this file -- see `_process_hello` for the actual RESOLVE call.
            """
            if not self._check_auth():
                return
            raw = self._read_body()
            if raw is None:
                return

            try:
                body = json.loads(raw)
                if not isinstance(body, dict):
                    raise TypeError("expected a JSON object")
                save_uuid = body.get("save_uuid")
                if not isinstance(save_uuid, str) or not _SYNC_SAVE_UUID_RE.match(save_uuid):
                    raise ValueError(f"invalid or missing save_uuid: {save_uuid!r}")
                int(body["hello_seq"])
                manifest_present = body["manifest_present"]
                if not isinstance(manifest_present, bool):
                    raise TypeError("manifest_present must be a bool")
                if manifest_present:
                    for field in ("format_version", "generation", "parent_generation", "head_seq", "gamets", "wall_ts"):
                        if field not in body:
                            raise KeyError(field)
            except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                print(f"rejected malformed sync hello: {exc}", file=sys.stderr)
                self.send_response(400)
                self.end_headers()
                return

            with _sync_lock:
                try:
                    response = _process_hello(resolved_sync_state_dir, body)
                except (ValueError, KeyError, TypeError) as exc:
                    print(f"rejected malformed sync hello: {exc}", file=sys.stderr)
                    self.send_response(400)
                    self.end_headers()
                    return

            body_bytes = json.dumps(response).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body_bytes)))
            self.end_headers()
            self.wfile.write(body_bytes)

        def _handle_sync_mutation(self) -> None:
            """POST /whiterun/sync/mutation (design doc §4.1/§4.4). Same auth/contract posture as
            /whiterun/sync/hello above. Body: {"epoch_id", "save_uuid", "generation", "seq",
            "event": {...}}. Epoch-fencing rejection is 409, not 500 (design doc §4.4) -- see
            `_process_mutation` for the commit-point ordering this exists to get right.
            """
            if not self._check_auth():
                return
            raw = self._read_body()
            if raw is None:
                return

            try:
                body = json.loads(raw)
                if not isinstance(body, dict):
                    raise TypeError("expected a JSON object")
                save_uuid = body.get("save_uuid")
                if not isinstance(save_uuid, str) or not _SYNC_SAVE_UUID_RE.match(save_uuid):
                    raise ValueError(f"invalid or missing save_uuid: {save_uuid!r}")
                for field in ("epoch_id", "generation", "seq", "event"):
                    if field not in body:
                        raise KeyError(field)
            except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                print(f"rejected malformed sync mutation: {exc}", file=sys.stderr)
                self.send_response(400)
                self.end_headers()
                return

            with _sync_lock:
                try:
                    status, message = _process_mutation(resolved_sync_state_dir, mutation_event_log, body)
                except (ValueError, KeyError, TypeError) as exc:
                    print(f"rejected malformed sync mutation: {exc}", file=sys.stderr)
                    self.send_response(400)
                    self.end_headers()
                    return

            if message is not None:
                print(f"sync mutation rejected ({status}): {message}", file=sys.stderr)
            self.send_response(status)
            self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            print(f"[listener] {self.address_string()} {format % args}", file=sys.stderr)

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--snapshot-path",
        type=Path,
        default=Path(__file__).parent / "whiterun-positions.json",
        help="Where the rolling snapshot file is written (the dashboard polls this path).",
    )
    parser.add_argument(
        "--shared-secret",
        type=str,
        default=None,
        help="Bearer token ChronicleBridge must send as X-Chronicle-Bridge-Token. "
        "Strongly recommended once this listens on a real LAN interface -- "
        "omitting it accepts POSTs from anyone who can reach the port.",
    )
    parser.add_argument(
        "--live-run",
        type=str,
        default=None,
        help="The run_id /whiterun/events appends detected deaths into, via "
        "'python -m chronicle inject'. No default and no auto-selection of an "
        "existing run -- omitting this makes /whiterun/events return 503. Never "
        "point this at a fixture/demo run the M7 release gate or the ladder's "
        "scenario tests depend on (e.g. runs/north-star-01); always a dedicated "
        "live-play run.",
    )
    parser.add_argument(
        "--sync-state-dir",
        type=Path,
        default=_DEFAULT_SYNC_STATE_DIR,
        help="Where the save/reload sync handshake's durable per-save_uuid session state lives "
        "(one JSON file per save_uuid, docs/design/chronicle-bridge-sync-handshake-out.md §4.3). "
        "NOT gated behind --live-run -- /whiterun/sync/hello and /whiterun/sync/mutation are "
        "always active (bearer-token auth only), since sync state is keyed by save_uuid, "
        "orthogonal to demo runs.",
    )
    args = parser.parse_args()

    if args.shared_secret is None:
        print(
            "[listener] WARNING: running with no --shared-secret -- anyone who can reach "
            "this port on the LAN can write to the snapshot file. Fine for a quick local "
            "test; set --shared-secret before leaving this running on a real network.",
            file=sys.stderr,
        )
    if args.live_run is None:
        print(
            "[listener] /whiterun/events disabled (no --live-run given) -- only "
            "/whiterun/positions is active.",
            file=sys.stderr,
        )

    server = ThreadingHTTPServer(
        ("0.0.0.0", args.port),
        _make_handler(args.snapshot_path, args.shared_secret, args.live_run, args.sync_state_dir),
    )
    print(f"ChronicleBridge listener on :{args.port}, writing {args.snapshot_path}", file=sys.stderr)
    server.serve_forever()


if __name__ == "__main__":
    main()
