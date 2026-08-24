# Lane 38 — M5 run comparison — delivery report

## Delivered

**Created:**
- `dashboard/src/derived/runCompare.ts` — pure merge-scan module (no Vue/store/router imports): `extractRolls`, `rollIdentityKey`, `findFirstDivergentRoll` (the linear first-divergent-roll finder), `computeDivergenceList` (ranked entity divergence + signed-Δ rows), `EntityDeltaRow`/`DivergenceEntry`/`DivergentRoll` types.
- `dashboard/src/derived/runCompare.test.ts` — 10 tests: extraction/keying, identical-runs → null, one-flipped-roll → exact tick/key, presence-only-on-one-side is not a divergence, earliest-not-any divergence, entity-list empty case, ranking by (first-divergence tick, blast radius), Δ sign, and a real-fixture proof against `runs/compare-fixture-a/b`.
- `dashboard/src/views/CompareScreen.vue` — the `/compare` screen: RunPicker×2 (A/B) + shared `T` input + "find first divergence" button + ViewSwitcher chrome; ranked `DivergenceList` as the primary section (above the fold), `DeltaTable` beneath it, two aligned `ComparePane`s (reusing `MapView.vue`) below that.
- `dashboard/src/views/CompareScreen.test.ts` — 4 tests: deep-link resolution of `run`/`runB`/`t`, DOM-order proof that the divergence list precedes the map panes, "find first divergence" jumping both playheads to the same tick, and a `t`-preset deep link landing both panes aligned on reload with zero interaction.
- `dashboard/src/components/compare/DivergenceList.vue`, `DeltaTable.vue`, `ComparePane.vue`, `useSecondRunLoad.ts` (run B's independent read-only load composable — the two-run analogue of lane 30's two-tick problem).
- `scenarios/run_compare_fixture.py` — a new, standalone producer script (not an edit to any landed scenario) that writes two real runs, `runs/compare-fixture-a` and `runs/compare-fixture-b`, sharing `seed_id: "compare-fixture-demo"`, identical schedule, differing only in `encounter_probability` (0.85 vs 0.15). Registered into `runs/index.json` automatically by `Driver.close()`.

**Edited (exactly the two named files, additive only):**
- `dashboard/src/router/index.ts` — added `CompareScreen` import, the `/compare` route, and `compare: "/compare"` in `VIEW_PATHS`.
- `dashboard/src/components/ViewSwitcher.vue` — added `"compare"` to `ViewName` and a `{ to: "/compare", view: "compare", label: "compare" }` entry to `LINKS`.

## Fixture-construction approach and why

Two real runs sharing one `seed_id`, produced by `scenarios/run_compare_fixture.py`:
- Identical schedule (5 NPCs across `market`/`bannered_mare`), identical `seed_id`/`save_uuid`/`generation` → every `encounter_rolled` record's `roll_key` (and therefore its `value`, per `chronicle.rng.roll()`'s pure-function-of-key design) is byte-identical between the two runs.
- The only config difference is `encounter_probability` (0.85 in run A vs 0.15 in run B) — the `threshold` each roll compares its (identical) `value` against. Verified directly: 96 shared roll keys, `value` identical on every one, `encountered` differs on 67/96.

This gives a real, deterministic, filesystem-backed "same seed_id, differing config" pair without hand-editing JSONL, and is exactly the shape `findFirstDivergentRoll` is built to catch (same key, same `value`, different `threshold`/`encountered`). The real-fixture test in `runCompare.test.ts` reads these two runs directly off disk and asserts exactly that shape holds, skipping gracefully (`describe.skipIf`) if the fixture hasn't been generated in a given environment.

This fixture only exercises the roll-level finder — it has no `witness()`/belief/grudge/obligation/reputation records, so `computeDivergenceList` correctly reports zero divergent entities for it (confirmed live in the browser: "0 divergent entities at t 23"). Entity-divergence-list correctness (ranking by first-divergence tick then blast radius, Δ signs, ties) is covered by synthetic `FrameRecord[]` fixtures in `runCompare.test.ts` and `CompareScreen.test.ts` instead, per the packet's explicit "your call" on fixture approach.

## Acceptance criteria — command tails

**`npm run build`:**
```
✓ 237 modules transformed.
dist/index.html                   0.75 kB │ gzip:  0.41 kB
dist/assets/index-DCrNT945.css   55.82 kB │ gzip:  9.21 kB
dist/assets/index-CaG-5ACW.js   255.05 kB │ gzip: 86.98 kB
✓ built in 933ms
```

**`npx vitest run` (full suite):**
```
 Test Files  75 passed (75)
      Tests  515 passed (515)
```

**`npm run check-range`:**
```
[dev] OK: 206 Partial Content, Content-Range: bytes 0-9/7320
[preview] OK: 206 Partial Content, Content-Range: bytes 0-9/7320
```

**`uv run pytest -q`:**
```
223 passed in 2.44s
```
(`git diff --stat -- chronicle/` returns empty — confirmed untouched.)

**`uv run ruff check .`:**
```
All checks passed!
```

## Live browser verification (Playwright)

Dev server started (`npm run dev`), navigated to `/compare?run=compare-fixture-a&runB=compare-fixture-b`:
- Ranked divergence list renders structurally and visually ABOVE the two map panes (confirmed both by DOM-order assertion in `CompareScreen.test.ts` and by screenshot: the list section occupies the top ~55% of the viewport, panes the bottom ~45%) — the primary rendering per the spec's v1.1 strengthening.
- The chrome banner shows the live roll-finder result inline: "first divergent roll: t 0 · market · adrianne / belethor..." (computed against the real fixture).
- Clicking "find first divergence" navigated the URL to `...&t=0` and both `.compare-pane__tick` labels read `"t 0"` — both playheads jumped together (verified via `browser_evaluate`).
- Reloading directly at `?run=compare-fixture-a&runB=compare-fixture-b&t=10` (a cold deep link, no interaction) rendered both `.compare-pane__tick` labels as `"t 10"` — aligned on load.
- Console showed repeated 416 (Range Not Satisfiable) errors from run A's LIVE tail poller — this is `streamReader.ts`'s own documented, harmless backoff behavior for a static run while `t` is unset ("live"); not introduced by this lane and not present once a tick is pinned via the URL or the finder.

`npm run visual-diff`: **4.84%** (69,721 / 1,440,000 pixels differ, against `/map` vs the approved mockup — this script targets `/map` specifically and is unaffected by this lane's changes; reported per the packet as informational only).

## Findings

1. **Blast-radius definition is implementer judgment, documented in-module.** The spec names "blast radius" as a sort tie-breaker but doesn't define it. This lane defines it as the count of an entity's own sub-records (beliefs/grudges/obligations/reputations) that differ between run A and run B at T — a local, per-entity measure — documented at `computeDivergenceList`'s header in `runCompare.ts`. A future lane wanting a network/cascade-propagation definition (e.g., "how many other entities' divergence causally follows from this one") would need graph-following logic this module doesn't build.
2. **`computeDivergenceList`'s first-divergence-tick detection replays both runs from scratch at every candidate tick** (O(ticks × records)) — a documented, deliberate scale tradeoff matching `derived/socialDiff.ts`'s own precedent ("correct at this data scale... not a general-purpose reader"), not something to silently "optimize" later without cause.
3. **`RunPicker`'s "no selection shows the most-recently-registered run" fallback display also applies to the run-B picker** (it's the same component, reused as-is per the packet's spirit) — cosmetic only; `urlState.runB`'s actual persisted value is unaffected (same non-writing-back guarantee `RunPicker.vue`'s own header documents for run A).
4. **`ComparePane.vue` does not thread `claimId`/`coverage`/`counts` into `MapView`**, so each pane's `StageLegend`/`LensPanel` render `MapView`'s own fixture-backed defaults rather than either run's real claim-stage breakdown — a deliberate low-ceremony scope call (the spec frames the maps as secondary context/selection-target, and per-pane claim-stage chrome duplicates work the primary divergence list already does better); flagged in case a future lane wants full per-run stage legends on the maps.
5. **The constructed fixture (`run_compare_fixture.py`) only produces roll-level divergence, not entity-level.** It has no `witness()` calls, so `computeDivergenceList` correctly reports zero divergent entities against it — confirmed live. Entity-list ranking/Δ-sign correctness is proven by the synthetic-`FrameRecord` unit tests instead. A future lane wanting a live-browser demo of a non-empty ranked list would need a second producer script with actual belief/grudge divergence (e.g., porting lane 37's two-driver `disabled_rules` pattern into a filesystem-persisted pair) — out of this lane's scope per the packet's "your call" on fixture approach.
