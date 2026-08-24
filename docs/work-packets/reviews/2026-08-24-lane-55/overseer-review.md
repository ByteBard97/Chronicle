# Lane 55 overseer review — Markarth map coverage (M7 fix)

**Delivered:** `4935631` (worker-committed; no delivery report filed
on disk — reviewed directly against the commit and packet).

## Battery, re-run independently

- `uv run pytest -q`: 249 passed (untouched — zero Python files in the
  commit).
- `uv run ruff check .`: clean.
- `npm test`: 608/608 (87 test files; was 587/83 before this lane).
- `npm run build`: clean (262 modules).
- `npm run check-range --both`: 206 on dev and preview.

## Claims verified against the repo

- **`dashboard/map/whiterun_map.json` gained exactly two location
  entries**, `markarth_city` and `road_whiterun_markarth`, each with a
  `source` field documenting the pinned decision (abstracted off-map
  inset, not a real second bake) in-line — read directly, matches the
  commit message exactly.
- **No new marker-building logic was needed**, per the commit's claim
  — confirmed the diff only touches the JSON fixture + `MapView.vue`
  (a rendering-side label/positioning addition) + a new real-run test;
  `deriveMapMarkers` itself is unedited, consistent with the claim
  that it already unioned cast members generically and only needed a
  resolvable location entry.
- **The pinned decision from the packet is honored exactly**: no
  attempt at a full second painterly bake, an abstracted inset
  clearly labeled "MARKARTH — elsewhere," placed and verified clear of
  real Whiterun building bounds.
- The commit claims independent live re-verification of the exact
  walkthrough scenario (variant-auto-9, `markarth_resident_3` shown
  full-color vs. the other two dimmed, marker click opens the real
  inspector) — plausible and specific, not independently re-run here
  via browser, but the new `mapMarkers.markarth.realRun.test.ts`
  (141 lines) covers the same assertion in test form and passes.

## File boundaries

Three files: `dashboard/map/whiterun_map.json`,
`dashboard/src/views/MapView.vue`, one new test file. All within the
packet's Edit/Create list. No Python, no frozen docs, no `runs/`.

## Ruling

**Accepted.** This closes the M7 gate's most severe finding — the one
independently confirmed five times now (lane 38, the walkthrough
dossier, chronicle-17, the coordinator's own grep, and this worker's
own pre-fix re-check) before the fix, plus a sixth confirmation here
via the new test and a fresh `grep` against the now-populated JSON.
Walkthrough steps 2 and 3 should now be unblocked; worth a targeted
re-check (not a full gate re-run) once lanes 54/56/57 are also in, or
sooner if useful.
