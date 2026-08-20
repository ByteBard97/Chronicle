# Scenario: save copied to another machine or cloud-restored

**Setup**: a save with a valid manifest (known `save_uuid`) is copied to a
different machine, or restored from a cloud backup, such that its
`generation`/`head_seq` doesn't match what this service instance has on
record for that `save_uuid` (a different, unknown `generation`).

**Trigger**: player loads the copied/restored save.

**Expected outcome**: resolves as **ADOPT** — treated as a fork from the
manifest's own `head_seq`, with ancestry linked via `parent_generation`.
Both the original machine's continuation and this restored save's new
play are preserved as sibling branches; neither silently overwrites the
other.

**Assert**: (1) both branches remain independently queryable after the
fact; (2) no event from one sibling branch leaks into the other's derived
state; (3) the ADOPT path doesn't require the original machine to be
reachable or even exist.

**Source**: `docs/research/09-save-sync-forensics.md` §5.2 decision table
("ADOPT"), §5.4 failure matrix.
