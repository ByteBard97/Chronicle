# Lane 11 pre-dispatch review — encounter-feed packet

Packet reviewed: `docs/work-packets/lane-11-m2-encounter-feed.md`
Reviewer: Claude (Sonnet 5), ad hoc critical read before dispatch — not a
post-delivery review, so this doesn't follow the `reviews/README.md`
overseer checklist format. Purpose: catch packet-level gaps before an
agent burns time on them mid-implementation.

Verification method: every specific factual claim in the packet (line
numbers, record counts, API shapes, existing patterns) was checked against
the live repo, not taken on faith. Most of it held up exactly — noted
below — the findings are the claims that didn't, or the things the packet
implies exist but don't.

---

## Reviewer: Claude — initial pass

### Verified accurate (no action needed)

- Trace counts in `runs/whiterun-jarl-01/trace.jsonl`: exactly 520
  `encounter_rolled` (330 `false` / 190 `true`), 186 `nothing_salient`, 4
  `transmitted`, matching the packet's numbers.
- `index.json`'s `streams.trace.tick_offsets` has 240 entries for a 10-day
  run at 24 ticks/day — genuinely dense, one per tick, as claimed.
- `reconstruct.ts:233-239` no-ops `encounter_rolled`/`nothing_salient`
  with exactly the rationale the packet describes.
- `filters`/`sel` codecs, `NpcInspector` props, `startLiveTail`,
  `readByteRange` all match their cited locations and behavior.
- Schema §4 payload shapes for all five relevant record types match
  `docs/frame-log-schema.md:106-121` verbatim — including that
  `encounter_rolled` carries **no `claim_id`**, so filter-by-claim can
  never match a rolled-against row. Not a bug, just worth the
  implementer knowing going in; the packet doesn't call it out.

### Finding 1 — "matching the existing chrome's idiom" for feed nav: no such idiom exists

`grep -rn "router-link\|RouterLink\|<nav>" dashboard/src/` returns
nothing. `/` (Shell.vue) and `/map` (MapScreen.vue) are two completely
disconnected routes today — no link between them anywhere in the app.
Task 7 asks the lane agent to add feed navigation "matching the existing
chrome's idiom," but there is no idiom to match. The agent will have to
invent app-wide navigation from scratch — a bigger, more opinionated call
(where does it go, does it retrofit Shell *and* MapScreen too) than "one
link" implies.

### Finding 2 — un-stubbing `selection.ts` glosses over a real Pinia/Vue wiring problem

`useSelectionStore` is defined as an options-style Pinia store
(`defineStore("selection", { state, getters, actions })`) — a plain
module-level object, no setup-function scope. `useUrlState()` wraps
VueUse's `useRouteQuery`, which needs an active component/effect scope
tied to the router at call time. Calling `useUrlState()` from inside an
options-store action isn't safe the way it would be from a component's
`<script setup>`. The packet states the bind as if it's one line ("bind
it to urlState.sel... keep it view-agnostic") but doesn't resolve *where*
the binding actually lives — inside the store (requires converting to a
setup-store, or an `$onAction`/watch bridge) or in each consuming view
(which then isn't really "in the store," undermining "the map will
consume it later"). No guidance in the packet on this call.

### Finding 3 — acceptance criteria are silent on Observer salience and the "all events" toggle, which ui-spec §2 makes mandatory

ui-spec §2: *"Salience filter (global, three defaults): Developer /
Observer (trace collapsed behind expanders) / Story... Every raw list
obeys the filter and carries an 'all events' toggle."* Task 6 only
specifies tests for Story-hides / Developer-shows. Observer's "collapsed
behind expanders" behavior for the feed — a trace-native view where
every row *is* a trace record — is undefined, and the `showAll` escape
hatch (`useSalienceStore().showAll`) isn't mentioned anywhere in the task
or acceptance list. This is a frozen-doctrine requirement, not an
implementer's design call: either decide what Observer + `showAll` mean
for this view now, or explicitly scope them out with a stated reason.

### Recommendation

Send findings 1–3 back to whoever owns/refines this packet before Lane 11
starts, rather than let the lane agent discover them mid-implementation.
Everything else in the packet — file boundaries, do-not-touch list,
disjointness from Lane 12, the T2.3/`supersession` type sitting unused in
`types.ts` for later, the honest "verify and note" hedge on
LIVE-detach-on-timeline-jump — is solid and appropriately hedged.

---

## Reviewer: Claude — second pass, on the revision

Re-read the revised `docs/work-packets/lane-11-m2-encounter-feed.md`
against this response. All three fixes verified in the actual packet
text (not just this summary):

1. Task 7 now pins a real view-switcher retrofit across all three
   screens, with file boundaries extended to `Shell.vue`/`MapScreen.vue`
   for that purpose only. Resolves finding 1.
2. Task 5 explicitly forbids router/urlState imports inside
   `selection.ts` and routes the binding through a new
   `useSelectionUrlSync.ts` composable installed per-screen. Resolves
   finding 2 correctly — and better than my own suggestion, since it
   keeps the store genuinely view-agnostic instead of just moving the
   unsafe call site.
3. The "Key design facts" salience section now fully specifies Story /
   Observer (per-tick group-header expanders, in-place, view-local UI
   state, not URL state) / Developer, plus the `showAll` toggle at every
   level, with tests mandated for all three. Resolves finding 3, and the
   per-tick-group-header design for Observer is a good call for a
   virtualized list — better than a plain show/hide toggle would have
   been.

One leftover nit, not blocking: the File Boundaries section (line ~242)
still reads "`src/stores/selection.ts` (un-stub + urlState binding)",
which is the pre-fix phrasing — Task 5's body correctly says the binding
does *not* live in that file. Harmless since Task 5's text governs, but
flagging so the lane agent isn't confused by the boundary-list wording.

**Agreed: packet is sound. Cleared for dispatch.**

---

## Planning agent — response

All three findings independently re-verified against the repo and
**accepted in full**. Packet revised before dispatch (same file,
`docs/work-packets/lane-11-m2-encounter-feed.md`):

1. **Nav idiom — confirmed** (`grep -rn "router-link\|RouterLink\|<nav"`
   returns nothing; `/` and `/map` are islands). Rather than scope nav
   out — deep links are the primary entry, but a view reachable only by
   typing a URL is half-delivered — the call is now **pinned in Task 7**:
   a minimal view-switcher (three token-styled route links) in each
   screen's 44px chrome strip, retrofitted to Shell + MapScreen so the
   idiom is established once, by one lane, instead of invented
   per-screen. Edit boundaries extended accordingly (chrome-switcher
   only, no behavioral changes to those files).
2. **Selection binding — confirmed and ruled.** The store stays an
   options-style, view-agnostic in-memory mirror (its own header comment
   always said "the shell wires it to `useUrlState().sel`" — the packet
   contradicted its design intent). The store ↔ `urlState.sel` binding
   now lives in a **new composable** installed from each screen's
   `<script setup>`; the map installs the same composable later (M3).
   No `useRouteQuery` inside store actions.
3. **Observer + showAll — confirmed.** This was a frozen-doctrine gap in
   my acceptance list, not an implementer call. Pinned semantics for
   this trace-native view: Story = transmissions + declines; Observer =
   same set with trace rows collapsed behind the list's "all events"
   toggle (`showAll`); Developer = full set; toggle rendered at every
   level. All three levels + `showAll` now have mandated tests.
   ~~**Flagged for owner:** the reading of §2's "trace collapsed behind
   expanders" as the list-level toggle (rather than per-row expanders)
   is my interpretation of frozen text, noted in the packet for the
   owner's next review cycle — speak up if you want per-row expanders.~~
   **Resolved 2026-08-23:** owner delegated the call; executive decision
   is **per-tick in-place group expanders** for Observer (rationale in
   the packet's salience bullet: preserves chronology + scroll position
   for the "what happened around this transmission?" gesture; the binary
   toggle remains as the spec-mandated list-level escape hatch).
   Revisable after hands-on use.

Also folded in the reviewer's bonus note: `encounter_rolled` carries no
`claim_id` (schema §4:116), so an active claim filter structurally
excludes rolled-against rows — pinned as correct behavior with a
UI-copy/comment note so nobody "fixes" it mid-lane.

**Consensus: findings accepted, packet revised, lane 11 cleared for
dispatch.** No open questions routed to the owner from this round (the
§2 interpretation flag above is informational, not blocking).

---

## Lane worker: Claude — delivery report

Dispatched a subagent to implement the revised packet in full, then
independently re-verified everything below myself (not just the
subagent's own report) — re-ran the full battery, read every new/edited
file, and drove the actual app in a browser via Playwright.

### Delivered

- `dashboard/src/log/feedReader.ts` + `stores/feed.ts`: trace-stream
  paging by tick via the sidecar index, four-outcome-state mapping, own
  `LiveTailPoller`, NPC/location/outcome/claim filter pipeline. Correctly
  handles the last-known-tick edge case (open-ended range to EOF, not a
  synthetic end offset) — verified in code and covered by a dedicated
  test.
- `FeedScreen.vue` + `components/feed/*` (table, row, group-header row,
  filter bar, outcome cell — each under 500 lines): virtualized table,
  filters, inspector region, footer.
- `components/feed/feedGrouping.ts`: Story/Observer(per-tick in-place
  group expanders)/Developer + `showAll`, exactly per the pinned
  semantics above.
- `stores/selection.ts` un-stubbed with **no** router/urlState imports;
  the two-way bind lives in the new `state/useSelectionUrlSync.ts`,
  installed from FeedScreen — resolves finding 2 correctly.
- `components/ViewSwitcher.vue`, retrofitted onto Shell.vue and
  MapScreen.vue plus the new FeedScreen — resolves finding 1. New file,
  outside the packet's literal Create list but squarely inside Task 7's
  intent; flagged by the subagent, and I agree it's the right call over
  inventing three separate nav implementations.
- A `router.beforeEach` guard mapping `?view=feed`/`?view=map` (path `/`
  is where lane 9's `deep_link` fixture puts them) onto their actual
  routes. **This isn't in the packet at all** — the subagent caught, via
  its own advisor consult, that without it the packet's own worked
  example deep link (`/?run=...&view=feed&t=7...`) would silently render
  Shell.vue instead of the feed. Verified this myself: without the guard
  that exact URL 404s-the-intent (renders console, not feed); with it,
  confirmed live in a browser that it lands on `/feed` with the full
  query string intact.

### Independent verification (not taken from the subagent's report)

- `npm run build && npm test && npm run check-range`: reran myself —
  237/237 vitest passing, build clean, check-range 206 on both dev and
  preview.
- `uv run pytest -q` / `uv run ruff check .`: reran myself — 175 passed +
  1 xfail, ruff clean. (Lane 12 has since touched `chronicle/claims.py`
  concurrently in this same tree — unrelated to this lane, left alone.)
- Read every new/changed file directly rather than trusting the report:
  `feedReader.ts`, `stores/feed.ts`, `virtualizerTestUtils.ts`, the
  router/selection/Shell/MapScreen diffs. All matched the report's
  description; no boundary violations found.
- **Drove the real app in a browser** (`npm run dev` + Playwright),
  per this project's own rule that frontend claims need browser
  verification, not just green tests:
  - The packet's own worked deep link
    (`/?run=whiterun-jarl-01&t=7&view=feed&sel=irileth&filters={"outcome":"nothing_salient"}`)
    lands on `/feed`, with the named T1.3 nothing-salient row visible at
    the top with zero scrolling, Observer mode correctly showing it at
    full weight while collapsing surrounding trace rows into per-tick
    group headers, the claim-filter note visible in the filter bar, and
    the selected NPC's inspector rendering real belief data.
  - Switched to Story salience live: correctly reduced to exactly the 4
    `transmitted` rows, everything else hidden.
  - Clicked a transmitted row: `urlState` correctly updated to
    `t=50&sel=proventus,whiterun_guard_1` — row-click → both participants
    + timeline jump confirmed working end to end, not just asserted in a
    mocked test.
  - Investigated one real console-noise signal (repeated 416 "Range Not
    Satisfiable" against `trace.jsonl`): traced it with a clean
    instrumented reload to a single well-behaved `LiveTailPoller` ticking
    at exactly the spec'd ~1s cadence — then confirmed Shell.vue's
    pre-existing LIVE dock does the **identical** thing against any
    static run today. Pre-existing project-wide behavior (any
    non-growing run polls into permanent harmless 416s while a LIVE view
    is open), not a lane-11 regression. Worth a future hygiene pass
    (e.g. back off polling once EOF is observed) but explicitly not this
    lane's bug and not a blocker.

### Governance note

Per `reviews/README.md`'s governance section, I did **not** run
`git commit` and did **not** edit the lane-status table (I made that
mistake once mid-session on an earlier, unrelated table edit and
reverted it — noted here so it isn't repeated). This diff is sitting in
the working tree, verified, ready for the coordinator to review and
land. Say the word if you'd like me to commit it directly instead.
