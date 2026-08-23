# Lane 10 — Component/integration tests for the map and timeline pieces

**Status:** Ready to start immediately. Test-only lane — no production
code changes except fixing a real bug a test proves exists. No file
overlap with any other lane.
**Effort:** medium-large (16 files: 14 components + 2 views).

## Context

Lane 8 (map conversion + visual parity, accepted) delivered
`src/views/MapScreen.vue`/`MapView.vue` and 13 components under
`src/components/map/` and `src/components/timeline/`, but its acceptance
criteria only named three: `MarkerLayer`, `LensPanel`, `TimelineBar` — the
only three that got test files. An audit found 14 components/views with
zero test coverage:

- `src/components/map/`: `CarrierMarker`, `GlyphLegend`, `LayerToggles`,
  `LocationLabels`, `MapBackdrop`, `NpcMarker`, `RouteOverlay`,
  `SatelliteNode`, `StageLegend`, `ZoomControls`.
- `src/components/timeline/`: `LiveDockPill`, `TimelineLegend`,
  `TimelineTrack`, `TransportControls`.
- `src/views/`: `MapScreen.vue`, `MapView.vue` (no test at all, unlike
  `Shell.vue`'s `Shell.test.ts`).

`vue-tsc`/`vite build` type-check and bundle these; they do not execute
them. Lane 5's `Shell.test.ts` found a real runtime-only bug this way
(`useRouteQuery`'s default history mode) that typecheck/build missed —
the same class of bug could be hiding in any of these 14 files.

## Read first

1. `src/components/map/MarkerLayer.test.ts`, `LensPanel.test.ts`,
   `src/components/timeline/TimelineBar.test.ts` — the established
   per-component pattern: `mount()` from `@vue/test-utils`, props in,
   assert on rendered structure/classes/inline styles, using
   `src/fixtures/whiterunMock.ts`'s fixture data (`CAST`, `buildMarkers`,
   etc. — read that file too) rather than inventing new fixtures.
2. `src/views/Shell.test.ts` — the established view-level integration
   pattern: mount through a real `vue-router` (`createMemoryHistory`) and
   `pinia`, with `fetch` stubbed, `flushPromises()` before assertions.
   This is your template for `MapScreen.test.ts`/`MapView.test.ts`.
3. `dashboard/design/design-tokens.md` and `map-c-skyrim.dc.html` — what
   each component is supposed to represent, if a prop's meaning isn't
   obvious from the `.vue` file alone.
4. Every `.vue` file you're testing, in full — read the actual props,
   emits, and template before writing assertions against them. Don't
   infer a component's contract from its name.

## Task

1. **One test file per untested component** (14 total), following the
   established pattern: mount with representative props (pull from
   `whiterunMock.ts` fixture data where the component consumes cast/map
   data; hand-construct minimal props otherwise), assert on the rendered
   output a human would actually check — classes present, correct count
   of child elements/markers, correct text/label content, correct
   conditional rendering (e.g. a toggle's on/off state changing which
   elements render), emitted events firing with the right payload on
   interaction (click/toggle handlers). Skip pure CSS-value assertions
   with no logic behind them (that's `tokens.css` restating itself) —
   test behavior and structure, not colors.
2. **`MapScreen.test.ts` and `MapView.test.ts`**: at least one
   integration-style test each proving the assembled view actually
   renders its children correctly wired together (e.g. `MapScreen`
   mounts `MapView` inside its chrome; `MapView` mounts `MarkerLayer` +
   the backdrop + the lens panel with real fixture data flowing through,
   not stubs). Use `Shell.test.ts`'s router/pinia/flushPromises pattern.
3. **Fix any real bug a test finds.** This lane is test-only by default,
   but if a test proves a component is actually broken (wrong prop
   wiring, an emit that never fires, a computed that throws on realistic
   input), fix it — narrowly, in that component only — and say so
   explicitly in your report. Don't fix things a test doesn't prove
   broken; don't refactor components that pass.
4. Keep every new test screenshot-stable per the project's existing
   discipline: no `Date.now()`/`Math.random()`/non-deterministic keys in
   assertions.

## Acceptance

- `npm run build` / `npm test` / `npm run check-range` green.
- All 16 files have at least one test; components with interactive
  behavior (toggles, click handlers, zoom controls) have a test that
  actually exercises the interaction, not just a mount-and-snapshot.
- Any bug fix is called out by name in the report, with the failing
  assertion that caught it.

## File boundaries

- **Create:** one `*.test.ts` per file named in Task 1 and 2, alongside
  the component it tests (matching existing naming convention).
- **Edit:** only a `.vue` file you are also adding/have a test for, and
  only to fix a bug that test proves — no unrelated changes.
- **Do not touch:** `src/log/`, `src/derived/`, `src/state/`, `src/stores/`
  (unless a map/timeline component's own file needs a one-line fix — report
  if you think it does, don't cross into store logic), `dashboard/design/`
  (read-only reference), `chronicle/`, `docs/` (other than this packet).

## Conventions

- Commits: this project's current convention is agents commit their own
  work; the overseer reviews what lands.
- TypeScript strict; no new dependencies.
