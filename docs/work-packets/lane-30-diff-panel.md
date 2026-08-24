# Lane 30 — M4 diff panel (Track B, dashboard; ui-spec §3.7)

**Status:** Ready to start immediately. Substrate: `runs/tier3-demo-01`
(all five Tier-3 record types, lane 29), lanes 6/11/14/21/22's idioms,
`mapData.ts` shareable (lane-21 review precedent). This is the first of
two M4 lanes; lane 31 (rule-firing log) follows.

**Effort:** medium-large (new view + derived module + tests).

## Context

The frozen spec (ui-spec §3.7, first half):

> **Diff panel:** T₁/T₂ (default playhead vs. one game-day earlier);
> every social-state delta with signed Δ, firing-rule chip,
> triggering-event link. Filter by NPC/rule/type.

The diff panel is the Tier-3 answer to "what changed, and which rule
did it" — over the full social state (beliefs/stages, grudges,
obligations, reputation), not just the claims layer.

## Read first (in order)

1. `docs/ui-spec.md` §3.7 (full section — the rule log is lane 31, but
   the rule-chip-link contract binds them), §1.2 (`t`, deep links).
2. `runs/tier3-demo-01/` — sample the `rule_evaluated` rows (fired and
   not), `grudge_formed`, `reputation_updated`, `threshold_crossed`.
3. `dashboard/src/stores/mapData.ts` — `stateAt` usage; you'll need
   state at **two** ticks (T₁ = playhead, T₂ = T₁ − 24).
4. `dashboard/src/log/reconstruct.ts` — the `SocialState` shape incl.
   layer-4 (grudges/obligations/reputation Maps).
5. `src/derived/rumorStage.ts` + `decay.ts` — stage/strength-at-T
   helpers (deltas compare derived-at-T values, not raw stored ones).
6. The lane-22 panel idiom (`components/drilldown/`,
   `panelUrlState.ts`) and the lane-21/14 store-reuse pattern.
7. `docs/work-packets/reviews/README.md` — governance.

## Key design facts (pinned — deviations come back as findings)

- **New route `/diff`** (`DiffScreen.vue`), chrome per the other
  screens; `view=diff` in the router guard; ViewSwitcher link.
- **Derived module** `src/derived/socialDiff.ts` (pure): two
  `SocialState`s + the trace records in (T₂, T₁] → typed delta rows
  (belief confidence/stage changes, new/lost beliefs, grudge
  formed/decayed-crossing, obligation transitions, reputation moves).
  Each row: signed Δ, the NPC, the type, the **rule chip** (matched
  from `rule_evaluated` rows in the window — by rule name), and the
  **triggering-event link** (the event/record key, deep-linkable to the
  feed at that tick).
- **T₂ default = T₁ − 24** (one game-day, ADR-0010); both editable
  (typed tick entry, urlState-backed — `t` is T₁; T₂ is view-local or
  in `filters` — pick one and note it).
- **Filter by NPC/rule/type** — urlState `filters` (existing codec).
- **Deltas compare derived-at-T values** (decay-adjusted), so a quiet
  day shows real decay, not just events — that's the point of the
  panel. Document the semantics in the module header.
- **Rule chips link to the rule log filtered to that rule** — lane 31's
  route (`/rules?filters={"rule":"..."}`); implement the link target
  against the planned route even before lane 31 lands (it 404s until
  then — acceptable, noted).
- **Fold in the M3 carry-forward:** an explicit automated landing-case
  test for the **T3.4 declined-by-rule deep link** against
  `tier3-demo-01` (deep link → declined row visible, rule name readable
  without scrolling) — the gate check's one deferred item.

## Task

1. `src/derived/socialDiff.ts` (+ tests: synthetic two-tick states —
   each delta type, signed values, rule matching, decay-only day; plus
   a real-run test against `tier3-demo-01` at a pinned window).
2. `DiffScreen.vue` + `components/diff/` (delta table, T₁/T₂ controls,
   filter bar, rule chips, event links). <500 lines/file.
3. Router + guard + ViewSwitcher entries.
4. Tests incl. the T3.4 landing case (above), deep-link resolution
   (`?view=diff&t=…&filters=…`), and filter behavior.
5. Run `npm run visual-diff`; report the number (informational).

## Acceptance

- `npm run build`, `npm test`, `npm run check-range` green;
  `uv run pytest -q` untouched-green (205+); ruff clean.
- The panel shows real two-tick deltas from `tier3-demo-01` with signed
  Δs, rule chips, and event links — covered by tests.
- The T3.4 declined landing case passes as an automated test (the M3
  gate's carry-forward).
- No new dependencies; no edits outside File boundaries.

## File boundaries

**Create:** `src/derived/socialDiff.ts` (+ tests),
`src/views/DiffScreen.vue` (+ test), `src/components/diff/`

**Edit:** `src/router/index.ts`, `src/components/ViewSwitcher.vue`

**Do not touch:** landed lanes' files (map/feed/timeline/tree/
drilldown components; `src/log/*`; stores — read/reuse, findings only),
frozen docs, `runs/`, Python

## Conventions

- TS strict; tokens only; **local commits OK** (path-scoped); never push.
- File a delivery report on disk (the coordinator's standing note).
- Report format: delivered, acceptance per criterion with command
  tails, findings list.
