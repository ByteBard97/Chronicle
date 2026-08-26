"""Tests for chronicle.sync -- the ADR-0005 RESOLVE table, epoch fencing, and dedup reuse.

Each RESOLVE branch is tested against a concrete Manifest/BranchState pair.
Scenario coverage below cites scenarios/sync/*.md by file number, the same
convention scenarios/test_tier3_accumulation.py uses for
docs/scenario-ladder.md:72.
"""

from chronicle.events import EventLog, NPCDied
from chronicle.sync import (
    SUPPORTED_FORMAT_VERSION,
    BranchState,
    Manifest,
    ResolveDecision,
    degraded_resolution,
    legacy_import_resolution,
    mutation_admissible,
    resolve,
)


def _manifest(**overrides):
    defaults = dict(
        format_version=1,
        save_uuid="s1",
        generation=0,
        parent_generation=None,
        head_seq=5,
        gamets=100.0,
        wall_ts=1000.0,
    )
    defaults.update(overrides)
    return Manifest(**defaults)


# --- The six-way RESOLVE table -----------------------------------------------


def test_continue_when_same_branch_head_ahead_and_gamets_current():
    # scenarios/sync/06-same-process-second-reload.md: a fresh handshake on
    # a branch the service already knows, at or ahead of the manifest.
    manifest = _manifest(head_seq=5, gamets=100.0)
    branch_state = BranchState(known=True, head_generation=0, head_seq=5, head_gamets=100.0, known_generations=frozenset({0}))

    result = resolve(manifest, branch_state)

    assert result.decision is ResolveDecision.CONTINUE
    assert result.branch_generation == 0
    assert result.replay_from_seq is None


def test_continue_replays_unacked_gap_when_branch_head_seq_is_ahead():
    # ADR-0005 point 3: "Resume branch; replay any un-ACKed gap events."
    manifest = _manifest(head_seq=5, gamets=100.0)
    branch_state = BranchState(known=True, head_generation=0, head_seq=8, head_gamets=100.0, known_generations=frozenset({0}))

    result = resolve(manifest, branch_state)

    assert result.decision is ResolveDecision.CONTINUE
    assert result.replay_from_seq == 6


def test_fork_when_gamets_older_than_branch_head():
    # scenarios/sync/11: setup A/B -- a reload to an earlier point on the
    # same save_uuid/generation forks rather than silently continuing.
    manifest = _manifest(generation=0, gamets=50.0, head_seq=2)
    branch_state = BranchState(known=True, head_generation=0, head_seq=8, head_gamets=100.0, known_generations=frozenset({0}))

    result = resolve(manifest, branch_state)

    assert result.decision is ResolveDecision.FORK
    assert result.fork_parent_generation == 0
    assert result.fork_at_gamets == 50.0


def test_adopt_when_save_uuid_known_but_generation_unknown():
    # scenarios/sync/03-save-copied-or-cloud-restored.md.
    manifest = _manifest(generation=7, parent_generation=3, head_seq=20, gamets=500.0)
    branch_state = BranchState(known=True, head_generation=0, head_seq=8, head_gamets=100.0, known_generations=frozenset({0}))

    result = resolve(manifest, branch_state)

    assert result.decision is ResolveDecision.ADOPT
    assert result.fork_parent_generation == 3
    assert result.fork_at_gamets == 500.0


def test_adopt_at_root_generation_has_no_ancestor_to_link():
    # scenarios/sync/03: a root-generation manifest (parent_generation=None,
    # ADR: "null/zero for the root") copied to another machine still
    # resolves ADOPT; there's honestly no ancestor to link, so
    # fork_parent_generation stays None rather than being defaulted.
    manifest = _manifest(generation=7, parent_generation=None, head_seq=20, gamets=500.0)
    branch_state = BranchState(known=True, head_generation=0, head_seq=8, head_gamets=100.0, known_generations=frozenset({0}))

    result = resolve(manifest, branch_state)

    assert result.decision is ResolveDecision.ADOPT
    assert result.fork_parent_generation is None
    assert result.fork_at_gamets == 500.0


def test_new_timeline_when_save_uuid_unknown():
    manifest = _manifest(save_uuid="never-seen", generation=0)
    branch_state = BranchState(known=False)

    result = resolve(manifest, branch_state)

    assert result.decision is ResolveDecision.NEW_TIMELINE
    assert result.branch_generation == 0


def test_new_timeline_starts_at_generation_zero_even_if_manifest_claims_otherwise():
    # A save_uuid the service has never seen carries no trustworthy prior
    # generation, regardless of what the manifest's own generation field says.
    manifest = _manifest(save_uuid="never-seen", generation=9)
    branch_state = BranchState(known=False)

    result = resolve(manifest, branch_state)

    assert result.decision is ResolveDecision.NEW_TIMELINE
    assert result.branch_generation == 0


def test_adopt_when_manifest_head_seq_exceeds_what_service_has_acked():
    # Not a named row in the ADR's table, but scenario 02's assert (3) rules
    # out a silent CONTINUE here: the manifest claims more ACKed history
    # than the service has on record (e.g. its store was restored from an
    # older backup). Conservative resolution: ADOPT-shaped, fork from the
    # manifest's own head_seq rather than assume continuity.
    manifest = _manifest(generation=0, head_seq=50, gamets=100.0)
    branch_state = BranchState(known=True, head_generation=0, head_seq=8, head_gamets=100.0, known_generations=frozenset({0}))

    result = resolve(manifest, branch_state)

    assert result.decision is ResolveDecision.ADOPT
    assert result.fork_parent_generation == 0
    assert result.fork_at_gamets == 100.0


def test_legacy_import_when_manifest_format_version_newer_than_supported():
    # scenarios/sync/04-manifest-version-newer-than-plugin.md: refuse to
    # interpret any field on a manifest stamped with a newer format_version
    # than this build understands; fall back to LEGACY_IMPORT rather than
    # risk misreading head_seq/gamets under an unknown layout.
    manifest = _manifest(format_version=SUPPORTED_FORMAT_VERSION + 1, generation=0, head_seq=999, gamets=999.0)
    branch_state = BranchState(known=True, head_generation=0, head_seq=8, head_gamets=100.0, known_generations=frozenset({0}))

    result = resolve(manifest, branch_state)

    assert result.decision is ResolveDecision.LEGACY_IMPORT
    assert result.branch_generation == 0
    assert result.save_uuid_hint == manifest.save_uuid


def test_legacy_import_is_constructed_without_a_manifest():
    # scenarios/sync/02-crash-mid-save.md: no manifest present at all --
    # there is nothing for resolve() to classify, so the caller constructs
    # this Resolution directly rather than calling resolve(). (Scenario 04
    # -- a manifest that IS present but too new to trust -- is covered by
    # test_legacy_import_when_manifest_format_version_newer_than_supported.)
    result = legacy_import_resolution(save_uuid_hint="Save 42 - Whiterun.ess")

    assert result.decision is ResolveDecision.LEGACY_IMPORT
    assert result.branch_generation == 0


def test_degraded_is_constructed_when_service_unreachable_at_hello():
    # scenarios/sync/01-service-unreachable-at-load.md.
    result = degraded_resolution()

    assert result.decision is ResolveDecision.DEGRADED
    assert result.branch_generation == -1


# --- Epoch fencing (ADR-0005 point 4) ---------------------------------------


def test_mutation_from_current_epoch_is_admissible():
    assert mutation_admissible(mutation_epoch=3, current_epoch=3) is True


def test_mutation_from_newer_epoch_is_admissible():
    assert mutation_admissible(mutation_epoch=4, current_epoch=3) is True


def test_mutation_from_stale_epoch_is_rejected():
    # scenarios/sync/09-co-save-read-vs-notification-race.md: an async op
    # started before a reload must not land in the post-reload timeline.
    assert mutation_admissible(mutation_epoch=2, current_epoch=3) is False


# --- Idempotency / dedup reuse (ADR-0005 point 7) ---------------------------


def test_eventlog_append_already_dedupes_on_branch_and_seq_no_new_mechanism_needed():
    # chronicle.sync deliberately adds no second dedup structure -- this
    # test documents (and pins) that EventLog.append()'s existing
    # (save_uuid, generation, seq) idempotency is what a sync-layer caller
    # should rely on directly. Covers scenarios/sync/08-quicksave-autosave-
    # spam.md's "no spurious branch creation from same-timeline saves" via
    # the same mechanism: replayed/duplicate seqs are no-ops, not new state.
    log = EventLog()
    event = NPCDied(tick=1, save_uuid="s1", generation=0, seq=1, gamets=1.0, wall_ts=1.0, npc_id="n", cause="c")

    assert log.append(event) is True
    assert log.append(event) is False  # a retried HELLO-buffer replay is a no-op


# --- Scenario notes for coverage this pure module cannot exercise ----------
#
# scenarios/sync/05-concurrent-second-writer-lost-update.md (dashboard vs.
# game write race) and scenarios/sync/10-unanchored-write-meets-gc-sweep.md
# (GC liveness/bitemporal rejection) are about layer-2+ store write
# semantics and branch GC, not the RESOLVE table or epoch fencing this
# module implements -- out of scope here, belongs with claims/social store
# and GC work respectively.
#
# scenarios/sync/07-mod-uninstalled-mid-playthrough.md and
# scenarios/sync/12-load-time-spike-nonblocking.md describe operational/
# real-time properties (dormant branches eventually GC'd; no frame-time
# stall under a live game process) that a pure function over explicit
# inputs cannot assert either way -- there is no game loop or GC pass
# here to observe. The RESOLVE-table piece they *do* exercise (07: reload
# after a gap resolves via the ordinary table, not a special code path;
# 12: back-pressure is tolerated by resolve()/EventLog, not by dropping)
# is covered by test_continue_replays_unacked_gap_when_branch_head_seq_is_ahead
# and the dedup test above. The rest is future integration-lane work
# (adapters/skyrim/listener.py + a live game process).
