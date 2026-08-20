# scenarios/sync

Regression scenarios for the save/reload sync handshake
(`docs/decisions/0004-timeline-branching.md`,
`docs/decisions/0005-sync-handshake.md`). Each file is a stub spec —
setup, trigger, asserted outcome, and the research finding it's drawn
from — not yet an executable scenario, since the SKSE shim and sync
protocol don't exist yet. Convert each to a runnable scenario (per
`scenarios/README.md`'s format) as `adapters/skyrim/`'s sync layer gets
built; the stubs exist now so the protocol's claims stay testable claims
rather than design-doc assertions (ADR-0007's inspectability principle,
applied to the protocol itself).

Source: `docs/research/09-save-sync-forensics.md`'s failure matrix (§5.4)
and six-pattern race catalog (§4.3), deduplicated against overlaps.

| # | Scenario | Covers |
|---|---|---|
| 01 | [service-unreachable-at-load](01-service-unreachable-at-load.md) | DEGRADED mode, never-block rule |
| 02 | [crash-mid-save](02-crash-mid-save.md) | `.skse`/`.ess` atomicity-by-convention residual risk |
| 03 | [save-copied-or-cloud-restored](03-save-copied-or-cloud-restored.md) | ADOPT decision |
| 04 | [manifest-version-newer-than-plugin](04-manifest-version-newer-than-plugin.md) | tolerant-read / LEGACY IMPORT fallback |
| 05 | [concurrent-second-writer-lost-update](05-concurrent-second-writer-lost-update.md) | dashboard/API vs. game race (CHIM PR #560 class) |
| 06 | [same-process-second-reload](06-same-process-second-reload.md) | no process-lifetime caching |
| 07 | [mod-uninstalled-mid-playthrough](07-mod-uninstalled-mid-playthrough.md) | dormant branches, no crash |
| 08 | [quicksave-autosave-spam](08-quicksave-autosave-spam.md) | cheap checkpoints, no branch explosion |
| 09 | [co-save-read-vs-notification-race](09-co-save-read-vs-notification-race.md) | event lands on wrong branch during the load window |
| 10 | [unanchored-write-meets-gc-sweep](10-unanchored-write-meets-gc-sweep.md) | SkyrimNet #487 / CHIM #572 class — reachability-based GC, mandatory bitemporal columns |
| 11 | [death-retry-silent-fork-vs-large-jump-confirm](11-death-retry-silent-fork-vs-large-jump-confirm.md) | automatic small-fork vs. confirmed large-fork |
| 12 | [load-time-spike-nonblocking](12-load-time-spike-nonblocking.md) | never-block rule under load-time burst |
