# Scenario: rapid quicksave/autosave spam

**Setup**: the player quicksaves or autosaves repeatedly in quick
succession (e.g. every few seconds during a dangerous fight).

**Trigger**: a burst of `kSaveGame` events, each triggering a manifest
write and checkpoint request.

**Expected outcome**: no branch explosion, no performance stall. Each
save's manifest write is cheap (a small fixed-size record, per the
manifest schema) and doesn't itself create a branch — only a *load* that
diverges from the current head does (ADR-0004). Intermediate checkpoints
may be pruned by count/age without affecting correctness, since a
checkpoint is a replay optimization, not a source of truth.

**Assert**: (1) no observable save-time stall attributable to the sync
layer, even under rapid repeated saves; (2) no spurious branch creation
from same-timeline saves; (3) checkpoint pruning (if implemented) never
removes a checkpoint a live save still references.

**Source**: `docs/research/09-save-sync-forensics.md` §5.4 failure matrix,
"Quicksave/autosave spam."
