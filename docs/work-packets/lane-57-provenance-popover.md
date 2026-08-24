# Lane 57 — M7 fix: provenance popover positioning + mutation narration (Track B)

**Status:** Ready to start immediately. Fixes M7 gate spec bug 4
(dossier step 5, "FAIL").

**Effort:** small-medium.

## Context

The provenance drill-down popover (lane 22) has two problems the
dossier found: (a) it renders pinned to a fixed screen corner
(top-right) instead of anchored near the clicked "drill" affordance,
and (b) its content is thin — a compressed retelling chain with
confidence numbers, but no inline callout of the mutation event
(slot/old value/new value) that makes the belief wrong. A stranger
following step 5 ("drill provenance from belief to dagger through the
mutation") using only this popover cannot get from "belief" to
"dagger" through "the mutation" in one place — that information
currently only lives in the separate tree view (lane 56).

## Read first

1. `docs/work-packets/reviews/2026-08-24-m7/dossier.md` step 5 and
   screenshot `09-drill-provenance.png`.
2. `docs/ui-spec.md` §3.6 (the drill-down's spec).
3. The provenance popover component (lane 22's landed work).

## Task

1. **Positioning:** anchor the popover near the invocation point (the
   clicked "drill" button/row), not a fixed screen corner. Use
   whatever positioning approach the codebase already uses elsewhere
   for anchored popovers/tooltips if one exists; if not, a simple
   relative-to-trigger-element position is enough — this doesn't need
   a floating-UI library dependency (no new deps, per every other
   lane's constraint).
2. **Content:** extend the chain narration to surface the mutation
   event inline where it occurs in the chain — slot name, old value,
   new value (the same data the tree view already has, e.g.
   `mutation_applied`'s payload) — not just confidence numbers per
   hop.
3. Tests: the popover renders near a known trigger position (not at a
   fixed corner regardless of trigger); a chain containing a mutation
   shows the slot/old/new inline.

## Acceptance

- `npm run build`, `npm test`, `npm run check-range` green;
  `uv run pytest -q` untouched-green; ruff clean.
- Popover position test passes for at least two different trigger
  positions (proving it's relative, not fixed).
- A mutation-containing chain's inline slot/old/new is covered by
  test.

## File boundaries

**Edit:** the provenance popover component (lane 22's), its styling.

**Do not touch:** frozen docs, `runs/`, Python, the tree view (lane
56 owns that fix; don't duplicate the mutation-narration logic there —
a small shared helper is fine if natural, but don't restructure lane
21/56's tree module from this lane).

## Conventions

- TS strict; tokens only; **local commits OK** (path-scoped, atomic
  `add && commit`); never push.
- File a delivery report on disk under
  `docs/work-packets/reviews/<date>-lane-57/`.
