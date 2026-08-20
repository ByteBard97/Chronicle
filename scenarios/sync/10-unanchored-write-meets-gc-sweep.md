# Scenario: an unanchored (mis-stamped) write meets a GC sweep

**Setup**: a record is written through a path that fails to stamp both
bitemporal fields (`gamets`, `wall_ts`) — e.g. a hypothetical future
admin/debug tool that writes directly without going through the normal
event path.

**Trigger**: a branch-GC pass runs while this unanchored record exists.

**Expected outcome**: the write is **rejected at write time**, not
silently accepted and then destroyed later by GC. Per ADR-0004, both
bitemporal fields are mandatory and never `NULL` — a write missing either
must fail loudly, not succeed with a gap that a later reachability sweep
then misinterprets. This is the exact failure class of SkyrimNet issue
#487 (237 externally-created memories hard-deleted because a cleanup
routine's liveness criterion was an internal timestamp a second write
path stamped differently) and CHIM PR #572 (NULL-timestamped manual edits
treated as "never anchored" and wiped on reconnect) — this scenario exists
specifically to prove Chronicle doesn't reproduce it.

**Assert**: (1) a write missing either bitemporal field is rejected, not
silently accepted; (2) no GC pass ever deletes a record solely because a
timestamp comparison flagged it — liveness is reachability-from-a-live-
save-reference only (ADR-0004); (3) user-curated content (a separate,
protected stream class) is never touched by this GC pass regardless of
its timestamps.

**Source**: `docs/research/09-save-sync-forensics.md` §1.3, §3.4, §4.3
race catalog item 5.
