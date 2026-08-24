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
| 21 | [lane-21-variant-tree.md](lane-21-variant-tree.md) | lanes 12, 14, 16, 17 (landed) | medium-large (code) |
| 22 | [lane-22-provenance-drilldown.md](lane-22-provenance-drilldown.md) | lanes 6, 12, 17 (landed); lane 21 concurrent | medium-large (code) |
| 23 | [lane-23-tell-decision.md](lane-23-tell-decision.md) | lane 19 (landed) | medium (code) |
| 24 | [lane-24-accumulation-threshold.md](lane-24-accumulation-threshold.md) | lanes 19, 23 (serial on driver.py) | medium (code) |
| 25 | [lane-25-obligation-violation.md](lane-25-obligation-violation.md) | lane 24 (serial) | small-medium (code) |
| 26 | [lane-26-reputation-wiring.md](lane-26-reputation-wiring.md) | lane 25 (serial) | medium (code) |
| 27 | [lane-27-supersession-replay.md](lane-27-supersession-replay.md) | lane 21 finding (landed) | small (code) |
| 28 | [lane-28-inspector-real-data.md](lane-28-inspector-real-data.md) | lane 14 (landed) | medium (code) |
| 29 | [lane-29-tier-3-demo-run.md](lane-29-tier-3-demo-run.md) | lanes 19–26 (landed) | small-medium (producer) |
| 30 | [lane-30-diff-panel.md](lane-30-diff-panel.md) | lane 29 (landed) | medium-large (code) |
| 31 | [lane-31-rule-firing-log.md](lane-31-rule-firing-log.md) | lane 30 (serial) | medium (code) |
| 32 | [lane-32-cli-hygiene.md](lane-32-cli-hygiene.md) | lanes 17, 29 findings | small (code) |
| 33 | [lane-33-tier-4a-design-prep.md](lane-33-tier-4a-design-prep.md) | lane 32; Tier 3 (landed) | medium (design doc) |
| 34 | [lane-34-layer-4-reconstruction.md](lane-34-layer-4-reconstruction.md) | lane-30 pre-dispatch finding | medium (code) |
| 35 | [lane-35-map-variant-lens.md](lane-35-map-variant-lens.md) | lanes 14, 21 (landed) | small-medium (code) |
| 36 | [lane-36-schedule-write-back.md](lane-36-schedule-write-back.md) | lane 33 (design accepted) | medium-large (code) |
| 37 | [lane-37-t4a2-counterfactual.md](lane-37-t4a2-counterfactual.md) | lane 36 (serial) | medium (test) |
| 38 | [lane-38-run-comparison.md](lane-38-run-comparison.md) | lanes 6, 21 (landed); lane 37 (fixture, when landed) | medium-large (code) |
| 39 | [lane-39-status-changed-event.md](lane-39-status-changed-event.md) | lane 26 backlog | small (code) |
| 40 | [lane-40-tier-4b-design-prep.md](lane-40-tier-4b-design-prep.md) | lanes 36, 37 (landed) | small-medium (design doc) |
| 41 | [lane-41-schedule-diff.md](lane-41-schedule-diff.md) | lanes 34, 36 (landed) | medium (code) |
| 42 | [lane-42-mourning-demo-run.md](lane-42-mourning-demo-run.md) | lane 36 (landed) | small (producer) |
| 43 | [lane-43-tier-4b-avoidance.md](lane-43-tier-4b-avoidance.md) | lane 40 (design accepted) | medium (code) |
| 44 | [lane-44-tier-5-design-prep.md](lane-44-tier-5-design-prep.md) | lane 43 | medium (design doc) |
| 45 | [lane-45-north-star-fixture-design.md](lane-45-north-star-fixture-design.md) | lane 44 (design ruled) | medium-large (design doc) |
| 46 | [lane-46-injection-console-display.md](lane-46-injection-console-display.md) | lane 9 (landed) | small (code) |
| 47 | [lane-47-role-model-vacancy.md](lane-47-role-model-vacancy.md) | lane 44 (design ruled) | medium (code) |
| 48 | [lane-48-succession.md](lane-48-succession.md) | lane 47 (serial) | medium (code) |
| 49 | [lane-49-north-star-composition.md](lane-49-north-star-composition.md) | lanes 45, 47, 48 (landed) | large (fixture + test + producer) |
| 50 | [lane-50-motivated-mutation.md](lane-50-motivated-mutation.md) | lane 45 (design ruled) | small-medium (code) |
| 51 | [lane-51-role-installed.md](lane-51-role-installed.md) | lane 47 (landed) | small (code) |
| 52 | [lane-52-role-inspector.md](lane-52-role-inspector.md) | lane 51 | medium (code) |
| 53 | [lane-53-m7-walkthrough-gate.md](lane-53-m7-walkthrough-gate.md) | lanes 49, 52 | medium (QA, no code) |
| 54 | [lane-54-timeline-global-chrome.md](lane-54-timeline-global-chrome.md) | lane 53 (M7 gate finding) | medium (code) |
| 55 | [lane-55-markarth-map-coverage.md](lane-55-markarth-map-coverage.md) | lane 53 (M7 gate finding) | medium-large (code) |
| 56 | [lane-56-variant-tree-edge-labels.md](lane-56-variant-tree-edge-labels.md) | lane 53 (M7 gate finding) | small-medium (code) |
| 57 | [lane-57-provenance-popover.md](lane-57-provenance-popover.md) | lane 53 (M7 gate finding) | small-medium (code) |
| 58 | [lane-58-outcome-filter-label-mismatch.md](lane-58-outcome-filter-label-mismatch.md) | lane 53 (M7 gate finding) | small (code) |

**Current wave:** 30 → 31 (Track B, M4 views); 32 → 33 (Track A, hygiene then Tier-4a design).

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
