# Scenario: crash between co-save write and `.ess` write

**Setup**: a save operation is interrupted (process kill, power loss)
after the co-save (`.skse`) manifest is written but before (or during)
the `.ess` write, or vice versa.

**Trigger**: player next loads the game / that save slot.

**Expected outcome**: the manifest is a single, version-checked record —
never half-read. If the `.ess` is missing or corrupt, the save doesn't
appear as loadable (vanilla behavior; not this system's concern). If the
co-save is missing/corrupt but the `.ess` is valid, the load resolves via
LEGACY IMPORT (no manifest → bootstrap from heuristics) rather than
crashing or silently trusting a partial manifest.

**Assert**: (1) no crash on load; (2) no service-side state corruption
from a partially-written manifest; (3) the resolution path taken
(CONTINUE/FORK/LEGACY IMPORT) is the conservative one, never a silent
assumption of continuity.

**Source**: ADR-0004/0005's "atomic by convention, not guaranteed"
implementation-risk note; `docs/research/09-save-sync-forensics.md` §5.4.
