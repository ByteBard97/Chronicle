# Lane 58 — M7 fix: outcome filter label/value mismatch (Track B)

**Status:** Ready to start immediately. Fixes M7 gate spec bug 5
(dossier T1.3/nothing-salient developer-twin findings) — small,
contained, independently confirmed by the coordinator
(`FeedFilterBar.vue:30,74`).

**Effort:** small.

## Context

`FeedFilterBar.vue`'s outcome `<select>` renders its dropdown *label*
with a hyphen (`o.replace("_", "-")`, e.g. "rolled-against",
"nothing-salient") but its underlying `value` — and therefore the
URL-serialized `filters` param — keeps the underscore
(`rolled_against`, `nothing_salient`). Typing the hyphenated form
visibly shown on screen into a hand-constructed URL silently returns
zero matching rows with the dropdown showing as unselected. Not a
`§1.2` pytest-emitter defect (no scenario test currently emits a
`filters=` link for these cases at all) — a plain UI internal-
consistency footgun.

## Read first

1. `docs/work-packets/reviews/2026-08-24-m7/dossier.md`'s T1.3 and
   nothing-salient sections (developer-twin sweep).
2. `dashboard/src/components/feed/FeedFilterBar.vue:30,74`.

## Task

Pick one (note which, and why):

- (a) Drop the `.replace("_", "-")` cosmetic transform — display the
  underscored form as-is, matching the value exactly; or
- (b) Keep the hyphenated display, but make filter-parsing (wherever
  the URL's `filters` param is read back into state) accept either
  form for `outcome`.

Either closes the gap; (a) is simpler and is the recommended default
absent a reason to prefer the cosmetic hyphenation.

Tests: a URL with the visibly-displayed label string round-trips to
the correct filter state (whichever form you chose to standardize on).

## Acceptance

- `npm run build`, `npm test`, `npm run check-range` green;
  `uv run pytest -q` untouched-green; ruff clean.
- The label shown in the dropdown and the value round-tripped through
  a URL agree — covered by test.

## File boundaries

**Edit:** `dashboard/src/components/feed/FeedFilterBar.vue` (+ its
test), and the URL-filter-parsing module only if approach (b) is
chosen.

**Do not touch:** everything else.

## Conventions

- TS strict; tokens only; **local commits OK** (path-scoped, atomic
  `add && commit`); never push.
- File a delivery report on disk under
  `docs/work-packets/reviews/<date>-lane-58/`.
