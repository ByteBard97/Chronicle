# Scenario: manifest schema version newer than the installed plugin

**Setup**: a save was created with a newer version of Chronicle's SKSE
shim than is currently installed (player downgraded the mod, or a save
was shared by someone on a newer version), so the co-save manifest's
`format_version` is higher than this build understands.

**Trigger**: player loads that save.

**Expected outcome**: the shim refuses to interpret fields it doesn't
recognize rather than misreading them (tolerant-read rule: unknown fields
are ignored, not corrupted or reinterpreted) and falls back to LEGACY
IMPORT. No crash, no silent misinterpretation of a `head_seq` or `gamets`
value under the wrong schema layout.

**Assert**: (1) no crash; (2) no corrupted branch state; (3) the fallback
path is LEGACY IMPORT, and a subsequent save re-writes a
current-version manifest.

**Source**: `docs/research/09-save-sync-forensics.md` §5.4 failure matrix,
"Player downgrades mod / manifest version newer than plugin."
