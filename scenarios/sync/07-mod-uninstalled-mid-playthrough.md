# Scenario: mod uninstalled mid-playthrough

**Setup**: a playthrough with Chronicle-tracked branches exists; the
player uninstalls the mod (or the SKSE shim) but continues playing
vanilla saves from the same character.

**Trigger**: further saves are made without the shim present, then the
mod is reinstalled later (or never).

**Expected outcome**: no crash, no corruption. Saves made without the
shim simply carry no manifest record on their next save (or an
unchanged one). Service-side, the corresponding branches go dormant —
no new events arrive, but nothing is deleted early. Standard branch GC
(reachability + grace period, ADR-0004) eventually archives them like any
other orphaned branch, not as a special case.

**Assert**: (1) uninstalling doesn't crash the game or corrupt existing
saves; (2) reinstalling and loading an old save resolves via the normal
decision table (likely LEGACY IMPORT or CONTINUE, depending on gap
length), not a special "mod was uninstalled" code path; (3) branches with
no mod-covered saves referencing them are GC-eligible on the same
schedule as any other orphan.

**Source**: `docs/research/09-save-sync-forensics.md` §5.4 failure matrix,
"Mod uninstalled mid-playthrough."
