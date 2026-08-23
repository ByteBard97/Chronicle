# Work packets — dashboard build, first wave

Five lanes implementing `docs/dashboard-build-plan.md` prerequisites + M0/M1.
Each packet is self-contained: hand it to an agent verbatim.

| Lane | Packet | Depends on | Effort |
|------|--------|-----------|--------|
| 1 | [lane-1-keyed-randomness-adr.md](lane-1-keyed-randomness-adr.md) | — | small (doc) |
| 2 | [lane-2-frame-log-schema.md](lane-2-frame-log-schema.md) | — | medium (doc) |
| 3 | [lane-3-tick-quantum.md](lane-3-tick-quantum.md) | — | small (doc + constants) |
| 4 | [lane-4-m0-substrate.md](lane-4-m0-substrate.md) | lanes 1–3 | large (code) |
| 5 | [lane-5-m1-scaffold.md](lane-5-m1-scaffold.md) | — | medium (code) |
| 6 | [lane-6-m1-reader-chrome.md](lane-6-m1-reader-chrome.md) | lane 5 (landed) | medium-large (code) |
| 7 | [lane-7-design-system.md](lane-7-design-system.md) | — (design vendored) | medium (code) |
| 8 | [lane-8-map-conversion.md](lane-8-map-conversion.md) | lane 8 foundation (28b81d6) | medium-large (code) |
| 9 | [lane-9-m1-cli-and-deep-links.md](lane-9-m1-cli-and-deep-links.md) | lane 4 (landed) | medium (code) |
| 10 | [lane-10-map-timeline-component-tests.md](lane-10-map-timeline-component-tests.md) | lane 8 (landed) | medium-large (test) |
| 11 | [lane-11-m2-encounter-feed.md](lane-11-m2-encounter-feed.md) | lanes 5, 6, 9 (landed) | medium-large (code) |
| 12 | [lane-12-t2-3-variant-resolution.md](lane-12-t2-3-variant-resolution.md) | lane 4 + Tier 2 mutation machinery (landed) | medium-large (code) |

**Start now, in parallel:** lanes 1, 2, 3, 5. **Start after 1–3 land:** lane 4.
**Current wave:** lanes 11 (dashboard, Track B) and 12 (sim, Track A) in parallel — disjoint trees.

Soft dependency not shown in the table: Lane 2's roll-record payload cites
Lane 1's `roll_key` vocabulary (members and order are ADR-0009's to decide).
The coordinator reviews Lane 1 before Lane 2 finalizes trace payloads.

## Coordination rules (all lanes)

1. **Frozen documents** — nobody edits `docs/ui-spec.md`,
   `docs/scenario-ladder.md`, or `docs/ui-doctrines.md`. Findings about
   them go to the coordinator, who runs the review cycle.
2. **No `git commit`** in any lane — the coordinator reviews and commits.
3. **Tests stay green** (`uv run pytest`, `uv run ruff check .`). Lanes
   that touch code must not change existing test assertions; if a test
   conflicts with your task, report it, don't edit it.
4. **File boundaries are the collision avoidance** — stay in yours. If
   your task seems to require editing another lane's file, that's a
   finding to report, not a boundary to cross.
5. Report format: what you delivered, acceptance status, and a findings
   list (anything surprising, contradictory, or out of scope you noticed).
