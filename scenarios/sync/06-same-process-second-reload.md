# Scenario: second reload within the same running game process

**Setup**: the player loads a save, plays, then loads another save (or
the same one again) without restarting the Skyrim process. The engine is
documented to not cleanly tear down script activity across in-session
reloads ("stacking scripts").

**Trigger**: the second in-session load.

**Expected outcome**: the shim treats this exactly like a fresh-process
load — no cached "current timeline" state survives from the first load
at the process level, only per-load state re-established via a fresh
HELLO/RESOLVE/ACK handshake. Re-registration of event hooks is idempotent
(safe to run N times in one process). A first-load-in-new-process is
indistinguishable, from the service's perspective, from a tenth-load-in-
same-process.

**Assert**: (1) no stale event-hook registrations from the first load
still firing after the second; (2) the second load's handshake resolves
correctly regardless of what happened in the first; (3) no orphaned
in-flight state (e.g. a spell-effect-driven timer) from the first load
leaks into the second.

**Source**: `docs/research/09-save-sync-forensics.md` §4.2, §4.3 race
catalog (same-process reload discussion).
