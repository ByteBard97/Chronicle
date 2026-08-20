# Scenario: a second writer (dashboard/API) races the game's own writes

**Setup**: an NPC's relationship/belief state is being written by two
paths concurrently — the live game (via the sync handshake) and a
dashboard or debug/admin tool editing the same record directly.

**Trigger**: both writes target the same record within a short window.

**Expected outcome**: no whole-record overwrite race. Writes go through
either a single serialized writer or per-key compare-and-set; a
read-modify-write from the dashboard never blindly overwrites fields the
game wrote concurrently. This is the failure class CHIM's PR #560
documents ("an NPC's relationship map silently reverts or empties").

**Assert**: (1) after both writes complete, no field written by either
path is silently lost; (2) the record's provenance (ADR-0007) correctly
attributes each field to its actual writer, not to whichever write
happened to land last.

**Source**: `docs/research/09-save-sync-forensics.md` §4.3 race catalog
item 4, citing CHIM/HerikaServer PR #560.
