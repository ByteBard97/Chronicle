"""The Python-side RESOLVE logic for the co-save sync handshake (docs/decisions/0005-sync-handshake.md).

ADR-0005 defines a HELLO/RESOLVE/ACK handshake between the SKSE shim and
this service: the shim reads a small co-save manifest on load and posts it
as HELLO (`SYNC_TIMELINE`); the service classifies it against what it
already knows about that `save_uuid` (RESOLVE) and replies ACK
(`TIMELINE_READY`) with a decision plus an epoch fencing token. This
module is the RESOLVE half only -- pure branch-key arithmetic against
`chronicle.events`'s existing `BranchKey`/`EventLog`/`lineage()` types, no
network, no filesystem, no wiring into `adapters/skyrim/`.

Kept deliberately narrow (docs/design/next-phases-2026-08.md §1): wiring
this into the listener, deciding where a manifest actually arrives from,
and everything on the C++ shim side (`g_isLoading`, co-save read/write,
the two load hooks) are explicitly out of scope for this lane -- they
need their own design-prep doc and/or the Windows build machine and a
live game, neither of which this module needs or touches.

Caller-supplies-context, same discipline as chronicle.propagate/rules:
resolve() takes an explicit BranchState snapshot rather than querying an
EventLog itself. A real caller assembles that snapshot from
EventLog.lineage() (or an equivalent branch-head index) -- that wiring is
future integration work, not this module's job.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class Manifest:
    """The co-save manifest record (ADR-0005's schema table).

    Field names are aligned to ADR-0004's (save_uuid, generation) branch
    key. `char_name_hash` is deliberately omitted here -- the ADR marks it
    "display/debug only, never a key," and RESOLVE never reads it; keeping
    it out of this module's core dataclass avoids the temptation to key
    anything off it later. gamets/wall_ts are mandatory, matching
    chronicle.events's bitemporal rule (never None).
    """

    format_version: int
    save_uuid: str
    generation: int
    parent_generation: int | None
    head_seq: int
    gamets: float
    wall_ts: float

    def __post_init__(self) -> None:
        if self.head_seq < 0:
            raise ValueError(f"head_seq must be >= 0, got {self.head_seq!r}")
        if self.generation < 0:
            raise ValueError(f"generation must be >= 0, got {self.generation!r}")
        if self.format_version < 0:
            raise ValueError(f"format_version must be >= 0, got {self.format_version!r}")


@dataclass(frozen=True)
class BranchState:
    """What the service already knows about a save_uuid at HELLO time.

    `known` is False when this save_uuid has never been seen before (the
    NEW TIMELINE / LEGACY IMPORT territory) -- in that case the other
    fields are meaningless and resolve() ignores them. When `known` is
    True, `head_generation`/`head_seq`/`head_gamets` describe the
    service's current branch head for that save_uuid, and
    `known_generations` lists every generation on record for it (so
    resolve() can tell "generation unknown" (ADOPT) apart from
    "generation known but behind" (FORK) without querying anything
    itself -- the caller assembles this from EventLog/lineage or an
    equivalent index).
    """

    known: bool
    head_generation: int = 0
    head_seq: int = 0
    head_gamets: float = 0.0
    known_generations: frozenset[int] = frozenset()

    def __post_init__(self) -> None:
        if self.known and self.head_generation not in self.known_generations:
            raise ValueError(
                "a known BranchState must list its own head_generation in known_generations "
                f"(head_generation={self.head_generation!r}, known_generations={sorted(self.known_generations)!r})"
            )


class ResolveDecision(Enum):
    """The six-way RESOLVE outcome (ADR-0005's decision table), verbatim."""

    CONTINUE = "CONTINUE"
    FORK = "FORK"
    ADOPT = "ADOPT"
    NEW_TIMELINE = "NEW_TIMELINE"
    LEGACY_IMPORT = "LEGACY_IMPORT"
    DEGRADED = "DEGRADED"


@dataclass(frozen=True)
class Resolution:
    """The outcome of a RESOLVE call: a decision plus whatever the caller needs to act on it.

    `branch_generation` means a DIFFERENT thing depending on `decision` --
    read `decision` before using it:

      - CONTINUE: the branch to keep tagging outbound events with (no new
        generation is created).
      - NEW_TIMELINE / LEGACY_IMPORT: the newly-opened branch's generation
        (always 0 -- see resolve()'s NEW_TIMELINE comment).
      - ADOPT (generation-unknown case): the new branch's own identity --
        `manifest.generation` IS the adopted generation, nothing to
        allocate.
      - FORK, and ADOPT's head_seq-ahead case: the branch being forked
        FROM, i.e. the SOURCE, not the destination. The actual child
        generation doesn't exist until the caller calls
        `EventLog.fork(save_uuid, from_generation=branch_generation,
        ...)` and gets one back -- resolve() cannot name it in advance.
        A caller that blindly tags new events with `branch_generation` on
        a FORK/head_seq-ahead-ADOPT result writes into the abandoned
        parent, exactly the wrong-branch bug this module exists to
        prevent -- always branch on `decision` first.

    `fork_parent_generation`/`fork_at_gamets` are populated for FORK/ADOPT
    (what EventLog.fork() would need); both None for the other decisions.
    `replay_from_seq` is populated for CONTINUE when the branch head is
    ahead of the manifest's head_seq (an un-ACKed gap to replay), else
    None.
    """

    decision: ResolveDecision
    branch_generation: int
    fork_parent_generation: int | None = None
    fork_at_gamets: float | None = None
    replay_from_seq: int | None = None
    save_uuid_hint: str | None = None


# The newest manifest `format_version` this build understands. A manifest
# stamped with a higher version was written by a newer shim than this
# build knows about (scenarios/sync/04) -- per the ADR's tolerant-read
# rule, unknown fields/layouts must never be misread, so resolve() refuses
# to interpret ANY field on such a manifest and routes to LEGACY_IMPORT
# instead, the same conservative fallback the ADR names for this case.
SUPPORTED_FORMAT_VERSION = 1


def resolve(manifest: Manifest, branch_state: BranchState) -> Resolution:
    """Classify a HELLO manifest against the service's branch state (ADR-0005's six-way table).

    Pure function: no I/O, no EventLog access. The rows this function can
    actually produce from a manifest (DEGRADED is the exception -- see
    below):

      - format_version newer than this build knows  -> LEGACY_IMPORT
      - unknown save_uuid                            -> NEW_TIMELINE
      - known save_uuid, unknown generation           -> ADOPT
      - known save_uuid+generation, gamets older
        than the branch head                         -> FORK
      - known save_uuid+generation, head_seq is AHEAD
        of what the service has ACKed (service lost
        track of committed state, e.g. restored from
        an older backup)                             -> ADOPT
      - known save_uuid+generation, head_seq >= and
        gamets equal/newer than the branch head       -> CONTINUE

    The fifth row isn't a named cell in the ADR's table -- none of
    CONTINUE/FORK's stated conditions match "gamets current but head_seq
    claims more than the service ever ACKed" -- but scenario 02's
    assertion (3), "the resolution path taken is the conservative one,
    never a silent assumption of continuity," rules out silently
    returning CONTINUE here. ADOPT's action ("treat as fork from the
    manifest's own head_seq") is the conservative read: rather than trust
    a head_seq the service never ACKed, treat this like an
    ancestry-linked fork from that manifest's own claimed state.

    LEGACY_IMPORT (for a missing manifest) and DEGRADED are NOT produced
    by this function from a normal manifest: per the ADR, LEGACY_IMPORT
    for a *missing* manifest applies when "no manifest is present at
    all" -- there is nothing to call resolve() with in that case, so the
    caller decides that before ever constructing a Manifest/calling
    resolve() (use legacy_import_resolution() directly). DEGRADED means
    "the service was unreachable at HELLO time" -- a fact about the
    shim's network call failing, not a value RESOLVE (which runs inside
    the reachable service) could ever compute from its own inputs. Both
    are real ResolveDecision values so a caller can construct a
    Resolution for them uniformly, but resolve() itself only reaches
    LEGACY_IMPORT via the format_version gate above, never DEGRADED.
    """
    if manifest.format_version > SUPPORTED_FORMAT_VERSION:
        return legacy_import_resolution(save_uuid_hint=manifest.save_uuid)

    if not branch_state.known:
        # NEW_TIMELINE always starts a fresh branch at generation 0 --
        # nothing about a save_uuid the service has never seen can be
        # trusted as "this is generation N," even if the manifest claims
        # one (mirrors legacy_import_resolution()'s branch_generation=0
        # for the same reason: a brand-new branch has no prior generation).
        return Resolution(decision=ResolveDecision.NEW_TIMELINE, branch_generation=0)

    if manifest.generation not in branch_state.known_generations:
        # ADOPT: known save_uuid, but this generation has never been seen --
        # a copied/cloud-restored save. Fork from the manifest's own head_seq,
        # linking ancestry via the manifest's own parent_generation field
        # (per the ADR: "link ancestry via parent_generation"). A root-
        # generation manifest legitimately carries parent_generation=None
        # (ADR: "null/zero for the root") -- that's an honest "no ancestor
        # to link," not a missing value, so it passes through unchanged
        # rather than being defaulted to something invented here.
        return Resolution(
            decision=ResolveDecision.ADOPT,
            branch_generation=manifest.generation,
            fork_parent_generation=manifest.parent_generation,
            fork_at_gamets=manifest.gamets,
        )

    if manifest.gamets < branch_state.head_gamets:
        # FORK: same save_uuid/generation, but this manifest's in-game clock
        # is behind the branch head -- a reload to an earlier point.
        return Resolution(
            decision=ResolveDecision.FORK,
            branch_generation=manifest.generation,
            fork_parent_generation=manifest.generation,
            fork_at_gamets=manifest.gamets,
        )

    if manifest.head_seq > branch_state.head_seq:
        # ADOPT-shaped: the manifest claims more ACKed history than the
        # service has on record for this branch (e.g. the service's store
        # was restored from an older backup). Never silently CONTINUE past
        # state the service never actually ACKed -- fork from the
        # manifest's own head_seq instead, same action as ADOPT.
        return Resolution(
            decision=ResolveDecision.ADOPT,
            branch_generation=manifest.generation,
            fork_parent_generation=manifest.generation,
            fork_at_gamets=manifest.gamets,
        )

    # CONTINUE: same branch, service's head_seq >= manifest's, gamets current.
    replay_from_seq = None
    if branch_state.head_seq > manifest.head_seq:
        replay_from_seq = manifest.head_seq + 1
    return Resolution(
        decision=ResolveDecision.CONTINUE,
        branch_generation=manifest.generation,
        replay_from_seq=replay_from_seq,
    )


def legacy_import_resolution(save_uuid_hint: str | None = None) -> Resolution:
    """The Resolution a caller constructs when no manifest is present at all (ADR-0005's LEGACY_IMPORT row).

    Also used internally by resolve() for the format-version-too-new
    fallback (scenarios/sync/04), since the ADR treats both as the same
    "bootstrap from heuristics" action. `save_uuid_hint` is informational
    only (e.g. a save filename's embedded ID, or the unreadable
    manifest's own save_uuid) and is carried on the Resolution for a
    caller/log to use; generation always starts at 0 for a bootstrapped
    branch, matching NEW_TIMELINE's reasoning above.
    """
    return Resolution(decision=ResolveDecision.LEGACY_IMPORT, branch_generation=0, save_uuid_hint=save_uuid_hint)


def degraded_resolution() -> Resolution:
    """The Resolution a caller (the shim side) uses when the service is unreachable at HELLO (ADR-0005's DEGRADED row).

    Never produced by resolve() -- see its docstring. This exists so a
    caller has a uniform Resolution value to hold while buffering events
    locally (ADR-0005's never-block rule) until a real HELLO/RESOLVE/ACK
    can complete on reconnect. `branch_generation=-1` is a deliberate
    sentinel: no real generation is known yet, and any code that tries to
    tag outbound events with this Resolution's branch_generation without
    first checking `decision == DEGRADED` will produce an obviously
    invalid branch key rather than a silently-wrong one.
    """
    return Resolution(decision=ResolveDecision.DEGRADED, branch_generation=-1)


# --- Epoch fencing (ADR-0005 point 4) ---------------------------------------
#
# Every load or new-game increments an epoch_id. Every mutation the shim
# sends carries the epoch it was issued under. The service discards any
# mutation whose epoch is older than the current active epoch -- this is
# what stops a stale async response from a pre-reload operation (an LLM
# call or network round trip started before the reload) from landing in
# the post-reload timeline.
#
# Caller discipline (no wiring code exists yet to show this in situ):
#   - The service holds one `current_epoch` int per active (save_uuid)
#     session, starting at 0 for a session's first HELLO.
#   - Every successful RESOLVE that hands back a Resolution also bumps
#     current_epoch by 1 (a new epoch per load/new-game, per the ADR) --
#     the caller does this increment, not resolve() itself, since
#     resolve() is a pure classification function with no session state.
#   - Every inbound MUTATION_EVENT is checked with mutation_admissible()
#     against that session's current_epoch before being folded into any
#     derived state; a rejected mutation is dropped (logged, not applied),
#     never queued for a "later" epoch that will never come.


def mutation_admissible(mutation_epoch: int, current_epoch: int) -> bool:
    """Whether a mutation issued under mutation_epoch may still be applied under current_epoch.

    True only when mutation_epoch >= current_epoch -- a mutation from a
    strictly older epoch is stale (issued before some load/new-game this
    session has since moved past) and must be discarded, never applied
    and never buffered for later (ADR-0005 point 4).
    """
    return mutation_epoch >= current_epoch


# --- Idempotency / dedup (ADR-0005 point 7) ---------------------------------
#
# The ADR specifies dedup keyed on (save_uuid, generation, event_seq).
# chronicle.events.EventLog.append() already implements exactly this: it
# tracks seen (save_uuid, generation)-scoped seq values in
# EventLog._seen_seqs and returns False (a no-op) for a duplicate
# (branch, seq) pair -- see EventLog.append()'s docstring, which cites
# this ADR directly ("This is what makes reconnect replays, retried
# network posts, and double-fired Papyrus events safe by construction").
#
# There is deliberately no second dedup mechanism in this module: a
# sync-layer caller should feed every inbound MUTATION_EVENT straight
# into EventLog.append() (after the epoch-fencing check above) and treat
# its bool return as the idempotency signal, rather than this module
# maintaining a parallel seen-set that could drift out of sync with the
# log's own.
