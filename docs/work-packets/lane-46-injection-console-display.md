# Lane 46 — InjectionConsole: display the writing inject form (Track B, small)

**Status:** Ready to start immediately; small filler. Backlog from the
13:23 handoff: `InjectionConsole.vue` still shows the compose-only
inject string, but the CLI's `inject` **writes** at LIVE (and refuses
historical ticks, pointing at the deferred fork milestone). The console
should show the real invocation.

**Effort:** small.

## Context

Lane 9 built the console's CLI-invocation display against the
compose-only form; the merged CLI (commit `870c6ea`) landed the writing
form afterward. The console is stale relative to the tool it teaches.

## Read first

- `dashboard/src/components/InjectionConsole.vue` — the current
  invocation display (lane 9's work).
- `chronicle/cli.py` — `inject`'s actual flags and semantics (writes at
  LIVE; refuses historical ticks; the fork pointer).
- `docs/ui-spec.md` §3.1 (the console's spec + fork semantics —
  frozen; findings only).
- `docs/work-packets/reviews/README.md` — governance.

## Task

1. Update the displayed CLI invocation to the writing form (exact flags
   per the CLI), including the LIVE-only note (historical-tick refusal
   → fork milestone pointer).
2. Keep the compose-only string if it documents something the writing
   form doesn't (read the two and decide; note the choice).
3. Tests: the displayed string matches the CLI's real flags (a
   string-level test against a canonical form — the lane-9 precedent
   for matching flags exactly).

## Acceptance

- `npm run build`, `npm test`, `npm run check-range` green;
  `uv run pytest -q` untouched-green; ruff clean.
- The displayed invocation matches `chronicle inject --help`'s actual
  interface (verified in the report).

## File boundaries

**Edit:** `dashboard/src/components/InjectionConsole.vue` (+ its test)

**Do not touch:** everything else.

## Conventions

- TS strict; tokens only; **local commits OK** (path-scoped); never push.
- File a delivery report on disk.
