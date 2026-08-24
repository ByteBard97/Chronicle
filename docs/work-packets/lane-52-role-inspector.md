# Lane 52 — M6 role inspector (Track B, dashboard; ui-spec §3.10)

**Status:** After **lane 51** lands (the `role_installed` roster
substrate — §3:98). Everything else is in place: lane 34's layer-4
reader, lane 41's schedule handling, the drill-down idiom (lane 22).

**Effort:** medium (new view + derived module + tests).

## Context

The frozen spec (ui-spec §3.10, verbatim):

> Role, holder (linked), duties with lapse state, vacancy history,
> succession record drill-down-able like any derivation. Role rows join
> the diff panel.

The role inspector is the last dashboard view in the spec's build
order (M6, "T5.x green") — the office-facing complement to the NPC
inspector: not "who is this person" but "who holds this office, what
does it do, what's lapsed, who held it before."

## Read first (in order)

1. `docs/ui-spec.md` §3.10, §2 (selection), §1.2 (deep links).
2. `docs/frame-log-schema.md` §3:98 (`role_installed`), §3:97
   (`status_changed` — `duty_lapsed`/`role_appointed`).
3. Lane 51's landed emission/replay (read the committed code).
4. `dashboard/src/log/reconstruct.ts` — where the roster replay lands
   (lane 51's Python-side branch is the model; the dashboard needs the
   same — likely in-bounds here, verify and note).
5. The lane-30 diff panel (role rows joining it — read the landed
   `socialDiff.ts`; a role-transition row type is the integration
   point).
6. `docs/work-packets/reviews/README.md` — governance.

## Key design facts (pinned)

- **Data:** roles reconstruct from `role_installed` + `npc_died` +
  `status_changed` events (lane 51's semantics). The dashboard's
  reconstruction needs the roster — if lane 51's replay didn't extend
  the dashboard's reader, this lane adds it (in-bounds; the
  lane-34/41 precedent).
- **The role card:** title, current holder (linked — selection
  navigates to that NPC's inspector), duties with live lapse state
  (lapsed duties shown with their `duty_lapsed` event), vacancy
  history (vacated_at spans), succession record (each
  `role_appointed` event — drill-down-able "like any derivation": the
  lane-22 provenance panel is the drill idiom).
- **New route `/roles`** (`RolesScreen.vue`), chrome per the other
  screens; `view=roles` in the guard; ViewSwitcher link.
- **Role rows in the diff panel:** `socialDiff.ts` gains a
  role-transition delta type (vacancy, lapse, appointment) — a small,
  additive row type, not a restructure (read the landed module first).
- **Test data:** a run with a role lifecycle — lane 51's tests
  produce the shape; the T6 north-star run (`runs/north-star-01`)
  becomes the real fixture when lane 49 lands; synthetic JSONL
  fixtures otherwise.

## Task

1. `src/derived/roles.ts` (pure): events → role cards (roster at T,
   lapse states, vacancy history, succession chain). Tests incl. the
   full lifecycle.
2. `RolesScreen.vue` + `components/roles/` (role list + role card with
   duties/lapse/vacancy/succession + holder link).
3. The diff-panel role-row type (small additive edit).
4. Router + guard + ViewSwitcher entries; tests (derived + view +
   deep-link).
5. Run `npm run visual-diff`; report the number (informational).

## Acceptance

- `npm run build`, `npm test`, `npm run check-range` green;
  `uv run pytest -q` untouched-green; ruff clean.
- A role's full lifecycle (install → vacancy → lapse → succession)
  renders correctly at arbitrary T — covered by tests.
- Diff panel shows role-transition rows — covered by test.
- No new dependencies; no edits outside File boundaries.

## File boundaries

**Create:** `dashboard/src/derived/roles.ts` (+ tests),
`dashboard/src/views/RolesScreen.vue` (+ test),
`dashboard/src/components/roles/`

**Edit:** `dashboard/src/router/index.ts`,
`dashboard/src/components/ViewSwitcher.vue`,
`dashboard/src/derived/socialDiff.ts` (additive row type),
`dashboard/src/log/reconstruct.ts` / `types.ts` (**only** if roster
replay is missing — finding first if so)

**Do not touch:** landed lanes' other files, stores, frozen docs,
`runs/`, Python

## Conventions

- TS strict; tokens only; **local commits OK** (path-scoped, atomic
  `add && commit`); never push.
- File a delivery report on disk. Report format: delivered, acceptance
  per criterion with command tails, findings list.
