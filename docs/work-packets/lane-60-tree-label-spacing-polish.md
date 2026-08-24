# Lane 60 — variant tree: residual cross-link label spacing polish (Track B, optional)

**Status:** Ready to start immediately. **Not gate-blocking** — this is
a follow-on polish item, not a fix for a filed spec bug. Lane 56
(accepted, `d7f61eb`) fixed the severe illegible-overlapping-labels
defect; both the combined spot-check (board, lane 54/56/57 row) and
the lane-59 formal re-run dossier independently noted the same minor
residual issue afterward: "some remaining cross-link labels are a bit
tight" / "residual visual crowding remains among the
`evidence-type-ordering+v1 (dent 0.1)` labels near variant-auto-7/8/9
... does not obscure the primary mutation-slot answer." Both explicitly
said this does not rise to gate-blocking.

**Effort:** small. Skip this lane entirely if you have higher-value
work queued — it's genuinely optional.

## Context

Lane 56 fixed the *illegible* case (hundreds of stacked duplicate
labels). What's left is a smaller layout-quality issue: when several
distinct `(fromId, toId, resolutionRule, confidenceDent)` groups land
close together in the tree's generational layout, their aggregated
labels can still crowd each other — tight, not overlapping-to-
illegibility.

## Read first

1. `docs/work-packets/reviews/2026-08-24-lane-56/overseer-review.md`
   and `2026-08-24-lane-59/dossier.md` (step 4) for exactly what was
   observed.
2. `dashboard/src/components/tree/TreeSvg.vue` (lane 56's landed fix).

## Task

Improve label placement so nearby aggregated cross-link labels don't
crowd each other — e.g. a small perpendicular offset when two labels'
bounding boxes would overlap, or a minimum-gap nudge along the shared
axis. Use whatever approach fits the existing layout code most
naturally; this is a quality nudge, not a rewrite. Add a test
asserting a minimum gap between any two rendered label bounding boxes
for a fixture with several close-together groups (`runs/north-star-01`
is a real case with this shape).

## Acceptance

- `npm run build`, `npm test`, `npm run check-range` green;
  `uv run pytest -q` untouched-green; ruff clean.
- No two rendered cross-link labels' bounding boxes overlap for a
  multi-group fixture — covered by test.
- The already-fixed illegible case (lane 56) has no regression.

## File boundaries

**Edit:** `dashboard/src/components/tree/TreeSvg.vue` (+ its test)
only.

**Do not touch:** everything else, including `derived/variantTree.ts`.

## Conventions

- TS strict; tokens only; **local commits OK** (path-scoped, atomic
  `add && commit`); never push.
- File a delivery report on disk under
  `docs/work-packets/reviews/<date>-lane-60/`.
