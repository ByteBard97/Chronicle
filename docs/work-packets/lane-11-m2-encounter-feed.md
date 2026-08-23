# Lane 11 — M2 encounter-feed view (Track B, dashboard)

**Status:** Ready to start immediately. All prerequisites landed: the trace
reader (lane 6), the sidecar index (lane 5's `serveRuns` + Range support),
the real demo run `runs/whiterun-jarl-01` (715 trace records), and
`@tanstack/vue-virtual` (already a declared dependency, zero imports — this
lane is its first consumer). No file overlap with any other lane. Lane 12
(T2.3, Track A) runs in parallel on the Python side — disjoint trees.

**Effort:** medium-large (code).

## Context

The encounter feed is the last M2 piece. `docs/dashboard-build-plan.md`
(M2, Track B): "encounter feed (spec §3.3) — virtualized table over
`trace.jsonl` paginated by the sidecar index, four outcome states with
equal weight, filters, row-click → both inspectors + timeline jump."

There is **no mockup** for this view in `dashboard/design/` — unlike lane
8's map conversion, this view is **designed-from-spec**: ui-spec §3.3 plus
the vendored design tokens (`dashboard/design/design-tokens.md`,
`src/styles/tokens.css`, `PanelGlass` as the surface primitive). Do not
invent a second visual language; reuse lane 7/8's.

The frozen spec text (ui-spec §3.3, verbatim):

> Chronological table over the trace stream: tick, location, participants,
> outcome — **four outcome states with equal visual weight**: transmitted
> (claim/variant), rolled-against (roll value vs. threshold), declined
> (rule name — tell-decision rows land here from Tier 3), nothing-salient.
> Filterable by NPC/location/outcome/claim. Row click → both inspectors +
> timeline jump. Story salience shows transmissions and declines only.

M2 outcome scoping (build plan, accepted): only three outcome types are
instrumented by producers at M2 — `transmitted`, `encounter_rolled` with
`encountered: false` (the "rolled-against" negative row; schema:116 says
it renders with equal weight), and `nothing_salient`. The fourth,
`transmission_declined`, is schema-reserved and typed
(`src/log/types.ts:181`) but **no records exist anywhere** — the
four-state rendering is built once now (per ui-spec §3.3 and schema:121)
and exercised against fixtures/tests; the T3.4 declined-by-rule landing
case is out of scope until M4.

## Read first (in order)

1. `docs/ui-spec.md` §3.3 (line 82–84), §1.2 URL-state contract (line 40),
   §2 global chrome (line 59–61: one global selection, salience defaults),
   §0 doctrines (line 16–21: negative results first-class, as-of-T
   rendering), §5 developer twin (line 138: the named negative-row landing
   cases). Frozen — do not edit; findings go to the coordinator.
2. `docs/frame-log-schema.md` §4 (lines 106–121): the trace record payload
   shapes, exactly. Especially `encounter_rolled` (:116),
   `transmitted` (:117), `nothing_salient` (:118, reason enum
   `"both-informed" | "neither-informed"`), `transmission_declined` (:121).
3. `dashboard/src/log/` — `types.ts` (TraceRecordType union :173–183),
   `runReader.ts`, `streamReader.ts`, `sidecarIndex.ts` (`tickAtOrBefore`),
   `reconstruct.ts` (:233–239 — see the note below), `stores/frameLog.ts`.
4. `runs/whiterun-jarl-01/trace.jsonl` — sample real records of each type
   (`head`, `jq`). Counts: 520 `encounter_rolled` (330 `no_encounter`),
   186 `nothing_salient`, 4 `transmitted`, plus `belief_formed` /
   `relationship_formed`. `runs/whiterun-jarl-01/index.json` — note
   `streams.trace.tick_offsets` is dense (one per tick); that's your
   pagination spine.
5. `src/state/urlState.ts` — the single owner of query keys; codecs for
   `t`, `sel`, `filters` (JSON string). Feed filters go in `filters`.
   History modes: `t` is 'replace', everything else 'push'.
6. `src/views/Shell.vue` + `src/views/Shell.test.ts:22-38` — the router +
   `useUrlState` consumption pattern and its test template (memory
   history, stubbed fetch, `flushPromises`). Follow these, not
   `MapScreen.test.ts` (MapScreen doesn't touch URL state; your view does).
7. `src/router/index.ts` — two routes today; adding `/feed` is one line.
8. `src/components/NpcInspector.vue` — props-driven (`npcName`,
   `asOfTick`); you pass real props, no edits to it needed.
9. `src/stores/selection.ts` — a stub ("no view reads this yet"); this
   lane un-stubs it (see Task).
10. `docs/work-packets/reviews/README.md` — the governance section and
    coordination rules. Lane agents do not commit.

## Key design facts (verified by the coordinator; build on these)

- **Feed rows cannot come from `RunReader.stateAt`.** `reconstruct.ts`
  treats `encounter_rolled` and `nothing_salient` as deliberate no-ops
  (:233–239, "trace-only records with no derived-state effect"). The feed
  reads the **trace stream itself**, paged by
  `index.json → streams.trace.tick_offsets` via
  `readByteRange` (`streamReader.ts:37`). Build a small feed reader/store
  for this (new file) — do not extend `reconstruct.ts`.
- **Outcome mapping:** "rolled-against" = `encounter_rolled` with
  `encountered: false` (render roll value vs. threshold). `encounter_rolled`
  with `encountered: true` is an encounter that then produced
  `transmitted`/`nothing_salient` rows — it is not itself one of the four
  outcome rows; how you group or elide it is your design call, document it
  in the report.
- **Row click → both inspectors + timeline jump** has no existing
  end-to-end mechanism. The honest mechanism today: write
  `urlState.sel` (both participant ids) and `urlState.t` (the row's tick);
  FeedScreen renders inspector panel(s) for the selected participants by
  passing props to `NpcInspector`. Un-stub `selection.ts` and bind it to
  `urlState.sel`. Wiring the *map's* markers/inspector to selection is
  **not** this lane (that's M3 wiring) — feed-side only.
- **LIVE appending** hits the documented `frameLog.ts:29-39` limitation
  (docked state doesn't re-fold tailed records). Scope: the feed should
  append new rows while docked to LIVE. Simplest correct approach: your
  feed store owns its own `LiveTailPoller` over the trace stream
  (`runReader.startLiveTail` exists, :136–149) and appends rows
  independently of `frameLog`'s reconstructed state. If you find you need
  to edit `frameLog.ts`, that's a finding — report it, don't edit it.
- **Virtualization:** `@tanstack/vue-virtual@3.13.36` is installed and
  unused. Use it. No new dependencies.
- **Salience (pinned, per pre-dispatch review + owner-delegated executive
  decision 2026-08-23):** ui-spec §2 mandates all three levels plus an
  "all events" toggle on every raw list — frozen doctrine, not a design
  call. For this trace-native view:
  - *Story*: transmissions + declines only.
  - *Observer*: transmissions + declines visible at full weight; trace
    rows (rolled-against, nothing-salient) **collapsed into per-tick
    group-header rows** (e.g. "tick 47 · 12 trace rows ▸") sitting inline
    in the chronology — expanding a group reveals that tick's trace rows
    **in place**, so the "what was the sim doing around this
    transmission?" gesture never loses scroll position. (Rationale: the
    row mix is ~710 trace vs. ~4 transmissions — a binary show/hide
    toggle jumps between extremes and destroys position in a virtualized
    list; in-place per-tick expanders preserve chronology and proximity.
    Owner delegated this call; revisable after hands-on use.)
  - *Developer*: the full row set, no group chrome.
  The list-level "all events" toggle (`useSalienceStore().showAll`) is
  rendered at every level per spec as the global escape hatch (Story/
  Observer → full Developer row set).
  Implementation notes: in Observer mode the virtualized list is
  heterogeneous (data rows + group-header rows, variable heights —
  `measureElement`); group expand/collapse state is view-local UI state,
  NOT URL state. Mirror the existing `SalienceSwitch`/`useSalienceStore`
  consumption pattern (Shell.vue) — don't build a parallel one.
- **Claim filter vs. rolled-against rows (pinned):** `encounter_rolled`
  carries **no `claim_id`** (schema §4:116), so an active claim filter
  structurally excludes rolled-against rows. That's correct behavior,
  not a bug — `transmitted`/`nothing_salient`/`transmission_declined`
  carry claim ids and match. Document this in the filter's UI copy or a
  code comment so nobody "fixes" it.
- **Deep-link landing cases (M2 acceptance, build plan:222-224):** given a
  URL like `/?run=whiterun-jarl-01&t=7&view=feed&sel=irileth&filters={"outcome":"nothing_salient"}`,
  the feed must open at that tick with the named negative row visible
  without scrolling — one named landing case for the T1.3 rolled-against
  row and one for a nothing-salient row. (The T3.4 declined case is M4.)
  Lane 9's pytest side (`scenarios/conftest.py` `deep_link` fixture)
  already emits these URLs; your job is the dashboard resolving them.
- **visual-diff.mjs is map-hardcoded** — visual verification for this lane
  is component/view tests plus manual inspection. Do not extend the
  visual-diff harness (that's a separate future lane if wanted).

## Task

1. **Feed reader/store** (new): page the trace stream by tick using the
   sidecar `tick_offsets` + Range reads; materialize rows for the four
   outcome states (three real + `transmission_declined` handled
   render-ready); own a `LiveTailPoller` for docked appending; filter
   pipeline for NPC/location/outcome/claim driven by `urlState.filters`.
2. **`FeedScreen.vue`** (new view, route `/feed`): chrome strip consistent
   with `MapScreen` (RunPicker, SalienceSwitch), virtualized table
   (columns: tick, location, participants, outcome — outcome cell carries
   the state-specific payload: claim/variant id, roll vs. threshold, rule
   name slot, reason), inspector region rendering `NpcInspector` for the
   selected participant(s), footer consistent with the app shell.
3. **Row interaction:** click → `selection.select`/`follow` with both
   participant ids → `urlState.sel`, and `urlState.t` = row tick (this is
   the timeline jump; it detaches LIVE via the existing
   `bindToUrlState` machinery — verify and note the behavior in your
   report).
4. **Filters UI:** NPC / location / outcome / claim; state lives in
   `urlState.filters` (JSON codec already exists); deep links with filters
   resolve on load.
5. **Selection store:** un-stub `src/stores/selection.ts` — but keep it
   an options-style, view-agnostic, in-memory mirror with **no
   router/urlState imports inside the store** (its own header comment
   specifies this: "the shell wires it to `useUrlState().sel`";
   `useRouteQuery` inside a store action is unsafe outside a component
   effect scope). The two-way binding store ↔ `urlState.sel` lives in a
   **new composable** (e.g. `src/state/useSelectionUrlSync.ts`) installed
   from each screen's `<script setup>`: store writes → `sel` (push);
   deep-link `sel` → store on load. FeedScreen installs it now; the map
   will install the same composable later (M3 wiring, not this lane).
6. **Tests** (vitest, jsdom, `@vue/test-utils`, following
   `Shell.test.ts`'s router pattern):
   - Feed store: paging over a fixture trace stream (byte-range reads
     mocked), outcome mapping incl. `encountered: false` → rolled-against,
     `transmission_declined` render path against a synthetic record,
     filter pipeline.
   - `FeedScreen.test.ts`: view resolves `view=feed` + `t` + `filters`
     from the URL; the two named landing cases (rolled-against row and
     nothing-salient row visible without scrolling at the deep-linked
     tick — assert the row is within the rendered virtual window); row
     click writes `sel` (both participants) and `t`.
   - Salience: all three levels per the pinned semantics (key design
     facts): Story = transmissions + declines; Observer = same set with
     trace rows collapsed into per-tick group headers that expand in
     place, plus the `showAll` escape hatch; Developer = full row set.
     Toggle rendered at every level.
   - Determinism discipline: no `Date.now()`/`Math.random()` in
     assertions.
7. **App navigation (pinned, per pre-dispatch review — there is no
   existing nav idiom; `/` and `/map` are disconnected islands today):**
   add a minimal view-switcher to each screen's 44px chrome strip, right
   of the RunPicker: three route links (`/` console, `/map`, `/feed`),
   token-styled (`tokens.css`, no ad-hoc values), active-view state shown.
   Retrofit it to Shell.vue and MapScreen.vue as well as your new
   FeedScreen — same component, all three screens, so the idiom is
   established once. Register `/feed` in the router and make `view=feed`
   in a URL land there.

## Acceptance

- `npm run build`, `npm test`, `npm run check-range` all green;
  `uv run pytest -q` and `uv run ruff check .` untouched-green.
- Four outcome states rendered with equal visual weight; the three
  instrumented ones verified against `runs/whiterun-jarl-01` data in
  tests; `transmission_declined` verified against a synthetic record.
- Filters by NPC/location/outcome/claim work and round-trip through the
  URL; back/forward behaves per urlState's history modes.
- The two M2 landing cases pass as automated tests (rolled-against,
  nothing-salient: deep link → row visible without scrolling).
- Row click → both participant ids in `sel` + `t` jump, covered by test.
- Salience: all three levels + the "all events" toggle behave per the
  pinned semantics (key design facts) and are covered by tests —
  including Observer's per-tick group headers expanding in place.
- Virtualized: the table renders a window, not 715+ DOM rows (assert
  rendered-row count << total in a test).
- No new dependencies; no edits outside File boundaries.

## File boundaries

**Create:**
- `dashboard/src/views/FeedScreen.vue`
- `dashboard/src/components/feed/` (table, row, filter bar, outcome cell —
  split as needed, <500 lines/file)
- `dashboard/src/stores/feed.ts` (or `src/log/feedReader.ts` + thin store —
  your call, one new module)
- `dashboard/src/views/FeedScreen.test.ts`,
  `dashboard/src/stores/feed.test.ts` (names flexible)

**Edit:**
- `dashboard/src/router/index.ts` (add `/feed`)
- `dashboard/src/stores/selection.ts` (un-stub + urlState binding)
- `dashboard/src/views/MapScreen.vue`, `dashboard/src/views/Shell.vue` —
  **only** to add the chrome view-switcher (Task 7); no behavioral changes
- `dashboard/src/state/useSelectionUrlSync.ts` (new composable, Task 5 —
  may live under `src/state/` or `src/composables/`; one new small file)

**Do not touch:**
- `src/log/reconstruct.ts`, `src/log/runReader.ts`, `src/log/streamReader.ts`,
  `src/log/sidecarIndex.ts`, `src/stores/frameLog.ts` (lane 6 files — report
  gaps as findings)
- `src/components/NpcInspector.vue`, `TimelineBar.vue`, map components
- `dashboard/scripts/visual-diff.mjs`, `scenarios/` (lane 9/12 territory)
- frozen docs; `runs/` data files

## Conventions

- TypeScript strict; Vue 3 `<script setup>`; design tokens from
  `src/styles/tokens.css` (no ad-hoc hex values).
- **No `git commit`** — the coordinator reviews and commits (governance
  ruling, `docs/work-packets/reviews/README.md`). This supersedes any
  older packet text saying agents commit.
- Don't change existing test assertions; if one conflicts with this task,
  report it.
- Report format: what you delivered, acceptance status per criterion with
  command output tails, and a findings list.
