# Lane 22 — provenance drill-down (Track B, dashboard; M3 §3.6)

**Status:** **Dependencies amended 2026-08-23 (pre-dispatch review
rulings):** lane 27 (supersession replay — the review's finding (a):
without it, appended Evidence is missing from replay and chains are
silently incomplete for T in (supersession tick, next keyframe)) and
lane 28 (inspector real-data wiring — finding (b): the invocation
points were pinned to an inspector that still renders fixture beliefs)
must land **first**. Substrate otherwise landed as before.

**Effort:** medium-large (derived module + panel component + two
invocation wirings + tests).

## Context

The final M3 view (build-plan §M3: "provenance drill-down (DAG-honest
span list)"), and the dashboard's signature gesture — ui-spec §3.6,
verbatim:

> Invoked from any belief/evidence element. Vertical span list: belief
> ← retelling (teller, tick, location, confidence delta) ← … ←
> witnessed event; unchanged retellings collapsed behind a count;
> mutations and resolutions always expanded. **DAG-honest:**
> corroborated beliefs render all incoming chains as parallel columns
> converging — never a spanning tree hiding a parent; superseded chains
> appear grayed with the resolution record between. Developer-excellent
> first; the Story-salience "lie has a biography" surface is a
> presentation pass over identical structure, deferred…

This is the view the whole provenance architecture exists to serve
(ADR-0007's "who believes this, from what evidence, through whom, since
when" — rendered).

## Read first (in order)

1. `docs/ui-spec.md` §3.6 (above), §1.2 (the `panels` query key —
   drill state serializes there), §0 (as-of-T). Frozen — findings to
   the coordinator.
2. `chronicle/claims.py` `chain_for` (the Python walk — your semantics
   reference; grounding evidence at index 0, `predecessor_belief_id`
   links) and the `Evidence` model (:119-136).
3. `dashboard/src/log/reconstruct.ts` — `SocialState`'s beliefs and
   evidence Maps (what's queryable; evidence is keyed how? verify, then
   design the walk).
4. `docs/frame-log-schema.md` §4:117 (`transmitted`: teller, tick via
   envelope, location, hearer belief), :119 (`mutation_applied`), :120
   (`supersession` as amended — the grayed-chain link).
5. The landed invocation hosts: `FeedScreen.vue`'s inspector region
   (:155-161, inspector props from selection) and `MapScreen.vue`'s
   inspector slot (lane 14's landed shape — read the committed file,
   not the lane-14 packet).
6. `src/state/urlState.ts` — the `panels` codec (shape, how panels open/
   close); the lane-11/14 store idioms.
7. `docs/work-packets/reviews/README.md` — governance; local commits
   fine (path-scoped), never push.

## Key design facts (pinned — deviations come back as findings)

- **Data:** new pure `src/derived/provenance.ts`: from `SocialState`
  (beliefs + evidence) + trace records (`transmitted`,
  `mutation_applied`, `supersession`) → a span-list model for one
  target belief at T. The walk follows `predecessor_belief_id` from the
  target's grounding evidence back to the witnessed event — the
  `chain_for` semantics, dashboard-side.
- **DAG honesty is the acceptance core,** not a nicety: a belief with
  multiple Evidence records (grounding + corroborations) renders **all
  incoming chains as parallel columns converging** — never a
  spanning-tree pick. Tests must include a corroborated belief and
  assert both parents render.
- **Collapse rule:** consecutive unchanged retellings (no mutation, no
  resolution) collapse behind a count ("— 3 retellings —");
  **mutations and resolutions are always expanded** with their real
  labels (mutated slot old→new + mutation id; resolution rule + dent).
- **Superseded chains:** where a `supersession` re-pointed a belief,
  the losing chain renders grayed with the supersession record as the
  interstitial element (loser → resolution record → winner). Null
  variant ids render as the canonical telling.
- **Panel, not a route:** the drill-down opens as a panel in the host
  screen; its open state + target belief id serialize into `panels`
  (existing codec — verify the shape and extend *within* it; if the
  codec can't express a drill target, that's a finding, not a new query
  key — §1.2's key list is frozen).
- **Invocation points (amended 2026-08-23):** a "drill" affordance on
  belief elements in (a) the real `NpcInspector` (both host screens —
  post-lane-28, its Beliefs-tab cards are real, drill-invokable
  elements) and (b) the **variant tree's holder table** (lane 21,
  landed — real holders; the earlier deferral is moot). Same component,
  all hosts.
- **As-of-T:** the panel renders the chain as of the screen's current
  T; scrubbing re-derives. Confidence deltas per span come from the
  chain's stored confidences (read, don't recompute decay — the
  reader's reconstructed values at T are the truth).

## Task

1. `src/derived/provenance.ts` (pure): the chain walk, parallel-column
   assembly, collapse computation, supersession interstitials. Unit
   tests: linear chain; corroborated belief (two parents); mutated
   hop; superseded chain (grayed + interstitial); collapse counting;
   canonical-root termination. Plus a real-run test against
   `carrier-mutation-01` (its 7 supersessions give you grayed chains).
2. `components/drilldown/ProvenancePanel.vue` (+ sub-components as
   needed, <500 lines/file): the vertical span list with parallel
   columns, collapse affordances, grayed superseded chains, span
   metadata (teller, tick, location, confidence delta). DOM/SVG per
   ui-doctrines (panels are DOM).
3. Wire the `panels` state + the two invocation points (FeedScreen,
   MapScreen inspectors).
4. Tests: derived module (above); panel component tests; host
   integration (router pattern): drill opens from a feed inspector
   belief → `panels` in the URL; deep link with the panel state lands
   open on the right belief; scrub re-derives.
5. Run `npm run visual-diff`; report the number (informational).

## Acceptance

- `npm run build`, `npm test`, `npm run check-range` green;
  `uv run pytest -q` untouched-green; ruff clean.
- DAG honesty tested: corroborated belief renders all parents;
  superseded chain grayed with the resolution record between.
- Collapse rule tested: unchanged runs collapsed, mutations/resolutions
  always expanded.
- Drill state round-trips through `panels` in the URL; deep link lands
  open on the target belief.
- No new dependencies; no edits outside File boundaries.

## File boundaries

**Create:**
- `dashboard/src/derived/provenance.ts` (+ tests)
- `dashboard/src/components/drilldown/` (panel + sub-components + test)

**Edit:**
- `dashboard/src/views/FeedScreen.vue`, `dashboard/src/views/MapScreen.vue`
  (invocation affordance + panel mount only)
- `dashboard/src/state/urlState.ts` — **only** if the `panels` codec
  needs a drill-target shape (finding first if so)

**Do not touch:**
- tree files (lane 21, in flight — invocation there is a follow-up)
- timeline files, map components, feed components (landed)
- `SatelliteNode.vue`, `RunPicker.vue`, `streamReader.ts` (lane 15)
- `src/log/*`, `src/stores/frameLog.ts`, `src/stores/mapData.ts`
  (read/reuse — findings, not edits)
- frozen docs; `runs/`; Python-side anything

## Conventions

- TypeScript strict; `<script setup>`; tokens from `src/styles/tokens.css`.
- **Local commits OK** (path-scoped, explicit adds); never push.
- Existing test assertions immutable; conflicts are findings.
- Report format: what you delivered, acceptance per criterion with
  command tails, the visual-diff number, findings list (expected: the
  tree-invocation follow-up; any `panels` codec gap).
