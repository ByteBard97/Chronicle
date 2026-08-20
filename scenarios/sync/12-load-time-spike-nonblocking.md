# Scenario: load-time event burst doesn't block the game

**Setup**: a cell/world load produces a burst of events all at once (many
NPCs, many state checks) right as the handshake is completing —
documented in the wild as SkyrimNet's own "cannot keep up with game load"
issue.

**Trigger**: the burst arrives at or immediately after `TIMELINE_READY`.

**Expected outcome**: the game thread is never blocked waiting for the
service to process the burst. The shim sends events asynchronously and
continues; the service processes the burst at its own pace, applying
back-pressure tolerance (buffering, not dropping) rather than forcing the
game to wait.

**Assert**: (1) no measurable frame-time/loading-screen impact
attributable to the sync layer during the burst; (2) all burst events are
eventually processed and folded into the correct branch, just not
necessarily instantly; (3) if the service falls behind, it degrades by
queuing, not by dropping events silently.

**Source**: `docs/research/09-save-sync-forensics.md` §4.3 race catalog
item 6, citing SkyrimNet issue #172.
