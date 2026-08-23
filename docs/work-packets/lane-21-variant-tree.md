# Lane 21 — variant tree view (Track B, dashboard; M3 §3.5)

**Status:** Ready to start immediately. Substrate landed: lane 12's
supersession machinery (`6235a1a`), lane 17's demo run
`runs/carrier-mutation-01` (1 mutation, 7 supersessions, 2+ variants),
lane 6's reader, lanes 11/14/16's integration idioms. Lane 15 (hygiene)
may run alongside — its three files (`SatelliteNode.vue`,
`RunPicker.vue`, `streamReader.ts`) are out of bounds here.

**Effort:** medium-large (new view + derived module + tests).

## Context

The last unbuilt M3 view (build-plan §M3: "variant tree (fixed
generational layout, hand-rolled SVG, supersession cross-links)"). This
is also vision v2.2's Bet 2 mitigation: the tree ships first as a
debugging instrument, so it pays for itself even if the player-facing
presentation bet fails. Build it developer-first.

The frozen spec (ui-spec §3.5, verbatim):

> One tree per claim: root = canonical; nodes = variants; **edges
> labeled with what the sim actually did** — mutated slot, old→new
> value, seeded mutation id, firing rule. …**Supersession records as
> dashed cross-links** (separate visual element matching their
> separate-record schema); node anatomy: variant summary, holder count
> at T, contested-claim dent where present. Node click → holder table +
> map overlay switches to this variant. Recolor modes: by hold,
> first-appearance time, holder count. **Fixed generational left-to-right
> layout, hand-rolled SVG** — positions stable across scrubs; no graph
> library, no force-direction.

## Read first (in order)

1. `docs/ui-spec.md` §3.5 (above) + §0/§1.2 (as-of-T, URL state).
   Frozen — findings to the coordinator.
2. `docs/frame-log-schema.md` — §4:119 (`mutation_applied`: slot,
   old/new value, `mutation_id`, roll_key), §4:120 **as amended**
   (`supersession`: nullable variant ids, `resolution_rule`,
   `confidence_dent`, the four replay fields). Note §5's keyframe
   variant fields (id, claim_id, parent_variant_id, slots, mutated_slot,
   gamets).
3. `dashboard/src/log/reconstruct.ts` (:35-47 `SocialState` — claims/
   variants/beliefs Maps) and `src/derived/mapMarkers.ts` (the lane-14
   derived-module idiom you mirror).
4. `src/stores/mapData.ts` — the landed run/state-at-T store. **Reuse
   it** (read-only) rather than building a third data path; if it's
   view-locked to the map, a thin shared extraction is a finding to
   report, not a refactor to do.
5. `src/router/index.ts` + the lane-11 `view=` guard — you'll add
   `/tree` and `view=tree`.
6. `runs/carrier-mutation-01/` — the real data: sample the
   `mutation_applied` + `supersession` records (`jq`). Note the null
   variant ids (the original telling) — the tree's canonical root.
7. `docs/work-packets/reviews/README.md` — governance; local commits
   fine (path-scoped), never push.

## Key design facts (pinned — deviations come back as findings)

- **New route `/tree`** (`VariantTreeScreen.vue`), chrome consistent
  with FeedScreen/MapScreen (RunPicker v-model, ViewSwitcher — add the
  tree link), `view=tree` deep-link mapping added to the lane-11 guard.
- **Data:** new pure `src/derived/variantTree.ts`: `SocialState` +
  trace records (`mutation_applied`, `supersession`) → tree model.
  Nodes: canonical root (the claim, "original telling" — where null
  variant ids point) + one per variant. Edges: lineage
  (`parent_variant_id`), labeled from `mutation_applied` (mutated slot,
  old→new, `mutation_id`; unmutated transmissions get a plain edge).
  Cross-links: dashed, one per `supersession` (loser → winner, labeled
  with `resolution_rule` + dent).
- **Holder count at T:** count `state.beliefs` values by `variant_id`
  (null → canonical root). Contested-claim dent: node marker where a
  supersession's winner belief holds that variant (show the dent value).
- **As-of-T everywhere:** nodes/edges/cross-links filtered to
  `gamets`/`tick` ≤ T; scrubbing re-derives (the map store's state-at-T
  pattern; tree positions are T-independent — only visibility/counts
  change, per "positions stable across scrubs").
- **Layout (pinned):** fixed generational left-to-right. x = lineage
  depth (canonical = 0). y = deterministic order (first-appearance
  gamets, tie → variant id). Hand-rolled SVG. **No graph library, no
  new dependencies.**
- **Claim selector:** one tree per claim — a simple claim dropdown in
  the chrome (claims enumerated from `SocialState.claims`; default the
  first). This is the tree's intrinsic picker, not the deferred map
  claim-picker.
- **Recolor modes:** implement **first-appearance** and
  **holder-count**. **"By hold" is out of scope** — no hold concept
  exists in the sim (location ids are bare strings); named finding,
  don't improvise a mapping.
- **Node click → holder table** (side panel: holders of that variant
  with confidence at T, linking their ids). The spec's "map overlay
  switches to this variant" is **deferred**: the map has no
  variant-level lens (lane 14 built claim-level rumor state). Named
  finding for a follow-up lane; do not build it here.
- **Allport-Postman taxonomy is not schema** (spec text) — edge labels
  are the real mutation data, nothing else.

## Task

1. `src/derived/variantTree.ts` (pure): tree-model builder + layout
   (deterministic positions) + holder-count/dent annotations. Unit
   tests: synthetic lineage (mutations, multi-generation, supersession
   to/from the canonical root) + the real run
   (`variantTree.realRun.test.ts` precedent: feedReader/mapMarkers).
2. `VariantTreeScreen.vue` + `components/tree/` (SVG tree, edge labels,
   dashed cross-links, node tooltips/summary, holder-table panel, claim
   dropdown, recolor toggle). <500 lines/file.
3. Router + guard + ViewSwitcher entries.
4. Tests: derived module (above); screen test (router pattern per
   Shell.test.ts): claim selector switches trees; scrub filters
   nodes/links by T; node click → holder table with the right holders;
   deep link `?view=tree&t=…` lands correctly; null-variant
   supersessions render against the canonical root (not a phantom
   "null" node).
5. Run `npm run visual-diff`; report the number (informational).

## Acceptance

- `npm run build`, `npm test`, `npm run check-range` green;
  `uv run pytest -q` untouched-green (186+); ruff clean.
- The tree renders `carrier-mutation-01`'s real lineage + all 7
  supersessions as dashed cross-links, at arbitrary T — covered by the
  real-run test.
- Layout is deterministic and scrub-stable (same tree, same positions —
  tested).
- No new dependencies; no edits outside File boundaries.

## File boundaries

**Create:**
- `dashboard/src/derived/variantTree.ts` (+ tests)
- `dashboard/src/views/VariantTreeScreen.vue` (+ test)
- `dashboard/src/components/tree/` (split as needed)

**Edit:**
- `dashboard/src/router/index.ts` (route + `view=tree` guard)
- `dashboard/src/components/ViewSwitcher.vue` (add the tree link)

**Do not touch:**
- map components, feed files, timeline files (landed lanes)
- `src/log/*`, `src/stores/frameLog.ts` (read, don't extend — findings)
- `src/stores/mapData.ts` (read/reuse; extraction is a finding)
- `SatelliteNode.vue`, `RunPicker.vue`, `streamReader.ts` (lane 15)
- frozen docs; `runs/`; Python-side anything

## Conventions

- TypeScript strict; `<script setup>`; tokens from `src/styles/tokens.css`.
- **Local commits OK** (path-scoped, explicit adds); never push.
- Existing test assertions immutable; conflicts are findings.
- Report format: what you delivered, acceptance per criterion with
  command tails, the visual-diff number, findings list (expected: the
  by-hold recolor gap; the map-overlay variant-lens deferral).
