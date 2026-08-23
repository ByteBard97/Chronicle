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
| 13 | [lane-13-t2-6-7-carriers.md](lane-13-t2-6-7-carriers.md) | lane 12 + death-awareness (landed) | medium (fixtures + tests) |
| 14 | [lane-14-map-real-data.md](lane-14-map-real-data.md) | lanes 6, 8, 11 (landed) | large (code) |
| 15 | [lane-15-dashboard-hygiene.md](lane-15-dashboard-hygiene.md) | lanes 8, 10, 11 (landed) | small (code) |
| 16 | [lane-16-timeline-real-data.md](lane-16-timeline-real-data.md) | lane 14 (in flight) | medium-large (code) |
| 17 | [lane-17-carrier-mutation-demo-run.md](lane-17-carrier-mutation-demo-run.md) | lane 13 (landed) | small-medium (producer + cli) |
| 18 | [lane-18-tier-3-design-prep.md](lane-18-tier-3-design-prep.md) | lane 12 (landed) | medium (design doc, no code) |
| 19 | [lane-19-rule-registry-core.md](lane-19-rule-registry-core.md) | lane 18 (design accepted) | medium (code) |
| 20 | [lane-20-grudge-decay.md](lane-20-grudge-decay.md) | lane 18 (design accepted) | small (code) |

**Current wave:** lanes 13 (Track A), 14 (Track B), 15 (Track B) — 13 disjoint from 14/15; 14 and 15 coordinate via their file boundaries (15 owns SatelliteNode/RunPicker/streamReader; 14 owns the map data path).

Soft dependency not shown in the table: Lane 2's roll-record payload cites
Lane 1's `roll_key` vocabulary (members and order are ADR-0009's to decide).
The coordinator reviews Lane 1 before Lane 2 finalizes trace payloads.

## Coordination rules (all lanes)

1. **Frozen documents** — nobody edits `docs/ui-spec.md`,
   `docs/scenario-ladder.md`, or `docs/ui-doctrines.md`. Findings about
   them go to the coordinator, who runs the review cycle.
2. **Commits** — local commits are fine for everyone (path-scoped,
   explicit adds, never `-a`/`-A`); the coordinator reviews every lane,
   post-commit where applicable, and can require fixes. **No pushing to
   a remote without explicit owner permission.** (Owner ruling
   2026-08-23 — see `reviews/README.md`'s governance section.)
3. **Tests stay green** (`uv run pytest`, `uv run ruff check .`). Lanes
   that touch code must not change existing test assertions; if a test
   conflicts with your task, report it, don't edit it.
4. **File boundaries are the collision avoidance** — stay in yours. If
   your task seems to require editing another lane's file, that's a
   finding to report, not a boundary to cross.
5. Report format: what you delivered, acceptance status, and a findings
   list (anything surprising, contradictory, or out of scope you noticed).
