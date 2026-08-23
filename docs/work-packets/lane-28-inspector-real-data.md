# Lane 28 — NpcInspector → real data (Track B, dashboard)

**Status:** Ready to start immediately; **lane 22 depends on this** (and
on lane 27). The component's own header has promised this wiring since
lane 6 ("Lane 6's reader wires the real per-tick belief list at
integration") — it never happened; today the Beliefs tab renders static
fixture content ("Fralia Gray-Mane") regardless of selection.

**Effort:** medium (component rewiring + tests).

## Context

Surfaced by lane 22's pre-dispatch review: the drill-down's invocation
points were pinned to the two inspectors, but the inspector shows mock
beliefs — real provenance would have attached to fake belief ids. This
lane makes the inspector real: for the selected NPC at T, the Beliefs
tab lists their actual beliefs from reconstructed state, each card a
real, drill-invokable element.

## Read first (in order)

1. `dashboard/src/components/NpcInspector.vue` (+ `BeliefCard.vue`,
   `StrengthBar.vue`) — the shell and fixture shapes being replaced.
   **Keep the visual shell/mockup skin** (lane 8's approved design) —
   this is a data transplant, not a redesign.
2. `dashboard/src/stores/mapData.ts` — the landed run/state-at-T store
   (`socialState`, `setTick`, docked LIVE). FeedScreen and MapScreen
   both have it; read from the store, don't build a third path.
3. `dashboard/src/log/reconstruct.ts` — `SocialState`'s beliefs/rumors/
   claims/variants Maps (what a real belief card needs: claim id,
   variant slots, confidence/verbatim/gist, first_learned).
4. `dashboard/src/derived/rumorStage.ts` (`rumorStageAt`) and
   `src/derived/decay.ts` (decay-at-T helpers, lane-14's
   `decayBelief`) — stage + strength-bar values at T.
5. How the hosts pass selection: `FeedScreen.vue` (:155-161) and
   `MapScreen.vue`'s inspector slot (lane 14's landed shape — read the
   committed file). The selected NPC id already arrives as a prop.
6. `docs/ui-spec.md` §3.2 (the inspector's spec) — frozen; findings
   only.
7. `docs/work-packets/reviews/README.md` — governance.

## Pinned implementation decisions

- **Data path:** the component consumes the selection (id prop, as
  today) + `mapData`'s `socialState` directly. Beliefs for the NPC =
  `state.beliefs` values where `holder_id` matches. Each card: claim id
  (+ variant label when varianted), stage via `rumorStageAt` at the
  current T, strength bars from the belief's decayed-at-T strengths
  (the lane-14 decay helpers — don't recompute your own).
- **As-of-T and scrubbing** come free from the store — verify the card
  list changes when T changes (test).
- **Empty states:** an NPC with no beliefs renders an honest empty
  Beliefs tab (not the fixture); a dead-before-anything NPC (the
  Jarl) shows nothing — same discipline as lane 14's "unheard".
- **The provenance block** on each card: wire the top-level facts
  (evidence type, source/teller, tick learned) from the belief's
  grounding evidence. The full chain render is lane 22's drill-down —
  the block stays a summary, but a **real** one.
- **Fixture removal:** the static belief fixture goes away in this
  component (screenshot-stability is preserved by real data being
  deterministic). `MapScreen.test.ts`/`MapView.test.ts` assertions
  that pinned fixture content (e.g. "Fralia") are the **one authorized
  test-edit class** — update them to real-data expectations; behavior
  assertions (structure, tabs, salience) must be preserved.
- **Visual skin unchanged:** no layout/token changes — if real data
  breaks the mockup's layout assumptions (long ids, many cards), report
  it; don't redesign.

## Task

1. Rewire `NpcInspector.vue`/`BeliefCard.vue` to real beliefs per the
   pins (new `src/derived/inspectorBeliefs.ts` pure module if the
   assembly is non-trivial — the lane-14/21 idiom).
2. Tests: derived module (synthetic states: varianted/unvarianted,
   dormant via decay, empty); component tests (real beliefs render;
   stage/strengths correct at T; scrub changes the list; empty NPC);
   the authorized host-test updates.
3. Real-run test (precedent: feedReader/mapMarkers/variantTree):
   against `carrier-mutation-01`, a selected NPC shows their real
   beliefs at a pinned T (e.g. `relief_caravaneer` post-resolution —
   note this interacts with lane 27's replay fix; if lane 27 hasn't
   landed, pin the test at a T ≥ the post-supersession keyframe).

## Acceptance

- `npm run build`, `npm test`, `npm run check-range` green;
  `uv run pytest -q` untouched-green; ruff clean.
- Selecting an NPC shows their real beliefs at T on both host screens;
  scrubbing updates them — covered by tests.
- No fixture belief content remains; no layout/token changes.
- No edits outside File boundaries.

## File boundaries

**Edit:** `dashboard/src/components/NpcInspector.vue`,
`BeliefCard.vue` (+ their tests), authorized host-test updates
(`MapScreen.test.ts`, `MapView.test.ts` — fixture-content assertions
only)

**Create:** `dashboard/src/derived/inspectorBeliefs.ts` (+ test) if
needed

**Do not touch:** tree files (lane 21), timeline files, feed components,
`src/log/*` (except via lane 27), `src/stores/mapData.ts` (read/reuse),
frozen docs, `runs/`, Python

## Conventions

- TS strict; tokens only; **local commits OK** (path-scoped); never push.
- Report format: delivered, acceptance per criterion with command
  tails, findings list.
