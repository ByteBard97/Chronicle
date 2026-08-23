# dashboard

Debug/observability web UI — a first-class deliverable, not an afterthought.
Reads directly off the event log and derived state in `chronicle/`.

Planned views: map with rumor overlay, causality
timeline (trace any belief back through its evidence chain to originating
events), and an injection console for manually firing events into a running
or scenario sim during debugging. The social-graph topology view is
**explicitly deferred** (docs/ui-spec.md §4): it unlocks only if Tier-3+
debugging demands topology the inspector's Relationships tab and the diff
panel can't show — and it may never earn a view, which is an acceptable
outcome per the forcing doctrine.

Build plan: [`../docs/dashboard-build-plan.md`](../docs/dashboard-build-plan.md)
(two tracks — sim-side frame-log substrate first, then the Vue app in tier
order). Stack: Vue 3 + Vite + TS, Pinia, vue-router/VueUse URL state,
`@tanstack/vue-virtual`, hand-rolled Canvas2D map. UI contract:
[`../docs/ui-spec.md`](../docs/ui-spec.md).

## map/

WhiterunWorld backdrop + spatial fixture for the map view:

- `whiterun_map.json` — committed. World→pixel calibration for the backdrop
  (`px = s·x + offsX + W/2`, `py = −s·y + offsY + H/2`) plus exterior
  world-unit and pixel coordinates for 26 named locations (load-door REFRs
  resolved via XTEL teleport links, plus named markers: market, Gildergreen,
  Skyforge, main gate, Heimskr's shrine). The sim's location IDs
  (`chronicle/fixtures/whiterun_schedule.py`) map onto these keys.
- `bake_whiterun_map.sh` — regenerates the backdrop with fo76utils from the
  user's own game files. Renders are deterministic run-to-run.
- `whiterun_topdown_4k.png` — gitignored (Bethesda-derived, internal use
  only; never commit). Regenerate with the bake script.

Extraction pipeline (esmdump REFR/XTEL dump → door resolution → JSON) is
ad-hoc in /tmp for now; productionize it if the location set needs to grow.
See docs/research/14-isometric-render-foundations.md for the render
foundations and verification.
