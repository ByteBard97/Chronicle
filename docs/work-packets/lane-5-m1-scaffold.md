# Lane 5 — M1 spike + dashboard scaffold (Track B, part 1)

**Status:** Ready to start **immediately**, in parallel with Lanes 1–4.
Your tree (`dashboard/`) shares no files with any other lane.
**Effort:** medium. This lane ends at a running empty shell, not views.

## Context

Chronicle's dashboard is a client-side Vue 3 app that reads sim run logs
over plain HTTP Range requests — no application backend
(`docs/ui-spec.md` §1.3). This lane proves the load-bearing assumption
(Range support) **before** building on it, then scaffolds the app. Views
(NPC inspector, console) are a later packet; do not build them here.

## Read first (in order)

1. `docs/ui-spec.md` §1.2–§1.3 (URL-state contract, runs directory,
   process model) and §0 (ruling constraints).
2. `docs/dashboard-build-plan.md` §0 (binding stack decisions — they are
   binding) and §2 M1.
3. `docs/ui-doctrines.md` (skim; D11/D12/D22 affect how you structure the
   reader and future map code).

## Task

1. **The Range spike — first, before anything else.** Create a dummy
   `runs/` log file; serve it with your dev setup; run
   `curl -H "Range: bytes=0-99"` against both `vite dev` and
   `vite preview`; record the results (status codes, headers) in
   `dashboard/README.md`. If either fails, stop and report — the fallback
   (a tiny static file server for `runs/` — file-serving is allowed, an
   application backend is not) is chosen before the reader client exists.
2. **Scaffold** `dashboard/` per the plan's binding decisions: Vue 3
   (`<script setup>`, Composition API) + Vite + TypeScript strict, Pinia,
   vue-router, VueUse (`useRouteQuery`), `@tanstack/vue-virtual`.
   Supply-chain rules: exact version pins, committed lockfile,
   `npm ci`, `--ignore-scripts` in `.npmrc`.
3. **Static wiring:** expose the repo-root `runs/` (gitignored) to the dev
   server — `server.fs.allow` + symlink, or serve the repo root with
   `dashboard/dist` as the app path. Record the chosen mechanism in
   `dashboard/README.md`.
4. **The standing Range assertion:** an automated check (script or test,
   runnable in CI) that fetches a run log with a `Range` header and
   asserts **206** — the spike verifies once; this catches silent
   regression later (ui-spec v1.2.1 §1.3).
5. **URL-state module:** `src/state/urlState.ts` implementing ui-spec §1.2's
   contract (`run`, `branch`, `t`, `view`, `sel`, `panels`, `filters`,
   `runB`/`alignment`) as one typed composable over `useRouteQuery` — the
   single place query keys are defined. Round-trip test: state → URL →
   state is identity.
6. **Shell:** app frame with run picker reading `runs/index.json`
   (tolerate its absence — Lanes 2/4 produce it later; mock one for now),
   empty view area, and the global salience-filter + selection stores as
   typed Pinia stubs (no UI beyond a smoke-test page).

## Acceptance

- Range spike results recorded in `dashboard/README.md`; standing 206
  assertion passes.
- `npm ci && npm run build` clean from a fresh checkout; type-check clean.
- URL-state round-trip test passes.
- No views built. If you find yourself styling, stop.

## File boundaries

- **Create/edit:** `dashboard/` only (plus its README). You may create a
  mock `runs/` fixture for tests.
- **Do not touch:** `chronicle/`, `scenarios/`, `docs/` (report findings
  to the coordinator instead), root config files.

## Conventions

- Do **not** `git commit` — the coordinator commits.
- `dashboard/map/` already exists (bake script, `whiterun_map.json`,
  gitignored PNG) — don't disturb it; the map view is a later milestone.
