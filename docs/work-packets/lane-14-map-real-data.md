# Lane 14 — map → real data wiring (Track B, dashboard; M3 prep)

**Status:** Ready to start immediately. Prerequisites landed: lane 6
reader (`RunReader.stateAt`), lane 8 map components, lane 11's
integration idiom (reader module + thin store, `useSelectionUrlSync`),
`derived/rumorStage.ts` (the per-NPC stage function, currently only
consumed by its own test). **Concurrency note:** lane 15 (hygiene) is in
flight touching `SatelliteNode.vue`, `RunPicker.vue`,
`streamReader.ts` — those three files are out of bounds here. Lane 13
(carriers, Python) is disjoint.

**Effort:** large (new derived module + store + view rewiring + tests).

## Context

`MapScreen.vue:8-9`'s own header names this lane: "Data is the mock
fixture… Lane 6's reader wires real per-tick state at M3." Today every
map component reaches into `src/fixtures/whiterunMock.ts` directly —
`MarkerLayer.vue:13,24` (`buildMarkers`) is the single point where cast
markers materialize. After this lane, the map's markers, stage legend,
selection, and inspector render reconstructed state-at-T from a real
run (`runs/whiterun-jarl-01`: 6 NPCs, 2 locations, 1 claim).

**Scope line (pinned):** this lane is **markers + selection + legends +
inspector**. The TimelineBar's real-data rewiring (typed event markers
per ui-spec §2:59, playhead, dock) is a *separate* follow-up lane — it
is a second data path (full-range event enumeration, not state-at-T).
TimelineBar stays fixture-driven; don't touch it.

## Read first (in order)

1. `docs/ui-spec.md` §3.1 (:91 — markers anchor at door pixel; jitter
   seeded by (npc_id, location_id)), §2 (:59 timeline markers —
   informational, next lane; :61-62 selection model + glyph precedence
   list). Frozen — findings to the coordinator.
2. `dashboard/src/fixtures/whiterunMock.ts` — what to keep (types,
   `CROP`/`toPct`, `STAGE_STYLE`, `GLYPH_COLOR` — pure presentation)
   vs. what this lane supersedes (`LOCATIONS`, `CAST`, `buildMarkers`,
   `JITTER_RING`). **Do not edit the fixture** — it still feeds
   TimelineBar and the visual-diff mock.
3. `dashboard/map/whiterun_map.json` — the location-id → pixel source of
   truth (26 location keys; the run's `location_id` values match these,
   NOT the fixture's shorthand ids — `bannered_mare`, not `bannered`).
4. `dashboard/src/log/reconstruct.ts` (:35-47 `SocialState`, rumor key
   format), `src/derived/rumorStage.ts` (:23-37 `rumorStageAt`),
   `src/derived/constants.ts` (:37-38 dormancy thresholds),
   `src/log/runReader.ts` (:105-149).
5. **The lane-11 idiom you'll mirror:** `src/log/feedReader.ts` (pure
   functions) + `src/stores/feed.ts` (setup-style store, `shallowRef`
   rows, status enum, owns its tailer) + `FeedScreen.vue` (:55
   composable install, :57-63 run watch, :119 RunPicker v-model,
   :155-161 inspector props from selection).
6. `src/stores/frameLog.ts:20-27` — the two-watcher ordering hazard;
   your store uses a single combined `[run, t]` watcher like
   `bindToUrlState` (:137-149). Do not extend frameLog.ts (see
   boundaries).
7. `src/components/map/` — `MarkerLayer.vue`, `NpcMarker.vue` (:35 the
   `@click.prevent` no-op you're replacing), `StageLegend.vue` (:9-20
   hard-coded counts + `claimId`/`coverage` props),
   `CarrierMarker.vue`/`RouteOverlay.vue` (static today).
8. `docs/work-packets/reviews/README.md` — governance. Lane agents do
   not commit.

## Key design facts (verified by the coordinator; pinned — deviations come back as findings)

- **Data path:** build `src/derived/mapMarkers.ts` (pure) +
  `src/stores/mapData.ts` (thin store owning its `RunReader`) — the
  lane-11 pattern. `frameLog.ts` discards `SocialState` (:92-95,
  110-113) and is do-not-touch; your store keeps the full state.
- **Cast enumeration:** no roster record exists. Cast = union of NPC ids
  observed in the run (belief `holder_id`s in `SocialState` + trace
  participant ids). In this run: 6 NPCs.
- **NPC position:** no movement records exist; locations are static per
  run. An NPC's location = where it appears in `encounter_rolled`/
  `transmitted` records (latest observation ≤ T wins; tie-break by
  frequency). Position = the location's pixel from
  `whiterun_map.json` (its `transform` block over baked `pixel` fields,
  per ui-spec §3.1) + jitter **seeded by (npc_id, location_id)** — a
  deterministic hash offset, NOT the fixture's per-location round-robin.
- **Stage rollup:** per (npc, claim): filter `state.rumors` by
  npc+claim across variants, find the matching belief (state.beliefs
  values where holder+claim match), call `rumorStageAt`. Worst-stage
  precedence when a holder has multiple variants of one claim.
- **Active claim:** the map renders one claim at a time. This lane: the
  run's first claim is the active claim (displayed in StageLegend's
  `claimId` prop; real coverage counts). A claim picker is a later lane.
- **Glyphs:** only **S** and **N** are derivable from current
  `SocialState` — D (schedule deviation) and G (grudge) need Tier 3/4
  state the reader doesn't reconstruct. Pin: D/G never render this lane
  (the precedence list in `GlyphLegend` stays intact for when they
  arrive). N = belief formed within the current game-day (24-tick day
  boundary, ADR-0010); S = the holder told the story within the last 24
  ticks (rumor state told-gamets). Keep the precedence D ▸ G ▸ S ▸ N.
- **Names:** no name source exists — a small display helper
  (`irileth` → "Irileth", `whiterun_guard_1` → "Whiterun Guard 1").
- **Carrier/satellite/route:** schema v1 has no carrier records; the
  mock's Markarth/Ri'saad story has no real counterpart. When the run
  has no carrier state, `CarrierMarker`/`RouteOverlay`/`SatelliteNode`
  are **hidden**, not static-mock. Hide at the `MapView` mount level
  (`v-if`) — do NOT edit `SatelliteNode.vue` (lane 15's file); the
  other two you may edit only if v-if at mount level doesn't suffice.
- **Selection:** install `useSelectionUrlSync()` in MapScreen (one
  line, `FeedScreen.vue:55` precedent). `NpcMarker` click emits the NPC
  id → `selection.select(id)`; the selection ring reads
  `selection.isSelected(id)`, not `CastMember.selected`. Inspector slot
  passes the selected id into `NpcInspector`'s existing props
  (`npc-name`, `as-of-tick`) — no NpcInspector edits (FeedScreen
  :155-161 precedent).
- **MapScreen joins URL state:** it consumes `useUrlState` nowhere
  today. Wire: `useUrlState()`, single combined `watch([run, t])`
  (mind the :20-27 hazard), RunPicker `v-model` retrofit (template
  change in MapScreen — do NOT edit RunPicker.vue), and make the fake
  chrome URL chip (:37) + hard-coded run meta (:28-29) real. Docked
  LIVE (`t===null`) → `stateAtLatestKnown()`; while docked, re-run it
  on tail callbacks (the feed store's own-tailer precedent).
- **Visual parity stops being the metric here.** On real data the map
  shows 6 NPCs and no carrier story — divergence from the 26-NPC mockup
  is expected and correct. Run `npm run visual-diff` and report the
  number for information; acceptance is behavioral.

## Task

1. **`src/derived/mapMarkers.ts`** (pure): given `SocialState` + trace
   observations + the map JSON → marker models (id, display name,
   position %, stage, stage style, glyph S/N-or-null, selected flag
   from an injected predicate). Plus the per-(npc,claim) rollup, the
   seeded jitter, and the display-name helper. Unit-tested against the
   real run (the `feedReader.realRun.test.ts` precedent) + synthetic
   states.
2. **`src/stores/mapData.ts`**: load(runId) → state at t; combined
   `[run, t]` watching is the *view's* job (FeedScreen pattern) — the
   store exposes `load(runId)`, `setTick(t)`, `dockToLatest()`, status
   enum, and the current `SocialState` as `shallowRef`. Owns its
   tailer; docked → re-fold on new records.
3. **MapScreen rewiring** per the pinned facts (URL state, selection
   composable, watches, RunPicker v-model, real chrome, inspector
   props).
4. **MarkerLayer/NpcMarker**: consume the store/derived models instead
   of fixture `buildMarkers`; click → selection; ring from store.
5. **StageLegend**: real per-stage counts + active claim id + coverage
   from the store.
6. **Hide** carrier/route/satellite mounts when no carrier state (v-if
   at MapView).
7. **Tests**: derived module (real-run + synthetic); store (mocked
   reader); `MapScreen.test.ts` rewritten to the Shell.test.ts router
   pattern (memory history, stubbed fetch, flushPromises) — it
   currently mounts without a router, which stops being true. Cover:
   run loads → markers render real NPCs at map-JSON positions; scrub
   (`t` change) → markers re-derive; deep link `?sel=irileth` → ring on
   the right marker + inspector shows her; marker click → `sel` in URL;
   no-carrier run → carrier/route/satellite hidden.
8. Run `npm run visual-diff`; report the number.

## Acceptance

- `npm run build`, `npm test`, `npm run check-range` green;
  `uv run pytest -q` untouched-green (183 passed); ruff clean.
- The map renders `runs/whiterun-jarl-01`'s real cast (6 NPCs) at real
  positions with real stages at T; scrubbing T re-derives markers —
  covered by tests.
- Selection round-trips: marker click → URL `sel`; deep link → ring +
  inspector. Covered by tests.
- Stage legend shows real counts for the active claim.
- No-carrier run → carrier/route/satellite hidden. Covered by test.
- Jitter is seeded by (npc_id, location_id) — same input, same
  position, covered by test.
- No new dependencies; no edits outside File boundaries.

## File boundaries

**Create:**
- `dashboard/src/derived/mapMarkers.ts` (+ test)
- `dashboard/src/stores/mapData.ts` (+ test)

**Edit:**
- `dashboard/src/views/MapScreen.vue`, `MapView.vue`
- `dashboard/src/components/map/MarkerLayer.vue`, `NpcMarker.vue`,
  `StageLegend.vue`
- `dashboard/src/views/MapScreen.test.ts` (rewrite to router pattern)
- `dashboard/src/components/map/CarrierMarker.vue`, `RouteOverlay.vue`
  — **only** if mount-level v-if in MapView doesn't suffice

**Do not touch:**
- `SatelliteNode.vue`, `RunPicker.vue`, `streamReader.ts` (lane 15, in
  flight)
- `src/stores/frameLog.ts`, `src/log/reconstruct.ts`,
  `src/log/runReader.ts`, feed files (lanes 6/11 — findings, not edits)
- `src/fixtures/whiterunMock.ts` (still feeds TimelineBar + the mock;
  its retirement is a later lane)
- TimelineBar + `components/timeline/` (the follow-up timeline lane)
- `dashboard/map/whiterun_map.json` (read-only data)
- frozen docs; `runs/`; Python-side anything

## Conventions

- TypeScript strict; `<script setup>`; tokens from `src/styles/tokens.css`.
- **No `git commit`** — the coordinator reviews and commits.
- Existing test assertions are immutable — **one authorized exception**:
  `MapScreen.test.ts` is rewritten per Task 7 (its no-router premise is
  what this lane changes). `MapView.test.ts` and other lane-10 tests
  must keep passing unedited; if one can't, that's a finding.
- Report format: what you delivered, acceptance status per criterion
  with command tails, the visual-diff number, and a findings list.
