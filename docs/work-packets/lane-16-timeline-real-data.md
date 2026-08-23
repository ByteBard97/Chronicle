# Lane 16 — TimelineBar → real data (Track B, dashboard; M3 timeline)

**Status:** Depends on **lane 14 landed** (the map's `t`/selection
wiring — this lane's playhead binds the same `urlState.t`; starting
early guarantees a mid-flight collision). Lane 15 disjoint. Lane 17
(mutation+carrier demo run) is *not* blocking — the widget works on
today's run; richer marker types just have no data until then.

**Effort:** medium-large (widget rewiring + derived module + tests).

## Context

The M3 milestone's timeline piece (build-plan §M3: "Timeline widget
(typed event markers, heat-stripe degradation, LIVE dock)"). Today
`TimelineBar.vue:13-18,32` is fixture-driven (`buildEvents`,
`DAY_TICKS`, `LIVE_STATES` from `whiterunMock.ts`). After this lane the
timeline renders the selected run's real event/trace streams.

The frozen spec (ui-spec §2:59, verbatim):

> At Tier 2 it grows into **the timeline**: playhead; play/pause; speed
> presets (¼×–8×, shown as multipliers, never tick rates); segment
> stepping at game-day and schedule-block boundaries; ±1 day skip;
> **typed event markers striped on the bar** — claim born, mutation,
> supersession, grudge formed, threshold crossed, role vacancy, carrier
> arrival — clickable, type-filterable, degrading to a heat stripe when
> dense. LIVE dock at the right end when tailing.

## Read first (in order)

1. `docs/ui-spec.md` §2:59 (above), §1.2 URL contract (`t` is the
   playhead; history mode 'replace'), §0:16 (as-of-T everywhere).
   Frozen — findings to the coordinator.
2. `dashboard/src/components/timeline/` — `TimelineBar.vue`,
   `TimelineTrack.vue` (:12-17 — takes events/days/live/docked props
   with pre-computed percents; **good boundary, keep it**),
   `TransportControls.vue`, `LiveDockPill.vue`, `TimelineLegend.vue`.
3. `src/stores/liveDock.ts` — dock/detach semantics + the frozen docked
   status string.
4. `src/state/urlState.ts` — `t` codec (:98-110) and history modes
   (:222-232).
5. The lane-11/14 idioms: `src/derived/` pure modules + thin stores;
   `FeedScreen.vue`'s urlState consumption. For marker derivation, the
   run's streams: `src/log/runReader.ts`, `types.ts` (trace + event
   record unions).
6. `runs/whiterun-jarl-01` — today's real marker data: `belief_formed`
   (1), `mutation_applied` (0), `supersession` (0), `grudge_formed`
   (0), `threshold_crossed` (0); `npc_died`/`crime_witnessed` in
   events. Marker types with zero records render as an active-but-empty
   legend entry, not an error.
7. `docs/work-packets/reviews/README.md` — governance. Lane agents do
   not commit.

## Key design facts (pinned — deviations come back as findings)

- **Marker taxonomy → record mapping (pinned):** claim born =
  `belief_formed` (first per claim); mutation = `mutation_applied`;
  supersession = `supersession`; grudge formed = `grudge_formed`;
  threshold crossed = `threshold_crossed`. **Role vacancy** (Tier 5)
  and **carrier arrival** (no schema v1 record; deriving it from
  location transitions is fuzzy) are registry entries with no producer
  yet — the type registry is built so adding them is config, and the
  gap is a named finding, not improvised derivation. Canonical events
  from the events stream (`npc_died`, `crime_witnessed`) are *event*
  markers — include them as a distinct "events" type; the spec's
  taxonomy is trace-derivation-flavored but the bar is an event index
  first (ui-doctrines: "the scrubber is an event index, not a position
  control").
- **Segment stepping = game-day boundaries only.** Schedule-block
  boundaries need schedule data the log doesn't carry dashboard-side —
  game-day stepping (24-tick boundaries, ADR-0010) only; the
  schedule-block gap is a named finding.
- **Play speed:** 1× = 1 tick/second (one game-day per 24s), presets
  ¼×–8×, **shown as multipliers** (never tick rates). Playing advances
  `urlState.t` (so every view follows — that's the point of the
  playhead being URL state); pause on any manual `t` edit.
- **Marker click** → `urlState.t = marker.tick` ('replace' mode — no
  history spam). **Type filter is view-local UI state** (not URL;
  salience-adjacent but not the salience store).
- **Heat stripe:** when markers-per-pixel exceed 1, bucket to a density
  stripe (pure function: markers + bar width → either individual
  markers or buckets with counts). Deterministic; test both regimes.
- **TimelineTrack's props boundary stays** — the parent computes
  percents; the track renders. The fixture's timeline layer
  (`EVENTS`/`buildEvents`/`DAY_TICKS`/`LIVE_STATES`) is superseded for
  the component path but **the fixture file is not edited** (its
  retirement is a later lane; the visual-diff mock still uses it).
- **Span:** [0, run's max tick]; day labels from 24-tick days. LIVE
  dock at the right end per the existing `liveDock` store + frozen
  status string.

## Task

1. **`src/derived/timelineMarkers.ts`** (pure): records (events +
   trace) → typed markers (`{tick, type, label, pos}`), day-tick
   boundaries from the run's range, heat-stripe bucketing. Unit-tested
   against the real run + synthetic records for the zero-data types.
2. **Rewire `TimelineBar.vue`**: consume the run's streams (via the
   lane-14 map store's run/tick state — read, don't re-own; if lane 14
   landed a shared run store, use it) and `urlState.t`; replace fixture
   imports.
3. **Play/pause + speed presets + ±1 day skip + day stepping** in
   `TransportControls.vue` — all writing `urlState.t` per the pinned
   semantics.
4. **Type filter + clickable markers** in `TimelineTrack.vue` (keep the
   percents-in boundary; filter state in TimelineBar).
5. **Tests**: derived module (mapping, buckets, day boundaries, all
   marker types incl. synthetic `mutation_applied`/`supersession`/
   `grudge_formed` records); component tests (marker click → `t`;
   filter hides/shows types; play advances `t` at 1 tick/s scaled by
   preset — fake timers; pause on manual edit; dock pill renders the
   frozen status string when docked).
6. Run `npm run visual-diff`; report the number (informational — the
   timeline now shows real data, mock parity is not the metric).

## Acceptance

- `npm run build`, `npm test`, `npm run check-range` green;
  `uv run pytest -q` untouched-green; ruff clean.
- The timeline renders the real run's markers (claim born + events
  today; the full taxonomy render-ready); zero-data types don't error.
- Marker click, type filter, play/pause/speed/step/skip, and LIVE dock
  all covered by tests; playhead is `urlState.t` throughout.
- Heat stripe appears only when dense (tested both regimes).
- No new dependencies; no edits outside File boundaries.

## File boundaries

**Create:**
- `dashboard/src/derived/timelineMarkers.ts` (+ test)

**Edit:**
- `dashboard/src/components/timeline/TimelineBar.vue`,
  `TimelineTrack.vue`, `TransportControls.vue`,
  `TimelineLegend.vue` (+ their tests — lane-10 tests asserting fixture
  content are the one authorized rewrite class, since the fixture
  premise is what this lane changes; behavior assertions on props
  boundaries must be preserved)
- `dashboard/src/views/MapScreen.vue` — **only** if the TimelineBar
  slot needs prop changes after lane 14 lands (coordinate against the
  landed lane-14 shape; report what you find)

**Do not touch:**
- `src/stores/frameLog.ts`, `src/stores/mapData.ts`, feed files,
  `src/log/*` (read, don't extend — findings)
- `src/fixtures/whiterunMock.ts` (retirement is a later lane)
- map components (lane 14's landed territory)
- frozen docs; `runs/`; Python-side anything

## Conventions

- TypeScript strict; `<script setup>`; tokens from `src/styles/tokens.css`.
- **No `git commit`** — the coordinator reviews and commits.
- Existing test assertions immutable except the Task-5 class above;
  conflicts are findings.
- Report format: what you delivered, acceptance status per criterion
  with command tails, the visual-diff number, and a findings list
  (expected: the schedule-block-stepping gap; role-vacancy and
  carrier-arrival producer gaps).
