# Scenario: co-save read vs. service-notification ordering

**Setup**: the shim is reading the co-save manifest during the engine's
load callback; the service is still serving the *previous* timeline's
state because the HELLO hasn't been sent/acknowledged yet.

**Trigger**: an event is generated in this narrow window — e.g. queued
Papyrus work from before the reload fires, or an async LLM call that was
in flight before the reload resolves during it.

**Expected outcome**: the event either doesn't reach the service before
HELLO/ACK completes (buffered by `g_isLoading`, per ADR-0005), or if it
does arrive, it's tagged with the pre-reload `(save_uuid, generation)`/
epoch and the service rejects it as stale rather than folding it into the
newly-active branch.

**Assert**: (1) no event generated in this window is folded into the
wrong branch's derived state; (2) the event is either correctly
attributed to the old (now-abandoned) branch, buffered, or dropped —
never silently misattributed.

**Source**: `docs/research/09-save-sync-forensics.md` §4.3 race catalog
item 1.
