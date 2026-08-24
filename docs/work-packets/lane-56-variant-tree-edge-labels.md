# Lane 56 — M7 fix: variant tree edge-label rendering (Track B)

**Status:** Ready to start immediately. Fixes M7 gate spec bug 3
(dossier step 4, "FAIL" — "the worst thing found in the whole
walkthrough").

**Effort:** small-medium (rendering-logic fix; the underlying data is
already correct).

## Context

`/tree`'s rendered page is dominated by hundreds of overlapping copies
of the same edge-label string (e.g. `"evidence-type-ordering+v1 (dent
0.1)"`), stacked diagonally and completely illegible. The underlying
data is correct — each variant node's tooltip/accessible name (e.g.
`"weapon: a dagger → a poisoned blade (mut-...)"`) is right, just not
reachable by a sighted human through the broken rendering. Violates
ui-spec §0's renderer-split doctrine ("SVG for panels, labels,
tooltips... no SVG-per-marker past ~1,000") — labels are clearly not
being deduplicated or laid out per edge.

## Read first

1. `docs/work-packets/reviews/2026-08-24-m7/dossier.md` step 4 and
   screenshots `10-tree-view.png` / `11-tree-variant9-holders.png`.
2. `docs/ui-spec.md` §0 (renderer-split doctrine) and §3.5 (variant
   tree).
3. The variant tree view's rendering module (from lane 21's landed
   work — find the SVG edge-label rendering code specifically).

## Task

1. Find why edge labels are rendering many overlapping times at a
   fixed origin instead of once, positioned near their own edge (a
   layout bug — likely a missing per-edge offset/key, or a loop
   re-rendering the same label for every generation level rather than
   once per edge).
2. Fix so each edge's label renders exactly once, positioned near its
   own edge.
3. Tests: a tree with N edges renders exactly N edge-label elements
   (not N² or unbounded); an existing multi-generation fixture
   (north-star-01-shaped, several variants) is the regression case.

## Acceptance

- `npm run build`, `npm test`, `npm run check-range` green;
  `uv run pytest -q` untouched-green; ruff clean.
- Edge-label count matches edge count exactly for a multi-variant
  fixture — covered by test.
- Live-verify against `runs/north-star-01`'s `/tree` view if you can
  (the dossier's screenshot is the before-state to compare against).

## File boundaries

**Edit:** the variant-tree view's rendering module/component only.

**Do not touch:** frozen docs, `runs/`, Python, the tree's data-layer
(`derived/` variant-tree-building logic) unless the bug turns out to
be there rather than in rendering — report as a finding first if so.

## Conventions

- TS strict; tokens only; **local commits OK** (path-scoped, atomic
  `add && commit`); never push.
- File a delivery report on disk under
  `docs/work-packets/reviews/<date>-lane-56/`.
