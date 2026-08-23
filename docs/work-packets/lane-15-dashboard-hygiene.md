# Lane 15 — dashboard hygiene batch (Track B)

**Status:** Ready to start immediately. Three small, independent fixes,
each already diagnosed — this is a batch lane, not a design lane. No
overlap with lane 14 (map → real data wiring) in flight: you touch the
label component, RunPicker, and the tail poller; lane 14 touches the
map's *data* path. If a file collision appears, stop and report.

**Effort:** small (three independent fixes + tests).

## Context

Three known defects from the lane-8/10/11 rounds, batched because none
justifies its own lane:

1. **Markarth satellite label collision** — known since the design
   rounds (recorded in the design lane's board row): the satellite
   node's label text renders *through* the dashed circle instead of
   clear of it.
2. **RunPicker shows "(none selected)"** on load — the M3 mockup's top
   bar shows an active run, so the visual-diff harness diffs chrome that
   should match. The picker should default to a run when the registry
   has one.
3. **Live-tail 416 spam** — `LiveTailPoller` polls `trace.jsonl` at ~1s;
   against a static (non-growing) run every poll is a harmless 416 Range
   Not Satisfiable, forever, in any LIVE-docked view (Shell's LIVE dock
   and the lane-11 feed store alike — verified live in the lane-11
   review; pre-existing project-wide behavior, not a lane-11 bug).

## Read first

1. `dashboard/src/components/map/SatelliteNode.vue` (+ its lane-10 test)
   and the mockup `dashboard/design/map-c-skyrim.dc.html` — how the
   satellite label is placed there (the vendored design is the visual
   contract; `dashboard/design/design-tokens.md` for geometry tokens).
2. `dashboard/src/components/RunPicker.vue` and `src/stores/runs.ts`
   (`pickableRuns`); `src/state/urlState.ts` (`run` codec, defaults
   omitted from the URL).
3. `dashboard/src/log/streamReader.ts` — `LiveTailPoller` (poll cadence,
   torn-tail handling, how a 416 surfaces); its two consumers:
   `src/log/runReader.ts` (`startLiveTail`) and `src/stores/feed.ts`.
4. `docs/work-packets/reviews/README.md` — governance + coordination
   rules. Lane agents do not commit.

## Task

1. **Satellite label collision:** fix the label placement so text renders
   clear of the dashed circle (match the mockup's placement — measure
   it, don't eyeball). Keep the component's props/interface unchanged;
   this is geometry only. Update/extend `SatelliteNode.test.ts` if it
   asserts the old geometry.
2. **RunPicker default:** when the runs registry loads and no `run` is
   selected (URL has no `run` param), default-select the registry's most
   recent run (by `created_wall_ts`; `whiterun-jarl-01` in practice
   today). Explicit user/URL selection always wins; a missing-registry
   environment keeps the current "(none selected)" behavior (the
   component already tolerates it). Do not change the codec's
   "defaults omitted from the URL" law — the default selection is
   in-memory until the user picks or a deep link sets `run`.
   Tests: defaults to most-recent on registry load; explicit `run` param
   is not overridden; empty registry → unchanged behavior.
3. **416 backoff:** fix in `LiveTailPoller` itself so both consumers
   benefit: on a 416 (requested range beyond current EOF), back off
   exponentially from the base interval (1s → 2s → 4s → … capped at
   10s); on any successful read (200/206 with new bytes), reset to the
   base interval immediately. Liveness is preserved (a growing run is
   picked up within the backoff window), static-run log spam dies.
   Tests: mock fetch; assert the interval sequence on repeated 416s, the
   cap, and the reset on new data. Do not change the poller's public
   interface.
4. Re-run `npm run visual-diff` after 1+2 and report the new overall %
   (the RunPicker fix should close the top-bar region's residual; the
   Markarth fix may move the map region slightly — either direction is
   fine, just report the number).

## Acceptance

- `npm run build`, `npm test`, `npm run check-range` green;
  `uv run pytest -q` untouched-green (183 passed), ruff clean.
- The three fixes each covered by tests as specified above.
- `npm run visual-diff` run, new overall % reported.
- No new dependencies; no interface changes to `LiveTailPoller`,
  `RunPicker`, or `SatelliteNode`.

## File boundaries

**Edit:**
- `dashboard/src/components/map/SatelliteNode.vue` (+ its test)
- `dashboard/src/components/RunPicker.vue` (+ a test — new if none exists)
- `dashboard/src/log/streamReader.ts` (+ its test — new if none exists)

**Do not touch:**
- `src/stores/feed.ts`, `src/log/runReader.ts` (consumers — they benefit
  through the poller; if you find they need changes, that's a finding)
- map data-path files (lane 14 in flight): `MapView.vue`, `MapScreen.vue`,
  marker components other than `SatelliteNode.vue`,
  `src/fixtures/whiterunMock.ts`, `src/stores/frameLog.ts`,
  `src/log/reconstruct.ts`
- frozen docs; `runs/`; Python-side anything

## Conventions

- TypeScript strict; design tokens from `src/styles/tokens.css`.
- **No `git commit`** — the coordinator reviews and commits.
- Don't change existing test assertions except as Task 1 allows (old
  geometry assertions); conflicts are findings.
- Report format: what you delivered per task, acceptance status with
  command output tails, the new visual-diff %, and a findings list.
