# Lane 55 — M7 fix: Markarth coverage on the map (Track B)

**Status:** Ready to start immediately. Fixes M7 gate spec bug 2
(dossier step 2/3, "FAIL" — blocks the walkthrough outright). This is
the most severe finding, now independently confirmed **four times**
(lane 38, the walkthrough agent, chronicle-17, and the coordinator's
own `grep -c markarth dashboard/map/whiterun_map.json` → 0).

**Effort:** medium-large (data/asset lane, not primarily a rendering-
logic lane — read the whole context section before scoping your own
approach).

## Context

`runs/north-star-01`'s trace/events genuinely contain `markarth_city`
and `markarth_resident_1/2/3` — real data reaching Markarth via the
caravaneer, exactly what the north-star fixture and T2.6/T2.7 exist to
prove. But `dashboard/map/whiterun_map.json`'s location list is
Whiterun-only. The map cannot render a Markarth marker at all, which
structurally blocks walkthrough steps 2 ("watch the rumor spread,
including the carrier hop") and 3 ("click a Markarth believer") — not
a rendering nit, a missing region for the exact location the
walkthrough's premise depends on.

Per prior research (`notes/inbox` and earlier session memory this
project doesn't track in-repo): no permissive 2D Markarth map/coords
fixture exists to bake a second full map region from. **Do not go
looking for one or attempt a full second painterly bake** — that's out
of scope for a fix lane. The dossier's own proposed fix, and this
packet's pinned decision, is smaller:

**Pinned decision:** add an abstracted, clearly-labeled "elsewhere:
Markarth" region to the existing map (a distinct panel/inset/off-map
zone, not a second full backdrop) that still places real markers for
Markarth NPCs and lets the rumor overlay show claims arriving there.
It does not need to look like a real place — it needs to exist as a
clickable, marker-bearing region so steps 2/3 have somewhere to land.

## Read first

1. `docs/work-packets/reviews/2026-08-24-m7/dossier.md` steps 2/3 and
   screenshot `12-map-variant9.png`.
2. `dashboard/map/whiterun_map.json` — the location/coordinate fixture.
3. Whatever module builds map markers from run data (likely
   `mapMarkers.ts` or similar, per lane 14's history) — this is where
   Markarth NPCs currently get silently dropped.
4. `chronicle/fixtures/carrier_schedule.py` — `MARKARTH_RESIDENTS`,
   `CARAVANEER` — confirm the real location ids/npc ids you need to
   place (`markarth_city`, `markarth_resident_1/2/3`, `caravaneer`,
   `relief_caravaneer`).

## Task

1. Add a Markarth entry (or entries) to the map's location/coordinate
   data — an off-map/inset region is fine per the pinned decision
   above; give it a real, visible "Markarth" label so it doesn't read
   as a bug.
2. Extend the marker-building module so Markarth NPCs (currently
   dropped because their location isn't in the fixture) render there.
3. Confirm the rumor overlay renders claims arriving at Markarth
   markers the same way it does for Whiterun ones — no new overlay
   logic should be needed if the location/marker data is correct;
   report a finding if it is.
4. Tests: a Markarth marker renders for a run with Markarth NPCs
   (`north-star-01`-shaped fixture data); clicking it surfaces the
   belief-card inspector like any other marker.

## Acceptance

- `npm run build`, `npm test`, `npm run check-range` green;
  `uv run pytest -q` untouched-green; ruff clean.
- A Markarth NPC (e.g. `markarth_resident_1`) renders as a clickable
  marker on `/map` for `runs/north-star-01` — covered by test, and
  spot-check live against the real run.
- No regression to Whiterun's existing marker rendering.

## File boundaries

**Edit:** `dashboard/map/whiterun_map.json` (or a new sibling file, if
that's the cleaner shape — note your choice), the marker-building
module, `MapScreen.vue` only if the inset needs its own rendering
branch.

**Do not touch:** frozen docs, `runs/`, Python, the painterly Whiterun
backdrop asset itself.

## Conventions

- TS strict; tokens only; **local commits OK** (path-scoped, atomic
  `add && commit`); never push.
- File a delivery report on disk under
  `docs/work-packets/reviews/<date>-lane-55/`.
