# Lane 54 — M7 fix: promote the timeline to global chrome (Track B)

**Status:** Ready to start immediately. Fixes M7 gate spec bug 1
(`docs/work-packets/reviews/2026-08-24-m7/dossier.md` step 1, "FAIL").

**Effort:** medium (layout change touching every view's shell, not a
one-file fix).

## Context

The stranger walkthrough's step 1 ("find the assassination on the
timeline") failed: the timeline (playhead, play/pause, speed presets,
typed event markers — ui-spec §2's global chrome) currently only
renders on `/map`. Every other view (`/`, `/feed`, `/tree`, `/diff`,
`/rules`, `/compare`, `/scheddiff`, `/roles`) shows only a bare tick
spinbutton. The dossier found it three navigation hops deep from the
landing view, with no "timeline" label anywhere in the nav — a real
stranger has no cue where to look.

ui-spec §2 already describes the timeline as global chrome, not a
map-specific feature — this lane implements that existing intent, it
does not change frozen spec text.

## Read first

1. `docs/ui-spec.md` §2 (global chrome, verbatim).
2. `docs/work-packets/reviews/2026-08-24-m7/dossier.md` step 1 (the
   failure) and screenshots `01-landing-console.png` /
   `12-map-variant9.png`.
3. Whatever component currently renders the timeline on `/map` (find
   it — likely `MapScreen.vue` or a child) and the shell/layout
   component every view mounts inside (`Shell.vue`, `App.vue`, or
   equivalent router-outlet wrapper).

## Task

1. Extract the timeline component (if it isn't already one) and mount
   it in the shared shell so every route renders it, not just `/map`.
2. It must stay fully functional off the map view (scrub, play/pause,
   speed presets, typed markers) — reuse the existing implementation,
   don't rebuild it.
3. Add a "timeline" label somewhere discoverable in the persistent
   chrome (not necessarily a new nav tab — the timeline itself being
   always-visible chrome may satisfy this; use judgment, note your
   choice).
4. Tests: the timeline renders and is interactive on at least one
   non-map view; existing map-view timeline tests stay green.

## Acceptance

- `npm run build`, `npm test`, `npm run check-range` green;
  `uv run pytest -q` untouched-green; ruff clean.
- The timeline is visible and functional from the landing view
  (`/?run=...`) without navigating to `/map` first — covered by test.
- No regression to `/map`'s existing timeline behavior.

## File boundaries

**Edit:** the shared shell/layout component, the timeline component
(wherever it currently lives), `MapScreen.vue` (only to remove a now-
duplicate mount if it moves to the shell), router if a nav label needs
adding.

**Do not touch:** frozen docs, `runs/`, Python, other views' own
internals beyond what's needed to remove a duplicate timeline mount.

## Conventions

- TS strict; tokens only; **local commits OK** (path-scoped, atomic
  `add && commit`); never push.
- File a delivery report on disk under
  `docs/work-packets/reviews/<date>-lane-54/`.
