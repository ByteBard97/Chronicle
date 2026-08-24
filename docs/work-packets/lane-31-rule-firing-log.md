# Lane 31 — M4 rule-firing log (Track B, dashboard; ui-spec §3.7)

**Status:** Serial after **lane 30** (shares the chrome idiom it
establishes; the rule-chip link contract lands there first).

**Effort:** medium (new view + derived module + tests).

## Context

The frozen spec (ui-spec §3.7, second half):

> **Rule log:** every registry evaluation — activations with inputs
> *and* evaluated-but-not-fired rows with current accumulator values.
> Fire-frequency histogram at top (the fires-too-often detector). Rule
> chip anywhere → this log filtered to that rule.

The companion to the diff panel: the diff answers "what changed," the
log answers "what did the rules *do*" — including the negative rows
(the ladder's "a counter stuck at 3-of-4 is visible, not silent").

## Read first (in order)

1. `docs/ui-spec.md` §3.7; the M3 gate check's §2 note on the declined
   landing case (lane 30 covers it).
2. `runs/tier3-demo-01/` — the `rule_evaluated` rows: all 16 live
   rules, fired and not, `inputs` with accumulator values.
3. `docs/frame-log-schema.md` §4:122 — the record shape.
4. Lane 30's landed `DiffScreen.vue` + `components/diff/` — the chrome
   and table idioms to mirror (read the committed files, not this
   packet's imagination of them).
5. The feed store's trace-paging idiom (`src/stores/feed.ts`,
   `src/log/feedReader.ts`) — the log pages the trace stream the same
   way, filtered to `rule_evaluated`.
6. `docs/work-packets/reviews/README.md` — governance.

## Key design facts (pinned)

- **New route `/rules`** (`RuleLogScreen.vue`), chrome per lane 30;
  `view=rules` in the guard; ViewSwitcher link.
- **Derived module** `src/derived/ruleLog.ts` (pure): trace records →
  log rows (rule, tick, fired, inputs summary, result summary) +
  per-rule fire-frequency histogram data (fires per rule over the
  window — the fires-too-often detector; show fired vs.
  evaluated-not-fired counts side by side).
- **The negative rows are first-class** (equal visual weight, per
  ui-doctrines): `fired: false` rows show the current accumulator
  values from `inputs` (e.g. "3/4 thefts"), not a blank.
- **Filter by rule** (dropdown + urlState `filters`) — and the
  deep-link contract: `?view=rules&filters={"rule":"<name>"}` is what
  lane 30's rule chips target.
- **Trace paging** per the feed idiom (sidecar `tick_offsets` + Range
  reads; own store, `feed.ts` pattern).

## Task

1. `src/derived/ruleLog.ts` (+ tests: row mapping, accumulator display,
   histogram bucketing; real-run against `tier3-demo-01`).
2. `RuleLogScreen.vue` + `components/rulelog/` (histogram strip, table,
   rule filter). <500 lines/file.
3. Router + guard + ViewSwitcher entries.
4. Tests: deep link filtered to a rule lands correct; negative rows
   render accumulator values; histogram counts match the real run.
5. Run `npm run visual-diff`; report the number (informational).

## Acceptance

- `npm run build`, `npm test`, `npm run check-range` green;
  `uv run pytest -q` untouched-green; ruff clean.
- The log renders all 16 rules' evaluations from `tier3-demo-01`,
  fired and not, with accumulator values — covered by tests.
- The rule-chip link contract works end-to-end (lane 30's chips →
  filtered log), covered by a test once both lanes exist.
- No new dependencies; no edits outside File boundaries.

## File boundaries

**Create:** `src/derived/ruleLog.ts` (+ tests),
`src/views/RuleLogScreen.vue` (+ test), `src/components/rulelog/`

**Edit:** `src/router/index.ts`, `src/components/ViewSwitcher.vue`

**Do not touch:** landed lanes' files, `src/log/*` (read/reuse),
stores, frozen docs, `runs/`, Python

## Conventions

- TS strict; tokens only; **local commits OK** (path-scoped); never push.
- File a delivery report on disk.
- Report format: delivered, acceptance per criterion with command
  tails, findings list.
