# Lane 41 — M5 schedule diff (Track B, dashboard; ui-spec §3.8)

**Status:** Ready to start immediately (queued behind lanes 35/38 for
sequencing). Substrate landed: lane 36's `schedule_rewrite` events and
`effective_schedule_at` replay (state-at-T now reflects overlays), lane
34's layer-4 reader.

**Effort:** medium (new view/panel + derived module + tests).

## Context

The frozen spec (ui-spec §3.8):

> Before/after lanes per NPC, inserted/removed blocks highlighted,
> causing rule and event linked. Lives in the inspector's Schedule tab
> and as a standalone multi-NPC comparison.

The schedule diff is the visible-half of Tier 4a: *the mourner's days
got rerouted — see exactly which blocks changed, and which rule/event
did it.* The inspector's Schedule tab is currently a "not wired yet"
placeholder (lane-28 note); this lane fills it AND builds the
standalone comparison.

## Read first (in order)

1. `docs/ui-spec.md` §3.8, §2 (selection), §1.2 (deep links).
2. `docs/frame-log-schema.md` §3:96 — the `schedule_rewrite` fields
   (`npc_id`, `location_id`, `start_tick`/`end_tick`, `cause`,
   `trigger_event_key`, `rule`).
3. Lane 36's landed code: `chronicle/schedule.py`'s
   `effective_schedule_at` (the semantics the dashboard mirrors:
   base blocks + total override for overlaid NPCs) and
   `chronicle/framelog.py`'s replay branch.
4. `dashboard/src/log/reconstruct.ts` — does the dashboard's
   reconstruction carry schedule/overlay state yet? (Lane 34's layer-4
   work added relationships/grudges/obligations/reputations; schedule
   handling may still be keyframe-static — verify and note. If the
   dashboard lacks schedule-at-T, the derived module computes
   effective presence from base blocks + `schedule_rewrite` records
   directly, mirroring the Python helper.)
5. `dashboard/src/components/NpcInspector.vue` — the Schedule tab
   placeholder you'll fill.
6. `docs/work-packets/reviews/README.md` — governance.

## Key design facts (pinned — deviations come back as findings)

- **Data:** schedule/overlay truth comes from the run's base schedule
  (keyframes) + `schedule_rewrite` events (the events stream) — NOT
  re-derived. The before/after lanes for an NPC: their base blocks,
  with inserted blocks highlighted (from `schedule_rewrite`) and
  overlaid-away spans marked. If the dashboard's reconstruction doesn't
  carry schedules yet, extend `reconstruct.ts`'s schedule handling in
  the same replay idiom (in-bounds here) — do NOT invent a second
  presence computation in the view layer.
- **The causal link is the point:** each inserted block links its
  `schedule_rewrite` event (tick, cause, `trigger_event_key`) and the
  firing `rule` — per the spec's "causing rule and event linked."
- **Two hosts, one component:** the inspector's Schedule tab (selected
  NPC, per ui-spec §3.8) and a standalone multi-NPC comparison (new
  route `/scheddiff`, chrome per the other screens; `view=scheddiff`
  guard entry; ViewSwitcher link).
- **As-of-T:** lanes render the schedule at the playhead's T;
  scrubbing moves the before/after boundary.
- **Test data:** no demo run contains `schedule_rewrite` yet — construct
  fixtures from the lane-36 rung pattern (a two-NPC, one-mourning
  fixture run; a checked-in JSONL fixture is fine). A mourning demo
  run is a separate producer follow-up (note it as a finding if the
  fixtures feel thin).

## Task

1. `src/derived/scheduleDiff.ts` (pure): base + rewrite records →
   per-NPC before/after lane models (inserted blocks, overlaid spans,
   the causal links). Tests incl. the lane-36 semantics (total
   override, automatic restoration past `end_tick`).
2. `components/scheddiff/ScheduleLanes.vue` (+ sub-components): the
   before/after lane rendering with inserted/removed highlights and
   the rule/event links.
3. Fill the inspector's Schedule tab (selected NPC) + the standalone
   `/scheddiff` route (multi-NPC, filterable).
4. Router + guard + ViewSwitcher entries; tests (derived + view +
   deep-link).
5. Run `npm run visual-diff`; report the number (informational).

## Acceptance

- `npm run build`, `npm test`, `npm run check-range` green;
  `uv run pytest -q` untouched-green; ruff clean.
- Inserted blocks and their causing rule/event render linked — covered
  by tests; restoration past `end_tick` renders correctly.
- Both hosts work (inspector tab + standalone), covered by tests.
- No new dependencies; no edits outside File boundaries.

## File boundaries

**Create:** `dashboard/src/derived/scheduleDiff.ts` (+ tests),
`dashboard/src/components/scheddiff/`,
`dashboard/src/views/SchedDiffScreen.vue` (+ test)

**Edit:** `dashboard/src/components/NpcInspector.vue` (Schedule tab
only), `dashboard/src/router/index.ts`,
`dashboard/src/components/ViewSwitcher.vue`,
`dashboard/src/log/reconstruct.ts` (**only** if schedule-at-T is
missing — finding first if so)

**Do not touch:** landed lanes' other files, `src/log/*` (beyond the
conditional reconstruct edit), stores, frozen docs, `runs/`, Python

## Conventions

- TS strict; tokens only; **local commits OK** (path-scoped); never push.
- File a delivery report on disk. Report format: delivered, acceptance
  per criterion with command tails, findings list.
