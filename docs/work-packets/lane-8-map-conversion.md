# Lane 8 — Map-view conversion + visual parity harness

**Status:** In flight (overseer-run subagents, dispatched 2026-08-22).
Parallel with lanes 4/6/7 by directory ownership.
**Effort:** medium-large. Two sub-lanes: 8a map components, 8b timeline +
harness.

## Context

Owner directive: convert the approved M3 mockup (`dashboard/design/
map-c-skyrim.dc.html`) to Vue components **now**, against the mock fixture,
rather than waiting for its forcing tier — it becomes the visual test
harness and de-risks M3. Hard constraints from the owner: every file under
500 lines; everything componentized; CSS ported faithfully from the
mockup; Playwright visual diff against the mockup as the sanity check.

## Scope and boundaries

- **8a owns:** `src/views/MapView.vue`, `src/components/map/**`.
- **8b owns:** `src/components/timeline/**`, `scripts/visual-diff.mjs`
  (+ devDeps playwright/pixelmatch/pngjs).
- **Overseer owns integration:** router/Shell wiring (shared files stay
  untouched by subagents).
- **Explicitly not lane 8:** inspector panel and app chrome (lane 7),
  reader/derived/stores (lane 6). The map consumes those at integration.

## Foundation (overseer, landed in 28b81d6)

- `src/styles/tokens.css` — design-tokens.md as CSS custom properties.
- `src/fixtures/whiterunMock.ts` — the mockup's data layer ported 1:1
  (real location pixels from whiterun_map.json, crop projection, 26-NPC
  cast, timeline events, stage legend, LIVE dock states).
- `public/assets/whiterun_topdown_4k.webp` — gitignored bake, served at
  `/assets/`.

## Acceptance

- Build/test/check-range green; component tests for MarkerLayer,
  LensPanel, TimelineBar.
- `npm run visual-diff` runs end-to-end Vue-vs-mockup at 1600×900 and
  reports a diff %; overseer reviews the diff image and iterates with the
  subagents until the map region is visually faithful (text metrics
  permitting — fonts via CDN).
