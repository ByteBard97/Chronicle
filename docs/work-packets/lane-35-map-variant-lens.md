# Lane 35 — map variant lens (Track B, dashboard; lane-21 follow-up)

**Status:** Ready to start immediately (or queued behind M4 lanes —
  coordinator's sequencing call at dispatch). The last deferred item
  from the M3 wave: ui-spec §3.5's "node click → holder table **+ map
  overlay switches to this variant**." Lane 21 shipped the holder table;
  this is the map half.

**Effort:** small-medium.

## Context

The variant tree's node click currently opens the holder table. The
spec's second half: the *map* responds — its overlay switches from the
claim-level rumor lens to the selected variant, so you see **who holds
this variant** (and who holds a superseded one) spatially. The
substrate is all landed: `mapData.ts` (state-at-T with beliefs by
`variant_id`), the selection/urlState machinery, lane 14's marker
styling.

## Read first (in order)

1. `docs/ui-spec.md` §3.5 (the node-click contract) and §3.1 (overlay
   layers, one active at a time, the lens selector naming the lens).
2. `dashboard/src/views/VariantTreeScreen.vue` + `components/tree/` —
   the landed node-click → holder-table path (read the committed code).
3. `dashboard/src/stores/mapData.ts` + `src/derived/mapMarkers.ts` —
   how markers get stage/style today (the claim-level lens).
4. `dashboard/src/state/urlState.ts` — the frozen key list (`sel`,
   `filters`) you must express variant selection within.
5. `docs/work-packets/reviews/README.md` — governance.

## Pinned implementation decisions

- **Variant selection rides the existing URL keys** — a variant id in
  `sel` (it's an entity) or `filters={"variant": ...}`; verify which
  reads more honestly against the codecs and note the choice. **No new
  query keys** (§1.2 is frozen).
- **The variant lens:** with a variant selected, markers style by
  relationship to that variant — holds-it (full stage style),
  holds-a-different-variant (dimmed/contrasted per tokens),
  holds-none (the existing "unheard" gray). The lens selector names it
  ("variant: <label>") — the claim-level rumor lens remains the
  default; this is a transient lens driven by tree selection.
- **Tree → map navigation:** node click also offers "view on map" —
  link to `/map` with the selection in the URL (deep-link law: every
  view state serializes).
- **As-of-T holds:** the lens reflects variant holding at the
  playhead's T, via `mapData`'s state.

## Task

1. Derived logic (extend `mapMarkers.ts` or a sibling module): markers
   for the variant lens + tests (synthetic + real-run
   `carrier-mutation-01`, which has multi-variant holding post-lane-27).
2. Map side: the lens rendering + selector label.
3. Tree side: the "view on map" affordance from a node (link with
   serialized state).
4. Tests: lens styling per holding class; scrubbing updates holding;
   the tree→map link lands with the lens active.
5. Run `npm run visual-diff`; report the number (informational).

## Acceptance

- `npm run build`, `npm test`, `npm run check-range` green;
  `uv run pytest -q` untouched-green; ruff clean.
- Selecting a variant in the tree and following the map link shows the
  variant lens with correct per-marker classes — covered by tests.
- No new query keys; no new dependencies; no edits outside boundaries.

## File boundaries

**Edit:** `dashboard/src/derived/mapMarkers.ts` (or sibling),
`dashboard/src/views/MapView.vue` / `MarkerLayer.vue`,
`dashboard/src/views/VariantTreeScreen.vue` (the affordance),
`src/state/urlState.ts` (**only** if a codec gap is found — finding
first)

**Do not touch:** `src/log/*`, other landed views/components, lane
30/31/34 files (M4 in flight), frozen docs, `runs/`, Python

## Conventions

- TS strict; tokens only; **local commits OK** (path-scoped); never push.
- File a delivery report on disk. Report format: delivered, acceptance
  per criterion with command tails, findings list.
