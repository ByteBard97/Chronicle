# Lane 38 — M5 run comparison (Track B, dashboard; ui-spec §3.9)

**Status:** Ready to start immediately (queued behind lane 35 for
sequencing). The Tier-4a design doc's sequencing note applies: the
merge-scan is testable against any two runs sharing a `seed_id` — this
lane does **not** wait on lane 36/37, though T4a.2's run pair becomes
its canonical fixture once landed.

**Effort:** medium-large (new view + derived merge-scan + tests).

## Context

The frozen spec (ui-spec §3.9, verbatim):

> Two runs (same seed_id, differing fixture/config), **aligned
> scrubbers**, three panes — but **the ranked divergence list is
> primary** (v1.1, per all three reviews): entities whose state
> differs, sorted by first-divergence tick then blast radius, each row
> narrating the counterfactual cascade and linking both maps to
> center-and-mark on click. The maps are the selection target and
> spatial context, not the primary rendering — divergence is sparse and
> entity-centric; making the user visually hunt a map for a table query
> is the wrong primary. Signed Δ tables beneath.
>
> **First-divergent-roll finder: a linear merge-scan** of the two trace
> streams for the earliest keyed roll whose value differs (not binary
> search — divergence is not monotone and nothing guarantees it),
> jumping both playheads there. T4a.2's assertion is this tool
> automated; the list is scriptable so CI can read it.

This is the dashboard's counterfactual instrument — and the tooling
twin of lane 37's T4a.2 assertion (design doc F4: **share one
definition of "outside the mourner's changed sites"** between the
scenario test and this tool).

## Read first (in order)

1. `docs/ui-spec.md` §3.9 (above) + §1.2 (`runB`/`alignment` query keys
   — already named in the frozen URL contract).
2. `docs/design/tier-4a-schedule-write-back.md` §2 (T4) — the
   roll-identity definition this tool automates (per-pair, byte-equal
   value/threshold/outcome).
3. The two demo runs (`runs/whiterun-jarl-01`, `runs/carrier-mutation-01`)
   — different seeds, so the lane's *test* fixtures come from you; the
   real-data shape comes from these.
4. `src/log/runReader.ts`, `src/stores/mapData.ts` (state-at-T),
   `src/derived/` idioms, the lane-30/31 chrome (once landed — read the
   committed files if they exist; otherwise lane 21/22's).
5. `docs/work-packets/reviews/README.md` — governance.

## Key design facts (pinned — deviations come back as findings)

- **New route `/compare`** (`CompareScreen.vue`), chrome per the other
  screens; `view=compare` in the guard; ViewSwitcher link. Run B
  selection rides the frozen `runB`/`alignment` URL keys (§1.2) —
  no new query keys.
- **The merge-scan is a pure derived module**
  (`src/derived/runCompare.ts`): two trace streams → the earliest keyed
  roll whose `value` differs (linear scan — divergence is not monotone;
  do not binary-search), the ranked divergence list (entities whose
  reconstructed state differs at T, sorted by first-divergence tick
  then blast radius), and signed-Δ tables. **The "outside the changed
  pairs" predicate must match lane 37's test helper exactly** (F4 —
  read `scenarios/test_tier4a_counterfactual.py` when it lands and
  mirror its definition; before then, implement against T4's wording
  and note the sync point in the report).
- **Ranked list primary, maps secondary** (the spec's v1.1
  strengthening): the list narrates each cascade with links that
  center-and-mark both maps; the maps are context, not the primary
  rendering.
- **Aligned scrubbers:** both panes share `t`; the finder jumps both
  playheads to the first divergent roll.
- **Test fixtures:** construct two same-seed runs for tests (a tiny
  producer or checked-in JSONL fixtures — your call; deterministic).

## Task

1. `src/derived/runCompare.ts` (+ tests: identical runs → no
   divergence; one flipped roll → found at the right tick; ranked list
   ordering; Δ signs).
2. `CompareScreen.vue` + `components/compare/` (ranked divergence list,
   Δ tables, aligned panes reusing the map at low ceremony, the
   finder button).
3. Router + guard + ViewSwitcher entries.
4. Tests incl. deep-link (`?view=compare&run=…&runB=…&t=…`) resolution.
5. Run `npm run visual-diff`; report the number (informational).

## Acceptance

- `npm run build`, `npm test`, `npm run check-range` green;
  `uv run pytest -q` untouched-green; ruff clean.
- The merge-scan finds the first divergent roll in a constructed pair
  — covered by tests; the ranked list orders per the spec.
- No new dependencies; no edits outside File boundaries.

## File boundaries

**Create:** `src/derived/runCompare.ts` (+ tests),
`src/views/CompareScreen.vue` (+ test), `src/components/compare/`

**Edit:** `src/router/index.ts`, `src/components/ViewSwitcher.vue`

**Do not touch:** landed lanes' files, `src/log/*` (read/reuse),
stores, frozen docs, `runs/` (read-only), Python

## Conventions

- TS strict; tokens only; **local commits OK** (path-scoped); never push.
- File a delivery report on disk. Report format: delivered, acceptance
  per criterion with command tails, findings list.
